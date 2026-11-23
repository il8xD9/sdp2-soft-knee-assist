"""
run_actuator_bag_SO.py  -  OpenSim 4.6 knee static optimisation WITH the final bladder actuator
==============================================================================================
Patient : man 70 kg / 1.70 m, 2 months after ACLR (Buttner 2025 group-mean waveforms, stance 0.705 s)
Model   : gait2392 scaled x0.9444 to 70 kg / 1.70 m (same file as the 30 Oct 2026 no-device run)
Device  : knee_assist_r = CoordinateActuator on knee_angle_r (extension only) + PrescribedController
          torque constant k = 206 990 mm^3 (Model B, 3-D virtual work, hand calc v6 SH-C04)
          -> max torque  20 kPa : 4.140 N.m      27 kPa : 5.589 N.m
Torque laws (Basem B1-B8 FINAL):
   Option 1  8.43-44 % stance : tau = alpha x deficit
   Option 2  13-36 %  stance  : tau = MIN(alpha x deficit, MAX(patient moment, 0))
   then  tau_delivered = MIN(tau, p_lim x k)   (bag pressure limit)  and tau = 0 if knee flexion <= 0 deg (DR-B6-2)
alpha  : 0.05, 0.10, 0.125, 0.15, 0.169, 0.20 (+ 0.50 as an extra check)
Runs   : Healthy baseline, ACL 2 mo baseline, 2 options x 2 pressures x 7 alpha (delivered),
         2 options x 7 alpha (requested = ideal torque source, no pressure limit) -> 44 conditions.
Static optimisation (same formulation as Scripts/run_opensim_knee_SO.py of the project):
   min sum(a_i^2) + a_res^2   s.t.  sum(r_i a_i F_i^max,FLV) + a_res = M_net - T_device,  0 <= a_i <= 1
   r_i from OpenSim computeMomentArm, F^max from calcInextensibleTendonActiveFiberForce.
Run headless:  java -cp jython.jar;org-opensim-modeling.jar org.python.util.jython run_actuator_bag_SO.py
or in the OpenSim 4.6 GUI: Scripts > Run.   Jython 2.5 compatible, ASCII only.
"""
from __future__ import division
import os, sys, math, time

try:
    import opensim as osim
    RUNTIME = "CPython + opensim"
except:
    import org.opensim.modeling as osim
    RUNTIME = "Jython %s + OpenSim Java API" % sys.version.split()[0]

# ------------------------------------------------------------------ settings
# Folder that contains Inputs/ Models/ Scripts/ ('' = find it automatically).
# If the run says "project folder not found", type the path here, e.g. r"C:\Users\me\Desktop\OPensim Result\Actuator_Run"
PROJECT_DIR = r""


def _find_base():
    cands = []
    if PROJECT_DIR:
        cands.append(PROJECT_DIR)
    try:
        cands.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except:
        pass
    try:
        if sys.argv and sys.argv[0]:
            cands.append(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
    except:
        pass
    cwd = os.getcwd()
    cands += [cwd, os.path.dirname(cwd)]
    home = os.path.expanduser("~")
    for b in [os.path.join(home, "Desktop"), os.path.join(home, "OneDrive", "Desktop"), os.path.join(home, "Documents"), "C:\\"]:
        cands.append(os.path.join(b, "OPensim Result", "Actuator_Run"))
        cands.append(os.path.join(b, "Actuator_Run"))
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "Models", "gait2392_scaled_70kg_170cm.osim")) \
                and os.path.isdir(os.path.join(c, "Inputs")):
            return os.path.abspath(c)
    raise RuntimeError("project folder not found: set PROJECT_DIR at the top of run_actuator_bag_SO.py")


BASE = _find_base()
INP = os.path.join(BASE, "Inputs")
MOD = os.path.join(BASE, "Models")
RES = os.path.join(BASE, "Results")
SCALED = os.path.join(MOD, "gait2392_scaled_70kg_170cm.osim")
KNEE = "knee_angle_r"
K_TORQUE = 206990e-9                  # m^3  (N.m per Pa)
P_LIM = {"20kPa": 20.0, "27kPa": 27.0}
ALPHAS = [0.05, 0.10, 0.125, 0.15, 0.169, 0.20, 0.50]
OPT = {"O1": (8.43, 44.0), "O2": (13.0, 36.0)}
BWH = 70.0 * 9.80665 * 1.70          # 1166.99 N.m per BW*h
T_STANCE = 0.705
HEALTHY_PEAK = None                   # filled from data
RESERVE_OPT = 1.0
QUAD = {"RF": "rect_fem", "VL": "vas_lat", "VM": "vas_med", "VI": "vas_int"}
HAMS = ["semimem", "semiten", "bifemlh", "bifemsh"]
GAS = ["med_gas", "lat_gas"]
LOG = []


