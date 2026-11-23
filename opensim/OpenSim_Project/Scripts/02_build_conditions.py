#!/usr/bin/env python3
"""
02_build_conditions.py
----------------------
PURPOSE : Pre-process the gait data, build the knee-assist actuator torque profiles and
          write every OpenSim input file (.mot / .sto / controller .xml) for every
          simulation condition.
INPUT   : Input_Data/*.csv  (written by 01_extract_input_data.py)
OUTPUT  : Simulations/<condition folders>/*  + Simulations/conditions_manifest.csv
          Actuator/*  (parameters, torque profiles, capability check, validation vs team table)
RUN     : python Scripts/02_build_conditions.py

PRE-PROCESSING DONE HERE (all automatic, nothing typed by hand):
  * Unit conversion   : moment BW*height -> N.m  (M = KEM * m * g * h ; m = 70 kg, h = 1.70 m,
                        ASM-BIO-02/03);  N.m/kg -> N.m (Winter);  deg -> rad for speeds.
  * Coordinate conv.  : project knee flexion (+) -> OpenSim gait2392 knee_angle_r (flexion -).
                        Project internal knee moment (extension +) == gait2392
                        knee_angle_r generalized force (extension +)  -> no sign flip.
  * Time normalisation: % stance -> time with stance duration T_st per epoch (Table 8,
                        ASM-BIO-04); Winter % gait cycle -> time with stride 1.1396 s.
  * Filtering         : NOT applied (waveforms are smooth group means extracted from vector
                        paths; a 6 Hz Butterworth altered the angle by up to 0.57 deg).
                        Velocities by 2nd-order central differences (numpy.gradient).
  * Synchronisation   : angle, moment, deficit and actuator torque share the same
                        1 % stance grid (same source figure panels, Buttner 2025).
"""
import os, json
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(ROOT, "Input_Data")
SIM = os.path.join(ROOT, "Simulations")
ACT = os.path.join(ROOT, "Actuator")

G = 9.80665          # m/s2 (definition; Table G0)
M_BODY = 70.0        # kg   design patient (ASM-BIO-03 table basis)
H_BODY = 1.70        # m    design stature (ASM-BIO-02)

# ---------------------------------------------------------------------------------
# ACTUATOR PARAMETERS  (Acuator_data.docx, SDP-II Mechanical Design & FEA, progress 6.4)
# ---------------------------------------------------------------------------------
P_MAX_PA = 100e3                      # Table 3-2 row 3; constraint C7 (0-100 kPa, relief-limited)
CONTACT_W = 45.4e-3                   # m  Section 6 Step 1 (29.8 flat + 2 x 7.8 R20 arcs)
CONTACT_S = 68.5e-3                   # m  Section 6 Step 1 (shank half of 137 mm straight length)
AREA_V4 = CONTACT_W * CONTACT_S       # m2 = 3109.9 mm2 (actuator V4, Acuator_data.docx) - superseded
AREA = 3140.3e-6                      # m2 = 3140.3 mm2  CAD V4.1 contact area (current mechanical baseline)
R_ARM = 34.25e-3                      # m  moment arm, Section 6 Case 1 (fixed r)
F_MAX = P_MAX_PA * AREA               # N  = 310.99 N
T_MAX = F_MAX * R_ARM                 # N.m = 10.76 N.m (capability at 100 kPa, CAD V4.1; was 10.65 with V4)
TMAX_TXT = "%.2f N.m" % T_MAX
ALPHA_PRIMARY = 0.20                  # team working case: alpha 0.20 -> 6.59 N.m at 2 months (CALC-BIO-03 Table 6B)
APTXT = "%.2f" % ALPHA_PRIMARY
ALPHA_LOW = 0.25
ALPHAS = [0.10, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]   # alpha sweep (user request)


def atag(a):
    return "a%03d" % int(round(a * 100))


