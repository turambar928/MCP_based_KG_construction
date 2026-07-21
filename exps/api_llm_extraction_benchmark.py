#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API-backed end-to-end LLM extraction benchmark.

This benchmark complements `external_benchmark_runner.py`.

It evaluates the raw-text -> LLM triples -> KG quality-control path on a small
TNEWS/CLUE sample. The TNEWS category is used as a silver label for category
prediction, and the dataset keywords are used as weak silver entities. These
are not human-annotated triple gold labels, so the report separates extraction
coverage from deterministic KG quality.
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
from typing import Any, Dict, List, Sequence, Tuple

from openai import OpenAI


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TNEWS_PATH = os.path.join(ROOT, "data", "train.json")
API_PATH = os.path.join(ROOT, "apis")
OUT_DIR = os.path.join(ROOT, "exps", "api_llm_extraction_benchmark")

RNG_SEED = 20260716
DEFAULT_DOCS = 45
DEFAULT_MODEL = "Qwen3.6-35B-A3B-no-thinking"
RELATIONS = {
    "HAS_CATEGORY",
    "MENTIONS",
    "RELATED_TO",
    "LOCATED_IN",
    "ORG_RELATED",
    "EVENT_RELATED",
    "PRODUCES",
    "PARTICIPATES_IN",
}
LABELS = [
    "news_story",
    "news_culture",
    "news_entertainment",
    "news_sports",
    "news_finance",
    "news_house",
    "news_car",
    "news_edu",
    "news_tech",
    "news_military",
    "news_travel",
    "news_world",
    "stock",
    "news_agriculture",
    "news_game",
]


@dataclass
class BenchConfig:
    api_key: str
    base_url: str
    model: str
    n_docs: int


def load_api_config() -> Tuple[str, str]:
    text = open(API_PATH, "r", encoding="utf-8").read()
    key_match = re.search(r"sk-[A-Za-z0-9]+", text)
    base_match = re.search(r"https?://[^\s]+", text)
    if not key_match or not base_match:
        raise RuntimeError("Cannot parse API key/base_url from apis")
    base_url = base_match.group(0).rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    return key_match.group(0), base_url


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def balanced_sample(rows: Sequence[Dict[str, Any]], n_docs: int, seed: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[row.get("label_desc", "unknown")].append(row)
    per_label = max(1, n_docs // max(1, len(buckets)))
    sampled: List[Dict[str, Any]] = []
    for _, bucket in sorted(buckets.items()):
        rng.shuffle(bucket)
        sampled.extend(bucket[:per_label])
    if len(sampled) < n_docs:
        rest = [r for r in rows if r not in sampled]
        rng.shuffle(rest)
        sampled.extend(rest[: n_docs - len(sampled)])
    sampled = sampled[:n_docs]
    rng.shuffle(sampled)
    return sampled


def call_llm(client: OpenAI, cfg: BenchConfig, sentence: str) -> str:
    system = (
        "You extract compact knowledge graph triples from Chinese news titles. "
        "Return strict JSON only. Do not add explanations."
    )
    user = f"""
Input title:
{sentence}

Allowed categories:
{", ".join(LABELS)}

Allowed relation types:
{", ".join(sorted(RELATIONS))}

Return this JSON schema exactly:
{{
  "category": one category from the allowed categories,
  "triples": [
    {{"subject": "...", "relation": "...", "object": "..."}}
  ]
}}

Rules:
- Infer the best category from the title.
- Include exactly one category triple: subject should be the title's main topic or "DOCUMENT", relation must be "HAS_CATEGORY", object must be the predicted category.
- Add 1 to 4 factual entity/event triples if the title contains enough information.
- Use only the allowed relation types.
- Keep subjects and objects short.
"""
    response = client.chat.completions.create(
        model=cfg.model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
        max_tokens=450,
    )
    return response.choices[0].message.content or ""


def parse_json_object(text: str) -> Tuple[Dict[str, Any] | None, str]:
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"json_error:{exc.msg}"
    if not isinstance(obj, dict):
        return None, "not_object"
    return obj, "ok"


def normalize_relation(value: Any) -> str:
    rel = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")
    aliases = {
        "CATEGORY": "HAS_CATEGORY",
        "MENTION": "MENTIONS",
        "MENTIONS_ENTITY": "MENTIONS",
        "RELATED": "RELATED_TO",
        "LOCATION": "LOCATED_IN",
    }
    return aliases.get(rel, rel)


def normalize_triples(obj: Dict[str, Any] | None) -> List[Dict[str, str]]:
    if not obj:
        return []
    triples = obj.get("triples", [])
    if not isinstance(triples, list):
        return []
    out: List[Dict[str, str]] = []
    for item in triples:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "subject": str(item.get("subject", "")).strip(),
                "relation": normalize_relation(item.get("relation", "")),
                "object": str(item.get("object", "")).strip(),
            }
        )
    category = str(obj.get("category", "")).strip()
    has_category = any(t["relation"] == "HAS_CATEGORY" for t in out)
    if category and not has_category:
        out.insert(0, {"subject": "DOCUMENT", "relation": "HAS_CATEGORY", "object": category})
    return out