def log(m):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), m)
    LOG.append(line)
    print(line)


def mkdirs(d):
    if not os.path.isdir(d):
        os.makedirs(d)


def read_csv(path):
    f = open(path, "r")
    lines = [l.strip() for l in f.read().splitlines() if l.strip()]
    f.close()
    cols = lines[0].split(",")
    rows = [l.split(",") for l in lines[1:]]
    return cols, rows


def read_sto(path):
    f = open(path, "r")
    lines = f.read().splitlines()
    f.close()
    i = [k for k, l in enumerate(lines) if l.strip().lower() == "endheader"][0]
    cols = lines[i + 1].split()
    rows = [[float(v) for v in l.split()] for l in lines[i + 2:] if l.strip()]
    return cols, rows


def col(cols, rows, name):
    j = cols.index(name)
    return [float(r[j]) for r in rows]


def interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return ys[-1]


def write_sto(path, name, cols, rows, deg="no"):
    f = open(path, "w")
    f.write("%s\nversion=1\nnRows=%d\nnColumns=%d\ninDegrees=%s\nendheader\n" % (name, len(rows), len(cols), deg))
    f.write("\t".join(cols) + "\n")
    for r in rows:
        f.write("\t".join(["%.8f" % v for v in r]) + "\n")
    f.close()


def write_csv(path, cols, rows):
    f = open(path, "w")
    f.write(",".join(cols) + "\n")
    for r in rows:
        out = []
        for v in r:
            if isinstance(v, str) or isinstance(v, unicode):
                out.append(v)
            else:
                out.append("%.6g" % v)
        f.write(",".join(out) + "\n")
    f.close()


def save_model(model, path):
    f = getattr(model, "printToXML", None)
    if f is None:
        f = getattr(model, "print")
    f(path)


# ------------------------------------------------------------------ input data (2-month patient)
def load_patient():
    c, r = read_csv(os.path.join(INP, "buttner2025_stance_knee_moment_BWh.csv"))
    pct = col(c, r, "pct_stance")
    mh = [v * BWH for v in col(c, r, "KEM_Control_2months")]
    ma = [v * BWH for v in col(c, r, "KEM_ACLR_2months")]
    c2, r2 = read_csv(os.path.join(INP, "buttner2025_stance_knee_angle_deg.csv"))
    flex = col(c2, r2, "KFA_ACLR_2months")
    cs, rs = read_sto(os.path.join(INP, "ACL_2Months_Baseline_knee_speed.sto"))
    u = col(cs, rs, "knee_angle_r_u")
    cm, rm = read_sto(os.path.join(INP, "ACL_2Months_Baseline_net_knee_moment.sto"))
    mnet_file = col(cm, rm, "knee_angle_r_moment")
    # grid: 1 % frames plus the exact Option-1 onset 8.43 %
    grid = sorted(pct + [8.43])
    d = {"pct": grid, "time": [], "flex": [], "u": [], "mnet": [], "mh": [], "deficit": []}
    for x in grid:
        d["time"].append(x / 100.0 * T_STANCE)
        d["flex"].append(interp(x, pct, flex))
        d["u"].append(interp(x, pct, u))
        d["mnet"].append(interp(x, pct, ma))
        d["mh"].append(interp(x, pct, mh))
        d["deficit"].append(interp(x, pct, mh) - interp(x, pct, ma))
    # check: net moment from the Buttner table equals the OpenSim input file of the no-device run
    dmax = max([abs(a - b * 1.0) for a, b in zip([interp(x, pct, ma) for x in pct], mnet_file)])
    d["check_mnet_vs_file"] = dmax
    return d


