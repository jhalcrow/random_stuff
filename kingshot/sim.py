#!/usr/bin/env python3
"""Kingshot battle simulator (State of Survival engine model).

Engine (from the open-source SoS simulator and kingshotguides.com's reverse engineering):

  per-troop attack   A_u = base_attack * (1 + atk%) * base_leth * (1 + leth%) / 100
  per-troop defense  D_v = base_health * (1 + hp%) * base_def * (1 + def%) / 100
  each round, every troop type u on each side hits the FIRST living enemy type in the order
  infantry -> cavalry -> archers, killing
      ceil( sqrt(n_u * army_min) * A_u / D_v / 100 * SkillMod(u, v) )
  where army_min = min(total attacker troops, total defender troops) fixed at battle start.
  Both sides act simultaneously off the previous round's counts.  Battle ends when a side is
  empty (or max_rounds).

  SkillMod = DamageUp * OppDefenseDown / (OppDamageDown * DefenseUp), each factor the product
  over distinct effect ops of (1 + v/100); skills of the same op (e.g. two Chenko joiners, or
  Amadeus' +25% Lethality next to Chenko's) add before the (1 + v) is formed.

Special Bonuses (widgets, city buffs, appointments) multiply (100 + stat%) once after summing.

Usage: python3 kingshot/sim.py            # runs the report for the stats in USER below
"""
import itertools, json, math, os, sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(__file__))
from heroes import HEROES, LEGENDARIES, EPICS, ATTACK_JOINERS, DEFENSE_JOINERS

TYPES = ('inf', 'cav', 'arch')
_TNAME = {'inf': 'infantry', 'cav': 'cavalry', 'arch': 'archers'}
_BASE = json.load(open(os.path.join(os.path.dirname(__file__), 'troops_base.json')))
TG_STEP = 1.05   # the table covers TG0-5; TG6-8 extrapolated at the table's own ~5%/level
PROC_SCALE = float(os.environ.get('PROC_SCALE', '1.0'))   # discount applied to chance-based skill EVs


def base_stats(ttype, tier=10, tg=8):
    """(attack, defense, lethality, health) hidden base stats for a troop type/tier/TG level."""
    k = f'{_TNAME[ttype]}|{tier}|{min(tg, 5)}'
    a, d, l, h = _BASE[k]
    extra = TG_STEP ** max(0, tg - 5)
    return a * extra, d, l, h * extra


# ---------------------------------------------------------------- your account
# Bonus Overview screenshot (2026-09-07).  "Squads'" bonuses apply to every troop type and add
# to the type-specific line, e.g. total infantry attack = 554.1 + 466.2.
SQUADS = dict(attack=554.1, defense=537.0, lethality=121.7, health=116.9)
USER_TYPE = {
    'inf':  dict(attack=466.2, defense=468.6, lethality=830.7, health=828.7),
    'cav':  dict(attack=444.3, defense=444.3, lethality=777.4, health=785.1),
    'arch': dict(attack=447.0, defense=447.0, lethality=795.9, health=796.3),
}
USER_STATS = {t: {k: SQUADS[k] + USER_TYPE[t][k] for k in SQUADS} for t in TYPES}
MARCH = 144_200          # Deployment Capacity from the Bonus Overview
WEAPON_BONUS = 62.5      # maxed exclusive weapon: +62.5% Lethality and Health to the hero's troop type


