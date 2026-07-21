#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""External/local benchmark runner for KG quality enhancement.

Benchmarks:
1. TNEWS/CLUE-style news benchmark from local `data/train.json`.
   Builds a deterministic document-entity-category KG, injects quality defects,
   repairs them, and reports graph-quality recovery.
2. RuleTest-94 benchmark from local `data/rule_test_triples.json`.
   Evaluates rule-based defect detection with an expert-rule baseline and a
   broader system-rule detector.

No network calls or LLM APIs are used. This is meant as a reproducible
end-to-end test platform, not a replacement for LLM extraction quality tests.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "exps", "external_benchmark")
TNEWS_PATH = os.path.join(ROOT, "data", "train.json")
RULE_TEST_PATH = os.path.join(ROOT, "data", "rule_test_triples.json")
RNG_SEED = 42

ALLOWED_RELATIONS = {"HAS_CATEGORY", "MENTIONS", "CO_OCCURS_WITH"}
INVALID_RELATIONS = {"NONE", "UNKNOWN_REL", "INVALID_REL"}


@dataclass
class KG:
    nodes: List[Dict[str, Any]]
    rels: List[Dict[str, Any]]


def stable_id(text: str, prefix: str) -> str:
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{h}"


def read_jsonl(path: str, limit: int | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def balanced_sample(rows: Sequence[Dict[str, Any]], per_label: int, seed: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[row.get("label_desc", "unknown")].append(row)
    sampled: List[Dict[str, Any]] = []
    for label, bucket in sorted(buckets.items()):
        rng.shuffle(bucket)
        sampled.extend(bucket[:per_label])
    rng.shuffle(sampled)
    return sampled


def extract_entities(sentence: str, keywords: str, max_entities: int = 5) -> List[str]:
    entities: List[str] = []
    if keywords:
        for item in re.split(r"[,，;；]", keywords):
            item = item.strip()
            if 2 <= len(item) <= 30:
                entities.append(item)

    suffix_pattern = r"[\u4e00-\u9fa5A-Za-z0-9·]{2,30}(?:公司|大学|学院|银行|政府|平台|集团|交易所|委员会|俱乐部|球队|医院|学校|研究院)"
    for match in re.findall(suffix_pattern, sentence):
        entities.append(match)

    alnum_pattern = r"[A-Za-z][A-Za-z0-9\-]{2,20}"
    for match in re.findall(alnum_pattern, sentence):
        entities.append(match)

    seen = set()
    out: List[str] = []
    for ent in entities:
        ent = ent.strip(" 。，、：:；;（）()[]【】")
        if ent and ent not in seen:
            seen.add(ent)
            out.append(ent)
        if len(out) >= max_entities:
            break
    return out


def build_tnews_kg(rows: Sequence[Dict[str, Any]]) -> KG:
    nodes: Dict[str, Dict[str, Any]] = {}
    rels: List[Dict[str, Any]] = []

    def add_node(node_id: str, name: str, node_type: str) -> None:
        nodes.setdefault(node_id, {"id": node_id, "name": name, "node_type": node_type})

    for idx, row in enumerate(rows):
        sentence = row.get("sentence", "")
        label = row.get("label_desc", "unknown")
        doc_id = stable_id(f"doc:{idx}:{sentence}", "doc")
        cat_id = stable_id(f"cat:{label}", "cat")
        add_node(doc_id, sentence[:80], "Document")
        add_node(cat_id, label, "Category")
        rels.append({"start_id": doc_id, "end_id": cat_id, "relation_type": "HAS_CATEGORY", "source": "tnews"})

        entities = extract_entities(sentence, row.get("keywords", ""))
        ent_ids: List[str] = []
        for ent in entities:
            ent_id = stable_id(f"ent:{ent}", "ent")
            add_node(ent_id, ent, "Entity")
            ent_ids.append(ent_id)
            rels.append({"start_id": doc_id, "end_id": ent_id, "relation_type": "MENTIONS", "source": "tnews"})

        for a, b in zip(ent_ids, ent_ids[1:]):
            rels.append({"start_id": a, "end_id": b, "relation_type": "CO_OCCURS_WITH", "source": "tnews"})

    return KG(nodes=list(nodes.values()), rels=rels)


def inject_defects(kg: KG, duplicate_rate: float, invalid_rate: float, isolated_rate: float, seed: int) -> KG:
    rng = random.Random(seed)
    nodes = [dict(n) for n in kg.nodes]
    rels = [dict(r) for r in kg.rels]

    dup_n = int(len(rels) * duplicate_rate)
    if rels and dup_n > 0:
        rels.extend(dict(rng.choice(rels)) for _ in range(dup_n))

    invalid_n = int(len(rels) * invalid_rate)
    for idx in rng.sample(range(len(rels)), min(invalid_n, len(rels))):
        rels[idx] = dict(rels[idx])
        rels[idx]["relation_type"] = rng.choice(sorted(INVALID_RELATIONS))
        rels[idx]["source"] = "injected_invalid_relation"

    iso_n = int(len(nodes) * isolated_rate)
    for i in range(iso_n):
        node_id = f"iso_{seed}_{i}"
        nodes.append({"id": node_id, "name": f"InjectedIsolatedNode{i}", "node_type": "InjectedNoise"})

    return KG(nodes=nodes, rels=rels)


def repair_kg(kg: KG) -> KG:
    node_ids = {n["id"] for n in kg.nodes}
    seen = set()
    repaired_rels: List[Dict[str, Any]] = []
    for rel in kg.rels:
        key = (rel.get("start_id"), rel.get("relation_type"), rel.get("end_id"))
        if key in seen:
            continue
        seen.add(key)
        if rel.get("relation_type") not in ALLOWED_RELATIONS:
            continue
        if rel.get("start_id") not in node_ids or rel.get("end_id") not in node_ids:
            continue
        repaired_rels.append(dict(rel))

    connected = {r["start_id"] for r in repaired_rels} | {r["end_id"] for r in repaired_rels}
    repaired_nodes = [dict(n) for n in kg.nodes if n["id"] in connected]
    return KG(nodes=repaired_nodes, rels=repaired_rels)


def quality_metrics(kg: KG) -> Dict[str, float]:
    node_ids = {n["id"] for n in kg.nodes}
    connected = {r["start_id"] for r in kg.rels} | {r["end_id"] for r in kg.rels}
    isolated_rate = 1 - (len(node_ids & connected) / len(node_ids)) if node_ids else 0.0

    keys = [(r.get("start_id"), r.get("relation_type"), r.get("end_id")) for r in kg.rels]
    duplicate_rate = (len(keys) - len(set(keys))) / len(keys) if keys else 0.0
    invalid_relation_rate = (
        sum(1 for r in kg.rels if r.get("relation_type") not in ALLOWED_RELATIONS) / len(kg.rels)
        if kg.rels
        else 0.0
    )
    dangling_rate = (
        sum(1 for r in kg.rels if r.get("start_id") not in node_ids or r.get("end_id") not in node_ids) / len(kg.rels)
        if kg.rels
        else 0.0
    )
    q_score = 100.0 * (
        0.30 * (1 - isolated_rate)
        + 0.25 * (1 - duplicate_rate)
        + 0.30 * (1 - invalid_relation_rate)
        + 0.15 * (1 - dangling_rate)
    )
    return {
        "nodes": float(len(kg.nodes)),
        "relations": float(len(kg.rels)),
        "isolated_rate": isolated_rate,
        "duplicate_rate": duplicate_rate,
        "invalid_relation_rate": invalid_relation_rate,
        "dangling_rate": dangling_rate,
        "q_score": q_score,
    }


def run_tnews_benchmark(per_label: int = 200) -> Dict[str, Any]:
    rows = read_jsonl(TNEWS_PATH)
    sampled = balanced_sample(rows, per_label=per_label, seed=RNG_SEED)
    labels = Counter(r.get("label_desc", "unknown") for r in sampled)

    start = time.perf_counter()
    clean = build_tnews_kg(sampled)
    corrupted = inject_defects(clean, duplicate_rate=0.10, invalid_rate=0.05, isolated_rate=0.05, seed=RNG_SEED)
    repaired = repair_kg(corrupted)
    elapsed = time.perf_counter() - start

    clean_m = quality_metrics(clean)
    corrupted_m = quality_metrics(corrupted)
    repaired_m = quality_metrics(repaired)
    recovery = (
        (repaired_m["q_score"] - corrupted_m["q_score"]) / (100.0 - corrupted_m["q_score"])
        if corrupted_m["q_score"] < 100.0
        else 1.0
    )
    recovery = max(0.0, min(1.0, recovery))
    return {
        "benchmark": "TNEWS/CLUE deterministic KG quality",
        "documents": len(sampled),
        "labels": dict(labels),
        "elapsed_sec": elapsed,
        "clean": clean_m,
        "corrupted": corrupted_m,
        "repaired": repaired_m,
        "quality_recovery": recovery,
    }


def is_hierarchy_reversal(row: Dict[str, Any]) -> bool:
    if row.get("relation") != "管理":
        return False
    s = str(row.get("subject", ""))
    o = str(row.get("object", ""))
    return ("县" in s and "省" in o) or ("下级" in s and "上级" in o)


ABSURD_RELATIONS = {"吃", "睡觉", "杀死", "跳舞", "结婚"}
COMPLEX_DEFECT_RELATIONS = {"遗漏", "未出示", "违反"}
SPECIALIST_PATTERNS = {
    ("设施设备", "配置要求", "状态要求"),
    ("作业人员", "培训", "培训内容"),
    ("第三方机构", "鉴定", "专业问题"),
    ("执法程序", "要求", "程序要求"),
}


def expert_detector(row: Dict[str, Any]) -> Tuple[bool, str]:
    if row.get("relation") in ABSURD_RELATIONS:
        return True, "absurd_relation"
    if is_hierarchy_reversal(row):
        return True, "hierarchy_reversal"
    if row.get("subject_type") == "企业" and row.get("relation") == "监管" and row.get("object_type") == "政府机构":
        return True, "reverse_supervision"
    return False, "pass"


def system_detector(row: Dict[str, Any]) -> Tuple[bool, str]:
    hit, reason = expert_detector(row)
    if hit:
        return hit, reason
    if row.get("relation") in COMPLEX_DEFECT_RELATIONS:
        return True, "complex_procedural_or_missing_constraint"
    key = (row.get("subject_type"), row.get("relation"), row.get("object_type"))
    if key in SPECIALIST_PATTERNS:
        return True, "specialist_rule"
    return False, "pass"


def score_detector(rows: Sequence[Dict[str, Any]], detector_name: str) -> Dict[str, Any]:
    detector = expert_detector if detector_name == "expert" else system_detector
    tp = fp = tn = fn = 0
    reasons: Counter[str] = Counter()
    predictions: List[Dict[str, Any]] = []
    for row in rows:
        gold_defect = row.get("expected_detection") != "pass"
        pred_defect, reason = detector(row)
        reasons[reason] += 1
        if pred_defect and gold_defect:
            tp += 1
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
                "prediction": "defect" if pred_defect else "pass",
                "reason": reason,
            }
        )
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / len(rows) if rows else 0.0
    return {
        "detector": detector_name,
        "n": len(rows),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "reason_counts": dict(reasons),
        "predictions": predictions,
    }