actuator = {
    "name": "knee_assist_r",
    "type_in_OpenSim": "CoordinateActuator on knee_angle_r (generalized torque about the knee "
                       "flexion axis, extension +) driven by a PrescribedController",
    "physical_device": "Posterior-knee TPU bladder (actuator-V4), restraint cover, strap harness",
    "working_principle": "pressure p on the shank-side contact patch -> force F = p*A acting at the "
                         "patch centroid -> knee extension torque T = F*r (Section 6)",
    "max_pressure_kPa": P_MAX_PA / 1e3,
    "contact_width_mm": CONTACT_W * 1e3,
    "contact_length_mm": CONTACT_S * 1e3,
    "contact_area_mm2": round(AREA * 1e6, 2),
    "moment_arm_mm": R_ARM * 1e3,
    "moment_arm_basis": "Case 1 - fixed r (no angle-dependent r_eff(theta) data exist; +/-20 % r -> +/-20 % T)",
    "max_force_N": round(F_MAX, 2),
    "max_torque_Nm": round(T_MAX, 3),
    "torque_direction": "knee EXTENSION only (bladder can only push); min control 0",
    "attachment": "posterior knee; strap harness two arms above / two below joint line; "
                  "shank-side patch starts at knee-centre level, centroid 34.25 mm distal",
    "operating_window_pct_stance": {"preop": [9, 37], "2 months": [9, 44], "4 months": [9, 44],
                                    "6 months": [9, 44], "12 months": [9, 40]},
    "window_source": "Table 7 candidate window (8.4-44 / 9-40 % stance) on the 1 % grid used by "
                     "team Table 6A (in_candidate_window flags)",
    "timing_rule": "torque = alpha * m * g * h * dM(phi) inside window, 0 outside (Table G0 / CALC-BIO-03)",
    "alpha_primary": ALPHA_PRIMARY,
    "alpha_primary_reason": "largest tabulated alpha that the 100 kPa actuator meets at every epoch "
                            "for 70 kg / 1.70 m (Table 6-1, constraint C18; used in C20)",
    "alpha_low": ALPHA_LOW,
    "alpha_max_rule": "alpha_max = T_max / peak full-deficit torque (capability-limited, peak = 10.65 N.m)",
    "alpha_sweep": ALPHAS,
    "alpha_sweep_profiles": "requested = alpha x m g h dM (ideal torque source, may exceed the device); "
                            "device_limited = min(requested, %s) (what the V4.1 bladder delivers at <= 100 kPa)" % TMAX_TXT,
    "stroke_mm": "NOT PROVIDED", "speed": "NOT PROVIDED (t_system, valve/tube flow open - C20/C21)",
    "rated_power": "NOT PROVIDED (mechanical power is computed here from torque x knee angular velocity)",
    "mass_on_leg_g": 97.04,
    "free_flexion": "vented outside the window; must not resist ~30 deg before toe-off and ~65 deg in swing",
    "body_mass_kg": M_BODY, "stature_m": H_BODY,
}

# ---------------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------------
ang = pd.read_csv(os.path.join(IN, "buttner2025_stance_knee_angle_deg.csv"))
mom = pd.read_csv(os.path.join(IN, "buttner2025_stance_knee_moment_BWh.csv"))
dfc = pd.read_csv(os.path.join(IN, "stance_deficit_table5A.csv"))
win = pd.read_csv(os.path.join(IN, "healthy_winter1987_full_gait.csv"))
team6a = pd.read_csv(os.path.join(IN, "team_required_torque_table6A.csv"))
pct = ang["pct_stance"].values  # 1..100

EPOCHS = ["preop", "2months", "4months", "6months", "12months"]
EPOCH_LABEL = {"preop": "Pre-op", "2months": "2 Months", "4months": "4 Months",
               "6months": "6 Months", "12months": "12 Months"}
EPOCH_TEAM = {"preop": "preop", "2months": "2 months", "4months": "4 months",
              "6months": "6 months", "12months": "12 months"}
# Stance duration (s).  Table 8 (ASM-BIO-04) except pre-op, which Table 8 does not list:
# pre-op uses the SAME ASM-BIO-04 ACLR relation T = 1.0334 - 0.2807 v with Buttner pre-op v = 1.16 m/s.
T_ST = {"healthy": 0.655, "preop": round(1.0334 - 0.2807 * 1.16, 4), "2months": 0.705,
        "4months": 0.685, "6months": 0.683, "12months": 0.677}
WINDOW = {"preop": (9, 37), "2months": (9, 44), "4months": (9, 44), "6months": (9, 44),
          "12months": (9, 40)}

ctrl_kfa = ang[[c for c in ang.columns if c.startswith("KFA_Control")]].mean(axis=1).values
ctrl_kem = mom[[c for c in mom.columns if c.startswith("KEM_Control")]].mean(axis=1).values


