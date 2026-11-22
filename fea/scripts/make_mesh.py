# -*- coding: utf-8 -*-
"""Structured finite-element mesh of the knee-assist device, built from the same geometry code that made the CAD
(cad/geometry/geo8.py + geo_A150.json).

Frame: Y = leg axis (thigh +Y), knee line y = 0, point = (R cos th, y, R sin th), th = 0 at the back (+X). Units mm.
The mesh holds every part of the device (leg tissue, pad, webbing rings, closure pieces, bladder, cover); the idealised
reference model used in this repository keeps only the bladder, the cover and two rigid leg halves (make_deck.py).
  bladder  closed mid-surface shell (t 2 mm), stadium section swept along the leg, flat end caps; ports closed.
  cover    0.43 mm fabric shell on the bladder mid-surface with end caps and sewing flanges.
Mesh levels: --h device size, --hT tissue size (back), --hTc tissue size (front). Level M0 is the one used.
Usage: python -P make_mesh.py --level M0 --out ../model [--norender]
Writes <out>/mesh_<level>.pkl, mesh_quality_<level>.csv, mesh_<level>_view.png"""
import argparse
import csv
import json
import math
import os
import pickle
import sys

import numpy as np

GEO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cad", "geometry")   # geometry code of the CAD
_argv = sys.argv
sys.argv = ["geo8.py", "A150"]
sys.path.insert(0, GEO_DIR)
import geo8 as G                                   # noqa: E402 (exact CAD build functions)
sys.argv = _argv
GEO = json.load(open(os.path.join(GEO_DIR, "geo_A150.json")))
assert GEO["opt"] == "A150" and G.Y_TF == 150.0

T_PAD, T_WEB, BASE = G.T_PAD, G.T_WEB, G.BASE      # 6, 3.18, 9.18
STACK = T_WEB + G.T_VEL                             # carrier + M3 patch = 4.68
Y_STACK = (96.215, 120.0)                           # |y| range of the carrier / patch / tab stack (95 snapped to 96.215)
COV_END = G.Y_BL + G.G_COV + 0.43 / 2               # 96.215 cover mid end
COV_R = 11.0 + 0.43 / 2                             # 11.215 cover end round (mid)
COV_W, COV_RC, COV_CZ = 34.43 - 0.43 / 2, 23.43 - 0.43 / 2, 11.0   # 34.215, 23.215
NOTCH_U = 4.5
FLANGE = 10.0 + 0.43 / 2                            # 10.215 flange width beyond the wall mid-surface
BL_RHO, BL_C, BL_END, BL_R = 21.0, 11.0, 94.0, 9.0  # bladder mid: stadium radius 21 about (22, +/-11), end face 94, round R9
Y_FLAP = 90.5                                        # tab emerges from the end round (geo8 bladder_a)


# ----------------------------------------------------------------------------------------------- helpers
class Mesh:
    def __init__(self):
        self.X = []
        self.el = []          # (type, pid, [nodes], group)

    def node(self, p):
        self.X.append([float(p[0]), float(p[1]), float(p[2])])
        return len(self.X) - 1

    def add(self, typ, pid, nodes, grp):
        self.el.append((typ, pid, [int(n) for n in nodes], grp))
        return len(self.el) - 1


def P(th, y, R):
    return (R * math.cos(th), y, R * math.sin(th))


def subdiv(anchors, h, minn=1):
    """sorted unique anchors -> list with uniform subdivision of every interval (<= h)"""
    out = [anchors[0]]
    for a, b in zip(anchors[:-1], anchors[1:]):
        n = max(minn, int(math.ceil((b - a) / h - 1e-9)))
        out += list(np.linspace(a, b, n + 1)[1:])
    return np.array(out)


def snap(anchors, tol):
    """anchors = [(value, priority)] -> sorted values, anchors closer than tol merged into the higher-priority one"""
    a = sorted(anchors)
    out = []
    for v, p in a:
        if out and v - out[-1][0] < tol:
            if p > out[-1][1]:
                out[-1] = (v, p)
            continue
        out.append((v, p))
    return [v for v, _ in out]


def ths(y, v, off):
    """polar angle of lateral position v (= z) on the radius r(y)+off (back side)"""
    return math.asin(max(-0.999, min(0.999, v / (G.r(y) + off))))


def hex_ok(X, n):
    p = X[n]
    v = np.dot(np.cross(p[1] - p[0], p[3] - p[0]), p[4] - p[0])
    return v > 0


def fix_hex(X, n):
    return n if hex_ok(X, n) else [n[4], n[5], n[6], n[7], n[0], n[1], n[2], n[3]]


