# -*- coding: utf-8 -*-
"""CAD v7 geometry (curved +2 SD leg, wrapped pad and webbing rings, bladder routes a/b, covers).
Common model frame for every part (all inserted at identity, except hooks and tube):
  Y = leg axis (thigh +Y), knee line at y = 0;  theta = 0 is the back of the knee (+X); theta > 0 towards +Z.
  point(theta, y, R) = (R cos th, y, R sin th).  Units mm.  Output: JSON op lists for build7.ps1."""
import json, math, os, sys
import numpy as np
from scipy.interpolate import PchipInterpolator

OUT = os.path.dirname(os.path.abspath(__file__))
# Final CAD: option A150 = thigh strap at +150 (biomechanics table B8, main), A100 = thigh strap at +100 (comparison).
# Both: calf strap at -120 (widest calf girth, C1), pad extended (Q1), M3 webbing carriers (Q2), cover follows the bladder (C4/C5).
OPT = sys.argv[1] if len(sys.argv) > 1 else 'A150'
Y_TF = 150.0 if OPT == 'A150' else 100.0          # thigh far strap centre (mm above the knee line)
Y_SF = -120.0                                       # calf strap centre (C1)
PAD_Y0 = -143.0                                     # pad shank end (Q1: seat end -138.5 + 4.5)
PAD_Y1 = 173.0 if OPT == 'A150' else 123.0          # pad thigh end (Q1: seat end 168.5 + 4.5)
NAMES = {'A150': dict(pad='streches.10.ipt', web='webbing.03.ipt', vel='velcro.05.ipt', cov='cover.06.ipt', asm='full asseymbly 07.iam'),
         'A100': dict(pad='streches.11.ipt', web='webbing.04.ipt', vel='velcro.06.ipt', cov='cover.07.ipt', asm='full asseymbly 08.iam')}[OPT]
G_COV = 1.0                                         # cover-to-bladder gap everywhere (C4, D35)
Y_BL = 95.0                                         # bladder end (actuator-V8 sweep -95..95)

# ---------------- leg profile r(y): circular sections from B8 v5 girths at mean + 2 SD (larger of 6 / 13 wk)
ST = [(-170, 62.0), (-120, 399.5 / (2 * math.pi)), (0, 433.9 / (2 * math.pi)), (50, 500.5 / (2 * math.pi)),
      (100, 557.2 / (2 * math.pi)), (150, 607.7 / (2 * math.pi)), (180, 101.5)]
_r = PchipInterpolator([a for a, _ in ST], [b for _, b in ST])
_dr = _r.derivative()


def r(y): return float(_r(y))
def dr(y): return float(_dr(y))


T_PAD, T_WEB, T_VEL = 6.0, 3.18, 1.5
BASE = T_PAD + T_WEB            # bladder base radial offset over the leg = webbing top


def P(th, y, R):
    return [R * math.cos(th), y, R * math.sin(th)]


def ys(a, b, step=5.0):
    n = max(2, int(math.ceil(abs(b - a) / step)) + 1)
    return list(np.linspace(a, b, n))


def spline_RY(th, ya, yb, off, step=5.0):
    return {'k': 'spline', 'p': [P(th, y, r(y) + off) for y in ys(ya, yb, step)]}


def line(a, b):
    return {'k': 'line', 'p': [a, b]}


def axial_plane(th):
    return [[0, 0, 0], [0, 100, 0], P(th, 0, 100)]


def band_region(th, ya, yb, o1, o2, step=5.0):
    """closed region in the axial half-plane at theta: o1 <= R - r(y) <= o2, ya <= y <= yb"""
    inner = spline_RY(th, ya, yb, o1, step)
    outer = spline_RY(th, yb, ya, o2, step)
    return [inner, line(inner['p'][-1], outer['p'][0]), outer, line(outer['p'][-1], inner['p'][0])]


def stepped_region(th, ya, yb, steps, add, rin=2.0, step=4.0):
    """region from radius rin up to r(y)+off(y)+add, off piecewise (steps = [(y1, y2, off)], ramps 2 mm), for cuts"""
    pts = []
    yy = ya
    def off_at(y):
        for a, b, o in steps:
            if a <= y <= b:
                return o
        return steps[-1][2] if False else None
    # build piecewise list of (y, off) with ramps
    segs = sorted(steps)
    pieces = []
    cur = ya
    prof = []
    for a, b, o in segs:
        prof.append((a, b, o))
    out = []
    for (a, b, o) in prof:
        out += [(y, o) for y in ys(a, b, step)]
    # outer boundary as polyline spline pieces per segment + ramp lines
    loop = []
    first = None
    prev_end = None
    for i, (a, b, o) in enumerate(prof):
        sp = {'k': 'spline', 'p': [P(th, y, r(y) + o + add) for y in ys(a, b, step)]}
        if prev_end is not None:
            loop.append(line(prev_end, sp['p'][0]))
        loop.append(sp)
        prev_end = sp['p'][-1]
    start = loop[0]['p'][0]
    loop.append(line(prev_end, P(th, prof[-1][1], rin)))
    loop.append(line(P(th, prof[-1][1], rin), P(th, prof[0][0], rin)))
    loop.append(line(P(th, prof[0][0], rin), start))
    return loop


