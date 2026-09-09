#!/usr/bin/env python3
"""Measured firing rates: what the trigger rows say once the round count is known.

A trigger count on its own is uninterpretable.  Divided by the round count it is a firing
RATE, directly comparable to the schedule in heroes.PROC_SPEC.  The 500-troop Narses fight
(reports.NARSES_500) supplies both: ~152 rounds from Yang's two verified schedules, and rows
for all six heroes on both sides.  That makes one report a calibration table for the whole
skill layer, including the opponent heroes whose schedules were only ever prose scrapes.

Rows 1-3 are the hero's own skills; rows 4+ belong to the TROOP TYPE, not the hero.

  python3 kingshot/firing.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from heroes import HEROES, PROC_SPEC, PERMANENT, TROOP_SKILLS
from reports import NARSES_500

ROUNDS = 152.0        # Avalanche 39 * 4 = 156, Ice Zone 59 / 0.40 = 148

ROWS = [('Charles',  NARSES_500['my_charles']),
        ('Sophia',   NARSES_500['my_sophia']),
        ('Yang',     NARSES_500['my_yang']),
        ('Long Fei', NARSES_500['their_long_fei']),
        ('Jabel',    NARSES_500['their_jabel']),
        ('Rosa',     NARSES_500['their_rosa'])]

TROOP_BY_TYPE = {}
for _n, _k, _v, _p, _t in TROOP_SKILLS:
    TROOP_BY_TYPE.setdefault(_t, []).append((_n, _p))


def modelled(name):
    """Firing rate per round the model currently assumes, or None if unmodelled."""
    if name in PERMANENT:
        return 1.0 / ROUNDS          # an aura is switched on once, at round 1
    spec = PROC_SPEC.get(name)
    if spec is None:
        return None
    kind, v, _ = spec
    return {'chance': v, 'periodic': 1.0 / v, 'always': 1.0}[kind]


def main():
    print(f"one fight, {ROUNDS:.0f} rounds\n")
    print(f"{'hero':10}{'row':>4}  {'skill':22}{'fired':>7}{'measured':>10}{'modelled':>10}  ratio")
    for hero, rows in ROWS:
        info = HEROES[hero]
        troop = [n for n, _ in TROOP_BY_TYPE.get(info['type'], [])]
        for i, (fired, _kills) in enumerate(rows):
            if i < 3:
                name = info['skills'][i]
                name = name[0] if isinstance(name, (list, tuple)) else name
            else:
                j = i - 3
                name = troop[j] if j < len(troop) else '(unmapped row)'
            meas, mod = fired / ROUNDS, modelled(name)
            r = f"{meas / mod:5.2f}" if mod else "    -"
            flag = ''
            if mod and (meas / mod > 1.5 or meas / mod < 0.67):
                flag = '  <-- schedule disagrees'
            m = f"{mod:>10.3f}" if mod else f"{'unmodelled':>10}"
            print(f"{hero:10}{i+1:>4}  {name:22}{fired:>7}{meas:>10.3f}{m}  {r}{flag}")
        print()
    print("Row 1-3 mapping assumes the panel lists a hero's skills in heroes.py order.  Where a")
    print("row shows exactly 1 trigger it is a permanent aura, which is a check on that mapping:")
    print("Charles' three all read 1, as they should.  Sophia's row 3 reads 1 but is modelled as")
    print("periodic 2 (~76 expected) -- either her order is wrong or that skill is an aura too.")
    print()
    print("HOW MUCH OF THIS IS THE ROUND COUNT?  Most rows come in low, which would also follow")
    print("from ROUNDS being too high, so the count must not simply be assumed.  Solving for it")
    print("over the non-Yang rows gives a broad, poor minimum near 120 (rms 0.53, and 0.53-0.59")
    print("anywhere from 100 to 152) -- no sharp constraint, and nowhere near the sim's 73.")
    print("Avalanche stays the anchor because it is PERIODIC: 39 triggers of an every-4th-round")
    print("skill is near-deterministic, where a chance rate is only as good as a scraped number.")


if __name__ == '__main__':
    main()
