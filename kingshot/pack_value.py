#!/usr/bin/env python3
"""Value of the $10 select-pack options (3 picks, repeats allowed) in one unit.

Unit: permille of relative stat, the same one gear.py's charm/gear comparison used -- one panel
point on stat s of type t is worth 1000/(100 + panel_t_s), with the panel read off a battle
report's Stat Bonuses block (hero, research and gear included).  A multiplicative x1.05 step on
a base stat is worth ln(1.05)*1000 = 48.8 per stat regardless of the panel.

Truegold sinks (kingshotguide.org/calculator/truegold-cost-chart, war-academy guide):
  * troop building TG8->TG9: 567 Truegold + 79 Tempered Truegold each (Barracks/Stable/Range);
    Town Center TG9 (1,260 + 180 Tempered) is the prerequisite.  A troop TG step multiplies base
    attack and base health by ~1.05 (troops_base.json TG0-5: 4.0/4.9/5.0/5.0/5.1 %; TG6+ is
    extrapolated at 5%).
  * exchange 10 Truegold -> 13 Truegold Dust, up to 200x/day; Dust buys research levels of +3%
    on one stat (tree.json: tier-I nodes 46-104 Dust/level, tier-VI 426-1032 Dust/level).
"""
import math
from gear import CHARM_TABLE, TABLE

ME = {'inf': dict(attack=1952.8, defense=1936.2, lethality=1805.7, health=1802.9),
      'cav': dict(attack=1820.7, defense=1804.7, lethality=1727.4, health=1729.6),
      'arch': dict(attack=1823.5, defense=1804.4, lethality=1745.5, health=1740.1)}
pts = lambda t, s: 1000 / (100 + ME[t][s])

charm = 4 * pts('cav', 'lethality') + 4 * pts('cav', 'health')          # cav L14->15
g_charm, d_charm, _ = CHARM_TABLE[15]
star = 2.75 * (pts('cav', 'attack') + pts('cav', 'defense'))            # cav T3 *1->*2
satin, threads, av, _, _ = TABLE[('Red T3', 2)]
tg9 = 2 * math.log(1.05) * 1000                                         # one type, one TG level
TG_RAW, TG_TEMP, TC_RAW = 567, 79, 1260
dust_per_tg = 1.3
research_lvl = 3 * pts('cav', 'attack')

print(f'reference steps: charm level {charm:.2f}   gear star {star:.2f}   TG9 one type {tg9:.1f} '
      f'(= {tg9/charm:.0f} charm levels)   +3% research level {research_lvl:.2f}')
print()
opts = [
    ('Truegold x54 -> Stable TG9 (raw Truegold binding)', 54 / TG_RAW * tg9),
    ('Truegold x54 -> TG9, TC TG9 amortised over 3 buildings', 54 / (TC_RAW + 3 * TG_RAW) * 3 * tg9),
    # player's frontier 2026-09-13: tier I 9/10 (104 Dust/level), tier II 6/10 (125), tier III 0/10
    # (86 Dust + 2 Tempered).  TG9 buildings are not available until February 2027.
    ('Truegold x54 -> 70 Dust -> tier-III research (86 + 2 Tempered/level)', 54 * dust_per_tg / 86 * research_lvl),
    ('Truegold x54 -> 70 Dust -> tier-I level 10 (104/level)', 54 * dust_per_tg / 104 * research_lvl),
    ('Truegold x54 -> 70 Dust -> tier-II level 7 (125/level)', 54 * dust_per_tg / 125 * research_lvl),
    ('Charm Guide x48', 48 / g_charm * charm),
    ('Charm Design x48', 48 / d_charm * charm),
    ("Artisan's Vision x48", 48 / av * star),
    ('Satin x24,000', 24000 / satin * star),
    ('Gilded Threads x240', 240 / threads * star),
]
for name, v in opts:
    print(f'  {name:70s} {v:6.2f}   ({v/charm:5.2f} charm levels)')
