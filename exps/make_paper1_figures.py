# -*- coding: utf-8 -*-
"""
Consolidated figure generator for paper1 §4 (Evaluation).
Renders one professional figure per experiment table, choosing the chart type that fits:
  - degradation rates ............ heatmap          -> degradation_heatmap.pdf
  - comprehensive results ........ grouped bars     -> comprehensive_results.pdf
  - recovery Exp1/2/3 ............ grouped bars     -> enhancement_effect.pdf
  - dimension improvement ........ grouped bars     -> dimension_improvement.pdf
  - single-scale ablation ........ grouped bars     -> ablation_bar.pdf
  - weight sensitivity ........... bar              -> weight_sensitivity.pdf
  - decision-net quality ......... bar (+chance)    -> decision_quality.pdf
  - decision-net efficiency ...... dual-panel bars  -> decision_efficiency.pdf
  - decision-net confusion ....... heatmaps         -> decision_confusion.pdf
  - semantic-score reliability ... scatter + fit    -> sem_reliability_scatter.pdf
  - web-search ablation .......... dual-panel bars  -> websearch_ablation.pdf
  - convergence .................. line             -> convergence.pdf
  - scalability .................. line             -> scalability.pdf
  - failure distribution ......... pie              -> failure_distribution.pdf

All numbers come from experiments.tex tables (hard-coded below) or from the produced
artifact files where available. Output: paper1/figure/experiments/*.pdf
Run:  python3 exps/make_paper1_figures.py
"""
import os
import json
import warnings
import numpy as np
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-kge-paper")
warnings.filterwarnings("ignore", message="Unable to import Axes3D.*")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "paper1", "figure", "experiments")
os.makedirs(OUT, exist_ok=True)

# ---- shared professional style ----
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
    "legend.fontsize": 9.5, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
    "font.family": "DejaVu Sans",
})
DOMAINS = ["Government", "Finance", "Environment", "Average"]
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
BLUE_SERIES = [BLUE["300"], BLUE["400"], BLUE["500"], BLUE["600"], BLUE["700"], BLUE["800"]]
DCOL = {"Government": BLUE["500"], "Finance": BLUE["700"],
        "Environment": BLUE["900"], "Average": BLUE["400"]}
SEQ = "Blues"


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p)
    plt.close(fig)
    print("saved", p)


def grouped_bars(ax, groups, series, data, colors, ylabel, value_fmt="%.1f", rot=0):
    """groups on x; one bar per series within each group. data[series][group]."""
    n = len(series)
    x = np.arange(len(groups))
    w = 0.8 / n
    for i, s in enumerate(series):
        vals = [data[s][g] for g in groups]
        bars = ax.bar(x + (i - (n - 1) / 2) * w, vals, w, label=s,
                      color=colors[i] if isinstance(colors, list) else colors[s],
                      edgecolor="white", linewidth=0.6)
        if value_fmt:
            ax.bar_label(bars, fmt=value_fmt, fontsize=7.5, padding=1.5)
    ax.set_xticks(x); ax.set_xticklabels(groups, rotation=rot)
    ax.set_ylabel(ylabel)
    ax.legend(frameon=False, ncol=min(n, 3))


# ============================================================ 1. degradation heatmap
def fig_degradation():
    issues = ["Field\nMissing", "Info.\nInconsistency", "Terminology\nError",
              "Logical\nContradiction", "Relationship\nError", "Hierarchical\nConflict"]
    doms = ["Government", "Finance", "Environment"]
    M = np.array([
        [26.5, 11.7, 11.6],
        [26.5, 10.2, 10.2],
        [25.6, 11.3, 11.8],
        [27.1, 11.0, 11.8],
        [27.9, 13.2, 9.8],
        [37.6, 21.5, 23.0],
    ])
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    im = ax.imshow(M, cmap=SEQ, aspect="auto", vmin=0, vmax=40)
    ax.set_xticks(range(3)); ax.set_xticklabels(doms)
    ax.set_yticks(range(6)); ax.set_yticklabels(issues)
    for i in range(6):
        for j in range(3):
            ax.text(j, i, f"{M[i,j]:.1f}", ha="center", va="center",
                    color="white" if M[i, j] > 22 else "black", fontsize=9)
    ax.set_title("Injected Degradation Rate (%)")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Degradation rate (%)")
    ax.grid(False)
    save(fig, "degradation_heatmap.pdf")


