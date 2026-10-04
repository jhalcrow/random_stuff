#!/usr/bin/env python3
"""Run the alliance battle simulator (../kingshot/sim.py) to compare troop count with stat quality.

Heroless mirror fights (the engine's best-validated regime), troop abilities off so only the
damage core is exercised. Writes data/sim_levers.json. No player data involved.

  python3 scripts/sim_levers.py
"""
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("TROOP_SKILLS", "0")
os.environ.setdefault("ROUND_MODE", "ceil")   # deterministic
sys.path.insert(0, str(ROOT.parent / "kingshot"))
import sim  # noqa: E402
from sim import Side, battle, USER_STATS, MARCH, ratio_troops, HERO_STATS, GEAR_EXP_ATK, GEAR_EXP_LETH  # noqa: E402

RATIO = (50, 20, 30)


def side(name, n=MARCH, mult=1.0, tg=8):
    st = copy.deepcopy(USER_STATS)
    for t in st:
        for k in ("attack", "lethality"):  # scale the (1 + x%) factor itself
            st[t][k] = ((1 + st[t][k] / 100) * mult - 1) * 100
    return Side(name, st, ratio_troops(int(n), *RATIO), heroes=[], tg=tg, ambusher=0.0)


CASES = [
    ("+20% troops", dict(n=MARCH * 1.2), {}),
    ("+50% troops", dict(n=MARCH * 1.5), {}),
    ("2x troops", dict(n=MARCH * 2), {}),
    ("+20% attack and lethality", dict(mult=1.2), {}),
    ("+50% attack and lethality", dict(mult=1.5), {}),
    ("Truegold 8 vs Truegold 5 troops", {}, dict(tg=5)),
]

rows = []
for label, a_kw, d_kw in CASES:
    r = battle(side("A", **a_kw), side("D", **d_kw))
    rows.append({"change": label, "kill_ratio": round(r["d_lost"] / max(r["a_lost"], 1), 2),
                 "winner_lost_pct": round(100 * r["a_lost"] / MARCH, 1)})

# Measured hero contribution (sim.py: exp_atk + gear, weapon + gear) vs the account's own stat totals.
gen7 = max(HERO_STATS.values(), key=lambda h: h.get("exp_atk", 0))
acct = USER_STATS["inf"]
hero = {
    "hero_attack_defense_pct": round(gen7["exp_atk"] + GEAR_EXP_ATK),
    "hero_lethality_health_pct": round(gen7["weapon_lv10"] + GEAR_EXP_LETH),
    "account_attack_pct": round(acct["attack"]),
    "account_lethality_pct": round(acct["lethality"]),
}
out = {"model": "kingshot/sim.py heroless mirror, 144,200 troops at 50/20/30", "cases": rows, "hero": hero}
(ROOT / "data/sim_levers.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
