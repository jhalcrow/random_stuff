"""Card database and decklists for the Atlantic 93/94 arena.

Only the cards in the decks below are implemented. Each card has a type set,
a mana cost string ("2UU", "XR", "0"), P/T for creatures, keywords, and an
'effect' key the engine dispatches on.
"""
from dataclasses import dataclass, field

COLOR_OF = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}


@dataclass(frozen=True)
class CardDef:
    name: str
    types: frozenset
    cost: str = "0"
    power: int = 0
    tough: int = 0
    kw: frozenset = frozenset()
    produces: str = ""       # lands / mana artifacts
    effect: str = ""         # engine handler key
    targets: str = ""        # 'any' | 'creature' | 'player' | 'spell' | 'artifact' | 'permanent' | 'land' | 'gycard' | ''
    text: str = ""

    @property
    def colors(self):
        return frozenset(COLOR_OF[c] for c in self.cost if c in COLOR_OF)

    @property
    def is_creature(self):
        return "creature" in self.types

    @property
    def is_land(self):
        return "land" in self.types

    @property
    def is_instant(self):
        return "instant" in self.types

    @property
    def cmc(self):
        n = 0
        num = ""
        for ch in self.cost:
            if ch.isdigit():
                num += ch
            elif ch == "X":
                pass
            else:
                n += 1
        return n + (int(num) if num else 0)


def C(name, types, cost="0", p=0, t=0, kw=(), produces="", effect="", targets="", text=""):
    return CardDef(name, frozenset(types.split()), cost, p, t, frozenset(kw), produces, effect, targets, text)


DB = {}


def add(*cards):
    for c in cards:
        DB[c.name] = c


