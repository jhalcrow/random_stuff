#!/usr/bin/env python3
"""Best four joiner skills for my rally and for my garrison.

A joiner contributes only its FIRST expedition skill (tooltip-verified for Vivian, Ava, Chenko,
Amane, Triton, Alcar, Petra).  The engine sums every skill into one coefficient per CHANNEL --
my damage up, enemy defense down, enemy damage down, my defense up -- and multiplies the
channels (sim._prod, from the reference engine).  So same-channel skills are interchangeable
(Vivian = Ava, Charles = Eric, Triton = Gordon, Chenko = Amane = Margot) and the best set spreads
across the channels my own lineup fills least.  My damage channel is already crowded by Yang's
procs and the troop abilities, which is why damage joiners (Chenko, Amane) rank low.

Search: every multiset of four from nine skill types, Monte Carlo (procs rolled), rally
Charles/Ava/Yang 45/30/25 and garrison Charles/Sophia/Wee & Woo 60/15/25 -- the Elo-best lineups --
1.9M vs 1.9M against gear.py's opposing lineups at 90% of my stats.  The deterministic engine
over-rates Alcar: his -70% fires two turns in five, so two Alcars fire on the same turns.

Result (2026-10-08, 400 runs per opposing lineup):
    Vivian, Ava, Charles, Triton       rally 1.655   garrison 3.022   <- best in BOTH
    Vivian, Petra, Eric, Triton        rally 1.645   garrison 2.988   (no duplicate of my leaders)
    Triton, Ava, Alcar, Petra          rally 1.483   garrison 2.786   (old DEFENSE_JOINERS)
    Vivian, Ava, Chenko, Amane         rally 1.402   garrison 2.686   (old ATTACK_JOINERS)
    Chenko x4                          rally 1.181   garrison 2.190
ASSUMES joiner skills at level 5 and that a joiner's skill stacks with the same skill on the
leader's hero.  Joiners and parity rallies are the least-validated part of the simulator.

  python3 kingshot/joiners.py [N]          # N runs per opposing lineup, default 150
"""
import math, os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gear
from sim import Side, USER_STATS, battle_mc, ratio_troops, score, ATTACK_JOINERS, DEFENSE_JOINERS

R, ENEMY = gear.RALLY, gear.enemy
SETS = [['Vivian', 'Ava', 'Charles', 'Triton'], ['Vivian', 'Petra', 'Eric', 'Triton'],
        ['Vivian', 'Ava', 'Petra', 'Charles'], ['Triton', 'Ava', 'Alcar', 'Petra'],
        ['Vivian', 'Ava', 'Chenko', 'Amane'], ['Chenko'] * 4, []]


def rally(j, n, rng):
    out = []
    for dl in gear.DEF_PANEL:
        for _ in range(n):
            r = battle_mc(Side('A', USER_STATS, ratio_troops(R, 45, 30, 25), heroes=['Charles', 'Ava', 'Yang'],
                               role='rally', joiners=list(j)),
                          Side('D', ENEMY, ratio_troops(R, 60, 15, 25), heroes=dl, role='garrison',
                               joiners=DEFENSE_JOINERS), rng)
            out.append(math.log(score(r, 'A')))
    return math.exp(statistics.mean(out))


def garrison(j, n, rng):
    out = []
    for al in gear.ATT_PANEL:
        ar = (55, 45, 0) if 'Sophia' in al else (50, 20, 30)
        for _ in range(n):
            r = battle_mc(Side('A', ENEMY, ratio_troops(R, *ar), heroes=al, role='rally', joiners=ATTACK_JOINERS),
                          Side('D', USER_STATS, ratio_troops(R, 60, 15, 25), heroes=['Charles', 'Sophia', 'Wee & Woo'],
                               role='garrison', joiners=list(j)), rng)
            out.append(math.log(score(r, 'D')))
    return math.exp(statistics.mean(out))


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    print(f"{'joiners':34s}{'rally':>8s}{'garrison':>10s}")
    for j in SETS:
        print(f"  {', '.join(j) or 'none':32s}{rally(j, n, random.Random(77)):8.3f}{garrison(j, n, random.Random(77)):10.3f}")
