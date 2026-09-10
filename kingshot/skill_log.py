#!/usr/bin/env python3
"""Per-skill Triggered/Kills rows transcribed from the Battle Details panels.

This is the highest-information part of a battle report and the simulator does not use it yet.
Two structural facts fall straight out of it:

1. Skills split into PURE BUFFS (kills column always blank) and DIRECT-DAMAGE skills (their own
   kill count).  sim.py models every skill as a multiplier on troop damage, so the whole
   direct-damage channel is missing.  Charles is pure buff; Vivian deals damage on row 2;
   Sophia and Ava on row 5; Yang on rows 1, 2 and 5.

2. SOME rows have fixed cadence and others do not.  Two identical solo attacks (see SOLO_RUNS in
   reports.py) fired Charles' rows 1-3 and Yang's row 1 exactly the same number of times, while
   Sophia's row 5 fired 7 times then 3 and Charles' row 4 fired 35 then 30.  Vivian's 12/12/12
   across three rallies is one of the fixed rows, not evidence that cadence is deterministic in
   general -- an earlier note here claimed the latter and was wrong.  What IS stable is per-trigger
   damage (Sophia 715 vs 731 kills per trigger across those two runs), so a nuke should be modelled
   as a deterministic magnitude with a random trigger count.

Open question the current data cannot settle: Yang scored 203 kills with ZERO archers and 588
with 3,000 next to Ava, but only 103 with 3,000 next to Sophia.  His nukes therefore do not
scale with his own troop count, and Ava's modelled kit (~2.1x combined) cannot account for a
5.7x swing.  See CALIBRATION_TESTS for the experiments that would pin this down.

  python3 kingshot/skill_log.py
"""

# report -> hero -> [(triggered, kills), ...] in panel row order
LOG = {
    'Ava 60/40/0': {
        'me Charles': [(1, 0), (1, 0), (1, 0), (37, 0)],
        'them Charles': [(1, 0), (1, 0), (1, 0), (37, 0)],
        'me Ava': [(1, 0), (8, 0), (1, 0), (9, 0), (2, 28), (2, 0)],
        'them Sophia': [(12, 0), (17, 0), (1, 0), (8, 0), (4, 102)],
        'me Yang': [(15, 203), (1, 0), (10, 0)],          # panel truncated after row 3
        'them Vivian': [(1, 0), (12, 432), (1, 0)],
    },
    'Ava 50/20/30': {
        'me Charles': [(1, 0), (1, 0), (1, 0), (28, 0)],
        'them Charles': [(1, 0), (1, 0), (1, 0), (48, 0)],
        'me Ava': [(1, 0), (7, 0), (1, 0), (4, 0), (3, 34), (2, 0)],
        'them Sophia': [(14, 0), (15, 0), (1, 0), (4, 0), (2, 34)],
        'me Yang': [(20, 250), (10, 186), (12, 0), (1, 0), (12, 152)],
        'them Vivian': [(1, 0), (12, 321), (1, 0)],
    },
    'Sophia 50/20/30': {
        'me Charles': [(1, 0), (1, 0), (1, 0), (25, 0)],
        'them Charles': [(1, 0), (1, 0), (1, 0), (45, 0)],
        'me Sophia': [(17, 0), (15, 0), (1, 0), (7, 0), (9, 45), (1, 0)],
        'them Sophia': [(14, 0), (15, 0), (1, 0), (8, 0), (11, 626)],
        'me Yang': [(15, 53), (2, 26), (14, 0), (1, 0), (3, 24)],
        'them Vivian': [(1, 0), (12, 562), (1, 0)],
    },
}

# Skills the model currently has, against the row count the reports show.
COVERAGE = {'Charles': (3, 4), 'Sophia': (3, 6), 'Ava': (3, 6), 'Yang': (3, 5), 'Vivian': (3, 3)}

# What field testing can and cannot settle, at the simulator's own ~9% per-rally CV.
# Repeats needed per arm to call an effect at 95%: 30% gap -> 1, 20% -> 2, 10% -> 7,
# 5% -> 27, 2% -> 159.  The 900-trio ranking in run.py separates its top lineups by 2-5%,
# so that ordering is NOT empirically checkable -- it has to come from a correct model.
# The three big findings survive a single pair of rallies even if the real engine is twice
# as noisy as the model: they stay 2-sigma up to a CV of 17% (Terror), 20% (archers) and
# 42% (the hero x composition interaction).
CALIBRATION_TESTS = [
    ('noise floor', 'Repeat one config 4-5 times (same heroes, ratio, joiners, target) and record '
                    'every kill count. The engine is known to be nondeterministic, so this measures '
                    'the spread rather than testing for it -- and every error bar below depends on '
                    'it. The simulator\'s own spread is ~9% CV; the real number is unmeasured.'),
    ('nuke scaling', 'Send 0/0/100 all-archer, then repeat at a different march size. Yang is the '
                     'only hero with three damage rows, so this isolates the direct-damage channel '
                     'and shows whether it scales with march size, troop count or neither.'),
    ('buff-only baseline', 'Send 100/0/0 all-infantry. Charles deals no damage at all, so whatever '
                           'kills appear come from troops plus the other two heroes firing without '
                           'matching troops -- a clean read on the engine term by itself.'),
    ('the Ava lift', 'All-archer twice, once with Ava in the cavalry slot and once with Sophia, '
                     'everything else fixed. This is the 5.7x swing with every other variable removed.'),
]

if __name__ == '__main__':
    print('Damage-dealing rows (kills > 0) by hero:\n')
    seen = {}
    for rep, heroes in LOG.items():
        for h, rows in heroes.items():
            name = h.split()[-1]
            seen.setdefault(name, set()).update(i for i, (t, k) in enumerate(rows) if k)
    for name, idx in sorted(seen.items()):
        print(f'  {name:8s} {"rows " + ", ".join(str(i+1) for i in sorted(idx)) if idx else "none (pure buff)"}')
    print('\nModel coverage:')
    for h, (have, actual) in COVERAGE.items():
        print(f'  {h:8s} {have}/{actual} skills modelled'
              f'{"" if have == actual else "   <-- incomplete"}')
    print('\nVivian row 2 -- fixed cadence, variable output:')
    for rep in LOG:
        t, k = LOG[rep]['them Vivian'][1]
        print(f'  {rep:16s} {t} triggers -> {k:4d} kills ({k/t:5.1f} each)')
    print('\nCalibration tests, in priority order:')
    for i, (name, why) in enumerate(CALIBRATION_TESTS, 1):
        print(f'  {i}. {name}\n     {why}')
