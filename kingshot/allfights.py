#!/usr/bin/env python3
"""Every fight in reports.py where one side's losses are uncensored, scored in one place.

k = simulated / observed on the UNCENSORED quantity: my own losses when I won, the enemy's when
I was wiped.  In both cases that is the LOSING side's total damage output, which is the thing the
model has been over-predicting.

  python3 kingshot/allfights.py
"""
import os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import Side, battle_mc
from reports import (TERRY_ATTACK_PANEL, TERRY_ATTACK_ENEMY, OPP2, OPP2_TROOPS, OPP2_TIERS,
                     OPP2_PANEL, SOLO_PANEL, NARSES, NARSES_TROOPS)

NP = {'inf': dict(attack=2379.0, defense=1941.2, lethality=2183.4, health=1801.1),
      'cav': dict(attack=2220.5, defense=1809.7, lethality=2089.2, health=1726.1),
      'arch': dict(attack=2223.8, defense=1809.4, lethality=2111.2, health=1737.6)}
TE = {'inf': 113_467, 'cav': 45_386, 'arch': 68_079}
TE20 = {'inf': 94_555, 'cav': 37_822, 'arch': 56_733}

# (label, my panel, my troops, my role, enemy panel, enemy troops, enemy tier, enemy heroes,
#  enemy Truegold level, enemy heroes, which side's losses are uncensored, observed)
FIGHTS = [
    ('Narses pure-arch 5k', NP, {'inf': 2500, 'cav': 1000, 'arch': 1500}, 'solo',
     NARSES, {'inf': 0, 'cav': 0, 'arch': 116_040}, 10, 2, ['Long Fei', 'Jabel', 'Rosa'], 'me', 72),
    ('Narses mixed atk 10k', SOLO_PANEL, {'inf': 5000, 'cav': 2000, 'arch': 3000}, 'solo',
     NARSES, NARSES_TROOPS, 10, 2, ['Long Fei', 'Jabel', 'Rosa'], 'me', 239),
    ('Narses mixed def 5k', SOLO_PANEL, {'inf': 2500, 'cav': 1000, 'arch': 1500}, 'garrison',
     NARSES, NARSES_TROOPS, 10, 2, ['Long Fei', 'Jabel', 'Rosa'], 'me', 292),
    ('Narses inf+arch 1k', NP, {'inf': 500, 'cav': 200, 'arch': 300}, 'solo',
     NARSES, {'inf': 61_785, 'cav': 0, 'arch': 61_785}, 10, 2, ['Long Fei', 'Jabel', 'Rosa'], 'me', 397),
    ('Terry 10k all archer', TERRY_ATTACK_PANEL, {'inf': 0, 'cav': 0, 'arch': 10_000}, 'solo',
     TERRY_ATTACK_ENEMY, TE, 11, 8, ['Triton', 'Ava', 'Yang'], 'them', 1_808),
    ('Terry 10k all inf', TERRY_ATTACK_PANEL, {'inf': 10_000, 'cav': 0, 'arch': 0}, 'solo',
     TERRY_ATTACK_ENEMY, TE, 11, 8, ['Triton', 'Ava', 'Yang'], 'them', 937),
    ('opponent-2 10k mixed', OPP2_PANEL, {'inf': 5000, 'cav': 2000, 'arch': 3000}, 'solo',
     OPP2, OPP2_TROOPS, OPP2_TIERS, 8, ['Triton', 'Ava', 'Wee & Woo'], 'them', 15_224),
    ('Terry 20k mixed', TERRY_ATTACK_PANEL, {'inf': 10_000, 'cav': 4000, 'arch': 6000}, 'solo',
     TERRY_ATTACK_ENEMY, TE20, 11, 8, ['Triton', 'Ava', 'Yang'], 'them', 22_570),
    # Recovered from the defender's mail after the attacker's copy was censored.  The first fight
    # in the set that measures MY output against a WEAK opponent, and the only one where the
    # model UNDER-predicts.  See rounds.py: its 152 measured rounds against the sim's 73 are what
    # show that a k on totals is a ratio of two cancelling errors, not one side's output.
    ('Narses 500 solo', NP, {'inf': 250, 'cav': 100, 'arch': 150}, 'solo',
     NARSES, {'inf': 61_785, 'cav': 24_714, 'arch': 37_071}, 10, 2,
     ['Long Fei', 'Jabel', 'Rosa'], 'them', 48_561),
]


def score(n=200, seed=1234):
    rng = random.Random(seed)
    out = []
    for lbl, mp, mt, mr, ep, et, tier, etg, eh, side, obs in FIGHTS:
        vals = []
        for _ in range(n):
            a = Side('A', mp, dict(mt), heroes=['Charles', 'Sophia', 'Yang'], role=mr, joiners=[],
                     hero_stats=False, tier=11, tg=8, widget_default=0.0)
            d = Side('D', ep, dict(et), heroes=eh, role=('solo' if mr == 'garrison' else 'garrison'),
                     joiners=[], hero_stats=False, tier=tier, tg=etg, widget_default=0.0)
            if mr == 'garrison':
                a, d = d, a
                r = battle_mc(a, d, rng)
                vals.append(r['d_lost'] if side == 'me' else r['a_lost'])
            else:
                r = battle_mc(a, d, rng)
                vals.append(r['a_lost'] if side == 'me' else r['d_lost'])
        out.append((lbl, obs, statistics.mean(vals)))
    return out


if __name__ == '__main__':
    print(f'{"fight":24s}{"observed":>10s}{"sim":>10s}{"k":>7s}')
    ks = []
    for lbl, obs, sim in score():
        ks.append(sim / obs)
        print(f'  {lbl:22s}{obs:10,}{sim:10,.0f}{sim/obs:7.2f}')
    print(f'\n  mean k {statistics.mean(ks):.2f}   spread {min(ks):.2f}-{max(ks):.2f}'
          f'   rms log err {statistics.mean([abs(__import__("math").log(k)) for k in ks]):.3f}')