# ---------------- pad outline (v6 streches.08 widths, s = arc length on the pad mid-surface from the bladder centre line)
S_POS = [(-143, 84.09), (-123, 84.09), (-100, 84.09), (0, 90.34), (50, 93.59), (100, 101.84), (123, 107.13), (150, 113.24), (173, 113.24)]
S_NEG = [(-143, -85.41), (-123, -85.41), (-100, -85.41), (0, -91.66), (45.34, -94.49), (100, -103.16), (123, -108.45), (150, -114.56), (173, -114.56)]
# v8 extension (Q1): shank end held at the -100/-123 width; thigh +150 = W = Cmin/2 = 455.6/2 = 227.8 mm (B8 operated leg
# +15 cm low girth) with the v6 +/- split (neg side 1.32 mm wider); beyond +150 held constant (assumption, no girth source).


def s_edge(y, side):
    tab = S_POS if side > 0 else S_NEG
    return float(np.interp(y, [a for a, _ in tab], [b for _, b in tab]))


def th_edge(y, side):
    return s_edge(y, side) / (r(y) + T_PAD / 2)


STATIONS = [  # name, y_c, width, side of the hook (+1 thigh / -1 shank), hook width, seat length, seat width, free L
    ('thigh_far', Y_TF, 25.4, +1, 31.0, 51.0, 37.0, 461.0),
    ('thigh_near', 35.0, 50.8, +1, 40.0, 60.0, 62.5, 422.5),
    ('shank_near', -35.0, 50.8, -1, 40.0, 60.0, 62.5, 364.5),
    ('shank_far', Y_SF, 25.4, -1, 31.0, 51.0, 37.0, 372.5),
]   # free L (last field) is the v9 cut length, recorded only (not used by the geometry); v10 values come from the calc


def sketch(sid, plane, loops, open_=False):
    if loops and isinstance(loops[0], dict):
        loops = [loops]
    return {'op': 'sketch', 'id': sid, 'plane': plane, 'loops': loops, 'open': open_}


# =====================================================================================  LEG
def leg_parts():
    tissue = {'part': 'leg-tissue.02.ipt', 'src': 'FEA:leg-tissue.01.ipt', 'ops': [{'op': 'suppress_all'}]}
    yA, yB = -170.0, 180.0
    prof = spline_RY(0, yA, yB, 0.0, 5.0)
    loop = [prof, line(prof['p'][-1], [0, yB, 0]), line([0, yB, 0], [0, yA, 0]), line([0, yA, 0], prof['p'][0])]
    tissue['ops'] += [sketch('leg', 'XY', [loop]), {'op': 'revolve', 'sketch': 'leg', 'angle': 'full', 'oper': 'new', 'name': 'Leg_revolve_B8_2SD'},
                      sketch('bone_t', [[0, 10, 0], [0, 10, 100], [100, 10, 0]], [[{'k': 'circle', 'c': [0, 10, 0], 'r': 15.0}]]),
                      {'op': 'extrude', 'sketch': 'bone_t', 'dist': 200, 'dir': 'away_y+', 'oper': 'cut', 'name': 'Femur_hole_D30'},
                      sketch('bone_s', [[0, -10, 0], [100, -10, 0], [0, -10, 100]], [[{'k': 'circle', 'c': [0, -10, 0], 'r': 15.0}]]),
                      {'op': 'extrude', 'sketch': 'bone_s', 'dist': 200, 'dir': 'away_y-', 'oper': 'cut', 'name': 'Tibia_hole_D30'},
                      {'op': 'fillet', 'r': 5.0, 'sel': {'type': 'circ_edges_at_y', 'y': [yA, yB], 'rmin': 40}, 'name': 'Leg_end_R5'}]
    bones = []
    for nm, src, a, b in (('thigh-bone.02.ipt', 'FEA:thigh-bone.01.ipt', 10.0, yB), ('shank-bone.02.ipt', 'FEA:shank-bone.01.ipt', yA, -10.0)):
        loop = [line([0, a, 0], [15, a, 0]), line([15, a, 0], [15, b, 0]), line([15, b, 0], [0, b, 0]), line([0, b, 0], [0, a, 0])]
        bones.append({'part': nm, 'src': src, 'ops': [{'op': 'suppress_all'}, sketch('bone', 'XY', [loop]),
                      {'op': 'revolve', 'sketch': 'bone', 'angle': 'full', 'oper': 'new', 'name': 'Bone_D30'},
                      {'op': 'fillet', 'r': 3.0, 'sel': {'type': 'circ_edges_at_y', 'y': [10.0, -10.0], 'rmin': 10}, 'name': 'Joint_end_R3'}]})
    return [tissue] + bones


