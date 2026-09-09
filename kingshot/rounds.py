#!/usr/bin/env python3
"""Round-count diagnostic: the second observable, and the one that identifies the model.

A total loss figure is rate x rounds, so an over-modelled per-round rate and an over-modelled
opponent (which ends the fight too early) partly cancel.  That degeneracy is why k on totals
barely moved under a dozen substantive changes to sim.py.  The round count breaks it, because
it depends only on how fast the OPPONENT kills -- nothing of my own damage enters it.

Yang's first two skills carry tooltip-verified schedules that agree with each other, so any
report with Yang in the lineup yields a round count for free:

    Avalanche   periodic 4   ->  rounds = triggers * 4
    Ice Zone    chance 0.40  ->  rounds = triggers / 0.40

Only these two are trusted.  Ambush (chance .40) and Charles' Unyielding Shield (chance .375)
imply 100 and 333 rounds for the same fight that these two put at ~152, so they either roll per
attacking squad rather than per round or their schedules are wrong.  Unresolved; not fitted.

  python3 kingshot/rounds.py
"""
import os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import Side, battle_mc
from allfights import FIGHTS

# fight label -> (Ice Zone triggers, Avalanche triggers) for MY Yang, read off the report
TRIGGERS = {
    'Narses mixed atk 10k': (9, 6),      # reports.NARSES_ROWS['my Yang']
    'Terry 10k all inf':    (3, 1),      # reports.TERRY_ATTACKS[1]['my_yang']
    'Terry 20k mixed':      (9, 7),      # reports.TERRY_ATTACKS[0]['my_yang']
    'Narses 500 solo':      (59, 39),    # reports.NARSES_500['my_yang']
}
LOW_COUNT = 5      # below this many triggers the Poisson noise swamps the estimate


def implied(ice, avalanche):
    return (ice / 0.40 + avalanche * 4) / 2


def sim_rounds(fight, n=200, seed=1234):
    _, mp, mt, mr, ep, et, tier, etg, eh, _, _ = fight
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        a = Side('A', mp, dict(mt), heroes=['Charles', 'Sophia', 'Yang'], role=mr, joiners=[],
                 hero_stats=False, tier=11, tg=8, widget_default=0.0)
        d = Side('D', ep, dict(et), heroes=eh, role=('solo' if mr == 'garrison' else 'garrison'),
                 joiners=[], hero_stats=False, tier=tier, tg=etg, widget_default=0.0)
        if mr == 'garrison':
            a, d = d, a
        out.append(battle_mc(a, d, rng)['rounds'])
    return statistics.mean(out)


def main():
    print(f"{'fight':24}{'sim':>7}{'IceZone':>9}{'Avlnch':>8}{'implied':>9}{'sim/real':>10}")
    for f in FIGHTS:
        if f[0] not in TRIGGERS:
            continue
        ice, av = TRIGGERS[f[0]]
        imp, s = implied(ice, av), sim_rounds(f)
        flag = '   <- 3 and 1 triggers: noise dominates' if min(ice, av) < LOW_COUNT else ''
        print(f"{f[0]:24}{s:>7.0f}{ice/0.40:>9.0f}{av*4:>8}{imp:>9.0f}{s/imp:>10.2f}{flag}")
    print("\nThe simulator ends fights too early nearly everywhere.  Fit this before fitting any")
    print("loss total: rounds constrain the opponent's damage alone, totals constrain a product.")


if __name__ == '__main__':
    main()
