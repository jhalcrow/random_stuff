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
from heroes import (HEROES, LEGENDARIES, EPICS, ATTACK_JOINERS, DEFENSE_JOINERS, PROC_SPEC,
                    proc_uptime, STRIKE, TROOP_SKILLS, PERMANENT)

TYPES = ('inf', 'cav', 'arch')
_TNAME = {'inf': 'infantry', 'cav': 'cavalry', 'arch': 'archers'}
_BASE = json.load(open(os.path.join(os.path.dirname(__file__), 'troops_base.json')))
TG_STEP = 1.05   # the table covers TG0-5; TG6-8 extrapolated at the table's own ~5%/level
PROC_SCALE = float(os.environ.get('PROC_SCALE', '1.0'))   # discount applied to chance-based skill EVs
# The engagement term sqrt(n_u * army_min) was modelled with army_min frozen at battle start.
# If the real engine recomputes it as armies shrink, the losing side's output decays twice over
# (its own count AND army_min fall together) while the winner's decays once -- exactly the
# asymmetry the reports show.  Toggle to test.
ARMY_MIN_LIVE = os.environ.get('ARMY_MIN_LIVE', '0') == '1'
# Engagement term exponents: army = n_u**ENG_A * army_min**ENG_B.  The reverse-engineered form
# is sqrt(n_u * army_min), i.e. 0.5/0.5, which compresses a big army's numerical advantage hard.
# Scanning these is how we test whether that compression is the reason the model runs hot.
ENG_A = float(os.environ.get('ENG_A', '0.5'))
ENG_B = float(os.environ.get('ENG_B', '0.5'))
# Reference engine applies a per-round attrition of 0.01%: dead -= dead * 0.0001 * round.
WEAR = float(os.environ.get('WEAR', '0.0001'))
# Whether a damage skill also grants its troop type an extra enemy target that round.  The
# reference gates that on effectTarget==40 in addition to effect==101; assuming every damage
# skill carries it makes the model far worse, so this defaults off.
STRIKE_CONTINUE = os.environ.get('STRIKE_CONTINUE', '0') == '1'
# Defence skills raise defence as 1/(1 - coef) in the reference, not (1 + coef).
DEF_RECIP = os.environ.get('DEF_RECIP', '1') == '1'
# Global multiplier on every hero skill magnitude.  PROC_SCALE only ever reached battle(), not
# battle_mc(), so it was a dead knob on the Monte Carlo path used for all the report fits; this
# one is applied where the effects are built and therefore reaches both.
SKILL_SCALE = float(os.environ.get('SKILL_SCALE', '1.0'))
TROOP_SKILLS_ON = os.environ.get('TROOP_SKILLS', '1') == '1'
# Per-ability ablation: comma-separated names to disable, for isolating which of the tooltip-
# sourced troop abilities the mixed cells actually want.
TROOP_SKILLS_OFF = {s.strip() for s in os.environ.get('TROOP_SKILLS_OFF', '').split(',') if s.strip()}
# Ambusher as a discrete per-round roll (tooltip wording) rather than a permanent damage split.
AMBUSH_ROLL = os.environ.get('AMBUSH_ROLL', '1') == '1'
# Reference Skill.protect() (effects 801/901): the DEFENDER soaks a share of the incoming dead
# from a pool set at `dead * value/100` once per round and depleted across that round's attacks.
# sim.py has never had this channel.  PROTECT is that share, 0 = off.
PROTECT = float(os.environ.get('PROTECT', '0.0'))
# Rounding of the per-attack kill term.  The reference uses ceil(), correct for a single battle,
# but this file averages hundreds of Monte Carlo runs and ceil() is a systematic upward bias that
# never averages out -- worst in long fights, where a nearly-dead side still books >=1 kill per
# troop type per round for hundreds of rounds.  'stochastic' rounds up with probability equal to
# the fractional part, which is unbiased in the mean.
ROUND_MODE = os.environ.get('ROUND_MODE', 'stochastic')


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
# Per-hero expedition stats at max star (31) and exclusive weapon strength 10, scraped from
# kingshotdata.com hero pages: exp_atk/exp_def apply to the hero's own troop type; the weapon adds
# Lethality and Health % to the same type.  These are NOT in the profile Bonus Overview.
HERO_STATS = json.load(open(os.path.join(os.path.dirname(__file__), 'hero_stats.json')))
# Max hero gear + expedition-stat calibration, fitted to the Stat Bonuses panel of two live
# battle reports (2026-09-08, mail 223407017193981 and its Sophia twin: identical target, squad,
# ratio and lineup except the cavalry hero, so Charles/Yang appear twice as a consistency check).
#   lethality/health contribution = weapon_lv10 + 690.0   (fit slope 1.000, constant 690.0 in all
#     six observations -> the weapon table is exact and max gear is +690%, not the +600% assumed)
#   attack/defense  contribution = 0.833 * exp_atk + 58.7 (all six within 3.6 points; the raw
#     exp_atk scrape overstates the in-battle number, so a flat +200% gear term was ~230 too high)
GEAR_EXP_LETH = float(os.environ.get('GEAR_LETH', '690'))
EXP_SCALE = float(os.environ.get('EXP_SCALE', '0.833'))
EXP_OFFSET = float(os.environ.get('EXP_OFFSET', '58.7'))