def bwh_to_nm(x):
    return np.asarray(x) * M_BODY * G * H_BODY


def full_deficit_torque(epoch):
    """alpha = 1 torque (N.m) inside the candidate window, 0 outside (Table G0 rule)."""
    dM = dfc["dM_%s_BWh" % epoch].values
    lo, hi = WINDOW[epoch]
    inwin = (pct >= lo) & (pct <= hi) & (dM > 0)
    return np.where(inwin, bwh_to_nm(dM), 0.0), inwin


# ---- validation of the torque rule against the team's own Table 6A (alpha .25/.50/.75/1.0, 70 kg)
val = []
for e in ["2months", "4months", "6months", "12months"]:
    tf, _ = full_deficit_torque(e)
    for a in [0.25, 0.5, 0.75, 1.0]:
        t = team6a[(team6a.epoch == EPOCH_TEAM[e]) & (team6a.body_mass_kg == 70) &
                   (np.isclose(team6a.alpha, a))].sort_values("pct_stance")
        diff = np.abs(a * tf - t["tau_assist_Nm"].values)
        val.append({"epoch": EPOCH_TEAM[e], "alpha": a, "max_abs_diff_Nm": round(diff.max(), 4),
                    "peak_this_work_Nm": round((a * tf).max(), 3),
                    "peak_team_table6A_Nm": t["tau_assist_Nm"].max(),
                    "PASS(<=0.01 N.m)": bool(diff.max() <= 0.01)})
val = pd.DataFrame(val)
os.makedirs(ACT, exist_ok=True)
val.to_csv(os.path.join(ACT, "validation_torque_rule_vs_team_Table6A.csv"), index=False)
print(val.to_string(index=False))

# ---------------------------------------------------------------------------------
# CONDITIONS
# ---------------------------------------------------------------------------------
GAIT2392_COORDS = ["pelvis_tilt", "pelvis_list", "pelvis_rotation", "pelvis_tx", "pelvis_ty",
                   "pelvis_tz", "hip_flexion_r", "hip_adduction_r", "hip_rotation_r",
                   "knee_angle_r", "ankle_angle_r", "subtalar_angle_r", "mtp_angle_r",
                   "hip_flexion_l", "hip_adduction_l", "hip_rotation_l", "knee_angle_l",
                   "ankle_angle_l", "subtalar_angle_l", "mtp_angle_l", "lumbar_extension",
                   "lumbar_bending", "lumbar_rotation"]
PELVIS_TY_VISUAL = 0.95  # m - visual offset only so the model stands above the floor in the GUI


def write_sto(path, name, cols, data, in_degrees=False):
    data = np.column_stack(data)
    with open(path, "w") as f:
        f.write("%s\nversion=1\nnRows=%d\nnColumns=%d\ninDegrees=%s\nendheader\n" %
                (name, data.shape[0], data.shape[1], "yes" if in_degrees else "no"))
        f.write("\t".join(cols) + "\n")
        for row in data:
            f.write("\t".join("%.8f" % v for v in row) + "\n")


def controller_xml(cond_id, t, tau, max_ctrl=None):
    pts_x = " ".join("%.6f" % v for v in t)
    pts_y = " ".join("%.6f" % v for v in tau)
    return """<?xml version="1.0" encoding="UTF-8" ?>
<!-- Knee-assist actuator + controller for condition %s.
     Paste inside <ForceSet><objects> (actuator) and <ControllerSet><objects> (controller)
     of a gait2392 model, or let Scripts/run_opensim_knee_SO.py add them automatically. -->
<OpenSimDocument Version="40000">
  <CoordinateActuator name="knee_assist_r">
    <!-- equivalent of the posterior bladder: T = p*A*r ; extension (+) only -->
    <coordinate>knee_angle_r</coordinate>
    <optimal_force>1</optimal_force>
    <min_control>0</min_control>
    <max_control>%.4f</max_control>
  </CoordinateActuator>
  <PrescribedController name="knee_assist_controller">
    <actuator_list>knee_assist_r</actuator_list>
    <FunctionSet name="ControlFunctions">
      <objects>
        <PiecewiseLinearFunction name="knee_assist_r">
          <x> %s </x>
          <y> %s </y>
        </PiecewiseLinearFunction>
      </objects>
    </FunctionSet>
  </PrescribedController>
</OpenSimDocument>
""" % (cond_id, T_MAX if max_ctrl is None else max_ctrl, pts_x, pts_y)


