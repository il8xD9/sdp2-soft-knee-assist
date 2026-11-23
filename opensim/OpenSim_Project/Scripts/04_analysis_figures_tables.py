#!/usr/bin/env python3
"""
04_analysis_figures_tables.py
-----------------------------
PURPOSE : Compute every result that can be obtained WITHOUT running OpenSim
          (knee angle, net knee moment, actuator torque / force / pressure / power /
          work / impulse, biological knee moment with the device, knee-moment
          reduction, restoration view, over-assistance check) for all conditions,
          and draw the corresponding figures and tables.
          Muscle forces / activations are NOT computed here (they need OpenSim:
          run_opensim_knee_SO.py, then 05_postprocess_opensim_results.py).
INPUT   : Simulations/conditions_manifest.csv + Simulations/**/<cond>_inputs_and_actuator.csv
          Input_Data/buttner2025_*.csv, healthy_winter1987_full_gait.csv
OUTPUT  : Results/*.csv, Tables/*.csv + Tables/OpenSim_Project_Results.xlsx, Graphs/*.png
SIGN CONVENTIONS (checked before every equation):
  knee flexion angle      : + flexion, 0 = full extension (project Table G0)
  net knee moment         : INTERNAL, extension +, N.m  (Buttner/Winter internal; == gait2392
                            knee_angle_r generalized force, extension +)
  actuator torque         : extension + (CoordinateActuator on knee_angle_r, control >= 0)
  biological knee moment  : M_bio = M_net - T_device   (same axis, same sign, same unit)
  power                   : P = T_device * omega_ext, omega_ext = -d(flexion)/dt [rad/s]
"""
import os
import json
import numpy as np
import pandas as pd
from plot_style import plt, COL, LAB, SHORT, DEVICE, BASE, ASSIST, INK, INK2, MUTED, GRID, finish, zero_line

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM = os.path.join(ROOT, "Simulations")
RES = os.path.join(ROOT, "Results")
TAB = os.path.join(ROOT, "Tables")
GRA = os.path.join(ROOT, "Graphs")
IN = os.path.join(ROOT, "Input_Data")
for d in (RES, TAB, GRA):
    os.makedirs(d, exist_ok=True)

M_BODY, H_BODY, G = 70.0, 1.70, 9.80665
act = json.load(open(os.path.join(ROOT, "Actuator", "actuator_parameters.json")))
T_MAX = act["max_torque_Nm"]
AP = act["alpha_primary"]
ATAG = "a%03d" % int(round(AP * 100))
APS = "%.2f" % AP
TMS = "%.2f N.m" % T_MAX
man = pd.read_csv(os.path.join(SIM, "conditions_manifest.csv"))
EPOCHS = ["preop", "2months", "4months", "6months", "12months"]
ORDER = ["healthy"] + EPOCHS
NOTE = ("Computed from input data (Buttner 2025 group means; 70 kg, 1.70 m). "
        "Not an OpenSim muscle simulation.")


def load(cid):
    row = man[man.cond_id == cid].iloc[0]
    return pd.read_csv(os.path.join(SIM, row.folder, cid + "_inputs_and_actuator.csv")), row


def trapz(y, x):
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))


# ------------------------------------------------------------------------------------
# 1. METRICS PER CONDITION
# ------------------------------------------------------------------------------------
rows = []
for _, r in man.iterrows():
    d, _ = load(r.cond_id)
    x = d.iloc[:, 0].values
    t = d.time_s.values
    kfa = d.knee_flexion_deg.values
    m = d.net_knee_moment_Nm.values
    tau = d.actuator_torque_Nm.values
    mb = d.biological_knee_moment_Nm.values
    P = d.actuator_power_W.values
    stance = x <= (60 if r.x_axis == "pct_GC" else 100)
    early = x <= (30 if r.x_axis == "pct_GC" else 50)
    win = tau > 0
    i_pk = int(np.argmax(np.where(early, m, -np.inf)))      # baseline early-stance extension peak
    pos = np.clip(m, 0, None)
    rec = {
        "cond_id": r.cond_id, "label": r.label, "group": r.group, "epoch": r.epoch,
        "assisted": int(r.assisted), "alpha": r.alpha, "primary_12": int(r.primary_12),
        "x_axis": r.x_axis,
        # --- knee angle
        "peak_flexion_deg": kfa.max(), "pct_at_peak_flexion": x[np.argmax(kfa)],
        "loading_response_peak_flexion_deg": kfa[early].max(),
        "pct_at_LR_peak": x[early][np.argmax(kfa[early])],
        "peak_extension_deg(min_flexion)": kfa.min(), "pct_at_peak_extension": x[np.argmin(kfa)],
        "ROM_deg": kfa.max() - kfa.min(),
        "LR_flexion_excursion_deg": kfa[early].max() - kfa[0],
        # --- net knee moment (internal, ext +)
        "peak_ext_moment_Nm": m.max(), "peak_ext_moment_Nm_per_kg": m.max() / M_BODY,
        "pct_at_peak_ext_moment": x[np.argmax(m)],
        "peak_flex_moment_Nm": m.min(), "peak_flex_moment_Nm_per_kg": m.min() / M_BODY,
        "pct_at_peak_flex_moment": x[np.argmin(m)],
        "early_stance_ext_peak_Nm": m[i_pk], "pct_early_peak": x[i_pk],
        # --- actuator
        "act_peak_torque_Nm": tau.max(), "pct_at_act_peak": x[np.argmax(tau)] if tau.max() > 0 else np.nan,
        "act_peak_force_N": d.actuator_force_N.max(), "act_peak_pressure_kPa": d.actuator_pressure_kPa.max(),
        "act_peak_pos_power_W": P.max(), "act_peak_neg_power_W": P.min(),
        "act_pos_work_J": trapz(np.clip(P, 0, None), t), "act_neg_work_J": trapz(np.clip(P, None, 0), t),
        "act_net_work_J": trapz(P, t),
        "act_angular_impulse_Nms": trapz(tau, t),
        "act_on_pct": x[win].min() if win.any() else np.nan,
        "act_off_pct": x[win].max() if win.any() else np.nan,
        "act_on_ms": 1000 * t[win].min() if win.any() else np.nan,
        "act_off_ms": 1000 * t[win].max() if win.any() else np.nan,
        "act_max_rise_rate_Nm_s": np.max(np.gradient(tau, t)) if win.any() else 0.0,
        "within_capability": bool(tau.max() <= T_MAX + 1e-6),
        # --- biological moment with device (H1: same gait, device shares the load)
        "peak_bio_ext_moment_Nm": mb.max(), "pct_at_peak_bio": x[np.argmax(mb)],
        "bio_moment_at_baseline_peak_Nm": mb[i_pk],
        "device_share_at_baseline_peak_pct": 100 * tau[i_pk] / m[i_pk] if m[i_pk] > 0 else np.nan,
        "peak_bio_ext_moment_early_Nm": mb[early].max(),
        "KMR_peak_pct": 100 * (m[early].max() - mb[early].max()) / m[early].max(),
        "KMR_at_baseline_peak_instant_pct": 100 * (m[i_pk] - mb[i_pk]) / m[i_pk],
        "KMR_window_impulse_pct": (100 * trapz(np.where(win, tau, 0), t) / trapz(np.where(win, pos, 0), t))
        if win.any() and trapz(np.where(win, pos, 0), t) > 0 else 0.0,
        "ext_moment_impulse_stance_Nms": trapz(pos, t),
        "bio_ext_moment_impulse_stance_Nms": trapz(np.clip(mb, 0, None), t),
        "over_assist_frames": int(np.sum(win & (mb < 0))),
        "over_assist_pct_of_window": 100 * np.sum(win & (mb < 0)) / max(np.sum(win), 1),
        "min_bio_moment_in_window_Nm": mb[win].min() if win.any() else np.nan,
        # --- restoration view (H2: device adds to the patient's own moment)
        "restored_net_peak_Nm(M+T)": (m + tau).max(),
    }
    rows.append(rec)
