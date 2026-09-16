#!/usr/bin/env python3
"""Build the paired, source-grounded Paper 1 KG repair benchmark.

The benchmark is derived from the three clean administrative corpora.  Each
document is mapped to a small field-level KG, split by document identity, and
then corrupted with two deterministic graph defects.  Every mutation is
recorded in a machine-readable manifest so repair quality can be measured
against the clean graph without relying on the paper's aggregate Q score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SEED = 42
FIELDS = ["服务事项", "权力类型", "行驶主体", "承办机构", "实施依据", "监管电话", "责任事项"]
SOURCES = {
    "government": ROOT / "exps" / "政务.jsonl",
    "finance": ROOT / "exps" / "金融.jsonl",
    "environment": ROOT / "exps" / "环境.jsonl",
}
DOMAIN_WRONG_VALUES = {
    "government": "某无管辖权个人工作室",
    "finance": "某无资质体育组织",
    "environment": "某无关商业机构",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def clean_text(value: Any, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def case_id(domain: str, row_index: int, row: dict[str, Any]) -> str:
    uid = str(row.get("统一发布平台unid", ""))
    digest = hashlib.sha1(f"{domain}|{row_index}|{uid}".encode()).hexdigest()[:12]
    return f"{domain}-{digest}"


def record_to_graph(domain: str, cid: str, row: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    service = clean_text(row.get("服务事项"), 100) or cid
    head = f"Document:{cid}:{service}"
    triples = []
    evidence_parts = []
    for field in FIELDS:
        value = clean_text(row.get(field))
        if not value:
            continue
        triples.append({"head": head, "relation": field, "tail": value})
        evidence_parts.append(f"{field}：{value}")
    evidence = "。".join(evidence_parts)
    return evidence, triples


def _rng_for(cid: str, seed: int) -> random.Random:
    mixed = int(hashlib.sha1(f"{seed}|{cid}".encode()).hexdigest()[:16], 16)
    return random.Random(mixed)


def corrupt_graph(domain: str, cid: str, clean: list[dict[str, str]], seed: int) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    rng = _rng_for(cid, seed)
    working = [{**triple, "_source_index": i} for i, triple in enumerate(clean)]
    available = list(range(len(clean)))
    rng.shuffle(available)
    operators = ["missing_triple", "duplicate_triple", "invalid_relation", "reversed_edge", "wrong_value"]
    if any(t["relation"] in {"行驶主体", "承办机构"} for t in clean):
        operators.append("hierarchy_conflict")
    rng.shuffle(operators)

    defects: list[dict[str, Any]] = []
    used_sources: set[int] = set()
    for operator in operators:
        candidates = [i for i in available if i not in used_sources]
        if operator == "hierarchy_conflict":
            candidates = [i for i in candidates if clean[i]["relation"] in {"行驶主体", "承办机构"}]
        if not candidates:
            continue
        source_index = candidates[0]
        used_sources.add(source_index)
        gold = dict(clean[source_index])
        positions = [j for j, triple in enumerate(working) if triple.get("_source_index") == source_index]
        if not positions:
            continue
        pos = positions[0]
        before = {k: v for k, v in working[pos].items() if not k.startswith("_")}

        if operator == "missing_triple":
            working.pop(pos)
            corrupt = None
        elif operator == "duplicate_triple":
            working.insert(pos + 1, dict(working[pos]))
            corrupt = before
        elif operator == "invalid_relation":
            working[pos]["relation"] = "UNKNOWN_REL"
            corrupt = {k: v for k, v in working[pos].items() if not k.startswith("_")}
        elif operator == "reversed_edge":
            working[pos]["head"], working[pos]["tail"] = working[pos]["tail"], working[pos]["head"]
            corrupt = {k: v for k, v in working[pos].items() if not k.startswith("_")}
        elif operator == "hierarchy_conflict":
            working[pos]["tail"] = DOMAIN_WRONG_VALUES[domain]
            corrupt = {k: v for k, v in working[pos].items() if not k.startswith("_")}
        else:
            working[pos]["tail"] = f"错误值-{domain}-{source_index}"
            corrupt = {k: v for k, v in working[pos].items() if not k.startswith("_")}

        defects.append({
            "document_id": cid,
            "defect_id": f"{cid}::{len(defects) + 1}",
            "defect_type": operator,
            "source_triple_index": source_index,
            "gold_triple": gold,
            "corrupted_triple": corrupt,
            "seed": seed,
        })
        if len(defects) == 2:
            break

    if len(defects) != 2:
        raise RuntimeError(f"Unable to inject two defects into {cid}")
    corrupted = [{k: v for k, v in triple.items() if not k.startswith("_")} for triple in working]
    return corrupted, defects


def select_and_split(rows: list[dict[str, Any]], domain: str, per_domain: int, seed: int):
    indexed = list(enumerate(rows))
    rng = random.Random(f"{seed}:{domain}")
    rng.shuffle(indexed)
    selected = indexed[: min(per_domain, len(indexed))]
    n = len(selected)
    train_end, val_end = int(0.70 * n), int(0.85 * n)
    for rank, (row_index, row) in enumerate(selected):
        split = "train" if rank < train_end else "validation" if rank < val_end else "test"
        yield split, row_index, row


def build(per_domain: int = 500, seed: int = SEED) -> dict[str, Any]:
    HERE.mkdir(parents=True, exist_ok=True)
    cases = []
    all_defects = []
    for domain, path in SOURCES.items():
        rows = load_jsonl(path)
        for split, row_index, row in select_and_split(rows, domain, per_domain, seed):
            cid = case_id(domain, row_index, row)
            evidence, clean = record_to_graph(domain, cid, row)
            if len(clean) < 3:
                continue
            corrupted, defects = corrupt_graph(domain, cid, clean, seed)
            cases.append({
                "case_id": cid,
                "domain": domain,
                "split": split,
                "source_row_index": row_index,
                "source_uid": str(row.get("统一发布平台unid", "")),
                "evidence_text": evidence,
                "allowed_relations": FIELDS,
                "clean_triples": clean,
                "corrupted_triples": corrupted,
                "defects": defects,
            })
            all_defects.extend(defects)

    cases.sort(key=lambda row: (row["domain"], row["split"], row["case_id"]))
    with (HERE / "benchmark.jsonl").open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")
    with (HERE / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for defect in all_defects:
            handle.write(json.dumps(defect, ensure_ascii=False) + "\n")

    summary = {
        "seed": seed,
        "requested_per_domain": per_domain,
        "n_cases": len(cases),
        "n_defects": len(all_defects),
        "cases_by_domain_split": dict(sorted(Counter(f"{c['domain']}:{c['split']}" for c in cases).items())),
        "defects_by_type": dict(sorted(Counter(d["defect_type"] for d in all_defects).items())),
        "protocol": "document-group split before deterministic graph corruption; two actual defects per case",
    }
    (HERE / "split_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-domain", type=int, default=500)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    print(json.dumps(build(args.per_domain, args.seed), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
