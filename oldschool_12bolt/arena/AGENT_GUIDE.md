# Playing a game in the arena

You are piloting one deck of Old School 93/94 Magic (Atlantic rules) against
another player through a text interface. The engine enforces the rules; you
make the decisions.

## Talking to the server

    curl -s http://127.0.0.1:PORT/wait/TOKEN
    curl -s -X POST --data-binary @- http://127.0.0.1:PORT/act/TOKEN <<'ACT'
    land #12
    cast #7 target opp
    attack #15
    ACT

`/wait` blocks until it is your turn to decide, then prints your view of the
game (starting with `=== DECISION: <WINDOW> ===`). If it prints `WAITING`,
just call it again. `/act` submits your actions for the pending decision and
then blocks until your next decision, so you normally only need `/act` calls
after the first `/wait`. When the series is finished the response starts with
`SERIES OVER`.

If a script fails, the response says `!! Your last script failed: ...` and the
same decision is still pending. Actions that ran before the failing line have
already happened. Fix the rest and submit again.

## Decision windows

- `MULLIGAN`: reply `keep` or `mulligan` (Paris mulligan).
- `MAIN1`: your first main phase. One action per line. Ending with
  `attack #a #b` moves to combat; ending with `done` (or no attack line) ends
  the turn without attacking (there is no separate main 2 if you do not attack).
- `BLOCK`: opponent attacked. Lines: `block #attacker with #blocker` (one blocker per
  attacker), and instants such as `cast #x target #attacker`, or `activate #factory`
  to animate a Factory and then block with it, all in ONE script. `pass` = no blocks.
  A script with only setup lines (tap/activate/cast) is not a complete answer; the
  engine asks again for your block lines.
- `COMBAT`: after blocks, before damage. Your instants, `sac atog #artifact`
  (+2/+2 each), or `pass`.
- `MAIN2`: after combat. Same actions as MAIN1 minus attack; end with `done`.
- `RESPOND`: the opponent cast a spell (shown in STACK). `cast #counter target #spellid`,
  another instant, or `pass`.
- `EOT`: end of opponent's turn. Instants (`cast Lightning Bolt target opp`) or `pass`.
- `TUTOR`: reply with a card name from the list shown. After it resolves you get
  a fresh MAIN decision (the rest of the script that cast the tutor is not run).
- `DISCARD`: end of your turn with more than 7 cards: `discard #a, #b`.

## Actions

- `land #id` play a land (one per turn).
- `cast #id` / `cast Card Name` optionally with `x=N` and `target <ref>`.
  Refs: `#id`, an exact card name, `opp`, `me`. Ancestral Recall defaults to you.
  Fireball / Earthquake / Braingeyser / Mind Twist need `x=N`.
- `activate #id [target #id]` for Mishra's Factory (animate, costs 1), Strip Mine
  (`activate #strip target #land`), Library of Alexandria (draw with exactly 7 in hand),
  Chaos Orb (costs 1, sorcery speed, 90% hit), Nevinyrral's Disk (costs 1), Jayemdae Tome
  (costs 4), Order of Leitbur (W: first strike).
- `lotus R` sacrifice a Black Lotus that is already on the battlefield (cast it first) for RRR floating (or just cast something the Lotus is
  needed for; the engine cracks it automatically, floating the rest).
- `tap #id [colour]` to float mana manually (rarely needed).
- `sac atog #artifact` pump Atog.
- `attack #a #b ...` or `attack all` (MAIN1 only).
- `done` / `pass`.

Mana is tapped automatically for each spell. Floating mana disappears (with mana
burn: 1 life per point) at the end of the phase. City of Brass costs 1 life per tap.

## Rules notes in this engine

- One blocker per attacker. Flying is only blocked by flying. First strike works.
- Protection from black: cannot be targeted, blocked or damaged by black.
- Moat: only fliers attack. The Abyss: at each player's upkeep, their weakest
  nonartifact creature dies. Black Vise: opponent takes (hand-4) at their upkeep.
- Unstable Mutation: +3/+3, a -1/-1 counter every upkeep.
- Serendib Efreet and Juzam Djinn deal 1 to their controller each upkeep.
- Chain Lightning is a sorcery; Lightning Bolt and Psionic Blast are instants.
- Balance, Timetwister, Wheel, Armageddon work as printed (Balance choices are
  automatic: extra lands/cards/creatures are sacrificed from the worst up).
- Mana Drain is just a Counterspell here. Recall is X=1.
- Paris mulligan. No ante. The game is a draw after 50 player-turns (25 each).

## Playing well

Read the whole state each decision: your life, their life, their hand size,
untapped mana on both sides, what is in graveyards. Count damage before
attacking. Do not walk creatures into first strikers. Hold counters for the
spells that matter. Burn face when the race is yours, burn creatures when it is
not. Remember the opponent can respond to your spells with instants.
