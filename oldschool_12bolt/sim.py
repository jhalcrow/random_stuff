#!/usr/bin/env python3
"""
Monte Carlo "playtest" for an Atlantic 93/94 Old School 12 Bolt (URw Lion Dib Bolt) deck.

The sim plays our deck card-by-card (real draws, real mana, a greedy but sane
sequencing policy) against stochastic opponent models that capture the
things that actually decide these matchups: how fast they clock us, what
blocks, how much creature removal / discard / countermagic they have, and
whether they land a Moat / The Abyss style lock.

It is a caricature of real games, not a rules engine. Use it to compare
candidate flex slots and to see which matchups need sideboard help, not as a
promise about win rates.

    python3 sim.py            # run every build vs every opponent
    python3 sim.py -n 5000    # more games per cell
    python3 sim.py --seed 7
"""
import argparse
import random
from collections import Counter
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Card definitions
# ---------------------------------------------------------------------------
# kind: land, mana, creature, burn, spell
# cost: total mana; colors: required colored pips (string of W/U/R)


@dataclass
class Card:
    name: str
    kind: str
    cost: int = 0
    colors: str = ""
    power: int = 0
    tough: int = 0
    flying: bool = False
    produces: str = ""      # for lands / mana artifacts: colors it can make ('*' = any)
    dmg: int = 0            # burn damage to face
    selfdmg: int = 0        # damage to us (Psionic Blast)


CARDS = {
    # lands
    "Volcanic Island": Card("Volcanic Island", "land", produces="UR"),
    "Plateau": Card("Plateau", "land", produces="RW"),
    "Tundra": Card("Tundra", "land", produces="UW"),
    "City of Brass": Card("City of Brass", "land", produces="*"),
    "Mishra's Factory": Card("Mishra's Factory", "land", produces="C"),
    "Strip Mine": Card("Strip Mine", "land", produces="C"),
    "Library of Alexandria": Card("Library of Alexandria", "land", produces="C"),
    # fast mana
    "Black Lotus": Card("Black Lotus", "mana", produces="LOTUS"),
    "Mox Sapphire": Card("Mox Sapphire", "mana", produces="U"),
    "Mox Ruby": Card("Mox Ruby", "mana", produces="R"),
    "Mox Pearl": Card("Mox Pearl", "mana", produces="W"),
    "Sol Ring": Card("Sol Ring", "mana", cost=1, produces="CC"),
    # creatures
    "Savannah Lions": Card("Savannah Lions", "creature", 1, "W", 2, 1),
    "Serendib Efreet": Card("Serendib Efreet", "creature", 3, "U", 3, 4, flying=True),
    # burn
    "Lightning Bolt": Card("Lightning Bolt", "burn", 1, "R", dmg=3),
    "Chain Lightning": Card("Chain Lightning", "burn", 1, "R", dmg=3),
    "Psionic Blast": Card("Psionic Blast", "burn", 3, "U", dmg=4, selfdmg=2),
    "Fireball": Card("Fireball", "burn", 1, "R", dmg=0),   # X spell, handled specially
    # spells
    "Swords to Plowshares": Card("Swords to Plowshares", "spell", 1, "W"),
    "Balance": Card("Balance", "spell", 2, "W"),
    "Chaos Orb": Card("Chaos Orb", "spell", 2, ""),
    "Ancestral Recall": Card("Ancestral Recall", "spell", 1, "U"),
    "Time Walk": Card("Time Walk", "spell", 2, "U"),
    "Wheel of Fortune": Card("Wheel of Fortune", "spell", 3, "R"),
    "Timetwister": Card("Timetwister", "spell", 3, "U"),
    "Unstable Mutation": Card("Unstable Mutation", "spell", 1, "U"),
    "Black Vise": Card("Black Vise", "spell", 1, ""),
    "Earthquake": Card("Earthquake", "spell", 1, "R"),   # X spell
    "Fork": Card("Fork", "spell", 2, "R"),
}

CORE = {
    "Savannah Lions": 4, "Serendib Efreet": 4,
    "Lightning Bolt": 4, "Chain Lightning": 4, "Psionic Blast": 4, "Fireball": 1,
    "Swords to Plowshares": 4, "Balance": 1, "Chaos Orb": 1,
    "Ancestral Recall": 1, "Time Walk": 1, "Wheel of Fortune": 1, "Timetwister": 1,
    "Black Lotus": 1, "Mox Sapphire": 1, "Mox Ruby": 1, "Mox Pearl": 1, "Sol Ring": 1,
    "Mishra's Factory": 4, "Strip Mine": 1, "Library of Alexandria": 1,
    "City of Brass": 4, "Volcanic Island": 4, "Plateau": 3, "Tundra": 2,
}
assert sum(CORE.values()) == 55, sum(CORE.values())

