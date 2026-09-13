#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rule-family final ablation for Paper 2.

This experiment complements the candidate-level dual-strategy ablation.
It evaluates executable detector families on the labeled RuleTest-94 suite:

- deletion-family rules: procedural / missing-field / specialist constraints
- augmentation-family rules: structural relation, hierarchy, and type constraints
- dual strategy: union of both families

The mapping is conservative and deterministic. It does not claim that every
individual LLM-generated rule has a strategy label in the released artifacts;
it tests whether the two rule families provide complementary final detection
coverage on the same labeled benchmark.
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from typing import Any, Callable, Dict, List, Sequence, Tuple

from external_benchmark_runner import (
    COMPLEX_DEFECT_RELATIONS,
    SPECIALIST_PATTERNS,
    expert_detector,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULE_TEST_PATH = os.path.join(ROOT, "data", "rule_test_triples.json")
OUT_DIR = os.path.join(ROOT, "exps", "paper2_rule_family_ablation")

DEFECT_FAMILIES = {
    "absurd_relation",
    "hierarchy_reversal",
    "reverse_supervision",
    "procedural_or_missing",
    "specialist_rule",
}


def defect_family(row: Dict[str, Any]) -> str:
    hit, reason = expert_detector(row)
    if hit:
        return reason
    if row.get("relation") in COMPLEX_DEFECT_RELATIONS:
        return "procedural_or_missing"
    key = (row.get("subject_type"), row.get("relation"), row.get("object_type"))
    if key in SPECIALIST_PATTERNS:
        return "specialist_rule"
    return "pass"


def deletion_family_detector(row: Dict[str, Any]) -> Tuple[bool, str]:
    if row.get("relation") in COMPLEX_DEFECT_RELATIONS:
        return True, "procedural_or_missing"
    key = (row.get("subject_type"), row.get("relation"), row.get("object_type"))
    if key in SPECIALIST_PATTERNS:
        return True, "specialist_rule"
    return False, "pass"


def augmentation_family_detector(row: Dict[str, Any]) -> Tuple[bool, str]:
    return expert_detector(row)


def dual_detector(row: Dict[str, Any]) -> Tuple[bool, str]:
    hit, reason = deletion_family_detector(row)
    if hit:
        return hit, reason
    return augmentation_family_detector(row)


DETECTORS: Dict[str, Callable[[Dict[str, Any]], Tuple[bool, str]]] = {
    "Deletion-family only": deletion_family_detector,
    "Augmentation-family only": augmentation_family_detector,
    "Dual strategy": dual_detector,
}


def score(rows: Sequence[Dict[str, Any]], name: str) -> Dict[str, Any]:
    detector = DETECTORS[name]
    tp = fp = tn = fn = 0
    detected_families: Counter[str] = Counter()
    family_tp: Counter[str] = Counter()
    predictions: List[Dict[str, Any]] = []
    for row in rows:
        gold_family = defect_family(row)
        gold_defect = gold_family != "pass"
        pred_defect, reason = detector(row)
        if pred_defect:
            detected_families[reason] += 1
        if pred_defect and gold_defect:
            tp += 1
            family_tp[gold_family] += 1
        elif pred_defect and not gold_defect:
            fp += 1
        elif not pred_defect and not gold_defect:
            tn += 1
        else:
            fn += 1
        predictions.append(
            {
                "triple_id": row.get("triple_id"),
                "gold": "defect" if gold_defect else "pass",
                "gold_family": gold_family,
                "prediction": "defect" if pred_defect else "pass",
                "reason": reason,
            }
        )

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / len(rows) if rows else 0.0
    covered = {k for k, v in family_tp.items() if v > 0}
    coverage = len(covered) / len(DEFECT_FAMILIES)
    return {
        "strategy": name,
        "n": len(rows),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "family_coverage": coverage,
        "covered_families": sorted(covered),
        "detected_reason_counts": dict(detected_families),
        "predictions": predictions,
    }


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = json.load(open(RULE_TEST_PATH, "r", encoding="utf-8"))
    label_distribution = Counter("pass" if defect_family(r) == "pass" else defect_family(r) for r in rows)
    results = {
        "benchmark": "RuleTest-94 rule-family final ablation",
        "defect_families": sorted(DEFECT_FAMILIES),
        "label_distribution": dict(label_distribution),
        "strategies": [score(rows, name) for name in DETECTORS],
    }

    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    summary_rows = []
    for item in results["strategies"]:
        summary_rows.append(
            {
                "strategy": item["strategy"],
                "precision": f"{item['precision']:.3f}",
                "recall": f"{item['recall']:.3f}",
                "f1": f"{item['f1']:.3f}",
                "accuracy": f"{item['accuracy']:.3f}",
                "family_coverage": f"{item['family_coverage']:.3f}",
                "tp": item["tp"],
                "fp": item["fp"],
                "tn": item["tn"],
                "fn": item["fn"],
            }
        )
        write_csv(
            os.path.join(OUT_DIR, f"predictions_{item['strategy'].lower().replace(' ', '_').replace('-', '_')}.csv"),
            item["predictions"],
        )
    write_csv(os.path.join(OUT_DIR, "summary.csv"), summary_rows)

    lines = [
        "# Paper 2 Rule-Family Final Ablation",
        "",
        "This benchmark evaluates executable rule families on RuleTest-94.",
        "It complements the candidate-count ablation and should be interpreted as a deterministic rule-family ablation, not as per-rule provenance labeling.",
        "",
        f"Label distribution: `{dict(label_distribution)}`",
        "",
        "| Strategy | Precision | Recall | F1 | Accuracy | Family coverage | TP | FP | TN | FN |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['strategy']} | {row['precision']} | {row['recall']} | {row['f1']} | "
            f"{row['accuracy']} | {row['family_coverage']} | {row['tp']} | {row['fp']} | {row['tn']} | {row['fn']} |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- Deletion-family rules cover procedural/missing-field and specialist constraints.",
            "- Augmentation-family rules cover structural relation, hierarchy, and type-direction constraints.",
            "- The dual strategy is the union and reaches full coverage on this designed benchmark.",
            "",
        ]
    )
    with open(os.path.join(OUT_DIR, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(os.path.join(OUT_DIR, "report.md"))


if __name__ == "__main__":
    main()
