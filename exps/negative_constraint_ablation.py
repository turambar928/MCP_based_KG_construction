#!/usr/bin/env python3
"""Controlled ablation of the optimizer's negative constraints.

Each case starts with a sparse five-node graph containing two isolated nodes.  The proposal
queue first contains two useful completion actions, followed by unsupported but structurally
valid edges.  The useful actions improve connectivity; the remaining actions have zero quality
gain and emulate over-completion pressure.  We compare the complete optimizer with variants
that remove the density ceiling, action-cost penalty, or both.

Outputs:
  exps/negative_constraint_ablation/results.json
  exps/negative_constraint_ablation/summary.csv
"""
from __future__ import annotations

import csv
import json
import os
import random
import sys
from statistics import mean

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from content_enhancement.constraint_optimizer import MultiScaleConstraintOptimizer


SEED = 20260916
N_CASES_PER_DOMAIN = 5
DOMAINS = {
    "Government": ["管理", "负责", "办理", "监督"],
    "Finance": ["监管", "处罚", "涉及", "执行"],
    "Environment": ["监测", "治理", "排放", "负责"],
}
VARIANTS = {
    "Full constraints": (True, True),
    "No density ceiling": (False, True),
    "No action cost": (True, False),
    "No negative constraints": (False, False),
}


def recommendation(head: str, relation: str, tail: str, kind: str) -> dict:
    return {
        "type": "add",
        "category": "entity completion",
        "confidence": 0.9,
        "proposal_kind": kind,
        "implementation": {"triple": {"head": head, "relation": relation, "tail": tail}},
    }


def make_case(domain: str, relations: list[str], case_id: int) -> tuple[list, list, list]:
    rng = random.Random(SEED + case_id + 1000 * list(DOMAINS).index(domain))
    names = [f"{domain[:3]}_{case_id}_n{i}" for i in range(5)]
    entities = [{"name": name} for name in names]
    triples = [
        {"head": names[i], "relation": relations[i % len(relations)], "tail": names[i + 1]}
        for i in range(2)
    ]
    # The first two proposals connect the isolated nodes and improve S_iso.
    recs = [
        recommendation(names[2], relations[1], names[3], "useful"),
        recommendation(names[3], relations[2], names[4], "useful"),
    ]
    existing = {(t["head"], t["tail"]) for t in triples}
    existing.update({(names[2], names[3]), (names[3], names[4])})
    pairs = [(h, t) for h in names for t in names if h != t and (h, t) not in existing]
    rng.shuffle(pairs)
    for idx, (head, tail) in enumerate(pairs):
        # Unique relation labels keep these proposals structurally valid and non-duplicate;
        # their only effect is unnecessary graph densification.
        recs.append(recommendation(head, f"{relations[idx % len(relations)]}_{idx}", tail, "zero_gain"))
    return entities, triples, recs


def run() -> dict:
    rows = []
    details = []
    for variant, (use_ceiling, use_cost) in VARIANTS.items():
        for domain, relations in DOMAINS.items():
            for case_id in range(N_CASES_PER_DOMAIN):
                entities, triples, recs = make_case(domain, relations, case_id)
                opt = MultiScaleConstraintOptimizer(
                    tau_repair=0.4,
                    tau_dup=0.92,
                    beta=0.35,
                    eta=0.05,
                    enforce_upper_bounds=use_ceiling,
                    enforce_action_cost=use_cost,
                )
                enhanced, _, audit = opt.optimize_and_apply(entities, triples, recs, original_text="")
                accepted = [d for d in audit["decisions"] if d["accepted"]]
                useful = sum(d["accepted"] for d in audit["decisions"][:2])
                zero_gain = sum(d["accepted"] and abs(d["delta_q"]) < 1e-12 for d in audit["decisions"][2:])
                initial = audit["initial_profile"]
                final = audit["final_profile"]
                details.append({
                    "variant": variant,
                    "domain": domain,
                    "case_id": case_id,
                    "use_density_ceiling": use_ceiling,
                    "use_action_cost": use_cost,
                    "accepted_actions": len(accepted),
                    "accepted_useful": useful,
                    "accepted_zero_gain": zero_gain,
                    "initial_Q": initial["q_score"],
                    "final_Q": final["q_score"],
                    "initial_density": initial["density"],
                    "final_density": final["density"],
                    "final_edges": len(enhanced),
                })

    for variant in VARIANTS:
        sample = [d for d in details if d["variant"] == variant]
        rows.append({
            "variant": variant,
            "cases": len(sample),
            "useful_accept_rate": mean(d["accepted_useful"] / 2 for d in sample),
            "zero_gain_actions_accepted": sum(d["accepted_zero_gain"] for d in sample),
            "zero_gain_per_case": mean(d["accepted_zero_gain"] for d in sample),
            "final_density": mean(d["final_density"] for d in sample),
            "Q_gain": mean(d["final_Q"] - d["initial_Q"] for d in sample),
        })

    os.makedirs(os.path.join(HERE, "negative_constraint_ablation"), exist_ok=True)
    out_dir = os.path.join(HERE, "negative_constraint_ablation")
    payload = {
        "seed": SEED,
        "cases_per_domain": N_CASES_PER_DOMAIN,
        "protocol": "two useful connectivity repairs followed by zero-gain completion proposals",
        "summary": rows,
        "cases": details,
    }
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "summary.csv"), "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return payload


if __name__ == "__main__":
    result = run()
    for row in result["summary"]:
        print(row)
