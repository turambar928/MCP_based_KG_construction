#!/usr/bin/env python3
"""Create a reproducible audit table from unresolved full-system defects."""

from __future__ import annotations

import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
CATEGORY = {
    "missing_triple": "source-field recovery",
    "duplicate_triple": "entity-scale deduplication",
    "invalid_relation": "schema relation repair",
    "reversed_edge": "edge-direction repair",
    "hierarchy_conflict": "organizational grounding",
    "wrong_value": "contextual value grounding",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    cases = {c["case_id"]: c for c in read_jsonl(HERE / "benchmark.jsonl") if c["split"] == "test"}
    predictions = {p["case_id"]: p for p in read_jsonl(HERE / "predictions_ours.jsonl")}
    metrics = list(csv.DictReader((HERE / "per_defect_metrics.csv").open(encoding="utf-8")))
    failed = [row for row in metrics if row["method"] == "ours" and row["success"] == "0"]
    audit = []
    for row in failed:
        case = cases[row["case_id"]]
        defect = next(d for d in case["defects"] if d["defect_id"] == row["defect_id"])
        prediction = predictions[row["case_id"]]
        audit.append({
            "case_id": row["case_id"], "domain": row["domain"], "defect_id": row["defect_id"],
            "defect_type": row["defect_type"], "failure_category": CATEGORY[row["defect_type"]],
            "gold_triple": json.dumps(defect["gold_triple"], ensure_ascii=False),
            "corrupted_triple": json.dumps(defect.get("corrupted_triple"), ensure_ascii=False),
            "system_output": json.dumps(prediction.get("triples", []), ensure_ascii=False),
            "status": prediction.get("status", "unknown"),
        })
    audit.sort(key=lambda row: (row["domain"], row["defect_type"], row["defect_id"]))
    rng = random.Random(42)
    sampled = list(audit)
    rng.shuffle(sampled)
    sampled = sampled[:150]
    write_csv(HERE / "failure_audit_all.csv", audit)
    write_csv(HERE / "failure_audit_sample.csv", sampled)
    summary = {
        "seed": 42, "n_unresolved": len(audit), "n_sampled": len(sampled),
        "unresolved_by_type": dict(sorted(Counter(row["defect_type"] for row in audit).items())),
        "unresolved_by_domain": dict(sorted(Counter(row["domain"] for row in audit).items())),
        "sampling": "fixed-seed sample without replacement from all unresolved held-out defects",
    }
    (HERE / "failure_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
