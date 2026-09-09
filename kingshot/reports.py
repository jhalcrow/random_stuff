#!/usr/bin/env python3
"""Live battle reports used to calibrate and validate the simulator.

All three were fought on 2026-09-08 by [PRO]Belisarius (X:480 Y:684) against the same
target, [ORM]N2DBLG (X:480 Y:683), within minutes of each other, with the same garrison
lineup (Charles / Sophia / Vivian) and 10,000 troops sent by the leader every time.  That
makes them a clean controlled experiment: exactly one variable changes between any pair.

The per-player "kills" field tracks the defender's *Injured* bucket; the Lightly Injured
bucket is a fixed 1.855x of it in every report from both sides, so total defender
casualties = kills * 2.855.  That is how the 50/20/30 total is reconstructed (its overview
screen was not captured).

  python3 kingshot/reports.py      # replay all three through the simulator
"""
import random, statistics, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sim import Side, battle_mc, score

WOUND_SCALE = 2.855          # total casualties per unit of the "kills"/Injured field
SENT = 10_000                # troops the leader sent in every one of the three

# Stat Bonuses panels, read straight off the reports (these are in-battle totals: city buffs +
# hero expedition stats + gear + widgets, so they are fed in with hero_stats=False).
ME_SOPHIA = {'inf': dict(attack=1617.3, defense=1594.3, lethality=2088.3, health=1799.0),
             'cav': dict(attack=1507.3, defense=1484.7, lethality=1996.0, health=1725.4),
             'arch': dict(attack=1509.6, defense=1484.5, lethality=2017.2, health=1736.7)}
ME_AVA    = {'inf': dict(attack=1617.3, defense=1594.3, lethality=2373.7, health=1799.0),
             'cav': dict(attack=1599.0, defense=1576.5, lethality=2304.5, health=1752.4),
             'arch': dict(attack=1509.6, defense=1484.5, lethality=2293.4, health=1736.7)}
ENEMY     = {'inf': dict(attack=2225.7, defense=2496.3, lethality=2165.5, health=2165.5),
             'cav': dict(attack=1937.6, defense=2145.1, lethality=1880.2, health=1660.2),
             'arch': dict(attack=1921.1, defense=2134.1, lethality=2039.2, health=1796.7)}
GARRISON = ['Charles', 'Sophia', 'Vivian']

# (label, cavalry hero, my stat panel, my troops, enemy troops, reported "kills")
REPORTS = [
    ('Sophia 60/40/0', 'Sophia', ME_SOPHIA, {'inf': 6006, 'cav': 4000, 'arch': 1},
     {'inf': 6002, 'cav': 4000, 'arch': 0}, 1433),
    ('Ava 60/40/0',    'Ava',    ME_AVA,    {'inf': 6006, 'cav': 4000, 'arch': 0},
     {'inf': 6004, 'cav': 4000, 'arch': 0},  894),
    ('Ava 50/20/30',   'Ava',    ME_AVA,    {'inf': 5006, 'cav': 2000, 'arch': 3000},
     {'inf': 6004, 'cav': 4000, 'arch': 0}, 1573),
    # Only two Chenko joiners landed on this one.  The infantry icon reads Lv 11.0 here against
    # Lv 10.9 in the other three, which is NOT a troop upgrade: the leader's own 10,000 are TG8
    # T11 in every report, and the icon shows a weighted AVERAGE tier, so it only moves with the
    # handful of joiner troops (6 of them, some below T11, drag it to 10.9; 2, both T11, leave it
    # at 11.0).  Troop quality is therefore constant across all four -- and the reading doubles as
    # an independent check on the joiner counts.
    ('Sophia 50/20/30', 'Sophia', ME_SOPHIA, {'inf': 5002, 'cav': 2000, 'arch': 3000},
     {'inf': 6004, 'cav': 4000, 'arch': 0},  580, 2),
]
JOINERS_DEFAULT = 4

# Stat-panel predictions the calibration in sim.py has to reproduce (see the fit in sim.py).
# Every one of the 24 values lands within 12 points of ~2000, i.e. under 0.6%.
PANEL_TOLERANCE = 12.0


def observed(kills):
    """Kill ratio implied by a report: defender casualties / my casualties (I was wiped each time)."""
    return kills * WOUND_SCALE / SENT


def match_buffs(stats, pct=20.0):
    """Strip a multiplicative buff stack of pct% off every line of a stat panel.

    All three reports were fought while the defender had roughly a 20% buff-and-pet stack up
    and the attacker had none, so the raw panels describe a badly one-sided fight.  Because the
    engine's kill term is super-linear in the stat ratio, conclusions drawn from that regime do
    not transfer to an even one -- run comparisons through here before trusting them.  A uniform
    multiplicative buff applied to all four lines of BOTH sides cancels out of the kill ratio,
    so this also stands in for "we both have our buffs up".
    """
    return {t: {k: (100 + v) / (1 + pct / 100) - 100 for k, v in s.items()}
            for t, s in stats.items()}


def replay(n=400, seed=31):
    rng = random.Random(seed)
    rows = []
    for label, cav, mine, my_t, en_t, kills, *rest in REPORTS:
        nj = rest[0] if rest else JOINERS_DEFAULT
        ks = []
        for _ in range(n):
            a = Side('A', mine, dict(my_t), heroes=['Charles', cav, 'Yang'], role='rally',
                     joiners=['Chenko'] * nj, hero_stats=False)
            d = Side('D', ENEMY, dict(en_t), heroes=GARRISON, role='garrison', hero_stats=False)
            ks.append(score(battle_mc(a, d, rng), 'A'))
        rows.append((label, observed(kills), statistics.mean(ks)))
    return rows


if __name__ == '__main__':
    print(f'{"report":18s} {"observed":>9s} {"sim":>8s} {"sim/obs":>9s}')
    for label, obs, sim in replay():
        print(f'  {label:16s} {obs:9.3f} {sim:8.3f} {sim/obs:9.2f}')
    print('\nControlled comparisons (same target, same 10,000 troops sent):')
    k = {r[0]: r[5] for r in REPORTS}
    print(f'  hero swap at 60/40/0 : Sophia / Ava = {k["Sophia 60/40/0"]/k["Ava 60/40/0"]:.2f}x')
    print(f'  ratio swap with Ava  : 50/20/30 / 60/40/0 = {k["Ava 50/20/30"]/k["Ava 60/40/0"]:.2f}x')
    print(f'  best observed        : Ava 50/20/30 beats Sophia 60/40/0 by '
          f'{k["Ava 50/20/30"]/k["Sophia 60/40/0"]:.2f}x')
    print('\nHero x composition interaction, observed (all normalised to four joiners):')
    print('                  60/40/0   50/20/30   effect of archers')
    print('    Ava             894       1573        x1.76')
    print('    Sophia         1433        783        x0.55')
    print('  interaction = 1.76 / 0.55 = 3.2x.  No setting of Terror Deathblow or Ava\'s skill')
    print('  magnitudes gets the simulator past ~1.6, so this gap is STRUCTURAL: the model does')
    print('  not capture how much a broad all-scope buffer (Ava) lifts the archer hero.  Yang')
    print('  scored 588 kills on 3,000 archers next to Ava and only 103 next to Sophia.')
    print('  Do not trust the simulator to compare across troop compositions until this is fixed.')


# ---------------------------------------------------------------- solo attacks
# Two solo marches on the same Lv30 Gilded Baron 52 seconds apart, byte-identical setup.
# Uniquely useful because the Baron's hero slots all read "Vacant" (no defender skills at all)
# and because running the same config twice measures the engine's noise directly.
SOLO_PANEL = {'inf': dict(attack=1960.8, defense=1933.2, lethality=1802.9, health=1799.0),
              'cav': dict(attack=1828.7, defense=1801.7, lethality=1722.6, health=1725.4),
              'arch': dict(attack=1831.5, defense=1801.4, lethality=1741.1, health=1736.7)}
