# 12 Bolt (URw Lion Dib Bolt) for LOBSTERCON 2026 — Atlantic 93/94

Main event: ATL Old School, Friday September 18 2026, 9 rounds of Swiss, cut to
Top 16. Atlantic B&R: Fallen Empires legal, Strip Mine / Mind Twist / Mana Drain
restricted, Black Vise and Fork unrestricted, mana burn on, no proxies.

"12 Bolt" = 4 Lightning Bolt + 4 Chain Lightning + 4 Psionic Blast. The shell is
the classic Lion Dib Bolt (a copy took 4th at the last Atlantic LOBSTERCON in
2024). Everything below is legal under the Atlantic list (one copy of every
restricted card).

## Final list (60)

Creatures (8)
- 4 Savannah Lions
- 4 Serendib Efreet

Burn (14)
- 4 Lightning Bolt
- 4 Chain Lightning
- 4 Psionic Blast
- 2 Fireball

Other spells (13)
- 4 Swords to Plowshares
- 3 Unstable Mutation
- 2 Black Vise
- 1 Balance
- 1 Ancestral Recall
- 1 Time Walk
- 1 Timetwister

Artifacts (6)
- 1 Black Lotus
- 1 Mox Sapphire
- 1 Mox Ruby
- 1 Mox Pearl
- 1 Sol Ring
- 1 Chaos Orb

Lands (19)
- 4 Mishra's Factory
- 4 City of Brass
- 4 Volcanic Island
- 3 Plateau
- 2 Tundra
- 1 Strip Mine
- 1 Library of Alexandria

Sideboard (15)
- 3 Earthquake
- 3 Red Elemental Blast
- 3 Blue Elemental Blast
- 3 Disenchant
- 2 Black Vise
- 1 Energy Flux

The one change from the pre-playtest list: Wheel of Fortune became the second
Fireball. In sixteen piloted games Wheel was never good (it refills a burn
opponent, it is a three-mana sorcery into Counterspell, and the deck rarely
empties its hand early enough), while Fireball was the best card against The
Deck (uncounterable X=6 when they tapped out for Tome) and closed two other
games as exact-lethal reach. Fireball is unrestricted in Atlantic.

## How this was tested

Two layers.

1. `sim.py`: a Monte Carlo of the deck against scripted opponents, used to pick
   the five flex slots. Fast, crude, thousands of games.
