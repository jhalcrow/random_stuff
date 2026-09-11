#!/usr/bin/env python3
"""Governor gear allocation for castle battles.

Enumerates every affordable combination of upgrade steps across the six governor gear pieces,
applies the set-bonus rule, and scores each in the simulator on the castle-attack and
garrison-defense scenarios.  Gear table (per-piece costs, cumulative stat %, set bonus %) is
from kingshot.net/database/governor-gear.

  python3 kingshot/gear.py
"""
import copy, itertools, re, statistics
from sim import Side, USER_STATS, TYPES, battle, ratio_troops, score, ATTACK_JOINERS, DEFENSE_JOINERS

# (tier, star): (satin, threads, artisan's vision, cumulative stat %, set bonus %)  -- Red tiers
TABLE = {
    ('Red T3', 0): (288000, 2880, 570, 127.75, 19.5), ('Red T3', 1): (302000, 3020, 600, 130.5, 19.5),
    ('Red T3', 2): (317000, 3170, 630, 133.25, 19.5), ('Red T3', 3): (333000, 3330, 660, 136.0, 19.5),
    ('Red T4', 0): (358000, 3580, 720, 138.75, 23.0), ('Red T4', 1): (384000, 3840, 770, 141.5, 23.0),
    ('Red T4', 2): (403000, 4030, 810, 144.25, 23.0), ('Red T4', 3): (423000, 4230, 850, 147.0, 23.0),
    ('Red T5', 0): (451000, 4510, 910, 150.0, 26.5), ('Red T5', 1): (479000, 4790, 970, 153.0, 26.5),
}
ORDER = [('Red T3', 0), ('Red T3', 1), ('Red T3', 2), ('Red T3', 3), ('Red T4', 0), ('Red T4', 1),
         ('Red T4', 2), ('Red T4', 3), ('Red T5', 0), ('Red T5', 1)]
TIER_RANK = {'Red T3': 3, 'Red T4': 4, 'Red T5': 5}

# your pieces: (troop type, current level) -- Governor Profile screenshot, 2026-09-11.
# Mapping confirmed by the player: crown + necklace = cavalry, helm + pants = infantry,
# ring + mace = archer.
PIECES = [('inf', ('Red T4', 1)), ('inf', ('Red T4', 0)), ('cav', ('Red T3', 1)), ('cav', ('Red T3', 1)),
          ('arch', ('Red T4', 0)), ('arch', ('Red T4', 0))]

# GOVERNOR CHARMS.  Each gear piece holds 3, so 6 per troop type; each charm gives BOTH lethality
# and health to its type (confirmed by the player), +4% each per level.  Per-level cost from
# kingshot.net/database/governor-charm, cross-checked against kingshotoptimizer.com/charms.
# level: (charm guides, charm designs, cumulative stat % per charm)
CHARM_TABLE = {12: (580, 600, 59.0), 13: (610, 780, 63.0), 14: (645, 960, 67.0),
               15: (685, 1140, 71.0), 16: (730, 1320, 75.0), 17: (780, 1500, 79.0),
               18: (835, 1680, 83.0)}
CHARM_STEP = 4.0
# your charms, 2026-09-11: infantry all 16, cavalry all 14, archer a mix of 14 and 15
CHARMS = {'inf': [16]*6, 'cav': [14]*6, 'arch': [14]*3 + [15]*3}
BUDGET = dict(satin=3_600_000, threads=41_190, av=6_460)
MAX_STEPS = 4
RALLY = 1_900_000
ENEMY_SCALE = 0.9

enemy = {t: {k: v * ENEMY_SCALE for k, v in USER_STATS[t].items()} for t in TYPES}
DEF_PANEL = [['Charles', 'Sophia', 'Wee & Woo'], ['Alcar', 'Margot', 'Vivian'], ['Triton', 'Sophia', 'Vivian'], ['Charles', 'Margot', 'Wee & Woo']]
ATT_PANEL = [['Amadeus', 'Ava', 'Yang'], ['Triton', 'Thrud', 'Yang'], ['Charles', 'Ava', 'Wee & Woo'], ['Charles', 'Sophia', 'Yang']]


def set_bonus(levels, at_or_above=True):
    """(defense bonus %, attack bonus %) from tier matching.  at_or_above: higher-tier pieces count
    toward lower-tier sets (the sensible reading); otherwise tiers must match exactly."""
    ranks = [TIER_RANK[l[0]] for l in levels]
    best_d = best_a = 0.0
    for tier, r in TIER_RANK.items():
        n = sum(1 for x in ranks if (x >= r if at_or_above else x == r))
        val = TABLE[(tier, 0)][4]
        if n >= 3:
            best_d = max(best_d, val)
        if n >= 6:
            best_a = max(best_a, val)
    return best_d, best_a


