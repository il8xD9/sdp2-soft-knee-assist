#!/usr/bin/env python3
"""
05_postprocess_opensim_results.py
---------------------------------
PURPOSE : Turn the OpenSim static-optimization output (written by run_opensim_knee_SO.py)
          into the muscle results: quadriceps force & activation curves, muscle force
          reduction (%) due to the actuator, antagonist (hamstring/gastrocnemius) force,
          reserve check, and the completed result tables.
RUN ONLY AFTER the OpenSim run produced Results/OpenSim_SO/ALL_conditions_SO_summary.csv.
          If that file is missing the script stops and writes nothing (no placeholder data).
INPUT   : Results/OpenSim_SO/ALL_conditions_SO_summary.csv, ALL_conditions_SO_long.csv,
          Results/metrics_all_conditions_computed.csv (from 04_...)
OUTPUT  : Graphs/Fig03, Fig04, Fig08, Fig11 (+ Fig14 antagonists), Tables/T10..T13 (+ xlsx sheets),
          Results/muscle_metrics_all_conditions.csv
DEFINITIONS (same sign / unit on both sides of every equation):
  Muscle Force Reduction (%) = (F_baseline - F_assisted) / F_baseline x 100
     F = peak force in early stance (1-50 % stance; 0-30 %GC for Winter)  [N, tension +]
     and, second definition, F = force impulse  integral F dt  over the actuator window [N.s]
  Quadriceps = rectus femoris + vastus lateralis + vastus medialis + vastus intermedius
"""
import os
import sys
import numpy as np
import pandas as pd
from plot_style import plt, COL, LAB, SHORT, DEVICE, BASE, ASSIST, INK, INK2, MUTED, finish, zero_line

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json as _json
_ACT = _json.load(open(os.path.join(ROOT, "Actuator", "actuator_parameters.json")))
AP = _ACT["alpha_primary"]
ATAG = "a%03d" % int(round(AP * 100))
APS = "%.2f" % AP
SO = os.path.join(ROOT, "Results", "OpenSim_SO")
TAB = os.path.join(ROOT, "Tables")
GRA = os.path.join(ROOT, "Graphs")
RES = os.path.join(ROOT, "Results")
summ_path = os.path.join(SO, "ALL_conditions_SO_summary.csv")
if not os.path.isfile(summ_path):
    sys.exit("OpenSim results not found (%s).\nRun Scripts/run_opensim_knee_SO.py in OpenSim first. "
             "Nothing was written." % summ_path)

S = pd.read_csv(summ_path)
S["x"] = S["x"].astype(float)
L = pd.read_csv(os.path.join(SO, "ALL_conditions_SO_long.csv"))
L["x"] = L["x"].astype(float)
man = pd.read_csv(os.path.join(ROOT, "Simulations", "conditions_manifest.csv"))
met = pd.read_csv(os.path.join(RES, "metrics_all_conditions_computed.csv"))
EPOCHS = ["preop", "2months", "4months", "6months", "12months"]
ORDER = ["healthy"] + EPOCHS
MUS = [("RF", "Rectus femoris"), ("VL", "Vastus lateralis"), ("VM", "Vastus medialis"),
       ("VI", "Vastus intermedius")]
cid_of = {"healthy": "Healthy", "preop": "ACL_PreOp", "2months": "ACL_2Months",
          "4months": "ACL_4Months", "6months": "ACL_6Months", "12months": "ACL_12Months"}
NOTE = ("OpenSim gait2392 knee static optimization (activation^2 cost, rigid-tendon FLV); "
        "kinematics/moments = Buttner 2025 group means; 70 kg, 1.70 m.")


def base_id(k):
    return "Healthy_Baseline" if k == "healthy" else cid_of[k] + "_Baseline"


def asst_id(k, tag=None):
    tag = tag or ATAG
    return ("Healthy_Assisted_" if k == "healthy" else cid_of[k] + "_Assisted_") + tag


def trapz(y, x):
    y, x = np.asarray(y, float), np.asarray(x, float)
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))


def cond(cid):
    return S[S.cond_id == cid].sort_values("x")


ANTAG_KEYS = ("bifem", "semimem", "semiten", "gas", "grac", "sar")