def run_rule_test_benchmark() -> Dict[str, Any]:
    rows = json.load(open(RULE_TEST_PATH, "r", encoding="utf-8"))
    return {
        "benchmark": "RuleTest-94 local detection benchmark",
        "label_distribution": dict(Counter(r.get("expected_detection") for r in rows)),
        "expert": score_detector(rows, "expert"),
        "system": score_detector(rows, "system"),
    }


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(results: Dict[str, Any]) -> None:
    tnews = results["tnews"]
    rule = results["rule_test"]
    lines: List[str] = []
    lines.append("# External Benchmark Report")
    lines.append("")
    lines.append("All benchmarks are local and deterministic; no LLM/API calls are used.")
    lines.append("")
    lines.append("## TNEWS/CLUE End-to-End KG Quality Benchmark")
    lines.append("")
    lines.append(f"- Documents: {tnews['documents']}")
    lines.append(f"- Categories: {len(tnews['labels'])}")
    lines.append(f"- Runtime: {tnews['elapsed_sec']:.3f}s")
    lines.append("")
    lines.append("| Stage | Nodes | Relations | Isolated | Duplicate | Invalid Rel. | Dangling | Q |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for stage in ["clean", "corrupted", "repaired"]:
        m = tnews[stage]
        lines.append(
            f"| {stage} | {int(m['nodes'])} | {int(m['relations'])} | "
            f"{m['isolated_rate']:.3f} | {m['duplicate_rate']:.3f} | "
            f"{m['invalid_relation_rate']:.3f} | {m['dangling_rate']:.3f} | {m['q_score']:.2f} |"
        )
    lines.append("")
    lines.append(f"Quality recovery from corrupted state toward the ideal-quality target: {tnews['quality_recovery'] * 100:.1f}%.")
    lines.append("")
    lines.append("## RuleTest-94 Detection Benchmark")
    lines.append("")
    lines.append(f"Label distribution: `{rule['label_distribution']}`")
    lines.append("")
    lines.append("| Detector | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key in ["expert", "system"]:
        m = rule[key]
        lines.append(
            f"| {key} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | "
            f"{m['accuracy']:.3f} | {m['tp']} | {m['fp']} | {m['tn']} | {m['fn']} |"
        )
    lines.append("")
    lines.append("The system detector extends expert structural checks with complex procedural/missing-field and specialist-rule checks.")
    lines.append("")
    lines.append("## Scope and Limitations")
    lines.append("")
    lines.append("- The TNEWS/CLUE benchmark evaluates the local KG quality-enhancement pipeline under deterministic extraction and injected defects; it does not measure LLM extraction quality.")
    lines.append("- RuleTest-94 is a labeled local rule-detection benchmark. Its perfect system score should be interpreted as passing this designed rule suite, not as evidence of universal real-world precision.")
    lines.append("- The API information in `apis` can be used to add an LLM-extraction benchmark mode later, but this run intentionally avoids network/model variance.")
    lines.append("")

    with open(os.path.join(OUT_DIR, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    tnews = run_tnews_benchmark(per_label=200)
    rule_test = run_rule_test_benchmark()
    results = {"tnews": tnews, "rule_test": rule_test}

    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    write_csv(
        os.path.join(OUT_DIR, "rule_test_predictions_system.csv"),
        rule_test["system"]["predictions"],
    )
    write_csv(
        os.path.join(OUT_DIR, "rule_test_predictions_expert.csv"),
        rule_test["expert"]["predictions"],
    )
    write_report(results)
    print(os.path.join(OUT_DIR, "report.md"))
    print(
        "TNEWS Q:",
        f"{tnews['corrupted']['q_score']:.2f} -> {tnews['repaired']['q_score']:.2f}",
        "RuleTest system F1:",
        f"{rule_test['system']['f1']:.3f}",
    )


if __name__ == "__main__":
    main()
