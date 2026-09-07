# Kingshot Advanced Truegold Research planner

`tree.json` is the full 92-tech Advanced Truegold Research tree (per-level cost,
time, effect, prerequisites) scraped from kingshotdata.com on 2026-09-07.

`plan.py [war_academy_tg_level] [dust_budget] [day_budget] [tempered_tg]` buys
(tech, level) steps cheapest-per-weighted-stat first while respecting every
prerequisite gate. Edit `WEIGHTS` / `TROOP` at the top to match your army.

    python3 kingshot/plan.py 6 15000 400

## Cost structure (War Academy TG6, no Tempered Truegold needed)

Every combat tech is +3% per level; the dust price per level is what changes:

| Step                     | dust/level | hours/level |
|--------------------------|-----------:|------------:|
| Tier I  L1-3             |         46 |          16 |
| Tier I  L4-6             |         59 |          21 |
| Tier II L1-3             |         73 |          24 |
| Tier I  L7-9             |         78 |          28 |
| Tier II L4-6             |         94 |          31 |
| Tier I  L10              |        104 |          38 |
| Tier II L7-9             |        125 |          41 |
| Tier II L10              |        166 |          55 |

Gates: Tier I L3/L6/L10 need Limited Supply L3/L6/L10. Tier II L3/L6/L10 need
Truegold Provisions I L3/L6/L10, which needs all three Health I techs at that
level, which chain back through Lethality -> Defense -> Attack of each troop.
So the tree is bought in waves of "all 13 techs to level N".

## Wave plan (cumulative)

| Wave                          | dust | days | cum dust | cum days |
|-------------------------------|-----:|-----:|---------:|---------:|
| Econ: 7 economy nodes to L10  | 2330 |   41 |     2330 |       41 |
| A: Tier I  x13 to L3          | 1794 |   26 |     4124 |       67 |
| B: Tier I  x13 to L6          | 2301 |   34 |     6425 |      101 |
| C: Tier II x13 to L3          | 2847 |   39 |     9272 |      140 |
| D: Tier I  x13 to L9          | 3042 |   46 |    12314 |      185 |
| E: Tier II x13 to L6          | 3666 |   50 |    15980 |      236 |
| F: Tier I  x13 to L10         | 1352 |   21 |    17332 |      256 |
| G: Tier II x13 to L9          | 4875 |   67 |    22207 |      323 |
| H: Tier II x13 to L10         | 2158 |   30 |    24365 |      353 |

Tier III+ needs War Academy TG7 and Tempered Truegold (Tier III alone: 14.6k
dust, 416 Tempered Truegold, 343 days).
