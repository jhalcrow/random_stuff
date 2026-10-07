# Kingshot battle simulator — handoff

**Goal.** A battle simulator for Kingshot accurate enough to rank hero lineups and guide Truegold
upgrade decisions, calibrated against real battle reports from two accounts the player owns
(`[PRO]Belisarius`, attacker; `[H8s]Narses`, target) in kingdom 203.

Every number in `battles.py` was read off a screenshot in `reports_raw/`, so a transcription can
always be re-checked rather than trusted — see `reports_raw/MANIFEST.md` for the index.

**Owning both accounts is the whole method.** The game censors a badly-beaten loser's mail, but the
winner's copy is always intact, so no fight is ever lost — and Narses can be reconfigured
(heroes on/off, one at a time) to turn a live game into a controlled experiment.

---

## The one rule that matters

**Never fit a constant to make a metric look better. Find the mechanism.**

Every number in the engine should be traceable to a tooltip, a trigger row, the reference engine,
or a measurement. This has been violated exactly once on purpose — the hero calibration below —
and that exception is quarantined, labelled, and currently failing a test.

Two corollaries learned the hard way:

- **A pre-registered number is only as good as the inputs it was generated from.** Twice a
  pre-registration pointed at the wrong conclusion because the inputs were wrong (the enemy panel
  once, the display convention once). Regenerate, don't recall: *a number that cannot be
  regenerated is not a pre-registration.*
- **Put a control row in every scan.** A scale scan without the heroless fight in it silently
  scaled troop abilities for days (see Retractions).

---

## Files

| file | role |
|---|---|
| `battles.py` | **The data.** Every measured battle, transcribed off the report. Self-checking. |
| `reports.py` | **The argument.** What each fight meant, every retraction, every pre-registration. |
| `allfights.py` | **The scorer.** Feeds a subset of `battles.py` through the engine, prints k. |
| `sim.py` | The engine. Damage core, skills, troop abilities, the calibration layer. |
| `heroes.py` | Hero/skill data, per-level tracks from the site crawl, troop abilities. |
| `ladder.py` | The hero ladder diagnostic (loss + round columns). |
| `killrows.py` | Scores the Battle Details Kills column per skill (kills = 35% of casualties). |
| `elo.py`, `run.py` | Rankings. These run **calibrated**; everything else runs raw. |
| `hero_skills.json` | Crawled L1–L5 skill tracks for 35 heroes (`crawl_heroes.py`). |
| `reports_raw/` | **The primary source.** All 215 report screenshots + `MANIFEST.md` indexing them. |

```
python3 kingshot/battles.py       # verify the data
python3 kingshot/allfights.py     # score every fight, raw
python3 kingshot/killrows.py      # score the per-skill kill rows
HERO_CAL_OFF=0.30 HERO_CAL_DEF=0.60 python3 kingshot/allfights.py    # score calibrated
python3 kingshot/elo.py 300       # rankings (calibrated by default)
```

---

## What is established

**The damage core is right.** `dead = sqrt(n_u × army_min) × A_u / D_v / 100 × SkillMod`, with
`A = base_atk×(1+atk%)×base_leth×(1+leth%)/100` and the matching defensive product. With both
sides heroless it scores **k 1.04–1.07** on loss totals *and* matches the round count (85–90
observed against 90.6 simulated). That is two independent observables, not one.

**The panel reconstruction is exact.** A hero adds `expedition_attack + 200` to attack *and*
defense of his own troop type, and `weapon_lv10 + 600` to lethality *and* health. Predicted to the
decimal before the report arrived on **seven consecutive heroes** across three troop types.

**Skill combination is additive, from the source.** The reference engine (`sos.battle`,
`Skill.java` / `Fight.java`) walks every skill into ONE running coefficient per channel
(`coef = coef + value/100`) and uses exactly two numbers per attack. `sim._prod` used to multiply a
factor per stat category *and per proc name*. Fixing it took rms log err over all fights from
0.843 to 0.499 — adopted on the source, not the fit.

**Trigger rows are a clock, and it is the good observable.** A periodic skill dates a fight
exactly: Yang's Avalanche (1-in-4) and Sophia's Terror Deathblow (1-in-2) are two independent
deterministic clocks. Round counts carry ~7% relative noise against 15–56% for loss totals.

**Reading the panel.** Zero-trigger rows are omitted entirely, so row position is not a stable
index. A scope-gated skill whose troop type is *absent* reads **1**, not 0 (measured twice).
`proc_taken` is rolled more than once per round — proved by inequality, since Unyielding Shield
fired 66 times at chance .375 in a fight that lasted ~90 rounds.