@dataclass
class Side:
    name: str
    stats: dict                                  # {type: {attack, defense, lethality, health}} in %
    troops: dict                                 # {type: count}
    heroes: list = field(default_factory=list)   # 3 lineup heroes
    role: str = 'solo'                           # 'rally' (initiating), 'garrison', 'solo'
    joiners: list = field(default_factory=list)  # joiner heroes; only their first skill counts
    tier: int = 10                               # troop tier; an int applies to all three types
    tg: int = 8                                  # Truegold level, same convention as tier
    # Armies are often not uniform -- a report can show infantry and archers at Lv 11.0 while the
    # cavalry reads Lv 10.0.  Pass a dict keyed by troop type to either field to model that;
    # tier_of()/tg_of() resolve a scalar or a dict transparently.
    special: dict = field(default_factory=dict)  # extra special bonus % per stat (pets, city, appointments)
    hero_stats: bool = True                      # add per-hero expedition stats + weapon to the hero's troop type
    # Per-hero widget scale, keyed by hero name: 1.0 = the widget at max level, 0.0 = the hero has
    # no widget unlocked at all.  Widgets are an account-by-account thing -- an opponent can field
    # a hero whose widget is missing or only part-levelled -- so assuming max on everyone silently
    # inflates them.  Any hero not named here defaults to WIDGET_DEFAULT.
    widget_levels: dict = field(default_factory=dict)
    widget_default: float = 1.0
    # Both of these were invented when this file was written from prose guides, and NEITHER
    # appears in the reference engine (request-laurent/sos.battle, Fight.java).  That engine has
    # no counter bonus at all, and reorders targeting only on every 20th round and only for units
    # carrying the biker/sniper perk -- not a flat per-round bypass.  Defaults are now 0; the
    # fields stay so the assumption can be re-tested.
    triangle: float = 0.0                        # counter bonus % (archers>infantry etc.) -- unsourced
    ambusher: float = 0.20                       # cavalry 'Ambusher': 20% chance to bypass Infantry
                                                 # and hit Archers -- tooltip-confirmed, Kingshot-specific

    # ---- derived
    def tier_of(self, ttype):
        return self.tier[ttype] if isinstance(self.tier, dict) else self.tier

    def tg_of(self, ttype):
        return self.tg[ttype] if isinstance(self.tg, dict) else self.tg

    def effects(self):
        """List of (kind, value, scope, op_id) from lineup skills + joiner first skills."""
        out = []
        for h in self.heroes:
            for i, (sname, effs) in enumerate(HEROES[h]['skills']):
                for kind, v, scope in effs:
                    out.append((kind, v * SKILL_SCALE, scope, f'{h}:{sname}'))
        for h in self.joiners:
            sname, effs = HEROES[h]['skills'][0]
            for kind, v, scope in effs:
                out.append((kind, v * SKILL_SCALE, scope, f'{h}:{sname}'))
        # Truegold gear skills, carried by the account rather than a hero.  Every PvP report in
        # reports.py shows both sides with Unyielding Shield firing, so it applies whenever the
        # side fields any hero at all.
        if TROOP_SKILLS_ON:
            for sname, kind, v, _p, ttype in TROOP_SKILLS:
                if sname in TROOP_SKILLS_OFF:
                    continue
                out.append((kind, v * SKILL_SCALE, ttype, f'Troop:{sname}'))
        return out

    def special_bonus(self):
        sp = {k: 0.0 for k in ('attack', 'defense', 'lethality', 'health')}
        for k, v in self.special.items():
            sp[k] += v
        for h in self.heroes:
            w = HEROES[h]['widget']
            if w and ((w[0] == 'rally' and self.role == 'rally') or (w[0] == 'defender' and self.role == 'garrison')):
                sp[w[1]] += w[2] * self.widget_levels.get(h, self.widget_default)
        return sp

    def hero_stat(self, ttype, key):
        """Additive % from lineup heroes of this troop type: star stats (atk/def), weapon + gear (leth/hp)."""
        s = 0.0
        if not self.hero_stats:
            return s
        for h in self.heroes:
            if HEROES[h]['type'] != ttype:
                continue
            hs = HERO_STATS[h]
            if key == 'attack':
                s += EXP_SCALE * hs['exp_atk'] + EXP_OFFSET
            elif key == 'defense':
                s += EXP_SCALE * hs['exp_def'] + EXP_OFFSET
            else:   # lethality / health
                s += hs['weapon_lv10'] + GEAR_EXP_LETH
        return s

    def stat(self, ttype, key):
        s = self.stats[ttype][key] + self.hero_stat(ttype, key)
        return (100 + s) * (1 + self.special_bonus()[key] / 100) / 100   # multiplier form