# ------------------------------------------------------------------ per-condition metrics
rows = []
for cid in S.cond_id.unique():
    d = cond(cid)
    xa = man[man.cond_id == cid].x_axis.iloc[0]
    early = d.x <= (30 if xa == "pct_GC" else 50)
    win = d.device_torque_Nm > 1e-6          # model read-back has ~1e-16 noise at the window edge
    t = d.time_s.values
    r = {"cond_id": cid}
    for k, _ in MUS + [("quadriceps", "")]:
        F = d["F_%s_N" % k].values
        r["peak_F_%s_early_N" % k] = F[early.values].max()
        r["peak_F_%s_N" % k] = F.max()
        r["F_%s_impulse_window_Ns" % k] = trapz(np.where(win, F, 0), t)
        r["F_%s_impulse_stance_Ns" % k] = trapz(F, t)
        if k != "quadriceps":
            a = d["a_%s" % k].values
            r["peak_a_%s_early" % k] = a[early.values].max()
            r["mean_a_%s_window" % k] = a[win.values].mean() if win.any() else np.nan
    r["peak_a_quadriceps_mean_early"] = np.max(np.mean([d["a_%s" % k].values for k, _ in MUS], axis=0)[early.values])
    r["max_abs_reserve_Nm"] = d.reserve_Nm.abs().max()
    r["max_abs_residual_Nm"] = d.residual_Nm.abs().max()
    ll = L[(L.cond_id == cid)]
    ant = ll[ll.muscle.str.contains("|".join(ANTAG_KEYS))]
    if len(ant):
        tot = ant.groupby("x").force_N.sum().reindex(d.x.values).values
        r["peak_antagonist_force_in_window_N"] = np.nanmax(np.where(win.values, tot, np.nan)) if win.any() else np.nanmax(tot[early.values])
        r["peak_antagonist_force_early_N"] = np.nanmax(tot[early.values])
    rows.append(r)
mm = pd.DataFrame(rows)
mm.to_csv(os.path.join(RES, "muscle_metrics_all_conditions.csv"), index=False)


def g(cid):
    return mm[mm.cond_id == cid].iloc[0]


def antag_total(cid):
    """Total antagonist (hamstrings, gastrocnemius, gracilis, sartorius) force per frame."""
    ll = L[(L.cond_id == cid)]
    ant = ll[ll.muscle.str.contains("|".join(ANTAG_KEYS))]
    return ant.groupby("x").force_N.sum().reindex(cond(cid).x.values).values


# ------------------------------------------------------------------ reductions
red = []
for k in ORDER:
    b = g(base_id(k))
    sub = man[(man.epoch == k) & (man.assisted == 1) & (man.group != "Healthy_Winter")]
    for cid in sub.sort_values(["alpha", "profile_type"]).cond_id:
        if cid not in set(mm.cond_id):
            continue
        a = g(cid)
        alpha = man[man.cond_id == cid].alpha.iloc[0]
        rec = {"Condition": LAB[k], "alpha": round(alpha, 3), "cond_id": cid,
               "profile_type": man[man.cond_id == cid].profile_type.iloc[0]}
        for m, _ in MUS + [("quadriceps", "")]:
            fb, fa = b["peak_F_%s_early_N" % m], a["peak_F_%s_early_N" % m]
            ib, ia = b["F_%s_impulse_window_Ns" % m], a["F_%s_impulse_window_Ns" % m]
            # baseline impulse must be evaluated over the SAME window as the assisted case
            dB, dA = cond(base_id(k)), cond(cid)
            w = dA.device_torque_Nm.values > 1e-6
            ib = trapz(np.where(w, dB["F_%s_N" % m].values, 0), dB.time_s.values)
            rec["%s peak baseline (N)" % m] = round(fb, 1)
            rec["%s peak assisted (N)" % m] = round(fa, 1)
            rec["%s MFR peak (%%)" % m] = round(100 * (fb - fa) / fb, 1) if fb > 1e-6 else np.nan
            rec["%s MFR window impulse (%%)" % m] = round(100 * (ib - ia) / ib, 1) if ib > 1e-6 else np.nan
        # antagonists: baseline evaluated over the SAME window as the assisted case
        wA = cond(cid).device_torque_Nm.values > 1e-6
        tb, ta = antag_total(base_id(k)), antag_total(cid)
        rec["Peak antagonist force in window, assisted (N)"] = round(np.nanmax(np.where(wA, ta, np.nan)), 1) if wA.any() else np.nan
        rec["Peak antagonist force in window, baseline (N)"] = round(np.nanmax(np.where(wA, tb, np.nan)), 1) if wA.any() else np.nan
        red.append(rec)
