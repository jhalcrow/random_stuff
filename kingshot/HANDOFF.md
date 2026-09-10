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
| `elo.py`, `run.py` | Rankings. These run **calibrated**; everything else runs raw. |
| `hero_skills.json` | Crawled L1–L5 skill tracks for 35 heroes (`crawl_heroes.py`). |
| `reports_raw/` | **The primary source.** All 215 report screenshots + `MANIFEST.md` indexing them. |

```
python3 kingshot/battles.py       # verify the data
python3 kingshot/allfights.py     # score every fight, raw
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

**Final raw scoreboard, all fixes, zero fitted constants: rms log err 0.194** (from 0.613 at the
start of the day). The controlled 500-series lands 0.95–1.13. Every remaining outlier is a march
with a troop type missing.

**The trio fight (my 3 vs his 3, 300/200/0)** now has the right clock (96 vs ~90 rounds) and a
loss total still 2.8× high — a clean per-round-output residual. Every single-type march still
runs high. The composition thread is real and untested heroless.

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
| Narses' widgets are an unmodelled gap | A padlock means *not owned*. He has essentially none; `widget_default=0.0` was already right. |

---

## Open questions

1. **The two-rules contradiction.** Nothing about Narses' account explains it. The model is wrong
   somewhere the calibration is papering over.
2. **The trio fight runs too long** — 172 simulated rounds against ~90 observed. The *first* error
   in that direction; every earlier one had fights ending early. His output is ~2× under-modelled
   when he fields three heroes.
3. **Ice Zone fires without archers.** 41 triggers and 686 kills on a march with zero archers,
   while Avalanche correctly collapsed to 1. Its tooltip says "Yang's **archers**". Seen twice.
4. **Yang's firing rates disagree with his tooltips** (Ice Zone 1.39× nominal, Ambush 0.62×) while
   Sophia's match exactly. Yang is the anomalous hero.
5. **Terry-class fights stay 1.5–3× off** — real opponent, unknown buffs/widgets/research, 10–20k
   troops. Least controlled data in the set. **Do not tune on them.**
6. `elo.py`/`run.py` run `hero_stats=True` + `widget_default=1.0`; `allfights.py` validates the
   opposite. The calibration touches only skill effects so it does not interact, but the base
   stats underneath are unverified.
7. Four skills remain unsourced (Saul/Resourceful, Yeonwoo/Well-Traveled, Amane/Exorcism,
   Fahd/Pathfinder) — `heroes.UNSOURCED`. `Skill.protect()` / `sim.PROTECT` is never implemented.

---

## The next tests, pre-registered (raw engine, both fixes)

**1. Defence form.** Charles only, 1,000 at 500/200/300, heroless Narses 83,620.
Linear: **157** losses (127–191). Reciprocal: **109** (84–136). Non-overlapping.

**2. Composition.** Heroless me vs heroless Narses, only the mix changed:
300/200/0 → he loses **14,775** (12,613–17,073), ~106 rounds; 500/0/500 → **54,527**
(42,306–71,456). Baseline 250/100/150 measured at 16,059. Far off 14,775 means the damage core
itself mis-handles an absent type.

The earlier "Narses with all three heroes" test is superseded: the contradiction it was designed
to resolve was the proc bug.
