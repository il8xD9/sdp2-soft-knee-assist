# -*- coding: utf-8 -*-
r"""Figures of the FEA report from the solver results.
Reads runs/<run>/<run>_results.csv, model/<run>/<run>_mesh.pkl and runs/<run>/<run>.OUT (raw output, see the README)
and writes results/figures/*.png.
Usage: python -P make_figures.py [--skip_out]   (--skip_out = only the charts that need no .OUT file)"""
import argparse, csv, os, pickle, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import post_process as P

OUT = os.path.join(R, "results", "figures"); os.makedirs(OUT, exist_ok=True)
K = 0.20699                     # N m per kPa (k = 206 990 mm3, hand calculation)
H = np.array([4.0573, 0.0])     # knee centre (mm)
COL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a5cc2", "#555555"]
ANG = [("3.0", "CHK_FB"), ("7.3", "HC_A7.3"), ("8.6", "HC_A8.6"), ("9.8", "HC_A9.8"), ("13.0", "HC_A13.0"),
       ("16.0", "HC_A16.0"), ("19.0", "HC_A19.0")]
CYC = ["HCC_P20", "HCC_PROJ", "HCC_P40", "HCC_P60"]


def load(run):
    f = os.path.join(R, "runs", run, run + "_results.csv")
    if not os.path.exists(f):
        return None
    rows = list(csv.DictReader(open(f)))
    for r in rows:
        for k, v in list(r.items()):
            try: r[k] = float(v)
            except (TypeError, ValueError): pass
        r["converged"] = str(r.get("converged")) in ("True", "1", "1.0")
    return rows


def cyc_table():
    f = os.path.join(R, "results", "tables", "cycle_moment.csv")
    if not os.path.exists(f):
        return []
    rows = list(csv.DictReader(open(f)))
    for r in rows:
        for k, v in list(r.items()):
            try: r[k] = float(v)
            except (TypeError, ValueError): pass
    return rows


def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=160); plt.close(fig); print("figure", name)


def angle_cases():
    """device moment = M(p) - M(vented step at the case angle) vs p k; one line per angle."""
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6)); res = []
    pp = np.array([0, 60])
    ax[0].plot(pp, K * pp, "k--", lw=1.2, label="hand calc p k (Model B)")
    for i, (a, run) in enumerate(ANG):
        rr = load(run)
        if rr is None: continue
        vb = [r for r in rr if r["kind"] == "S" and r["converged"]]
        if not vb: continue
        m0 = vb[-1]["M_knee_ext_Nm"]
        pts = [(0.0, 0.0)] + [(r["p_kPa"], r["M_knee_ext_Nm"] - m0) for r in rr if r["kind"] == "W" and r["converged"] and r["p_kPa"] <= 60]
        if len(pts) < 2: continue          # vented flexion did not reach the case angle - nothing to plot
        x, y = zip(*pts)
        ax[0].plot(x, y, "-o", ms=4, color=COL[i % len(COL)], label="%s deg (%s)" % (a, run))
        for p_, m_ in pts[1:]:
            res.append((float(a), p_, m_ / (K * p_)))
    ax[0].set_xlabel("bladder pressure p (kPa)"); ax[0].set_ylabel("device moment about the knee centre (N m)")
    ax[0].set_title("Angle cases: FEA (solid) vs hand calc (dashed)"); ax[0].legend(fontsize=7); ax[0].grid(alpha=0.3)
    for j, p_ in enumerate((20, 40, 60)):
        d = sorted((a, q) for a, pq, q in res if abs(pq - p_) < 1e-6)
        if d: ax[1].plot([a for a, _ in d], [q for _, q in d], "-o", ms=4, color=COL[j], label="%d kPa" % p_)
    cr = cyc_table()
    for j, (run, p_) in enumerate((("HCC_P20", 20), ("HCC_P40", 40), ("HCC_P60", 60))):
        d = [r for r in cr if r["run"] == run and r["phase"] == "W" and r["stance_pct"] <= 21 and r.get("fold_state") in (0, 0.0)
             and r.get("ratio_FEA_to_hc") not in (None, "")]
        if d: ax[1].plot([r["theta_deg"] for r in d], [r["ratio_FEA_to_hc"] for r in d], "o", mfc="none", ms=5, color=COL[j],
                         label="%d kPa, cycle loading 13-21 %%" % p_)
    ax[1].axhline(1.0, color="k", ls="--", lw=1); ax[1].set_xlabel("knee flexion angle (deg)"); ax[1].set_ylabel("FEA / hand calc (-)")
    ax[1].set_title("Ratio device moment / p k"); ax[1].legend(fontsize=7); ax[1].grid(alpha=0.3)
    save(fig, "angle_cases_moment.png")
    return res


