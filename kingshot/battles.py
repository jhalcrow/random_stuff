#!/usr/bin/env python3
"""EVERY MEASURED BATTLE, TRANSCRIBED IN ONE PLACE.

This file is the DATA.  reports.py is the argument -- what each fight meant, what it refuted,
which claims were retracted.  allfights.py is the SCORER -- it feeds a subset of these into the
engine.  When they disagree about a number, THIS FILE WINS: everything here was read directly off
a battle report screenshot, and nothing here is inferred, fitted or carried over from a previous
fight.

CASUALTY ACCOUNTING, checked on every record: injured + lightly_injured + losses = casualties,
and squad - casualties = residents.  ("Losses" is non-zero only where the player's infirmary
overflowed and wounded became deaths; it is the same casualty either way.)

CENSORING is the reason `uncensored` exists.  A wiped side's casualties pin at its squad size and
measure nothing, so each fight is scored on the side that was NOT wiped:
    I win  -> MY losses are the observable (they measure HIS output)
    I lose -> HIS losses are the observable (they measure MY output)
Both wiped, or neither, is noted per record.

PANELS are the in-game Stat Bonuses page, as percentages, for the fight as fought.  They already
contain hero expedition stats, hero gear and research, which is why every fight is simulated with
hero_stats=False against the panel rather than reconstructing it.  Widgets are NOT in the panel --
they are Special Bonuses applied afterwards.

TRIGGER ROWS are the Battle Details panel, in displayed order, as (name, triggers, kills).  Rows
that fired ZERO times are omitted by the game, so row position is not a stable index.  A
scope-gated skill whose troop type is absent shows 1, not 0 (measured on Avalanche and on Terror
Deathblow).  kills=None means the game showed a dash.

  python3 kingshot/battles.py        # verify every record's arithmetic
"""

# Narses' panel with no heroes, identical across every heroless report -- he is unbuffed.
NARSES_BARE = {'inf': (238.6, 232.0, 179.9, 181.0),
               'cav': (217.3, 206.7, 160.8, 158.6),
               'arch': (239.1, 232.0, 176.8, 177.2)}
# Narses with Long Fei only: his INFANTRY line moves, the other two do not.
NARSES_LONGFEI = {'inf': (520.9, 514.3, 251.4, 294.6),
                  'cav': (217.3, 206.7, 160.8, 158.6),
                  'arch': (239.1, 232.0, 176.8, 177.2)}
# Narses with all three (Long Fei / Jabel / Rosa): every line moves.
NARSES_TRIO = {'inf': (520.9, 514.3, 251.4, 294.6),
               'cav': (356.1, 345.5, 259.4, 227.3),
               'arch': (474.3, 467.2, 311.3, 243.9)}
# His skills are NOT maxed: Long Fei 4, Jabel 5, Rosa 4 (confirmed by the player).
# His widgets: Long Fei NONE, Rosa NONE, Jabel level 1 (a padlock means not owned).
NARSES_SKILL_LEVELS = {'Long Fei': 4, 'Jabel': 5, 'Rosa': 4}
NARSES_WIDGETS = {'Long Fei': 0.0, 'Rosa': 0.0, 'Jabel': 0.1}

# My panel, heroless, as it drifted over the session.  The ONLY changes are research upgrades and
# one lapsed buff -- see the note on each.
MINE_BARE_V1 = {'inf': (1102.3, 1090.7, 1042.4, 1040.6),      # 2026-09-09 evening
                'cav': (1080.3, 1069.3, 990.8, 992.6),
                'arch': (1083.1, 1069.0, 1009.2, 1004.1)}
MINE_BARE_V2 = {'inf': (1102.3, 1090.7, 1045.2, 1042.4),      # + small research upgrades
                'cav': (1080.3, 1069.3, 993.9, 996.1),
                'arch': (1083.1, 1069.0, 1012.0, 1006.6)}
MINE_BARE_V3 = {'inf': (1102.3, 1085.7, 1045.2, 1042.4),      # - a +5% Defense buff that lapsed
                'cav': (1080.3, 1064.3, 993.9, 996.1),        #   between 22:54 and 23:03
                'arch': (1083.1, 1064.0, 1012.0, 1006.6)}

# Hero panel deltas, MEASURED and then confirmed by prediction on seven consecutive heroes:
# a hero adds (expedition attack + 200) to attack AND defense of his own troop type, and
# (weapon Lv.10 + 600) to lethality AND health of the same type.
HERO_PANEL_DELTA = {'Charles': ('inf', 850.52, 760.5),
                    'Sophia':  ('cav', 740.43, 733.5),
                    'Yang':    ('arch', 740.43, 733.5)}


