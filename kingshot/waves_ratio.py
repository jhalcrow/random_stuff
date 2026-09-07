#!/usr/bin/env python3
"""Ratio sweep for one garrison lineup under consecutive rallies with no refill.

  RALLY_SIZE=1900000 ATT_SCALES=0.9 python3 kingshot/waves_ratio.py [N] [garrison_multiple]
"""
import os, random, sys, statistics
from sim import Side, USER_STATS, MARCH, TYPES, battle_mc, ratio_troops, ATTACK_JOINERS, DEFENSE_JOINERS

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
GAR_MULT = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
RALLY = int(os.environ.get('RALLY_SIZE', MARCH))
SCALE = float(os.environ.get('ATT_SCALES', '0.9').split(',')[0])
GAR = ['Charles', 'Sophia', 'Wee & Woo']
ATTACKERS = [(['Charles', 'Sophia', 'Marlin'], (55, 45, 0)), (['Charles', 'Sophia', 'Yang'], (60, 40, 0)), (['Charles', 'Ava', 'Yang'], (45, 30, 25))]
WAVES = 3
rng = random.Random(11)
stats = {t: {k: v * SCALE for k, v in USER_STATS[t].items()} for t in TYPES}
GRID = [(i, c, 100 - i - c) for i in range(0, 101, 10) for c in range(0, 101 - i, 10)]

rows = []
for ratio in GRID:
    held = [0, 0, 0]; left1 = []; left_end = []; killed = []
    for heroes, aratio in ATTACKERS:
        for _ in range(N):
            troops = ratio_troops(int(RALLY * GAR_MULT), *ratio)
            k = 0; w = 0
            while w < WAVES and sum(troops.values()) > 0:
                a = Side('A', stats, ratio_troops(RALLY, *aratio), heroes=heroes, role='rally', joiners=ATTACK_JOINERS)
                d = Side('D', USER_STATS, dict(troops), heroes=GAR, role='garrison', joiners=DEFENSE_JOINERS)
                r = battle_mc(a, d, rng)
                k += r['a_lost']
                troops = {t: int(v) for t, v in r['d_left'].items()}
                if sum(troops.values()) == 0:
                    break
                w += 1
                if w == 1:
                    left1.append(sum(troops.values()))
            for i in range(w):
                held[i] += 1
            killed.append(k); left_end.append(sum(troops.values()))
    tot = N * len(ATTACKERS)
    rows.append((ratio, [h / tot for h in held], statistics.mean(left1) if left1 else 0, statistics.mean(left_end), statistics.mean(killed)))

print(f'garrison {GAR} at {int(RALLY*GAR_MULT):,} vs {RALLY:,} rallies at x{SCALE} stats, {N} runs x {len(ATTACKERS)} attackers per ratio\n')
for key, label in ((lambda r: r[2], 'garrison troops left after ONE hit (single-battle optimum)'),
                   (lambda r: r[1][1], 'probability of holding TWO hits'),
                   (lambda r: r[1][2], 'probability of holding THREE hits'),
                   (lambda r: r[4], 'attacker troops killed over the sequence')):
    print(f'--- best ratios by {label} ---')
    for r in sorted(rows, key=key, reverse=True)[:8]:
        print(f'  {r[0][0]:3d}/{r[0][1]:3d}/{r[0][2]:3d}   hold1 {r[1][0]*100:5.1f}%  hold2 {r[1][1]*100:5.1f}%  hold3 {r[1][2]*100:5.1f}%   left after 1: {r[2]:10,.0f}   killed {r[4]:10,.0f}')
    print()
