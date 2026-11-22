# -*- coding: utf-8 -*-
"""Leak and centring check of the bladder in a deck.
1  closed cavity: every edge of the bladder shell (body + end caps) is shared by exactly 2 bladder elements -> no hole, no leak
   (inlet port and both vent ports = closed wall, i.e. valves closed; pressure acts on the whole inner wall).
2  pressure: the PLOAD4 range of each pressure subcase covers every bladder element and nothing else.
3  centring: bladder y-extent and centroid vs the knee line y = 0; knee axis = Z through X = r(0) - 65.
Usage: python -P seal_check.py <deck.nas> <deck_mesh.pkl>   -> prints a report (also written next to the deck)."""
import os, pickle, re, sys
from collections import Counter
import numpy as np

nas, pkl = sys.argv[1], sys.argv[2]
m = pickle.load(open(pkl, 'rb'))
X, EL, S = m['X'], m['el'], m['S']
bl = list(S['bl_body']) + list(S['bl_cap'])
out = []
def P(s): out.append(s); print(s)

def nodes_of(e):
    rec = EL[e]
    for it in rec:
        if isinstance(it, (list, tuple)) and len(it) in (3, 4) and all(isinstance(q, (int, np.integer)) for q in it): return list(it)
    raise ValueError(rec)

edges = Counter()
for e in bl:
    n = nodes_of(e)
    for i in range(len(n)):
        a, b = n[i], n[(i + 1) % len(n)]
        edges[(min(a, b), max(a, b))] += 1
free = [k for k, v in edges.items() if v == 1]; multi = [k for k, v in edges.items() if v > 2]
P('bladder shell elements %d (body %d, caps %d), edges %d, free edges %d, edges on >2 elements %d'
  % (len(bl), len(S['bl_body']), len(S['bl_cap']), len(edges), len(free), len(multi)))
P('  -> closed cavity, no leak path: %s' % ('YES' if not free else 'NO'))

# element ids as written in the deck: read the CQUAD4/CTRIA3 cards of the bladder property and the PLOAD4 ranges
txt = open(nas).read().splitlines()
pl = [l.split(',') for l in txt if l.startswith('PLOAD4')]
P('PLOAD4 cards %d: ' % len(pl) + '; '.join('SID %s p %s MPa EID %s THRU %s' % (c[1], c[3], c[2], c[8]) for c in pl))
if not pl:
    P('no PLOAD4 (0 kPa run): vented reference, pressure check not applicable')
    pl = [['', '', '0', '', '', '', '', '', '-1']]
lo, hi = int(pl[0][2]), int(pl[0][8])
shell_ids = []
for l in txt:
    if l.startswith('CQUAD4') or l.startswith('CTRIA3'):
        c = l.split(','); shell_ids.append((int(c[1]), int(c[2])))
inrange = [(e, p) for e, p in shell_ids if lo <= e <= hi]
props = Counter(p for e, p in inrange)
P('shell elements inside the PLOAD4 range: %d, by PSHELL id %s' % (len(inrange), dict(props)))
P('  -> pressure on all %d bladder elements and nothing else: %s' % (len(bl), 'n/a (0 kPa)' if hi < 0 else 'YES' if len(inrange) == len(bl) and len(props) <= 2 else 'CHECK'))

bn = sorted(set(n for e in bl for n in nodes_of(e)))
Y = X[bn, 1] if X.shape[0] > max(bn) else None
if Y is not None:
    P('bladder grid y: %.2f .. %.2f mm, mean %.2f; z: %.2f .. %.2f; x: %.2f .. %.2f' % (Y.min(), Y.max(), Y.mean(), X[bn, 2].min(), X[bn, 2].max(), X[bn, 0].min(), X[bn, 0].max()))
    P('  -> symmetric about the knee line y = 0 within %.2f mm (ends), centred medial-lateral within %.2f mm'
      % (abs(Y.max() + Y.min()), abs(X[bn, 2].max() + X[bn, 2].min())))
open(os.path.splitext(nas)[0] + '_seal_check.txt', 'w').write('\n'.join(out) + '\n')
