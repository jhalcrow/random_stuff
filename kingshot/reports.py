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

THE DATA NOW LIVES IN battles.py.  This file is the ARGUMENT -- what each fight meant, what it
refuted, which claims were retracted and why.  battles.py is the transcription, checked against
the report screenshots and self-verifying on casualty arithmetic; where the two disagree about a
number, battles.py wins.  HANDOFF.md is the summary of both.
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

# COMBAT ALWAYS RUNS UNTIL ONE SIDE IS WIPED (confirmed by the player), so where a report exists
# the winner's own losses are the informative quantity.
# BUT THE REPORT ITSELF CAN BE WITHHELD.  A 500-troop march on Narses returned only "Our troops
# were annihilated with overwhelming force!  Battle results cannot be reviewed" -- no panels, no
# losses, no trigger rows.  The earlier claim here that "nothing is ever censored" was wrong, and
# it was load-bearing: the whole uncensored-quantity method assumes every fight yields numbers.
# WHERE THE THRESHOLD SITS: 500 troops against 123,570 (0.40% of the defender) was withheld;
# 10,000 against Terry's 227,000 (4.4%) was not, even though Terry lost only 937 troops there.
# So the trigger is the SIZE RATIO of the marches, not how little damage the loser did.  Narses'
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


# ------------------------------------------------- Ambusher / archer ability ablation
# Full cross of Ambusher against the two archer abilities, over the four sweep cells:
#
#   configuration                     mix   arch    inf   opp2   mean  spread
#   Amb on  + both archer abilities  2.01   1.58   1.84   1.67   1.78   1.27
#   Amb on  + Howling Wind only      2.06   1.45   1.97   1.71   1.80   1.42
#   Amb on  + Volley only            2.10   1.45   2.02   1.72   1.82   1.45
#   Amb on  + neither                2.27   1.35   2.14   1.76   1.88   1.68
#   Amb off + both archer abilities  1.44   1.62   1.86   1.29   1.55   1.44
#   Amb off + neither                1.54   1.32   2.12   1.30   1.57   1.63
#
# The archer abilities are second-order and both belong: keeping both gives the tightest spread
# in either half (1.27 with Ambusher, 1.44 without).  AMBUSHER is what moves the mixed cells --
# on 2.01/1.67, off 1.44/1.29 -- and it is the only mechanic that fires exclusively there.
#
# NOT the split-vs-roll modelling.  The tooltip says "20% chance", and the reports carry Ambusher
# as its own row with a trigger count (3 in the ~16 rounds Sophia's cavalry survived = 19%), so it
# is a discrete per-round redirect rather than a permanent damage split.  Implemented that way
# (AMBUSH_ROLL, default on) and it changes almost nothing: mean 1.77 against 1.78.  The old split
# gave cavalry two attacks a round, each with its own ceil(), but the expectation was the same.
#
# WHAT IT IS INSTEAD -- the base stat spread between troop types:
#     T11 TG8   infantry  attack   829   health 2487
#               cavalry   attack  2487   health  829
#               archers   attack  3317   health  571
# An archer is 4.36x squishier than an infantryman before any bonuses, so redirecting cavalry onto
# archers is worth an enormous amount.  Both sides' panels show archer defence and health bonuses
# within a few percent of their infantry ones, so that entire gap comes from troops_base.json --
# scraped from kingshotsimulator.com's JS bundle and never validated against anything.
#
# That makes the base-stat table, not Ambusher, the live suspect: it is the one input to the
# mixed cells that has never been checked, Ambusher's value is entirely determined by it, and
# a table that exaggerates the archer/infantry gap would produce exactly this signature.


# ------------------------------------------------- base stats cleared; Ambusher isolated
# The pure-archer probe: Narses fielded 116,040 ARCHERS AND NOTHING ELSE (T10 TG2).  I attacked
# with 5,000 at 50/20/30 and won, losing 72 while wiping all 116,040.  My losses are the
# uncensored quantity.
#     OBSERVED  I lost 72        SIM  I lost 75        k = 1.04
# troops_base.json is therefore NOT the problem.  Archer durability is right, measured against a
# target made entirely of archers, and the previous note's suspect is closed.
#
# But Ambusher is INERT in that fight -- with no enemy infantry there is no front line to bypass.
# Re-testing it on the Narses MIXED fights (41,190 of each type), where it does fire:
#
#     configuration      I attack (obs 239)   I defend (obs 292)
#     Ambusher on              1.20                 1.26
#     Ambusher off             1.04                 1.09
#
# Across five independent fights the pattern is now exact: whenever Ambusher is inert or disabled
# the model reproduces reality at k = 1.04-1.09.  Whenever it is active, k rises -- 1.20/1.26 on
# Narses, and 2.04/1.66 on the tougher Terry and opponent-2 mixed cells.
#
# CONCLUSION.  Ambusher exists -- the tooltip says so and the reports carry it as its own row with
# a ~19% trigger rate.  So this is an IMPLEMENTATION bug, not a case for deleting the mechanic
# again.  Everything it depends on has now been independently verified: archer durability (this
# fight), the engine (k=1 with skills off), my heroes' nine skills (tooltips), the troop abilities
# (tooltips), tier and Truegold.  What remains unverified is only how the redirect itself resolves
# -- whether the bypass rolls per cavalry unit rather than per round, whether the redirected
# attack lands at full strength, or whether the front line still absorbs part of it.
#
# The default stays ambusher=0.20 because that is what the game says.  ambusher=0.0 currently fits
# better, and that is recorded here as a measurement, NOT adopted as a setting -- fitting a
# confirmed-real mechanic out of existence is the error this file has already made once.


# ------------------------------------------------- the ceil() bias, and what it does not explain
# allfights.py scores every fight where one side's losses are uncensored -- my own when I won, the
# enemy's when I was wiped.  In both cases that is the LOSING side's cumulative damage output.
#
# Tested and REJECTED as the residual: recomputing army_min each round (rms 0.494 -> 0.482), the
# engagement exponents (ENG_A 0.6 and 0.7 both worse), and Skill.protect() as a flat absorption
# pool (0.458 -> 0.417, and it largely cancels because both sides carry it).
#
# FOUND: math.ceil() on the per-attack kill term.  The reference uses it and is right to -- it
# runs a battle once.  This file averages 200 Monte Carlo runs, where ceil() is a systematic
# upward bias that never averages out: a side whose army is nearly dead still books >=1 kill per
# troop type per round, for as long as the fight runs.  Rounding up with probability equal to the
# fractional part is unbiased in the mean.
#
#   rounding      N-arch  N-atk  N-def  N-i+a  T-arch  T-inf   opp2  T-mix   mean  rms log
#   ceil            1.16   1.17   1.23   2.38    1.53   1.84   1.68   2.07   1.63    0.458
#   stochastic      1.14   1.04   1.13   1.53    1.49   1.83   1.64   2.01   1.48    0.364
#
# The prediction was that it would bite hardest in LONG fights, and it does: the 1,000-troop
# Narses grind (the longest in the set) goes 2.38 -> 1.53 while the short lopsided wins barely
# move.  ROUND_MODE now defaults to stochastic.
#
# WHAT IT DOES NOT EXPLAIN.  The four Terry and opponent-2 cells hardly shift (1.49/1.83/1.64/2.01)
# and they are the ones where I am WIPED.  Every fight I WIN now sits at 1.04-1.53; every fight I
# LOSE sits at 1.49-2.01.  That is a cleaner split than anything earlier in this file, and it says
# the remaining error is specific to being annihilated -- the regime where the sqrt(n_u) term
# drives my output to near zero while the model still has me fighting.  That is the next thread.


# ------------------------------------------------- bear_check() is not a regression test
# It has been cited after every change in this session as "Bear Trap still reproduces 16,797",
# implying the changes were safe.  That was worthless reassurance.  bear_check() hand-computes the
# formula inline -- it never calls battle() or battle_mc(), hardcodes the bear's defence rather
# than building D from stats, and applies a 1.10 archer multiplier that is the counter-triangle
# deleted earlier today as unsourced.  Run under ROUND_MODE, TROOP_SKILLS, AMBUSH_ROLL, DEF_RECIP,
# SKILL_SCALE, WEAR and ENG_A toggles it returns 16,797 every time.
#
# It also is NOT player data -- it came from a kingshotguides.com worked example on day one, the
# same class of community source that supplied the counter-triangle and the per-round cavalry
# bypass, both of which turned out to be wrong for this engine.
#
# What it is actually good for: confirming base_stats() and sqrt(n_u * army_min) still agree with
# a third-party worked example.  Everything else should be judged by allfights.py, which scores
# the real engine against eight measured battles.  Docstring corrected accordingly.


# ------------------------------------------------- next test, pre-registered
# k measures the LOSING side's cumulative damage output.  Grouped by WHOSE output that is:
#     Narses' output over-predicted by  1.14, 1.04, 1.13, 1.53   mean 1.21
#     MY output over-predicted by       1.49, 1.83, 1.64, 2.01   mean 1.74
# So this was never a win/lose effect -- it is an asymmetry between the two sides, and the side
# whose output is over-predicted is the one sitting at 2,379% infantry attack against Narses' 521%.
# That fits a soft cap or diminishing return on very high stat multipliers.
#
# BUT STATS AND WIN/LOSE ARE CONFOUNDED: I beat the weak opponent and lose to the strong ones, so
# every fight measuring MY output is also a fight I lost.  Nothing in the set separates them.
#
# THE TEST: a march small enough to LOSE to Narses.  That measures MY output against a weak
# opponent, which no existing fight does.  500 troops at 50/20/30 is comfortably past the
# crossover (the simulator has 1,000 winning 99% of the time and 700 winning 1%), and since the
# simulator over-predicts my output, reality will lose at 500 at least as readily.
#
# HIS RATIO SHOULD BE 50/20/30.  Every fight with an anomalous k (mine over-predicted) faces a
# 50/20/30-ish enemy -- Terry at 50/20/30, opponent-2 at 45/20/35.  Matching that shape leaves his
# STAT LEVEL as the only difference from those cells, which is the variable under test.  The
# choice does not affect whether the test works: 50/20/30, 50/0/50 and thirds all lose 0% of the
# time at a 500-troop march, with his losses landing within 10% of each other.
#
# PRE-REGISTERED PREDICTIONS -- 500 troops at 50/20/30 against a 50/20/30 Narses:
#     simulator says he loses 40,667 and I am wiped.
#     if the over-prediction follows MY side (a stat-level cap):  he really loses ~23,400  (k 1.74)
#     if it follows the OPPONENT (something about Terry/opp2):    he really loses ~33,600  (k 1.21)
#
# RESULT: RUN, AND VOID.  The march was wiped -- which the simulator did call, at 0% win -- but
# the game withheld the report (see the censorship note above), so none of the three numbers
# could be read.  Two separate faults, worth keeping straight:
#   1. The design was unsound.  Losing to a WEAK opponent requires a march small enough to trip
#      the size-ratio censor, so against Narses the window "I lose AND a report exists" is
#      probably empty.  No choice of his ratio would have rescued it.
#   2. The 40,667 does not reproduce.  Under allfights.py's configuration the same fight gives
#      33,273 (latest panel) or 22,790 (SOLO_PANEL); 40,667 came from some intermediate state
#      that is now lost.  A pre-registered number I cannot regenerate is not a pre-registration.
# The one thing salvaged: with hero_stats=True the simulator has 500 troops WIPING Narses
# (122,935 of 123,570).  Reality wiped my 500, so the reported panel really does already include
# hero expedition stats, and allfights.py's hero_stats=False is right.  A cheap confirmation of
# a switch that was previously only argued from the panel layout.


# ------------------------------------------------- the 500-troop test, RECOVERED
# Mail 223407017237641.  The attacker's copy was censored; the DEFENDER's copy was not, and the
# player owns both accounts.  THE CENSOR IS THEREFORE NOT A DATA LOSS -- it withholds the mail
# from the loser, not from the winner.  Any future fight can be recovered from the other side.
#
# Overview: his squad 123,570, injured 16,997 + lightly injured 31,564 = 48,561 casualties,
# residents 75,009 (48,561 + 75,009 = 123,570 exactly).  My 500 wiped: 176 + 324, residents 0.
# Power confirms the split independently: -1,291,772 / 48,561 = 26.6 per troop for his T10 TG2,
# -23,760 / 500 = 47.5 for my T11 TG8.
NARSES_500 = dict(my_troops={'inf': 250, 'cav': 100, 'arch': 150}, my_losses=500,
                  enemy=NARSES, enemy_troops={'inf': 61_785, 'cav': 24_714, 'arch': 37_071},
                  enemy_losses=48_561,
                  # rows as displayed: (triggers, kills)
                  my_charles=[(1, 0), (1, 0), (1, 0), (125, 0)],
                  my_sophia=[(28, 0), (43, 0), (1, 0), (16, 0), (11, 640), (4, 0)],
                  my_yang=[(59, 1_591), (39, 1_864), (40, 0), (8, 0), (26, 878)],
                  their_long_fei=[(35, 0), (1, 0), (58, 22)],
                  their_jabel=[(30, 0), (122, 27), (1, 0), (17, 0)],
                  their_rosa=[(38, 0), (1, 0), (1, 0), (7, 0)])

# THE PRE-REGISTERED TEST RESOLVED AGAINST BOTH HYPOTHESES.
#     simulator  33,299        k 0.69   -- the sim UNDER-predicts my output by 1.46x
#     "my stats are capped"   ~23,400   -- would need k 1.74; reality was more than double it
#     "it is the opponent"    ~33,600   -- would need k 1.21
# Every fight measuring MY output before this one over-predicted it (1.49 to 2.01).  Against a
# WEAK opponent the same model under-predicts it.  A cap on my own high stat multipliers cannot
# do that -- my stats are the same in both -- so that hypothesis is dead, not merely unsupported.

# WHAT ACTUALLY BROKE THE PROBLEM OPEN: the trigger counts are a ROUND COUNT.
# Yang's first two skills have tooltip-verified schedules, and they agree with each other:
#     Avalanche  periodic 4, fired 39  ->  156 rounds
#     Ice Zone   chance .40, fired 59  ->  148 rounds
# The fight ran about 152 rounds.  The simulator runs 73.  My troops survived twice as long as
# the model says, and that is measured, not inferred.
#
# TWO OBSERVABLES IDENTIFY WHAT ONE COULD NOT.  Total losses alone are degenerate: rate and
# survival trade off along a ridge, and (my /1.2, his /1.5), (my /1.4, his /1.8) and
# (my /1.6, his /2.0) all fit the five Narses totals about equally (rms log err 0.12-0.16).
# The round count is orthogonal -- per-round rate depends only on MY damage, round count only on
# HIS -- so together they pin it exactly:
#     my per-round damage over-modelled  1.4x
#     his per-round damage over-modelled 2.0x
#   sim at (1.4, 2.0): 152 rounds, 49,138 killed, 324/round
#   observed:          152 rounds, 48,561 killed, 319/round
#
# THIS RETIRES THE WHOLE "WHOSE SIDE IS OVER-PREDICTED" FRAMING.  Both sides are over-modelled.
# k on totals was never measuring one side's output: in a fight that ends in a wipe, the loser's
# total output = rate x rounds, and the two errors partly cancel.  That is why k moved so little
# under a dozen substantive changes, and why it pointed at my side -- an artefact of which error
# happened to dominate, not a fact about my stats.

# THE ROUND-COUNT TEST APPLIED RETROACTIVELY (rounds.py).  reports.py already stored Yang rows
# for other fights, so this is free evidence that was sitting in the file unused:
#     fight                  sim rounds   implied   sim/real
#     Narses 500 solo             73        152       0.48
#     Narses mixed atk 10k        13         23       0.57
#     Terry 20k mixed             20         25       0.77
#     Terry 10k all infantry      19          6       3.32
# The simulator ends fights too early almost everywhere.  The all-infantry fight inverts it, but
# rests on 3 and 1 triggers -- Poisson noise there is larger than the effect, so it carries very
# little weight and must not be read as a fifth data point.
#
# CAVEAT ON THE OTHER ROWS.  Only Yang's first two schedules are trusted.  Ambush (chance .40,
# 40 triggers) implies 100 rounds, and Charles' Unyielding Shield (chance .375, 125 triggers)
# implies 333.  Either those roll per attacking squad rather than per round, or the schedules are
# wrong.  Unresolved, and deliberately not fitted around.

# HERO DAMAGE SHARE, measured on both sides of one fight: mine 640 + 1,591 + 1,864 + 878 = 4,973
# of 48,561 = 10.2%; his 22 + 27 = 49 of my 500 = 9.8%.  The ~10% hero channel holds on both
# sides at a 247:1 size mismatch, which is a stronger check than either earlier estimate.


# ------------------------------------------------- crossover test, SUPERSEDED before running
# Written when the censored mail looked like a data loss.  It is not -- the defender's copy is
# intact and the player owns both accounts -- and the recovered report answered the question the
# crossover was designed to sneak up on, so this is kept only as the reasoning it replaced.
# One part of it survives and is now load-bearing: an error applied EQUALLY to both sides cancels
# out of the crossover.  That same cancellation is what hid the real fault in the totals.
#
# TURN THE MEASUREMENT INTO A BIT, NOT A NUMBER.  The censor can withhold panels but it cannot
# hide who won -- "annihilated with overwhelming force" IS the outcome.  So test the CROSSOVER:
# the march size at which I flip from beating Narses to losing to him.
#
# Why that separates what the loss set could not.  Simulating the two stories directly (divide a
# side's output by its k, by scaling the opponent's D term) across march sizes at 50/20/30:
#
#     hypothesis                700    850   1000   1200   1400    <- my march, win probability
#     H0  simulator as-is        2%    32%    88%   100%   100%
#     H1  my output /1.74, his /1.21   0%     0%    14%    71%   100%
#     H2  both sides /1.45       2%    34%    91%   100%   100%
#
# H2 IS INDISTINGUISHABLE FROM H0.  A bias that hits both sides equally does not move the
# crossover at all -- it cancels.  Only the DIFFERENTIAL moves it, and 1.74/1.21 = 1.44 moves it
# by about 250 troops.  That is what makes this test worth running and the last one not: it asks
# whether the side-asymmetry is real at all, which comes before any question of mechanism.
#
# THE TEST: 1,000 troops at 50/20/30, three or four times.
#     simulator says I win 88% of the time, losing ~600 of the 1,000.
#     if the differential is real, I win 14% of the time and am usually wiped.
# Three attacks: 3 wins has p=0.68 under H0 and p=0.003 under H1; 3 losses inverts that.
#
# It cannot be censored into uselessness.  A win always yields a full report (and my own losses
# then measure HIS output, another k), and a loss yields the bit even if the panels are withheld.
# Cost is at most 1,000 troops a run, against the 20,000 already spent on single Terry attacks.
#
# CAVEAT, stated in advance: this measures the RATIO of the two sides' outputs, not either one.
# It cannot distinguish a cap on my stats from an over-model of Narses; it only says whether the
# 1.74/1.21 split is a real asymmetry or an artifact of the win/lose confound.

# ------------------------------------------------- next step
# STOP FITTING TOTALS.  A total is rate x rounds and the two errors cancel; that degeneracy is
# what made the last dozen changes look inert.  Fit the ROUND COUNT first -- it isolates the
# opponent's per-round damage with no contribution from mine -- then fit the rate.
#
# CAPTURE THE TRIGGER ROWS ON EVERY REPORT FROM NOW ON.  They are worth more than the loss
# totals: a Yang lineup yields a round count for free, and the round count is the observable that
# identifies the model.  Where the loser's mail is censored, pull the winner's copy instead.
#
# The obvious suspect for "the sim ends fights ~2x too early" is the engagement term
# sqrt(n_u * army_min) with army_min frozen at battle start (ARMY_MIN_LIVE, ENG_A, ENG_B in
# sim.py are already switches for exactly this).  Worth testing against the round counts BEFORE
# touching anything else, because the round count can now falsify it directly.

# FIRST RESULT FROM THE NEW OBSERVABLE (ARMY_MIN_LIVE=1, i.e. army_min recomputed each round
# instead of frozen at battle start).  Tested against round counts, which is the point -- this is
# a survival-side hypothesis, so the round count judges it and the totals barely can:
#     fight                  rounds sim/real     totals k
#     Terry 20k mixed          0.77 -> 0.98      2.01 -> 1.95
#     Narses 500 solo          0.48 -> 0.64      0.68 -> 0.69
#     Narses mixed atk 10k     0.57 -> 0.57      1.04 -> 1.09
#     Terry 10k all infantry   3.32 -> 5.86      1.83 -> 1.79   (noise-dominated, ignore)
# rms log err over all nine totals 0.366 -> 0.348.
# So it moves both observables the right way and lands the best-measured fight almost exactly.
# DEFAULT NOT FLIPPED.  It is a partial fix -- 0.64 still means the fight ends too early -- and
# the per-round rate error (1.4x) is untouched.  Fitting one channel at a time is the entire
# lesson of the last thirty reports; taking this now would re-confound the two.


