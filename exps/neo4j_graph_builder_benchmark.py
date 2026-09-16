#!/usr/bin/env python3
"""Compare our schema-guided extraction path with Neo4j LLM Graph Builder.

The benchmark uses the same balanced TNEWS sample, model, temperature, node
types, and relationship vocabulary for both systems.  Neo4j's public Graph
Builder uses ``LLMGraphTransformer`` as its core text-to-graph extractor; this
script invokes that component directly so the comparison is batchable and
reproducible without a Neo4j database or manual website interaction.

Run with the optional benchmark dependencies:

    NO_PROXY=api.cipsup.cn no_proxy=api.cipsup.cn \
      uv run --with langchain-neo4j==0.10.0 \
      --with langchain-openai==1.3.2 \
      python exps/neo4j_graph_builder_benchmark.py

The API key is read from the untracked local ``api`` file and is never written
to an output artifact.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from langchain_core.documents import Document
from langchain_neo4j import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
TNEWS_PATH = ROOT / "data" / "train.json"
API_PATH = ROOT / "api"
OUT_DIR = ROOT / "exps" / "neo4j_graph_builder_benchmark"

RNG_SEED = 20260716
DEFAULT_DOCS = 45
DEFAULT_WORKERS = 1
DEFAULT_MODEL = "Qwen3.8-27B-no-thinking"

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
    "news_stock",
    "news_agriculture",
    "news_game",
]
NODE_TYPES = [
    "Document",
    "Category",
    "Entity",
    "Organization",
    "Person",
    "Location",
    "Event",
    "Product",
]
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


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    model: str
    n_docs: int
    workers: int


def load_api_config() -> tuple[str, str]:
    text = API_PATH.read_text(encoding="utf-8")
    key_match = re.search(r"sk-[A-Za-z0-9_-]+", text)
    base_match = re.search(r"https?://[^\s]+", text)
    if not key_match or not base_match:
        raise RuntimeError("Cannot parse API key and base URL from local api file")
    base_url = base_match.group(0).rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    host = re.sub(r"^https?://", "", base_url).split("/", 1)[0]
    for env_name in ("NO_PROXY", "no_proxy"):
        current = os.environ.get(env_name, "")
        values = [value for value in current.split(",") if value]
        if host not in values:
            values.append(host)
        os.environ[env_name] = ",".join(values)
    return key_match.group(0), base_url


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def balanced_sample(
    rows: Sequence[dict[str, Any]], n_docs: int, seed: int
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[row.get("label_desc", "unknown")].append(row)
    per_label = max(1, n_docs // max(1, len(buckets)))
    sampled: list[dict[str, Any]] = []
    for _, bucket in sorted(buckets.items()):
        bucket = list(bucket)
        rng.shuffle(bucket)
        sampled.extend(bucket[:per_label])
    if len(sampled) < n_docs:
        sampled_ids = {id(row) for row in sampled}
        rest = [row for row in rows if id(row) not in sampled_ids]
        rng.shuffle(rest)
        sampled.extend(rest[: n_docs - len(sampled)])
    sampled = sampled[:n_docs]
    rng.shuffle(sampled)
    return sampled


def parse_json_value(text: str) -> Any | None:
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"```$", "", raw).strip()
    for opening, closing in (("{", "}"), ("[", "]")):
        start, end = raw.find(opening), raw.rfind(closing)
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def normalize_relation(value: Any) -> str:
    relation = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")
    aliases = {
        "CATEGORY": "HAS_CATEGORY",
        "HAS_CATEGORY_OF": "HAS_CATEGORY",
        "MENTION": "MENTIONS",
        "MENTIONS_ENTITY": "MENTIONS",
        "RELATED": "RELATED_TO",
        "LOCATION": "LOCATED_IN",
    }
    return aliases.get(relation, relation)


def normalize_direct_output(value: Any | None) -> list[dict[str, str]]:
    if not isinstance(value, dict):
        return []
    triples = value.get("triples", [])
    if not isinstance(triples, list):
        triples = []
    output: list[dict[str, str]] = []
    for item in triples:
        if not isinstance(item, dict):
            continue
        output.append(
            {
                "subject": str(item.get("subject", "")).strip(),
                "relation": normalize_relation(item.get("relation", "")),
                "object": str(item.get("object", "")).strip(),
            }
        )
    category = str(value.get("category", "")).strip()
    if category and not any(t["relation"] == "HAS_CATEGORY" for t in output):
        output.insert(
            0,
            {"subject": "DOCUMENT", "relation": "HAS_CATEGORY", "object": category},
        )
    return output


def bind_document_subject(
    triples: Sequence[dict[str, str]], doc_id: int
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for triple in triples:
        copied = dict(triple)
        if copied.get("relation") == "HAS_CATEGORY" and copied.get(
            "subject", ""
        ).upper() in {"DOCUMENT", "DOC", "TITLE"}:
            copied["subject"] = f"DOC_{doc_id}"
        output.append(copied)
    return output


def repair_triples(triples: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    repaired: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for triple in triples:
        subject = str(triple.get("subject", "")).strip()
        relation = normalize_relation(triple.get("relation", ""))
        obj = str(triple.get("object", "")).strip()
        if not subject or not relation or not obj:
            continue
        if relation not in RELATIONS or subject == obj:
            continue
        if relation == "HAS_CATEGORY" and obj not in LABELS:
            continue
        key = (subject, relation, obj)
        if key in seen:
            continue
        seen.add(key)
        repaired.append({"subject": subject, "relation": relation, "object": obj})
    return repaired


def make_graph_builder(cfg: Config) -> LLMGraphTransformer:
    llm = ChatOpenAI(
        model=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        temperature=0,
        max_tokens=900,
        timeout=60,
        max_retries=0,
    )
    categories = ", ".join(LABELS)
    return LLMGraphTransformer(
        llm=llm,
        allowed_nodes=NODE_TYPES,
        allowed_relationships=sorted(RELATIONS),
        node_properties=False,
        relationship_properties=False,
        ignore_tool_usage=True,
        additional_instructions=(
            "For every input create exactly one Category node whose id is the best "
            "label from this list: "
            f"{categories}. Connect the main topic to it with HAS_CATEGORY. "
            "Extract only facts supported by the text and return JSON only."
        ),
    )


def graph_builder_extract(
    transformer: LLMGraphTransformer, sentence: str
) -> list[dict[str, str]]:
    graph = transformer.convert_to_graph_documents([Document(page_content=sentence)])[0]
    return [
        {
            "subject": str(rel.source.id).strip(),
            "relation": normalize_relation(rel.type),
            "object": str(rel.target.id).strip(),
        }
        for rel in graph.relationships
    ]


def direct_extract(client: OpenAI, cfg: Config, sentence: str) -> list[dict[str, str]]:
    system = (
        "You extract compact knowledge graph triples from Chinese news titles. "
        "Return strict JSON only without explanations."
    )
    user = f"""Input title:
{sentence}