def _panel(bare, *heroes):
    p = {t: list(v) for t, v in bare.items()}
    for h in heroes:
        t, atk, leth = HERO_PANEL_DELTA[h]
        p[t][0] += atk; p[t][1] += atk; p[t][2] += leth; p[t][3] += leth
    return {t: tuple(round(x, 1) for x in v) for t, v in p.items()}


THIRDS = {'inf': 27_866, 'cav': 27_867, 'arch': 27_867}          # 83,600
THIRDS_B = {'inf': 27_866, 'cav': 27_877, 'arch': 27_877}        # 83,620, a later reading
LARGE = {'inf': 61_785, 'cav': 24_714, 'arch': 37_071}           # 123,570, his other garrison

BATTLES = [
 dict(mail='223407017262625', when='2026-09-09 ~19:00', label='1000 NO HEROES',
      me=dict(heroes=[], troops={'inf':500,'cav':200,'arch':300}, panel=MINE_BARE_V1,
              injured=241, lightly=446, losses=0, residents=313),
      him=dict(heroes=[], troops=THIRDS, panel=NARSES_BARE,
               injured=29_262, lightly=54_338, losses=0, residents=0),
      outcome='victory', uncensored='me', observed=687,
      rows={'mine': [('Unyielding Shield', 104, None)],
            'his': [('Ambusher', 25, None), ('archer row 1', 7, None)]},
      note='Both sides Vacant in all three slots and "No Special Stats Bonuses". The damage core '
           'with the entire skill layer switched off. Also shows his TG2 ability rows directly.'),

 dict(mail='223407017271858', when='2026-09-09 20:36:53', label='500 NO HEROES',
      me=dict(heroes=[], troops={'inf':250,'cav':100,'arch':150}, panel=MINE_BARE_V2,
              injured=176, lightly=324, losses=0, residents=0),
      him=dict(heroes=[], troops=THIRDS, panel=NARSES_BARE,
               injured=5_621, lightly=10_438, losses=0, residents=67_541),
      outcome='defeat', uncensored='him', observed=16_059,
      rows={'mine': [('Unyielding Shield', 66, None), ('Ambusher', 18, None),
                     ('Assault Lance', 11, 287), ('Warding Impaler', 2, None),
                     ('Volley', 9, None), ('Howling Wind', 17, 319)],
            'his': [('Ambusher', 17, None), ('archer row 1', 9, None)]},
      note='Sized for power after the audit. HIS rows carry no lifetime confound (he keeps 67,541 '
           'of 83,600), and they date the fight at 85-90 rounds against the simulator 90.6.'),

 dict(mail='223407017275279', when='2026-09-09 21:33:32', label='500 YANG ONLY',
      me=dict(heroes=['Yang'], troops={'inf':250,'cav':100,'arch':150},
              panel=_panel(MINE_BARE_V2, 'Yang'),
              injured=82, lightly=150, losses=0, residents=268),
      him=dict(heroes=[], troops=THIRDS, panel=NARSES_BARE,
               injured=29_262, lightly=54_338, losses=0, residents=0),
      outcome='victory', uncensored='me', observed=232,
      rows={'mine': [('Unyielding Shield', 57, None), ('Ambusher', 13, None),
                     ('Assault Lance', 9, 410),
                     ('Ice Zone', 51, 4_246), ('Avalanche', 23, 3_567), ('Ambush', 23, None),
                     ('Volley', 8, None), ('Howling Wind', 26, 2_945)],
            'his': [('Ambusher', 19, None), ('archer row 1', 10, None)]},
      note='Avalanche is periodic 4, so 23 triggers date the fight at 92 rounds against the '
           'simulator 45.6 -- the clock is 2.0x too fast with ONE hero. Warding Impaler fired 0 '
           'and its row is omitted.'),

 dict(mail='223407017277424', when='2026-09-09 ~22:10', label='500 CHARLES ONLY',
      me=dict(heroes=['Charles'], troops={'inf':250,'cav':100,'arch':150},
              panel=_panel(MINE_BARE_V2, 'Charles'),
              injured=79, lightly=144, losses=0, residents=277),
      him=dict(heroes=[], troops=THIRDS, panel=NARSES_BARE,
               injured=22_828, lightly=54_338, losses=6_434, residents=0),
      outcome='victory', uncensored='me', observed=223,
      rows={'mine': [('Intimidation', 1, None), ('Iron Bodies', 1, None), ('Great Justice', 1, None),
                     ('Unyielding Shield', 173, None), ('Ambusher', 39, None),
                     ('Assault Lance', 28, 1_082), ('Volley', 24, None), ('Howling Wind', 53, 1_641)],
            'his': [('Ambusher', 41, None), ('archer row 1', 22, None)]},
      note='His "Losses" row is non-zero because the player\'s infirmary was full and wounded '
           'became deaths; the three rows still sum to 83,600. Charles is three DEFENSIVE auras '
           'and zero offensive, and the clock came out exact (his Ambusher predicted 40.3, got 41).'),

 dict(mail='223407017280638', when='2026-09-09 22:27:16', label='500 SOPHIA ONLY',
      me=dict(heroes=['Sophia'], troops={'inf':250,'cav':100,'arch':150},
              panel=_panel(MINE_BARE_V2, 'Sophia'),
              injured=102, lightly=186, losses=0, residents=212),
      him=dict(heroes=[], troops=THIRDS, panel=NARSES_BARE,
               injured=29_262, lightly=54_338, losses=0, residents=0),
      outcome='victory', uncensored='me', observed=288,
      rows={'mine': [('Unyielding Shield', 93, None),
                     ('Arcane Pact', 39, None), ('Terror Deathblow', 46, None),
                     ('Terror Annihilation', 1, None),
                     ('Ambusher', 20, None), ('Assault Lance', 15, 1_651),
                     ('Volley', 9, None), ('Howling Wind', 33, 1_167)],
            'his': [('Ambusher', 16, None), ('archer row 1', 7, None)]},
      note='Terror Deathblow is periodic 1-in-2, so 46 triggers date the fight at 92 rounds -- a '
           'second deterministic clock independent of Yang. Her firing rates all match the model, '
           'unlike Yang\'s.'),

 dict(mail='223407017281728', when='2026-09-09 22:43:22', label='500 SOPHIA 100/250/150',
      me=dict(heroes=['Sophia'], troops={'inf':100,'cav':250,'arch':150},
              panel=_panel(MINE_BARE_V2, 'Sophia'),
              injured=83, lightly=151, losses=0, residents=266),
      him=dict(heroes=[], troops=THIRDS, panel=NARSES_BARE,
               injured=29_262, lightly=54_338, losses=0, residents=0),
      outcome='victory', uncensored='me', observed=234,
      rows={'mine': [('Unyielding Shield', 46, None),
                     ('Arcane Pact', 30, None), ('Terror Deathblow', 36, None),
                     ('Terror Annihilation', 1, None),
                     ('Ambusher', 19, None), ('Assault Lance', 12, 1_437),
                     ('Warding Impaler', 6, None),
                     ('Volley', 13, None), ('Howling Wind', 18, 824)],
            'his': [('Ambusher', 12, None), ('archer row 1', 7, None)]},
      note='Same hero, same total, only the mix changed -- her cavalry 20%% -> 50%% of the march. '
           'Warding Impaler appears as a sixth cavalry row now that cavalry is 250; it was omitted '
           'at 100 where it fired zero times.'),

 dict(mail='223407017281976', when='2026-09-09 22:54:20', label='1000 SOPHIA no cavalry',
      me=dict(heroes=['Sophia'], troops={'inf':500,'cav':0,'arch':500},
              panel=_panel(MINE_BARE_V2, 'Sophia'),
              injured=235, lightly=435, losses=0, residents=330),
      him=dict(heroes=[], troops=THIRDS, panel=NARSES_BARE,
               injured=29_262, lightly=54_338, losses=0, residents=0),
      outcome='victory', uncensored='me', observed=670,
      rows={'mine': [('Unyielding Shield', 109, None),
                     ('Arcane Pact', 59, None), ('Terror Deathblow', 1, None),
                     ('Terror Annihilation', 1, None),
                     ('Volley', 15, None), ('Howling Wind', 44, 4_893)],
            'his': [('Ambusher', 24, None), ('archer row 1', 13, None)]},
      note='Cav-scoped Terror Deathblow reads 1, the COLLAPSED value for a scope-gated skill whose '
           'troop type is absent -- not 0, and not omitted. No cavalry rows at all on my side.'),

 dict(mail='223407017282381', when='2026-09-09 23:03:32', label='500 CHARLES+SOPHIA',
      me=dict(heroes=['Charles','Sophia'], troops={'inf':250,'cav':100,'arch':150},
              panel={'inf': (1952.8, 1936.2, 1805.7, 1802.9),
                     'cav': (1820.7, 1804.7, 1727.4, 1729.6),
                     'arch': (1083.1, 1064.0, 1012.0, 1006.6)},
              injured=29, lightly=51, losses=0, residents=420),
      him=dict(heroes=[], troops=THIRDS, panel=NARSES_BARE,
               injured=29_262, lightly=54_338, losses=0, residents=0),
      outcome='victory', uncensored='me', observed=80,
      rows={'mine': [('Intimidation', 1, None), ('Iron Bodies', 1, None), ('Great Justice', 1, None),
                     ('Unyielding Shield', 72, None),
                     ('Arcane Pact', 28, None), ('Terror Deathblow', 38, None),
                     ('Terror Annihilation', 1, None),
                     ('Ambusher', 9, None), ('Assault Lance', 14, 1_366),
                     ('Volley', 4, None), ('Howling Wind', 19, 947)],
            'his': [('Ambusher', 16, None), ('archer row 1', 5, None)]},
      note='FIRST PANEL MISS in eight: every DEFENSE value is exactly 5.0 below the sum of the '
           'single-hero panels while attack/lethality/health are exact -- a +5%% Defense bonus '
           'lapsed since the previous report. Panel recorded AS REPORTED, not as predicted.'),

 dict(mail='223407017290304', when='2026-09-10 04:38:30', label='500 vs NARSES + LONG FEI',
      me=dict(heroes=[], troops={'inf':250,'cav':100,'arch':150}, panel=MINE_BARE_V3,
              injured=176, lightly=324, losses=0, residents=0),
      him=dict(heroes=['Long Fei'], troops=THIRDS_B, panel=NARSES_LONGFEI,
               injured=1_473, lightly=2_733, losses=0, residents=79_414),
      outcome='defeat', uncensored='him', observed=4_206,
      rows={'mine': [('Unyielding Shield', 64, None), ('Ambusher', 9, None),
                     ('Assault Lance', 14, 161), ('Warding Impaler', 4, None),
                     ('Volley', 6, None), ('Howling Wind', 11, 61)],
            'his': [('Mighty Paragon', 23, None), ('Celestial Sustenance', 1, None),
                    ('Art of War', 49, 28), ('Ambusher', 12, None), ('archer row 1', 5, None)]},
      note='The mirror of the Charles test: a hero on HIS side, none on mine. Adding a hero also '
           'adds his expedition STATS -- his infantry attack went 238.6 -> 520.9 -- which my '
           'pre-registration failed to account for.'),

 dict(mail='223407017291692', when='2026-09-10 ~05:00', label='500 TRIO vs TRIO',
      me=dict(heroes=['Charles','Sophia','Yang'], troops={'inf':300,'cav':200,'arch':0},
              panel={'inf': (1952.8, 1936.2, 1805.7, 1802.9),
                     'cav': (1820.7, 1804.7, 1727.4, 1729.6),
                     'arch': (1823.5, 1804.4, 1745.5, 1740.1)},
              injured=None, lightly=None, losses=None, residents=0, wiped=500),
      him=dict(heroes=['Long Fei','Jabel','Rosa'], troops=LARGE, panel=NARSES_TRIO,
               injured=None, lightly=None, losses=None, residents=None, total=8_142),
      outcome='defeat', uncensored='him', observed=8_142,
      rows={'mine': [('Intimidation', 1, None), ('Iron Bodies', 1, None), ('Great Justice', 1, None),
                     ('Unyielding Shield', 145, None),
                     ('Arcane Pact', 31, None), ('Terror Deathblow', 45, None),
                     ('Terror Annihilation', 1, None),
                     ('Ambusher', 21, None), ('Assault Lance', 14, 936), ('Warding Impaler', 4, None),
                     ('Ice Zone', 41, 686), ('Avalanche', 1, None), ('Ambush', 30, None)],
            'his': [('Mighty Paragon', 30, None), ('Celestial Sustenance', 1, None),
                    ('Art of War', 69, 24),
                    ('Rally Flag', 37, None), ("Hero's Domain", 147, 30), ('Youthful Rage', 1, None),
                    ('Ambusher', 21, None), ('Rosa row 1', 40, None)]},
      note='Casualty split not captured (only the summary line, 500 troops / 8,142 kills / '
           '-23,625 power). ICE ZONE FIRED 41 TIMES FOR 686 KILLS WITH ZERO ARCHERS while '
           'Avalanche correctly collapsed to 1 -- unexplained, and its tooltip says "Yang\'s '
           'archers". Terror Deathblow 45 dates the fight at ~90 rounds against the simulator 172.'),
]


def check():
    """Verify the arithmetic of every record that captured a full casualty split."""
    bad = 0
    for b in BATTLES:
        for who in ('me', 'him'):
            s = b[who]
            if s.get('injured') is None:
                continue
            squad = sum(s['troops'].values())
            cas = s['injured'] + s['lightly'] + s['losses']
            if cas + s['residents'] != squad:
                print(f"  MISMATCH {b['label']:28} {who:4} "
                      f"{cas} + {s['residents']} != {squad}")
                bad += 1
    print(f"{len(BATTLES)} battles, casualty arithmetic checks: "
          f"{'all consistent' if not bad else f'{bad} MISMATCHES'}")
    return bad


if __name__ == '__main__':
    check()
    print()
    print(f"{'label':28}{'outcome':9}{'scored on':11}{'observed':>10}")
    for b in BATTLES:
        print(f"  {b['label']:26}{b['outcome']:9}{b['uncensored']:11}{b['observed']:>10,}")
