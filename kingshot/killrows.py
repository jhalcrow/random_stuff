#!/usr/bin/env python3
"""Score the Battle Details KILLS column -- the per-skill kill counts -- against the engine.

Every number the game labels "kills" counts only the INJURED bucket, 35.0% of casualties (the
skull on the summary line and the Kills column alike; Terry's defence report: skull 3,408 =
0.35 x his 9,734 casualties).  So a damage skill's row should read 0.35 x the casualties the
engine attributes to it.

Attribution: skills combine additively into one coefficient per channel (sim._prod), so a live
damage skill with coefficient c, alongside total C, is credited dead x c / (1 + C) of each strike.

What it shows (2026-10-07): the troop-ability strikes -- Assault Lance (cavalry, +100%) and
Howling Wind (archers, +50%) -- land within ~10% of the engine per trigger in the heroless and
Yang fights.  Those strikes ARE base cavalry and archer damage, so this checks the damage core,
front-line targeting and the sqrt(n x army_min) term at the level of a single strike, which no
loss total can.  Yang's Ice Zone (0.59 per trigger) and Avalanche (0.80) are over-modelled per
strike but fire more often than modelled, and their totals land.

  python3 kingshot/killrows.py
"""
import collections, inspect, os, random, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim, battles, allfights
from sim import Side, DMG_UP

INJURED_SHARE = 1 / 2.855
ATTR, TRIG = collections.Counter(), collections.Counter()


def _attr(src, a, u, u_effs, dead):
    side = 'mine' if src is a else 'his'
    c = [(v, nm) for kind, v, scope, nm in u_effs if kind in DMG_UP and scope in ('all', u)]
    tot = 1 + sum(v for v, _ in c) / 100
    for v, nm in c:
        ATTR[(side, nm.split(':', 1)[1])] += dead * (v / 100) / tot


def _trig(ae, de, pae, pde):
    for side, effs in (('mine', ae), ('his', de)):
        for nm in {e[3].split(':', 1)[1] for e in effs}:
            TRIG[(side, nm)] += 1
    for side, d in (('mine', pae), ('his', pde)):
        for effs in d.values():
            for nm in {e[3].split(':', 1)[1] for e in effs}:
                TRIG[(side, nm)] += 1


# An instrumented copy of the real battle_mc, built from its source so it cannot drift from it.
_src = inspect.getsource(sim.battle_mc).replace('def battle_mc(', 'def _battle_mc_diag(')
_src = _src.replace("            ta = next((v for v in TYPES if nd[v] > 0), None)",
                    "            _trig(ae, de, pae, pde)\n            ta = next((v for v in TYPES if nd[v] > 0), None)")
_src = _src.replace("                        if ROUND_MODE == 'stochastic':",
                    "                        _attr(src, a, u, u_effs, dead)\n                        if ROUND_MODE == 'stochastic':")
_ns = dict(vars(sim)); _ns.update(_attr=_attr, _trig=_trig)
exec(_src, _ns)
battle_mc_diag = _ns['_battle_mc_diag']

LABELS = {'1000 NO HEROES': 'Narses 1000 NO HEROES', '500 NO HEROES': 'Narses 500 NO HEROES',
          '500 YANG ONLY': 'Narses 500 YANG ONLY', '500 CHARLES ONLY': 'Narses 500 CHARLES ONLY',
          '500 SOPHIA ONLY': 'Narses 500 SOPHIA ONLY', '500 SOPHIA 100/250/150': 'Narses 500 SOPHIA 100/250/150',
          '1000 SOPHIA no cavalry': 'Narses 1000 SOPHIA no cav', '500 CHARLES+SOPHIA': 'Narses 500 CHARLES+SOPHIA',
          '500 vs NARSES + LONG FEI': 'Narses 500 + LONG FEI', '500 TRIO vs TRIO': 'Narses 500 TRIO vs TRIO'}


def run(lbl, n=200, seed=7):
    ATTR.clear(); TRIG.clear()
    rng = random.Random(seed)
    _, mp, mt, mr, ep, et, tier, etg, eh, side, obs = next(f for f in allfights.FIGHTS if f[0] == lbl)
    for _ in range(n):
        a = Side('A', mp, dict(mt), heroes=allfights.MY_HEROES.get(lbl, allfights.DEFAULT_MY_HEROES),
                 role=mr, joiners=[], hero_stats=False, tier=11, tg=8, widget_default=0.0)
        d = Side('D', ep, dict(et), heroes=eh, role='garrison', joiners=[], hero_stats=False,
                 tier=tier, tg=etg, widget_default=0.0,
                 troop_abilities=allfights.ENEMY_TROOP_ABILITIES.get(lbl, {}),
                 troop_reforges=set(), skill_levels=allfights.NARSES_LEVELS)
        battle_mc_diag(a, d, rng)
    return {k: v / n for k, v in ATTR.items()}, {k: v / n for k, v in TRIG.items()}


def main():
    by = collections.defaultdict(list)
    print(f"{'fight':26s}{'skill':18s}{'obs/trig':>9s}{'sim/trig':>9s}{'ratio':>7s}   (sim x 0.35)")
    for b in battles.BATTLES:
        attr, trig = run(LABELS[b['label']])
        for who in ('mine', 'his'):
            for name, t_obs, k_obs in b['rows'][who]:
                k_sim, t_sim = attr.get((who, name)), trig.get((who, name))
                if k_obs and k_sim and t_sim:
                    o, s = k_obs / t_obs, INJURED_SHARE * k_sim / t_sim
                    by[name].append(o / s)
                    print(f"  {b['label'][:24]:24s}{name:18s}{o:9.1f}{s:9.1f}{o / s:7.2f}")
    print()
    for k, v in by.items():
        print(f"  {k:18s} n={len(v)}  median ratio {statistics.median(v):.2f}  range {min(v):.2f}-{max(v):.2f}")


if __name__ == '__main__':
    main()
