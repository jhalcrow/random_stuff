"""A small Old School 93/94 rules engine driven by two Policy objects.

The engine asks a policy for a decision at these windows:
  mulligan, main1, block, combat, main2, respond, eot, tutor
Each decision is a text script of actions (see AGENT_GUIDE.md).
"""
import random
from cards import DB, DECKS

NEXT_ID = [1]


class IllegalAction(Exception):
    pass


class Obj:
    def __init__(self, name, owner):
        self.id = NEXT_ID[0]
        NEXT_ID[0] += 1
        self.card = DB[name]
        self.owner = owner
        self.controller = owner
        self.tapped = False
        self.sick = True
        self.damage = 0
        self.m1 = 0            # -1/-1 counters
        self.temp_p = 0        # until end of turn
        self.temp_t = 0
        self.first_strike_eot = False
        self.animated = False  # Mishra's Factory
        self.attached_to = None
        self.auras = []
        self.used = False      # Chaos Orb / Disk / Tome / Library activation this turn
        self.attacking = False
        self.blocking = None

    @property
    def name(self):
        return self.card.name

    def is_creature(self):
        return self.card.is_creature or self.animated

    def is_artifact(self):
        return "artifact" in self.card.types or self.animated

    def color(self):
        return set(self.card.colors)

    def keywords(self, game):
        kw = set(self.card.kw)
        if self.first_strike_eot:
            kw.add("first strike")
        return kw

    def power(self, game):
        if self.animated:
            base = 2
        else:
            base = self.card.power
        p = base - self.m1 + self.temp_p + 3 * len([a for a in self.auras if a.name == "Unstable Mutation"])
        p += game.static_bonus(self)[0]
        return p

    def tough(self, game):
        base = 2 if self.animated else self.card.tough
        t = base - self.m1 + self.temp_t + 3 * len([a for a in self.auras if a.name == "Unstable Mutation"])
        t += game.static_bonus(self)[1]
        return t

    def label(self, game=None, mine=False):
        s = f"#{self.id} {self.name}"
        if game and self.is_creature():
            s += f" {self.power(game)}/{self.tough(game)}"
            kws = sorted(self.keywords(game))
            if kws:
                s += " (" + ", ".join(kws) + ")"
            if self.damage:
                s += f" [{self.damage} dmg]"
            if self.auras:
                s += " +" + "/".join(a.name for a in self.auras)
            if self.sick and self.controller is not None:
                s += " [summoning sick]"
        if self.tapped:
            s += " [TAPPED]"
        return s


class Player:
    def __init__(self, name, decklist, policy, game):
        self.name = name
        self.game = game
        self.policy = policy
        self.library = [Obj(n, self) for n in decklist]
        game.rng.shuffle(self.library)
        self.hand = []
        self.battlefield = []
        self.graveyard = []
        self.exile = []
        self.life = 20
        self.pool = []          # floating mana: list of colour letters ('C' colourless)
        self.lands_played = 0
        self.extra_turns = 0
        self.seen_log = 0
        self.mulligans = 0

    @property
    def opp(self):
        return self.game.players[1 - self.game.players.index(self)]

    def creatures(self):
        return [o for o in self.battlefield if o.is_creature()]

    def lands(self):
        return [o for o in self.battlefield if o.card.is_land]

    def draw(self, n=1):
        for _ in range(n):
            if not self.library:
                self.game.log_event(f"{self.name} cannot draw from an empty library and loses")
                self.life = -99
                return
            self.hand.append(self.library.pop())

    def find(self, ref, zone):
        """Resolve '#12' or a card name inside a zone list."""
        ref = ref.strip()
        if ref.startswith("#"):
            for o in zone:
                if str(o.id) == ref[1:]:
                    return o
            raise IllegalAction(f"{ref} is not available here")
        matches = [o for o in zone if o.name.lower() == ref.lower()]
        if not matches:
            raise IllegalAction(f"no '{ref}' available here")
        return matches[0]


