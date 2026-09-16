#!/usr/bin/env python3
"""Build f_phi instances from the paired, manifest-backed repair benchmark."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


HERE = Path(__file__).resolve().parent
BENCHMARK = HERE.parent / "paper1_repair_benchmark" / "benchmark.jsonl"
SCALE = {
    "missing_triple": "entity",
    "duplicate_triple": "entity",
    "invalid_relation": "graph",
    "reversed_edge": "graph",
    "hierarchy_conflict": "graph",
    "wrong_value": "context",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def graph_features(case: dict[str, Any], triples: list[dict[str, str]]) -> dict[str, float]:
    expected_relations = {triple["relation"] for triple in case["clean_triples"]}
    allowed = set(case["allowed_relations"])
    required_head = case["clean_triples"][0]["head"]
    keys = [(t["head"], t["relation"], t["tail"]) for t in triples]
    counts = Counter(keys)
    n_e = len(keys)
    nodes = {value for triple in triples for value in (triple["head"], triple["tail"])}
    n_v = len(nodes)
    present_relations = {t["relation"] for t in triples if t["relation"] in allowed}
    n_missing = len(expected_relations - present_relations)
    n_dup = sum(count - 1 for count in counts.values() if count > 1)
    n_logconf = sum(t["head"] != required_head or t["relation"] not in allowed for t in triples)
    n_ungrounded = sum(t["tail"] not in case["evidence_text"] for t in triples)
    S_iso = 100.0 * (1.0 - n_missing / max(1, len(expected_relations)))
    S_red = 100.0 * (1.0 - n_dup / max(1, n_e))
    S_log = 100.0 * (1.0 - n_logconf / max(1, n_e))
    S_sem = 100.0 * (1.0 - n_ungrounded / max(1, n_e))
    density = n_e / max(1, n_v * (n_v - 1))
    return {
        "n_v": n_v, "n_e": n_e, "density": round(density, 6),
        "S_iso": round(S_iso, 4), "S_red": round(S_red, 4),
        "S_log": round(S_log, 4), "S_sem": round(S_sem, 4),
        "sem_observed": 1, "n_missing": n_missing, "n_dup": n_dup,
        "n_logconf": n_logconf, "n_viol_feat": n_missing + n_dup + n_logconf + n_ungrounded,
    }


def scale_targets(defects: list[dict[str, Any]]) -> tuple[str, dict[str, float]]:
    counts = Counter(SCALE[d["defect_type"]] for d in defects)
    total = sum(counts.values())
    dominant = max(("entity", "graph", "context"), key=lambda name: (counts[name], -("entity", "graph", "context").index(name)))
    return dominant, {name: counts[name] / total for name in ("entity", "graph", "context")}


def build() -> pd.DataFrame:
    rows = []
    cache = []
    for case in read_jsonl(BENCHMARK):
        for variant, triples, y_repair in (
            ("clean", case["clean_triples"], 0),
            ("dirty", case["corrupted_triples"], 1),
        ):
            features = graph_features(case, triples)
            if y_repair:
                label, target = scale_targets(case["defects"])
                defects = "|".join(d["defect_type"] for d in case["defects"])
            else:
                label, target, defects = "none", {"entity": 0.0, "graph": 0.0, "context": 0.0}, ""
            rows.append({
                "uid": case["case_id"], "domain": case["domain"], "split": case["split"],
                "variant": variant, "is_dirty": y_repair, **features, "y_repair": y_repair,
                "scale_label": label, "pi_entity": target["entity"], "pi_graph": target["graph"],
                "pi_context": target["context"], "defects": defects,
            })
            cache.append({"uid": case["case_id"], "variant": variant, "domain": case["domain"],
                          "triples": [f"{t['head']} --[{t['relation']}]-> {t['tail']}" for t in triples]})
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "dataset.csv", index=False)
    with (HERE / "triples_cache.jsonl").open("w", encoding="utf-8") as handle:
        for item in cache:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    summary = {
        "source": str(BENCHMARK.relative_to(HERE.parents[1])), "n_rows": len(df),
        "n_documents": df["uid"].nunique(), "split_rows": df["split"].value_counts().to_dict(),
        "label_rows": df["y_repair"].value_counts().sort_index().to_dict(),
    }
    (HERE / "dataset_meta.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return df


if __name__ == "__main__":
    build()
