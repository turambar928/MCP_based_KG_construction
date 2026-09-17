"""Shared visual style for Paper 1 publication figures."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

# Okabe--Ito inspired, color-vision-safe palette with restrained journal tones.
INK = "#17212B"
MUTED = "#5F6B76"
GRID = "#D8DEE4"
PALE = "#F4F7F9"
BLUE = "#0072B2"
BLUE_DARK = "#004C73"
BLUE_LIGHT = "#DCEEF7"
GREEN = "#009E73"
GREEN_LIGHT = "#DDF3EC"
ORANGE = "#D55E00"
ORANGE_LIGHT = "#FAE7D9"
AMBER = "#E69F00"
PURPLE = "#8E6C8A"
GRAY = "#8A949E"
LIGHT_GRAY = "#E9EDF0"
WHITE = "#FFFFFF"

HEAT_CMAP = LinearSegmentedColormap.from_list(
    "paper_blue", ["#F7FAFC", "#DCEEF7", "#7DB9D8", BLUE_DARK]
)


def apply_style() -> None:
    # Fail explicitly rather than silently substitute a different serif font.
    for path in Path('/usr/share/fonts/truetype/msttcorefonts').glob('Times_New_Roman*.ttf'):
        font_manager.fontManager.addfont(str(path))
    font_manager.findfont('Times New Roman', fallback_to_default=False)
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman"],
            "mathtext.fontset": "custom",
            "mathtext.rm": "Times New Roman",
            "mathtext.it": "Times New Roman:italic",
            "mathtext.bf": "Times New Roman:bold",
            "mathtext.sf": "Times New Roman",
            "mathtext.tt": "Times New Roman",
            "mathtext.cal": "Times New Roman:italic",
            "mathtext.fallback": None,
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "axes.titlesize": 8.5,
            "axes.titleweight": "bold",
            "axes.labelcolor": INK,
            "axes.edgecolor": INK,
            "axes.linewidth": 0.7,
            "xtick.labelsize": 7.2,
            "ytick.labelsize": 7.2,
            "xtick.color": INK,
            "ytick.color": INK,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "legend.fontsize": 7.0,
            "legend.frameon": False,
            "text.color": INK,
            "figure.facecolor": WHITE,
            "axes.facecolor": WHITE,
            "savefig.facecolor": WHITE,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.025,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "lines.linewidth": 1.25,
            "patch.linewidth": 0.7,
        }
    )


def panel_label(ax, label: str, x: float = -0.12, y: float = 1.04) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9,
        fontweight="bold",
        color=INK,
    )


def clean_axis(ax, grid_axis: str | None = "x") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.55, alpha=0.75)
        ax.set_axisbelow(True)


def save_vector(fig, path: Path, also_png: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    if also_png:
        fig.savefig(path.with_suffix(".png"), dpi=450)
    plt.close(fig)