# =====================================================================================  PAD
def pad_part():
    ops = [{'op': 'suppress_all'}]
    ops += [sketch('ann', 'XY', [band_region(0, PAD_Y0, PAD_Y1, 0.0, T_PAD)]),
            {'op': 'revolve', 'sketch': 'ann', 'angle': 'full', 'oper': 'new', 'name': 'Pad_layer_6mm', 'body': 'pad'}]
    secs = []
    ysec = [PAD_Y0, -123, -100, 0, 45.34, 50, 100, 123] + ([150, PAD_Y1] if PAD_Y1 > 123 else [])
    for i, y in enumerate(ysec):
        t1, t2 = th_edge(y, -1), th_edge(y, +1)
        Ro, Ri = r(y) + 40, 3.0
        loop = [{'k': 'arc3', 'p': [P(t1, y, Ri), P((t1 + t2) / 2, y, Ri), P(t2, y, Ri)]}, line(P(t2, y, Ri), P(t2, y, Ro)),
                {'k': 'arc3', 'p': [P(t2, y, Ro), P((t1 + t2) / 2, y, Ro), P(t1, y, Ro)]}, line(P(t1, y, Ro), P(t1, y, Ri))]
        ops.append(sketch('w%d' % i, [[0, y, 0], [100, y, 0], [0, y, 100]], [loop]))
        secs.append('w%d' % i)
    ops.append({'op': 'loft', 'sketches': secs, 'oper': 'new', 'name': 'Pad_outline_wrapped', 'body': 'wedge'})
    ops.append({'op': 'combine', 'base': 'pad', 'tools': ['wedge'], 'oper': 'intersect', 'keep': False})
    ops.append({'op': 'fillet', 'r': 2.0, 'r_try': [2.0, 1.5, 1.0], 'sel': {'type': 'all'}, 'name': 'Pad_edges', 'optional': True})
    seats = []
    for nm, yc, b, side, wh, ls, ws, L in STATIONS:
        te = th_edge(yc, side)
        tt = te + side * ls / (r(yc) + T_PAD / 2)
        t0 = te - side * 4.0 / (r(yc) + T_PAD / 2)           # 4 mm overlap into the pad
        tm = (t0 + tt) / 2
        ops.append(sketch('seat_' + nm, axial_plane(tm), [band_region(tm, yc - ws / 2, yc + ws / 2, 0.0, T_PAD, 3.0)]))
        ops.append({'op': 'revolve', 'sketch': 'seat_' + nm, 'angle': math.degrees(abs(tt - t0)), 'oper': 'join', 'name': 'Seat_' + nm})
        Rm = r(yc) + T_PAD / 2
        for yy in (yc - ws / 2, yc + ws / 2):
            seats.append(P(tt, yy, r(yy) + T_PAD / 2))
    ops.append({'op': 'fillet', 'r': 5.0, 'r_try': [5.0, 3.0, 2.0], 'sel': {'type': 'near', 'pts': seats, 'tol': 3.5}, 'name': 'Seat_tips', 'optional': True})
    ops.append({'op': 'material', 'name': 'A3 neoprene-spacer laminate 6 mm (pad, D12-1)', 'E': 96.5, 'nu': 0.33, 'rho': 203.9, 'Sy': 345, 'Su': 345})
    return {'part': NAMES['pad'], 'src': 'V5:streches.09.ipt', 'ops': ops}


# =====================================================================================  WEBBING / VELCRO / HOOKS
def station_angles(st):
    nm, yc, b, side, wh, ls, ws, L = st
    R6 = r(yc) + T_PAD
    te = th_edge(yc, side)
    te_op = th_edge(yc, -side)
    d = {}
    d['te'] = te; d['te_op'] = te_op
    d['hi'] = te + side * (10.0 - 0.5) / R6          # webbing stops 0.3 mm before the hook inner edge
    d['hc'] = te + side * (10.0 + wh / 2) / R6
    d['ho'] = te + side * (10.0 + wh + 0.5) / R6
    d['tip'] = te + side * ls / (r(yc) + T_PAD / 2)
    d['ramp'] = 15.0 / r(yc)
    return d


M3_Y = {+1: (95.0, 120.0), -1: (-120.0, -95.0)}     # M3 patch footprint along the leg (v7, unchanged)


def free_intervals(y1, y2):
    """parts of [y1, y2] not covered by a ring band (the carrier fills only these)"""
    segs = [(y1, y2)]
    for st in STATIONS:
        a, b = st[1] - st[2] / 2, st[1] + st[2] / 2
        out = []
        for s, e in segs:
            if b <= s or a >= e:
                out.append((s, e)); continue
            if a > s: out.append((s, a))
            if b < e: out.append((b, e))
        segs = out
    return [(s, e) for s, e in segs if e - s > 0.5]