DMG_UP = ('leth', 'atk', 'dmg', 'proc')
DEF_UP = ('def', 'hp')
TAKEN = ('taken', 'proc_taken')
OPP_DMG_DOWN = ('e_atk', 'e_leth', 'e_dmg', 'proc_e_dmg')
OPP_DEF_DOWN = ('e_taken', 'e_def', 'proc_e_taken')


def _prod(effs, kinds, scope_ok, sign=+1, reciprocal=False):
    """Multiply (1 +/- sum/100) over distinct ops.  Op = kind (stat category) for flat skills,
    or the skill name for chance-based (proc_) skills, so procs always multiply.

    reciprocal: use 1/(1 - sum/100) instead of (1 + sum/100).  The reference engine raises a
    defender's defence as `defense = defense / (1 - coefDefense)` (Fight.java:133), which is
    strictly stronger than the (1 + coef) this file assumed -- a +25% defence skill divides
    damage by 1.333, not 1.25.  Defence-side factors use this form; attack-side ones do not,
    because Skill.damage() really does accumulate `coef = coef + value/100`.
    """
    by_op = {}
    for kind, v, scope, name in effs:
        if kind in kinds and scope_ok(scope):
            op = name if kind.startswith('proc') else ('atk' if kind == 'dmg' else kind)
            if kind.startswith('proc'):
                v *= PROC_SCALE
            by_op[op] = by_op.get(op, 0) + v
    m = 1.0
    for v in by_op.values():
        if reciprocal:
            m *= 1.0 / max(1e-6, 1 - sign * v / 100)
        else:
            m *= (1 + sign * v / 100)
    return m


