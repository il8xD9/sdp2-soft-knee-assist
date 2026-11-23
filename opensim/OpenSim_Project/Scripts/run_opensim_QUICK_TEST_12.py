"""
run_opensim_QUICK_TEST_12.py  --  QUICK TEST copy (12 primary conditions only).
  Identical to run_opensim_knee_SO.py except ONLY_PRIMARY_12 = True.
  Original header:  ONE script that runs the whole OpenSim part of the project.
====================================================================================
HOW TO RUN (pick ONE):
  A) OpenSim 4.x GUI (no installation needed):
       File > Open Model is NOT needed.  Scripts > Run...  > select this file.
       (the GUI runs it with its built-in Jython interpreter)
  B) Python with the OpenSim package (conda install -c opensim-org opensim):
       python run_opensim_knee_SO.py
If the project folder or gait2392 model is not found automatically, type the two paths
in USER SETTINGS below (PROJECT_DIR, MODEL_PATH) and run again.  Use a folder path
without Arabic characters (OpenSim cannot open non-ASCII paths).

WHAT IT DOES (all automatic):
  1. Loads OpenSim's bundled gait2392_simbody.osim (23 DOF, 92 muscles) and scales it
     uniformly to the design patient (70 kg, 1.70 m; ASM-BIO-02/03).
  2. For every condition listed in Simulations/conditions_manifest.csv (116 conditions:
     6 baselines; alpha sweep 0.10-1.00 (11 values) x 6 groups as 'requested' torque (66);
     'device-limited' copies where the request exceeds 10.76 N.m (CAD V4.1); 6 'capped'; 2 Winter
     full-cycle). The 12 primary conditions = 6 baselines + alpha 0.20 (team working case):
       - adds the knee-assist actuator  'knee_assist_r'  (CoordinateActuator on
         knee_angle_r, extension only, max 10.76 N.m) + a PrescribedController that
         carries the condition's torque-vs-time profile;
       - saves the model to Models/Healthy or Models/ACL  (<condition>.osim; primary 12 only
         unless SAVE_ALL_MODELS = True);
       - reads the device torque BACK FROM THE OPENSIM MODEL at every frame;
       - solves knee STATIC OPTIMIZATION frame by frame with OpenSim's muscle model:
             minimise   sum(a_i^2) + a_res^2
             subject to sum(r_i * a_i * F_i^max,FLV) + a_res*R_opt = M_net - T_device
                        min_control_i <= a_i <= max_control_i
         r_i      = OpenSim moment arm of muscle i about knee_angle_r (computeMomentArm)
         F^max,FLV= OpenSim rigid-tendon active fibre force at a = 1 (force-length-velocity,
                    pennation) = calcInextensibleTendonActiveFiberForce  (the quantity
                    OpenSim's own StaticOptimization tool uses)
         M_net    = net internal knee moment of the condition (source inverse dynamics)
       - optionally runs OpenSim's AnalyzeTool (MuscleAnalysis + Actuation) from the
         setup XML written next to the motion file (native cross-check of moment arms).
  3. Writes Results/OpenSim_SO/<condition>_SO_*.sto/.csv and ALL_conditions_SO_*.csv and
     Results/OpenSim_SO/run_log.txt.
  (To run one MuscleAnalysis by hand in the GUI instead: open Models/<group>/<cond>.osim
   first, then Tools > Analyze > Load the condition's _Setup_MuscleAnalysis.xml > Run;
   the GUI uses the currently open model.)
  Then: run
        python Scripts/05_postprocess_opensim_results.py   to make the muscle graphs/tables.

Compatible with Jython 2.7 (OpenSim GUI) and CPython 3 (opensim package).  ASCII only.
"""
from __future__ import division   # Jython 2.5 (OpenSim GUI) has no print_function; all prints are single-argument
import os
import sys
import csv
import math
import time