# ------------------------------------------------- firing rates (firing.py)
# With the round count known, every trigger row becomes a firing RATE, comparable directly to
# heroes.PROC_SPEC.  One report is therefore a calibration table for the whole skill layer --
# including the opponent heroes, whose schedules were never more than prose scrapes.
#
# 15 of the 21 modelled rows disagree by more than 1.5x.  The two that do not are Yang's Ice Zone
# (0.97) and Avalanche (1.03), which is not independent evidence: they defined the round count.
#     Unyielding Shield  modelled .375  measured .822   2.19x
#     Hero's Domain      modelled .500  measured .803   1.61x
#     Art of War         modelled .250  measured .382   1.53x
#     Arcane Pact        modelled .400  measured .184   0.46x
#     Rally Flag         modelled .400  measured .197   0.49x
#     Volley             modelled .100  measured .053   0.53x
#     Howling Wind       modelled .300  measured .171   0.57x   ... and eight more
# Note Volley and Howling Wind are TOOLTIP values, not scrapes, and they still come in at ~0.55.
# Note also that Yang's own rows 1-2 sit at 1.00 while his rows 3-5 sit at 0.53-0.66 -- same
# hero, same troops, same rounds -- so this is not a uniform rescaling of everything.
#
# CORRECTION TO THE PREVIOUS ENTRY.  It said the fight "ran about 152 rounds" and the simulator's
# 73 was too early by 2.1x.  Stated too precisely.  Most rows coming in low is ALSO what a
# too-high round count would produce, so the count has to be solved for, not assumed.  Solving it
# over the non-Yang rows gives a broad, poor minimum near 120 (rms log err 0.53, and 0.53-0.59
# anywhere between 100 and 152).  The honest statement: the fight ran 120-156 rounds and the
# simulator is early by 1.6-2.1x.  The direction and rough size hold; the second decimal did not.
# Avalanche remains the anchor because it is PERIODIC -- 39 triggers of an every-4th-round skill
# is near-deterministic, where every chance rate is only as good as the number scraped for it.
#
# ALSO CORRECTED: allfights.py labelled mean|log k| as "rms log err".  Mean-abs is always the
# smaller of the two, so every "rms log err" quoted above this line is really mean-abs (the
# ceil() fix "0.458 -> 0.364", the ARMY_MIN_LIVE note "0.366 -> 0.348", and the Narses joint fits
# in this file).  Comparisons between those numbers stand -- both are monotone in the errors --
# but the figures never meant what they said.  The default now prints 0.424 where it printed
# 0.366.  Both are printed from here on.

# TWO ENGINE KNOBS TESTED AGAINST THE ROUND COUNT, BOTH REJECTED AS FIXES:
#     ENG_B 0.5 -> 0.4   aggregate rounds rms 0.556 -> 0.382, and totals improve too -- but
#                        per-fight it does not converge, it OVERSHOOTS: Terry 20k goes 0.77 ->
#                        1.86 and Narses 10k 0.57 -> 1.22 while Narses 500 goes 0.48 -> 0.89.
#                        Trading all-under for mixed over/under lowers an rms without fixing
#                        anything.  This is the same trap as fitting a constant.
#     ARMY_MIN_LIVE=1    coherent but partial: 0.48 -> 0.64, 0.77 -> 0.98, 0.57 -> 0.57.  No sign
#                        flips, every fight still early.  Better shape, smaller aggregate gain.
# Neither touches the real residual: Terry/opponent-2 totals stay at 1.6-1.9 and the 500-solo at
# 0.67 under both.  Judge candidates per-fight and by sign, never by the aggregate alone.


# ------------------------------------------------- next test, pre-registered
# The engine knobs are not where the measurable error is.  15 of 21 skill rows are wrong by more
# than 1.5x, they are now directly observable, and nothing in sim.py's damage core is.  So fit
# the SKILL LAYER, and start by asking whether the ~0.55 shortfall is a real mechanism or just
# wrong numbers.  Volley and Howling Wind are tooltip values, not scrapes, and still measure
# ~0.55, which is what makes a mechanism plausible -- something like a troop ability only rolling
# when its own type acts, so a 50/20/30 march dilutes it.
#
# THE TEST: 1,500 PURE INFANTRY solo on Narses at 50/20/30, recovered from his mail.
# Pure infantry is the discriminator because it removes the dilution entirely -- one troop type,
# so Unyielding Shield can only roll for the type that is present.  It is also the longest fight
# available at this march size, which is what makes the trigger counts precise.
#
#     simulator: 207 rounds, he loses 19,337, I am wiped   (300 runs, seed 11)
#     Unyielding Shield triggers   ~78  if the tooltip .375 is simply right and dilution is real
#                                 ~171  if .822 is the true rate regardless of composition
# Those cannot be confused: the gap is a factor of 2.2 on a count in the hundreds, where Poisson
# noise is a few percent.  Read Avalanche off the same report for the round count and divide.
#
# Do NOT use pure archer for this.  It caps out around 38-51 rounds at any march size that still
# loses (5,000 archers wins outright), giving under 15 Avalanche triggers -- too few to separate
# .10 from .053 on Volley.  Infantry survives, so infantry is where the statistics are.
#
# WHY NOT MORE ENGINE FITTING: ENG_B and ARMY_MIN_LIVE were both tested against the round count
# and neither touches the residual (Terry/opponent-2 stay at 1.6-1.9, the 500-solo at 0.67).
# Chasing the damage core while a quarter of the skill schedules are 2x wrong is fitting noise.

# ATTACK WITH ALL THREE HEROES.  The whole measurement is hero panel rows: no heroes means no
# Battle Details, hence no Avalanche round count and no Unyielding Shield count, and the fight
# yields nothing.  Yang supplies the round count even in a pure-infantry march -- confirmed on
# the Terry 10,000 all-infantry report, where he still books kills with zero archers.
#
# The composition also buys a second, free reading of the same question.  Yang shows 5 rows when
# archers are present and 3 when they are not: his own skills keep firing at zero archers, while
# Volley and Howling Wind vanish outright.  So a pure-infantry march predicts Yang shows 3 rows.
# If instead they appear, troop abilities are not gated on their type at all and the dilution
# story is dead without needing Unyielding Shield at all.
#
# That observation exposed a real inconsistency in sim._alive: it skipped a troop ability only
# for a type that STARTED alive and then died, so a pure-infantry march kept firing archer and
# cavalry abilities all fight.  Fixed to require the type alive now.  NO NUMERICAL EFFECT --
# those effects carry scope=ttype and _prod already filtered them out for absent types, so every
# figure above and the 19,337 / 207 pre-registration are unchanged.  Correctness only.
#
# A NO-HERO ATTACK IS A GOOD SEPARATE TEST, for the opposite reason: it switches off my entire
# skill layer, which is where 15 of 21 measurable quantities are wrong, and measures the damage
# core nearly clean.  Three caveats: Narses keeps his heroes, so only half the skill layer goes;
# there is no round count without my panel rows; and the Stat Bonuses panel will change once hero
# expedition stats drop out, which is itself a direct check on the hero_stats=False decision.
# Worth running after the infantry test, not instead of it.


# ------------------------------------------------- 1,500 pure infantry (mail 223407017240989)
# DEFEAT.  My 1,500 wiped (525 + 975); he lost 5,460 + 10,138 = 15,598, residents 107,972
# (15,598 + 107,972 = 123,570 exactly).  Power -70,875 me, -414,960 him.
#
# MY PANEL HAD CHANGED -- the buffs from the previous session had worn off, and Special Bonuses
# now reads a single +5.0% Appointment-based Squads' Attack (his: 0.0%).  Infantry attack
# 2379.0 -> 1965.8, infantry lethality 2183.4 -> 1802.9.  The pre-registered 19,337 was computed
# on the old panel and is therefore not the model's prediction for the fight that happened.
NARSES_1500_INF_PANEL = {
    'inf': dict(attack=1965.8, defense=1941.2, lethality=1802.9, health=1801.1),
    'cav': dict(attack=1833.7, defense=1809.7, lethality=1724.3, health=1726.1),
    'arch': dict(attack=1836.5, defense=1809.4, lethality=1742.7, health=1737.6)}
NARSES_1500_INF = dict(my_troops={'inf': 1_500, 'cav': 0, 'arch': 0}, my_losses=1_500,
                       enemy=NARSES, enemy_troops={'inf': 61_785, 'cav': 24_714, 'arch': 37_071},
                       enemy_losses=15_598,
                       my_charles=[(1, 0), (1, 0), (1, 0), (463, 0)],
                       my_sophia=[(87, 0), (1, 0), (1, 0)],
                       my_yang=[(53, 1_073), (1, 0), (79, 0)],
                       their_long_fei=[(84, 0), (1, 0), (173, 73)],
                       their_jabel=[(71, 0), (324, 83), (1, 0), (33, 0)],
                       their_rosa=[(87, 0), (1, 0), (1, 0), (18, 0)])

# NARSES NEVER HAD A BUFF -- confirmed by the player, who owns both accounts.  All the variation
# is MINE: buffs have been expiring across today's reports.  So 514.3 / 345.5 / 467.2 is his TRUE
# defence, and the 500-troop report's lower 411.9 / 271.3 / 372.7 is that same defence seen
# through a 20% Enemy Squads' Defense bonus I still had at the time.
#
# AND THAT BONUS IS RECIPROCAL, NOT MULTIPLICATIVE.  Reducing enemy defence by 20% divides the
# multiplier by 1.20; it does not multiply it by 0.80:
#     inf   true 514.3   x0.80 -> 391.4   /1.20 -> 411.9   report says 411.9
#     cav   true 345.5   x0.80 -> 256.4   /1.20 -> 271.3   report says 271.3
#     arch  true 467.2   x0.80 -> 353.8   /1.20 -> 372.7   report says 372.7
# Matches to 0.05 of a point on all three types, where the multiplicative form is out by ~20.
# This is independent corroboration of DEF_RECIP in sim.py, which uses 1/(1-c) for defence-side
# factors on the strength of the reference engine alone (Fight.java:133).  A live panel now says
# the same thing about the reduction side, from a completely separate source.
#
# RESOLVED, AND IT MOVED FOUR SCORED FIGHTS.  Which enemy panel a fight gets is decided by which
# of MY panels it used, with no guesswork: NP reconstructs to within 0.08 of a point as the
# unbuffed panel with +20/+20 applied, so every NP fight had the stack up and must see his defence
# through the accompanying -20%.  SOLO_PANEL sits at the unbuffed level (lethality 1802.9,
# identical to the post-lapse panel, against NP's 2183.4), so those fights keep plain NARSES.
#     fight                  before  after
#     Narses pure-arch 5k      1.14   1.01
#     Narses inf+arch 1k       1.53   1.05     <- the outlier that stood unexplained all session
#     Narses mixed atk 10k     1.04   1.04     (SOLO_PANEL, already right)
#     Narses mixed def 5k      1.13   1.13     (SOLO_PANEL, already right)
# All six Narses fights now sit in 0.85-1.13, against 0.68-1.60 before.  Overall rms log err
# 0.424 -> 0.363.  The 1.53 was never a modelling failure; it was a buff-state bookkeeping error.
#
# THE TERRY / OPPONENT-2 RESIDUAL IS NOT THE SAME THING and must not be "fixed" the same way.
# SPECIAL_BONUSES above records both sides of those fights, the player verified the panel was
# identical across all three, and both sides' bonuses are already folded into the Stat Bonuses
# the panels were read from.  So 1.46-2.00 there is not a buff artefact.  What is left unverified
# in those fights is the opponents' heroes -- Triton, Ava, Wee & Woo, all prose scrapes -- and
# firing.py now shows the schedules are broadly wrong.  That is where that residual lives.
#
# NARSES_ED20 is his panel AS DISPLAYED under that bonus -- not "unbuffed Narses", which is what
# an earlier version of this note wrongly called it.
NARSES_ED20 = {t: dict(d, defense=(100 + d['defense']) / 1.2 - 100) for t, d in NARSES.items()}

# WHAT THE TWO CORRECTIONS DO.  Both move toward 1, and the two fights I lost now agree:
#     1,500 pure infantry   pre-registered panel 19,337  k 1.24  ->  report's panel 13,357  k 0.86
#     500 at 50/20/30       as scored           33,080  k 0.68  ->  report's defence 39,865  k 0.82
# So my output against Narses is under-predicted by a consistent ~1.2x in both, not by 1.46x in
# one of them.  Part of what looked like a dramatic reversal was a stale panel.
# LESSON: re-derive a pre-registered number from the report's OWN panel before scoring it.  The
# prediction was honestly made on the then-current stats; it stopped describing the fight the
# moment the buffs lapsed.

# THE PRE-REGISTERED TEST: BOTH PREDICTIONS FALSIFIED, AND MORE INTERESTINGLY THAN EITHER.
#     predicted  ~78 triggers if the tooltip .375 is right and composition dilutes it
#     predicted ~171 triggers if .822 holds regardless of composition
#     OBSERVED   463
# The round count here is at most ~200 (Ambush 79/.40 = 198; Ice Zone 53/.40 = 133; the simulator
# says 206).  463 triggers over <=200 rounds is more than 2 per round, and no per-round
# probability can exceed 1.  UNYIELDING SHIELD IS NOT A PER-ROUND CHANCE ROLL AT ALL.  Modelling
# it as chance .375 is structurally wrong, not numerically wrong, and no fitted value can fix it.
# It plausibly rolls per incoming attack or per infantry sub-unit; that is untested.
#
# It does scale with infantry, sub-linearly: 250 infantry gave 125 triggers at ~0.82/round,
# 1,500 gave 463 at 2.25-3.48/round -- 6x the troops for 2.7-4.2x the rate.
#
# THE DILUTION HYPOTHESIS IS DEAD.  Stripping cavalry and archers did not bring Unyielding Shield
# down to a nominal .375; it sent the count up by a factor of 3.7.

# THE ROW-VANISHING PREDICTION WAS CONFIRMED, which is the one thing that went as expected.
# Yang shows 3 rows, not 5 -- Volley and Howling Wind are absent with zero archers.  Sophia shows
# 3, with no Assault Lance at zero cavalry.  Troop abilities really are gated on their own type
# being present, so the sim._alive fix was right.

# BUT THE TEST DESTROYED ITS OWN ROUND ANCHOR, which I should have seen when designing it.
# YANG'S AVALANCHE COLLAPSES TO 1 TRIGGER WITH ZERO ARCHERS (it fired 39 times at 150 archers).
# The same collapse is visible in the Terry 10,000 all-infantry report, whose row 2 also reads 1.
# rounds.py had written that fight off as "3 and 1 triggers, noise dominates" -- wrong reason.
# It was not noise: Avalanche structurally cannot fire without archers, so its implied round count
# was meaningless rather than merely imprecise.  A PURE-TYPE MARCH CANNOT ANCHOR A ROUND COUNT.
#
# CONSEQUENCE FOR THE EARLIER ROUND-COUNT CLAIM.  Without Avalanche, this fight's count rests on
# two chance rates that disagree badly: Ice Zone says 133 rounds, Ambush says 198, and the sim
# says 206.  In the 500-troop fight Ice Zone and Avalanche agreed at ~152 while Ambush said 100 --
# so Ice Zone and Ambush are mutually inconsistent ACROSS fights and cannot both be .40.
# "The simulator ends fights too early" rested mainly on the one fight Avalanche could anchor.
# It is not refuted here, but this fight cannot support it either.


# ------------------------------------------------- how Special Bonuses enter the panel (SOLVED)
# The 08:14:37 report's Special Bonuses page names the channels explicitly, mine against his:
#     Squads' Attack Bonus            +20.0%   /  +0.0%
#     Squads' Lethality Bonus         +20.0%   /  +0.0%
#     Enemy Squads' Defense           -20.0%   /  -0.0%
#     Appointment-based Squads' Attack +5.0%   /  +0.0%
# Every line of his is zero, which is the player's account confirmed in the game's own words.
#
# Comparing my panel with that stack active against my panel after it lapsed gives an exact,
# unambiguous mapping over all twelve stat lines -- not a fit, a match to four decimal places:
#              attack  lethality  defense  health
#     inf      1.2000     1.2000   1.0000  1.0000
#     cav      1.2000     1.2000   1.0000  1.0000
#     arch     1.2000     1.2000   1.0000  1.0000
# and his defence, seen through my -20.0%, is exactly his true defence / 1.20.
#
#     a stated +c% on one of MY stats     ->  my multiplier   x (1 + c)
#     a stated -c% on ENEMY defence       ->  his multiplier  / (1 + c)      NOT x (1 - c)
#
# The asymmetry is the point, and it is the same reciprocal form sim.py's DEF_RECIP uses for
# defence-side skills on the strength of the reference engine (Fight.java:133).  Two independent
# sources now agree, and the reduction side is confirmed against a labelled percentage rather
# than inferred from a ratio.

def with_special(panel, atk=0.0, leth=0.0, e_def=0.0, defn=0.0, hp=0.0):
    """Apply a Special Bonuses state to a base panel, in the game's own form.

    atk/leth/defn/hp are percentages on the side's OWN stats and multiply by (1 + c/100).
    e_def is the magnitude of an *opponent's* Enemy Squads' Defense bonus pointed at this side,
    so this side's displayed defence is divided by (1 + e_def/100).  Pass e_def=20.0, not -20.0.

    Panels are stored as the "+x%" the report shows, i.e. a multiplier of (100 + x) / 100.
    """
    def scaled(x, f):
        return (100.0 + x) * f - 100.0
    out = {}
    for t, d in panel.items():
        out[t] = dict(d,
                      attack=scaled(d['attack'], 1 + atk / 100.0),
                      lethality=scaled(d['lethality'], 1 + leth / 100.0),
                      defense=scaled(d['defense'], (1 + defn / 100.0) / (1 + e_def / 100.0)),
                      health=scaled(d['health'], 1 + hp / 100.0))
    return out


# Round-trip checks against the two measured panels (both exact to 0.1 of a point):
#   with_special(NARSES_1500_INF_PANEL, atk=20, leth=20)  ==  the 500-troop fight's own panel
#   with_special(NARSES, e_def=20)                        ==  his defence as the 500 report shows
NARSES_ED20 = with_special(NARSES, e_def=20.0)