met = pd.DataFrame(rows)

# healthy reference peak for restoration / % healthy
h = met[met.cond_id == "Healthy_Baseline"].iloc[0]
met["peak_ext_moment_pct_of_healthy"] = 100 * met.peak_ext_moment_Nm / h.peak_ext_moment_Nm
met["restored_peak_pct_of_healthy"] = 100 * met["restored_net_peak_Nm(M+T)"] / h.peak_ext_moment_Nm

met.loc[met.group != "ACL", "restored_peak_pct_of_healthy"] = np.nan
met.loc[met.group != "ACL", "restored_net_peak_Nm(M+T)"] = np.nan
met.to_csv(os.path.join(RES, "metrics_all_conditions_computed.csv"), index=False)
# over-assistance guard (H1): where in the window is the ACL net moment already <= 0, and at
# which alpha does the device torque equal the net moment at the deficit peak
dfc = pd.read_csv(os.path.join(IN, "stance_deficit_table5A.csv"))
WINDOW = {"preop": (9, 37), "2months": (9, 44), "4months": (9, 44), "6months": (9, 44), "12months": (9, 40)}
guard = []
for e in EPOCHS:
    d, _ = load({"preop": "ACL_PreOp", "2months": "ACL_2Months", "4months": "ACL_4Months",
                 "6months": "ACL_6Months", "12months": "ACL_12Months"}[e] + "_Baseline")
    p = d.pct_stance.values
    full = dfc["dM_%s_BWh" % e].values * M_BODY * G * H_BODY
    lo, hi = WINDOW[e]
    w = (p >= lo) & (p <= hi) & (full > 0)
    mn = d.net_knee_moment_Nm.values
    a_safe_peak = mn[np.argmax(np.where(w, full, -1))] / full[w].max()
    nonpos = w & (mn <= 0)
    guard.append({"epoch": e, "window_pct_stance": "%d-%d" % (lo, hi),
                  "pct_of_window_with_ACL_net_moment_<=0": round(100 * nonpos.sum() / w.sum(), 1),
                  "stance_pct_with_net_<=0": ", ".join(str(int(v)) for v in p[nonpos]) or "-",
                  "alpha_where_device_equals_net_at_deficit_peak": round(a_safe_peak, 3),
                  "alpha_max_capability": round(act["alpha_max_per_epoch"][
                      {"preop": "Pre-op", "2months": "2 Months", "4months": "4 Months",
                       "6months": "6 Months", "12months": "12 Months"}[e]], 3)})
guard = pd.DataFrame(guard)
guard.to_csv(os.path.join(RES, "over_assistance_alpha_guard.csv"), index=False)
print(guard.to_string(index=False))

# ------------------------------------------------------------------------------------
# 2. TABLES
# ------------------------------------------------------------------------------------
NE = "see T12-T14 (OpenSim static optimisation)"
cid_of = {"healthy": "Healthy", "preop": "ACL_PreOp", "2months": "ACL_2Months",
          "4months": "ACL_4Months", "6months": "ACL_6Months", "12months": "ACL_12Months"}


def base_id(k):
    return "Healthy_Baseline" if k == "healthy" else cid_of[k] + "_Baseline"


def asst_id(k, tag=None):
    tag = tag or ATAG
    return ("Healthy_Assisted_" if k == "healthy" else cid_of[k] + "_Assisted_") + tag


def g(cid):
    return met[met.cond_id == cid].iloc[0]


