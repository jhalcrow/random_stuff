"""Kingshot hero expedition skills at level 5, encoded as SkillMod effects.

Effect tuples: (kind, value_percent, scope).  Kinds map to the engine's effect-op categories;
values of the SAME kind add together and are applied once, different kinds multiply
(kingshotguides.com: "same effect_op -> add, different -> multiply").  Chance-based skills use
their own op (kind prefixed proc_) so they multiply with everything.
  DamageUp      leth (op101)  atk / dmg (op102)  proc (expected value of chance-based extra damage)
  DefenseUp     taken (op111, incoming x (1-v))  def (op112)  hp (op113)  proc_taken
  OppDamageDown e_atk (201)  e_leth (202)  e_dmg (203)  proc_e_dmg   -> enemy damage x (1-v)
  OppDefDown    e_taken (211)  e_def (212)  proc_e_taken            -> our damage x (1+v)
  scope: 'all' or a troop type ('inf', 'cav', 'arch').  For dmg/taken/hp/def it is OUR troop
         type; for enemy_taken it is the ENEMY target type ('all' = any).

Chance-based skills are encoded as expected value (e.g. 40% chance of +50% damage -> dmg 20).
"proc for N turns" skills use steady-state uptime.  Values follow kingshotdata.com skill text
(Sept 2026) and the ordering in the community simulator's skill list.

Widget: exclusive-weapon expedition skill.  ('rally'|'defender', stat, 15).  Rally widgets only
apply when the hero is in the lineup of a player INITIATING a rally; defender widgets only when
the hero is in a garrison lineup.  They are Special Bonuses: they multiply (100 + stat%).

Per-hero expedition stats (star ATK/DEF %, weapon Lethality/Health %) live in hero_stats.json.
"""

EPIC = 'epic'
LEG = 'legendary'