# five flex slots on top of the 55-card core
BUILDS = {
    "A: 3 Mutation + 2 Vise": {"Unstable Mutation": 3, "Black Vise": 2},
    "B: 4 Vise + 1 Fork": {"Black Vise": 4, "Fork": 1},
    "C: 4 Mutation + 1 Fork": {"Unstable Mutation": 4, "Fork": 1},
    "D: 2 Mutation + 2 Vise + Fork": {"Unstable Mutation": 2, "Black Vise": 2, "Fork": 1},
}


def build_deck(extra):
    counts = Counter(CORE)
    counts.update(extra)
    assert sum(counts.values()) == 60, sum(counts.values())
    return [CARDS[n] for n, k in counts.items() for _ in range(k)]


# ---------------------------------------------------------------------------
# Opponent models
# ---------------------------------------------------------------------------

@dataclass
class OppCreature:
    name: str
    power: int
    tough: int
    flying: bool = False
    first_strike: bool = False
    pro_red: bool = False      # can't be bolted, blocks Lions all day
    big: bool = False          # can't be burned out profitably (Juzam, Su-Chi, Serra)
    grows: int = 0             # Atog style: extra damage when it connects
    sick: bool = True          # arrived this turn, cannot attack yet


@dataclass
class Opponent:
    name: str
    # schedule[turn] = list of creatures that may arrive on that opp turn, with probability
    schedule: dict = field(default_factory=dict)
    creature_prob: float = 0.8
    removal_prob: dict = field(default_factory=dict)  # turn -> P(remove our best creature)
    removal_kind: str = "swords"  # swords (exile, we gain life), bolt (only kills tough<=3), terror
    discard_turn2: float = 0.0   # Hymn to Tourach on their turn 2
    mind_twist: float = 0.0      # one-shot restricted Mind Twist around turn 3-4
    counter_prob: float = 0.0    # per our turn, P(they hold a counter for our best spell)
    lock_turn: dict = field(default_factory=dict)   # turn -> P(Moat)  (stops non-fliers)
    abyss_turn: dict = field(default_factory=dict)  # turn -> P(The Abyss)
    face_burn: dict = field(default_factory=dict)   # turn -> expected burn to our face
    geddon_turn: dict = field(default_factory=dict) # turn -> P(Armageddon)
    hand_profile: list = field(default_factory=lambda: [7, 6, 5, 4, 3, 2, 2, 1, 1, 1, 1, 1])
    disenchant_prob: float = 0.0  # per turn, P(they kill a Black Vise)
    lifegain: dict = field(default_factory=dict)
    life: int = 20
    blocks: bool = True
    plays_first_prob: float = 0.5


def the_deck():
    return Opponent(
        "The Deck (UWbr control)",
        schedule={2: [OppCreature("Mishra's Factory", 2, 2)],
                  3: [OppCreature("Mishra's Factory", 2, 2)],
                  6: [OppCreature("Serra Angel", 4, 4, flying=True, big=True)],
                  8: [OppCreature("Serra Angel", 4, 4, flying=True, big=True)]},
        creature_prob=0.6,
        removal_prob={2: .25, 3: .35, 4: .4, 5: .45, 6: .5, 7: .55, 8: .6, 9: .65, 10: .7},
        removal_kind="swords", mind_twist=0.35, counter_prob=0.35,
        lock_turn={4: .2, 5: .3, 6: .35, 7: .4, 8: .5},
        abyss_turn={4: .15, 5: .25, 6: .3, 7: .35},
        hand_profile=[7, 7, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5],
        disenchant_prob=0.35,
    )


def white_weenie():
    return Opponent(
        "White Weenie (Lions / Order of Leitbur / Crusade)",
        schedule={1: [OppCreature("Savannah Lions", 2, 1)],
                  2: [OppCreature("White Knight", 2, 2, first_strike=True)],
                  3: [OppCreature("Order of Leitbur", 2, 2, first_strike=True)],
                  4: [OppCreature("Savannah Lions", 2, 1)],
                  5: [OppCreature("Serra Angel", 4, 4, flying=True, big=True)],
                  6: [OppCreature("Order of Leitbur", 2, 2, first_strike=True)]},
        creature_prob=0.8,
        removal_prob={1: .15, 2: .3, 3: .35, 4: .35, 5: .35, 6: .35, 7: .35},
        removal_kind="swords",
        geddon_turn={4: .25, 5: .3},
        hand_profile=[7, 6, 4, 3, 2, 1, 1, 0, 0, 0, 0, 0],
        disenchant_prob=0.3,
    )