add(
    # ---- lands ----
    C("Volcanic Island", "land", produces="UR"),
    C("Plateau", "land", produces="RW"),
    C("Tundra", "land", produces="UW"),
    C("Underground Sea", "land", produces="UB"),
    C("Badlands", "land", produces="BR"),
    C("Taiga", "land", produces="RG"),
    C("Scrubland", "land", produces="WB"),
    C("Island", "land", produces="U"),
    C("Mountain", "land", produces="R"),
    C("Plains", "land", produces="W"),
    C("Swamp", "land", produces="B"),
    C("Forest", "land", produces="G"),
    C("City of Brass", "land", produces="WUBRG", text="1 damage to you when tapped"),
    C("Mishra's Factory", "land", produces="C", effect="factory", text="1: becomes a 2/2 artifact creature until end of turn"),
    C("Strip Mine", "land", produces="C", effect="strip", targets="land", text="T, sacrifice: destroy target land"),
    C("Library of Alexandria", "land", produces="C", effect="library", text="T: draw a card if you have exactly 7 cards in hand"),
    # ---- mana artifacts ----
    C("Black Lotus", "artifact", "0", produces="LOTUS", text="sacrifice: add three mana of one colour"),
    C("Mox Sapphire", "artifact", "0", produces="U"),
    C("Mox Ruby", "artifact", "0", produces="R"),
    C("Mox Pearl", "artifact", "0", produces="W"),
    C("Mox Jet", "artifact", "0", produces="B"),
    C("Mox Emerald", "artifact", "0", produces="G"),
    C("Sol Ring", "artifact", "1", produces="CC"),
    # ---- creatures ----
    C("Savannah Lions", "creature", "W", 2, 1),
    C("Serendib Efreet", "creature", "2U", 3, 1, ["flying"], text="upkeep: 1 damage to you"),
    C("White Knight", "creature", "WW", 2, 2, ["first strike", "pro-black"]),
    C("Order of Leitbur", "creature", "WW", 2, 2, ["pro-black"], text="W: first strike until end of turn (auto in combat)"),
    C("Serra Angel", "creature", "3WW", 4, 4, ["flying", "vigilance"]),
    C("Atog", "creature", "1R", 1, 2, text="sacrifice an artifact: +2/+2 until end of turn"),
    C("Ornithopter", "artifact creature", "0", 0, 2, ["flying"]),
    C("Su-Chi", "artifact creature", "4", 4, 4),
    C("Hypnotic Specter", "creature", "1BB", 2, 2, ["flying"], text="combat damage to a player: they discard at random"),
    C("Juzam Djinn", "creature", "2BB", 5, 5, text="upkeep: 1 damage to you"),
    C("Sedge Troll", "creature", "2R", 2, 2, text="+1/+1 while you control a Swamp"),
    C("Kird Ape", "creature", "R", 1, 1, text="+1/+2 while you control a Forest"),
    C("Erhnam Djinn", "creature", "3G", 4, 5),
    C("Ball Lightning", "creature", "RRR", 6, 1, ["haste", "trample"], text="sacrificed at end of turn"),
    C("Argothian Pixies", "creature", "1G", 2, 1, text="can't be blocked by artifact creatures"),
    # ---- burn / removal ----
    C("Lightning Bolt", "instant", "R", effect="damage3", targets="any"),
    C("Chain Lightning", "sorcery", "R", effect="damage3", targets="any"),
    C("Psionic Blast", "instant", "2U", effect="psiblast", targets="any", text="4 damage to target, 2 to you"),
    C("Fireball", "sorcery", "XR", effect="fireball", targets="any", text="X damage to target"),
    C("Earthquake", "sorcery", "XR", effect="earthquake", text="X damage to each non-flying creature and each player"),
    C("Swords to Plowshares", "instant", "W", effect="swords", targets="creature", text="exile target creature; its controller gains life equal to its power"),
    C("Terror", "instant", "1B", effect="terror", targets="creature", text="destroy target nonblack nonartifact creature"),
    C("Disenchant", "instant", "1W", effect="disenchant", targets="artifact-or-enchantment"),
    C("Shatter", "instant", "1R", effect="shatter", targets="artifact"),
    C("Chaos Orb", "artifact", "2", effect="orb", targets="permanent", text="1, T: flip; destroy target permanent (90% in this engine). One use."),
    C("Nevinyrral's Disk", "artifact", "4", effect="disk", text="enters tapped. 1, T: destroy all creatures, artifacts and enchantments"),
    # ---- counters ----
    C("Counterspell", "instant", "UU", effect="counter", targets="spell"),
    C("Mana Drain", "instant", "UU", effect="counter", targets="spell"),
    C("Red Elemental Blast", "instant", "R", effect="reb", targets="blue", text="counter target blue spell or destroy target blue permanent"),
    C("Blue Elemental Blast", "instant", "U", effect="beb", targets="red", text="counter target red spell or destroy target red permanent"),
    # ---- card advantage / power ----
    C("Ancestral Recall", "instant", "U", effect="draw3", targets="player"),
    C("Time Walk", "sorcery", "1U", effect="timewalk"),
    C("Timetwister", "sorcery", "2U", effect="twister"),
    C("Wheel of Fortune", "sorcery", "2R", effect="wheel"),
    C("Braingeyser", "sorcery", "XUU", effect="geyser", targets="player"),
    C("Demonic Tutor", "sorcery", "1B", effect="tutor"),
    C("Regrowth", "sorcery", "1G", effect="regrowth", targets="gycard"),
    C("Recall", "sorcery", "XXU", effect="recall", text="discard X, return X cards from graveyard (engine: X=1)"),
    C("Balance", "sorcery", "1W", effect="balance"),
    C("Mind Twist", "sorcery", "XB", effect="mindtwist", targets="player"),
    C("Hymn to Tourach", "sorcery", "BB", effect="hymn", targets="player"),
    C("Dark Ritual", "instant", "B", effect="ritual", text="add BBB"),
    C("Armageddon", "sorcery", "3W", effect="geddon"),
    C("Jayemdae Tome", "artifact", "4", effect="tome", text="4, T: draw a card"),
    # ---- enchantments / auras ----
    C("Crusade", "enchantment", "WW", text="white creatures get +1/+1"),
    C("Moat", "enchantment", "2WW", text="creatures without flying can't attack"),
    C("The Abyss", "enchantment", "3B", text="each upkeep, that player destroys a nonartifact creature they control"),
    C("Black Vise", "artifact", "1", text="opponent's upkeep: damage equal to their hand size minus 4"),
    C("Ivory Tower", "artifact", "1", text="your upkeep: gain life equal to your hand size minus 4"),
    C("Unstable Mutation", "enchantment aura", "U", effect="aura", targets="creature", text="+3/+3; -1/-1 counter each upkeep"),
    C("Giant Growth", "instant", "G", effect="pump3", targets="creature"),
    C("Sylvan Library", "enchantment", "1G", text="(engine: no effect)"),
)


# ---------------------------------------------------------------------------
# Decklists (Atlantic legal: one copy of each restricted card)
# ---------------------------------------------------------------------------

def deck(text):
    out = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        n, name = line.split(" ", 1)
        assert name in DB, name
        out += [name] * int(n)
    assert len(out) == 60, (len(out), text[:40])
    return out


DECKS = {}

DECKS["12 Bolt"] = deck("""
4 Savannah Lions
4 Serendib Efreet
4 Lightning Bolt
4 Chain Lightning
4 Psionic Blast
1 Fireball
4 Swords to Plowshares
3 Unstable Mutation
2 Black Vise
1 Balance
1 Ancestral Recall
1 Time Walk
1 Wheel of Fortune
1 Timetwister
1 Black Lotus
1 Mox Sapphire
1 Mox Ruby
1 Mox Pearl
1 Sol Ring
1 Chaos Orb
4 Mishra's Factory
4 City of Brass
4 Volcanic Island
3 Plateau
2 Tundra
1 Strip Mine
1 Library of Alexandria
""")

DECKS["The Deck"] = deck("""
2 Serra Angel
3 Counterspell
1 Mana Drain
2 Red Elemental Blast
4 Swords to Plowshares
2 Disenchant
1 Lightning Bolt
1 Fireball
2 Moat
1 The Abyss
1 Jayemdae Tome
1 Ancestral Recall
1 Time Walk
1 Timetwister
1 Braingeyser
1 Balance
1 Demonic Tutor
1 Mind Twist
1 Regrowth
1 Recall
1 Chaos Orb
1 Black Lotus
1 Mox Sapphire
1 Mox Pearl
1 Mox Ruby
1 Mox Jet
1 Mox Emerald
1 Sol Ring
1 Library of Alexandria
1 Strip Mine
4 Mishra's Factory
4 Tundra
3 Volcanic Island
2 Underground Sea
1 Scrubland
1 Plateau
3 City of Brass
2 Island
1 Plains
""")

