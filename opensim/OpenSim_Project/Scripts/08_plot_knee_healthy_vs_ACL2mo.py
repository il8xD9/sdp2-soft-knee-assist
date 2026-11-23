"""
08_plot_knee_healthy_vs_ACL2mo.py - Fig21: knee angle, moment and power, healthy vs ACL 2 months
(no-device OpenSim baseline). Reads Simulations/<cond>/<cond>_inputs_and_actuator.csv, writes Graphs/Fig21*.png.
Run:  python Scripts/08_plot_knee_healthy_vs_ACL2mo.py   (CPython 3 + matplotlib)
Power = net knee moment (extension +) x knee angular velocity (extension +) = M x knee_angle_r speed.
Stance only: the source waveforms (Buttner 2025) cover stance only.
"""
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(PROJ, "Simulations") + os.sep
FILES = {"Healthy": os.path.join("Healthy_Baseline", "Healthy_Baseline_inputs_and_actuator.csv"),
         "ACLR 2 months": os.path.join("ACL_2Months", "Baseline", "ACL_2Months_Baseline_inputs_and_actuator.csv")}
STYLE = {"Healthy": dict(color="#2a78d6", ls="-"), "ACLR 2 months": dict(color="#eb6834", ls="--")}
INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e4e3dd"

D = {}
for k, f in FILES.items():
    R = list(csv.DictReader(open(BASE + f)))
    x = [0.0] + [float(r["pct_stance"]) for r in R]
    ang = [float(r["knee_flexion_deg"]) for r in R]
    mom = [float(r["net_knee_moment_Nm"]) for r in R]
    # knee power = moment (extension +) x angular velocity (extension +) = M x knee_angle_r speed
    pw = [float(r["net_knee_moment_Nm"]) * float(r["knee_angle_r_speed_rad_s"]) for r in R]
    D[k] = dict(x=x[1:], ang=ang, mom=mom, pw=pw, T=float(R[-1]["time_s"]))

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})

WIN1, WIN2 = (8.43, 44), (13, 36)


def style_ax(ax, ylab, title):
    ax.set_xlim(0, 100)
    ax.set_xlabel("Time (% stance)")
    ax.set_ylabel(ylab)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.axhline(0, color=MUTED, lw=0.8, ls=":")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.axvspan(*WIN1, color="#d9d8d1", alpha=0.35, lw=0, zorder=0)
    ax.axvspan(*WIN2, color="#bdbcb3", alpha=0.35, lw=0, zorder=0)
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold")


def lines(ax, key):
    for k in FILES:
        ax.plot(D[k]["x"], D[k][key], lw=2, label=k, **STYLE[k])


def note(ax, x, y, text, dx=6, dy=6, ha="left"):
    ax.annotate(text, xy=(x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8.5, color=INK, ha=ha,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))


def pk(k, key, lo, hi, fn=max):
    xs, ys = D[k]["x"], D[k][key]
    idx = [i for i in range(len(xs)) if lo <= xs[i] <= hi]
    i = fn(idx, key=lambda j: ys[j])
    return xs[i], ys[i]