BARON = {t: dict(attack=3150.0, defense=3150.0, lethality=3150.0, health=3150.0)
         for t in ('inf', 'cav', 'arch')}
SOLO_TROOPS = {'inf': 101_805, 'cav': 40_722, 'arch': 61_083}     # 50/20/30, 203,610 total
BARON_TROOPS = {'inf': 178_000, 'cav': 178_000, 'arch': 178_000}  # 534,000, flat thirds

# (label, defender losses, my losses, hero-attributed kills)
SOLO_RUNS = [('Baron 203,610 A', 180_529, 203_610, 54_601),
             ('Baron 203,610 B', 159_421, 203_610, 49_435),
             ('Baron 100,000',    62_191, 100_000, 20_595),
             ('Baron 50,000',     15_117,  50_000,  3_065)]

# Per-skill nuke output across the four: (march size, kills, triggers) for each damage row.
# Per-trigger magnitude scales as march_size^1.15 (mean over the four rows), while trigger
# counts scale roughly as sqrt(march_size) -- i.e. with battle length.  Total nuke damage is
# the product of the two, which is why the hero share stays near 30% except in the shortest
# fight (50,000 troops, only 20%: too few rounds for the nukes to accumulate).
NUKE_ROWS = {
    'Sophia r5': [(203_610, 5_007, 7), (203_610, 2_193, 3), (100_000, 1_955, 7), (50_000, 233, 2)],
    'Yang r1':   [(203_610, 19_304, 25), (203_610, 17_791, 25), (100_000, 6_582, 16), (50_000, 1_460, 10)],
    'Yang r2':   [(203_610, 18_818, 14), (203_610, 18_969, 17), (100_000, 9_401, 14), (50_000, 957, 4)],
    'Yang r5':   [(203_610, 11_472, 14), (203_610, 10_482, 13), (100_000, 2_657, 5), (50_000, 415, 2)],
}

# What these two settled:
#  * NOISE: kills 159,421 vs 180,529 -> CV 8.8% on n=2, against the simulator's 7.6% for this
#    config.  My own casualties were byte-identical both times (409 injured, 203,201 lightly),
#    so only the damage DEALT varies.
#  * WIDGETS: the solo panel's infantry lethality reads 1802.9%, and 1802.87% is what the rally
#    panel gives once the +15% rally widget is divided out.  Rally widgets do not fire on a solo
#    march, confirmed to 0.03 points.
#  * RESEARCH DRIFT since the rallies: attack and defense up 317-343 points on every type,
#    lethality and health unchanged to 0.1.  Any comparison across that boundary must use each
#    report's own panel.
#  * ENGINE TERM: subtract the hero-attributed kills and compare the remainder to the simulator,
#    which has no direct-damage channel at all.  Across a 4x range of march size the ratios are
#    0.88 / 1.00 / 0.90 / 1.12, mean 0.98.  Single-run noise is ~9%, so the worst miss is about
#    one sigma.  The sqrt(n_u * army_min) * A/D kills formula is correct -- validated in solo
#    role, against a different opponent with no heroes, from 50,000 to 203,610 troops.  The
#    entire remaining shortfall is the missing nuke channel (20-33% of observed damage).
#  * NUKES: per-trigger damage is stable run to run (Sophia 715 vs 731, Yang row5 819 vs 806),
#    while trigger COUNTS swing hard (Sophia row5 fired 7 times then 3).  So model nuke magnitude
#    as a deterministic function of state and the trigger count as the random variable.
#  * CORRECTION to the note in skill_log.py: trigger cadence is NOT generally deterministic.
#    Only some rows are fixed (Charles rows 1-3 and Yang row 1 were identical across both runs);
#    the rest vary.  Vivian's 12/12/12 across three rallies was a fixed row, not a general rule.


# ---------------------------------------------------------------- first win
# Solo, 10,000 troops at 50/20/30, vs [H8s]Narses (Long Fei / Jabel / Rosa), 2026-09-08 20:11.
# VICTORY: their 123,570 wiped for 239 of mine (85 injured + 154 lightly).
NARSES = {'inf': dict(attack=520.9, defense=514.3, lethality=251.4, health=294.6),
          'cav': dict(attack=356.1, defense=345.5, lethality=259.4, health=227.3),
          'arch': dict(attack=474.3, defense=467.2, lethality=311.3, health=243.9)}
NARSES_TROOPS = {'inf': 41_190, 'cav': 41_190, 'arch': 41_190}

# New damage rows for the catalogue: Long Fei deals damage on row 3, Jabel on row 2, Rosa on none.
NARSES_ROWS = {'Long Fei': [(8, 0), (1, 0), (11, 11)],
               'Jabel': [(6, 0), (17, 14), (1, 0), (1, 0)],
               'Rosa': [(4, 0), (1, 0), (1, 0), (1, 0)],
               'my Yang': [(9, 5_922), (6, 4_535), (4, 0), (5, 0), (4, 435)]}

# "Residents" is the SURVIVORS row: squad - casualties = residents, checked on six reports
# across both sides.  It retro-confirms casualty totals that were never shown directly.

# OPEN PROBLEM this fight exposed -- enemy troop base stats are a free parameter.
# Reading the icon as tier + Truegold level ("Lv 11.0" badge 8 = T11 TG8, which matches the
# leader's own troops exactly) puts Narses and the Baron at T10 TG2.  That reading improves the
# Narses fit (my losses 398 sim vs 239 observed, from 672 under the old T10/TG8 assumption) but
# blows up the Baron fit (207,752 vs 117,957 observed, from 111,933).  The two cannot both be
# right, and the likeliest explanation is that the Gilded Baron is an event monster with a
# scripted stat block rather than normal troops.
#
# CONSEQUENCE for the earlier claim: the SHAPE of the engine validation stands -- base stats are
# constant across the four Baron runs, so the march-size scaling result is untouched.  But the
# ABSOLUTE level of that fit rests on an unobservable, so "mean ratio 0.98" is weaker than it
# looked.  What would settle it is any fight where the opponent's troop tier and Truegold level
# are known rather than inferred.


# ---------------------------------------------------------------- first defence
# Narses attacked with his whole 123,570 (T10 TG2, confirmed by the player, not inferred).
# I garrisoned 5,000 at 50/20/30 with Charles / Sophia / Yang and held, losing 292.
DEFENCE = dict(my_troops={'inf': 2_500, 'cav': 1_000, 'arch': 1_500}, my_losses=292,
               enemy=NARSES, enemy_troops=NARSES_TROOPS, enemy_losses=123_570)

# DEFENDER WIDGETS DO NOT FIRE WHEN DEFENDING YOUR OWN CITY.
# My Stat Bonuses panel is byte-identical across a solo attack and this defence
# (inf 1960.8 / 1933.2 / 1802.9 / 1799.0), while the rally panel shows Yang's rally
# lethality widget applied (1802.9 -> 2088.3, +15%).  Charles' defender-health and Sophia's
# defender-lethality widgets contributed nothing here.  Either they require reinforcing
# ANOTHER player's city, or the widget slots are misclassified in heroes.py.  Every garrison
# recommendation made before this report assumed they fire.

# COMBAT ALWAYS RUNS UNTIL ONE SIDE IS WIPED (confirmed by the player).  Nothing is ever
# censored, so the winner's own losses are the informative quantity in every report.  Narses'
# 123,570 wiped in both fights with an identical 43,251 / 80,319 split, which re-confirms that
# the wound split is deterministic given a full wipe.

