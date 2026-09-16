#!/usr/bin/env python3
"""Independent-judge and repeated-run validation on 180 benchmark triples."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from openai import OpenAI
from scipy.stats import pearsonr, spearmanr


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
API_FILE = ROOT / "api"
JUDGE_MODEL = "google/gemma-4-26B-A4B-it"
METHODS = ("no_repair", "ours")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_api() -> OpenAI:
    text = API_FILE.read_text(encoding="utf-8")
    key = re.search(r"sk-[A-Za-z0-9_-]+", text)
    url = re.search(r"https?://[^\s]+", text)
    if not key or not url:
        raise RuntimeError("Cannot parse local API configuration")
    base = url.group().rstrip("/") + "/v1"
    host = re.sub(r"^https?://", "", base).split("/", 1)[0]
    for env_name in ("NO_PROXY", "no_proxy"):
        values = [v for v in os.environ.get(env_name, "").split(",") if v]
        if host not in values:
            values.append(host)
        os.environ[env_name] = ",".join(values)
    return OpenAI(api_key=key.group(), base_url=base, timeout=180)


def triple_key(triple: dict[str, Any]) -> tuple[str, str, str]:
    return triple["head"], triple["relation"], triple["tail"]


def build_sample() -> list[dict[str, Any]]:
    cases = {c["case_id"]: c for c in read_jsonl(HERE / "benchmark.jsonl") if c["split"] == "test"}
    rng = random.Random(42)
    sample = []
    for method in METHODS:
        predictions = {p["case_id"]: p for p in read_jsonl(HERE / f"predictions_{method}.jsonl")}
        for domain in ("government", "finance", "environment"):
            pool = []
            for cid, case in cases.items():
                if case["domain"] != domain:
                    continue
                gold = {triple_key(t) for t in case["clean_triples"]}
                for index, triple in enumerate(predictions[cid]["triples"]):
                    pool.append({
                        "item_id": f"{method}:{cid}:{index}", "method": method, "domain": domain,
                        "case_id": cid, "triple": triple, "evidence_text": case["evidence_text"],
                        "gold_valid": int(triple_key(triple) in gold),
                    })
            rng.shuffle(pool)
            sample.extend(pool[:30])
    sample.sort(key=lambda row: row["item_id"])
    with (HERE / "semantic_sample.jsonl").open("w", encoding="utf-8") as handle:
        for row in sample:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return sample


def parse_scores(text: str) -> dict[str, float]:
    raw = re.sub(r"^```(?:json)?", "", text.strip()).strip()
    raw = re.sub(r"```$", "", raw).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        value = json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {}
    scores = {}
    for item in value.get("scores", []):
        try:
            scores[str(item["id"])] = max(0.0, min(1.0, float(item["score"])))
        except (KeyError, TypeError, ValueError):
            continue
    return scores


def judge_batch(client: OpenAI, batch: list[dict[str, Any]], temperature: float) -> tuple[dict[str, float], str, float]:
    payload = [{"id": row["item_id"], "evidence": row["evidence_text"], "triple": row["triple"]} for row in batch]
    prompt = (
        "Blindly score whether each KG triple is fully supported by its Chinese source evidence. "
        "Use 1.0 for exact support, 0.0 for contradiction or unsupported content, and intermediate values only for partial support. "
        "Return strict JSON {\"scores\":[{\"id\":\"...\",\"score\":0.0}]}. Items:\n" +
        json.dumps(payload, ensure_ascii=False)
    )
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=JUDGE_MODEL, messages=[{"role": "user", "content": prompt}],
        temperature=temperature, max_tokens=1600,
    )
    raw = response.choices[0].message.content or ""
    return parse_scores(raw), raw, time.perf_counter() - start


def run_judge(sample: list[dict[str, Any]]) -> None:
    client = load_api()
    raw_rows = []
    score_rows = []
    repeat_subset = random.Random(42).sample(sample, 50)
    for repeat, subset in [(0, sample)] + [(r, repeat_subset) for r in range(1, 6)]:
        temperature = 0.0 if repeat == 0 else 0.1
        for offset in range(0, len(subset), 10):
            batch = subset[offset:offset + 10]
            last_error = ""
            for attempt in range(3):
                try:
                    scores, raw, latency = judge_batch(client, batch, temperature)
                    if len(scores) != len(batch):
                        raise ValueError(f"expected {len(batch)} scores, got {len(scores)}")
                    raw_rows.append({"repeat": repeat, "offset": offset, "latency_sec": latency,
                                     "raw_response": raw})
                    score_rows.extend({"item_id": row["item_id"], "repeat": repeat,
                                       "judge_score": scores[row["item_id"]]} for row in batch)
                    break
                except Exception as exc:
                    last_error = f"{type(exc).__name__}:{str(exc)[:160]}"
                    time.sleep(2 ** attempt)
            else:
                raise RuntimeError(last_error)
            print(f"repeat={repeat} completed={min(offset + 10, len(subset))}/{len(subset)}", flush=True)
    with (HERE / "semantic_judge_raw.jsonl").open("w", encoding="utf-8") as handle:
        for row in raw_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (HERE / "semantic_judge_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "repeat", "judge_score"])
        writer.writeheader(); writer.writerows(score_rows)


def analyze(sample: list[dict[str, Any]]) -> dict[str, Any]:
    truth = {row["item_id"]: row for row in sample}
    scores = list(csv.DictReader((HERE / "semantic_judge_scores.csv").open(encoding="utf-8")))
    primary = [row for row in scores if int(row["repeat"]) == 0]
    gold = [truth[row["item_id"]]["gold_valid"] for row in primary]
    judged = [float(row["judge_score"]) for row in primary]
    pearson = pearsonr(gold, judged)
    spearman = spearmanr(gold, judged)
    by_method = {}
    for method in METHODS:
        values = [float(row["judge_score"]) for row in primary if truth[row["item_id"]]["method"] == method]
        by_method[method] = {"n": len(values), "mean_judge_score": statistics.mean(values)}
    repeated: dict[str, list[float]] = defaultdict(list)
    for row in scores:
        if int(row["repeat"]) > 0:
            repeated[row["item_id"]].append(float(row["judge_score"]))
    item_sds = [statistics.pstdev(values) for values in repeated.values() if len(values) == 5]
    run_means = []
    for repeat in range(1, 6):
        values = [float(row["judge_score"]) for row in scores if int(row["repeat"]) == repeat]
        run_means.append(statistics.mean(values))
    report = {
        "judge_model": JUDGE_MODEL, "n_primary": len(primary), "gold_positive_rate": statistics.mean(gold),
        "pearson_r": pearson.statistic, "pearson_p": pearson.pvalue,
        "spearman_rho": spearman.statistic, "spearman_p": spearman.pvalue,
        "by_method": by_method, "repeat_subset_n": len(repeated),
        "mean_item_sd_over_5_runs": statistics.mean(item_sds),
        "aggregate_mean_sd_over_5_runs": statistics.pstdev(run_means),
        "repeat_run_means": run_means,
    }
    (HERE / "semantic_reliability.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-run", action="store_true")
    args = parser.parse_args()
    sample = build_sample()
    if not args.skip_run:
        run_judge(sample)
    analyze(sample)


if __name__ == "__main__":
    main()