def skill_mod(att, att_effs, u, dfn, def_effs, v):
    """SkillMod = DamageUp * OppDefenseDown / (OppDamageDown * DefenseUp) for attacker type u
    hitting defender type v.  Every factor is prod over ops of (1 + summed value/100); the
    defender's factors sit in the denominator (kingshotguides.com / Absy Labs form)."""
    dmg_up = _prod(att_effs, DMG_UP, lambda s: s in ('all', u))
    opp_def_down = _prod(att_effs, OPP_DEF_DOWN, lambda s: s in ('all', v))
    opp_dmg_down = _prod(def_effs, OPP_DMG_DOWN, lambda s: s in ('all', u))
    def_up = _prod(def_effs, TAKEN + DEF_UP, lambda s: s in ('all', v), reciprocal=DEF_RECIP)
    tri = 1.0
    if (u, v) in (('arch', 'inf'), ('inf', 'cav'), ('cav', 'arch')):
        tri = 1 + att.triangle / 100
    return dmg_up * opp_def_down / (opp_dmg_down * def_up) * tri


def battle(a: Side, d: Side, max_rounds=5000, wear=WEAR, verbose=False):
    """Simulate a to the end. Returns dict with losses and winner."""
    A = {}
    D = {}
    for s in (a, d):
        for t in TYPES:
            ba, bd, bl, bh = base_stats(t, s.tier_of(t), s.tg_of(t))
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
        if ARMY_MIN_LIVE:
            army_min = min(sum(na.values()), sum(nd.values()))
        kills_on_d = {t: 0.0 for t in TYPES}
        kills_on_a = {t: 0.0 for t in TYPES}
        for (src, n_src, n_tgt, Aa, Dd, mm, kills) in (
                (a, na, nd, A, D, mods, kills_on_d), (d, nd, na, A, D, modd, kills_on_a)):
            tgt_name = d.name if src is a else a.name
            target = next((v for v in TYPES if n_tgt[v] > 0), None)
            if target is None:
                continue
            army_sqrt = army_min ** ENG_B
            for u in TYPES:
                if n_src[u] <= 0:
                    continue
                army = n_src[u] ** ENG_A * army_sqrt
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



def _split_effects(effs):
    """Flat effects (always on) and proc skills grouped by skill name with full magnitudes."""
    flat, procs = [], {}
    for kind, v, scope, name in effs:
        # PERMANENT wins over the kind prefix: these were written as 'proc' when this file assumed
        # everything was chance-based, but the reports show them firing exactly once (switched on
        # at battle start) and the in-game tooltip gives no chance or duration.
        if name.split(':', 1)[1] in PERMANENT:
            flat.append((kind, v, scope, name))
        elif kind.startswith('proc'):
            sname = name.split(':', 1)[1]
            mag = v / proc_uptime(sname)
            procs.setdefault(sname, []).append((kind, mag, scope, name))
        else:
            flat.append((kind, v, scope, name))
    return flat, procs


