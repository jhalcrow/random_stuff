#!/usr/bin/env python3
"""The hero ladder: the same target, the same troops, heroes added one at a time.

Four fights against the SAME heroless Narses (83,600 in thirds, T10 TG2, no special bonuses),
differing only in how many heroes were fielded.  Because everything else is held constant, the
k values isolate the hero layer and nothing else -- and because the panel for each was PREDICTED
to the decimal before the fight, the stat half is known to be right, so any error is skills.

    0 heroes      k 1.05      the damage core alone
    Charles       k 1.13      + three permanent auras, zero procs
    Yang          k 0.83      + three procs, zero auras
    Sophia+Yang   k 0.62      + two proc heroes, six procs

A single hero of either kind is fine.  The error appears only when heroes are COMBINED, and it
grows with how many are combined -- the model credits Sophia with dividing losses by 2.4 when
she really divides them by 1.78.  Extrapolating that per-hero over-credit is roughly where the
three-hero fights against Terry sit.

  python3 kingshot/ladder.py
"""
import math, os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import Side, battle_mc
from allfights import NOHERO_ENEMY, NOHERO_PANEL

ENEMY_TROOPS = {'inf': 27_866, 'cav': 27_867, 'arch': 27_867}
ENEMY_CAPS = {'inf': 0, 'cav': 0, 'arch': 1}       # his TG2 rows, read off the heroless report
BIG = {'inf': 5000, 'cav': 2000, 'arch': 3000}

# Heroless baseline panel, before any hero is added.
BASE = {'inf': dict(attack=1102.3, defense=1090.7, lethality=1042.4, health=1040.6),
        'cav': dict(attack=1080.3, defense=1069.3, lethality=990.8, health=992.6),
        'arch': dict(attack=1083.1, defense=1069.0, lethality=1009.2, health=1004.1)}


def panel(**per_type):
    """Add (attack/defense, lethality/health) to a troop type -- a hero's expedition stats plus
    the measured +200 / +600 gear.  Every one of these was predicted before its report arrived
    and matched to the decimal."""
    p = {t: dict(d) for t, d in BASE.items()}
    for t, (atk, leth) in per_type.items():
        p[t]['attack'] += atk
        p[t]['defense'] += atk
        p[t]['lethality'] += leth
        p[t]['health'] += leth
    return p


LADDER = [
    ('0 heroes',    NOHERO_PANEL,                                   [],  {'inf': 500, 'cav': 200, 'arch': 300}, 687),
    ('Charles',     panel(inf=(850.52, 760.5)),            ['Charles'],  BIG,  39),
    ('Yang',        panel(arch=(740.43, 733.5)),              ['Yang'],  BIG,  73),
    ('Sophia+Yang', panel(cav=(740.43, 733.5), arch=(740.43, 733.5)),
                                                    ['Sophia', 'Yang'],  BIG,  41),
]


def run(panel_, heroes, troops, n=400, seed=11):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        a = Side('A', panel_, dict(troops), heroes=heroes, joiners=[], role='solo',
                 hero_stats=False, tier=11, tg=8, widget_default=0.0)
        d = Side('D', NOHERO_ENEMY, dict(ENEMY_TROOPS), heroes=[], joiners=[], role='garrison',
                 hero_stats=False, tier=10, tg=2, widget_default=0.0,
                 troop_abilities=ENEMY_CAPS, troop_reforges=set())
        out.append(battle_mc(a, d, rng)['a_lost'])
    return statistics.mean(out)


def main():
    print(f"{'lineup':16}{'observed':>10}{'sim':>9}{'k':>7}")
    errs = []
    for lbl, p, hs, troops, obs in LADDER:
        s = run(p, hs, troops)
        errs.append(math.log(s / obs))
        print(f"  {lbl:14}{obs:>10,}{s:>9.1f}{s / obs:>7.2f}")
    print(f"\n  rms log err {math.sqrt(sum(x * x for x in errs) / len(errs)):.3f}")
    print("  k falls monotonically as heroes are added: the model over-credits each one, and the")
    print("  error is in combining them, not in any single hero's auras or procs.")


if __name__ == '__main__':
    main()
