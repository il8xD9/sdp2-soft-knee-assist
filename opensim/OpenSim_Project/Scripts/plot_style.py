"""Shared figure style (validated categorical palette; thin marks; recessive grid)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#ffffff"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8985"
GRID = "#e4e3df"
# condition colours: healthy = neutral ink; ACL epochs = categorical slots 1-5 in fixed order
COL = {"healthy": "#3b3a37", "preop": "#2a78d6", "2months": "#eb6834", "4months": "#1baf7a",
       "6months": "#eda100", "12months": "#e87ba4"}
LAB = {"healthy": "Healthy (matched controls)", "preop": "ACL Pre-op", "2months": "ACL 2 months",
       "4months": "ACL 4 months", "6months": "ACL 6 months", "12months": "ACL 12 months"}
SHORT = {"healthy": "Healthy", "preop": "Pre-op", "2months": "2 mo", "4months": "4 mo",
         "6months": "6 mo", "12months": "12 mo"}
DEVICE = "#eb6834"     # actuator series
BASE = "#3b3a37"       # baseline series
ASSIST = "#2a78d6"     # assisted series

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.labelsize": 9.5,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.8,
    "legend.frameon": False, "legend.fontsize": 8.5, "font.size": 9.5,
    "savefig.dpi": 300, "figure.dpi": 110,
})


def finish(fig, path, note=None):
    if note:
        fig.text(0.01, -0.01, note, fontsize=7, color=MUTED, ha="left", va="top")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def zero_line(ax):
    ax.axhline(0, color=MUTED, lw=0.8, zorder=1)