def stats_for(levels):
    """Your stats after moving pieces to `levels` (deltas relative to current gear)."""
    cur = [p[1] for p in PIECES]
    s = copy.deepcopy(USER_STATS)
    for (ttype, _), old, new in zip(PIECES, cur, levels):
        d = TABLE[new][3] - TABLE[old][3]
        s[ttype]['attack'] += d
        s[ttype]['defense'] += d
    d0, a0 = set_bonus(cur)
    d1, a1 = set_bonus(levels)
    for t in TYPES:
        s[t]['defense'] += d1 - d0
        s[t]['attack'] += a1 - a0
    return s


def cost_of(levels):
    tot = dict(satin=0, threads=0, av=0)
    for (_, old), new in zip(PIECES, levels):
        i0, i1 = ORDER.index(old), ORDER.index(new)
        for lv in ORDER[i0 + 1:i1 + 1]:
            c = TABLE[lv]
            tot['satin'] += c[0]; tot['threads'] += c[1]; tot['av'] += c[2]
    return tot


def attack_score(my):
    out = []
    for dl in DEF_PANEL:
        a = Side('A', my, ratio_troops(RALLY, 60, 40, 0), heroes=['Charles', 'Sophia', 'Yang'], role='rally', joiners=ATTACK_JOINERS)
        d = Side('D', enemy, ratio_troops(RALLY, 60, 15, 25), heroes=dl, role='garrison', joiners=DEFENSE_JOINERS)
        out.append(score(battle(a, d), 'A'))
    return statistics.geometric_mean(out)


def defense_score(my):
    out = []
    for al in ATT_PANEL:
        ar = (55, 45, 0) if 'Sophia' in al else (50, 20, 30)
        a = Side('A', enemy, ratio_troops(RALLY, *ar), heroes=al, role='rally', joiners=ATTACK_JOINERS)
        d = Side('D', my, ratio_troops(RALLY, 60, 40, 0), heroes=['Charles', 'Sophia', 'Wee & Woo'], role='garrison', joiners=DEFENSE_JOINERS)
        out.append(score(battle(a, d), 'D'))
    return statistics.geometric_mean(out)


if __name__ == '__main__':
    base_a, base_d = attack_score(USER_STATS), defense_score(USER_STATS)
    print(f'baseline: attack kill ratio {base_a:.3f}, defense kill ratio {base_d:.3f}; set bonus now {set_bonus([p[1] for p in PIECES])}')
    results = []
    for steps in itertools.product(range(MAX_STEPS + 1), repeat=len(PIECES)):
        levels = [ORDER[ORDER.index(p[1]) + n] for p, n in zip(PIECES, steps)]
        c = cost_of(levels)
        if any(c[k] > BUDGET[k] for k in BUDGET):
            continue
        s = stats_for(levels)
        ga, gd = attack_score(s) / base_a - 1, defense_score(s) / base_d - 1
        results.append((ga + gd, ga, gd, steps, levels, c))
    results.sort(reverse=True)
    print(f'{len(results)} affordable plans evaluated\n')
    def show(r):
        tot, ga, gd, steps, levels, c = r
        names = ['inf1', 'inf2', 'cav1', 'cav2', 'arch1', 'arch2']
        plan = ', '.join(f'{n} -> {l[0]} {l[1]}*' for n, l, st in zip(names, levels, steps) if st)
        print(f'  attack {ga*100:+5.2f}%  defense {gd*100:+5.2f}%  set {set_bonus(levels)}  threads {c["threads"]:,} av {c["av"]:,} satin {c["satin"]:,}\n      {plan or "no upgrades"}')
    print('Top plans by combined gain (attack + defense kill-ratio gain):')
    for r in results[:8]: show(r)
    print('\nBest for attack only:'); show(max(results, key=lambda r: r[1]))
    print('\nBest for defense only:'); show(max(results, key=lambda r: r[2]))
    print('\nReference plans:')
    for label, steps in [('all four T3 pieces +1 star', (0, 0, 1, 1, 1, 1)), ('both cav to T4 0*', (0, 0, 4, 4, 0, 0)),
                         ('inf pieces +1 star each', (1, 1, 0, 0, 0, 0)), ('cav1 to T4 0*, cav2 +3 stars', (0, 0, 4, 3, 0, 0)),
                         ('arch2 to T4 0* (3rd T4 piece)', (0, 0, 0, 0, 0, 3))]:
        levels = [ORDER[ORDER.index(p[1]) + n] for p, n in zip(PIECES, steps)]
        c = cost_of(levels)
        ok = all(c[k] <= BUDGET[k] for k in BUDGET)
        s = stats_for(levels)
        print(f'  {label:36s} attack {100*(attack_score(s)/base_a-1):+5.2f}%  defense {100*(defense_score(s)/base_d-1):+5.2f}%  threads {c["threads"]:,} av {c["av"]:,}  {"ok" if ok else "OVER BUDGET"}')
