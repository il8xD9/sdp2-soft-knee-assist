#!/usr/bin/env python3
"""
01_extract_input_data.py
------------------------
PURPOSE : Read the team's Biomechanics_Master_Data.xlsx (closure package, 29 Sep 2026)
          and write tidy, machine-readable CSV files into Input_Data/.
          Nothing is invented: every column is copied from a named sheet/table.
INPUT   : Input_Data/Source_Files/Biomechanics_Master_Data.xlsx
          Input_Data/Source_Files/WBDSinfo.csv
OUTPUT  : Input_Data/*.csv  (one file per source table, see FILES below)
RUN     : python Scripts/01_extract_input_data.py      (CPython 3, pandas, openpyxl)
"""
import os
import pandas as pd
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Input_Data", "Source_Files")
OUT = os.path.join(ROOT, "Input_Data")
XLSX = os.path.join(SRC, "Biomechanics_Master_Data.xlsx")

wb = openpyxl.load_workbook(XLSX, data_only=True)


def sheet_rows(name):
    return [list(r) for r in wb[name].iter_rows(values_only=True)]


def table_after_header(rows, header_row_idx, stop_when_first_col_none=True, ncols=None):
    """Return a DataFrame whose header is rows[header_row_idx] and data follow it."""
    hdr = [h for h in rows[header_row_idx] if h is not None]
    n = ncols or len(hdr)
    data = []
    for r in rows[header_row_idx + 1:]:
        if r[0] is None or (isinstance(r[0], str) and r[0].startswith("TABLE")):
            if stop_when_first_col_none:
                break
            continue
        data.append(r[:n])
    return pd.DataFrame(data, columns=hdr[:n])


log = []

# --- Sheet 01: Healthy full gait (Winter 1987) -------------------------------------
r = sheet_rows("01_Healthy_Full_Gait")
df = table_after_header(r, 3)
df = df[pd.to_numeric(df["pct_GC"], errors="coerce").notna()].copy()
for c in ["pct_GC", "time_s_from_IC", "knee_angle_deg", "knee_angle_sd", "knee_ang_vel_deg_s",
          "M_int_Nm_per_kg", "M_int_sd", "vGRF_N_per_kg", "vGRF_sd"]:
    df[c] = pd.to_numeric(df[c])
df.to_csv(os.path.join(OUT, "healthy_winter1987_full_gait.csv"), index=False)
log.append(("healthy_winter1987_full_gait.csv", "01_Healthy_Full_Gait / TABLE 1", len(df)))
# events table 1b
i1b = [i for i, x in enumerate(r) if x[0] and str(x[0]).startswith("TABLE 1b")][0]
ev = table_after_header(r, i1b + 1, ncols=6)
ev.to_csv(os.path.join(OUT, "healthy_winter1987_events.csv"), index=False)
log.append(("healthy_winter1987_events.csv", "01_Healthy_Full_Gait / TABLE 1b", len(ev)))

# --- Sheet 02: ACLR epochs ----------------------------------------------------------
r = sheet_rows("02_ACLR_Recovery_Epochs")
df = table_after_header(r, 3)
df.to_csv(os.path.join(OUT, "aclr_recovery_epochs_table2A.csv"), index=False)
log.append(("aclr_recovery_epochs_table2A.csv", "02_ACLR_Recovery_Epochs / TABLE 2A", len(df)))

# --- Sheet 03: ACLR evolution summary -----------------------------------------------
r = sheet_rows("03_ACLR_Full_Gait")
df = table_after_header(r, 3)
df.to_csv(os.path.join(OUT, "aclr_gait_evolution_table2B.csv"), index=False)
log.append(("aclr_gait_evolution_table2B.csv", "03_ACLR_Full_Gait / TABLE 2B", len(df)))

# --- Sheets 05/06: stance angle and moment (Buttner 2025) ----------------------------
for sh, fn in [("05_Stance_Angle", "buttner2025_stance_knee_angle_deg.csv"),
               ("06_Stance_Moment", "buttner2025_stance_knee_moment_BWh.csv")]:
    r = sheet_rows(sh)
    df = table_after_header(r, 3)
    num_cols = [c for c in df.columns if c.startswith(("pct_", "KFA_", "KEM_")) and c != "KEM_unit"]
    df = df[num_cols].apply(pd.to_numeric)
    df.to_csv(os.path.join(OUT, fn), index=False)
    log.append((fn, sh + " / TABLE 4", len(df)))

