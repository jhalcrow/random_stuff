#!/usr/bin/env python3
"""Summarise results/*.json produced by server.py."""
import glob
import json
import sys

files = sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else "results/agents_*.json"))
tot_w = tot_g = 0
for f in files:
    d = json.load(open(f))
    rows = []
    for r in d["results"]:
        w = r["winner"]
        tot_g += 1
        tot_w += (w == d["a"])
        fb = sum(1 for e in r["log"] if "agent timed out" in e)
        rows.append(f"  game {r['game']}: {r['on_the_play']} on the play -> {w} on turn {r['turns']} "
                    f"(life {r['life'][d['a']]} / {r['life'][d['b']]}){' [bot fallbacks: %d]' % fb if fb else ''}")
    print(f"{d['a']} vs {d['b']}:")
    print("\n".join(rows))
print(f"\n12 Bolt total: {tot_w}/{tot_g}")