# =============================== USER SETTINGS ======================================
PROJECT_DIR = r""          # e.g. r"C:\sdp2_opensim\OpenSim_Project"   ('' = auto-detect)
MODEL_PATH = r""           # e.g. r"C:\Users\me\Documents\OpenSim\4.6\Models\Gait2392_Simbody\gait2392_simbody.osim"
SCALE_MODEL = True         # uniform scale to the design patient
TARGET_MASS_KG = 70.0      # ASM-BIO-03 table basis
GENERIC_HEIGHT_M = 1.80    # gait2392 generic subject (~1.8 m, 75.16 kg)
TARGET_HEIGHT_M = 1.70     # ASM-BIO-02
HIP_FLEXION_DEG = 0.0      # no hip data exist for the ACL epochs -> neutral (assumption)
ANKLE_ANGLE_DEG = 0.0      # no ankle data exist -> neutral (assumption)
QUAD_STRENGTH_FACTOR = 1.0 # 1.0 = generic strength. (<1 = sensitivity for quadriceps weakness)
RESERVE_OPTIMAL_FORCE = 1.0  # N.m, knee reserve actuator (heavily penalised, OpenSim practice)
RUN_NATIVE_MUSCLE_ANALYSIS = True   # OpenSim AnalyzeTool cross-check (12 primary conditions only)
ONLY_PRIMARY_12 = True     # True = run only the 12 primary conditions (fast test)
SAVE_ALL_MODELS = False    # False = save .osim only for the 12 primary conditions (others ~1 MB each)
# =====================================================================================

T_DEVICE_MAX = 10.7555     # N.m  (100 kPa x 3140.3 mm2 x 34.25 mm; CAD V4.1, Eq. 4.14 -> 10.76 N.m)
KNEE = "knee_angle_r"
QUAD_KEYS = [("RF", ("rect_fem", "recfem")), ("VL", ("vas_lat", "vaslat")),
             ("VM", ("vas_med", "vasmed")), ("VI", ("vas_int", "vasint"))]

# ------------------------------------------------------------------------- OpenSim import
RUNTIME = ""
try:
    import opensim as osim
    RUNTIME = "CPython %s + opensim package" % sys.version.split()[0]
except:
    try:
        import org.opensim.modeling as osim
        RUNTIME = "OpenSim GUI scripting (Jython %s)" % sys.version.split()[0]
    except:
        print("ERROR: OpenSim is not available in this Python. Run the script from the "
              "OpenSim GUI (Scripts > Run) or from a Python that has 'import opensim'.")
        raise

LOG_LINES = []
KNEE_MUSCLE_CACHE = []     # same model geometry for every condition -> scan once
try:
    _STR = basestring          # Jython / Python 2 (Java strings arrive as unicode)
except NameError:
    _STR = str


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    LOG_LINES.append(line)
    print(line)


def err():
    return str(sys.exc_info()[1]).replace("\n", " ")[:300]


def mkdirs(d):
    if not os.path.isdir(d):
        os.makedirs(d)


def save_model(model, path):
    f = getattr(model, "printToXML", None)
    if f is None:
        f = getattr(model, "print")        # Java name (keyword in Jython -> getattr)
    f(path)


# ------------------------------------------------------------------------- locate files
def find_project_dir():
    cands = []
    ov = globals().get("PROJECT_DIR_OVERRIDE", "")     # may be set in the Scripting Shell
    if ov:
        cands.append(ov)
    if PROJECT_DIR:
        cands.append(PROJECT_DIR)
    try:
        cands.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except:
        pass
    cwd = os.getcwd()
    cands += [cwd, os.path.dirname(cwd), os.path.dirname(os.path.dirname(cwd))]
    home = os.path.expanduser("~")
    for base in [home, os.path.join(home, "Desktop"), os.path.join(home, "Documents"),
                 os.path.join(home, "Downloads"), os.path.join(home, "OneDrive", "Desktop"),
                 os.path.join(home, "OneDrive", "Documents"), "C:\\", "D:\\"]:
        for sub in ["OpenSim_Project", os.path.join("sdp2_opensim", "OpenSim_Project"),
                    os.path.join("OpenSim_Project", "OpenSim_Project")]:
            cands.append(os.path.join(base, sub))
    # scan one folder level below the usual places (e.g. C:\SDP2_Opensim_New\OpenSim_Project)
    for base in ["C:\\", "D:\\", home, os.path.join(home, "Desktop"), os.path.join(home, "Documents"),
                 os.path.join(home, "Downloads"), os.path.join(home, "OneDrive", "Desktop")]:
        try:
            subs = os.listdir(base)
        except:
            subs = []
        for d in subs:
            for sub in ["OpenSim_Project", os.path.join("OpenSim_Project", "OpenSim_Project"), ""]:
                cands.append(os.path.join(base, d, sub))
    for c in cands:
        try:
            if c and os.path.isfile(os.path.join(c, "Simulations", "conditions_manifest.csv")):
                return os.path.abspath(c)
        except:
            pass
    return None


