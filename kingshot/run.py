#!/usr/bin/env python3
"""Rank hero trios and troop ratios for castle attack and garrison defense.

  python3 kingshot/run.py            # full report
  python3 kingshot/run.py --quick    # top lists only

Opponent model: a mirror of your own stats (same Bonus Overview numbers, same troop tier),
evaluated against a PANEL of meta enemy lineups so no single enemy choice drives the result.
Scores are kill ratios (enemy troops lost / your troops lost) averaged over the panel.
"""
import itertools, sys, statistics
from sim import (Side, USER_STATS, MARCH, TYPES, battle, ratio_troops, score, HEROES,
                 LEGENDARIES, EPICS, ATTACK_JOINERS, DEFENSE_JOINERS)
from heroes import trios

QUICK = '--quick' in sys.argv
TRIOS = trios()          # one infantry + one cavalry + one archer (the game's march rule)

# Enemy garrison lineups you may run into when attacking (meta defensive trios).
DEF_PANEL = [
    ['Charles', 'Sophia', 'Wee & Woo'],
    ['Alcar', 'Margot', 'Vivian'],
    ['Triton', 'Sophia', 'Vivian'],
    ['Charles', 'Margot', 'Wee & Woo'],
]
# Enemy rally leaders you may be attacked by (meta offensive trios).
ATT_PANEL = [
    ['Amadeus', 'Ava', 'Yang'],
    ['Triton', 'Thrud', 'Yang'],
    ['Charles', 'Ava', 'Wee & Woo'],
    ['Alcar', 'Thrud', 'Rosa'],
]
ENEMY_DEF_RATIO = (60, 15, 25)
ENEMY_ATT_RATIO = (50, 20, 30)
MY_RATIO = (50, 20, 30)


def enemy_stats(scale=1.0):
    return {t: {k: v * scale for k, v in USER_STATS[t].items()} for t in TYPES}


def eval_attack(trio, ratio=MY_RATIO, role='rally', joiners=ATTACK_JOINERS, scale=1.0, n=MARCH):
    res = []
    for dl in DEF_PANEL:
        me = Side('me', USER_STATS, ratio_troops(n, *ratio), heroes=list(trio), role=role,
                  joiners=joiners if role == 'rally' else [])
        en = Side('enemy', enemy_stats(scale), ratio_troops(n, *ENEMY_DEF_RATIO), heroes=dl,
                  role='garrison', joiners=DEFENSE_JOINERS)
        r = battle(me, en)
        res.append((score(r, 'A'), r['winner'] == 'me', r['a_lost'], r['d_lost']))
    return res


def eval_defense(trio, ratio=(60, 15, 25), joiners=DEFENSE_JOINERS, scale=1.0, n=MARCH):
    res = []
    for al in ATT_PANEL:
        en = Side('enemy', enemy_stats(scale), ratio_troops(n, *ENEMY_ATT_RATIO), heroes=al,
                  role='rally', joiners=ATTACK_JOINERS)
        me = Side('me', USER_STATS, ratio_troops(n, *ratio), heroes=list(trio), role='garrison',
                  joiners=joiners)
        r = battle(en, me)
        res.append((score(r, 'D'), r['winner'] == 'me', r['d_lost'], r['a_lost']))
    return res


def summarize(res):
    return statistics.geometric_mean([max(x[0], 1e-6) for x in res]), sum(1 for x in res if x[1])


def rank(evalfn, label, **kw):
    rows = []
    for trio in TRIOS:
        g, wins = summarize(evalfn(trio, **kw))
        rows.append((g, wins, trio))
    rows.sort(reverse=True)
    print(f'\n=== {label}: top trios (kill ratio = enemy lost / yours lost, geometric mean over '
          f'{len(DEF_PANEL)} enemy lineups) ===')
    for g, wins, trio in rows[:15]:
        print(f'  {g:6.3f}  wins {wins}/4  {", ".join(trio)}')
    # marginal value per hero: mean score of trios containing the hero, over the top 300
    top = rows[:300]
    per = {}
    for g, wins, trio in rows:
        for h in trio:
            per.setdefault(h, []).append(g)
    print(f'  --- average score of every trio containing each hero ---')
    for h, v in sorted(per.items(), key=lambda kv: -statistics.mean(kv[1]))[:12]:
        print(f'  {statistics.mean(v):6.3f}  {h}')
    return rows


def ratio_search(evalfn, trio, label, **kw):
    best = []
    for inf in range(0, 101, 5):
        for cav in range(0, 101 - inf, 5):
            arch = 100 - inf - cav
            g, wins = summarize(evalfn(trio, ratio=(inf, cav, arch), **kw))
            best.append((g, wins, (inf, cav, arch)))
    best.sort(reverse=True)
    print(f'\n=== {label}: troop ratio for {", ".join(trio)} (inf/cav/arch) ===')
    for g, wins, r in best[:10]:
        print(f'  {g:6.3f}  wins {wins}/4  {r[0]}/{r[1]}/{r[2]}')
    for r in [(50, 20, 30), (60, 15, 25), (70, 30, 0), (34, 33, 33), (10, 10, 80)]:
        g, wins = summarize(evalfn(trio, ratio=r, **kw))
        print(f'  ref {g:6.3f}  wins {wins}/4  {r[0]}/{r[1]}/{r[2]}')
    return best[0][2]


if __name__ == '__main__':
    print('Your effective stats (Squads + type):')
    for t in TYPES:
        print('  ', t, {k: round(v, 1) for k, v in USER_STATS[t].items()})

    att = rank(eval_attack, 'CASTLE ATTACK as rally leader (rally widgets + 4 joiner skills)')
    solo = rank(eval_attack, 'CASTLE ATTACK solo march (no widgets, no joiners)', role='solo')
    dfn = rank(eval_defense, 'GARRISON DEFENSE as garrison leader (defender widgets + 4 reinforcement skills)')

    if not QUICK:
        best_att = att[0][2]
        best_def = dfn[0][2]
        ratio_search(eval_attack, best_att, 'CASTLE ATTACK rally')
        ratio_search(eval_defense, best_def, 'GARRISON DEFENSE')
        print('\n=== sensitivity: enemy stats x0.8 / x1.2 (top-5 attack trios) ===')
        for g, wins, trio in att[:5]:
            lo, wl = summarize(eval_attack(trio, scale=0.8))
            hi, wh = summarize(eval_attack(trio, scale=1.2))
            print(f'  {", ".join(trio):40s} weak enemy {lo:6.3f} ({wl}/4)  strong enemy {hi:6.3f} ({wh}/4)')
        print('\n=== sensitivity: enemy stats x0.8 / x1.2 (top-5 defense trios) ===')
        for g, wins, trio in dfn[:5]:
            lo, wl = summarize(eval_defense(trio, scale=0.8))
            hi, wh = summarize(eval_defense(trio, scale=1.2))
            print(f'  {", ".join(trio):40s} weak enemy {lo:6.3f} ({wl}/4)  strong enemy {hi:6.3f} ({wh}/4)')
