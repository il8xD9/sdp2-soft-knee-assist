# -*- coding: utf-8 -*-
"""Post-processing of a solved deck (.OUT of the Inventor Nastran solver, SOL 106) -> CSV / XLSX tables + images.

All numbers come from the solver output (final increment of every subcase, LOAD = 1.0):
  knee moment  M_ext = sum over the shank-half grids of ((X + u) - H) x F_spc, z component (N mm -> N m); positive =
               extension (flexion = +theta about +Z).
  stresses     max von Mises (both shell surfaces) of bladder and cover.
  cavity       volume enclosed by the deformed bladder mid-surface (closed capsule incl. caps).
  convergence  increments, iterations, bisections from the .LOG.
The other quantities in the code (rings, skin pressure, slip) belong to the full-device model and are empty here.
Usage: python -P post_process.py <run.OUT> [--quick]"""
import csv
import math
import os
import pickle
import re
import sys

import numpy as np

KIND_TABLES = [
    ("disp", "D I S P L A C E M E N T   V E C T O R"),
    ("spcf", "F O R C E S   O F   S I N G L E - P O I N T"),
    ("qforce", "F O R C E S   I N   Q U A D"),
    ("tforce", "F O R C E S   I N   T R I A"),
    ("qstress", "S T R E S S E S   I N   Q U A D"),
    ("tstress", "S T R E S S E S   I N   T R I A"),
    ("cgrid", "S T R E S S E S   O N   C O N T A C T   S U R F A C E"),
    ("cseg", "N O N L I N E A R   F O R C E S   I N   C O N T A C T"),
    ("ese", "E L E M E N T   S T R A I N   E N E R G I E S"),
    ("oload", "L O A D   V E C T O R"),
]


def fl(s):
    try:
        return float(s)
    except ValueError:
        return None


def parse_out(path, subs=None):
    """dict sub -> tables of the final increment (LOAD = 1.0); plus list of (sub, inc, load) seen"""
    res, seen = {}, []
    sub, load, table, cid = None, None, None, None
    with open(path, errors="replace") as fh:
        for line in fh:
            m = re.match(r"\s+LOAD INCREMENT = (\d+)\s+LOAD = (\S+)\s+SUBCASE (\d+)", line)
            if m:
                sub, load = int(m.group(3)), fl(m.group(2))
                if not seen or seen[-1][:2] != (sub, int(m.group(1))):
                    seen.append((sub, int(m.group(1)), load))
                continue
            hit = None
            for k, key in KIND_TABLES:
                if key in line:
                    hit = k
                    break
            if hit:
                table = hit
                if hit == "cgrid":
                    mm = re.search(r"S U R F A C E\s+(\d+)", line.replace("S U R F A C E", "S U R F A C E "))
                    cid = int(re.findall(r"(\d+)\s*$", line.strip())[0]) if re.findall(r"(\d+)\s*$", line.strip()) else 0
                continue
            if "MAXIMUM" in line or "TOTAL" in line and table not in ("ese",):
                if table != "ese":
                    table = None if "MAXIMUM" in line else table
            if table is None or sub is None or load is None or abs(load - 1.0) > 1e-6:
                continue
            if subs is not None and sub not in subs:      # make_figures: keep only the requested subcases (RAM)
                continue
            r = res.setdefault(sub, {k: {} for k, _ in KIND_TABLES})
            t = line.split()
            if not t:
                continue
            if table in ("disp", "spcf", "oload"):
                if len(t) == 8 and t[0].isdigit():
                    v = [fl(x) for x in t[2:8]]
                    if None not in v:
                        r[table][int(t[0])] = np.array(v)
            elif table in ("qforce", "tforce"):
                if t[0].isdigit():
                    vals = [fl(x) for x in t[1:] if fl(x) is not None]
                    if len(vals) >= 8:
                        r[table][int(t[0])] = np.array(vals[-8:])
            elif table in ("qstress", "tstress"):
                if t[0].isdigit():
                    vals = [fl(x) for x in t[1:] if fl(x) is not None]
                    if len(vals) >= 7:
                        cur = int(t[0])
                        r[table].setdefault(cur, []).append(vals[-1])
                        r["_cur"] = cur
                else:
                    vals = [fl(x) for x in t if fl(x) is not None]
                    if len(vals) == len(t) and len(vals) >= 7 and "_cur" in r:
                        r[table][r["_cur"]].append(vals[-1])
            elif table == "cgrid":
                if len(t) == 5 and t[0].isdigit():
                    r["cgrid"].setdefault(cid, {})[int(t[0])] = (fl(t[1]), fl(t[2]))
            elif table == "ese":
                m2 = re.search(r"TOTAL ENERGY OF ALL ELEMENTS IN (?:PROBLEM|SET)\s*=?\s*(\S+)", line)
                if m2:
                    r["ese"]["total"] = r["ese"].get("total", 0.0) + (fl(m2.group(1)) or 0.0)
                m3 = re.search(r"TYPE = (\w+)", line)
                if m3:
                    r["_esetype"] = m3.group(1)
                m4 = re.search(r"SUBTOTAL\s+(\S+)", line)
                if m4 and "_esetype" in r:
                    r["ese"][r["_esetype"]] = fl(m4.group(1))
    return res, seen