def find_model(proj):
    cands = []
    if MODEL_PATH:
        cands.append(MODEL_PATH)
    cands.append(os.path.join(proj, "Models", "gait2392_simbody.osim"))
    home = os.path.expanduser("~")
    for v in ["4.6", "4.5", "4.4", "4.3", "4.2", "4.1", "4.0"]:
        for docs in [os.path.join(home, "Documents"), os.path.join(home, "OneDrive", "Documents"),
                     os.path.join(home, "OneDrive", "Documents and Settings")]:
            cands.append(os.path.join(docs, "OpenSim", v, "Models", "Gait2392_Simbody",
                                      "gait2392_simbody.osim"))
        for root in ["C:\\OpenSim %s" % v, "C:\\Program Files\\OpenSim %s" % v,
                     "/Applications/OpenSim %s" % v]:
            cands.append(os.path.join(root, "Resources", "Models", "Gait2392_Simbody",
                                      "gait2392_simbody.osim"))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    # last resort: walk Documents/OpenSim
    for docs in [os.path.join(home, "Documents", "OpenSim"),
                 os.path.join(home, "OneDrive", "Documents", "OpenSim")]:
        if os.path.isdir(docs):
            for dp, dn, fn in os.walk(docs):
                for f in fn:
                    if f.lower() == "gait2392_simbody.osim":
                        return os.path.join(dp, f)
    return None


# ------------------------------------------------------------------------- file readers
def read_table(path):
    """Read an OpenSim .sto/.mot (header ... endheader) or a CSV into (columns, rows)."""
    f = open(path, "r")
    lines = f.read().splitlines()
    f.close()
    start = 0
    for i, l in enumerate(lines):
        if l.strip().lower() == "endheader":
            start = i + 1
            break
    if path.lower().endswith(".csv"):
        parsed = [r for r in csv.reader(lines[start:]) if r]
        return [c.strip() for c in parsed[0]], parsed[1:]
    cols = [c.strip() for c in lines[start].split()]
    rows = []
    for l in lines[start + 1:]:
        if l.strip():
            rows.append(l.split())
    return cols, rows


def read_manifest(proj):
    cols, rows = read_table(os.path.join(proj, "Simulations", "conditions_manifest.csv"))
    out = []
    for r in rows:
        d = {}
        for k, v in zip(cols, r):
            d[k] = v
        out.append(d)
    return out


def in_degrees(path):
    f = open(path, "r")
    head = f.read(2000).lower()
    f.close()
    return "indegrees=yes" in head.replace(" ", "")


def column(path, name):
    cols, rows = read_table(path)
    j = cols.index(name)
    return [float(r[j]) for r in rows]


def write_sto(path, name, cols, data_rows, in_degrees="no"):
    f = open(path, "w")
    f.write("%s\nversion=1\nnRows=%d\nnColumns=%d\ninDegrees=%s\nendheader\n" %
            (name, len(data_rows), len(cols), in_degrees))
    f.write("\t".join(cols) + "\n")
    for r in data_rows:
        f.write("\t".join(["%.8g" % v for v in r]) + "\n")
    f.close()


def write_csv(path, cols, data_rows, mode="w", header=True):
    f = open(path, mode)
    if header:
        f.write(",".join(cols) + "\n")
    for r in data_rows:
        f.write(",".join([str(v) if isinstance(v, _STR) else "%.8g" % v for v in r]) + "\n")
    f.close()


