#!/usr/bin/env python3
"""Run the additional API experiments required for the Paper 1 submission.

The script is resumable.  It never downloads a local model and deliberately
disables environment proxy inheritance for the OpenAI-compatible endpoint.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import httpx
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exps.paper1_repair_benchmark.run_benchmark import (
    call_json,
    deduplicate,
    direct_llm_method,
    normalize_triple,
    ours_method,
    parse_triples,
    prompt_payload,
    rule_only,
)


HERE = Path(__file__).resolve().parent
BENCHMARK = ROOT / "exps" / "paper1_repair_benchmark" / "benchmark.jsonl"
API_FILE = ROOT / "api"
CLAUDE = "claude-haiku-4-5-20251001"
QWEN = "Qwen3.8-27B-no-thinking"
GPT = "gpt-5.6-sol"
GEMMA = "google/gemma-4-26B-A4B-it"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(rows, key=lambda item: item["case_id"]):
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def api_config() -> tuple[str, str]:
    text = API_FILE.read_text(encoding="utf-8")
    key = re.search(r"sk-[A-Za-z0-9_-]+", text)
    url = re.search(r"https?://[^\s]+", text)
    if not key or not url:
        raise RuntimeError("Cannot parse local API configuration")
    base = url.group(0).rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    return key.group(0), base


def make_client(key: str, base_url: str) -> OpenAI:
    return OpenAI(
        api_key=key,
        base_url=base_url,
        timeout=180,
        max_retries=0,
        http_client=httpx.Client(trust_env=False, timeout=180),
    )


def simple_pipeline_method(client: OpenAI, model: str, case: dict[str, Any]) -> dict[str, Any]:
    """Strong simple baseline: rules + one grounded LLM call + deduplication.

    It intentionally omits the graph profile, scale prior, trial-state utility,
    and constraint gate used by the full method.
    """
    structural = rule_only(case)
    system = (
        "Repair the supplied small knowledge graph using only the Chinese source evidence. "
        "Return the complete final graph as strict JSON: "
        "{\"triples\":[{\"head\":...,\"relation\":...,\"tail\":...}]}. "
        "Copy field values exactly from the source, use the required document node and allowed relations, "
        "and do not invent facts."
    )
    user = prompt_payload(case, structural) + (
        "\nDeterministic deduplication and obvious reversed-edge cleanup have already been applied. "
        "Restore missing or corrupted fields and retain correct fields."
    )
    raw, latency = call_json(client, model, system, user)
    triples, status = parse_triples(raw)
    return {
        "triples": deduplicate(triples),
        "status": status,
        "calls": 1,
        "latency_sec": latency,
        "raw_responses": [raw],
    }


def extraction_method(client: OpenAI, model: str, case: dict[str, Any]) -> dict[str, Any]:
    """Construct a graph from source text without seeing a corrupted graph."""
    required_head = case["clean_triples"][0]["head"]
    payload = {
        "source_evidence": case["evidence_text"],
        "required_document_node": required_head,
        "allowed_relations": case["allowed_relations"],
    }
    system = (
        "Extract a document-level knowledge graph from the supplied Chinese source. "
        "Return strict JSON only as "
        "{\"triples\":[{\"head\":...,\"relation\":...,\"tail\":...}]}. "
        "Use the required document node as every head, use only allowed relations, copy exact source spans, "
        "and emit at most one triple per relation."
    )
    raw, latency = call_json(client, model, system, json.dumps(payload, ensure_ascii=False), max_tokens=1200)
    triples, status = parse_triples(raw)
    return {
        "triples": triples,
        "status": status,
        "calls": 1,
        "latency_sec": latency,
        "raw_responses": [raw],
    }


def run_one(
    method: Callable[[OpenAI, str, dict[str, Any]], dict[str, Any]],
    model: str,
    case: dict[str, Any],
    key: str,
    base_url: str,
) -> dict[str, Any]:
    error = "not_run"
    for attempt in range(5):
        client = make_client(key, base_url)
        try:
            result = method(client, model, case)
            return {
                "case_id": case["case_id"],
                "domain": case["domain"],
                "split": case.get("split", "test"),
                "model": model,
                **result,
            }
        except Exception as exc:  # retain failures as end-to-end outcomes
            error = f"{type(exc).__name__}:{str(exc)[:240]}"
            if attempt < 4:
                if type(exc).__name__ == "RateLimitError":
                    time.sleep(20 * (attempt + 1))
                else:
                    time.sleep(min(30, 2 ** attempt))
        finally:
            client.close()
    return {
        "case_id": case["case_id"],
        "domain": case["domain"],
        "split": case.get("split", "test"),
        "model": model,
        "triples": [],
        "status": error,
        "calls": 0,
        "latency_sec": 0.0,
        "raw_responses": [],
    }


def run_batch(
    label: str,
    method: Callable[[OpenAI, str, dict[str, Any]], dict[str, Any]],
    model: str,
    cases: list[dict[str, Any]],
    output: Path,
    workers: int,
) -> None:
    existing = {row["case_id"]: row for row in read_jsonl(output)}
    pending = [case for case in cases if existing.get(case["case_id"], {}).get("status") != "ok"]
    print(f"[{label}] total={len(cases)} pending={len(pending)} model={model}", flush=True)
    if not pending:
        return
    key, base_url = api_config()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(run_one, method, model, case, key, base_url): case
            for case in pending
        }
        for index, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            existing[row["case_id"]] = row
            if index % 10 == 0 or index == len(pending):
                write_jsonl(output, list(existing.values()))
                ok = sum(item.get("status") == "ok" for item in existing.values())
                print(f"[{label}] completed={index}/{len(pending)} stored_ok={ok}", flush=True)


def test_cases() -> list[dict[str, Any]]:
    return [case for case in read_jsonl(BENCHMARK) if case["split"] == "test"]


def cross_model_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for domain in ("government", "finance", "environment"):
        selected.extend(sorted((c for c in cases if c["domain"] == domain), key=lambda c: c["case_id"])[:20])
    return sorted(selected, key=lambda c: c["case_id"])


def with_input(case: dict[str, Any], triples: list[dict[str, str]]) -> dict[str, Any]:
    return {**case, "corrupted_triples": triples}


def run_stages(stages: list[str], workers: int) -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    cases = test_cases()

    if "synthetic_simple" in stages:
        run_batch(
            "synthetic-simple", simple_pipeline_method, CLAUDE, cases,
            HERE / "predictions_simple_pipeline_claude.jsonl", workers,
        )

    if "clean_full" in stages:
        clean_cases = [with_input(case, case["clean_triples"]) for case in cases]
        run_batch(
            "clean-full", ours_method, CLAUDE, clean_cases,
            HERE / "predictions_full_clean_claude.jsonl", workers,
        )

    extraction_path = HERE / "natural_extraction_claude.jsonl"
    if "natural_extract" in stages:
        run_batch("natural-extract", extraction_method, CLAUDE, cases, extraction_path, workers)

    if "natural_repair" in stages:
        extracted = {row["case_id"]: row for row in read_jsonl(extraction_path)}
        complete = sum(row.get("status") == "ok" for row in extracted.values())
        if len(extracted) != len(cases):
            raise RuntimeError(
                f"Natural extraction must return one end-to-end outcome per document before repair: "
                f"rows={len(extracted)} ok={complete} expected={len(cases)}"
            )
        print(f"[natural-repair-input] rows={len(extracted)} parse_ok={complete}", flush=True)
        natural_cases = [with_input(case, extracted[case["case_id"]]["triples"]) for case in cases]
        run_batch(
            "natural-simple", simple_pipeline_method, CLAUDE, natural_cases,
            HERE / "natural_repairs_simple_claude.jsonl", workers,
        )
        run_batch(
            "natural-full", ours_method, CLAUDE, natural_cases,
            HERE / "natural_repairs_full_claude.jsonl", workers,
        )

    if "cross_model" in stages:
        subset = cross_model_cases(cases)
        for model, slug in ((GEMMA, "gemma"),):
            for method_name, method in (
                ("direct", direct_llm_method),
                ("simple", simple_pipeline_method),
                ("full", ours_method),
            ):
                run_batch(
                    f"cross-{slug}-{method_name}", method, model, subset,
                    HERE / f"cross_model_{slug}_{method_name}.jsonl", workers,
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stages", nargs="+",
        choices=["synthetic_simple", "clean_full", "natural_extract", "natural_repair", "cross_model", "all"],
        default=["all"],
    )
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    stages = args.stages
    if "all" in stages:
        stages = ["synthetic_simple", "clean_full", "natural_extract", "natural_repair", "cross_model"]
    run_stages(stages, args.workers)


if __name__ == "__main__":
    main()
