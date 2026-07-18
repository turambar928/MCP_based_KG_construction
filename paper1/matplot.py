# -*- coding: utf-8 -*-
"""
Generate experiment figures for the KG quality-enhancement paper.

Run:
    python3 paper1/matplot.py

The script regenerates all figures whose values are fully reported in
sections/experiments.tex. Figures that require unavailable raw instance-level
data, such as semantic-score scatter points and decision-confusion matrices,
are intentionally not synthesized here.
"""

import os
import warnings

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-kge-paper")
warnings.filterwarnings("ignore", message="Unable to import Axes3D.*")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(ROOT, "figure", "experiments")
os.makedirs(OUTDIR, exist_ok=True)

DOMAINS = ["Government", "Finance", "Environment"]

# Monochrome blue palette. Series are distinguished by shade and marker/position,
# not by unrelated hues, so all figures read as one visual system.
BLUE = {
    "50": "#EFF6FF",
    "100": "#DBEAFE",
    "200": "#BFDBFE",
    "300": "#93C5FD",
    "400": "#60A5FA",
    "500": "#3B82F6",
    "600": "#2563EB",
    "700": "#1D4ED8",
    "800": "#1E40AF",
    "900": "#1E3A8A",
}
COLORS = {
    "gray": "#6B7280",
    "light_gray": "#D1D5DB",
    "text": "#111827",
}

SERIES_COLORS = [
    BLUE["300"],
    BLUE["400"],
    BLUE["500"],
    BLUE["600"],
    BLUE["700"],
    BLUE["800"],
]

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
        "font.size": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "figure.dpi": 160,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


# --------------------------------------------------------------------------- #
# Data reported in experiments.tex
# --------------------------------------------------------------------------- #

DEGRADATION_ROWS = [
    "Field\nMissing",
    "Info.\nIncons.",
    "Terminology\nError",
    "Logical\nContrad.",
    "Relation\nError",
    "Hierarchy\nConflict",
]
DEGRADATION = np.array(
    [
        [26.5, 11.7, 11.6],
        [26.5, 10.2, 10.2],
        [25.6, 11.3, 11.8],
        [27.1, 11.0, 11.8],
        [27.9, 13.2, 9.8],
        [37.6, 21.5, 23.0],
    ]
)

COMPREHENSIVE = {
    "Clean Ref. (Exp1)": [85.83, 76.01, 82.88],
    "Degraded (Exp2)": [79.87, 70.42, 65.25],
    "Rules (Exp7)": [81.23, 71.15, 68.42],
    "LLM (Exp8)": [83.45, 73.28, 72.11],
    "Full Repair (Exp3)": [87.69, 76.07, 78.46],
}

RECOVERY = {
    "Clean Ref.": COMPREHENSIVE["Clean Ref. (Exp1)"],
    "Degraded": COMPREHENSIVE["Degraded (Exp2)"],
    "Full Repair": COMPREHENSIVE["Full Repair (Exp3)"],
}

DIM_LABELS = [
    "Triple\nUniqueness",
    "Logical\nConsistency",
    "Semantic\nReasonableness",
]
DIM_IMPROVEMENT = np.array(
    [
        [1.42, 11.85, 18.77],
        [13.66, 0.00, 11.38],
        [16.23, 10.75, 22.70],
    ]
)

ABLATION = {
    "No Enh.": [79.87, 70.42, 65.25],
    "Entity": [82.15, 73.84, 70.38],
    "Graph": [84.21, 70.42, 71.67],
    "Context": [85.34, 74.15, 75.82],
    "Full": [87.69, 76.07, 78.46],
}

WEIGHT_SCHEMES = ["Equal", "Logic-heavy", "Semantic-heavy", "Struct.-light", "Balanced"]
WEIGHT_Q = [80.74, 84.41, 81.73, 84.23, 81.90]

DECISION_QUALITY = {
    "Repair trigger": [0.796, 0.787],
    "Scale prior": [0.494, 0.376],
}

DECISION_EFFICIENCY = {
    "Deployment gate": {"q": 79.64, "calls": 0.46, "latency": 1.28},
    "Full repair": {"q": 80.74, "calls": 1.00, "latency": 2.80},
}

