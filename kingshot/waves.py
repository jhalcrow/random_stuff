#!/usr/bin/env python3
"""Consecutive rallies against one garrison with no refill between hits.

Each wave is a fresh rally of MARCH troops led by the attacker lineup with the attack joiners.
The garrison starts at MARCH troops in its ratio; whatever survives a wave (per troop type)
fights the next wave.  Reports the probability of holding through 1, 2 and 3 waves, expected
attacker losses inflicted, and expected garrison remaining after 3 waves.

  python3 kingshot/waves.py [N] [garrison_size_multiple]     # default 200 runs, garrison = 1 rally
"""
import random, sys, statistics
from sim import (Side, USER_STATS, MARCH, TYPES, battle_mc, ratio_troops,
                 ATTACK_JOINERS, DEFENSE_JOINERS)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
GAR_MULT = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0   # garrison size as a multiple of one rally
WAVES = 3
rng = random.Random(7)

ATTACKERS = [
    ('Charles / Sophia / Marlin 55/45/0', ['Charles', 'Sophia', 'Marlin'], (55, 45, 0)),
    ('Charles / Sophia / Yang 60/40/0', ['Charles', 'Sophia', 'Yang'], (60, 40, 0)),
    ('Charles / Ava / Yang 45/30/25', ['Charles', 'Ava', 'Yang'], (45, 30, 25)),
]
SCALES = [1.0, 0.85]     # attacker stats relative to yours: equal, and a typical weaker rally leader

GARRISONS = [
    ('Charles / Sophia / Wee & Woo 60/15/25', ['Charles', 'Sophia', 'Wee & Woo'], (60, 15, 25)),
    ('Charles / Sophia / Wee & Woo 50/20/30', ['Charles', 'Sophia', 'Wee & Woo'], (50, 20, 30)),
    ('Charles / Sophia / Wee & Woo 35/65/0', ['Charles', 'Sophia', 'Wee & Woo'], (35, 65, 0)),
    ('Charles / Sophia / Wee & Woo 45/35/20', ['Charles', 'Sophia', 'Wee & Woo'], (45, 35, 20)),
    ('Long Fei / Sophia / Wee & Woo 40/60/0', ['Long Fei', 'Sophia', 'Wee & Woo'], (40, 60, 0)),
    ('Alcar / Sophia / Wee & Woo 40/60/0', ['Alcar', 'Sophia', 'Wee & Woo'], (40, 60, 0)),
    ('Triton / Sophia / Vivian 60/15/25', ['Triton', 'Sophia', 'Vivian'], (60, 15, 25)),
    ('Charles / Ava / Wee & Woo 35/25/40', ['Charles', 'Ava', 'Wee & Woo'], (35, 25, 40)),
    ('Charles / Jabel / Wee & Woo 60/15/25', ['Charles', 'Jabel', 'Wee & Woo'], (60, 15, 25)),
]


def run(gar, att, scale):
    stats = {t: {k: v * scale for k, v in USER_STATS[t].items()} for t in TYPES}
    held = [0] * (WAVES + 1)
    att_lost = []
    left = []
    for _ in range(N):
        troops = ratio_troops(int(MARCH * GAR_MULT), *gar[2])
        lost = 0
        w = 0
        while w < WAVES and sum(troops.values()) > 0:
            a = Side('A', stats, ratio_troops(MARCH, *att[2]), heroes=att[1], role='rally', joiners=ATTACK_JOINERS)
            d = Side('D', USER_STATS, dict(troops), heroes=gar[1], role='garrison', joiners=DEFENSE_JOINERS)
            r = battle_mc(a, d, rng)
            lost += r['a_lost']
            troops = {t: int(v) for t, v in r['d_left'].items()}
            if sum(troops.values()) == 0:
                break
            w += 1
        for k in range(1, w + 1):
            held[k] += 1
        att_lost.append(lost)
        left.append(sum(troops.values()))
    return [h / N for h in held], statistics.mean(att_lost), statistics.mean(left)


if __name__ == '__main__':
    print(f'{N} runs per pairing; each wave a fresh {MARCH:,}-troop rally; garrison starts at {int(MARCH*GAR_MULT):,} and is not refilled\n')
    summary = {}
    for scale in SCALES:
        print(f'=== attacker stats x{scale} ===')
        print(f'  {"garrison":40s} ' + ' '.join(f'{a[0][:22]:>22s}' for a in ATTACKERS) + '   mean P(hold 1/2/3)  att lost/run')
        for gar in GARRISONS:
            cells = []
            ph = [[], [], []]
            lost_all = []
            for att in ATTACKERS:
                held, lost, left = run(gar, att, scale)
                cells.append(f'{held[1]*100:3.0f}/{held[2]*100:3.0f}/{held[3]*100:3.0f}%'.rjust(22))
                for i in range(3):
                    ph[i].append(held[i + 1])
                lost_all.append(lost)
            m = [statistics.mean(x) for x in ph]
            summary.setdefault(gar[0], []).append(m)
            print(f'  {gar[0]:40s} ' + ' '.join(cells) + f'   {m[0]*100:3.0f}/{m[1]*100:3.0f}/{m[2]*100:3.0f}%   {statistics.mean(lost_all):9,.0f}')
        print()
    print('Ranking by mean probability of holding 3 consecutive rallies (both attacker strengths):')
    rows = sorted(summary.items(), key=lambda kv: -statistics.mean(m[2] for m in kv[1]))
    for name, ms in rows:
        print(f'  hold3 {statistics.mean(m[2] for m in ms)*100:5.1f}%   hold2 {statistics.mean(m[1] for m in ms)*100:5.1f}%   hold1 {statistics.mean(m[0] for m in ms)*100:5.1f}%   {name}')