# ------------------------------------------------------------------------- model helpers
def scale_model(model, state):
    f = TARGET_HEIGHT_M / GENERIC_HEIGHT_M
    ss = osim.ScaleSet()
    bodies = model.getBodySet()
    for i in range(bodies.getSize()):
        sc = osim.Scale()
        sc.setSegmentName(bodies.get(i).getName())
        sc.setScaleFactors(osim.Vec3(f, f, f))
        sc.setApply(True)
        ss.cloneAndAppend(sc)
    ok = model.scale(state, ss, True, TARGET_MASS_KG)
    return ok, f


def total_mass(model):
    m = 0.0
    bodies = model.getBodySet()
    for i in range(bodies.getSize()):
        m += bodies.get(i).getMass()
    return m


def add_actuator(model, times, torques, max_ctrl=T_DEVICE_MAX):
    ca = osim.CoordinateActuator(KNEE)
    ca.setName("knee_assist_r")
    ca.setOptimalForce(1.0)
    ca.setMinControl(0.0)
    ca.setMaxControl(max_ctrl)
    model.addForce(ca)
    ctrl_ok = True
    try:
        pc = osim.PrescribedController()
        pc.setName("knee_assist_controller")
        pc.addActuator(ca)
        fn = osim.PiecewiseLinearFunction()
        for t, v in zip(times, torques):
            fn.addPoint(t, v)
        try:
            pc.prescribeControlForActuator("knee_assist_r", fn)
        except:
            pc.prescribeControlForActuator(0, fn)
        model.addController(pc)
    except:
        ctrl_ok = False
        log("   WARNING: PrescribedController not attached (%s); profile taken from file" % err())
    try:
        model.finalizeConnections()
    except:
        pass
    return ctrl_ok


def device_torque_from_model(model, state, act_name):
    act = None
    try:
        act = osim.CoordinateActuator.safeDownCast(model.getForceSet().get(act_name))
    except:
        act = None
    if act is None:
        return None, "no-actuator"
    try:
        return act.computeActuation(state), "computeActuation"
    except:
        pass
    try:
        return act.getControl(state) * act.getOptimalForce(), "getControl"
    except:
        pass
    try:
        model.realizeDynamics(state)
        return act.getActuation(state), "getActuation"
    except:
        return None, "failed: " + err()


def knee_muscles(model, state, knee):
    """Muscles whose moment arm about the knee exceeds 1 mm somewhere in 0..90 deg flexion."""
    out = []
    musc = model.getMuscles()
    for i in range(musc.getSize()):
        mus = musc.get(i)
        rmax = 0.0
        for qdeg in [5.0, 0.0, -20.0, -45.0, -90.0]:
            knee.setValue(state, math.radians(qdeg), False)
            model.realizePosition(state)
            try:
                r = mus.computeMomentArm(state, knee)
            except:
                r = mus.getGeometryPath().computeMomentArm(state, knee)
            rmax = max(rmax, abs(r))
        if rmax > 1e-3:
            out.append(str(mus.getName()))
    knee.setValue(state, 0.0, False)
    return out


def frame_capacities(model, state, mus_obj):
    """Max active force along the tendon at activation 1 for every muscle at this frame.
    Primary: OpenSim rigid-tendon value (as used by OpenSim StaticOptimization).
    Fallback: compliant-tendon equilibrium at activation 1 (if the primary call is missing)."""
    try:
        return [mo.calcInextensibleTendonActiveFiberForce(state, 1.0) for mo in mus_obj], \
            "rigid-tendon FLV"
    except:
        pass
    for mo in mus_obj:
        mo.setActivation(state, 1.0)
    model.equilibrateMuscles(state)
    model.realizeDynamics(state)
    vals = [mo.getActiveFiberForceAlongTendon(state) for mo in mus_obj]
    return vals, "equilibrium a=1 (fallback)"


def quad_label(name):
    n = name.lower()
    for lab, keys in QUAD_KEYS:
        for k in keys:
            if k in n:
                return lab
    return None


# ------------------------------------------------------------------------- static optimisation
def solve_so(c, lb, ub, b, c_res):
    """min sum a_i^2 + a_r^2  s.t. sum c_i a_i + c_res a_r = b,  lb<=a_i<=ub.
    Exact KKT solution: a_i = clip(mu*c_i, lb_i, ub_i), a_r = mu*c_res, g(mu)=b (bisection)."""
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
    acts = []
    for ci, l, u in zip(c, lb, ub):
        a = mu * ci
        acts.append(min(max(a, l), u))
    return acts, mu * c_res