WEBSEARCH = {
    "Full search": {"q": 87.69, "latency": 4.2, "calls": 3.1},
    "No search": {"q": 85.41, "latency": 2.8, "calls": 0.0},
    "Cached": {"q": 87.52, "latency": 1.3, "calls": 0.0},
}

CONVERGENCE = {
    "Government": [79.87, 83.28, 83.64, 87.69],
    "Finance": [70.42, 70.42, 73.39, 76.07],
    "Environment": [65.25, 68.09, 72.78, 78.46],
}

SCALABILITY_TRIPLES = np.array([2520, 6301, 12602, 18903, 25205])
SCALABILITY_RUNTIME = np.array([0.152, 0.366, 0.775, 1.134, 1.532])

FAILURE = {
    "Domain jargon": 42,
    "Implicit hierarchy": 28,
    "Temporal reasoning": 18,
    "Low-context ambiguity": 12,
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _save(fig, name):
    pdf = os.path.join(OUTDIR, f"{name}.pdf")
    fig.savefig(pdf)
    plt.close(fig)
    print(f"  -> {pdf}")


def _grid(ax, axis="y"):
    ax.grid(axis=axis, linestyle="--", linewidth=0.5, alpha=0.35, color=COLORS["gray"])
    ax.set_axisbelow(True)


def _blue_shades(n, start=300, stop=800):
    keys = ["100", "200", "300", "400", "500", "600", "700", "800", "900"]
    start_i = keys.index(str(start))
    stop_i = keys.index(str(stop))
    idx = np.linspace(start_i, stop_i, n).round().astype(int)
    return [BLUE[keys[i]] for i in idx]


def _bar_labels(ax, bars, fmt="{:.1f}", dy=0.6, fontsize=7, rotation=0):
    ymax = ax.get_ylim()[1]
    for bar in bars:
        h = bar.get_height()
        y = min(h + dy, ymax - 0.8)
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            fmt.format(h),
            ha="center",
            va="bottom",
            fontsize=fontsize,
            rotation=rotation,
            clip_on=False,
        )


def _grouped_bars(ax, data, colors, width=0.18, label_values=False, ylim=None):
    labels = list(data.keys())
    values = np.array(list(data.values()))
    x = np.arange(values.shape[1])
    offsets = (np.arange(len(labels)) - (len(labels) - 1) / 2) * width

    for i, label in enumerate(labels):
        bars = ax.bar(
            x + offsets[i],
            values[i],
            width,
            label=label,
            color=colors[i],
            edgecolor="white",
            linewidth=0.5,
        )
        if label_values:
            _bar_labels(ax, bars, fontsize=6.4, rotation=90 if len(labels) > 3 else 0)

    ax.set_xticks(x)
    ax.set_xticklabels(DOMAINS)
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_ylabel(r"$Q_{score}$")
    _grid(ax)
    return labels


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #


def plot_degradation_heatmap():
    fig, ax = plt.subplots(figsize=(4.7, 3.5))
    im = ax.imshow(DEGRADATION, cmap="Blues", aspect="auto", vmin=0, vmax=40)

    ax.set_xticks(np.arange(len(DOMAINS)))
    ax.set_xticklabels(DOMAINS)
    ax.set_yticks(np.arange(len(DEGRADATION_ROWS)))
    ax.set_yticklabels(DEGRADATION_ROWS)

    threshold = 24
    for r in range(DEGRADATION.shape[0]):
        for c in range(DEGRADATION.shape[1]):
            val = DEGRADATION[r, c]
            ax.text(
                c,
                r,
                f"{val:.1f}",
                ha="center",
                va="center",
                fontsize=7.5,
                color="white" if val >= threshold else "black",
            )

    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cbar.set_label("Injected rate (%)", fontsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    _save(fig, "degradation_heatmap")


def plot_comprehensive_results():
    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    _grouped_bars(
        ax,
        COMPREHENSIVE,
        SERIES_COLORS[:5],
        width=0.15,
        label_values=True,
        ylim=(60, 92),
    )
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.18),
        ncol=3,
        frameon=False,
        columnspacing=1.0,
        handlelength=1.4,
    )
    _save(fig, "comprehensive_results")


def plot_enhancement_effect():
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    _grouped_bars(
        ax,
        RECOVERY,
        _blue_shades(3, 300, 800),
        width=0.22,
        label_values=True,
        ylim=(55, 93),
    )
    ax.legend(loc="lower right", frameon=False)
    _save(fig, "enhancement_effect")