def load_healthy():
    cm, rm = read_sto(os.path.join(INP, "Healthy_Baseline_net_knee_moment.sto"))
    cs, rs = read_sto(os.path.join(INP, "Healthy_Baseline_knee_speed.sto"))
    ck, rk = read_sto(os.path.join(INP, "Healthy_Baseline_kinematics.mot"))
    t = col(cm, rm, "time")
    d = {"pct": [i + 1.0 for i in range(len(t))], "time": t,
         "flex": [-v for v in col(ck, rk, KNEE)], "u": col(cs, rs, "knee_angle_r_u"),
         "mnet": col(cm, rm, "knee_angle_r_moment")}
    d["mh"] = d["mnet"]
    d["deficit"] = [0.0] * len(t)
    return d


# ------------------------------------------------------------------ device torque laws
def torque_profile(d, opt, alpha, plim_kpa):
    """returns (tau_requested_law, tau_delivered) lists"""
    lo, hi = OPT[opt]
    req, dev = [], []
    tmax = None
    if plim_kpa is not None:
        tmax = plim_kpa * 1000.0 * K_TORQUE
    for x, dfc, m, fl in zip(d["pct"], d["deficit"], d["mnet"], d["flex"]):
        if x < lo - 1e-9 or x > hi + 1e-9:
            t = 0.0
        else:
            t = alpha * dfc
            if opt == "O2":
                t = min(t, max(m, 0.0))
            t = max(t, 0.0)
        if fl <= 0.0:                 # DR-B6-2: no torque with the knee straight / hyperextended
            t = 0.0
        req.append(t)
        dev.append(min(t, tmax) if tmax is not None else t)
    return req, dev


# ------------------------------------------------------------------ OpenSim helpers
def add_actuator(model, times, torques, max_ctrl, lo_pct, hi_pct):
    ca = osim.CoordinateActuator(KNEE)
    ca.setName("knee_assist_r")
    ca.setOptimalForce(1.0)
    ca.setMinControl(0.0)
    ca.setMaxControl(max_ctrl)
    model.addForce(ca)
    pc = osim.PrescribedController()
    pc.setName("knee_assist_controller")
    pc.addActuator(ca)
    fn = osim.PiecewiseLinearFunction()
    eps = 1e-6
    pts = []
    for t, v in zip(times, torques):
        pts.append((t, v))
    # make the on/off steps sharp: zero just before the first and just after the last non-zero frame
    nz = [i for i, (t, v) in enumerate(pts) if v > 0]
    out = []
    for i, (t, v) in enumerate(pts):
        if nz and i == nz[0] and i > 0:
            out.append((t - eps, 0.0))
        out.append((t, v))
        if nz and i == nz[-1] and i < len(pts) - 1:
            out.append((t + eps, 0.0))
    for t, v in out:
        fn.addPoint(t, v)
    try:
        pc.prescribeControlForActuator("knee_assist_r", fn)
    except:
        pc.prescribeControlForActuator(0, fn)
    model.addController(pc)
    try:
        model.finalizeConnections()
    except:
        pass


def device_from_model(model, state):
    act = osim.CoordinateActuator.safeDownCast(model.getForceSet().get("knee_assist_r"))
    try:
        return act.computeActuation(state)
    except:
        return act.getControl(state) * act.getOptimalForce()


def solve_so(c, lb, ub, b, c_res):
    def g(mu):
        s = c_res * c_res * mu
        for ci, l, u in zip(c, lb, ub):
            a = mu * ci
            if a < l:
                a = l
            elif a > u:
                a = u
            s += ci * a
        return s
    lo, hi = -1e-3, 1e-3
    k = 0
    while g(hi) < b and k < 200:
        hi *= 2.0
        k += 1
    k = 0
    while g(lo) > b and k < 200:
        lo *= 2.0
        k += 1
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        if g(mid) < b:
            lo = mid
        else:
            hi = mid
    mu = 0.5 * (lo + hi)
    return [min(max(mu * ci, l), u) for ci, l, u in zip(c, lb, ub)], mu * c_res


KNEE_MUSCLES = []


def knee_muscles(model, state, knee):
    out = []
    musc = model.getMuscles()
    for i in range(musc.getSize()):
        mus = musc.get(i)
        rmax = 0.0
        for qdeg in [5.0, 0.0, -20.0, -45.0, -90.0]:
            knee.setValue(state, math.radians(qdeg), False)
            model.realizePosition(state)
            rmax = max(rmax, abs(mus.computeMomentArm(state, knee)))
        if rmax > 1e-3:
            out.append(str(mus.getName()))
    knee.setValue(state, 0.0, False)
    return out