def web_parts():
    web = [{'op': 'suppress_all'}]
    vel = [{'op': 'suppress_all'}]
    vel_b = [{'op': 'suppress_all'}]
    hooks = []
    tails = []
    for st in STATIONS:
        nm, yc, b, side, wh, ls, ws, L = st
        a = station_angles(st)
        ya, yb = yc - b / 2, yc + b / 2
        def rev(tag, t1, t2, o1, o2, oper, lst, name):
            tm = (t1 + t2) / 2
            lst.append(sketch(tag, axial_plane(tm), [band_region(tm, ya, yb, o1, o2, 3.0)]))
            lst.append({'op': 'revolve', 'sketch': tag, 'angle': math.degrees(abs(t2 - t1)), 'oper': oper, 'name': name})
        def loft(tag, t1, o1, t2, o2, lst, name):
            lst.append(sketch(tag + 'a', axial_plane(t1), [band_region(t1, ya, yb, o1, o1 + T_WEB, 3.0)]))
            lst.append(sketch(tag + 'b', axial_plane(t2), [band_region(t2, ya, yb, o2, o2 + T_WEB, 3.0)]))
            lst.append({'op': 'loft', 'sketches': [tag + 'a', tag + 'b'], 'oper': 'join', 'name': name})
        first = 'new' if st is STATIONS[0] else 'new'
        # 1 over the pad: hook inner edge -> opposite pad edge
        rev('op_' + nm, a['hi'], a['te_op'], T_PAD, T_PAD + T_WEB, 'new', web, 'Over_pad_' + nm)
        # 2 ramp down at the opposite pad edge
        t_skin1 = a['te_op'] - side * a['ramp']
        loft('rd_' + nm, a['te_op'], T_PAD, t_skin1, 0.02, web, 'Ramp_down_' + nm)
        # 3 skin round the front: from t_skin1 (going away from the back) to the seat-tip ramp end
        t_skin2 = a['tip'] + side * a['ramp']
        # angles: going from t_skin1 by -side direction round the front to t_skin2 (= t_skin1 - side*(2pi - |...|))
        span = 2 * math.pi - abs(t_skin2 - t_skin1)
        t_end = t_skin1 - side * span
        rev('sk_' + nm, t_skin1, t_end, 0.02, T_WEB + 0.02, 'join', web, 'Skin_' + nm)
        # 4 ramp up onto the seat tip
        loft('ru_' + nm, t_skin2, 0.02, a['tip'], T_PAD, web, 'Ramp_up_' + nm)
        # 5 over the seat: seat tip -> hook outer edge
        rev('os_' + nm, a['tip'], a['ho'], T_PAD, T_PAD + T_WEB, 'join', web, 'Over_seat_' + nm)
        # 6 closure: Velcro (1.5) + fold-back tail (3.18), 72 mm from the seat-tip ramp towards the front
        tv = 72.0 / (r(yc) + T_WEB)
        t_a, t_b = t_skin2, t_skin2 + side * tv
        rev('tail_' + nm, t_a, t_b, T_WEB + T_VEL + 0.04, 2 * T_WEB + T_VEL + 0.04, 'join', web, 'Tail_' + nm)
        tails.append((nm, t_b, ya, yb))
        for lst in (vel, vel_b):
            rev('vel_' + nm, t_a, t_b, T_WEB + 0.02, T_WEB + T_VEL + 0.02, 'new', lst, 'Velcro_closure_' + nm)
        # hook placement (centre on the seat surface, tangent, along the cone generator)
        R6 = r(yc) + T_PAD
        th = a['hc']; s_, c_ = math.sin(th), math.cos(th)
        rp = dr(yc); N = math.sqrt(1 + rp * rp)
        o = P(th, yc, R6)
        ex = [s_, 0.0, -c_]                                  # -e_theta
        ey = [rp * c_ / N, 1 / N, rp * s_ / N]
        ez = [c_ / N, -rp / N, s_ / N]
        hl = 30.25 if wh == 40.0 else 17.5
        lift = 0.0
        for xx in np.linspace(-wh / 2, wh / 2, 21):
            for yy in np.linspace(-hl, hl, 41):
                q = [o[k] + xx * ex[k] + yy * ey[k] for k in range(3)]
                pen = (r(q[1]) + T_PAD) - math.hypot(q[0], q[2])
                lift = max(lift, pen)
        lift += 0.05
        o = [o[k] + lift * ez[k] for k in range(3)]
        hooks.append({'station': nm, 'file': 'hook.05.ipt' if wh == 40.0 else 'hook.06.ipt', 'o': o, 'x': ex, 'y': ey, 'z': ez, 'lift': lift})
    # v8 (Q2): M3 carriers - 40 mm wide Type XXV pieces sewn to the pad under the M3 patches where no ring lies,
    # so the patch stays level with the bladder tab (patch on BASE, tab bottom at BASE + 1.5)
    for (y1, y2), tg in (M3_Y[+1], 'thigh'), (M3_Y[-1], 'shank'):
        for k, (a, b) in enumerate(free_intervals(y1, y2)):
            tw = 20.0 / (r((a + b) / 2) + T_PAD)
            web.append(sketch('car_%s%d' % (tg, k), axial_plane(0.0), [band_region(0.0, a, b, T_PAD, BASE, 2.5)]))
            web.append({'op': 'revolve', 'sketch': 'car_%s%d' % (tg, k), 'angle': math.degrees(2 * tw), 'oper': 'new', 'name': 'M3_carrier_%s%d' % (tg, k)})
    # combine all webbing bodies into one
    web.append({'op': 'combine_all', 'name': 'Webbing_rings'})
    # round the free tail tips (full round, R = half width of one webbing) and all small edges
    tips = []
    for nm, tb, ya, yb in tails:
        for yy in (ya, yb):
            tips.append(P(tb, yy, r(yy) + 1.5 * T_WEB + T_VEL + 0.04))
    web.append({'op': 'fillet', 'r': 10.0, 'sel': {'type': 'near', 'pts': tips, 'tol': 2.0}, 'name': 'Tail_tips_R10', 'optional': True})
    web.append({'op': 'fillet', 'r': 0.5, 'r_try': [0.5], 'sel': {'type': 'all'}, 'name': 'Edges_R0.5', 'optional': True})
    web.append({'op': 'material', 'name': 'MIL-W-4088K Type XXV nylon webbing (D12-5)', 'E': 498000, 'nu': 0.35, 'rho': 576, 'Sy': 247600, 'Su': 247600})
    # M3 patches (route a only): on the webbing top at the bladder ends, 40 wide, y 95..120
    for sgn in (+1, -1):
        y1, y2 = (95.0, 120.0) if sgn > 0 else (-120.0, -95.0)
        tw = 20.0 / (r((y1 + y2) / 2) + BASE)
        loop = band_region(0.0, y1, y2, BASE, BASE + T_VEL, 2.5)
        vel.append(sketch('m3_%d' % sgn, axial_plane(0.0), [loop]))
        vel.append({'op': 'revolve', 'sketch': 'm3_%d' % sgn, 'angle': math.degrees(2 * tw), 'oper': 'new', 'name': 'M3_patch_%s' % ('thigh' if sgn > 0 else 'shank')})
    mat = {'op': 'material', 'name': 'Velcro Hook 88 / Loop 1000 (woven nylon, D12-4)', 'E': 498000, 'nu': 0.35, 'rho': 109, 'Sy': 83, 'Su': 83}
    for lst in (vel, vel_b):
        lst.append({'op': 'combine_all', 'name': 'Velcro'})
        lst.append({'op': 'fillet', 'r': 3.0, 'sel': {'type': 'short_edges', 'max_len': 1.6}, 'name': 'Corners_R3', 'optional': True})
        lst.append(dict(mat))
    return ([{'part': NAMES['web'], 'src': 'V5:webbing.02.ipt', 'ops': web},
             {'part': NAMES['vel'], 'src': 'V5:velcro.03.ipt', 'ops': vel}], hooks)


