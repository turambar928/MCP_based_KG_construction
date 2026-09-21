#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Profile-conditioned constrained KG enhancement runtime.

This module operationalizes the Chapter 3/4 method claims:

- multi-scale quality profile P(G);
- lightweight semantic redundancy approximation for Q_uniq;
- f_phi neural routing when the trained NumPy model is available;
- neural-prior utility/cost based action selection;
- feasibility checks before each committed edit;
- one-step trial evaluation followed by receding-horizon re-planning.

The implementation is intentionally dependency-light so it can run inside the
MCP server without requiring the experiment environment.
"""

from __future__ import annotations

import copy
import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover - fallback keeps server importable.
    np = None


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPHI_DIR = os.path.join(ROOT, "exps", "decision_network")


SCALES = ("entity", "graph", "context")
FEATURES = ("S_iso", "S_red", "S_log", "S_sem", "n_v", "n_e", "density", "n_viol_feat")


@dataclass
class QualityProfile:
    """Operational quality profile used by the runtime optimizer."""

    S_iso: float
    S_red: float
    S_log: float
    S_sem: float
    n_v: int
    n_e: int
    density: float
    n_viol_feat: int
    q_score: float
    violations: List[Dict[str, Any]]

    def fphi_vector(self) -> List[float]:
        return [
            self.S_iso,
            self.S_red,
            self.S_log,
            self.S_sem,
            float(self.n_v),
            float(self.n_e),
            self.density,
            float(self.n_viol_feat),
        ]


@dataclass
class RouterOutput:
    p_repair: float
    pi: Dict[str, float]
    source: str


@dataclass
class CandidateAction:
    operation: str
    triple: Dict[str, Any]
    recommendation: Dict[str, Any]
    scale: str
    confidence: float


@dataclass
class ActionDecision:
    iteration: int
    accepted: bool
    operation: str
    triple: Dict[str, Any]
    scale: str
    utility: float
    delta_q: float
    hard_violation_delta: int
    cost: float
    reason: str
    before_q: float
    after_q: float
    router: Dict[str, Any]


class FphiRouter:
    """Runtime inference wrapper for the trained f_phi NumPy model."""

    def __init__(self, model_dir: str = FPHI_DIR):
        self.model_dir = model_dir
        self.params: Optional[Dict[str, Any]] = None
        self.scaler: Optional[Dict[str, Any]] = None
        self.available = False
        self._load()

    def _load(self) -> None:
        if np is None:
            return
        model_path = os.path.join(self.model_dir, "fphi_model.npz")
        scaler_path = os.path.join(self.model_dir, "scaler.json")
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            return
        try:
            params = np.load(model_path)
            self.params = {k: params[k] for k in params.files}
            with open(scaler_path, "r", encoding="utf-8") as f:
                self.scaler = json.load(f)
            self.available = True
        except Exception:
            self.params = None
            self.scaler = None
            self.available = False

    @staticmethod
    def _relu(x: Any) -> Any:
        return np.maximum(0, x)

    @staticmethod
    def _sigmoid(x: float) -> float:
        return float(1.0 / (1.0 + math.exp(-x)))

    @staticmethod
    def _softmax(z: Any) -> List[float]:
        z = z - z.max()
        e = np.exp(z)
        return [float(v) for v in (e / e.sum())]

    def predict(self, profile: QualityProfile) -> RouterOutput:
        if self.available and self.params is not None and self.scaler is not None and np is not None:
            x = np.asarray(profile.fphi_vector(), dtype=float)
            mu = np.asarray(self.scaler.get("mu", [0] * len(x)), dtype=float)
            sd = np.asarray(self.scaler.get("sd", [1] * len(x)), dtype=float)
            x = (x - mu) / (sd + 1e-9)
            p = self.params
            a1 = self._relu(x @ p["W1"] + p["b1"])
            a2 = self._relu(a1 @ p["W2"] + p["b2"])
            repair_logit = float((a2 @ p["wr"] + p["br"]).item())
            scale_logits = a2 @ p["Ws"] + p["bs"]
            probs = self._softmax(scale_logits)
            return RouterOutput(
                p_repair=self._sigmoid(repair_logit),
                pi={scale: probs[i] for i, scale in enumerate(SCALES)},
                source="f_phi",
            )

        # Fallback follows the same interface and keeps production robust.
        deficits = {
            "entity": max(0.0, 100.0 - min(profile.S_iso, profile.S_red)),
            "graph": max(0.0, 100.0 - profile.S_log),
            "context": max(0.0, 100.0 - profile.S_sem),
        }
        total = sum(deficits.values())
        p_repair = min(1.0, max(deficits.values()) / 25.0 + min(0.25, profile.n_viol_feat / 20.0))
        scale_prior = (
            {scale: deficits[scale] / total for scale in SCALES}
            if total > 0
            else {scale: 1.0 / len(SCALES) for scale in SCALES}
        )
        return RouterOutput(
            p_repair=p_repair,
            pi=scale_prior,
            source="heuristic_fallback",
        )


class MultiScaleConstraintOptimizer:
    """Constraint-driven optimizer used by EnhancementExecutor."""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        lower_bounds: Optional[Dict[str, float]] = None,
        upper_bounds: Optional[Dict[str, float]] = None,
        tau_repair: float = 0.05,
        tau_dup: float = 0.92,
        beta: float = 0.35,
        eta: float = 0.05,
        hard_reward: float = 0.20,
        confidence_weight: float = 0.02,
        max_iterations: int = 12,
        enforce_upper_bounds: bool = True,
        enforce_action_cost: bool = True,
    ):
        raw_weights = weights or {"S_iso": 0.25, "S_red": 0.25, "S_log": 0.25, "S_sem": 0.25}
        if any(value < 0 for value in raw_weights.values()) or sum(raw_weights.values()) <= 0:
            raise ValueError("quality weights must be non-negative and have a positive sum")
        weight_sum = sum(raw_weights.values())
        self.weights = {key: value / weight_sum for key, value in raw_weights.items()}
        self.lower_bounds = lower_bounds or {"S_iso": 55.0, "S_red": 55.0, "S_log": 60.0, "S_sem": 45.0}
        self.upper_bounds = upper_bounds or {"density": 0.75}
        self.tau_repair = tau_repair
        self.tau_dup = tau_dup
        self.beta = beta
        self.eta = eta
        self.hard_reward = hard_reward
        self.confidence_weight = confidence_weight
        self.max_iterations = max_iterations
        self.enforce_upper_bounds = enforce_upper_bounds
        self.enforce_action_cost = enforce_action_cost
        self.costs = {"delete": 0.30, "remove": 0.30, "retype": 0.16, "complete": 0.06, "add": 0.06, "bundle": 0.12}
        self.router = FphiRouter()

    def assess(self, entities: Sequence[Dict[str, Any]], triples: Sequence[Dict[str, Any]], original_text: str = "") -> QualityProfile:
        nodes = self._nodes(entities, triples)
        edges = [self._clean_triple(t) for t in triples if self._clean_triple(t)]
        n_v = len(nodes)
        n_e = len(edges)
        # Density is measured on the loop-free simple directed projection.  A
        # multi-relational KG may contain several triples for the same ordered
        # node pair, which must not make graph density exceed one.
        projected_edges = {(head, tail) for head, _, tail in edges if head != tail}
        density = len(projected_edges) / (n_v * (n_v - 1)) if n_v > 1 else 0.0

        connected = set()
        for h, _, t in edges:
            connected.add(h)
            connected.add(t)
        isolated = len(nodes - connected)
        r_iso = isolated / n_v if n_v else 1.0

        redundant_pairs = self._redundant_pairs(edges)
        r_red = self._redundant_excess_rate(n_e, redundant_pairs)

        logic_violations = self._logic_violations(edges, nodes)
        violating_edges = {v["edge_index"] for v in logic_violations if "edge_index" in v}
        r_log = len(violating_edges) / n_e if n_e else 0.0

        sem_penalty = self._semantic_penalty(edges, original_text)
        S_iso = 100.0 * (1.0 - r_iso)
        S_red = 100.0 * (1.0 - min(1.0, r_red))
        S_log = 100.0 * (1.0 - r_log)
        S_sem = 100.0 * (1.0 - sem_penalty)
        q_score = sum(self.weights[k] * v for k, v in {
            "S_iso": S_iso,
            "S_red": S_red,
            "S_log": S_log,
            "S_sem": S_sem,
        }.items())

        violations: List[Dict[str, Any]] = []
        for node in sorted(nodes - connected):
            violations.append({"scale": "entity", "type": "isolated_node", "target": node, "hard": False})
        for i, j, sim in redundant_pairs:
            violations.append({"scale": "entity", "type": "redundant_triple", "pair": [i, j], "similarity": sim, "hard": False})
        violations.extend(logic_violations)
        if sem_penalty > 0.05:
            violations.append({"scale": "context", "type": "semantic_low_evidence", "penalty": sem_penalty, "hard": False})

        return QualityProfile(
            S_iso=S_iso,
            S_red=S_red,
            S_log=S_log,
            S_sem=S_sem,
            n_v=n_v,
            n_e=n_e,
            density=density,
            n_viol_feat=len(violations),
            q_score=q_score,
            violations=violations,
        )

    def route(self, profile: QualityProfile) -> RouterOutput:
        return self.router.predict(profile)

    def optimize_and_apply(
        self,
        entities: List[Dict[str, Any]],
        triples: List[Dict[str, Any]],
        recommendations: Sequence[Dict[str, Any]],
        original_text: str = "",
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """Apply a receding-horizon constrained policy over finite candidates.

        At each step the current graph is profiled and routed again.  Every
        available candidate is evaluated on a trial graph; the highest-utility
        feasible candidate is committed, after which the policy re-plans from
        the new state.  This is exact over the finite one-step candidate set,
        while making no claim of a globally optimal edit sequence.
        """
        enhanced = [dict(t) for t in triples]
        decisions: List[ActionDecision] = []
        applied: List[Dict[str, Any]] = []

        profile = self.assess(entities, enhanced, original_text)
        initial_router = self.route(profile)
        router_trace: List[Dict[str, Any]] = [asdict(initial_router)]

        if initial_router.p_repair < self.tau_repair and not any(v.get("hard") for v in profile.violations):
            return enhanced, applied, {
                "initial_profile": asdict(profile),
                "final_profile": asdict(profile),
                "router": asdict(initial_router),
                "router_trace": router_trace,
                "decisions": [],
                "stopped_reason": "repair_probability_below_threshold",
            }

        stopped_reason = "iteration_limit"
        evaluated_states = set()
        for iteration in range(1, self.max_iterations + 1):
            before = self.assess(entities, enhanced, original_text)
            router = self.route(before)
            if iteration > 1:
                router_trace.append(asdict(router))
            hard_before = sum(bool(v.get("hard")) for v in before.violations)
            if router.p_repair < self.tau_repair and hard_before == 0:
                stopped_reason = "repair_probability_below_threshold"
                break
            if not before.violations:
                stopped_reason = "no_detected_violations"
                break

            candidates = self._recommendations_to_actions(recommendations)
            candidates.extend(self._violations_to_actions(before, enhanced))
            candidates = self._deduplicate_candidates(candidates)
            state_key = tuple(sorted(self._clean_triple(t) for t in enhanced if self._clean_triple(t)))
            scored = []
            for cand in candidates:
                candidate_key = (state_key, self._candidate_signature(cand))
                if candidate_key in evaluated_states:
                    continue
                evaluated_states.add(candidate_key)
                trial = self._apply_candidate(copy.deepcopy(enhanced), cand)
                after = self.assess(entities, trial, original_text)
                feasible, reason = self._check_constraints(before, after, cand)
                utility, delta_q, action_cost, hard_delta = self._utility(before, after, cand, router)
                scored.append((utility, feasible, reason, cand, trial, after, delta_q, action_cost, hard_delta))

            feasible_scored = [item for item in scored if item[1] and item[0] > 0.0]
            selected = max(feasible_scored, key=lambda item: item[0]) if feasible_scored else None
            for item in scored:
                utility, feasible, reason, cand, trial, after, delta_q, action_cost, hard_delta = item
                accepted = item is selected
                if accepted:
                    decision_reason = "accepted"
                elif feasible and utility > 0.0:
                    decision_reason = "lower_utility_than_selected"
                elif feasible:
                    decision_reason = "non_positive_utility"
                else:
                    decision_reason = reason
                decision = ActionDecision(
                    iteration=iteration,
                    accepted=accepted,
                    operation=cand.operation,
                    triple=cand.triple,
                    scale=cand.scale,
                    utility=utility,
                    delta_q=delta_q,
                    hard_violation_delta=hard_delta,
                    cost=action_cost,
                    reason=decision_reason,
                    before_q=before.q_score,
                    after_q=after.q_score,
                    router=asdict(router),
                )
                decisions.append(decision)
                if accepted:
                    enhanced = trial
                    applied.append(self._applied_record(cand, decision))

            if selected is None:
                stopped_reason = "no_positive_feasible_action"
                break

        final_profile = self.assess(entities, enhanced, original_text)
        return enhanced, applied, {
            "initial_profile": asdict(profile),
            "final_profile": asdict(final_profile),
            "router": asdict(initial_router),
            "router_trace": router_trace,
            "decisions": [asdict(d) for d in decisions],
            "stopped_reason": stopped_reason,
        }

    def _nodes(self, entities: Sequence[Dict[str, Any]], triples: Sequence[Dict[str, Any]]) -> set:
        nodes = {str(e.get("name", "")).strip() for e in entities if str(e.get("name", "")).strip()}
        for triple in triples:
            clean = self._clean_triple(triple)
            if clean:
                nodes.add(clean[0])
                nodes.add(clean[2])
        return nodes

    @staticmethod
    def _clean_triple(triple: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        head = str(triple.get("head", triple.get("source", ""))).strip()
        relation = str(triple.get("relation", triple.get("name", ""))).strip()
        tail = str(triple.get("tail", triple.get("target", ""))).strip()
        if not head and not relation and not tail:
            return None
        return head, relation, tail

    @staticmethod
    def _char_vector(text: str) -> Counter:
        normalized = re.sub(r"\s+", "", str(text).lower())
        grams = [normalized[i : i + 2] for i in range(max(1, len(normalized) - 1))]
        if len(normalized) <= 2:
            grams.append(normalized)
        return Counter(g for g in grams if g)

    @classmethod
    def _cosine_text(cls, a: str, b: str) -> float:
        va = cls._char_vector(a)
        vb = cls._char_vector(b)
        if not va or not vb:
            return 0.0
        dot = sum(va[k] * vb.get(k, 0) for k in va)
        na = math.sqrt(sum(v * v for v in va.values()))
        nb = math.sqrt(sum(v * v for v in vb.values()))
        return dot / (na * nb + 1e-9)

    def _triple_sim(self, a: Tuple[str, str, str], b: Tuple[str, str, str]) -> float:
        return (
            0.4 * self._cosine_text(a[0], b[0])
            + 0.2 * self._cosine_text(a[1], b[1])
            + 0.4 * self._cosine_text(a[2], b[2])
        )

    def _redundant_pairs(self, edges: Sequence[Tuple[str, str, str]]) -> List[Tuple[int, int, float]]:
        pairs = []
        for i in range(len(edges)):
            for j in range(i + 1, len(edges)):
                sim = 1.0 if edges[i] == edges[j] else self._triple_sim(edges[i], edges[j])
                if sim >= self.tau_dup:
                    pairs.append((i, j, sim))
        return pairs

    @staticmethod
    def _redundant_excess_rate(n_edges: int, pairs: Sequence[Tuple[int, int, float]]) -> float:
        """Fraction removable after retaining one representative per similarity component."""
        if n_edges == 0:
            return 0.0
        parent = list(range(n_edges))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            root_left, root_right = find(left), find(right)
            if root_left != root_right:
                parent[root_right] = root_left

        for left, right, _ in pairs:
            union(left, right)
        n_components = len({find(index) for index in range(n_edges)})
        return (n_edges - n_components) / n_edges

    def _logic_violations(self, edges: Sequence[Tuple[str, str, str]], nodes: set) -> List[Dict[str, Any]]:
        violations = []
        for idx, (head, relation, tail) in enumerate(edges):
            if not head or not relation or not tail:
                violations.append({"scale": "graph", "type": "empty_field", "edge_index": idx, "hard": True})
            if head == tail:
                violations.append({"scale": "graph", "type": "self_loop", "edge_index": idx, "hard": True})
            if relation.lower() in {"none", "unknown", "unknown_rel", "invalid_rel", "无", "未知"}:
                violations.append({"scale": "graph", "type": "invalid_relation", "edge_index": idx, "hard": True})
            if self._hierarchy_reversal(head, relation, tail):
                violations.append({"scale": "graph", "type": "hierarchy_reversal", "edge_index": idx, "hard": True})
            if head not in nodes or tail not in nodes:
                violations.append({"scale": "graph", "type": "dangling_endpoint", "edge_index": idx, "hard": True})
        return violations

    @staticmethod
    def _hierarchy_reversal(head: str, relation: str, tail: str) -> bool:
        if relation not in {"管理", "监管", "上级", "隶属于"}:
            return False
        lower_terms = ("县", "区", "镇", "乡", "街道")
        upper_terms = ("省", "自治区", "直辖市", "国家", "国务院")
        return any(x in head for x in lower_terms) and any(x in tail for x in upper_terms)

    def _semantic_penalty(self, edges: Sequence[Tuple[str, str, str]], original_text: str) -> float:
        if not edges:
            return 0.0
        text = re.sub(r"\s+", "", original_text or "")
        if not text:
            # Absence of evidence is not evidence of semantic correctness.
            # Use an explicitly neutral fallback that remains distinguishable
            # from source-supported scores and does not block all restoration.
            return 0.50
        unsupported = 0
        for _, _, tail in edges:
            normalized_tail = re.sub(r"\s+", "", tail)
            if not normalized_tail or normalized_tail not in text:
                unsupported += 1
        return unsupported / len(edges)

    def _recommendations_to_actions(self, recommendations: Sequence[Dict[str, Any]]) -> List[CandidateAction]:
        actions: List[CandidateAction] = []
        for rec in recommendations:
            implementation = rec.get("implementation", rec)
            raw_actions = implementation.get("actions", [])
            if not raw_actions and implementation.get("triple"):
                raw_actions = [implementation]
            if len(raw_actions) > 1:
                bundle_actions = []
                for instruction in raw_actions:
                    triple = instruction.get("triple", instruction)
                    clean = self._normalize_action_triple(triple)
                    if clean:
                        bundle_actions.append(
                            {
                                "operation": self._normalize_operation(
                                    instruction.get("action", instruction.get("operation", rec.get("type", "add")))
                                ),
                                "triple": clean,
                            }
                        )
                if bundle_actions:
                    actions.append(
                        CandidateAction(
                            operation="bundle",
                            triple={"actions": bundle_actions},
                            recommendation=rec,
                            scale=self._infer_scale(rec, "bundle", {}),
                            confidence=float(rec.get("confidence", implementation.get("confidence", 0.7)) or 0.7),
                        )
                    )
                    continue
            for instruction in raw_actions:
                triple = instruction.get("triple", instruction)
                clean = self._normalize_action_triple(triple)
                if not clean:
                    continue
                operation = self._normalize_operation(instruction.get("action", instruction.get("operation", rec.get("type", "add"))))
                scale = self._infer_scale(rec, operation, clean)
                actions.append(
                    CandidateAction(
                        operation=operation,
                        triple=clean,
                        recommendation=rec,
                        scale=scale,
                        confidence=float(rec.get("confidence", implementation.get("confidence", 0.7)) or 0.7),
                    )
                )
        return actions

    def _violations_to_actions(self, profile: QualityProfile, triples: Sequence[Dict[str, Any]]) -> List[CandidateAction]:
        actions: List[CandidateAction] = []
        clean_edges = [self._clean_triple(t) for t in triples]
        for violation in profile.violations:
            edge_index = violation.get("edge_index")
            if isinstance(edge_index, int) and 0 <= edge_index < len(clean_edges) and clean_edges[edge_index]:
                head, relation, tail = clean_edges[edge_index]
                triple = {"head": head, "relation": relation, "tail": tail}
                if violation.get("type") == "hierarchy_reversal":
                    actions.append(
                        CandidateAction(
                            operation="bundle",
                            triple={
                                "actions": [
                                    {"operation": "delete", "triple": triple},
                                    {"operation": "complete", "triple": {"head": tail, "relation": relation, "tail": head}},
                                ]
                            },
                            recommendation={
                                "source": "constraint_detector",
                                "category": "逻辑推理",
                                "type": "auto_fix_hierarchy_reversal",
                                "confidence": 0.9,
                            },
                            scale="graph",
                            confidence=0.9,
                        )
                    )
                elif violation.get("type") in {"self_loop", "empty_field", "invalid_relation"}:
                    actions.append(
                        CandidateAction(
                            operation="delete",
                            triple=triple,
                            recommendation={
                                "source": "constraint_detector",
                                "category": "逻辑推理",
                                "type": f"auto_remove_{violation.get('type')}",
                                "confidence": 0.85,
                            },
                            scale="graph",
                            confidence=0.85,
                        )
                    )
            if violation.get("type") == "redundant_triple":
                pair = violation.get("pair", [])
                if len(pair) == 2:
                    duplicate_idx = pair[1]
                    if 0 <= duplicate_idx < len(clean_edges) and clean_edges[duplicate_idx]:
                        head, relation, tail = clean_edges[duplicate_idx]
                        actions.append(
                            CandidateAction(
                                operation="delete",
                                triple={"head": head, "relation": relation, "tail": tail},
                                recommendation={
                                    "source": "constraint_detector",
                                    "category": "关系补全",
                                    "type": "auto_remove_redundant_triple",
                                    "confidence": float(violation.get("similarity", 0.9)),
                                },
                                scale="entity",
                                confidence=float(violation.get("similarity", 0.9)),
                            )
                        )
        return actions

    @staticmethod
    def _normalize_action_triple(triple: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        head = triple.get("head", triple.get("source", triple.get("subject")))
        relation = triple.get("relation", triple.get("name", triple.get("predicate")))
        tail = triple.get("tail", triple.get("target", triple.get("object")))
        clean = {"head": head, "relation": relation, "tail": tail}
        if any(v is None for v in clean.values()):
            return None
        return {k: str(v).strip() for k, v in clean.items()}

    @staticmethod
    def _normalize_operation(operation: str) -> str:
        op = str(operation or "add").lower()
        if op in {"remove", "delete", "del"}:
            return "delete"
        if op in {"retype", "replace", "rewrite"}:
            return "retype"
        return "complete"

    @staticmethod
    def _infer_scale(rec: Dict[str, Any], operation: str, triple: Dict[str, Any]) -> str:
        category = str(rec.get("category", "") + " " + rec.get("module", "") + " " + rec.get("type", "")).lower()
        if "逻辑" in category or "logic" in category or operation in {"delete", "retype"}:
            return "graph"
        if "context" in category or "semantic" in category or "语义" in category:
            return "context"
        return "entity"

    @staticmethod
    def _candidate_signature(cand: CandidateAction) -> Tuple[str, str, str]:
        payload = json.dumps(cand.triple, ensure_ascii=False, sort_keys=True)
        return cand.operation, cand.scale, payload

    def _deduplicate_candidates(self, candidates: Sequence[CandidateAction]) -> List[CandidateAction]:
        """Keep the highest-confidence instance of each operationally identical action."""
        unique: Dict[Tuple[str, str, str], CandidateAction] = {}
        for candidate in candidates:
            signature = self._candidate_signature(candidate)
            incumbent = unique.get(signature)
            if incumbent is None or candidate.confidence > incumbent.confidence:
                unique[signature] = candidate
        return list(unique.values())

    def _apply_candidate(self, triples: List[Dict[str, Any]], cand: CandidateAction) -> List[Dict[str, Any]]:
        if cand.operation == "bundle":
            for action in cand.triple.get("actions", []):
                child = CandidateAction(
                    operation=action["operation"],
                    triple=action["triple"],
                    recommendation=cand.recommendation,
                    scale=cand.scale,
                    confidence=cand.confidence,
                )
                triples = self._apply_candidate(triples, child)
            return triples

        target = cand.triple
        if cand.operation == "delete":
            # E is a multiset: one delete action removes one occurrence.  This
            # preserves a representative when repairing exact duplicates.
            result = []
            removed = False
            for triple in triples:
                if not removed and self._normalize_action_triple(triple) == target:
                    removed = True
                    continue
                result.append(triple)
            return result
        if cand.operation == "retype":
            # If a replacement relation is provided, rewrite matching head/tail.
            new_relation = cand.recommendation.get("new_relation") or target.get("new_relation")
            if new_relation:
                for triple in triples:
                    clean = self._normalize_action_triple(triple)
                    if clean and clean["head"] == target["head"] and clean["tail"] == target["tail"]:
                        triple["relation"] = str(new_relation)
            return triples
        if not any(self._normalize_action_triple(t) == target for t in triples):
            triples.append({**target, "confidence": cand.confidence, "enhanced": True, "source": "constraint_optimizer"})
        return triples

    def _check_constraints(self, before: QualityProfile, after: QualityProfile, cand: CandidateAction) -> Tuple[bool, str]:
        for key, lb in self.lower_bounds.items():
            before_value = getattr(before, key)
            after_value = getattr(after, key)
            # Preserve an already feasible dimension.  If the input starts
            # below its lower bound, allow feasibility restoration one step at
            # a time but never permit that deficient dimension to deteriorate.
            if before_value + 1e-9 >= lb and after_value + 1e-9 < lb:
                return False, f"lower_bound_violation:{key}"
            if before_value + 1e-9 < lb and after_value + 1e-9 < before_value:
                return False, f"deficit_regression:{key}"
            # Avoid destructive commits that degrade a dimension by more than 2 points.
            if after_value < before_value - 2.0:
                return False, f"quality_regression:{key}"
        if self.enforce_upper_bounds and after.density > self.upper_bounds.get("density", 1.0):
            return False, "upper_bound_violation:density"
        if cand.operation == "delete" and after.n_e == 0 and before.n_e > 0:
            return False, "destructive_empty_graph"
        return True, "feasible"

    def _utility(
        self,
        before: QualityProfile,
        after: QualityProfile,
        cand: CandidateAction,
        router: RouterOutput,
    ) -> Tuple[float, float, float, int]:
        delta_q = (after.q_score - before.q_score) / 100.0
        if cand.operation == "bundle":
            cost = sum(self.costs.get(a.get("operation"), 0.10) for a in cand.triple.get("actions", []))
        else:
            cost = self.costs.get(cand.operation, 0.10)
        prior = max(router.pi.get(cand.scale, 1.0 / 3.0), 0.05)
        cost_penalty = self.beta * cost if self.enforce_action_cost else 0.0
        hard_before = sum(bool(v.get("hard")) for v in before.violations)
        hard_after = sum(bool(v.get("hard")) for v in after.violations)
        hard_delta = hard_before - hard_after
        normalized_hard_gain = max(0, hard_delta) / max(1, hard_before)
        utility = (
            delta_q
            + self.hard_reward * normalized_hard_gain
            - cost_penalty
            + self.eta * math.log(prior + 1e-6)
            + self.confidence_weight * cand.confidence
        )
        return utility, delta_q, cost, hard_delta

    @staticmethod
    def _applied_record(cand: CandidateAction, decision: ActionDecision) -> Dict[str, Any]:
        rec = dict(cand.recommendation)
        rec["constraint_decision"] = asdict(decision)
        rec["operation"] = cand.operation
        rec["scale"] = cand.scale
        rec["applied_by"] = "constraint_optimizer"
        return rec
