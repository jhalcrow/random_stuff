#!/usr/bin/env python3
"""Which troop type's governor charm to level next, simulated rather than assumed.

A charm level gives +4 lethality AND +4 health to one troop type.  An earlier answer valued that
with a shortcut that treats every panel point as equally useful (1000 / (100 + panel)), which
favoured whichever type had the lowest panel and the cheapest next level.  The simulator says the
points are not equal: infantry HEALTH keeps the front line standing, so every type keeps firing
longer, while infantry lethality is worth almost nothing.

Method: rally and garrison kill ratios (gear.py's scenarios, archer-inclusive compositions plus
the current Elo-best lineups), each type raised by +1..+6 charm levels, gain per level taken as
a least-squares slope -- a single +4 step can tip a 25-round fight by a whole round, so one-step
differences are lumpy.

Result (2026-10-08, charms inf 16 / cav 15 / arch 15): infantry wins in all three scenarios by
1.3-2.4x per level, and still wins per design despite costing 1,500 designs against 1,320.
Archer vs cavalry is close and flips between scenarios.

  python3 kingshot/charm_value.py
"""
import copy, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gear
from sim import Side, USER_STATS, TYPES, battle, ratio_troops, score, ATTACK_JOINERS, DEFENSE_JOINERS
R = gear.RALLY
enemy = gear.enemy
ATT_PANEL = gear.ATT_PANEL
DEF_PANEL = gear.DEF_PANEL
def att(my, heroes, ratio):
    return statistics.geometric_mean([score(battle(
        Side('A', my, ratio_troops(R, *ratio), heroes=heroes, role='rally', joiners=ATTACK_JOINERS),
        Side('D', enemy, ratio_troops(R, 60, 15, 25), heroes=dl, role='garrison', joiners=DEFENSE_JOINERS)), 'A') for dl in DEF_PANEL])
def dfn(my, heroes, ratio):
    out = []
    for al in ATT_PANEL:
        ar = (55, 45, 0) if 'Sophia' in al else (50, 20, 30)
        out.append(score(battle(Side('A', enemy, ratio_troops(R, *ar), heroes=al, role='rally', joiners=ATTACK_JOINERS),
            Side('D', my, ratio_troops(R, *ratio), heroes=heroes, role='garrison', joiners=DEFENSE_JOINERS)), 'D'))
    return statistics.geometric_mean(out)
SCEN = [
    ('Elo-best: rally Charles/Ava/Yang 45/30/25, garrison Charles/Sophia/W&W 60/15/25',
     (['Charles','Ava','Yang'], (45,30,25)), (['Charles','Sophia','Wee & Woo'], (60,15,25))),
    ('research-plan A: rally C/S/Y 50/20/30, garrison C/S/W&W 60/15/25',
     (['Charles','Sophia','Yang'], (50,20,30)), (['Charles','Sophia','Wee & Woo'], (60,15,25))),
    ('research-plan B: rally C/S/Y 40/20/40, garrison C/S/W&W 50/20/30',
     (['Charles','Sophia','Yang'], (40,20,40)), (['Charles','Sophia','Wee & Woo'], (50,20,30))),
]
COST = {'inf': (780, 1500), 'cav': (730, 1320), 'arch': (730, 1320)}
print('\n\nSLOPE: least-squares gain per charm level over +1..+6 levels (smooths the round-count steps)')
for name, (ah, ar), (dh, dr) in SCEN:
    ba, bd = att(USER_STATS, ah, ar), dfn(USER_STATS, dh, dr)
    print(f'\n{name}')
    for t in TYPES:
        for part, keys in (('both', ('lethality','health')), ('leth only', ('lethality',)), ('health only', ('health',))):
            xs, ys = [], []
            for lv in range(1, 7):
                s = copy.deepcopy(USER_STATS)
                for k in keys: s[t][k] += 4*lv
                xs.append(lv); ys.append(100*(att(s, ah, ar)/ba-1) + 100*(dfn(s, dh, dr)/bd-1))
            slope = sum(x*y for x, y in zip(xs, ys)) / sum(x*x for x in xs)
            extra = f'   per 1k designs {slope/COST[t][1]*1000:.3f}' if part == 'both' else ''
            print(f'  {t:4s} {part:12s} {slope:+.3f}% per level{extra}')