def hook_parts():
    out = []
    for nm, src, xm, ym in (('hook.05.ipt', 'V3:hook.04.ipt', 17.5, 28.0), ('hook.06.ipt', 'V3:hook.03.ipt', 0, 0)):
        out.append({'part': nm, 'src': src, 'ops': [{'op': 'fillet', 'r': 1.0, 'r_try': [1.0, 0.75, 0.5], 'sel': ({'type': 'largest_faces', 'n': 2} if xm else {'type': 'all'}), 'name': 'Face_edges', 'optional': True}]})
    return out


# =====================================================================================  BLADDER and COVER
def frame(y):
    """base point on the bladder base curve (theta = 0), tangent t, outward normal n, lateral ez"""
    x = r(y) + BASE
    rp = dr(y); N = math.sqrt(1 + rp * rp)
    t = [rp / N, 1 / N, 0.0]
    n = [1 / N, -rp / N, 0.0]
    return [x, y, 0.0], t, n


def L(y, u, v):
    B, t, n = frame(y)
    return [B[0] + u * n[0], B[1] + u * n[1], v]


def sec_plane(y):
    B, t, n = frame(y)
    return [B, [B[0] + 10 * n[0], B[1] + 10 * n[1], 0.0], [B[0], B[1], 10.0]]


def path(ya, yb, uoff=0.0):
    return [{'k': 'spline', 'p': [L(y, uoff, 0.0) for y in ys(ya, yb, 5.0)]}]


def stadium(y, uo=0.0, half=33.0, rr=22.0):
    """outer bladder section (66 x 44), base on u = 0"""
    c = half - rr
    return [line(L(y, 0, -c), L(y, 0, c)),
            {'k': 'arc3', 'p': [L(y, 0, c), L(y, rr - rr * math.cos(math.pi / 4), c + rr * math.sin(math.pi / 4)), L(y, rr, half)]},
            {'k': 'arc3', 'p': [L(y, rr, half), L(y, rr + rr * math.sin(math.pi / 4), c + rr * math.cos(math.pi / 4)), L(y, 2 * rr, c)]},
            line(L(y, 2 * rr, c), L(y, 2 * rr, -c)),
            {'k': 'arc3', 'p': [L(y, 2 * rr, -c), L(y, rr + rr * math.sin(math.pi / 4), -c - rr * math.cos(math.pi / 4)), L(y, rr, -half)]},
            {'k': 'arc3', 'p': [L(y, rr, -half), L(y, rr - rr * math.cos(math.pi / 4), -c - rr * math.sin(math.pi / 4)), L(y, 0, -c)]}]


def rect(y, u1, u2, v1, v2):
    return [line(L(y, u1, v1), L(y, u1, v2)), line(L(y, u1, v2), L(y, u2, v2)), line(L(y, u2, v2), L(y, u2, v1)), line(L(y, u2, v1), L(y, u1, v1))]


def bladder_a():
    ops = [{'op': 'suppress_all'}]
    ops += [sketch('path', 'XY', path(-95, 95), True), sketch('sec', sec_plane(-95), [stadium(-95)]),
            {'op': 'sweep', 'sketch': 'sec', 'path': 'path', 'oper': 'new', 'name': 'Body_66x44_L190'},
            {'op': 'fillet', 'r': 10.0, 'sel': {'type': 'faces_normal', 'normals': [frame(-95)[1], frame(95)[1]]}, 'name': 'Ends_R10'},
            {'op': 'shell', 't': 2.0, 'name': 'Wall_2mm'}]
    for sgn in (+1, -1):
        y1, y2 = (90.5, 120.0) if sgn > 0 else (-120.0, -90.5)
        ops += [sketch('tp%d' % sgn, 'XY', path(y1, y2), True), sketch('ts%d' % sgn, sec_plane(y1), [rect(y1, 1.5, 3.5, -20, 20)]),
                {'op': 'sweep', 'sketch': 'ts%d' % sgn, 'path': 'tp%d' % sgn, 'oper': 'join', 'name': 'M3_tab_%s' % ('thigh' if sgn > 0 else 'shank')}]
    corners = [L(y, 2.5, v) for y in (120.0, -120.0) for v in (-20.0, 20.0)]
    ops += [{'op': 'fillet', 'r': 5.0, 'sel': {'type': 'near', 'pts': corners, 'tol': 1.2}, 'name': 'Tab_corners_R5', 'optional': True},
            sketch('port', sec_plane(95), [[{'k': 'circle', 'c': L(95, 22, 0), 'r': 3.0}]]),
            {'op': 'extrude', 'sketch': 'port', 'dist': 4.0, 'dir': 'sym', 'oper': 'cut', 'name': 'Port_D6'}]
    return {'part': 'actuator-V8.ipt', 'src': 'V3:actuator-V7.ipt', 'ops': ops}


