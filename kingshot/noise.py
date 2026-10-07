#!/usr/bin/env python3
"""Is the calibration error bigger than the game's own luck?

For every scored fight, run the engine 300 times and take the spread of log(observable) as the
luck a single real battle carries; then express each fight's miss in those units (z).  If the
engine were perfect, the misses would look like luck: mean z^2 ~ 1 and ~5% of fights beyond |z| 2.

The engine's RNG stands in for the game's.  The one direct check: two identical solo attacks in
reports.py differed by CV 8.8% on n=2 against the engine's 7.6% for that configuration.

Result (2026-10-07, 21 fights): rms miss 0.155 against rms luck 0.147 -- model error beyond luck
about 0.05 overall -- but concentrated: 4 fights beyond |z| 2 against ~1 expected, three of them
marches missing a troop type (Terry and Narses pure infantry, z +5.1 each; Sophia no-cavalry,
-3.1).  The other 17 have mean z^2 0.68: indistinguishable from luck.

  python3 kingshot/noise.py
"""
import math, os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import Side, battle_mc
import allfights as af


def main(n=300):
    rows = []
    for lbl, mp, mt, mr, ep, et, tier, etg, eh, side, obs in af.FIGHTS:
        rng = random.Random(2024); vals = []
        narses = lbl in af.ENEMY_NO_REFORGE
        for _ in range(n):
            a = Side('A', mp, dict(mt), heroes=af.MY_HEROES.get(lbl, af.DEFAULT_MY_HEROES), role=mr,
                     joiners=[], hero_stats=False, tier=11, tg=8, widget_default=af.MY_WIDGETS.get(lbl, 0.0))
            d = Side('D', ep, dict(et), heroes=eh, role=('solo' if mr == 'garrison' else 'garrison'),
                     joiners=[], hero_stats=False, tier=tier, tg=etg, widget_default=0.0,
                     troop_abilities=af.ENEMY_TROOP_ABILITIES.get(lbl, {}),
                     troop_reforges=(set() if narses else None),
                     skill_levels=(af.NARSES_LEVELS if narses else {}))
            if mr == 'garrison':
                r = battle_mc(d, a, rng); vals.append(r['d_lost'] if side == 'me' else r['a_lost'])
            else:
                r = battle_mc(a, d, rng); vals.append(r['a_lost'] if side == 'me' else r['d_lost'])
        lv = [math.log(max(v, 1)) for v in vals]
        mu, sd = statistics.mean(lv), statistics.pstdev(lv)
        rows.append((lbl, obs, sd, mu - math.log(obs)))
    print(f"{'fight':32s}{'obs':>8s}{'luck sd':>9s}{'miss':>8s}{'z':>7s}")
    for lbl, obs, sd, miss in rows:
        print(f"  {lbl:30s}{obs:8,}{sd:9.2f}{miss:8.2f}{miss / sd:7.1f}")
    N = len(rows)
    rms_m = math.sqrt(sum(r[3] ** 2 for r in rows) / N)
    rms_s = math.sqrt(sum(r[2] ** 2 for r in rows) / N)
    print(f"\n  rms miss {rms_m:.3f}   rms luck {rms_s:.3f}   mean z^2 {sum((r[3]/r[2])**2 for r in rows)/N:.2f}"
          f"   model error beyond luck {math.sqrt(max(0, rms_m**2 - rms_s**2)):.3f}"
          f"   |z|>2: {sum(abs(r[3]/r[2]) > 2 for r in rows)} of {N}")


if __name__ == '__main__':
    main()
