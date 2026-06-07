# -*- coding: utf-8 -*-
"""
论文配图生成脚本 (Constraint-Driven Multi-Scale KG Quality Enhancement)
================================================================================
直接运行 `python3 matplot.py` 会在 figure/experiments/ 下生成全部 PDF。
每个函数对应 experiments.tex 里的一个图占位符，文件名与 \includegraphics 一致。

图型分配（回答“哪个图适合什么类型”）：
  - enhancement_effect   分组柱状图  : Exp1/2/3 跨三域恢复对比（离散配置→柱状）
  - dimension_improvement 热力图     : 3维度×3域改进矩阵（凸显 Finance-Logic=0 模式）
  - ablation_bar         分组柱状图  : 5种尺度配置×3域（多离散配置→柱状）
  - failure_distribution 饼图        : 4类失败占比，和为100%（占比→饼图）
  - convergence          折线图      : Q vs 迭代次数（趋势→折线；数据为 TODO 占位）

所有数值均取自 experiments.tex 中已报告的真实结果；convergence 的数据是占位，
等你拿到“每域每次迭代的 Q 值”后替换 CONVERGENCE 字典即可。
"""

import os
import matplotlib
matplotlib.use("Agg")  # 无显示环境，仅出文件
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------------------------------------------- #
# 全局样式（期刊风格：serif、细线、白底）
# --------------------------------------------------------------------------- #
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
})

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figure", "experiments")
os.makedirs(OUTDIR, exist_ok=True)

DOMAINS = ["Government", "Finance", "Environment"]

# 配色（色盲友好，五档够用）
C_EXP1 = "#4C72B0"   # 蓝  - clean baseline
C_EXP2 = "#C44E52"   # 红  - degraded
C_EXP3 = "#55A868"   # 绿  - full system
C_ENTITY = "#8172B3"
C_GRAPH = "#CCB974"
C_CONTEXT = "#64B5CD"

# --------------------------------------------------------------------------- #
# 真实数据（来自 experiments.tex，请勿随意改动）
# --------------------------------------------------------------------------- #

# tab:comprehensive_results —— Exp1 / Exp2 / Exp3
COMPREHENSIVE = {
    "Exp1 (Clean)":        [85.83, 76.01, 82.88],
    "Exp2 (Degraded)":     [79.87, 70.42, 65.25],
    "Exp3 (Full System)":  [87.69, 76.07, 78.46],
}

# tab:dimension_improvement —— Exp3 vs Exp2，行=维度，列=域
DIM_LABELS = ["Triple Uniqueness\n(Entity)",
              "Logical Consistency\n(Graph)",
              "Semantic Reason.\n(Context)"]
DIM_IMPROVEMENT = np.array([
    [1.42, 11.85, 18.77],   # Triple Uniqueness
    [13.66, 0.00, 11.38],   # Logical Consistency
    [16.23, 10.75, 22.70],  # Semantic Reasonableness
])

# tab:ablation_single —— 单尺度消融
ABLATION = {
    "No Enh. (Exp2)":   [79.87, 70.42, 65.25],
    "Entity (Exp4)":    [82.15, 73.84, 70.38],
    "Graph (Exp5)":     [84.21, 70.42, 71.67],
    "Context (Exp6)":   [85.34, 74.15, 75.82],
    "Full (Exp3)":      [87.69, 76.07, 78.46],
}

# tab:failure_mapping —— 失败模式占比
FAILURE = {
    "Domain-specific jargon": 42,
    "Implicit hierarchy":     28,
    "Temporal reasoning":     18,
    "Low-context ambiguity":  12,
}

# fig:convergence —— TODO: 占位数据！换成每域每次迭代的真实 Q 值。
# 起点用 Exp2 (degraded)，终点用 Exp3 (full)，中间为占位插值，仅示意收敛形状。
CONVERGENCE = {
    "Government":  [79.87, 84.30, 86.80, 87.50, 87.69, 87.69],
    "Finance":     [70.42, 73.10, 75.20, 76.00, 76.07, 76.07],
    "Environment": [65.25, 71.50, 75.80, 77.90, 78.46, 78.46],
}
CONVERGENCE_IS_PLACEHOLDER = True  # 填好真实数据后改为 False


def _save(fig, name):
    pdf = os.path.join(OUTDIR, name + ".pdf")
    fig.savefig(pdf)
    plt.close(fig)
    print(f"  -> {pdf}")


