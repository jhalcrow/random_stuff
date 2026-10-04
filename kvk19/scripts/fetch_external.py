#!/usr/bin/env python3
"""Fetch public kingdom history for K203 and K365. No API key needed.

- kingshotguide.org: daily kingdom stats (free tier: last 7 days + deltas since tracking began)
- kingshotoptimizer.com: KvK history and Bradley-Terry ratings (overall / prep / battle rank)

Writes data/external/{kingshotguide,kingshotoptimizer}_{kid}.json. Kingdom-level data only.
"""
import json
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "external"
UA = {"User-Agent": "kvk19-scout/1.0 (python urllib)", "Accept": "application/json"}


def fetch(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = dict(UA, **({"Content-Type": "application/json"} if body is not None else {}))
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as r:
        return json.load(r)


OUT.mkdir(parents=True, exist_ok=True)
for kid in (203, 365):
    g = fetch(f"https://www.kingshotguide.org/api/kingdom-rankings/{kid}/stats")
    (OUT / f"kingshotguide_{kid}.json").write_text(json.dumps(g, indent=1) + "\n")
    o = fetch("https://kingshotoptimizer.com/api/kvk-rankings", {"type": "kingdom", "kingdomId": kid})
    (OUT / f"kingshotoptimizer_{kid}.json").write_text(json.dumps(o, indent=1) + "\n")
    print(f"K{kid}: {len(g.get('series', []))} daily points, {len(o['result']['history'])} KvKs")