def plot_dimension_improvement():
    # Heatmap avoids the legend/annotation overlap that occurred in the grouped
    # bar version of this figure.
    avg = DIM_IMPROVEMENT.mean(axis=1, keepdims=True)
    data = np.hstack([DIM_IMPROVEMENT, avg])
    cols = DOMAINS + ["Average"]

    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    im = ax.imshow(data, cmap="Blues", aspect="auto", vmin=0, vmax=23)

    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols)
    ax.set_yticks(np.arange(len(DIM_LABELS)))
    ax.set_yticklabels(DIM_LABELS)

    threshold = 13
    for r in range(data.shape[0]):
        for c in range(data.shape[1]):
            val = data[r, c]
            ax.text(
                c,
                r,
                f"+{val:.1f}",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if val >= threshold else "black",
            )

    ax.axvline(len(DOMAINS) - 0.5, color="white", linewidth=1.6)
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cbar.set_label("Improvement (Exp3 - Exp2)", fontsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    _save(fig, "dimension_improvement")


def plot_ablation_bar():
    fig, ax = plt.subplots(figsize=(6.7, 3.4))
    _grouped_bars(
        ax,
        ABLATION,
        SERIES_COLORS[:5],
        width=0.15,
        label_values=True,
        ylim=(60, 91),
    )
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.16),
        ncol=5,
        frameon=False,
        columnspacing=0.9,
        handlelength=1.2,
    )
    _save(fig, "ablation_bar")


def plot_weight_sensitivity():
    fig, ax = plt.subplots(figsize=(5.8, 3.1))
    x = np.arange(len(WEIGHT_SCHEMES))
    bars = ax.bar(x, WEIGHT_Q, color=_blue_shades(len(WEIGHT_SCHEMES), 300, 800), edgecolor="white", linewidth=0.5)
    _bar_labels(ax, bars, fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(WEIGHT_SCHEMES, rotation=18, ha="right")
    ax.set_ylabel(r"Average $Q_{score}$")
    ax.set_ylim(78, 86)
    _grid(ax)
    _save(fig, "weight_sensitivity")


def plot_decision_quality():
    fig, ax = plt.subplots(figsize=(4.7, 3.0))
    labels = list(DECISION_QUALITY.keys())
    vals = np.array(list(DECISION_QUALITY.values()))
    x = np.arange(len(labels))
    width = 0.28
    b1 = ax.bar(x - width / 2, vals[:, 0], width, label="Accuracy", color=BLUE["500"])
    b2 = ax.bar(x + width / 2, vals[:, 1], width, label="F1", color=BLUE["800"])
    _bar_labels(ax, b1, fmt="{:.2f}", dy=0.025, fontsize=7)
    _bar_labels(ax, b2, fmt="{:.2f}", dy=0.025, fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 0.95)
    ax.set_ylabel("Score")
    ax.legend(loc="upper right", frameon=False)
    _grid(ax)
    _save(fig, "decision_quality")


def plot_decision_efficiency():
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 3.0), gridspec_kw={"wspace": 0.35})
    labels = list(DECISION_EFFICIENCY.keys())
    q = [DECISION_EFFICIENCY[k]["q"] for k in labels]
    calls = [DECISION_EFFICIENCY[k]["calls"] for k in labels]
    latency = [DECISION_EFFICIENCY[k]["latency"] for k in labels]

    x = np.arange(len(labels))
    bars = axes[0].bar(x, q, color=_blue_shades(2, 400, 800))
    _bar_labels(axes[0], bars, fontsize=7)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(["Gate", "Full"])
    axes[0].set_ylabel(r"$Q_{score}$")
    axes[0].set_ylim(76, 82)
    _grid(axes[0])

    width = 0.28
    b1 = axes[1].bar(x - width / 2, calls, width, label="LLM calls/doc", color=BLUE["500"])
    b2 = axes[1].bar(x + width / 2, latency, width, label="Latency/doc (s)", color=BLUE["800"])
    _bar_labels(axes[1], b1, fmt="{:.2f}", dy=0.05, fontsize=7)
    _bar_labels(axes[1], b2, fmt="{:.1f}", dy=0.05, fontsize=7)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(["Gate", "Full"])
    axes[1].set_ylim(0, 3.2)
    axes[1].legend(loc="upper left", frameon=False)
    _grid(axes[1])
    _save(fig, "decision_efficiency")