# FIRST FULLY-SPECIFIED TWO-SIDED TESTS (both tiers and Truegold levels known).
# The first pass got these badly wrong by assuming max widgets on everyone.  Narses has NO
# widget on two of his three heroes and only a level-1 widget on Jabel, while my own defender
# widgets are proven not to fire at all (above).  Both errors were real and they pointed in
# opposite directions, so they partly cancelled:
#
#   fight                  observed   naive sim         corrected sim
#   I attack with 10,000        239   391 (1.63x)       297 (1.24x)
#   I defend with  5,000        292   308 (1.05x)       400 (1.37x)
#
# The "excellent 1.05x" on defence was luck, and the attack/defence ASYMMETRY reported from it
# does not exist.  What is left is a single uniform bias: the model over-predicts my losses by
# roughly 30% in both directions, which is a far more tractable shape than two separate faults.
#
# That residual is the expected signature of the missing nuke channel.  Hero direct damage was
# 11% of the kills in the defence fight and at least 9% in the attack; without it the enemy
# survives extra rounds in the simulator, so my troops eat extra rounds of incoming damage, and
# the engine's positive feedback turns a ~10% damage shortfall into a ~30% loss overshoot.
# Implementing the nuke channel should collapse both ratios toward 1.0 -- that is the test.
#
# LESSON: never assume an opponent's widgets are maxed.  Side.widget_levels now takes a per-hero
# scale (1.0 = max, 0.0 = not unlocked) with widget_default for the rest.  Every opponent model
# built before this -- run.py's 900-trio ranking, elo.py, gear.py -- assumed max widgets on both
# sides.  That is harmless where both sides are mirrored but not where they are not.

# The Gilded Baron is confirmed as an event monster with a scripted stat block: a real player
# at T10 TG2 fits the engine, while the Baron at the same nominal tier/TG gives 204,077 against
# 117,957 observed.  The Baron-based "mean ratio 0.98" should be read as validating the SHAPE
# of the march-size scaling only; the Narses pair is now the real absolute check.


# ---------------------------------------------------------------- large rally
# Rally on [GOD]Earthling, mail 223407016665003 (older research state, TG7 troops).
# VICTORY: their 663,292 wiped, I lost 177,243 of 923,309 -- uncensored on my side.
BIG_RALLY = dict(
    me={'inf': dict(attack=2048.1, defense=2030.0, lethality=2779.8, health=2230.9),
        'cav': dict(attack=2024.2, defense=2003.6, lethality=2739.4, health=2210.7),
        'arch': dict(attack=1907.9, defense=1887.3, lethality=2706.5, health=2174.6)},
    enemy={'inf': dict(attack=2176.3, defense=2237.3, lethality=2285.7, health=2276.2),
           'cav': dict(attack=2052.0, defense=2108.3, lethality=2099.5, health=2080.4),
           'arch': dict(attack=2179.1, defense=2240.2, lethality=2291.5, health=2279.6)},
    my_troops={'inf': 363_155, 'cav': 158_639, 'arch': 401_515},      # 923,309
    enemy_troops={'inf': 0, 'cav': 84_994, 'arch': 578_298},          # 663,292, NO infantry
    my_losses=177_243, enemy_losses=663_292,
    my_heroes=['Charles', 'Ava', 'Yang'], enemy_heroes=['Triton', 'Thrud', 'Yang'],
    contributors=[('Belisarius', 299_415, 80_189), ('Bjorn', 241_601, 73_104)],  # rest unlisted
    # Yang vs Yang, both sides' damage rows visible in one fight:
    my_yang=[(3, 27_134), (2, 20_270), (3, 17_103)],
    their_yang=[(2, 7_364), (5, 16_623), (4, 15_654)],
)

# A RALLY IS NOT ONE ARMY WITH ONE STAT SHEET.
# The Stat Bonuses panel shows the LEADER's bonuses, but each contributing player's troops fight
# with their own.  I sent 299,415 of the 923,309 -- 32% -- and the simulator applies my sheet to
# all of it, inflating the rally badly: it predicts 101,480 of my troops lost against 177,243
# observed (0.57x).  Scaling the whole rally to ~0.85x of my own sheet reproduces the observed
# losses, which is what you would expect when two thirds of it is joiners weaker than the leader.
# Every rally recommendation in run.py / elo.py treats the rally as homogeneous at the leader's
# stats and therefore overstates rallies relative to solo marches.
#
# THIS ALSO BREAKS the "one uniform bias" story from the previous commit.  Sim-over-observed on
# my own losses now reads 1.24x and 1.37x on single-player solo fights but 0.51x on this rally.
# The errors point in opposite directions, so the missing nuke channel cannot be the whole
# explanation; the multi-player rally has a separate and larger fault of its own.
#
# NUKE CHANNEL: this is the only report where BOTH sides' damage rows are visible for the same
# hero.  Per trigger my Yang did 9,045 / 10,135 / 5,701 against their 3,682 / 3,325 / 3,914 --
# a ratio of 1.46x to 3.05x.  If a nuke scaled exactly like a troop volley (sqrt(n_u * army_min)
# * A/D, with army_min identical for both sides) mine should have hit 0.89x theirs.  So the
# volley analogy, which held across march sizes against one target, does NOT carry across the
# two sides of a fight.  Confounded here by the multi-player rally, unknown joiner skills and
# unknown widget levels at that time -- a solo fight where both sides' rows are visible would
# settle it cleanly.


# ---------------------------------------------------------------- Terry defence
# Solo, one player each side, BOTH sides' Yang damage rows visible -- the clean two-sided nuke
# test.  Terry attacked my 10,000 (50/20/30) with 226,932 and wiped me; he lost 9,734.
# Both sides T11 TG8 (Lv 11.0, badge 8).  Mail 223407017217906.
TERRY = {'inf': dict(attack=1216.4, defense=897.5, lethality=1227.1, health=1281.4),
         'cav': dict(attack=1354.0, defense=988.7, lethality=1170.0, health=1032.2),
         'arch': dict(attack=1482.7, defense=1095.2, lethality=1318.2, health=1111.9)}
TERRY_TROOPS = {'inf': 124_813, 'cav': 22_693, 'arch': 79_426}
TERRY_FIGHT = dict(my_panel={'inf': dict(attack=2585.6, defense=2009.9, lethality=2278.6, health=1920.5),
                             'cav': dict(attack=2413.9, defense=1873.4, lethality=2180.4, health=1840.8),
                             'arch': dict(attack=2417.4, defense=1873.2, lethality=2203.3, health=1853.0)},
                   my_troops={'inf': 5_000, 'cav': 2_000, 'arch': 3_000}, my_losses=10_000,
                   enemy_losses=9_734, my_heroes=['Charles', 'Sophia', 'Yang'],
                   enemy_heroes=['Amadeus', 'Ava', 'Yang'],
                   my_yang=[(5, 274), (1, 0), (3, 0)], their_yang=[(6, 526), (3, 412), (2, 0), (2, 0)])

# ENGINE: I was wiped, so Terry's losses are the uncensored quantity.  Sim gives 18,966 against
# 9,734 observed (1.95x) with my defender widgets off, 25,206 (2.59x) with them on.
#
# UNEXPLAINED PANEL CHANGE: in this report attack sits 27% above defence and lethality 18% above
# health, where in every earlier non-rally panel each pair matched within 1.5%.  That is not the
# clean +15% signature of a widget, so it is NOT read as the defender widget firing -- it looks
# like an attack/lethality buff.  Per-report panels mean it blocks nothing, but the cause is
# unknown and it is a reminder that the panel carries buffs I cannot see or name.

# NUKE CHANNEL -- three guesses, three failures.  Every Yang row-1 observation:
#
#   fight                     army_min  own arch  per trigger    target D
#   Baron 203,610              203,610    61,083          772  10,562,500
#   Baron 100,000              100,000    30,000          411  10,562,500
#   Baron  50,000               50,000    15,000          146  10,562,500
#   Narses attack               10,000     3,000          658     242,403
#   Narses defence               5,000     1,500          462     242,403
#   Terry defence, mine         10,000     3,000           55   1,377,746
#   Terry defence, theirs       10,000    79,426           88   4,262,953
#   Earthling rally, mine      663,292   401,515        9,045   4,815,172
#   Earthling rally, theirs    663,292   578,298        3,682   4,965,158
#
# Ruled out:
#   * proportional to the caster's own troops -- 3,000 archers gave 658/trigger against Narses
#     and 55 against Terry, and Yang once scored 203 kills with ZERO archers
#   * a simple A/D volley -- it misses 2.5x LOW in the Terry fight and 1.6-3.4x HIGH in the
#     Earthling rally, opposite directions, so no constant correction fixes both
#   * purely army_min -- identical army_min for both sides of the Terry fight, 1.6x apart
#
# Six variables move across these nine points with one report per combination.  Opportunistic
# reports will not crack this; it needs a designed sweep that moves ONE variable at a time.


