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
