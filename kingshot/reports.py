#!/usr/bin/env python3
"""Live battle reports used to calibrate and validate the simulator.

All three were fought on 2026-09-08 by [PRO]Belisarius (X:480 Y:684) against the same
target, [ORM]N2DBLG (X:480 Y:683), within minutes of each other, with the same garrison
lineup (Charles / Sophia / Vivian) and 10,000 troops sent by the leader every time.  That
makes them a clean controlled experiment: exactly one variable changes between any pair.

The per-player "kills" field tracks the defender's *Injured* bucket; the Lightly Injured
bucket is a fixed 1.855x of it in every report from both sides, so total defender
casualties = kills * 2.855.  That is how the 50/20/30 total is reconstructed (its overview
screen was not captured).

  python3 kingshot/reports.py      # replay all three through the simulator
"""
import random, statistics, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sim import Side, battle_mc, score

WOUND_SCALE = 2.855          # total casualties per unit of the "kills"/Injured field
SENT = 10_000                # troops the leader sent in every one of the three

# Stat Bonuses panels, read straight off the reports (these are in-battle totals: city buffs +
# hero expedition stats + gear + widgets, so they are fed in with hero_stats=False).
ME_SOPHIA = {'inf': dict(attack=1617.3, defense=1594.3, lethality=2088.3, health=1799.0),
             'cav': dict(attack=1507.3, defense=1484.7, lethality=1996.0, health=1725.4),
             'arch': dict(attack=1509.6, defense=1484.5, lethality=2017.2, health=1736.7)}
ME_AVA    = {'inf': dict(attack=1617.3, defense=1594.3, lethality=2373.7, health=1799.0),
             'cav': dict(attack=1599.0, defense=1576.5, lethality=2304.5, health=1752.4),
             'arch': dict(attack=1509.6, defense=1484.5, lethality=2293.4, health=1736.7)}
ENEMY     = {'inf': dict(attack=2225.7, defense=2496.3, lethality=2165.5, health=2165.5),
             'cav': dict(attack=1937.6, defense=2145.1, lethality=1880.2, health=1660.2),
             'arch': dict(attack=1921.1, defense=2134.1, lethality=2039.2, health=1796.7)}
GARRISON = ['Charles', 'Sophia', 'Vivian']

# (label, cavalry hero, my stat panel, my troops, enemy troops, reported "kills")
REPORTS = [
    ('Sophia 60/40/0', 'Sophia', ME_SOPHIA, {'inf': 6006, 'cav': 4000, 'arch': 1},
     {'inf': 6002, 'cav': 4000, 'arch': 0}, 1433),
    ('Ava 60/40/0',    'Ava',    ME_AVA,    {'inf': 6006, 'cav': 4000, 'arch': 0},
     {'inf': 6004, 'cav': 4000, 'arch': 0},  894),
    ('Ava 50/20/30',   'Ava',    ME_AVA,    {'inf': 5006, 'cav': 2000, 'arch': 3000},
     {'inf': 6004, 'cav': 4000, 'arch': 0}, 1573),
]

# Stat-panel predictions the calibration in sim.py has to reproduce (see the fit in sim.py).
# Every one of the 24 values lands within 12 points of ~2000, i.e. under 0.6%.
PANEL_TOLERANCE = 12.0


def observed(kills):
    """Kill ratio implied by a report: defender casualties / my casualties (I was wiped each time)."""
    return kills * WOUND_SCALE / SENT


def replay(n=400, seed=31):
    rng = random.Random(seed)
    rows = []
    for label, cav, mine, my_t, en_t, kills in REPORTS:
        ks = []
        for _ in range(n):
            a = Side('A', mine, dict(my_t), heroes=['Charles', cav, 'Yang'], role='rally',
                     joiners=['Chenko'] * 4, hero_stats=False)
            d = Side('D', ENEMY, dict(en_t), heroes=GARRISON, role='garrison', hero_stats=False)
            ks.append(score(battle_mc(a, d, rng), 'A'))
        rows.append((label, observed(kills), statistics.mean(ks)))
    return rows


if __name__ == '__main__':
    print(f'{"report":18s} {"observed":>9s} {"sim":>8s} {"sim/obs":>9s}')
    for label, obs, sim in replay():
        print(f'  {label:16s} {obs:9.3f} {sim:8.3f} {sim/obs:9.2f}')
    print('\nControlled comparisons (same target, same 10,000 troops sent):')
    k = {r[0]: r[5] for r in REPORTS}
    print(f'  hero swap at 60/40/0 : Sophia / Ava = {k["Sophia 60/40/0"]/k["Ava 60/40/0"]:.2f}x')
    print(f'  ratio swap with Ava  : 50/20/30 / 60/40/0 = {k["Ava 50/20/30"]/k["Ava 60/40/0"]:.2f}x')
    print(f'  best observed        : Ava 50/20/30 beats Sophia 60/40/0 by '
          f'{k["Ava 50/20/30"]/k["Sophia 60/40/0"]:.2f}x')
    print('\nOpen: Sophia at 50/20/30 is untested.  The two effects should NOT simply multiply --')
    print('Terror Deathblow is a cavalry-damage skill, so halving cavalry halves what it scales.')