def bladder_b():
    ops = [{'op': 'suppress_all'}]
    ends = {'type': 'faces_normal', 'normals': [frame(-95)[1], frame(95)[1]]}
    ops += [sketch('path', 'XY', path(-95, 95), True), sketch('sec', sec_plane(-95), [stadium(-95)]),
            {'op': 'sweep', 'sketch': 'sec', 'path': 'path', 'oper': 'new', 'name': 'Body_66x44_L190', 'body': 'shell'},
            {'op': 'fillet', 'r': 10.0, 'sel': ends, 'name': 'Ends_R10', 'body': 'shell'},
            {'op': 'shell', 't': 2.0, 'name': 'Wall_2mm', 'body': 'shell'},
            sketch('fpath', 'XY', path(-105, 105), True), sketch('fsec', sec_plane(-105), [rect(-105, 21, 23, -43, 43)]),
            {'op': 'sweep', 'sketch': 'fsec', 'path': 'fpath', 'oper': 'new', 'name': 'Seal_fin_10mm', 'body': 'fin'}]
    corners = [L(y, 22, v) for y in (105.0, -105.0) for v in (-43.0, 43.0)]
    ops.append({'op': 'fillet', 'r': 10.0, 'sel': {'type': 'near', 'pts': corners, 'tol': 1.5}, 'name': 'Fin_corners_R10', 'body': 'fin', 'optional': True})
    tabs = [(-121.55, -100.0, -20.0, 20.0, 'shank'), (100.0, 121.55, 5.0, 20.0, 'thigh1'), (100.0, 121.55, -20.0, -5.0, 'thigh2')]
    for y1, y2, v1, v2, tg in tabs:
        ops += [sketch('tp_' + tg, 'XY', path(y1, y2), True), sketch('ts_' + tg, sec_plane(y1), [rect(y1, 21, 23, v1, v2)]),
                {'op': 'sweep', 'sketch': 'ts_' + tg, 'path': 'tp_' + tg, 'oper': 'join', 'name': 'Tab_' + tg, 'body': 'fin'}]
    ops += [sketch('path2', 'XY', path(-95, 95), True), sketch('sec2', sec_plane(-95), [stadium(-95)]),
            {'op': 'sweep', 'sketch': 'sec2', 'path': 'path2', 'oper': 'new', 'name': 'Tool_solid', 'body': 'tool'},
            {'op': 'fillet', 'r': 10.0, 'sel': ends, 'name': 'Tool_ends_R10', 'body': 'tool'},
            {'op': 'combine', 'base': 'fin', 'tools': ['tool'], 'oper': 'cut', 'keep': False},
            {'op': 'combine', 'base': 'shell', 'tools': ['fin'], 'oper': 'join', 'keep': False},
            sketch('port', sec_plane(95), [[{'k': 'circle', 'c': L(95, 22, 0), 'r': 3.0}]]),
            {'op': 'extrude', 'sketch': 'port', 'dist': 24.0, 'dir': 'sym', 'oper': 'cut', 'name': 'Port_D6_through_seal'}]
    return {'part': 'actuator-V9.ipt', 'src': 'V3:actuator-V7.ipt', 'ops': ops}


def cover_sec(y, w, cz, Rc, ulow=-40.0):
    """cover section: vertical walls at |v| = w from ulow up to u = 22, top arcs radius Rc centred (22, +/-cz), top line"""
    top = 22 + Rc
    k = math.sin(math.pi / 4)
    return [line(L(y, ulow, -w), L(y, 22, -w)),
            {'k': 'arc3', 'p': [L(y, 22, -w), L(y, 22 + Rc * k, -cz - Rc * k), L(y, top, -cz)]},
            line(L(y, top, -cz), L(y, top, cz)),
            {'k': 'arc3', 'p': [L(y, top, cz), L(y, 22 + Rc * k, cz + Rc * k), L(y, 22, w)]},
            line(L(y, 22, w), L(y, ulow, w)), line(L(y, ulow, w), L(y, ulow, -w))]


WEB_Y = [(st[1] - st[2] / 2, st[1] + st[2] / 2) for st in STATIONS]


def rin_steps(ya, yb):
    """surface the cover / flange sits on: pad (+6) except over the webbing (+9.18)"""
    cuts = sorted(WEB_Y)
    steps = []
    cur = ya
    for a, b in cuts:
        if b + 0.5 <= ya or a - 0.5 >= yb:          # v8: band outside the range (moved far rings) - skip
            continue
        a2, b2 = a - 2.5, b + 2.5
        if a2 > cur:
            steps.append((cur, a2, T_PAD))
        steps.append((max(a - 0.5, cur), min(b + 0.5, yb), BASE))
        cur = b2
    if cur < yb:
        steps.append((cur, yb, T_PAD))
    return steps