def atog():
    return Opponent(
        "Atog (UR artifact aggro)",
        schedule={1: [OppCreature("Ornithopter", 0, 2, flying=True)],
                  2: [OppCreature("Atog", 1, 2, grows=4)],
                  3: [OppCreature("Su-Chi", 4, 4, big=True)],
                  4: [OppCreature("Mishra's Factory", 2, 2)],
                  5: [OppCreature("Su-Chi", 4, 4, big=True)]},
        creature_prob=0.8,
        removal_prob={1: .25, 2: .3, 3: .35, 4: .35, 5: .35, 6: .35, 7: .35},
        removal_kind="bolt",
        face_burn={3: 1, 4: 1, 5: 1.5, 6: 2, 7: 2, 8: 2},
        hand_profile=[7, 6, 5, 4, 3, 2, 1, 1, 0, 0, 0, 0],
    )


def troll_disco():
    return Opponent(
        "Troll Disco / Deadguy (Hymn, Juzam, Specter)",
        schedule={2: [OppCreature("Hypnotic Specter", 2, 2, flying=True)],
                  3: [OppCreature("Juzam Djinn", 5, 5, big=True)],
                  4: [OppCreature("Sedge Troll", 2, 2)],
                  5: [OppCreature("Juzam Djinn", 5, 5, big=True)],
                  6: [OppCreature("Hypnotic Specter", 2, 2, flying=True)]},
        creature_prob=0.7,
        removal_prob={2: .3, 3: .35, 4: .4, 5: .4, 6: .4, 7: .45},
        removal_kind="terror",
        discard_turn2=0.45, mind_twist=0.4,
        hand_profile=[7, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1, 1],
        disenchant_prob=0.3,
    )


def erhnam_burnem():
    return Opponent(
        "Erhnam Burn'em / Zoo (Kird Ape, Erhnam, bolts)",
        schedule={1: [OppCreature("Kird Ape", 2, 3)],
                  2: [OppCreature("Kird Ape", 2, 3)],
                  3: [OppCreature("Serendib Efreet", 3, 4, flying=True)],
                  4: [OppCreature("Erhnam Djinn", 4, 5, big=True)],
                  6: [OppCreature("Erhnam Djinn", 4, 5, big=True)]},
        creature_prob=0.8,
        removal_prob={1: .25, 2: .3, 3: .35, 4: .35, 5: .35, 6: .35, 7: .35},
        removal_kind="bolt",
        face_burn={2: 0.5, 3: 1, 4: 1.5, 5: 2, 6: 2, 7: 2.5, 8: 2.5},
        hand_profile=[7, 6, 5, 4, 3, 2, 1, 0, 0, 0, 0, 0],
    )


OPPONENTS = [the_deck, white_weenie, atog, troll_disco, erhnam_burnem]


# ---------------------------------------------------------------------------
# Game state for our deck
# ---------------------------------------------------------------------------

@dataclass
class OurCreature:
    card: Card
    mutation: int = 0          # +3/+3 shrinking each upkeep
    summoning_sick: bool = True
    counters: int = 0

    @property
    def power(self):
        return self.card.power + (3 - self.counters if self.mutation else 0)

    @property
    def tough(self):
        return self.card.tough + (3 - self.counters if self.mutation else 0)


