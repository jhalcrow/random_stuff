#!/usr/bin/env python3
"""Monte Carlo round-robin: top attack lineups (rally leaders + attack joiners) vs top garrison
lineups (garrison leaders + defensive reinforcement skills), all on mirror stats.  Every pairing
is fought N times with chance skills rolled each round; ratings are fitted by Bradley-Terry
maximum likelihood on the win matrix and reported on the Elo scale (400 * log10 of the strength
ratio, centred so the mean is 1500).

  python3 kingshot/elo.py [N]      # default N = 300 battles per pairing
"""
import math, os, random, sys
from sim import (Side, USER_STATS, MARCH, TYPES, battle_mc, ratio_troops, score,
                 ATTACK_JOINERS, DEFENSE_JOINERS)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
SIZE = int(os.environ.get('RALLY_SIZE', MARCH))          # troops per side
ATT_SCALE = float(os.environ.get('ATT_SCALE', '1.0'))    # attacker stats relative to yours
DEF_SCALE = float(os.environ.get('DEF_SCALE', '1.0'))    # defender stats relative to yours
rng = random.Random(2026)

ATTACKERS = [
    ('Charles / Ava / Wee & Woo  40/35/25', ['Charles', 'Ava', 'Wee & Woo'], (40, 35, 25)),
    ('Charles / Ava / Yang  45/30/25', ['Charles', 'Ava', 'Yang'], (45, 30, 25)),
    ('Charles / Sophia / Wee & Woo  55/45/0', ['Charles', 'Sophia', 'Wee & Woo'], (55, 45, 0)),
    ('Charles / Sophia / Yang  60/40/0', ['Charles', 'Sophia', 'Yang'], (60, 40, 0)),
    ('Charles / Sophia / Marlin  55/45/0', ['Charles', 'Sophia', 'Marlin'], (55, 45, 0)),
    ('Amadeus / Ava / Wee & Woo  50/20/30', ['Amadeus', 'Ava', 'Wee & Woo'], (50, 20, 30)),
    ('Triton / Thrud / Yang  50/20/30', ['Triton', 'Thrud', 'Yang'], (50, 20, 30)),
]
DEFENDERS = [
    ('Charles / Sophia / Wee & Woo  35/65/0', ['Charles', 'Sophia', 'Wee & Woo'], (35, 65, 0)),
    ('Charles / Sophia / Wee & Woo  60/15/25', ['Charles', 'Sophia', 'Wee & Woo'], (60, 15, 25)),
    ('Charles / Ava / Wee & Woo  35/25/40', ['Charles', 'Ava', 'Wee & Woo'], (35, 25, 40)),
    ('Alcar / Sophia / Wee & Woo  40/60/0', ['Alcar', 'Sophia', 'Wee & Woo'], (40, 60, 0)),
    ('Long Fei / Sophia / Wee & Woo  40/60/0', ['Long Fei', 'Sophia', 'Wee & Woo'], (40, 60, 0)),
    ('Charles / Jabel / Wee & Woo  60/15/25', ['Charles', 'Jabel', 'Wee & Woo'], (60, 15, 25)),
    ('Triton / Sophia / Vivian  60/15/25', ['Triton', 'Sophia', 'Vivian'], (60, 15, 25)),
]


def fight(att, dfn):
    sa = {t: {k: v * ATT_SCALE for k, v in USER_STATS[t].items()} for t in TYPES}
    sd = {t: {k: v * DEF_SCALE for k, v in USER_STATS[t].items()} for t in TYPES}
    a = Side('A', sa, ratio_troops(SIZE, *att[2]), heroes=att[1], role='rally', joiners=ATTACK_JOINERS)
    d = Side('D', sd, ratio_troops(SIZE, *dfn[2]), heroes=dfn[1], role='garrison', joiners=DEFENSE_JOINERS)
    wins = draws = 0
    ratios = []
    for _ in range(N):
        r = battle_mc(a, d, rng)
        if r['winner'] == 'A':
            wins += 1
        elif r['winner'] == 'draw':
            draws += 1
        ratios.append(score(r, 'A'))
    ratios.sort()
    return wins, draws, sum(ratios) / N, ratios[N // 10], ratios[9 * N // 10]


def bradley_terry(players, games, iters=2000):
    """games: list of (i, j, score_i in [0,1]).  Returns log-strengths, mean 0."""
    s = [0.0] * len(players)
    for _ in range(iters):
        grad = [0.0] * len(players)
        for i, j, sc in games:
            p = 1 / (1 + math.exp(s[j] - s[i]))
            grad[i] += sc - p
            grad[j] -= sc - p
        for k in range(len(players)):
            s[k] += 0.05 * grad[k] / max(1, sum(1 for g in games if k in g[:2]))
        m = sum(s) / len(s)
        s = [x - m for x in s]
    return s


if __name__ == '__main__':
    print(f'{N} Monte Carlo battles per pairing, {SIZE:,} troops each side, attacker stats x{ATT_SCALE}, defender stats x{DEF_SCALE}\n')
    names = [a[0] for a in ATTACKERS] + [d[0] for d in DEFENDERS]
    games = []
    table = {}
    for ai, att in enumerate(ATTACKERS):
        for di, dfn in enumerate(DEFENDERS):
            w, dr, mean_ratio, p10, p90 = fight(att, dfn)
            table[(ai, di)] = (w, dr, mean_ratio, p10, p90)
            games.append((ai, len(ATTACKERS) + di, (w + 0.5 * dr) / N))
    # win-rate matrix
    print('Attacker win rate (%) vs each garrison:')
    print(' ' * 40 + ' '.join(f'D{di+1:<5d}' for di in range(len(DEFENDERS))) + '  mean')
    for ai, att in enumerate(ATTACKERS):
        row = [table[(ai, di)][0] / N * 100 for di in range(len(DEFENDERS))]
        print(f'  {att[0]:38s}' + ' '.join(f'{x:5.1f} ' for x in row) + f' {sum(row)/len(row):5.1f}')
    print('\nGarrisons: ' + '; '.join(f'D{di+1}={d[0]}' for di, d in enumerate(DEFENDERS)))
    print('\nAttacker kill ratio (mean, 10th-90th percentile) vs each garrison:')
    for ai, att in enumerate(ATTACKERS):
        cells = [f'{table[(ai, di)][2]:4.2f}[{table[(ai, di)][3]:4.2f}-{table[(ai, di)][4]:4.2f}]' for di in range(len(DEFENDERS))]
        print(f'  {att[0]:38s} ' + ' '.join(cells))

    s = bradley_terry(names, games)
    elo = [1500 + 400 * x / math.log(10) for x in s]
    print('\nElo (Bradley-Terry fit, 1500 = average of all 14 lineups):')
    rows = sorted(zip(elo, names), reverse=True)
    for e, n in rows:
        side = 'ATTACK ' if n in [a[0] for a in ATTACKERS] else 'DEFENSE'
        print(f'  {e:7.0f}  {side}  {n}')
    print('\nAttack side only:')
    for e, n in rows:
        if n in [a[0] for a in ATTACKERS]:
            print(f'  {e:7.0f}  {n}')
    print('Defense side only:')
    for e, n in rows:
        if n in [d[0] for d in DEFENDERS]:
            print(f'  {e:7.0f}  {n}')
