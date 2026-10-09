#!/usr/bin/env python3
"""Governor gear plan, valued per stat point rather than by an equal-weight shortcut.

Each gear star adds +2.75 (T4) or +3 (T5) to attack AND defense of its piece's troop type; the
6-piece set at a tier adds attack to every type.  Per-point values are least-squares slopes of
the simulated kill-ratio gain (three archer-inclusive rally+garrison scenarios, deterministic
engine) over +2.75..+22 points, because one star can tip a 25-round fight by a whole round.  The
Monte Carlo engine cannot separate these plans: at 1.9M-vs-1.9M parity the winner flips between
runs and luck swamps a 1% difference.

Result (2026-10-08, satin 2.64M / threads 31.2k / AV 4,908): an infantry star is worth ~2.9x a
cavalry star and ~2.2x an archer star, almost entirely through infantry DEFENSE (the front
line).  Best affordable: both infantry pieces to T4*3 plus one archer star, ~2.25%; finishing
the cavalry pair to T4 for the 6-piece set, ~1.20% for 4,020 AV.  This reverses the earlier
"cavalry pair first" advice, which came from the equal-weight shortcut.

  python3 kingshot/gear_plan.py
"""
import copy, itertools, math, os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gear
from gear import PIECES, ORDER, TABLE, cost_of, stats_for, set_bonus
from sim import Side, USER_STATS, battle, battle_mc, ratio_troops, score, ATTACK_JOINERS, DEFENSE_JOINERS
BUDGET = gear.BUDGET
R = gear.RALLY; enemy = gear.enemy
SCEN = [(['Charles','Ava','Yang'], (45,30,25), ['Charles','Sophia','Wee & Woo'], (60,15,25)),
        (['Charles','Sophia','Yang'], (50,20,30), ['Charles','Sophia','Wee & Woo'], (60,15,25)),
        (['Charles','Sophia','Yang'], (40,20,40), ['Charles','Sophia','Wee & Woo'], (50,20,30))]
def att(my, h, ratio, fn=battle, rng=None, n=1):
    v = []
    for dl in gear.DEF_PANEL:
        for _ in range(n):
            args = (Side('A', my, ratio_troops(R, *ratio), heroes=h, role='rally', joiners=ATTACK_JOINERS),
                    Side('D', enemy, ratio_troops(R, 60, 15, 25), heroes=dl, role='garrison', joiners=DEFENSE_JOINERS))
            v.append(math.log(score(fn(*args, rng) if rng else fn(*args), 'A')))
    return math.exp(statistics.mean(v))
def dfn(my, h, ratio, fn=battle, rng=None, n=1):
    v = []
    for al in gear.ATT_PANEL:
        ar = (55, 45, 0) if 'Sophia' in al else (50, 20, 30)
        for _ in range(n):
            args = (Side('A', enemy, ratio_troops(R, *ar), heroes=al, role='rally', joiners=ATTACK_JOINERS),
                    Side('D', my, ratio_troops(R, *ratio), heroes=h, role='garrison', joiners=DEFENSE_JOINERS))
            v.append(math.log(score(fn(*args, rng) if rng else fn(*args), 'D')))
    return math.exp(statistics.mean(v))
def value(s, fn=battle, n=1, seed=5):
    tot = []
    for ah, ar, dh, dr in SCEN:
        rng = random.Random(seed) if fn is battle_mc else None
        ba = BASE_A[(tuple(ah), ar, fn.__name__)]; bd = BASE_D[(tuple(dh), dr, fn.__name__)]
        tot.append(100*(att(s, ah, ar, fn, rng, n)/ba - 1) + 100*(dfn(s, dh, dr, fn, random.Random(seed) if rng else None, n)/bd - 1))
    return statistics.mean(tot), tot
BASE_A, BASE_D = {}, {}
def bases(fn, n=1, seed=5):
    for ah, ar, dh, dr in SCEN:
        BASE_A[(tuple(ah), ar, fn.__name__)] = att(USER_STATS, ah, ar, fn, random.Random(seed) if fn is battle_mc else None, n)
        BASE_D[(tuple(dh), dr, fn.__name__)] = dfn(USER_STATS, dh, dr, fn, random.Random(seed) if fn is battle_mc else None, n)
bases(battle)
def slope(mod):
    xs, ys = [], []
    for k in range(1, 9):
        s = copy.deepcopy(USER_STATS); mod(s, 2.75 * k)
        xs.append(2.75 * k); ys.append(value(s)[0])
    return sum(x*y for x, y in zip(xs, ys)) / sum(x*x for x in xs)
SL = {}
for t in ('inf', 'cav', 'arch'):
    def m(s, x, t=t): s[t]['attack'] += x; s[t]['defense'] += x
    SL[t] = slope(m)
    def ma(s, x, t=t): s[t]['attack'] += x
    def md(s, x, t=t): s[t]['defense'] += x
    print(f'{t:4s} gear point (attack+defense) {SL[t]:.4f}%   attack only {slope(ma):.4f}%   defense only {slope(md):.4f}%')
def mall(s, x):
    for t in ('inf','cav','arch'): s[t]['attack'] += x
def dall(s, x):
    for t in ('inf','cav','arch'): s[t]['defense'] += x
SL['set_atk'] = slope(mall); SL['set_def'] = slope(dall)
print(f'set bonus: +1 attack on all types {SL["set_atk"]:.4f}%   +1 defense on all types {SL["set_def"]:.4f}%')
cur = [p[1] for p in PIECES]
def lin(levels):
    v = 0.0
    for (t, old), new in zip(PIECES, levels):
        v += SL[t] * (TABLE[new][3] - TABLE[old][3])
    d0, a0 = set_bonus(cur); d1, a1 = set_bonus(levels)
    return v + SL['set_atk'] * (a1 - a0) + SL['set_def'] * (d1 - d0)
res = []
names = ['helm', 'pants', 'crown', 'necklace', 'ring', 'mace']
for steps in itertools.product(*[range(0, min(6, len(ORDER) - ORDER.index(p[1]))) for p in PIECES]):
    levels = [ORDER[ORDER.index(p[1]) + k] for p, k in zip(PIECES, steps)]
    c = cost_of(levels)
    if any(c[k] > BUDGET[k] for k in BUDGET): continue
    res.append((lin(levels), steps, levels, c))
res.sort(key=lambda r: -r[0])
print('\nbest affordable plans, linearised:')
for v, steps, levels, c in res[:8]:
    print(f"  {v:5.2f}%  AV {c['av']:,}  {', '.join(f'{n} {l[0][4:]}*{l[1]}' for n, k, l in zip(names, steps, levels) if k)}")
print('\nper star, cheapest next step on each piece (gain per 100 AV):')
for (t, old), n in zip(PIECES, names):
    nxt = ORDER[ORDER.index(old) + 1]; d = TABLE[nxt][3] - TABLE[old][3]
    print(f'  {n:9s} {old[0][4:]}*{old[1]} -> {nxt[0][4:]}*{nxt[1]}: +{d:.2f} pts  {SL[t]*d:.3f}%  ({SL[t]*d/TABLE[nxt][2]*100:.3f}% per 100 AV)')
cav = [ORDER[ORDER.index(p[1]) + (3 if p[0] == 'cav' else 0)] for p in PIECES]
c = cost_of(cav)
print(f"\ncav pair to T4*0 (6pc T4 set): {lin(cav):.3f}%  of which set bonus {SL['set_atk']*3.5:.3f}%   AV {c['av']:,}")
