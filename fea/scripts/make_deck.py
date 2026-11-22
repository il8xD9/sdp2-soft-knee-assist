# -*- coding: utf-8 -*-
"""Inventor Nastran SOL 106 (nonlinear static, large displacement) input deck for the knee-assist bladder.

Idealised reference set-up (options used in build_decks.sh):
  --rigid_leg     leg = two rigid halves split at the knee line y = 0, hinged on the knee axis; the shank half is turned
                  by prescribed displacements (exact rigid rotation).
  --core 25       core model: bladder + cover only, bonded to the halves outside a 50 mm fold band (|y| < 25 mm); in the
                  band the bladder wall has 1 % of its modulus along the leg, so it folds like the mitre of the hand
                  calculation.
  --floor_bond    band floor bonded to a smoothly bent copy of the leg surface.
  --cov_endiso    end-facing cover elements use the isotropic end-cap property.
  --slstab 1e-4   slide-line contact stabilisation (PARAM SLINESTABKSFACT).
  --seq MULTI     fixed-angle case: bend vented to --theta, then pressurise to each value of --plist (kPa).
  --seq CYCLE     gait cycle: knee angle per stance frame from inputs/patient_waveform_option2.csv, fill at 13 %,
                  window 13-36 % at --cyc_p (kPa, or PROJ = project pressure profile); --cyc_end, --cyc_step.
Knee moment = sum over the shank-half reactions of (x - H) x F about the knee centre H (post_process.py).
Usage: python -P make_deck.py --mesh <mesh.pkl> --out <deck.nas> --run <name> [options]"""
import argparse
import csv
import json
import math
import os
import pickle

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TISSUE = {"relaxed": (0.00275, 0.0275), "contracted": (0.2, 2.0)}
ALPHA_RING = 1.0e-3
TREF = 20.0
MU_SKIN = 0.37
SFAC_SKIN = None        # None = by tissue state
SFAC_BY_TISSUE = {"contracted": 0.01, "relaxed": 0.01}   # SFAC 1 diverged for the contracted tissue too
SFAC_DEV = 1.0          # bladder-cover / bladder-base (solver default penalty)
# option 2 window: frame, ms, theta, p20, p27 (biomechanics Option-2 waveform + hand calculation)
W2 = [(13, 92, 3.28, 6.9, 6.9), (14, 99, 3.93, 13.0, 13.0), (15, 106, 4.50, 15.2, 18.6), (16, 113, 4.95, 16.7, 22.5),
      (17, 120, 5.29, 17.8, 24.1), (18, 127, 5.53, 18.8, 25.4), (19, 134, 5.68, 19.4, 26.2), (20, 141, 5.76, 19.8, 26.8),
      (21, 148, 5.78, 20.0, 27.0), (22, 155, 5.75, 19.9, 26.9), (23, 162, 5.68, 19.6, 26.5), (24, 169, 5.59, 19.2, 25.9),
      (25, 176, 5.48, 18.6, 25.1), (26, 183, 5.37, 17.9, 24.1), (27, 190, 5.25, 17.1, 23.0), (28, 197, 5.15, 16.2, 21.9),
      (29, 204, 5.05, 15.3, 20.7), (30, 212, 4.98, 14.4, 19.5), (31, 219, 4.91, 13.5, 18.3), (32, 226, 4.84, 12.6, 17.1),
      (33, 233, 4.79, 11.8, 15.2), (34, 240, 4.73, 10.9, 11.2), (35, 247, 4.68, 7.0, 7.0), (36, 254, 4.63, 2.8, 2.8)]
S1 = [(1, 7, -1.92), (3, 21, -0.76), (6, 42, 0.01), (9, 63, 0.88), (12, 85, 2.59)]
REL = [(37, 4.57), (40, 4.36), (45, 3.99), (50, 3.74), (55, 3.68), (60, 3.78), (65, 4.06), (70, 4.65), (75, 5.63), (80, 7.10),
       (85, 9.25), (87, 10.43)]
TOFF = [(90, 12.83), (95, 19.13), (100, 27.81)]
P_RES = 2.4
DTH_MAX = 2.5
NINC_D = 10
SKIP = []
VENT = False
MU_RING = None          # None = MU_SKIN; relaxed runs: 0.0
COVER_BEND = 1.0        # PSHELL 12I/t^3 of the cover; fabric value set by the options; a plate-stiff cover keeps the
                        # whole device straight (no squeeze, no torque)
FLANGE_BEND = None      # PSHELL 10 (sewing flange, every node shared with pad CHEXA) 12I/t^3; None = COVER_BEND.
                        # at 0.003 the flange rotations at the pad nodes are near-singular (E5080 -> E5076 in D2)
COVER_ORTHO = 0.01      # default; --cover_ortho 0 = isotropic cover. E_leg / E_hoop of the cover membrane (MID1 = MAT8 11, material 1 = leg axis via CORD2R 91 = MCID);
                        # None = isotropic MAT1 9; 0.01 -> E_leg = G12 = 4.98 MPa,
                        # E_hoop 498 MPa; bending (MID2) stays MAT1 9 with COVER_BEND; end caps (normal = leg axis) PSHELL 11 isotropic
FLANGE_ISO = True       # default; --flange_ortho = orthotropic flange. With COVER_ORTHO: sewing flange (PSHELL 10) keeps the isotropic MAT1 9 membrane
BOND_SKIN = False       # diagnostic only: pad/ring-skin contacts bonded (BSCONP TYPE 3) = perfect anchorage upper bound
# --- idealised reference options
RIGID_LEG = False       # hand-calculation (Model B) reference: leg = two rigid halves split at the plane y = 0, hinge = knee axis.
                        # Tissue CHEXA dropped; every skin grid SPC 123: y >= 0 fixed (thigh), y < 0 exact rigid rotation by SPCD
                        # (shank). Exact SPCD instead of RBE2 because RBE2 is linear in this solver.