def group_of(name):
    for lab, key in QUAD.items():
        if key in name:
            return lab
    for key in HAMS:
        if key in name:
            return "HAM"
    for key in GAS:
        if key in name:
            return "GAS"
    return "OTHER"


def run_condition(cid, d, tau, max_ctrl, window, save, meta):
    times = d["time"]
    model = osim.Model(SCALED)
    model.setName("gait2392_knee_assist_" + cid)
    add_actuator(model, times, tau, max_ctrl, window[0], window[1])
    state = model.initSystem()
    if save:
        save_model(model, os.path.join(MOD, cid + ".osim"))
    cs = model.getCoordinateSet()
    knee = cs.get(KNEE)
    if not KNEE_MUSCLES:
        KNEE_MUSCLES.extend(knee_muscles(model, state, knee))
        log("Knee-crossing muscles (%d): %s" % (len(KNEE_MUSCLES), ", ".join(KNEE_MUSCLES)))
    musc = model.getMuscles()
    mus_obj = [musc.get(n) for n in KNEE_MUSCLES]
    lb = [m.getMinControl() for m in mus_obj]
    ub = [m.getMaxControl() for m in mus_obj]
    rows, act_rows, frc_rows = [], [], []
    maxdiff = 0.0
    for k in range(len(times)):
        state.setTime(times[k])
        for cn in range(cs.getSize()):
            co = cs.get(cn)
            if not co.getLocked(state):
                co.setValue(state, 0.0, False)
                co.setSpeedValue(state, 0.0)
        cs.get("pelvis_ty").setValue(state, 0.95, False)
        knee.setValue(state, math.radians(-d["flex"][k]), False)
        knee.setSpeedValue(state, d["u"][k])
        model.realizeVelocity(state)
        t_dev = device_from_model(model, state)
        maxdiff = max(maxdiff, abs(t_dev - tau[k]))
        r = [m.computeMomentArm(state, knee) for m in mus_obj]
        fmax = [max(m.calcInextensibleTendonActiveFiberForce(state, 1.0), 0.0) for m in mus_obj]
        c = [ri * fi for ri, fi in zip(r, fmax)]
        m_bio = d["mnet"][k] - t_dev
        a, a_res = solve_so(c, lb, ub, m_bio, RESERVE_OPT)
        f = [ai * fi for ai, fi in zip(a, fmax)]
        g = {"RF": 0.0, "VL": 0.0, "VM": 0.0, "VI": 0.0, "HAM": 0.0, "GAS": 0.0, "OTHER": 0.0}
        ga = {"RF": 0.0, "VL": 0.0, "VM": 0.0, "VI": 0.0}
        m_ext, m_flex = 0.0, 0.0
        for n, fi, ai, ri in zip(KNEE_MUSCLES, f, a, r):
            lab = group_of(n)
            g[lab] += fi
            if lab in ga:
                ga[lab] = ai
            if ri * fi > 0:
                m_ext += ri * fi
            else:
                m_flex += ri * fi
        quad = g["RF"] + g["VL"] + g["VM"] + g["VI"]
        resid = sum([ri * fi for ri, fi in zip(r, f)]) + a_res * RESERVE_OPT - m_bio
        rows.append([d["pct"][k], times[k], d["flex"][k], d["u"][k], d["mnet"][k], d["mh"][k], d["deficit"][k],
                     t_dev, t_dev / K_TORQUE / 1000.0, t_dev * d["u"][k], m_bio, d["mnet"][k] + t_dev,
                     m_ext, m_flex, a_res * RESERVE_OPT, resid,
                     g["RF"], g["VL"], g["VM"], g["VI"], quad, g["HAM"], g["GAS"], g["OTHER"], sum(f),
                     ga["RF"], ga["VL"], ga["VM"], ga["VI"], (ga["RF"] + ga["VL"] + ga["VM"] + ga["VI"]) / 4.0])
        act_rows.append([times[k]] + a + [a_res])
        frc_rows.append([times[k]] + f + [a_res * RESERVE_OPT])
    cols = ["pct_stance", "time_s", "knee_flexion_deg", "knee_angle_r_speed_rad_s", "net_knee_moment_Nm",
            "healthy_knee_moment_Nm", "deficit_Nm", "device_torque_Nm", "bag_pressure_kPa", "device_power_W",
            "muscle_required_moment_H1_Nm", "patient_plus_device_H2_Nm", "muscle_extensor_moment_Nm",
            "muscle_flexor_moment_Nm", "reserve_Nm", "residual_Nm",
            "F_RF_N", "F_VL_N", "F_VM_N", "F_VI_N", "F_quadriceps_N", "F_hamstrings_N", "F_gastrocnemius_N",
            "F_other_knee_N", "F_all_knee_muscles_N", "a_RF", "a_VL", "a_VM", "a_VI", "a_quad_mean"]
    write_csv(os.path.join(RES, cid + "_SO_summary.csv"), cols, rows)
    write_sto(os.path.join(RES, cid + "_SO_activation.sto"), cid + "_SO_activation",
              ["time"] + KNEE_MUSCLES + ["knee_reserve"], act_rows)
    write_sto(os.path.join(RES, cid + "_SO_force.sto"), cid + "_SO_force",
              ["time"] + KNEE_MUSCLES + ["knee_reserve_Nm"], frc_rows)
    write_sto(os.path.join(RES, cid + "_actuator_controls.sto"), cid + "_controls",
              ["time", "knee_assist_r"], [[t, v] for t, v in zip(times, tau)])
    log("   %-28s peak device %.3f N.m (model read-back max diff %.1e)  peak quad %.1f N  max|reserve| %.4f" %
        (cid, max(tau), maxdiff, max([r_[20] for r_ in rows]), max([abs(r_[14]) for r_ in rows])))
    meta["readback_maxdiff"] = maxdiff
    return cols, rows