red = pd.DataFrame(red)

# ------------------------------------------------------------------ completed tables
NA = "-"
t1, t2, t3 = [], [], []
for k in ORDER:
    for cid in (base_id(k), asst_id(k)):
        q = met[met.cond_id == cid].iloc[0]
        u = g(cid)
        rr = red[red.cond_id == asst_id(k)].iloc[0]
        assisted = bool(q.assisted)
        t1.append({"Condition": LAB[k] + (" + Actuator" if assisted else " (no actuator)"),
                   "Peak net knee ext. moment (N.m)": round(q.peak_ext_moment_Nm, 2),
                   "Peak biological knee ext. moment, early stance (N.m)": round(q.peak_bio_ext_moment_early_Nm, 2),
                   "Peak quadriceps force, early stance (N)": round(u.peak_F_quadriceps_early_N, 1),
                   "Peak actuator torque (N.m)": round(q.act_peak_torque_Nm, 2),
                   "Knee moment reduction, early-stance peak (%)": round(q.KMR_peak_pct, 1) if assisted else NA,
                   "Quadriceps force reduction, peak (%)": rr["quadriceps MFR peak (%)"] if assisted else NA,
                   "Quadriceps force reduction, window impulse (%)": rr["quadriceps MFR window impulse (%)"] if assisted else NA})
        t2.append({"Condition": LAB[k] + (" + Actuator" if assisted else " (no actuator)"),
                   "Stance knee ROM (deg)": round(q.ROM_deg, 2),
                   "Peak net knee ext. moment (N.m)": round(q.peak_ext_moment_Nm, 2),
                   "Peak quadriceps force (N)": round(u.peak_F_quadriceps_early_N, 1),
                   "Peak activation RF / VL / VM / VI": "%.3f / %.3f / %.3f / %.3f" % (
                       u.peak_a_RF_early, u.peak_a_VL_early, u.peak_a_VM_early, u.peak_a_VI_early),
                   "Peak mean quadriceps activation": round(u.peak_a_quadriceps_mean_early, 3),
                   "Max |reserve| (N.m)": round(u.max_abs_reserve_Nm, 3)})
    b, a = g(base_id(k)), g(asst_id(k))
    rr = red[red.cond_id == asst_id(k)].iloc[0]
    t3.append({"Group": LAB[k],
               "Quad force without (N)": round(b.peak_F_quadriceps_early_N, 1),
               "Quad force with (N)": round(a.peak_F_quadriceps_early_N, 1),
               "Quad MFR peak (%)": rr["quadriceps MFR peak (%)"],
               "RF / VL / VM / VI MFR peak (%)": "%s / %s / %s / %s" % (rr["RF MFR peak (%)"], rr["VL MFR peak (%)"],
                                                                     rr["VM MFR peak (%)"], rr["VI MFR peak (%)"]),
               "Quad MFR window impulse (%)": rr["quadriceps MFR window impulse (%)"],
               "Antagonist peak in window without / with (N)": "%s / %s" % (
                   rr["Peak antagonist force in window, baseline (N)"], rr["Peak antagonist force in window, assisted (N)"])})
tables = {"T10_Main_Results_with_OpenSim": pd.DataFrame(t1),
          "T11_Kinematics_Muscle_Activation": pd.DataFrame(t2),
          "T12_Healthy_vs_ACL_Muscle": pd.DataFrame(t3),
          "T13_Muscle_Force_Reduction_All": red}
for n, df in tables.items():
    df.to_csv(os.path.join(TAB, n + ".csv"), index=False)
xl = os.path.join(TAB, "OpenSim_Project_Results.xlsx")
mode = "a" if os.path.isfile(xl) else "w"
kw = {"if_sheet_exists": "replace"} if mode == "a" else {}
with pd.ExcelWriter(xl, engine="openpyxl", mode=mode, **kw) as xw:
    for n, df in tables.items():
        df.to_excel(xw, sheet_name=n[:31], index=False)
print(pd.DataFrame(t3).to_string(index=False))

