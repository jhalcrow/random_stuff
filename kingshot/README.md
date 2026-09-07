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

# Battle simulator (castle attack / garrison defense)

`sim.py` is a round-by-round battle engine using the reverse-engineered State of Survival
model that Kingshot shares (kingshotguides.com / kingshotsimulator.com, Absy Labs, the
open-source `request-laurent/sos.battle` and `ryo-HIT-1589/wos-simulator` engines):

    per-troop attack   A_u = base_atk * (1 + atk%) * base_leth * (1 + leth%) / 100
    per-troop defense  D_v = base_hp  * (1 + hp%)  * base_def  * (1 + def%)  / 100
    kills per round    ceil( sqrt(n_u * army_min) * A_u / D_v / 100 * SkillMod(u,v) )
    SkillMod = DamageUp * OppDefenseDown / (OppDamageDown * DefenseUp)

Every troop type hits the enemy's infantry first, then cavalry, then archers (cavalry has a
20% chance to bypass to archers); counters give +10% damage; both sides act simultaneously.
`troops_base.json` holds the hidden base stats (Def and Leth are 10 for every tier; Attack and
Health scale) for T1-T11 x TG0-5; TG6-8 are extrapolated at +5% per level.
`bear_check()` reproduces the published Bear Trap worked example exactly (16,797).

`heroes.py` encodes every legendary through Gen 7 plus the Gen 1 combat epics: expedition
skills at level 5 as SkillMod effect ops (same op adds, different ops multiply; chance-based
skills as expected value) and the exclusive-weapon widget (rally-only or defender-only +15%
special bonus).  `hero_stats.json` (scraped from kingshotdata.com, checked against the in-game
Hero Stats panel) holds each hero's max-star expedition Attack/Defense % and the level-10
weapon's Lethality/Health %.  Max hero gear adds a flat +200% Attack/Defense and +600%
Lethality/Health on top (verified in-game).  All of it applies to the hero's own troop type and
is NOT in the profile Bonus Overview.  Base values scale hard by generation: Gen 1 epics 140%,
Amadeus 260%, Gen 4 370%, Gen 6 540%, Gen 7 650% Attack/Defense; weapon Lethality/Health 62.5%
(Gen 1) to 160.5% (Gen 7).  A march holds exactly one infantry, one cavalry and one archer
hero, so `heroes.trios()` enumerates the 900 legal lineups.

    python3 run.py              # rank all 3,654 trios for rally attack, solo attack, garrison
    python3 analyze.py          # picks vs community meta, ratio search, reinforcement skills
    python3 joint.py 40         # optimise trio and troop ratio together
    python3 elo.py 300          # Monte Carlo round-robin of top lineups, Elo by Bradley-Terry
    PROC_SCALE=0.5 python3 ...  # discount chance-based skills to half their expected value

Account stats are the `USER_STATS` block in `sim.py` (from the Bonus Overview screenshot).
The opponent is a mirror of those stats against a panel of meta lineups.

`battle_mc()` rolls chance skills once per round at squad level and fires timed skills on their
schedule (`heroes.PROC_SPEC`), instead of using expected values.

Model caveats: TG6-8 troop skills are not modelled (symmetric on both sides); Sophia's
Terror and Alcar's infantry skills carry large expected values and drive several results, so
compare the PROC_SCALE=1.0 / 0.75 / 0.5 rankings before trusting a lineup; rally and garrison
sizes are set equal to your march (144,200), and only ratios were searched.