t_main = []
for k in ORDER:
    for cid in (base_id(k), asst_id(k)):
        q = g(cid)
        t_main.append({
            "Condition": LAB[k] + (" + Actuator" if q.assisted else " (no actuator)"),
            "Peak net knee ext. moment (N.m)": round(q.peak_ext_moment_Nm, 2),
            "Peak biological knee ext. moment, early stance (N.m)": round(q.peak_bio_ext_moment_early_Nm, 2),
            "Peak quadriceps force (N)": NE,
            "Peak actuator torque (N.m)": round(q.act_peak_torque_Nm, 2),
            "Knee moment reduction, early-stance peak (%)": round(q.KMR_peak_pct, 1) if q.assisted else "-",
            "Knee moment reduction, window impulse (%)": round(q.KMR_window_impulse_pct, 1) if q.assisted else "-",
            "Muscle force reduction (%)": NE if q.assisted else "-"})
t_main = pd.DataFrame(t_main)

t_kin = []
for k in ORDER:
    for cid in (base_id(k), asst_id(k)):
        q = g(cid)
        t_kin.append({"Condition": LAB[k] + (" + Actuator" if q.assisted else " (no actuator)"),
                      "Stance knee ROM (deg)": round(q.ROM_deg, 2),
                      "Loading-response peak flexion (deg)": round(q.loading_response_peak_flexion_deg, 2),
                      "Peak extension, min flexion (deg)": round(q["peak_extension_deg(min_flexion)"], 2),
                      "Peak net knee ext. moment (N.m/kg)": round(q.peak_ext_moment_Nm_per_kg, 3),
                      "Peak net knee flex. moment (N.m/kg)": round(q.peak_flex_moment_Nm_per_kg, 3),
                      "Peak quadriceps force (N)": NE, "Peak quadriceps activation (-)": NE})
t_kin = pd.DataFrame(t_kin)

t_cmp = []
for k in ORDER:
    b, a = g(base_id(k)), g(asst_id(k))
    t_cmp.append({"Group": LAB[k],
                  "Peak flexion LR (deg)": round(b.loading_response_peak_flexion_deg, 2),
                  "Stance ROM (deg)": round(b.ROM_deg, 2),
                  "Peak ext. moment (N.m)": round(b.peak_ext_moment_Nm, 2),
                  "Peak ext. moment (% healthy)": round(b.peak_ext_moment_pct_of_healthy, 1),
                  "Peak flex. moment (N.m)": round(b.peak_flex_moment_Nm, 2),
                  "Actuator peak torque (N.m)": round(a.act_peak_torque_Nm, 2),
                  "Biological ext. moment WITH actuator, early-stance peak (N.m)": round(a.peak_bio_ext_moment_early_Nm, 2),
                  "Knee moment reduction peak (%)": round(a.KMR_peak_pct, 1),
                  "Knee moment reduction window (%)": round(a.KMR_window_impulse_pct, 1),
                  "Over-assisted window (%)": round(a.over_assist_pct_of_window, 1),
                  "Restored net peak M+T, H2 (% healthy)": round(a.restored_peak_pct_of_healthy, 1) if k != "healthy" else "-",
                  "Quadriceps force without / with": NE})
t_cmp = pd.DataFrame(t_cmp)

t_act = []
PTYPE_ORDER = {"requested": 0, "device_limited": 1, "capped": 2}
for k in ORDER:
    sub = man[(man.epoch == k) & (man.assisted == 1) & (man.group != "Healthy_Winter")].copy()
    sub["po"] = sub.profile_type.map(PTYPE_ORDER)
    for cid in sub.sort_values(["alpha", "po"]).cond_id:
        q = g(cid)
        ptype = man[man.cond_id == cid].profile_type.iloc[0]
        t_act.append({"Condition": LAB[k], "alpha": round(q.alpha, 3),
                      "Profile": {"requested": "requested (ideal torque source)",
                                  "device_limited": "device-limited (<= %s)" % TMS,
                                  "capped": "capped T <= max(M_net,0)"}[ptype],
                      "Peak torque (N.m)": round(q.act_peak_torque_Nm, 2),
                      "Peak at (% stance)": q.pct_at_act_peak,
                      "Peak force (N)": round(q.act_peak_force_N, 1),
                      "Peak pressure (kPa)": round(q.act_peak_pressure_kPa, 1),
                      "On / off (% stance)": "%g-%g" % (q.act_on_pct, q.act_off_pct),
                      "On / off (ms after IC)": "%.0f-%.0f" % (q.act_on_ms, q.act_off_ms),
                      "Peak +power (W)": round(q.act_peak_pos_power_W, 2),
                      "Peak -power (W)": round(q.act_peak_neg_power_W, 2),
                      "+work (J)": round(q.act_pos_work_J, 3), "-work (J)": round(q.act_neg_work_J, 3),
                      "Net work (J)": round(q.act_net_work_J, 3),
                      "Total assistance, angular impulse (N.m.s)": round(q.act_angular_impulse_Nms, 3),
                      "Max torque rise rate (N.m/s)": round(q.act_max_rise_rate_Nm_s, 1),
                      "Within %s capability" % TMS: q.within_capability,
                      "KMR peak (%)": round(q.KMR_peak_pct, 1),
                      "KMR window (%)": round(q.KMR_window_impulse_pct, 1),
                      "Over-assisted window (%)": round(q.over_assist_pct_of_window, 1)})
t_act = pd.DataFrame(t_act)

w = met[met.group == "Healthy_Winter"]
t_win = pd.DataFrame([{"Condition": q.label, "Peak flexion (deg)": round(q.peak_flexion_deg, 2),
                       "at %GC": q.pct_at_peak_flexion,
                       "Peak extension (deg)": round(q["peak_extension_deg(min_flexion)"], 2),
                       "Full-cycle ROM (deg)": round(q.ROM_deg, 2),
                       "Peak ext. moment (N.m)": round(q.peak_ext_moment_Nm, 2),
                       "Peak flex. moment (N.m)": round(q.peak_flex_moment_Nm, 2),
                       "Peak actuator torque (N.m)": round(q.act_peak_torque_Nm, 2),
                       "Peak biological ext. moment, early stance (N.m)": round(q.peak_bio_ext_moment_early_Nm, 2),
                       "KMR peak (%)": round(q.KMR_peak_pct, 1)} for _, q in w.iterrows()])