class Game:
    def __init__(self, deck, opp: Opponent, rng: random.Random, on_play: bool):
        self.rng = rng
        self.opp = opp
        self.on_play = on_play
        self.library = deck[:]
        rng.shuffle(self.library)
        self.hand = []
        self.lands = []            # Card
        self.mana_rocks = []       # Card (Moxen, Sol Ring)
        self.lotus = False
        self.creatures = []        # OurCreature
        self.vises = 0
        self.life = 20
        self.opp_life = opp.life
        self.opp_creatures = []
        self.moat = False
        self.abyss = False
        self.turn = 0
        self.land_played = False
        self.orb_used = False
        self.strip_used = False
        self.log = []
        self.mulligan()

    # ---- setup ----------------------------------------------------------
    def mulligan(self):
        for hand_size in (7, 6, 5):
            self.hand = self.library[:hand_size]
            self.library = self.library[hand_size:]
            mana = sum(1 for c in self.hand if c.kind in ("land", "mana"))
            if 2 <= mana <= 5 or (hand_size == 5):
                return
            self.library += self.hand
            self.rng.shuffle(self.library)

    def draw(self, n=1):
        for _ in range(n):
            if not self.library:
                self.log.append("decked")
                self.life = 0
                return
            self.hand.append(self.library.pop())

    # ---- mana -----------------------------------------------------------
    def mana_sources(self):
        """list of (colors, amount) available this turn."""
        src = []
        for l in self.lands:
            if l.name == "Mishra's Factory" and any(c.card.name == "Factory" for c in self.creatures):
                continue
            src.append(l.produces)
        for m in self.mana_rocks:
            if m.name == "Sol Ring":
                src += ["C", "C"]
            else:
                src.append(m.produces)
        return src

    def can_pay(self, sources, cost, colors):
        """Greedy colour matching; sources is list of 'U','R','W','C','*','UR'..."""
        pool = list(sources)
        for pip in colors:
            cand = [s for s in pool if pip in s or s == "*"]
            if not cand:
                return None
            # prefer single-colour sources so flexible ones stay free
            cand.sort(key=lambda s: (s == "*", len(s)))
            pool.remove(cand[0])
        if len(pool) < cost - len(colors):
            return None
        # spend generic: colourless first
        pool.sort(key=lambda s: (s != "C", s == "*", len(s)))
        for _ in range(cost - len(colors)):
            pool.pop(0)
        return pool

    # ---- opponent turn --------------------------------------------------
    def opp_turn(self):
        t = self.turn
        o = self.opp
        # discard
        if t == 2 and self.rng.random() < o.discard_turn2 and self.hand:
            for _ in range(min(2, len(self.hand))):
                self.hand.pop(self.rng.randrange(len(self.hand)))
            self.log.append("hymned")
        if t in (3, 4) and o.mind_twist and self.rng.random() < o.mind_twist / 2 and self.hand:
            n = min(len(self.hand), t - 1)
            for _ in range(n):
                self.hand.pop(self.rng.randrange(len(self.hand)))
            o.mind_twist = 0
            self.log.append("twisted")
        # Armageddon
        if self.rng.random() < o.geddon_turn.get(t, 0):
            self.lands = [l for l in self.lands if l.name == "Library of Alexandria" and False]
            self.opp_creatures = self.opp_creatures  # they keep their board
            self.log.append("geddon")
        # locks
        if not self.moat and self.rng.random() < o.lock_turn.get(t, 0):
            self.moat = True
        if not self.abyss and self.rng.random() < o.abyss_turn.get(t, 0):
            self.abyss = True
        # removal on our best creature (scaled down as their hand empties)
        gas = min(1.0, o.hand_profile[min(t - 1, len(o.hand_profile) - 1)] / 4.0)
        r = o.removal_prob.get(t, o.removal_prob.get(max(o.removal_prob, default=0), 0)) * gas
        if self.creatures and self.rng.random() < r:
            target = max(self.creatures, key=lambda c: c.power)
            ok = True
            if o.removal_kind == "bolt" and target.tough > 3:
                ok = False
            if ok:
                self.creatures.remove(target)
                if o.removal_kind == "swords":
                    self.life += target.power
        # Disenchant on Vise
        if self.vises and self.rng.random() < o.disenchant_prob:
            self.vises -= 1
        # their attack (creatures that arrived last turn are now unsick)
        for c in self.opp_creatures:
            c.sick = False
        # creatures
        for c in o.schedule.get(t, []):
            if self.rng.random() < o.creature_prob:
                self.opp_creatures.append(OppCreature(**{**c.__dict__, "sick": True}))
        blockers = list(self.creatures)
        dmg = 0
        incoming = sum(c.power + c.grows for c in self.opp_creatures if not c.sick)
        for c in sorted(self.opp_creatures, key=lambda x: -(x.power + x.grows)):
            if c.power == 0 or c.sick:
                continue
            # we chump/ trade only with Factories or when lethal looms
            if c.flying and not any(b.card.flying for b in blockers):
                dmg += c.power + c.grows
                continue
            block = None
            for b in blockers:
                if (b.card.flying or not c.flying) and b.tough > c.power and b.power >= c.tough:
                    block = b
                    break
            if block:
                blockers.remove(block)
                self.opp_creatures.remove(c)
                continue
            # trade when we are losing the race
            if self.life <= self.opp_life:
                trade = next((b for b in blockers if (b.card.flying or not c.flying)
                              and b.power >= c.tough and not c.first_strike), None)
                if trade:
                    blockers.remove(trade)
                    self.creatures.remove(trade)
                    self.opp_creatures.remove(c)
                    continue
            # chump when the swing would otherwise kill us
            if incoming - dmg >= self.life and self.life - dmg <= c.power + c.grows:
                chump = next((b for b in blockers if (b.card.flying or not c.flying)), None)
                if chump:
                    blockers.remove(chump)
                    self.creatures.remove(chump)
                    continue
            dmg += c.power + c.grows
        # Vise damage happens on their upkeep
        if self.vises:
            hs = o.hand_profile[min(t - 1, len(o.hand_profile) - 1)]
            self.opp_life -= self.vises * max(0, hs - 4)
        self.life -= dmg
        self.life -= max(0, int(round(o.face_burn.get(t, 0) * gas + self.rng.random() - 0.5)))
        self.opp_life += o.lifegain.get(t, 0)

    # ---- our turn -------------------------------------------------------
    def upkeep(self):
        for c in list(self.creatures):
            if c.card.name == "Serendib Efreet":
                self.life -= 1
            if c.mutation:
                c.counters += 1
                if c.tough <= 0:
                    self.creatures.remove(c)
        if self.abyss:
            non_art = [c for c in self.creatures if c.card.name != "Factory"]
            if non_art:
                self.creatures.remove(min(non_art, key=lambda c: c.power))

    def play_land(self):
        lands = [c for c in self.hand if c.kind == "land"]
        if not lands:
            return
        need = Counter()
        for c in self.hand:
            for pip in c.colors:
                need[pip] += 1
        have = Counter()
        for l in self.lands:
            for p in l.produces:
                have[p] += 1
        for m in self.mana_rocks:
            have[m.produces] += 1

        def score(l):
            if l.name == "Library of Alexandria":
                return 5 if len(self.hand) >= 6 and self.turn <= 2 else -1
            if l.name == "Strip Mine":
                return -2
            if l.name == "Mishra's Factory":
                return 1 if sum(have[p] for p in "WUR") >= 3 else -0.5
            if l.produces == "*":
                return 3 if self.turn <= 2 else 1.5
            return sum(need[p] * (0.5 if have[p] else 1.5) for p in l.produces)

        best = max(lands, key=score)
        self.hand.remove(best)
        self.lands.append(best)
        self.land_played = True

    def play_turn(self):
        self.turn += 1
        self.upkeep()
        if not (self.turn == 1 and self.on_play):
            self.draw()
        self.land_played = False
        self.play_land()
        # drop rocks
        for c in [c for c in self.hand if c.kind == "mana"]:
            if c.name == "Black Lotus":
                self.hand.remove(c)
                self.lotus = True
            elif c.name == "Sol Ring":
                continue  # handled in casting
            else:
                self.hand.remove(c)
                self.mana_rocks.append(c)
        # Library of Alexandria: if we hold 7 cards, tapping it for a card beats using it for mana
        if any(l.name == "Library of Alexandria" for l in self.lands) and len(self.hand) == 7:
            self.draw()
        for c in self.creatures:
            c.summoning_sick = False
        self.main_phase()
        self.attack()
        self.main_phase(second=True)
        if len(self.hand) > 7:
            self.hand = self.hand[:7]

    def main_phase(self, second=False):
        sources = self.mana_sources()
        if second:
            sources = getattr(self, "_leftover", [])
        lotus_avail = self.lotus
        opp_stops_ground = self.moat or any(
            c.tough >= 3 and not c.flying for c in self.opp_creatures)

        def cast(card, extra_generic=0):
            nonlocal sources, lotus_avail
            pool = self.can_pay(sources, card.cost + extra_generic, card.colors)
            if pool is None and lotus_avail:
                # lotus gives 3 of one colour: model as three '*'
                pool = self.can_pay(sources + ["*", "*", "*"], card.cost + extra_generic, card.colors)
                if pool is None:
                    return False
                lotus_avail = False
                self.lotus = False
            if pool is None:
                return False
            sources = pool
            self.hand.remove(card)
            self.log.append(f"T{self.turn} cast {card.name}")
            return True

        def countered(card):
            if self.rng.random() < self.opp.counter_prob and card.cost >= 1 and card.kind != "burn":
                self.log.append(f"countered {card.name}")
                return True
            return False

        def in_hand(name):
            return next((c for c in self.hand if c.name == name), None)

        # Sol Ring first
        sr = in_hand("Sol Ring")
        if sr and cast(sr):
            self.mana_rocks.append(sr)
            sources += ["C", "C"]

        # card draw
        for name in ("Ancestral Recall", "Time Walk"):
            c = in_hand(name)
            if c and cast(c) and not countered(c):
                if name == "Ancestral Recall":
                    self.draw(3)
                else:
                    self.extra_turn = True

        # removal on big threats we cannot burn out
        big = [c for c in self.opp_creatures if c.big or c.pro_red]
        while big:
            c = in_hand("Swords to Plowshares")
            if not c or not cast(c):
                break
            tgt = max(big, key=lambda x: x.power)
            self.opp_creatures.remove(tgt)
            self.opp_life += tgt.power
            big.remove(tgt)

        # Chaos Orb: Moat/Abyss first, then the biggest creature
        orb = in_hand("Chaos Orb")
        if orb and (self.moat or self.abyss or big or (self.opp_creatures and self.turn >= 4)) and cast(orb):
            if self.rng.random() < 0.85:
                if self.moat:
                    self.moat = False
                elif self.abyss:
                    self.abyss = False
                elif self.opp_creatures:
                    tgt = max(self.opp_creatures, key=lambda x: x.power)
                    self.opp_creatures.remove(tgt)
                    if tgt in big:
                        big.remove(tgt)

        # Balance: when we are empty-handed / creatureless and they have a board
        bal = in_hand("Balance")
        if bal and len(self.opp_creatures) >= 2 and len(self.creatures) == 0 and cast(bal) and not countered(bal):
            self.opp_creatures.clear()
            self.hand = self.hand[:min(len(self.hand), max(1, self.opp.hand_profile[min(self.turn - 1, 11)]))]

        # Black Vise: only vs decks that keep cards
        for _ in range(2):
            v = in_hand("Black Vise")
            if v and self.opp.hand_profile[min(self.turn, 11)] > 4 and cast(v):
                self.vises += 1

        # if the burn in hand is lethal, point it at the face before doing anything else
        reach = sum(c.dmg for c in self.hand if c.kind == "burn")
        if reach >= self.opp_life:
            for spell in sorted([c for c in self.hand if c.kind == "burn" and c.name != "Fireball"],
                                key=lambda c: -c.dmg):
                if cast(spell):
                    self.opp_life -= spell.dmg
                    self.life -= spell.selfdmg
                    if self.opp_life <= 0:
                        return

        # creatures
        for name in ("Savannah Lions", "Serendib Efreet"):
            while True:
                c = in_hand(name)
                if not c or not cast(c):
                    break
                if countered(c):
                    continue
                self.creatures.append(OurCreature(c))

        # Unstable Mutation on our best evasive / unblocked body
        mut = in_hand("Unstable Mutation")
        if mut and self.creatures:
            tgt = max(self.creatures, key=lambda c: (c.card.flying, c.power))
            if not tgt.mutation and cast(mut) and not countered(mut):
                tgt.mutation = 1

        # burn: kill blockers / racing threats when they matter, else face
        def burn_spells():
            return [c for c in self.hand if c.kind == "burn" and c.name != "Fireball"]

        def burn_target():
            # creature worth killing: blocks our attackers or races us
            threats = [c for c in self.opp_creatures if not c.big and not c.pro_red and c.tough <= 4]
            if not threats:
                return None
            racing = self.life <= 10 or (sum(c.power + c.grows for c in self.opp_creatures) >= 4 and self.opp_life > 10)
            blocking = self.creatures and any(c.tough >= 2 and not c.flying for c in threats) and self.opp_life > 8
            if racing or blocking:
                return max(threats, key=lambda c: (c.grows, c.power, -c.tough))
            return None

        for spell in sorted(burn_spells(), key=lambda c: c.cost):
            tgt = burn_target()
            lethal_face = self.opp_life <= sum(c.dmg for c in burn_spells()) + sum(
                c.power for c in self.creatures if not c.summoning_sick and (c.card.flying or not opp_stops_ground))
            if tgt and not lethal_face:
                if tgt.tough <= spell.dmg and cast(spell):
                    self.opp_creatures.remove(tgt)
                    self.log.append(f"T{self.turn}   -> kills {tgt.name}")
                    self.life -= spell.selfdmg
            else:
                if cast(spell):
                    self.opp_life -= spell.dmg
                    self.life -= spell.selfdmg
            if self.opp_life <= 0:
                return

        # Fireball: X to face when it finishes, or as removal for Su-Chi/Juzam-sized things late
        fb = in_hand("Fireball")
        big = [c for c in self.opp_creatures if c.big or c.pro_red]
        if fb:
            x = len(sources) - 1 + (3 if lotus_avail else 0)
            if x >= self.opp_life and cast(fb, extra_generic=x):
                self.opp_life -= x
            elif x >= 4 and big and cast(fb, extra_generic=x):
                tgt = max(big, key=lambda c: c.power)
                if tgt.tough <= x:
                    self.opp_creatures.remove(tgt)

        # Earthquake (sideboard): sweep the ground when they have the wider board
        eq = in_hand("Earthquake")
        if eq:
            x = len(sources) - 1 + (3 if lotus_avail else 0)
            theirs = [c for c in self.opp_creatures if not c.flying and c.tough <= x]
            ours = [c for c in self.creatures if not c.card.flying and c.tough <= x]
            if x >= 1 and len(theirs) >= 2 and len(theirs) > len(ours) and self.life > x + 2:
                x = min(x, max(c.tough for c in theirs))
                if cast(eq, extra_generic=x):
                    for c in theirs:
                        self.opp_creatures.remove(c)
                    for c in ours:
                        self.creatures.remove(c)
                    self.opp_life -= x
                    self.life -= x
                    self.log.append(f"T{self.turn}   -> quake for {x}")

        # Fork copies a bolt to the face when we are racing
        fk = in_hand("Fork")
        if fk and self.opp_life <= 12 and burn_spells() and cast(fk):
            b = burn_spells()[0]
            if cast(b):
                self.opp_life -= b.dmg * 2

        # refills
        for name in ("Wheel of Fortune", "Timetwister"):
            c = in_hand(name)
            if c and len(self.hand) <= 2 and cast(c) and not countered(c):
                self.hand = []
                self.draw(7)
                sources = []
                # allow one-mana burn from a fresh Wheel with any leftover... none

        # animate a Factory as an extra attacker if nothing else to do with mana
        if not second and any(l.name == "Mishra's Factory" for l in self.lands) and \
                "C" in sources and not any(c.card.name == "Factory" for c in self.creatures):
            if self.turn >= 2 and (not opp_stops_ground or self.opp_life <= 6):
                sources.remove("C")
                fac = OurCreature(Card("Factory", "creature", 0, "", 2, 2))
                fac.summoning_sick = False
                fac.temp = True
                self.creatures.append(fac)
        self._leftover = sources

    def attack(self):
        if self.opp_life <= 0:
            return
        attackers = [c for c in self.creatures if not c.summoning_sick]
        if self.moat:
            attackers = [c for c in attackers if c.card.flying]
        blockers = list(self.opp_creatures)
        for a in sorted(attackers, key=lambda c: -c.power):
            # opponent blocks if a blocker kills it and survives, or chumps when at lethal risk
            good = [b for b in blockers if (b.flying or not a.card.flying) and
                    (b.power >= a.tough and (b.tough > a.power or b.first_strike))]
            if good and self.opp.blocks:
                continue  # stay home; burn clears the blocker first
            chump = [b for b in blockers if (b.flying or not a.card.flying)]
            if chump and self.opp_life <= a.power + 2 and self.opp.blocks:
                b = chump[0]
                blockers.remove(b)
                if a.power >= b.tough:
                    self.opp_creatures.remove(b)
                continue
            self.opp_life -= a.power
            self.log.append(f"T{self.turn} {a.card.name} hits for {a.power}")
        # factories go back to being lands
        self.creatures = [c for c in self.creatures if not getattr(c, "temp", False)]

    # ---- driver ---------------------------------------------------------
    def play(self, max_turns=14):
        self.extra_turn = False
        if not self.on_play:
            self.turn = 0
            self.opp_turn_pre()
        while self.turn < max_turns:
            self.play_turn()
            if self.opp_life <= 0:
                return True, self.turn
            if self.life <= 0:
                return False, self.turn
            if self.extra_turn:
                self.extra_turn = False
                self.play_turn()
                if self.opp_life <= 0:
                    return True, self.turn
            self.opp_turn()
            if self.life <= 0:
                return False, self.turn
            if self.opp_life <= 0:
                return True, self.turn
        # long game: control decks win, aggro decks have run out
        return (self.opp.name.startswith("The Deck") is False and self.opp_life < self.life), max_turns

    def opp_turn_pre(self):
        """Opponent on the play gets a turn-1 before us."""
        self.turn = 1
        for c in self.opp.schedule.get(1, []):
            if self.rng.random() < self.opp.creature_prob:
                self.opp_creatures.append(OppCreature(**{**c.__dict__, "sick": True}))
        self.turn = 0


