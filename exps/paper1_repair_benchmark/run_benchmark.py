#!/usr/bin/env python3
"""Run fair KG-repair baselines on the paired Paper 1 benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BENCHMARK = HERE / "benchmark.jsonl"
API_FILE = ROOT / "api"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
API_METHODS = {"direct_llm", "react_agent", "ours"}
METHODS = ["no_repair", "rule_only", "shacl", "direct_llm", "react_agent", "ours"]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_api_config() -> tuple[str, str]:
    text = API_FILE.read_text(encoding="utf-8")
    key = re.search(r"sk-[A-Za-z0-9_-]+", text)
    url = re.search(r"https?://[^\s]+", text)
    if not key or not url:
        raise RuntimeError("Cannot parse local API configuration")
    base_url = url.group(0).rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    host = re.sub(r"^https?://", "", base_url).split("/", 1)[0]
    for env_name in ("NO_PROXY", "no_proxy"):
        values = [v for v in os.environ.get(env_name, "").split(",") if v]
        if host not in values:
            values.append(host)
        os.environ[env_name] = ",".join(values)
    return key.group(0), base_url


def normalize_triple(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    head = " ".join(str(value.get("head", value.get("subject", ""))).split())
    relation = " ".join(str(value.get("relation", value.get("predicate", ""))).split())
    tail = " ".join(str(value.get("tail", value.get("object", ""))).split())
    if not head or not relation or not tail:
        return None
    return {"head": head[:420], "relation": relation[:80], "tail": tail[:420]}


def parse_triples(text: str) -> tuple[list[dict[str, str]], str]:
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        return [], "missing_json"
    try:
        value = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as exc:
        return [], f"json_error:{exc.msg}"
    items = value.get("triples", []) if isinstance(value, dict) else []
    triples = [triple for item in items if (triple := normalize_triple(item))]
    return triples, "ok" if triples else "empty_triples"


def deduplicate(triples: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    result = []
    for triple in triples:
        normalized = normalize_triple(triple)
        if not normalized:
            continue
        key = tuple(normalized.values())
        if key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def tool_report(case: dict[str, Any], triples: list[dict[str, str]]) -> dict[str, Any]:
    allowed = set(case["allowed_relations"])
    required_head = case["clean_triples"][0]["head"]
    counts = Counter(tuple(t.values()) for t in triples)
    return {
        "duplicate_rows": sum(n - 1 for n in counts.values() if n > 1),
        "invalid_relation_indices": [i for i, t in enumerate(triples) if t["relation"] not in allowed],
        "reversed_or_wrong_head_indices": [i for i, t in enumerate(triples) if t["head"] != required_head],
        "ungrounded_tail_indices": [i for i, t in enumerate(triples) if t["tail"] not in case["evidence_text"]],
        "present_relations": sorted({t["relation"] for t in triples if t["relation"] in allowed}),
        "allowed_relations": case["allowed_relations"],
        "required_head": required_head,
    }


def no_repair(case: dict[str, Any]) -> list[dict[str, str]]:
    return [normalize_triple(t) for t in case["corrupted_triples"] if normalize_triple(t)]


def rule_only(case: dict[str, Any]) -> list[dict[str, str]]:
    required_head = case["clean_triples"][0]["head"]
    allowed = set(case["allowed_relations"])
    repaired = []
    for raw in case["corrupted_triples"]:
        triple = normalize_triple(raw)
        if not triple:
            continue
        if triple["head"] != required_head and triple["tail"] == required_head:
            triple = {"head": required_head, "relation": triple["relation"], "tail": triple["head"]}
        if triple["head"] != required_head or triple["relation"] not in allowed:
            continue
        repaired.append(triple)
    return deduplicate(repaired)


def shacl_repair(case: dict[str, Any]) -> list[dict[str, str]]:
    """Apply canonical-head and allowed-predicate shapes; preserve duplicate raw rows."""
    required_head = case["clean_triples"][0]["head"]
    allowed = set(case["allowed_relations"])
    return [
        triple for raw in case["corrupted_triples"]
        if (triple := normalize_triple(raw))
        and triple["head"] == required_head
        and triple["relation"] in allowed
    ]


def prompt_payload(case: dict[str, Any], triples: list[dict[str, str]]) -> str:
    payload = {
        "source_evidence": case["evidence_text"],
        "required_document_node": case["clean_triples"][0]["head"],
        "allowed_relations": case["allowed_relations"],
        "corrupted_triples": triples,
    }
    return json.dumps(payload, ensure_ascii=False)


def call_json(client: OpenAI, model: str, system: str, user: str, max_tokens: int = 1800) -> tuple[str, float]:
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or "", time.perf_counter() - start


def direct_llm_method(client: OpenAI, model: str, case: dict[str, Any]) -> dict[str, Any]:
    system = (
        "You repair a small knowledge graph using only the supplied Chinese source evidence. "
        "Return strict JSON only as {\"triples\":[{\"head\":...,\"relation\":...,\"tail\":...}]}. "
        "Copy entity and field values exactly from the evidence. Do not invent facts."
    )
    user = prompt_payload(case, case["corrupted_triples"]) + (
        "\nRepair missing, duplicate, reversed, invalid-relation, and unsupported-value defects. "
        "Use only the required document node and allowed relations."
    )
    raw, latency = call_json(client, model, system, user)
    triples, parse_status = parse_triples(raw)
    return {"triples": triples, "status": parse_status, "calls": 1, "latency_sec": latency,
            "raw_responses": [raw]}


def react_agent_method(client: OpenAI, model: str, case: dict[str, Any]) -> dict[str, Any]:
    initial = [normalize_triple(t) for t in case["corrupted_triples"] if normalize_triple(t)]
    report = tool_report(case, initial)
    diag_system = (
        "You are a ReAct-style KG repair agent. Inspect the source, graph, and deterministic tool report. "
        "Return strict JSON with keys issues and repair_plan. Do not output the final graph yet."
    )
    diag_user = prompt_payload(case, initial) + "\nTOOL_REPORT=" + json.dumps(report, ensure_ascii=False)
    diagnosis, latency1 = call_json(client, model, diag_system, diag_user, max_tokens=1000)
    repair_system = (
        "You are the acting step of a KG repair agent. Return strict JSON only as "
        "{\"triples\":[{\"head\":...,\"relation\":...,\"tail\":...}]}. "
        "Use only source-supported exact values, the required head, and allowed relations."
    )
    repair_user = prompt_payload(case, initial) + "\nAGENT_DIAGNOSIS=" + diagnosis
    raw, latency2 = call_json(client, model, repair_system, repair_user)
    triples, parse_status = parse_triples(raw)
    return {"triples": triples, "status": parse_status, "calls": 2,
            "latency_sec": latency1 + latency2, "raw_responses": [diagnosis, raw]}


def constrain_output(case: dict[str, Any], triples: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    required_head = case["clean_triples"][0]["head"]
    allowed = set(case["allowed_relations"])
    evidence = case["evidence_text"]
    accepted = []
    rejected = Counter()
    seen_relations = set()
    for triple in deduplicate(triples):
        if triple["head"] != required_head:
            rejected["wrong_head"] += 1
        elif triple["relation"] not in allowed:
            rejected["invalid_relation"] += 1
        elif triple["tail"] not in evidence:
            rejected["ungrounded"] += 1
        elif triple["relation"] in seen_relations:
            rejected["relation_cardinality"] += 1
        else:
            seen_relations.add(triple["relation"])
            accepted.append(triple)
    return accepted, dict(rejected)


def ours_method(client: OpenAI, model: str, case: dict[str, Any]) -> dict[str, Any]:
    structural = rule_only(case)
    report = tool_report(case, structural)
    system = (
        "You are the context-scale repair module in a constraint-driven KG optimizer. "
        "Entity-scale duplicate repair and graph-scale schema checks have already run. "
        "Use the source evidence to restore missing or corrupted field triples. Return the COMPLETE final graph, "
        "including every unchanged triple and exactly one triple for every nonempty allowed field in the evidence. "
        "Return strict JSON only as "
        "{\"triples\":[{\"head\":...,\"relation\":...,\"tail\":...}]}. Copy exact source spans; do not infer unsupported facts."
    )
    user = prompt_payload(case, structural) + "\nMULTISCALE_DIAGNOSIS=" + json.dumps(report, ensure_ascii=False)
    raw, latency = call_json(client, model, system, user)
    proposed, parse_status = parse_triples(raw)
    constrained, rejected = constrain_output(case, proposed)
    return {"triples": constrained, "status": parse_status, "calls": 1,
            "latency_sec": latency, "raw_responses": [raw], "constraint_rejections": rejected,
            "tool_report": report}


def deterministic_result(method: str, case: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    fn: Callable[[dict[str, Any]], list[dict[str, str]]] = {
        "no_repair": no_repair,
        "rule_only": rule_only,
        "shacl": shacl_repair,
    }[method]
    triples = fn(case)
    return {"case_id": case["case_id"], "domain": case["domain"], "split": case["split"],
            "method": method, "model": None, "triples": triples, "status": "ok", "calls": 0,
            "latency_sec": time.perf_counter() - start, "raw_responses": []}


def run_api_case(method: str, case: dict[str, Any], key: str, base_url: str, model: str) -> dict[str, Any]:
    last_error = "not_run"
    for attempt in range(5):
        try:
            client = OpenAI(api_key=key, base_url=base_url, timeout=180)
            payload = {
                "direct_llm": direct_llm_method,
                "react_agent": react_agent_method,
                "ours": ours_method,
            }[method](client, model, case)
            return {"case_id": case["case_id"], "domain": case["domain"], "split": case["split"],
                    "method": method, "model": model, **payload}
        except Exception as exc:
            last_error = f"{type(exc).__name__}:{str(exc)[:200]}"
            if attempt < 4:
                if type(exc).__name__ == "RateLimitError":
                    time.sleep(20 * (attempt + 1))
                else:
                    time.sleep(min(30, 2 ** attempt))
    return {"case_id": case["case_id"], "domain": case["domain"], "split": case["split"],
            "method": method, "model": model, "triples": [], "status": last_error, "calls": 0,
            "latency_sec": 0.0, "raw_responses": []}


def load_existing(path: Path) -> dict[str, dict[str, Any]]:
    return {row["case_id"]: row for row in read_jsonl(path)} if path.exists() else {}


def save_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in sorted(rows, key=lambda item: item["case_id"]):
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_method(method: str, cases: list[dict[str, Any]], model: str, workers: int) -> None:
    out = HERE / f"predictions_{method}.jsonl"
    existing = load_existing(out)
    pending = [case for case in cases if existing.get(case["case_id"], {}).get("status") != "ok"]
    print(f"[{method}] total={len(cases)} pending={len(pending)}", flush=True)
    if method not in API_METHODS:
        for case in pending:
            existing[case["case_id"]] = deterministic_result(method, case)
        save_rows(out, list(existing.values()))
        return

    key, base_url = load_api_config()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_api_case, method, case, key, base_url, model): case for case in pending}
        for completed, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            existing[result["case_id"]] = result
            if completed % 10 == 0 or completed == len(pending):
                ok = sum(row.get("status") == "ok" for row in existing.values())
                print(f"[{method}] completed={completed}/{len(pending)} stored_ok={ok}", flush=True)
                save_rows(out, list(existing.values()))
    save_rows(out, list(existing.values()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=METHODS)
    parser.add_argument("--split", choices=["train", "validation", "test", "all"], default="test")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    cases = read_jsonl(BENCHMARK)
    if args.split != "all":
        cases = [case for case in cases if case["split"] == args.split]
    if args.limit:
        cases = cases[:args.limit]
    fingerprint = hashlib.sha256(BENCHMARK.read_bytes()).hexdigest()[:16]
    print(f"benchmark={fingerprint} cases={len(cases)} model={args.model}", flush=True)
    for method in args.methods:
        run_method(method, cases, args.model, args.workers)


if __name__ == "__main__":
    main()