# ------------------------------------------------- Terry's widgets and Ava's stars: NO CHANGE
# Reported: Terry's widgets are not all maxed and his Ava is only 4 stars, but her skills are
# fully upgraded.  Traced through sim.py, the first two facts cannot reach the model:
#     widget level  -> Side.special_bonus(), scaled by widget_levels / widget_default
#     star level    -> Side.hero_stat(), expedition stats at max star, gated by hero_stats
# allfights.py runs both sides with widget_default=0.0 and hero_stats=False precisely because the
# Stat Bonuses panel already contains both.  Reading the panel is what makes an opponent's
# account state unobservable-and-irrelevant rather than an unknown to guess at.
#
# THE TRAP THIS AVOIDS IS SHARP, because "correcting" it would have looked like progress:
#     fight                observed   panel only   +max widgets   +max star stats
#     Terry 10k all archer    1,808        2,728          2,372               658
#     Terry 10k all inf         937        1,726          1,501               391
#     opponent-2 10k mixed   15,224       23,827         18,840             4,582
#     Terry 20k mixed        22,570       46,101         39,625             9,543
# Granting Terry max widgets moves k from 1.51 to 1.31 -- the right direction -- while being
# double-counting.  A metric improving is not evidence a change is correct.
#
# THE THIRD FACT IS THE USEFUL ONE.  Skill LEVEL is not in the panel and is not scaled by stars or
# widgets: heroes.py stores flat magnitudes (Ava: e_def 25, Chiaroscuro proc_e_taken 25, Light and
# Cold leth 25) which are max-level values.  "Fully upgraded" confirms those are right for Terry,
# so under-levelled opponent skills is now excluded as an explanation for the 1.46-2.00 residual.
# What is left there is the scraped magnitudes and SCHEDULES themselves -- and firing.py already
# shows 15 of 21 schedules wrong by more than 1.5x.  The residual has nowhere else to hide.
#
# RETRACTED -- I read that thread wrong.  Terry's Yang shows 4 rows because HIS VOLLEY FIRED
# ZERO TIMES AND THE PANEL OMITS ZERO-TRIGGER ROWS ENTIRELY.  His 4th row is everyone else's 5th.
# He is not missing an ability; nothing differs between the two archer squads.  Re-mapped:
#     mine   Ice Zone 9   Avalanche 7   Ambush 8   Volley 1   Howling Wind 5
#     Terry  Ice Zone 8   Avalanche 6   Ambush 5   (Volley 0, omitted)   Howling Wind 6
# which is two closely matching archer squads, exactly as it should be.
#
# THE GENERAL RULE MATTERS MORE THAN THE THREAD: ROW POSITION IS NOT A STABLE INDEX.  A row that
# never fired is not shown, so indices shift up and any positional mapping is only valid once the
# row COUNT has been checked against what that hero should have.  firing.py maps by position and
# now refuses to do so silently when the count is wrong.  Expected counts are 3 skills plus the
# troop abilities of the hero's own type: infantry 4, cavalry 4, archer 5.
#
# THE UPSIDE: AN ABSENT ROW IS DATA, NOT A GAP.  It says "fired exactly zero times", which bounds
# the rate.  Terry's Volley at 0 over ~25 rounds, mine at 1 over the same 25, and mine at 8 over
# ~152 in the 500 fight all sit under a nominal .10 -- the same ~0.55 shortfall firing.py found.
#
# THE SIX-ROW ANOMALY IS SOLVED, AND IT WAS A MISSING MECHANIC.  Row 6 is WARDING IMPALER, a
# Truegold cavalry ability, tooltip read off the Sophia/Ava block of a Terry report:
#     "The reforged [Assault Lance] is a great improvement not just in strength but defense as
#      well, granting Cavalry a 10% chance of taking half damage when under attack."
# The model had NO cavalry damage reduction of any kind.  Now in TROOP_SKILLS as
# ('Warding Impaler', 'proc_taken', 0.10 * 50.0, 0.10, 'cav').
#
# CAVALRY DISPLAYS THREE TROOP ABILITY ROWS, not one.  Order pinned from the report rather than
# from list order: row 5 is the only one booking kills so it is Assault Lance (double damage), and
# the tooltip is anchored to the last row, which leaves Ambusher first.  firing.py now holds this
# as TROOP_ROWS instead of deriving it from TROOP_SKILLS, which would have got it wrong.
#     row 4  Ambusher          16 fired   .105/round   modelled .20   0.53
#     row 5  Assault Lance     11 fired   .072/round   modelled .15   0.48
#     row 6  Warding Impaler    4 fired   .026/round   modelled .10   0.26
# Ambusher joins the ~0.55 cluster, which now covers all three troop types.  Note Ambusher has no
# modelled firing rate at all: sim.py carries it as Side.ambusher, a targeting effect, so it never
# appears in TROOP_SKILLS and firing.py can only measure it, not compare it.
#
# ADDING IT MAKES THE AGGREGATE SLIGHTLY WORSE AND IT STAYS IN.  rms log err 0.363 -> 0.371,
# mean|log| 0.273 -> 0.286; some fights improve (pure-arch 1.01 -> 0.97), others worsen (mixed def
# 1.13 -> 1.18).  A tooltip-confirmed mechanic is not deleted because a fit likes it less -- that
# is the same discipline as refusing the max-widget "improvement" three entries above, and the
# opposite of what k-chasing did for most of this session.  What the regression actually says is
# that something else is compensating for the absent cavalry mitigation, which is a lead.


# ------------------------------------------------- Truegold gates troop abilities (per type)
# Reported: the sixth ability modifies the other Truegold ability and these unlock at higher TG.
# The tooltip agrees on the first half in the game's own words -- "the REFORGED [Assault Lance]".
# Community sources do not document the progression at all: searched, and fetched kingshot.net
# and kingshotdata.com War Academy pages, neither of which carries ability names, chances or
# unlock levels.  One summary gave base-unlock values of 25% / 10% / 20% for Unyielding Shield,
# Assault Lance and Howling Wind -- exactly two-thirds of the 37.5 / 15 / 30 tooltips in this
# file, consistent with the values scaling by TG level -- but that is an unverified summary and is
# NOT used for anything.
#
# THE REPORTS PROVE IT DIRECTLY, which is better than any source.  One fight, same rounds, both
# sides, counting troop-ability rows (rows 4+):
#     mine, TG8    Charles inf 1     Sophia cav 3     Yang arch 2
#     Narses, TG2  Long Fei inf 0    Jabel  cav 1     Rosa arch 1
# Long Fei shows three rows -- his skills and nothing else -- with 61,785 infantry over ~152
# rounds.  Unyielding Shield would have fired dozens of times.  HIS TG2 INFANTRY DOES NOT HAVE IT.
# sim.py handed every troop ability to any side fielding a hero, on the explicit and now-falsified
# grounds that "every PvP report shows both sides with Unyielding Shield firing".
#
# Side.troop_abilities now caps them per troop type.  ONLY THE PROVEN CAP IS APPLIED:
#     variant                      Narses six mean|log|    all ten rms
#     no gate                             0.096               0.377
#     inf=0 only (proven)                 0.034               0.367
#     inf=0 cav=0 arch=1 (guessed)        0.132               0.381
# His cavalry and archer rows are short too, but the panel does not say WHICH ability each is, and
# guessing overshoots worse than not gating at all.  Left out until a tooltip settles it.
#
# WHERE THAT LEAVES THE MODEL.  All six Narses fights: 0.94, 0.99, 1.06, 0.94, 0.90, 0.99.
# Against the one opponent whose troops, tiers, buff state, heroes AND Truegold ability set are
# all pinned down, the simulator is within 10% everywhere and within 6% in five of six.  Every
# remaining error in the set is Terry and opponent-2 (1.49-1.99), both TG8 so ungated, both with
# unverified scraped heroes.  The residual is now entirely on the unverified side of the data.


# ------------------------------------------------- the reforge tier, from the barracks tooltips
#     Immortalists  (Truegold Infantry, TG8): "increasing Infantry Defense by 4%, reducing an
#                    extra 10% damage when [Unyielding Shield] is active"
#     Truegold Wind (Truegold Archers,  TG8): "increasing Archers' basic Attack by 4%.  Archers
#                    can deal an extra 25% damage when [Howling Wind] is active"
# Same shape as Warding Impaler: a flat research stat plus a CONDITIONAL MODIFIER on the base
# ability.  That confirms the reading -- these resize an existing ability rather than being one.
#
# IT ALSO EXPLAINS A ROW COUNT I HAD NOT QUESTIONED.  A modifier gets no Battle Details row of its
# own, which is why Charles shows 4 rows and Yang 5 -- exactly the base abilities -- while Sophia
# shows 6.  Warding Impaler is the exception because it grants a distinct new proc (10% chance of
# half damage) rather than resizing an old one, so it earns a row.  Rows count PROCS, not upgrades.
#
# ONLY THE CONDITIONAL HALF IS MODELLED.  The flat +4% Infantry Defense and +4% Archers' basic
# Attack are War Academy research and are therefore already inside the Stat Bonuses panel every
# fight is parameterised from.  Adding them would double-count exactly as granting Terry max
# widgets would have.  The deltas apply at the base ability's own trigger, so they resize its
# effect rather than rolling again:  Unyielding Shield .375 x 36 -> .375 x 46 (EV 13.5 -> 17.25),
# Howling Wind .30 x 50 -> .30 x 75 (EV 15.0 -> 22.5).  Narses gets neither: a TG2 account holding
# a top-tier reforge is not credible, though note his rows cannot confirm that either way, since
# a reforge adds no row.
#
# EFFECT.  Aggregate is flat (rms log err 0.362 -> 0.360) but the structure changed, and the part
# that matters most improved:
#     Narses 500 solo        0.90 -> 0.99      <- these two DIRECTLY measure my own output
#     Narses 1500 pure inf   0.99 -> 1.02      <-
#     Narses mixed def 5k    1.06 -> 0.98
#     Narses mixed atk 10k   0.99 -> 0.96
#     Narses pure-arch 5k    0.94 -> 0.88
#     Narses inf+arch 1k     0.94 -> 0.87
# The two fights that measure MY damage output now sit on 1.00.  The four that measure HIS now
# under-predict by 2-13%, which points at his side still being too weak in the model -- his
# scraped hero magnitudes, or the cavalry and archer abilities his TG2 rows show him having but
# which I declined to guess at.  That is a sharper question than "k is 1.5" ever was.


# ------------------------------------------------- does the Truegold work fix Terry?  NO.
# Terry and opponent-2 sit at 1.51 / 1.80 / 1.55 / 2.03, essentially unmoved by everything in the
# reforge and TG-gating work.  The reason is structural, not a shortfall in the modelling: TERRY
# IS TG8 LIKE ME, so he gets exactly the abilities and reforges I do and they cancel.  Every
# change that fixed the Narses fights was an ASYMMETRY -- his TG2 infantry lacking Unyielding
# Shield, his missing reforges, my lapsed buff stack.  There is no asymmetry with Terry to find.
#
# AND NO GLOBAL SKILL-LAYER CHANGE CAN FIX BOTH.  firing.py measures nearly every chance skill at
# ~0.55 of its modelled rate, on both sides and all three troop types, so the obvious move is to
# apply that to PROC_SPEC.  Tested:
#     group             as it stands   procs x0.55
#     Terry / opp2         0.537          0.249      <- nearly fixed
#     Narses six           0.068          0.797      <- destroyed
# The two groups want opposite corrections.  My procs are identical in both, so the difference is
# not mine: against Narses my troops live ~152 rounds and procs accumulate, against Terry ~25.
# Slowing procs takes 3x off my output in the Narses fights and 1.9x in the Terry ones, and only
# the latter wanted it.  NOT APPLIED -- it is a diagnostic, and "fixes one group by breaking the
# other" is the signature of a wrong mechanism, however good the measurement behind it.
#
# WHAT IS ACTUALLY LEFT.  Terry's residual has the shape of HIS side being too weak in the model:
# under-model his output, my troops survive too long, my output comes out ~2x high.  Every other
# input to those fights is now verified -- panels read from the report, buff state recorded on
# both sides, tiers and TG known, troop abilities symmetric and cancelling, skill LEVELS confirmed
# maxed by the player.  The only unverified thing left in the entire set is the SKILL MAGNITUDES
# of Triton, Ava and Wee & Woo, which are prose scrapes and have never been checked against
# anything.  For comparison, my own nine are all tooltip-verified on kind, magnitude, scope and
# schedule, and my side is the one that now reads 0.99-1.03.
#
# THE ASK IS SMALL AND EXACT: the three skill tooltips for Triton and for Ava, read off the hero
# screen the same way Sophia's and Yang's were.  That is six numbers, and it is the last
# unverified input in the whole calibration.


# ------------------------------------------------- Triton and Ava verified: the last unknown
# All six tooltips, Lv. 5, read off a Terry report.  FOUR OF SIX WERE ALREADY RIGHT, and the two
# that were wrong were both badly LOW -- exactly the direction the residual predicted, which is
# the first time a prediction in this file has been confirmed rather than falsified:
#     Command of Power  "total Squads' Defense by 25%"                        25        ok
#     Warfare of Power  "total Squads' skill damage dealt by 30%"              6 -> 30
#     Oath of Power     "Infantry Health 20%, Cavalry and Archer Health 30%"   20/30/30 ok
#     Dissolution       "total Enemy Squad's Defense by 25%"                  25        ok
#     Chiaroscuro       "50% increased damage for 2 turns every 4 turns"      25 -> 50
#     Light and Cold    "total Squad's Lethality by 25%"                      25        ok
# Chiaroscuro's SCHEDULE was already right (periodic 4, duration 2); only its size was halved.
#
# THE FIX IS TARGETED, WHICH IS WHAT SEPARATES IT FROM EVERY REJECTED CANDIDATE.  Triton and Ava
# appear on Terry's and opponent-2's side and nowhere else, so the six Narses fights do not move
# at all -- 0.88, 0.96, 0.98, 0.87, 0.97, 1.04 before and after.  Compare the procs-x0.55 test,
# which bought Terry 0.537 -> 0.249 by wrecking Narses 0.068 -> 0.797.  A correct mechanism moves
# the fights it belongs to and leaves the rest alone.
#     Terry / opp2 mean|log|   0.537 -> 0.428 (Chiaroscuro) -> 0.266 (both)
#     all ten rms log err      0.354 -> 0.282               -> 0.185
#
# CAVEAT ON WARFARE OF POWER, stated because the fit likes it and that is not evidence.  The
# tooltip says "SKILL damage dealt" and sim.py has no separate skill-damage channel -- every hero
# skill enters through the same SkillMod multiplier as basic damage, so 30 is applied generically.
# If the narrow reading were right, +30% on the ~10% of kills hero skills actually book would be
# worth about +3% overall and the fit would barely have moved; it moved a lot, so the data prefers
# the generic reading.  That is suggestive, not proof.  Two things support it independently: the
# reference engine's effect 101 is "a plain multiplier on that troop type's damage", and the value
# 30 sits naturally with its sibling skills (25 / 25 / 25 / 20-30) where the scraped 6 was an
# outlier.  If a skill-damage channel is ever built, revisit this first.

# ------------------------------------------------- where the calibration stands
#     fight                  observed        sim       k
#     Narses pure-arch 5k          72         63    0.88
#     Narses mixed atk 10k        239        228    0.96
#     Narses mixed def 5k         292        287    0.98
#     Narses inf+arch 1k          397        346    0.87
#     Terry 10k all archer      1,808      2,207    1.22
#     Terry 10k all inf           937      1,183    1.26
#     opponent-2 10k mixed     15,224     18,302    1.20
#     Terry 20k mixed          22,570     31,961    1.42
#     Narses 500 solo          48,561     46,899    0.97
#     Narses 1500 pure inf     15,598     16,149    1.04
#     mean k 1.08   spread 0.87-1.42   rms log err 0.170
# Against a measured per-rally noise of 8.8% CV, six of the ten are inside noise.  Nothing here
# was fitted: every change came from a tooltip, a panel or a row count.  The one number that was
# ever fitted -- the gear constants -- is the oldest thing in the file and should be re-derived.
#
# WHAT IS STILL OPEN, in order of how much it could still be hiding:
#   1. Terry's four sit at 1.20-1.42, a consistent over-prediction of MY output against him and
#      the only group left with any structure.  Wee & Woo (opponent-2) is still an unverified
#      scrape, and so is every joiner in the rally fits.
#   2. firing.py: 15 of 21 schedules disagree with measurement, most at ~0.55 of nominal.  This
#      is a real measurement with no correct mechanism yet -- applying it globally breaks Narses.
#   3. Unyielding Shield fires >2x per round, so it is not a per-round roll at all.
#   4. Narses' cavalry and archer TG rows: he has one of each and I do not know which.


# ------------------------------------------------- RETRACTION: the "~0.55 firing rate" was mine
# This file recorded, as a headline finding, that 15 of 21 skill schedules disagreed with
# measurement by more than 1.5x, "most at ~0.55 of nominal", across both sides and all three
# troop types.  THAT WAS A DENOMINATOR ERROR IN MY OWN ANALYSIS, not a game mechanic.
#
# A troop ability only runs while its type is ALIVE.  firing.py divided every trigger count by the
# 152-round battle length when most of those abilities stopped when the troops carrying them died.
# My troops' simulated lifetimes in that fight are infantry 71, cavalry 76, archers 79 of 152
# rounds -- and 76/152 = 0.50, 79/152 = 0.52.  That IS the "~0.55".
#
# Inverting the observed counts instead of dividing them recovers those lifetimes from the data
# alone, from five independent proc rates that never saw the simulator:
#     cavalry   Arcane Pact 70, Terror Deathblow 86, Ambusher 80, Assault Lance 73  (sim: 76)
#     archers   Volley 80, Howling Wind 87                                          (sim: 79)
# The schedules were right the whole time.  Corrected, the table reads Arcane Pact 0.92, Terror
# Deathblow 1.13, Assault Lance 0.96, Volley 1.01, Howling Wind 1.10, Ice Zone 0.97,
# Avalanche 1.03 -- and the count of genuine disagreements falls from 15 to 4.
#
# This also explains why applying 0.55 globally to PROC_SPEC fixed Terry and destroyed Narses:
# there was nothing to apply.  sim.py already models troop death; only my measurement did not.
#
# WHAT SURVIVES AS A REAL ANOMALY, now only four:
#   Unyielding Shield  1.76 per infantry-round -- still above 1, so still not a per-round roll
#   Terror Annihilation  fired 1 -- now fixed, see below
#   Ambush             0.66 against a .40 tooltip
#   Warding Impaler    0.53, but on 4 triggers, so mostly noise
#
# TERROR ANNIHILATION RECLASSIFIED AS A PERMANENT AURA.  It fired exactly once in both reports,
# with cavalry alive for 76 rounds in one of them, which is this file's own definition of an aura.
# It had been modelled as periodic 2 (~38 firings).  Its sibling Terror Deathblow is genuinely
# periodic -- 43 with cavalry, collapsing to 1 without, the same signature as Avalanche.
#
# ALSO NEW, and unexplained: DAMAGE-DEALING hero skills need their own troop type, buff skills do
# not.  With zero cavalry Sophia's Arcane Pact still fired 87 times over ~207 rounds (.42 against
# a .40 tooltip) while Terror Deathblow collapsed to 1.  Yang behaves the same way.  But Sophia's
# surviving skills track her CAVALRY lifetime while Yang's track the whole battle, and that
# asymmetry between two heroes on the same side is the sharpest open question in the skill layer.

# ------------------------------------------------- state after the retraction and the aura fix
#     mean k 1.05   spread 0.86-1.28   rms log err 0.126   mean|log| 0.095
# Nine of ten fights are inside 30%, six inside the measured 8.8% per-rally noise.  For contrast,
# this session opened at mean k 1.48, spread 1.04-2.01.


# ------------------------------------------------- Narses' heroes verified: THE FIT GOT WORSE
# All nine tooltips, plus Ambusher and Volley confirmed unchanged.  EIGHT OF THE NINE WERE WRONG,
# and the five proc magnitudes were all badly LOW -- the direction the residual predicted:
#     Mighty Paragon        40% chance, damage taken -40%       20 -> 40
#     Celestial Sustenance  Squad's Defense +20%                25 -> 20
#     Art of War            25% chance of dealing 180% damage   25 -> 80
#     Rally Flag            40% chance, damage taken -50%       20 -> 50
#     Hero's Domain         50% chance of 50% more damage       25 -> 50
#     Youthful Rage         Squads' Lethality +25%              25  ok
#     Chaos Gambit          40% chance, Damage Dealt +40%       20 -> 40
#     Enchanting Dance      Enemy Damage Dealt -16%   -- the file called this "Rose of War", 20
#     Golden Rhythm         Archers' total Attack +24%          30 -> 24
#
# APPLYING VERIFIED DATA MADE THE MODEL FAR WORSE: Narses' six went from 0.86-1.05 to 0.27-3.39,
# all-ten rms log err 0.126 -> 0.899.  The values are read off the game, so THE PREVIOUS GOOD FIT
# WAS TWO ERRORS CANCELLING: magnitudes about half to a third of true, against a combination rule
# that over-applies them by about the same factor.  Every proc correction adds error monotonically
# (bisected: 0.071 -> 0.367 -> 0.290 -> 0.657 -> 0.921 -> 1.072 -> 1.199), so it is not one bad
# reading.  The data stays in.  Reverting it to recover 0.126 would be fitting the metric against
# the game, which is the one thing this file has refused to do all session.
#
# THE COMBINATION RULE IS NOT SIMPLY MULTIPLICATIVE-VS-ADDITIVE.  _prod multiplies distinct procs;
# the reference engine accumulates (Skill.damage(): coef = coef + value/100).  Tested by patching
# _prod to accumulate: all-ten rms 0.891 -> 0.754, Narses 1.137 -> 0.945.  Better, nowhere near
# enough, so that is not the fault either.
#
# WHAT THE TRIGGER COUNTS SAY, and this is the real find: PROCS ROLL PER ATTACK, NOT PER ROUND.
#     Hero's Domain     .50 chance    324 in ~207 rounds = 1.57/round = 3.1x nominal
#     Art of War        .25 chance    173 in ~207 rounds = 0.84/round = 3.4x nominal
#     Unyielding Shield .375 chance   463 in ~207 rounds = 2.24/round = 6.0x nominal
# A per-round probability cannot exceed 1.  Narses fields three troop types, so ~3 attacks per
# round, and 3x nominal is exactly what a per-attack roll produces.  Unyielding Shield at 6x is a
# defensive proc rolled when attacked, so it may see two rolls per attacking squad.
#
# WHY THAT IS THE FAULT.  battle_mc rolls each chance skill ONCE PER ROUND at squad level and
# applies the result to that whole side's damage for the round.  If the game instead rolls per
# attack and boosts only THAT attack, the expected damage is the same -- but the model multiplies
# the entire round's output by a proc that should have touched a third of it.  With three damage
# procs live on Narses that is close to the 3x over-prediction observed, and it explains why the
# error only surfaced once the magnitudes were correct: at a third of true magnitude the
# over-application cancelled exactly.
#
# NEXT STEP, and it is now a specific engine change rather than a search: roll chance procs per
# SOURCE TROOP TYPE inside the per-type damage loop, not once per side per round.  The trigger
# counts predict the result quantitatively -- a side fielding n troop types should show n times
# nominal -- so it is falsifiable against every report already in this file.
#
# STATE: mean k 1.76, spread 0.27-3.39, rms log err 0.899.  This is a REGRESSION in fit and an
# advance in correctness, and the two should not be confused.  The model was accidentally right.


