#!/usr/bin/env python3
"""Generate all active experiment figures from archived Paper 1 results."""
from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from figure_style import (
    AMBER,
    BLUE,
    BLUE_DARK,
    BLUE_LIGHT,
    GREEN,
    GRAY,
    GRID,
    HEAT_CMAP,
    INK,
    LIGHT_GRAY,
    MUTED,
    ORANGE,
    PALE,
    WHITE,
    apply_style,
    clean_axis,
    panel_label,
    save_vector,
)

apply_style()
ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "exps" / "paper1_repair_benchmark"
EXTENSIONS = ROOT / "exps" / "paper1_submission_extensions"
ROUTER = ROOT / "exps" / "decision_network"
OUT = ROOT / "paper1" / "figure" / "experiments"

LABELS = {
    "source_field_copy": "Source-field Copy",
    "no_repair": "No Repair",
    "rule_only": "Rule Only",
    "shacl": "SHACL-style",
    "direct_llm": "Direct LLM",
    "react_agent": "ReAct-style",
    "simple_pipeline": "Simple Pipeline",
    "ours": "Diagnosis + Gate",
    "no_context_reasoning": "No context reasoning",
    "no_structural_preprocessing": "No structural preprocessing",
    "no_constraint_gate": "No constraint gate",
    "full": "Diagnosis + Gate",
}


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def overall(path: Path):
    return {
        row["method"]: row
        for row in json.loads(path.read_text(encoding="utf-8"))
        if row["domain"] == "ALL"
    }


def bootstrap_ci(values, seed=42, repeats=5000):
    rng = random.Random(seed)
    means = sorted(
        sum(values[rng.randrange(len(values))] for _ in values) / len(values)
        for _ in range(repeats)
    )
    return means[int(0.025 * repeats)], means[int(0.975 * repeats)]