**The Kills column is a per-strike measurement, and it agrees.** Every number the game labels
"kills" -- the skull on the summary line and the Kills column of Battle Details -- counts only the
**Injured** bucket, 35.0% of casualties (Terry's defence: skull 3,408 = 0.35 × his 9,734). Scored
on that basis (`killrows.py`), the troop-ability strikes land on the engine per trigger: Assault
Lance median 0.97 over eight fights, Howling Wind 1.07-1.11 in the heroless, Yang, no-cavalry and
Long Fei fights. Those strikes *are* base cavalry and archer damage, so this confirms the damage
core, front-line targeting and `sqrt(n × army_min)` at the level of a single strike -- an
observable no loss total can supply.

**Sizing an experiment.** Power *improves* as the march shrinks, because a closer fight lasts
longer. At 10,000 troops a fight ends in four rounds, Avalanche fires once, and the loss total is
a two-digit number at 22% noise. **Size calibration marches for 30+ rounds while still winning**
— 400–600 against this Narses.

---

## The hero calibration — RETIRED: it was a bug

The "hero over-credit" was a unit-convention bug, found on a fresh read of `_split_effects`
next to `apply_site_magnitudes()`. `heroes.py` stores rolled procs as **expected values**
(Ice Zone `40` = 0.40 × 100) and `_split_effects` divides by uptime to recover the magnitude;
the crawl's `apply_site_magnitudes()` overwrote those EVs with the site's raw **magnitudes**, and
the division stayed. Every chance/periodic proc went live at `magnitude / uptime` — Ice Zone
+250%, Avalanche +400%, Terror Deathblow +400% — while flat auras were untouched.

Fixed at the source (`apply_site_magnitudes` targets `magnitude × uptime` for any skill in
`PROC_SPEC`). A second convention split sits on the site's side: for skills worded "40% chance of
… by 50%" the site's per-level track is the **chance**, not the magnitude — seven skills, flagged
in `heroes.SITE_TRACK_IS_CHANCE`, including Jabel's Rally Flag. **Raw engine, zero fitted constants:** the original 10k ladder goes from rms 0.287
to **0.048** (flat: 1.08 / 0.96 / 1.05 / 1.03 / 1.00); all nineteen fights 0.613 → **0.390**,
better than the calibrated engine's 0.395. The calibration layer stays in `sim.py`, off, as a
record. `elo.py` / `run.py` run raw.

**Defence-coefficient form — open, split verdict.** With the proc bug gone, switching the
defensive channel from the SoS reference's `1/(1−c)` to the Kingshot-cited `(1+c)` takes the
nineteen-fight rms to **0.182** and fixes Charles (0.74 → 1.11) — but takes the 10k ladder from
0.048 to 0.280 with one powered miss (Charles+Yang 1k, z +3.4). Linear is the default; the
conflict is recorded at `DEF_RECIP` in `sim.py`; the discriminating test is pre-registered.

**Scoreboard after the 2026-10-07 review: twenty fights, rms log err 0.163, zero fitted
constants** (0.194 on nineteen before it). Two changes, both read off reports:

1. **The trio fight was a units error, not a 2.8× residual.** Its 8,142 is the kills field, so
   his casualties were 8,142 × 2.855 = **23,245**; the engine says ~21,000-23,000 (k 0.91-0.99)
   with the clock right (96-99 rounds against ~90). It is now in `allfights.py`.
2. **Avalanche and Terror Deathblow collapse when their hero's troop type was never brought** --
   both read "1" in exactly that case, while Ice Zone, Ambush and Arcane Pact keep firing. The
   engine used to fire Avalanche anyway, and it is scoped `all`, so a no-archer march got +100%
   on every type every fourth round. `sim.COLLAPSE_IF_ABSENT`; rms 0.186 → 0.160.

Defence form re-checked on the corrected set: linear 0.163, reciprocal 0.422 (the trio fight
alone: 0.91 against 1.51). Linear stays; the 10k ladder (linear 0.272, reciprocal 0.047) is still
the only evidence the other way.

Remaining outliers: Terry 10k all-infantry 1.53, Terry 20k 1.28, Narses 1000 heroless 1.24,
Narses 500 solo 0.81, pure-archer 5k 0.82, Sophia no-cavalry 0.80.

---

## Retractions — do not re-derive these

| claim | why it died |
|---|---|
| "Nothing is ever censored" | False and load-bearing. The loser's mail can be withheld entirely. |
| "The damage core is correct" (first version) | Rested on one k of the form rate × rounds, with rate and rounds erring in opposite directions. Re-established later on two independent observables. |
| "k falls monotonically with hero count" | Four of five ladder rungs sat inside the simulator's own single-draw band. Underpowered; over-read. |
| "The proc channel is 3.3× too strong" | Compared the scale fixing Charles' *losses* against the one fixing Yang's *clock* — different observables. Invalid. |
| proc-vs-aura explains the defensive channel | Charles' auras 1.34×, Sophia's proc 1.48×. Same number. |
| troop share sets the per-hero scale | Sophia's cavalry 20% → 50% of the march moved the scale 0.50 → 0.45, not toward 0.82. |
| one badly-modelled skill carries the error | Removing Terror Deathblow (the largest magnitude in the roster) left the over-credit where it was. |
| saturation by magnitude | Charles has the *larger* modelled defensive multiplier yet needs the *smaller* correction. |
| "Long Fei is under-rated in the rankings" | Stale flag. `apply_site_magnitudes()` had already put his max values in the table. |
| "The trio fight runs 2.8× high" / "his output is ~2× under-modelled with three heroes" | Its observation was the kills field (Injured only, 35%) read as casualties. Corrected, k ≈ 0.9-1.0. |
| Narses' widgets are an unmodelled gap | A padlock means *not owned*. He has essentially none; `widget_default=0.0` was already right. |

---

## Open questions

1. **The two-rules contradiction** (Long Fei fight vs trio) was built on the trio's unit error
   and should be re-derived from scratch before anyone spends time on it.
2. **Infantry damage is unmeasured.** No infantry ability has a Kills row, and infantry is ~17%
   of a mixed march's output, so no loss total pins its base attack. The research advice that
   infantry attack/lethality are nearly worthless rests on `troops_base.json`, not on a fight.
   Both pure-infantry fights still run high (Terry 1.53, Narses 1.15). Test 3 below.
3. **Yang's procs have the right totals and the wrong shape.** Ice Zone fires ~1.6× its 40% and
   books 0.59 of the modelled kills per trigger; Avalanche 0.80 per trigger. Totals match. Ice
   Zone also strikes with zero archers (41 triggers, 686 kills in the trio fight).
4. **Howling Wind runs 1.3-1.5× per strike whenever Charles or Sophia is in the march**, and
   Assault Lance 2.6× in the trio fight, against ~1.0-1.1 otherwise. Something about when the
   soft targets (his cavalry and archers) are reached differs with heroes on. Second-order.
5. **Every calibration fight is a solo march, lopsided 1:4 to 1:170, with no rally, no joiners
   and no widgets.** The research valuations (`gear.py`, `minister_plan.py`) run 1.9M-vs-1.9M
   rallies with joiner skills against an opponent assumed to be 90% of my panel. The engagement
   term is safe at parity (the candidate forms coincide there), but joiner skills, rally widgets
   and the 25-30-round regime are untested.
6. **The valuation panel is stale.** `sim.USER_STATS` is the 2026-09-07 Bonus Overview plus
   *modelled* hero stats (infantry attack 1,020 against 1,102 on the heroless report). Regenerate
   it from a current report before trusting small differences between stats.
7. `elo.py`/`run.py` run `hero_stats=True` + `widget_default=1.0`; `allfights.py` validates the
   opposite. Four skills remain unsourced (`heroes.UNSOURCED`). `sim.PROTECT` is never used.

---

## The next tests, pre-registered (raw engine, both fixes)

**1. Defence form.** Charles only, 1,000 at 500/200/300, heroless Narses 83,620.
Linear: **157** losses (127–191). Reciprocal: **109** (84–136). Non-overlapping.

**2. Composition.** Heroless me vs heroless Narses, only the mix changed:
300/200/0 → he loses **14,775** (12,613–17,073), ~106 rounds; 500/0/500 → **54,527**
(42,306–71,456). Baseline 250/100/150 measured at 16,059. Far off 14,775 means the damage core
itself mis-handles an absent type.

**3. Infantry damage.** Heroless me, **1,000 pure infantry**, vs heroless Narses (83,620 in
thirds). I am wiped, so his casualties measure my infantry's output alone. Engine (panel
`MINE_BARE_V3`): he loses **9,962** (9,664-10,268), ~190 rounds. Regenerate with the panel on the
day; a result near 2× would mean the infantry base attack is wrong and the research advice on
infantry offence with it.

The earlier "Narses with all three heroes" test is superseded: the contradiction it was designed
to resolve was the proc bug.