# ------------------------------------------------- skill level is per ACCOUNT, not per hero
# Narses has not fully upgraded his heroes.  His tooltips read Long Fei Lv. 4, Rosa Lv. 4, Jabel
# Lv. 5, while Triton's and Ava's on Terry's account all read Lv. 5.  So the nine magnitudes above
# are correct for scoring the NARSES fights and wrong as canonical hero data -- Belisarius has
# every hero maxed, and Long Fei, Jabel and Rosa are all in LEGENDARIES, which run.py, elo.py,
# gear.py, waves.py and research_value.py draw on to rank HIS lineups.
#
# THIS WAS LIVE CONTAMINATION, not a hypothetical: Long Fei and Rosa both appear in run.py's top
# 15 trios, so writing Narses' Lv. 4 numbers into heroes.py silently under-rated two legendaries
# in every recommendation the tool would have made.  Caught only because the player said so.
#
# heroes.SKILL_LEVEL now records the level each verified magnitude was read at, UNDERLEVELLED
# names the heroes below max (Long Fei, Rosa), and run.py prints a warning whenever either shows
# up in a ranking.  The Lv.4 -> Lv.5 step is NOT guessed: the two levels are never seen for the
# same skill, and the scraped values they replaced were wrong by inconsistent factors
# (Chiaroscuro 25 against a true 50, Warfare of Power 6 against a true 30), so they carry no curve.
#
# WHAT WOULD FIX IT PROPERLY: the same nine tooltips off an account that has them maxed, or the
# same hero at two levels so the step can be measured.  Until then those two heroes are usable for
# scoring Narses and not for choosing Belisarius' marches.
# NOTE the allfights scoring is unaffected -- those fights ARE against Narses at his own levels --
# so the 0.899 regression and the per-attack proc finding stand exactly as recorded above.


# ------------------------------------------------- engine: per-attack procs (DONE, and it is
#                                                    correct, and it does NOT fix the fit)
# IMPLEMENTED.  heroes.PER_ATTACK marks the procs whose tooltip describes an ATTACK; battle_mc
# now rolls those once per attacking troop type inside the per-type damage loop and applies each
# roll only to that type's damage.  Everything else still rolls once per round.
#
# VALIDATED ON A NEW OBSERVABLE (procs.py).  Simulated trigger counts against the 1,500-troop
# report, where Narses fielded three troop types throughout:
#     proc              observed   per-round   per-attack   model/observed
#     Art of War             173          52          155        0.90
#     Hero's Domain          324         104          310        0.96
#     Mighty Paragon          84          83          248        0.99
#     Rally Flag              71          83          248        1.17
#     Chaos Gambit            87          83          248        0.95
# The two ATTACK procs need the per-attack column and the three others the per-round column, and
# that split is the tooltip wording rather than a fitted choice.  The model had never been held
# to trigger counts at all before this.
#
# IT DOES NOT FIX THE DAMAGE ERROR, and that was predictable: rolling per type and applying per
# type leaves the EXPECTED damage unchanged, only its variance.  rms log err 0.899 -> 0.902.
# Recorded so the next person does not expect otherwise.
#
# FIVE COMBINATION RULES TESTED AND REJECTED -- all-ten rms log err, verified magnitudes in place:
#     procs multiply, by skill name (current)          0.891
#     procs accumulate within kind (reference form)    0.754
#     damage reductions: strongest only, no stacking   0.918
#     damage reductions: summed, capped at 90%         0.764
#     hero 'all' scope read as the hero's OWN type     0.396
# The last is much the best and is NOT adopted: the tooltips say "total Squads'" and "all squads"
# outright, so a rule contradicting them that improves the fit is compensating for a different
# error -- the same signature as procs-x0.55 and ENG_B 0.4.  Adopting it would rebuild exactly the
# two-errors-cancelling state that the verified magnitudes just exposed.
#
# WHERE THAT LEAVES IT.  Narses' output is over-predicted about 3x with correct magnitudes on
# both sides, and no stacking rule tried accounts for it.  The remaining suspects, none tested:
#   - proc magnitudes may not be a straight multiplier on the damage term at all
#   - "damage taken -50%" may reduce the DEALT damage of the attacker rather than raising defence
#   - the reference's Skill.protect() pool (sim.PROTECT, never implemented) soaks a share of dead
#     per round and would blunt exactly the runaway feedback that turns 1.35x into 3x
# PROTECT is the one with an actual reference implementation behind it and has never been tried.


# ------------------------------------------------- Elo rerun on the current engine
# 200 battles per pairing, 144,200 troops a side, mirror stats.  What today's verified data did to
# the ranking (Bradley-Terry, 1500 = mean of all 14 lineups):
#     Charles / Jabel / Wee & Woo  60/15/25    1528 -> 1765   +237
#     Triton / Thrud / Yang  50/20/30          1047 -> 1204   +157
#     Charles / Ava / Yang  45/30/25           1297 -> 1387    +90
#     Long Fei / Sophia / Wee & Woo  40/60/0   1840 -> 1918    +78
#     Charles / Sophia / Wee & Woo  55/45/0    1480 -> 1300   -180
#     Charles / Sophia / Marlin  55/45/0       1544 -> 1379   -166
#     Charles / Sophia / Yang  60/40/0         1589 -> 1431   -158
# The movement is exactly the verified changes and nothing else: every Jabel and Triton lineup
# rose (Rally Flag 20->50, Hero's Domain 25->50, Warfare of Power 6->30) and every Sophia lineup
# fell (Terror Annihilation reclassified from periodic-2 to a one-shot aura).
#
# HOW MUCH TO TRUST IT.  These are mirror-stat pairings, and an error hitting both sides equally
# cancels out of a relative ranking -- the same cancellation the crossover analysis established.
# So the ORDER survives the 3x absolute error far better than any single rating does.  What does
# NOT cancel is a difference in how much two lineups lean on procs, and that is precisely what
# moved: the biggest risers are the ones whose procs got stronger, through the same channel the
# model over-applies.  So the movers are the least trustworthy part of the table.
#
# TWO THINGS THAT ARE SAFE TO READ:
#   Every defence lineup outranks every attack lineup, and attacker win rates run 0-52% with means
#   of 7-21%.  On equal troops and mirror stats the garrison wins, and that is not a small edge.
#   Long Fei tops the table while carrying Lv.4 magnitudes, so his lineup is if anything UNDERSTATED.
#
# UNVALIDATED CONFIGURATION, worth fixing before this file is trusted further: elo.py runs Side()
# with hero_stats=True and widget_default=1.0 against USER_STATS (the profile Bonus Overview),
# while every fight allfights.py validates runs the opposite way -- in-battle panel stats with both
# switches off.  The engine is calibrated in one configuration and used for planning in another.


# ------------------------------------------------- the whole roster, from the site
# crawl_heroes.py pulls every hero's Expedition skills at every level from kingshotoptimizer.com
# into hero_skills.json; heroes.apply_site_magnitudes() scales the modelled effects to MAX level.
#
# VALIDATED BEFORE TRUSTED.  Triton's, Ava's and Jabel's Lv.5 tooltips match the site's L5 exactly,
# and Long Fei at L4 round-trips to 40 / 20 / 80 -- precisely his in-game tooltips.  Six skills
# whose site L5 is exactly 1.25x my in-game Lv.4 reading, which is the L4->L5 step.
#
# THE SCRAPED MAGNITUDES WERE WRONG ALMOST EVERYWHERE -- 44 of the modelled skills disagreed with
# the site's max, by factors from x0.10 to x5.00:
#     Alcar Praetorian Will   100 -> 10     Thrud Reckless Charge     20 -> 100
#     Yang Avalanche           25 -> 100    Hilde Elixir of Strength  25 -> 100
#     Yang Ice Zone            40 -> 100    Vivian Trap of Greed      15 -> 60
#     Sophia Arcane Pact       20 -> 40     Wee & Woo Artillerymen    15 -> 10
# THIS IS WHY THE ELO TABLE LOOKED WRONG.  Charles, Triton, Ava and Jabel came out unchanged --
# they were the only ones ever verified in game -- and every other hero in those pools was ranked
# on numbers that were off by up to 10x.  The ranking was never measuring lineup quality.
#
# Side.skill_levels models an opponent's under-levelled heroes: Narses runs Long Fei 4, Jabel 5,
# Rosa 4.  heroes.level_scale() reads the step off the site rather than guessing it, which is the
# thing the previous entry explicitly refused to invent.
#
# EFFECT ON THE FIT: rms log err 0.899 -> 0.884, but the shape changed completely.
#     Narses six   0.25-3.24  ->  0.66-1.51     much better
#     Terry / opp2 1.20-1.51  ->  2.32-5.44     much worse
# Both sides' magnitudes roughly doubled, so the proc-combination fault -- procs multiplying by
# skill name -- now compounds over much larger numbers and dominates everything else.  Against
# Narses my troops live ~150 rounds and the error saturates; against Terry ~25 rounds and it does
# not.  The data is now right and the mechanism is wrong, which is the correct order to fix them
# in but does not yet show up in the metric.
#
# STILL UNSOURCED, 4 skills: Saul Resourceful, Yeonwoo Well-Traveled, Amane Exorcism, Fahd
# Pathfinder.  None is in a lineup any current tool ranks.


# ------------------------------------------------- hero base stats: checked, and NOT the problem
# The same site carries each hero's Expedition stats, split across two sections -- star Attack and
# Defense under the "Expedition" heading, the exclusive weapon's Lethality and Health under
# "Expedition Stats".  crawl_heroes.py now captures both.
#
# UNLIKE THE SKILL MAGNITUDES, hero_stats.json was essentially right: 22 of 29 heroes matched the
# site exactly, and four of the seven misses were heroes with no exclusive weapon where the model
# stores 0 and the site simply has no tile -- agreement, not disagreement.  Only four real errors:
#     Chenko  exp_atk/def  200.16 -> 140.11
#     Fahd    exp_atk/def  200.16 -> 140.11
#     Gordon  exp_atk/def  200.16 -> 140.11
#     Helga   weapon       55.00  -> 55.50
# Chenko is in ATTACK_JOINERS and the rally fits carry four of him, so that one is not cosmetic.
#
# THE CONTRAST IS THE POINT.  44 skill magnitudes were wrong by up to 10x while 22 of 29 stat
# blocks were exact.  Both tables came from prose scrapes, but the stats are single numbers a
# scraper reads off a page while the skills needed a human to parse a sentence into kind, scope
# and magnitude -- and that is where it went wrong.  So the Elo problem was the SKILL layer alone,
# and checking the stats was worth doing precisely because it ruled the other half out.
#
# NO EFFECT ON allfights (hero_stats=False there -- the reported panel already contains them) and
# none on the Elo ordering either; the corrected heroes were not near the top.  rms log err stays
# 0.884 and the ranking is unchanged from the previous entry.


# ------------------------------------------------- NO HEROES ON EITHER SIDE (mail 223407017262625)
# The single most useful report in this file.  Battle Details reads "Infantry Hero: Vacant",
# "Cavalry Hero: Vacant", "Archer Hero: Vacant" on BOTH sides, and Special Bonuses reads "No
# Special Stats Bonuses".  That is the damage core with the entire skill layer switched off and
# no buff state to reconstruct.
#     me   1,000 (500/200/300) T11 TG8, panel inf 1102.3 / 1090.7 / 1042.4 / 1040.6
#     him  83,600 (thirds)     T10 TG2, panel inf  238.6 /  232.0 /  179.9 /  181.0
#     VICTORY: I lose 241 + 446 = 687 of 1,000 (313 residents); he is wiped, 29,262 + 54,338.
#     I won, so my 687 measures HIS output -- the uncensored quantity.
#
#     SIMULATED 721 AGAINST 687 OBSERVED.  k = 1.05.
#
# THE DAMAGE CORE IS CORRECT.  Everything the model does without heroes -- sqrt(n_u * army_min),
# the A and D stat products, targeting, per-type tiers and Truegold levels, attrition, stochastic
# rounding, casualty accounting, troop abilities and their TG gating -- lands within 5% on a fight
# with an 84:1 troop mismatch.  EVERY REMAINING ERROR IN THIS FILE IS IN THE HERO SKILL LAYER.
# That is worth more than any of the fits above, because it converts an open-ended search over the
# whole engine into a bounded one over a single subsystem.
#
# TWO THINGS IT SETTLES ON THE WAY:
#   TROOP ABILITIES NEED NO HERO.  Unyielding Shield fired 104 times with all three hero slots
#   vacant.  sim.py's comment claimed they apply "whenever the side fields any hero at all" --
#   corrected.  They are War Academy research, carried by the account.
#   HIS TG2 ROWS ARE NOW VISIBLE RATHER THAN INFERRED: one cavalry ability (Ambusher, 25 triggers)
#   and one archer (7), with his infantry section blank.  That is exactly the {inf 0, cav 0,
#   arch 1} cap I guessed and then REJECTED for making the fit worse -- it was right, and it read
#   as wrong only because the hero layer around it was wrong.  With the cap: k 1.05 and I win 95%.
#   Without it: k 1.46 and I lose every time.
#
# ALSO A CLEAN MEASURE OF WHAT HEROES ARE WORTH: my infantry attack is 1102.3 here against 2379.0
# with a lineup and the 20% stack -- so hero expedition stats and buffs together are most of the
# panel, which is why hero_stats=False against a reported panel has always been the right call.


# ------------------------------------------------- next test, pre-registered: bisect the hero layer
# The heroless fight worked because it switched off a whole subsystem at once.  Do the same to the
# hero layer, which is now the only place the error can be.  It splits cleanly down the middle:
#     CHARLES  Intimidation, Iron Bodies, Great Justice -- three PERMANENT auras, ZERO procs
#     YANG     Ice Zone, Avalanche, Ambush              -- three PROCS, ZERO auras
# So one march with Charles alone tests the aura channel and one with Yang alone tests the proc
# channel, against a heroless baseline that is already measured at k 1.05.  Same 1,000 troops at
# 500/200/300, same target, other two hero slots left Vacant.
#
# THE PANEL IS ITSELF A PREDICTION, and a free end-to-end check on hero_stats.json:
#     Charles only -> INFANTRY ATTACK must read 1752.8  (1102.3 + his 650.52)
#     Yang only    -> ARCHER ATTACK must read 1623.5    (1083.1 + his 540.43)
# If either line comes back different, hero_stats.json is wrong and nothing downstream is safe.
# If both land, the stat half of the hero layer is confirmed and only the skill half is left.
#
# PRE-REGISTERED, against Narses at 83,600 in thirds, his TG caps {inf 0, cav 0, arch 1}:
#     no heroes      726 losses (measured 687, k 1.05)   138 rounds
#     Charles only   193 losses                          106 rounds
#     Yang only      101 losses                           22 rounds
#
# WHAT EACH OUTCOME MEANS:
#   Charles lands and Yang does not  -> auras are right, procs are wrong.  That is the expected
#       result if _prod's multiply-by-skill-name is the fault, and it would localise the bug to
#       one function with three known-good and three known-bad inputs to test against.
#   Both land                        -> a single hero is fine and the fault is in COMBINING
#       several, which points at stacking rather than at any one skill's magnitude or schedule.
#   Charles misses too               -> the aura channel is wrong as well, and the "damage core is
#       correct" conclusion needs re-examining, because auras are just stat multipliers.
#   Yang's 22 rounds is worth watching on its own: three procs at full magnitude end the fight six
#   times faster than no heroes at all, which is the over-application showing up as a round count
#   rather than as a loss total, and Avalanche's trigger count will measure it directly.


# ------------------------------------------------- CHARLES ONLY (mail 223407017263368)
# 10,000 at 5,000/2,000/3,000 against the same heroless Narses, 30 minutes after the baseline.
# Cavalry and Archer slots read Vacant on both sides; only Charles is fielded.
#     VICTORY: I lose 15 + 24 = 39 of 10,000.  He is wiped.
#     SIMULATED 44.  k = 1.12.
#
# THE AURA CHANNEL IS CORRECT.  With the core at 1.05 and core-plus-three-auras at 1.12, and the
# full lineup against Terry at 2.3-5.4, THE FAULT IS IN PROCS.  That is the outcome this test was
# pre-registered to distinguish, and it lands on the branch that localises the bug to _prod.
#
# MY PANEL PREDICTION WAS WRONG, AND USEFULLY SO.  I predicted infantry attack 1752.8 from
# hero_stats.json alone and the report reads 1952.8 -- I forgot hero GEAR.  Because this fight has
# exactly one hero against a heroless baseline, the delta IS his whole contribution:
#     attack / defense    1102.3 -> 1952.8   = exp_atk 650.52 + EXACTLY 200.0
#     lethality / health  1042.4 -> 1802.9   = weapon  160.50 + EXACTLY 600.0
#     cavalry and archer lines unchanged, as predicted
# sim.py had these FITTED to two reports as 0.833*exp_atk + 58.7 and weapon + 690, giving 600.58
# and 850.50.  The fitted attack was 30% low, the fitted lethality 12% high, and the two constants
# were the wrong way round in size.  Replaced with the measured +200 / +600, which reconstructs
# the panel exactly.  This is the last fitted constant in the project and it is now measured.
# CAVEAT: gear is per-hero equipment (Charles carries four +100 Lv.20 pieces and a +10), so
# applying one hero's gear to all of them is still an assumption -- the same one the fitted
# constants made, now anchored to a measurement rather than to a two-point fit.
# It does not touch allfights, which runs hero_stats=False against reported panels, but it does
# touch every ranking in run.py, elo.py, gear.py and waves.py, which run hero_stats=True.

# ------------------------------------------------- next test, pre-registered: YANG ONLY
# Same 10,000 at 5,000/2,000/3,000, same target, Infantry and Cavalry slots Vacant.  Yang is three
# procs and zero auras, the exact complement of Charles.
#     panel must read  archer attack 1823.5, defense 1809.4, lethality 1742.7, health 1737.6
#                      (1083.1 + 540.43 + 200, and 1009.2 + 133.5 + 600)
#     simulator says my losses 60 in 4 ROUNDS.
# FOUR ROUNDS IS THE PREDICTION TO WATCH, not the loss total.  Three procs at full magnitude end
# an 84:1 fight in a quarter of the time the same troops take with Charles' three auras (10) or
# with no heroes at all (138).  Avalanche is periodic 4, so the sim says it fires ABOUT ONCE.  If
# the report shows Avalanche firing five or ten times, the fight really lasted 20-40 rounds and
# the proc channel is over-applied by exactly that factor -- measured directly off the row, with
# no fitting and no reliance on the loss total at all.


# ------------------------------------------------- YANG ONLY (mail, 2026-09-09 17:44:33)
# Same 10,000 at 5,000/2,000/3,000, same heroless Narses, Infantry and Cavalry slots Vacant.
#     VICTORY: I lose 26 + 47 = 73 of 10,000.  SIMULATED 60.  k = 0.83.
#
# THE PANEL PREDICTION LANDED EXACTLY: archer 1823.5 / 1809.4 / 1742.7 / 1737.6, predicted to the
# decimal from hero_stats.json plus the +200 / +600 gear measured off the CHARLES fight.  That is
# a different hero and a different troop type, so the gear constants are now confirmed rather than
# merely fitted to the one report they came from.  Infantry and cavalry lines unchanged.
# AVALANCHE FIRED ONCE, as predicted for a 4-round fight.  The rows imply 4 to 10.7 rounds
# (Avalanche 1 -> 4, Ice Zone 3 -> 7.5, Ambush 3 -> 7.5, Unyielding Shield 4 -> 10.7) against the
# simulator's 4, so the proc channel is NOT over-firing with one hero.
#
# MY PREDICTION WAS WRONG ON WHICH BRANCH.  I said "Charles lands and Yang does not -> auras are
# right, procs are wrong" was the expected outcome.  BOTH LANDED:
#     no heroes            k 1.05
#     Charles, 3 auras     k 1.12
#     Yang, 3 procs        k 0.83
# A single hero of either kind is fine.  So the fault is not in auras, not in procs, and not in
# any one skill's magnitude or schedule -- it is in COMBINING SEVERAL, which is the second branch
# this test was pre-registered to distinguish and the one I called less likely.
#
# THAT IS A MUCH SHARPER TARGET than "the proc channel".  _prod multiplies distinct proc names
# together, so N procs live in the same round multiply N factors; with one hero that is at most
# three and the error is invisible, with two proc heroes it is six, and against Terry it is nine
# on each side.  The over-prediction growing from 1.0 to 5.4 as heroes are added is exactly the
# signature of a product where a sum belongs.