Allowed categories:
{", ".join(LABELS)}

Allowed relation types:
{", ".join(sorted(RELATIONS))}

Return this schema:
{{"category":"one allowed category","triples":[{{"subject":"...","relation":"...","object":"..."}}]}}

Include exactly one HAS_CATEGORY triple. Add one to four factual triples when
the title supports them. Use only allowed relation types and short entity names.
"""
    response = client.chat.completions.create(
        model=cfg.model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
        max_tokens=700,
    )
    return normalize_direct_output(parse_json_value(response.choices[0].message.content or ""))


def run_method(
    rows: Sequence[dict[str, Any]],
    extractor: Callable[[str], list[dict[str, str]]],
    workers: int,
    initial_outputs: Sequence[Sequence[dict[str, str]]] | None = None,
    initial_statuses: Sequence[str] | None = None,
    initial_elapsed: float = 0.0,
    checkpoint_path: Path | None = None,
    fingerprint: str = "",
) -> tuple[list[list[dict[str, str]]], list[str], float]:
    outputs = [list(items) for items in initial_outputs] if initial_outputs else [[] for _ in rows]
    statuses = list(initial_statuses) if initial_statuses else ["not_run" for _ in rows]
    start = time.perf_counter()

    def run_one(index: int) -> tuple[int, list[dict[str, str]], str]:
        last_error = "not_run"
        for attempt in range(3):
            try:
                triples = bind_document_subject(
                    extractor(rows[index].get("sentence", "")), index
                )
                return index, triples, "ok"
            except Exception as exc:
                last_error = f"{type(exc).__name__}:{str(exc)[:160]}"
                retryable = type(exc).__name__ in {"RateLimitError", "APITimeoutError"}
                if not retryable or attempt == 2:
                    break
                delay = 30 * (attempt + 1) if type(exc).__name__ == "RateLimitError" else 10
                print(
                    f"doc {index}: {type(exc).__name__}; retrying in {delay}s",
                    flush=True,
                )
                time.sleep(delay)
        return index, [], last_error

    pending = [index for index, status in enumerate(statuses) if status != "ok"]
    if len(pending) != len(rows):
        print(f"resuming {len(pending)} failed/pending documents", flush=True)
    if not pending:
        return outputs, statuses, initial_elapsed

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, index) for index in pending]
        for completed, future in enumerate(as_completed(futures), start=1):
            index, triples, status = future.result()
            outputs[index] = triples
            statuses[index] = status
            print(f"completed {completed}/{len(pending)} ({status.split(':', 1)[0]})", flush=True)
            if checkpoint_path is not None:
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                checkpoint_path.write_text(
                    json.dumps(
                        {
                            "fingerprint": fingerprint,
                            "outputs": outputs,
                            "statuses": statuses,
                            "elapsed_sec": initial_elapsed
                            + time.perf_counter()
                            - start,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
    return outputs, statuses, initial_elapsed + time.perf_counter() - start


def load_saved_method(
    rows: Sequence[dict[str, Any]], checkpoint_path: Path, fingerprint: str
) -> tuple[list[list[dict[str, str]]], list[str], float]:
    if checkpoint_path.exists():
        saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        outputs = saved.get("outputs", [])
        statuses = saved.get("statuses", [])
        if (
            saved.get("fingerprint") == fingerprint
            and len(outputs) == len(rows)
            and len(statuses) == len(rows)
        ):
            return outputs, statuses, float(saved.get("elapsed_sec", 0.0))
    return ([[] for _ in rows], ["not_run" for _ in rows], 0.0)


def experiment_fingerprint(cfg: Config, rows: Sequence[dict[str, Any]]) -> str:
    """Invalidate checkpoints whenever the effective experiment changes."""
    payload = {
        "version": 2,
        "model": cfg.model,
        "temperature": 0,
        "labels": LABELS,
        "node_types": NODE_TYPES,
        "relations": sorted(RELATIONS),
        "sentences": [row.get("sentence", "") for row in rows],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stable_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def split_keywords(value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[,，;；]", value or "")
        if len(item.strip()) >= 2
    ]


def category_prediction(triples: Sequence[dict[str, str]]) -> str:
    for triple in triples:
        if triple.get("relation") == "HAS_CATEGORY":
            return triple.get("object", "")
    return ""


def evaluate(
    rows: Sequence[dict[str, Any]],
    triples_by_doc: Sequence[Sequence[dict[str, str]]],
    statuses: Sequence[str],
    elapsed: float,
) -> dict[str, Any]:
    keyword_hits = keyword_total = category_hits = 0
    relation_keys: list[tuple[str, str, str]] = []
    nodes: set[str] = set()
    invalid = empty = self_loop = invalid_category = duplicates = 0
    for row, triples in zip(rows, triples_by_doc):
        prediction = category_prediction(triples)
        category_hits += int(prediction == row.get("label_desc"))
        triple_text = " ".join(
            f"{triple.get('subject', '')} {triple.get('object', '')}" for triple in triples
        )
        for keyword in split_keywords(row.get("keywords", "")):
            keyword_total += 1
            keyword_hits += int(keyword in triple_text)
        document_keys: list[tuple[str, str, str]] = []
        for triple in triples:
            subject = str(triple.get("subject", "")).strip()
            relation = normalize_relation(triple.get("relation", ""))
            obj = str(triple.get("object", "")).strip()
            empty += int(not subject or not relation or not obj)
            invalid += int(relation not in RELATIONS)
            self_loop += int(bool(subject and obj and subject == obj))
            invalid_category += int(relation == "HAS_CATEGORY" and obj not in LABELS)
            if subject:
                nodes.add(stable_id(subject))
            if obj:
                nodes.add(stable_id(obj))
            key = (subject, relation, obj)
            relation_keys.append(key)
            document_keys.append(key)
        duplicates += len(document_keys) - len(set(document_keys))

    total = len(relation_keys)
    invalid_count = invalid + empty + self_loop + invalid_category
    invalid_rate = invalid_count / total if total else 1.0
    duplicate_rate = duplicates / total if total else 1.0
    return {
        "parse_success": sum(status == "ok" for status in statuses) / len(rows),
        "category_hits": category_hits,
        "category_accuracy": category_hits / len(rows),
        "keyword_hits": keyword_hits,
        "keyword_recall": keyword_hits / keyword_total if keyword_total else 0.0,
        "keyword_count": keyword_total,
        "document_coverage": sum(bool(doc) for doc in triples_by_doc) / len(rows),
        "triples": total,
        "triples_per_doc": total / len(rows),
        "nodes": len(nodes),
        "invalid_rate": invalid_rate,
        "duplicate_rate": duplicate_rate,
        "elapsed_sec": elapsed,
    }


def paired_category_comparison(
    rows: Sequence[dict[str, Any]],
    neo4j: Sequence[Sequence[dict[str, str]]],
    ours: Sequence[Sequence[dict[str, str]]],
) -> dict[str, Any]:
    outcomes = Counter()
    for row, neo4j_triples, our_triples in zip(rows, neo4j, ours):
        gold = row.get("label_desc", "")
        outcomes[
            (
                category_prediction(neo4j_triples) == gold,
                category_prediction(our_triples) == gold,
            )
        ] += 1
    neo4j_only = outcomes[(True, False)]
    ours_only = outcomes[(False, True)]
    discordant = neo4j_only + ours_only
    if discordant:
        lower = min(neo4j_only, ours_only)
        tail = sum(math.comb(discordant, k) for k in range(lower + 1))
        exact_p = min(1.0, 2.0 * tail / (2**discordant))
    else:
        exact_p = 1.0
    return {
        "both_correct": outcomes[(True, True)],
        "neo4j_only_correct": neo4j_only,
        "ours_only_correct": ours_only,
        "both_wrong": outcomes[(False, False)],
        "exact_mcnemar_two_sided_p": exact_p,
    }


def write_report(results: dict[str, Any]) -> None:
    labels = [
        ("neo4j_graph_builder", "Neo4j LLM Graph Builder"),
        ("mcp_raw", "Ours (one-pass extraction)"),
        ("mcp_constrained", "Ours + constraint validation"),
    ]
    lines = [
        "# Neo4j LLM Graph Builder Comparison",
        "",
        "This benchmark compares the public Neo4j LLM Graph Builder core extractor "
        "with our extraction and validation path under the same model, schema, "
        "temperature, input sample, and concurrency.",
        "",
        "## Setup",
        "",
        f"- Model: `{results['model']}`",
        f"- Documents: {results['documents']} balanced TNEWS titles",
        f"- Categories: {results['categories']}",
        f"- Random seed: `{results['seed']}`",
        f"- Workers: {results['workers']}",
        f"- Neo4j Graph Builder commit inspected: `{results['neo4j_commit']}`",
        "- Neo4j extractor: `langchain-neo4j==0.10.0` `LLMGraphTransformer`",
        "",
        "## Results",
        "",
        "| System | Parse | Cat. acc. | Keyword recall | Doc. coverage | Triples/doc | Invalid | Duplicate | Time (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, label in labels:
        metric = results["metrics"][key]
        lines.append(
            f"| {label} | {metric['parse_success']:.3f} | "
            f"{metric['category_accuracy']:.3f} | {metric['keyword_recall']:.3f} | "
            f"{metric['document_coverage']:.3f} | {metric['triples_per_doc']:.2f} | "
            f"{metric['invalid_rate']:.3f} | {metric['duplicate_rate']:.3f} | "
            f"{metric['elapsed_sec']:.2f} |"
        )
    paired = results["paired_category"]
    lines.extend(
        [
            "",
            "## Paired category audit",
            "",
            f"- Both correct: {paired['both_correct']}",
            f"- Neo4j only correct: {paired['neo4j_only_correct']}",
            f"- Ours only correct: {paired['ours_only_correct']}",
            f"- Both wrong: {paired['both_wrong']}",
            "- Exact two-sided McNemar p-value: "
            f"{paired['exact_mcnemar_two_sided_p']:.3f}",
            "",
            "## Interpretation boundaries",
            "",
            "- TNEWS supplies category labels and weak entity keywords, not gold triples; "
            "category accuracy and keyword recall are therefore silver-label indicators.",
            "- The comparison targets Text-to-KG extraction and post-extraction structural "
            "validation. It does not measure every semantic fact against a gold graph.",
            "- The Neo4j baseline is its reproducible core extractor with a custom schema, "
            "which the public Graph Builder interface supports; no Neo4j database is needed "
            "to evaluate extracted graph documents.",
            "",
        ]
    )
    (OUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    api_key, base_url = load_api_config()
    cfg = Config(
        api_key=api_key,
        base_url=base_url,
        model=os.getenv("KG_BENCH_MODEL", DEFAULT_MODEL),
        n_docs=int(os.getenv("KG_BENCH_N_DOCS", str(DEFAULT_DOCS))),
        workers=int(os.getenv("KG_BENCH_WORKERS", str(DEFAULT_WORKERS))),
    )
    all_rows = read_jsonl(TNEWS_PATH)
    dataset_labels = {str(row.get("label_desc", "")) for row in all_rows}
    if dataset_labels != set(LABELS):
        raise RuntimeError(
            "TNEWS label vocabulary does not match the benchmark schema: "
            f"dataset={sorted(dataset_labels)}, configured={sorted(LABELS)}"
        )
    rows = balanced_sample(all_rows, cfg.n_docs, RNG_SEED)
    fingerprint = experiment_fingerprint(cfg, rows)
    transformer = make_graph_builder(cfg)
    client = OpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout=60,
        max_retries=0,
    )

    neo4j_checkpoint = OUT_DIR / "neo4j_checkpoint.json"
    mcp_checkpoint = OUT_DIR / "mcp_checkpoint.json"
    neo4j_initial, neo4j_status_initial, neo4j_elapsed_initial = load_saved_method(
        rows, neo4j_checkpoint, fingerprint
    )
    mcp_initial, mcp_status_initial, mcp_elapsed_initial = load_saved_method(
        rows, mcp_checkpoint, fingerprint
    )

    print("Running Neo4j LLM Graph Builder...", flush=True)
    neo4j, neo4j_status, neo4j_elapsed = run_method(
        rows,
        lambda text: graph_builder_extract(transformer, text),
        cfg.workers,
        neo4j_initial,
        neo4j_status_initial,
        neo4j_elapsed_initial,
        neo4j_checkpoint,
        fingerprint,
    )
    print("Running our one-pass extraction...", flush=True)
    mcp_raw, mcp_status, mcp_elapsed = run_method(
        rows,
        lambda text: direct_extract(client, cfg, text),
        cfg.workers,
        mcp_initial,
        mcp_status_initial,
        mcp_elapsed_initial,
        mcp_checkpoint,
        fingerprint,
    )
    mcp_constrained = [repair_triples(triples) for triples in mcp_raw]

    metrics = {
        "neo4j_graph_builder": evaluate(rows, neo4j, neo4j_status, neo4j_elapsed),
        "mcp_raw": evaluate(rows, mcp_raw, mcp_status, mcp_elapsed),
        "mcp_constrained": evaluate(
            rows, mcp_constrained, mcp_status, mcp_elapsed
        ),
    }
    results = {
        "benchmark": "Neo4j LLM Graph Builder comparison on TNEWS",
        "model": cfg.model,
        "documents": len(rows),
        "categories": len(Counter(row.get("label_desc", "") for row in rows)),
        "seed": RNG_SEED,
        "workers": cfg.workers,
        "neo4j_commit": "5ff7af3e9bb9226e1bbecd02f70f8d98697727a7",
        "fingerprint": fingerprint,
        "metrics": metrics,
        "paired_category": paired_category_comparison(rows, neo4j, mcp_raw),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (OUT_DIR / "predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "doc_id",
                "gold_label",
                "sentence",
                "keywords",
                "neo4j_status",
                "mcp_status",
                "neo4j_triples",
                "mcp_raw_triples",
                "mcp_constrained_triples",
            ],
        )
        writer.writeheader()
        for index, row in enumerate(rows):
            writer.writerow(
                {
                    "doc_id": index,
                    "gold_label": row.get("label_desc", ""),
                    "sentence": row.get("sentence", ""),
                    "keywords": row.get("keywords", ""),
                    "neo4j_status": neo4j_status[index],
                    "mcp_status": mcp_status[index],
                    "neo4j_triples": json.dumps(neo4j[index], ensure_ascii=False),
                    "mcp_raw_triples": json.dumps(mcp_raw[index], ensure_ascii=False),
                    "mcp_constrained_triples": json.dumps(
                        mcp_constrained[index], ensure_ascii=False
                    ),
                }
            )
    write_report(results)
    print(OUT_DIR / "report.md")


if __name__ == "__main__":
    main()
