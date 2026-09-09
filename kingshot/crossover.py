#!/usr/bin/env python3
"""Crossover test: at what march size do I flip from beating Narses to losing to him?

The loss set cannot separate "my output is over-predicted" from "I only ever measure my output
in fights I lost" -- stats and win/lose are confounded.  The crossover can, because a bias that
hits BOTH sides equally cancels out of it: only the differential between the two sides' k moves
the flip point.  And the outcome is a bit, not a number, so the game's report censor (which
withheld a 500-troop march entirely) cannot destroy the measurement.

A hypothesis "my output divided by x" is simulated by multiplying the OPPONENT's D term by x,
which is exactly equivalent in dead = sqrt(n*armyMin) * A / D / 100.

  python3 kingshot/crossover.py
"""
import os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import Side, battle_mc
from reports import NARSES
from allfights import NP

NARSES_TOTAL = 123_570
SIZES = (700, 850, 1000, 1200, 1400, 1600, 2000)

# (label, divide MY output by, divide HIS output by)
HYPOTHESES = [
    ('H0  simulator as-is',       1.00, 1.00),
    ('H1  my-side differential',  1.74, 1.21),   # the measured k split
    ('H2  uniform bias',          1.45, 1.45),   # control: should not move the crossover
]


def split(total, ratio=(.5, .2, .3)):
    i, c = int(total * ratio[0]), int(total * ratio[1])
    return {'inf': i, 'cav': c, 'arch': total - i - c}


def _weaken(panel, factor):
    """Raise this side's defence by `factor`, i.e. divide the opponent's damage output by it."""
    return {t: dict(d, health=factor * (100 + d['health']) - 100) for t, d in panel.items()}


def run(march, my_div=1.0, his_div=1.0, n=200, seed=11):
    rng = random.Random(seed)
    mine, his = _weaken(NP, his_div), _weaken(NARSES, my_div)
    wins, lost = 0, []
    for _ in range(n):
        a = Side('A', mine, split(march), heroes=['Charles', 'Sophia', 'Yang'], role='solo',
                 joiners=[], hero_stats=False, tier=11, tg=8, widget_default=0.0)
        d = Side('D', his, split(NARSES_TOTAL), heroes=['Long Fei', 'Jabel', 'Rosa'],
                 role='garrison', joiners=[], hero_stats=False, tier=10, tg=2, widget_default=0.0)
        r = battle_mc(a, d, rng)
        wins += r['winner'] == 'A'
        lost.append(r['a_lost'])
    return wins / n, statistics.mean(lost)


def main():
    for title, idx in (('win probability', 0), ('my losses, of the march', 1)):
        print(f"\n{title:28}" + ''.join(f"{s:>8,}" for s in SIZES))
        for label, my_div, his_div in HYPOTHESES:
            row = [run(s, my_div, his_div)[idx] for s in SIZES]
            fmt = (lambda v: f"{v:>7.0%} ") if idx == 0 else (lambda v: f"{v:>7,.0f} ")
            print(f"{label:28}" + ''.join(fmt(v) for v in row))
    print("\nH2 tracking H0 is the point: an equal bias on both sides cancels out of the")
    print("crossover, so a shift can only come from the asymmetry between them.")


if __name__ == '__main__':
    main()