# ------------------------------------------------- next test, pre-registered: TWO PROC HEROES
# Charles + Yang would NOT test this -- Charles has zero procs, so Yang's three would still be the
# only ones live and the count would not change.  The test needs two PROC heroes.
#     SOPHIA + YANG, Infantry slot Vacant, same 10,000 at 5,000/2,000/3,000, same target.
#     Sophia brings Arcane Pact and Terror Deathblow; Yang brings three.  Six procs against three.
#     panel must read  cavalry 1820.7 / 1809.7 / 1724.3 / 1726.1
#                      archer  1823.5 / 1809.4 / 1742.7 / 1737.6   (unchanged from the Yang fight)
#     simulator says my losses 25 in 3.2 rounds, against 73 observed for Yang alone.
# IF THE COMBINATION IS THE FAULT, reality will come in well above 25 -- the model should be
# roughly halving the losses that adding Sophia actually saves.  If reality lands near 25, two
# proc heroes are still fine and the break is at three, which the full Charles+Sophia+Yang march
# would then pin down (simulator: 5 losses, and 5 is small enough that any real number at all
# would settle it).


# ------------------------------------------------- SOPHIA + YANG (mail 223407017263680)
# Two proc heroes, Infantry slot Vacant, same 10,000 against the same heroless Narses.
#     VICTORY: I lose 15 + 26 = 41 of 10,000.  SIMULATED 25.  k = 0.62.
# PRE-REGISTERED PREDICTION CONFIRMED: "if the combination is the fault, reality will come in
# well above 25".  It came in at 41, and the model is crediting Sophia with dividing losses by
# 2.4 (60 -> 25) when she really divides them by 1.78 (73 -> 41).
#
# THE PANEL LANDED EXACTLY FOR A THIRD HERO: cavalry 1820.7 / 1809.7 / 1724.3 / 1726.1, predicted
# from hero_stats.json plus the +200 / +600 gear.  Charles, Yang and Sophia now all reconstruct to
# the decimal, on three different troop types, so the stat half of the hero layer is settled and
# every remaining error is skills.
#
# SOPHIA'S WIDGET DOES NOT AFFECT THIS MEASUREMENT.  It is ('defender', 'lethality', 15) and the
# panel carries no widget term -- cavalry lethality is exactly base + weapon + gear -- so if it
# fires it is applied in battle rather than in the panel.  Either way +15 on a 1724.3 multiplier
# is a rounding error here: forcing it on moves the simulated losses from 25.4 to 25.4.  It stays
# an open question for garrison fights, where the multiplier is smaller and the gate is the one
# that matters; it is not one for this ladder.
#
# ------------------------------------------------- THE HERO LADDER (ladder.py)
# Four fights, same target, same troops, heroes added one at a time, every panel predicted before
# the report arrived:
#     0 heroes        observed  687   sim  726   k 1.06
#     Charles         observed   39   sim   44   k 1.12    three auras, zero procs
#     Yang            observed   73   sim   60   k 0.83    three procs, zero auras
#     Sophia+Yang     observed   41   sim   25   k 0.62    two proc heroes, six procs
# k FALLS MONOTONICALLY WITH HERO COUNT.  One hero of either kind is fine; the error appears only
# on combining them and compounds with how many are combined.  Extrapolating the per-hero
# over-credit lands close to where the three-hero Terry fights sit.
#
# THE REFERENCE COMBINATION RULE HELPS AND IS NOT ENOUGH.  Patching _prod so procs ACCUMULATE into
# one coefficient per kind (Skill.damage(): coef = coef + value/100) instead of each contributing
# its own factor moves every fight the right way and cuts the ladder rms from 0.264 to 0.204:
#     0 heroes 1.06 -> 1.08   Charles 1.12 -> 1.16   Yang 0.83 -> 0.89   Sophia+Yang 0.62 -> 0.70
# Right direction on all four, so accumulation is part of the answer, but Sophia+Yang is still
# 0.70 and the monotone decline survives.  Something else about combining heroes is still missing.
# NOT APPLIED YET: it is a real improvement on a clean four-point ladder, but adopting it while a
# second combination effect is still unidentified risks the same two-errors-cancelling trap that
# the verified magnitudes exposed.  The ladder makes that testable now -- any candidate rule has
# to flatten k across all four, not just lower an average.


# ------------------------------------------------- searching the combination rule on the ladder
# Every candidate scored against all four rungs.  The criterion is FLATTENING -- spread is
# max-min of log k across the ladder -- not lowering an average, because a rule that just scales
# everything down can improve rms while leaving the hero-count trend untouched.
#     rule                       0 heroes  Charles  Yang  Sophia+Yang    rms   spread
#     multiply (current)             1.05     1.12  0.83     0.64       0.248   0.55
#     accumulate (reference form)    1.09     1.14  0.89     0.70       0.202   0.46
#     strongest proc only            1.11     1.14  0.93     0.72       0.188   0.46
#     multiply + SkillMod cap 3      1.07     1.15  0.94     0.76       0.160   0.44
#     'all' scope = hero's own type  1.05     1.79  0.86     1.18       0.312   0.73
# NONE of them flattens it.  Every one keeps the monotone decline; they only shift the level.
#
# THE SCOPE RULE IS NOW REFUTED, and that matters because it was the BEST candidate back when the
# magnitudes were still wrong (0.396 against 0.891).  On clean isolated data it is the WORST of
# the five: Charles blows up to 1.79 because his auras stop protecting his own cavalry and
# archers.  It was never a mechanism, only a compensation for the wrong magnitudes -- exactly the
# thing refusing to adopt it was meant to avoid.
#
# WHAT DOES FLATTEN IT is a single scale on HERO procs only, leaving troop abilities alone so the
# heroless rung cannot move:
#     x1.00  1.05  1.12  0.83  0.64   rms 0.248  spread 0.55
#     x0.50  1.05  1.12  0.95  0.95   rms 0.069  spread 0.16
#     x0.40  1.05  1.12  0.98  1.03   rms 0.063  spread 0.13
#     x0.25  1.05  1.12  1.06  1.21   rms 0.116  spread 0.14
# So hero procs are over-applied by roughly 2 to 2.5x, and one constant absorbs the whole
# hero-count trend.  NOT ADOPTED.  It is a fitted constant with no mechanism behind it, which is
# the one thing this file has consistently refused, and a scale that absorbs a trend is exactly
# what a missing mechanism looks like from the outside.  Recorded as a MEASURED RESIDUAL: whatever
# the real rule is, it has to reduce hero proc contribution by about half at two heroes.

# ------------------------------------------------- next tests, pre-registered: the missing rungs
# The ladder has Charles (auras), Yang (procs) and Sophia+Yang (two proc heroes).  Two rungs are
# missing and they separate hypotheses the current four cannot:
#   SOPHIA ALONE -- 2 procs and 1 aura, against Yang's 3 procs and 0 auras.  If the over-credit
#       scales with PROC COUNT, Sophia alone lands nearer 1.0 than Yang did (0.83); if it scales
#       with a hero being present at all, she lands at 0.83 too.  panel: cavalry 1820.7 / 1809.7 /
#       1724.3 / 1726.1, infantry and archer unchanged.  Simulator: 39 losses.
#   CHARLES + YANG -- one aura hero plus one proc hero, no added procs over Yang alone.  If the
#       decline is really about PROCS, this should sit near Charles' and Yang's own values and NOT
#       drop to Sophia+Yang's 0.62.  If it drops anyway, the fault is about HEROES rather than
#       procs and the whole proc framing is wrong.  panel: infantry 1952.8 / 1941.2 / 1802.9 /
#       1801.1 and archer 1823.5 / 1809.4 / 1742.7 / 1737.6.  Simulator: 12 losses.
# Charles+Yang is the sharper of the two, because it is the one case where the model adds a hero
# WITHOUT adding a proc.  It cleanly separates "the model over-credits procs" from "the model
# over-credits heroes", and nothing measured so far can tell those apart.


# ------------------------------------------------- CHARLES + YANG (mail 223407017264209)
# Fought at 1,000 (500/200/300), so it is directly comparable to the heroless baseline rather than
# to the 10,000-troop rungs.  Same heroless Narses, Cavalry slot Vacant.
#     VICTORY: I lose 10 + 16 = 26 of 1,000 (974 residents); Narses wiped.
#     THE PANEL LANDED EXACTLY FOR A FOURTH CONSECUTIVE HERO -- inf 1952.8 / 1941.2 / 1802.9 /
#     1801.1, arch 1823.5 / 1809.4 / 1742.7 / 1737.6, cavalry unchanged.  The stat half is settled.
#     Rows: Charles 1/1/1 + Unyielding Shield 23; cavalry Ambusher 5, Assault Lance 6 (426 kills);
#           Yang Ice Zone 18 (3,776), Avalanche 15 (6,257), Ambush 12, row4 4, row5 7 (1,272).
#
# THIS RUNG WAS PRE-REGISTERED TO KILL ONE OF TWO FRAMINGS, AND IT KILLED THE PROC FRAMING.
# Charles has zero procs, so adding him to Yang adds a HERO without adding a PROC.  If the decline
# were about procs it should have sat near Charles' and Yang's own values; it came in at 0.60,
# BELOW two-proc-hero Sophia+Yang.  So "the proc channel is over-applied" is dead as stated.

# ------------------------------------------------- THE COMBINATION RULE, SETTLED FROM THE SOURCE
# Read Skill.java and Fight.java rather than fitting.  The reference engine keeps exactly TWO
# numbers per attack (Fight.java:127-128, coefAttack and coefDefense) and builds each by walking
# every skill into ONE running accumulator:
#     Skill.damage()   coef = 1;  cases 201/221/301/211:  coef = coef + skill.getValue() / 100.0
#     Skill.defense()  coef = 0;  cases 202/302:          coef = coef + skill.getValue() / 100.0
# There is no product over distinct skills or stat categories anywhere in it.  Only effect 101
# ("extra damage") multiplies, and it carries a `coef = coef - 1` guard so it cannot re-multiply
# within a round.  sim._prod multiplied a separate factor per stat category AND PER PROC NAME.
# ADOPTED.  Every fight in allfights moves the right way, and by far the most where the theory
# says it should -- the fights with three proc heroes on BOTH sides, where a product over proc
# names compounds nine factors against nine:
#     opponent-2 10k mixed  5.44 -> 2.29     Terry 10k all archer  4.21 -> 1.67
#     Terry 20k mixed       3.62 -> 1.90     Narses 500 solo       1.51 -> 1.03
#     rms log err 0.843 -> 0.499     mean|log| 0.613 -> 0.400     spread 0.66-5.44 -> 0.71-2.54
# THE FIT IS NOT THE EVIDENCE.  It is adopted because it is what the reference implementation
# does; the improvement is a consequence, and given the degeneracy recorded below, loss totals are
# no longer strong enough evidence to adopt anything on their own.
#
# REJECTED ALTERNATIVES, all of which fit the ladder BETTER and none of which has a source:
#     strongest-per-kind (procs of a kind take a max, not a product)   rms 0.174  spread 0.46
#     diminishing returns, total c -> c/(1 + c/2)                      rms 0.225  spread 0.31
# Both beat accumulation on the ladder.  Both are fitted shapes chosen for flattening a curve,
# which is the exact move this project has refused throughout, and both contradict the source.
# Not adopted.  Recorded so they are not rediscovered and mistaken for progress.

# ------------------------------------------------- THE LADDER WAS MEASURING THE WRONG THING
# After the accumulation fix k still falls monotonically: 1.08 / 0.96 / 0.89 / 0.70 / 0.60.  But
# the round count -- which depends only on how fast the fight ENDS, not on how much I absorb --
# explains it almost exactly.  On both rungs Avalanche (periodic 4) can date:
#     Yang           sim 4.7 rounds vs 6 observed    ratio 0.82   sqrt 0.91   k 0.89
#     Charles+Yang   sim 21  rounds vs 52 observed   ratio 0.39   sqrt 0.63   k 0.60
# k = sqrt(round ratio) on both.  The simulator wipes Narses far too fast and my troops are
# exposed for a fraction of the rounds they really faced.  Charles+Yang's length is corroborated
# independently: Unyielding Shield fired 23 times at chance .375 -> 61 rounds, against Avalanche's
# 60.  So "the model over-credits each additional hero" was a description of a symptom.
#
# AND IT IS TWO ERRORS, NOT ONE -- THIS IS THE IMPORTANT PART.
# Scale ONLY my side's skill output by F and re-run Charles+Yang:
#     F      1.00   0.60   0.40   0.30   0.25   0.20
#     rounds 14.9   19.4   24.1   27.9   30.4   34.0      (observed ~52-60)
#     losses 13.9   18.5   22.4   26.3   28.8   31.8      (observed 26)
# The losses land at F = 0.30, where the fight still runs 28 rounds against 52 observed.  The two
# observables want different corrections.  So my output is over-modelled AND the opponent's
# per-round rate is over-modelled, and they partly cancel in every loss total in this file.
#
# CONSEQUENCE -- A RETRACTION.  "THE DAMAGE CORE IS CORRECT" IS NOT SUPPORTED.
# The heroless fight's k of 1.05 was read as validating the entire engine below the hero layer.
# It cannot bear that weight: it is a single number of the form rate x rounds, and this ladder now
# shows rate and rounds erring in opposite directions.  The heroless fight's own row supports the
# same doubt -- Unyielding Shield fired 104 times at chance .375, which needs ~277 rounds of
# infantry-alive time if it rolls once per round, against the simulator's 139.  What survives from
# that report is narrower and still valuable: the TG2 ability caps, that troop abilities need no
# hero, and that the panel reconstruction is right.  What does not survive is "every remaining
# error in this file is in the hero skill layer."

# ------------------------------------------------- THE BLOCKER: per-round or per-attack?
# Converting a trigger count into a round count requires knowing how many times a chance proc is
# rolled per round, and the reports disagree.  Dating each fight by Avalanche and dividing out the
# nominal chance gives rolls-per-round (a LOWER bound, since a troop ability stops when its type
# dies):
#     Narses 500 solo   R=156   Ice Zone 0.95   Ambush 0.64   Unyielding Shield 2.14
#     Charles+Yang      R= 60   Ice Zone 0.75   Ambush 0.50   Unyielding Shield 1.02
# Yang's hero procs sit under 1 in both, consistent with one roll per round throttled by troop
# lifetime.  Unyielding Shield does not: 2.14 in one fight and 1.02 in the other, and 2.14 cannot
# be explained by lifetime because lifetime only pushes the estimate UP.  Until this is settled,
# Avalanche is the only trustworthy clock, and it needs archers to fire at all.
#
# ------------------------------------------------- HOW NOISY IS A SINGLE BATTLE?  (the power audit)
# Asked by the player, and it lands: does the 84:1 imbalance make these tests too noisy to read?
# Each ladder rung is ONE battle, so the right test is how surprising the observed number is as a
# single draw from the simulator's own distribution -- not how far the MEANS are apart.  4,000 runs
# per rung:
#     rung            obs   sim mean   sim sd   5-95% band     z    P(draw >= obs)
#     0 heroes        687      737      114      603 - 1000   -0.4      0.60
#     Charles          39       38       15        15 -   65   +0.1      0.46
#     Yang             73       66       14        44 -   90   +0.5      0.30
#     Sophia+Yang      41       28       16         0 -   55   +0.8      0.21
#     Charles+Yang     26       16      3.9        10 -   22   +2.6      0.009
#
# FOUR OF THE FIVE RUNGS ARE CONSISTENT WITH PURE NOISE.  "k falls monotonically with hero count"
# rests on ONE significant rung.  A single draw of 41 from a mean of 28 with sd 16 is unremarkable,
# and the apparent trend is four insignificant points arranged in a suggestive order.  The tell was
# there to be seen before the statistics: the WORST k belongs to the SMALLEST loss count.  At 84:1
# I lose 26 troops of 1,000, and a count that small cannot carry a 30% inference.
# THIS RETRACTS THE MONOTONE DECLINE as an established fact.  It does not retract the accumulation
# fix, which rests on the source and on fights with five-figure loss counts (Terry, opponent-2),
# where relative noise is a fraction of a percent.
#
# THE ROUND COUNT SURVIVES THE SAME AUDIT, AND COMFORTABLY.
#     rung            obs rnd   sim mean   sim sd   rel sd     z
#     Yang                  6        4.7      0.8     16%     1.3
#     Charles+Yang         52       20.7      1.4      7%    22.8
# Round counts carry about 7% relative noise against 15-56% for loss totals, because a fight's
# length is set by accumulated attrition rather than by the last few stochastic rounds.  The
# Charles+Yang length discrepancy is 23 sigma.  So: the loss-total ladder was underpowered and was
# over-read; the round-count finding built on top of it stands.
#
# WHAT THE IMBALANCE ACTUALLY COSTS, AND HOW TO BUY POWER BACK.  Scanning march size, Yang alone,
# pure archers, same Narses (1,500 runs each):
#     archers    win%   losses  rel sd   rounds  rel sd   Avalanche
#        250       0%      250  wiped      51.6     3%        12.9
#        500     100%      203     9%      34.4     8%         8.6
#      1,000     100%      143    12%      16.9    11%         4.2
#      2,000     100%      113    15%       9.3    15%         2.3
#      8,000     100%      106    22%       4.5    21%         1.1
# POWER IMPROVES AS THE MARCH SHRINKS, because a closer fight lasts longer and both observables
# average over more rounds.  The 10,000-troop rungs were the worst available design: they end in
# four rounds, so Avalanche fires ONCE (no clock) and the loss total is a two-digit number at 22%
# noise.  Below 500 my losses censor at a total wipe and stop measuring anything.  500 is the
# optimum: still a win, so my losses measure HIS output uncensored, losses in the hundreds at 9%,
# and Avalanche firing about nine times.
# RULE FOR EVERY FUTURE CALIBRATION MARCH: size it so the fight runs 30+ rounds and I still win.
# Against this Narses that is 400-600 troops, not 10,000.

# --------------------------------- SECOND HEROLESS FIGHT (mail 223407017271858, 2026-09-10)
# Requested at the power-optimal size after the audit above, and it is the first calibration march
# in this file that was DESIGNED rather than just fought.  500 at 250/100/150, both sides Vacant
# in all three slots, same 83,600 Narses.
#     DEFEAT: I am wiped, 176 + 324 = 500.  He loses 5,621 + 10,438 = 16,059 of 83,600
#     (residents 67,541; 83,600 - 16,059 = 67,541, checks).
# SCORED ON HIS LOSSES, NOT MINE.  I lost, so my 500 is censored at the squad size and measures
# nothing at all.  His 16,059 is the uncensored quantity and it measures MY output -- the exact
# thing the round-count work says is over-modelled.  A defeat is not a wasted report; it just
# swaps which side's number carries the information.
#     SIMULATED 16,738 +/- 1,165 AGAINST 16,059 OBSERVED.  k = 1.04, z = -0.6, and the observed
#     value sits mid-band (90% band 14,872-18,721).  The simulator also calls the defeat, at a 0%
#     win rate over 4,000 runs.
# AND THE DESIGN WORKED: relative noise 7%, against 22% for the 10,000-troop marches.  This is the
# first heroless result strong enough to carry weight on its own.
# My panel moved slightly (small research upgrades): lethality and health up 2-4 points on every
# type.  NARSES' PANEL IS BYTE-FOR-BYTE IDENTICAL to the first heroless report, which re-confirms
# he is unbuffed and unchanged, and makes the two reports a matched pair.

# --------------------------------- THE CLOCK IS RIGHT WITHOUT HEROES
# The reason to want this fight was the round count, and it delivers one with no lifetime confound
# at all.  HE KEEPS 67,541 OF 83,600 TROOPS, so his squads never die and his rows run the whole
# battle.  Reading every row at one roll per round:
#     row                          triggers      p    implied rounds
#     HIS Ambusher (cav)                 17   0.20        85    <- no lifetime confound
#     HIS archer row 1                    9   0.10        90    <- no lifetime confound
#     mine Ambusher (cav)                18   0.20        90
#     mine Volley (arch)                  9   0.10        90
#     mine Assault Lance (cav)           11   0.15        73
#     mine Howling Wind (arch)           17   0.30        57
#     mine Unyielding Shield (inf)       66   0.375      176    <- IMPOSSIBLE at one roll/round
# SIMULATED 90.6 +/- 3.4 ROUNDS.  His two unconfounded rows say 85 and 90.  Four rows agree at
# 85-90 and the simulator lands on 90.6.
# THIS IS THE ANSWER THE PURE-ARCHER TEST WAS PRE-REGISTERED TO GET, arriving for free: THE CORE
# LOOP'S CLOCK IS CORRECT.  So the 23-sigma round-count error on Charles+Yang is NOT in the core
# loop -- it is in the HERO LAYER, which is where the loss-total ladder pointed before the power
# audit showed the ladder could not support the claim.  Two independent routes, one conclusion.
# It also partly rehabilitates "the damage core is correct": that claim now rests on a
# well-powered loss total (7% noise, z = -0.6) AND an independent clock check, rather than on a
# single degenerate rate-times-rounds number.  Still narrower than the original claim -- targeting
# and per-type attrition are only checked in aggregate here.
#
# AND IT SETTLES HALF THE PER-ROUND / PER-ATTACK QUESTION, BY INEQUALITY.  Unyielding Shield fired
# 66 times at chance .375, which needs 176 rounds at one roll per round -- in a fight that lasted
# about 90.  A trigger count cannot exceed its battle length, and troop lifetime only pushes the
# implied count DOWN, so this cannot be explained away: proc_taken IS rolled more than once per
# round, about twice here.  The offensive procs in the same report do not need more than one roll
# (Assault Lance 73 and Howling Wind 57 both fit inside 90 with normal lifetime attrition), so
# defensive and offensive procs are NOT rolled the same number of times.  That asymmetry is new,
# and it is measured rather than assumed.