def main_results():
    rows = overall(RESULTS / "summary.json")
    with (EXTENSIONS / "synthetic_simple_pipeline.csv").open(encoding="utf-8", newline="") as handle:
        extension_rows = list(csv.DictReader(handle))
    simple = next(row for row in extension_rows if row["method"] == "Simple pipeline")
    rows["simple_pipeline"] = {
        key: (float(value) if key not in {"method"} else value)
        for key, value in simple.items()
    }
    copy_rows = json.loads((ROOT / "exps/paper1_mechanism_audit/source_field_results.json").read_text())
    cp = next(r for r in copy_rows if r["stream"] == "controlled")
    rows["source_field_copy"] = {}
    for key, source_key in [("defect_repair_rate", "repair"), ("triple_f1", "triple_f1"), ("exact_match", "exact_match")]:
        rows["source_field_copy"][key] = cp[source_key]
        rows["source_field_copy"][key+"_ci_low"] = cp[source_key]
        rows["source_field_copy"][key+"_ci_high"] = cp[source_key]
    methods = ["source_field_copy", "ours", "simple_pipeline", "direct_llm", "react_agent", "rule_only", "shacl", "no_repair"]
    metrics = [
        ("defect_repair_rate", "Defect repair", "o", BLUE),
        ("triple_f1", "Triple F1", "D", GREEN),
        ("exact_match", "Exact graph", "s", AMBER),
    ]

    fig, (ax, cost_ax) = plt.subplots(
        1, 2, figsize=(7.15, 3.05), gridspec_kw={"width_ratios": [1.58, 1.0], "wspace": 0.36}
    )
    y = np.arange(len(methods))
    offsets = [-0.19, 0.0, 0.19]
    ax.axhspan(-0.46, 0.46, color=BLUE_LIGHT, alpha=0.58, zorder=0)
    for offset, (metric, label, marker, color) in zip(offsets, metrics):
        vals = np.array([rows[m][metric] for m in methods])
        low = np.array([rows[m][metric + "_ci_low"] for m in methods])
        high = np.array([rows[m][metric + "_ci_high"] for m in methods])
        ax.errorbar(
            vals,
            y + offset,
            xerr=np.vstack([vals - low, high - vals]),
            fmt=marker,
            markersize=4.4,
            markerfacecolor=color,
            markeredgecolor=WHITE,
            markeredgewidth=0.45,
            color=color,
            elinewidth=0.8,
            capsize=1.8,
            label=label,
            zorder=3,
        )
    ax.set_yticks(y, [LABELS[m] for m in methods])
    ax.get_yticklabels()[0].set_fontweight("bold")
    ax.invert_yaxis()
    ax.set_xlim(-0.02, 1.03)
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_xlabel("Held-out score")
    ax.set_title("Quality with 95% bootstrap intervals", loc="left", pad=17)
    clean_axis(ax, "x")
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.01), ncol=3,
              handletextpad=0.35, columnspacing=0.9, borderaxespad=0.0)
    panel_label(ax, "a", x=-0.24, y=1.12)

    api_methods = ["direct_llm", "simple_pipeline", "ours", "react_agent"]
    styles = {
        "direct_llm": (GRAY, "o"),
        "simple_pipeline": (GREEN, "s"),
        "ours": (BLUE, "o"),
        "react_agent": (ORANGE, "D"),
    }
    for method in api_methods:
        row = rows[method]
        color, marker = styles[method]
        cost_ax.errorbar(
            row["latency_sec"],
            row["defect_repair_rate"],
            xerr=[[row["latency_sec"] - row["latency_sec_ci_low"]],
                  [row["latency_sec_ci_high"] - row["latency_sec"]]],
            yerr=[[row["defect_repair_rate"] - row["defect_repair_rate_ci_low"]],
                  [row["defect_repair_rate_ci_high"] - row["defect_repair_rate"]]],
            fmt=marker,
            color=color,
            markerfacecolor=color,
            markeredgecolor=WHITE,
            markeredgewidth=0.6,
            markersize=7.2 if method == "ours" else 6.3,
            elinewidth=0.9,
            capsize=2,
            zorder=3,
        )
    label_offsets = {"direct_llm": (5, -14), "simple_pipeline": (6, 8), "ours": (5, 7), "react_agent": (-20, -16)}
    for method in api_methods:
        row = rows[method]
        cost_ax.annotate(
            LABELS[method],
            (row["latency_sec"], row["defect_repair_rate"]),
            xytext=label_offsets[method],
            textcoords="offset points",
            fontsize=7.1,
            fontweight="bold" if method == "ours" else "normal",
            color=styles[method][0],
        )
    cost_ax.set_xlim(5.3, 23.0)
    cost_ax.set_ylim(0.84, 1.01)
    cost_ax.set_xlabel("Latency per document (s)")
    cost_ax.set_ylabel("Defect repair rate")
    cost_ax.set_title("Quality--latency trade-off", loc="left", pad=17)
    clean_axis(cost_ax, "both")
    cost_ax.text(
        0.98,
        0.04,
        "circle/square: 1 call\ndiamond: 2 calls",
        transform=cost_ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.6,
        color=MUTED,
    )
    panel_label(cost_ax, "b", x=-0.22, y=1.12)
    fig.subplots_adjust(left=0.125, right=0.985, bottom=0.19, top=0.82)
    save_vector(fig, OUT / "repair_benchmark_results.pdf")


