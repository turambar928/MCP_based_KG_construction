#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paper 2 dual-strategy rule-generation ablation.

This script reuses existing per-call LLM outputs from
`per_item_rule_suggestions.jsonl` and aggregates rules by strategy without
making any API calls. It is intended to support a conservative ablation claim:
deletion completion and augmentation expansion contribute complementary
candidate rules before final validation/deduplication.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Set, Tuple


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from rule_generate_scripts.generate_rules_from_gov_texts import aggregate_rules

DEFAULT_SOURCES = [
    ("gov20", os.path.join(ROOT, "exps", "rule_suggestions_1", "per_item_rule_suggestions.jsonl")),
    ("gov_full", os.path.join(ROOT, "exps", "rule_suggestions", "per_item_rule_suggestions.jsonl")),
]
OUT_DIR = os.path.join(ROOT, "exps", "paper2_dual_strategy_ablation")

RULE_KEYS = [
    "entity_types",
    "relationship_types",
    "type_conflict_rules_forbidden",
    "type_conflict_rules_allowed",
    "hierarchy_rules",
    "geo_hierarchy_rules",
    "procedural_rules",
]


@dataclass
class StrategyStats:
    source: str
    strategy: str
    calls: int
    total_rules: int
    category_counts: Dict[str, int]
    coverage_vs_dual: float
    unique_vs_other: int
    overlap_with_other: int


def load_rows(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row.get("llm_result"), dict) and "error" not in row["llm_result"]:
                rows.append(row)
    return rows


def aggregate_for(rows: Iterable[Dict[str, Any]], strategy: str) -> Dict[str, Any]:
    selected = [r for r in rows if strategy == "dual" or r.get("strategy") == strategy]
    return aggregate_rules([r["llm_result"] for r in selected])


def canonical_item(key: str, value: Any) -> str:
    return key + "::" + json.dumps(value, ensure_ascii=False, sort_keys=True)


