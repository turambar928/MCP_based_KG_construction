#!/usr/bin/env python3
"""Measure document-batch scaling and incremental profile updates for Paper 1."""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exps.decision_network.build_from_repair_benchmark import graph_features


HERE = Path(__file__).resolve().parent
BENCHMARK = ROOT / "exps" / "paper1_repair_benchmark" / "benchmark.jsonl"
TARGETS = [1_000, 5_000, 10_000, 50_000]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def clone_case(case: dict[str, Any], copy_index: int, remaining: int) -> dict[str, Any]:
    triples = case["clean_triples"][:remaining]
    old_head = case["clean_triples"][0]["head"]
    new_head = f"Batch{copy_index}:{old_head}"
    cloned = [{**triple, "head": new_head} for triple in triples]
    return {
        **case,
        "case_id": f"batch-{copy_index}-{case['case_id']}",
        "clean_triples": cloned,
        "corrupted_triples": cloned,
        "allowed_relations": [triple["relation"] for triple in cloned],
    }


def build_batch(pool: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    batch = []
    edges = 0
    index = 0
    while edges < target:
        source = pool[index % len(pool)]
        remaining = target - edges
        cloned = clone_case(source, index, remaining)
        batch.append(cloned)
        edges += len(cloned["clean_triples"])
        index += 1
    assert edges == target
    return batch


def full_profile(batch: list[dict[str, Any]]) -> tuple[float, float]:
    total_quality = 0.0
    total_violations = 0.0
    for case in batch:
        profile = graph_features(case, case["corrupted_triples"])
        total_quality += profile["S_iso"] + profile["S_red"] + profile["S_log"] + profile["S_sem"]
        total_violations += profile["n_viol_feat"]
    return total_quality, total_violations


def incremental_update(case: dict[str, Any]) -> dict[str, float]:
    changed = dict(case)
    changed["corrupted_triples"] = case["corrupted_triples"] + [case["corrupted_triples"][0]]
    return graph_features(changed, changed["corrupted_triples"])


def time_call(fn, repeats: int) -> list[float]:
    values = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        values.append(time.perf_counter() - start)
    return values


def main() -> None:
    pool = read_jsonl(BENCHMARK)
    rows = []
    for target in TARGETS:
        tracemalloc.start()
        batch = build_batch(pool, target)
        _, graph_state_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        full_profile(batch)  # warm-up
        full_times = time_call(lambda: full_profile(batch), 7)
        changed = batch[len(batch) // 2]
        incremental_update(changed)
        incremental_times = time_call(lambda: incremental_update(changed), 200)
        tracemalloc.start()
        full_profile(batch)
        _, profile_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        full_median = statistics.median(full_times)
        incremental_median = statistics.median(incremental_times)
        rows.append({
            "triples": target,
            "documents": len(batch),
            "full_profile_median_s": full_median,
            "full_profile_ms_per_triple": full_median / target * 1000,
            "incremental_one_document_median_s": incremental_median,
            "incremental_speedup": full_median / incremental_median,
            "graph_state_peak_mb": graph_state_peak / (1024 * 1024),
            "profile_working_peak_mb": profile_peak / (1024 * 1024),
            "api_calls": 0,
        })
        print(rows[-1], flush=True)
    with (HERE / "scalability_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (HERE / "scalability_summary.json").write_text(
        json.dumps({"seed": 42, "repeats_full": 7, "repeats_incremental": 200, "rows": rows}, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