manifest = []
profiles = []


def make_condition(cond_id, folder, label, group, epoch, kfa_deg, kem_nm, t, pct_axis,
                   axis_name, tau, alpha, profile_src, primary, phase_note,
                   profile_type="none", limited_id=None):
    d = os.path.join(SIM, folder)
    os.makedirs(d, exist_ok=True)
    kfa_deg = np.asarray(kfa_deg, float)
    q_deg = -kfa_deg                                   # gait2392: flexion negative
    dkfa = np.gradient(kfa_deg, t)                     # deg/s, flexion velocity
    u = np.deg2rad(-dkfa)                              # rad/s, knee_angle_r speed (extension +)
    tau = np.asarray(tau, float)
    F = tau / R_ARM
    p_kpa = F / AREA / 1e3
    power = tau * u                                    # W (+ = device does positive work)
    m_bio = kem_nm - tau
    # .mot (all 23 gait2392 coordinates; only the knee is data-driven)
    cols = ["time"] + GAIT2392_COORDS
    mat = [t]
    for c in GAIT2392_COORDS:
        if c == "knee_angle_r":
            mat.append(q_deg)
        elif c == "pelvis_ty":
            mat.append(np.full_like(t, PELVIS_TY_VISUAL))
        else:
            mat.append(np.zeros_like(t))
    write_sto(os.path.join(d, cond_id + "_kinematics.mot"), cond_id + "_kinematics", cols, mat, True)
    write_sto(os.path.join(d, cond_id + "_knee_speed.sto"), cond_id + "_knee_speed",
              ["time", "knee_angle_r_u"], [t, u])
    write_sto(os.path.join(d, cond_id + "_net_knee_moment.sto"), cond_id + "_net_knee_moment",
              ["time", "knee_angle_r_moment"], [t, kem_nm])
    write_sto(os.path.join(d, cond_id + "_actuator_controls.sto"), cond_id + "_controls",
              ["time", "knee_assist_r"], [t, tau])
    with open(os.path.join(d, cond_id + "_actuator_controller.xml"), "w") as f:
        f.write(controller_xml(cond_id, t, tau,
                               max(T_MAX, float(np.max(tau))) if profile_type == "requested" else T_MAX))
    tab = pd.DataFrame({axis_name: pct_axis, "time_s": t, "knee_flexion_deg": kfa_deg,
                        "knee_angle_r_deg_OpenSim": q_deg, "knee_flex_velocity_deg_s": dkfa,
                        "knee_angle_r_speed_rad_s": u, "net_knee_moment_Nm": kem_nm,
                        "net_knee_moment_Nm_per_kg": kem_nm / M_BODY,
                        "actuator_torque_Nm": tau, "actuator_force_N": F,
                        "actuator_pressure_kPa": p_kpa, "actuator_power_W": power,
                        "biological_knee_moment_Nm": m_bio})
    tab.to_csv(os.path.join(d, cond_id + "_inputs_and_actuator.csv"), index=False)
    manifest.append({"cond_id": cond_id, "folder": folder.replace("\\", "/"), "label": label,
                     "group": group, "epoch": epoch, "assisted": int(np.any(tau > 0)),
                     "alpha": alpha, "profile_type": profile_type,
                     "within_capability": int(np.max(tau) <= T_MAX + 1e-9),
                     "device_limited_cond_id": limited_id if limited_id else cond_id,
                     "profile_source": profile_src, "primary_12": int(primary),
                     "x_axis": axis_name, "n_frames": len(t), "t_start": t[0], "t_end": t[-1],
                     "phase_covered": phase_note,
                     "mot": cond_id + "_kinematics.mot", "speed": cond_id + "_knee_speed.sto",
                     "moment": cond_id + "_net_knee_moment.sto",
                     "controls": cond_id + "_actuator_controls.sto"})
    p = tab[[axis_name, "time_s", "actuator_torque_Nm", "actuator_force_N", "actuator_pressure_kPa",
             "actuator_power_W"]].copy()
    p.insert(0, "cond_id", cond_id)
    profiles.append(p)