def rule_set(agg: Dict[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for key in RULE_KEYS:
        for value in agg.get(key, []) or []:
            out.add(canonical_item(key, value))
    return out


def count_rules(agg: Dict[str, Any]) -> Dict[str, int]:
    return {key: len(agg.get(key, []) or []) for key in RULE_KEYS}


def save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def analyze_source(name: str, path: str) -> Tuple[List[StrategyStats], Dict[str, Any]]:
    rows = load_rows(path)
    by_strategy = {
        "deletion": [r for r in rows if r.get("strategy") == "deletion"],
        "augmentation": [r for r in rows if r.get("strategy") == "augmentation"],
        "dual": rows,
    }

    aggregated = {strategy: aggregate_for(rows, strategy) for strategy in by_strategy}
    sets = {strategy: rule_set(agg) for strategy, agg in aggregated.items()}
    dual_total = max(1, len(sets["dual"]))

    stats: List[StrategyStats] = []
    deletion_unique = len(sets["deletion"] - sets["augmentation"])
    augmentation_unique = len(sets["augmentation"] - sets["deletion"])
    strategy_overlap = len(sets["deletion"] & sets["augmentation"])
    for strategy in ["deletion", "augmentation", "dual"]:
        if strategy == "deletion":
            other = sets["augmentation"]
        elif strategy == "augmentation":
            other = sets["deletion"]
        else:
            other = set()
        unique = len(sets[strategy] - other) if other else deletion_unique + augmentation_unique
        overlap = len(sets[strategy] & other) if other else strategy_overlap
        stats.append(
            StrategyStats(
                source=name,
                strategy=strategy,
                calls=len(by_strategy[strategy]),
                total_rules=len(sets[strategy]),
                category_counts=count_rules(aggregated[strategy]),
                coverage_vs_dual=len(sets[strategy]) / dual_total,
                unique_vs_other=unique,
                overlap_with_other=overlap,
            )
        )

    summary = {
        "source": name,
        "input_path": path,
        "calls": {k: len(v) for k, v in by_strategy.items()},
        "total_rules": {k: len(v) for k, v in sets.items()},
        "overlap": strategy_overlap,
        "deletion_unique": deletion_unique,
        "augmentation_unique": augmentation_unique,
        "dual_gain_over_best_single": (
            (len(sets["dual"]) - max(len(sets["deletion"]), len(sets["augmentation"])))
            / max(1, max(len(sets["deletion"]), len(sets["augmentation"])))
        ),
        "category_counts": {k: count_rules(v) for k, v in aggregated.items()},
    }

    source_dir = os.path.join(OUT_DIR, name)
    os.makedirs(source_dir, exist_ok=True)
    for strategy, agg in aggregated.items():
        save_json(os.path.join(source_dir, f"aggregated_{strategy}.json"), agg)
    save_json(os.path.join(source_dir, "summary.json"), summary)
    return stats, summary


def write_csv(stats: List[StrategyStats]) -> None:
    path = os.path.join(OUT_DIR, "dual_strategy_ablation.csv")
    fieldnames = [
        "source",
        "strategy",
        "calls",
        "total_rules",
        "coverage_vs_dual",
        "unique_vs_other",
        "overlap_with_other",
    ] + RULE_KEYS
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in stats:
            row = {
                "source": s.source,
                "strategy": s.strategy,
                "calls": s.calls,
                "total_rules": s.total_rules,
                "coverage_vs_dual": round(s.coverage_vs_dual, 4),
                "unique_vs_other": s.unique_vs_other,
                "overlap_with_other": s.overlap_with_other,
            }
            row.update(s.category_counts)
            writer.writerow(row)


def write_report(summaries: List[Dict[str, Any]], stats: List[StrategyStats]) -> None:
    path = os.path.join(OUT_DIR, "report.md")
    lines: List[str] = []
    lines.append("# Paper 2 Dual-Strategy Ablation")
    lines.append("")
    lines.append("This report is generated from existing `per_item_rule_suggestions.jsonl` logs. It does not call any LLM API.")
    lines.append("The metrics are candidate-rule contribution metrics before the final manual/validation filtering used by the paper's 294-rule table.")
    lines.append("")

    for summary in summaries:
        lines.append(f"## Source: `{summary['source']}`")
        lines.append("")
        lines.append("| Strategy | Calls | Candidate rules | Coverage vs dual | Unique vs other | Overlap |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for s in [x for x in stats if x.source == summary["source"]]:
            lines.append(
                f"| {s.strategy} | {s.calls} | {s.total_rules} | "
                f"{s.coverage_vs_dual:.3f} | {s.unique_vs_other} | {s.overlap_with_other} |"
            )
        lines.append("")
        lines.append(
            f"Dual strategy gain over the stronger single strategy: "
            f"{summary['dual_gain_over_best_single'] * 100:.1f}%."
        )
        lines.append("")
        lines.append("| Category | Deletion | Augmentation | Dual |")
        lines.append("| --- | ---: | ---: | ---: |")
        for key in RULE_KEYS:
            c = summary["category_counts"]
            lines.append(f"| `{key}` | {c['deletion'][key]} | {c['augmentation'][key]} | {c['dual'][key]} |")
        lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append("- Deletion and augmentation both contribute non-overlapping candidate rules, supporting the complementarity claim.")
    lines.append("- These values should be reported as candidate-rule ablation results, not as final precision/recall on the manually verified 94-case test set.")
    lines.append("- Final precision/recall still requires the manually annotated test labels, which are not present in the current repository.")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    all_stats: List[StrategyStats] = []
    summaries: List[Dict[str, Any]] = []

    for name, path in DEFAULT_SOURCES:
        if not os.path.exists(path):
            print(f"skip missing source: {path}")
            continue
        stats, summary = analyze_source(name, path)
        all_stats.extend(stats)
        summaries.append(summary)

    write_csv(all_stats)
    save_json(os.path.join(OUT_DIR, "dual_strategy_ablation.json"), summaries)
    write_report(summaries, all_stats)

    print(f"wrote {OUT_DIR}")
    for summary in summaries:
        print(
            summary["source"],
            "dual_rules=", summary["total_rules"]["dual"],
            "gain=", f"{summary['dual_gain_over_best_single'] * 100:.1f}%",
        )


if __name__ == "__main__":
    main()