# post-board configurations for build A, tested against the matchups they are meant for
SIDEBOARD_PLANS = {
    "A vs WW:   -2 Vise -1 Mutation +3 Earthquake": (
        {"Unstable Mutation": 2, "Earthquake": 3}, [1]),
    "A vs Zoo:  -2 Vise +2 Earthquake": (
        {"Unstable Mutation": 3, "Earthquake": 2}, [4]),
    "A vs Deck: -2 Swords -1 Mutation +2 Vise +1 Fork (REB not modelled)": (
        {"Unstable Mutation": 2, "Black Vise": 4, "Fork": 1, "Swords to Plowshares": -2}, [0]),
}


def run_sideboard(n, seed):
    rng = random.Random(seed)
    print("\nPost-board (build A) vs the matchup each plan targets:\n")
    for label, (extra, opp_idxs) in SIDEBOARD_PLANS.items():
        deck = build_deck(extra)
        for idx in opp_idxs:
            wins = 0
            for i in range(n):
                g = Game(deck, OPPONENTS[idx](), rng, on_play=(i % 2 == 0))
                w, _ = g.play()
                wins += w
            print(f"{label:<66} {wins / n * 100:5.1f}%")


def run(n, seed):
    rng = random.Random(seed)
    results = {}
    for bname, extra in BUILDS.items():
        deck = build_deck(extra)
        for opp_fn in OPPONENTS:
            wins = 0
            turns = []
            for i in range(n):
                opp = opp_fn()
                g = Game(deck, opp, rng, on_play=(i % 2 == 0))
                w, t = g.play()
                wins += w
                if w:
                    turns.append(t)
            results[(bname, opp_fn().name)] = (wins / n, sum(turns) / max(1, len(turns)))
    return results