# ------------------------------------------------------------------ figures
# Fig 3 - quadriceps force vs stance (baseline) : total + per-muscle small multiples
fig, axs = plt.subplots(1, 5, figsize=(17, 3.8), sharex=True)
for ax, (m, name) in zip(axs, [("quadriceps", "Quadriceps total")] + MUS):
    for k in ORDER:
        d = cond(base_id(k))
        ax.plot(d.x, d["F_%s_N" % m], color=COL[k], lw=2.3 if k == "healthy" else 1.6, label=LAB[k])
    ax.set(title=name, xlabel="Stance (%)", xlim=(0, 60))
    ax.set_ylim(bottom=0)
axs[0].set_ylabel("Muscle force (N)")
axs[0].legend(loc="upper right", fontsize=7)
finish(fig, os.path.join(GRA, "Fig03_Quadriceps_Force_vs_Gait_Cycle.png"), NOTE)

# Fig 4 - activation
fig, axs = plt.subplots(1, 4, figsize=(15, 3.8), sharey=True)
for ax, (m, name) in zip(axs, MUS):
    for k in ORDER:
        d = cond(base_id(k))
        ax.plot(d.x, d["a_%s" % m], color=COL[k], lw=2.3 if k == "healthy" else 1.6, label=LAB[k])
    ax.set(title=name, xlabel="Stance (%)", xlim=(0, 60))
axs[0].set_ylabel("Activation (0-1)")
axs[0].set_ylim(bottom=0)
axs[0].legend(loc="upper right", fontsize=7)
finish(fig, os.path.join(GRA, "Fig04_Quadriceps_Activation_vs_Gait_Cycle.png"), NOTE)

# Fig 8 - quad force without vs with (small multiples)
fig, axs = plt.subplots(2, 3, figsize=(12.5, 7.0), sharex=True)
for ax, k in zip(axs.ravel(), ORDER):
    b, a = cond(base_id(k)), cond(asst_id(k))
    ax.fill_between(b.x, a.F_quadriceps_N, b.F_quadriceps_N, where=a.device_torque_Nm > 0,
                    color=DEVICE, alpha=0.18, lw=0)
    ax.plot(b.x, b.F_quadriceps_N, color=BASE, lw=1.9, label="Without actuator")
    ax.plot(a.x, a.F_quadriceps_N, color=ASSIST, lw=1.9, label="With actuator (alpha %s)" % APS)
    rr = red[red.cond_id == asst_id(k)].iloc[0]
    ax.set_title("%s   (peak -%.0f %%)" % (LAB[k], rr["quadriceps MFR peak (%)"]), fontsize=10)
    ax.set_xlim(0, 60)
for ax in axs[1]:
    ax.set_xlabel("Stance (%)")
for ax in axs[:, 0]:
    ax.set_ylabel("Quadriceps force RF+VL+VM+VI (N)")
axs[0, 0].legend(loc="upper right", fontsize=8)
finish(fig, os.path.join(GRA, "Fig08_Quadriceps_Force_Without_vs_With_Actuator.png"), NOTE)

# Fig 11 - muscle force reduction
fig, ax = plt.subplots(figsize=(11, 4.4))
xi = np.arange(len(ORDER))
bw = 0.16
shades = {"quadriceps": "#0d366b", "RF": "#2a78d6", "VL": "#5598e7", "VM": "#86b6ef", "VI": "#b7d3f6"}
for j, m in enumerate(["quadriceps", "RF", "VL", "VM", "VI"]):
    vals = [red[red.cond_id == asst_id(k)]["%s MFR peak (%%)" % m].iloc[0] for k in ORDER]
    ax.bar(xi + (j - 2) * (bw + 0.01), vals, width=bw, color=shades[m],
           label=dict(MUS).get(m, "Quadriceps total"))
    if m == "quadriceps":
        for xv, v in zip(xi, vals):
            ax.text(xv - 2 * (bw + 0.01), v + 2, "%.0f" % v, ha="center", fontsize=7.5, color=INK)
ax.set_xticks(xi)
ax.set_xticklabels([SHORT[k] for k in ORDER])
ax.set(ylabel="Peak force reduction (%)", title="Muscle force reduction due to the actuator (alpha = %s, early stance peak)" % APS)
zero_line(ax)
ax.legend(loc="upper center", ncol=5, fontsize=8, bbox_to_anchor=(0.5, -0.1))
finish(fig, os.path.join(GRA, "Fig11_Muscle_Force_Reduction_by_Actuator.png"), NOTE)