RIGID_COVER_YMIN = None  # with RIGID_LEG: cover body / cap grids with |y| >= YMIN turn rigidly with their half
THETA_T = None          # seq MULTI: knee angle of the case (deg)
PLIST = None            # seq MULTI: pressure levels (kPa), applied one after the other at THETA_T
# --- gait cycle: seq CYCLE = stance 1 -> 50 % with the knee
# on the knee angle of the biomechanics Option-2 waveform; supply from heel strike (linear fill to the window-onset pressure at 13 %), window 13-36 % at
# the test pressure (vents closed), vent 36 -> 50 % (exponential to the 2.4 kPa residual).
CYC_P = None            # constant test pressure (kPa) in the window, or "PROJ" = project profile W2 p20 (6.9 -> 20 -> 2.8 kPa)
CYC_END = 50            # last stance frame (%)
CYC_STEP = 1            # stance frame stride (%); > 1: frames k*step < 13, then 13, the peak 21 +- k*step, and CYC_END
FLOOR_BOND = False      # core model, band floor bonded to the smoothly bent leg surface (no floor contact)
FLOOR_BED = None        # core model, rigid bed copied from the band floor faces, offset mm towards the leg
COV_ENDISO = None       # cover body elements with |n. Y| > T (end-facing) take the isotropic end-cap property 11
SUP_BLEND = False       # core model, rigid support continuous across the knee line, band grids turn by theta*s(y)
SLSTAB = None           # PARAM SLINESTABKSFACT = slide-line contact stabilisation (default: solver 0.0)
CORE_SLEEVE = False     # with CORE_BAND: cover in the band = rigid sleeve turning by theta/2
CORE_BAND = None        # with RIGID_LEG: hand-calc core model (bladder + cover on rigid halves), crease band half-width mm
CREASE_GAP = None       # with RIGID_LEG: cut pad + cover flange elements with |y centroid| < G mm; None = off


def f(v):
    s = "%.7g" % float(v)
    if "." not in s:
        s = s.replace("e", ".e") if "e" in s else s + "."
    return s


def opt1_frames(plim):
    rows = []
    with open(os.path.join(ROOT, "inputs", "patient_waveform_option2.csv")) as fh:
        for line in fh:
            if line.startswith("#") or line.startswith("stance"):
                continue
            a = line.strip().split(",")
            rows.append((int(a[0]), float(a[1]), float(a[2]), float(a[4])))
    d21 = [r[2] for r in rows if r[0] == 21][0]
    return [(r[0], r[1], r[3], plim * r[2] / d21) for r in rows if 9 <= r[0] <= 44]


def sequence(opt, plim, seq, vref=False):
    """list of steps: dict(name, kind, frame, ms, theta, p, ninc, therm)"""
    st = [dict(name="D1 donning (25 % tightening)", kind="D", frame=0, ms=0.0, theta=0.0, p=0.0, ninc=NINC_D, therm=0.25),
          dict(name="D2 pre-tension", kind="D", frame=0, ms=0.0, theta=0.0, p=0.0, ninc=2 * NINC_D, therm=True)]
    if seq == "D":
        return st
    if seq == "MULTI":         # matrix / sweep deck: flex vented to THETA_T (= vented reference before), the pressure
        th = float(THETA_T)    # levels PLIST one after the other at that angle, then vent again (VREF)
        st.append(dict(name="flex vented to %.2f deg" % th, kind="S", frame=0, ms=0.0, theta=th, p=0.0, ninc=3, therm=True))
        pp = 0.0
        for p in PLIST:
            st.append(dict(name="P %g kPa at %.2f deg" % (p, th), kind="W", frame=0, ms=0.0, theta=th, p=float(p),
                           ninc=max(4, int(math.ceil(abs(p - pp) / 5.0))), therm=True))
            pp = float(p)
        st.append(dict(name="VREF vented at %.2f deg" % th, kind="VREF", frame=0, ms=0.0, theta=th, p=0.0,
                       ninc=max(4, int(math.ceil(pp / 10.0))), therm=True))
        seq = "MULTI_DONE"
        vref = False
    if seq == "CYCLE":
        wf = {}
        with open(os.path.join(ROOT, "inputs", "patient_waveform_option2.csv")) as fh:
            for line in fh:
                if line.startswith("#") or line.startswith("stance"):
                    continue
                a_ = line.strip().split(",")
                wf[int(a_[0])] = (float(a_[1]), float(a_[4]))
        pw = {fr: (p20 if CYC_P == "PROJ" else float(CYC_P)) for fr, ms_, th_, p20, p27 in W2}
        p13, p36 = pw[13], pw[36]
        pp = 0.0
        if CYC_STEP <= 1:
            frames = list(range(1, CYC_END + 1))
        else:
            frames = sorted(set([f for f in range(CYC_STEP, 13, CYC_STEP)] + [12, 13]
                                + [f for f in range(21, 12, -CYC_STEP) if f > 13] + list(range(21, CYC_END + 1, CYC_STEP)) + [CYC_END]))
        for fr in frames:
            ms_, th_ = wf[fr]
            if CORE_BAND is not None and fr < 13:      # core reference: vented flexion to the onset, fill at 13 % (5 steps)
                p, kd, nm = 0.0, "S", "S %d%% vented" % fr
            elif CORE_BAND is not None and fr == 13 and p13 > 0:
                for k_ in range(1, 6):
                    st.append(dict(name="F13 fill %d/5" % k_, kind="F", frame=13, ms=float(ms_), theta=th_, p=p13 * k_ / 5.0,
                                   ninc=max(2, int(math.ceil(p13 / 5.0 / 5.0))), therm=True))
                pp = p13
                p, kd, nm = pw[fr], "W", "W %d%%" % fr
            elif fr < 13:
                p, kd, nm = p13 * fr / 13.0, "F", "F %d%% fill" % fr
            elif fr <= 36:
                p, kd, nm = pw[fr], "W", "W %d%%" % fr
            else:
                x_ = (fr - 36) / float(CYC_END - 36)
                p = p36 * (P_RES / p36) ** x_ if p36 > P_RES else p36 + (min(p36, P_RES) - p36) * x_
                kd, nm = "V", "V %d%% vent" % fr
            st.append(dict(name=nm, kind=kd, frame=fr, ms=float(ms_), theta=th_, p=p,
                           ninc=max(2, int(math.ceil(abs(p - pp) / 5.0))), therm=True))
            pp = p
        seq = "MULTI_DONE"
        vref = False
    if seq == "MINI":          # check deck: flex vented to the 21 % angle, inflate to the peak there, vent again (VREF)
        th21 = [w for w in W2 if w[0] == 21][0][2]
        st.append(dict(name="flex vented to %.2f deg" % th21, kind="S", frame=21, ms=148.0, theta=th21, p=0.0, ninc=3, therm=True))
        st.append(dict(name="W 21%% inflate %d kPa" % plim, kind="W", frame=21, ms=148.0, theta=th21, p=float(plim), ninc=8, therm=True))
        vref = True
        seq = "MINI_DONE"
    if seq in ("MINI_DONE", "MULTI_DONE"):
        win = []
    elif opt == 2:
        for fr, ms, th in S1:
            st.append(dict(name="S1 %d%%" % fr, kind="S", frame=fr, ms=float(ms), theta=th, p=0.0, ninc=2, therm=True))
        win = [(fr, ms, th, (p20 if plim == 20 else p27)) for fr, ms, th, p20, p27 in W2]
    else:
        for fr, ms, th in S1[:3]:
            st.append(dict(name="S1 %d%%" % fr, kind="S", frame=fr, ms=float(ms), theta=th, p=0.0, ninc=2, therm=True))
        win = opt1_frames(plim)
    for fr, ms, th, p in win:
        rising = p >= st[-1]["p"] - 1e-9
        st.append(dict(name="W %d%%" % fr, kind="W", frame=fr, ms=float(ms), theta=th, p=p, ninc=4 if rising else 2, therm=True))
        if seq == "D-21" and fr == 21:
            break
    if seq not in ("D-21", "MINI_DONE", "MULTI_DONE"):
        lastw = st[-1]["frame"]
        for fr, th in REL:
            if fr <= lastw:
                continue
            st.append(dict(name="R %d%%" % fr, kind="R", frame=fr, ms=fr * 7.05, theta=th, p=P_RES, ninc=3, therm=True))
        if seq in ("FULL", "D-SW"):
            for fr, th in TOFF:
                st.append(dict(name="TO %d%%" % fr, kind="TO", frame=fr, ms=fr * 7.05, theta=th, p=P_RES, ninc=4, therm=True))
            a0 = TOFF[-1][1]
            for a, b in ((a0, 65.0), (65.0, 78.0)):
                n = int(math.ceil((b - a) / DTH_MAX))
                for k in range(1, n + 1):
                    th = a + (b - a) * k / n
                    st.append(dict(name="SW %.1f deg" % th, kind="SW", frame=100, ms=0.0, theta=th, p=P_RES, ninc=4, therm=True))
    if vref:
        last = st[-1]
        st.append(dict(name="VREF vented at %.2f deg" % last["theta"], kind="VREF", frame=last["frame"], ms=last["ms"],
                       theta=last["theta"], p=0.0, ninc=4, therm=True))
    # split angle jumps > DTH_MAX into sub-steps (SPCD is linear inside a subcase)
    out = []
    for s_ in st:
        if out:
            d = s_["theta"] - out[-1]["theta"]
            n = int(math.ceil(abs(d) / DTH_MAX - 1e-9))
            for k in range(1, n):
                t = out[-1]["theta"]
                q = dict(s_)
                q["name"] = s_["name"] + " sub %d/%d" % (k, n)
                q["theta"] = out[-1]["theta"] + (s_["theta"] - out[-1]["theta"]) / (n - k + 1)
                q["p"] = out[-1]["p"] + (s_["p"] - out[-1]["p"]) / (n - k + 1)
                q["kind"] = s_["kind"] + "_sub"
                out.append(q)
        out.append(s_)
    return out