# ------------------------------------------------- Notes on Special Bonuses (Terry fight)
# The report's own breakdown of what the Stat Bonuses panel is made of.  Header reads
# "Stats Bonuses include the following Special Bonuses", which settles a standing question:
# the panel already has all of this baked in, so feeding panels straight into Side(stats=...)
# with special={} is correct and nothing is double counted.
SPECIAL_BONUSES = {           # (mine, Terry's) in %
    'Squads Attack':               (20.0, 0.0),
    'Squads Lethality':            (20.0, 0.0),
    'Enemy Squads Defense':       (-20.0, -0.0),
    'Enemy Defense Penalty (Pet)':(-10.0, -6.0),
    'Enemy Lethality Penalty (Pet)':(-5.0, -4.0),
    'Enemy Health Penalty (Pet)':  (-5.0, -3.5),
    'Attack Bonus (Pet Skill)':    (10.0, 6.0),
    'Defense Bonus (Pet Skill)':   (10.0, 7.0),
    'Lethality Bonus (Pet Skill)': (10.0, 6.0),
    'Health Bonus (Pet Skill)':    (10.0, 7.0),
    'Appointment Squads Attack':    (5.0, 0.0),
}

# DECOMPOSITION, my two defence panels (Narses fight, unbuffed -> Terry fight, buffed).
# Pet skills are passive so they sit in both panels and cancel out of the ratio; only the
# temporary buffs differ.
#
#   stat        Narses    Terry   observed   temp buffs   residual
#   attack      1960.8   2585.6     1.3032   1.25 (20+5)    1.0425
#   lethality   1802.9   2278.6     1.2500   1.20 (20)      1.0417
#   defense     1933.2   2009.9     1.0377   1.00           1.0377
#   health      1799.0   1920.5     1.0640   1.00           1.0640
#
# Attack and lethality leave the SAME 1.042 residual, which is research done between the two
# fights.  This independently re-validates the special-bonus model on a fresh set of bonuses:
# sources ADD within a stat (Squads' Attack 20 + Appointment 5 = 25) and the sum multiplies
# (100 + base) exactly once -- the same rule the widget stacking followed.
#
# CAVEAT THIS CREATES, and it reaches backwards.  The "Enemy X Penalty" lines sit in MY column
# but must be reflected in the OPPONENT'S displayed lines -- a debuff I inflict cannot be part
# of my own stat sheet.  So every opponent panel stored in this file is that opponent AS SEEN
# THROUGH MY DEBUFF LOADOUT, not their true sheet.  Reproducing the fight it came from is fine;
# reusing it for a fight where my pets or buffs differ is not.  That applies to N2DBLG, NARSES,
# BARON, TERRY and the Earthling rally alike.
#
# It also retro-explains the N2DBLG analysis: "he had a 20% buff stack and I did not" is
# literally these Squads' Attack / Squads' Lethality / Enemy Squads' Defense lines.
#
# What it does NOT change: the Terry engine fit (1.95x) and the nuke problem both stand, since
# both were computed from panels that already included all of this.


# ------------------------------------------------- Terry attacks (same special bonuses)
# Two attacks on Terry with the Special Bonuses panel verified identical to the defence above,
# so buff state is held constant across all three.  I was wiped in both; Terry's losses are the
# uncensored quantity.  Two cells of the designed sweep: 20,000 at 50/20/30, and 10,000 pure
# infantry (the zero-archer test).
TERRY_ATTACKS = [
    dict(label='20,000 at 50/20/30', my_troops={'inf': 10_000, 'cav': 4_000, 'arch': 6_000},
         enemy_troops={'inf': 94_555, 'cav': 37_822, 'arch': 56_733},
         my_losses=20_000, enemy_losses=22_570,
         my_yang=[(9, 596), (7, 1_020), (8, 0), (1, 0), (5, 487)],
         their_yang=[(8, 608), (6, 908), (5, 0), (6, 757)]),
    dict(label='10,000 ALL INFANTRY', my_troops={'inf': 10_000, 'cav': 0, 'arch': 0},
         enemy_troops={'inf': 113_467, 'cav': 45_386, 'arch': 68_079},
         my_losses=10_000, enemy_losses=937,
         my_yang=[(3, 64), (1, 0), (4, 0)],
         their_yang=[(9, 558), (7, 529), (6, 0), (2, 0), (5, 303)]),
]
TERRY_ATTACK_PANEL = {  # mine; Terry's is TERRY_ATTACK_ENEMY below
    'inf': dict(attack=2555.7, defense=1994.3, lethality=2266.1, health=1909.9),
    'cav': dict(attack=2384.0, defense=1857.9, lethality=2167.9, health=1830.1),
    'arch': dict(attack=2387.5, defense=1857.6, lethality=2190.8, health=1842.4)}
TERRY_ATTACK_ENEMY = {
    'inf': dict(attack=1537.8, defense=1140.5, lethality=1255.0, health=1309.5),
    'cav': dict(attack=1378.4, defense=1001.0, lethality=1180.1, health=1042.4),
    'arch': dict(attack=1507.1, defense=1107.6, lethality=1328.3, health=1122.1)}

# ENGINE BIAS IS NOW CONSISTENT, which is the useful part.  Three Terry fights, buffs held
# constant, sim over-predicts the losing side's damage output by an almost identical factor:
#     10,000 defending  observed  9,734   sim 18,966   1.95x
#     20,000 attacking  observed 22,570   sim 45,611   2.02x
#     10,000 all-inf    observed    937   sim  1,827   1.95x
# A stable ~1.97x multiplicative error is a missing term, not chaos, and is a far better target
# than the scattered ratios from the mixed earlier reports.
# Possible pattern, flagged as a hypothesis rather than a finding: in the Terry fights I lost and
# MY damage is over-predicted; in the Narses fights Narses lost and HIS damage was over-predicted
# (1.24x, 1.37x).  That would mean the real engine punishes the losing side harder than the model
# does.  The Earthling rally does not fit that reading, but it has the heterogeneous-rally
# confound already accounted for separately.

# NUKE REGRESSION (nuke_fit.py) -- 13 observations of Yang row 1, all drivers fitted at once
# instead of eyeballing pairs, which is what produced three wrong hypotheses in a row.
#   single drivers:  army_min    +0.82  (rms x2.92)   <- much the strongest alone
#                    own archers +0.31  (rms x3.96)
#                    A caster    +1.13  (rms x5.25)
#   best pair:       army_min^+1.23 * D_target^-0.88  (rms x1.94)  <- signs are physical
#   best triple adds a NEGATIVE exponent on the caster's own attack, which is absurd: with 13
#   correlated points that is overfitting, not a discovery.
# Conclusion: army_min (battle scale) and the target's defence x health are the real drivers with
# sensible signs, but no power law in these variables gets below a ~2x typical error, so a
# structural piece is still missing.  What the ALL-INFANTRY cell did settle: Yang's nuke fires and
# deals real damage with ZERO archers (21.3 per trigger, against 66.2 with 6,000 archers at twice
# the march size), so own troop count matters only weakly -- roughly 1.3x beyond the scale effect.

# TACTICAL, and unambiguous: an all-infantry march is catastrophic into a 50/20/30 garrison.
# 10,000 pure infantry killed 937; 10,000 at 50/20/30 killed 9,734 -- more than 10x -- because
# every one of your infantry piles into his infantry, first in the targeting order and the worst
# matchup, while his 68,079 archers counter yours.  Kill ratios across the three Terry fights:
# 20,000 at 50/20/30 -> 1.13, 10,000 at 50/20/30 defending -> 0.97, 10,000 all-infantry -> 0.09.