class Game:
    def __init__(self, deck_a, deck_b, policy_a, policy_b, seed=0, first=0, names=None):
        self.rng = random.Random(seed)
        self.log = []
        self.stack = []
        self.turn = 0
        self.over = False
        self.winner = None
        names = names or (deck_a, deck_b)
        self.players = [Player(names[0], DECKS[deck_a], policy_a, self),
                        Player(names[1], DECKS[deck_b], policy_b, self)]
        self.deck_names = [deck_a, deck_b]
        self.active = self.players[first]
        self.phase = "setup"
        self.attackers = []
        self.orb_success = 0.9

    # ------------------------------------------------------------------ util
    def log_event(self, s):
        self.log.append(f"T{self.turn}: {s}")

    def other(self, p):
        return p.opp

    def check_win(self):
        for p in self.players:
            if p.life <= 0 and not self.over:
                self.over = True
                self.winner = p.opp
                self.log_event(f"{p.name} is at {p.life} life. {p.opp.name} wins.")
        return self.over

    def all_permanents(self):
        return self.players[0].battlefield + self.players[1].battlefield

    def static_bonus(self, obj):
        p = t = 0
        if not obj.is_creature():
            return 0, 0
        crusades = sum(1 for o in self.all_permanents() if o.name == "Crusade")
        if "white" in obj.color() and not obj.animated:
            p += crusades
            t += crusades
        if obj.name == "Kird Ape" and any("G" in l.card.produces and l.name != "City of Brass" for l in obj.controller.lands()):
            p += 1
            t += 2
        if obj.name == "Sedge Troll" and any("B" in l.card.produces and l.name != "City of Brass" for l in obj.controller.lands()):
            p += 1
            t += 1
        return p, t

    def has_moat(self):
        return any(o.name == "Moat" for o in self.all_permanents())

    # ------------------------------------------------------------------ zones
    def to_graveyard(self, obj):
        p = obj.controller or obj.owner
        for zone in (p.battlefield, p.hand):
            if obj in zone:
                zone.remove(obj)
        if obj in self.stack_objs():
            self.stack = [e for e in self.stack if e["obj"] is not obj]
        for a in list(obj.auras):
            self.to_graveyard(a)
        if obj.attached_to is not None:
            if obj in obj.attached_to.auras:
                obj.attached_to.auras.remove(obj)
            obj.attached_to = None
        obj.controller = None
        self.reset(obj)
        obj.owner.graveyard.append(obj)

    def exile(self, obj):
        p = obj.controller
        if obj in p.battlefield:
            p.battlefield.remove(obj)
        for a in list(obj.auras):
            self.to_graveyard(a)
        obj.controller = None
        self.reset(obj)
        obj.owner.exile.append(obj)

    def reset(self, obj):
        obj.tapped = False
        obj.sick = True
        obj.damage = 0
        obj.m1 = 0
        obj.temp_p = obj.temp_t = 0
        obj.animated = False
        obj.attacking = False
        obj.blocking = None
        obj.first_strike_eot = False
        obj.auras = []
        obj.used = False

    def stack_objs(self):
        return [e["obj"] for e in self.stack]

    def state_based(self):
        changed = True
        while changed:
            changed = False
            for p in self.players:
                for o in list(p.battlefield):
                    if o.is_creature() and (o.tough(self) <= 0 or o.damage >= o.tough(self)):
                        self.log_event(f"{o.name} ({p.name}) dies")
                        self.to_graveyard(o)
                        changed = True
                    elif o.card.types & {"aura"} and (o.attached_to is None or o.attached_to.controller is None
                                                      or not o.attached_to.is_creature()):
                        self.to_graveyard(o)
                        changed = True
        self.check_win()

    def damage_player(self, p, n, source=""):
        if n <= 0:
            return
        p.life -= n
        self.log_event(f"{p.name} takes {n}{(' from ' + source) if source else ''} ({p.life} life)")
        self.check_win()

    def damage_creature(self, o, n):
        if n <= 0:
            return
        o.damage += n
        self.log_event(f"{o.name} ({o.controller.name}) takes {n} damage")

    # ------------------------------------------------------------------ mana
    def sources(self, p):
        """Untapped mana sources: list of (obj, options) where option is a str of colours it makes."""
        out = []
        for o in p.battlefield:
            if o.tapped:
                continue
            prod = o.card.produces
            if not prod or prod == "LOTUS":
                continue
            if o.name == "Mishra's Factory" and o.animated:
                continue
            if o.sick and o.is_creature():
                continue
            out.append((o, prod))
        return out

    def mana_potential(self, p):
        n = len(p.pool)
        for o, prod in self.sources(p):
            n += 2 if prod == "CC" else 1
        if any(o.name == "Black Lotus" for o in p.battlefield):
            n += 3
        return n

    def pay(self, p, cost, x=0, allow_lotus=True):
        """Tap sources to pay. Returns True on success (sources tapped), raises otherwise."""
        pips = [c for c in cost if c in "WUBRG"]
        generic = int("".join(ch for ch in cost if ch.isdigit()) or 0) + x * cost.count("X")
        plan = self._plan_payment(p, pips, generic, allow_lotus)
        if plan is None:
            raise IllegalAction(f"cannot pay {cost}{' with X=' + str(x) if x else ''}")
        used_pool, taps, lotus_colour = plan
        for m in used_pool:
            p.pool.remove(m)
        for o, colour in taps:
            o.tapped = True
            if o.name == "City of Brass":
                self.damage_player(p, 1, "City of Brass")
        if lotus_colour:
            lotus = next(o for o in p.battlefield if o.name == "Black Lotus")
            self.to_graveyard(lotus)
            self.log_event(f"{p.name} sacrifices Black Lotus for {lotus_colour * 3}")
            # surplus lotus mana floats
            need = len(pips) + generic
            # (handled inside planner: lotus counted as three of one colour)
        return True

    def _plan_payment(self, p, pips, generic, allow_lotus):
        pool = list(p.pool)
        srcs = self.sources(p)
        lotus = allow_lotus and any(o.name == "Black Lotus" for o in p.battlefield)
        # try without lotus first, then with each lotus colour
        options = [None] + ([c for c in "WUBRG"] if lotus else [])
        for lc in options:
            res = self._try_pay(pool, srcs, pips, generic, lc)
            if res is not None:
                used_pool, taps, leftover_pool = res
                if lc:
                    # floating leftover lotus mana
                    p_pool_add = leftover_pool
                else:
                    p_pool_add = []
                # commit leftover to pool after paying
                self._pending_pool = p_pool_add
                return used_pool, taps, lc
        return None

    def _try_pay(self, pool, srcs, pips, generic, lotus_colour):
        """Greedy with backtracking over sources. Returns (used_pool, taps, leftover_lotus)."""
        avail = []  # (kind, key, colours, amount)
        for m in pool:
            avail.append(("pool", m, m if m != "C" else "", 1))
        for o, prod in srcs:
            if prod == "CC":
                avail.append(("src", o, "", 2))
            elif prod == "C":
                avail.append(("src", o, "", 1))
            else:
                avail.append(("src", o, prod, 1))
        lotus_units = [("lotus", i, lotus_colour, 1) for i in range(3)] if lotus_colour else []
        avail += lotus_units
        need_pips = list(pips)
        need_generic = generic
        # assign pips: least flexible sources first
        chosen = []
        remaining = list(avail)
        for pip in sorted(need_pips, key=lambda c: -sum(1 for a in avail if c in a[2])):
            cands = [a for a in remaining if pip in a[2] and a[3] == 1]
            if not cands:
                return None
            cands.sort(key=lambda a: (a[0] == "lotus", len(a[2]), a[0] != "pool"))
            c = cands[0]
            chosen.append((c, pip))
            remaining.remove(c)
        # generic: prefer pool, colourless, sol ring, then single-colour lands, then flexible
        remaining.sort(key=lambda a: (a[0] == "lotus", a[0] != "pool", a[2] != "", -a[3], len(a[2])))
        gen_chosen = []
        while need_generic > 0 and remaining:
            # prefer a source that does not overpay (Sol Ring for a 1-cost spell burns a mana)
            fits = [a for a in remaining if a[3] <= need_generic]
            a = fits[0] if fits else remaining[0]
            remaining.remove(a)
            gen_chosen.append(a)
            need_generic -= a[3]
        if need_generic > 0:
            return None
        used_pool = [c[0][1] for c in chosen if c[0][0] == "pool"] + [a[1] for a in gen_chosen if a[0] == "pool"]
        taps = [(c[0][1], c[1]) for c in chosen if c[0][0] == "src"] + [(a[1], "") for a in gen_chosen if a[0] == "src"]
        used_lotus = sum(1 for c in chosen if c[0][0] == "lotus") + sum(1 for a in gen_chosen if a[0] == "lotus")
        leftover = []
        if lotus_colour:
            leftover = [lotus_colour] * (3 - used_lotus)
        # Sol Ring surplus floats as colourless
        surplus = -need_generic
        leftover += ["C"] * surplus
        return used_pool, taps, leftover

    def commit_pool(self, p):
        p.pool += getattr(self, "_pending_pool", [])
        self._pending_pool = []

    def mana_burn(self, p):
        if p.pool:
            n = len(p.pool)
            p.pool = []
            self.damage_player(p, n, "mana burn")

    # ------------------------------------------------------------------ turn
    def run(self, max_turns=30):
        for p in self.players:
            p.draw(7)
            self.mulligan(p)
        self.turn = 0
        while not self.over and self.turn < max_turns:
            self.take_turn(self.active)
            if self.over:
                break
            if self.active.extra_turns > 0:
                self.active.extra_turns -= 1
            else:
                self.active = self.active.opp
        if not self.over:
            self.over = True
            self.winner = None
            self.log_event("Turn limit reached: draw")
        return self.winner

    def mulligan(self, p):
        while True:
            dec = p.policy.decide(self, p, "mulligan", "")
            if dec.strip().lower().startswith("mull") and len(p.hand) > 4:
                p.library += p.hand
                p.hand = []
                self.rng.shuffle(p.library)
                p.mulligans += 1
                p.draw(7 - p.mulligans)
                self.log_event(f"{p.name} mulligans to {len(p.hand)}")
            else:
                self.log_event(f"{p.name} keeps {len(p.hand)}")
                return

    def take_turn(self, p):
        self.turn += 1
        self.attackers = []
        p.lands_played = 0
        self.log_event(f"--- {p.name}'s turn {self.turn} ---")
        # untap
        for o in p.battlefield:
            o.tapped = False
            o.sick = False
            o.used = False
        # upkeep
        self.upkeep(p)
        if self.over:
            return
        # draw
        if not (self.turn == 1):
            p.draw()
        elif self.turn == 1 and p is not self.players[0] and self.active is p:
            p.draw()
        # main 1
        self.phase = "main1"
        attacked = self.main_phase(p, "main1")
        if self.over:
            return
        if attacked:
            self.combat(p)
            if self.over:
                return
            self.phase = "main2"
            self.main_phase(p, "main2")
            if self.over:
                return
        # end of turn window for the opponent
        self.phase = "end"
        self.eot_window(p.opp)
        if self.over:
            return
        self.cleanup(p)

    def upkeep(self, p):
        for o in list(p.battlefield):
            if o.name in ("Serendib Efreet", "Juzam Djinn"):
                self.damage_player(p, 1, o.name)
            for a in list(o.auras):
                if a.name == "Unstable Mutation":
                    o.m1 += 1
        for o in self.all_permanents():
            if o.name == "Black Vise" and o.controller is p.opp:
                self.damage_player(p, len(p.hand) - 4, "Black Vise")
            if o.name == "Ivory Tower" and o.controller is p:
                g = len(p.hand) - 4
                if g > 0:
                    p.life += g
                    self.log_event(f"{p.name} gains {g} from Ivory Tower")
        if any(o.name == "The Abyss" for o in self.all_permanents()):
            cands = [c for c in p.creatures() if not c.is_artifact()]
            if cands:
                victim = min(cands, key=lambda c: (c.power(self), c.tough(self)))
                self.log_event(f"The Abyss destroys {victim.name} ({p.name})")
                self.to_graveyard(victim)
        self.state_based()

    def cleanup(self, p):
        for q in self.players:
            for o in list(q.battlefield):
                if o.name == "Ball Lightning":
                    self.log_event("Ball Lightning is sacrificed")
                    self.to_graveyard(o)
                    continue
                o.damage = 0
                o.temp_p = o.temp_t = 0
                o.first_strike_eot = False
                if o.animated:
                    o.animated = False
                o.attacking = False
                o.blocking = None
            self.mana_burn(q)
        while len(p.hand) > 7:
            # discard: excess lands first, then most expensive
            lands = [c for c in p.hand if c.card.is_land]
            victim = lands[0] if len(lands) > 2 else max(p.hand, key=lambda c: c.card.cmc)
            p.hand.remove(victim)
            p.graveyard.append(victim)
            self.log_event(f"{p.name} discards {victim.name} to hand size")
        self.state_based()

    # ------------------------------------------------------------------ decision windows
    def main_phase(self, p, which):
        """Loop asking the policy for actions until 'done' or 'attack'. Returns True if attacking."""
        error = ""
        for _ in range(40):
            script = p.policy.decide(self, p, which, error)
            error = ""
            try:
                result = self.execute_script(p, script, which)
            except IllegalAction as e:
                error = str(e)
                continue
            if self.over:
                return False
            if result == "attack":
                return True
            if result == "done":
                self.mana_burn(p)
                return False
        self.mana_burn(p)
        return False

    def execute_script(self, p, script, window):
        """Execute a multi-line action script. Returns 'done', 'attack', or 'pass'."""
        lines = [l.strip() for l in script.replace(";", "\n").splitlines() if l.strip()]
        if not lines:
            lines = ["done" if window in ("main1", "main2") else "pass"]
        for line in lines:
            if self.over:
                return "done"
            verb, _, rest = line.partition(" ")
            verb = verb.lower()
            rest = rest.strip()
            if verb in ("done", "pass", "end", "no", "keep"):
                if window in ("main1", "main2"):
                    return "done"
                return "pass"
            if verb == "land" and window in ("main1", "main2"):
                self.play_land(p, rest)
            elif verb == "cast":
                self.cast_from_script(p, rest, window)
            elif verb in ("activate", "animate"):
                self.activate(p, rest, window)
            elif verb == "lotus":
                self.crack_lotus(p, rest)
            elif verb == "tap":
                self.manual_tap(p, rest)
            elif verb == "attack" and window == "main1":
                self.declare_attackers(p, rest)
                return "attack"
            elif verb == "block" and window == "block":
                self.declare_block(p, rest)
            elif verb == "sac" and rest.lower().startswith("atog"):
                self.atog_sac(p, rest)
            elif verb in ("mulligan", "mull"):
                pass
            else:
                raise IllegalAction(f"unknown or out-of-window action: '{line}'")
        if window in ("main1", "main2"):
            return "done"
        return "pass"

    def play_land(self, p, ref):
        if p.lands_played >= 1:
            raise IllegalAction("already played a land this turn")
        o = p.find(ref, p.hand)
        if not o.card.is_land:
            raise IllegalAction(f"{o.name} is not a land")
        p.hand.remove(o)
        o.controller = p
        o.sick = False
        p.battlefield.append(o)
        p.lands_played += 1
        self.log_event(f"{p.name} plays {o.name}")

    def crack_lotus(self, p, colour):
        colour = (colour or "R").strip().upper()[:1]
        if colour not in "WUBRG":
            raise IllegalAction("lotus needs a colour letter W/U/B/R/G")
        lotus = next((o for o in p.battlefield if o.name == "Black Lotus"), None)
        if not lotus:
            raise IllegalAction("no Black Lotus on the battlefield")
        self.to_graveyard(lotus)
        p.pool += [colour] * 3
        self.log_event(f"{p.name} sacrifices Black Lotus for {colour * 3}")

    def manual_tap(self, p, rest):
        parts = rest.split()
        if not parts:
            raise IllegalAction("tap what?")
        o = p.find(parts[0], p.battlefield)
        colour = parts[1].upper() if len(parts) > 1 else None
        prod = o.card.produces
        if o.tapped or not prod or prod == "LOTUS":
            raise IllegalAction(f"{o.name} cannot be tapped for mana now")
        o.tapped = True
        if prod == "CC":
            p.pool += ["C", "C"]
        elif prod == "C":
            p.pool.append("C")
        else:
            c = colour if (colour and colour in prod) else prod[0]
            p.pool.append(c)
            if o.name == "City of Brass":
                self.damage_player(p, 1, "City of Brass")

    # ---- casting -------------------------------------------------------
    def parse_cast(self, rest):
        """'<card> [x=N] [target <ref>]' -> (cardref, x, targetref)"""
        x = 0
        target = None
        tokens = rest.split()
        card_tokens = []
        i = 0
        while i < len(tokens):
            t = tokens[i]
            tl = t.lower()
            if tl.startswith("x="):
                x = int(tl[2:])
            elif tl in ("target", "targeting", "on", "->", "at"):
                target = " ".join(tokens[i + 1:])
                break
            else:
                card_tokens.append(t)
            i += 1
        return " ".join(card_tokens), x, target

    def resolve_target(self, p, card, targetref, on_stack=False):
        kind = card.targets
        if not kind:
            return None
        if targetref is None:
            if kind == "player":
                return p if card.effect in ("draw3", "geyser") else p.opp
            if kind == "any":
                return p.opp
            raise IllegalAction(f"{card.name} needs a target ({kind})")
        t = targetref.strip().lower()
        if t in ("opp", "opponent", "them", "face", "their face", "player"):
            if kind in ("any", "player"):
                return p.opp
            raise IllegalAction(f"{card.name} cannot target a player")
        if t in ("me", "myself", "self", "you"):
            if kind in ("any", "player"):
                return p
            raise IllegalAction(f"{card.name} cannot target a player")
        if kind == "spell" or (kind in ("blue", "red") and self.stack):
            for e in reversed(self.stack):
                o = e["obj"]
                if t == f"#{o.id}" or t == o.name.lower():
                    if kind == "blue" and "blue" not in o.card.colors:
                        raise IllegalAction("Red Elemental Blast only hits blue")
                    if kind == "red" and "red" not in o.card.colors:
                        raise IllegalAction("Blue Elemental Blast only hits red")
                    return e
            if kind == "spell":
                raise IllegalAction("no such spell on the stack")
        if kind == "gycard":
            return p.find(targetref, p.graveyard)
        # permanents
        perms = self.all_permanents()
        o = None
        for cand in perms:
            if t == f"#{cand.id}" or t == cand.name.lower():
                o = cand
                break
        if o is None:
            raise IllegalAction(f"no target '{targetref}' on the battlefield")
        if kind in ("any", "creature") and not o.is_creature():
            raise IllegalAction(f"{o.name} is not a creature")
        if kind == "artifact" and not o.is_artifact():
            raise IllegalAction(f"{o.name} is not an artifact")
        if kind == "artifact-or-enchantment" and not (o.is_artifact() or "enchantment" in o.card.types):
            raise IllegalAction(f"{o.name} is not an artifact or enchantment")
        if kind == "land" and not o.card.is_land:
            raise IllegalAction(f"{o.name} is not a land")
        if kind == "blue" and "blue" not in o.card.colors:
            raise IllegalAction("Red Elemental Blast only hits blue permanents")
        if kind == "red" and "red" not in o.card.colors:
            raise IllegalAction("Blue Elemental Blast only hits red permanents")
        if "pro-black" in o.card.kw and "black" in card.colors:
            raise IllegalAction(f"{o.name} has protection from black")
        return o

    def cast_from_script(self, p, rest, window):
        cardref, x, targetref = self.parse_cast(rest)
        obj = p.find(cardref, p.hand)
        card = obj.card
        if card.is_land:
            raise IllegalAction("use 'land' to play lands")
        sorcery_speed = window in ("main1", "main2") and not self.stack
        if not card.is_instant and not sorcery_speed:
            raise IllegalAction(f"{card.name} can only be cast in your main phase with an empty stack")
        if card.name in ("Ancestral Recall",) and targetref is None:
            targetref = "me"
        is_permanent = card.is_creature or "artifact" in card.types or ("enchantment" in card.types and "aura" not in card.types)
        target = None if is_permanent else self.resolve_target(p, card, targetref)
        if card.effect == "fireball" and x <= 0:
            raise IllegalAction("Fireball needs x=N")
        if card.effect == "earthquake" and x <= 0:
            raise IllegalAction("Earthquake needs x=N")
        if card.effect in ("geyser", "mindtwist") and x <= 0:
            raise IllegalAction(f"{card.name} needs x=N")
        if card.effect == "recall":
            x = 1
        self.pay(p, card.cost, x)
        self.commit_pool(p)
        p.hand.remove(obj)
        tdesc = ""
        if isinstance(target, Player):
            tdesc = f" targeting {target.name}"
        elif isinstance(target, dict):
            tdesc = f" targeting {target['obj'].name}"
        elif target is not None:
            tdesc = f" targeting {target.name}"
        self.log_event(f"{p.name} casts {card.name}{(' X=' + str(x)) if x else ''}{tdesc}")
        entry = {"obj": obj, "caster": p, "target": target, "x": x, "countered": False}
        self.stack.append(entry)
        # response window for the opponent
        self.response_window(p.opp, entry)
        # resolve everything if we are the outermost cast
        if getattr(self, "_depth", 0) == 0:
            self.resolve_stack()

    def response_window(self, responder, entry):
        if not self.can_respond(responder, entry):
            return
        self._depth = getattr(self, "_depth", 0) + 1
        try:
            error = ""
            for _ in range(5):
                script = responder.policy.decide(self, responder, "respond", error)
                try:
                    before = len(self.stack)
                    self.execute_script(responder, script, "respond")
                    if len(self.stack) > before:
                        # they cast something: the original caster may respond to that
                        self.response_window(entry["caster"], self.stack[-1])
                    return
                except IllegalAction as e:
                    error = str(e)
        finally:
            self._depth -= 1

    def can_respond(self, r, entry):
        if self.over:
            return False
        spell = entry["obj"].card
        pot = self.mana_potential(r)
        for c in r.hand:
            cd = c.card
            if not cd.is_instant or cd.cmc > pot:
                continue
            if cd.effect == "counter":
                return True
            if cd.effect == "reb" and "blue" in spell.colors:
                return True
            if cd.effect == "beb" and "red" in spell.colors:
                return True
            if cd.effect == "ritual":
                continue
            # kill a creature in response to an aura / pump, or save one from burn
            if spell.effect in ("aura", "pump3") and cd.targets in ("creature", "any"):
                return True
            if spell.effect in ("damage3", "psiblast", "fireball", "terror", "swords") and cd.effect == "pump3":
                return True
            if spell.effect in ("damage3", "psiblast", "fireball") and cd.effect == "swords" and entry["target"] is not None \
                    and not isinstance(entry["target"], Player):
                return True
        return False

    def resolve_stack(self):
        while self.stack and not self.over:
            e = self.stack.pop()
            obj = e["obj"]
            if e["countered"]:
                self.log_event(f"{obj.name} was countered")
                obj.owner.graveyard.append(obj)
                continue
            self.resolve(e)
            self.state_based()

    def resolve(self, e):
        obj, p, t, x = e["obj"], e["caster"], e["target"], e["x"]
        card = obj.card
        eff = card.effect
        # target legality on resolution
        if isinstance(t, Obj) and t.controller is None and card.targets != "gycard":
            self.log_event(f"{card.name} fizzles (target gone)")
            p.graveyard.append(obj)
            return
        goes_to_gy = True
        if card.is_creature or "artifact" in card.types or "enchantment" in card.types:
            goes_to_gy = False
            obj.controller = p
            obj.sick = True
            if card.name == "Nevinyrral's Disk":
                obj.tapped = True
            if "aura" in card.types:
                if t is None or not t.is_creature():
                    p.graveyard.append(obj)
                    return
                obj.attached_to = t
                t.auras.append(obj)
                self.log_event(f"{card.name} enchants {t.name}")
            p.battlefield.append(obj)
            self.log_event(f"{card.name} enters the battlefield under {p.name}")
        elif eff == "damage3":
            self.deal(t, 3, card.name)
        elif eff == "psiblast":
            self.deal(t, 4, card.name)
            self.damage_player(p, 2, "Psionic Blast")
        elif eff == "fireball":
            self.deal(t, x, card.name)
        elif eff == "earthquake":
            for q in self.players:
                for c in list(q.creatures()):
                    if "flying" not in c.keywords(self):
                        self.damage_creature(c, x)
                self.damage_player(q, x, "Earthquake")
        elif eff == "swords":
            gain = t.power(self)
            owner = t.controller
            self.log_event(f"{t.name} is exiled; {owner.name} gains {gain}")
            owner.life += gain
            self.exile(t)
        elif eff == "terror":
            if "black" in t.color() or t.is_artifact():
                self.log_event("Terror has no legal effect on that target")
            else:
                self.log_event(f"Terror destroys {t.name}")
                self.to_graveyard(t)
        elif eff in ("disenchant", "shatter"):
            self.log_event(f"{card.name} destroys {t.name}")
            self.to_graveyard(t)
        elif eff == "counter":
            t["countered"] = True
            self.log_event(f"{card.name} counters {t['obj'].name}")
        elif eff in ("reb", "beb"):
            if isinstance(t, dict):
                t["countered"] = True
                self.log_event(f"{card.name} counters {t['obj'].name}")
            else:
                self.log_event(f"{card.name} destroys {t.name}")
                self.to_graveyard(t)
        elif eff == "draw3":
            t.draw(3)
            self.log_event(f"{t.name} draws 3")
        elif eff == "timewalk":
            p.extra_turns += 1
            self.log_event(f"{p.name} takes an extra turn")
        elif eff == "twister":
            for q in self.players:
                q.library += q.hand + q.graveyard
                q.hand, q.graveyard = [], []
                self.rng.shuffle(q.library)
                q.draw(7)
            self.log_event("Timetwister: everyone shuffles up and draws 7")
            goes_to_gy = True
        elif eff == "wheel":
            for q in self.players:
                q.graveyard += q.hand
                q.hand = []
                q.draw(7)
            self.log_event("Wheel of Fortune: everyone discards and draws 7")
        elif eff == "geyser":
            t.draw(x)
            self.log_event(f"{t.name} draws {x}")
        elif eff == "tutor":
            self.tutor(p)
        elif eff == "regrowth":
            p.graveyard.remove(t)
            p.hand.append(t)
            self.log_event(f"{p.name} regrows {t.name}")
        elif eff == "recall":
            if p.hand and p.graveyard:
                d = max(p.hand, key=lambda c: c.card.is_land)
                p.hand.remove(d)
                p.graveyard.append(d)
                best = max(p.graveyard, key=lambda c: (c.name in ("Ancestral Recall", "Time Walk", "Balance", "Swords to Plowshares", "Counterspell"), c.card.cmc))
                p.graveyard.remove(best)
                p.hand.append(best)
                self.log_event(f"{p.name} recalls {best.name}")
            p.exile.append(obj)
            goes_to_gy = False
        elif eff == "balance":
            self.balance(p)
        elif eff == "mindtwist":
            self.discard_random(t, x)
        elif eff == "hymn":
            self.discard_random(t, 2)
        elif eff == "ritual":
            p.pool += ["B", "B", "B"]
        elif eff == "geddon":
            for q in self.players:
                for l in list(q.lands()):
                    self.to_graveyard(l)
            self.log_event("Armageddon destroys all lands")
        elif eff == "pump3":
            t.temp_p += 3
            t.temp_t += 3
        if goes_to_gy:
            p.graveyard.append(obj)

    def deal(self, t, n, src):
        if isinstance(t, Player):
            self.damage_player(t, n, src)
        else:
            self.damage_creature(t, n)

    def discard_random(self, q, n):
        for _ in range(min(n, len(q.hand))):
            c = self.rng.choice(q.hand)
            q.hand.remove(c)
            q.graveyard.append(c)
            self.log_event(f"{q.name} discards {c.name}")

    def balance(self, p):
        o = p.opp
        # lands
        n = min(len(p.lands()), len(o.lands()))
        for q in self.players:
            ls = q.lands()
            while len(ls) > n:
                victim = max(ls, key=lambda l: (l.name in ("Mishra's Factory", "Strip Mine"), -len(l.card.produces)))
                self.to_graveyard(victim)
                ls = q.lands()
        # hands
        n = min(len(p.hand), len(o.hand))
        for q in self.players:
            while len(q.hand) > n:
                victim = max(q.hand, key=lambda c: (c.card.is_land, -c.card.cmc))
                q.hand.remove(victim)
                q.graveyard.append(victim)
        # creatures
        n = min(len(p.creatures()), len(o.creatures()))
        for q in self.players:
            cs = q.creatures()
            while len(cs) > n:
                victim = min(cs, key=lambda c: (c.power(self), c.tough(self)))
                self.to_graveyard(victim)
                cs = q.creatures()
        self.log_event(f"Balance resolves: lands {len(p.lands())}, hands {len(p.hand)}, creatures {len(p.creatures())}")

    def tutor(self, p):
        names = sorted(set(c.name for c in p.library))
        error = ""
        for _ in range(3):
            choice = p.policy.decide(self, p, "tutor", error + "\nLibrary contains: " + ", ".join(names))
            choice = choice.strip().strip("'\"")
            for c in p.library:
                if c.name.lower() == choice.lower():
                    p.library.remove(c)
                    p.hand.append(c)
                    self.rng.shuffle(p.library)
                    self.log_event(f"{p.name} tutors for a card")
                    return
            error = f"'{choice}' is not in your library."
        c = p.library.pop()
        p.hand.append(c)

    # ---- activated abilities -------------------------------------------
    def activate(self, p, rest, window):
        cardref, x, targetref = self.parse_cast(rest)
        o = p.find(cardref, p.battlefield)
        name = o.name
        if name == "Mishra's Factory":
            if o.animated:
                raise IllegalAction("already animated")
            self.pay(p, "1")
            self.commit_pool(p)
            o.animated = True
            self.log_event(f"{p.name} animates Mishra's Factory")
        elif name == "Strip Mine":
            if o.tapped:
                raise IllegalAction("Strip Mine is tapped")
            t = self.resolve_target(p, DB["Strip Mine"], targetref)
            self.to_graveyard(o)
            self.log_event(f"{p.name} Strip Mines {t.name} ({t.controller.name})")
            self.to_graveyard(t)
        elif name == "Library of Alexandria":
            if o.tapped or len(p.hand) != 7:
                raise IllegalAction("Library needs exactly 7 cards in hand and to be untapped")
            o.tapped = True
            p.draw()
            self.log_event(f"{p.name} draws with Library of Alexandria")
        elif name == "Chaos Orb":
            if window not in ("main1", "main2"):
                raise IllegalAction("Chaos Orb only in your main phase")
            if o.sick:
                raise IllegalAction("Chaos Orb is summoning sick this turn")
            t = self.resolve_target(p, DB["Chaos Orb"], targetref)
            self.pay(p, "1")
            self.commit_pool(p)
            self.to_graveyard(o)
            if self.rng.random() < self.orb_success:
                self.log_event(f"Chaos Orb lands on {t.name} ({t.controller.name}) and destroys it")
                self.to_graveyard(t)
            else:
                self.log_event("Chaos Orb misses")
        elif name == "Nevinyrral's Disk":
            if o.tapped:
                raise IllegalAction("Disk is tapped")
            self.pay(p, "1")
            self.commit_pool(p)
            for q in self.players:
                for x in list(q.battlefield):
                    if x.is_creature() or x.is_artifact() or "enchantment" in x.card.types:
                        self.to_graveyard(x)
            self.log_event("Nevinyrral's Disk wipes the board")
        elif name == "Jayemdae Tome":
            if o.tapped or o.sick:
                raise IllegalAction("Tome is tapped or summoning sick")
            self.pay(p, "4")
            self.commit_pool(p)
            o.tapped = True
            p.draw()
            self.log_event(f"{p.name} draws with Jayemdae Tome")
        elif name == "Atog":
            self.atog_sac(p, rest)
        elif name == "Order of Leitbur":
            self.pay(p, "W")
            self.commit_pool(p)
            o.first_strike_eot = True
        elif name == "Black Lotus":
            self.crack_lotus(p, targetref or "R")
        else:
            raise IllegalAction(f"{name} has no activated ability here")
        self.state_based()

    def atog_sac(self, p, rest):
        atog = next((c for c in p.battlefield if c.name == "Atog"), None)
        if not atog:
            raise IllegalAction("no Atog")
        parts = rest.split()
        ref = parts[-1] if parts else ""
        arts = [o for o in p.battlefield if o.is_artifact() and o is not atog]
        if not arts:
            raise IllegalAction("no artifact to sacrifice")
        try:
            a = p.find(ref, arts)
        except IllegalAction:
            a = min(arts, key=lambda o: (o.card.is_creature, o.card.cmc))
        self.to_graveyard(a)
        atog.temp_p += 2
        atog.temp_t += 2
        self.log_event(f"Atog eats {a.name}: now {atog.power(self)}/{atog.tough(self)}")

    # ---- combat --------------------------------------------------------
    def declare_attackers(self, p, rest):
        refs = [r.strip() for r in rest.replace(",", " ").split() if r.strip()]
        if not refs or refs == ["all"]:
            cands = [c for c in p.creatures() if not c.tapped and (not c.sick or "haste" in c.keywords(self))]
            if self.has_moat():
                cands = [c for c in cands if "flying" in c.keywords(self)]
            if not cands:
                raise IllegalAction("no creature can attack")
            chosen = cands
        else:
            chosen = []
            for r in refs:
                o = p.find(r, p.battlefield)
                if not o.is_creature():
                    raise IllegalAction(f"{o.name} is not a creature")
                if o.tapped:
                    raise IllegalAction(f"{o.name} is tapped")
                if o.sick and "haste" not in o.keywords(self):
                    raise IllegalAction(f"{o.name} is summoning sick")
                if self.has_moat() and "flying" not in o.keywords(self):
                    raise IllegalAction(f"Moat stops {o.name}")
                chosen.append(o)
        for o in chosen:
            o.attacking = True
            if "vigilance" not in o.keywords(self):
                o.tapped = True
        self.attackers = chosen
        self.log_event(f"{p.name} attacks with " + ", ".join(f"{o.name} {o.power(self)}/{o.tough(self)}" for o in chosen))

    def combat(self, p):
        d = p.opp
        # defender: instants + blocks
        error = ""
        for _ in range(5):
            script = d.policy.decide(self, d, "block", error)
            try:
                self.execute_script(d, script, "block")
                break
            except IllegalAction as e:
                error = str(e)
        if self.over:
            return
        self.attackers = [a for a in self.attackers if a.controller is p and a.attacking]
        # attacker's post-block instants
        if any(c.card.is_instant and c.card.cmc <= self.mana_potential(p) for c in p.hand) or \
                any(c.name == "Atog" for c in self.attackers) or any(c.name == "Order of Leitbur" for c in self.attackers):
            error = ""
            for _ in range(3):
                script = p.policy.decide(self, p, "combat", error)
                try:
                    self.execute_script(p, script, "combat")
                    break
                except IllegalAction as e:
                    error = str(e)
        if self.over:
            return
        self.attackers = [a for a in self.attackers if a.controller is p and a.attacking]
        self.combat_damage(p, d)
        self.mana_burn(p)
        self.mana_burn(d)

    def declare_block(self, d, rest):
        # 'block <attacker> with <blocker>'
        m = rest.lower().split(" with ")
        if len(m) != 2:
            raise IllegalAction("use: block <attacker> with <blocker>")
        att = None
        for a in self.attackers:
            if m[0].strip() in (f"#{a.id}", a.name.lower()):
                att = a
                break
        if att is None:
            raise IllegalAction(f"'{m[0]}' is not attacking")
        blk = d.find(m[1].strip(), d.battlefield)
        if not blk.is_creature():
            raise IllegalAction(f"{blk.name} is not a creature")
        if blk.tapped:
            raise IllegalAction(f"{blk.name} is tapped")
        if blk.blocking is not None:
            raise IllegalAction(f"{blk.name} is already blocking")
        if "flying" in att.keywords(self) and "flying" not in blk.keywords(self):
            raise IllegalAction(f"{blk.name} cannot block a flier")
        if "pro-black" in att.card.kw and "black" in blk.color():
            raise IllegalAction(f"{att.name} has protection from black")
        if att.name == "Argothian Pixies" and blk.is_artifact():
            raise IllegalAction("Argothian Pixies can't be blocked by artifact creatures")
        blk.blocking = att
        self.log_event(f"{d.name} blocks {att.name} with {blk.name}")

    def combat_damage(self, p, d):
        blockers = {b.blocking: b for b in d.creatures() if b.blocking is not None}
        # Order of Leitbur gets first strike automatically when W is available? keep simple: no auto.
        pairs = []
        for a in self.attackers:
            b = blockers.get(a)
            pairs.append((a, b))
        # first strike step
        def fs(c):
            return "first strike" in c.keywords(self)

        dead = set()
        for a, b in pairs:
            if b is None:
                continue
            if fs(a) and not fs(b):
                self.damage_creature(b, a.power(self))
                if b.damage >= b.tough(self):
                    dead.add(b)
            elif fs(b) and not fs(a):
                self.damage_creature(a, b.power(self))
                if a.damage >= a.tough(self):
                    dead.add(a)
        self.state_based()
        # regular damage
        for a, b in pairs:
            if a.controller is None:
                continue
            if b is None or b.controller is None:
                if b is not None and "trample" in a.keywords(self):
                    self.damage_player(d, a.power(self), a.name)
                elif b is None:
                    self.damage_player(d, a.power(self), a.name)
                    if a.name == "Hypnotic Specter" and a.power(self) > 0:
                        self.discard_random(d, 1)
                continue
            if a in dead or b in dead:
                if b in dead and "trample" in a.keywords(self):
                    self.damage_player(d, a.power(self), a.name)
                continue
            if not fs(a) or fs(b):
                dmg = a.power(self)
                if "trample" in a.keywords(self):
                    lethal = max(0, b.tough(self) - b.damage)
                    self.damage_creature(b, min(dmg, lethal))
                    self.damage_player(d, dmg - min(dmg, lethal), a.name)
                else:
                    self.damage_creature(b, dmg)
            if not fs(b) or fs(a):
                self.damage_creature(a, b.power(self))
        for a in self.attackers:
            a.attacking = False
        for b in d.creatures():
            b.blocking = None
        self.state_based()

    def eot_window(self, q):
        """Instant window for the non-active player at end of turn."""
        if self.over:
            return
        pot = self.mana_potential(q)
        if not any(c.card.is_instant and c.card.cmc <= pot and c.card.effect not in ("counter", "reb", "beb", "ritual")
                   for c in q.hand):
            return
        error = ""
        for _ in range(3):
            script = q.policy.decide(self, q, "eot", error)
            try:
                self.execute_script(q, script, "eot")
                break
            except IllegalAction as e:
                error = str(e)
        self.mana_burn(q)

    # ------------------------------------------------------------------ rendering
    def render(self, p, window, error=""):
        o = p.opp
        lines = []
        lines.append(f"=== DECISION: {window.upper()} === Turn {self.turn} ({'your' if self.active is p else 'opponent'} turn), phase {self.phase}")
        lines.append(f"You ({p.name}): {p.life} life, {len(p.library)} in library | Opponent ({o.name}): {o.life} life, {len(o.hand)} in hand, {len(o.library)} in library")
        if error:
            lines.append(f"!! Your last script failed: {error}")
        new = self.log[p.seen_log:]
        p.seen_log = len(self.log)
        if new:
            lines.append("Events since your last decision:")
            lines += ["  " + e for e in new[-25:]]
        if self.stack:
            lines.append("STACK (top last): " + "; ".join(
                f"#{e['obj'].id} {e['obj'].name} by {e['caster'].name}" +
                (f" -> {e['target'].name if isinstance(e['target'], (Player, Obj)) else e['target']['obj'].name}" if e['target'] is not None else "")
                for e in self.stack))
        lines.append("Your hand: " + (", ".join(f"#{c.id} {c.name}" + (f" ({c.card.cost})" if not c.card.is_land else "") for c in p.hand) or "(empty)"))
        lines.append("Your battlefield: " + (", ".join(x.label(self) for x in p.battlefield) or "(empty)"))
        if p.pool:
            lines.append("Floating mana: " + "".join(p.pool))
        lines.append(f"Untapped mana available: {self.mana_potential(p)} " +
                     "(" + ", ".join(f"#{s.id} {s.name}={prod}" for s, prod in self.sources(p)) + ")")
        lines.append("Opponent battlefield: " + (", ".join(x.label(self) for x in o.battlefield) or "(empty)"))
        lines.append(f"Graveyards: yours [{', '.join(c.name for c in p.graveyard)}] | theirs [{', '.join(c.name for c in o.graveyard)}]")
        if window == "block" and self.attackers:
            lines.append("ATTACKING YOU: " + ", ".join(a.label(self) for a in self.attackers))
            lines.append("Untapped potential blockers: " + (", ".join(c.label(self) for c in p.creatures() if not c.tapped) or "none"))
        if self.has_moat():
            lines.append("MOAT is on the battlefield: only fliers can attack.")
        return "\n".join(lines)
