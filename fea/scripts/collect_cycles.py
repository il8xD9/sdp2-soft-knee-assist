# -*- coding: utf-8 -*-
r"""Collects the gait-cycle and fixed-angle runs and compares, frame by frame, the knee moment of the FEA with the hand
calculation (Model B, M = p k, k = 206 990 mm3 -> 0.20699 N m per kPa).
  device moment  M_dev = M_knee(p, theta) - M_knee(0, theta): the vented run HCC_P0 at the same stance frame (after the
                 peak angle: its loading branch, interpolated by knee angle, --p0_load_branch).
  fold state     --state_flag marks frames where the folded bladder sits in another stable shape (volume step > 2.5 mL).
Reads runs/<run>/<run>_results.csv (post_process.py).
Output: results/tables/cycle_moment.csv, margin_moment.csv, cycle_summary.csv; results/figures/cycle_HCC.png.
Usage: python -P collect_cycles.py --ref_cyc HCC --ref_ang HC --p0_load_branch --stance_max 36 --state_flag"""
import argparse, csv, math, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K_HC = 206990.0e-9 * 1000.0      # m3 * Pa/kPa -> N m per kPa (0.20699)
PS = ["P0", "P20", "P40", "P60", "P80", "P100", "PROJ"]


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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="")
    ap.add_argument("--ref_cyc", default="B0C"); ap.add_argument("--ref_ang", default="B0")   # fixed reference = HCC / HC
    ap.add_argument("--p0_load_branch", action="store_true")   # after the peak angle the vented P0 = loading branch by angle
    ap.add_argument("--stance_max", type=int, default=None)   # cycles stop at 36 % (make_deck --cyc_end 36)
    ap.add_argument("--state_flag", action="store_true")   # flag squeezed fold states per run
    a = ap.parse_args()
    td = os.path.join(R, "results", "tables"); idir = os.path.join(R, "results", "figures")
    os.makedirs(td, exist_ok=True); os.makedirs(idir, exist_ok=True)
    out, summ = [], []
    for fam, label in ((a.ref_cyc, "idealised reference (rigid halves, bonded)"),):
        runs = {p: load("%s_%s" % (fam, p)) for p in PS}
        base = runs["P0"]
        # vented reference by knee angle (fallback when the P0 frame itself did not converge, e.g. the empty bladder unfolding)
        import numpy as np
        bp = sorted((r["theta"], r["M_knee_ext_Nm"]) for r in (base or []) if r["converged"] and r["kind"] in ("F", "W", "V"))
        fpk = None
        if a.p0_load_branch and base:
            # elastic + frictionless model -> M0 depends on the angle only; the empty bladder switched branch (snap)
            # right after the peak angle, so every frame after the peak uses the converged loading branch, by angle
            cyc = [r for r in base if r["kind"] in ("S", "F", "W", "V")]
            fpk = int(max(cyc, key=lambda r: r["theta"])["frame"])
            bp = sorted({round(r["theta"], 6): r["M_knee_ext_Nm"] for r in cyc
                         if r["converged"] and int(r["frame"]) <= fpk}.items())
        def m0_interp(th):
            if len(bp) < 2 or th < bp[0][0] - 1e-9 or th > bp[-1][0] + 1e-9:
                return None
            return float(np.interp(th, [a for a, _ in bp], [b for _, b in bp]))
        for p in PS:
            rr = runs[p]
            if rr is None:
                summ.append(dict(family=fam, run="%s_%s" % (fam, p), status="not run")); continue
            dev = []
            for i, r in enumerate(rr):
                if r["kind"] not in ("F", "W", "V", "S"):
                    continue
                if a.stance_max is not None and int(r["frame"]) > a.stance_max:   # report up to 36 % only
                    continue
                bm = [q for q in (base or []) if q["kind"] == r["kind"] and int(q["frame"]) == int(r["frame"])]
                b = bm[-1] if bm else None                  # P0 matched by phase and stance frame (fill steps)
                m = r.get("M_knee_ext_Nm") if r["converged"] else None
                if fpk is not None and int(r["frame"]) > fpk:
                    mv = m0_interp(r["theta"]); src = "P0 loading branch by angle" if mv is not None else "none"
                elif b is not None and b["converged"]:
                    mv, src = b["M_knee_ext_Nm"], "P0 same frame"
                else:
                    mv = m0_interp(r["theta"]); src = "P0 interpolated by angle" if mv is not None else "none"
                md = (m - mv) if (m is not None and mv is not None) else None
                hc = r["p_kPa"] * K_HC
                row = dict(family=fam, model=label, run="%s_%s" % (fam, p), subcase=int(r["subcase"]), phase=r["kind"],
                           stance_pct=int(r["frame"]), time_ms=r["ms"], theta_deg=r["theta"], p_kPa=r["p_kPa"],
                           M_knee_Nm=m, M_vented_Nm=mv, vented_reference=src,
                           M_device_Nm=md, M_handcalc_Nm=hc, ratio_FEA_to_hc=(md / hc if md is not None and hc > 1e-9 else None),
                           V_bladder_mL=r.get("V_bladder_mid_cm3"), slip_maxabs_mm=r.get("slip_y_maxabs_mm"),
                           p_skin_under_bladder_peak_kPa=r.get("p_under_bladder_peak_kPa"))
                out.append(row)
                if r["kind"] == "W":
                    dev.append(row)
            if a.state_flag:
                # fold-state level along the run. A step where the bladder volume drops > 2.5 cm3 while the
                # moment rises > 15 % (pressure not falling by > 1 kPa) = the bladder squeezed into another fold state (level + 1);
                # the reverse (volume up > 2.5 cm3, moment down > 12 %, pressure not rising by > 2.5 kPa) = level - 1.
                # Level 0 = the state at the window onset (W 13 %); + = squeezed (less volume), - = relaxed (more volume).
                mine = [o for o in out if o["run"] == "%s_%s" % (fam, p) and o["phase"] in ("F", "W")]
                lv, prev, lvls = 0, None, []
                for o in mine:
                    if o["M_knee_Nm"] is None or o["V_bladder_mL"] in (None, ""):
                        lvls.append(None); continue
                    if prev is not None:
                        dV = float(o["V_bladder_mL"]) - float(prev["V_bladder_mL"]); dP = o["p_kPa"] - prev["p_kPa"]
                        rel = (o["M_knee_Nm"] - prev["M_knee_Nm"]) / max(abs(prev["M_knee_Nm"]), 1e-9)
                        if dV < -2.5 and rel > 0.15 and dP > -1.0:
                            lv += 1
                        elif dV > 2.5 and rel < -0.12 and dP < 2.5:
                            lv -= 1
                    lvls.append(lv); prev = o
                wl = [x for o, x in zip(mine, lvls) if o["phase"] == "W" and x is not None]
                lref = wl[0] if wl else 0          # level 0 = the state reached after the fill, at the window onset (W 13 %)
                for o, x in zip(mine, lvls):
                    o["fold_state"] = (x - lref) if x is not None else None
                    o["state_note"] = ("" if x is None or x == lref else
                                       "squeezed fold state (+, higher energy) - not used for the ratio" if x > lref else
                                       "relaxed fold state (-, lower energy) - reported separately, not used for the ratio")
                dev = [d for d in dev if d.get("fold_state") == 0]
            cw = [d for d in dev if d["M_device_Nm"] is not None]
            pk = [d for d in dev if d["stance_pct"] == 21]
            summ.append(dict(family=fam, run="%s_%s" % (fam, p), status="%d/%d window frames" % (len(cw), len(dev)),
                             M_device_21pct_Nm=(pk[0]["M_device_Nm"] if pk else None), M_hc_21pct_Nm=(pk[0]["M_handcalc_Nm"] if pk else None),
                             ratio_21pct=(pk[0]["ratio_FEA_to_hc"] if pk else None),
                             M_device_window_max_Nm=(max(d["M_device_Nm"] for d in cw) if cw else None)))
    mg = []
    for fam in (a.ref_ang, "REAL"):
        for ang in ("3.0", "7.3", "8.6", "9.8", "13.0", "16.0", "19.0"):
            rr = load("%s_A%s" % (fam, ang))
            if rr is None:
                mg.append(dict(run="%s_A%s" % (fam, ang), status="not run")); continue
            vb = [r for r in rr if r["kind"] == "S" and r["converged"]]
            m0 = vb[-1]["M_knee_ext_Nm"] if vb and abs(vb[-1]["theta"] - rr[-1]["theta"]) < 1e-6 else None   # vented at the case angle
            for r in rr:
                if r["kind"] == "W":
                    md = (r["M_knee_ext_Nm"] - m0) if (r["converged"] and m0 is not None) else None
                    hc = r["p_kPa"] * K_HC
                    mg.append(dict(run="%s_A%s" % (fam, ang), status="ok" if r["converged"] else "not converged", theta_deg=r["theta"],
                                   p_kPa=r["p_kPa"], M_device_Nm=md, M_vented_before_Nm=m0, M_handcalc_Nm=hc,
                                   ratio_FEA_to_hc=(md / hc if isinstance(md, float) and hc > 0 else None)))
    for nm, rows in (("cycle_moment.csv", out), ("cycle_summary.csv", summ), ("margin_moment.csv", mg)):
        keys = []
        for r in rows:
            keys += [k for k in r if k not in keys]
        with open(os.path.join(td, nm), "w", newline="") as fh:
            w = csv.DictWriter(fh, keys); w.writeheader(); w.writerows(rows)
        print("written", os.path.join(td, nm), len(rows))
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        for fam in (a.ref_cyc,):
            fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
            for p in PS:
                d = [r for r in out if r["run"] == "%s_%s" % (fam, p) and r["M_device_Nm"] is not None]
                if not d: continue
                l, = ax[0].plot([r["stance_pct"] for r in d], [r["M_device_Nm"] for r in d], "-o", ms=3, label=p)
                ax[0].plot([r["stance_pct"] for r in d], [r["M_handcalc_Nm"] for r in d], "--", color=l.get_color(), lw=0.8)
                ax[1].plot([r["stance_pct"] for r in d], [r["p_kPa"] for r in d], color=l.get_color(), label=p)
            ax[0].axvspan(13, 36, color="0.92"); ax[0].set_xlabel("% stance"); ax[0].set_ylabel("device moment about the knee centre (N m)")
            ax[0].set_title("%s: FEA (solid) vs hand calc p k (dashed)" % fam); ax[0].legend(fontsize=7)
            ax[1].axvspan(13, 36, color="0.92"); ax[1].set_xlabel("% stance"); ax[1].set_ylabel("bladder pressure (kPa)"); ax[1].legend(fontsize=7)
            fig.tight_layout(); fig.savefig(os.path.join(idir, "cycle_%s.png" % fam), dpi=150); plt.close(fig)
    except Exception as ex:
        print("plots not written:", ex)


if __name__ == "__main__":
    main()