def cover8():
    """v8 cover (route a): the pocket follows the bladder with a 1 mm gap everywhere (C4). The section is the v7 one
    (inner walls |v| = 34, top arcs R23 about (22, +/-11), inner top u = 45); the pillow ends are replaced by end caps
    1 mm beyond the bladder ends (inner +/-96.0, outer +/-96.43) with inner rounds R11 = bladder end R10 + 1 (outer R11.43).
    Each end cap has a centred notch on its leg-side edge for the M3 tab (C5): 42 wide (40 + 2 x 1), up to u = 4.5
    (tab top 3.5 + 1), top corners R1 in the sketch, entry corners R1 (end-view sketch)."""
    ops = [{'op': 'suppress_all'}]
    w, cz, Rc, tf = 34.43, 11.0, 23.43, 0.43
    ye_o = Y_BL + G_COV + tf                        # 96.43
    for tag, ww, rc, ye, rf in (('out', w, Rc, ye_o, 10.0 + G_COV + tf), ('in', w - tf, Rc - tf, Y_BL + G_COV, 10.0 + G_COV)):
        ops += [sketch('p_' + tag, 'XY', path(-ye, ye), True), sketch('s_' + tag, sec_plane(-ye), [cover_sec(-ye, ww, cz, rc)]),
                {'op': 'sweep', 'sketch': 's_' + tag, 'path': 'p_' + tag, 'oper': 'new', 'name': 'Cover_' + tag, 'body': tag},
                {'op': 'fillet', 'r': rf, 'sel': {'type': 'faces_normal', 'normals': [frame(-ye)[1], frame(ye)[1]]}, 'name': 'End_cap_R%.2f_%s' % (rf, tag), 'body': tag}]
    ops.append({'op': 'combine', 'base': 'out', 'tools': ['in'], 'oper': 'cut', 'keep': False})
    st = rin_steps(-140, 140)
    ops += [sketch('seat', 'XY', [stepped_region(0, -140, 140, st, 0.0)]),
            {'op': 'revolve', 'sketch': 'seat', 'angle': 'full', 'oper': 'cut', 'name': 'Sits_on_pad_and_webbing', 'body': 'out'}]
    fl = rin_steps(-ye_o + 0.5, ye_o - 0.5)
    ops += [sketch('flange', 'XY', [stepped_layer(0, fl, tf)]),
            {'op': 'revolve', 'sketch': 'flange', 'angle': 'full', 'oper': 'new', 'name': 'Flange_layer', 'body': 'fl'},
            {'op': 'boxcut', 'body': 'fl', 'keep_zabs': [w - tf, w + 10.0], 'keep_xpos': True, 'name': 'Flanges_10mm'},
            {'op': 'combine', 'base': 'out', 'tools': ['fl'], 'oper': 'join', 'keep': False},
            sketch('grom', sec_plane(95), [[{'k': 'circle', 'c': L(95, 22, 0), 'r': 3.0}]]),
            {'op': 'extrude', 'sketch': 'grom', 'dist': 80.0, 'dir': 'sym', 'oper': 'cut', 'name': 'Grommet_hole_D6'}]
    nw, nu, rn = 21.0, 4.5, 1.0
    entry = []
    for sgn in (+1, -1):
        y0 = sgn * (Y_BL + G_COV + tf / 2)
        k = math.sin(math.pi / 4)
        loop = [line(L(y0, -15.0, -nw), L(y0, nu - rn, -nw)),
                {'k': 'arc3', 'p': [L(y0, nu - rn, -nw), L(y0, nu - rn + rn * k, -nw + rn - rn * k), L(y0, nu, -nw + rn)]},
                line(L(y0, nu, -nw + rn), L(y0, nu, nw - rn)),
                {'k': 'arc3', 'p': [L(y0, nu, nw - rn), L(y0, nu - rn + rn * k, nw - rn + rn * k), L(y0, nu - rn, nw)]},
                line(L(y0, nu - rn, nw), L(y0, -15.0, nw)), line(L(y0, -15.0, nw), L(y0, -15.0, -nw))]
        tag = 'thigh' if sgn > 0 else 'shank'
        ops += [sketch('notch_' + tag, sec_plane(y0), [loop]),
                {'op': 'extrude', 'sketch': 'notch_' + tag, 'dist': 6.0, 'dir': 'sym', 'oper': 'cut', 'name': 'M3_tab_notch_%s_42x4.5' % tag}]
        # entry corners: where the notch side meets the cap edge on the pad / webbing
        on_web = any(a - 0.5 <= abs(y0) * sgn <= b + 0.5 for a, b in WEB_Y)
        off = BASE if on_web else T_PAD
        Bp = frame(y0)[0]
        ub = math.sqrt((r(y0) + off) ** 2 - nw ** 2) - Bp[0]   # leg-side cap edge at |v| = 21 lies on the curved pad / webbing
        entry += [L(y0, ub, s * nw) for s in (-1, 1)]
    ops += [{'op': 'fillet', 'r': rn, 'r_try': [1.0, 0.75, 0.5], 'sel': {'type': 'near', 'pts': entry, 'tol': 1.5, 'max_len': 0.8}, 'name': 'Notch_entry_R1', 'optional': True},
            {'op': 'material_keep'}]
    return {'part': NAMES['cov'], 'src': 'V5:cover.04.ipt', 'ops': ops}


