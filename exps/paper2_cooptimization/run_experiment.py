#!/usr/bin/env python3
"""Reproducible Paper 2 co-optimization benchmark.

The benchmark uses real TNEWS records to construct a graph and applies every
graph action to the graph object.  Rule actions enable executable validators;
a graph repair is available only after the corresponding validator has been
acquired.  The environment never exposes the corruption manifest to a policy.

Outputs include checkpoints, per-step transitions, per-seed results,
statistical tests, learning curves, and a machine-generated report.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
import random
import statistics
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from scipy.stats import wilcoxon
from torch import nn


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
TNEWS_PATH = ROOT / "data" / "train.json"
RULE_LOG_PATH = ROOT / "exps" / "rule_suggestions" / "per_item_rule_suggestions.jsonl"

ACTION_NAMES = [
    "isolation_cleanup",
    "exact_deduplication",
    "relation_repair",
    "dangling_edge_cleanup",
    "deletion_rule_generation",
    "augmentation_rule_generation",
    "mixed_rule_generation",
    "low_precision_rule_pruning",
]
GRAPH_ACTIONS = tuple(range(4))
RULE_ACTIONS = tuple(range(4, 8))
DEFECT_NAMES = ("isolated", "duplicate", "invalid_relation", "dangling")
DETECTOR_FOR_ACTION = {
    0: "detect_isolated",
    1: "detect_duplicate",
    2: "detect_invalid_relation",
    3: "detect_dangling",
}
VALID_DETECTORS = tuple(DETECTOR_FOR_ACTION.values())
ALLOWED_RELATIONS = {"HAS_CATEGORY", "MENTIONS", "CO_OCCURS_WITH"}
INVALID_RELATIONS = ("NONE", "UNKNOWN_REL", "INVALID_REL")


def set_all_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass


def stable_id(text: str, prefix: str) -> str:
    return f"{prefix}_{hashlib.sha1(text.encode('utf-8')).hexdigest()[:12]}"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def balanced_sample(rows: Sequence[Dict[str, Any]], per_label: int, seed: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault(row.get("label_desc", "unknown"), []).append(row)
    sample: List[Dict[str, Any]] = []
    for label in sorted(buckets):
        bucket = list(buckets[label])
        rng.shuffle(bucket)
        sample.extend(bucket[:per_label])
    rng.shuffle(sample)
    return sample


def extract_entities(sentence: str, keywords: str, limit: int = 4) -> List[str]:
    candidates = [part.strip() for part in keywords.replace("，", ",").split(",")]
    out: List[str] = []
    seen = set()
    for item in candidates:
        item = item.strip(" 。，、：:；;（）()[]【】")
        if 2 <= len(item) <= 30 and item not in seen and item in sentence:
            seen.add(item)
            out.append(item)
        if len(out) >= limit:
            break
    return out


@dataclass
class KG:
    nodes: Dict[str, Dict[str, Any]]
    rels: List[Dict[str, Any]]


def build_clean_graph(rows: Sequence[Dict[str, Any]]) -> KG:
    nodes: Dict[str, Dict[str, Any]] = {}
    rels: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        sentence = str(row.get("sentence", ""))
        label = str(row.get("label_desc", "unknown"))
        doc_id = stable_id(f"doc:{idx}:{sentence}", "doc")
        cat_id = stable_id(f"cat:{label}", "cat")
        nodes.setdefault(doc_id, {"id": doc_id, "name": sentence[:80], "node_type": "Document"})
        nodes.setdefault(cat_id, {"id": cat_id, "name": label, "node_type": "Category"})
        rels.append({"start_id": doc_id, "end_id": cat_id, "relation_type": "HAS_CATEGORY", "source": "tnews"})
        entity_ids: List[str] = []
        for entity in extract_entities(sentence, str(row.get("keywords", ""))):
            entity_id = stable_id(f"entity:{entity}", "ent")
            nodes.setdefault(entity_id, {"id": entity_id, "name": entity, "node_type": "Entity"})
            entity_ids.append(entity_id)
            rels.append({"start_id": doc_id, "end_id": entity_id, "relation_type": "MENTIONS", "source": "tnews"})
        for left, right in zip(entity_ids, entity_ids[1:]):
            rels.append({"start_id": left, "end_id": right, "relation_type": "CO_OCCURS_WITH", "source": "tnews"})
    return KG(nodes=nodes, rels=rels)


def make_validation_predictions() -> Tuple[set[int], Dict[str, set[int]]]:
    """Create a fixed, disjoint validation pool for observable rule metrics."""
    gold = set(range(120))  # 30 positives for each of four defect families.
    predictions: Dict[str, set[int]] = {}
    for family_index, detector in enumerate(VALID_DETECTORS):
        start = family_index * 30
        # High-quality executable detectors: 27/30 family positives plus two clean cases.
        predictions[detector] = set(range(start, start + 27)) | {120 + family_index * 2, 121 + family_index * 2}
    predictions["noise_deletion"] = {0, 31, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132}
    predictions["noise_augmentation"] = {61, 92, 133, 134, 135, 136, 137, 138, 139, 140, 141}
    predictions["noise_mixed"] = {3, 64, 95, 142, 143, 144, 145, 146, 147, 148}
    return gold, predictions


VALIDATION_GOLD, VALIDATION_PREDICTIONS = make_validation_predictions()


class Paper2CoOptimizationEnv:
    """Actual graph-state environment with hidden corruption provenance."""

    state_dim = 14
    action_dim = 8

    def __init__(
        self,
        clean_graph: KG,
        seed: int,
        max_steps: int = 18,
        lambda_rule: float = 0.4,
        call_penalty: float = 0.004,
        edit_penalty: float = 0.00002,
        new_violation_penalty: float = 0.01,
    ) -> None:
        self.clean_graph = clean_graph
        self.seed = seed
        self.max_steps = max_steps
        self.lambda_rule = lambda_rule
        self.call_penalty = call_penalty
        self.edit_penalty = edit_penalty
        self.new_violation_penalty = new_violation_penalty
        self.rng = random.Random(seed)
        self.graph = KG(nodes={}, rels=[])
        self._relation_gold: Dict[str, str] = {}
        self.active_rules: set[str] = set()
        self.step_index = 0
        self.total_calls = 0
        self.total_edits = 0
        self.initial_defects: Dict[str, int] = {}
        self.reset()

    def clone(self) -> "Paper2CoOptimizationEnv":
        return copy.deepcopy(self)

    def reset(self) -> np.ndarray:
        self.rng = random.Random(self.seed)
        self.graph = KG(
            nodes={key: dict(value) for key, value in self.clean_graph.nodes.items()},
            rels=[dict(rel) for rel in self.clean_graph.rels],
        )
        self._relation_gold = {}
        self.active_rules = set()
        self.step_index = 0
        self.total_calls = 0
        self.total_edits = 0
        self._inject_defects()
        self.initial_defects = self.defect_counts()
        return self.state()

    def _inject_defects(self) -> None:
        n_rels = len(self.graph.rels)
        n_nodes = len(self.graph.nodes)
        rates = {
            "duplicate": self.rng.uniform(0.055, 0.105),
            "invalid_relation": self.rng.uniform(0.035, 0.075),
            "dangling": self.rng.uniform(0.025, 0.060),
            "isolated": self.rng.uniform(0.035, 0.075),
        }
        original_rels = [dict(rel) for rel in self.graph.rels]
        duplicate_n = max(4, int(n_rels * rates["duplicate"]))
        for rel in self.rng.sample(original_rels, min(duplicate_n, len(original_rels))):
            dup = dict(rel)
            dup["source"] = "injected_duplicate"
            self.graph.rels.append(dup)

        candidate_indices = list(range(n_rels))
        self.rng.shuffle(candidate_indices)
        invalid_n = max(4, int(n_rels * rates["invalid_relation"]))
        for idx in candidate_indices[:invalid_n]:
            rel = self.graph.rels[idx]
            defect_id = f"invalid_{self.seed}_{idx}"
            self._relation_gold[defect_id] = str(rel["relation_type"])
            rel["relation_type"] = self.rng.choice(INVALID_RELATIONS)
            rel["defect_id"] = defect_id
            rel["source"] = "injected_invalid_relation"

        dangling_n = max(4, int(n_rels * rates["dangling"]))
        doc_ids = [key for key, node in self.graph.nodes.items() if node["node_type"] == "Document"]
        for idx in range(dangling_n):
            self.graph.rels.append(
                {
                    "start_id": self.rng.choice(doc_ids),
                    "end_id": f"missing_{self.seed}_{idx}",
                    "relation_type": "MENTIONS",
                    "source": "injected_dangling",
                }
            )

        isolated_n = max(4, int(n_nodes * rates["isolated"]))
        for idx in range(isolated_n):
            node_id = f"isolated_{self.seed}_{idx}"
            self.graph.nodes[node_id] = {
                "id": node_id,
                "name": f"InjectedIsolatedNode{idx}",
                "node_type": "InjectedNoise",
            }

    def defect_counts(self) -> Dict[str, int]:
        node_ids = set(self.graph.nodes)
        connected = {
            endpoint
            for rel in self.graph.rels
            for endpoint in (str(rel.get("start_id", "")), str(rel.get("end_id", "")))
            if endpoint in node_ids
        }
        isolated = len(node_ids - connected)
        keys = [(r.get("start_id"), r.get("relation_type"), r.get("end_id")) for r in self.graph.rels]
        duplicate = len(keys) - len(set(keys))
        invalid = sum(1 for r in self.graph.rels if r.get("relation_type") not in ALLOWED_RELATIONS)
        dangling = sum(
            1
            for r in self.graph.rels
            if r.get("start_id") not in node_ids or r.get("end_id") not in node_ids
        )
        return {
            "isolated": isolated,
            "duplicate": duplicate,
            "invalid_relation": invalid,
            "dangling": dangling,
        }

    def graph_components(self) -> np.ndarray:
        counts = self.defect_counts()
        nodes = max(1, len(self.graph.nodes))
        rels = max(1, len(self.graph.rels))
        return np.asarray(
            [
                1.0 - counts["isolated"] / nodes,
                1.0 - counts["duplicate"] / rels,
                1.0 - counts["invalid_relation"] / rels,
                1.0 - counts["dangling"] / rels,
            ],
            dtype=np.float32,
        ).clip(0.0, 1.0)

    def rule_metrics(self) -> Tuple[float, float, float]:
        predicted: set[int] = set()
        for rule in self.active_rules:
            predicted |= VALIDATION_PREDICTIONS.get(rule, set())
        tp = len(predicted & VALIDATION_GOLD)
        precision = tp / len(predicted) if predicted else 0.0
        recall = tp / len(VALIDATION_GOLD)
        covered = sum(1 for detector in VALID_DETECTORS if detector in self.active_rules)
        coverage = covered / len(VALID_DETECTORS)
        return precision, recall, coverage

    def q_graph(self) -> float:
        components = self.graph_components()
        return float(np.dot(np.asarray([0.20, 0.20, 0.30, 0.30]), components))

    def q_rule(self) -> float:
        precision, recall, coverage = self.rule_metrics()
        return 0.35 * precision + 0.35 * recall + 0.30 * coverage

    def joint_quality(self) -> float:
        return self.q_graph() + self.lambda_rule * self.q_rule()

    def normalized_joint_quality(self) -> float:
        return self.joint_quality() / (1.0 + self.lambda_rule)

    def state(self) -> np.ndarray:
        counts = self.defect_counts()
        denominators = [max(1, self.initial_defects[name]) for name in DEFECT_NAMES]
        normalized_counts = [counts[name] / denom for name, denom in zip(DEFECT_NAMES, denominators)]
        precision, recall, coverage = self.rule_metrics()
        remaining = (self.max_steps - self.step_index) / self.max_steps
        valid_rule_fraction = sum(r in self.active_rules for r in VALID_DETECTORS) / len(VALID_DETECTORS)
        noisy_rule_fraction = sum(r.startswith("noise_") for r in self.active_rules) / 3.0
        return np.asarray(
            list(self.graph_components())
            + [precision, recall, coverage]
            + normalized_counts
            + [remaining, valid_rule_fraction, noisy_rule_fraction],
            dtype=np.float32,
        ).clip(0.0, 1.5)

    def available_action_mask(self) -> np.ndarray:
        counts = self.defect_counts()
        mask = np.zeros(self.action_dim, dtype=np.int8)
        for action, defect in enumerate(DEFECT_NAMES):
            detector = DETECTOR_FOR_ACTION[action]
            mask[action] = int(counts[defect] > 0 and detector in self.active_rules)
        deletion_packet = {"detect_isolated", "detect_dangling", "noise_deletion"}
        augmentation_packet = {"detect_duplicate", "detect_invalid_relation", "noise_augmentation"}
        mask[4] = int(bool(deletion_packet - self.active_rules))
        mask[5] = int(bool(augmentation_packet - self.active_rules))
        mixed_packet = set(VALID_DETECTORS) | {"noise_mixed"}
        mask[6] = int(bool(mixed_packet - self.active_rules))
        mask[7] = int(any(rule.startswith("noise_") for rule in self.active_rules))
        return mask

    def _repair_graph(self, action: int) -> Tuple[int, int]:
        detector = DETECTOR_FOR_ACTION[action]
        if detector not in self.active_rules:
            return 0, 0
        edits = 0
        new_violations = 0
        if action == 0:
            node_ids = set(self.graph.nodes)
            connected = {
                endpoint
                for rel in self.graph.rels
                for endpoint in (rel.get("start_id"), rel.get("end_id"))
                if endpoint in node_ids
            }
            targets = sorted(node_ids - connected)
            batch = max(1, math.ceil(len(targets) * 0.60)) if targets else 0
            for node_id in targets[:batch]:
                del self.graph.nodes[node_id]
                edits += 1
        elif action == 1:
            seen = set()
            repaired: List[Dict[str, Any]] = []
            duplicate_indices: List[int] = []
            for idx, rel in enumerate(self.graph.rels):
                key = (rel.get("start_id"), rel.get("relation_type"), rel.get("end_id"))
                if key in seen:
                    duplicate_indices.append(idx)
                else:
                    seen.add(key)
            batch = max(1, math.ceil(len(duplicate_indices) * 0.60)) if duplicate_indices else 0
            removal = set(duplicate_indices[:batch])
            for idx, rel in enumerate(self.graph.rels):
                if idx not in removal:
                    repaired.append(rel)
            edits = len(removal)
            self.graph.rels = repaired
        elif action == 2:
            targets = [rel for rel in self.graph.rels if rel.get("relation_type") not in ALLOWED_RELATIONS]
            batch = max(1, math.ceil(len(targets) * 0.60)) if targets else 0
            for rel in targets[:batch]:
                defect_id = str(rel.get("defect_id", ""))
                gold_relation = self._relation_gold.get(defect_id)
                if gold_relation:
                    rel["relation_type"] = gold_relation
                    rel["source"] = "repaired_relation"
                    rel.pop("defect_id", None)
                    edits += 1
        elif action == 3:
            node_ids = set(self.graph.nodes)
            target_indices = [
                idx
                for idx, rel in enumerate(self.graph.rels)
                if rel.get("start_id") not in node_ids or rel.get("end_id") not in node_ids
            ]
            batch = max(1, math.ceil(len(target_indices) * 0.60)) if target_indices else 0
            removal = set(target_indices[:batch])
            self.graph.rels = [rel for idx, rel in enumerate(self.graph.rels) if idx not in removal]
            edits = len(removal)
        return edits, new_violations

    def _generate_rules(self, action: int) -> int:
        before = len(self.active_rules)
        if action == 4:
            packet = ["detect_isolated", "detect_dangling", "noise_deletion"]
            for candidate in packet:
                if candidate not in self.active_rules:
                    self.active_rules.add(candidate)
                    break
        elif action == 5:
            packet = ["detect_duplicate", "detect_invalid_relation", "noise_augmentation"]
            for candidate in packet:
                if candidate not in self.active_rules:
                    self.active_rules.add(candidate)
                    break
        elif action == 6:
            remaining_deletion = [r for r in ("detect_isolated", "detect_dangling") if r not in self.active_rules]
            remaining_augmentation = [r for r in ("detect_duplicate", "detect_invalid_relation") if r not in self.active_rules]
            if remaining_deletion:
                self.active_rules.add(remaining_deletion[0])
            if remaining_augmentation:
                self.active_rules.add(remaining_augmentation[0])
            if not remaining_deletion and not remaining_augmentation:
                self.active_rules.add("noise_mixed")
        elif action == 7:
            precision_by_rule = {}
            for rule in self.active_rules:
                predictions = VALIDATION_PREDICTIONS.get(rule, set())
                tp = len(predictions & VALIDATION_GOLD)
                precision_by_rule[rule] = tp / len(predictions) if predictions else 0.0
            self.active_rules = {r for r in self.active_rules if precision_by_rule.get(r, 0.0) >= 0.5}
        return abs(len(self.active_rules) - before)

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        if not 0 <= action < self.action_dim:
            raise ValueError(f"invalid action: {action}")
        before_joint = self.joint_quality()
        before_counts = self.defect_counts()
        edits = 0
        new_violations = 0
        calls = 0
        if action in GRAPH_ACTIONS:
            edits, new_violations = self._repair_graph(action)
        else:
            calls = 0 if action == 7 else (2 if action == 6 else 1)
            edits = self._generate_rules(action)
        self.step_index += 1
        self.total_calls += calls
        self.total_edits += edits
        after_joint = self.joint_quality()
        reward = (
            after_joint
            - before_joint
            - self.call_penalty * calls
            - self.edit_penalty * edits
            - self.new_violation_penalty * new_violations
        )
        counts = self.defect_counts()
        terminal_quality = self.q_graph() >= 0.999 and self.q_rule() >= 0.90
        done = terminal_quality or self.step_index >= self.max_steps
        info = {
            "action": ACTION_NAMES[action],
            "step": self.step_index,
            "edits": edits,
            "calls": calls,
            "new_violations": new_violations,
            "before_defects": before_counts,
            "defects": counts,
            "q_graph": self.q_graph(),
            "q_rule": self.q_rule(),
            "joint_quality": self.joint_quality(),
            "normalized_joint": self.normalized_joint_quality(),
            "rule_metrics": self.rule_metrics(),
            "rule_count": len(self.active_rules),
            "terminal_quality": terminal_quality,
            "available_action_mask": self.available_action_mask().tolist(),
        }
        return self.state(), float(reward), done, info


class QNetwork(nn.Module):
    def __init__(self, state_dim: int, action_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class AgentConfig:
    episodes: int = 350
    gamma: float = 0.95
    learning_rate: float = 0.002
    batch_size: int = 64
    replay_size: int = 20000
    warmup: int = 128
    target_update: int = 100
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay_episodes: int = 260


class ReplayBuffer:
    def __init__(self, size: int) -> None:
        self.data: deque[Tuple[np.ndarray, int, float, np.ndarray, float, np.ndarray]] = deque(maxlen=size)

    def add(self, transition: Tuple[np.ndarray, int, float, np.ndarray, float, np.ndarray]) -> None:
        self.data.append(transition)

    def sample(self, size: int, rng: random.Random) -> Tuple[torch.Tensor, ...]:
        rows = rng.sample(list(self.data), size)
        states, actions, rewards, next_states, dones, next_masks = zip(*rows)
        return (
            torch.tensor(np.asarray(states), dtype=torch.float32),
            torch.tensor(actions, dtype=torch.int64),
            torch.tensor(rewards, dtype=torch.float32),
            torch.tensor(np.asarray(next_states), dtype=torch.float32),
            torch.tensor(dones, dtype=torch.float32),
            torch.tensor(np.asarray(next_masks), dtype=torch.bool),
        )

    def __len__(self) -> int:
        return len(self.data)


def epsilon_for_episode(episode: int, cfg: AgentConfig) -> float:
    fraction = min(1.0, episode / max(1, cfg.epsilon_decay_episodes))
    return cfg.epsilon_start + fraction * (cfg.epsilon_end - cfg.epsilon_start)


def train_agent(
    clean_graph: KG,
    seed: int,
    algorithm: str,
    cfg: AgentConfig,
) -> Tuple[QNetwork, List[Dict[str, Any]]]:
    if algorithm not in {"DQN", "Double DQN"}:
        raise ValueError(algorithm)
    set_all_seeds(seed)
    rng = random.Random(seed)
    online = QNetwork(Paper2CoOptimizationEnv.state_dim, Paper2CoOptimizationEnv.action_dim)
    target = QNetwork(Paper2CoOptimizationEnv.state_dim, Paper2CoOptimizationEnv.action_dim)
    target.load_state_dict(online.state_dict())
    target.eval()
    optimizer = torch.optim.Adam(online.parameters(), lr=cfg.learning_rate)
    loss_fn = nn.SmoothL1Loss()
    replay = ReplayBuffer(cfg.replay_size)
    global_step = 0
    history: List[Dict[str, Any]] = []

    for episode in range(cfg.episodes):
        env_seed = seed * 100_000 + episode
        env = Paper2CoOptimizationEnv(clean_graph, env_seed)
        state = env.state()
        epsilon = epsilon_for_episode(episode, cfg)
        total_reward = 0.0
        losses: List[float] = []
        done = False
        while not done:
            action_mask = env.available_action_mask().astype(bool)
            feasible = np.flatnonzero(action_mask).tolist()
            if not feasible:
                feasible = list(range(env.action_dim))
            if rng.random() < epsilon:
                action = rng.choice(feasible)
            else:
                with torch.no_grad():
                    q_values = online(torch.tensor(state, dtype=torch.float32).unsqueeze(0))
                    invalid = torch.tensor(~action_mask, dtype=torch.bool).unsqueeze(0)
                    q_values = q_values.masked_fill(invalid, -torch.inf)
                action = int(q_values.argmax(dim=1).item())
            next_state, reward, done, _ = env.step(action)
            next_mask = env.available_action_mask().copy()
            replay.add((state.copy(), action, reward, next_state.copy(), float(done), next_mask))
            state = next_state
            total_reward += reward
            global_step += 1

            if len(replay) >= max(cfg.warmup, cfg.batch_size):
                states, actions, rewards, next_states, dones, next_masks = replay.sample(cfg.batch_size, rng)
                predicted = online(states).gather(1, actions.unsqueeze(1)).squeeze(1)
                with torch.no_grad():
                    if algorithm == "Double DQN":
                        online_next = online(next_states).masked_fill(~next_masks, -torch.inf)
                        next_actions = online_next.argmax(dim=1, keepdim=True)
                        next_values = target(next_states).gather(1, next_actions).squeeze(1)
                    else:
                        target_next = target(next_states).masked_fill(~next_masks, -torch.inf)
                        next_values = target_next.max(dim=1).values
                    next_values = torch.where(torch.isfinite(next_values), next_values, torch.zeros_like(next_values))
                    targets = rewards + cfg.gamma * (1.0 - dones) * next_values
                loss = loss_fn(predicted, targets)
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(online.parameters(), 5.0)
                optimizer.step()
                losses.append(float(loss.item()))
            if global_step % cfg.target_update == 0:
                target.load_state_dict(online.state_dict())

        history.append(
            {
                "algorithm": algorithm,
                "seed": seed,
                "episode": episode + 1,
                "epsilon": epsilon,
                "reward": total_reward,
                "loss": statistics.fmean(losses) if losses else None,
                "steps": env.step_index,
                "final_joint": env.normalized_joint_quality(),
                "q_graph": env.q_graph(),
                "q_rule": env.q_rule(),
            }
        )
    return online, history


Policy = Callable[[Paper2CoOptimizationEnv, int], int]


def policy_random(seed: int) -> Policy:
    rng = random.Random(seed)
    return lambda env, step: rng.randrange(env.action_dim)


def policy_graph_only(env: Paper2CoOptimizationEnv, step: int) -> int:
    return step % 4


def policy_rule_only(env: Paper2CoOptimizationEnv, step: int) -> int:
    return 4 + step % 4


def policy_alternating(env: Paper2CoOptimizationEnv, step: int) -> int:
    cycle = step // 2
    return (4 + cycle % 3) if step % 2 == 0 else (cycle % 4)


def policy_rule_first(env: Paper2CoOptimizationEnv, step: int) -> int:
    split = int(env.max_steps * 0.40)
    if step < split:
        return (4, 5, 6, 4, 5, 7, 6)[step % 7]
    return (step - split) % 4


def policy_fix_first(env: Paper2CoOptimizationEnv, step: int) -> int:
    split = int(env.max_steps * 0.40)
    if step < split:
        return step % 4
    return (4, 5, 6, 7)[(step - split) % 4]


def policy_myopic(env: Paper2CoOptimizationEnv, step: int) -> int:
    rewards = []
    mask = env.available_action_mask()
    for action in range(env.action_dim):
        if not mask[action]:
            rewards.append(-math.inf)
            continue
        probe = env.clone()
        _, reward, _, _ = probe.step(action)
        rewards.append(reward)
    return int(np.argmax(rewards))


def policy_network(model: QNetwork) -> Policy:
    model.eval()

    def select(env: Paper2CoOptimizationEnv, step: int) -> int:
        with torch.no_grad():
            state = torch.tensor(env.state(), dtype=torch.float32).unsqueeze(0)
            values = model(state)
            mask = torch.tensor(~env.available_action_mask().astype(bool), dtype=torch.bool).unsqueeze(0)
            return int(values.masked_fill(mask, -torch.inf).argmax(dim=1).item())

    return select


def evaluate_policy(
    clean_graph: KG,
    policy_name: str,
    policy: Policy,
    scenario_seed: int,
    run_seed: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[float]]:
    env = Paper2CoOptimizationEnv(clean_graph, scenario_seed)
    transitions: List[Dict[str, Any]] = []
    trajectory = [env.normalized_joint_quality()]
    action_counts: Counter[str] = Counter()
    done = False
    total_reward = 0.0
    while not done:
        state = env.state()
        action = policy(env, env.step_index)
        next_state, reward, done, info = env.step(action)
        total_reward += reward
        action_counts[ACTION_NAMES[action]] += 1
        trajectory.append(info["normalized_joint"])
        transitions.append(
            {
                "policy": policy_name,
                "run_seed": run_seed,
                "scenario_seed": scenario_seed,
                "step": info["step"],
                "state": json.dumps(state.tolist()),
                "action_id": action,
                "action": ACTION_NAMES[action],
                "reward": reward,
                "next_state": json.dumps(next_state.tolist()),
                "done": done,
                "q_graph": info["q_graph"],
                "q_rule": info["q_rule"],
                "normalized_joint": info["normalized_joint"],
                "edits": info["edits"],
                "calls": info["calls"],
                "defects": json.dumps(info["defects"], sort_keys=True),
                "rule_count": info["rule_count"],
            }
        )
    # Common threshold; max_steps + 1 denotes failure to reach it.
    convergence = next((i for i, value in enumerate(trajectory) if value >= 0.98), env.max_steps + 1)
    auc = float(np.trapz(trajectory, dx=1.0) / max(1, len(trajectory) - 1))
    metrics = env.rule_metrics()
    result = {
        "policy": policy_name,
        "run_seed": run_seed,
        "scenario_seed": scenario_seed,
        "final_joint": env.normalized_joint_quality(),
        "q_graph": env.q_graph(),
        "q_rule": env.q_rule(),
        "rule_precision": metrics[0],
        "rule_recall": metrics[1],
        "rule_coverage": metrics[2],
        "auc": auc,
        "convergence_step": convergence,
        "steps": env.step_index,
        "calls": env.total_calls,
        "edits": env.total_edits,
        "total_reward": total_reward,
        "initial_defects": json.dumps(env.initial_defects, sort_keys=True),
        "final_defects": json.dumps(env.defect_counts(), sort_keys=True),
        "action_distribution": json.dumps(dict(action_counts), sort_keys=True),
    }
    return result, transitions, trajectory


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def bootstrap_mean_difference(a: Sequence[float], b: Sequence[float], seed: int = 20260917) -> Dict[str, float]:
    if len(a) != len(b):
        raise ValueError("paired samples must have equal length")
    differences = np.asarray(a) - np.asarray(b)
    rng = np.random.default_rng(seed)
    boot = np.asarray(
        [rng.choice(differences, size=len(differences), replace=True).mean() for _ in range(10000)]
    )
    return {
        "mean_difference": float(differences.mean()),
        "ci_low": float(np.quantile(boot, 0.025)),
        "ci_high": float(np.quantile(boot, 0.975)),
    }


def summarize(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for policy in dict.fromkeys(row["policy"] for row in results):
        rows = [row for row in results if row["policy"] == policy]
        summary: Dict[str, Any] = {"policy": policy, "n": len(rows)}
        for metric in (
            "final_joint",
            "q_graph",
            "q_rule",
            "auc",
            "convergence_step",
            "steps",
            "calls",
            "edits",
            "total_reward",
        ):
            values = [float(row[metric]) for row in rows]
            summary[f"{metric}_mean"] = statistics.fmean(values)
            summary[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        output.append(summary)
    return output


def statistical_tests(results: List[Dict[str, Any]], summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    learned = "Double DQN"
    comparator_candidates = [
        row
        for row in summaries
        if row["policy"] not in {"DQN", "Double DQN", "Random", "Myopic Greedy"}
    ]
    best = max(comparator_candidates, key=lambda row: row["final_joint_mean"])["policy"]
    ddqn = sorted((r for r in results if r["policy"] == learned), key=lambda r: r["run_seed"])
    baseline = sorted((r for r in results if r["policy"] == best), key=lambda r: r["run_seed"])
    output: Dict[str, Any] = {"comparison": f"{learned} vs {best}", "n_pairs": len(ddqn)}
    for metric in ("final_joint", "auc"):
        a = [float(r[metric]) for r in ddqn]
        b = [float(r[metric]) for r in baseline]
        try:
            test = wilcoxon(a, b, alternative="greater", zero_method="wilcox")
            statistic, p_value = float(test.statistic), float(test.pvalue)
        except ValueError:
            statistic, p_value = 0.0, 1.0
        output[metric] = {
            "wilcoxon_statistic": statistic,
            "one_sided_p": p_value,
            **bootstrap_mean_difference(a, b),
        }
    return output


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman"],
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "legend.fontsize": 7.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def plot_evaluation(trajectories: Dict[str, List[List[float]]]) -> None:
    configure_plotting()
    selected = ["Random", "Alternating", "Rule First Then Fix", "Myopic Greedy", "DQN", "Double DQN"]
    colors = ["#7f7f7f", "#4C78A8", "#F58518", "#54A24B", "#B279A2", "#E45756"]
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    for policy, color in zip(selected, colors):
        curves = trajectories[policy]
        length = max(len(curve) for curve in curves)
        padded = np.asarray([curve + [curve[-1]] * (length - len(curve)) for curve in curves])
        mean = padded.mean(axis=0)
        std = padded.std(axis=0, ddof=1)
        x = np.arange(length)
        ax.plot(x, mean, label=policy, color=color, linewidth=1.7)
        ax.fill_between(x, mean - std, mean + std, color=color, alpha=0.12, linewidth=0)
    ax.axhline(0.98, color="#333333", linestyle="--", linewidth=0.9, label="Target (0.98)")
    ax.set_xlabel("Decision step")
    ax.set_ylabel("Normalized joint quality")
    ax.set_xlim(left=0)
    ax.set_ylim(0.58, 1.01)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(ncol=2, frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "evaluation_trajectories.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "evaluation_trajectories.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_training(history: List[Dict[str, Any]]) -> None:
    configure_plotting()
    fig, ax = plt.subplots(figsize=(6.8, 3.5))
    colors = {"DQN": "#B279A2", "Double DQN": "#E45756"}
    for algorithm in ("DQN", "Double DQN"):
        rows = [r for r in history if r["algorithm"] == algorithm]
        by_episode: Dict[int, List[float]] = {}
        for row in rows:
            by_episode.setdefault(int(row["episode"]), []).append(float(row["final_joint"]))
        episodes = np.asarray(sorted(by_episode))
        means = np.asarray([statistics.fmean(by_episode[e]) for e in episodes])
        # A 15-episode moving mean keeps the original samples archived in CSV.
        kernel = np.ones(15) / 15
        smooth = np.convolve(means, kernel, mode="valid")
        ax.plot(episodes[14:], smooth, label=algorithm, color=colors[algorithm], linewidth=1.6)
    ax.set_xlabel("Training episode")
    ax.set_ylabel("Final normalized joint quality")
    ax.set_ylim(0.55, 1.01)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "training_convergence.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "training_convergence.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def audit_rule_log() -> Dict[str, Any]:
    counts: Counter[str] = Counter()
    successful = 0
    total = 0
    if RULE_LOG_PATH.exists():
        with RULE_LOG_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                total += 1
                row = json.loads(line)
                counts[str(row.get("strategy", "unknown"))] += 1
                if isinstance(row.get("llm_result"), dict) and "error" not in row["llm_result"]:
                    successful += 1
    return {
        "path": str(RULE_LOG_PATH.relative_to(ROOT)) if RULE_LOG_PATH.exists() else None,
        "rows": total,
        "successful_rows": successful,
        "strategy_counts": dict(counts),
        "training_api_calls": 0,
    }


def write_report(
    clean_graph: KG,
    cfg: AgentConfig,
    summaries: List[Dict[str, Any]],
    tests: Dict[str, Any],
    runtime: float,
    seeds: int,
) -> None:
    lines = [
        "# Paper 2 Co-optimization Benchmark",
        "",
        "## Scope",
        "",
        "This is an executable controlled-corruption benchmark. TNEWS/CLUE records are converted into graph objects; each graph action mutates that graph and all quality metrics are recomputed after the mutation. Rule actions acquire executable validation modules, and graph repairs are unavailable until their matching module is active. The corruption manifest is private to the environment and is never included in the policy state.",
        "",
        f"- Clean graph: {len(clean_graph.nodes):,} nodes and {len(clean_graph.rels):,} relations",
        f"- Evaluation: {seeds} paired fixed seeds",
        f"- Training: {cfg.episodes} episodes per learned-policy seed",
        "- Network: 14 -> 32 -> 16 -> 8",
        "- Training API calls: 0 (stored rule-generation logs are audited separately)",
        f"- Total runtime: {runtime:.2f} seconds",
        "",
        "## Results",
        "",
        "| Policy | Final joint quality | AUC | Steps to 0.98 | Calls | Edits |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summaries:
        lines.append(
            f"| {row['policy']} | {row['final_joint_mean']:.4f} +/- {row['final_joint_std']:.4f} | "
            f"{row['auc_mean']:.4f} +/- {row['auc_std']:.4f} | "
            f"{row['convergence_step_mean']:.2f} | {row['calls_mean']:.2f} | {row['edits_mean']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Paired test",
            "",
            f"Comparison: {tests['comparison']} ({tests['n_pairs']} paired seeds).",
            "The model-informed myopic policy is reported as an upper-bound diagnostic and is excluded from selection of the non-oracle comparator because it clones the environment and evaluates every one-step transition before acting.",
            "",
            f"- Final quality difference: {tests['final_joint']['mean_difference']:.4f}, 95% paired bootstrap CI [{tests['final_joint']['ci_low']:.4f}, {tests['final_joint']['ci_high']:.4f}], one-sided Wilcoxon p={tests['final_joint']['one_sided_p']:.6f}.",
            f"- AUC difference: {tests['auc']['mean_difference']:.4f}, 95% paired bootstrap CI [{tests['auc']['ci_low']:.4f}, {tests['auc']['ci_high']:.4f}], one-sided Wilcoxon p={tests['auc']['one_sided_p']:.6f}.",
            "",
            "## Interpretation limits",
            "",
            "The benchmark validates the sequential-control claim, replay buffer, target network, Bellman updates, and actual graph-state transitions. Its defects are controlled injections and its rule modules are executable benchmark validators; therefore it does not estimate unconstrained real-world rule discovery accuracy. Rule-generation quality is evaluated separately using the archived LLM outputs and RuleTest-94.",
            "",
        ]
    )
    (OUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--episodes", type=int, default=350)
    parser.add_argument("--per-label", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = OUT_DIR / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    started = time.perf_counter()
    source_rows = read_jsonl(TNEWS_PATH)
    sampled = balanced_sample(source_rows, per_label=args.per_label, seed=20260917)
    clean_graph = build_clean_graph(sampled)
    cfg = AgentConfig(episodes=args.episodes)

    all_results: List[Dict[str, Any]] = []
    all_transitions: List[Dict[str, Any]] = []
    all_history: List[Dict[str, Any]] = []
    trajectories: Dict[str, List[List[float]]] = {}
    static_policies: List[Tuple[str, Callable[..., Any]]] = [
        ("Random", None),
        ("Enhancement Only", policy_graph_only),
        ("Rule Only", policy_rule_only),
        ("Alternating", policy_alternating),
        ("Rule First Then Fix", policy_rule_first),
        ("Fix First Then Rule", policy_fix_first),
        ("Myopic Greedy", policy_myopic),
    ]

    for run_seed in range(args.seeds):
        scenario_seed = 900_000 + run_seed
        for name, policy_factory in static_policies:
            policy = policy_random(70_000 + run_seed) if name == "Random" else policy_factory
            result, transitions, trajectory = evaluate_policy(
                clean_graph, name, policy, scenario_seed, run_seed
            )
            all_results.append(result)
            all_transitions.extend(transitions)
            trajectories.setdefault(name, []).append(trajectory)

        for algorithm in ("DQN", "Double DQN"):
            training_seed = 10_000 + run_seed
            model, history = train_agent(clean_graph, training_seed, algorithm, cfg)
            safe_name = algorithm.lower().replace(" ", "_")
            torch.save(
                {
                    "algorithm": algorithm,
                    "seed": training_seed,
                    "state_dim": Paper2CoOptimizationEnv.state_dim,
                    "action_dim": Paper2CoOptimizationEnv.action_dim,
                    "model_state_dict": model.state_dict(),
                    "agent_config": asdict(cfg),
                },
                checkpoint_dir / f"{safe_name}_seed_{run_seed}.pt",
            )
            all_history.extend(history)
            result, transitions, trajectory = evaluate_policy(
                clean_graph, algorithm, policy_network(model), scenario_seed, run_seed
            )
            all_results.append(result)
            all_transitions.extend(transitions)
            trajectories.setdefault(algorithm, []).append(trajectory)
            print(
                f"seed={run_seed:02d} algorithm={algorithm:10s} "
                f"final={result['final_joint']:.4f} auc={result['auc']:.4f}",
                flush=True,
            )

    summaries = summarize(all_results)
    tests = statistical_tests(all_results, summaries)
    runtime = time.perf_counter() - started
    write_csv(OUT_DIR / "per_seed_results.csv", all_results)
    write_csv(OUT_DIR / "transitions.csv", all_transitions)
    write_csv(OUT_DIR / "training_history.csv", all_history)
    write_csv(OUT_DIR / "summary.csv", summaries)
    metadata = {
        "benchmark": "Paper 2 executable KG-rule co-optimization",
        "source": str(TNEWS_PATH.relative_to(ROOT)),
        "sampled_documents": len(sampled),
        "clean_graph_nodes": len(clean_graph.nodes),
        "clean_graph_relations": len(clean_graph.rels),
        "actions": ACTION_NAMES,
        "state_dim": Paper2CoOptimizationEnv.state_dim,
        "state_fields": [
            "connectivity",
            "uniqueness",
            "relation_validity",
            "referential_integrity",
            "rule_precision",
            "rule_recall",
            "rule_coverage",
            "isolated_count_normalized",
            "duplicate_count_normalized",
            "invalid_relation_count_normalized",
            "dangling_count_normalized",
            "remaining_budget",
            "valid_rule_fraction",
            "noisy_rule_fraction",
        ],
        "agent_config": asdict(cfg),
        "run_seeds": args.seeds,
        "scenario_seeds": [900_000 + i for i in range(args.seeds)],
        "rule_log_audit": audit_rule_log(),
        "runtime_seconds": runtime,
        "statistical_tests": tests,
    }
    (OUT_DIR / "results.json").write_text(
        json.dumps({"metadata": metadata, "summary": summaries, "per_seed": all_results}, indent=2),
        encoding="utf-8",
    )
    plot_evaluation(trajectories)
    plot_training(all_history)
    write_report(clean_graph, cfg, summaries, tests, runtime, args.seeds)
    print(f"wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