def cycles():
    rows = cyc_table()
    if not rows: return
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for i, run in enumerate(CYC):
        d = [r for r in rows if r["run"] == run and r["phase"] == "W" and r.get("M_device_Nm") not in (None, "")]
        if not d: continue
        c = COL[i]
        main = [r for r in d if r.get("fold_state") in (0, 0.0)]
        other = [r for r in d if r.get("fold_state") not in (0, 0.0, None, "")]
        ax[0].plot([r["stance_pct"] for r in main], [r["M_device_Nm"] for r in main], "-o", ms=3.5, color=c, label=run + " (main fold state)")
        if other:
            ax[0].plot([r["stance_pct"] for r in other], [r["M_device_Nm"] for r in other], "x", ms=6, color=c, label=run + " (other fold state)")
        ax[0].plot([r["stance_pct"] for r in d], [r["M_handcalc_Nm"] for r in d], "--", lw=1, color=c)
        ax[1].plot([r["stance_pct"] for r in d], [r["p_kPa"] for r in d], "-", color=c, label=run)
    ax[0].set_xlabel("% stance"); ax[0].set_ylabel("device moment (N m)"); ax[0].set_title("Window 13-36 %: FEA (markers) vs p k (dashed)")
    ax[0].legend(fontsize=6.5); ax[0].grid(alpha=0.3)
    ax2 = ax[1].twinx()
    th = sorted({(r["stance_pct"], r["theta_deg"]) for r in rows if r["run"] == "HCC_P20" and r["phase"] == "W"})
    ax2.plot([a for a, _ in th], [b for _, b in th], "k:", lw=1.5, label="knee angle"); ax2.set_ylabel("knee flexion (deg)")
    ax[1].set_xlabel("% stance"); ax[1].set_ylabel("bladder pressure (kPa)"); ax[1].set_title("Inputs: pressure per run and knee angle")
    ax[1].legend(fontsize=7, loc="lower left"); ax2.legend(fontsize=7, loc="lower right"); ax[1].grid(alpha=0.3)
    save(fig, "cycles_moment.png")
    # fold states: PROJ moment and volume
    d = [r for r in rows if r["run"] == "HCC_PROJ" and r["phase"] == "W"]
    if d:
        fig, ax = plt.subplots(figsize=(8, 4.2)); ax2 = ax.twinx()
        ax.plot([r["stance_pct"] for r in d], [r["M_knee_Nm"] for r in d], "-o", ms=4, color=COL[0], label="knee moment (N m)")
        ax2.plot([r["stance_pct"] for r in d], [r["V_bladder_mL"] for r in d], "-s", ms=4, color=COL[1], label="bladder volume (mL)")
        for r in d:
            if r.get("fold_state") not in (0, 0.0, None, ""):
                ax.axvspan(r["stance_pct"] - 0.5, r["stance_pct"] + 0.5, color="#f6d2d2", lw=0)
        ax.set_xlabel("% stance"); ax.set_ylabel("knee moment (N m)"); ax2.set_ylabel("bladder volume (mL)")
        ax.set_title("HCC_PROJ: two fold states (shaded = squeezed state: less volume, more moment)")
        ax.legend(loc="upper left", fontsize=7); ax2.legend(loc="lower right", fontsize=7); ax.grid(alpha=0.3)
        save(fig, "fold_states_proj.png")