# ============================================================ 2. comprehensive results
def fig_comprehensive():
    methods = ["Exp2: No Enh.", "Exp7: Rule", "Exp8: LLM", "Exp1: Clean", "Exp3: Ours"]
    data = {
        "Exp2: No Enh.": {"Government": 79.87, "Finance": 70.42, "Environment": 65.25, "Average": 71.85},
        "Exp7: Rule":    {"Government": 81.23, "Finance": 71.15, "Environment": 68.42, "Average": 73.60},
        "Exp8: LLM":     {"Government": 83.45, "Finance": 73.28, "Environment": 72.11, "Average": 76.28},
        "Exp1: Clean":   {"Government": 85.83, "Finance": 76.01, "Environment": 82.88, "Average": 81.57},
        "Exp3: Ours":    {"Government": 87.69, "Finance": 76.07, "Environment": 78.46, "Average": 80.74},
    }
    cols = [BLUE["200"], BLUE["300"], BLUE["500"], BLUE["700"], BLUE["900"]]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    grouped_bars(ax, DOMAINS, methods, data, cols, "Comprehensive Quality $Q_{score}$", "%.1f")
    ax.set_ylim(60, 92)
    ax.set_title("Comprehensive Results Across Methods and Domains")
    save(fig, "comprehensive_results.pdf")


# ============================================================ 3. enhancement effect (Exp1/2/3)
def fig_enhancement():
    series = ["Exp1: Clean (ceiling)", "Exp2: Degraded", "Exp3: Ours (enhanced)"]
    data = {
        "Exp1: Clean (ceiling)": {"Government": 85.83, "Finance": 76.01, "Environment": 82.88, "Average": 81.57},
        "Exp2: Degraded":        {"Government": 79.87, "Finance": 70.42, "Environment": 65.25, "Average": 71.85},
        "Exp3: Ours (enhanced)": {"Government": 87.69, "Finance": 76.07, "Environment": 78.46, "Average": 80.74},
    }
    cols = [BLUE["300"], BLUE["600"], BLUE["900"]]
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    grouped_bars(ax, DOMAINS, series, data, cols, "Comprehensive Quality $Q_{score}$", "%.1f")
    ax.set_ylim(60, 92)
    ax.set_title("Quality Recovery from Degraded Data (Exp1 vs Exp2 vs Exp3)")
    save(fig, "enhancement_effect.pdf")


# ============================================================ 4. dimension improvement
def fig_dimension():
    series = ["Triple Uniqueness (Entity)", "Logical Consistency (Graph)", "Semantic Reasonableness (Context)"]
    doms = ["Government", "Finance", "Environment", "Average"]
    data = {
        "Triple Uniqueness (Entity)":       {"Government": 1.42, "Finance": 11.85, "Environment": 18.77, "Average": 10.68},
        "Logical Consistency (Graph)":      {"Government": 13.66, "Finance": 0.00, "Environment": 11.38, "Average": 8.35},
        "Semantic Reasonableness (Context)":{"Government": 16.23, "Finance": 10.75, "Environment": 22.70, "Average": 16.56},
    }
    cols = [BLUE["400"], BLUE["600"], BLUE["800"]]
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    grouped_bars(ax, doms, series, data, cols, "Score Improvement (Exp3 $-$ Exp2)", "%.1f")
    ax.set_title("Per-Dimension Quality Improvement")
    save(fig, "dimension_improvement.pdf")


# ============================================================ 5. ablation single-scale
def fig_ablation():
    series = ["Exp2: None", "Exp4: Entity", "Exp5: Graph", "Exp6: Context", "Exp3: Full"]
    data = {
        "Exp2: None":    {"Government": 79.87, "Finance": 70.42, "Environment": 65.25, "Average": 71.85},
        "Exp4: Entity":  {"Government": 82.15, "Finance": 73.84, "Environment": 70.38, "Average": 75.46},
        "Exp5: Graph":   {"Government": 84.21, "Finance": 70.42, "Environment": 71.67, "Average": 75.43},
        "Exp6: Context": {"Government": 85.34, "Finance": 74.15, "Environment": 75.82, "Average": 78.44},
        "Exp3: Full":    {"Government": 87.69, "Finance": 76.07, "Environment": 78.46, "Average": 80.74},
    }
    cols = [BLUE["200"], BLUE["300"], BLUE["500"], BLUE["700"], BLUE["900"]]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    grouped_bars(ax, DOMAINS, series, data, cols, "Comprehensive Quality $Q_{score}$", "%.1f")
    ax.set_ylim(60, 92)
    ax.set_title("Single-Scale Ablation vs Full System")
    save(fig, "ablation_bar.pdf")