# --------------------------------------------------------------------------- #
# 1. enhancement_effect : 分组柱状图
# --------------------------------------------------------------------------- #
def plot_enhancement_effect():
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    x = np.arange(len(DOMAINS))
    w = 0.26
    series = list(COMPREHENSIVE.items())
    colors = [C_EXP1, C_EXP2, C_EXP3]
    for i, (label, vals) in enumerate(series):
        bars = ax.bar(x + (i - 1) * w, vals, w, label=label, color=colors[i],
                      edgecolor="white", linewidth=0.5)
        ax.bar_label(bars, fmt="%.1f", padding=2, fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels(DOMAINS)
    ax.set_ylabel(r"Comprehensive Quality Score $Q_{score}$")
    ax.set_ylim(55, 95)
    ax.legend(loc="lower right", frameon=False, ncol=1)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    _save(fig, "enhancement_effect")


# --------------------------------------------------------------------------- #
# 2. dimension_improvement : 热力图
# --------------------------------------------------------------------------- #
def plot_dimension_improvement():
    # 追加“Average”列
    avg = DIM_IMPROVEMENT.mean(axis=1, keepdims=True)
    data = np.hstack([DIM_IMPROVEMENT, avg])
    cols = DOMAINS + ["Average"]

    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=0, vmax=data.max())

    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols)
    ax.set_yticks(np.arange(len(DIM_LABELS)))
    ax.set_yticklabels(DIM_LABELS)

    # 单元格数值标注，按底色深浅自动选黑/白字
    thr = data.max() * 0.55
    for r in range(data.shape[0]):
        for c in range(data.shape[1]):
            v = data[r, c]
            ax.text(c, r, f"+{v:.2f}", ha="center", va="center",
                    color="white" if v > thr else "black", fontsize=8.5)

    # 用细线分隔 Average 列
    ax.axvline(len(DOMAINS) - 0.5, color="white", linewidth=2)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Score improvement (Exp3 $-$ Exp2)", fontsize=8.5)
    ax.set_title("Quality Dimension Improvement by Domain")
    # 关闭多余边框
    for s in ax.spines.values():
        s.set_visible(False)
    _save(fig, "dimension_improvement")


# --------------------------------------------------------------------------- #
# 3. ablation_bar : 分组柱状图
# --------------------------------------------------------------------------- #
def plot_ablation_bar():
    fig, ax = plt.subplots(figsize=(6.6, 3.7))
    x = np.arange(len(DOMAINS))
    series = list(ABLATION.items())
    n = len(series)
    w = 0.16
    colors = [C_EXP2, C_ENTITY, C_GRAPH, C_CONTEXT, C_EXP3]
    for i, (label, vals) in enumerate(series):
        offset = (i - (n - 1) / 2) * w
        bars = ax.bar(x + offset, vals, w, label=label, color=colors[i],
                      edgecolor="white", linewidth=0.4)
        ax.bar_label(bars, fmt="%.1f", padding=2, fontsize=6.2, rotation=90)
    ax.set_xticks(x)
    ax.set_xticklabels(DOMAINS)
    ax.set_ylabel(r"Comprehensive Quality Score $Q_{score}$")
    ax.set_ylim(60, 95)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.16),
              ncol=5, frameon=False, columnspacing=1.0, handletextpad=0.4)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    _save(fig, "ablation_bar")


# --------------------------------------------------------------------------- #
# 4. failure_distribution : 饼图
# --------------------------------------------------------------------------- #
def plot_failure_distribution():
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    labels = list(FAILURE.keys())
    sizes = list(FAILURE.values())
    colors = [C_EXP2, C_GRAPH, C_ENTITY, C_CONTEXT]
    explode = [0.04, 0, 0, 0]  # 突出最大类
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, autopct=lambda p: f"{p:.0f}%",
        startangle=90, counterclock=False, colors=colors, explode=explode,
        wedgeprops=dict(edgecolor="white", linewidth=1.2),
        pctdistance=0.72,
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(9)
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(0.98, 0.5),
              frameon=False, fontsize=8.5)
    ax.set_aspect("equal")
    _save(fig, "failure_distribution")


# --------------------------------------------------------------------------- #
# 5. convergence : 折线图  (TODO: 数据为占位)
# --------------------------------------------------------------------------- #
def plot_convergence():
    if CONVERGENCE_IS_PLACEHOLDER:
        print("  [!] convergence 使用占位数据，请用真实每迭代 Q 值替换 CONVERGENCE。")
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    colors = {"Government": C_EXP1, "Finance": C_EXP2, "Environment": C_EXP3}
    markers = {"Government": "o", "Finance": "s", "Environment": "^"}
    for dom, vals in CONVERGENCE.items():
        it = np.arange(len(vals))
        ax.plot(it, vals, marker=markers[dom], color=colors[dom],
                label=dom, linewidth=1.6, markersize=5)
    ax.set_xlabel("Iteration")
    ax.set_ylabel(r"Comprehensive Quality Score $Q_{score}$")
    ax.set_xticks(np.arange(max(len(v) for v in CONVERGENCE.values())))
    ax.legend(loc="lower right", frameon=False)
    ax.grid(linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    if CONVERGENCE_IS_PLACEHOLDER:
        ax.text(0.02, 0.02, "PLACEHOLDER DATA", transform=ax.transAxes,
                fontsize=8, color="gray", alpha=0.7)
    _save(fig, "convergence")


def main():
    print("生成论文配图到:", OUTDIR)
    print("[1/5] enhancement_effect (grouped bar)")
    plot_enhancement_effect()
    print("[2/5] dimension_improvement (heatmap)")
    plot_dimension_improvement()
    print("[3/5] ablation_bar (grouped bar)")
    plot_ablation_bar()
    print("[4/5] failure_distribution (pie)")
    plot_failure_distribution()
    print("[5/5] convergence (line)")
    plot_convergence()
    print("完成。")


if __name__ == "__main__":
    main()
