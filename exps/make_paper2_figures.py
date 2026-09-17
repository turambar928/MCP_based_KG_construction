#!/usr/bin/env python3
"""Generate Paper 2 figures from archived result artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper2" / "figure" / "experiments"


def configure() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman"],
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def rule_quantity() -> None:
    comparison = json.loads((ROOT / "data" / "rule_comparison_report" / "comparison_data.json").read_text())
    generated = json.loads((ROOT / "data" / "rule_suggestions" / "aggregated_rules.json").read_text())
    quantity = comparison["rule_quantity_comparison"]
    labels = ["Entity type", "Relation type", "Hierarchical", "Procedural"]
    expert = [quantity["expert_entity_types"], quantity["expert_relationship_types"], 0, 0]
    automatic = [
        quantity["generated_entity_types"],
        quantity["generated_relationship_types"],
        len(generated["hierarchy_rules"]),
        len(generated["procedural_rules"]),
    ]
    x = np.arange(len(labels))
    width = 0.34
    fig, ax = plt.subplots(figsize=(6.8, 3.15))
    bars_a = ax.bar(x - width / 2, expert, width, label="Expert", color="#6B7280")
    bars_b = ax.bar(x + width / 2, automatic, width, label="Auto-generated", color="#2F6BDE")
    for bars in (bars_a, bars_b):
        for bar in bars:
            if bar.get_height() > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 1.2,
                    f"{int(bar.get_height())}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
    ax.set_ylabel("Rule count")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 98)
    ax.grid(axis="y", color="#d9d9d9", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "rule_quantity.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    configure()
    rule_quantity()


if __name__ == "__main__":
    main()
