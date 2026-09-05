"""A generic heuristic policy so the engine can be smoke-tested and so a
subagent can be paired against a fast bot when needed."""
from engine import Player, Obj


class Bot:
    def __init__(self, name="bot"):
        self.name = name

    def decide(self, game, p, window, error):
        if error and window == "tutor":
            return self.w_tutor(game, p)
        if error and window not in ("main1", "main2"):
            return "pass"
        if error:
            # something in the script was illegal: fall back to just attacking / ending
            return self.attack_line(game, p) if window == "main1" else "done"
        fn = getattr(self, "w_" + window, None)
        return fn(game, p) if fn else "pass"

    def attack_line(self, game, p, extra_names=()):
        attackers = []
        blockers = [b for b in p.opp.creatures() if not b.tapped]
        for c in p.creatures():
            if c.tapped or (c.sick and "haste" not in c.keywords(game)):
                continue
            if game.has_moat() and "flying" not in c.keywords(game):
                continue
            killers = [b for b in blockers if ("flying" in b.keywords(game) or "flying" not in c.keywords(game))
                       and b.power(game) >= c.tough(game) and (b.tough(game) > c.power(game) or "first strike" in b.keywords(game))]
            if not killers or p.opp.life <= c.power(game):
                attackers.append(f"#{c.id}")
        attackers += list(extra_names)
        return ("attack " + " ".join(attackers)) if attackers else "done"

    # ---- helpers
    def castable(self, game, p, c):
        pot = game.mana_potential(p)
        return c.card.cmc <= pot

    def best_creature_target(self, game, p, dmg=None):
        opp = p.opp.creatures()
        if dmg is not None:
            opp = [c for c in opp if c.tough(game) - c.damage <= dmg]
        if not opp:
            return None
        return max(opp, key=lambda c: (c.power(game), c.tough(game)))

    def w_mulligan(self, game, p):
        lands = sum(1 for c in p.hand if c.card.is_land or c.card.produces)
        return "keep" if 2 <= lands <= 5 or len(p.hand) <= 5 else "mulligan"

    def w_tutor(self, game, p):
        for want in ("Ancestral Recall", "Juzam Djinn", "Moat", "Balance", "Black Lotus", "Serra Angel"):
            if any(c.name == want for c in p.library):
                return want
        return p.library[0].name

    def w_main1(self, game, p):
        acts = []
        budget = game.mana_potential(p)
        lands = [c for c in p.hand if c.card.is_land]
        if lands and p.lands_played == 0:
            # colour we lack first
            have = "".join(l.card.produces for l in p.battlefield)
            need = "".join(c.card.cost for c in p.hand if not c.card.is_land)
            def score(l):
                pr = l.card.produces
                if l.name == "Library of Alexandria":
                    return 3 if len(p.hand) >= 6 else -1
                if l.name == "Strip Mine":
                    return -2
                return sum(1 for ch in pr if ch in need and ch not in have) + (0.5 if pr == "WUBRG" else 0) + 0.1 * len(pr)
            best = max(lands, key=score)
            acts.append(f"land #{best.id}")
            if best.card.produces and best.name != "Library of Alexandria":
                budget += 1
        for c in p.hand:
            if c.card.produces and not c.card.is_land and c.name != "Black Lotus" and c.card.cmc <= budget:
                acts.append(f"cast #{c.id}")
                budget += (2 if c.name == "Sol Ring" else 1) - c.card.cmc
        if any(c.name == "Black Lotus" for c in p.hand):
            acts.append("cast Black Lotus")
        hasty = [c.name for c in p.hand if "haste" in c.card.kw and c.card.cmc <= budget]

        def spend(c, extra=0):
            nonlocal budget
            if c.card.cmc + extra <= budget:
                budget -= c.card.cmc + extra
                return True
            return False

        # card draw
        for c in p.hand:
            if c.card.effect in ("draw3", "timewalk") and spend(c):
                acts.append(f"cast #{c.id}" + (" target me" if c.card.effect == "draw3" else ""))
        # removal on big things
        opp_big = [c for c in p.opp.creatures() if c.tough(game) >= 4]
        for c in p.hand:
            if c.card.effect in ("swords", "terror") and opp_big and spend(c):
                acts.append(f"cast #{c.id} target #{opp_big[0].id}")
                opp_big = opp_big[1:]
        if any(c.card.effect == "ritual" for c in p.hand) and any(c.card.is_creature and c.card.cmc >= 3 for c in p.hand):
            r = next(c for c in p.hand if c.card.effect == "ritual")
            if spend(r):
                acts.append(f"cast #{r.id}")
                budget += 3
        # creatures, most expensive first
        for c in sorted([c for c in p.hand if c.card.is_creature], key=lambda c: -c.card.cmc):
            if spend(c):
                acts.append(f"cast #{c.id}")
        for c in p.hand:
            if c.name in ("Crusade", "Moat", "The Abyss", "Black Vise", "Jayemdae Tome", "Chaos Orb", "Nevinyrral's Disk") and spend(c):
                acts.append(f"cast #{c.id}")
        for c in p.hand:
            if c.card.effect == "aura" and p.creatures() and spend(c):
                best = max(p.creatures(), key=lambda x: ("flying" in x.keywords(game), x.power(game)))
                acts.append(f"cast #{c.id} target #{best.id}")
        # burn: kill a creature that blocks us, else face
        for c in p.hand:
            if c.card.effect in ("damage3", "psiblast") and spend(c):
                tgt = self.best_creature_target(game, p, 3 if c.card.effect == "damage3" else 4)
                if tgt is not None and tgt.power(game) >= 2 and p.opp.life > 6:
                    acts.append(f"cast #{c.id} target #{tgt.id}")
                else:
                    acts.append(f"cast #{c.id} target opp")
        for c in p.hand:
            if c.card.effect == "fireball":
                x = budget - 1
                if x >= 2 and spend(c, x):
                    acts.append(f"cast #{c.id} x={x} target opp")
            if c.card.effect == "hymn" and spend(c):
                acts.append(f"cast #{c.id} target opp")
            if c.card.effect == "mindtwist":
                x = budget - 1
                if x >= 2 and len(p.opp.hand) >= 2 and spend(c, x):
                    acts.append(f"cast #{c.id} x={x} target opp")
            if c.card.effect == "tutor" and spend(c):
                acts.append(f"cast #{c.id}")
            if c.card.effect in ("wheel", "twister") and len(p.hand) <= 2 and spend(c):
                acts.append(f"cast #{c.id}")
            if c.card.effect == "geddon" and len(p.creatures()) > len(p.opp.creatures()) + 1 and spend(c):
                acts.append(f"cast #{c.id}")
        acts.append(self.attack_line(game, p, hasty))
        return "\n".join(acts)

    def w_main2(self, game, p):
        acts = []
        budget = game.mana_potential(p)
        for c in sorted([c for c in p.hand if c.card.is_creature], key=lambda c: -c.card.cmc):
            if c.card.cmc <= budget:
                budget -= c.card.cmc
                acts.append(f"cast #{c.id}")
        for c in p.hand:
            if c.card.effect in ("damage3", "psiblast") and c.card.cmc <= budget:
                budget -= c.card.cmc
                acts.append(f"cast #{c.id} target opp")
        acts.append("done")
        return "\n".join(acts)

    def w_block(self, game, p):
        acts = []
        used = set()
        for a in sorted(game.attackers, key=lambda a: -a.power(game)):
            cands = [b for b in p.creatures() if not b.tapped and b.id not in used
                     and ("flying" not in a.keywords(game) or "flying" in b.keywords(game))]
            # block if we kill it and survive, or if we would die otherwise
            good = [b for b in cands if b.power(game) >= a.tough(game) and b.tough(game) > a.power(game)]
            trade = [b for b in cands if b.power(game) >= a.tough(game)]
            incoming = sum(x.power(game) for x in game.attackers)
            if good:
                b = good[0]
            elif trade and p.life <= p.opp.life:
                b = trade[0]
            elif cands and incoming >= p.life:
                b = min(cands, key=lambda b: b.power(game))
            else:
                continue
            used.add(b.id)
            acts.append(f"block #{a.id} with #{b.id}")
        return "\n".join(acts) or "pass"

    def w_combat(self, game, p):
        acts = []
        if any(a.name == "Atog" for a in game.attackers):
            arts = [o for o in p.battlefield if o.is_artifact() and o.name != "Atog" and not o.card.is_creature]
            for a in arts[:3]:
                acts.append(f"sac atog #{a.id}")
        return "\n".join(acts) or "pass"

    def w_respond(self, game, p):
        top = game.stack[-1]
        spell = top["obj"].card
        for c in p.hand:
            if not self.castable(game, p, c):
                continue
            if c.card.effect == "counter" and (spell.is_creature or spell.effect in ("draw3", "wheel", "twister", "geyser", "aura", "balance", "geddon", "mindtwist")):
                return f"cast #{c.id} target #{top['obj'].id}"
            if c.card.effect == "reb" and "blue" in spell.colors:
                return f"cast #{c.id} target #{top['obj'].id}"
            if c.card.effect == "beb" and "red" in spell.colors and spell.effect in ("damage3", "fireball", "wheel"):
                return f"cast #{c.id} target #{top['obj'].id}"
        return "pass"

    def w_eot(self, game, p):
        acts = []
        for c in p.hand:
            if c.card.effect in ("damage3", "psiblast") and c.card.is_instant and self.castable(game, p, c):
                acts.append(f"cast #{c.id} target opp")
                break
        return "\n".join(acts) or "pass"