# ------------------------------------------------- completed Terry sweep
# The designed sweep, run in full against one opponent with the Special Bonuses panel verified
# identical throughout.  I was wiped in every cell, so Terry's losses are the uncensored quantity.
TERRY_SWEEP = [
    # (label, my troops, enemy troops, my losses, Terry's losses, Yang row1 (triggers, kills))
    ('10,000 50/20/30 defending', {'inf': 5_000, 'cav': 2_000, 'arch': 3_000},
     {'inf': 113_467, 'cav': 45_386, 'arch': 68_079}, 10_000, 9_734, (5, 274)),
    ('20,000 50/20/30 attacking', {'inf': 10_000, 'cav': 4_000, 'arch': 6_000},
     {'inf': 94_555, 'cav': 37_822, 'arch': 56_733}, 20_000, 22_570, (9, 596)),
    ('10,000 all archer', {'inf': 0, 'cav': 0, 'arch': 10_000},
     {'inf': 113_467, 'cav': 45_386, 'arch': 68_079}, 10_000, 1_808, (1, 53)),
    ('10,000 all infantry', {'inf': 10_000, 'cav': 0, 'arch': 0},
     {'inf': 113_467, 'cav': 45_386, 'arch': 68_079}, 10_000, 937, (3, 64)),
]

# RESULT 1 -- THE ENGINE STRUCTURE IS RIGHT AND ONE CONSTANT IS WRONG.
# Simulator over-predicts my damage output in every cell by almost the same factor:
#     20,000 50/20/30      observed 22,570   sim 45,135   2.00x
#     10,000 all archer    observed  1,808   sim  3,002   1.66x
#     10,000 all infantry  observed    937   sim  1,839   1.96x
#     10,000 50/20/30 def  observed  9,734   sim 18,966   1.95x
# Divide the whole simulator by k = 1.89 and the four land at +5.7%, -12.3%, +3.7%, +2.9%.
# Measured single-run noise is 8.8%, so three are inside it and the fourth is just outside.
# Pure archer, pure infantry, mixed, attacking, defending, 10k and 20k -- composition and scale
# behaviour are all correct; a single multiplicative factor is missing.  Whether k is universal
# or specific to this opponent is the obvious next question, and the same sweep against a
# different player answers it directly.

# RESULT 2 -- THE NUKE'S OWN-TROOP DEPENDENCE SATURATES, which is why every power-law fit failed.
# March fixed at 10,000, same target, same buffs, Yang row 1 kills per trigger:
#       0 archers -> 21.3      3,000 archers -> 54.8      10,000 archers -> 53.0
# Going 0 -> 3,000 is worth ~2.5x; 3,000 -> 10,000 adds nothing.  A log-linear regression cannot
# represent a saturating curve, so nuke_fit.py was structurally incapable of fitting this no
# matter which drivers went in -- that, not bad luck, is why three hypotheses in a row missed.

# RESULT 3 -- SINGLE-TYPE MARCHES ARE CATASTROPHIC, and it is the largest effect in the dataset.
# Terry killed per troop sent:  50/20/30 -> 1.13,  all archer -> 0.18,  all infantry -> 0.094.
# Mixed is 6x better than pure archer and 12x better than pure infantry.  It is not about WHICH
# type: with one type you have no front line, everything you own is exposed to all three of his
# types at once, and all your damage funnels into whichever type is first in his targeting order.


# ------------------------------------------------- second opponent, cell 1
# A different player ([PRO], name is whitespace characters) with ZERO special bonuses on every
# line -- no pets, no buffs -- where Terry at least had pet skills.  My own buffs identical to
# the Terry sweep.  Solo, 10,000 at 50/20/30, I was wiped, so his losses are uncensored.
OPP2 = {'inf': dict(attack=1380.6, defense=1009.3, lethality=1032.5, health=1112.8),
        'cav': dict(attack=1422.5, defense=1052.7, lethality=1038.7, health=985.8),
        'arch': dict(attack=1471.7, defense=1083.6, lethality=1199.8, health=1040.9)}
OPP2_TROOPS = {'inf': 81_050, 'cav': 36_022, 'arch': 63_038}     # 180,110
OPP2_TIERS = {'inf': 11, 'cav': 10, 'arch': 11}                  # his cavalry reads Lv 10.0
OPP2_PANEL = {'inf': dict(attack=2555.7, defense=2120.0, lethality=2360.7, health=1980.2),
              'cav': dict(attack=2384.0, defense=1975.3, lethality=2258.6, health=1897.7),
              'arch': dict(attack=2387.5, defense=1975.1, lethality=2282.4, health=1910.4)}
OPP2_CELL1 = dict(my_troops={'inf': 5_000, 'cav': 2_000, 'arch': 3_000}, my_losses=10_000,
                  enemy_losses=15_224, enemy_heroes=['Triton', 'Ava', 'Wee & Woo'],
                  my_yang_row1=(8, 519))
# 15,224 killed for 10,000 sent is 1.52 per troop -- the best PvP result in the whole dataset,
# and he is 1.30x softer than Terry on the infantry my archers target.

# Side.tier and Side.tg now accept a dict keyed by troop type as well as an int, because armies
# are routinely non-uniform.  Guessing a single tier for this opponent gave k anywhere from 1.56
# (all T11) to 2.18 (all T10), which is wider than the whole question; his real split pins it.
#
# IS k UNIVERSAL?  Five cells across two opponents:
#     Terry 20,000 50/20/30        2.00
#     Terry 10,000 all infantry    1.96
#     Terry 10,000 50/20/30 def    1.95
#     Terry 10,000 all archer      1.66
#     opponent 2, 10,000 50/20/30  1.63
#   mean 1.84, spread 1.63-2.00, sd 0.18
# Every cell over-predicts, in a band under 1.25x wide, across two opponents with completely
# different buff loadouts (Terry had pet skills; this one has literally none).  So k is NOT an
# artefact of the special-bonus channels, and a global constant near 1.8 is defensible today.
# It is not yet proven constant: 1.63-1.66 versus 1.95-2.00 looks like two clusters rather than
# scatter around one value, and the remaining sweep cells against this opponent will say whether
# that is real or just the ~9% noise stacking up.


# ------------------------------------------------- k is a symptom, not a parameter
# Fitting k was the wrong move.  If the engine were implemented correctly k would be 1, so a
# stable 1.8 is a bug to find, not a constant to apply.  Diagnosis so far:
#
# NOT the round count.  The reports give a proxy via fixed-cadence skills (Charles row 4 fires
# 17 / 23 / 23 times in three cells).  The simulator runs 17.3 / 15.6 / 15.1 -- the same or
# FEWER rounds -- while still over-killing, so it is over-killing per round.
#
# NOT the engagement term.  Scanning army = n_u**ENG_A * army_min**ENG_B over a 5x5 grid, the
# reverse-engineered sqrt(n_u * army_min) (0.5/0.5) gives the TIGHTEST spread of k across cells
# (max/min 1.24) of anything tried.  Exponents that pull the mean k toward 1 (0.70/0.20 gives
# mean 0.98) make the spread worse (1.41).  So that form is right and the error is elsewhere.
# ENG_A/ENG_B stay at 0.5/0.5; the knobs are left in place for future tests.
#
# NOT a live army_min.  Recomputing it each round as armies shrink moves the mean 1.81 -> 1.70
# but does not tighten the spread.  Left off by default (ARMY_MIN_LIVE).
#
# LARGELY THE MISSING HERO DAMAGE CHANNEL.  The simulator models no direct-damage skills, so it
# under-kills MY army by whatever the ENEMY's heroes contributed; I then survive too long and
# over-kill them.  k should therefore track how much hero damage the opponent brought, and it does:
#
#   cell                 my losses   from their heroes   share     k
#   Terry 20k mix           20,000               2,976   14.9%   2.00
#   Terry 10k all inf       10,000               1,464   14.6%   1.94
#   Terry 10k all arch      10,000                 956    9.6%   1.65
#   opp2 10k mix            10,000                 264    2.6%   1.62
#
#   r = 0.895;  k = 1.49 + 3.04 * share
#
# That is the Terry/opponent-2 split: Terry fields Yang, the heaviest direct-damage hero in the
# roster; opponent 2 fields Wee & Woo, who barely scratched me.  So k was never a constant -- the
# spread in it IS the size of the channel the model is missing.
#
# STILL UNEXPLAINED: the intercept.  Against an opponent whose heroes deal no direct damage the
# fit still predicts k = 1.49, not 1.0.  With four points that intercept is soft, but it says
# roughly half the error is the missing channel and roughly half is something else not yet found.
# Implementing the channel is now both the fix and the measurement: whatever k remains afterwards
# is the real residual bug.