def cover(route):
    ops = [{'op': 'suppress_all'}]
    if route == 'a':
        w, cz, Rc, half_len = 34.43, 11.0, 23.43, 122.0
    else:
        w, cz, Rc, half_len = 44.43, 21.0, 23.43, 122.0
    tf = 0.43
    for tag, ww, rc, hl in (('out', w, Rc, half_len), ('in', w - tf, Rc - tf, half_len - tf)):
        if route == 'a':
            ops += [sketch('p_' + tag, 'XY', path(-95, 95), True), sketch('s_' + tag, sec_plane(-95), [cover_sec(-95, ww, cz, rc)]),
                    {'op': 'sweep', 'sketch': 's_' + tag, 'path': 'p_' + tag, 'oper': 'new', 'name': 'Cover_' + tag, 'body': tag}]
            for sgn in (+1, -1):
                y0, y1 = 95.0 * sgn, hl * sgn
                endtop = 6.0 if tag == 'out' else 6.0 - tf
                ops += [sketch('e0%s%d' % (tag, sgn), sec_plane(y0), [cover_sec(y0, ww, cz, rc)]),
                        sketch('e1%s%d' % (tag, sgn), sec_plane(y1), [rect(y1, -40.0, endtop, -ww, ww)]),
                        {'op': 'loft', 'sketches': ['e0%s%d' % (tag, sgn), 'e1%s%d' % (tag, sgn)], 'oper': 'join', 'name': 'Pillow_end_%s%d' % (tag, sgn), 'body': tag}]
        else:
            ops += [sketch('p_' + tag, 'XY', path(-hl, hl), True), sketch('s_' + tag, sec_plane(-hl), [cover_sec(-hl, ww, cz, rc)]),
                    {'op': 'sweep', 'sketch': 's_' + tag, 'path': 'p_' + tag, 'oper': 'new', 'name': 'Cover_' + tag, 'body': tag},
                    {'op': 'fillet', 'r': 10.0 if tag == 'out' else 10.0 - tf, 'sel': {'type': 'near', 'tol': 1.0, 'pts': [L(yy, 22 + rc, 0.0) for yy in (-hl, hl)] + [L(yy, 22 + rc * math.sin(math.pi / 4), sv * (cz + rc * math.sin(math.pi / 4))) for yy in (-hl, hl) for sv in (-1, 1)]}, 'name': 'End_top_R10_' + tag, 'body': tag, 'optional': True}]
    ops.append({'op': 'combine', 'base': 'out', 'tools': ['in'], 'oper': 'cut', 'keep': False})
    st = rin_steps(-140, 140)
    ops += [sketch('seat', 'XY', [stepped_region(0, -140, 140, st, 0.0)]),
            {'op': 'revolve', 'sketch': 'seat', 'angle': 'full', 'oper': 'cut', 'name': 'Sits_on_pad_and_webbing', 'body': 'out'}]
    # sewing flanges: layer 0.43 on the pad/webbing, |z| from (w - 0.43) to (w + 10), x > 0
    fl = rin_steps(-half_len + 0.5, half_len - 0.5)
    ops += [sketch('flange', 'XY', [stepped_layer(0, fl, tf)]),
            {'op': 'revolve', 'sketch': 'flange', 'angle': 'full', 'oper': 'new', 'name': 'Flange_layer', 'body': 'fl'},
            {'op': 'boxcut', 'body': 'fl', 'keep_zabs': [w - tf, w + 10.0], 'keep_xpos': True, 'name': 'Flanges_10mm'},
            {'op': 'combine', 'base': 'out', 'tools': ['fl'], 'oper': 'join', 'keep': False},
            sketch('grom', sec_plane(95), [[{'k': 'circle', 'c': L(95, 22, 0), 'r': 3.0}]]),
            {'op': 'extrude', 'sketch': 'grom', 'dist': 80.0, 'dir': 'sym', 'oper': 'cut', 'name': 'Grommet_hole_D6'},
            {'op': 'material_keep'}]
    return {'part': 'cover.04.ipt' if route == 'a' else 'cover.05.ipt', 'src': 'V3:cover.03.ipt', 'ops': ops}


def stepped_layer(th, steps, t):
    """closed region of thickness t above the stepped surface"""
    lo, hi = [], []
    loop = []
    prev = None
    segs_lo = []
    for a, b, o in steps:
        segs_lo.append({'k': 'spline', 'p': [P(th, y, r(y) + o) for y in ys(a, b, 4.0)]})
    segs_hi = []
    for a, b, o in reversed(steps):
        segs_hi.append({'k': 'spline', 'p': [P(th, y, r(y) + o + t) for y in ys(b, a, 4.0)]})
    for sp in segs_lo:
        if prev is not None:
            loop.append(line(prev, sp['p'][0]))
        loop.append(sp); prev = sp['p'][-1]
    loop.append(line(prev, segs_hi[0]['p'][0])); prev = None
    for sp in segs_hi:
        if prev is not None:
            loop.append(line(prev, sp['p'][0]))
        loop.append(sp); prev = sp['p'][-1]
    loop.append(line(prev, segs_lo[0]['p'][0]))
    return loop


def tube_place(route):
    B, t, n = frame(95.0)
    C = [B[0] + 22 * n[0], B[1] + 22 * n[1], 0.0]
    o = [C[0] - 2 * t[0] + 0.31 * n[0], C[1] - 2 * t[1] + 0.31 * n[1], 0.0]
    return {'file': 'tupe-15.ipt', 'o': o, 'x': n, 'y': [0, 0, -1], 'z': t}


if __name__ == '__main__':
    webs, hooks = web_parts()
    parts = [pad_part()] + webs + [cover8()]          # only the changed parts are rebuilt; the rest are file copies
    same = ['leg-tissue.02.ipt', 'thigh-bone.02.ipt', 'shank-bone.02.ipt', 'hook.05.ipt', 'hook.06.ipt', 'actuator-V8.ipt', 'tupe-15.ipt']
    json.dump({'opt': OPT, 'names': NAMES, 'same': same, 'parts': parts, 'hooks': hooks, 'tube': tube_place('a'),
               'stations': {s[0]: s[1] for s in STATIONS}, 'pad': [PAD_Y0, PAD_Y1],
               'carriers': {tg: free_intervals(*M3_Y[s]) for s, tg in ((1, 'thigh'), (-1, 'shank'))}},
              open(os.path.join(OUT, 'geo_%s.json' % OPT), 'w'), indent=0)
    print(OPT, 'parts', len(parts), 'ops', sum(len(p['ops']) for p in parts), 'carriers', {tg: free_intervals(*M3_Y[s]) for s, tg in ((1, 'thigh'), (-1, 'shank'))})
    for y in (-120, -100, -35, 0, 35, 50, 95, 100, 123):
        print('y %5.0f r %.2f dr %.3f' % (y, r(y), dr(y)))
    for st in STATIONS:
        a = station_angles(st)
        print(st[0], {k: round(math.degrees(v), 2) for k, v in a.items()})
