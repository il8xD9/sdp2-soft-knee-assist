#!/usr/bin/env python3
"""
06_verification_checks.py
-------------------------
PURPOSE : Independent checks of the computed results against values published in the
          biomechanics workbook and the actuator design data, and an independent
          numerical check of the static-optimization solver used in run_opensim_knee_SO.py.
          Reference values are re-read from the source workbook here (not from Input_Data).
OUTPUT  : Results/verification_checks.csv
"""
import os
import re
import numpy as np
import pandas as pd
import openpyxl
from scipy.optimize import minimize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json as _json
AP = _json.load(open(os.path.join(ROOT, "Actuator", "actuator_parameters.json")))["alpha_primary"]
ATAG = "a%03d" % int(round(AP * 100))
XL = os.path.join(ROOT, "Input_Data", "Source_Files", "Biomechanics_Master_Data.xlsx")
met = pd.read_csv(os.path.join(ROOT, "Results", "metrics_all_conditions_computed.csv")).set_index("cond_id")
man = pd.read_csv(os.path.join(ROOT, "Simulations", "conditions_manifest.csv")).set_index("cond_id")
wb = openpyxl.load_workbook(XL, data_only=True)
checks = []


def add(cid, what, ours, ref, tol, src):
    diff = ours - ref
    checks.append({"check": cid, "quantity": what, "this_work": round(ours, 4), "reference": ref,
                   "difference": round(diff, 4), "tolerance": tol,
                   "result": "PASS" if abs(diff) <= tol else "FAIL", "reference_source": src})


# V1 peak KEM (% of healthy) and LR peak flexion vs Table 2B (sheet 03)
rows = [list(r) for r in wb["03_ACLR_Full_Gait"].iter_rows(values_only=True)]
kfa_row = [r for r in rows if r[0] and str(r[0]).startswith("Peak stance knee flexion")][0]
ref_kfa = [float(str(v).split("@")[0]) for v in kfa_row[1:6]]
for cid, ref in zip(["Healthy_Baseline", "ACL_2Months_Baseline", "ACL_4Months_Baseline",
                     "ACL_6Months_Baseline", "ACL_12Months_Baseline"], ref_kfa):
    add("V1", "LR peak knee flexion (deg) " + cid, met.loc[cid, "loading_response_peak_flexion_deg"], ref, 0.1,
        "Table 2B (sheet 03), Buttner Fig.3 digitised")
kem_row = [r for r in rows if r[0] and str(r[0]).startswith("Peak internal KEM (N.m/kg")][0]
for cid, ref in zip(["Healthy_Baseline", "ACL_2Months_Baseline", "ACL_4Months_Baseline",
                     "ACL_6Months_Baseline", "ACL_12Months_Baseline"], kem_row[1:6]):
    add("V2", "Peak internal KEM (N.m/kg) " + cid, met.loc[cid, "peak_ext_moment_Nm_per_kg"], float(ref), 0.01,
        "Table 2B (sheet 03), h_ref 1.70 m")

# V3 torque impulse at alpha 0.5 (70 kg, 1.70 m) vs Table 6B
rows = [list(r) for r in wb["08_Assist_Torque"].iter_rows(values_only=True)]
for r in rows[4:40]:
    if r[1] == 70.0 and r[2] == 1.7:
        e = {"2 months": "ACL_2Months", "4 months": "ACL_4Months", "6 months": "ACL_6Months",
             "12 months": "ACL_12Months"}[r[0]]
        ours = met.loc[e + "_Assisted_" + ATAG, "act_angular_impulse_Nms"] * 0.5 / AP
        add("V3", "Torque impulse alpha 0.50 (N.m.s) " + r[0], ours, float(r[13]), 0.01, "Table 6B (sheet 08)")
        add("V4", "Peak torque alpha 1.00 (N.m) " + r[0],
            met.loc[e + "_Assisted_" + ATAG, "act_peak_torque_Nm"] / AP, float(r[8]), 0.02, "Table 6B (sheet 08)")

# V5 actuator capability and alpha_max vs the CAD V4.1 actuator data
act = pd.read_csv(os.path.join(ROOT, "Actuator", "actuator_capability_check.csv")).set_index("epoch")
add("V5", "Torque capability at 100 kPa (N.m)", float(act["capability_100kPa_Nm"].iloc[0]), 10.76, 0.01,
    "CAD V4.1: 100 kPa x 3140.3 mm2 x 34.25 mm = 10.76 N.m")
