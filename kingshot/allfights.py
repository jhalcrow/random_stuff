#!/usr/bin/env python3
"""Every fight in reports.py where one side's losses are uncensored, scored in one place.

k = simulated / observed on the UNCENSORED quantity: my own losses when I won, the enemy's when
I was wiped.  In both cases that is the LOSING side's total damage output, which is the thing the
model has been over-predicting.

  python3 kingshot/allfights.py
"""
import math, os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import Side, battle_mc
from reports import (TERRY_ATTACK_PANEL, TERRY_ATTACK_ENEMY, OPP2, OPP2_TROOPS, OPP2_TIERS,
                     OPP2_PANEL, SOLO_PANEL, NARSES, NARSES_TROOPS, NARSES_ED20,
                     NARSES_1500_INF_PANEL)

NP = {'inf': dict(attack=2379.0, defense=1941.2, lethality=2183.4, health=1801.1),
      'cav': dict(attack=2220.5, defense=1809.7, lethality=2089.2, health=1726.1),
      'arch': dict(attack=2223.8, defense=1809.4, lethality=2111.2, health=1737.6)}
TE = {'inf': 113_467, 'cav': 45_386, 'arch': 68_079}
TE20 = {'inf': 94_555, 'cav': 37_822, 'arch': 56_733}

# Mail 223407017262625: both sides heroless, no special bonuses, panels far below the with-hero
# ones (my infantry attack 1102.3 against 2379.0), which is itself a measure of how much of the
# panel is hero expedition stats.
# A SECOND heroless report, 2026-09-10, after the player made small research upgrades: lethality
# and health up 2-4 points on every type, everything else identical.  Narses' panel is byte-for-
# byte the same as the first heroless report, which re-confirms he is unbuffed and unchanged.
NOHERO_PANEL_V2 = {'inf': dict(attack=1102.3, defense=1090.7, lethality=1045.2, health=1042.4),
                   'cav': dict(attack=1080.3, defense=1069.3, lethality=993.9,  health=996.1),
                   'arch':dict(attack=1083.1, defense=1069.0, lethality=1012.0, health=1006.6)}
# Yang alone on the same base: archer +740.43 attack/defense and +733.5 lethality/health, which
# is his expedition stats plus the measured +200 / +600 gear.  PREDICTED TO THE DECIMAL before
# the report arrived, the fifth consecutive hero for which that has held.
YANG_PANEL_V2 = {'inf': dict(attack=1102.3, defense=1090.7, lethality=1045.2, health=1042.4),
                 'cav': dict(attack=1080.3, defense=1069.3, lethality=993.9,  health=996.1),
                 'arch':dict(attack=1823.5, defense=1809.4, lethality=1745.5, health=1740.1)}
# Charles alone on the same base: infantry +850.52 attack/defense, +760.5 lethality/health.
# Predicted to the decimal before the report -- the SIXTH consecutive hero for which that held.
CHARLES_PANEL_V2 = {'inf': dict(attack=1952.8, defense=1941.2, lethality=1805.7, health=1802.9),
                    'cav': dict(attack=1080.3, defense=1069.3, lethality=993.9,  health=996.1),
                    'arch':dict(attack=1083.1, defense=1069.0, lethality=1012.0, health=1006.6)}
# Sophia alone on the same base: cavalry +740.43 attack/defense, +733.5 lethality/health.
# Predicted to the decimal -- the SEVENTH consecutive hero.
SOPHIA_PANEL_V2 = {'inf': dict(attack=1102.3, defense=1090.7, lethality=1045.2, health=1042.4),
                   'cav': dict(attack=1820.7, defense=1809.7, lethality=1727.4, health=1729.6),
                   'arch':dict(attack=1083.1, defense=1069.0, lethality=1012.0, health=1006.6)}
NOHERO_PANEL = {'inf': dict(attack=1102.3, defense=1090.7, lethality=1042.4, health=1040.6),
                'cav': dict(attack=1080.3, defense=1069.3, lethality=990.8, health=992.6),
                'arch': dict(attack=1083.1, defense=1069.0, lethality=1009.2, health=1004.1)}