# ----------------------------------------------------------------------------------------------- build
def build(h=4.0, hT=8.0, hTc=16.0, npad=2, nrad=5, eps0=0.05):
    M = Mesh()
    S = {}                                   # named sets
    # --------------------------------------------------------------- tissue grids
    # theta: fine (hT) for |th| <= 135 deg, coarse (hTc) at the front; arc measured on R = 70
    Rref = 70.0
    def theta_list():
        lim = math.radians(135.0)
        nf = int(math.ceil(2 * lim * Rref / hT))
        nc = max(2, int(math.ceil((2 * math.pi - 2 * lim) * Rref / hTc)))
        a = list(np.linspace(-lim, lim, nf + 1)) + list(np.linspace(lim, 2 * math.pi - lim, nc + 1)[1:-1])
        return np.array(a)
    TH = theta_list()
    nth = len(TH)
    yT_anchor = [(-170.0, 3), (-10.0, 3), (0.0, 3), (10.0, 3), (180.0, 3)]
    YT = subdiv(snap(yT_anchor, 0.5), hT)
    q = 1.4
    w = np.array([q ** k for k in range(nrad)])
    s_lay = np.concatenate([[0.0], np.cumsum(w[::-1]) / w.sum()])      # 0 at the bore .. 1 at the skin, fine at the skin
    tid = np.zeros((nth, len(YT), nrad + 1), dtype=int)
    for j, y in enumerate(YT):
        R = G.r(y)
        for i, th in enumerate(TH):
            for k, s in enumerate(s_lay):
                tid[i, j, k] = M.node(P(th, y, 15.0 + (R - 15.0) * s))
    X = np.array(M.X)
    S["tissue_e"] = []
    for i in range(nth):
        i2 = (i + 1) % nth
        for j in range(len(YT) - 1):
            for k in range(nrad):
                n = [tid[i, j, k], tid[i2, j, k], tid[i2, j + 1, k], tid[i, j + 1, k],
                     tid[i, j, k + 1], tid[i2, j, k + 1], tid[i2, j + 1, k + 1], tid[i, j + 1, k + 1]]
                S["tissue_e"].append(M.add("CHEXA", 1, fix_hex(X, n), "tissue"))
    # skin faces (outward normal), with centre theta / y
    skin = []
    for i in range(nth):
        i2 = (i + 1) % nth
        for j in range(len(YT) - 1):
            f = [tid[i, j, -1], tid[i, j + 1, -1], tid[i2, j + 1, -1], tid[i2, j, -1]]
            p = X[f]
            nrm = np.cross(p[1] - p[0], p[3] - p[0])
            c = p.mean(0)
            if np.dot(nrm, [c[0], 0, c[2]]) < 0:
                f = f[::-1]
            thc = math.atan2(c[2], c[0])
            skin.append((f, thc, c[1]))
    S["skin"] = skin
    S["bore_thigh"] = sorted(int(tid[i, j, 0]) for i in range(nth) for j, y in enumerate(YT) if y >= 10.0 - 1e-6)
    S["bore_shank"] = sorted(int(tid[i, j, 0]) for i in range(nth) for j, y in enumerate(YT) if y <= -10.0 + 1e-6)
    dth_t = np.diff(np.concatenate([TH, [TH[0] + 2 * math.pi]]))

    def interference(th, y):
        """inward offset of device skin-contact nodes: facet sagitta of the tissue + eps0 (contact closed at donning)"""
        t = (th - TH[0]) % (2 * math.pi) + TH[0]
        i = int(np.searchsorted(TH, t, side="right") - 1) % nth
        return G.r(y) * (1 - math.cos(dth_t[i] / 2)) + eps0

    # --------------------------------------------------------------- device y grid
    st = {s[0]: s for s in G.STATIONS}
    anc = [(G.PAD_Y0, 5), (G.PAD_Y1, 5), (0.0, 1)]
    for nm, yc, b, side, wh, ls, ws, L in G.STATIONS:
        anc += [(yc - b / 2, 4), (yc + b / 2, 4), (yc - ws / 2, 3), (yc + ws / 2, 3)]
    for sg in (1, -1):
        anc += [(sg * COV_END, 6), (sg * Y_STACK[1], 2), (sg * (COV_END - COV_R), 3)]
        for k in range(1, 4):                                         # cover end round stations
            anc.append((sg * (COV_END - COV_R + COV_R * math.sin(math.radians(22.5 * k))), 2))
    YD = subdiv(snap(anc, 1.2), h)
    ny = len(YD)

    def in_rng(a, b):
        return [j for j, y in enumerate(YD) if a - 1e-6 <= y <= b + 1e-6]

    def snapy(v):
        return float(YD[np.argmin(abs(YD - v))])

    # cover wall lateral position (mid) vs y, flange outer edge
    def vwall(y):
        a = abs(y)
        if a <= COV_END - COV_R:
            return COV_W
        if a >= COV_END:
            return COV_W - COV_R
        w_ = a - (COV_END - COV_R)
        return COV_W - (COV_R - math.sqrt(max(COV_R ** 2 - w_ ** 2, 0.0)))

    # --------------------------------------------------------------- pad (hex)
    lat = [11.0, 20.0]                                                # bladder base flat edge, carrier / tab edge
    nseg = []
    segdef = []                                                       # per y: anchor angles (left edge .. right edge)

    def pad_anchors(y):
        R6 = G.r(y) + T_PAD
        vw = vwall(y)
        a = [G.th_edge(y, -1), -ths(y, vw + FLANGE, T_PAD), -ths(y, vw, T_PAD), -lat[1] / R6, -ths(y, lat[0], T_PAD),
             ths(y, lat[0], T_PAD), lat[1] / R6, ths(y, vw, T_PAD), ths(y, vw + FLANGE, T_PAD), G.th_edge(y, +1)]
        return a
    A = np.array([pad_anchors(y) for y in YD])
    Rm = np.array([G.r(y) + T_PAD for y in YD])
    for s_ in range(A.shape[1] - 1):
        L = ((A[:, s_ + 1] - A[:, s_]) * Rm).max()
        hh = 1.5 * h if s_ in (0, A.shape[1] - 2) else h          # pad outer parts (edge -> flange) at 1.5 h
        nseg.append(max(1, int(math.ceil(L / hh - 1e-9))))
    nflat = nseg[4]                                                   # elements across the bladder base flat (|v| <= 11)
    PAD_TH = []
    for j in range(ny):
        row = [A[j, 0]]
        for s_ in range(A.shape[1] - 1):
            row += list(np.linspace(A[j, s_], A[j, s_ + 1], nseg[s_] + 1)[1:])
        PAD_TH.append(row)
    PAD_TH = np.array(PAD_TH)
    ncol = PAD_TH.shape[1]
    col_anchor = np.concatenate([[0], np.cumsum(nseg)])               # column index of every anchor
    offs = list(np.linspace(0.0, T_PAD, npad + 1))
    pid_ = np.zeros((ncol, ny, npad + 1), dtype=int)
    for j, y in enumerate(YD):
        for i in range(ncol):
            th = PAD_TH[j, i]
            for k, o in enumerate(offs):
                oo = -interference(th, y) if k == 0 else o
                pid_[i, j, k] = M.node(P(th, y, G.r(y) + oo))
    X = np.array(M.X)
    S["pad_e"], S["pad_bottom"], S["pad_top"] = [], [], []
    for i in range(ncol - 1):
        for j in range(ny - 1):
            for k in range(npad):
                n = [pid_[i, j, k], pid_[i + 1, j, k], pid_[i + 1, j + 1, k], pid_[i, j + 1, k],
                     pid_[i, j, k + 1], pid_[i + 1, j, k + 1], pid_[i + 1, j + 1, k + 1], pid_[i, j + 1, k + 1]]
                S["pad_e"].append(M.add("CHEXA", 2, fix_hex(X, n), "pad"))
            thc, yc_ = PAD_TH[j, i:i + 2].mean(), YD[j:j + 2].mean()
            S["pad_bottom"].append(([pid_[i, j, 0], pid_[i + 1, j, 0], pid_[i + 1, j + 1, 0], pid_[i, j + 1, 0]], thc, yc_))
            S["pad_top"].append(([pid_[i, j, -1], pid_[i + 1, j, -1], pid_[i + 1, j + 1, -1], pid_[i, j + 1, -1]], thc, yc_, i, j))

    # --------------------------------------------------------------- seats (hex), rings, hooks
    S["rings"] = {}
    S["hooks"] = {}
    S["seat_e"] = []
    for nm, yc, b, side, wh, ls, ws, Lf in G.STATIONS:
        a = G.station_angles(st[nm])
        rows_seat = in_rng(snapy(yc - ws / 2), snapy(yc + ws / 2))
        rows_ring = in_rng(snapy(yc - b / 2), snapy(yc + b / 2))
        edge_col = ncol - 1 if side > 0 else 0
        tt = a["tip"]
        # seat columns: edge(y) -> hi -> ho -> tip (angles measured outward in the side direction)
        def segs_len(th0, th1, R):
            return abs(th1 - th0) * R
        R6c = G.r(yc) + T_PAD
        n1 = max(1, int(math.ceil(segs_len(a["te"], a["hi"], R6c) / h)))
        n2 = max(2, int(math.ceil(segs_len(a["hi"], a["ho"], R6c) / h)))
        n3 = max(1, int(math.ceil(segs_len(a["ho"], tt, R6c) / h)))
        nsc = n1 + n2 + n3 + 1
        sid = np.zeros((nsc, len(rows_seat), npad + 1), dtype=int)
        sth = np.zeros((nsc, len(rows_seat)))
        for jj, j in enumerate(rows_seat):
            y = YD[j]
            te_y = PAD_TH[j, edge_col]
            ang = [te_y] + list(np.linspace(te_y, a["hi"], n1 + 1)[1:]) + list(np.linspace(a["hi"], a["ho"], n2 + 1)[1:]) + \
                list(np.linspace(a["ho"], tt, n3 + 1)[1:])
            sth[:, jj] = ang
            for ii in range(nsc):
                for k, o in enumerate(offs):
                    if ii == 0:
                        sid[ii, jj, k] = pid_[edge_col, j, k]
                    else:
                        oo = -interference(ang[ii], y) if k == 0 else o
                        sid[ii, jj, k] = M.node(P(ang[ii], y, G.r(y) + oo))
        X = np.array(M.X)
        for ii in range(nsc - 1):
            for jj in range(len(rows_seat) - 1):
                for k in range(npad):
                    n = [sid[ii, jj, k], sid[ii + 1, jj, k], sid[ii + 1, jj + 1, k], sid[ii, jj + 1, k],
                         sid[ii, jj, k + 1], sid[ii + 1, jj, k + 1], sid[ii + 1, jj + 1, k + 1], sid[ii, jj + 1, k + 1]]
                    S["seat_e"].append(M.add("CHEXA", 2, fix_hex(X, n), "pad"))
                S["pad_bottom"].append(([sid[ii, jj, 0], sid[ii + 1, jj, 0], sid[ii + 1, jj + 1, 0], sid[ii, jj + 1, 0]],
                                        sth[ii:ii + 2, jj].mean(), YD[rows_seat[jj:jj + 2]].mean()))
        # --- ring loop as a list of columns (node id per ring row), unwrapped angle increasing
        jr0 = rows_seat.index(rows_ring[0])
        nr = len(rows_ring)
        def seat_col(ii):
            return [int(sid[ii, jr0 + r_, -1]) for r_ in range(nr)], float(sth[ii, jr0:jr0 + nr].mean())
        def pad_col(i):
            return [int(pid_[i, j, -1]) for j in rows_ring], float(PAD_TH[rows_ring, i].mean())
        ramp = a["ramp"]
        cols = []          # (node ids, angle, kind); kind of the element that STARTS at this column
        hook_cols = []
        if side > 0:
            for i in range(ncol):
                cols.append(pad_col(i) + ("pad",))
            for ii in range(1, nsc):
                kind = "hook" if n1 <= ii < n1 + n2 else "seat"
                cols.append(seat_col(ii) + (kind,))
            th_start_front = tt
            th_end_front = PAD_TH[rows_ring, 0].mean() + 2 * math.pi
        else:
            for ii in range(nsc - 1, 0, -1):
                cols.append(seat_col(ii) + ("seat",))
            for i in range(ncol):
                cols.append(pad_col(i) + ("pad",))
            th_start_front = PAD_TH[rows_ring, -1].mean()
            th_end_front = tt + 2 * math.pi
        # front: ramp down (15 mm), skin, ramp up; closure laminate next to the seat-side ramp
        Rf = G.r(yc)
        nramp = max(2, int(math.ceil(15.0 / h)))
        span = (th_end_front - th_start_front) - 2 * ramp
        tv = 72.0 / (G.r(yc) + T_WEB)
        nclo = max(2, int(math.ceil(tv * Rf / h)))
        nfr = max(2, int(math.ceil((span - tv) * Rf / (1.5 * h))))
        t1 = th_start_front + ramp
        t2 = th_end_front - ramp
        if side > 0:
            fr_angles = list(np.linspace(t1, t1 + tv, nclo + 1)) + list(np.linspace(t1 + tv, t2, nfr + 1)[1:])
            clo_rng = (t1 - 1e-9, t1 + tv + 1e-9)
        else:
            fr_angles = list(np.linspace(t1, t2 - tv, nfr + 1)) + list(np.linspace(t2 - tv, t2, nclo + 1)[1:])
            clo_rng = (t2 - tv - 1e-9, t2 + 1e-9)
        ramp_dn = list(np.linspace(th_start_front, t1, nramp + 1)[1:-1])
        ramp_up = list(np.linspace(t2, th_end_front, nramp + 1)[1:-1])
        new_angles = [(t, "ramp") for t in ramp_dn] + [(t, "front") for t in fr_angles] + [(t, "ramp") for t in ramp_up]
        newcols = []
        for t, kind in new_angles:
            ids = []
            for j in rows_ring:
                y = YD[j]
                if kind == "front":
                    o = -interference(t, y)
                elif t < t1:
                    o = T_PAD + (-interference(t, y) - T_PAD) * (t - th_start_front) / ramp
                else:
                    o = -interference(t, y) + (T_PAD + interference(t, y)) * (t - t2) / ramp
                ids.append(M.node(P(t, y, G.r(y) + o)))
            kk = "front" if kind == "front" else "ramp"
            if kind == "front" and clo_rng[0] <= t <= clo_rng[1]:
                kk = "front_clo"
            newcols.append((ids, t, kk))
        loop = cols + newcols
        # close the loop with the first column
        loop.append((loop[0][0], loop[0][1] + 2 * math.pi, "end"))
        ring_e, ring_info, skin_faces = [], [], []
        hook_e = []
        for c in range(len(loop) - 1):
            ids0, ta, kind0 = loop[c]
            ids1, tb, kind1 = loop[c + 1]
            tm = 0.5 * (ta + tb)
            # element kind by position
            if side > 0:
                is_hook = a["hi"] - 1e-9 <= ta and tb <= a["ho"] + 1e-9 and ta >= a["hi"] - 1e-9 and tb <= a["ho"] + 1e-9 and ta < 2 * math.pi
            else:
                is_hook = a["ho"] - 1e-9 <= ta and tb <= a["hi"] + 1e-9
            if is_hook:
                continue
            onskin = kind0 in ("front", "front_clo", "ramp") or kind1 in ("front", "front_clo", "ramp")
            clo = kind0 == "front_clo" and kind1 in ("front_clo",)
            pid = 4 if clo else 3
            for r_ in range(nr - 1):
                q_ = [ids0[r_], ids1[r_], ids1[r_ + 1], ids0[r_ + 1]]           # G1->G2 = hoop, normal inward
                e = M.add("CQUAD4", pid, q_, "ring_" + nm)
                ring_e.append(e)
                ring_info.append((e, c, 0.5 * (YD[rows_ring[r_ + 1]] - YD[rows_ring[r_]]) * 2, tm, onskin, clo))
                if onskin:
                    skin_faces.append(q_)
        # hook elements: seat top between hi and ho over the seat rows
        for ii in range(n1, n1 + n2):
            for jj in range(len(rows_seat) - 1):
                q_ = [sid[ii, jj, -1], sid[ii + 1, jj, -1], sid[ii + 1, jj + 1, -1], sid[ii, jj + 1, -1]]
                hook_e.append(M.add("CQUAD4", 5, q_, "hook_" + nm))
        S["rings"][nm] = dict(e=ring_e, info=ring_info, skin=skin_faces, rows=[float(YD[j]) for j in rows_ring],
                              nodes=sorted(set(n for e_ in ring_e for n in M.el[e_][2])), yc=yc, b=b, side=side,
                              ncols=len(loop) - 1)
        S["hooks"][nm] = dict(e=hook_e, file="hook.05.ipt" if wh == 40.0 else "hook.06.ipt", wh=wh)

    # --------------------------------------------------------------- carrier / patch stack (hex) + tabs
    ia, ib = col_anchor[3], col_anchor[6]                     # columns -20 .. +20
    S["stack_e"], S["tab_e"], S["stack_top_row"] = [], [], {}
    for sg in (1, -1):
        rows = in_rng(Y_STACK[0], Y_STACK[1]) if sg > 0 else in_rng(-Y_STACK[1], -Y_STACK[0])
        top = {}
        for j in rows:
            y = YD[j]
            for i in range(ia, ib + 1):
                top[i, j] = M.node(P(PAD_TH[j, i], y, G.r(y) + T_PAD + STACK))
        X = np.array(M.X)
        for i in range(ia, ib):
            for jj in range(len(rows) - 1):
                j, j2 = rows[jj], rows[jj + 1]
                n = [pid_[i, j, -1], pid_[i + 1, j, -1], pid_[i + 1, j2, -1], pid_[i, j2, -1],
                     top[i, j], top[i + 1, j], top[i + 1, j2], top[i, j2]]
                S["stack_e"].append(M.add("CHEXA", 6, fix_hex(X, n), "stack"))
                S["tab_e"].append(M.add("CQUAD4", 7, [top[i, j], top[i + 1, j], top[i + 1, j2], top[i, j2]], "tab"))
        jedge = rows[0] if sg > 0 else rows[-1]
        S["stack_top_row"][sg] = [top[i, jedge] for i in range(col_anchor[4], col_anchor[5] + 1)]   # |v| <= 11 columns

    # --------------------------------------------------------------- bladder (closed mid-surface)
    nf_b = 4
    yb = [y for y in YD if abs(y) <= COV_END - COV_R - 1e-6 and abs(y) <= 85.0 + 1e-6]
    yb = sorted(set([float(v) for v in yb] + [-85.0, 85.0]))
    endz = [85.0 + BL_R * math.sin(math.radians(90.0 * k / nf_b)) for k in range(1, nf_b + 1)]
    YB = np.array(sorted(set([-v for v in endz] + yb + endz)))
    n_arc = max(4, int(math.ceil(math.pi * BL_RHO / h)))

    def bl_rho(y):
        a_ = abs(y)
        if a_ <= 85.0:
            return BL_RHO
        w_ = min(a_ - 85.0, BL_R)
        return BL_RHO - (BL_R - math.sqrt(max(BL_R ** 2 - w_ ** 2, 0.0)))

    def stadium_uv(rho):
        pts = []
        for v in np.linspace(-BL_C, BL_C, nflat + 1)[:-1]:
            pts.append((22.0 - rho, v))
        for p_ in np.linspace(0, math.pi, n_arc + 1)[:-1]:
            pts.append((22.0 - rho * math.cos(p_), BL_C + rho * math.sin(p_)))
        for v in np.linspace(BL_C, -BL_C, nflat + 1)[:-1]:
            pts.append((22.0 + rho, v))
        for p_ in np.linspace(0, math.pi, n_arc + 1)[:-1]:
            pts.append((22.0 + rho * math.cos(p_), -BL_C - rho * math.sin(p_)))
        return pts
    nper = 2 * nflat + 2 * n_arc
    brow = []
    for y in YB:
        brow.append([M.node(G.L(y, u, v)) for u, v in stadium_uv(bl_rho(y))])
    S["bl_body"], S["bl_cap"] = [], []
    X = np.array(M.X)

    def orient_out(q_, centre):
        p = X[q_]
        nrm = np.cross(p[1] - p[0], p[2] - p[0]) if len(q_) == 3 else np.cross(p[2] - p[0], p[3] - p[1])
        return q_ if np.dot(nrm, p.mean(0) - centre) > 0 else q_[::-1]
    for jb in range(len(YB) - 1):
        cen = np.array(G.L(0.5 * (YB[jb] + YB[jb + 1]), 22.0, 0.0))
        for ip in range(nper):
            ip2 = (ip + 1) % nper
            q_ = [brow[jb][ip], brow[jb][ip2], brow[jb + 1][ip2], brow[jb + 1][ip]]
            S["bl_body"].append(M.add("CQUAD4", 8, orient_out(q_, cen), "bladder"))
    for jb, sg in ((0, -1), (len(YB) - 1, 1)):
        y = YB[jb]
        rho0 = bl_rho(y)
        nring = max(2, int(math.ceil(rho0 / h)))
        rings = [brow[jb]]
        rr = list(np.linspace(rho0, 0.0, nring + 1)[1:-1])
        for rho in rr:
            rings.append([M.node(G.L(y, u, v)) for u, v in stadium_uv(rho)])
        mid = [M.node(G.L(y, 22.0, v)) for v in np.linspace(-BL_C, BL_C, nflat + 1)]
        X = np.array(M.X)
        cen = np.array(G.L(y - sg * 30.0, 22.0, 0.0))
        for a_ in range(len(rings) - 1):
            for ip in range(nper):
                ip2 = (ip + 1) % nper
                q_ = [rings[a_][ip], rings[a_][ip2], rings[a_ + 1][ip2], rings[a_ + 1][ip]]
                S["bl_cap"].append(M.add("CQUAD4", 8, orient_out(q_, cen), "bladder"))
        last = rings[-1]
        bot = last[0:nflat + 1]                                         # v -11 .. 11 at u = 22 - rho
        topr = last[nflat + n_arc: 2 * nflat + n_arc + 1][::-1]          # v -11 .. 11 at u = 22 + rho
        for c in range(nflat):
            for q_ in ([bot[c], bot[c + 1], mid[c + 1], mid[c]], [mid[c], mid[c + 1], topr[c + 1], topr[c]]):
                S["bl_cap"].append(M.add("CQUAD4", 8, orient_out(q_, cen), "bladder"))
        arcR = last[nflat: nflat + n_arc + 1]
        arcL = last[2 * nflat + n_arc:] + [last[0]]
        for arc, cc in ((arcR, mid[-1]), (arcL, mid[0])):
            for c in range(len(arc) - 1):
                S["bl_cap"].append(M.add("CTRIA3", 8, orient_out([cc, arc[c], arc[c + 1]], cen), "bladder"))
    # flap (M3 tab root): bladder base row nearest |y| = 90.5 -> stack top edge row
    S["flap_e"] = []
    for sg in (1, -1):
        jb = int(np.argmin(abs(YB - sg * Y_FLAP)))
        bot = brow[jb][0:nflat + 1]
        edge = S["stack_top_row"][sg]
        assert len(edge) == len(bot), (len(edge), len(bot))
        for c in range(nflat):
            S["flap_e"].append(M.add("CQUAD4", 7, [bot[c], bot[c + 1], edge[c + 1], edge[c]], "tab"))
    S["bl_nodes"] = sorted(set(n for e in S["bl_body"] + S["bl_cap"] for n in M.el[e][2]))

    # --------------------------------------------------------------- cover (mid-surface) + flanges
    jc = in_rng(-COV_END, COV_END)
    ia_w = {-1: col_anchor[2], 1: col_anchor[7]}
    ia_f = {-1: col_anchor[1], 1: col_anchor[8]}
    n_lo = max(2, int(math.ceil(12.0 / h)))
    n_up = max(3, int(math.ceil((22.0 - NOTCH_U) / h)))
    n_carc = max(4, int(math.ceil(0.5 * math.pi * COV_RC / h)))
    n_top = nflat
    crow = []
    X = np.array(M.X)
    for j in jc:
        y = YD[j]
        dl = COV_W - vwall(y)
        rc = COV_RC - dl
        ids = []
        for sgn in (-1,):
            pass
        # left wall bottom (pad node) -> notch level -> 22 -> arc -> top -> arc -> right wall -> bottom
        vl = -vwall(y)
        pb = X[pid_[ia_w[-1], j, -1]]
        Bp, t_, n_ = G.frame(y)
        ub = float(np.dot(pb - np.array(Bp), np.array(n_)))
        seq = [pid_[ia_w[-1], j, -1]]
        for u in np.linspace(ub, NOTCH_U, n_lo + 1)[1:]:
            seq.append(M.node(G.L(y, u, vl)))
        for u in np.linspace(NOTCH_U, 22.0, n_up + 1)[1:]:
            seq.append(M.node(G.L(y, u, vl)))
        for p_ in np.linspace(0, 0.5 * math.pi, n_carc + 1)[1:]:
            seq.append(M.node(G.L(y, 22.0 + rc * math.sin(p_), -COV_CZ - rc * math.cos(p_))))
        for v in np.linspace(-COV_CZ, COV_CZ, n_top + 1)[1:]:
            seq.append(M.node(G.L(y, 22.0 + rc, v)))
        for p_ in np.linspace(0.5 * math.pi, 0, n_carc + 1)[1:]:
            seq.append(M.node(G.L(y, 22.0 + rc * math.sin(p_), COV_CZ + rc * math.cos(p_))))
        for u in np.linspace(22.0, NOTCH_U, n_up + 1)[1:]:
            seq.append(M.node(G.L(y, u, -vl)))
        pb = X[pid_[ia_w[1], j, -1]]
        ub = float(np.dot(pb - np.array(Bp), np.array(n_)))
        for u in np.linspace(NOTCH_U, ub, n_lo + 1)[1:-1]:
            seq.append(M.node(G.L(y, u, -vl)))
        seq.append(pid_[ia_w[1], j, -1])
        crow.append(seq)
    X = np.array(M.X)
    S["cov_body"], S["cov_cap"], S["cov_flange"] = [], [], []
    for a_ in range(len(jc) - 1):
        cen = np.array(G.L(0.5 * (YD[jc[a_]] + YD[jc[a_ + 1]]), 22.0, 0.0))
        for c in range(len(crow[a_]) - 1):
            q_ = [crow[a_][c], crow[a_][c + 1], crow[a_ + 1][c + 1], crow[a_ + 1][c]]
            S["cov_body"].append(M.add("CQUAD4", 9, orient_out(q_, cen), "cover"))
    # end caps: Coons patch on the flat end face, bottom edge = notch line u = 4.5
    for a_, sg in ((0, -1), (len(jc) - 1, 1)):
        y = YD[jc[a_]]
        ring = crow[a_]
        left = ring[n_lo: n_lo + n_up + 1]                       # notch level -> 22 on the left wall
        top = ring[n_lo + n_up: n_lo + n_up + 2 * n_carc + n_top + 1]
        right = ring[n_lo + n_up + 2 * n_carc + n_top: n_lo + 2 * n_up + 2 * n_carc + n_top + 1][::-1]
        Bp, t_, n_ = G.frame(y)
        def uv(nid):
            p = X[nid] - np.array(Bp)
            return np.array([np.dot(p, n_), p[2]])
        Lp = np.array([uv(n) for n in left])
        Rp = np.array([uv(n) for n in right])
        Tp = np.array([uv(n) for n in top])
        m_ = len(top) - 1
        nn = len(left) - 1
        Bt = np.array([[NOTCH_U, v] for v in np.linspace(Lp[0, 1], Rp[0, 1], m_ + 1)])
        grid = [[None] * (m_ + 1) for _ in range(nn + 1)]
        for i in range(nn + 1):
            for k in range(m_ + 1):
                if i == 0 and k in (0, m_):
                    grid[i][k] = left[0] if k == 0 else right[0]
                elif k == 0:
                    grid[i][k] = left[i]
                elif k == m_:
                    grid[i][k] = right[i]
                elif i == nn:
                    grid[i][k] = top[k]
                else:
                    s_, t2_ = k / m_, i / nn
                    p = ((1 - t2_) * Bt[k] + t2_ * Tp[k] + (1 - s_) * Lp[i] + s_ * Rp[i]
                         - ((1 - s_) * (1 - t2_) * Lp[0] + s_ * (1 - t2_) * Rp[0] + (1 - s_) * t2_ * Lp[-1] + s_ * t2_ * Rp[-1]))
                    grid[i][k] = M.node(G.L(y, p[0], p[1]))
        X = np.array(M.X)
        cen = np.array(G.L(y - sg * 30.0, 22.0, 0.0))
        for i in range(nn):
            for k in range(m_):
                q_ = [grid[i][k], grid[i][k + 1], grid[i + 1][k + 1], grid[i + 1][k]]
                S["cov_cap"].append(M.add("CQUAD4", 9, orient_out(q_, cen), "cover"))
    # cap corners where the wall runs into the end round (boundary angle ~180 deg): split quads with an angle > 150 deg
    # into two triangles through the obtuse corner
    X = np.array(M.X)
    keep = []
    for e in S["cov_cap"]:
        typ, pidc, n, grp = M.el[e]
        p = X[n]
        ang = []
        for a_ in range(4):
            u_, v_ = p[(a_ + 1) % 4] - p[a_], p[a_ - 1] - p[a_]
            ang.append(math.degrees(math.acos(max(-1.0, min(1.0, np.dot(u_, v_) / (np.linalg.norm(u_) * np.linalg.norm(v_) + 1e-30))))))
        k = int(np.argmax(ang))
        if ang[k] > 150.0:
            t1 = [n[k], n[(k + 1) % 4], n[(k + 2) % 4]]
            t2 = [n[k], n[(k + 2) % 4], n[(k + 3) % 4]]
            M.el[e] = ("CTRIA3", pidc, t1, grp)
            keep.append(M.add("CTRIA3", pidc, t2, grp))
    S["cov_cap"] += keep
    # flanges = pad-top faces between the wall and the flange edge (shared nodes)
    for side_ in (-1, 1):
        c0, c1 = sorted((ia_w[side_], ia_f[side_]))
        for a_ in range(len(jc) - 1):
            j, j2 = jc[a_], jc[a_ + 1]
            for i in range(c0, c1):
                S["cov_flange"].append(M.add("CQUAD4", 10, [pid_[i, j, -1], pid_[i + 1, j, -1], pid_[i + 1, j2, -1], pid_[i, j2, -1]], "cover_flange"))

    # --------------------------------------------------------------- contact surfaces (device side)
    # bladder base master: pad-top faces with |v| <= wall, |y| <= cover end
    S["base_master"] = [t[0] for t in S["pad_top"] if col_anchor[2] <= t[3] < col_anchor[7] and abs(t[2]) <= COV_END + 1e-6]
    meta = dict(h=h, hT=hT, hTc=hTc, npad=npad, nrad=nrad, eps0=eps0, YD=YD, YT=YT, TH=TH, YB=YB, PAD_TH=PAD_TH,
                col_anchor=col_anchor, nflat=nflat, n_arc=n_arc, H=np.array([G.r(0.0) - 65.0, 0.0, 0.0]),
                r0=G.r(0.0), names=GEO["names"], stations={s[0]: s[1] for s in G.STATIONS})
    return M, S, meta