# ---- alpha sweep (requested = ideal torque source; delivered = device-limited at the 100 kPa capability)
ALPHAS = act["alpha_sweep"]


def atag(a):
    return "a%03d" % int(round(a * 100))


sweep = []
for k in ORDER:
    for a_ in ALPHAS:
        rid = asst_id(k, atag(a_))
        lid = man[man.cond_id == rid].device_limited_cond_id.iloc[0]
        r_, d_ = g(rid), g(lid)
        sweep.append({
            "Group": LAB[k], "group_key": k, "alpha": a_,
            "Required peak torque (N.m)": round(r_.act_peak_torque_Nm, 2),
            "Required peak force (N)": round(r_.act_peak_force_N, 1),
            "Required peak pressure (kPa)": round(r_.act_peak_pressure_kPa, 1),
            "Achievable at <= 100 kPa": "yes" if r_.within_capability else "NO",
            "Delivered peak torque (N.m)": round(d_.act_peak_torque_Nm, 2),
            "Delivered peak pressure (kPa)": round(d_.act_peak_pressure_kPa, 1),
            "KMR early-stance peak, requested (%)": round(r_.KMR_peak_pct, 1),
            "KMR early-stance peak, delivered (%)": round(d_.KMR_peak_pct, 1),
            "KMR window impulse, requested (%)": round(r_.KMR_window_impulse_pct, 1),
            "KMR window impulse, delivered (%)": round(d_.KMR_window_impulse_pct, 1),
            "Over-assisted window, requested (%)": round(r_.over_assist_pct_of_window, 1),
            "Over-assisted window, delivered (%)": round(d_.over_assist_pct_of_window, 1),
            "Min muscle moment in window, delivered (N.m)": round(d_.min_bio_moment_in_window_Nm, 2),
            "Total assistance impulse, requested (N.m.s)": round(r_.act_angular_impulse_Nms, 3),
            "Total assistance impulse, delivered (N.m.s)": round(d_.act_angular_impulse_Nms, 3),
            "Net mechanical work, delivered (J)": round(d_.act_net_work_J, 3),
            "H2 restored peak M+T, requested (% healthy)": round(r_.restored_peak_pct_of_healthy, 1) if k != "healthy" else np.nan,
            "H2 restored peak M+T, delivered (% healthy)": round(d_.restored_peak_pct_of_healthy, 1) if k != "healthy" else np.nan,
            "cond_requested": rid, "cond_delivered": lid})
sweep = pd.DataFrame(sweep)
PIV = [("Required peak torque (N.m)", "A  Required peak actuator torque (N.m)"),
       ("Required peak pressure (kPa)", "B  Required peak pressure (kPa); > 100 = not achievable by the actuator"),
       ("Delivered peak torque (N.m)", "C  Delivered peak torque, device-limited (N.m)"),
       ("KMR early-stance peak, requested (%)", "D  Knee moment reduction, early-stance peak, requested torque (%)"),
       ("KMR early-stance peak, delivered (%)", "E  Knee moment reduction, early-stance peak, delivered torque (%)"),
       ("KMR window impulse, delivered (%)", "F  Knee moment reduction, window impulse, delivered torque (%)"),
       ("Over-assisted window, delivered (%)", "G  Window frames where device > patient's net moment, delivered (%)"),
       ("H2 restored peak M+T, delivered (% healthy)", "H  H2: peak net moment with device, delivered (% of healthy)")]
pivots = {}
for col, title in PIV:
    pv = sweep.pivot(index="alpha", columns="Group", values=col)[[LAB[k] for k in ORDER]]
    pivots[title] = pv
    pv.to_csv(os.path.join(TAB, "T11_Sweep_" + col.split(" (")[0].replace(",", "").replace(" ", "_")
                           .replace("+", "plus") + ".csv"))
print(pivots[PIV[0][1]].round(2).to_string())

val = pd.read_csv(os.path.join(ROOT, "Actuator", "validation_torque_rule_vs_team_Table6A.csv"))
cap = pd.read_csv(os.path.join(ROOT, "Actuator", "actuator_capability_check.csv"))

tables = {"T1_Main_Results": t_main, "T2_Kinematics_Kinetics": t_kin,
          "T3_Healthy_vs_ACL_Recovery": t_cmp, "T4_Actuator_All_Alpha": t_act,
          "T5_Healthy_FullGait_Winter": t_win, "T6_Alpha_Guard_OverAssist": guard,
          "T7_Actuator_Capability": cap, "T8_Validation_vs_Team_Table6A": val,
          "T9_All_Metrics_Raw": met,
          "T10_Alpha_Sweep_All": sweep.drop(columns=["group_key"])}
for n, df in tables.items():
    df.to_csv(os.path.join(TAB, n + ".csv"), index=False)
with pd.ExcelWriter(os.path.join(TAB, "OpenSim_Project_Results.xlsx"), engine="openpyxl") as xw:
    readme = pd.DataFrame({"Read me": [
        "OpenSim_Project results workbook - generated by Scripts/04_analysis_figures_tables.py",
        "All numbers are COMPUTED FROM INPUT DATA (Buttner 2025 / Winter 1987 group means, design basis "
        "70 kg, 1.70 m) and the actuator data (CAD V4.1).",
        "Cells marked 'see T12-T14' are given by the OpenSim run (Tables T12-T14); "
        "05_postprocess_opensim_results.py fills them in.",
        "Conventions: knee flexion +; internal knee moment, extension +; actuator torque extension +; "
        "biological moment = net - actuator.",
        "KMR = knee moment reduction of the BIOLOGICAL (muscle-required) extension moment, "
        "assuming the same gait with and without the device (hypothesis H1)."]})
    readme.to_excel(xw, sheet_name="README", index=False)
    for n, df in tables.items():
        df.to_excel(xw, sheet_name=n[:31], index=False)
    r0 = 0
    for title, pv in pivots.items():
        pd.DataFrame({title: []}).to_excel(xw, sheet_name="T11_Alpha_Sweep_Pivots", startrow=r0, index=False)
        pv.to_excel(xw, sheet_name="T11_Alpha_Sweep_Pivots", startrow=r0 + 1)
        r0 += len(pv) + 4