def run_condition(proj, cond, scaled_path, all_long, all_wide):
    cid = cond["cond_id"]
    folder = os.path.join(proj, "Simulations", cond["folder"].replace("/", os.sep))
    group = "Healthy" if cond["group"].startswith("Healthy") else "ACL"
    outdir = os.path.join(proj, "Results", "OpenSim_SO")
    mkdirs(outdir)
    times = column(os.path.join(folder, cond["mot"]), "time")
    q_deg = column(os.path.join(folder, cond["mot"]), KNEE)
    if not in_degrees(os.path.join(folder, cond["mot"])):
        q_deg = [math.degrees(v) for v in q_deg]
    u = column(os.path.join(folder, cond["speed"]), "knee_angle_r_u")
    m_net = column(os.path.join(folder, cond["moment"]), "knee_angle_r_moment")
    tau_file = column(os.path.join(folder, cond["controls"]), "knee_assist_r")
    xname = cond["x_axis"]
    cols_in, rows_in = read_table(os.path.join(folder, cid + "_inputs_and_actuator.csv"))
    xs = [float(r[cols_in.index(xname)]) for r in rows_in]

    # ---- model with actuator + controller
    model = osim.Model(scaled_path)
    model.setName("gait2392_knee_assist_" + cid)
    # 'requested' alpha profiles are an ideal torque source (may exceed the 10.76 N.m device);
    # 'device_limited' / 'capped' profiles respect the 100 kPa limit
    ptype = cond.get("profile_type", "requested")
    max_ctrl = max(T_DEVICE_MAX, max(tau_file)) if ptype == "requested" else T_DEVICE_MAX
    ctrl_ok = add_actuator(model, times, tau_file, max_ctrl)
    is_primary = cond.get("primary_12", "0") == "1"
    state = model.initSystem()
    mdir = os.path.join(proj, "Models", group)
    mkdirs(mdir)
    model_path = os.path.join(mdir, cid + ".osim")
    if SAVE_ALL_MODELS or is_primary:
        save_model(model, model_path)

    cs = model.getCoordinateSet()
    knee = cs.get(KNEE)
    hip = cs.get("hip_flexion_r")
    ank = cs.get("ankle_angle_r")
    if not KNEE_MUSCLE_CACHE:
        KNEE_MUSCLE_CACHE.extend(knee_muscles(model, state, knee))
        log("Knee-crossing muscles (%d): %s" % (len(KNEE_MUSCLE_CACHE), ", ".join(KNEE_MUSCLE_CACHE)))
    names = list(KNEE_MUSCLE_CACHE)
    musc = model.getMuscles()
    mus_obj = [musc.get(n) for n in names]
    lb = []
    ub = []
    for mo in mus_obj:
        lb.append(mo.getMinControl())
        ub.append(mo.getMaxControl())

    act_rows, frc_rows, ma_rows, sum_rows = [], [], [], []
    cap_methods = {}
    dev_methods = {}
    max_dev_diff = 0.0
    for k in range(len(times)):
        state.setTime(times[k])
        for cn in range(cs.getSize()):
            co = cs.get(cn)
            if not co.getLocked(state):
                co.setSpeedValue(state, 0.0)
        hip.setValue(state, math.radians(HIP_FLEXION_DEG), False)
        ank.setValue(state, math.radians(ANKLE_ANGLE_DEG), False)
        knee.setValue(state, math.radians(q_deg[k]), False)
        knee.setSpeedValue(state, u[k])
        model.realizeVelocity(state)
        tau_dev, dev_method = device_torque_from_model(model, state, "knee_assist_r")
        if tau_dev is None or not ctrl_ok:
            tau_dev = tau_file[k]
            dev_method = "file (" + dev_method + ")"
        dev_methods[dev_method] = dev_methods.get(dev_method, 0) + 1
        max_dev_diff = max(max_dev_diff, abs(tau_dev - tau_file[k]))
        r, c = [], []
        for mo in mus_obj:
            try:
                ri = mo.computeMomentArm(state, knee)
            except:
                ri = mo.getGeometryPath().computeMomentArm(state, knee)
            r.append(ri)
        fmax, cap_method = frame_capacities(model, state, mus_obj)
        for i in range(len(mus_obj)):
            if quad_label(str(mus_obj[i].getName())):
                fmax[i] *= QUAD_STRENGTH_FACTOR
            if fmax[i] < 0:
                fmax[i] = 0.0
            c.append(r[i] * fmax[i])
        cap_methods[cap_method] = cap_methods.get(cap_method, 0) + 1
        m_bio = m_net[k] - tau_dev
        a, a_res = solve_so(c, lb, ub, m_bio, RESERVE_OPTIMAL_FORCE)
        forces = [ai * fi for ai, fi in zip(a, fmax)]
        reserve = a_res * RESERVE_OPTIMAL_FORCE
        m_mus = sum([ri * fi for ri, fi in zip(r, forces)])
        resid = m_mus + reserve - m_bio
        q = {"RF": 0.0, "VL": 0.0, "VM": 0.0, "VI": 0.0}
        qa = {"RF": 0.0, "VL": 0.0, "VM": 0.0, "VI": 0.0}
        for n, fo, ai in zip(names, forces, a):
            lab = quad_label(n)
            if lab:
                q[lab] += fo
                qa[lab] = ai
        quad = q["RF"] + q["VL"] + q["VM"] + q["VI"]
        act_rows.append([times[k]] + a + [a_res])
        frc_rows.append([times[k]] + forces + [reserve])
        ma_rows.append([times[k]] + r)
        sum_rows.append([xs[k], times[k], -q_deg[k], m_net[k], tau_dev, m_bio, m_mus, reserve,
                         resid, q["RF"], q["VL"], q["VM"], q["VI"], quad,
                         qa["RF"], qa["VL"], qa["VM"], qa["VI"]])
        for n, ai, fo, ri, fm in zip(names, a, forces, r, fmax):
            all_long.append([cid, "%.4g" % xs[k], "%.6g" % times[k], n, "%.6g" % ai, "%.6g" % fo,
                             "%.6g" % ri, "%.6g" % fm])

    write_sto(os.path.join(outdir, cid + "_SO_activation.sto"), cid + "_SO_activation",
              ["time"] + names + ["knee_reserve"], act_rows)
    write_sto(os.path.join(outdir, cid + "_SO_force.sto"), cid + "_SO_force",
              ["time"] + names + ["knee_reserve_Nm"], frc_rows)
    write_sto(os.path.join(outdir, cid + "_SO_moment_arm_knee.sto"), cid + "_moment_arms",
              ["time"] + names, ma_rows)
    scol = [xname, "time_s", "knee_flexion_deg", "net_knee_moment_Nm", "device_torque_Nm",
            "biological_knee_moment_Nm", "muscle_knee_moment_Nm", "reserve_Nm", "residual_Nm",
            "F_RF_N", "F_VL_N", "F_VM_N", "F_VI_N", "F_quadriceps_N",
            "a_RF", "a_VL", "a_VM", "a_VI"]
    write_csv(os.path.join(outdir, cid + "_SO_summary.csv"), scol, sum_rows)
    for rr in sum_rows:
        all_wide.append([cid] + rr)
    pk = max([rr[13] for rr in sum_rows])
    log("   %-38s muscles=%d  peak quad force=%.1f N  max|reserve|=%.3f N.m  "
        "device-from-model=%s (max diff vs file %.2e)  F_max method=%s" %
        (cid, len(names), pk, max([abs(rr[7]) for rr in sum_rows]), str(dev_methods), max_dev_diff,
         str(cap_methods)))

    if RUN_NATIVE_MUSCLE_ANALYSIS and os.path.isfile(model_path) and is_primary:
        setup = os.path.join(folder, cid + "_Setup_MuscleAnalysis.xml")
        if os.path.isfile(setup):
            try:
                at = osim.AnalyzeTool(setup)
                at.run()
                log("      native AnalyzeTool (MuscleAnalysis + Actuation) done -> %s" %
                    os.path.join(cond["folder"], "MuscleAnalysis"))
            except:
                log("      native AnalyzeTool skipped: %s" % err())
    return names, scol


