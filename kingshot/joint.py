#!/usr/bin/env python3
"""Joint search: for the top-N trios from the fixed-ratio ranking, optimise the troop ratio on a
coarse grid and report the best (trio, ratio) pairs for rally attack and garrison defense.

  PROC_SCALE=0.75 python3 kingshot/joint.py [N]
"""
import itertools, sys
from run import eval_attack, eval_defense, summarize, TRIOS

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
GRID = [(i, c, 100 - i - c) for i in range(0, 101, 10) for c in range(0, 101 - i, 10)]


def joint(evalfn, base_ratio, label):
    rows = []
    for trio in TRIOS:
        g, w = summarize(evalfn(trio, ratio=base_ratio))
        rows.append((g, trio))
    rows.sort(reverse=True)
    best = []
    for g0, trio in rows[:N]:
        for r in GRID:
            g, w = summarize(evalfn(trio, ratio=r))
            best.append((g, w, trio, r))
    best.sort(reverse=True)
    print(f'\n=== {label}: best trio + ratio (inf/cav/arch), top {N} trios x {len(GRID)} ratios ===')
    seen = set()
    for g, w, trio, r in best:
        if trio in seen:
            continue
        seen.add(trio)
        print(f'  {g:6.3f}  wins {w}/4  {r[0]}/{r[1]}/{r[2]:<3d} {", ".join(trio)}')
        if len(seen) >= 12:
            break


joint(eval_attack, (50, 20, 30), 'CASTLE ATTACK rally')
joint(eval_defense, (60, 15, 25), 'GARRISON DEFENSE')