# ============================================================ 6. weight sensitivity
def fig_weight():
    schemes = ["Equal\n(default)", "Logic-\nheavy", "Semantic-\nheavy", "Structural-\nlight", "Balanced\nalt."]
    vals = [80.74, 84.41, 81.73, 84.23, 81.90]
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    cols = [BLUE["900"], BLUE["300"], BLUE["400"], BLUE["500"], BLUE["700"]]
    bars = ax.bar(schemes, vals, color=cols, edgecolor="white")
    ax.bar_label(bars, fmt="%.2f", fontsize=9, padding=2)
    ax.axhline(80.74, ls="--", color=BLUE["800"], lw=1, alpha=0.7)
    ax.set_ylim(78, 86); ax.set_ylabel("Average $Q_{score}$")
    ax.set_title("Weight-Scheme Sensitivity (equal-weight is the most conservative)")
    save(fig, "weight_sensitivity.pdf")


# ============================================================ 7. decision-network quality
def fig_decision_quality():
    labels = ["$p_{repair}$\nAccuracy", "$p_{repair}$\nF1", "$\\pi$ top-1", "$\\pi$ macro-F1"]
    vals = [0.796, 0.787, 0.494, 0.376]
    cols = [BLUE["500"], BLUE["700"], BLUE["500"], BLUE["700"]]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    bars = ax.bar(labels, vals, color=cols, edgecolor="white")
    ax.bar_label(bars, fmt="%.3f", fontsize=9, padding=2)
    ax.axhline(0.33, ls="--", color="gray", lw=1)
    ax.text(3.4, 0.345, "3-way chance 0.33", fontsize=8, color="gray", ha="right")
    ax.set_ylim(0, 1.0); ax.set_ylabel("Score")
    ax.set_title("Decision Network $f_\\phi$ Prediction Quality")
    save(fig, "decision_quality.pdf")


# ============================================================ 8. decision-network efficiency
def fig_decision_efficiency():
    cfgs = ["No decision net\n(always repair)", "Full\n(with $f_\\phi$)"]
    Q = [80.74, 79.64]; calls = [1.00, 0.46]; lat = [2.80, 1.28]
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.8))
    for ax, (vals, title, ylab, fmt) in zip(axes, [
        (Q, "Quality", "$Q_{score}$", "%.2f"),
        (calls, "LLM calls / doc", "calls", "%.2f"),
        (lat, "Latency / doc", "seconds", "%.2f")]):
        bars = ax.bar(cfgs, vals, color=[BLUE["400"], BLUE["800"]], edgecolor="white", width=0.6)
        ax.bar_label(bars, fmt=fmt, fontsize=9, padding=2)
        ax.set_title(title); ax.set_ylabel(ylab)
    axes[0].set_ylim(78, 82)
    fig.suptitle("Effect of the Decision Network on Quality and Cost (54% fewer calls)", y=1.02)
    save(fig, "decision_efficiency.pdf")