# ------------------------------------------------- checked against the reference engine
# Source: request-laurent/sos.battle (Java), the 6-month reverse-engineering effort that claims
# >99% reproduction of real battles.  Read Fight.java and Fighter.java directly rather than the
# prose guides this file was originally built from.
#
# CONFIRMED CORRECT in sim.py:
#   Fight.java:118   army = Math.pow(nbUnit,0.5) * Math.pow(armyMin,0.5)   -> sqrt(n_u*army_min)
#   Fight.java:155   deadValue = army * attack / defense / 100.0, then Math.ceil
#   Fighter.java:215 attack  = attack * (1+troopAttack) * damage * (1+troopLethality) / 100
#   Fighter.java:216 defense = health * (1+troopHealth) * defense * (1+troopDefense) / 100
#   targeting: the loop over unit types skips types with no troops and stops after the first one
#   it damages (needContinue() is false except for one specific skill effect), i.e. first living
#   type -- which is what sim.py already did.
#
# TWO MECHANICS IN sim.py WERE INVENTED and appear nowhere in the reference:
#   * a +10% counter-triangle bonus (archers>infantry etc.)
#   * a 20% per-round cavalry bypass onto archers
#   The reference has no counter bonus at all, and reorders targeting only on every 20th round
#   and only for units carrying the biker/sniper perk -- not a flat per-round split.  The bypass
#   mattered a lot: archers are ~5x squishier than infantry, so routing a fifth of cavalry damage
#   into them every round inflated exactly the cells that field cavalry.  Both defaults are now 0.
#
# ONE MECHANIC WAS MISSING: Fight.java applies 0.01% attrition per round,
#   deadValue -= deadValue * 0.0001 * round.  sim.py had the parameter but defaulted it to zero,
#   and battle_mc ignored it entirely.  Now WEAR = 0.0001 and both loops apply it.
#
# EFFECT ON k:
#   before  mix 2.00  arch 1.68  inf 1.94  opp2 1.65   mean 1.82
#   after   mix 1.47  arch 1.54  inf 2.05  opp2 1.29   mean 1.59
# The two cells that field cavalry drop hard (2.00->1.47, 1.65->1.29) and the two that do not
# barely move -- the signature of a real bug rather than a fitted constant.  The Bear Trap
# regression still reproduces 16,797 exactly.
#
# The residual is now concentrated in the all-infantry cell (2.05).  That is also the cell where
# the enemy's heroes did the largest share of the killing, which is consistent with the missing
# direct-damage channel being what is left -- but the spread got wider, not narrower, so the
# single-constant reading of k is dead and should not be revived.


# ------------------------------------------------- how tier and Truegold actually enter
# Yes, both are modelled, and Side.tier/Side.tg now take per-troop-type dicts.  But the way they
# enter is worth writing down, because it is counter-intuitive and it bounds how much they can
# explain.
#
# Base defense and base lethality are 10 for EVERY entry in the 198-row table -- all 11 tiers,
# all 6 Truegold levels.  Only base attack and base health scale, and they scale by the same
# factor: a tier step multiplies attack by 1.199 and health by 1.200; a Truegold step multiplies
# attack by 1.051 and health by 1.050.  Since
#     A = base_atk * M_atk * 10 * M_leth / 100      D = base_hp * M_hp * 10 * M_def / 100
# that common factor CANCELS out of A/D whenever both armies move together.  Measured:
#     both T11 TG8   k = 1.47
#     both T11 TG5   k = 1.46
#     both T5  TG0   k = 1.47
# Tier and Truegold only ever act through the DIFFERENCE between the two sides -- and there they
# are powerful:
#     me T11 vs him T10   k = 2.07
#     me T10 vs him T11   k = 1.04
# One tier of relative advantage is worth 1.44x on the damage ratio.
#
# TWO CONSEQUENCES.
# 1. The TG6-8 values are EXTRAPOLATED (table stops at TG5; TG_STEP = 1.05 per level).  That
#    guess is harmless in every fight where both sides are TG8, which is all the Terry and
#    opponent-2 cells, so it cannot be behind the residual k there.  It is NOT harmless against
#    Narses (me TG8, him TG2) -- that fit carries the extrapolation error in full.
# 2. Reading a troop icon wrongly is expensive.  Getting opponent 2's cavalry tier wrong by one
#    step moved k from 1.56 to 2.18, which is wider than the entire effect being chased.  The
#    per-type dict exists because of that.


# ------------------------------------------------- the "missing nuke channel" was a wrong frame
# Implementing it is what disproved it.  Reading Skill.java rather than reasoning from the
# reports, effect 101 -- the thing the Battle Details Kills column attributes to a hero -- does
# this:
#     case 101:  coef = coef * (1 + skill.getValue()/100.0)   [gated on the skill's own unit type]
# It is a MULTIPLIER on that troop type's damage, not a separate additive source.  sim.py already
# applies exactly that through skill_mod()'s proc handling.  So the Kills column is attribution --
# how much of the troop damage is owed to the skill boost -- not damage the model was missing.
#
# The one genuinely separate mechanic is the extra target: needContinue() lets a troop type strike
# an ADDITIONAL enemy type in the same round, but it requires effectTarget==40 AS WELL AS
# effect==101, so only a minority of damage skills carry it.  Implemented and measured:
#     no extra strikes (default)   mix 1.47  arch 1.54  inf 2.05  opp2 1.29   mean 1.59
#     extra strike on every 101    mix 1.76  arch 7.73  inf 2.05  opp2 3.97   mean 3.88
# Granting it to every damage skill triples archer output and wrecks the fit, so STRIKE_CONTINUE
# defaults off.  The machinery stays: if a specific skill can be shown to carry effectTarget 40,
# it can be switched on per skill rather than globally.
#
# CONSEQUENCE FOR EVERYTHING ABOVE.  The reading that k tracks the enemy's hero damage share
# (r = 0.895) has to be retired.  The correlation was real but the causal story behind it was not:
# there was no missing additive channel for that share to stand in for.  Two independent things
# were true at once -- opponents with heavy damage heroes hit harder, and the model was 1.6x hot --
# and I read the second as being caused by the first.  The residual k = 1.59 is still unexplained
# and is now the whole of the problem rather than half of it.