def parse_log(path):
    out = dict(iters={}, bis={}, levels={}, fatal=[], warn={})
    sub = None
    if not os.path.exists(path):
        return out
    for line in open(path, errors="replace"):
        m = re.search(r"LOAD LEVEL FOR SUBCASE\s+(\d+)\s+AT\s+([\d.Ee+-]+)\s+PERCENT", line)
        if m:
            sub = int(m.group(1))
            out["levels"].setdefault(sub, []).append(float(m.group(2)))
        if sub is not None and "SOLVING FOR DISPLACEMENTS" in line:
            out["iters"][sub] = out["iters"].get(sub, 0) + 1
        if sub is not None and "BISECTING CURRENT LOAD INCREMENT" in line:
            out["bis"][sub] = out["bis"].get(sub, 0) + 1
        m = re.search(r"(FATAL ERROR [A-Z]?\d+:.*)", line)
        if m:
            out["fatal"].append(m.group(1).strip())
        m = re.search(r"WARNING ([A-Z]\d+):", line)
        if m:
            out["warn"][m.group(1)] = out["warn"].get(m.group(1), 0) + 1
    return out


def tri_area_normal(p):
    return 0.5 * np.cross(p[1] - p[0], p[2] - p[0])


def face_area(p):
    if len(p) == 3:
        return np.linalg.norm(tri_area_normal(p))
    return 0.5 * np.linalg.norm(np.cross(p[2] - p[0], p[3] - p[1]))


def closed_volume(Xd, faces):
    v = 0.0
    for fc in faces:
        p = Xd[fc]
        tris = [p[[0, 1, 2]]] if len(fc) == 3 else [p[[0, 1, 2]], p[[0, 2, 3]]]
        for t in tris:
            v += np.dot(t[0], np.cross(t[1], t[2])) / 6.0
    return abs(v)