def plot_websearch_ablation():
    fig, axes = plt.subplots(1, 3, figsize=(6.8, 2.85), gridspec_kw={"wspace": 0.38})
    labels = list(WEBSEARCH.keys())
    q = [WEBSEARCH[k]["q"] for k in labels]
    latency = [WEBSEARCH[k]["latency"] for k in labels]
    calls = [WEBSEARCH[k]["calls"] for k in labels]
    tick_labels = ["Full", "No search", "Cached"]
    x = np.arange(len(labels))

    panels = [
        (q, r"$Q_{score}$", (84.5, 88.4), "{:.2f}", 0.08, BLUE["400"]),
        (latency, "Latency/doc (s)", (0, 4.9), "{:.1f}", 0.10, BLUE["600"]),
        (calls, "Search calls/doc", (0, 3.7), "{:.1f}", 0.08, BLUE["800"]),
    ]
    width = 0.52
    for ax, (values, ylabel, ylim, fmt, dy, color) in zip(axes, panels):
        bars = ax.bar(
            x,
            values,
            width,
            color=color,
            edgecolor="white",
            linewidth=0.6,
        )
        _bar_labels(ax, bars, fmt=fmt, dy=dy, fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(tick_labels, rotation=18, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.margins(x=0.08)
        _grid(ax)
    _save(fig, "websearch_ablation")


def plot_convergence():
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    markers = ["o", "s", "^"]
    for i, (domain, vals) in enumerate(CONVERGENCE.items()):
        ax.plot(
            np.arange(len(vals)),
            vals,
            marker=markers[i],
            color=SERIES_COLORS[i + 2],
            linewidth=1.6,
            markersize=4.5,
            label=domain,
        )
    ax.set_xlabel("Iteration")
    ax.set_ylabel(r"$Q_{score}$")
    ax.set_xticks(np.arange(4))
    ax.set_ylim(64, 90)
    ax.legend(loc="lower right", frameon=False)
    _grid(ax)
    _save(fig, "convergence")


def plot_scalability():
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    ax.plot(
        SCALABILITY_TRIPLES / 1000,
        SCALABILITY_RUNTIME,
        color=BLUE["700"],
        marker="o",
        linewidth=1.6,
        markersize=4.5,
    )
    ax.set_xlabel("Triples (thousands)")
    ax.set_ylabel("Runtime (s)")
    ax.set_ylim(0, 1.7)
    _grid(ax)
    _save(fig, "scalability")


def plot_failure_distribution():
    fig, ax = plt.subplots(figsize=(5.3, 3.0))
    labels = list(FAILURE.keys())
    values = list(FAILURE.values())
    y = np.arange(len(labels))
    bars = ax.barh(y, values, color=_blue_shades(len(labels), 300, 800))
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Share of residual failures (%)")
    ax.set_xlim(0, 48)
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.8, bar.get_y() + bar.get_height() / 2, f"{w:.0f}%", va="center", fontsize=7.5)
    _grid(ax, axis="x")
    _save(fig, "failure_distribution")


def main():
    jobs = [
        ("degradation_heatmap", plot_degradation_heatmap),
        ("comprehensive_results", plot_comprehensive_results),
        ("enhancement_effect", plot_enhancement_effect),
        ("dimension_improvement", plot_dimension_improvement),
        ("ablation_bar", plot_ablation_bar),
        ("weight_sensitivity", plot_weight_sensitivity),
        ("decision_quality", plot_decision_quality),
        ("decision_efficiency", plot_decision_efficiency),
        ("websearch_ablation", plot_websearch_ablation),
        ("convergence", plot_convergence),
        ("scalability", plot_scalability),
        ("failure_distribution", plot_failure_distribution),
    ]
    print("Generating experiment figures in:", OUTDIR)
    for i, (name, fn) in enumerate(jobs, start=1):
        print(f"[{i}/{len(jobs)}] {name}")
        fn()
    print("Done.")
    print("Note: sem_reliability_scatter.pdf and decision_confusion.pdf require raw data and are not regenerated.")


if __name__ == "__main__":
    main()