print(t_cmp.to_string(index=False))

# ------------------------------------------------------------------------------------
# 3. FIGURES
# ------------------------------------------------------------------------------------
def curve(cid, col):
    d, r = load(cid)
    return d.iloc[:, 0].values, d[col].values


def label_end(ax, x, y, text, color, dx=1.0):
    ax.text(x + dx, y, text, color=INK2, fontsize=7.5, va="center")


win_raw = pd.read_csv(os.path.join(IN, "healthy_winter1987_full_gait.csv"))

# Fig 1 - knee angle
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axs[0]
x = win_raw.pct_GC
ax.fill_between(x, win_raw.knee_angle_deg - win_raw.knee_angle_sd, win_raw.knee_angle_deg + win_raw.knee_angle_sd,
                color=COL["healthy"], alpha=0.10, lw=0)
ax.plot(x, win_raw.knee_angle_deg, color=COL["healthy"], label="Healthy, Winter 1987 (mean +/- 1 SD)")
ax.axvline(60, color=MUTED, lw=0.8)
ax.text(30, -3.2, "Stance (0-60 %)", ha="center", color=INK2, fontsize=8)
ax.text(80, -3.2, "Swing", ha="center", color=INK2, fontsize=8)
ax.set(xlabel="Gait cycle (%)", ylabel="Knee flexion (deg)", title="A  Healthy - full gait cycle",
       xlim=(0, 100), ylim=(-5, 75))
ax.legend(loc="upper left")
ax = axs[1]
for k in ORDER:
    xx, yy = curve(base_id(k), "knee_flexion_deg")
    ax.plot(xx, yy, color=COL[k], lw=2.4 if k == "healthy" else 1.7, label=LAB[k], zorder=3 if k == "healthy" else 2)
ax.set(xlabel="Stance (%)", ylabel="Knee flexion (deg)", title="B  Stance phase - Healthy vs ACL epochs",
       xlim=(0, 100))
ax.legend(loc="upper left", ncol=2)
finish(fig, os.path.join(GRA, "Fig01_Knee_Angle_vs_Gait_Cycle.png"),
       "Sources: Winter 1987 (A); Buttner 2025 digitised group means (B). Flexion positive. ACL swing-phase data: not available in any project source.")

# Fig 2 - knee moment
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axs[0]
mw, sd = win_raw.M_int_Nm_per_kg * M_BODY, win_raw.M_int_sd * M_BODY
ax.fill_between(x, mw - sd, mw + sd, color=COL["healthy"], alpha=0.10, lw=0)
ax.plot(x, mw, color=COL["healthy"], label="Healthy, Winter 1987 (mean +/- 1 SD)")
zero_line(ax)
ax.axvline(60, color=MUTED, lw=0.8)
ax.set(xlabel="Gait cycle (%)", ylabel="Internal knee moment (N.m)  [+ extension]",
       title="A  Healthy - full gait cycle (70 kg)", xlim=(0, 100))
ax.legend(loc="upper right")
ax = axs[1]
for k in ORDER:
    xx, yy = curve(base_id(k), "net_knee_moment_Nm")
    ax.plot(xx, yy, color=COL[k], lw=2.4 if k == "healthy" else 1.7, label=LAB[k], zorder=3 if k == "healthy" else 2)
zero_line(ax)
ax.axvspan(9, 44, color=DEVICE, alpha=0.06, lw=0)
ax.text(26.5, -24, "actuator window\n9-44 % stance", ha="center", fontsize=7.5, color=INK2)
ax.set(xlabel="Stance (%)", ylabel="Internal knee moment (N.m)  [+ extension]",
       title="B  Stance phase - Healthy vs ACL epochs (70 kg, 1.70 m)", xlim=(0, 100))
ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.14), fontsize=8)
finish(fig, os.path.join(GRA, "Fig02_Knee_Moment_vs_Gait_Cycle.png"),
       "Net internal knee moment from the sources' inverse dynamics; BW*height x m*g*h (h = 1.70 m, ASM-BIO-02).")

# Fig 5 - actuator torque
fig, ax = plt.subplots(figsize=(8.2, 4.4))
for k in ORDER:
    xx, yy = curve(asst_id(k), "actuator_torque_Nm")
    ax.plot(xx, yy, color=COL[k], lw=5 if k == "healthy" else 1.7, alpha=0.3 if k == "healthy" else 1,
            zorder=1 if k == "healthy" else 2,
            label=LAB[k] + (" (design command = 2-month profile)" if k == "healthy" else " (assist-as-needed)"))
ax.axhline(T_MAX, color=INK2, lw=0.9)
ax.text(59, T_MAX + 0.25, "capability at 100 kPa = %.2f N.m" % T_MAX, ha="right", fontsize=8, color=INK2)
ax.set(xlabel="Stance (%)", ylabel="Actuator torque (N.m)  [+ extension]",
       title="Actuator torque vs stance (alpha = %s)" % APS, xlim=(0, 60), ylim=(-0.3, 12))
ax.legend(loc="upper center", fontsize=8, bbox_to_anchor=(0.5, -0.14), ncol=2)
finish(fig, os.path.join(GRA, "Fig05_Actuator_Torque_vs_Gait_Cycle.png"),
       "T = alpha x m x g x h x dM(phi) inside the candidate window (Table G0 / CALC-BIO-03); healthy uses the 2-month design command.")