NOHERO_ENEMY = {'inf': dict(attack=238.6, defense=232.0, lethality=179.9, health=181.0),
                'cav': dict(attack=217.3, defense=206.7, lethality=160.8, health=158.6),
                'arch': dict(attack=239.1, defense=232.0, lethality=176.8, health=177.2)}

# (label, my panel, my troops, my role, enemy panel, enemy troops, enemy tier, enemy heroes,
#  enemy Truegold level, enemy heroes, which side's losses are uncensored, observed)
FIGHTS = [
    # WHICH ENEMY PANEL EACH FIGHT GETS IS DECIDED BY WHICH OF MY PANELS IT USES.
    # NP reconstructs to within 0.08 of a point as the unbuffed panel with +20% Squads' Attack and
    # +20% Squads' Lethality applied, so every NP fight was fought with that stack up -- and the
    # 08:14:37 Special Bonuses page shows the stack always carries -20% Enemy Squads' Defense with
    # it, so those fights must see his defence as NARSES_ED20.  SOLO_PANEL sits at the unbuffed
    # level instead (its lethality is 1802.9, identical to the post-lapse panel, against NP's
    # 2183.4), so those fights get his undiminished NARSES.
    # The inference that the three channels always travel together rests on two observed states,
    # both all-on or all-off.  A report showing them apart would break it.
    ('Narses pure-arch 5k', NP, {'inf': 2500, 'cav': 1000, 'arch': 1500}, 'solo',
     NARSES_ED20, {'inf': 0, 'cav': 0, 'arch': 116_040}, 10, 2, ['Long Fei', 'Jabel', 'Rosa'], 'me', 72),
    ('Narses mixed atk 10k', SOLO_PANEL, {'inf': 5000, 'cav': 2000, 'arch': 3000}, 'solo',
     NARSES, NARSES_TROOPS, 10, 2, ['Long Fei', 'Jabel', 'Rosa'], 'me', 239),
    ('Narses mixed def 5k', SOLO_PANEL, {'inf': 2500, 'cav': 1000, 'arch': 1500}, 'garrison',
     NARSES, NARSES_TROOPS, 10, 2, ['Long Fei', 'Jabel', 'Rosa'], 'me', 292),
    ('Narses inf+arch 1k', NP, {'inf': 500, 'cav': 200, 'arch': 300}, 'solo',
     NARSES_ED20, {'inf': 61_785, 'cav': 0, 'arch': 61_785}, 10, 2, ['Long Fei', 'Jabel', 'Rosa'], 'me', 397),
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
    # Narses never had a buff; MY 20% Enemy Squads' Defense bonus was still active here and the panel
    # shows his defence through it (divided by 1.20, not multiplied by 0.80).  Scoring with plain
    # NARSES put 20% too much defence on him and cost 0.14 of k.
    ('Narses 500 solo', NP, {'inf': 250, 'cav': 100, 'arch': 150}, 'solo',
     NARSES_ED20, {'inf': 61_785, 'cav': 24_714, 'arch': 37_071}, 10, 2,
     ['Long Fei', 'Jabel', 'Rosa'], 'them', 48_561),
    # Pure infantry, fought after that bonus had lapsed too -- hence its own panel
    # rather than NP, and his true undiminished defence, so plain NARSES is right for this one.
    ('Narses 1500 pure inf', NARSES_1500_INF_PANEL, {'inf': 1500, 'cav': 0, 'arch': 0}, 'solo',
     NARSES, {'inf': 61_785, 'cav': 24_714, 'arch': 37_071}, 10, 2,
     ['Long Fei', 'Jabel', 'Rosa'], 'them', 15_598),
    # NO HEROES ON EITHER SIDE and "No Special Stats Bonuses" -- the damage core with the entire
    # skill layer switched off.  The cleanest calibration point in the set.  I won, so my 687
    # losses measure HIS output.
    ('Narses 1000 NO HEROES', NOHERO_PANEL, {'inf': 500, 'cav': 200, 'arch': 300}, 'solo',
     NOHERO_ENEMY, {'inf': 27_866, 'cav': 27_867, 'arch': 27_867}, 10, 2, [], 'me', 687),
    # A DEFEAT, which is why it is scored on HIS losses: I am wiped, so my 500 is censored at the
    # squad size and measures nothing, while his 16,059 is uncensored and measures MY output --
    # the exact quantity the round-count work says is over-modelled.  Sized for power: 500 troops
    # runs ~90 rounds, so both observables average over many rounds (his losses carry 7% noise
    # against 22% for the 10,000-troop marches).
    ('Narses 500 NO HEROES', NOHERO_PANEL_V2, {'inf': 250, 'cav': 100, 'arch': 150}, 'solo',
     NOHERO_ENEMY, {'inf': 27_866, 'cav': 27_867, 'arch': 27_867}, 10, 2, [], 'him', 16_059),
    # Yang alone at the same size and target -- the matched partner to the fight above.  A
    # VICTORY with Narses wiped, so HIS losses censor at 83,600 and mine are the observable.
    ('Narses 500 YANG ONLY', YANG_PANEL_V2, {'inf': 250, 'cav': 100, 'arch': 150}, 'solo',
     NOHERO_ENEMY, {'inf': 27_866, 'cav': 27_867, 'arch': 27_867}, 10, 2, [], 'me', 232),
    # Charles alone, the other half of the bisection at the same size.  Also a victory with Narses
    # wiped, so again my losses are the observable.  79 + 144 = 223 (residents 277).
    ('Narses 500 CHARLES ONLY', CHARLES_PANEL_V2, {'inf': 250, 'cav': 100, 'arch': 150}, 'solo',
     NOHERO_ENEMY, {'inf': 27_866, 'cav': 27_867, 'arch': 27_867}, 10, 2, [], 'me', 223),
    # Sophia alone, third rung of the 500-troop bisection.  Victory, Narses wiped, so my losses
    # (102 + 186 = 288, residents 212) are the observable.
    ('Narses 500 SOPHIA ONLY', SOPHIA_PANEL_V2, {'inf': 250, 'cav': 100, 'arch': 150}, 'solo',
     NOHERO_ENEMY, {'inf': 27_866, 'cav': 27_867, 'arch': 27_867}, 10, 2, [], 'me', 288),
    # The SAME Sophia at a different mix -- her cavalry 20% -> 50% of the march.  The pre-
    # registered troop-share test.  Victory, Narses wiped, my losses 83 + 151 = 234 (residents 266).
    ('Narses 500 SOPHIA 100/250/150', SOPHIA_PANEL_V2, {'inf': 100, 'cav': 250, 'arch': 150},
     'solo', NOHERO_ENEMY, {'inf': 27_866, 'cav': 27_867, 'arch': 27_867}, 10, 2, [], 'me', 234),
]


