#!/usr/bin/env python3
"""Generate the three method diagrams referenced by paper1."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle


OUT = Path(__file__).resolve().parent / "figure" / "method"
BLUE = "#2563A5"
LIGHT_BLUE = "#E8F1FA"
TEAL = "#168A83"
LIGHT_TEAL = "#E5F5F3"
ORANGE = "#D9772A"
LIGHT_ORANGE = "#FFF0E3"
DARK = "#243447"
GRAY = "#64748B"


def setup(width=11, height=5):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def box(ax, xy, wh, title, subtitle="", fc="white", ec=BLUE, lw=1.8, title_size=11):
    x, y = xy; w, h = wh
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
                           facecolor=fc, edgecolor=ec, linewidth=lw)
    ax.add_patch(patch)
    ax.text(x + w/2, y + h*0.62, title, ha="center", va="center",
            fontsize=title_size, weight="bold", color=DARK)
    if subtitle:
        ax.text(x + w/2, y + h*0.30, subtitle, ha="center", va="center",
                fontsize=8.5, color=GRAY, linespacing=1.25)
    return patch


def arrow(ax, start, end, color=GRAY, rad=0, label=None, label_xy=None):
    p = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14,
                        linewidth=1.7, color=color,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(p)
    if label:
        x, y = label_xy or ((start[0]+end[0])/2, (start[1]+end[1])/2)
        ax.text(x, y, label, ha="center", va="center", fontsize=8.5, color=color,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5))


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def architecture():
    fig, ax = setup(12, 5.1)
    box(ax, (.02, .35), (.13, .30), "Input KG", "entities, triples,\nsource evidence", LIGHT_BLUE)
    box(ax, (.21, .23), (.21, .54), "Multi-Scale Assessment",
        "Entity: connectivity, uniqueness\nGraph: logical consistency\nContext: semantic evidence", LIGHT_TEAL, TEAL)
    box(ax, (.48, .55), (.18, .22), "Quality Profile", "$s=[S_{iso},S_{red},S_{log},S_{sem}]$", LIGHT_BLUE)
    box(ax, (.48, .23), (.18, .22), "Violation Set", "hard and soft defects", LIGHT_ORANGE, ORANGE)
    box(ax, (.72, .55), (.18, .22), "Scale-Aware Router", "$p_{repair}$ and scale prior $\\pi$", LIGHT_BLUE)
    box(ax, (.72, .23), (.18, .22), "Constraint Gate", "lower bounds, density ceiling,\naction utility", LIGHT_ORANGE, ORANGE)
    box(ax, (.92, .35), (.065, .30), "KG$^*$", "", LIGHT_TEAL, TEAL, title_size=10)
    arrow(ax, (.15,.50), (.21,.50), BLUE)
    arrow(ax, (.42,.59), (.48,.66), TEAL)
    arrow(ax, (.42,.41), (.48,.34), TEAL)
    arrow(ax, (.66,.66), (.72,.66), BLUE)
    arrow(ax, (.66,.34), (.72,.34), ORANGE)
    arrow(ax, (.81,.55), (.81,.45), GRAY, label="candidate tools", label_xy=(.86,.50))
    arrow(ax, (.90,.34), (.92,.47), ORANGE)
    arrow(ax, (.952,.35), (.37,.18), TEAL, rad=-.22, label="re-assess until stopping rule", label_xy=(.66,.08))
    ax.text(.50,.93,"Constraint-Driven Multi-Scale Enhancement Loop",ha="center",fontsize=15,weight="bold",color=DARK)
    save(fig, "image1.png")


def scales():
    fig, ax = setup(11, 4.8)
    centers = [(.18,.50),(.50,.50),(.82,.50)]
    specs = [
        ("Entity Scale", "1-hop local topology", "isolated nodes\nnear-duplicate triples", LIGHT_BLUE, BLUE),
        ("Graph Scale", "multi-hop schema logic", "type compatibility\nhierarchy direction", LIGHT_TEAL, TEAL),
        ("Context Scale", "source and cross-document", "factual support\nsemantic plausibility", LIGHT_ORANGE, ORANGE),
    ]
    for (cx,cy),(title,scope,items,fc,ec) in zip(centers,specs):
        ax.add_patch(Circle((cx,cy),.145,facecolor=fc,edgecolor=ec,linewidth=2.2))
        ax.text(cx,cy+.055,title,ha="center",fontsize=12,weight="bold",color=DARK)
        ax.text(cx,cy,scope,ha="center",fontsize=9,color=ec)
        ax.text(cx,cy-.075,items,ha="center",va="center",fontsize=8.5,color=GRAY,linespacing=1.35)
    arrow(ax,(.325,.50),(.355,.50),GRAY,label="expand scope",label_xy=(.34,.60))
    arrow(ax,(.645,.50),(.675,.50),GRAY,label="ground meaning",label_xy=(.66,.60))
    ax.text(.50,.88,"Progressive Relational Dependency Validation",ha="center",fontsize=15,weight="bold",color=DARK)
    ax.text(.50,.15,"Local structure  $\\longrightarrow$  global consistency  $\\longrightarrow$  external evidence",
            ha="center",fontsize=10,color=GRAY)
    save(fig, "image2.png")


def optimization():
    fig, ax = setup(12, 5.3)
    steps = [
        (.03,"Assess","compute $s$ and violations",LIGHT_TEAL,TEAL),
        (.22,"Route","predict $p_{repair}$ and $\\pi$",LIGHT_BLUE,BLUE),
        (.41,"Propose","rules, retrieval, LLM",LIGHT_BLUE,BLUE),
        (.60,"Trial Edit","local quality estimate",LIGHT_ORANGE,ORANGE),
        (.79,"Constraint Gate","feasible and $U(a|v)>0$",LIGHT_ORANGE,ORANGE),
    ]
    for x,title,sub,fc,ec in steps:
        box(ax,(x,.48),(.15,.23),title,sub,fc,ec,title_size=10.5)
    for x in [.18,.37,.56,.75]:
        arrow(ax,(x,.595),(x+.04,.595),GRAY)
    box(ax,(.79,.14),(.15,.18),"Commit", "update $G^*$",LIGHT_TEAL,TEAL)
    arrow(ax,(.865,.48),(.865,.32),TEAL,label="accept",label_xy=(.91,.40))
    arrow(ax,(.79,.25),(.13,.44),TEAL,rad=-.20,label="next assessment",label_xy=(.48,.10))
    arrow(ax,(.865,.48),(.70,.40),ORANGE,rad=.15,label="reject",label_xy=(.78,.39))
    ax.text(.50,.91,"Utility-Guided Repair with Constraint Checks",ha="center",fontsize=15,weight="bold",color=DARK)
    ax.text(.50,.80,"Every candidate is evaluated on a trial graph before any edit is committed",
            ha="center",fontsize=9.5,color=GRAY)
    save(fig, "image3.png")


if __name__ == "__main__":
    architecture(); scales(); optimization()
    print(f"wrote method figures to {OUT}")
