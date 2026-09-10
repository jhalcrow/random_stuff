#!/usr/bin/env python3
"""Do the simulated proc trigger counts match the reports?

Trigger counts are a validation target the model had never been held to.  Under the per-attack
rule (heroes.PER_ATTACK) a proc described as an ATTACK is rolled once per attacking troop type,
so its expected count is (types alive) x chance x rounds; every other proc is rolled once per
round.  Both predictions are checked here against the 1,500-troop report, where Narses fielded
three troop types for essentially the whole fight.

  python3 kingshot/procs.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from heroes import PROC_SPEC, PER_ATTACK
from reports import NARSES_1500_INF as R

ROUNDS = 207.0        # simulated length of that fight
ENEMY_TYPES = 3       # Narses fielded infantry, cavalry and archers throughout

CASES = [('Art of War',     R['their_long_fei'][2][0]),
         ("Hero's Domain",  R['their_jabel'][1][0]),
         ('Mighty Paragon', R['their_long_fei'][0][0]),
         ('Rally Flag',     R['their_jabel'][0][0]),
         ('Chaos Gambit',   R['their_rosa'][0][0])]


def expected(name):
    mode, p, _ = PROC_SPEC[name]
    per_round = p if mode == 'chance' else (1.0 / p if mode == 'periodic' else 1.0)
    rolls = ENEMY_TYPES if name in PER_ATTACK else 1
    return rolls * per_round * ROUNDS


def main():
    print(f"{'proc':18}{'observed':>10}{'per-round':>11}{'per-attack':>12}{'model':>8}{'err':>8}")
    for name, obs in CASES:
        mode, p, _ = PROC_SPEC[name]
        base = (p if mode == 'chance' else 1.0) * ROUNDS
        exp = expected(name)
        tag = 'attack' if name in PER_ATTACK else 'round'
        print(f"{name:18}{obs:>10}{base:>11.0f}{base * ENEMY_TYPES:>12.0f}{tag:>8}{exp / obs:>8.2f}")
    print("\nThe two ATTACK procs need the per-attack column and the three others need the")
    print("per-round column; that split is the tooltip wording, not a fitted choice.")


if __name__ == '__main__':
    main()