# --------------------------------- YANG ONLY at 500 (mail 223407017275279) -- THE TEST FAILED
# The pre-registered test, fought exactly as specified: 500 at 250/100/150, Infantry and Cavalry
# slots Vacant, same heroless Narses.  A DESIGNED experiment with numbers written down first.
#     VICTORY: I lose 82 + 150 = 232 of 500 (268 residents).  NARSES IS WIPED, 29,262 + 54,338 =
#     83,600, zero residents -- so HIS losses censor at the squad size and MINE are the observable.
#
#     PRE-REGISTERED  141 +/- 11, 90% band 123-160.   OBSERVED 232.   k = 0.61, z = +8.0.
# THE PREDICTION FAILED, AND FAILING IS THE POINT: it failed in the direction and by roughly the
# factor the round-count work said it would, on a fight sized so that noise could not do it.
#
# THE PANEL LANDED EXACTLY FOR A FIFTH CONSECUTIVE HERO: archer 1823.5 / 1809.4 / 1745.5 / 1740.1,
# infantry and cavalry unchanged from the heroless report.  The stat half of the hero layer has
# now been predicted to the decimal on five heroes and three troop types.  It is not the problem.
#
# THE CLOCK IS BROKEN BY 2x WITH A SINGLE HERO -- three independent readings:
#     Avalanche      periodic 4, deterministic     23 triggers  ->  92 rounds
#     HIS Ambusher   chance .20                    19 triggers  ->  95 rounds
#     HIS archer row chance .10                    10 triggers  -> 100 rounds
#     SIMULATED 45.6 ROUNDS.
# The pre-registered refutation threshold was "his Ambusher at 20 or more".  It came in at 19 --
# one short of the number I named, with Avalanche and his archer row independently putting the
# fight at 92 and 100.  The threshold is met on the evidence; the single number I picked was
# marginally too aggressive, which is worth recording as a lesson about naming one statistic when
# three are available.  Recorded either way: the clock is 2.0x too fast with ONE hero.
#
# THE MATCHED PAIR IS THE RESULT.  Same 500 troops, same composition, same target, heroless
# against Yang-only, an hour apart:
#                            heroless    +Yang     ratio
#         REAL kills/round        178      909      5.1x
#         SIM  kills/round        185     1834      9.9x
#     THE MODEL CREDITS YANG WITH 1.94x THE OUTPUT BOOST HE REALLY GIVES.
# With no heroes, output and clock are both right (k 1.04, rounds 90.6 against 85-100 observed).
# Add one hero carrying three procs and nothing else, and the output error is a clean factor of
# two.  This is the proc channel, isolated, quantified, and measured on a well-powered pair rather
# than inferred from a noisy ladder.  Note what it does NOT say: the earlier framing "the model
# over-credits each additional HERO" is still dead.  One hero is enough.
#
# THE PER-ROUND LOSS RATE IS A SECOND, SMALLER ERROR, still in the same direction as before.
#     sim   141 losses in 45.6 rounds = 3.09/round      real  232 in 92 = 2.52/round   -> 1.23x
# So output is over-modelled 2.0x and my own casualty rate 1.2x.  They partly cancel in the loss
# total, which is why k came out 0.61 rather than 0.50.  Two errors, as the ladder work concluded.
#
# --------------------------------- THE SHARPEST OPEN LEAD: YANG'S PROC RATES DISAGREE
# With the fight dated at 92 rounds, every one of Yang's rows becomes a measured firing rate:
#     Ice Zone   51 triggers -> 0.554/round   tooltip .40   RATIO 1.39x
#     Avalanche  23 triggers -> 0.250/round   periodic 4    exact by construction
#     Ambush     23 triggers -> 0.250/round   tooltip .40   RATIO 0.62x
# TWO SKILLS WITH THE SAME NOMINAL .40 CHANCE FIRE AT 0.554 AND 0.250 IN THE SAME FIGHT.  That is
# not sampling noise: at 92 rounds the binomial sd on a .40 chance is about 4.7 triggers, and
# these differ by 28.
# ICE ZONE CANNOT BE EXPLAINED BY LIFETIME.  51 triggers at .40 needs 127 rounds, more than the
# fight lasted, and troop lifetime only pushes an implied count DOWN.  So Ice Zone is rolled more
# than once per round, exactly as Unyielding Shield was shown to be in the heroless report.
# AND ITS RATE IS NOT CONSTANT ACROSS FIGHTS.  In the 500-troop three-hero fight, at the SAME
# march composition (250/100/150), Ice Zone fired 59 times in ~156 rounds = 0.378/round, which
# matches the tooltip.  Here the same skill in the same composition fires at 0.554.  Something
# conditions the roll count that is not in the model, and it is not march composition.
# THAT IS THE NEXT THING TO IDENTIFY, and it is a per-skill question now rather than a
# combination-rule question, which is a much smaller search.

# --------------------------------- CHARLES ONLY at 500 (mail 223407017277424)
# The other half of the bisection, same size, same target, Cavalry and Archer slots Vacant.
#     VICTORY: I lose 79 + 144 = 223 of 500 (277 residents).  Narses wiped: 6,434 + 22,828 +
#     54,338 = 83,600 exactly.  His "Losses" row is non-zero here only because the player's
#     infirmary was full, so some wounded became deaths -- the three rows still sum to the squad
#     and the total casualty figure is unaffected.  His side censors at 83,600; mine is the
#     observable.
# THE PANEL LANDED EXACTLY FOR A SIXTH CONSECUTIVE HERO: infantry 1952.8 / 1941.2 / 1805.7 /
# 1802.9, cavalry and archer unchanged.
#
# THE CLOCK PREDICTION LANDED, AND THAT IS THE RESULT.
#     pre-registered  his Ambusher 40.3, his archer row 20.2, 201.5 +/- 6.7 rounds
#     OBSERVED        his Ambusher 41,   his archer row 22    -> 205 and 220 rounds
#     my own rows corroborate: Ambusher 39 -> 195, Assault Lance 28 -> 187, Howling Wind 53 -> 177
# Simulated 201.5 against 205 observed, a ratio of 0.98.  CHARLES DOES NOT BREAK THE CLOCK.
# Set against Yang at the same size, where the clock ran 2.0x fast, the bisection is complete:
#     heroless   clock right (90.6 vs 85-100)      output right (k 1.04)
#     Charles    clock RIGHT (201.5 vs 205)
#     Yang       clock 2.0x TOO FAST (45.6 vs 92)
# All three of Charles' skills are defensive -- e_leth 20, taken 20, hp 25 -- so he contributes
# NOTHING to my output, and the fight length being exact is precisely what that predicts.
#
# HIS LOSS TOTAL IS STILL WRONG, AND BECAUSE THE CLOCK IS RIGHT IT IS CLEANLY INTERPRETABLE.
#     sim 164 +/- 20 against 223 observed.  k = 0.74, z = +3.0.
#     losses per round: sim 0.814, real 1.088 -> the model is 0.75x, i.e. it credits Charles with
#     1.34x the survivability he really provides.
# This is the first time a loss total can be read as a RATE rather than a product, because the
# denominator is independently confirmed.  Every earlier k in this file was rate x rounds.
#
# --------------------------------- TWO ERRORS, NOT ONE -- AND THEY ARE VERY DIFFERENT SIZES
# Scale every hero skill effect (troop abilities untouched) by s and ask what s fixes each fight.
# DIAGNOSTIC ONLY, not a proposed fix: the question is whether ONE mechanism covers both.
#     s        Charles losses (obs 223)     Yang rounds (obs 92)
#     1.00        163      0.73                45.5      0.49
#     0.80        225      1.01                53.1      0.58
#     0.30        471      2.11                94.0      1.02
# CHARLES NEEDS 0.80 AND YANG NEEDS 0.30.  No single factor fixes both -- at Charles' value Yang
# is still off by 1.7x, and at Yang's value Charles is off by 2.1x.  So this is NOT a uniform
# over-credit of the hero layer.  The aura channel is about 25% too strong; the proc channel is
# about 3.3x too strong.  That difference is the finding.
#
# THE ERROR IS NOT IN THE SCHEDULE, THE MAGNITUDE, OR THE SCOPE.  All three were checked:
#   - firing rates are not uniformly high -- Ice Zone fires 1.39x nominal and Ambush 0.62x, so a
#     blanket "procs fire too often" is refuted by the rows themselves;
#   - magnitudes and scopes are tooltip-verified six for six (Ice Zone .40/100/arch, Avalanche
#     1-in-4/100/all, Ambush .40/50/all, and Sophia's three);
#   - sim.py converts the stored expected value back to full magnitude correctly
#     (`mag = v / proc_uptime(sname)`), so the chance is not being applied twice.
# So the over-credit is in how a LIVE proc enters the damage calculation, not in whether or how
# often it goes live.  That is a much smaller place to look than where this started.
#
# ONE CONFOUND, STATED PLAINLY.  Charles is auras AND defensive; Yang is procs AND offensive.
# These two fights cannot separate "procs are over-credited" from "offensive skills are
# over-credited".  Every claim above is safe under either reading; the distinction is what the
# next test is for.

# --------------------------------- SOPHIA ONLY at 500 (mail 223407017280638)
#     VICTORY: I lose 102 + 186 = 288 of 500 (212 residents).  Narses wiped at exactly 83,600,
#     so his side censors and mine is the observable.
#     PRE-REGISTERED 128 +/- 21 (band 94-163).  OBSERVED 288.  k = 0.44, z = +7.6.  The worst
#     miss in the file, and the third pre-registered failure in a row in the same direction.
# THE PANEL LANDED EXACTLY FOR A SEVENTH CONSECUTIVE HERO: cavalry 1820.7 / 1809.7 / 1727.4 /
# 1729.6, infantry and archer unchanged.
#
# THE CLOCK PREDICTION WAS CONFIRMED: "his Ambusher well above 12" -> observed 16.
# TERROR DEATHBLOW IS A SECOND DETERMINISTIC CLOCK.  It is periodic 1-in-2 and fired 46 times,
# dating the fight at 92 rounds with no chance involved at all -- the first clock in this file
# that is independent of Yang's Avalanche.  Corroborated by Arcane Pact (39 -> 98), my Ambusher
# (20 -> 100), Assault Lance (15 -> 100), Volley (9 -> 90), Howling Wind (33 -> 110).
#     SIMULATED 60.4 ROUNDS AGAINST 92.  The clock is 1.52x too fast (Yang was 2.0x).
#
# HER FIRING RATES ALL MATCH THE MODEL, WHICH YANG'S DID NOT:
#     Arcane Pact         39/92 = 0.424/round   modelled 0.400   ratio 1.06
#     Terror Deathblow    46/92 = 0.500/round   modelled 0.500   ratio 1.00
#     Terror Annihilation 1 trigger -- an AURA row, exactly as heroes.PERMANENT treats it
# So the schedule anomaly found on Yang (Ice Zone 1.39x nominal, Ambush 0.62x) is specific to
# Yang, not a property of procs.  Yang is the odd hero, not the representative one.

# --------------------------------- RETRACTION: THE PROC/AURA FRAMING IS DEAD
# The previous entry concluded "the aura channel is ~25% too strong, the proc channel ~3.3x".
# SOPHIA REFUTES IT.  Reading each hero's loss total as a RATE against its own MEASURED round
# count -- which is only possible now that two deterministic clocks exist:
#     Charles   defensive effects are AURAS      model credits 1.34x the survivability given
#     Sophia    defensive effect is a PROC       model credits 1.48x the survivability given
# Those are the same number within noise.  THE PROC/AURA DISTINCTION DOES NOT EXPLAIN THE
# DEFENSIVE CHANNEL.
# WHERE THE 3.3x CAME FROM, AND WHY IT WAS WRONG: it compared the scale needed to fix CHARLES'
# LOSSES (0.80) against the scale needed to fix YANG'S CLOCK (0.30).  Those are two different
# observables, and the comparison was not valid.  My error, and exactly the kind the round-count
# work was supposed to prevent -- a number quoted across observables that do not correspond.
#
# --------------------------------- WHAT THE CORRECTED SCAN SHOWS
# Same treatment for every hero, both observables, sim/observed (1.00 = model matches reality):
#     s      Charles loss  Charles rnd   Yang loss  Yang rnd   Sophia loss  Sophia rnd
#     1.00       0.74         0.98         0.61       0.49        0.44         0.66
#     0.80       1.01         1.09         0.72       0.58        0.59         0.76
#     0.50       1.49         1.40         1.00       0.77        0.96         1.02
# A SINGLE PER-HERO SCALE FIXES BOTH OBSERVABLES AT ONCE for Charles (s ~ 0.82: 1.01 and 1.09)
# and for Sophia (s = 0.50: 0.96 and 1.02).  For those two heroes the model's error is a pure
# over-scaling of their skill effects, nothing structural.  YANG IS THE EXCEPTION: his losses
# want 0.50 and his clock wants about 0.30, and he is also the hero whose measured firing rates
# disagree with his tooltips.  Both anomalies point at the same hero.
#
# THE OPEN QUESTION IS NOW NARROW: what sets the per-hero scale?  It is not skill magnitude in
# any simple way -- Charles' hero-only DEFENSIVE multiplier is 2.37 and needs only s 0.82, while
# Sophia's is 2.06 and needs 0.50, so the hero with the LARGER modelled effect needs the SMALLER
# correction.  A saturation-by-magnitude law is refuted by that pair.
# WHAT DOES TRACK, ACROSS ALL THREE, IS THE HERO'S SHARE OF THE MARCH:
#     Charles  infantry 250/500 = 50%   s 0.82
#     Yang     archers  150/500 = 30%   s 0.50 (losses)
#     Sophia   cavalry  100/500 = 20%   s 0.50
# Three points and a monotone trend is weak evidence, and the share is confounded with which
# skills each hero has.  It is a hypothesis, not a finding.  The next test is built to break it.

# --------------------------------- SOPHIA AT 100/250/150 (mail 223407017281728)
# The pre-registered troop-share test: same hero, same 500 total, same target, same Vacant slots,
# only the composition changed so her cavalry went from 20% of the march to 50%.
#     VICTORY: I lose 83 + 151 = 234 of 500 (266 residents).  Narses wiped at exactly 83,600.
#     PRE-REGISTERED 91 +/- 18 (band 61-122).  OBSERVED 234.  z = +7.9.
#     Terror Deathblow (periodic 1-in-2) fired 36 -> 72 ROUNDS, corroborated by Arcane Pact
#     (30 -> 75) and his Volley (7 -> 70).  SIMULATED 43.6 -> the clock is 1.65x too fast.
#     Warding Impaler appears as a sixth cavalry row (6 triggers) now that cavalry is 250; it was
#     omitted at 100 cavalry because it fired zero times.  Consistent with the row-omission rule.
#
# THE TROOP-SHARE HYPOTHESIS IS REFUTED.
#     composition          loss ratio   round ratio   s that fixes BOTH
#     cavalry 20%             0.44         0.66            ~0.50
#     cavalry 50%             0.39         0.61            ~0.45
# The hypothesis predicted s would climb from 0.50 toward Charles' 0.82 as her share rose to
# match his.  It went DOWN slightly instead.  Troop share does not set the per-hero scale, and
# the monotone 50/30/20% ordering across three heroes was the coincidence it was flagged as.
#
# WHAT THE TEST GAVE INSTEAD IS WORTH MORE THAN WHAT IT WAS ASKED.  At BOTH compositions a SINGLE
# scale fixes BOTH observables at once, and it is the same scale (0.50 and 0.45, one sampling
# interval apart).  So for Sophia the model's error is a clean multiplicative over-credit of her
# skill effects, STABLE ACROSS MARCH COMPOSITION -- a per-hero constant, not an interaction with
# the army she is leading.  That is a much stronger statement than any single fight could make,
# and it is what makes isolating individual SKILLS worth doing: a per-hero constant is an
# aggregate over three skills, so it can be decomposed.
#
# STATE OF THE PER-HERO SCALES:
#     Charles   3 defensive auras, 0 offensive              s ~ 0.82
#     Sophia    1 defensive proc + 2 offensive procs        s ~ 0.48  (two compositions)
#     Yang      3 offensive procs                           s ~ 0.50 losses / 0.30 clock (split)
# Ordered by offensive content, which is the surviving hypothesis now that both proc/aura and
# troop share are dead.  It is NOT explained by offensive magnitude: Sophia's offensive EV totals
# 137.5 against Yang's 85, yet she needs the LARGER scale.  Recorded as unexplained.

# --------------------------------- SOPHIA WITH ZERO CAVALRY (mail 223407017281976)
# 1,000 at 500 infantry / 0 cavalry / 500 archers.  The single-skill isolation test.
#     VICTORY: I lose 235 + 435 = 670 of 1,000 (330 residents).  Narses wiped, so his side
#     censors and mine is the observable.
# THE PRE-REGISTERED FORK RESOLVED ON THE "UNCHANGED" BRANCH, ON EVERY ROW:
#     observable          scale UNCHANGED   model becomes RIGHT   OBSERVED
#     his Ambusher                     25                    17         24
#     his archer row                   12                     8         13
#     my Arcane Pact                   50                    34         59
#     my losses                537 +/- 40            270 +/- 36        670
# REMOVING THE LARGEST SINGLE SKILL MAGNITUDE IN THE ROSTER DID NOT REMOVE THE ERROR.  Terror
# Deathblow carries EV 100, more than Sophia's other two skills combined, and taking it out of
# play left the over-credit essentially where it was.  So the error is spread evenly across her
# skills rather than concentrated in one of them, and "one badly modelled skill" is dead.
#
# A PREDICTION I GOT WRONG IN DETAIL, RECORDED AS SUCH.  I wrote that Terror Deathblow "must read
# ZERO and be omitted", and that a non-zero count would mean the scope gate itself is broken.  It
# read 1.  The gate is fine -- 1 is the COLLAPSED value a scope-gated skill shows when its troop
# type is absent, exactly as this file already recorded for Avalanche (1 trigger at 1,500 infantry
# with no archers).  I had that precedent written down and still predicted 0.  The substance of
# the test is unaffected; the display convention is now pinned on a second skill.
#
# THE FIRST PREDICTIVE SUCCESS OF THE CALIBRATED MODEL.  Choosing the march required predicting
# the fight with the measured s ~ 0.48 applied, and that calibrated run said 124 rounds.  Observed
# 120-150 across six rows.  It also correctly ruled out 700 troops as a wipe, which would have
# censored the observable.  Sizing a test with the calibrated model, not the raw one, is now
# standard practice in this file.
#
# THE PER-HERO SCALE IS INVARIANT TO A GREAT DEAL.  For Sophia it is now measured at three
# compositions -- 250/100/150, 100/250/150 and 500/0/500 -- spanning a 2x change in march size,
# her own troop type at 20%, 50% and 0% of the army, and one of her three skills switched off.
# Raw loss ratios: 0.44, 0.39, 0.40.  That is a constant.

# --------------------------------- THE OFFENSIVE/DEFENSIVE ASYMMETRY, QUANTIFIED
# With five hero fights and both observables on each, fit TWO scales instead of one: one for the
# channels that raise my damage (DMG_UP + OPP_DEF_DOWN) and one for those that lower what I take
# (TAKEN + DEF_UP + OPP_DMG_DOWN).  DIAGNOSTIC, NOT ADOPTED -- see the note below.
#     BEST FIT: offensive x0.40, defensive x0.65    rms log err 0.170 over ten observables
#     fight                  current loss / round      two-scale loss / round
#     Charles 250/100/150         0.74   0.98               1.28   1.29
#     Yang    250/100/150         0.61   0.50               1.08   0.87
#     Sophia  250/100/150         0.44   0.66               0.96   1.14
#     Sophia  100/250/150         0.39   0.61               0.89   1.07
#     Sophia  500/0/500           0.40   0.63               0.74   0.96
# Spread goes from 0.39-0.98 to 0.74-1.29 and rms from about 0.6 to 0.170.  OFFENSIVE SKILLS NEED
# ROUGHLY TWICE THE CORRECTION DEFENSIVE ONES DO.  That is the surviving structure after
# proc-vs-aura, troop share, single-skill isolation and saturation-by-magnitude were all refuted.
# NOT ADOPTED.  Two constants fitted to the fights they are scored on is exactly the move this
# project has refused throughout, and Charles is over-corrected (1.28) which says the two-scale
# form is not the true shape either.  It is recorded as a MEASUREMENT of the asymmetry -- a fact
# any real mechanism has to reproduce -- not as a fix.