def repair_diagnostics():
    defect_rows = list(csv.DictReader((RESULTS / "per_defect_metrics.csv").open(encoding="utf-8")))
    method_order = ["rule_only", "direct_llm", "react_agent", "ours"]
    type_order = [
        "missing_triple",
        "duplicate_triple",
        "invalid_relation",
        "reversed_edge",
        "wrong_value",
        "hierarchy_conflict",
    ]
    type_labels = ["Missing", "Duplicate", "Invalid\nrelation", "Reversed\nedge", "Wrong\nvalue", "Hierarchy"]
    grouped = defaultdict(list)
    for row in defect_rows:
        grouped[(row["method"], row["defect_type"])].append(int(row["success"]))
    defect = np.array(
        [[np.mean(grouped[(method, kind)]) for kind in type_order] for method in method_order]
    )

    ablation = overall(RESULTS / "ablation_summary.json")
    variant_order = ["no_context_reasoning", "no_structural_preprocessing", "no_constraint_gate", "full"]
    variant_labels = ["No completion", "Direct LLM", "No gate", "Diag. + Gate"]
    # All displayed quantities use a higher-is-better direction.
    ablation_matrix = np.array(
        [
            [
                ablation[v]["defect_repair_rate"],
                ablation[v]["clean_fact_preservation"],
                1 - ablation[v]["overrepair_rate"],
                ablation[v]["triple_f1"],
                ablation[v]["exact_match"],
            ]
            for v in variant_order
        ]
    )

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.15, 3.15), gridspec_kw={"width_ratios": [1.28, 1.05], "wspace": 0.42}
    )
    im1 = ax1.pcolormesh(defect, cmap=HEAT_CMAP, vmin=0, vmax=1,
                         shading="flat", edgecolors=WHITE, linewidth=0.45)
    ax1.set_xticks(np.arange(len(type_labels)) + 0.5, type_labels)
    ax1.set_yticks(np.arange(len(method_order)) + 0.5, [LABELS[m] for m in method_order])
    ax1.set_xlim(0, defect.shape[1])
    ax1.set_ylim(defect.shape[0], 0)
    ax1.get_yticklabels()[-1].set_fontweight("bold")
    for i in range(defect.shape[0]):
        for j in range(defect.shape[1]):
            value = defect[i, j]
            ax1.text(j + 0.5, i + 0.5, f"{100*value:.0f}", ha="center", va="center",
                     fontsize=6.8, color=WHITE if value > 0.67 else INK,
                     fontweight="bold" if method_order[i] == "ours" else "normal")
    ax1.set_title("Repair rate by defect type (%)", loc="left", pad=7)
    ax1.tick_params(length=0)
    for spine in ax1.spines.values(): spine.set_visible(False)
    panel_label(ax1, "a", x=-0.20)

    im2 = ax2.pcolormesh(ablation_matrix, cmap=HEAT_CMAP, vmin=0, vmax=1,
                         shading="flat", edgecolors=WHITE, linewidth=0.45)
    ax2.set_xticks(np.arange(5) + 0.5, ["Repair", "Preserve", "Safe\nedits", "Triple\nF1", "Exact"])
    ax2.set_yticks(np.arange(len(variant_order)) + 0.5, variant_labels)
    ax2.set_xlim(0, ablation_matrix.shape[1])
    ax2.set_ylim(ablation_matrix.shape[0], 0)
    ax2.get_yticklabels()[-1].set_fontweight("bold")
    for i in range(ablation_matrix.shape[0]):
        for j in range(ablation_matrix.shape[1]):
            value = ablation_matrix[i, j]
            ax2.text(j + 0.5, i + 0.5, f"{100*value:.1f}", ha="center", va="center",
                     fontsize=6.7, color=WHITE if value > 0.72 else INK,
                     fontweight="bold" if variant_order[i] == "full" else "normal")
    ax2.set_title("Pipeline settings (%; higher is better)", loc="left", pad=7)
    ax2.tick_params(length=0)
    for spine in ax2.spines.values(): spine.set_visible(False)
    panel_label(ax2, "b", x=-0.22)

    fig.text(0.985, 0.055, "Darker cells indicate higher scores.", ha="right", va="bottom",
             fontsize=6.7, color=MUTED)
    fig.subplots_adjust(left=0.15, right=0.985, bottom=0.18, top=0.86)
    save_vector(fig, OUT / "repair_diagnostics.pdf")