# ============================================================ 9. decision confusion matrices
def fig_decision_confusion():
    try:
        P = dict(np.load(os.path.join(HERE, "decision_network", "fphi_model.npz")))
        sc = json.load(open(os.path.join(HERE, "decision_network", "scaler.json")))
        sp = json.load(open(os.path.join(HERE, "decision_network", "splits.json")))
        import pandas as pd
        df = pd.read_csv(os.path.join(HERE, "decision_network", "dataset.csv"))
        df["n_viol_feat"] = df[["n_missing", "n_dup", "n_logconf"]].sum(axis=1)
        df = df.dropna(subset=["S_sem"]).reset_index(drop=True)
        feats, mu, sd = sc["features"], np.array(sc["mu"]), np.array(sc["sd"])
        SCALES = sc["scales"]
        X = (df[feats].to_numpy(float) - mu) / sd
        relu = lambda z: np.maximum(0, z)
        a1 = relu(X @ P["W1"] + P["b1"]); a2 = relu(a1 @ P["W2"] + P["b2"])
        pr = 1 / (1 + np.exp(-(a2 @ P["wr"] + P["br"]).ravel()))
        ps = a2 @ P["Ws"] + P["bs"]
        te = sp["test"]
        yr = df["y_repair"].to_numpy(int)
        pred = (pr >= 0.4).astype(int)
        cm = np.zeros((2, 2), int)
        for i in te:
            cm[yr[i], pred[i]] += 1
        sidx = df["scale_label"].map({s: i for i, s in enumerate(SCALES)}).fillna(-1).to_numpy().astype(int)
        te_d = [i for i in te if sidx[i] >= 0]
        pscale = ps[te_d].argmax(1)
        cm3 = np.zeros((3, 3), int)
        for k, i in enumerate(te_d):
            cm3[sidx[i], pscale[k]] += 1

        fig, (a, b) = plt.subplots(1, 2, figsize=(9.2, 4.0))
        for ax, M, ticks, title in [
            (a, cm, ["skip", "repair"], "Repair trigger $p_{repair}$"),
            (b, cm3, SCALES, "Scale-prior $\\pi$ (top-1)")]:
            im = ax.imshow(M, cmap="Blues")
            ax.set_xticks(range(len(ticks))); ax.set_xticklabels(ticks, rotation=20)
            ax.set_yticks(range(len(ticks))); ax.set_yticklabels(ticks)
            ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title(title)
            for i in range(M.shape[0]):
                for j in range(M.shape[1]):
                    ax.text(j, i, M[i, j], ha="center", va="center",
                            color="white" if M[i, j] > M.max() * 0.5 else "black")
            ax.grid(False)
        fig.suptitle("Decision Network Confusion Matrices (held-out test)", y=1.02)
        save(fig, "decision_confusion.pdf")
    except Exception as e:
        print("skip decision_confusion:", e)


# ============================================================ 10. semantic reliability scatter
def fig_sem_scatter():
    import pandas as pd
    f = os.path.join(HERE, "semantic_reliability", "rescored_triples.csv")
    if not os.path.exists(f):
        print("skip sem scatter (no file)"); return
    d = pd.read_csv(f).dropna(subset=["qwen_score", "gemma_score"])
    x, y = d["qwen_score"].to_numpy(), d["gemma_score"].to_numpy()
    r = np.corrcoef(x, y)[0, 1]
    # jitter for overlapping discrete points
    xj = x + np.random.default_rng(0).normal(0, 0.012, len(x))
    yj = y + np.random.default_rng(1).normal(0, 0.012, len(y))
    cmap = {"government": BLUE["500"], "finance": BLUE["700"], "environment": BLUE["900"]}
    fig, ax = plt.subplots(figsize=(5.4, 5.0))
    for dom, c in cmap.items():
        m = d["domain"].to_numpy() == dom
        ax.scatter(xj[m], yj[m], s=22, alpha=0.6, color=c, label=dom.capitalize(), edgecolor="none")
    a, b = np.polyfit(x, y, 1)
    xs = np.array([0, 1]); ax.plot(xs, a * xs + b, color=BLUE["900"], lw=1.4, label=f"fit (r={r:.2f})")
    ax.plot([0, 1], [0, 1], ls=":", color="gray", lw=1, label="y = x")
    ax.set_xlabel("Qwen-32B $S_{sem}$ (per triple)")
    ax.set_ylabel("Independent judge (Gemma-4-26B)")
    ax.set_title("Semantic-Score Agreement with an Independent Judge")
    ax.legend(frameon=False, loc="upper left"); ax.set_xlim(-0.05, 1.05); ax.set_ylim(-0.05, 1.05)
    save(fig, "sem_reliability_scatter.pdf")