# Fig 14 - antagonist force (over-assistance check)
fig, axs = plt.subplots(1, 6, figsize=(17, 3.4), sharey=True)
for ax, k in zip(axs, ORDER):
    for cid, colr, lab in [(base_id(k), BASE, "without"), (asst_id(k), ASSIST, "with actuator")]:
        ll = L[(L.cond_id == cid) & L.muscle.str.contains("|".join(ANTAG_KEYS))]
        tot = ll.groupby("x").force_N.sum()
        ax.plot(tot.index, tot.values, color=colr, lw=1.7, label=lab)
    ax.set(title=LAB[k], xlabel="Stance (%)", xlim=(0, 60))
axs[0].set_ylabel("Hamstrings + gastrocnemius force (N)")
axs[0].legend(loc="upper left", fontsize=7)
finish(fig, os.path.join(GRA, "Fig14_Antagonist_Force_Without_vs_With_Actuator.png"),
       NOTE + " Knee-only SO: ankle/hip moments not constrained.")
# Fig 20 - alpha sweep of quadriceps force reduction (requested vs delivered)
import json
ALPHAS = json.load(open(os.path.join(ROOT, "Actuator", "actuator_parameters.json")))["alpha_sweep"]
sw = []
for k in ORDER:
    for a_ in ALPHAS:
        rid = asst_id(k, "a%03d" % int(round(a_ * 100)))
        if rid not in set(red.cond_id):
            continue
        lid = man[man.cond_id == rid].device_limited_cond_id.iloc[0]
        rr = red[red.cond_id == rid].iloc[0]
        ll = red[red.cond_id == lid].iloc[0] if lid in set(red.cond_id) else rr
        rec = {"Group": LAB[k], "group_key": k, "alpha": a_}
        for m, _ in MUS + [("quadriceps", "")]:
            rec["%s MFR peak requested (%%)" % m] = rr["%s MFR peak (%%)" % m]
            rec["%s MFR peak delivered (%%)" % m] = ll["%s MFR peak (%%)" % m]
            rec["%s peak force delivered (N)" % m] = ll["%s peak assisted (N)" % m]
        rec["Antagonist peak in window, delivered (N)"] = ll["Peak antagonist force in window, assisted (N)"]
        sw.append(rec)
sw = pd.DataFrame(sw)
sw.drop(columns=["group_key"]).to_csv(os.path.join(TAB, "T14_Alpha_Sweep_Muscle.csv"), index=False)
with pd.ExcelWriter(xl, engine="openpyxl", mode="a", if_sheet_exists="replace") as xw:
    sw.drop(columns=["group_key"]).to_excel(xw, sheet_name="T14_Alpha_Sweep_Muscle", index=False)
    sw.pivot(index="alpha", columns="Group", values="quadriceps MFR peak delivered (%)")[
        [LAB[k] for k in ORDER]].to_excel(xw, sheet_name="T14b_Quad_MFR_vs_alpha")
fig, axs = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
for ax, col, ttl in [(axs[0], "quadriceps MFR peak requested (%)", "A  Requested torque (ideal)"),
                     (axs[1], "quadriceps MFR peak delivered (%)", "B  Delivered torque (device-limited)")]:
    for k in ORDER:
        d = sw[sw.group_key == k]
        ax.plot(d.alpha, d[col], color=COL[k], lw=1.7, marker="o", ms=3.5, label=LAB[k])
    ax.axhline(100, color=INK2, lw=0.9)
    ax.set_xticks(ALPHAS)
    ax.set_xticklabels(["%.2g" % a_ for a_ in ALPHAS], fontsize=7.5, rotation=45)
    ax.set(title=ttl, xlabel="Assistance fraction alpha (-)")
axs[0].set_ylabel("Peak quadriceps force reduction (%)")
h_, l_ = axs[0].get_legend_handles_labels()
fig.legend(h_, l_, loc="upper center", ncol=6, bbox_to_anchor=(0.5, 1.09), fontsize=8)
fig.subplots_adjust(bottom=0.22)
finish(fig, os.path.join(GRA, "Fig20_Alpha_Sweep_Quadriceps_Force_Reduction.png"), NOTE)
print("muscle figures and tables written.")