def main(out_path, quick=False):
    base = out_path[:-4]
    ipath = base + "_info.pkl"
    if not os.path.exists(ipath):
        # the run info is kept with the deck in model\<run>\
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        name = os.path.basename(base); run = os.path.basename(os.path.dirname(os.path.abspath(out_path)))
        for cand in (os.path.join(root, "model", run, name + "_info.pkl"),
                     os.path.join(root, "model", name, name + "_info.pkl")):
            if os.path.exists(cand):
                if run != name and os.path.basename(os.path.dirname(cand)) == name:
                    print("note: %s has no deck folder of its own; using the run info of model\\%s "
                          "(the latest deck of that name)" % (run, name))
                ipath = cand; break
    info = pickle.load(open(ipath, "rb"))
    mp = info["mesh"]
    if not os.path.isabs(mp):
        mp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), mp)
    mesh = pickle.load(open(mp, "rb"))
    X0, EL, S, meta = mesh["X"], mesh["el"], mesh["S"], mesh["meta"]
    H = np.asarray(info["H"])
    res, seen = parse_out(out_path)
    lg = parse_log(base + ".LOG")
    steps = info["steps"]
    nsub = len(steps)
    gid = lambda i: int(i) + 1
    # node areas of the device-side skin contact surfaces
    def node_areas(faces):
        a = {}
        for fc in faces:
            ar = face_area(X0[fc]) / len(fc)
            for n in fc:
                a[gid(n)] = a.get(gid(n), 0.0) + ar
        return a
    pad_faces = [p[0] for p in S["pad_bottom"]]
    ring_faces = [fc for r in S["rings"].values() for fc in r["skin"]]
    area = node_areas(pad_faces + ring_faces)
    pos = {g: X0[g - 1] for g in area}
    pairs = {p[0]: p[1] for p in info["pairs"]}
    skin_pairs = [k for k, nm in pairs.items() if nm.startswith("pad_skin") or nm.startswith("ring_skin")]
    zones = {"under_bladder": lambda x: abs(x[2]) <= 33.0 and abs(x[1]) <= 95.0 and x[0] > 0,
             "posterior_knee": lambda x: -40.0 <= x[1] <= 20.0 and abs(x[2]) <= 45.0 and x[0] > 0}
    for nm, r in S["rings"].items():
        ya, yb = min(r["rows"]), max(r["rows"])
        zones["ring_" + nm] = (lambda a_, b_: (lambda x: a_ - 1e-6 <= x[1] <= b_ + 1e-6))(ya, yb)
    zone_nodes = {z: [g for g in area if fn(pos[g])] for z, fn in zones.items()}
    # pad bottom -> nearest skin node (for slip)
    skin_nodes = sorted(set(n for fc, th, y in S["skin"] for n in fc))
    sk = X0[skin_nodes]
    pb_nodes = sorted(set(n for fc in pad_faces for n in fc))
    near = {}
    for n in pb_nodes:
        d = ((sk - X0[n]) ** 2).sum(1)
        near[n] = skin_nodes[int(np.argmin(d))]
    bl_faces = [EL[e][2] for e in S["bl_body"] + S["bl_cap"]]
    groups = {"bladder": S["bl_body"] + S["bl_cap"], "cover": S["cov_body"] + S["cov_cap"], "cover_flange": S["cov_flange"],
              "hooks": [e for h in S["hooks"].values() for e in h["e"]], "rings": [e for r in S["rings"].values() for e in r["e"]],
              "tabs": S["tab_e"] + S["flap_e"]}
    rows = []
    ring_rows = []
    pmaps, dmaps = {}, {}
    for k in range(1, nsub + 1):
        s_ = steps[k - 1]
        row = dict(subcase=k, name=s_["name"], kind=s_["kind"], frame=s_["frame"], ms=s_["ms"], theta=s_["theta"], p_kPa=s_["p"],
                   converged=k in res, increments=sum(1 for q in seen if q[0] == k), iterations=lg["iters"].get(k, 0),
                   bisections=lg["bis"].get(k, 0))
        if k not in res:
            rows.append(row)
            continue
        r = res[k]
        U = np.zeros_like(X0)
        for g, v in r["disp"].items():
            U[g - 1] = v[:3]
        Xd = X0 + U
        # knee moment from the shank bore reactions
        Ms, Fs, Mt, Ft = 0.0, np.zeros(3), 0.0, np.zeros(3)
        th = math.radians(s_["theta"])
        c, s = math.cos(th), math.sin(th)
        for n in S["bore_shank"]:
            F = r["spcf"].get(gid(n))
            if F is None:
                continue
            x = X0[n] - H
            xr = np.array([c * x[0] - s * x[1], s * x[0] + c * x[1], x[2]])
            Ms += np.cross(xr, F[:3])[2]
            Fs += F[:3]
        for n in S["bore_thigh"]:
            F = r["spcf"].get(gid(n))
            if F is None:
                continue
            Mt += np.cross(X0[n] - H, F[:3])[2]
            Ft += F[:3]
        row.update(M_knee_ext_Nm=Ms / 1000.0, M_thigh_Nm=Mt / 1000.0, Fshank_x_N=-Fs[0], Fshank_y_N=-Fs[1], Fshank_z_N=-Fs[2],
                   Fthigh_x_N=-Ft[0], Fthigh_y_N=-Ft[1])
        # rings
        for nm, rg in S["rings"].items():
            cols = {}
            for (e, cidx, wdt, tm, onskin, clo) in rg["info"]:
                fv = r["qforce"].get(e + 1)
                if fv is None:
                    continue
                cols.setdefault(cidx, [0.0, tm, onskin])
                cols[cidx][0] += fv[0] * wdt
            if cols:
                T = np.array([v[0] for v in cols.values()])
                Tf = np.array([v[0] for v in cols.values() if v[2]])
                row["T_%s_mean_N" % nm] = T.mean()
                row["T_%s_front_N" % nm] = Tf.mean() if len(Tf) else float("nan")
                Tb = np.array([v[0] for v in cols.values() if not v[2]])
                row["T_%s_backmedian_N" % nm] = float(np.median(Tb)) if len(Tb) else float("nan")
                row["T_%s_min_N" % nm] = T.min()
                row["T_%s_max_N" % nm] = T.max()
                for cidx, (t_, tm, onskin) in sorted(cols.items()):
                    ring_rows.append(dict(subcase=k, ring=nm, column=cidx, theta_deg=math.degrees(tm) % 360, on_skin=onskin, T_N=t_))
        # stresses
        for g, els in groups.items():
            vm = [max(r["qstress"].get(e + 1, [0.0]) + r["tstress"].get(e + 1, [0.0])) for e in els]
            row["vm_max_%s_MPa" % g] = max(vm) if vm else float("nan")
        # skin contact pressure
        Fn = {}
        for cid in skin_pairs:
            for g, (nf, sf) in r["cgrid"].get(cid, {}).items():
                if g in area:
                    Fn[g] = Fn.get(g, 0.0) + abs(nf or 0.0)
        for z, nodes in zone_nodes.items():
            A = sum(area[g] for g in nodes)
            F = sum(Fn.get(g, 0.0) for g in nodes)
            pk = max([Fn.get(g, 0.0) / area[g] for g in nodes] or [0.0])
            row["p_%s_mean_kPa" % z] = 1000.0 * F / A if A else float("nan")
            row["p_%s_peak_kPa" % z] = 1000.0 * pk
            row["F_%s_N" % z] = F
        row["skin_contact_force_total_N"] = sum(Fn.values())
        pmaps[k] = {g: 1000.0 * Fn.get(g, 0.0) / area[g] for g in area}
        dmaps[k] = Xd
        # cavity, slip
        row["V_bladder_mid_cm3"] = closed_volume(Xd, bl_faces) / 1000.0
        if pb_nodes:
            sl = np.array([U[n, 1] - U[near[n], 1] for n in pb_nodes])
            row["slip_y_mean_mm"] = float(sl.mean())
            row["slip_y_maxabs_mm"] = float(abs(sl).max())
            row["u_device_y_mean_mm"] = float(U[pb_nodes, 1].mean())
            # contact penetration of the pad bottom into the skin (penalty contact), radial, nearest skin grid
            pen = np.array([math.hypot(Xd[near[n], 0], Xd[near[n], 2]) - math.hypot(Xd[n, 0], Xd[n, 2]) for n in pb_nodes])
            row["pen_pad_median_mm"] = float(np.median(pen))
            row["pen_pad_p95_mm"] = float(np.percentile(pen, 95))
        row["ESE_total_mJ"] = r["ese"].get("total", float("nan"))
        rows.append(row)
    # device (inflation) moment = total knee moment at the frame minus the vented reference at the same angle (VREF)
    for i, rw in enumerate(rows):
        if rw["kind"] == "VREF" and rw.get("converged") and i > 0 and rows[i - 1].get("converged"):
            prev = rows[i - 1]
            prev["M_device_vs_VREF_Nm"] = prev["M_knee_ext_Nm"] - rw["M_knee_ext_Nm"]
            prev["dV_vs_VREF_cm3"] = prev["V_bladder_mid_cm3"] - rw["V_bladder_mid_cm3"]
    outdir = os.path.dirname(out_path)
    name = os.path.basename(base)
    keys = []
    for rw in rows:
        for kk in rw:
            if kk not in keys:
                keys.append(kk)
    with open(os.path.join(outdir, name + "_results.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        for rw in rows:
            wr.writerow({kk: (round(v, 6) if isinstance(v, float) else v) for kk, v in rw.items()})
    if ring_rows:
        with open(os.path.join(outdir, name + "_ring_tension.csv"), "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(ring_rows[0].keys()))
            wr.writeheader()
            for rw in ring_rows:
                wr.writerow(rw)
    conv = [dict(subcase=k, levels=" ".join("%.1f" % v for v in lg["levels"].get(k, [])), iterations=lg["iters"].get(k, 0),
                 bisections=lg["bis"].get(k, 0)) for k in range(1, nsub + 1)]
    with open(os.path.join(outdir, name + "_convergence.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(conv[0].keys()))
        wr.writeheader()
        for rw in conv:
            wr.writerow(rw)
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "per_subcase"
        ws.append(keys)
        for rw in rows:
            ws.append([rw.get(kk) for kk in keys])
        ws2 = wb.create_sheet("convergence")
        ws2.append(list(conv[0].keys()))
        for rw in conv:
            ws2.append(list(rw.values()))
        ws3 = wb.create_sheet("run_info")
        for kk in ("run", "opt", "plim", "tissue", "padE", "seq", "alpha", "mu"):
            ws3.append([kk, str(info.get(kk))])
        for nm, v in info["dT"].items():
            ws3.append(["dT_" + nm, v])
        ws3.append(["fatal", "; ".join(lg["fatal"]) or "none"])
        ws3.append(["warnings", "; ".join("%s x%d" % kv for kv in lg["warn"].items())])
        wb.save(os.path.join(outdir, name + "_results.xlsx"))
    except Exception as ex:                       # noqa: BLE001
        print("xlsx not written:", ex)
    if not quick:
        plots(rows, outdir, name)
        maps(rows, pmaps, dmaps, pos, S, EL, outdir, name)
    device_moment(outdir, name)
    done = [rw for rw in rows if rw.get("converged")]
    print("%s: %d/%d subcases converged" % (name, len(done), nsub))
    for rw in done:
        print("  %2d %-24s th %6.2f p %5.1f  M %7.3f N.m  T tn %6.2f sn %6.2f tf %6.2f sf %6.2f N  p_bl %6.2f/%6.2f kPa  V %6.1f  it %d bis %d" % (
            rw["subcase"], rw["name"][:24], rw["theta"], rw["p_kPa"], rw.get("M_knee_ext_Nm", float("nan")),
            rw.get("T_thigh_near_front_N", float("nan")), rw.get("T_shank_near_front_N", float("nan")),
            rw.get("T_thigh_far_front_N", float("nan")), rw.get("T_shank_far_front_N", float("nan")),
            rw.get("p_under_bladder_mean_kPa", float("nan")), rw.get("p_under_bladder_peak_kPa", float("nan")),
            rw.get("V_bladder_mid_cm3", float("nan")), rw["iterations"], rw["bisections"]))
    if lg["fatal"]:
        print("FATAL:", lg["fatal"][:3])


def device_moment(outdir, name):
    """pressurised run X and its vented baseline XV (same kinematics, p = 0): device (inflation) knee moment per subcase
    = M_ext(X) - M_ext(XV); written to a CSV next to the pressurised run"""
    base = name[:-1] if name.endswith("V") else name
    runs = os.path.dirname(outdir)
    fp = os.path.join(runs, base, base + "_results.csv")
    fv = os.path.join(runs, base + "V", base + "V_results.csv")
    if not (os.path.exists(fp) and os.path.exists(fv)):
        return
    P = {int(r["subcase"]): r for r in csv.DictReader(open(fp))}
    V = {int(r["subcase"]): r for r in csv.DictReader(open(fv))}
    out = os.path.join(runs, base, base + "_device_moment.csv")
    with open(out, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["subcase", "name", "theta_deg", "p_kPa", "M_total_Nm", "M_vented_Nm", "M_device_Nm"])
        for k in sorted(P):
            a, v = P[k], V.get(k)
            if v is None or not a.get("M_knee_ext_Nm") or not v.get("M_knee_ext_Nm"):
                continue
            mt, mv = float(a["M_knee_ext_Nm"]), float(v["M_knee_ext_Nm"])
            wr.writerow([k, a["name"], a["theta"], a["p_kPa"], round(mt, 5), round(mv, 5), round(mt - mv, 5)])
    print("device moment table:", out)


def plots(rows, outdir, name):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = [r for r in rows if r.get("converged")]
    if not d:
        return
    x = np.arange(1, len(d) + 1)
    lab = [r["name"].split(" sub")[0] for r in d]
    fig, ax = plt.subplots(4, 1, figsize=(12, 12), sharex=True)
    ax[0].plot(x, [r["theta"] for r in d], "o-", label="knee flexion (deg)")
    ax[0].plot(x, [r["p_kPa"] for r in d], "s-", label="bladder pressure (kPa)")
    ax[0].legend()
    ax[1].plot(x, [r.get("M_knee_ext_Nm") for r in d], "o-", color="C3")
    ax[1].set_ylabel("knee moment, + extension (N m)")
    for nm in ("thigh_far", "thigh_near", "shank_near", "shank_far"):
        ax[2].plot(x, [r.get("T_%s_front_N" % nm) for r in d], "o-", label=nm)
    ax[2].set_ylabel("ring tension, strap on skin (N)")
    ax[2].legend(fontsize=8)
    ax[3].plot(x, [r.get("p_under_bladder_mean_kPa") for r in d], "o-", label="under bladder mean")
    ax[3].plot(x, [r.get("p_under_bladder_peak_kPa") for r in d], "--", label="under bladder peak")
    ax[3].plot(x, [r.get("p_posterior_knee_peak_kPa") for r in d], ":", label="posterior knee peak")
    ax[3].set_ylabel("skin pressure (kPa)")
    ax[3].legend(fontsize=8)
    ax[3].set_xticks(x)
    ax[3].set_xticklabels(lab, rotation=90, fontsize=7)
    for a in ax:
        a.grid(alpha=0.3)
    fig.suptitle(name)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, name + "_history.png"), dpi=100)
    plt.close(fig)


def maps(rows, pmaps, dmaps, pos, S, EL, outdir, name):
    """unrolled skin-pressure maps (theta x y, device-side contact grids) and deformed device side views for D2, the
    peak-pressure subcase and the last converged subcase"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = [r for r in rows if r.get("converged")]
    if not d:
        return
    pick = []
    for r in d:
        if r["name"].startswith("D2"):
            pick.append(r["subcase"])
    pk = max(d, key=lambda r: r["p_kPa"])
    if pk["p_kPa"] > 0:
        pick.append(pk["subcase"])
    pick.append(d[-1]["subcase"])
    pick = sorted(set(pick))
    if not pos:                # core model (no pad / skin contact): no skin-pressure maps
        return
    g = sorted(pos)
    th = np.array([math.degrees(math.atan2(pos[n][2], pos[n][0])) for n in g])
    yy = np.array([pos[n][1] for n in g])
    for k in pick:
        lab = [r for r in d if r["subcase"] == k][0]
        pv = np.array([pmaps[k].get(n, 0.0) for n in g])
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        sc = ax[0].scatter(th, yy, c=np.clip(pv, 0, np.percentile(pv, 99.5) if pv.max() > 0 else 1), s=6, cmap="viridis")
        fig.colorbar(sc, ax=ax[0], label="skin contact pressure (kPa), clipped at the 99.5th percentile")
        ax[0].set_xlabel("theta (deg), 0 = back of the leg")
        ax[0].set_ylabel("y (mm), knee line 0")
        ax[0].set_title("%s  sub %d %s  max %.1f kPa" % (name, k, lab["name"], pv.max()))
        Xd = dmaps[k]
        for grp, col in (("bl_body", "C3"), ("cov_body", "C2")):
            for e in S[grp][::3]:
                q = Xd[EL[e][2]]
                ax[1].plot(np.append(q[:, 1], q[0, 1]), np.append(q[:, 0], q[0, 0]), color=col, lw=0.3)
        sk = [fc for fc, t_, y_ in S["skin"] if abs(t_) < 0.05]
        for fc in sk:
            q = Xd[fc]
            ax[1].plot(q[:, 1], q[:, 0], color="k", lw=0.5)
        ax[1].set_xlabel("y (mm)")
        ax[1].set_ylabel("x (mm, posterior)")
        ax[1].set_aspect("equal")
        ax[1].set_title("deformed side view at theta 0: bladder (red), cover (green), skin (black)")
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, "%s_map_sub%02d.png" % (name, k)), dpi=95)
        plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1], quick="--quick" in sys.argv)