# Truegold troop abilities are per-troop-type research, so a low-TG opponent lacks what a TG8
# account has.  Keyed by fight label; anything absent is uncapped.
#
# ONLY THE PROVEN CAP IS APPLIED.  Narses' Long Fei shows three rows -- his skills, no Unyielding
# Shield -- with 61,785 infantry over ~152 rounds, so his TG2 infantry demonstrably lacks it.
# His Jabel and Rosa each show ONE troop-ability row where my TG8 cavalry shows three and archers
# two, so he is short there too, but WHICH ability each row is cannot be read from the panel.
# Guessing it (cav=0, arch=1) overshoots badly -- Narses' six go to mean|log| 0.132, against
# 0.034 for the infantry cap alone and 0.096 for no cap at all.  So the guess is left out.
# Narses at TG2 predates the reforges entirely: they sit above the base abilities he does not
# even have on infantry.  A reforge adds no Battle Details row, so his rows cannot confirm this
# directly -- but a TG2 account holding a top-tier reforge is not credible.
# Narses' heroes are not fully upgraded: his tooltips read Long Fei Lv.4, Jabel Lv.5, Rosa Lv.4.
# heroes.py now holds MAX-level magnitudes from the site, so his have to be scaled back down.
# Round-trip check: Long Fei at L4 comes out 40 / 20 / 80, exactly his in-game tooltips.
NARSES_LEVELS = {'Long Fei': 4, 'Jabel': 5, 'Rosa': 4}