# ----------------------------------------------------------------------------------------------- quality
def quality(M):
    X = np.array(M.X)
    rows = {}
    for typ, pid, n, grp in M.el:
        p = X[n]
        if typ == "CQUAD4" or typ == "CTRIA3":
            k = len(n)
            ed = [np.linalg.norm(p[(a + 1) % k] - p[a]) for a in range(k)]
            ang = []
            for a in range(k):
                u, v = p[(a + 1) % k] - p[a], p[a - 1] - p[a]
                c = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-30)
                ang.append(math.degrees(math.acos(max(-1, min(1, c)))))
            ar = max(ed) / max(min(ed), 1e-12)
            jac = 1.0
            if k == 4:
                n1 = np.cross(p[1] - p[0], p[3] - p[0])
                warp = 0.0
                for a in range(4):
                    na = np.cross(p[(a + 1) % 4] - p[a], p[a - 1] - p[a])
                    c = np.dot(na, n1) / (np.linalg.norm(na) * np.linalg.norm(n1) + 1e-30)
                    jac = min(jac, c)
                    warp = max(warp, math.degrees(math.acos(max(-1, min(1, c)))))
            mina, maxa = min(ang), max(ang)
        else:
            # hex: edge aspect, scaled Jacobian at the 8 corners
            E = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
            ed = [np.linalg.norm(p[b] - p[a]) for a, b in E]
            ar = max(ed) / max(min(ed), 1e-12)
            nb = {0: (1, 3, 4), 1: (2, 0, 5), 2: (3, 1, 6), 3: (0, 2, 7), 4: (7, 5, 0), 5: (4, 6, 1), 6: (5, 7, 2), 7: (6, 4, 3)}
            jac = 1.0
            for c_, (a, b, d) in nb.items():
                u, v, w = p[a] - p[c_], p[b] - p[c_], p[d] - p[c_]
                sj = np.dot(np.cross(u, v), w) / (np.linalg.norm(u) * np.linalg.norm(v) * np.linalg.norm(w) + 1e-30)
                jac = min(jac, sj)
            mina = maxa = float("nan")
        r = rows.setdefault(grp, dict(n=0, ar=[], jac=[], mina=[], maxa=[]))
        r["n"] += 1
        r["ar"].append(ar)
        r["jac"].append(jac)
        if mina == mina:
            r["mina"].append(mina)
            r["maxa"].append(maxa)
    out = []
    for g, r in rows.items():
        ar = np.array(r["ar"])
        out.append(dict(group=g, elements=r["n"], AR_mean=ar.mean(), AR_max=ar.max(), AR_gt10=int((ar > 10).sum()),
                        min_scaled_jacobian=min(r["jac"]), jac_lt_0_2=int((np.array(r["jac"]) < 0.2).sum()),
                        min_angle=(min(r["mina"]) if r["mina"] else float("nan")),
                        max_angle=(max(r["maxa"]) if r["maxa"] else float("nan"))))
    return out


