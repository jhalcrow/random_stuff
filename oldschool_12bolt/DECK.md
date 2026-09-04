# 12 Bolt (URw Lion Dib Bolt) for LOBSTERCON 2026 — Atlantic 93/94

Main event: ATL Old School, Friday September 18 2026, 9 rounds of Swiss, cut to
Top 16. Atlantic B&R: Fallen Empires legal, Strip Mine / Mind Twist / Mana Drain
restricted, Black Vise and Fork unrestricted, mana burn on, no proxies.

"12 Bolt" = 4 Lightning Bolt + 4 Chain Lightning + 4 Psionic Blast. The shell is
the classic Lion Dib Bolt (a copy took 4th at the last Atlantic LOBSTERCON in
2024). Everything below is legal under the Atlantic list (one copy of every
restricted card).

## Main deck (60)

Creatures (8)
- 4 Savannah Lions
- 4 Serendib Efreet

Burn (13)
- 4 Lightning Bolt
- 4 Chain Lightning
- 4 Psionic Blast
- 1 Fireball

Other spells (14)
- 4 Swords to Plowshares
- 3 Unstable Mutation
- 2 Black Vise
- 1 Balance
- 1 Ancestral Recall
- 1 Time Walk
- 1 Wheel of Fortune
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

## Sideboard (15)

- 3 Earthquake
- 3 Red Elemental Blast
- 3 Blue Elemental Blast
- 3 Disenchant
- 2 Black Vise
- 1 Energy Flux

## Why these flex slots

The 55-card core (creatures, 12 bolts, Fireball, 4 Swords, power, Orb, Balance,
Wheel, Twister, 19 lands) is not really negotiable. The last five slots were
chosen by simulation (`sim.py`, 2000 games per cell, on the play / on the draw
alternating):

```
                               The Deck   White Weenie   Atog    Troll Disco   Erhnam/Zoo   mean
A: 3 Mutation + 2 Vise           48%          37%         62%        53%          38%       47%
B: 4 Vise + 1 Fork               57%          26%         54%        51%          29%       43%
C: 4 Mutation + 1 Fork           42%          35%         59%        51%          38%       45%
D: 2 Mutation + 2 Vise + Fork    49%          30%         57%        51%          34%       44%
```

- Four main-deck Vises (B) is the best anti-control configuration but bleeds
  badly against every creature deck, where Vise is a blank. Two main plus two in
  the board (A) keeps most of the control edge without the aggro cost.
- Unstable Mutation on a Serendib Efreet is a 6-power flier that ends games in
  two swings and dodges Moat; it was the single biggest driver in the aggro
  matchups. A fourth copy (C) mostly produced dead cards when the creature had
  already been Plowed.
- Fork never earned its slot: it is a two-mana card in a deck whose whole plan
  is one-mana spells.

Post-board checks (build A):

```
vs White Weenie:  -2 Vise -1 Mutation +3 Earthquake        37% -> 43%
vs Erhnam/Zoo:    -2 Vise +2 Earthquake                     38% -> 36%   (Kird Ape has 3 toughness, Erhnam 5: bring BEB instead)
vs The Deck:      -2 Swords -1 Mutation +2 Vise +1 Fork     48% -> 58%   (REB is not modelled; it should be better still)
```

## Sideboard guide

- The Deck / Counterburn / any Counterspell deck: +2 Black Vise, +3 Red
  Elemental Blast; -2 Swords to Plowshares, -3 Unstable Mutation. Keep two
  Swords for Serra Angel and animated Factories.
- White Weenie / Goblins / Elves: +3 Earthquake; -2 Black Vise, -1 Unstable
  Mutation. Quake for 2 clears Lions, Knights and Orders while your Efreets
  fly over it.
- Erhnam Burn'em / Zoo / UR aggro: +3 Blue Elemental Blast; -2 Black Vise,
  -1 Unstable Mutation. BEB kills Kird Ape and counters the bolts aimed at your
  x/1 creatures.
- Atog: +3 Disenchant, +3 Blue Elemental Blast, +1 Energy Flux; -2 Black Vise,
  -3 Unstable Mutation, -1 Balance, -1 Timetwister.
- Robots / Workshop: +3 Disenchant, +1 Energy Flux; -2 Black Vise, -2 Unstable
  Mutation.
- Troll Disco / Deadguy / Hymn decks: no changes, or +2 Black Vise for
  -2 Unstable Mutation if they are the slow Disk version.

## Play notes

- Point burn at the face unless the creature is actually blocking a Lion or
  out-racing you. Twelve bolts plus Fireball is 40 damage; the opponent starts
  at 20.
- Serendib Efreet is your best card against The Deck (flies over Moat, and The
  Abyss only eats one creature a turn). Mutate the Efreet, not the Lion, when
  they have Moat.
- Save Swords for Juzam, Erhnam, Su-Chi, Serra and Triskelion. Bolts handle
  everything with 3 toughness or less.
- Strip Mine is restricted, so the one copy should hit a City of Brass or the
  only source of a colour, not a random dual.
- Psionic Blast only exists in Alpha/Beta/Unlimited and Chain Lightning only in
  Legends. No proxies at this event, so make sure you own the twelve.

## Caveats on the numbers

`sim.py` plays our deck for real (draws, mana, colours, summoning sickness,
blocks) but the opponents are stochastic scripts: a creature schedule, a
removal rate that fades as their hand empties, discard, counters and Moat/Abyss
odds. It is good for comparing our own builds and for spotting which matchups
need help; it is not a prediction of your record. Run `python3 sim.py
--trace 1` to watch a game against White Weenie.