# ------------------------------------------------- k, decomposed at last
# Running the four cells with NO hero skills on either side separates the engine from the skill
# data, which should have been the first diagnostic rather than the last:
#
#     with hero skills      mix 1.57  arch 1.52  inf 2.21  opp2 1.38   mean 1.67
#     NO hero skills        mix 1.04  arch 1.08  inf 2.54  opp2 0.96   mean 1.40
#
# THREE OF FOUR CELLS LAND AT k = 1 WITH THE SKILLS OFF.  The engine -- sqrt(n_u * army_min),
# the /100 and ceil, both stat products, first-living-type targeting, per-type tier and Truegold,
# the reference attrition, and the removal of the invented triangle and cavalry bypass -- is
# correct.  The residual was never in the engine.
#
# HERO SKILL MAGNITUDES ARE ROUGHLY 3-4x TOO STRONG.  Scanning a global multiplier:
#     SKILL_SCALE  1.00  0.75  0.50  0.35  0.25  0.00
#     mean k       1.67  1.57  1.49  1.46  1.44  1.40
#     mix          1.57  1.41  1.26  1.19  1.15  1.04
# The likely cause is in the reference's condition(): a skill is live only when
# (round - roundLag) % roundFreq == 0, so a frequency-5 skill fires one round in five.  This
# file models skills as continuously active or as chance procs, with uptimes in heroes.py that
# have never been checked against that gating.  SKILL_SCALE is left at 1.0 deliberately -- the
# fix is to implement the round-frequency schedule, not to fit another global constant.
#
# THE ALL-INFANTRY CELL IS A SEPARATE BUG.  It sits at 2.21-2.54 and moves the WRONG way as
# skills are weakened, so whatever is wrong there is not shared with the other three.  It is the
# only cell where the march is a single front-line troop type.
#
# TWO BUGS FOUND ALONG THE WAY:
#   * PROC_SCALE was read only by battle(), never by battle_mc() -- so it was a dead knob on the
#     Monte Carlo path that every report fit in this file uses.  SKILL_SCALE is applied where the
#     effects are built and reaches both.
#   * Defence skills: the reference raises defence as 1/(1 - coef), not (1 + coef) (Fight.java:133).
#     DEF_RECIP implements it and defaults on.  It makes the fit slightly WORSE (1.59 -> 1.68),
#     which is expected when a stronger transform is applied to skill values that are themselves
#     3-4x too big -- not evidence against the reference.


# ------------------------------------------------- skill uptimes measured, not guessed
# heroes.OBSERVED_UPTIME now carries 18 skills whose uptime is measured from Battle Details
# trigger counts (triggers / rounds) in the three PvP fights where the engine is validated.  The
# Baron fights were excluded: its trigger counts exceed the simulator's round count outright,
# which is another sign it is a scripted monster rather than a normal battle.
#
# ROW MAPPING CORRECTED: rows 1-3 of a hero panel are the base expedition skills; rows 4+ are TG
# and gear skills that heroes.py does not model.  Charles' row 4 is Unyielding Shield, a TG proc --
# which retires it as the round-count proxy used earlier in this file, since its counts (35, 30,
# 20, 24 across the Baron series) are not monotonic in battle length and so it is not fixed-cadence.
#
# THE BIG ONE: Charles' three base skills fire EXACTLY ONCE in every single report, and this file
# had all three permanently active -- a 15-30x overstatement on the hero in every one of my
# lineups.  Triton's three do the same on the opponents' side, as does Sophia's Terror Annihilation.
# Yang's and Sophia's other skills were understated instead, so the error was not one-directional.
#
#   variant                          mix   arch    inf   opp2   mean
#   no hero skills at all           1.04   1.08   2.54   0.96   1.40
#   both sides, measured uptimes    1.30   1.54   1.97   1.14   1.49
#   my heroes only, measured        1.40   1.53   1.94   1.20   1.52
#   guessed uptimes (before)        1.57   1.52   2.21   1.38   1.67
#
# Mean k 1.67 -> 1.49, and the two mixed cells (the ones the recommendations actually care about)
# 1.57 -> 1.30 and 1.38 -> 1.14.  Bear Trap still reproduces 16,797.
#
# WHAT IS LEFT.  Turning skills off entirely still gives a better mean (1.40) than any uptime
# setting, so the residual is not uptime alone -- the skill VALUES and SCOPES in heroes.py are
# scraped from prose and remain unverified, and the all-infantry cell (1.97) is still the separate
# structural bug it has been all along.  Uptimes are now data; magnitudes are still guesses.

# CORRECTED by the player, with the in-game tooltips:
#   * A skill that fires exactly once per battle is a PERMANENT aura switched on at the start --
#     the single trigger is the game recording that it turned on.  "Intimidation Lv. 5 -- reduces
#     enemy Squad's Total Lethality by 20%", no chance, no duration.  So the previous commit's
#     reading of those as ~0.03 uptime was wrong in the opposite direction from the original bug,
#     and heroes.PERMANENT now pins eleven of them back to always-on.  sim._split_effects treats
#     PERMANENT as authoritative over the 'proc' kind prefix they were written with.
#   * Charles row 4 is Unyielding Shield, a TRUEGOLD gear skill: "37.5% chance to reduce incoming
#     damage by 36%".  Both sides carry it in every PvP report and sim.py modelled no TG or gear
#     skills at all.  heroes.TG_SKILLS now holds it and Side.effects() applies it to any side
#     fielding heroes.
#
#   variant                                   mix   arch    inf   opp2   mean
#   everything flat-on (before today)        1.57   1.52   2.21   1.38   1.67
#   all uptimes measured (over-corrected)    1.30   1.54   1.97   1.14   1.49
#   permanent auras + measured procs         1.37   1.38   2.04   1.14   1.48
#   + the Unyielding Shield TG skill         1.26   1.35   1.98   1.14   1.43
#
# The two mixed cells are now 1.26 and 1.14, from 1.57 and 1.38 this morning.  The early N2DBLG
# rally fits recovered too: 2.94 -> and the whole set back from 1.70/1.75/3.25/4.09 to
# 1.22/1.61/2.75/2.94, though still worse than before the uptime work, which keeps the joiner
# uptimes (4x Chenko, still flat-on) as the live suspect there.
#
# CAVEAT ON MAGNITUDES.  Terror Annihilation was stored as 37.5 because this file assumed "+75%
# on one turn in two" and halved it into an expected value.  If it is permanent, the stored
# number is half what it should be.  The same halving may sit in other entries.  Uptimes are now
# data; the magnitudes behind them are still unverified prose scrapes and this is the clearest
# example of the two assumptions being entangled.

# REGRESSION TO FLAG, not to bury: the four early N2DBLG rally fits got WORSE with these changes.
#   before  1.04 / 1.14 / 0.76 / 1.74      after  1.70 / 1.75 / 3.25 / 4.09
# Those four are the least trustworthy data in this file -- multi-player rallies, joiner skills
# whose uptimes are still unmeasured and therefore still flat-on, and an opponent panel carrying
# a 20% buff stack -- but that is an explanation, not an excuse.  Two candidates: the joiners
# (4x Chenko in every one of them) are the only skills left running at flat uptime, and the
# heterogeneous-rally problem recorded earlier is untouched.  Measuring Chenko's uptime from a
# rally report's Battle Details is the cheap test.


# ------------------------------------------------- rows 4+ are TROOP abilities, not hero skills
# The single biggest structural misreading in this file, corrected by the player's tooltips.
# Rows 4 and 5 of a hero's Battle Details panel belong to that hero's TROOP TYPE and every player
# has them; sim.py modelled none of them.  Verbatim:
#   Unyielding Shield  37.5% chance to reduce incoming damage by 36%          (infantry)
#   Ambusher           20% chance to bypass Infantry and directly attack Archers  (cavalry)
#   Assault Lance      15% chance to deal double damage                       (cavalry)
#   Volley             10% chance to attack twice in a row                    (archers)
#   Howling Wind       30% chance to deal 50% extra damage                    (archers)
#
# AMBUSHER WAS REAL ALL ALONG.  It was deleted earlier today because the reference engine has no
# such mechanic -- but that engine is State of Survival, a DIFFERENT GAME that shares the core
# formula.  Treating it as authoritative for Kingshot's troop abilities was an over-application:
# it settles the damage maths, not the ability list.  Side.ambusher is back to 0.20.
#
# A BUG WHILE IMPLEMENTING: the tooltips give raw effect sizes, but _split_effects() recovers a
# live magnitude as value/uptime, so the stored number must be the EXPECTED value.  Passing 36%
# and 0.375 gave a 96% damage reduction when live.  TROOP_SKILLS now stores chance x effect.
#
#   variant                                  mix   arch    inf   opp2   mean   spread
#   everything flat-on (start of today)     1.57   1.52   2.21   1.38   1.67    1.60
#   permanent auras + measured procs        1.37   1.38   2.04   1.14   1.48    1.79
#   + troop abilities and Ambusher          1.71   1.36   1.67   1.36   1.53    1.25
#
# The all-infantry cell -- structurally broken all session at 2.0-2.5 -- is finally at 1.67, and
# Unyielding Shield is why: it is an infantry-only defensive ability, so a pure-infantry march was
# the configuration most damaged by its absence.  The spread across cells (1.25) is the tightest
# it has been.
#
# HONEST TENSION: restoring Ambusher makes the two MIXED cells worse (1.37 -> 1.71, 1.14 -> 1.36)
# even though the tooltip confirms it exists.  A confirmed-real mechanic degrading the fit means
# something it interacts with is still wrong -- most likely the skill magnitudes, which remain
# unverified prose scrapes, or the archer abilities' interaction with the ambush target.  Do not
# resolve that by removing Ambusher again.