def pv():
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for i, (a, run) in enumerate(ANG):
        rr = load(run)
        if rr is None: continue
        pts = [(r["p_kPa"], r["V_bladder_mid_cm3"]) for r in rr if r["converged"] and r["kind"] in ("S", "W") and r["p_kPa"] <= 60
               and abs(r["theta"] - float(a.replace("7.3", "7.28").replace("8.6", "8.63").replace("9.8", "9.78"))) < 0.02]
        if pts:
            x, y = zip(*sorted(pts)); ax.plot(x, y, "-o", ms=4, color=COL[i % len(COL)], label="%s deg" % a)
    ax.set_xlabel("bladder pressure (kPa)"); ax.set_ylabel("bladder mid-surface volume (mL)"); ax.set_title("Pressure - volume at fixed knee angle")
    ax.legend(fontsize=7); ax.grid(alpha=0.3); save(fig, "pressure_volume.png")


def solver_effort():
    fig, ax = plt.subplots(figsize=(10, 3.8)); x0 = 0; ticks = []
    for i, run in enumerate(["CHK_FB"] + [a[1] for a in ANG[1:]] + ["HCC_P0"] + CYC):
        rr = load(run)
        if rr is None: continue
        it = [r["iterations"] if r["converged"] else 0 for r in rr]
        ax.bar(np.arange(len(it)) + x0, it, color=COL[i % len(COL)], width=0.85)
        ticks.append((x0 + len(it) / 2.0, run)); x0 += len(it) + 2
    ax.set_xticks([t for t, _ in ticks]); ax.set_xticklabels([n for _, n in ticks], rotation=30, fontsize=7)
    ax.set_ylabel("Newton iterations per subcase"); ax.set_title("Solver effort per subcase (0 = not converged / not reached)")
    ax.grid(alpha=0.3, axis="y"); save(fig, "solver_iterations.png")


# ----------------------------------------------------------------- pictures from the solver output (.OUT)
def mesh_of(run):
    m = pickle.load(open(os.path.join(R, "model", run, run + "_mesh.pkl"), "rb"))
    return m["X"], m["el"], m["S"], m["meta"]


def faces(EL, ids):
    return [EL[e][2] for e in ids]


def draw(ax, X, EL, S, U=None, val=None, vmax=None, cmap="viridis", alpha=1.0):
    groups = [("cov_body", "#bbbbbb", 0.25), ("cov_cap", "#bbbbbb", 0.25), ("cov_flange", "#999999", 0.35),
              ("bl_body", "#2a78d6", 1.0), ("bl_cap", "#2a78d6", 1.0)]
    Xd = X + (U if U is not None else 0)
    cre = set(S.get("_crease", []))
    for nm, col, al in groups:
        ids = S.get(nm, [])
        if not ids: continue
        polys = [[(Xd[n][0], Xd[n][2], Xd[n][1]) for n in EL[e][2]] for e in ids]
        if val is not None and (nm.startswith("bl") or S.get("_cover_opaque")):
            cm = plt.get_cmap(cmap); vv = [val.get(e, 0.0) for e in ids]
            fc = [cm(min(v / vmax, 1.0)) for v in vv]
            pc = Poly3DCollection(polys, facecolors=fc, edgecolors="none", alpha=1.0)
        else:
            fcs = [("#eb6834" if (e in cre and nm.startswith("bl")) else col) for e in ids]
            pc = Poly3DCollection(polys, facecolors=fcs, edgecolors=(0, 0, 0, 0.12), linewidths=0.2, alpha=al)
        ax.add_collection3d(pc)
    ax.set_xlim(60, 150); ax.set_ylim(-45, 45); ax.set_zlim(-110, 110)
    ax.set_box_aspect((90, 90, 220)); ax.set_xlabel("x posterior (mm)", fontsize=7); ax.set_ylabel("z (mm)", fontsize=7)
    ax.set_zlabel("y along leg (mm)", fontsize=7); ax.tick_params(labelsize=6); ax.view_init(elev=12, azim=-58)