# ============================================================ 11. web-search ablation
def fig_websearch():
    cfgs = ["Full\n(search on)", "No-Search\n(LLM only)", "Offline\n(cached)"]
    Q = [87.69, 85.41, 87.52]; lat = [4.2, 2.8, 1.3]; calls = [3.1, 0.0, 0.0]
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.8))
    for ax, (vals, title, ylab, fmt, ylim) in zip(axes, [
        (Q, "Quality", "$Q_{score}$", "%.2f", (84, 89)),
        (lat, "Latency / doc", "seconds", "%.1f", None),
        (calls, "Search calls / doc", "calls", "%.1f", None)]):
        bars = ax.bar(cfgs, vals, color=[BLUE["400"], BLUE["700"], BLUE["900"]], edgecolor="white", width=0.65)
        ax.bar_label(bars, fmt=fmt, fontsize=9, padding=2)
        ax.set_title(title); ax.set_ylabel(ylab)
        if ylim: ax.set_ylim(*ylim)
    fig.suptitle("Web-Search Completion: Quality vs Cost (Government Domain)", y=1.02)
    save(fig, "websearch_ablation.pdf")


# ============================================================ 12. convergence line
def fig_convergence():
    f = os.path.join(HERE, "convergence.json")
    traj = json.load(open(f)) if os.path.exists(f) else {
        "Government": [79.867, 83.281, 83.636, 87.694, 87.694],
        "Finance": [70.421, 70.421, 73.385, 76.073, 76.073],
        "Environment": [65.246, 68.09, 72.783, 78.457, 78.457]}
    mk = {"Government": "o-", "Finance": "s-", "Environment": "^-"}
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for name, qs in traj.items():
        ax.plot(range(len(qs)), qs, mk.get(name, "o-"), color=DCOL[name],
                label=name, lw=2, ms=6)
    ax.set_xlabel("Iteration"); ax.set_ylabel("Comprehensive Quality $Q_{score}$")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title("Per-Iteration Convergence (plateaus by iteration 3, $T\\leq5$)")
    ax.legend(frameon=False)
    save(fig, "convergence.pdf")


# ============================================================ 13. scalability line
def fig_scalability():
    f = os.path.join(HERE, "scalability.json")
    if os.path.exists(f):
        rows = json.load(open(f))["rows"]
        tri = [r["triples"] for r in rows]; rt = [r["runtime_s"] for r in rows]
        mspt = [r["ms_per_triple"] for r in rows]
    else:
        tri = [2520, 6301, 12602, 18903, 25205]; rt = [0.152, 0.366, 0.775, 1.134, 1.532]
        mspt = [0.060, 0.058, 0.062, 0.060, 0.061]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(tri, rt, "o-", color=BLUE["700"], lw=2, ms=6, label="Total runtime")
    # linear reference through origin and last point
    k = rt[-1] / tri[-1]
    ax.plot([0, tri[-1]], [0, k * tri[-1]], ls="--", color="gray", lw=1, label="linear reference")
    ax.set_xlabel("Number of triples $|E|$"); ax.set_ylabel("Assessment runtime (s)")
    ax.set_title("Scalability: Runtime vs KG Size (near-linear)")
    ax2 = ax.twinx()
    ax2.plot(tri, mspt, "s:", color=BLUE["900"], lw=1.3, ms=5, label="ms / triple")
    ax2.set_ylabel("ms per triple", color=BLUE["900"]); ax2.set_ylim(0, 0.12)
    ax2.tick_params(axis="y", colors=BLUE["900"]); ax2.grid(False); ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")
    save(fig, "scalability.pdf")


# ============================================================ 14. failure distribution pie
def fig_failure():
    labels = ["Domain-specific\njargon (42%)", "Implicit\nhierarchy (28%)",
              "Temporal\nreasoning (18%)", "Low-context\nambiguity (12%)"]
    sizes = [42, 28, 18, 12]
    cols = [BLUE["300"], BLUE["500"], BLUE["700"], BLUE["900"]]
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    ax.pie(sizes, labels=labels, colors=cols, autopct="%d%%", startangle=90,
           wedgeprops=dict(edgecolor="white", linewidth=1.5), textprops={"fontsize": 9.5},
           pctdistance=0.75)
    ax.set_title("Failure-Case Distribution (150 uncorrected defects)")
    ax.grid(False)
    save(fig, "failure_distribution.pdf")


if __name__ == "__main__":
    fig_degradation()
    fig_comprehensive()
    fig_enhancement()
    fig_dimension()
    fig_ablation()
    fig_weight()
    fig_decision_quality()
    fig_decision_efficiency()
    fig_decision_confusion()
    fig_sem_scatter()
    fig_websearch()
    fig_convergence()
    fig_scalability()
    fig_failure()
    print("\nAll figures written to", OUT)