# ------------------------------------------------- Sophia's tooltips: my originals were right
# Verbatim:
#   Arcane Pact Lv.5        "a 40% chance of reducing Squad's Damage Taken by 50% every turn"
#   Terror - Deathblow Lv.5 "Enemy targets suffer the effects of Terror every 2 turns and will
#                            receive 200% increased Cavalry damage on the following turn."
#   Terror - Annihilation   "All Squads deal 75% increased damage to Terrified targets."
# -> uptimes 0.40, 0.50, 0.50 and EVs 20, 100, 37.5, which is exactly what PROC_SPEC already held.
#
# The "measured uptime" pass earlier in this session made all of them about 2x too low, because
# the denominator was the SIMULATOR's round count (~29) while the tooltips imply the real fight
# ran ~15 (Arcane Pact fires at 40% and fired 6 times).  Correct values, corrected with a wrong
# denominator.  Restored; only the PERMANENT reclassification and the troop abilities survive
# from that pass.  Terror Annihilation goes back to periodic/2 -- it is gated on Terror, which
# Deathblow keeps up one turn in two, so it is not the permanent aura its single trigger suggested.
#
# NEW MECHANIC the trigger counts exposed.  In one battle, Sophia's skills imply 15-18 rounds and
# Yang's imply 27-28.  That is the reference's Skill.condition(): a hero's skills stop firing once
# that hero's troop type is destroyed -- her cavalry (4,000 of 20,000) died first.  Implemented,
# with one Kingshot-specific correction: the gate is "wiped DURING the battle", not "never
# present", because Yang demonstrably fires 15 times and scores 203 kills in a march carrying zero
# archers.  Gating on absence instead collapses the single-type cells to 0.52 and 0.73.
#
#   variant                                 mix   arch    inf   opp2   mean  spread
#   everything flat-on (start of today)    1.57   1.52   2.21   1.38   1.67   1.60
#   tooltip values, no death gate          2.15   1.45   1.84   1.74   1.79   1.48
#   + gate on absence (over-applied)       2.04   0.52   0.73   1.67   1.24   3.92
#   + gate on death during battle          2.04   1.47   1.84   1.66   1.75   1.38
#
# WHERE THIS LANDS, honestly: every input is now tooltip-verified or reference-sourced, and the
# fit is WORSE than when several inputs were wrong (mean 1.75 vs 1.52 mid-session).  Wrong inputs
# were cancelling each other.  That is the right trade -- verified inputs and a visible error beat
# unverified inputs and a flattering one -- but it means a real error remains and is now isolated
# rather than masked.  The mixed cells (2.04, 1.66) are the worst, which points at composition
# interactions: Ambusher, the archer abilities, and the ambush target all touch mixed marches and
# nothing else.


# ------------------------------------------------- all six Yang/Sophia skills verified exact
# Tooltips, verbatim, against what heroes.py already held:
#   Ice Zone Lv.5      "granting Yang's archers a 40% chance of dealing 100% extra damage to the
#                       target for each attack"            -> 0.40, EV 40, archers   MATCH
#   Avalanche Lv.5     "an additional strike against a target by all Squads every 4 turns for
#                       100% damage"                       -> 1-in-4, EV 25, all     MATCH
#   Ambush Lv.5        "a 40% chance of increasing Squad's Damage Dealt by 50%"
#                                                          -> 0.40, EV 20, all       MATCH
#   Arcane Pact Lv.5   "a 40% chance of reducing Squad's Damage Taken by 50% every turn"
#                                                          -> 0.40, EV 20, all       MATCH
#   Terror-Deathblow   "Terror every 2 turns ... 200% increased Cavalry damage ... lasts 1 turn"
#                                                          -> 1-in-2, EV 100, cav    MATCH
#   Terror-Annihilation "All Squads deal 75% increased damage to Terrified targets"
#                                                          -> 1-in-2, EV 37.5, all   MATCH
# Six for six on magnitude, uptime AND scope.  Row order confirmed too (Ice Zone 1, Avalanche 2,
# Ambush 3).  These two heroes appear in every fitted cell, so HERO SKILL DATA IS NO LONGER A
# SUSPECT for the residual -- which was the lead named at the end of the previous note, and it is
# now closed.
#
# THE ROUND COUNT WAS RIGHT ALL ALONG.  Yang's three skills independently imply ~28 rounds for the
# Terry 20k fight (11/0.40, 7/0.25, 11/0.40) and the simulator gives 29.  The earlier inference
# that "the real fights ran ~15" came from Sophia's counts, and those are low because her cavalry
# died at round ~16 -- the very mechanic since implemented.  Two wrong readings in a row from the
# same numbers: first that they measured uptime, then that they measured battle length.  They
# measure uptime x survival, and only Yang's (whose archers lasted) isolate either.
#
# REMAINING SUSPECTS, now that hero skills and round count are both cleared:
#   * the OTHER heroes' magnitudes -- Charles, Triton, Ava, Wee & Woo are still prose scrapes,
#     and Charles is in every one of my lineups
#   * composition interactions -- the mixed cells (2.04, 1.66) are worse than the single-type
#     ones (1.47, 1.84), and Ambusher plus the archer abilities only bite on mixed marches


# ------------------------------------------------- Charles verified: 9 for 9 on my own lineup
#   Intimidation Lv.5   "reduces enemy Squad's Total Lethality by 20%"   -> e_leth 20, all   MATCH
#   Iron Bodies Lv.5    "reducing Squad's Damage Taken by 20%"           -> taken 20, all    MATCH
#   Great Justice Lv.5  "increasing Squad's total Health by 25%"         -> hp 25, all       MATCH
# None of the three carries a chance or a duration, which independently confirms the PERMANENT
# reclassification rather than resting on the single-trigger observation alone.
#
# Charles + Sophia + Yang is the entire lineup in every fitted cell, and all nine skills now match
# the in-game text on kind, magnitude, scope AND schedule.  MY SIDE'S HERO DATA IS CLOSED.  What
# remains unverified is the opponents' heroes -- Triton, Ava, Wee & Woo -- which are still prose
# scrapes, and the composition interactions.
#
# STATE OF THE MODEL after a day of this:
#   engine (formula, targeting, scale, tier/TG, attrition)     validated, k = 1 with skills off
#   stat panel reconstruction                                   24/24 lines within 12 of ~2000
#   widget stacking and special bonuses                         confirmed to 0.03 points
#   troop abilities (5, incl. the restored Ambusher)            tooltip-sourced
#   my heroes' 9 skills                                         tooltip-verified, 9/9
#   per-rally noise                                             measured, 8.8% CV
#   REMAINING: k = 2.04 / 1.47 / 1.84 / 1.66 across the sweep
#
# The mixed cells are the worst two, and every mechanic that bites only on mixed marches -- the
# Ambusher redirect, and how Volley and Howling Wind compose with it -- is implemented from
# tooltips but never validated as a SYSTEM.  That is the next place to look, and it is a code
# question rather than a data-collection one.