# references: CAD V4.1 T_max = 10.7555 N.m divided by CALC-BIO-03 Table 6B full-deficit peaks
for ep, ref in [("2 Months", 0.3263), ("4 Months", 0.4197), ("6 Months", 0.4148), ("12 Months", 0.5990)]:
    add("V6", "alpha reached at 100 kPa " + ep, float(act.loc[ep, "alpha_max_at_100kPa"]), ref, 0.001,
        "CAD V4.1 T_max / CALC-BIO-03 Table 6B peak")
# working case alpha 0.20: p = T / (A r), A = 3140.3 mm2, r = 34.25 mm (2 months = 61.3 kPa in the SDP-II report)
for ep, cid, ref in [("2 Months", "ACL_2Months", 61.3), ("4 Months", "ACL_4Months", 47.7),
                     ("6 Months", "ACL_6Months", 48.2), ("12 Months", "ACL_12Months", 33.4)]:
    add("V7", "Pressure needed alpha 0.20 (kPa) " + ep, met.loc[cid + "_Assisted_a020", "act_peak_pressure_kPa"],
        ref, 0.2, "SDP-II report (61.3 kPa at 6.59 N.m) / CALC-BIO-03 Table 6B alpha 0.20")

# V8 timing of the torque peak (ms) vs Table 9
for cid, ref in [("ACL_2Months", 148), ("ACL_4Months", 144), ("ACL_6Months", 143), ("ACL_12Months", 142)]:
    T = man.loc[cid + "_Assisted_" + ATAG, "t_end"]           # = stance duration (100 % stance)
    add("V8", "Time of torque peak (ms) " + cid, met.loc[cid + "_Assisted_" + ATAG, "pct_at_act_peak"] / 100 * T * 1000,
        ref, 1.0, "Table 9 (sheet 11), ASM-BIO-04")

# V9 Winter healthy peak moment
add("V9", "Winter peak internal KEM (N.m, 70 kg)", met.loc["HealthyWinter_FullGait_Baseline", "peak_ext_moment_Nm"],
    0.615 * 70, 0.01, "Table 1 (sheet 01), Winter 1987 Tab. 4.24(b)")

# V10 static-optimization solver = exact optimum (vs scipy SLSQP) on 300 random problems
src = open(os.path.join(ROOT, "Scripts", "run_opensim_knee_SO.py")).read()
ns = {}
exec(re.search(r"def solve_so.*?return acts, mu \* c_res\n", src, re.S).group(0), ns)
rng = np.random.default_rng(7)
worst_cost, worst_con = 0.0, 0.0
for _ in range(300):
    n = int(rng.integers(3, 14))
    c = list(rng.normal(0, 60, n))
    lb, ub = [0.01] * n, [1.0] * n
    b = float(rng.normal(0, 150))
    a, ar = ns["solve_so"](c, lb, ub, b, 1.0)
    f = np.sum(np.square(a)) + ar ** 2
    r = minimize(lambda x: np.sum(x ** 2), np.full(n + 1, 0.1),
                 bounds=[(l, u) for l, u in zip(lb, ub)] + [(None, None)],
                 constraints=[{"type": "eq", "fun": lambda x: np.dot(c, x[:-1]) + x[-1] - b}],
                 method="SLSQP", options={"ftol": 1e-14, "maxiter": 500})
    worst_cost = max(worst_cost, (f - r.fun) / max(r.fun, 1e-9))
    worst_con = max(worst_con, abs(np.dot(c, a) + ar - b))
add("V10", "SO solver: max relative cost above SLSQP optimum", worst_cost, 0.0, 1e-4, "scipy SLSQP, 300 random cases")
add("V11", "SO solver: max moment-equation residual (N.m)", worst_con, 0.0, 1e-6, "same")

out = pd.DataFrame(checks)
out.to_csv(os.path.join(ROOT, "Results", "verification_checks.csv"), index=False)
print(out[["check", "quantity", "this_work", "reference", "result"]].to_string(index=False))
print("\n%d / %d PASS" % ((out.result == "PASS").sum(), len(out)))