2. `arena/`: a real two-player rules engine with full Atlantic decklists on both
   sides (The Deck, White Weenie, Atog, Deadguy Ale, Erhnam Burn'em). Each seat
   was piloted by a separate LLM agent through a text interface, making every
   mulligan, land drop, cast, response, block and attack. Sixteen complete games
   were played this way; no game fell back to the scripted bot.

### Monte Carlo (flex slots), 2000 games per cell

```
                               The Deck   White Weenie   Atog    Deadguy   Erhnam/Zoo   mean
A: 3 Mutation + 2 Vise           53%          48%         74%       57%        49%       56%
B: 4 Vise + 1 Fork               58%          44%         69%       53%        36%       52%
C: 4 Mutation + 1 Fork           42%          50%         74%       57%        48%       54%
D: 2 Mutation + 2 Vise + Fork    50%          47%         74%       57%        43%       54%
```

Build A wins on mean and is never worse than second in any column. Four Vises
is the best anti-control build but blanks against creature decks. Post-board
checks: Earthquake lifts White Weenie from 48% to 55%; against Zoo it does
nothing (Kird Ape has 3 toughness, Erhnam 5) so Blue Elemental Blast comes in
there instead.

### Agent-piloted games

Round 1 was played with a data error (Serendib Efreet entered as 3/1 instead of
3/4), so every Efreet died to a Bolt. The corrected round fixed that plus several
interface problems the pilots reported. The corrected round was cut short by a
usage limit after six games.

```
Round 1 (Efreet wrongly 3/1)          Corrected round (Efreet 3/4)
vs The Deck       W (play), draw (draw)  W (play)
vs White Weenie   W, W                   draw at turn limit (play)
vs Atog           L, L                   W (play)
vs Deadguy Ale    W, L                   W (play)
vs Erhnam Burn'em L, W                   L (play), W (draw)
                  5-4-1                  4-1-1
```

Sixteen games is a small sample; read the narratives, not the record.

## What the pilots found, matchup by matchup

**The Deck.** Won on the play twice and drew once (The Deck stabilised at 3 life
after countering seven spells; the game hit the turn limit). What worked: early
burn before they have UU, Fireball when they tap out, Mishra's Factory as the
recurring damage they must answer, Strip Mine on a colour source, Black Vise
even when countered because it eats a Counterspell. What did not: Serendib
Efreet into Red Elemental Blast (0 for 2), Unstable Mutation (countered or
dead), Savannah Lions into Swords, Library of Alexandria (an aggro deck rarely
holds 7). The Deck pilot's own verdict: 12 Bolt sandbagged burn for ten turns
while The Deck sat at 3 to 4 life with one counter up; forcing the counter every
turn wins that game. Board: +2 Vise, +3 REB; -3 Mutation, -2 Swords.

**White Weenie.** 2-0-1. Bolt and Chain kill every two-drop one for one, Efreet
flies over, Lions do the rest. Armageddon on an empty board still hurt (it wiped
Library and five lands), so once ahead, hold a land or two in hand and keep the
Moxen. Black Vise dealt 0 damage in three games; it is the first card out.
Chaos Orb on their one post-Geddon Factory was game-winning. Board: +3
Earthquake; -2 Vise, -1 Mutation.

**Atog.** 0-2 with the broken Efreet, then a win on the play once Efreet could
block and survive Bolt. The lessons: Bolt Atog on sight, Swords Su-Chi, and
Balance is a two-for-three when they Lotus out Su-Chi plus Atog. Their Factories
did most of the damage in the losses, so block or Bolt them. Psionic Blast's
self-damage is real against 11 burn spells plus Vises: use Blast early, never at
3 life. Library is a liability against their four Vises. Board: +3 Disenchant,
+3 BEB, +1 Energy Flux; -2 Vise, -3 Mutation, -1 Balance, -1 Library.

**Deadguy Ale.** 2-1. Hymn to Tourach is the whole matchup: it stripped Swords,
Chaos Orb and Psionic Blast out of a hand that was holding them, and then Juzam
Djinn had no answer. Deploy and fire, do not sandbag; Chain Lightning the turn
one Specter; Efreet's 3-a-turn plus Juzam's own upkeep damage wins the race if
you kept your life total. Board nothing, or +2 Vise for -2 Mutation against the
slow Disk build.

**Erhnam Burn'em.** 2-2. A race decided by mana: Strip Mine on the only colour
source won a game for each side, and the two losses were a mulligan to six with
Factories only, and a Volcanic Island stripped on turn 4. Ball Lightning is the
card to respect: keep a Factory or Lightning Bolt (instant) available in the
block window; Chain Lightning cannot help there. Efreet at 3/4 was "the card I
have no answer to" from the other seat. Black Vise did 12 damage in one game
against a stuck hand and nothing in the others. Board: +3 BEB; -2 Vise, -1
Mutation.

## Play notes

- Point burn at the face unless the creature is actually blocking a Lion or
  out-racing you. Fourteen burn spells is 44 damage; the opponent starts at 20.
- Serendib Efreet is your best card against every deck but The Deck. Cast it
  when they are tapped out or short on red, mutate it, and count its upkeep
  ping into every race.
- Save Swords for Juzam, Erhnam, Su-Chi, Serra and animated Factories. Bolts
  handle everything with 3 toughness or less.
- Strip Mine is restricted, so the one copy should hit a City of Brass, a
  Library, or the only source of a colour, not a random dual. The pilots won
  three games with it.
- Against discard, dump the hand. Against counters, force a counter every turn.
- Mulligan one-land hands even with Sol Ring and Lotus; two losses started
  that way.
- Psionic Blast only exists in Alpha/Beta/Unlimited and Chain Lightning only in
  Legends. No proxies at this event, so make sure you own the twelve.

## Running it yourself

```
python3 sim.py --sideboard              # Monte Carlo flex-slot comparison
cd arena
python3 server.py --a "12 Bolt" --b "The Deck" --games 20 --bots    # engine, bots both sides
python3 server.py --a "12 Bolt" --b "Atog" --games 2 --agents a,b --port 8701
python3 aggregate.py "results/*.json"
```

With `--agents`, the server exposes a long-poll HTTP interface (see
`arena/AGENT_GUIDE.md`) and any two clients, human or model, can play the game.
Full per-turn logs of every piloted game are in `arena/results/`.

## Caveats

- The arena engine implements the ~70 cards in these six decks and nothing
  else. One blocker per attacker, no regeneration, no Chain Lightning
  bounce-back, Mana Drain is a plain Counterspell, Balance choices are
  automatic. Chaos Orb hits 90% of the time.
- Round 1 games predate the Efreet fix and several interface fixes (Factories
  no longer pay for their own animation, tutors re-prompt, cleanup discards are
  chosen by the player, the draw limit is 50 player-turns). The corrected
  White Weenie draw was still under the old 30-turn limit.
- The pilots are language-model agents. They played coherently (the game logs
  are worth reading) but they also sandbagged, misjudged races and misread the
  interface, on both sides of the table.