@dataclass
class Side:
    name: str
    stats: dict                                  # {type: {attack, defense, lethality, health}} in %
    troops: dict                                 # {type: count}
    heroes: list = field(default_factory=list)   # 3 lineup heroes
    role: str = 'solo'                           # 'rally' (initiating), 'garrison', 'solo'
    joiners: list = field(default_factory=list)  # joiner heroes; only their first skill counts
    tier: int = 10
    tg: int = 8
    special: dict = field(default_factory=dict)  # extra special bonus % per stat (pets, city, appointments)
    weapon_bonus: float = WEAPON_BONUS
    triangle: float = 10.0                       # innate counter bonus % (archers>infantry etc.)
    ambusher: float = 0.20                       # cavalry chance to bypass the front line and hit archers

    # ---- derived
    def effects(self):
        """List of (kind, value, scope, op_id) from lineup skills + joiner first skills."""
        out = []
        for h in self.heroes:
            for i, (sname, effs) in enumerate(HEROES[h]['skills']):
                for kind, v, scope in effs:
                    out.append((kind, v, scope, f'{h}:{sname}'))
        for h in self.joiners:
            sname, effs = HEROES[h]['skills'][0]
            for kind, v, scope in effs:
                out.append((kind, v, scope, f'{h}:{sname}'))
        return out

    def special_bonus(self):
        sp = {k: 0.0 for k in ('attack', 'defense', 'lethality', 'health')}
        for k, v in self.special.items():
            sp[k] += v
        for h in self.heroes:
            w = HEROES[h]['widget']
            if w and ((w[0] == 'rally' and self.role == 'rally') or (w[0] == 'defender' and self.role == 'garrison')):
                sp[w[1]] += w[2]
        return sp

    def stat(self, ttype, key):
        s = self.stats[ttype][key]
        if key in ('lethality', 'health'):
            s += self.weapon_bonus * sum(1 for h in self.heroes if HEROES[h]['type'] == ttype)
        return (100 + s) * (1 + self.special_bonus()[key] / 100) / 100   # multiplier form


DMG_UP = ('leth', 'atk', 'dmg', 'proc')
DEF_UP = ('def', 'hp')
TAKEN = ('taken', 'proc_taken')
OPP_DMG_DOWN = ('e_atk', 'e_leth', 'e_dmg', 'proc_e_dmg')
OPP_DEF_DOWN = ('e_taken', 'e_def', 'proc_e_taken')


def _prod(effs, kinds, scope_ok, sign=+1):
    """Multiply (1 +/- sum/100) over distinct ops.  Op = kind (stat category) for flat skills,
    or the skill name for chance-based (proc_) skills, so procs always multiply."""
    by_op = {}
    for kind, v, scope, name in effs:
        if kind in kinds and scope_ok(scope):
            op = name if kind.startswith('proc') else ('atk' if kind == 'dmg' else kind)
            if kind.startswith('proc'):
                v *= PROC_SCALE
            by_op[op] = by_op.get(op, 0) + v
    m = 1.0
    for v in by_op.values():
        m *= (1 + sign * v / 100)
    return m


def skill_mod(att, att_effs, u, dfn, def_effs, v):
    """SkillMod = DamageUp * OppDefenseDown / (OppDamageDown * DefenseUp) for attacker type u
    hitting defender type v.  Every factor is prod over ops of (1 + summed value/100); the
    defender's factors sit in the denominator (kingshotguides.com / Absy Labs form)."""
    dmg_up = _prod(att_effs, DMG_UP, lambda s: s in ('all', u))
    opp_def_down = _prod(att_effs, OPP_DEF_DOWN, lambda s: s in ('all', v))
    opp_dmg_down = _prod(def_effs, OPP_DMG_DOWN, lambda s: s in ('all', u))
    def_up = _prod(def_effs, TAKEN + DEF_UP, lambda s: s in ('all', v))
    tri = 1.0
    if (u, v) in (('arch', 'inf'), ('inf', 'cav'), ('cav', 'arch')):
        tri = 1 + att.triangle / 100
    return dmg_up * opp_def_down / (opp_dmg_down * def_up) * tri