# Fig 6 - actuator force & pressure (two panels, no dual axis), Fig 6b power
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.2))
for k in ORDER:
    xx, F = curve(asst_id(k), "actuator_force_N")
    _, p = curve(asst_id(k), "actuator_pressure_kPa")
    kw = dict(lw=5, alpha=0.3, zorder=1) if k == "healthy" else dict(lw=1.7, zorder=2)
    lab = LAB[k] + (" (= 2-month profile)" if k == "healthy" else "")
    axs[0].plot(xx, F, color=COL[k], label=lab, **kw)
    axs[1].plot(xx, p, color=COL[k], label=lab, **kw)
axs[0].axhline(act["max_force_N"], color=INK2, lw=0.9)
axs[0].text(1, act["max_force_N"] + 6, "F max = %.0f N (100 kPa)" % act["max_force_N"], ha="left", fontsize=8, color=INK2)
axs[1].axhline(100, color=INK2, lw=0.9)
axs[1].text(59, 102, "p max = 100 kPa", ha="right", fontsize=8, color=INK2)
axs[0].set(xlabel="Stance (%)", ylabel="Bladder force on shank, F = T / r (N)", title="A  Actuator force (r = 34.25 mm)",
           xlim=(0, 60), ylim=(-5, 340))
axs[1].set(xlabel="Stance (%)", ylabel="Required gauge pressure, p = F / A (kPa)",
           title="B  Required pressure (A = 3140.3 mm2, CAD V4.1)", xlim=(0, 60), ylim=(-2, 110))
axs[0].legend(loc="center right", fontsize=8)
finish(fig, os.path.join(GRA, "Fig06_Actuator_Force_vs_Gait_Cycle.png"),
       "Fixed moment arm r = 34.25 mm (CAD V4.1). alpha = %s." % APS)

fig, ax = plt.subplots(figsize=(8.2, 4.2))
for k in ORDER:
    xx, P = curve(asst_id(k), "actuator_power_W")
    kw = dict(lw=5, alpha=0.3, zorder=1) if k == "healthy" else dict(lw=1.7, zorder=2)
    ax.plot(xx, P, color=COL[k], label=LAB[k], **kw)
zero_line(ax)
ax.text(12, ax.get_ylim()[0] * 0.85, "knee flexing:\ndevice absorbs (-)", fontsize=7.5, color=INK2)
ax.text(30, ax.get_ylim()[1] * 0.75, "knee extending:\ndevice does work (+)", fontsize=7.5, color=INK2)
ax.set(xlabel="Stance (%)", ylabel="Actuator mechanical power P = T x omega (W)",
       title="Actuator mechanical power vs stance (alpha = %s)" % APS, xlim=(0, 60))
ax.legend(loc="lower right", fontsize=8)
finish(fig, os.path.join(GRA, "Fig06b_Actuator_Power_vs_Gait_Cycle.png"),
       "omega = knee extension velocity from the source knee-angle waveform (central differences).")

# Fig 7 - knee moment without vs with actuator (small multiples)
fig, axs = plt.subplots(2, 3, figsize=(12.5, 7.0), sharex=True)
for ax, k in zip(axs.ravel(), ORDER):
    xx, m = curve(base_id(k), "net_knee_moment_Nm")
    _, mb = curve(asst_id(k), "biological_knee_moment_Nm")
    _, tau = curve(asst_id(k), "actuator_torque_Nm")
    ax.fill_between(xx, mb, m, where=tau > 0, color=DEVICE, alpha=0.18, lw=0)
    ax.plot(xx, m, color=BASE, lw=1.9, label="Without actuator: net = muscle moment")
    ax.plot(xx, mb, color=ASSIST, lw=1.9, label="With actuator: muscle (biological) moment")
    ax.plot(xx, tau, color=DEVICE, lw=1.4, label="Actuator torque")
    zero_line(ax)
    q = g(asst_id(k))
    ttl = ("peak -%.0f %%" % q.KMR_peak_pct) if q.KMR_peak_pct <= 100 else "over-assisted: muscle moment < 0"
    ax.set_title("%s   (%s)" % (LAB[k], ttl), fontsize=10)
    ax.set_xlim(0, 60)
for ax in axs[1]:
    ax.set_xlabel("Stance (%)")
for ax in axs[:, 0]:
    ax.set_ylabel("Internal knee moment (N.m) [+ ext]")
axs[0, 0].legend(loc="lower right", fontsize=7.5)
fig.suptitle("Knee extension moment: without vs with actuator (alpha = %s; same gait assumed)" % APS,
             fontsize=12, fontweight="bold", color=INK, y=1.0)
finish(fig, os.path.join(GRA, "Fig07_Knee_Moment_Without_vs_With_Actuator.png"),
       "Shaded = moment supplied by the device. Below zero = device exceeds the net extensor need (over-assistance).")

# Fig 9 - Healthy vs ACL Pre-op
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.2))
for k in ["healthy", "preop"]:
    xx, y = curve(base_id(k), "knee_flexion_deg")
    axs[0].plot(xx, y, color=COL[k], lw=2.2, label=LAB[k])
    xx, y = curve(base_id(k), "net_knee_moment_Nm")
    axs[1].plot(xx, y, color=COL[k], lw=2.2, label=LAB[k])
zero_line(axs[1])
hb, pb = g(base_id("healthy")), g(base_id("preop"))
axs[0].set(xlabel="Stance (%)", ylabel="Knee flexion (deg)", title="A  Knee angle", xlim=(0, 100))
axs[1].set(xlabel="Stance (%)", ylabel="Internal knee moment (N.m) [+ ext]",
           title="B  Knee moment  (pre-op peak = %.0f %% of healthy)" % pb.peak_ext_moment_pct_of_healthy,
           xlim=(0, 100))
axs[0].legend(loc="upper left")
finish(fig, os.path.join(GRA, "Fig09_Healthy_vs_ACL_PreOp.png"), NOTE)

