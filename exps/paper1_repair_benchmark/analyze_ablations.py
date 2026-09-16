#!/usr/bin/env python3
"""Derive component ablations from the shared held-out repair runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from analyze_results import case_metrics, summarize
from run_benchmark import parse_triples


HERE = Path(__file__).resolve().parent


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    cases = {c["case_id"]: c for c in read_jsonl(HERE / "benchmark.jsonl") if c["split"] == "test"}
    sources = {
        "full": {r["case_id"]: r for r in read_jsonl(HERE / "predictions_ours.jsonl")},
        "no_context_reasoning": {r["case_id"]: r for r in read_jsonl(HERE / "predictions_rule_only.jsonl")},
        "no_structural_preprocessing": {r["case_id"]: r for r in read_jsonl(HERE / "predictions_direct_llm.jsonl")},
    }
    rows = []
    for name, predictions in sources.items():
        for cid, case in cases.items():
            pred = dict(predictions[cid])
            pred["method"] = name
            row, _ = case_metrics(case, pred)
            rows.append(row)

    # The full run stores the pre-gate LLM proposal.  Re-evaluating that exact
    # proposal isolates the constraint gate without another model call.
    for cid, case in cases.items():
        full = sources["full"][cid]
        raw = (full.get("raw_responses") or [""])[-1]
        triples, status = parse_triples(raw)
        pred = {**full, "method": "no_constraint_gate", "triples": triples,
                "status": status, "calls": full.get("calls", 0)}
        row, _ = case_metrics(case, pred)
        rows.append(row)

    summary = summarize(rows)
    write_csv(HERE / "ablation_per_case.csv", rows)
    write_csv(HERE / "ablation_summary.csv", summary)
    (HERE / "ablation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for row in summary:
        if row["domain"] == "ALL":
            print(row["method"], round(row["defect_repair_rate"], 4),
                  round(row["clean_fact_preservation"], 4), round(row["overrepair_rate"], 4))


if __name__ == "__main__":
    main()