def ranges(ids):
    ids = sorted(set(int(i) for i in ids))
    out = []
    a = b = ids[0]
    for i in ids[1:]:
        if i == b + 1:
            b = i
        else:
            out.append((a, b))
            a = b = i
    out.append((a, b))
    return out


def set_card(sid, ids):
    parts = ["%d THRU %d" % (a, b) if b > a else "%d" % a for a, b in ranges(ids)]
    lines, cur = [], "SET %d = " % sid
    for k, p in enumerate(parts):
        add = p + ("," if k < len(parts) - 1 else "")
        if len(cur) + len(add) > 70:
            lines.append(cur)
            cur = "  "
        cur += add
    lines.append(cur)
    return lines


def write(mesh_pkl, out, run="R1", opt=2, plim=20, tissue="relaxed", padE=0.0965, seq="D-21", vref=False, calib=None,
          maxiter=25, nb_pad=6, title=None, extra_param=()):
    m = pickle.load(open(mesh_pkl, "rb"))
    X, EL, S, meta = m["X"], m["el"], m["S"], m["meta"]
    H = meta["H"]
    skip_grid, skip_el = set(), set()
    if RIGID_LEG:              # rigid leg halves (hand-calc Model B reference); the run's own mesh pkl keeps this S
        S = dict(S)
        meta = dict(meta)
        Xa = np.asarray(X)
        skin_all = sorted(set(n for fc, th_, y_ in S["skin"] for n in fc))
        th_n = [n for n in skin_all if Xa[n][1] >= 0.0]
        sh_n = [n for n in skin_all if Xa[n][1] < 0.0]
        if RIGID_COVER_YMIN is not None:
            cn = sorted(set(n for e in S["cov_body"] + S["cov_cap"] for n in EL[e][2]))
            th_n += [n for n in cn if Xa[n][1] >= RIGID_COVER_YMIN]
            sh_n += [n for n in cn if Xa[n][1] <= -RIGID_COVER_YMIN]
        tis_n = set(n for e in S["tissue_e"] for n in EL[e][2])
        skip_grid = tis_n - set(skin_all)
        skip_el = set(S["tissue_e"])
        S["bore_thigh"], S["bore_shank"] = th_n, sh_n
        S["tissue_e"] = []
        meta["rigid_leg"] = dict(split_y=0.0, n_thigh=len(th_n), n_shank=len(sh_n), cover_ymin=RIGID_COVER_YMIN)
        if CREASE_GAP:         # pad + cover sewing flange cut at the knee line, as the
            G_ = float(CREASE_GAP)  # pad of the knee-joint CAD and the hand calc (only the bladder + cover cross the crease)
            yc = lambda e: float(Xa[EL[e][2]][:, 1].mean())
            fy = lambda fc: float(Xa[list(fc)][:, 1].mean())
            cut = set(e for e in S["pad_e"] + S["cov_flange"] if abs(yc(e)) < G_)
            S["pad_e"] = [e for e in S["pad_e"] if e not in cut]
            S["cov_flange"] = [e for e in S["cov_flange"] if e not in cut]
            S["pad_bottom"] = [p for p in S["pad_bottom"] if abs(fy(p[0])) >= G_]
            S["base_master"] = [fc for fc in S["base_master"] if abs(fy(fc)) >= G_]
            skip_el |= cut
            used = set()
            for i_, e_ in enumerate(EL):
                if i_ not in skip_el:
                    used.update(e_[2])
            skip_grid |= set(n for e in cut for n in EL[e][2]) - used - set(skin_all)
            meta["rigid_leg"].update(crease_gap=G_, crease_cut_elements=len(cut))
        if CORE_BAND is not None:  # hand-calc core = rigid halves + bladder + cover only (Model B)
            B_ = float(CORE_BAND)
            S["cov_flange"] = [e for e in S["cov_flange"] if abs(float(Xa[EL[e][2]][:, 1].mean())) >= B_]   # flange cut in the band
            keep = set(S["bl_body"] + S["bl_cap"] + S["cov_body"] + S["cov_cap"] + S["cov_flange"])
            skip_el = set(range(len(EL))) - keep
            ub = lambda n: Xa[n][0] - (meta_r(Xa[n][1]) + 9.18)
            bl_n = sorted(set(n for e in S["bl_body"] + S["bl_cap"] for n in EL[e][2]))
            fl_n = sorted(set(n for e in S["cov_flange"] for n in EL[e][2]))
            base_n = [n for n in bl_n if ub(n) < 1.5 and abs(Xa[n][1]) >= B_]          # bladder floor, bonded to the halves
            flb_n = [n for n in fl_n if abs(Xa[n][1]) >= B_]                            # cover sewing flange, bonded
            cvb_n = set(n for e in S["cov_body"] for n in EL[e][2] if abs(Xa[n][1]) < B_)   # cover wall nodes in the band stay free
            S["base_master"] = [fc for fc in S["base_master"] if (SUP_BLEND or abs(float(Xa[list(fc)][:, 1].mean())) >= 2.5)
                                and not any(n in cvb_n for n in fc)]     # --sup_blend keeps the knee-line faces (no slot)
            if FLOOR_BED is not None:  # rigid bed = the band floor faces copied FLOOR_BED mm towards the leg (new grids);
                # replaces the pad-top support, which lies 4.2 mm below the floor (the floor outside the band is bonded at its
                # mesh position, so the free band floor was pulled 4.2 mm down onto it and ridged)
                fset = set(n for n in bl_n if ub(n) < 1.5)
                bed_f = [list(EL[e][2]) for e in S["bl_body"] if all(n in fset for n in EL[e][2])
                         and abs(float(Xa[EL[e][2]][:, 1].mean())) < B_ + 6.0]
                nsum = {}
                for fc in bed_f:
                    p_ = Xa[list(fc)]
                    nv = np.cross(p_[1] - p_[0], p_[2] - p_[0])
                    nv = nv / np.linalg.norm(nv)
                    if nv[0] > 0:
                        nv = -nv                    # towards the leg
                    for n in fc:
                        nsum[n] = nsum.get(n, 0.0) + nv
                bn = sorted(nsum)
                new_id = {n: len(Xa) + k for k, n in enumerate(bn)}
                newp = np.array([Xa[n] + float(FLOOR_BED) * nsum[n] / np.linalg.norm(nsum[n]) for n in bn])
                Xa = np.vstack([Xa, newp])
                X = Xa
                S["base_master"] = [[new_id[n] for n in fc] for fc in bed_f]   # raw normal -x as the old support faces
                meta["rigid_leg"].update(floor_bed=float(FLOOR_BED), n_bed_faces=len(bed_f), n_bed_grids=len(bn))
            bfl_n = []
            if FLOOR_BOND:             # "bladder bonded": the band floor is bonded to the leg surface, which bends
                bfl_n = [n for n in bl_n if ub(n) < 1.5 and abs(Xa[n][1]) < B_]   # smoothly through the band (theta * s(y));
                S["base_master"] = []  # no floor contact at all (removes the slot, the 4.2 mm drop and the floor chatter)
            sup_n = sorted(set(n for fc in S["base_master"] for n in fc))                # rigid support surface under the floor
            fixed = sorted(set(base_n) | set(flb_n) | set(sup_n) | set(bfl_n))
            sleeve = sorted(set(n for e in S["cov_body"] + S["cov_cap"] for n in EL[e][2] if abs(Xa[n][1]) < B_) - set(fixed)) if CORE_SLEEVE else []
            S["bore_mid"] = sleeve       # rigid sleeve in the band, turns by theta/2 (not part of the knee moment)
            S["bore_thigh"] = [n for n in fixed if Xa[n][1] >= 0.0]
            S["bore_shank"] = [n for n in fixed if Xa[n][1] < 0.0]
            used = set(n for e in keep for n in EL[e][2]) | set(sup_n)
            skip_grid = set(range(len(Xa))) - used
            for k_ in ("pad_e", "seat_e", "stack_e", "tab_e", "flap_e", "tissue_e"):
                S[k_] = []
            S["pad_bottom"] = []
            S["skin"] = [sk for sk in S["skin"] if all(n in used for n in sk[0])]
            S["rings"] = {}
            S["hooks"] = {}
            if SUP_BLEND:      # support grids in the band turn by theta * s, s = 0 at y = +B (thigh) .. 1 at y = -B (shank)
                S["sup_blend"] = {n: min(1.0, max(0.0, (B_ - Xa[n][1]) / (2.0 * B_))) for n in sup_n if abs(Xa[n][1]) < B_ and n not in set(base_n) | set(flb_n)}
            if FLOOR_BOND:             # bonded band floor follows the same smooth bend
                S.setdefault("sup_blend", {}).update({n: min(1.0, max(0.0, (B_ - Xa[n][1]) / (2.0 * B_))) for n in bfl_n})
                meta["rigid_leg"].update(floor_bond=True, n_floor_bonded_band=len(bfl_n))
            meta["rigid_leg"]["bl_crease"] = [e for e in S["bl_body"] if abs(float(Xa[EL[e][2]][:, 1].mean())) < B_]
            meta["rigid_leg"].update(core_band=B_, n_sleeve=len(S.get("bore_mid", [])), n_bl_crease=len(meta["rigid_leg"]["bl_crease"]), n_floor_bonded=len(base_n), n_flange_bonded=len(flb_n), n_support=len(sup_n))
        m = dict(m, S=S, meta=meta)
        if FLOOR_BED is not None and CORE_BAND is not None:
            m["X"] = X                                          # the run's mesh carries the bed grids
    steps = sequence(opt, plim, seq, vref)
    if CORE_BAND is not None:                  # core model has no straps: no donning / pre-tension subcases
        steps = [s_ for s_ in steps if s_["kind"] != "D"]
    sfac_skin = SFAC_SKIN if SFAC_SKIN is not None else SFAC_BY_TISSUE[tissue]
    if VENT:                                   # vented baseline run: same kinematics, p = 0 (passive knee moment M0(theta))
        for s_ in steps:
            s_["p"] = 0.0
    dT = {"thigh_far": -30.0, "thigh_near": -30.0, "shank_near": -30.0, "shank_far": -30.0}
    if calib:
        c = json.load(open(calib))
        dT.update(c.get(tissue, c))
    L = []
    w = L.append
    nid = lambda i: int(i) + 1            # node index -> GRID id
    eid = lambda i: int(i) + 1            # element index -> EID
    # --------------------------------------------------------------- output sets
    ring_e = [e for r in S["rings"].values() for e in r["e"]]
    hook_e = [e for h in S["hooks"].values() for e in h["e"]]
    bl_e = S["bl_body"] + S["bl_cap"]
    cov_e = S["cov_body"] + S["cov_cap"] + S["cov_flange"]
    shells = ring_e + hook_e + bl_e + cov_e + S["tab_e"] + S["flap_e"]
    dev_nodes = set()
    for e in shells + S["pad_e"] + S["seat_e"] + S["stack_e"]:
        dev_nodes.update(EL[e][2])
    skin_nodes = set(n for fc, th, y in S["skin"] for n in fc)
    bore = S["bore_thigh"] + S["bore_shank"]
    w("SOL 106")
    w("CEND")
    if title is None and seq == "CYCLE":
        title = ("a10 %s %s cycle p%s padE%g mu%g%s" % (
            run, "RIGIDLEG-idealised" if RIGID_LEG else tissue, CYC_P, padE, MU_SKIN, " bond" if BOND_SKIN else "") + (" gap%g" % CREASE_GAP if CREASE_GAP else "") + (" core%g%s" % (CORE_BAND, "s" if CORE_SLEEVE else "") if CORE_BAND is not None else ""))[:64]
    if title is None and (RIGID_LEG or seq == "MULTI"):
        title = ("a10 %s %s th%g padE%g mu%g%s%s" % (
            run, "RIGIDLEG-idealised" if RIGID_LEG else tissue, THETA_T if THETA_T is not None else -1, padE, MU_SKIN,
            " bond" if BOND_SKIN else "", ((" rcov%g" % RIGID_COVER_YMIN) if RIGID_COVER_YMIN is not None else "") + (" gap%g" % CREASE_GAP if CREASE_GAP else "") + (" core%g%s" % (CORE_BAND, "s" if CORE_SLEEVE else "") if CORE_BAND is not None else "")))[:64]
    w("TITLE = %s" % (title or "full asseymbly 07 %s opt%d %dkPa %s padE %g seq %s" % (run, opt, plim, tissue, padE, seq)))
    w("ECHO = NONE")
    L += set_card(1, [nid(n) for n in dev_nodes | skin_nodes])
    L += set_card(2, [nid(n) for n in bore])
    L += set_card(3, [eid(e) for e in shells + S["stack_e"]])
    L += set_card(4, [eid(e) for e in bl_e + cov_e])
    L += set_card(5, [eid(e) for e in ring_e + hook_e + cov_e])
    L += set_card(6, [nid(n) for n in S["bl_nodes"]])
    w("DISPLACEMENT(PRINT) = 1")
    w("SPCFORCES(PRINT) = 2")
    w("STRESS(PRINT) = 3")
    w("STRAIN(PRINT) = 4")
    w("FORCE(PRINT) = 5")
    w("ESE(PRINT) = 3")
    w("OLOAD(PRINT) = 6")
    w("TEMPERATURE(INITIAL) = 1")
    for k, s_ in enumerate(steps, start=1):
        w("SUBCASE %d" % k)
        w("  LABEL = %s th=%.2f p=%.2fkPa" % (s_["name"], s_["theta"], s_["p"]))
        w("  SPC = 1")
        w("  LOAD = %d" % (1000 + k))
        w("  NLPARM = %d" % k)
        w("  TEMPERATURE(LOAD) = %d" % (1 if not s_["therm"] else (2 if s_["therm"] is True or s_["therm"] >= 1.0 else 3)))
    w("BEGIN BULK")
    w("PARAM,UNITS,MM")
    w("PARAM,LGDISP,1")
    w("PARAM,AUTOSPC,YES")
    if SLSTAB is not None:
        w("PARAM,SLINESTABKSFACT,%s" % f(SLSTAB))
    w("PARAM,GRDPNT,0")
    for kv in extra_param:
        w("PARAM,%s" % kv)
    for k, s_ in enumerate(steps, start=1):
        w("NLPARM,%d,%d,,ITER,1,%d,PW,NO\n,0.01,0.01,0.001\n,10" % (k, s_["ninc"], maxiter))
    # --------------------------------------------------------------- materials / properties
    A10, D1 = TISSUE[tissue]
    w("$ tissue neo-Hookean (MATHP MID A10 A01 D1 RHO), %s" % tissue)
    w("MATHP,1,%s,0.,%s,1.e-9" % (f(A10), f(D1)))
    w("PSOLID,1,1,0")
    w("MAT1,2,%s,,0.33,%s" % (f(padE), f(203.9e-12)))
    w("PSOLID,2,2,0")
    w("$ rings: MAT8 orthotropic shell, thermal expansion along the hoop (element x) only")
    w("MAT8,3,498.,498.,0.35,184.4,184.4,184.4,%s\n,%s,0.,%s" % (f(576e-12), f(ALPHA_RING), f(TREF)))
    w("PSHELL,3,3,3.18,3,,3")
    rho_clo = (576.0 * 3.18 * 2 + 109.0 * 1.5) / 7.86
    w("MAT8,4,498.,498.,0.35,184.4,184.4,184.4,%s\n,%s,0.,%s" % (f(rho_clo * 1e-12), f(ALPHA_RING), f(TREF)))
    w("PSHELL,4,4,7.86,4,0.139,4")          # closure = 3 separate layers: bending 12I/t^3 = (2 x 3.18^3 + 1.5^3) / 7.86^3
    w("MAT1,5,2760.,,0.37,%s" % f(1410e-12))
    w("PSHELL,5,5,4.,5,,5")
    w("MAT1,6,498.,,0.35,%s" % f((576.0 * 3.18 + 109.0 * 1.5) / 4.68 * 1e-12))
    w("PSOLID,6,6,0")
    w("MAT1,7,7.2,,0.49,%s" % f(1120e-12))
    w("PSHELL,7,7,2.,7,,7")
    w("PSHELL,8,7,2.,7,,7")
    w("MAT1,9,498.,,0.35,%s" % f(1105e-12))
    mid_cov = 9
    if COVER_ORTHO is not None:
        r_ = float(COVER_ORTHO)
        w("$ cover membrane: orthotropic fabric, material 1 = leg axis (global Y via CORD2R 91), material 2 = hoop")
        w("CORD2R,91,0,0.,0.,0.,1.,0.,0.\n,0.,1.,0.")
        w("MAT8,11,%s,498.,%s,%s,,,%s" % (f(498.0 * r_), f(0.35 * r_), f(498.0 * r_), f(1105e-12)))
        mid_cov = 11
    w("PSHELL,9,%d,0.43,9,%s,9" % (mid_cov, f(COVER_BEND)))
    w("PSHELL,10,%d,0.43,9,%s,9" % (9 if FLANGE_ISO else mid_cov, f(COVER_BEND if FLANGE_BEND is None else FLANGE_BEND)))
    cov_mcid, cov_cap = set(), set()
    bl_crease = set(meta.get("rigid_leg", {}).get("bl_crease", [])) if CORE_BAND is not None else set()
    if bl_crease:              # bladder wall in the crease band folds (hand-calc mitre): 1 % of E along the leg, full hoop
        if COVER_ORTHO is None:
            w("CORD2R,91,0,0.,0.,0.,1.,0.,0.\n,0.,1.,0.")
        w("MAT8,12,0.072,7.2,0.0049,0.02416,,,%s" % f(1120e-12))
        w("PSHELL,12,12,2.,7,,7")
    if COVER_ORTHO is not None:
        w("PSHELL,11,9,0.43,9,%s,9" % f(COVER_BEND))
        cov_mcid = set(S["cov_body"]) | (set() if FLANGE_ISO else set(S["cov_flange"]))
        cov_cap = set(S["cov_cap"])
        if COV_ENDISO is not None:     # the leg axis (MCID 91) is ill-defined on end-facing walls -> isotropic like the caps
            Xn = np.asarray(X)
            def _ny(e):
                p_ = Xn[list(EL[e][2])]
                n_ = np.cross(p_[1] - p_[0], p_[2] - p_[0])
                return abs(n_[1]) / np.linalg.norm(n_)
            endw = set(e for e in S["cov_body"] if _ny(e) > float(COV_ENDISO))
            cov_mcid -= endw
            cov_cap |= endw
            meta.setdefault("cover", {})["n_end_iso"] = len(endw)
    # --------------------------------------------------------------- grids / elements
    for i, x in enumerate(X):
        if i in skip_grid:
            continue
        w("GRID,%d,,%s,%s,%s" % (i + 1, f(x[0]), f(x[1]), f(x[2])))
    for i, (typ, pid, n, grp) in enumerate(EL):
        if i in skip_el:
            continue
        g = [str(nid(v)) for v in n]
        if typ == "CHEXA":
            w("CHEXA,%d,%d,%s\n,%s" % (i + 1, pid, ",".join(g[:6]), ",".join(g[6:])))
        elif i in bl_crease:
            w("%s,%d,12,%s,91" % (typ, i + 1, ",".join(g)))
        elif i in cov_cap:
            w("%s,%d,11,%s" % (typ, i + 1, ",".join(g)))
        elif i in cov_mcid:
            w("%s,%d,%d,%s,91" % (typ, i + 1, pid, ",".join(g)))
        else:
            w("%s,%d,%d,%s" % (typ, i + 1, pid, ",".join(g)))
    # --------------------------------------------------------------- constraints
    for grp in (S["bore_thigh"], S["bore_shank"], S.get("bore_mid", [])):
        ids = [nid(v) for v in grp]
        for c in range(0, len(ids), 6):
            w("SPC1,1,123,%s" % ",".join(map(str, ids[c:c + 6])))
    # --------------------------------------------------------------- temperatures
    w("TEMPD,1,%s" % f(TREF))
    w("TEMPD,2,%s" % f(TREF))
    tset = {}
    for nm, r in S["rings"].items():
        for n in r["nodes"]:
            tset[nid(n)] = TREF + dT[nm]
    items = sorted(tset.items())
    w("TEMPD,3,%s" % f(TREF))
    for c in range(0, len(items), 3):
        w("TEMP,2,%s" % ",".join("%d,%s" % (g, f(t)) for g, t in items[c:c + 3]))
        w("TEMP,3,%s" % ",".join("%d,%s" % (g, f(TREF + 0.25 * (t - TREF))) for g, t in items[c:c + 3]))
    # --------------------------------------------------------------- contacts
    def bsseg(sid, faces):
        g = [str(nid(n)) for fc in faces for n in (list(fc) + ([-1] if len(fc) == 3 else []))]
        g = ["0" if v == "0" else v for v in g]
        lines = ["BSSEG,%d,%s" % (sid, ",".join(g[:7]))]
        for c in range(7, len(g), 8):
            lines.append("," + ",".join(g[c:c + 8]))
        w("\n".join(lines))
    pairs = []
    skin = S["skin"]
    Xc = np.asarray(X)

    def cells(name, sl, ms, key, cy, cs, margin, mu, sfac):
        """split one contact into patches: slave faces binned on a (y, s) grid of cy x cs mm, master faces within the
        cell + margin.  The solver builds slave x master segment pairs per BSCONP, so patches keep the contact element
        count (and RAM) small; a slave face belongs to exactly one patch."""
        cy, cs = cy * CELL, cs * CELL
        sk = [key(Xc[fc].mean(0)) for fc in sl]
        mk = [key(Xc[fc].mean(0)) for fc in ms]
        bins = {}
        for fc, (y, s2) in zip(sl, sk):
            bins.setdefault((int(math.floor(y / cy)), int(math.floor(s2 / cs))), []).append(fc)
        for (iy, isx), faces in sorted(bins.items()):
            ya, yb, sa, sb = iy * cy - margin, (iy + 1) * cy + margin, isx * cs - margin, (isx + 1) * cs + margin
            mm = [fc for fc, (y, s2) in zip(ms, mk) if ya <= y <= yb and sa <= s2 <= sb]
            pairs.append(("%s_%d_%d" % (name, iy, isx), faces, mm, mu, sfac))

    CELL = max(0.6, min(1.0, meta["h"] / 5.0))       # patch size follows the device mesh size (contact elements ~ constant per patch)

    def skin_key(c):
        return (c[1], math.atan2(c[2], c[0]) * 75.0)
    skin_f = [fc for fc, th, y in skin]
    cells("pad_skin", [p[0] for p in S["pad_bottom"]], skin_f, skin_key, 25.0, 30.0, 8.0, MU_SKIN, sfac_skin)
    for nm, r in S["rings"].items():
        cells("ring_skin_" + nm, r["skin"], skin_f, skin_key, 30.0, 40.0, 8.0, MU_RING if MU_RING is not None else MU_SKIN, sfac_skin)
    YD = meta["YD"]

    def bl_key(c):
        u = c[0] - (meta_r(c[1]) + 9.18)
        return (c[1], math.atan2(c[2], u - 22.0) * 25.0)
    bl_f = [EL[e][2] for e in bl_e]
    cv_f = [EL[e][2] for e in S["cov_body"] + S["cov_cap"]]
    cv_f = [fc[::-1] for fc in cv_f]                        # master normals face the bladder (inward)
    cells("bladder_cover", bl_f, cv_f, bl_key, 20.0, 20.0, 6.0, 0.0, SFAC_DEV)
    # base slaves: bladder elements whose centroid lies in the lower 14 mm of the bladder section
    base_sl = [EL[e][2] for e in bl_e if Xc[EL[e][2]].mean(0)[0] - (meta_r(Xc[EL[e][2]].mean(0)[1]) + 9.18) < 14.0]
    cells("bladder_base", base_sl, [fc[::-1] for fc in S["base_master"]], lambda c: (c[1], c[2]), 25.0, 25.0, 6.0, 0.0, SFAC_DEV)
    pairs = [p for p in pairs if not any(p[0].startswith(k) for k in SKIP)]
    info_pairs = []
    for k, (nm, sl, ms, mu, sfac) in enumerate(pairs, start=1):
        if not sl or not ms:
            continue
        bsseg(100 + 2 * k, sl)
        bsseg(101 + 2 * k, ms)
        typ = 3 if (BOND_SKIN and (nm.startswith("pad_skin") or nm.startswith("ring_skin"))) else 1
        w("BSCONP,%d,%d,%d,%s,,%s,%d" % (k, 100 + 2 * k, 101 + 2 * k, f(sfac), f(mu), typ))
        info_pairs.append((k, nm, len(sl), len(ms), mu, sfac))
    nce = sum(p[2] * p[3] for p in info_pairs)
    # --------------------------------------------------------------- loads per subcase
    shank = S["bore_shank"]
    bl_ids = [eid(e) for e in bl_e]
    for k, s_ in enumerate(steps, start=1):
        sid = 1000 + k
        th = math.radians(s_["theta"])
        c, s = math.cos(th), math.sin(th)
        blend = S.get("sup_blend", {})
        for n in shank:
            if n in blend:
                continue
            x = Xc[n] - H
            u = [c * x[0] - s * x[1] - x[0], s * x[0] + c * x[1] - x[1], 0.0]
            for d in range(3):
                w("SPCD,%d,%d,%d,%s" % (sid, nid(n), d + 1, f(u[d])))
        for n, sb in sorted(blend.items()):   # blended support grids (thigh- and shank-side of the band)
            cb, sbn = math.cos(th * sb), math.sin(th * sb)
            x = Xc[n] - H
            u = [cb * x[0] - sbn * x[1] - x[0], sbn * x[0] + cb * x[1] - x[1], 0.0]
            for d in range(3):
                w("SPCD,%d,%d,%d,%s" % (sid, nid(n), d + 1, f(u[d])))
        if S.get("bore_mid"):
            c2, s2 = math.cos(th / 2.0), math.sin(th / 2.0)
            for n in S["bore_mid"]:
                x = Xc[n] - H
                u = [c2 * x[0] - s2 * x[1] - x[0], s2 * x[0] + c2 * x[1] - x[1], 0.0]
                for d in range(3):
                    w("SPCD,%d,%d,%d,%s" % (sid, nid(n), d + 1, f(u[d])))
        if s_["p"] > 0:
            for a, b in ranges(bl_ids):
                if b > a:
                    w("PLOAD4,%d,%d,%s,,,,THRU,%d" % (sid, a, f(s_["p"] / 1000.0), b))
                else:
                    w("PLOAD4,%d,%d,%s" % (sid, a, f(s_["p"] / 1000.0)))
    w("ENDDATA")
    open(out, "w").write("\n".join(L) + "\n")
    info = dict(run=run, opt=opt, plim=plim, tissue=tissue, padE=padE, seq=seq, steps=steps, dT=dT, H=H, mesh=os.path.relpath(os.path.abspath(out[:-4] + "_mesh.pkl"), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace(os.sep, "/"),   # repo-relative (post_process resolves it)
                pairs=info_pairs, alpha=ALPHA_RING, mu=MU_SKIN, mu_ring=(MU_RING if MU_RING is not None else MU_SKIN), sfac=sfac_skin)
    if RIGID_LEG or seq in ("MULTI", "CYCLE"):
        info.update(rigid_leg=RIGID_LEG, rigid_cover_ymin=RIGID_COVER_YMIN, bond_skin=BOND_SKIN, theta_case=THETA_T, plist=PLIST,
                    cover_ortho=COVER_ORTHO, flange_iso=FLANGE_ISO, cyc_p=CYC_P, cyc_end=CYC_END, cyc_step=CYC_STEP, seq=seq, crease_gap=CREASE_GAP, core_band=CORE_BAND, slstab=SLSTAB, sup_blend=SUP_BLEND, cov_endiso=COV_ENDISO, floor_bed=FLOOR_BED, floor_bond=FLOOR_BOND)
    pickle.dump(info, open(out[:-4] + "_info.pkl", "wb"))
    import shutil
    if RIGID_LEG:                                               # the run's mesh carries the rigid-half grid sets
        pickle.dump(m, open(out[:-4] + "_mesh.pkl", "wb"))
    else:
        shutil.copyfile(mesh_pkl, out[:-4] + "_mesh.pkl")          # the run keeps its own mesh (meshes are regenerated)
    with open(out[:-4] + "_steps.csv", "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["subcase", "name", "kind", "frame_pct", "time_ms", "theta_deg", "p_kPa", "ninc", "thermal"])
        for k, s_ in enumerate(steps, start=1):
            wr.writerow([k, s_["name"], s_["kind"], s_["frame"], s_["ms"], round(s_["theta"], 4), round(s_["p"], 4), s_["ninc"], s_["therm"]])
    print("%s: subcases %d grids %d elements %d contact pairs %d, slave x master segment products %d" % (
        os.path.basename(out), len(steps), len(X), len(EL), len(info_pairs), nce))


_GEO = None


def meta_r(y):
    global _GEO
    if _GEO is None:
        import sys
        gd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cad", "geometry")   # geometry code of the CAD
        a0 = sys.argv
        sys.argv = ["geo8.py", "A150"]
        sys.path.insert(0, gd)
        import geo8
        sys.argv = a0
        _GEO = geo8
    return _GEO.r(y)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run", default="R1")
    ap.add_argument("--opt", type=int, default=2)
    ap.add_argument("--plim", type=float, default=20)
    ap.add_argument("--tissue", default="relaxed")
    ap.add_argument("--padE", type=float, default=0.0965)
    ap.add_argument("--seq", default="D-21")
    ap.add_argument("--vref", action="store_true")
    ap.add_argument("--calib", default=None)
    ap.add_argument("--maxiter", type=int, default=25)
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--sfac", type=float, default=None)
    ap.add_argument("--mu", type=float, default=None)
    ap.add_argument("--nincD", type=int, default=None)
    ap.add_argument("--skip", default="")
    ap.add_argument("--vent", action="store_true")
    ap.add_argument("--mu_ring", type=float, default=None)
    ap.add_argument("--cover_bend", type=float, default=None)
    ap.add_argument("--bond_skin", action="store_true")
    ap.add_argument("--flange_bend", type=float, default=None)
    ap.add_argument("--cover_ortho", type=float, default=None)
    ap.add_argument("--flange_iso", action="store_true")
    ap.add_argument("--flange_ortho", action="store_true")
    ap.add_argument("--rigid_leg", action="store_true")          # s
    ap.add_argument("--rigid_cover", type=float, default=None)
    ap.add_argument("--theta", type=float, default=None)
    ap.add_argument("--plist", default=None)
    ap.add_argument("--floor_bond", action="store_true")         # core model, band floor bonded, blended
    ap.add_argument("--floor_bed", type=float, default=None)       # core model, rigid bed under the band floor, offset mm
    ap.add_argument("--cov_endiso", type=float, default=None)      # end-facing cover body elements isotropic
    ap.add_argument("--sup_blend", action="store_true")         # core model, continuous rigid support across the knee line
    ap.add_argument("--slstab", type=float, default=None)          # slide-line contact stabilisation factor
    ap.add_argument("--sleeve", action="store_true")              # core model, rigid sleeve in the band
    ap.add_argument("--core", type=float, default=None)             # with --rigid_leg, bladder + cover core model, crease band mm
    ap.add_argument("--crease_gap", type=float, default=None)       # with --rigid_leg, pad / flange cut at the knee line
    ap.add_argument("--cyc_p", default=None)                       # seq CYCLE test pressure (kPa) or PROJ
    ap.add_argument("--cyc_step", type=int, default=None)         # seq CYCLE stance stride (%), default 1
    ap.add_argument("--cyc_end", type=int, default=None)          # seq CYCLE last stance frame (%), default 50
    a = ap.parse_args()
    CREASE_GAP = a.crease_gap
    CORE_BAND = a.core
    SLSTAB = a.slstab
    SUP_BLEND = a.sup_blend
    COV_ENDISO = a.cov_endiso
    FLOOR_BED = a.floor_bed
    FLOOR_BOND = a.floor_bond
    CORE_SLEEVE = a.sleeve
    if a.cyc_end is not None:
        CYC_END = a.cyc_end
    if a.cyc_step is not None:
        CYC_STEP = a.cyc_step
    if a.cyc_p is not None:
        CYC_P = "PROJ" if a.cyc_p.upper() == "PROJ" else float(a.cyc_p)
    if a.seq == "CYCLE" and CYC_P is None:
        raise SystemExit("--seq CYCLE needs --cyc_p")
    if a.plim == int(a.plim):
        a.plim = int(a.plim)
    RIGID_LEG = a.rigid_leg
    RIGID_COVER_YMIN = a.rigid_cover
    THETA_T = a.theta
    if a.plist:
        PLIST = [float(v) for v in a.plist.split(",") if v.strip()]
    if a.seq == "MULTI" and (THETA_T is None or not PLIST):
        raise SystemExit("--seq MULTI needs --theta and --plist")
    if a.flange_iso:
        FLANGE_ISO = True
    if a.flange_ortho:
        FLANGE_ISO = False
    if a.cover_ortho is not None:
        COVER_ORTHO = a.cover_ortho if a.cover_ortho > 0 else None
    if a.cover_bend is not None:
        COVER_BEND = a.cover_bend
    if a.flange_bend is not None:
        FLANGE_BEND = a.flange_bend
    BOND_SKIN = a.bond_skin
    if a.sfac is not None:
        SFAC_SKIN = a.sfac
    if a.mu is not None:
        MU_SKIN = a.mu
    SKIP = [k for k in a.skip.split(",") if k]
    MU_RING = a.mu_ring
    VENT = a.vent
    if a.nincD is not None:
        NINC_D = a.nincD
    write(a.mesh, a.out, a.run, a.opt, a.plim, a.tissue, a.padE, a.seq, a.vref, a.calib, a.maxiter, extra_param=a.param)