ENEMY_NO_REFORGE = {'Narses 1000 NO HEROES', 'Narses 500 NO HEROES', 'Narses 500 YANG ONLY', 'Narses 500 CHARLES ONLY', 'Narses 500 SOPHIA ONLY', 'Narses 500 SOPHIA 100/250/150', 'Narses pure-arch 5k', 'Narses mixed atk 10k', 'Narses mixed def 5k',
                    'Narses inf+arch 1k', 'Narses 500 solo', 'Narses 1500 pure inf'}

# My own lineup is Charles / Sophia / Yang in every fight EXCEPT the heroless one, where the
# report reads "Vacant" in all three slots on both sides.
MY_HEROES = {'Narses 1000 NO HEROES': [], 'Narses 500 NO HEROES': [],
             'Narses 500 YANG ONLY': ['Yang'], 'Narses 500 CHARLES ONLY': ['Charles'], 'Narses 500 SOPHIA ONLY': ['Sophia'],
             'Narses 500 SOPHIA 100/250/150': ['Sophia']}
DEFAULT_MY_HEROES = ['Charles', 'Sophia', 'Yang']

ENEMY_TROOP_ABILITIES = {
    # The heroless report shows his TG2 rows DIRECTLY: one cavalry ability (Ambusher, 25 triggers)
    # and one archer (7), with the infantry section blank on his side.  No longer a guess.
    'Narses 1000 NO HEROES': {'inf': 0, 'cav': 0, 'arch': 1},
    # Same two rows on his side of the 500 report: cavalry Ambusher 17, one archer ability 9.
    'Narses 500 NO HEROES':  {'inf': 0, 'cav': 0, 'arch': 1},
    'Narses 500 YANG ONLY':  {'inf': 0, 'cav': 0, 'arch': 1},
    'Narses 500 CHARLES ONLY': {'inf': 0, 'cav': 0, 'arch': 1},
    'Narses 500 SOPHIA ONLY': {'inf': 0, 'cav': 0, 'arch': 1},
    'Narses 500 SOPHIA 100/250/150': {'inf': 0, 'cav': 0, 'arch': 1},
    'Narses pure-arch 5k':   {'inf': 0},
    'Narses mixed atk 10k':  {'inf': 0},
    'Narses mixed def 5k':   {'inf': 0},
    'Narses inf+arch 1k':    {'inf': 0},
    'Narses 500 solo':       {'inf': 0},
    'Narses 1500 pure inf':  {'inf': 0},
}


def score(n=200, seed=1234):
    rng = random.Random(seed)
    out = []
    for lbl, mp, mt, mr, ep, et, tier, etg, eh, side, obs in FIGHTS:
        vals = []
        for _ in range(n):
            a = Side('A', mp, dict(mt), heroes=MY_HEROES.get(lbl, DEFAULT_MY_HEROES), role=mr,
                     joiners=[], hero_stats=False, tier=11, tg=8, widget_default=0.0)
            d = Side('D', ep, dict(et), heroes=eh, role=('solo' if mr == 'garrison' else 'garrison'),
                     joiners=[], hero_stats=False, tier=tier, tg=etg, widget_default=0.0,
                     troop_abilities=ENEMY_TROOP_ABILITIES.get(lbl, {}),
                     troop_reforges=(set() if lbl in ENEMY_NO_REFORGE else None),
                     skill_levels=(NARSES_LEVELS if lbl in ENEMY_NO_REFORGE else {}))
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
    # This line used to label mean|log k| as "rms log err".  They are not the same and mean-abs
    # is always the smaller, so every "rms log err" quoted in reports.py before 2026-09-09 is
    # really mean-abs.  Both are printed now: comparisons across those older notes stay valid
    # (both are monotone in the errors), but the number never meant what it said.
    logs = [math.log(k) for k in ks]
    rms = math.sqrt(sum(x * x for x in logs) / len(logs))
    print(f'\n  mean k {statistics.mean(ks):.2f}   spread {min(ks):.2f}-{max(ks):.2f}'
          f'   rms log err {rms:.3f}   mean|log| {statistics.mean([abs(x) for x in logs]):.3f}')