def render(M, S, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    X = np.array(M.X)
    fig = plt.figure(figsize=(14, 7))
    cols = {"pad": "#c8b98a", "ring": "#3b6fb6", "hook": "#222222", "bladder": "#d9534f", "cover": "#8fbc8f",
            "cover_flange": "#5f8f5f", "tab": "#aa3333", "stack": "#555599"}
    for k, (el, az) in enumerate(((10, -30), (10, 120))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        polys, fc = [], []
        for typ, pid, n, grp in M.el:
            if grp == "tissue":
                continue
            key = "ring" if grp.startswith("ring") else ("hook" if grp.startswith("hook") else grp)
            if typ == "CHEXA":
                if grp != "stack":
                    continue
                n = n[4:]
            polys.append(X[n][:, [0, 2, 1]])
            fc.append(cols.get(key, "#999999"))
        pc = Poly3DCollection(polys, facecolors=fc, edgecolors="k", linewidths=0.05, alpha=0.9)
        ax.add_collection3d(pc)
        sk = [X[f][:, [0, 2, 1]] for f, th, y in S["skin"]]
        ax.add_collection3d(Poly3DCollection(sk, facecolors="#f2d0c0", edgecolors="none", alpha=0.25))
        ax.set_xlim(-110, 150)
        ax.set_ylim(-130, 130)
        ax.set_zlim(-180, 190)
        ax.view_init(el, az)
        ax.set_xlabel("X (posterior)")
        ax.set_ylabel("Z")
        ax.set_zlabel("Y (leg axis)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    LV = {"M0": (5.0, 10.0, 10.0, 2, 4), "M1": (4.0, 8.0, 8.0, 2, 5), "M2": (3.4, 6.8, 6.8, 2, 5), "M3": (2.5, 5.0, 5.0, 3, 6)}   # front = back size; M2 kept <= 60 000 grids (RAM)
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="M1")
    ap.add_argument("--h", type=float)
    ap.add_argument("--hT", type=float)
    ap.add_argument("--hTc", type=float)
    ap.add_argument("--npad", type=int)
    ap.add_argument("--nrad", type=int)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model"))
    ap.add_argument("--norender", action="store_true")
    a = ap.parse_args()
    h, hT, hTc, npad, nrad = LV[a.level]
    h = a.h or h
    hT = a.hT or hT
    hTc = a.hTc or hTc
    npad = a.npad or npad
    nrad = a.nrad or nrad
    M, S, meta = build(h, hT, hTc, npad, nrad)
    os.makedirs(a.out, exist_ok=True)
    X = np.array(M.X)
    pickle.dump(dict(X=X, el=M.el, S=S, meta=meta, level=a.level), open(os.path.join(a.out, "mesh_%s.pkl" % a.level), "wb"))
    q = quality(M)
    with open(os.path.join(a.out, "mesh_quality_%s.csv" % a.level), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(q[0].keys()))
        wr.writeheader()
        for r in q:
            wr.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    cnt = {}
    for typ, pid, n, grp in M.el:
        cnt[grp.split("_")[0]] = cnt.get(grp.split("_")[0], 0) + 1
    print("level %s h %.2f hT %.1f hTc %.1f npad %d nrad %d: grids %d elements %d" % (a.level, h, hT, hTc, npad, nrad, len(X), len(M.el)))
    print(" ", cnt)
    for r in q:
        print("  %-14s n %6d AR mean %.2f max %.2f (>10: %d) minJ %.3f (<0.2: %d) angle %.1f..%.1f" % (
            r["group"], r["elements"], r["AR_mean"], r["AR_max"], r["AR_gt10"], r["min_scaled_jacobian"], r["jac_lt_0_2"],
            r["min_angle"], r["max_angle"]))
    if not a.norender:
        render(M, S, os.path.join(a.out, "mesh_%s_view.png" % a.level))
