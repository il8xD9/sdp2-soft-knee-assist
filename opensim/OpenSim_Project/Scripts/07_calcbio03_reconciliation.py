#!/usr/bin/env python3
"""
07_calcbio03_reconciliation.py
------------------------------
PURPOSE : Check that the OpenSim inputs (extracted from the CALC-BIO-02 workbook) are numerically
          identical to CALC-BIO-03 (Biomechanics_Master_Data_CALC-BIO-03.xlsx), so that the OpenSim
          conditions can be labelled CALC-BIO-03 without re-extracting.
INPUT   : Input_Data/*.csv, Actuator/actuator_capability_check.csv,
          Input_Data/Source_Files/Biomechanics_Master_Data_CALC-BIO-03.xlsx
OUTPUT  : Results/CALC-BIO-03_reconciliation.csv  (PASS / FAIL per check)
RUN     : python Scripts/07_calcbio03_reconciliation.py
"""
import os
import numpy as np
import pandas as pd
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(ROOT, "Input_Data")
WB = openpyxl.load_workbook(os.path.join(IN, "Source_Files", "Biomechanics_Master_Data_CALC-BIO-03.xlsx"),
                            data_only=True)


def table(sheet, first_header):
    rows = [list(r) for r in WB[sheet].iter_rows(values_only=True)]
    i = [k for k, r in enumerate(rows) if r[0] == first_header][0]
    hdr = [h for h in rows[i] if h is not None]
    data = []
    for r in rows[i + 1:]:
        if r[0] is None or (isinstance(r[0], str) and r[0].startswith("TABLE")):
            break
        data.append(r[:len(hdr)])
    return pd.DataFrame(data, columns=hdr)


out = []


def add(cid, item, value, tol, unit, note=""):
    out.append({"check": cid, "item": item, "max_abs_difference": value, "tolerance": tol, "unit": unit,
                "outcome": "PASS" if value <= tol else "FAIL", "note": note})


# R1/R2 stance waveforms (sheets 05 and 06) vs extracted CSVs
for cid, sheet, csv in [("R1", "05_Stance_Angle", "buttner2025_stance_knee_angle_deg.csv"),
                        ("R2", "06_Stance_Moment", "buttner2025_stance_knee_moment_BWh.csv")]:
    new = table(sheet, "pct_stance").apply(pd.to_numeric, errors="coerce").dropna(subset=["pct_stance"])
    old = pd.read_csv(os.path.join(IN, csv))
    cols = [c for c in new.columns if c in old.columns and c != "pct_stance"]
    d = max(float(np.nanmax(np.abs(new[c].values - old[c].values))) for c in cols)
    add(cid, "%s, %d columns x %d points" % (sheet, len(cols), len(new)), d, 1e-9,
        "deg" if cid == "R1" else "BW*h")

# R3 full-deficit peak torque (70 kg, 1.70 m) vs Table 6B
t6 = table("08_Assist_Torque", "Recovery epoch")
cap = pd.read_csv(os.path.join(ROOT, "Actuator", "actuator_capability_check.csv")).set_index("epoch")
lab = {"2 months": "2 Months", "4 months": "4 Months", "6 months": "6 Months", "12 months": "12 Months"}
for _, r in t6.iterrows():
    if r["Recovery epoch"] in lab:
        ours = float(cap.loc[lab[r["Recovery epoch"]], "full_deficit_peak_Nm(alpha=1)"])
        ref = float(r["Peak full-deficit torque [N.m] (70 kg; 1.70 m)"])
        add("R3", "Full-deficit peak torque " + r["Recovery epoch"], abs(ours - ref), 0.05, "N.m",
            "package %.3f vs CALC-BIO-03 %.4f" % (ours, ref))

# R4 candidate window: same 1 %-grid frames switched on
t7 = table("09_Assist_Window", "epoch")
old7 = pd.read_csv(os.path.join(IN, "assist_window_table7.csv")).set_index("epoch")
for _, r in t7.iterrows():
    e = r["epoch"]
    on3, off3 = float(r["candidate_onset_pct_stance_unrounded"]), float(r["candidate_offset_pct_stance_unrounded"])
    on2, off2 = float(old7.loc[e, "candidate_onset_pct"]), float(old7.loc[e, "candidate_offset_pct"])
    grid = np.arange(1, 101)
    diff = int(np.sum(((grid >= on3) & (grid <= off3)) != ((grid >= on2) & (grid <= off2))))
    add("R4", "Window frames %s (CALC-BIO-03 %.2f-%.2f vs package %.1f-%.1f)" % (e, on3, off3, on2, off2),
        diff, 0, "frames")

# R5 stance durations (Table 8)
t8 = table("10_Gait_Timing", "epoch")
old8 = pd.read_csv(os.path.join(IN, "gait_timing_table8.csv"))
col = [c for c in t8.columns if c.startswith("stance_duration_s")][0]
colo = [c for c in old8.columns if c.startswith("stance_duration")][0]
d = float(np.nanmax(np.abs(pd.to_numeric(t8[col], errors="coerce").values[:len(old8)]
                           - pd.to_numeric(old8[colo], errors="coerce").values)))
add("R5", "Stance durations Table 8", d, 1e-6, "s")

res = pd.DataFrame(out)
res.to_csv(os.path.join(ROOT, "Results", "CALC-BIO-03_reconciliation.csv"), index=False)
print(res.to_string(index=False))
print("\nALL PASS" if (res.outcome == "PASS").all() else "\nSOME CHECKS FAILED")