# --------------------------------- next test, pre-registered: CHARLES + SOPHIA at 500
# THE FIRST OUT-OF-SAMPLE TEST IN THIS SERIES.  The two scales were fitted on SINGLE-hero fights
# only, so a TWO-hero march is genuinely out of sample, and it also tests whether the per-hero
# corrections COMPOSE -- the question the original ladder failed to answer because it was
# underpowered.  Charles is purely defensive and Sophia mostly offensive, so the pair exercises
# both scales at once.
#     CHARLES + SOPHIA, 500 at 250/100/150, Archer slot Vacant, same heroless Narses.
#     panel must read  infantry 1952.8 / 1941.2 / 1805.7 / 1802.9
#                      cavalry  1820.7 / 1809.7 / 1727.4 / 1729.6
#                      archer   1083.1 / 1069.0 / 1012.0 / 1006.6  (unchanged)
# THE TWO HYPOTHESES, both generated at 4,000 runs, seed 11:
#     RAW MODEL        I win, losing 27 +/- 7 of 500 (band 15-40), 53 rounds
#                      -> Terror Deathblow 27, Arcane Pact 21, his Ambusher 11
#     TWO-SCALE        I win, losing 68 +/- 13 of 500 (band 48-90), 87 rounds
#                      -> Terror Deathblow 43, Arcane Pact 35, his Ambusher 17
# READ TERROR DEATHBLOW FIRST.  It is periodic 1-in-2, so 27 against 43 is a DETERMINISTIC
# discrimination with no sampling noise at all -- the cleanest single number this project has had
# to decide anything.  The loss bands do not overlap either.
# A THIRD OUTCOME MATTERS TOO: if the observed values land BEYOND the two-scale branch (Terror
# Deathblow well above 43, losses above 90), the per-hero errors COMPOUND when heroes are combined
# and the whole per-hero-constant picture needs the combination term the ladder originally chased.


# --------------------------------- CHARLES + SOPHIA at 500 (mail 223407017282381)
# The out-of-sample test.  500 at 250/100/150, Archer slot Vacant, same heroless Narses.
#     VICTORY: I lose 29 + 51 = 80 of 500 (420 residents).  Narses wiped, so mine is the
#     observable.  Terror Deathblow fired 38 -> 76 ROUNDS (periodic 1-in-2, deterministic).
#     observable        PRE-REG raw   PRE-REG two-scale   OBSERVED
#     losses            27 (15-40)        68 (48-90)          80
#     rounds                    53                87          76
#     Terror Deathblow          27                43          38
#     Arcane Pact               21                35          28
#     his Ambusher              11                17          16
# THE TWO-SCALE CORRECTION, FITTED ON SINGLE-HERO FIGHTS ONLY, PREDICTED A TWO-HERO MARCH
# SUBSTANTIALLY CORRECTLY on all four observables; the raw model is wrong on every one.
# AND THE COMPOUNDING BRANCH DID NOT HAPPEN.  Terror Deathblow came in at 38 against the
# "compounds" threshold of >43, and losses at 80 against >90.  PER-HERO ERRORS COMPOSE, THEY DO
# NOT COMPOUND.  That closes out the original ladder's framing for good: "the model over-credits
# each additional hero, and it compounds with how many" is now refuted on a powered, pre-
# registered test, not merely shown to be underpowered.
#
# --------------------------------- A PANEL MISS, THE FIRST IN EIGHT, AND IT IS SYSTEMATIC
# Predicted infantry 1952.8 / 1941.2 / 1805.7 / 1802.9, cavalry 1820.7 / 1809.7 / 1727.4 / 1729.6,
# archer 1083.1 / 1069.0 / 1012.0 / 1006.6.
# Observed    infantry 1952.8 / 1936.2 / 1805.7 / 1802.9, cavalry 1820.7 / 1804.7 / 1727.4 / 1729.6,
#             archer   1083.1 / 1064.0 / 1012.0 / 1006.6.
# EVERY DEFENSE VALUE IS EXACTLY 5.0 LOW; attack, lethality and health are exact on all three
# types.  A uniform -5.0 on ONE stat across ALL types is not a hero-stat error -- it is a single
# missing term, and the natural reading is a +5% Defense bonus that lapsed.  The previous report
# (22:54:20) still had it; this one (23:03:32) does not, and the player has said buffs have been
# expiring through the session.  WORTH CHECKING ON THE SPECIAL BONUSES PAGE, because it means the
# 500-troop series is not perfectly matched: the earlier fights carried +5% Defense and this one
# did not.  It does not corrupt the scoring -- every fight is run against its OWN reported panel
# with hero_stats=False -- but it is a real inhomogeneity in an otherwise controlled series.

# --------------------------------- A BUG THAT INVALIDATED THE FIRST ROUND OF FITS
# Implementing the calibration exposed it.  Side.effects() emits troop-ability effects with a
# 'Troop:' PREFIX on the name ('Troop:Unyielding Shield'), and every scale scan in this file
# matched the BARE name against TROOP_SKILLS.  Nothing matched, so TROOP ABILITIES WERE BEING
# SCALED ALONGSIDE HERO SKILLS in all of them -- the per-hero s values (0.82, 0.48, 0.50/0.30)
# and the first two-scale fit (0.40 / 0.65) alike.
# WHY IT MATTERS: the heroless fights say troop abilities are RIGHT (k 1.04, clock exact within
# noise), so a fit that quietly scales them down is absorbing a correction the data forbids.  The
# scans only ever ran hero fights, so the heroless control that would have caught it immediately
# was never in the scan.  THE FIX IS TO PUT IT THERE: the clean refit below carries the heroless
# fight as a control row that must stay at 1.0 whatever the scales do.
# WHAT SURVIVES UNTOUCHED, because it never went through a scan: every clock measurement (heroless
# exact, Charles exact, Yang 2.0x, Sophia 1.5x), the proc-vs-aura refutation (rate comparisons),
# the troop-share refutation (raw ratios 0.44 / 0.39 / 0.40), and the single-skill isolation
# (pre-registered from the raw model).  What needed redoing is every fitted number.

# --------------------------------- THE CLEAN REFIT, WITH A CONTROL ROW
# Troop abilities properly excluded this time, and the heroless fight carried as a control that
# must stay at 1.0 whatever the scales do.
#     BEST FIT: offensive x0.30, defensive x0.60   rms log err 0.165 over ten observables
#     fight                    raw loss / rnd     calibrated loss / rnd
#     Charles 250/100/150         0.74  0.98          1.18   1.15
#     Yang    250/100/150         0.61  0.49          1.08   0.89
#     Sophia  250/100/150         0.44  0.66          1.01   1.20
#     Sophia  100/250/150         0.39  0.61          0.97   1.15
#     Sophia  500/0/500           0.40  0.63          0.68   0.90
#     Charles+Sophia              0.35  0.70          0.95   1.20   <- HELD OUT of the fit
#     0 heroes 500 (control)        --    --            --   1.01   <- untouched, as required
# The clean fit is BETTER than the contaminated one (0.165 against 0.170) as well as legitimate.
# Over all eighteen measured fights: rms log err 0.608 -> 0.406, mean|log| 0.500 -> 0.276.
#
# WHERE IT STILL FAILS, AND WHY THAT IS THE NEXT TEST.  The Terry-class fights stay at 1.45 to
# 2.98 -- and they are precisely the fights with HEROES ON BOTH SIDES.  Every one of the eight
# calibration fights was against a HEROLESS Narses, so the correction has only ever been measured
# on MY heroes.  Whether it applies to the opponent's is untested, and it is the largest remaining
# residual in the file.

# --------------------------------- next test, pre-registered: NARSES WITH ONE HERO
# THE MIRROR OF THE CHARLES TEST, using the two-account advantage: put a hero on NARSES and field
# NONE myself.  My heroless side is the configuration this file has validated twice (k 1.04-1.05,
# clock exact), so the only hero in the fight is his, and the enemy-hero channel is isolated as
# cleanly as mine was.
#     ME: 500 at 250/100/150, ALL THREE SLOTS VACANT.  NARSES: 83,600, LONG FEI ONLY.
#     I lose -- I am wiped -- so HIS losses are the uncensored observable, exactly as in the
#     heroless 500 fight whose 16,059 they should be compared against.
# LONG FEI IS THE RIGHT CHOICE OF HIS THREE: he separates the hypotheses most sharply, and his
# skills span both channels (Mighty Paragon proc_taken 40 and Celestial Sustenance def 20 are
# defensive, Art of War proc 80 offensive) so the test exercises both scales at once.  His level
# is 4, already in NARSES_LEVELS and round-trip checked against his in-game tooltips.
# PRE-REGISTERED, generated at 3,000 runs, seed 11:
#     RAW MODEL     he loses 4,482 +/- 805  (90% band 3,178-5,846),  51 rounds, his Ambusher ~10
#     CALIBRATED    he loses 8,614 +/- 869  (90% band 7,203-10,077), 73 rounds, his Ambusher ~15
#     control: with Narses heroless both give 16,808, and the measured value is 16,059.
# The bands are nearly 2x apart and do not overlap, and his Ambusher separates them independently.
# IF THE OBSERVED VALUE LANDS NEAR 8,600, the calibration applies to BOTH sides' heroes and the
# Terry residuals are explained by the same correction applied symmetrically.  IF IT LANDS NEAR
# 4,500, the model is right about ENEMY heroes and wrong only about mine -- which would be a
# strange and very informative asymmetry, and would mean the correction must never be applied to
# an opponent.  Either answer resolves the largest residual left in this file.


# --------------------------------- NARSES + LONG FEI (mail 223407017290304) -- THE MIRROR TEST
# Me heroless at 500 (250/100/150), all three slots Vacant.  Narses 83,620 with LONG FEI ONLY.
#     DEFEAT: I am wiped, 176 + 324 = 500.  HE LOSES 1,473 + 2,733 = 4,206 (residents 79,414).
#     His losses are the uncensored observable, as designed.
#
# I GOT THE PRE-REGISTRATION WRONG, AND THE NAIVE READING OF IT POINTS THE OPPOSITE WAY.
# I predicted his losses at 4,482 raw / 8,614 calibrated, and 4,206 lands squarely on RAW.  But
# those numbers were generated against his HEROLESS panel.  Adding a hero adds his expedition
# STATS as well as his skills, and his infantry line went 238.6 / 232.0 / 179.9 / 181.0 to
# 520.9 / 514.3 / 251.4 / 294.6 -- his infantry attack more than doubled.  I predict MY panel
# before every one of my own fights and had simply never done it for his.  Scored the way every
# other fight in this file is scored, against the panels as reported:
#     RAW MODEL     he loses 2,044 (band 1,315-2,882),  43 rounds   k 0.49
#     CALIBRATED    he loses 3,918 (band 3,001-4,945),  62 rounds   k 0.93
#     OBSERVED                4,206                     ~55-65 rounds
# THE CALIBRATION IS RIGHT AND THE RAW MODEL IS WRONG BY 2x, on both observables.  The round count
# is independently pinned by six rows: his Ambusher 12 -> 60, Mighty Paragon 23 -> 57, my Volley
# 6 -> 60, his Volley 5 -> 50, my Ambusher 9 -> 45, and Art of War 49 -> 65 read as PER_ATTACK
# over three attacking types.  Calibrated says 62.
# SO THE CORRECTION APPLIES SYMMETRICALLY TO BOTH SIDES' HEROES.  It was fitted entirely on MY
# heroes against a heroless opponent; it now predicts a fight in which the only hero on the board
# is the OPPONENT'S, and one belonging to a different account at a different level (Lv.76, 4
# stars, skills at 4).  That is the second out-of-sample validation, and the more demanding one.
# THE LESSON IS ABOUT THE PRE-REGISTRATION, NOT THE MODEL: a pre-registered number is only as good
# as the inputs it was generated from, and taking mine at face value would have produced exactly
# the wrong conclusion.  Predict the OPPONENT's panel too, from now on, whenever his lineup changes.
#
# --------------------------------- SCOREBOARD, ALL NINETEEN FIGHTS
#     raw         mean k 1.04   rms log err 0.613   mean|log| 0.511
#     calibrated  mean k 1.24   rms log err 0.395   mean|log| 0.265
# The whole controlled 500-troop series lands 0.70-1.18 calibrated, including the enemy-hero
# fight at 0.92 and the held-out two-hero fight at 0.97.  The heroless fights are untouched.
#
# WHAT THE CALIBRATION DOES NOT FIX, STATED PLAINLY.  The Terry-class fights stay at 1.45 to 2.98
# and some get WORSE (Terry 20k mixed 1.90 -> 2.10, Terry 10k all inf 2.54 -> 2.98).  I expected
# the enemy-hero result to explain them; it does not, because the calibration was already being
# applied to both sides in those runs.  So they have a different problem, and the honest reading
# is that they are the least controlled data in the file: a real opponent whose buff state,
# widget levels and research are all unknown, at 10-20k troops where a fight lasts a handful of
# rounds and every observable is noisy.  They should NOT be used to tune anything.
#
# --------------------------------- CALIBRATION IS NOW ON FOR RANKINGS
# sim.enable_hero_calibration() is called by run.py and elo.py.  It stays OFF in allfights.py and
# the diagnostics, which exist to keep the raw error visible.  The justification is that the raw
# model is wrong by 2-3x on every hero fight measured and the correction is ASYMMETRIC, so it
# reorders offensive against defensive heroes instead of cancelling out of a relative ranking --
# which is exactly the kind of error a ranking cannot absorb.  It remains two constants with no
# mechanism; that search is not closed, it is just no longer blocking the rankings.


# --------------------------------- ELO RERUN, CALIBRATED (2026-09-10)
# TWO THINGS HAD TO BE FIXED BEFORE THE RANKING MEANT ANYTHING.
# 1. The banner was stale: it quoted "rms log err 0.90" from an engine several fixes ago and said
#    nothing about the calibration being on.  Rewritten to print the live scales and what they do
#    and do not justify.
# 2. THE ROUND-ROBIN WAS DEGENERATE AT EQUAL TROOPS.  A garrison beats a rally of the same size in
#    essentially every cell, so win rates pinned at 0 or 100 and the Bradley-Terry fit ran into a
#    separation boundary -- FIVE DEFENDERS TIED AT EXACTLY 2028, which is the fit failing, not a
#    result.  A rally is several marches against one garrison anyway, so ATT_SIZE now sizes the
#    attacker as a multiple of the garrison.  Probed at N=60: 2x gives a 51% mean win rate, 3x
#    gives 79%, 4x gives 87%.  DEFAULT 2.0.  Same lesson as the 500-troop calibration marches --
#    pick the matchup where the observable actually varies.
#
# ATTACK, calibrated (raw in brackets):
#     2106 [1850]  Charles / Sophia / Marlin      55/45/0
#     1991 [1760]  Charles / Sophia / Yang        60/40/0
#     1770 [1946]  Triton / Thrud / Yang          50/20/30
#     1687 [1570]  Charles / Sophia / Wee & Woo   55/45/0
#     1474 [1389]  Charles / Ava / Yang           45/30/25
#     1201 [1014]  Charles / Ava / Wee & Woo      40/35/25
#      848 [ 759]  Amadeus / Ava / Wee & Woo      50/20/30
# DEFENCE, calibrated (raw in brackets):
#     1951 [1961]  Charles / Sophia / Wee & Woo   60/15/25
#     1750 [1736]  Long Fei / Sophia / Wee & Woo  40/60/0     <- UNDER-rated, Lv.4 magnitudes
#     1606 [1841]  Charles / Sophia / Wee & Woo   35/65/0
#     1588 [1761]  Triton / Sophia / Vivian       60/15/25
#     1514 [1474]  Charles / Jabel / Wee & Woo    60/15/25
#      850 [1093]  Charles / Ava / Wee & Woo      35/25/40
#      665 [ 846]  Alcar / Sophia / Wee & Woo     40/60/0
#
# THE CALIBRATION CHANGES THE ANSWER, WHICH IS THE POINT OF IT BEING ASYMMETRIC.  Triton / Thrud /
# Yang falls from FIRST attacker (1946) to THIRD (1770) and Charles / Sophia / Marlin takes the
# top spot.  That is the proc-heavy lineup being demoted, exactly the reorder predicted when the
# correction was wired in: a uniform error would have cancelled out of a mirror-stat ranking, an
# offensive-vs-defensive one does not.  The defence order is more stable -- the same lineup leads
# both -- because defence leans less on the channel that was most over-credited.
#
# CAVEATS THAT STILL STAND.  Long Fei carries Lv.4 magnitudes read off Narses' account, so his
# garrison is under-rated and would place higher with maxed skills.  This file runs hero_stats=True
# and widget_default=1.0 against USER_STATS, a configuration no report has validated (allfights
# validates the opposite one); the calibration touches only skill effects so it does not interact
# with that, but the base stats underneath are unverified.  And the scales remain two constants
# with no mechanism.  READ THE ORDER, NOT THE NUMBERS.


# --------------------------------- THE "LONG FEI IS UNDER-RATED" CAVEAT WAS WRONG
# Asked by the player: why not use the Long Fei data we scraped?  We already were.
# apply_site_magnitudes() runs at import and overwrites every modelled magnitude with the site's
# MAX-level value, so the canonical table has held Mighty Paragon 50 / Celestial Sustenance 25 /
# Art of War 100 -- his L5 column -- since the crawl.  elo.py never passes skill_levels, so the
# Elo run rated him at max.  THE RANKING WAS RIGHT; THE WARNING PRINTED ABOVE IT WAS NOT, AND SO
# WAS THE CAVEAT I ATTACHED TO IT.  His garrison at 1750 is his real rating, not a floor.
# WHY THE FLAG WAS STALE.  UNDERLEVELLED was derived from SKILL_LEVEL, which records WHERE EACH
# VALUE WAS FIRST READ -- Long Fei and Rosa off Narses' Lv.4 account.  That was the right flag
# when those readings WERE the table.  The crawl replaced the readings and nobody replaced the
# flag, so it kept warning about a correction that had already been made.  A derived set is only
# as good as the thing it is derived from.
# ALSO SUPERSEDED: the comment insisting "the Lv.4 -> Lv.5 step cannot be inferred from what is
# recorded" and refusing to guess it.  Correct when written; the site supplies the whole L1-L5
# track, so the step is READ (Mighty Paragon 40 -> 50, Art of War 80 -> 100), not fitted.
# WHAT THE FLAG NOW TRACKS.  The site covers every modelled skill but FOUR -- Saul/Resourceful,
# Yeonwoo/Well-Traveled, Amane/Exorcism, Fahd/Pathfinder -- which keep magnitudes typed in from
# prose with nothing to check them against.  UNSOURCED now names those four heroes, and the
# warning says the rating is uncertain IN EITHER DIRECTION rather than under-rated, which is the
# honest shape of that uncertainty.
# The two mechanisms are now cleanly separated and both verified: the canonical table holds MAX
# (50 / 25 / 100), and skill_levels + level_scale takes an opponent's copy down to his actual
# level (Narses' Long Fei: 40 / 20 / 80, exactly x0.8).  allfights is unchanged at rms 0.395.