def trace(opp_idx, seed):
    rng = random.Random(seed)
    deck = build_deck(next(iter(BUILDS.values())))
    g = Game(deck, OPPONENTS[opp_idx](), rng, on_play=True)
    g.extra_turn = False
    print("vs", g.opp.name)
    while g.turn < 14 and g.life > 0 and g.opp_life > 0:
        n = len(g.log)
        g.play_turn()
        print(f"T{g.turn}: {', '.join(x.split(' ', 1)[1] for x in g.log[n:]) or '-'}")
        print(f"    hand={[c.name for c in g.hand]}")
        print(f"    board={[(c.card.name, c.power, c.tough) for c in g.creatures]} lands={len(g.lands)} "
              f"life={g.life} opp={g.opp_life} opp board={[c.name for c in g.opp_creatures]}"
              f"{' MOAT' if g.moat else ''}{' ABYSS' if g.abyss else ''}")
        if g.opp_life <= 0:
            break
        g.opp_turn()
        print(f"  opp turn -> life={g.life} opp={g.opp_life} opp board={[c.name for c in g.opp_creatures]}")
    print("WIN" if g.opp_life <= 0 else "LOSS" if g.life <= 0 else "timeout")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--trace", metavar="OPP", help="print one game vs opponent index 0-4 using build A")
    ap.add_argument("--sideboard", action="store_true", help="also run the post-board plans")
    args = ap.parse_args()
    if args.trace is not None:
        trace(int(args.trace), args.seed)
        return
    res = run(args.n, args.seed)
    opps = [o().name for o in OPPONENTS]
    w = max(len(b) for b in BUILDS)
    print(f"{args.n} games per cell, win% (avg kill turn)\n")
    print(" " * (w + 2) + " | ".join(f"{o[:22]:>22}" for o in opps) + " |  mean")
    for b in BUILDS:
        cells = [res[(b, o)] for o in opps]
        mean = sum(c[0] for c in cells) / len(cells)
        print(f"{b:<{w}}  " + " | ".join(f"{c[0]*100:5.1f}% (t{c[1]:4.1f})   " for c in cells) + f" | {mean*100:5.1f}%")
    if args.sideboard:
        run_sideboard(args.n, args.seed)


if __name__ == "__main__":
    main()