# Fig 10 - ACL recovery
fig, axs = plt.subplots(1, 3, figsize=(14.5, 4.3), gridspec_kw={"width_ratios": [1.1, 1.1, 0.9]})
for k in ORDER:
    xx, y = curve(base_id(k), "knee_flexion_deg")
    axs[0].plot(xx, y, color=COL[k], lw=2.4 if k == "healthy" else 1.7, label=LAB[k])
    xx, y = curve(base_id(k), "net_knee_moment_Nm")
    axs[1].plot(xx, y, color=COL[k], lw=2.4 if k == "healthy" else 1.7, label=LAB[k])
zero_line(axs[1])
axs[0].set(xlabel="Stance (%)", ylabel="Knee flexion (deg)", title="A  Knee angle", xlim=(0, 60), ylim=(-4, 15))
axs[1].set(xlabel="Stance (%)", ylabel="Internal knee moment (N.m) [+ ext]", title="B  Knee moment", xlim=(0, 60))
axs[0].legend(loc="upper left", fontsize=7.5)
ax = axs[2]
days = {"preop": -10.6, "2months": 56.6, "4months": 114.4, "6months": 174.6, "12months": 346.9}
xs = [days[e] for e in EPOCHS]
ys = [g(base_id(e)).peak_ext_moment_pct_of_healthy for e in EPOCHS]
ax.plot(xs, ys, color=INK2, lw=1.2, zorder=1)
for e, xv, yv in zip(EPOCHS, xs, ys):
    ax.scatter([xv], [yv], s=60, color=COL[e], zorder=3, edgecolor="white", linewidth=1.5)
    ax.text(xv, yv + (-12 if e == "2months" else 4), "%s\n%.0f %%" % (SHORT[e], yv), ha="center", fontsize=7.5, color=INK2)
ax.axhline(100, color=COL["healthy"], lw=1.2)
ax.text(340, 102, "healthy = 100 %", ha="right", fontsize=7.5, color=INK2)
ax.set(xlabel="Days from surgery", ylabel="Peak ext. moment (% of healthy)", title="C  Recovery of peak extension moment",
       ylim=(0, 115), xlim=(-40, 380))
finish(fig, os.path.join(GRA, "Fig10_ACL_Recovery_PreOp_to_12Months.png"), NOTE)

# Fig 12 - knee moment reduction
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.3))
labels = [SHORT[k] for k in ORDER]
xi = np.arange(len(ORDER))
for ax, col, ttl in [(axs[0], "KMR_peak_pct", "A  Early-stance peak ext. moment reduction"),
                     (axs[1], "KMR_window_impulse_pct", "B  Ext.-moment impulse reduction in window")]:
    bw = 0.2
    for j, (tag, shade) in enumerate([("a010", "#86b6ef"), (ATAG, "#2a78d6"), ("a100_lim", "#184f95"),
                                      (ATAG + "cap", "#eb6834")]):
        vals = [g(asst_id(k, tag))[col] for k in ORDER]
        ax.bar(xi + (j - 1.5) * (bw + 0.015), vals, width=bw, color=shade,
               label={"a010": "alpha 0.10", ATAG: "alpha %s (working case)" % APS,
                      "a100_lim": "device maximum (alpha 1.0 clipped at %s)" % TMS,
                      ATAG + "cap": "alpha %s capped at own net moment" % APS}[tag])
        if tag == ATAG:
            for xv, v in zip(xi, vals):
                ax.text(xv - 0.5 * (bw + 0.015), v + 2, "%.0f" % v, ha="center", fontsize=7.5, color=INK)
    ax.axhline(100, color=MUTED, lw=0.8)
    ax.set_xticks(xi)
    ax.set_xticklabels(labels)
    ax.set(ylabel="Reduction (%)", title=ttl, ylim=(0, 200))
    ax.text(-0.45, 104, "100 % = fully replaced", ha="left", fontsize=7, color=INK2)
axs[0].legend(loc="upper left", fontsize=8)
finish(fig, os.path.join(GRA, "Fig12_Knee_Moment_Reduction_by_Actuator.png"),
       "Reduction of the muscle-required (biological) knee extension moment, same gait assumed (H1). >100 % = over-assistance at the peak.")

# Fig 13 - restoration view (H2)
fig, axs = plt.subplots(1, 5, figsize=(16, 3.6), sharey=True)
xh, mh = curve(base_id("healthy"), "net_knee_moment_Nm")
for ax, e in zip(axs, EPOCHS):
    xx, m = curve(base_id(e), "net_knee_moment_Nm")
    _, tau = curve(asst_id(e), "actuator_torque_Nm")
    ax.plot(xh, mh, color=COL["healthy"], lw=2.0, label="Healthy")
    ax.plot(xx, m, color=COL[e], lw=1.6, label="ACL, no actuator")
    ax.plot(xx, m + tau, color=COL[e], lw=1.6, ls=(0, (4, 2)), label="ACL + actuator torque")
    zero_line(ax)
    ax.set(title=LAB[e], xlim=(0, 60), xlabel="Stance (%)")
axs[0].set_ylabel("Knee moment (N.m) [+ ext]")
axs[0].legend(loc="lower right", fontsize=7)
finish(fig, os.path.join(GRA, "Fig13_Restoration_View_ACL_plus_Device_vs_Healthy.png"),
       "Alternative hypothesis H2 (ASM-BIO-08): device torque adds to the patient's own moment (alpha = %s)." % APS)

# ------------------------------------------------------------------------------------
# ALPHA SWEEP FIGURES (Fig15-Fig19)
# ------------------------------------------------------------------------------------
RAMP11 = ["#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
          "#184f95", "#104281", "#0d366b"]
SW_NOTE = ("alpha sweep 0.10-1.00. Requested = alpha x m x g x h x dM (ideal torque source); "
           "delivered = requested clipped at the %s / 100 kPa capability of actuator CAD V4.1." % TMS)


def top_legend(fig, ax, ncol=6):
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=ncol, bbox_to_anchor=(0.5, 1.09), fontsize=8)
    fig.subplots_adjust(bottom=0.22)