# ------------------------------------------------------------------ metrics
def trapz(xs, ys):
    s = 0.0
    for i in range(1, len(xs)):
        s += 0.5 * (ys[i] + ys[i - 1]) * (xs[i] - xs[i - 1])
    return s


def metrics(cid, meta, cols, rows, base_rows, window):
    C = dict([(n, i) for i, n in enumerate(cols)])
    g = lambda rr, n: [r[C[n]] for r in rr]
    pct = g(rows, "pct_stance")
    t = g(rows, "time_s")
    tau = g(rows, "device_torque_Nm")
    mnet = g(rows, "net_knee_moment_Nm")
    quad = g(rows, "F_quadriceps_N")
    bquad = g(base_rows, "F_quadriceps_N")
    ham = g(rows, "F_hamstrings_N")
    bham = g(base_rows, "F_hamstrings_N")
    gas = g(rows, "F_gastrocnemius_N")
    allm = g(rows, "F_all_knee_muscles_N")
    ball = g(base_rows, "F_all_knee_muscles_N")
    mbio = g(rows, "muscle_required_moment_H1_Nm")
    h2 = g(rows, "patient_plus_device_H2_Nm")
    pw = g(rows, "device_power_W")
    aq = g(rows, "a_quad_mean")
    baq = g(base_rows, "a_quad_mean")
    lo, hi = window
    inw = [i for i, x in enumerate(pct) if lo - 1e-9 <= x <= hi + 1e-9]
    grid1 = [i for i in inw if abs(pct[i] - round(pct[i])) < 1e-9]     # 1 % frames only (Basem's frame count)
    on = [i for i in inw if tau[i] > 0]
    i21 = pct.index(21.0)
    pk = max(tau)
    ipk = tau.index(pk)
    w_t = [t[i] for i in inw]
    pos_w = sum([0.5 * (max(pw[i], 0) + max(pw[i - 1], 0)) * (t[i] - t[i - 1]) for i in range(1, len(t))])
    neg_w = sum([0.5 * (min(pw[i], 0) + min(pw[i - 1], 0)) * (t[i] - t[i - 1]) for i in range(1, len(t))])
    over = [i for i in grid1 if tau[i] > mnet[i] + 1e-9 and tau[i] > 0]
    flexor_frames = [i for i in grid1 if mbio[i] < -1e-6]
    qimp = trapz(w_t, [quad[i] for i in inw])
    bqimp = trapz(w_t, [bquad[i] for i in inw])
    m = {
        "cond_id": cid, "option": meta.get("opt", "-"), "pressure_limit": meta.get("plim", "-"),
        "profile": meta.get("ptype", "-"), "alpha": meta.get("alpha", 0.0),
        "peak_device_torque_Nm": pk, "peak_time_ms": t[ipk] * 1000.0, "peak_pct_stance": pct[ipk],
        "device_torque_at_21pct_Nm": tau[i21],
        "onset_torque_Nm": tau[on[0]] if on else 0.0, "onset_ms": t[on[0]] * 1000.0 if on else 0.0,
        "offset_torque_Nm": tau[on[-1]] if on else 0.0, "offset_ms": t[on[-1]] * 1000.0 if on else 0.0,
        "peak_bag_pressure_kPa": pk / K_TORQUE / 1000.0,
        "pressure_needed_for_request_kPa": meta.get("req_peak", pk) / K_TORQUE / 1000.0,
        "requested_peak_Nm": meta.get("req_peak", pk),
        "frames_saturated_at_limit": meta.get("n_sat", 0),
        "torque_impulse_Nms": trapz(t, tau),
        "device_work_positive_J": pos_w, "device_work_negative_J": neg_w,
        "frames_in_window_1pct": len(grid1), "frames_above_patient_moment": len(over),
        "frames_muscle_moment_flexor_H1": len(flexor_frames),
        "min_muscle_required_moment_in_window_Nm": min([mbio[i] for i in inw]) if inw else 0.0,
        "muscle_required_moment_at_21pct_Nm": mbio[i21],
        "muscle_share_left_at_21pct_H1": mbio[i21] / mnet[i21] if mnet[i21] > 0 else 0.0,
        "H2_peak_patient_plus_device_Nm": max(h2[:60]),
        "H2_pct_of_healthy": max(h2[:60]) / HEALTHY_PEAK * 100.0,
        "quad_force_peak_N": max(quad), "quad_force_at_21pct_N": quad[i21],
        "quad_force_peak_in_window_N": max([quad[i] for i in inw]),
        "quad_force_window_impulse_Ns": qimp,
        "quad_activation_mean_in_window": sum([aq[i] for i in inw]) / max(len(inw), 1),
        "hamstring_force_peak_in_window_N": max([ham[i] for i in inw]),
        "gastrocnemius_force_peak_in_window_N": max([gas[i] for i in inw]),
        "all_knee_muscle_force_peak_in_window_N": max([allm[i] for i in inw]),
        "max_abs_reserve_Nm": max([abs(r[C["reserve_Nm"]]) for r in rows]),
        "max_abs_residual_Nm": max([abs(r[C["residual_Nm"]]) for r in rows]),
        "device_readback_maxdiff_Nm": meta.get("readback_maxdiff", 0.0),
    }
    bq_peak = max(bquad)
    bq_w = max([bquad[i] for i in inw])
    m["quad_peak_reduction_pct"] = (bq_peak - m["quad_force_peak_N"]) / bq_peak * 100.0
    m["quad_at_21pct_reduction_pct"] = (bquad[i21] - quad[i21]) / bquad[i21] * 100.0 if bquad[i21] > 0 else 0.0
    m["quad_window_impulse_reduction_pct"] = (bqimp - qimp) / bqimp * 100.0 if bqimp > 0 else 0.0
    m["quad_activation_window_reduction_pct"] = 0.0
    bam = sum([baq[i] for i in inw]) / max(len(inw), 1)
    if bam > 0:
        m["quad_activation_window_reduction_pct"] = (bam - m["quad_activation_mean_in_window"]) / bam * 100.0
    bh = max([bham[i] for i in inw])
    m["hamstring_change_in_window_N"] = m["hamstring_force_peak_in_window_N"] - bh
    m["all_knee_muscle_change_pct"] = (m["all_knee_muscle_force_peak_in_window_N"] - max([ball[i] for i in inw])) / \
        max([ball[i] for i in inw]) * 100.0
    return m


