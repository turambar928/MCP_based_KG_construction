#!/usr/bin/env python3
"""Compute defect-level repair, preservation, quality, cost, and paired statistics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scipy.stats import binomtest


HERE = Path(__file__).resolve().parent
METHODS = ["no_repair", "rule_only", "shacl", "direct_llm", "react_agent", "ours"]
METRICS = [
    "repair_precision", "repair_recall", "defect_repair_rate", "clean_fact_preservation",
    "overrepair_rate", "triple_precision", "triple_recall", "triple_f1", "exact_match",
    "q_score", "calls", "latency_sec",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def key(triple: dict[str, Any]) -> tuple[str, str, str]:
    return str(triple.get("head", "")), str(triple.get("relation", "")), str(triple.get("tail", ""))


def counter(triples: list[dict[str, Any]]) -> Counter:
    return Counter(key(triple) for triple in triples)


def intersection_size(a: Counter, b: Counter) -> int:
    return sum((a & b).values())


def defect_success(defect: dict[str, Any], clean: Counter, dirty: Counter, output: Counter) -> bool:
    gold = key(defect["gold_triple"])
    kind = defect["defect_type"]
    gold_restored = output[gold] >= clean[gold]
    if kind == "duplicate_triple":
        return output[gold] == clean[gold]
    corrupt_value = defect.get("corrupted_triple")
    if kind == "missing_triple" or not corrupt_value:
        return gold_restored
    corrupt = key(corrupt_value)
    corrupt_removed = output[corrupt] <= clean[corrupt]
    return gold_restored and corrupt_removed


def case_metrics(case: dict[str, Any], prediction: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bool]]:
    clean = counter(case["clean_triples"])
    dirty = counter(case["corrupted_triples"])
    output = counter(prediction.get("triples", []))
    required_add = clean - dirty
    required_remove = dirty - clean
    actual_add = output - dirty
    actual_remove = dirty - output
    good_add = intersection_size(actual_add, required_add)
    good_remove = intersection_size(actual_remove, required_remove)
    good_edits = good_add + good_remove
    required_edits = sum(required_add.values()) + sum(required_remove.values())
    actual_edits = sum(actual_add.values()) + sum(actual_remove.values())
    harmful_edits = max(0, actual_edits - good_edits)

    correct = intersection_size(output, clean)
    out_n, clean_n = sum(output.values()), sum(clean.values())
    triple_precision = correct / out_n if out_n else 0.0
    triple_recall = correct / clean_n if clean_n else 0.0
    triple_f1 = (2 * triple_precision * triple_recall / (triple_precision + triple_recall)
                 if triple_precision + triple_recall else 0.0)

    originally_clean = clean & dirty
    preserved = intersection_size(output, originally_clean)
    preservation = preserved / sum(originally_clean.values()) if originally_clean else 1.0
    allowed = set(case["allowed_relations"])
    required_head = case["clean_triples"][0]["head"]
    unique = len(output) / out_n if out_n else 0.0
    validity = (sum(n for (h, r, _), n in output.items() if h == required_head and r in allowed) / out_n
                if out_n else 0.0)
    grounded = (sum(n for (_, _, t), n in output.items() if t in case["evidence_text"]) / out_n
                if out_n else 0.0)
    q_score = 100.0 * (triple_recall + unique + validity + grounded) / 4.0

    defect_outcomes = {
        defect["defect_id"]: defect_success(defect, clean, dirty, output)
        for defect in case["defects"]
    }
    row = {
        "case_id": case["case_id"], "domain": case["domain"], "method": prediction["method"],
        "status": prediction.get("status", "unknown"),
        "n_required_edits": required_edits, "n_actual_edits": actual_edits,
        "n_good_edits": good_edits, "n_harmful_edits": harmful_edits,
        "repair_precision": good_edits / actual_edits if actual_edits else 0.0,
        "repair_recall": good_edits / required_edits if required_edits else 1.0,
        "defect_repair_rate": sum(defect_outcomes.values()) / len(defect_outcomes),
        "clean_fact_preservation": preservation,
        "overrepair_rate": harmful_edits / actual_edits if actual_edits else 0.0,
        "triple_precision": triple_precision, "triple_recall": triple_recall, "triple_f1": triple_f1,
        "exact_match": float(output == clean), "q_score": q_score,
        "calls": float(prediction.get("calls", 0)), "latency_sec": float(prediction.get("latency_sec", 0)),
    }
    return row, defect_outcomes


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def bootstrap_ci(values: list[float], seed: int = 42, repeats: int = 5000) -> tuple[float, float]:
    if not values:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    estimates = sorted(mean([values[rng.randrange(len(values))] for _ in values]) for _ in range(repeats))
    return estimates[int(0.025 * repeats)], estimates[min(repeats - 1, int(0.975 * repeats))]


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["method"], row["domain"])].append(row)
        groups[(row["method"], "ALL")].append(row)
    out = []
    for (method, domain), items in sorted(groups.items()):
        record = {"method": method, "domain": domain, "n_cases": len(items),
                  "n_ok": sum(item["status"] == "ok" for item in items)}
        for metric in METRICS:
            values = [float(item[metric]) for item in items]
            avg = mean(values)
            lo, hi = bootstrap_ci(values)
            record[metric] = avg
            record[f"{metric}_ci_low"] = lo
            record[f"{metric}_ci_high"] = hi
        out.append(record)
    return out


def mcnemar(outcomes: dict[str, dict[str, bool]]) -> list[dict[str, Any]]:
    ours = outcomes["ours"]
    rows = []
    for method in METHODS:
        if method == "ours":
            continue
        common = sorted(set(ours) & set(outcomes[method]))
        ours_only = sum(ours[d] and not outcomes[method][d] for d in common)
        baseline_only = sum(outcomes[method][d] and not ours[d] for d in common)
        discordant = ours_only + baseline_only
        p = binomtest(min(ours_only, baseline_only), discordant, 0.5).pvalue if discordant else 1.0
        rows.append({"comparison": f"ours_vs_{method}", "n_defects": len(common),
                     "ours_only_success": ours_only, "baseline_only_success": baseline_only,
                     "exact_mcnemar_p": p})
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=METHODS)
    args = parser.parse_args()
    cases = {case["case_id"]: case for case in read_jsonl(HERE / "benchmark.jsonl") if case["split"] == "test"}
    rows = []
    defect_metric_rows = []
    outcomes: dict[str, dict[str, bool]] = {}
    for method in args.methods:
        path = HERE / f"predictions_{method}.jsonl"
        predictions = {row["case_id"]: row for row in read_jsonl(path)}
        missing = sorted(set(cases) - set(predictions))
        if missing:
            raise RuntimeError(f"{method} is missing {len(missing)} test predictions")
        outcomes[method] = {}
        for cid, case in cases.items():
            row, defect_rows = case_metrics(case, predictions[cid])
            rows.append(row)
            outcomes[method].update(defect_rows)
            defect_type = {d["defect_id"]: d["defect_type"] for d in case["defects"]}
            for defect_id, success in defect_rows.items():
                defect_metric_rows.append({
                    "case_id": cid, "domain": case["domain"], "method": method,
                    "defect_id": defect_id, "defect_type": defect_type[defect_id],
                    "success": int(success),
                })

    summary = summarize(rows)
    paired = mcnemar(outcomes) if set(args.methods) == set(METHODS) else []
    write_csv(HERE / "per_case_metrics.csv", rows)
    write_csv(HERE / "per_defect_metrics.csv", defect_metric_rows)
    write_csv(HERE / "summary.csv", summary)
    (HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "pairwise_mcnemar.json").write_text(json.dumps(paired, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in summary:
        if row["domain"] == "ALL":
            print(row["method"], {k: round(row[k], 4) for k in
                  ["defect_repair_rate", "clean_fact_preservation", "overrepair_rate", "triple_f1", "q_score", "calls", "latency_sec"]})


if __name__ == "__main__":
    main()
