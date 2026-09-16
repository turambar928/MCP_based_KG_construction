#!/usr/bin/env python3
"""Generate submission figures directly from archived Paper 1 result tables."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "exps" / "paper1_repair_benchmark"
OUT = ROOT / "paper1" / "figure" / "experiments"
OUT.mkdir(parents=True, exist_ok=True)

LABELS = {
    "no_repair": "No Repair",
    "rule_only": "Rule Only",
    "shacl": "SHACL-style",
    "direct_llm": "Direct LLM",
    "react_agent": "ReAct",
    "ours": "Ours",
    "no_context_reasoning": "No context",
    "no_structural_preprocessing": "No structure",
    "no_constraint_gate": "No gate",
    "full": "Full",
}
COLORS = ["#9AA0A6", "#4E79A7", "#76B7B2", "#F28E2B", "#E15759", "#2F6B3C"]


def overall(path: Path):
    return {r["method"]: r for r in json.loads(path.read_text(encoding="utf-8")) if r["domain"] == "ALL"}


def main_results():
    rows = overall(RESULTS / "summary.json")
    methods = ["no_repair", "rule_only", "shacl", "direct_llm", "react_agent", "ours"]
    metrics = [
        ("defect_repair_rate", "Defect repair"),
        ("clean_fact_preservation", "Clean-fact preservation"),
        ("triple_f1", "Triple F1"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.25), sharey=True)
    x = np.arange(len(methods))
    for ax, (metric, title) in zip(axes, metrics):
        values = np.array([rows[m][metric] for m in methods])
        lo = np.array([rows[m][metric + "_ci_low"] for m in methods])
        hi = np.array([rows[m][metric + "_ci_high"] for m in methods])
        ax.bar(x, values, color=COLORS, width=0.72, edgecolor="white", linewidth=0.5)
        ax.errorbar(x, values, yerr=np.vstack([values - lo, hi - values]), fmt="none",
                    ecolor="#202124", elinewidth=0.8, capsize=2)
        ax.set_title(title, fontsize=10)
        ax.set_xticks(x, [LABELS[m] for m in methods], rotation=48, ha="right", fontsize=7.5)
        ax.set_ylim(0, 1.06)
        ax.grid(axis="y", alpha=0.25, linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Score")
    fig.tight_layout(pad=0.8)
    fig.savefig(OUT / "repair_benchmark_results.pdf", bbox_inches="tight")
    plt.close(fig)


def ablation():
    rows = overall(RESULTS / "ablation_summary.json")
    methods = ["no_context_reasoning", "no_structural_preprocessing", "no_constraint_gate", "full"]
    metrics = [
        ("defect_repair_rate", "Repair"),
        ("clean_fact_preservation", "Preservation"),
        ("overrepair_rate", "Over-repair"),
        ("triple_f1", "Triple F1"),
    ]
    x = np.arange(len(methods))
    width = 0.19
    fig, ax = plt.subplots(figsize=(7.4, 3.45))
    palette = ["#4E79A7", "#59A14F", "#E15759", "#F28E2B"]
    for i, (metric, label) in enumerate(metrics):
        values = [rows[m][metric] for m in methods]
        ax.bar(x + (i - 1.5) * width, values, width, label=label, color=palette[i])
    ax.set_xticks(x, [LABELS[m] for m in methods])
    ax.set_ylim(0, 1.06)
    ax.set_ylabel("Score")
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(ncol=4, frameon=False, fontsize=8, loc="upper center")
    fig.tight_layout(pad=0.8)
    fig.savefig(OUT / "repair_ablation.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main_results()
    ablation()
    print("wrote repair_benchmark_results.pdf and repair_ablation.pdf")
