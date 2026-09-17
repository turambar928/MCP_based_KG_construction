#!/usr/bin/env python3
"""Analyze Paper 1 submission-extension experiments from archived predictions."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from scipy.stats import binomtest, wilcoxon

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exps.decision_network.build_from_repair_benchmark import graph_features
from exps.paper1_repair_benchmark.analyze_results import case_metrics, counter, intersection_size
from exps.paper1_repair_benchmark.run_benchmark import normalize_triple, parse_triples


HERE = Path(__file__).resolve().parent
BENCH = ROOT / "exps" / "paper1_repair_benchmark"
DECISION = ROOT / "exps" / "decision_network"
FEATURES = ["S_iso", "S_red", "S_log", "S_sem", "n_v", "n_e", "density", "n_viol_feat"]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def triple_key(triple: dict[str, Any]) -> tuple[str, str, str]:
    normalized = normalize_triple(triple)
    return tuple(normalized.values()) if normalized else ("", "", "")


def generic_metrics(
    input_triples: list[dict[str, Any]],
    output_triples: list[dict[str, Any]],
    gold_triples: list[dict[str, Any]],
) -> dict[str, float]:
    inp, out, gold = counter(input_triples), counter(output_triples), counter(gold_triples)
    initial_errors = sum((gold - inp).values()) + sum((inp - gold).values())
    final_errors = sum((gold - out).values()) + sum((out - gold).values())
    correct = intersection_size(out, gold)
    n_out, n_gold = sum(out.values()), sum(gold.values())
    precision = correct / n_out if n_out else 0.0
    recall = correct / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    initially_correct = inp & gold
    preservation = (
        intersection_size(out, initially_correct) / sum(initially_correct.values())
        if initially_correct else 1.0
    )
    actual_add, actual_remove = out - inp, inp - out
    required_add, required_remove = gold - inp, inp - gold
    good_edits = intersection_size(actual_add, required_add) + intersection_size(actual_remove, required_remove)
    actual_edits = sum(actual_add.values()) + sum(actual_remove.values())
    return {
        "initial_errors": float(initial_errors),
        "final_errors": float(final_errors),
        "error_reduction": (initial_errors - final_errors) / initial_errors if initial_errors else float(final_errors == 0),
        "clean_fact_preservation": preservation,
        "overrepair_rate": max(0, actual_edits - good_edits) / actual_edits if actual_edits else 0.0,
        "triple_precision": precision,
        "triple_recall": recall,
        "triple_f1": f1,
        "exact_match": float(out == gold),
    }


def load_cases() -> dict[str, dict[str, Any]]:
    return {
        case["case_id"]: case
        for case in read_jsonl(BENCH / "benchmark.jsonl")
        if case["split"] == "test"
    }


def summarize_synthetic(cases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    paths = {
        "Direct LLM": BENCH / "predictions_direct_llm.jsonl",
        "Simple pipeline": HERE / "predictions_simple_pipeline_claude.jsonl",
        "Full system": BENCH / "predictions_ours.jsonl",
    }
    rows = []
    for method, path in paths.items():
        preds = {row["case_id"]: row for row in read_jsonl(path)}
        metrics = []
        for cid, case in cases.items():
            pred = {**preds[cid], "method": method}
            record, _ = case_metrics(case, pred)
            metrics.append(record)
        record = {
            "method": method,
            "n": len(metrics),
            "parse_success": mean([float(preds[cid].get("status") == "ok") for cid in cases]),
            "defect_repair_rate": mean([m["defect_repair_rate"] for m in metrics]),
            "clean_fact_preservation": mean([m["clean_fact_preservation"] for m in metrics]),
            "overrepair_rate": mean([m["overrepair_rate"] for m in metrics]),
            "triple_f1": mean([m["triple_f1"] for m in metrics]),
            "exact_match": mean([m["exact_match"] for m in metrics]),
            "calls": mean([m["calls"] for m in metrics]),
            "latency_sec": mean([m["latency_sec"] for m in metrics]),
        }
        for metric in ("defect_repair_rate", "triple_f1", "exact_match", "latency_sec"):
            low, high = paired_bootstrap([m[metric] for m in metrics], repeats=5_000)
            record[f"{metric}_ci_low"] = low
            record[f"{metric}_ci_high"] = high
        rows.append(record)
    write_csv(HERE / "synthetic_simple_pipeline.csv", rows)
    return rows


def summarize_natural(cases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    extraction = {r["case_id"]: r for r in read_jsonl(HERE / "natural_extraction_claude.jsonl")}
    systems = {
        "Extracted graph (no repair)": extraction,
        "Simple pipeline": {r["case_id"]: r for r in read_jsonl(HERE / "natural_repairs_simple_claude.jsonl")},
        "Full system": {r["case_id"]: r for r in read_jsonl(HERE / "natural_repairs_full_claude.jsonl")},
    }
    rows = []
    for name, predictions in systems.items():
        records = []
        for cid, case in cases.items():
            initial = extraction[cid]["triples"]
            output = predictions[cid]["triples"]
            metrics = generic_metrics(initial, output, case["clean_triples"])
            metrics["calls"] = float(predictions[cid].get("calls", 0)) if name != "Extracted graph (no repair)" else 0.0
            metrics["latency_sec"] = float(predictions[cid].get("latency_sec", 0)) if name != "Extracted graph (no repair)" else 0.0
            records.append(metrics)
        rows.append({
            "method": name,
            "n_documents": len(records),
            "parse_success": (
                mean([float(predictions[cid].get("status") == "ok") for cid in cases])
                if name != "Extracted graph (no repair)"
                else mean([float(extraction[cid].get("status") == "ok") for cid in cases])
            ),
            "documents_with_natural_errors": sum(r["initial_errors"] > 0 for r in records),
            "mean_initial_errors": mean([r["initial_errors"] for r in records]),
            "mean_final_errors": mean([r["final_errors"] for r in records]),
            "error_reduction": mean([r["error_reduction"] for r in records if r["initial_errors"] > 0]),
            "clean_fact_preservation": mean([r["clean_fact_preservation"] for r in records]),
            "overrepair_rate": mean([r["overrepair_rate"] for r in records]),
            "triple_f1": mean([r["triple_f1"] for r in records]),
            "exact_match": mean([r["exact_match"] for r in records]),
            "calls": mean([r["calls"] for r in records]),
            "latency_sec": mean([r["latency_sec"] for r in records]),
        })
    write_csv(HERE / "natural_error_summary.csv", rows)
    return rows


def paired_bootstrap(values: list[float], repeats: int = 10_000, seed: int = 42) -> tuple[float, float]:
    rng = random.Random(seed)
    estimates = sorted(mean([values[rng.randrange(len(values))] for _ in values]) for _ in range(repeats))
    return estimates[int(0.025 * repeats)], estimates[int(0.975 * repeats)]


def paired_statistics(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    simple = {r["case_id"]: r for r in read_jsonl(HERE / "predictions_simple_pipeline_claude.jsonl")}
    full = {r["case_id"]: r for r in read_jsonl(BENCH / "predictions_ours.jsonl")}
    simple_defects, full_defects = {}, {}
    for cid, case in cases.items():
        _, simple_outcomes = case_metrics(case, {**simple[cid], "method": "simple"})
        _, full_outcomes = case_metrics(case, {**full[cid], "method": "full"})
        simple_defects.update(simple_outcomes)
        full_defects.update(full_outcomes)
    full_only = sum(full_defects[k] and not simple_defects[k] for k in full_defects)
    simple_only = sum(simple_defects[k] and not full_defects[k] for k in full_defects)
    discordant = full_only + simple_only

    extraction = {r["case_id"]: r for r in read_jsonl(HERE / "natural_extraction_claude.jsonl")}
    natural_simple = {r["case_id"]: r for r in read_jsonl(HERE / "natural_repairs_simple_claude.jsonl")}
    natural_full = {r["case_id"]: r for r in read_jsonl(HERE / "natural_repairs_full_claude.jsonl")}
    f1_diff, error_diff, simple_exact, full_exact = [], [], [], []
    for cid, case in cases.items():
        inp = extraction[cid]["triples"]
        s = generic_metrics(inp, natural_simple[cid]["triples"], case["clean_triples"])
        f = generic_metrics(inp, natural_full[cid]["triples"], case["clean_triples"])
        f1_diff.append(f["triple_f1"] - s["triple_f1"])
        error_diff.append(s["final_errors"] - f["final_errors"])
        simple_exact.append(bool(s["exact_match"]))
        full_exact.append(bool(f["exact_match"]))
    f1_ci = paired_bootstrap(f1_diff)
    error_ci = paired_bootstrap(error_diff)
    natural_full_only = sum(f and not s for f, s in zip(full_exact, simple_exact))
    natural_simple_only = sum(s and not f for f, s in zip(full_exact, simple_exact))
    natural_discordant = natural_full_only + natural_simple_only
    nonzero_errors = [value for value in error_diff if value != 0]
    return {
        "controlled_full_vs_simple": {
            "n_defects": len(full_defects),
            "full_only_success": full_only,
            "simple_only_success": simple_only,
            "mcnemar_p": binomtest(min(full_only, simple_only), discordant, 0.5).pvalue if discordant else 1.0,
        },
        "natural_full_vs_simple": {
            "mean_triple_f1_difference": mean(f1_diff),
            "triple_f1_difference_ci": list(f1_ci),
            "mean_errors_prevented_per_document": mean(error_diff),
            "errors_prevented_ci": list(error_ci),
            "wilcoxon_one_sided_p": (
                wilcoxon(nonzero_errors, alternative="greater").pvalue if nonzero_errors else 1.0
            ),
            "full_only_exact": natural_full_only,
            "simple_only_exact": natural_simple_only,
            "exact_match_mcnemar_p": (
                binomtest(min(natural_full_only, natural_simple_only), natural_discordant, 0.5).pvalue
                if natural_discordant else 1.0
            ),
        },
    }


def make_annotation_sample(cases: dict[str, dict[str, Any]], limit: int = 200) -> dict[str, Any]:
    extraction = {r["case_id"]: r for r in read_jsonl(HERE / "natural_extraction_claude.jsonl")}
    candidates = []
    for cid, case in sorted(cases.items()):
        pred = counter(extraction[cid]["triples"])
        gold = counter(case["clean_triples"])
        for triple, count in sorted((gold - pred).items()):
            for occurrence in range(count):
                candidates.append((cid, "missing_gold_triple", triple, occurrence))
        for triple, count in sorted((pred - gold).items()):
            for occurrence in range(count):
                candidates.append((cid, "unsupported_or_mismatched_output", triple, occurrence))
    rng = random.Random(42)
    rng.shuffle(candidates)
    chosen = candidates[:limit]
    rows = []
    for index, (cid, issue_type, triple, occurrence) in enumerate(chosen, start=1):
        case = cases[cid]
        rows.append({
            "sample_id": f"NE-{index:03d}",
            "case_id": cid,
            "domain": case["domain"],
            "issue_type": issue_type,
            "head": triple[0],
            "relation": triple[1],
            "tail": triple[2],
            "occurrence": occurrence + 1,
            "source_evidence": case["evidence_text"],
            "system_reference_label": "error",
            "annotator_a_is_error": "",
            "annotator_a_repair_acceptable": "",
            "annotator_b_is_error": "",
            "annotator_b_repair_acceptable": "",
            "adjudicated_is_error": "",
            "adjudicated_repair_acceptable": "",
            "notes": "",
        })
    write_csv(HERE / "natural_error_annotation_sample.csv", rows)
    digest = hashlib.sha256((HERE / "natural_error_annotation_sample.csv").read_bytes()).hexdigest()
    manifest = {
        "seed": 42,
        "population_discrepancies": len(candidates),
        "sample_size": len(rows),
        "sample_sha256": digest,
        "human_annotation_status": "pending_two_independent_annotators",
    }
    (HERE / "natural_error_annotation_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def gate_audit(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    predictions = {r["case_id"]: r for r in read_jsonl(BENCH / "predictions_ours.jsonl")}
    detail = []
    reason_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    for cid, case in cases.items():
        raw = (predictions[cid].get("raw_responses") or [""])[-1]
        proposed, _ = parse_triples(raw)
        required_head = case["clean_triples"][0]["head"]
        allowed = set(case["allowed_relations"])
        evidence = case["evidence_text"]
        gold = counter(case["clean_triples"])
        accepted: Counter = Counter()
        seen_exact: Counter = Counter()
        seen_relations: set[str] = set()
        for raw_triple in proposed:
            triple = normalize_triple(raw_triple)
            if not triple:
                continue
            key = triple_key(triple)
            reason = "accepted"
            if seen_exact[key] > 0:
                reason = "duplicate"
            elif triple["head"] != required_head:
                reason = "wrong_head"
            elif triple["relation"] not in allowed:
                reason = "invalid_relation"
            elif triple["tail"] not in evidence:
                reason = "ungrounded"
            elif triple["relation"] in seen_relations:
                reason = "relation_cardinality"
            seen_exact[key] += 1
            if reason == "accepted":
                accepted[key] += 1
                seen_relations.add(triple["relation"])
                continue
            reason_counts[reason] += 1
            if reason == "duplicate":
                outcome = "prevented_extra_duplicate" if accepted[key] >= gold[key] else "rejected_potential_gold_copy"
            elif gold[key] > accepted[key]:
                outcome = "rejected_gold_triple"
            else:
                outcome = "prevented_non_gold_triple"
            outcome_counts[outcome] += 1
            detail.append({
                "case_id": cid,
                "domain": case["domain"],
                "reason": reason,
                "gold_membership": int(gold[key] > 0),
                "outcome": outcome,
                "head": key[0],
                "relation": key[1],
                "tail": key[2],
            })
    write_csv(HERE / "constraint_gate_rejections.csv", detail)
    result = {
        "n_cases": len(cases),
        "n_rejections": len(detail),
        "by_reason": dict(reason_counts),
        "by_outcome": dict(outcome_counts),
    }
    (HERE / "constraint_gate_audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def load_router() -> tuple[dict[str, np.ndarray], dict[str, Any], float]:
    params = dict(np.load(DECISION / "fphi_model.npz"))
    scaler = json.loads((DECISION / "scaler.json").read_text(encoding="utf-8"))
    quality = json.loads((DECISION / "decision_quality.json").read_text(encoding="utf-8"))
    return params, scaler, float(quality["tau_repair"])


def router_probability(features: dict[str, float], params: dict[str, np.ndarray], scaler: dict[str, Any]) -> float:
    x = np.array([[features[name] for name in scaler["features"]]], dtype=float)
    x = (x - np.asarray(scaler["mu"])) / np.asarray(scaler["sd"])
    a1 = np.maximum(0, x @ params["W1"] + params["b1"])
    a2 = np.maximum(0, a1 @ params["W2"] + params["b2"])
    logit = float((a2 @ params["wr"] + params["br"]).ravel()[0])
    return 1.0 / (1.0 + np.exp(-np.clip(logit, -50, 50)))


def evaluate_router_stream(
    name: str,
    cases: dict[str, dict[str, Any]],
    dirty_inputs: dict[str, list[dict[str, Any]]],
    dirty_repairs: dict[str, dict[str, Any]],
    clean_repairs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    params, scaler, tau = load_router()
    rng = random.Random(42)
    records = []
    for cid, case in sorted(cases.items()):
        for variant, graph in (("clean", case["clean_triples"]), ("dirty", dirty_inputs[cid])):
            feat = graph_features(case, graph)
            label = int(counter(graph) != counter(case["clean_triples"]))
            prob = router_probability(feat, params, scaler)
            decisions = {
                "Learned router": int(prob >= tau),
                "Heuristic violations": int(feat["n_viol_feat"] > 0),
                "Quality threshold": int(min(feat[s] for s in ("S_iso", "S_red", "S_log", "S_sem")) < 95.0),
                "Random 50%": int(rng.random() < 0.5),
                "Always repair": 1,
                "Never repair": 0,
            }
            repair = clean_repairs[cid] if variant == "clean" else dirty_repairs[cid]
            for policy, routed in decisions.items():
                output = repair["triples"] if routed else graph
                metrics = generic_metrics(graph, output, case["clean_triples"])
                records.append({
                    "stream": name,
                    "case_id": cid,
                    "domain": case["domain"],
                    "variant": variant,
                    "label_dirty": label,
                    "policy": policy,
                    "routed": routed,
                    "router_probability": prob,
                    "calls": float(repair.get("calls", 0)) if routed else 0.0,
                    "latency_sec": float(repair.get("latency_sec", 0)) if routed else 0.0,
                    **metrics,
                })
    summaries = []
    for policy in sorted({r["policy"] for r in records}):
        items = [r for r in records if r["policy"] == policy]
        labels = [r["label_dirty"] for r in items]
        preds = [r["routed"] for r in items]
        dirty = [r for r in items if r["label_dirty"]]
        clean = [r for r in items if not r["label_dirty"]]
        summaries.append({
            "stream": name,
            "policy": policy,
            "n": len(items),
            "dirty_prevalence": mean(labels),
            "route_accuracy": accuracy_score(labels, preds),
            "route_f1": f1_score(labels, preds, zero_division=0),
            "false_negative_rate": sum(y and not p for y, p in zip(labels, preds)) / max(1, sum(labels)),
            "false_positive_rate": sum((not y) and p for y, p in zip(labels, preds)) / max(1, len(labels) - sum(labels)),
            "error_reduction_dirty": mean([r["error_reduction"] for r in dirty]),
            "clean_exact_match": mean([r["exact_match"] for r in clean]),
            "triple_f1": mean([r["triple_f1"] for r in items]),
            "exact_match": mean([r["exact_match"] for r in items]),
            "calls_per_doc": mean([r["calls"] for r in items]),
            "latency_per_doc": mean([r["latency_sec"] for r in items]),
        })
    write_csv(HERE / f"router_{name}_per_case.csv", records)
    return summaries


def router_analysis(cases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    clean_repairs = {r["case_id"]: r for r in read_jsonl(HERE / "predictions_full_clean_claude.jsonl")}
    synthetic_inputs = {cid: case["corrupted_triples"] for cid, case in cases.items()}
    synthetic_repairs = {r["case_id"]: r for r in read_jsonl(BENCH / "predictions_ours.jsonl")}
    natural_extract = {r["case_id"]: r for r in read_jsonl(HERE / "natural_extraction_claude.jsonl")}
    natural_inputs = {cid: natural_extract[cid]["triples"] for cid in cases}
    natural_repairs = {r["case_id"]: r for r in read_jsonl(HERE / "natural_repairs_full_claude.jsonl")}
    summaries = evaluate_router_stream("controlled", cases, synthetic_inputs, synthetic_repairs, clean_repairs)
    summaries += evaluate_router_stream("natural_extraction", cases, natural_inputs, natural_repairs, clean_repairs)
    write_csv(HERE / "router_end_to_end_summary.csv", summaries)
    return summaries


def leave_one_domain_out() -> list[dict[str, Any]]:
    df = pd.read_csv(DECISION / "dataset.csv")
    df["n_viol_feat"] = df[["n_missing", "n_dup", "n_logconf"]].sum(axis=1)
    rows = []
    for held_out in sorted(df["domain"].unique()):
        train = df[df["domain"] != held_out]
        test = df[df["domain"] == held_out]
        trigger = make_pipeline(
            StandardScaler(),
            MLPClassifier(hidden_layer_sizes=(32, 16), random_state=42, max_iter=2000, early_stopping=True),
        )
        trigger.fit(train[FEATURES], train["y_repair"])
        trigger_pred = trigger.predict(test[FEATURES])
        train_dirty = train[train["scale_label"] != "none"]
        test_dirty = test[test["scale_label"] != "none"]
        scale_ids = {name: index for index, name in enumerate(("entity", "graph", "context"))}
        train_scale = train_dirty["scale_label"].map(scale_ids).to_numpy(int)
        test_scale = test_dirty["scale_label"].map(scale_ids).to_numpy(int)
        scale = make_pipeline(
            StandardScaler(),
            MLPClassifier(hidden_layer_sizes=(32, 16), random_state=42, max_iter=2000, early_stopping=True),
        )
        scale.fit(train_dirty[FEATURES], train_scale)
        scale_pred = scale.predict(test_dirty[FEATURES])
        rows.append({
            "held_out_domain": held_out,
            "n_train": len(train),
            "n_test": len(test),
            "trigger_accuracy": accuracy_score(test["y_repair"], trigger_pred),
            "trigger_f1": f1_score(test["y_repair"], trigger_pred, zero_division=0),
            "scale_top1": accuracy_score(test_scale, scale_pred),
            "scale_macro_f1": f1_score(test_scale, scale_pred, average="macro", zero_division=0),
        })
    write_csv(HERE / "leave_one_domain_out.csv", rows)
    return rows


def cross_model(cases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    selected = []
    for domain in ("government", "finance", "environment"):
        selected.extend(sorted((c for c in cases.values() if c["domain"] == domain), key=lambda c: c["case_id"])[:20])
    ids = {c["case_id"] for c in selected}
    sources = {
        ("Claude Haiku", "Direct LLM"): BENCH / "predictions_direct_llm.jsonl",
        ("Claude Haiku", "Simple pipeline"): HERE / "predictions_simple_pipeline_claude.jsonl",
        ("Claude Haiku", "Full system"): BENCH / "predictions_ours.jsonl",
    }
    for model, slug in (("Gemma-4-26B-A4B-it", "gemma"),):
        for method, method_slug in (("Direct LLM", "direct"), ("Simple pipeline", "simple"), ("Full system", "full")):
            sources[(model, method)] = HERE / f"cross_model_{slug}_{method_slug}.jsonl"
    rows = []
    for (model, method), path in sources.items():
        predictions = {r["case_id"]: r for r in read_jsonl(path) if r["case_id"] in ids}
        metrics = []
        for case in selected:
            pred = {**predictions[case["case_id"]], "method": method}
            item, _ = case_metrics(case, pred)
            metrics.append(item)
        rows.append({
            "model": model,
            "method": method,
            "n": len(metrics),
            "defect_repair_rate": mean([m["defect_repair_rate"] for m in metrics]),
            "clean_fact_preservation": mean([m["clean_fact_preservation"] for m in metrics]),
            "overrepair_rate": mean([m["overrepair_rate"] for m in metrics]),
            "triple_f1": mean([m["triple_f1"] for m in metrics]),
            "exact_match": mean([m["exact_match"] for m in metrics]),
            "calls": mean([m["calls"] for m in metrics]),
            "latency_sec": mean([m["latency_sec"] for m in metrics]),
        })
    write_csv(HERE / "cross_model_summary.csv", rows)
    return rows


def markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], digits: int = 3) -> str:
    header = "| " + " | ".join(label for _, label in columns) + " |"
    rule = "|" + "|".join("---" if i == 0 else "---:" for i in range(len(columns))) + "|"
    body = []
    for row in rows:
        vals = []
        for key, _ in columns:
            value = row[key]
            vals.append(f"{value:.{digits}f}" if isinstance(value, float) else str(value))
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, rule, *body])


def main() -> None:
    cases = load_cases()
    synthetic = summarize_synthetic(cases)
    natural = summarize_natural(cases)
    annotation = make_annotation_sample(cases)
    gate = gate_audit(cases)
    router = router_analysis(cases)
    lodo = leave_one_domain_out()
    models = cross_model(cases)
    paired = paired_statistics(cases)
    result = {
        "synthetic_simple_pipeline": synthetic,
        "natural_error": natural,
        "annotation_manifest": annotation,
        "constraint_gate": gate,
        "router_end_to_end": router,
        "leave_one_domain_out": lodo,
        "cross_model": models,
        "paired_statistics": paired,
    }
    (HERE / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Paper 1 submission-extension experiments",
        "",
        "## Strong simple-pipeline baseline on the controlled test set",
        "",
        markdown_table(synthetic, [("method", "Method"), ("defect_repair_rate", "Repair"), ("triple_f1", "F1"), ("exact_match", "Exact"), ("calls", "Calls"), ("latency_sec", "Latency (s)")]),
        "",
        "## Naturally occurring extraction errors",
        "",
        markdown_table(natural, [("method", "Method"), ("documents_with_natural_errors", "Docs with errors"), ("error_reduction", "Error reduction"), ("triple_f1", "F1"), ("exact_match", "Exact"), ("calls", "Calls")]),
        "",
        "The natural-error input is produced by a real Claude extraction call from source text; no defect is injected. The structured source fields provide the reference graph.",
        "",
        "## Constraint gate",
        "",
        f"The gate rejected {gate['n_rejections']} proposals. Reasons: `{json.dumps(gate['by_reason'], ensure_ascii=False)}`. Outcomes: `{json.dumps(gate['by_outcome'], ensure_ascii=False)}`.",
        "",
        "## Paired full-vs-simple tests",
        "",
        f"Controlled defects: `{json.dumps(paired['controlled_full_vs_simple'], ensure_ascii=False)}`.",
        "",
        f"Natural extraction: `{json.dumps(paired['natural_full_vs_simple'], ensure_ascii=False)}`.",
        "",
        "## End-to-end router comparison",
        "",
        markdown_table(router, [("stream", "Stream"), ("policy", "Policy"), ("route_f1", "Route F1"), ("triple_f1", "Triple F1"), ("exact_match", "Exact"), ("calls_per_doc", "Calls/doc"), ("latency_per_doc", "Latency/doc")]),
        "",
        "## Leave-one-domain-out router evaluation",
        "",
        markdown_table(lodo, [("held_out_domain", "Held-out"), ("trigger_f1", "Trigger F1"), ("scale_top1", "Scale top-1"), ("scale_macro_f1", "Scale macro-F1")]),
        "",
        "## Cross-model comparison on the fixed 60-case subset",
        "",
        markdown_table(models, [("model", "Model"), ("method", "Method"), ("defect_repair_rate", "Repair"), ("triple_f1", "F1"), ("exact_match", "Exact"), ("latency_sec", "Latency")]),
        "",
        "## Human annotation status",
        "",
        f"A frozen {annotation['sample_size']}-item sample has been prepared. Two independent human labels and adjudication are still required; no model judgment is reported as human agreement.",
        "",
    ]
    (HERE / "report.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report[:17]))


if __name__ == "__main__":
    main()