def setup_xml(cid, mot_name):
    return """<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40600">
  <AnalyzeTool name="%(c)s">
    <model_file>../Models/%(c)s.osim</model_file>
    <replace_force_set>false</replace_force_set>
    <force_set_files />
    <results_directory>./Analyze_%(c)s</results_directory>
    <output_precision>8</output_precision>
    <initial_time>0.007050</initial_time>
    <final_time>0.705000</final_time>
    <solve_for_equilibrium_for_auxiliary_states>false</solve_for_equilibrium_for_auxiliary_states>
    <AnalysisSet name="Analyses"><objects>
        <Actuation name="Actuation"><on>true</on><start_time>0.007050</start_time><end_time>0.705000</end_time><step_interval>1</step_interval><in_degrees>true</in_degrees></Actuation>
        <MuscleAnalysis name="MuscleAnalysis"><on>true</on><start_time>0.007050</start_time><end_time>0.705000</end_time><step_interval>1</step_interval><in_degrees>true</in_degrees><muscle_list> all</muscle_list><moment_arm_coordinate_list> knee_angle_r</moment_arm_coordinate_list><compute_moments>true</compute_moments></MuscleAnalysis>
    </objects><groups /></AnalysisSet>
    <ControllerSet name="Controllers"><objects /><groups /></ControllerSet>
    <external_loads_file />
    <states_file />
    <coordinates_file>%(m)s</coordinates_file>
    <speeds_file />
    <lowpass_cutoff_frequency_for_coordinates>-1</lowpass_cutoff_frequency_for_coordinates>
  </AnalyzeTool>
</OpenSimDocument>
""" % {"c": cid, "m": mot_name}