tau_full = {e: full_deficit_torque(e)[0] for e in EPOCHS}
alpha_max = {e: T_MAX / tau_full[e].max() for e in EPOCHS}
DESIGN_EPOCH = "2months"   # governing case (largest requirement) -> device design command



def add_alpha_sweep(id_prefix, folder_prefix, label, group, epoch, kfa, kem, t, tau_alpha1, src):
    """alpha sweep: 'requested' (ideal torque source) for every alpha; when the requested peak
    exceeds the 100 kPa capability an extra 'device_limited' run = min(requested, T_MAX)."""
    for a in ALPHAS:
        tag = atag(a)
        req = a * tau_alpha1
        lim_id = None
        if req.max() > T_MAX + 1e-9:
            lim_id = id_prefix + tag + "_lim"
            make_condition(lim_id, folder_prefix + tag + "_lim",
                           "%s (alpha %.2f, device-limited %s)" % (label, a, TMAX_TXT), group, epoch, kfa, kem,
                           t, pct, "pct_stance", np.minimum(req, T_MAX), a,
                           src + "; clipped at the 100 kPa capability", False, "stance 1-100 %",
                           profile_type="device_limited")
        make_condition(id_prefix + tag, folder_prefix + tag, "%s (alpha %.2f)" % (label, a), group, epoch,
                       kfa, kem, t, pct, "pct_stance", req, a, src, abs(a - ALPHA_PRIMARY) < 1e-9,
                       "stance 1-100 %", profile_type="requested", limited_id=lim_id)


# ---- Healthy (Buttner matched controls, stance) ----
t_h = pct / 100.0 * T_ST["healthy"]
kem_h = bwh_to_nm(ctrl_kem)
make_condition("Healthy_Baseline", "Healthy_Baseline", "Healthy", "Healthy", "healthy",
               ctrl_kfa, kem_h, t_h, pct, "pct_stance", np.zeros_like(t_h), 0.0, "none", True,
               "stance 1-100 %")
make_condition("Healthy_Assisted_" + atag(ALPHA_PRIMARY) + "cap", "Healthy_Assisted/" + atag(ALPHA_PRIMARY) + "cap",
               "Healthy + Actuator (alpha %s, capped at own net ext. moment)" % APTXT, "Healthy", "healthy",
               ctrl_kfa, kem_h, t_h, pct, "pct_stance",
               np.minimum(ALPHA_PRIMARY * tau_full[DESIGN_EPOCH], np.clip(kem_h, 0, None)), ALPHA_PRIMARY,
               "design command x " + APTXT + " capped so that T <= max(M_net; 0) (proposed over-assistance guard; not team spec)",
               False, "stance 1-100 %", profile_type="capped")
add_alpha_sweep("Healthy_Assisted_", "Healthy_Assisted/", "Healthy + Actuator", "Healthy", "healthy",
                ctrl_kfa, kem_h, t_h, tau_full[DESIGN_EPOCH],
                "device design command = 2-month required profile x alpha (governing case)")

# ---- ACL epochs ----
for e in EPOCHS:
    folder = "ACL_" + {"preop": "PreOp", "2months": "2Months", "4months": "4Months",
                        "6months": "6Months", "12months": "12Months"}[e]
    t_e = pct / 100.0 * T_ST[e]
    kfa = ang["KFA_ACLR_%s" % e].values
    kem = bwh_to_nm(mom["KEM_ACLR_%s" % e].values)
    make_condition(folder + "_Baseline", folder + "/Baseline", "ACL " + EPOCH_LABEL[e], "ACL", e,
                   kfa, kem, t_e, pct, "pct_stance", np.zeros_like(t_e), 0.0, "none", True,
                   "stance 1-100 %")
    add_alpha_sweep(folder + "_Assisted_", folder + "/Assisted_", "ACL %s + Actuator" % EPOCH_LABEL[e],
                    "ACL", e, kfa, kem, t_e, tau_full[e],
                    "assist-as-needed: alpha x own-epoch deficit (Table G0)")
    make_condition(folder + "_Assisted_" + atag(ALPHA_PRIMARY) + "cap", folder + "/Assisted_" + atag(ALPHA_PRIMARY) + "cap",
                   "ACL %s + Actuator (alpha %s, capped)" % (EPOCH_LABEL[e], APTXT), "ACL", e, kfa, kem, t_e, pct,
                   "pct_stance", np.minimum(ALPHA_PRIMARY * tau_full[e], np.clip(kem, 0, None)), ALPHA_PRIMARY,
                   "alpha " + APTXT + " x deficit capped so that T <= max(M_net; 0) (proposed over-assistance guard; not team spec)",
                   False, "stance 1-100 %", profile_type="capped")