def battle_mc(a: Side, d: Side, rng, max_rounds=5000):
    """Monte Carlo battle: chance skills are rolled once per round at squad level, periodic skills
    fire on their schedule.  Same engine as battle() otherwise."""
    global PROC_SCALE
    saved, PROC_SCALE = PROC_SCALE, 1.0     # magnitudes here are full values, not scaled EVs
    try:
        A, D = {}, {}
        for s in (a, d):
            for t in TYPES:
                ba, bd, bl, bh = base_stats(t, s.tier_of(t), s.tg_of(t))
                A[(s.name, t)] = ba * s.stat(t, 'attack') * bl * s.stat(t, 'lethality') / 100
                D[(s.name, t)] = bh * s.stat(t, 'health') * bd * s.stat(t, 'defense') / 100
        fa, pa = _split_effects(a.effects())
        fd, pd = _split_effects(d.effects())
        active = {}          # (side, skill) -> rounds remaining
        na, nd = dict(a.troops), dict(d.troops)
        army_min = min(sum(na.values()), sum(nd.values()))
        army_sqrt = army_min ** ENG_B
        rnd = 0
        while rnd < max_rounds and sum(na.values()) > 0 and sum(nd.values()) > 0:
            rnd += 1
            if ARMY_MIN_LIVE:
                army_min = min(sum(na.values()), sum(nd.values()))
                army_sqrt = army_min ** ENG_B
            # decide which procs are live this round
            live = {'a': list(fa), 'd': list(fd)}
            for side, procs in (('a', pa), ('d', pd)):
                for sname, effs in procs.items():
                    mode, p, dur = PROC_SPEC[sname]
                    key = (side, sname)
                    if mode == 'always':
                        on = True
                    elif mode == 'periodic':
                        if rnd % p == 0:
                            active[key] = dur
                        on = active.get(key, 0) > 0
                    else:
                        if rng.random() < p:
                            active[key] = dur
                        on = active.get(key, 0) > 0
                    if on:
                        live[side].extend(effs)
                    if key in active and active[key] > 0:
                        active[key] -= 1
            # A hero's skills stop firing once that hero's own troop type is wiped -- the
            # reference gates every skill on it (Skill.condition: "Si l'unite est decimee, alors
            # le hero n'a plus d'effet").  The reports show it plainly: in the Terry 20k fight
            # Sophia's skills imply ~16 rounds while Yang's imply ~28, because her cavalry died
            # first.  Troop abilities are gated the same way, on their own type.
            # The gate is "wiped DURING the battle", not "never present": the reports show Yang
            # firing 15 times and scoring 203 kills in a march carrying ZERO archers, so a hero
            # whose type was never brought still contributes.  Only a type that started with
            # troops and has since been destroyed silences its hero.
            def _alive(effs, counts, start):
                out = []
                for kind, v, scope, nm in effs:
                    who = nm.split(':', 1)[0]
                    t = scope if who == 'Troop' else (HEROES[who]['type'] if who in HEROES else None)
                    if t in TYPES:
                        if who == 'Troop':
                            # A troop ability belongs to the TROOPS, not to the hero whose panel
                            # row displays it, so it needs that type alive NOW -- whether or not
                            # the march ever had any.  Evidence: Yang shows 5 rows with archers
                            # present and 3 without.  His own skills keep firing at zero archers
                            # (row 1 still books kills); Volley and Howling Wind vanish entirely.
                            # The old rule only skipped a type that started alive and then died,
                            # so a pure-infantry march fired archer and cavalry abilities all
                            # fight -- worst exactly in the single-type cells used to isolate them.
                            if counts.get(t, 0) <= 0:
                                continue
                        elif start.get(t, 0) > 0 and counts.get(t, 0) <= 0:
                            continue
                    out.append((kind, v, scope, nm))
                return out
            ae = _alive(live['a'], na, a.troops)
            de = _alive(live['d'], nd, d.troops)
            ta = next((v for v in TYPES if nd[v] > 0), None)
            td = next((v for v in TYPES if na[v] > 0), None)
            kills_on_d = {t: 0.0 for t in TYPES}
            kills_on_a = {t: 0.0 for t in TYPES}
            for src, n_src, n_tgt, target, kills, my_effs, their_effs, other in (
                    (a, na, nd, ta, kills_on_d, ae, de, d), (d, nd, na, td, kills_on_a, de, ae, a)):
                for u in TYPES:
                    if n_src[u] <= 0:
                        continue
                    army = n_src[u] ** ENG_A * army_sqrt
                    shares = [(target, 1.0)]
                    if u == 'cav' and target != 'arch' and n_tgt['arch'] > 0 and src.ambusher > 0:
                        # "20% chance to bypass Infantry and directly attack Archers" -- a discrete
                        # per-round roll, not a permanent split.  The reports carry it as its own
                        # row with a trigger count (3 in ~16 rounds of cavalry life = 19%).
                        # Splitting instead gives the cavalry TWO attacks a round, each with its
                        # own ceil(), one of them against a target ~5x squishier.
                        if AMBUSH_ROLL:
                            if rng.random() < src.ambusher:
                                shares = [('arch', 1.0)]
                        else:
                            shares = [(target, 1 - src.ambusher), ('arch', src.ambusher)]
                    # Extra strikes.  In the reference, needContinue() requires BOTH effect==101
                    # AND effectTarget==40, so only a minority of damage skills grant an extra
                    # target; the rest of effect 101 is a plain multiplier on that troop type's
                    # damage, which skill_mod() already applies.  Turning this on for every damage
                    # skill triples archer output and wrecks the fit (see STRIKE_CONTINUE below),
                    # so it is off until a specific skill can be shown to carry effectTarget 40.
                    # Reference gates this on `unitType == skill.getUnitType()` -- the HERO's own
                    # troop type, not the skill's declared scope.  Avalanche reads 'all' as a
                    # damage buff but only ever strikes with Yang's archers.
                    extra = 0 if not STRIKE_CONTINUE else sum(1 for _, _, _, nm in my_effs
                                if nm.split(':', 1)[1] in STRIKE
                                and HEROES[nm.split(':', 1)[0]]['type'] == u)
                    if extra:
                        hit = {t for t, _ in shares}
                        for v in TYPES:
                            if extra <= 0:
                                break
                            if n_tgt[v] > 0 and v not in hit:
                                shares.append((v, 1.0)); hit.add(v); extra -= 1
                    for tgt, share in shares:
                        mod = skill_mod(src, my_effs, u, other, their_effs, tgt)
                        dead = share * army * A[(src.name, u)] / D[(other.name, tgt)] / 100 * mod
                        dead -= dead * WEAR * rnd          # reference engine's per-round attrition
                        if PROTECT:
                            dead *= (1 - PROTECT)          # defender absorption, Skill.protect()
                        if ROUND_MODE == 'stochastic':
                            f = math.floor(dead)
                            kills[tgt] += f + (1 if rng.random() < dead - f else 0)
                        else:
                            kills[tgt] += math.ceil(dead)
            for t in TYPES:
                nd[t] = max(0, nd[t] - kills_on_d[t])
                na[t] = max(0, na[t] - kills_on_a[t])
        a_lost = sum(a.troops.values()) - sum(na.values())
        d_lost = sum(d.troops.values()) - sum(nd.values())
        return dict(rounds=rnd, a_lost=a_lost, d_lost=d_lost, a_left=na, d_left=nd,
                    winner=(a.name if sum(nd.values()) == 0 and sum(na.values()) > 0 else
                            d.name if sum(na.values()) == 0 else 'draw'))
    finally:
        PROC_SCALE = saved


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
    """Reproduce kingshotguides.com's worked Bear Trap example: expected 16,797 damage.

    NOT A REGRESSION TEST, despite being cited as one throughout this project's history.  It
    hand-computes the formula inline: it never calls battle() or battle_mc(), it hardcodes the
    bear's defence instead of building D from stats, and it applies a 1.10 archer multiplier that
    is the counter-triangle since deleted from the model as unsourced.  It touches base_stats()
    and the sqrt engagement term and nothing else, so it returns 16,797 no matter what is done to
    targeting, troop abilities, skill uptimes, rounding, Ambusher, per-type tiers or widgets --
    verified by running it under all of those toggles.

    Its worth is as a check on ONE thing: that base_stats() and sqrt(n_u * army_min) still agree
    with a third-party worked example.  Use allfights.py for anything else; that scores the real
    engine against eight measured battles.
    """
    stats = {t: dict(attack=25, defense=0, lethality=0, health=0) for t in TYPES}
    me = Side('me', stats, {'inf': 6000, 'cav': 6000, 'arch': 6000}, tier=6, tg=0, hero_stats=False)
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