DECKS["White Weenie"] = deck("""
4 Savannah Lions
4 White Knight
4 Order of Leitbur
2 Serra Angel
3 Crusade
4 Swords to Plowshares
2 Disenchant
3 Armageddon
1 Balance
1 Black Lotus
1 Mox Pearl
1 Sol Ring
1 Chaos Orb
1 Ancestral Recall
1 Time Walk
4 Mishra's Factory
1 Strip Mine
1 Library of Alexandria
2 Tundra
1 City of Brass
18 Plains
""")

DECKS["Atog"] = deck("""
4 Atog
4 Ornithopter
4 Su-Chi
4 Lightning Bolt
4 Chain Lightning
2 Psionic Blast
1 Fireball
4 Black Vise
2 Shatter
1 Ancestral Recall
1 Time Walk
1 Wheel of Fortune
1 Black Lotus
1 Mox Sapphire
1 Mox Ruby
1 Mox Pearl
1 Mox Jet
1 Mox Emerald
1 Sol Ring
1 Chaos Orb
1 Strip Mine
1 Library of Alexandria
4 Mishra's Factory
4 Volcanic Island
4 City of Brass
4 Mountain
2 Island
""")

DECKS["Deadguy Ale"] = deck("""
4 Hypnotic Specter
4 Juzam Djinn
4 Sedge Troll
4 Hymn to Tourach
4 Dark Ritual
4 Lightning Bolt
3 Chain Lightning
2 Terror
2 Nevinyrral's Disk
1 Mind Twist
1 Demonic Tutor
1 Black Lotus
1 Mox Jet
1 Mox Ruby
1 Sol Ring
1 Chaos Orb
1 Strip Mine
1 Library of Alexandria
4 Mishra's Factory
4 Badlands
4 City of Brass
5 Swamp
3 Mountain
""")

DECKS["Erhnam Burn'em"] = deck("""
4 Kird Ape
4 Erhnam Djinn
4 Ball Lightning
2 Argothian Pixies
4 Lightning Bolt
4 Chain Lightning
2 Fireball
2 Giant Growth
1 Regrowth
1 Wheel of Fortune
1 Black Lotus
1 Mox Ruby
1 Mox Emerald
1 Sol Ring
1 Chaos Orb
1 Strip Mine
1 Library of Alexandria
4 Mishra's Factory
4 Taiga
4 City of Brass
6 Mountain
5 Forest
2 Forest
""")

PRIMERS = {
    "12 Bolt": """URw aggro-burn. 8 cheap creatures (Lions, Efreet), 12 three-or-four damage burn spells
plus Fireball, 4 Swords for the fat creatures, and power. Plan: creature turn 1-2, then point
burn at the opponent's face and count to 20. Only burn a creature if it is blocking profitably
or racing you. Unstable Mutation goes on Serendib Efreet (a 6/4 flier). Black Vise is for
slow opponents who keep cards in hand. Save Swords for 4+ toughness creatures.""",
    "The Deck": """UWbr control. Counterspells for their key spells (creatures, card draw, Vise), Swords
for creatures, Moat and The Abyss to lock out ground creatures, Serra Angel and Factories to
win. Card advantage from Tome, Ancestral, Braingeyser, Recall. Use Balance when behind on
board or cards. Do not walk into burn at low life; Swords on your own creature gains life
in an emergency. Red Elemental Blast counters blue spells (Ancestral, Psionic Blast,
Timetwister) or destroys Serendib Efreet.""",
    "White Weenie": """Mono-white aggro. Curve out 1-2 drops, Crusade to grow the team, Swords their
blockers, Armageddon when you are ahead on board to lock them out. Order of Leitbur and White
Knight have first strike (Order gets it automatically in this engine) and protection from
black.""",
    "Atog": """UR artifact aggro. Ornithopters, Su-Chi and Factories beat down; Atog sacrifices
artifacts (Moxen, Ornithopters, Vises, Sol Ring) for +2/+2 each to finish games: an
unblocked Atog with three artifacts to eat is 7 damage. Bolts and Chains kill blockers or go
face. Black Vise punishes slow hands.""",
    "Deadguy Ale": """BR disruption-aggro. Dark Ritual into Hypnotic Specter or Juzam Djinn, Hymn and
Mind Twist to strip their hand, Bolts to clear blockers, Terror for big creatures, Disk to reset
a board you are losing. Juzam costs you 1 life a turn; race hard.""",
    "Erhnam Burn'em": """RG aggro-burn. Kird Ape turn 1 (2/3 with a Forest/Taiga), Erhnam Djinn 4/5 on
turn 3-4, Ball Lightning for 6 hasty trample damage, and 10 burn spells to clear the way or
finish. Giant Growth wins combats or saves a creature from Bolt.""",
}