# --- Sheet 07: stance deficit + summary ---------------------------------------------
r = sheet_rows("07_Stance_Deficit")
df = table_after_header(r, 3)
num_cols = [c for c in df.columns if c.startswith(("pct_", "M_", "dM_"))]
df = df[num_cols].apply(pd.to_numeric)
df.to_csv(os.path.join(OUT, "stance_deficit_table5A.csv"), index=False)
log.append(("stance_deficit_table5A.csv", "07_Stance_Deficit / TABLE 5A", len(df)))
i5b = [i for i, x in enumerate(r) if x[0] and str(x[0]).startswith("TABLE 5B")][0]
df = table_after_header(r, i5b + 1, ncols=18)
df.to_csv(os.path.join(OUT, "stance_deficit_summary_table5B.csv"), index=False)
log.append(("stance_deficit_summary_table5B.csv", "07_Stance_Deficit / TABLE 5B", len(df)))

# --- Sheet 08: required torque (team calculation CALC-BIO-02, used for VALIDATION) ---
r = sheet_rows("08_Assist_Torque")
df = table_after_header(r, 3, ncols=14)
df.to_csv(os.path.join(OUT, "team_torque_envelope_table6B.csv"), index=False)
log.append(("team_torque_envelope_table6B.csv", "08_Assist_Torque / TABLE 6B", len(df)))
i6a = [i for i, x in enumerate(r) if x[0] and str(x[0]).startswith("TABLE 6A")][0]
df = table_after_header(r, i6a + 1, ncols=16)
df.to_csv(os.path.join(OUT, "team_required_torque_table6A.csv"), index=False)
log.append(("team_required_torque_table6A.csv", "08_Assist_Torque / TABLE 6A", len(df)))

# --- Sheets 09/10/11: window, timing, deadlines --------------------------------------
for sh, fn, tag in [("09_Assist_Window", "assist_window_table7.csv", "TABLE 7"),
                    ("10_Gait_Timing", "gait_timing_table8.csv", "TABLE 8"),
                    ("11_Control_Deadlines", "control_deadlines_table9.csv", "TABLE 9"),
                    ("15_Assumptions", "assumptions_ASM_BIO.csv", "ASSUMPTIONS"),
                    ("16_Conflicts", "conflicts_CF.csv", "CONFLICTS")]:
    r = sheet_rows(sh)
    df = table_after_header(r, 3)
    df.to_csv(os.path.join(OUT, fn), index=False)
    log.append((fn, sh + " / " + tag, len(df)))

# --- Sheet 13: Nawaf handover (knee angle / torque vs time) --------------------------
r = sheet_rows("13_Nawaf_Handover")
i = [k for k, x in enumerate(r) if x[0] and str(x[0]).startswith("TABLE 10B-2")][0]
df = table_after_header(r, i + 1, ncols=13)
df.to_csv(os.path.join(OUT, "handover_time_series_table10B2.csv"), index=False)
log.append(("handover_time_series_table10B2.csv", "13_Nawaf_Handover / TABLE 10B-2", len(df)))

# --- WBDS metadata (index only: no marker / GRF data were supplied) ------------------
w = pd.read_csv(os.path.join(SRC, "WBDSinfo.csv"))
subj = w.drop_duplicates("Subject")[["Subject", "AgeGroup", "Age", "Height", "Mass", "Gender",
                                      "Dominance", "LegLength"]]
subj.to_csv(os.path.join(OUT, "wbds_subject_anthropometrics.csv"), index=False)
log.append(("wbds_subject_anthropometrics.csv", "WBDSinfo.csv (one row per subject)", len(subj)))

pd.DataFrame(log, columns=["file", "source_sheet_table", "rows"]).to_csv(
    os.path.join(OUT, "_extraction_log.csv"), index=False)
for l in log:
    print("%-45s <- %-45s rows=%d" % l)