def write_mot(path, d):
    names = ["pelvis_tilt", "pelvis_list", "pelvis_rotation", "pelvis_tx", "pelvis_ty", "pelvis_tz", "hip_flexion_r",
             "hip_adduction_r", "hip_rotation_r", "knee_angle_r", "ankle_angle_r", "subtalar_angle_r", "mtp_angle_r",
             "hip_flexion_l", "hip_adduction_l", "hip_rotation_l", "knee_angle_l", "ankle_angle_l", "subtalar_angle_l",
             "mtp_angle_l", "lumbar_extension", "lumbar_bending", "lumbar_rotation"]
    rows = []
    for t, fl in zip(d["time"], d["flex"]):
        r = [t] + [0.0] * len(names)
        r[1 + names.index("pelvis_ty")] = 0.95
        r[1 + names.index("knee_angle_r")] = -fl
        rows.append(r)
    write_sto(path, "ACL_2Months_kinematics_with_8.43pct_frame", ["time"] + names, rows, deg="yes")


# ------------------------------------------------------------------ main
def main():
    global HEALTHY_PEAK
    t0 = time.time()
    mkdirs(RES)
    mkdirs(os.path.join(BASE, "Setups"))
    log("Runtime: %s | %s" % (RUNTIME, osim.opensimCommon.GetVersionAndDate()))
    log("Model: %s" % SCALED)
    d = load_patient()
    HEALTHY_PEAK = max(d["mh"])
    log("2-month data: %d frames (1-100 %% + 8.43 %%); healthy peak %.3f N.m; patient peak %.3f N.m; deficit peak %.3f N.m at %.0f %%; "
        "net moment vs OpenSim input file max diff %.2e N.m" %
        (len(d["pct"]), HEALTHY_PEAK, max(d["mnet"][:60]), max(d["deficit"]), d["pct"][d["deficit"].index(max(d["deficit"]))],
         d["check_mnet_vs_file"]))
    log("Device: k = %.0f mm3 -> T(20 kPa) = %.4f N.m, T(27 kPa) = %.4f N.m; alpha_lim = %.4f / %.4f (on 33 N.m)" %
        (K_TORQUE * 1e9, 20e3 * K_TORQUE, 27e3 * K_TORQUE, 20e3 * K_TORQUE / 33.0, 27e3 * K_TORQUE / 33.0))
    write_mot(os.path.join(BASE, "Setups", "ACL_2Months_kinematics.mot"), d)
    write_csv(os.path.join(RES, "input_waveforms_2months.csv"),
              ["pct_stance", "time_s", "knee_flexion_deg", "knee_angle_r_speed_rad_s", "patient_moment_Nm",
               "healthy_moment_Nm", "deficit_Nm"],
              [[a, b, c, e, f, g_, h] for a, b, c, e, f, g_, h in zip(d["pct"], d["time"], d["flex"], d["u"], d["mnet"],
                                                                     d["mh"], d["deficit"])])
    allm = []
    # healthy reference
    hd = load_healthy()
    hcols, hrows = run_condition("Healthy_Baseline", hd, [0.0] * len(hd["time"]), 1.0, (0, 0), False, {})
    # ACL baseline
    meta = {"opt": "-", "plim": "-", "ptype": "no device", "alpha": 0.0}
    bcols, brows = run_condition("ACL2mo_Baseline", d, [0.0] * len(d["time"]), 1.0, (0, 0), True, meta)
    mb = metrics("ACL2mo_Baseline", meta, bcols, brows, brows, (8.43, 44.0))
    allm.append(mb)
    hq = max([r[20] for r in hrows])
    log("Reference: healthy peak quad %.1f N (30 Oct run: 985.5)  ACL 2 mo peak quad %.1f N (30 Oct run: 235.8)" %
        (hq, mb["quad_force_peak_N"]))
    conds = []
    for opt in ["O1", "O2"]:
        for a in ALPHAS:
            conds.append((opt, None, a))
            for pl in ["20kPa", "27kPa"]:
                conds.append((opt, pl, a))
    for opt, pl, a in conds:
        req, dev = torque_profile(d, opt, a, P_LIM[pl] if pl else None)
        ptype = "delivered" if pl else "requested"
        cid = "ACL2mo_%s_%s_a%s" % (opt, pl if pl else "ideal", ("%.3f" % a).replace("0.", ""))
        n_sat = len([1 for r_, v in zip(req, dev) if r_ - v > 1e-9])
        meta = {"opt": opt, "plim": pl if pl else "none (ideal)", "ptype": ptype, "alpha": a,
                "req_peak": max(req), "n_sat": n_sat}
        maxc = (P_LIM[pl] * 1000.0 * K_TORQUE) if pl else max(1.0, max(req) * 1.01)
        save = pl is not None
        cols, rows = run_condition(cid, d, dev, maxc, OPT[opt], save, meta)
        if save:
            f = open(os.path.join(BASE, "Setups", cid + "_Setup_Analyze.xml"), "w")
            f.write(setup_xml(cid, "ACL_2Months_kinematics.mot"))
            f.close()
        allm.append(metrics(cid, meta, cols, rows, brows, OPT[opt]))
    keys = ["cond_id", "option", "pressure_limit", "profile", "alpha", "requested_peak_Nm", "peak_device_torque_Nm",
            "peak_time_ms", "peak_pct_stance", "device_torque_at_21pct_Nm", "onset_ms", "onset_torque_Nm", "offset_ms",
            "offset_torque_Nm", "peak_bag_pressure_kPa", "pressure_needed_for_request_kPa", "frames_saturated_at_limit",
            "torque_impulse_Nms", "device_work_positive_J", "device_work_negative_J", "frames_in_window_1pct",
            "frames_above_patient_moment", "frames_muscle_moment_flexor_H1", "min_muscle_required_moment_in_window_Nm",
            "muscle_required_moment_at_21pct_Nm", "muscle_share_left_at_21pct_H1", "H2_peak_patient_plus_device_Nm",
            "H2_pct_of_healthy", "quad_force_peak_N", "quad_peak_reduction_pct", "quad_force_at_21pct_N",
            "quad_at_21pct_reduction_pct", "quad_force_peak_in_window_N", "quad_force_window_impulse_Ns",
            "quad_window_impulse_reduction_pct", "quad_activation_mean_in_window", "quad_activation_window_reduction_pct",
            "hamstring_force_peak_in_window_N", "hamstring_change_in_window_N", "gastrocnemius_force_peak_in_window_N",
            "all_knee_muscle_force_peak_in_window_N", "all_knee_muscle_change_pct", "max_abs_reserve_Nm",
            "max_abs_residual_Nm", "device_readback_maxdiff_Nm"]
    write_csv(os.path.join(RES, "ALL_conditions_metrics.csv"), keys, [[m[k] for k in keys] for m in allm])
    log("FINISHED %d conditions (+ healthy reference) in %.1f s" % (len(allm), time.time() - t0))
    f = open(os.path.join(RES, "run_log.txt"), "w")
    f.write("\n".join(LOG) + "\n")
    f.close()


main()