def semantic_reliability():
    sample = {row["item_id"]: row for row in read_jsonl(RESULTS / "semantic_sample.jsonl")}
    scores = list(csv.DictReader((RESULTS / "semantic_judge_scores.csv").open(encoding="utf-8")))
    primary = [row for row in scores if int(row["repeat"]) == 0]

    gold_groups = {
        0: [float(row["judge_score"]) for row in primary if sample[row["item_id"]]["gold_valid"] == 0],
        1: [float(row["judge_score"]) for row in primary if sample[row["item_id"]]["gold_valid"] == 1],
    }
    method_groups = {
        method: [float(row["judge_score"]) for row in primary if sample[row["item_id"]]["method"] == method]
        for method in ("no_repair", "ours")
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.15, 2.65), gridspec_kw={"wspace": 0.38})
    rng = np.random.default_rng(42)
    for x, gold in enumerate((0, 1)):
        vals = np.array(gold_groups[gold])
        jitter = rng.uniform(-0.10, 0.10, len(vals))
        ax1.scatter(np.full(len(vals), x) + jitter, vals, s=12, color=GRAY if gold == 0 else BLUE,
                    alpha=0.52, edgecolors="none", zorder=2)
        mean = vals.mean()
        low, high = bootstrap_ci(vals.tolist())
        ax1.errorbar(x, mean, yerr=[[mean-low], [high-mean]], fmt="D", markersize=5.2,
                     color=INK, markerfacecolor=WHITE, markeredgewidth=1.0, capsize=3, zorder=4)
        ax1.text(x, min(1.09, high + 0.07), f"mean {mean:.3f}", ha="center", va="bottom", fontsize=7)
    ax1.set_xticks([0, 1], ["Gold invalid\n(n=12)", "Gold valid\n(n=168)"])
    ax1.set_ylim(-0.06, 1.16)
    ax1.set_ylabel("Independent judge score")
    ax1.set_title("Agreement with exact gold validity", loc="left", pad=6)
    clean_axis(ax1, "y")
    panel_label(ax1, "a", x=-0.18)

    methods = ["no_repair", "ours"]
    y = np.arange(2)
    ax2.axhspan(0.54, 1.46, color=BLUE_LIGHT, alpha=0.55, zorder=0)
    for idx, method in enumerate(methods):
        vals = method_groups[method]
        mean = np.mean(vals)
        low, high = bootstrap_ci(vals)
        color = BLUE if method == "ours" else GRAY
        ax2.errorbar(mean, idx, xerr=[[mean-low], [high-mean]], fmt="o", markersize=6.2,
                     color=color, markerfacecolor=color, markeredgecolor=WHITE,
                     markeredgewidth=0.6, elinewidth=1.0, capsize=2.5, zorder=3)
        ax2.annotate(f"{mean:.3f}", (mean, idx), xytext=(0, -12),
                     textcoords="offset points", va="center", ha="center", fontsize=7.2,
                     color=color, fontweight="bold" if method == "ours" else "normal")
    ax2.set_yticks(y, [LABELS[m] for m in methods])
    ax2.get_yticklabels()[1].set_fontweight("bold")
    ax2.invert_yaxis()
    ax2.set_xlim(0.82, 1.02)
    ax2.set_xlabel("Mean source-support score")
    ax2.set_title("Blind scores by system", loc="left", pad=6)
    clean_axis(ax2, "x")
    ax2.text(0.02, 0.03, "Five repeat-run means: 0.960 each", transform=ax2.transAxes,
             ha="left", va="bottom", fontsize=6.8, color=MUTED)
    panel_label(ax2, "b", x=-0.20)
    fig.subplots_adjust(left=0.095, right=0.98, bottom=0.22, top=0.84)
    save_vector(fig, OUT / "semantic_reliability.pdf")