def main():
    t0 = time.time()
    log("Runtime: " + RUNTIME)
    proj = find_project_dir()
    if proj is None:
        log("ERROR: project folder not found. Set PROJECT_DIR at the top of this script.")
        return
    log("Project folder: " + proj)
    mpath = find_model(proj)
    if mpath is None:
        log("ERROR: gait2392_simbody.osim not found. Set MODEL_PATH at the top of this script.")
        return
    log("Generic model: " + mpath)
    outdir = os.path.join(proj, "Results", "OpenSim_SO")
    mkdirs(outdir)

    base = osim.Model(mpath)
    state = base.initSystem()
    log("Generic model mass %.2f kg, %d muscles, %d coordinates" %
        (total_mass(base), base.getMuscles().getSize(), base.getCoordinateSet().getSize()))
    scaled_name = "gait2392_scaled_%dkg_%dcm.osim" % (int(TARGET_MASS_KG), int(TARGET_HEIGHT_M * 100))
    if SCALE_MODEL:
        try:
            ok, f = scale_model(base, state)
            if not ok:
                raise RuntimeError("Model.scale returned False")
            base.setName("gait2392_scaled_design_patient")
            state = base.initSystem()
            log("Scaled uniformly x%.4f, mass now %.2f kg" % (f, total_mass(base)))
        except:
            log("WARNING: scaling failed (%s) -> generic geometry used" % err())
            scaled_name = "gait2392_generic_copy.osim"
    else:
        scaled_name = "gait2392_generic_copy.osim"
    scaled_path = os.path.join(proj, "Models", scaled_name)
    mkdirs(os.path.join(proj, "Models"))
    save_model(base, scaled_path)
    log("Base model saved: " + scaled_path)

    conds = read_manifest(proj)
    if ONLY_PRIMARY_12:
        conds = [c for c in conds if c["primary_12"] == "1"]
    log("Conditions to run: %d" % len(conds))
    all_long, all_wide = [], []
    done = 0
    scol = None
    for cond in conds:
        try:
            names, scol = run_condition(proj, cond, scaled_path, all_long, all_wide)
            done += 1
        except:
            log("   ERROR in %s: %s" % (cond["cond_id"], err()))
    try:
        write_csv(os.path.join(outdir, "ALL_conditions_SO_long.csv"),
                  ["cond_id", "x", "time_s", "muscle", "activation", "force_N", "moment_arm_m",
                   "max_active_force_FLV_N"], all_long)
        if scol:
            f = open(os.path.join(outdir, "ALL_conditions_SO_summary.csv"), "w")
            f.write(",".join(["cond_id", "x"] + scol[1:]) + "\n")
            for r in all_wide:
                f.write(",".join([str(r[0])] + ["%.8g" % v for v in r[1:]]) + "\n")
            f.close()
    except:
        log("ERROR while writing the combined CSV files: %s" % err())
    finally:
        settings = ["RUNTIME=" + RUNTIME, "MODEL=" + mpath, "SCALE_MODEL=%s" % SCALE_MODEL,
                    "TARGET_MASS_KG=%g" % TARGET_MASS_KG, "TARGET_HEIGHT_M=%g" % TARGET_HEIGHT_M,
                    "HIP_FLEXION_DEG=%g" % HIP_FLEXION_DEG, "ANKLE_ANGLE_DEG=%g" % ANKLE_ANGLE_DEG,
                    "QUAD_STRENGTH_FACTOR=%g" % QUAD_STRENGTH_FACTOR,
                    "RESERVE_OPTIMAL_FORCE=%g" % RESERVE_OPTIMAL_FORCE,
                    "conditions_ok=%d/%d" % (done, len(conds)),
                    "elapsed_s=%.1f" % (time.time() - t0)]
        log("FINISHED: %d of %d conditions in %.1f s" % (done, len(conds), time.time() - t0))
        f = open(os.path.join(outdir, "run_log.txt"), "w")
        f.write("\n".join(settings) + "\n\n" + "\n".join(LOG_LINES) + "\n")
        f.close()
    print("Results in: " + outdir)


main()