def panel_a(ax):
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 3.2)
    ax.axis("off")
    phases = [(0, 3.3, "IC"), (3.3, 20, "Loading\nresponse"), (20, 51.7, "Mid-stance"), (51.7, 83.3, "Terminal\nstance"), (83.3, 100, "Pre-\nswing")]
    for a, b, t in phases:
        ax.add_patch(Rectangle((a, 1.9), b - a, 0.7, fc="#eeede8", ec=MUTED, lw=0.8))
        if t != "IC":
            ax.text((a + b) / 2, 2.25, t, ha="center", va="center", fontsize=8.5, color=INK)
    ax.annotate("IC", xy=(1.6, 2.6), xytext=(1.6, 3.0), ha="center", fontsize=8.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
    ax.add_patch(Rectangle((WIN1[0], 1.1), WIN1[1] - WIN1[0], 0.45, fc="#d9d8d1", ec=MUTED, lw=0.8))
    ax.text(WIN1[1] + 1.5, 1.32, "Option 1 window 8.43-44 % (59-310 ms)", va="center", fontsize=8.5, color=INK)
    ax.add_patch(Rectangle((WIN2[0], 0.45), WIN2[1] - WIN2[0], 0.45, fc="#bdbcb3", ec=MUTED, lw=0.8))
    ax.text(WIN2[1] + 1.5, 0.67, "Option 2 window 13-36 % (92-254 ms)", va="center", fontsize=8.5, color=INK)
    for t in range(0, 101, 20):
        ax.text(t, 0.05, f"{t}%", ha="center", fontsize=8, color=MUTED)
    ax.text(0, -0.35, "Phase limits: Perry & Burnfield 2010 Ch. 2, converted % stance = % gait cycle / 0.60", fontsize=8, color=MUTED)
    ax.set_title("(a) Stance phases and assist windows", loc="left",
                 fontsize=11, color=INK, fontweight="bold")


def panel_b(ax):
    lines(ax, "ang")
    style_ax(ax, "Knee flexion (deg)", "(b) Knee angle")
    for k, dy in (("Healthy", 8), ("ACLR 2 months", -16)):
        x, y = pk(k, "ang", 10, 30)
        note(ax, x, y, f"{y:.1f}° @ {x:.0f} %", dy=dy)
    ax.text(99, 1, "Flexion ↑", ha="right", fontsize=8.5, color=MUTED)


def panel_c(ax):
    lines(ax, "mom")
    style_ax(ax, "Knee moment (N·m)", "(c) Knee moment (internal, extension +)")
    for k, dy in (("Healthy", 6), ("ACLR 2 months", 10)):
        x, y = pk(k, "mom", 10, 35)
        note(ax, x, y, f"{y:.1f} N·m @ {x:.0f} %", dy=dy)
    ax.text(99, 36, "Extension ↑", ha="right", fontsize=8.5, color=MUTED)
    ax.set_ylim(-30, 50)
    yh = D["Healthy"]["mom"][20]; ya = D["ACLR 2 months"]["mom"][20]
    ax.annotate("", xy=(21, yh), xytext=(21, ya), arrowprops=dict(arrowstyle="<->", color=INK, lw=1))
    ax.text(22.5, (yh + ya) / 2 - 3, "deficit 33 N·m\n@ 21 %", ha="left", va="center", fontsize=8.5, color=INK, bbox=dict(fc="white", ec="none", pad=1.5))


def panel_d(ax):
    lines(ax, "pw")
    style_ax(ax, "Knee power (W)", "(d) Knee power (moment x angular velocity)")
    for k, dy, dx in (("Healthy", -4, 8), ("ACLR 2 months", -22, 22)):
        x, y = pk(k, "pw", 5, 25, fn=min)
        note(ax, x, y, f"{y:.1f} W @ {x:.0f} %", dy=dy, dx=dx)
    ax.text(99, 22, "Generation ↑", ha="right", fontsize=8.5, color=MUTED)


def legend(fig):
    h = [plt.Line2D([], [], lw=2, **STYLE[k]) for k in FILES]
    lab = [f"Healthy (stance {D['Healthy']['T']:.3f} s)", f"ACLR 2 months (stance {D['ACLR 2 months']['T']:.3f} s)"]
    fig.legend(h, lab, loc="upper right", ncol=2, frameon=False, fontsize=9.5)


SRC = ("OpenSim 4.6 no-device baseline (Healthy_Baseline and ACL_2Months/Baseline). Input waveforms from Buttner et al. 2025 "
       "(stance only - no swing data for ACLR). Moment = net knee moment (taken from Buttner, not an independent calculation). Reference man 70 kg, 1.70 m.")

fig, axs = plt.subplots(2, 2, figsize=(13, 8.6))
panel_a(axs[0, 0]); panel_b(axs[0, 1]); panel_c(axs[1, 0]); panel_d(axs[1, 1])
legend(fig)
fig.text(0.01, 0.005, SRC, fontsize=7.5, color=MUTED, wrap=True)
fig.tight_layout(rect=(0, 0.04, 1, 0.95))
out = os.path.join(PROJ, "Graphs") + os.sep
fig.savefig(out + "Fig21_Healthy_vs_ACL2mo_Knee_Panel.png", dpi=300, facecolor="white")

for name, fn in (("Fig21a_Stance_Phases_and_Assist_Windows", panel_a), ("Fig21b_Knee_Angle_Healthy_vs_ACL2mo", panel_b),
                 ("Fig21c_Knee_Moment_Healthy_vs_ACL2mo", panel_c), ("Fig21d_Knee_Power_Healthy_vs_ACL2mo", panel_d)):
    f, ax = plt.subplots(figsize=(6.8, 4.2))
    fn(ax)
    if not name.startswith("Fig21a"):
        ax.legend(loc="upper right", frameon=False, fontsize=9)
    f.tight_layout()
    f.savefig(out + name + ".png", dpi=300, facecolor="white")
print("Fig21 written to", out)
