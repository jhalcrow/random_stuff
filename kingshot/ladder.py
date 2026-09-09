#!/usr/bin/env python3
"""The hero ladder: the same target, the same troops, heroes added one at a time.

Five fights against the SAME heroless Narses (83,600 in thirds, T10 TG2, no special bonuses),
differing only in how many heroes were fielded.  Because everything else is held constant, the
k values isolate the hero layer and nothing else -- and because the panel for each was PREDICTED
to the decimal before the fight, the stat half is known to be right, so any error is skills.

    0 heroes      k 1.08      the damage core alone
    Charles       k 0.96      + three permanent auras, zero procs
    Yang          k 0.89      + three procs, zero auras
    Sophia+Yang   k 0.70      + a second PROC hero  (six procs)
    Charles+Yang  k 0.60      + a second AURA hero  (still only three procs)

WHAT THE LADDER LOOKS LIKE IT SAYS, AND WHY THAT READING IS WRONG.  k falls monotonically with
hero count, and Charles+Yang -- which adds a hero WITHOUT adding a proc -- is the worst rung, so
for a while this read as "the model over-credits each additional hero, and it is about stacking
heroes rather than about procs."  The round-count columns kill that reading.  On both rungs that
Yang's periodic-4 Avalanche can date, k is almost exactly the SQUARE ROOT of the round ratio:

    Yang           rounds 4.7 sim vs 6 observed    ratio 0.82   sqrt 0.91   k 0.89
    Charles+Yang   rounds 21  sim vs 52 observed   ratio 0.39   sqrt 0.63   k 0.60

So the loss error is not about how much damage my troops absorb per round.  It is that the
simulator wipes Narses far too fast, and my troops are therefore exposed for a fraction of the
rounds they really faced.  A loss total is rate x rounds, and the ladder has been measuring the
product.  Chase the round count.

AND IT IS TWO ERRORS, NOT ONE.  Scaling my side's output down until the losses land needs a
factor of 0.30 on Charles+Yang -- and at that factor the fight still runs 28 rounds against 52
observed.  Getting the length right and getting the losses right want different corrections, so
the opponent's per-round rate is over-modelled too, and the two partly cancel in every total in
this project.  That includes the heroless fight whose k of 1.05 was read as validating the damage
core; see reports.py.

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


# Observed round count, read off the report: (Ice Zone triggers, Avalanche triggers) for my Yang.
# Avalanche is PERIODIC 4, so its count dates a fight outright; Ice Zone is chance .40 and only
# corroborates.  Rungs without Yang have no anchor and carry None.
ANCHOR = {'Yang': (3, 1), 'Charles+Yang': (18, 15)}

LADDER = [
    ('0 heroes',    NOHERO_PANEL,                                   [],  {'inf': 500, 'cav': 200, 'arch': 300}, 687),
    ('Charles',     panel(inf=(850.52, 760.5)),            ['Charles'],  BIG,  39),
    ('Yang',        panel(arch=(740.43, 733.5)),              ['Yang'],  BIG,  73),
    ('Sophia+Yang', panel(cav=(740.43, 733.5), arch=(740.43, 733.5)),
                                                    ['Sophia', 'Yang'],  BIG,  41),
    # The decisive rung: adds a HERO without adding a PROC, since Charles has none.  Fought at
    # 1,000 troops, so it is directly comparable to the heroless baseline.
    ('Charles+Yang', panel(inf=(850.52, 760.5), arch=(740.43, 733.5)),
                                                   ['Charles', 'Yang'],  {'inf': 500, 'cav': 200, 'arch': 300}, 26),
]


def run(panel_, heroes, troops, n=400, seed=11):
    """Returns (mean losses, mean rounds).  BOTH matter: a loss total is rate x rounds, so an
    over-modelled per-round rate and an over-modelled opponent -- which ends the fight early --
    partly cancel in it.  The round count does not share that degeneracy."""
    rng = random.Random(seed)
    lost, rounds = [], []
    for _ in range(n):
        a = Side('A', panel_, dict(troops), heroes=heroes, joiners=[], role='solo',
                 hero_stats=False, tier=11, tg=8, widget_default=0.0)
        d = Side('D', NOHERO_ENEMY, dict(ENEMY_TROOPS), heroes=[], joiners=[], role='garrison',
                 hero_stats=False, tier=10, tg=2, widget_default=0.0,
                 troop_abilities=ENEMY_CAPS, troop_reforges=set())
        r = battle_mc(a, d, rng)
        lost.append(r['a_lost'])
        rounds.append(r['rounds'])
    return statistics.mean(lost), statistics.mean(rounds)


def main():
    print(f"{'lineup':16}{'observed':>10}{'sim':>9}{'k':>7}"
          f"{'obs rnd':>10}{'sim rnd':>9}{'rnd k':>7}{'sqrt':>7}")
    errs = []
    for lbl, p, hs, troops, obs in LADDER:
        s, sr = run(p, hs, troops)
        errs.append(math.log(s / obs))
        line = f"  {lbl:14}{obs:>10,}{s:>9.1f}{s / obs:>7.2f}"
        if lbl in ANCHOR:
            ice, av = ANCHOR[lbl]
            orr = (ice / 0.40 + av * 4) / 2
            line += f"{orr:>10.0f}{sr:>9.1f}{sr / orr:>7.2f}{math.sqrt(sr / orr):>7.2f}"
        else:
            line += f"{'--':>10}{sr:>9.1f}{'--':>7}{'--':>7}"
        print(line)
    print(f"\n  rms log err {math.sqrt(sum(x * x for x in errs) / len(errs)):.3f}")
    print("  k STILL falls monotonically with hero count -- but the last two columns say why, and")
    print("  it is not what it looks like.  On both anchored rungs k is almost exactly the square")
    print("  root of the round-count ratio, so the loss error is the fight ending too early: my")
    print("  troops are exposed for a quarter of the rounds they really faced.  Chase the round")
    print("  count, not the loss total.  See reports.py -- forcing the rounds right does NOT fix")
    print("  the losses, so there are two errors here, not one, and they partly cancel.")


if __name__ == '__main__':
    main()