def repair_triples(triples: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    repaired: List[Dict[str, str]] = []
    seen = set()
    for triple in triples:
        subj = triple["subject"].strip()
        rel = normalize_relation(triple["relation"])
        obj = triple["object"].strip()
        if not subj or not rel or not obj:
            continue
        if rel not in RELATIONS:
            continue
        if subj == obj:
            continue
        if rel == "HAS_CATEGORY" and obj not in LABELS:
            continue
        key = (subj, rel, obj)
        if key in seen:
            continue
        seen.add(key)
        repaired.append({"subject": subj, "relation": rel, "object": obj})
    return repaired


def bind_document_subject(triples: Sequence[Dict[str, str]], doc_id: int) -> List[Dict[str, str]]:
    """Make generic document category triples instance-specific.

    LLMs often emit (DOCUMENT, HAS_CATEGORY, label). That is reasonable per
    document, but exact duplicate metrics operate at KG level, so the generic
    subject would make all documents in the same category look duplicated.
    """
    out: List[Dict[str, str]] = []
    for triple in triples:
        copied = dict(triple)
        if copied.get("relation") == "HAS_CATEGORY" and copied.get("subject", "").upper() in {"DOCUMENT", "DOC", "TITLE"}:
            copied["subject"] = f"DOC_{doc_id}"
        out.append(copied)
    return out


def stable_id(text: str, prefix: str) -> str:
    return f"{prefix}_{hashlib.sha1(text.encode('utf-8')).hexdigest()[:12]}"


def kg_quality(triples_by_doc: Sequence[Sequence[Dict[str, str]]]) -> Dict[str, float]:
    nodes = set()
    rel_keys = []
    invalid = empty = self_loop = invalid_category = 0
    for triples in triples_by_doc:
        for triple in triples:
            s = triple.get("subject", "").strip()
            r = normalize_relation(triple.get("relation", ""))
            o = triple.get("object", "").strip()
            if not s or not r or not o:
                empty += 1
            if r not in RELATIONS:
                invalid += 1
            if s and o and s == o:
                self_loop += 1
            if r == "HAS_CATEGORY" and o not in LABELS:
                invalid_category += 1
            if s:
                nodes.add(stable_id(s, "n"))
            if o:
                nodes.add(stable_id(o, "n"))
            rel_keys.append((s, r, o))
    total = len(rel_keys)
    dup = total - len(set(rel_keys))
    connected = set()
    for s, _, o in rel_keys:
        if s:
            connected.add(stable_id(s, "n"))
        if o:
            connected.add(stable_id(o, "n"))
    isolated_rate = 1 - (len(nodes & connected) / len(nodes)) if nodes else 0.0
    invalid_rate = (invalid + empty + self_loop + invalid_category) / total if total else 1.0
    duplicate_rate = dup / total if total else 1.0
    q_score = 100.0 * (0.35 * (1 - invalid_rate) + 0.30 * (1 - duplicate_rate) + 0.20 * (1 - isolated_rate) + 0.15)
    return {
        "nodes": float(len(nodes)),
        "relations": float(total),
        "invalid_rate": invalid_rate,
        "duplicate_rate": duplicate_rate,
        "isolated_rate": isolated_rate,
        "q_score": max(0.0, min(100.0, q_score)),
    }


def split_keywords(value: str) -> List[str]:
    out = []
    for item in re.split(r"[,，;；]", value or ""):
        item = item.strip()
        if len(item) >= 2:
            out.append(item)
    return out


def keyword_recall(rows: Sequence[Dict[str, Any]], triples_by_doc: Sequence[Sequence[Dict[str, str]]]) -> Tuple[float, int]:
    hit = total = 0
    for row, triples in zip(rows, triples_by_doc):
        text = " ".join(f"{t.get('subject', '')} {t.get('object', '')}" for t in triples)
        kws = split_keywords(row.get("keywords", ""))
        for kw in kws:
            total += 1
            if kw in text:
                hit += 1
    return (hit / total if total else 0.0), total


def category_prediction(triples: Sequence[Dict[str, str]]) -> str:
    for triple in triples:
        if triple.get("relation") == "HAS_CATEGORY":
            return triple.get("object", "")
    return ""


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(results: Dict[str, Any]) -> None:
    lines = [
        "# API LLM Extraction Benchmark Report",
        "",
        "This benchmark uses the API-backed LLM to extract triples directly from raw TNEWS/CLUE titles.",
        "TNEWS labels are used as silver category labels; provided keywords are used as weak silver entity mentions.",
        "",
        "## Setup",
        "",
        f"- Model: `{results['model']}`",
        f"- Documents: {results['documents']}",
        f"- Categories: {results['categories']}",
        f"- API calls attempted: {results['api_calls']}",
        f"- Runtime: {results['elapsed_sec']:.2f}s",
        "",
        "## Main Results",
        "",
        "| Metric | Raw LLM KG | Repaired KG |",
        "| --- | ---: | ---: |",
        f"| Parse success | {results['parse_success_rate']:.3f} | - |",
        f"| Category accuracy | {results['raw_category_accuracy']:.3f} | {results['repaired_category_accuracy']:.3f} |",
        f"| Keyword recall | {results['raw_keyword_recall']:.3f} | {results['repaired_keyword_recall']:.3f} |",
        f"| Documents with triples | {results['raw_doc_coverage']:.3f} | {results['repaired_doc_coverage']:.3f} |",
        f"| Avg triples / doc | {results['raw_triples_per_doc']:.2f} | {results['repaired_triples_per_doc']:.2f} |",
        f"| KG quality score | {results['raw_quality']['q_score']:.2f} | {results['repaired_quality']['q_score']:.2f} |",
        f"| Invalid triple rate | {results['raw_quality']['invalid_rate']:.3f} | {results['repaired_quality']['invalid_rate']:.3f} |",
        f"| Duplicate triple rate | {results['raw_quality']['duplicate_rate']:.3f} | {results['repaired_quality']['duplicate_rate']:.3f} |",
        "",
        "## Interpretation",
        "",
        "- Category accuracy evaluates whether the LLM can infer the TNEWS label from the title.",
        "- Keyword recall is a weak proxy for entity extraction coverage, not a gold triple-level recall.",
        "- The repaired KG applies deterministic quality-control rules: remove empty triples, invalid relation labels, invalid categories, self-loops, and exact duplicates.",
        "- This benchmark therefore tests the full API extraction path plus the system's post-extraction quality-control layer.",
        "",
    ]
    with open(os.path.join(OUT_DIR, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run(cfg: BenchConfig) -> Dict[str, Any]:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = balanced_sample(read_jsonl(TNEWS_PATH), cfg.n_docs, RNG_SEED)
    client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url, timeout=45, max_retries=1)

    predictions: List[Dict[str, Any]] = []
    raw_by_doc: List[List[Dict[str, str]]] = []
    repaired_by_doc: List[List[Dict[str, str]]] = []
    parse_ok = 0
    start = time.perf_counter()

    for idx, row in enumerate(rows):
        error = "ok"
        raw_text = ""
        obj = None
        try:
            raw_text = call_llm(client, cfg, row.get("sentence", ""))
            obj, error = parse_json_object(raw_text)
            if obj is not None:
                parse_ok += 1
        except Exception as exc:  # API benchmarks should record failures, not crash.
            error = f"api_error:{type(exc).__name__}"
        raw_triples = bind_document_subject(normalize_triples(obj), idx)
        repaired_triples = repair_triples(raw_triples)
        raw_by_doc.append(raw_triples)
        repaired_by_doc.append(repaired_triples)

        predictions.append(
            {
                "doc_id": idx,
                "gold_label": row.get("label_desc", ""),
                "sentence": row.get("sentence", ""),
                "keywords": row.get("keywords", ""),
                "parse_status": error,
                "raw_category": category_prediction(raw_triples),
                "repaired_category": category_prediction(repaired_triples),
                "raw_triples": json.dumps(raw_triples, ensure_ascii=False),
                "repaired_triples": json.dumps(repaired_triples, ensure_ascii=False),
                "raw_response": raw_text,
            }
        )

    elapsed = time.perf_counter() - start
    raw_quality = kg_quality(raw_by_doc)
    repaired_quality = kg_quality(repaired_by_doc)
    raw_kw_recall, n_keywords = keyword_recall(rows, raw_by_doc)
    repaired_kw_recall, _ = keyword_recall(rows, repaired_by_doc)

    def cat_acc(key: str) -> float:
        hits = sum(1 for pred, row in zip(predictions, rows) if pred[key] == row.get("label_desc"))
        return hits / len(rows) if rows else 0.0

    results = {
        "benchmark": "API LLM end-to-end TNEWS extraction",
        "model": cfg.model,
        "documents": len(rows),
        "categories": len(Counter(r.get("label_desc", "") for r in rows)),
        "api_calls": len(rows),
        "elapsed_sec": elapsed,
        "parse_success_rate": parse_ok / len(rows) if rows else 0.0,
        "raw_category_accuracy": cat_acc("raw_category"),
        "repaired_category_accuracy": cat_acc("repaired_category"),
        "raw_keyword_recall": raw_kw_recall,
        "repaired_keyword_recall": repaired_kw_recall,
        "keyword_count": n_keywords,
        "raw_doc_coverage": sum(1 for triples in raw_by_doc if triples) / len(rows) if rows else 0.0,
        "repaired_doc_coverage": sum(1 for triples in repaired_by_doc if triples) / len(rows) if rows else 0.0,
        "raw_triples_per_doc": sum(len(t) for t in raw_by_doc) / len(rows) if rows else 0.0,
        "repaired_triples_per_doc": sum(len(t) for t in repaired_by_doc) / len(rows) if rows else 0.0,
        "raw_quality": raw_quality,
        "repaired_quality": repaired_quality,
    }

    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    write_csv(os.path.join(OUT_DIR, "predictions.csv"), predictions)
    write_report(results)
    return results


def main() -> None:
    api_key, base_url = load_api_config()
    n_docs = int(os.getenv("API_BENCH_N_DOCS", str(DEFAULT_DOCS)))
    model = os.getenv("API_BENCH_MODEL", DEFAULT_MODEL)
    cfg = BenchConfig(api_key=api_key, base_url=base_url, model=model, n_docs=n_docs)
    results = run(cfg)
    print(os.path.join(OUT_DIR, "report.md"))
    print(
        "API LLM extraction:",
        f"parse={results['parse_success_rate']:.3f}",
        f"cat_acc={results['repaired_category_accuracy']:.3f}",
        f"kw_recall={results['repaired_keyword_recall']:.3f}",
        f"Q={results['raw_quality']['q_score']:.2f}->{results['repaired_quality']['q_score']:.2f}",
    )


if __name__ == "__main__":
    main()