def pictures():
    X, EL, S, meta = mesh_of("HCC_P20")
    cre = meta["rigid_leg"].get("bl_crease", [])
    S = dict(S); S["_crease"] = cre
    # 1 mesh
    fig = plt.figure(figsize=(6.5, 7.5)); ax = fig.add_subplot(projection="3d"); draw(ax, X, EL, S)
    ax.set_title("Core model mesh: bladder (blue), fold band |y| < 25 mm (orange),\ncover (grey); knee axis = z line at x 4.06, y 0", fontsize=8)
    save(fig, "mesh_core_model.png")
    # 2 deformed + stress at the 21 % peak frame
    cases = [("HCC_P0", "W 21%", "0 kPa (vented)"), ("HCC_P20", "W 21%", "20 kPa"), ("HCC_P40", "W 21%", "40 kPa"), ("HCC_P60", "W 21%", "60 kPa")]
    got = []
    for run, nm, lab in cases:
        rr = load(run)
        if rr is None: continue
        sub = [int(r["subcase"]) for r in rr if r["name"] == nm and r["converged"]]
        if not sub: continue
        res, _ = P.parse_out(os.path.join(R, "runs", run, run + ".OUT"), subs={sub[0]})
        s = sub[0]
        if s not in res: continue
        d = res[s]["disp"]
        U = np.array([d.get(n + 1, np.zeros(6))[:3] for n in range(len(X))])
        vm = {}
        for tb in ("qstress", "tstress"):
            for eid, vals in res[s][tb].items():
                if vals: vm[eid - 1] = max(vals)
        got.append((run, lab, U, vm, s))
    if got:
        vmax = max(max([v for e, v in vm.items() if e in set(S["bl_body"])] or [1.0]) for _, _, _, vm, _ in got)
        fig = plt.figure(figsize=(4.0 * len(got), 7.0))
        for i, (run, lab, U, vm, s) in enumerate(got):
            ax = fig.add_subplot(1, len(got), i + 1, projection="3d"); draw(ax, X, EL, S, U=U, val=vm, vmax=vmax, cmap="turbo")
            bl = [vm.get(e, 0) for e in S["bl_body"]]
            ax.set_title("%s, 21 %% stance (5.78 deg)\nbladder von Mises max %.2f MPa" % (lab, max(bl) if bl else 0), fontsize=8)
        sm = plt.cm.ScalarMappable(cmap="turbo", norm=plt.Normalize(0, vmax)); sm.set_array([])
        fig.colorbar(sm, ax=fig.axes, shrink=0.5, label="bladder von Mises (MPa)")
        fig.savefig(os.path.join(OUT, "deformed_stress_21pct.png"), dpi=150, bbox_inches="tight"); plt.close(fig); print("figure deformed_stress_21pct.png")
        # 3 mid-plane section (|z| < 1.5 mm): bladder and cover outline, undeformed and inflated
        fig, ax = plt.subplots(figsize=(6.2, 7.2))
        bn = sorted({n for e in S["bl_body"] + S["bl_cap"] for n in EL[e][2] if abs(X[n][2] - 2.2) < 0.6})
        cn = sorted({n for e in S["cov_body"] + S["cov_cap"] for n in EL[e][2] if abs(X[n][2] - 2.2) < 0.6})
        ax.scatter(X[bn, 0], X[bn, 1], s=3, color="0.6", label="undeformed (0 deg)")
        for i, (run, lab, U, vm, s) in enumerate(got):
            ax.scatter(X[bn, 0] + U[bn, 0], X[bn, 1] + U[bn, 1], s=4, color=COL[i], label="bladder " + lab)
            ax.scatter(X[cn, 0] + U[cn, 0], X[cn, 1] + U[cn, 1], s=2, marker="x", color=COL[i], alpha=0.5)
        ax.axhline(0, color="k", lw=0.8, ls=":"); ax.axhspan(-25, 25, color="#eb6834", alpha=0.08)
        ax.set_xlabel("x posterior (mm)"); ax.set_ylabel("y along the leg (mm, + thigh)"); ax.set_aspect("equal")
        ax.set_title("Section near the mid-plane (z = 2.2 mm) at 21 % stance (dots bladder, x cover);\nshaded = fold band, dotted = knee line", fontsize=8)
        ax.legend(fontsize=6.5, loc="lower left"); save(fig, "section_midplane_21pct.png")
    # 4 HCC_P60: last converged state (W 13 %, 3.28 deg, 60 kPa) with the grid where the next step stopped
    rr = load("HCC_P60")
    sub = [int(r["subcase"]) for r in (rr or []) if r["name"] == "W 13%" and r["converged"]]
    if sub:
        s = sub[0]; res, _ = P.parse_out(os.path.join(R, "runs", "HCC_P60", "HCC_P60.OUT"), subs={s})
        if s in res:
            d = res[s]["disp"]; U = np.array([d.get(n + 1, np.zeros(6))[:3] for n in range(len(X))])
            vm = {}
            for tb in ("qstress", "tstress"):
                for eid, vals in res[s][tb].items():
                    if vals: vm[eid - 1] = max(vals)
            fig = plt.figure(figsize=(11, 6.5))
            g = 10899 - 1; Xg = X[g] + U[g]
            for i, (sel, ttl) in enumerate(((None, "bladder von Mises (MPa), cover transparent"),
                                            ("cov", "cover von Mises (MPa) - shank-end region"))):
                ax = fig.add_subplot(1, 2, i + 1, projection="3d")
                if sel is None:
                    vmax = max([vm.get(e, 0) for e in S["bl_body"]] or [1]); draw(ax, X, EL, S, U=U, val=vm, vmax=vmax, cmap="turbo")
                else:
                    ce = [e for e in S["cov_body"] + S["cov_cap"] + S.get("cov_flange", [])]
                    vmax = max([vm.get(e, 0) for e in ce] or [1])
                    Sc = {k: (v if k in ("cov_body", "cov_cap", "cov_flange") else []) for k, v in S.items() if isinstance(v, list)}
                    Sc["_cover_opaque"] = True
                    draw(ax, X, EL, Sc, U=U, val=vm, vmax=vmax, cmap="turbo")
                ax.computed_zorder = False
                ax.scatter([Xg[0]], [Xg[2]], [Xg[1]], s=140, color="magenta", edgecolors="k", marker="*", depthshade=False, zorder=20)
                ax.text(Xg[0], Xg[2], Xg[1] - 14, "grid 10899", fontsize=7, color="k", zorder=21,
                        bbox=dict(facecolor="white", edgecolor="magenta", pad=1.5))
                ax.set_title("HCC_P60, 13 %% stance (3.28 deg), 60 kPa - last converged state\n%s, max %.2f" % (ttl, vmax), fontsize=8)
                sm = plt.cm.ScalarMappable(cmap="turbo", norm=plt.Normalize(0, vmax)); sm.set_array([])
                fig.colorbar(sm, ax=ax, shrink=0.45)
            fig.savefig(os.path.join(OUT, "p60_13pct_stop_point.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
            print("figure p60_13pct_stop_point.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--skip_out", action="store_true"); a = ap.parse_args()
    angle_cases(); cycles(); pv(); solver_effort()
    if not a.skip_out:
        pictures()
