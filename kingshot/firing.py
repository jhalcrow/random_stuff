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

# A TROOP ABILITY ONLY RUNS WHILE ITS TYPE IS ALIVE, so dividing its trigger count by the battle
# length under-counts it by exactly the fraction of the battle that type survived.  An earlier
# version of this file divided everything by ROUNDS and concluded that 15 of 21 schedules were
# wrong by more than 1.5x, most at "~0.55 of nominal".  THAT WAS MY OWN DENOMINATOR ERROR, not a
# game mechanic: 76/152 = 0.50 and 79/152 = 0.52 are the "~0.55".
# My troops' lifetimes in this fight, simulated: infantry 71, cavalry 76, archers 79 of 152
# rounds.  Inverting the observed counts instead gives cavalry 70/86/80/73 and archers 80/87 --
# the same numbers from five independent proc rates, so the schedules were right all along.
LIFETIME = {'inf': 71.0, 'cav': 76.0, 'arch': 79.0}

# HERO skills are the exception and are divided by the full battle length: Yang's Ice Zone and
# Avalanche imply 148 and 156, outliving his archers, which matches the Terry all-infantry report
# where he books kills with zero archers.  Sophia's do NOT -- hers imply 70 and 86, tracking her
# cavalry.  That asymmetry between two heroes on the same side is unexplained and is now the
# sharpest open question in the skill layer.
HERO_USES_TROOP_LIFETIME = {'Sophia'}

ROWS = [('Charles',  NARSES_500['my_charles']),
        ('Sophia',   NARSES_500['my_sophia']),
        ('Yang',     NARSES_500['my_yang']),
        ('Long Fei', NARSES_500['their_long_fei']),
        ('Jabel',    NARSES_500['their_jabel']),
        ('Rosa',     NARSES_500['their_rosa'])]

# Troop-ability rows IN THE ORDER THE PANEL SHOWS THEM, which is not TROOP_SKILLS order and is
# not derivable from it.  Cavalry displays three, one of them Ambusher -- which sim.py handles as
# a targeting effect rather than a TROOP_SKILLS entry, so it has no modelled firing rate here.
# The cavalry order is read off the 500-troop report: row 5 is the only one booking kills, which
# makes it Assault Lance (double damage), and the Warding Impaler tooltip is anchored to the last
# row.  That leaves Ambusher first.  Rows 4-6 fired 16, 11 and 4 times.
TROOP_ROWS = {'inf': ['Unyielding Shield'],
              'cav': ['Ambusher', 'Assault Lance', 'Warding Impaler'],
              'arch': ['Volley', 'Howling Wind']}


def modelled(name):
    """Firing rate per round the model currently assumes, or None if unmodelled."""
    if name in PERMANENT:
        return 1.0 / ROUNDS          # an aura is switched on once, at round 1
    spec = PROC_SPEC.get(name)
    if spec is None:
        return None
    kind, v, _ = spec
    return {'chance': v, 'periodic': 1.0 / v, 'always': 1.0}[kind]


EXPECTED_ROWS = {t: 3 + len(v) for t, v in TROOP_ROWS.items()}


def check_rows(hero, rows):
    """A row that never fired is omitted from the panel, so indices shift and positional mapping
    silently mis-assigns.  Verified on Terry's Yang, which shows 4 rows because his Volley fired
    zero times -- his 4th row is everyone else's 5th.  Never map by position without this."""
    want = EXPECTED_ROWS[HEROES[hero]['type']]
    if len(rows) < want:
        return f"  !! {len(rows)} rows, expected {want}: a zero-trigger row is omitted, mapping below is UNSAFE"
    if len(rows) > want:
        return f"  !! {len(rows)} rows, expected {want}: {len(rows) - want} troop ability/-ies not in TROOP_ROWS"
    return None


def main():
    print(f"one fight, {ROUNDS:.0f} rounds; troop lifetimes "
          + ", ".join(f"{t} {v:.0f}" for t, v in LIFETIME.items()) + "\n")
    print(f"{'hero':10}{'row':>4}  {'skill':22}{'fired':>7}{'over':>6}{'measured':>10}{'modelled':>10}  ratio")
    for hero, rows in ROWS:
        warn = check_rows(hero, rows)
        if warn:
            print(warn)
        info = HEROES[hero]
        troop = TROOP_ROWS.get(info['type'], [])
        for i, (fired, _kills) in enumerate(rows):
            if i < 3:
                name = info['skills'][i]
                name = name[0] if isinstance(name, (list, tuple)) else name
            else:
                j = i - 3
                name = troop[j] if j < len(troop) else '(unmapped row)'
            ttype = info['type']
            denom = ROUNDS
            if i >= 3 or hero in HERO_USES_TROOP_LIFETIME:
                denom = LIFETIME[ttype]
            meas, mod = fired / denom, modelled(name)
            r = f"{meas / mod:5.2f}" if mod else "    -"
            flag = ''
            if mod and (meas / mod > 1.5 or meas / mod < 0.67):
                flag = '  <-- schedule disagrees'
            m = f"{mod:>10.3f}" if mod else f"{'unmodelled':>10}"
            print(f"{hero:10}{i+1:>4}  {name:22}{fired:>7}{denom:>6.0f}{meas:>10.3f}{m}  {r}{flag}")
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