# ---- Supplementary: Healthy full gait cycle (Winter 1987) ----
T_STRIDE = 1.1396
pgc = win["pct_GC"].values
t_w = pgc / 100.0 * T_STRIDE
kem_w = win["M_int_Nm_per_kg"].values * M_BODY
# device design command mapped to % gait cycle with Winter toe-off 60 % (stance % = %GC / 0.60)
stance_equiv = pgc / 0.60
tau_w_full = np.where(stance_equiv <= 100, np.interp(stance_equiv, pct, tau_full[DESIGN_EPOCH],
                                                     left=0.0, right=0.0), 0.0)
make_condition("HealthyWinter_FullGait_Baseline", "Healthy_FullGait_Winter/Baseline",
               "Healthy full cycle (Winter 1987)", "Healthy_Winter", "healthy_winter",
               win["knee_angle_deg"].values, kem_w, t_w, pgc, "pct_GC", np.zeros_like(t_w), 0.0,
               "none", False, "full gait cycle 0-100 %GC")
make_condition("HealthyWinter_FullGait_Assisted_" + atag(ALPHA_PRIMARY), "Healthy_FullGait_Winter/Assisted_" + atag(ALPHA_PRIMARY),
               "Healthy full cycle + Actuator (alpha %s)" % APTXT, "Healthy_Winter", "healthy_winter",
               win["knee_angle_deg"].values, kem_w, t_w, pgc, "pct_GC", ALPHA_PRIMARY * tau_w_full,
               ALPHA_PRIMARY, "device design command (2-month profile x " + APTXT + ") mapped to %GC (TO = 60 %)",
               False, "full gait cycle 0-100 %GC", profile_type="requested")

man = pd.DataFrame(manifest)
man.to_csv(os.path.join(SIM, "conditions_manifest.csv"), index=False)
pd.concat(profiles).to_csv(os.path.join(ACT, "actuator_profiles_all_conditions.csv"), index=False)

# ---- capability check per epoch ----
cap = []
for e in EPOCHS:
    full_pk = tau_full[e].max()
    cap.append({"epoch": EPOCH_LABEL[e], "full_deficit_peak_Nm(alpha=1)": round(full_pk, 3),
                "alpha_0.20_peak_Nm": round(0.20 * full_pk, 3),
                "alpha_0.25_peak_Nm": round(0.25 * full_pk, 3),
                "alpha_0.30_peak_Nm": round(0.30 * full_pk, 3),
                "alpha_0.50_peak_Nm": round(0.50 * full_pk, 3),
                "capability_100kPa_Nm": round(T_MAX, 3),
                "alpha_max_at_100kPa": round(alpha_max[e], 4),
                "pressure_needed_alpha0.20_kPa": round(0.20 * full_pk / R_ARM / AREA / 1e3, 1),
                "pressure_needed_alpha0.30_kPa": round(0.30 * full_pk / R_ARM / AREA / 1e3, 1),
                "alpha_0.20_within_capability": bool(0.20 * full_pk <= T_MAX + 1e-9),
                "alpha_0.30_within_capability": bool(0.30 * full_pk <= T_MAX + 1e-9)})
cap = pd.DataFrame(cap)
cap.to_csv(os.path.join(ACT, "actuator_capability_check.csv"), index=False)
print(cap.to_string(index=False))

actuator["alpha_max_per_epoch"] = {EPOCH_LABEL[e]: round(alpha_max[e], 4) for e in EPOCHS}
actuator["stance_duration_s"] = T_ST
with open(os.path.join(ACT, "actuator_parameters.json"), "w") as f:
    json.dump(actuator, f, indent=2)
pd.DataFrame([{"parameter": k, "value": json.dumps(v) if isinstance(v, (dict, list)) else v}
              for k, v in actuator.items()]).to_csv(os.path.join(ACT, "actuator_parameters.csv"),
                                                   index=False)
print("\nconditions written:", len(man))
print(man[["cond_id", "assisted", "alpha", "primary_12", "n_frames"]].to_string(index=False))
