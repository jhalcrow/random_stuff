#!/usr/bin/env python3
"""Pull kingdom + top-6 alliance activity aggregates from MightPulse.

Usage:
  python3 scripts/mightpulse_pull.py --probe   # print response shapes only (keys/types, no values)
  python3 scripts/mightpulse_pull.py           # write data/mightpulse_summary.json

The API key is read from MIGHTPULSE_API_KEY and is never printed. Member-level
data stays in memory; only per-alliance aggregates are written.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.mightpulse.com/v1"
KINGDOMS = (203, 365)
TOP_N = 6
MIN_INTERVAL = 1.1  # seconds between requests; keeps us under 60 req/min
OUT = Path(__file__).resolve().parent.parent / "data" / "mightpulse_summary.json"
KINGDOM_FIELDS = ("player_count", "located", "active_7d", "active_30d", "alliance_count",
                  "power", "avg_power", "power_rank", "activity_rank", "health",
                  "power_gain_7d", "tc_pushers_7d", "hero_power", "troop_power")

_last_call = 0.0


def api_key():
    key = os.environ.get("MIGHTPULSE_API_KEY")
    if not key:
        sys.exit("MIGHTPULSE_API_KEY is not set")
    return key


def get(path, params=None):
    global _last_call
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(5):
        wait = MIN_INTERVAL - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + api_key(),
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                delay = float(e.headers.get("Retry-After") or 2 ** (attempt + 2))
                print(f"429 on {path}; waiting {delay:.0f}s", file=sys.stderr)
                time.sleep(delay)
                continue
            # Report status + path only; never echo headers (they carry the key).
            raise SystemExit(f"HTTP {e.code} on GET {path}") from None
    raise SystemExit(f"gave up on GET {path} after repeated 429s")


def shape(obj, depth=0, max_depth=4):
    """Structure of a JSON value with values stripped (safe to print: no names)."""
    if isinstance(obj, dict):
        if depth >= max_depth:
            return "{...}"
        return {k: shape(v, depth + 1, max_depth) for k, v in obj.items()}
    if isinstance(obj, list):
        return [f"len={len(obj)}", shape(obj[0], depth + 1, max_depth)] if obj else []
    return type(obj).__name__


def unwrap(obj):
    """Strip a common {'data': ...} envelope if present."""
    return obj["data"] if isinstance(obj, dict) and "data" in obj and len(obj) <= 3 else obj


def find_list(obj, keys):
    obj = unwrap(obj)
    if isinstance(obj, list):
        return obj
    for k in keys:
        if isinstance(obj.get(k), list):
            return obj[k]
        if isinstance(obj.get(k), dict):  # e.g. {"roster": {"members": [...]}}
            inner = find_list(obj[k], keys)
            if inner is not None:
                return inner
    return None


def parse_ts(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000 if v > 1e12 else v, timezone.utc)
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def top_alliances(kid):
    rows = find_list(get(f"/kingdoms/{kid}/ranks", {"board": "alliance_power", "limit": TOP_N}),
                     ("rows", "items", "results"))
    if rows is None:
        raise SystemExit(f"could not find rows in ranks response for K{kid}; run --probe")
    return [{"tag": r["abbr"], "name": r.get("name"), "score": r.get("score")} for r in rows[:TOP_N]]


def alliance_activity(kid, tag, now):
    resp = get(f"/alliances/{kid}/{urllib.parse.quote(tag, safe='')}", {"include": "info,roster"})
    members = find_list(resp, ("members", "roster"))
    if members is None:
        raise SystemExit(f"could not find members for K{kid} {tag}; run --probe")
    windows = {"24h": 1, "72h": 3, "7d": 7}
    counts = dict.fromkeys(windows, 0)
    total_power = power_7d = 0
    unknown_ts = 0
    for m in members:
        p = m.get("power") or 0
        total_power += p
        ts = parse_ts(m.get("last_active_at"))
        if m.get("online"):
            age_days = 0.0
        elif ts is None:
            unknown_ts += 1
            continue
        else:
            age_days = (now - ts).total_seconds() / 86400
        for w, d in windows.items():
            if age_days <= d:
                counts[w] += 1
        if age_days <= 7:
            power_7d += p
    n = len(members)
    tcs = [m["town_center_level"] for m in members if isinstance(m.get("town_center_level"), (int, float))]
    return {
        "tag": tag,
        "members": n,
        "active_24h": counts["24h"],
        "active_72h": counts["72h"],
        "active_7d": counts["7d"],
        "active_7d_pct": round(100 * counts["7d"] / n, 1) if n else None,
        "total_power": total_power,
        "power_share_active_7d_pct": round(100 * power_7d / total_power, 1) if total_power else None,
        "median_tc_level": sorted(tcs)[len(tcs) // 2] if tcs else None,
        "members_missing_last_active": unknown_ts,
    }


def probe():
    """Print shapes of each endpoint (no values) so parsing can be checked."""
    kid = KINGDOMS[0]
    print(f"== /kingdoms/{kid}")
    print(json.dumps(shape(get(f"/kingdoms/{kid}")), indent=2))
    ranks = get(f"/kingdoms/{kid}/ranks", {"board": "alliance_power", "limit": 2})
    print(f"== /kingdoms/{kid}/ranks")
    print(json.dumps(shape(ranks), indent=2))
    rows = find_list(ranks, ("rows", "items", "results")) or []
    if rows and "abbr" in rows[0]:
        tag = rows[0]["abbr"]
        a = get(f"/alliances/{kid}/{urllib.parse.quote(tag, safe='')}", {"include": "info,roster"})
        print(f"== /alliances/{kid}/<tag>?include=info,roster")
        print(json.dumps(shape(a), indent=2))
        m = find_list(a, ("members", "roster"))
        if m:
            sample = [x.get("last_active_at") for x in m[:3]]
            print("last_active_at value types:", [type(v).__name__ for v in sample])
            print("last_active_at looks numeric:", all(isinstance(v, (int, float)) for v in sample if v is not None))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()
    api_key()
    if args.probe:
        probe()
        return
    now = datetime.now(timezone.utc)
    out = {"generated_at": now.isoformat(timespec="seconds"),
           "source": "MightPulse API (data up to 1h old)",
           "activity_basis": "online now or last_active_at within window",
           "kingdoms": {}}
    for kid in KINGDOMS:
        k = unwrap(get(f"/kingdoms/{kid}"))
        kingdom = {f: k.get(f) for f in KINGDOM_FIELDS}
        alliances = []
        for a in top_alliances(kid):
            row = alliance_activity(kid, a["tag"], now)
            row["rank_score"] = a["score"]
            alliances.append(row)
        tot = lambda f: sum(a[f] for a in alliances)
        top = {f: tot(f) for f in ("members", "active_24h", "active_72h", "active_7d", "total_power")}
        p7 = sum(a["total_power"] * (a["power_share_active_7d_pct"] or 0) / 100 for a in alliances)
        top["active_7d_pct"] = round(100 * top["active_7d"] / top["members"], 1) if top["members"] else None
        top["power_share_active_7d_pct"] = round(100 * p7 / top["total_power"], 1) if top["total_power"] else None
        out["kingdoms"][str(kid)] = {"kingdom": kingdom, "top_alliances": alliances, "top6_totals": top}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