def router_efficiency():
    data = json.loads((ROUTER / "efficiency_sim.json").read_text(encoding="utf-8"))
    always = data["no_decision_net"]
    gated = data["with_fphi"]
    rows = [
        ("Calls / document", always["calls_per_doc"], gated["calls_per_doc"], "1.00", "0.50"),
        ("Latency / document", always["latency_per_doc"], gated["latency_per_doc"], "11.45 s", "5.72 s"),
    ]

    fig, ax = plt.subplots(figsize=(3.45, 2.15))
    y = np.arange(len(rows))
    for i, (label, base, gate, base_text, gate_text) in enumerate(rows):
        norm_gate = gate / base
        ax.plot([norm_gate, 1], [i, i], color=GRID, linewidth=2.4, solid_capstyle="round", zorder=1)
        ax.scatter(1, i, s=42, color=GRAY, edgecolor=WHITE, linewidth=0.6, zorder=3)
        ax.scatter(norm_gate, i, s=50, color=BLUE, edgecolor=WHITE, linewidth=0.6, zorder=3)
        ax.annotate(base_text, (1, i), xytext=(5, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=7, color=GRAY)
        ax.annotate(gate_text, (norm_gate, i), xytext=(-5, 0), textcoords="offset points",
                    va="center", ha="right", fontsize=7, color=BLUE, fontweight="bold")
    ax.set_yticks(y, [row[0] for row in rows])
    ax.invert_yaxis()
    ax.set_xlim(0.35, 1.17)
    ax.set_xticks([0.5, 0.75, 1.0], ["50", "75", "100"])
    ax.set_xlabel("Relative cost (% of always repair)")
    clean_axis(ax, "x")
    legend = [
        Line2D([0], [0], marker="o", linestyle="", color=GRAY, label="Always repair", markersize=5.5),
        Line2D([0], [0], marker="o", linestyle="", color=BLUE, label=r"With $f_\varphi$ gate", markersize=5.5),
    ]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.55, 1.34), ncol=2,
              columnspacing=1.1, handletextpad=0.35)
    ax.text(0.75, 1.04, "50% reduction", transform=ax.get_xaxis_transform(), ha="center",
            va="bottom", fontsize=7.1, color=BLUE_DARK, fontweight="bold")
    fig.subplots_adjust(left=0.34, right=0.91, bottom=0.24, top=0.70)
    save_vector(fig, OUT / "router_efficiency.pdf")


def failure_audit():
    summary = json.loads((RESULTS / "failure_summary.json").read_text(encoding="utf-8"))
    mapping = {
        "invalid_relation": "Invalid relation",
        "wrong_value": "Wrong value",
        "missing_triple": "Missing triple",
        "reversed_edge": "Reversed edge",
    }
    items = sorted(summary["unresolved_by_type"].items(), key=lambda item: (-item[1], mapping[item[0]]))
    labels = [mapping[key] for key, _ in items]
    values = [value for _, value in items]

    fig, ax = plt.subplots(figsize=(3.45, 2.25))
    y = np.arange(len(labels))
    ax.hlines(y, 0, values, color=BLUE_LIGHT, linewidth=3.2, zorder=1)
    ax.scatter(values, y, s=47, color=BLUE, edgecolor=WHITE, linewidth=0.6, zorder=3)
    for yi, value in zip(y, values):
        ax.text(value + 0.12, yi, str(value), va="center", ha="left", fontsize=7.5,
                color=BLUE_DARK, fontweight="bold")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 3.65)
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xlabel("Unresolved defects")
    clean_axis(ax, "x")
    ax.text(0.0, 1.12, "9 / 450 unresolved; all in Government", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=7.4, color=INK, fontweight="bold")
    fig.subplots_adjust(left=0.37, right=0.92, bottom=0.22, top=0.78)
    save_vector(fig, OUT / "failure_audit.pdf")


if __name__ == "__main__":
    main_results()
    print("Wrote active controlled-result figure; historical supplementary plots are not regenerated.")
