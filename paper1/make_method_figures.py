#!/usr/bin/env python3
"""Generate the active Paper 1 method diagrams as vector graphics."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from figure_style import (
    BLUE,
    BLUE_DARK,
    BLUE_LIGHT,
    GREEN,
    GREEN_LIGHT,
    GRID,
    INK,
    MUTED,
    ORANGE,
    ORANGE_LIGHT,
    PALE,
    WHITE,
    apply_style,
    save_vector,
)

apply_style()
OUT = Path(__file__).resolve().parent / "figure" / "method"


def setup(width=7.15, height=3.0):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def box(ax, xy, wh, title, lines=(), fc=WHITE, ec=GRID, title_color=INK,
        lw=0.9, radius=0.012, title_size=8.2, body_size=6.9, zorder=2):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=zorder,
    )
    ax.add_patch(patch)
    ax.text(x + 0.045*w, y + h*0.72, title, ha="left", va="center",
            fontsize=title_size, fontweight="bold", color=title_color, zorder=zorder+1)
    if lines:
        ax.text(x + 0.045*w, y + h*0.40, "\n".join(lines), ha="left", va="center",
                fontsize=body_size, color=MUTED, linespacing=1.32, zorder=zorder+1)
    return patch


def arrow(ax, start, end, color=MUTED, rad=0.0, lw=1.25, style="-|>", zorder=3):
    patch = FancyArrowPatch(
        start, end, arrowstyle=style, mutation_scale=9.5,
        linewidth=lw, color=color, connectionstyle=f"arc3,rad={rad}", zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def chip(ax, xy, text, fc, ec):
    x, y = xy
    patch = FancyBboxPatch((x, y), 0.12, 0.085, boxstyle="round,pad=0.004,rounding_size=0.012",
                           facecolor=fc, edgecolor=ec, linewidth=0.7, zorder=4)
    ax.add_patch(patch)
    ax.text(x + 0.06, y + 0.043, text, ha="center", va="center", fontsize=6.4,
            color=ec, fontweight="bold", zorder=5)


def architecture():
    fig, ax = setup(7.15, 3.15)
    # Five-stage left-to-right pipeline.
    stages = [
        (0.015, 0.40, 0.115, 0.25, "Input", ("KG triples", "source evidence"), PALE, MUTED),
        (0.175, 0.28, 0.185, 0.49, "Multi-scale assessment",
         ("Entity  · local structure", "Graph   · constraints", "Context · source support"),
         GREEN_LIGHT, GREEN),
        (0.405, 0.54, 0.155, 0.22, "Quality profile",
         (r"$\mathbf{s}=[S_{iso},S_{red},S_{log},S_{sem}]$",), BLUE_LIGHT, BLUE),
        (0.405, 0.25, 0.155, 0.22, "Violation set",
         ("hard + soft defects",), ORANGE_LIGHT, ORANGE),
        (0.615, 0.50, 0.15, 0.25, "Scale-aware router",
         (r"$p_{repair}$ + scale prior $\pi$",), BLUE_LIGHT, BLUE),
        (0.805, 0.31, 0.145, 0.38, "Constraint gate",
         ("source support", "schema + cardinality", "least-destructive edit"), ORANGE_LIGHT, ORANGE),
    ]
    for x, y, w, h, title, lines, fc, ec in stages:
        box(ax, (x, y), (w, h), title, lines, fc=fc, ec=ec, title_color=INK)
    box(ax, (0.965, 0.40), (0.03, 0.20), r"$G^*$", (), fc=GREEN_LIGHT, ec=GREEN,
        title_color=GREEN, title_size=8.5)

    arrow(ax, (0.13, 0.525), (0.175, 0.525), MUTED)
    arrow(ax, (0.36, 0.60), (0.405, 0.65), GREEN)
    arrow(ax, (0.36, 0.44), (0.405, 0.36), GREEN)
    arrow(ax, (0.56, 0.65), (0.615, 0.63), BLUE)
    arrow(ax, (0.56, 0.36), (0.805, 0.43), ORANGE, rad=-0.08)
    arrow(ax, (0.765, 0.61), (0.805, 0.56), BLUE)
    arrow(ax, (0.95, 0.50), (0.965, 0.50), GREEN)

    chip(ax, (0.60, 0.28), "Rules", PALE, MUTED)
    chip(ax, (0.60, 0.17), "Source copy", GREEN_LIGHT, GREEN)
    chip(ax, (0.735, 0.17), "LLM reason", BLUE_LIGHT, BLUE)
    ax.text(0.615, 0.39, "candidate actions", ha="left", va="center", fontsize=6.5,
            color=MUTED, fontweight="bold")
    arrow(ax, (0.765, 0.24), (0.81, 0.36), MUTED, rad=-0.1, lw=0.9)

    arrow(ax, (0.98, 0.39), (0.27, 0.16), GREEN, rad=-0.17, lw=1.15)
    ax.text(0.54, 0.055, "re-assess after committed edits", ha="center", va="center",
            fontsize=6.8, color=GREEN, fontweight="bold")
    ax.text(0.014, 0.91, "D I A G N O S E", fontsize=6.4, color=GREEN, fontweight="bold")
    ax.plot([0.014, 0.56], [0.88, 0.88], color=GREEN, linewidth=1.0)
    ax.text(0.615, 0.91, "ACT WITHIN CONSTRAINTS", fontsize=6.4, color=ORANGE,
            fontweight="bold")
    ax.plot([0.615, 0.995], [0.88, 0.88], color=ORANGE, linewidth=1.0)
    fig.subplots_adjust(left=0.01, right=0.995, bottom=0.03, top=0.98)
    save_vector(fig, OUT / "image1.pdf")


def scales():
    fig, ax = setup(7.15, 2.55)
    cards = [
        (0.025, "1", "Entity scale", "1-hop topology",
         ("connectivity", "duplicate evidence"), ("isolated nodes", "redundant triples"), BLUE_LIGHT, BLUE),
        (0.35, "2", "Graph scale", "multi-hop constraints",
         ("type compatibility", "hierarchy direction"), ("schema conflicts", "reversed edges"), GREEN_LIGHT, GREEN),
        (0.675, "3", "Context scale", "source-grounded meaning",
         ("factual support", "semantic plausibility"), ("missing values", "unsupported facts"), ORANGE_LIGHT, ORANGE),
    ]
    for x, number, title, scope, signals, defects, fc, ec in cards:
        patch = FancyBboxPatch((x, 0.18), 0.285, 0.66,
                               boxstyle="round,pad=0.008,rounding_size=0.016",
                               facecolor=fc, edgecolor=ec, linewidth=1.0)
        ax.add_patch(patch)
        ax.text(x + 0.025, 0.75, number, ha="left", va="center", fontsize=13,
                fontweight="bold", color=ec)
        ax.text(x + 0.065, 0.75, title, ha="left", va="center", fontsize=9,
                fontweight="bold", color=INK)
        ax.text(x + 0.025, 0.62, scope, ha="left", va="center", fontsize=7.1,
                color=ec, fontweight="bold")
        ax.plot([x + 0.025, x + 0.26], [0.55, 0.55], color=WHITE, linewidth=1.1)
        ax.text(x + 0.025, 0.47, "SIGNALS", ha="left", va="center", fontsize=5.9,
                color=MUTED, fontweight="bold")
        ax.text(x + 0.025, 0.385, "\n".join(signals), ha="left", va="center",
                fontsize=6.4, color=INK, linespacing=1.25)
        ax.text(x + 0.155, 0.47, "DETECTS", ha="left", va="center", fontsize=5.9,
                color=MUTED, fontweight="bold")
        ax.text(x + 0.155, 0.385, "\n".join(defects), ha="left", va="center",
                fontsize=6.4, color=INK, linespacing=1.25)
    arrow(ax, (0.31, 0.51), (0.35, 0.51), MUTED)
    arrow(ax, (0.635, 0.51), (0.675, 0.51), MUTED)
    ax.text(0.5, 0.07, "dependency horizon expands  ·  evidence becomes richer",
            ha="center", va="center", fontsize=6.8, color=MUTED)
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.04, top=0.98)
    save_vector(fig, OUT / "image2.pdf")


def optimization():
    fig, ax = setup(7.15, 2.75)
    steps = [
        (0.02, "Assess", ("quality profile", "+ violations"), GREEN_LIGHT, GREEN),
        (0.205, "Route", (r"$p_{repair}$", r"+ scale prior $\pi$"), BLUE_LIGHT, BLUE),
        (0.39, "Propose", ("rules · source", "· LLM"), BLUE_LIGHT, BLUE),
        (0.575, "Trial edit", (r"estimate $\Delta Q$", "+ action cost"), ORANGE_LIGHT, ORANGE),
        (0.76, "Constraint gate", ("feasible?", r"$U(a\mid v)>0$?"), ORANGE_LIGHT, ORANGE),
    ]
    for index, (x, title, lines, fc, ec) in enumerate(steps, 1):
        box(ax, (x, 0.50), (0.145, 0.31), title, lines, fc=fc, ec=ec, title_color=INK,
            title_size=8.1, body_size=6.7)
        ax.text(x + 0.012, 0.77, f"{index:02d}", ha="left", va="center", fontsize=6.1,
                color=ec, fontweight="bold")
    for x in (0.165, 0.35, 0.535, 0.72):
        arrow(ax, (x, 0.655), (x + 0.04, 0.655), MUTED)

    box(ax, (0.79, 0.14), (0.115, 0.20), "Commit", (r"update $G^*$",),
        fc=GREEN_LIGHT, ec=GREEN, title_color=INK, title_size=7.8, body_size=6.6)
    arrow(ax, (0.835, 0.50), (0.845, 0.34), GREEN)
    ax.text(0.865, 0.41, "accept", ha="left", va="center", fontsize=6.5,
            color=GREEN, fontweight="bold")
    arrow(ax, (0.80, 0.50), (0.67, 0.42), ORANGE, rad=0.12)
    ax.text(0.71, 0.40, "reject", ha="center", va="center", fontsize=6.5,
            color=ORANGE, fontweight="bold")
    arrow(ax, (0.79, 0.22), (0.09, 0.46), GREEN, rad=-0.20, lw=1.15)
    ax.text(0.44, 0.07, "next assessment", ha="center", va="center", fontsize=6.7,
            color=GREEN, fontweight="bold")
    ax.text(0.02, 0.93, "Every candidate is evaluated on a trial graph before commit.",
            ha="left", va="center", fontsize=7.1, color=MUTED)
    fig.subplots_adjust(left=0.01, right=0.995, bottom=0.03, top=0.98)
    save_vector(fig, OUT / "image3.pdf")


if __name__ == "__main__":
    architecture()
    scales()
    optimization()
    print("wrote 3 vector method figures")