HEROES = {
    # ---------------- Gen 1 legendaries ----------------
    'Amadeus': dict(gen=1, rarity=LEG, type='inf', widget=('rally', 'attack', 15), skills=[
        ('Battle Ready', [('leth', 25, 'all')]),
        ('Way of the Blade', [('atk', 25, 'all')]),
        ('Unrighteous Strike', [('proc', 20, 'all')]),          # 40% chance +50%
    ]),
    'Helga': dict(gen=1, rarity=LEG, type='inf', widget=('rally', 'lethality', 15), skills=[
        ('Oath of Guardian', [('proc_taken', 20, 'all')]),           # 40% chance -50% taken
        ('Echoes of Valhalla', [('atk', 25, 'all')]),
        ("Nature's Balance", [('leth', 25, 'all')]),
    ]),
    'Jabel': dict(gen=1, rarity=LEG, type='cav', widget=('defender', 'lethality', 15), skills=[
        ('Rally Flag', [('proc_taken', 20, 'all')]),                 # 40% chance -50% taken
        ("Hero's Domain", [('proc', 25, 'all')]),                # 50% chance +50%
        ('Youthful Rage', [('leth', 25, 'all')]),
    ]),
    'Saul': dict(gen=1, rarity=LEG, type='arch', widget=('defender', 'attack', 15), skills=[
        ('Taskforce Training', [('def', 10, 'all'), ('hp', 15, 'all')]),
        ('Resourceful', []),                                    # construction, no combat effect
        ('Positional Battler', [('leth', 25, 'all')]),
    ]),
    # ---------------- Gen 1 epics (2 skills, no widget) ----------------
    'Chenko': dict(gen=1, rarity=EPIC, type='cav', widget=None, skills=[
        ('Stand of Arms', [('leth', 25, 'all')]),
        ('Shield Wall', [('taken', 20, 'all')]),
    ]),
    'Yeonwoo': dict(gen=1, rarity=EPIC, type='arch', widget=None, skills=[
        ('On Guard', [('leth', 25, 'all')]),
        ('Well-Traveled', []),
    ]),
    'Amane': dict(gen=1, rarity=EPIC, type='arch', widget=None, skills=[
        ('Tri-Phalanx', [('atk', 25, 'all')]),
        ('Exorcism', []),
    ]),
    'Gordon': dict(gen=1, rarity=EPIC, type='cav', widget=None, skills=[
        ('Super Nutrients', [('hp', 25, 'all')]),
        ('Trash Talk', [('atk', 25, 'all')]),
    ]),
    'Howard': dict(gen=1, rarity=EPIC, type='inf', widget=None, skills=[
        ("Defenders' Edge", [('taken', 20, 'all')]),
        ('Weaken', [('e_atk', 20, 'all')]),
    ]),
    'Quinn': dict(gen=1, rarity=EPIC, type='arch', widget=None, skills=[
        ('Sixth Sense', [('taken', 20, 'all')]),
        ('Precision Shot', [('proc', 25, 'all')]),               # 50% chance +50%
    ]),
    'Fahd': dict(gen=1, rarity=EPIC, type='cav', widget=None, skills=[
        ('Desert Eclipse', [('e_dmg', 20, 'all')]),
        ('Pathfinder', []),
    ]),
    # ---------------- Gen 2 ----------------
    'Zoe': dict(gen=2, rarity=LEG, type='inf', widget=('defender', 'attack', 15), skills=[
        ('Sundering Wound', [('proc', 24, 'all')]),              # 20% chance, 40%/turn x3 turns
        ('Charisma', [('atk', 25, 'all')]),
        ('Infinite Arsenal', [('proc_e_taken', 25, 'all')]),     # 50% chance +50% taken
    ]),
    'Hilde': dict(gen=2, rarity=LEG, type='cav', widget=('defender', 'health', 15), skills=[
        ('Noble Path', [('atk', 15, 'all'), ('def', 10, 'all')]),
        ('Elixir of Strength', [('proc', 25, 'all')]),           # 25% chance 200%
        ('Trial by Fire', [('proc_taken', 20, 'all')]),              # 40% chance -50% taken
    ]),
    'Marlin': dict(gen=2, rarity=LEG, type='arch', widget=('rally', 'lethality', 15), skills=[
        ('Wild Card', [('proc', 20, 'all')]),                    # 40% chance +50%
        ('Rumhead', [('proc_e_dmg', 18, 'all')]),                # 20% chance -50% enemy leth, 2 turns
        ('Dynamo', [('proc', 25, 'all')]),                       # 50% chance +50%
    ]),
    # ---------------- Gen 3 ----------------
    'Eric': dict(gen=3, rarity=LEG, type='inf', widget=('defender', 'defense', 15), skills=[
        ('Holy Warrior', [('e_atk', 20, 'all')]),
        ('Conviction', [('taken', 20, 'all')]),
        ('Exhortation', [('hp', 25, 'all')]),
    ]),
    'Petra': dict(gen=3, rarity=LEG, type='cav', widget=('rally', 'attack', 15), skills=[
        ('Evil Eye', [('proc_e_taken', 25, 'all')]),             # 50% chance +50% taken
        ('The Favor', [('proc', 25, 'all')]),                    # 50% chance +50% attack
        ('The Shield', [('proc_taken', 20, 'all')]),                 # 40% chance -50% taken
    ]),
    'Jaeger': dict(gen=3, rarity=LEG, type='arch', widget=('defender', 'health', 15), skills=[
        ('The Tempest', [('proc', 20, 'all')]),                  # 20% chance +40% for 3 turns (~49% uptime)
        ('The Resistance', [('proc_e_dmg', 18, 'all')]),         # 20% chance -50% enemy leth 2 turns
        ('The Celebration', [('hp', 25, 'all')]),
    ]),
    # ---------------- Gen 4 ----------------
    'Alcar': dict(gen=4, rarity=LEG, type='inf', widget=('defender', 'health', 15), skills=[
        ('Rescuing Hands', [('proc_taken', 28, 'inf'), ('proc_taken', 28, 'arch')]),   # -70% for 2 of every 5 turns
        ('Praetorian Will', [('dmg', 100, 'inf'), ('dmg', 10, 'cav'), ('dmg', 10, 'arch')]),
        ('Carpe Diem', [('proc', 60, 'inf'), ('proc_e_taken', 25, 'all')]),   # infantry hits: +60%, target +25% taken 1 turn
    ]),
    'Margot': dict(gen=4, rarity=LEG, type='cav', widget=('defender', 'lethality', 15), skills=[
        ('Warbringer', [('atk', 25, 'all')]),
        ('Subterfuge', [('proc_taken', 20, 'all')]),                 # 20% dodge
        ('Sleight Hand', [('proc', 50, 'cav')]),                 # 25% chance extra 200% attack
    ]),
    'Rosa': dict(gen=4, rarity=LEG, type='arch', widget=('rally', 'lethality', 15), skills=[
        ('Chaos Gambit', [('proc', 20, 'all')]),                 # 40% chance +50%
        ('Rose of War', [('e_dmg', 20, 'all')]),
        ('Golden Rhythm', [('atk', 30, 'arch')]),
    ]),
    # ---------------- Gen 5 ----------------
    'Long Fei': dict(gen=5, rarity=LEG, type='inf', widget=('defender', 'attack', 15), skills=[
        ('Mighty Paragon', [('proc_taken', 20, 'all')]),             # 40% chance -50%
        ('Celestial Sustenance', [('def', 25, 'all')]),
        ('Art of War', [('proc', 25, 'all')]),                   # 25% chance 200%
    ]),
    'Thrud': dict(gen=5, rarity=LEG, type='cav', widget=('rally', 'lethality', 15), skills=[
        ('Battle Hunger', [('taken', 15, 'inf'), ('taken', 15, 'arch'), ('dmg', 15, 'inf'), ('dmg', 15, 'arch')]),
        ('Reckless Charge', [('proc', 20, 'cav')]),              # 20% chance +100%
        ('Ancestral Guidance', [('proc', 12.5, 'all'), ('proc_taken', 12.5, 'all')]),  # 2 of every 4 turns
    ]),
    'Vivian': dict(gen=5, rarity=LEG, type='arch', widget=('defender', 'defense', 15), skills=[
        ('Crouching Tiger', [('e_taken', 25, 'all')]),
        ('Focus Fire', [('proc', 25, 'all'), ('proc_e_taken', 4, 'all')]),   # +100% every 4th attack; +15% next hit
        ('Trap of Greed', [('proc', 15, 'arch')]),               # +60% every 4th attack
    ]),
    # ---------------- Gen 6 ----------------
    'Triton': dict(gen=6, rarity=LEG, type='inf', widget=('defender', 'defense', 15), skills=[
        ('Command of Power', [('def', 25, 'all')]),
        ('Warfare of Power', [('proc', 6, 'all')]),              # +30% skill damage; ~20% of damage is skill EV
        ('Oath of Power', [('hp', 20, 'inf'), ('hp', 30, 'cav'), ('hp', 30, 'arch')]),
    ]),
    'Sophia': dict(gen=6, rarity=LEG, type='cav', widget=('defender', 'lethality', 15), skills=[
        ('Arcane Pact', [('proc_taken', 20, 'all')]),                # 40% chance -50%
        ('Terror Deathblow', [('proc', 100, 'cav')]),            # +200% cav damage on 1 of every 2 turns
        ('Terror Annihilation', [('proc', 37.5, 'all')]),        # +75% vs terrified (1 of 2 turns)
    ]),
    'Yang': dict(gen=6, rarity=LEG, type='arch', widget=('rally', 'lethality', 15), skills=[
        ('Avalanche', [('proc', 25, 'all')]),                    # extra 100% strike every 4 turns
        ('Ice Zone', [('proc', 40, 'arch')]),                    # 40% chance +100%
        ('Ambush', [('proc', 20, 'all')]),                       # 40% chance +50%
    ]),
    # ---------------- Gen 7 ----------------
    'Charles': dict(gen=7, rarity=LEG, type='inf', widget=('defender', 'health', 15), skills=[
        ('Intimidation', [('e_leth', 20, 'all')]),
        ('Iron Bodies', [('taken', 20, 'all')]),
        ('Great Justice', [('hp', 25, 'all')]),
    ]),
    'Ava': dict(gen=7, rarity=LEG, type='cav', widget=('rally', 'lethality', 15), skills=[
        ('Dissolution', [('e_def', 25, 'all')]),
        ('Chiaroscuro', [('proc_e_taken', 25, 'all')]),          # +50% taken for 2 of every 4 turns
        ('Light and Cold', [('leth', 25, 'all')]),
    ]),
    'Wee & Woo': dict(gen=7, rarity=LEG, type='arch', widget=('defender', 'attack', 15), skills=[
        ('Artillerymen', [('atk', 15, 'all'), ('leth', 10, 'all')]),
        ('Chain Shelling', [('e_taken', 30, 'arch'), ('e_taken', 25, 'inf')]),
        ('Boom Boom', [('proc', 25, 'all')]),                    # 50% chance +50%
    ]),
}

LEGENDARIES = [h for h, d in HEROES.items() if d['rarity'] == LEG]
BY_TYPE = {t: [h for h, d in HEROES.items() if d['type'] == t and h != 'Diana'] for t in ('inf', 'cav', 'arch')}


def trios():
    """Every legal lineup: exactly one infantry, one cavalry and one archer hero."""
    import itertools
    return [t for t in itertools.product(BY_TYPE['inf'], BY_TYPE['cav'], BY_TYPE['arch'])]
EPICS = [h for h, d in HEROES.items() if d['rarity'] == EPIC]
COMBAT_HEROES = LEGENDARIES + [h for h in EPICS if h not in ('Fahd',)] + ['Fahd']

# Meta joiner picks (their FIRST skill is what a joiner contributes).
ATTACK_JOINERS = ['Vivian', 'Chenko', 'Yeonwoo', 'Amane']          # +25% enemy taken, +25%, +25%, +25%
DEFENSE_JOINERS = ['Charles', 'Eric', 'Triton', 'Gordon']          # -20% enemy leth, -20% enemy atk, +25% def, +25% hp