def battle(a: Side, d: Side, max_rounds=5000, wear=0.0, verbose=False):
    """Simulate a to the end. Returns dict with losses and winner."""
    A = {}
    D = {}
    for s in (a, d):
        for t in TYPES:
            ba, bd, bl, bh = base_stats(t, s.tier, s.tg)
            A[(s.name, t)] = ba * s.stat(t, 'attack') * bl * s.stat(t, 'lethality') / 100
            D[(s.name, t)] = bh * s.stat(t, 'health') * bd * s.stat(t, 'defense') / 100
    ae, de = a.effects(), d.effects()
    mods = {(u, v): skill_mod(a, ae, u, d, de, v) for u in TYPES for v in TYPES}
    modd = {(u, v): skill_mod(d, de, u, a, ae, v) for u in TYPES for v in TYPES}
    na = dict(a.troops); nd = dict(d.troops)
    army_min = min(sum(na.values()), sum(nd.values()))
    rnd = 0
    while rnd < max_rounds and sum(na.values()) > 0 and sum(nd.values()) > 0:
        rnd += 1
        kills_on_d = {t: 0.0 for t in TYPES}
        kills_on_a = {t: 0.0 for t in TYPES}
        for (src, n_src, n_tgt, Aa, Dd, mm, kills) in (
                (a, na, nd, A, D, mods, kills_on_d), (d, nd, na, A, D, modd, kills_on_a)):
            tgt_name = d.name if src is a else a.name
            target = next((v for v in TYPES if n_tgt[v] > 0), None)
            if target is None:
                continue
            army_sqrt = math.sqrt(army_min)
            for u in TYPES:
                if n_src[u] <= 0:
                    continue
                army = math.sqrt(n_src[u]) * army_sqrt
                shares = [(target, 1.0)]
                if u == 'cav' and target != 'arch' and n_tgt['arch'] > 0 and src.ambusher > 0:
                    shares = [(target, 1 - src.ambusher), ('arch', src.ambusher)]
                for tgt, share in shares:
                    dead = share * army * Aa[(src.name, u)] / Dd[(tgt_name, tgt)] / 100 * mm[(u, tgt)]
                    dead -= dead * wear * rnd
                    kills[tgt] += math.ceil(dead)
        for t in TYPES:
            nd[t] = max(0, nd[t] - kills_on_d[t])
            na[t] = max(0, na[t] - kills_on_a[t])
        if verbose and rnd <= 3:
            print(rnd, na, nd)
    a_lost = sum(a.troops.values()) - sum(na.values())
    d_lost = sum(d.troops.values()) - sum(nd.values())
    return dict(rounds=rnd, a_lost=a_lost, d_lost=d_lost, a_left=na, d_left=nd,
                winner=(a.name if sum(nd.values()) == 0 and sum(na.values()) > 0 else
                        d.name if sum(na.values()) == 0 else 'draw'))


def ratio_troops(total, inf, cav, arch):
    s = inf + cav + arch
    return {'inf': int(total * inf / s), 'cav': int(total * cav / s), 'arch': total - int(total * inf / s) - int(total * cav / s)}


# ---------------------------------------------------------------- scoring helpers
def score(res, me):
    """Kill ratio, with win/loss sign. >1 means you trade favourably."""
    mine = res['a_lost'] if me == 'A' else res['d_lost']
    theirs = res['d_lost'] if me == 'A' else res['a_lost']
    return theirs / max(mine, 1)


def bear_check():
    """Reproduce kingshotguides.com's worked Bear Trap example: expected 16,797 damage."""
    stats = {t: dict(attack=25, defense=0, lethality=0, health=0) for t in TYPES}
    me = Side('me', stats, {'inf': 6000, 'cav': 6000, 'arch': 6000}, tier=6, tg=0, weapon_bonus=0)
    total = 0.0
    army_min = 5000
    for t in TYPES:
        ba, bd, bl, bh = base_stats(t, 6, 0)
        A = ba * 1.25 * bl / 100
        Dbear = 83.3333 * 10 / 100
        dmg = math.sqrt(6000 * army_min) * A / Dbear / 100
        if t == 'arch':
            dmg *= 1.10
        total += dmg
    return math.ceil(total * 10)


if __name__ == '__main__':
    print('Bear Trap check (expect 16797):', bear_check())