# --------------------------------- FULL TRIO vs FULL TRIO (mail 223407017291692) -- THE CALIBRATION BREAKS
# Charles / Sophia / Yang, 500 at 300 infantry / 200 cavalry / ZERO archers, against Narses'
# LARGE garrison (61,785 / 24,714 / 37,071 = 123,570) with Long Fei, Jabel AND Rosa.
#     DEFEAT: I am wiped (500, -23,625 power).  HE LOSES 8,142 -- the uncensored observable.
#     RAW         he loses 29,501   160 rounds   k 3.62
#     CALIBRATED  he loses 23,760   172 rounds   k 2.92
#     OBSERVED             8,142    ~90 rounds
# NOT PRE-REGISTERED, so this is post-hoc scoring and weaker evidence than the designed tests.
#
# THE FIRST FIGHT WHERE THE SIMULATOR RUNS TOO LONG.  Sophia's Terror Deathblow is periodic 1-in-2
# and fired 45 -> 90 ROUNDS, corroborated by Arcane Pact 31 -> 78, Ambush 30 -> 75, Assault Lance
# 14 -> 93, Ice Zone 41 -> 103, and both Ambushers at 21 -> 105.  The simulator says 172.  Every
# previous error had it ending fights EARLY.  I lose here, so the length is set by how fast HE
# kills ME: his output is about 2x UNDER-modelled, and the calibration scales his heroes DOWN,
# which makes it worse.
#
# TWO FIGHTS, TWO OPPOSITE ANSWERS.  Applying the calibration per side (k on his losses / round
# ratio; 1.00 / 1.00 is perfect):
#     fight                      neither        mine only          BOTH
#     1 enemy hero (Long Fei)  0.48 / 0.72    0.48 / 0.72    0.93 / 1.03
#     3 enemy heroes (trio)    3.62 / 1.78    0.91 / 0.98    2.91 / 1.90
# The Long Fei fight needs the correction ON the opponent; this one needs it OFF.  NO SINGLE RULE
# COVERS BOTH.  That is evidence the calibration is fitting a REGIME rather than a mechanism --
# which was always the risk of adopting two constants, and it has now been caught by data rather
# than by argument.  It does not undo the nine controlled fights it does describe; it bounds them.
#
# CONFOUNDS, STATED BEFORE ANYONE READS TOO MUCH INTO "1 vs 3 ENEMY HEROES".  The two fights also
# differ in his garrison (83,600 in thirds vs 123,570 at 50/20/30), in my composition (250/100/150
# vs 300/200/0), and in my own hero count (none vs three).  Enemy hero count is the most
# interesting difference but it is NOT isolated, which is exactly what the next test fixes.
# Also note this march had NO ARCHERS while Yang held the archer slot: his Avalanche collapsed to
# 1 as the scope gate predicts, but ICE ZONE FIRED 41 TIMES FOR 686 KILLS with no archers on the
# board.  Consistent with the Terry all-infantry report where Yang books kills without archers,
# and still unexplained -- Ice Zone's tooltip says "Yang's ARCHERS".
#
# CONSEQUENCE FOR THE ELO TABLES, STATED PLAINLY.  They apply the calibration to BOTH sides, and
# every pairing in them has three heroes a side -- the regime where "both" is worst (2.91).  The
# rankings I reported an hour ago are therefore on weaker ground than I said at the time.  The
# ORDER may still be usable, since mirror pairings cancel more than a one-sided fight does, but
# that is now an assumption rather than something measured.  DO NOT treat the Elo numbers as
# settled until the test below resolves which rule is right.

# --------------------------------- next test, pre-registered: NARSES WITH ALL THREE HEROES
# THE EXACT CONTINUATION OF THE LONG FEI TEST -- 1 enemy hero to 3, everything else held.
#     ME: 500 at 250/100/150, ALL THREE SLOTS VACANT.  NARSES: 83,600 (27,866 / 27,877 / 27,877),
#     LONG FEI + JABEL + ROSA.  Same garrison, same composition, same heroless me as the fight
#     that produced 16,059 and the one that produced 4,206.
#     His panel should read infantry 520.9 / 514.3 / 251.4 / 294.6, cavalry 356.1 / 345.5 /
#     259.4 / 227.3, archer 474.3 / 467.2 / 311.3 / 243.9 -- the Stat Bonuses are percentages, so
#     the trio's panel from the large-garrison fight should carry over unchanged.  If it does not,
#     his research or buffs moved and that must be recorded before scoring.
# PRE-REGISTERED, 3,000 runs, seed 11.  I field no heroes, so "mine only" is the same as no
# calibration at all, and the two rules separate cleanly:
#     CALIBRATION ON BOTH     he loses 768 +/- 163  (90% band 516-1,049),  25 rounds
#     CALIBRATION MINE ONLY   he loses 259 +/- 120  (90% band 83-478),     14 rounds
# The bands do not overlap.  Read the round count off HIS Ambusher (chance .20) and Jabel's rows.
# WHAT EACH OUTCOME MEANS.  Near 768 and the two-sided rule survives, and the trio fight's failure
# is about MY no-archer march or his larger garrison rather than his hero count.  Near 259 and the
# one-sided rule wins, meaning the correction must never touch an opponent -- which would also
# retract the conclusion I drew from the Long Fei fight.  ABOVE 1,049 and neither rule works and
# the enemy-hero channel needs its own treatment entirely.


# --------------------------------- NARSES' SKILL LEVELS: ACCOUNTED FOR AND VERIFIED
# Asked by the player: Long Fei and Rosa are at 4, Jabel at 5.  That is exactly NARSES_LEVELS, and
# it is passed as skill_levels in every scoring run and every pre-registration above.  Verified on
# all NINE skills rather than the one I had checked before:
#     Long Fei  Mighty Paragon 50 -> 40   Celestial Sustenance 25 -> 20   Art of War 100 -> 80
#     Jabel     Rally Flag 40             Hero's Domain 50                Youthful Rage 25 (Lv.5, unchanged)
#     Rosa      Chaos Gambit 50 -> 40     Enchanting Dance 20 -> 16       Golden Rhythm 30 -> 24
# All three of Rosa's scale despite Enchanting Dance needing the SKILL_ALIAS -> 'roseofwar' lookup,
# which was the one place this could have silently no-opped (level_scale returns 1.0 on a miss).
#
# --------------------------------- BUT HIS WIDGETS ARE NOT ACCOUNTED FOR, AND THAT IS A REAL GAP
# The question exposed a different omission on the same side of the board.  Every fight in this
# file runs widget_default=0.0 for BOTH sides, which is right for MY side (validated that way) and
# right for a HEROLESS Narses (no heroes, no widgets) -- but wrong the moment he fields heroes.
# Two of his three carry 'defender' widgets that apply in a garrison:
#     Long Fei ('defender','attack',15)   Jabel ('defender','lethality',15)   Rosa ('rally',...) inert
# Widgets are Special Bonuses, so they multiply AFTER the panel sum and are NOT in the reported
# Stat Bonuses -- giving him zero silently under-credits him, which is exactly the direction the
# trio fight's failure needs.
#     TRIO FIGHT (observed 8,142 in ~90 rounds)
#         raw          widgets off  29,352  k 3.60  160r      widgets on  21,836  k 2.68  118r
#         calibrated   widgets off  23,723  k 2.91  171r      widgets on  17,606  k 2.16  127r
#     LONG FEI FIGHT (observed 4,206 in ~60 rounds)
#         raw          widgets off   2,032  k 0.48   43r      widgets on   1,791  k 0.43   38r
#         calibrated   widgets off   3,905  k 0.93   62r      widgets on   3,415  k 0.81   54r
# HIS WIDGETS MOVE EVERYTHING THE RIGHT WAY ON THE TRIO FIGHT and cost a little on the Long Fei
# one, and the conclusion drawn from Long Fei survives either way (0.81 calibrated against 0.43
# raw).  They do NOT resolve the contradiction: the trio fight is still 2.16x off with widgets on
# and the calibration applied to both sides, while "mine only" fits it.
# UNKNOWN AND WORTH ASKING: his actual widget levels.  Long Fei's slot reads as a LOCKED padlock in
# the Hero Comparison panel while the other two look unlocked, so widget_default=1.0 for all three
# is probably too generous and 0.0 is definitely too stingy.  Not fitted -- asked.
#
# --------------------------------- pre-registration REVISED for the widget cases
# Me heroless 500 (250/100/150) vs Narses 83,600 with all three heroes, skills 4/5/4:
#     rule                       his widgets OFF              his widgets ON
#     calibration on BOTH     766 (515-1,047)  25r          587 (369-850)  19r
#     calibration MINE ONLY      259 (84-475)  14r           199 (45-395)  11r
# The two RULES still separate cleanly whichever widget state turns out to be right -- 766 vs 259,
# or 587 vs 199 -- because the widget effect is much smaller than the rule difference.  That is
# what makes the test still worth running before his widget levels are known.


# --------------------------------- HIS WIDGET STATE, ANSWERED: THE GAP WAS NOT REAL
# The player checked: the padlock means the widget is NOT OWNED.  Long Fei has none, Rosa has
# none, Jabel's is level 1.  So the honest configuration is widget_default=0.0 on his side with a
# sliver for Jabel -- which is what every fight in this file was ALREADY doing.
#     TRIO FIGHT, calibrated, by Jabel's widget fraction:
#         0.00 -> k 2.91 / 171r     0.05 -> 2.89 / 170r     0.10 -> 2.87 / 169r
#         0.20 -> 2.82 / 166r       1.00 -> 2.50 / 147r  (impossible; shown only as a bound)
#     Observed 8,142 in ~90 rounds.
# SO THE WIDGET LEAD IS DEAD, and both of the previous entry's conclusions REVERT to their
# widgets-off form -- which is to say they stand exactly as first scored:
#     Long Fei fight   calibrated k 0.93, 62 rounds against ~60 observed.  He owns no widget, so
#                      the 0.81 figure computed with one was the hypothetical, not the correction.
#     Trio fight       calibrated k 2.87-2.91, ~170 rounds against ~90.  Still ~3x wrong.
# The two-rules contradiction therefore stands in full: Long Fei needs the calibration applied to
# the opponent, the trio needs it not applied, and nothing about his account explains the
# difference.  Worth noting that the lead was still worth chasing -- it was a real unmodelled term
# and the only way to find out it was negligible was to ask and then measure it.
#
# WHAT THIS RULES OUT, which is the useful part.  The trio fight's ~3x miss is NOT his skill levels
# (verified on all nine), NOT his expedition stats (they are in the reported panel), NOT his gear
# (likewise), and NOT his widgets (he has essentially none).  His side is now fully specified from
# the report, so whatever is wrong is in the MODEL, not in the inputs.
#
# PRE-REGISTRATION STANDS AT THE WIDGETS-OFF NUMBERS.  Me heroless 500 (250/100/150) vs Narses
# 83,600 with all three heroes, skills 4/5/4, his widgets as above:
#     CALIBRATION ON BOTH     he loses 766 +/- 163  (90% band 515-1,047),  25 rounds
#     CALIBRATION MINE ONLY   he loses 259 +/- 120  (90% band 84-475),     14 rounds


# =================================================================================================
# FRESH LOOK (2026-09-10): THE HERO OVER-CREDIT WAS A UNIT-CONVENTION BUG, NOT A MECHANISM
# =================================================================================================
# Asked to look again with fresh eyes.  What turned up is a single line, and it accounts for
# nearly everything the calibration layer was papering over.
#
# THE BUG.  heroes.py stores a rolled proc as its EXPECTED VALUE -- Ice Zone is 40, meaning
# 0.40 x 100% -- and sim._split_effects recovers the live magnitude by dividing by uptime.  That
# was the convention behind the "six for six" tooltip verification.  apply_site_magnitudes(),
# added with the kingshotoptimizer crawl, then overwrote every stored value with the site's raw
# MAGNITUDE (Ice Zone -> 100), and the division by uptime stayed.  Every chance and periodic proc
# went live at magnitude / uptime:
#     Ice Zone  +250% (tooltip +100%)    Avalanche  +400% (+100%)    Terror Deathblow  +400% (+200%)
#     Ambush    +100% (+50%)             Arcane Pact -100% (-50%)    Mighty Paragon    -125% (-50%)
# Flat auras were untouched, which is exactly why Charles needed almost no correction and Sophia's
# firing RATES matched while her EFFECT was 2x too large; and why the fitted offensive scale came
# out at 0.30, i.e. 1/(2 to 4).  Long Fei's values were the exception (raw Lv.4 magnitudes read
# off Narses' tooltips), which is the mixed convention that hid this.
#
# THE FIX.  apply_site_magnitudes() now targets magnitude x uptime for any skill with a PROC_SPEC
# entry, scaling from the stored value only for the shape of multi-component skills.  Verified:
# every proc goes live at its tooltip magnitude.  Two 20% residuals noted, not chased -- Ambush and
# Arcane Pact land at 40 where the in-game tooltip says 50; the site's L5 track reads 40.
#
# WHAT IT DOES, RAW, WITH NO FITTED CONSTANTS AT ALL:
#     the original 10k ladder     rms 0.287 -> 0.048    1.08 / 0.96 / 1.05 / 1.03 / 1.00  -- FLAT
#     all nineteen fights          rms 0.613 -> 0.390   (the calibrated engine, with two fitted
#                                                        constants, was 0.395)
#     Yang only  0.60 -> 1.04     Sophia only  0.45 -> 0.91     Long Fei  0.50 -> 0.95
# THE CALIBRATION IS RETIRED.  elo.py and run.py run raw.  The layer stays in sim.py, off, as a
# record.  The "two rules" contradiction is resolved for the fight that produced it: Long Fei
# scores 0.96 / clock 1.07 with nothing applied to either side.
#
# WHAT THE BUG DID NOT EXPLAIN -- CHARLES -- AND THE FORM OF THE DEFENCE COEFFICIENT.
# Charles has no procs, so he stayed at 0.74.  The candidate is the FORM of the defensive
# channel: sim.py used the SoS reference's 1/(1 - c), imported over the Kingshot-cited (1 + c)
# that skill_mod's own docstring quotes.  Tested as a binary form choice, not a magnitude:
#     LINEAR, all nineteen fights   rms 0.390 -> 0.182   spread 0.80-1.69   17 of 19 improve
#     Charles 0.74 -> 1.11   Charles+Sophia 0.55 -> 1.04   Long Fei 0.95 -> 1.08
#     opponent-2 1.32 -> 1.03   Terry 20k 1.58 -> 1.26
# BUT NOT SETTLED.  The same switch takes the 10k ladder from 0.048 to 0.280, and one rung is a
# powered miss: Charles+Yang at 1,000 goes 25.9 -> 39.3 against an observed 26 with sd 3.9,
# z +3.4.  Charles fits linear at 500 troops (his one powered fight, 223, sits inside linear's
# 207-297 and outside reciprocal's 134-200) and reciprocal at 1k/10k.  Neither form is the
# mechanism yet.  Linear is the DEFAULT -- larger and better-powered set, and the Kingshot-cited
# form -- with the conflict recorded at the switch in sim.py.  DEF_RECIP=1 restores the reference.
#
# THE TRIO FIGHT, NOW ISOLATED.  With both fixes its CLOCK is right -- 96 rounds against ~90
# observed, from 207 -- while its loss total stays 2.8x (22,870 against 8,142).  My survival is
# now modelled correctly there; my per-round OUTPUT is not.  Sensitivity probes say the sim thinks
# my missing archers barely matter (35,227 -> 33,945) while reality moved 6x between the two
# matched fights, so the composition thread stays open and is exactly what the heroless
# composition test below separates.
#
# THE SINGLE-TYPE OUTLIERS SURVIVE BOTH FIXES.  Terry 10k all inf 1.69, Narses 1500 pure inf
# 1.30, Terry 10k all archer 1.12 -- every fight where I fielded one troop type still runs high.
# Every heroless validation was a three-type march, so the damage core's behaviour with a type
# ABSENT has never been tested on its own.

# --------------------------------- next tests, pre-registered (raw engine, both fixes, no calibration)
# 1. DEFENCE FORM.  Charles only, 1,000 at 500/200/300, all other slots Vacant, heroless Narses.
#        LINEAR      I win, losing 157 (90% band 127-191), ~93 rounds
#        RECIPROCAL  I win, losing 109 (90% band  84-136), ~92 rounds
#    Bands do not overlap.  Either answer settles the form on a powered fight at the size where
#    the two currently disagree.
# 2. COMPOSITION.  Heroless me vs heroless Narses 83,620, composition varied, nothing else:
#        300/200/  0   he loses 14,775 +/- 1,334  (12,613-17,073)   ~106 rounds
#        500/  0/500   he loses 54,527 +/- 9,014  (42,306-71,456)   ~133 rounds   (I win 2%)
#    (measured baseline 250/100/150: 16,059, sim 16,723.)  If 300/200/0 lands near 14,775 the
#    core handles an absent type and the trio residual is in the hero layer; if it is far off,
#    the core itself mis-handles composition and that is a bug in a sixty-line loop.

# --------------------------------- ELO, RAW ENGINE, BOTH FIXES -- FIRST RUN WAS DEGENERATE
# The rerun at ATT_SIZE 2.0 came back with five attackers tied at exactly 1960 and every defender
# at ~1040: the Bradley-Terry fit pinned at a separation boundary, as it was before ATT_SIZE
# existed.  The two fixes shifted the attack/defence balance enough that a 2x attacker now wins
# essentially every cell, so 2.0 is no longer the informative middle.  A sentence claiming "the
# two headline recommendations survive" was written against that table and is RETRACTED -- a
# degenerate fit supports no claim about order.  Re-probed and re-run below.

# --------------------------------- THE SITE'S PER-LEVEL TRACK IS SOMETIMES THE CHANCE
# Chasing the two "20% residuals" (Ambush and Arcane Pact live at 40 where the in-game tooltip
# says 50) found a second convention split, this time on the site's side.  For every skill worded
# "40% chance of ... by 50%" the site's L1-L5 track runs 8/16/24/32/40 -- it is the CHANCE that
# levels, and the 50% magnitude is fixed.  For Mighty Paragon ("40% chance ... by 50%" as well,
# but tracked 10/20/30/40/50) it is the MAGNITUDE that levels.  The site is not consistent, so no
# rule on the numbers alone can tell them apart; the descriptions can.
# A scan for every chance proc whose track max equals chance x 100 found fourteen candidates.
# Read against their descriptions:
#     CHANCE-TRACKS (EV was 16, should be 0.40 x 50 = 20):  Ambush, Arcane Pact, Unrighteous
#         Strike, Oath of Guardian, Rally Flag (Jabel -- Narses' fights), Trial by Fire, Wild Card
#     COINCIDENCES ("50% chance of ... 50%": both readings give EV 25):  Hero's Domain, Precision
#         Shot, Infinite Arsenal, Dynamo, Evil Eye, The Favor -- already right, no flag needed
#     Boom Boom (Wee & Woo) is not in the crawl at all.
# heroes.SITE_TRACK_IS_CHANCE carries the seven with their fixed magnitude; apply_site_magnitudes
# targets (track / 100) x magnitude for them.  All seven verified at EV 20.  The pre-crawl
# hand-entered values had every one of these right; the crawl made them wrong; and it took a bug
# hunt that started somewhere else entirely to notice.

# --------------------------------- FINAL SCOREBOARD OF THE FRESH LOOK -- RAW, ALL FIXES, NO CONSTANTS
# Proc EVs restored, seven chance-tracks flagged, linear defence.  Nothing fitted.
#     rms log err 0.194   mean|log| 0.146   spread 0.79-1.74   (start of the day: 0.613 / 0.511)
#     the controlled 500-troop series:
#         NO HEROES 0.99   YANG 1.08   CHARLES 1.13   SOPHIA 1.01   SOPHIA 100/250/150 0.95
#         CHARLES+SOPHIA 1.06   + LONG FEI 1.08                      SOPHIA no cav 0.79
#     the older fights:
#         mixed atk 10k 0.99   inf+arch 1k 0.94   mixed def 5k 1.11   opponent-2 1.10
#         Terry 10k archer 1.18   Terry 20k 1.28   NO HEROES 1000 1.21   500 solo 0.81
#     still out:
#         Terry 10k all inf 1.74   Narses 1500 pure inf 1.33   pure-arch 5k 0.82   no cav 0.79
# EVERY REMAINING OUTLIER IS A MARCH WITH A TROOP TYPE MISSING.  That is the composition thread,
# the one thing never tested heroless, and the pre-registered 300/200/0 and 500/0/500 fights are
# built to separate it from the hero layer.  The trio fight (2.82, clock right) is the same thread
# with heroes on top.

# --------------------------------- ELO, RAW ENGINE, ALL FIXES, ATT_SIZE 1.25 (2026-09-10)
# 7x7 round-robin, 300 battles a pairing.  Non-degenerate: distinct ratings, win rates span the middle.
#          1929  DEFENSE  Charles / Sophia / Wee & Woo  60/15/25
#          1881  ATTACK   Charles / Ava / Yang  45/30/25
#          1861  ATTACK   Charles / Sophia / Yang  60/40/0
#          1755  ATTACK   Charles / Ava / Wee & Woo  40/35/25
#          1576  DEFENSE  Charles / Sophia / Wee & Woo  35/65/0
#          1538  DEFENSE  Charles / Jabel / Wee & Woo  60/15/25
#          1524  ATTACK   Triton / Thrud / Yang  50/20/30
#          1432  DEFENSE  Charles / Ava / Wee & Woo  35/25/40
#          1431  DEFENSE  Triton / Sophia / Vivian  60/15/25
#          1418  ATTACK   Amadeus / Ava / Wee & Woo  50/20/30
#          1339  DEFENSE  Long Fei / Sophia / Wee & Woo  40/60/0
#          1284  ATTACK   Charles / Sophia / Marlin  55/45/0
#          1080  ATTACK   Charles / Sophia / Wee & Woo  55/45/0
#           952  DEFENSE  Alcar / Sophia / Wee & Woo  40/60/0
# Read the ORDER, not the numbers.  Ratings stay soft while the defence-coefficient form is an
# open split verdict; the attacker-size ratio that makes the matrix informative fell from 2.0
# to 1.25 with the fixes, which is itself a substantive shift in modelled attack/defence balance.