def sweep_lines(ax, col, groups=ORDER, healthy_band=True):
    for k in groups:
        d = sweep[sweep.group_key == k]
        if k == "healthy" and healthy_band:
            ax.plot(d.alpha, d[col], color=COL[k], lw=5, alpha=0.3, zorder=1, label=LAB[k])
        else:
            ax.plot(d.alpha, d[col], color=COL[k], lw=1.7, marker="o", ms=3.5, zorder=2, label=LAB[k])
    ax.set_xticks(ALPHAS)
    ax.set_xticklabels(["%.2g" % a_ for a_ in ALPHAS], fontsize=7.5, rotation=45)
    ax.set_xlabel("Assistance fraction alpha (-)")


# Fig 15 - required torque / pressure vs alpha
fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
sweep_lines(axs[0], "Required peak torque (N.m)")
axs[0].axhline(T_MAX, color=INK2, lw=0.9)
axs[0].text(0.66, T_MAX - 0.7, "actuator capability\n%s (100 kPa)" % TMS, fontsize=8, color=INK2, va="top")
axs[0].set(ylabel="Required peak torque (N.m)", title="A  Required peak actuator torque vs alpha")
sweep_lines(axs[1], "Required peak pressure (kPa)")
axs[1].axhline(100, color=INK2, lw=0.9)
axs[1].text(0.66, 94, "maximum operating\npressure 100 kPa", fontsize=8, color=INK2, va="top")
axs[1].set(ylabel="Required peak pressure (kPa)", title="B  Pressure needed vs alpha (fixed r, A)")
top_legend(fig, axs[0])
finish(fig, os.path.join(GRA, "Fig15_Alpha_Sweep_Required_Torque_and_Pressure.png"),
       "Healthy uses the 2-month design command (same line as 2 months). " + SW_NOTE)

# Fig 16 - knee moment reduction vs alpha
fig, axs = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
sweep_lines(axs[0], "KMR early-stance peak, requested (%)")
sweep_lines(axs[1], "KMR early-stance peak, delivered (%)")
for ax, ttl in zip(axs, ["A  Requested torque (ideal)", "B  Delivered torque (device-limited)"]):
    ax.axhline(100, color=INK2, lw=0.9)
    ax.text(0.1, 104, "100 % = muscle extensor peak fully replaced; above = over-assisted", fontsize=7.5, color=INK2)
    ax.set_title(ttl)
axs[0].set_ylabel("Early-stance peak knee moment reduction (%)")
top_legend(fig, axs[0])
finish(fig, os.path.join(GRA, "Fig16_Alpha_Sweep_Knee_Moment_Reduction.png"),
       "Reduction of the muscle-required knee extension moment, same gait assumed (H1). " + SW_NOTE)

# Fig 17 - over-assistance vs alpha
fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
sweep_lines(axs[0], "Over-assisted window, requested (%)")
sweep_lines(axs[1], "Over-assisted window, delivered (%)")
axs[0].set(ylabel="Window frames with device torque > net moment (%)", title="A  Requested torque (ideal)",
           ylim=(-3, 105))
axs[1].set(title="B  Delivered torque (device-limited)")
top_legend(fig, axs[0])
finish(fig, os.path.join(GRA, "Fig17_Alpha_Sweep_Over_Assistance.png"),
       "Over-assistance (H1): the muscles would have to produce a FLEXOR moment against the device. " + SW_NOTE)

# Fig 18 - restoration (H2) vs alpha
fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
sweep_lines(axs[0], "H2 restored peak M+T, requested (% healthy)", EPOCHS)
sweep_lines(axs[1], "H2 restored peak M+T, delivered (% healthy)", EPOCHS)
for ax, ttl in zip(axs, ["A  Requested torque (ideal)", "B  Delivered torque (device-limited)"]):
    ax.axhline(100, color=COL["healthy"], lw=1.2)
    ax.text(0.1, 102.5, "healthy peak = 100 %", fontsize=7.5, color=INK2)
    ax.set_title(ttl)
axs[0].set(ylabel="Peak net knee ext. moment with device (% healthy)", ylim=(0, 115))
top_legend(fig, axs[0], ncol=5)
finish(fig, os.path.join(GRA, "Fig18_Alpha_Sweep_Restoration_H2.png"),
       "Hypothesis H2 (ASM-BIO-08): device torque adds to the patient's own moment. " + SW_NOTE)

# Fig 19 - torque profiles for every alpha (small multiples)
fig, axs = plt.subplots(2, 3, figsize=(13, 7), sharex=True, sharey=True)
for ax, k in zip(axs.ravel(), ORDER):
    for a_, c_ in zip(ALPHAS, RAMP11):
        xx, yy = curve(asst_id(k, atag(a_)), "actuator_torque_Nm")
        ax.plot(xx, yy, color=c_, lw=1.4, label="alpha %.2g" % a_)
    ax.axhline(T_MAX, color=DEVICE, lw=1.1)
    ax.set_title(LAB[k] + (" (design command)" if k == "healthy" else ""), fontsize=10)
    ax.set_xlim(0, 60)
axs[0, 0].text(1, T_MAX + 0.8, "%s device limit" % TMS, fontsize=7.5, color=INK2)
for ax in axs[1]:
    ax.set_xlabel("Stance (%)")
for ax in axs[:, 0]:
    ax.set_ylabel("Requested actuator torque (N.m)")
h_, l_ = axs[0, 0].get_legend_handles_labels()
fig.legend(h_, l_, loc="upper center", ncol=11, bbox_to_anchor=(0.5, 1.04), fontsize=7.5)
finish(fig, os.path.join(GRA, "Fig19_Alpha_Sweep_Torque_Profiles.png"),
       "Torque above the orange line cannot be produced at <= 100 kPa; the delivered profile is clipped there. "
       + SW_NOTE)

print("figures written to", GRA)
