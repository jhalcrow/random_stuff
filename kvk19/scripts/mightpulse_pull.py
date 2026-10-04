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
                  "power_gain_7d", "tc_pushers_7d", "hero_power", "troop_power",
                  # Kingdom-level power fields are sums over each top-100 leaderboard.
                  "mystic_trial", "hero_total", "hero_equip", "governor_gear_power",
                  "governor_charm_power", "pet_power", "research_power", "building_power",
                  "master_power", "gov_power")
SCORE_BOARDS = ("mystic_trial",)  # player boards: only scores are kept, never names or IDs

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
                                                   "Accept": "application/json",
                                                   # Cloudflare rejects the default Python-urllib UA (error 1010).
                                                   "User-Agent": "kvk19-scout/1.0 (python urllib)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                delay = float(e.headers.get("Retry-After") or 2 ** (attempt + 2))
                print(f"429 on {path}; waiting {delay:.0f}s", file=sys.stderr)
                time.sleep(delay)
                continue
            # Report status, path and a redacted body snippet; never echo headers (they carry the key).
            body = e.read(300).decode("utf-8", "replace").replace(api_key(), "<redacted>")
            raise SystemExit(f"HTTP {e.code} on GET {path}: {body}") from None
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
    resp = get(f"/kingdoms/{kid}/ranks", {"board": "alliance_power", "limit": TOP_N})
    rows = (resp.get("board") or {}).get("rows")  # shape confirmed by --probe: {"board": {"rows": [...]}}
    if rows is None:
        raise SystemExit(f"could not find rows in ranks response for K{kid}; run --probe")
    return [{"tag": r["abbr"], "name": r.get("name"), "score": r.get("score")} for r in rows[:TOP_N]]


def board_scores(kid, board):
    """Aggregate a player leaderboard by rank band. Names and IDs are discarded here."""
    bd = get(f"/kingdoms/{kid}/ranks", {"board": board, "limit": 100})["board"]
    sc = sorted((r["score"] for r in bd["rows"]), reverse=True)
    band = lambda a, b: sc[a:b]
    avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None
    return {
        "captured_at": datetime.fromtimestamp(bd["captured_at"], timezone.utc).isoformat(timespec="seconds"),
        "n": len(sc),
        "total": sum(sc),
        "at_rank": {str(r): sc[r - 1] for r in (1, 5, 10, 25, 50, 75, 100) if r <= len(sc)},
        "avg_1_10": avg(band(0, 10)),
        "avg_11_50": avg(band(10, 50)),
        "avg_51_100": avg(band(50, 100)),
    }


def fetch_roster(kid, tag):
    """Roster stays in memory only; never written to disk."""
    resp = get(f"/alliances/{kid}/{urllib.parse.quote(tag, safe='')}", {"include": "info,roster"})
    members = find_list(resp, ("members", "roster"))
    if members is None:
        raise SystemExit(f"could not find members for K{kid} {tag}; run --probe")
    return resp, members


def activity(members, ref, use_online):
    """Counts of members active within 24h/72h/7d of `ref`, and power share of 7d actives."""
    windows = {"24h": 1, "72h": 3, "7d": 7}
    counts = dict.fromkeys(windows, 0)
    total_power = power_7d = 0
    for m in members:
        p = m.get("power") or 0
        total_power += p
        ts = parse_ts(m.get("last_active_at"))
        if use_online and m.get("online"):
            age_days = 0.0
        elif ts is None:
            continue
        else:
            age_days = (ref - ts).total_seconds() / 86400
        for w, d in windows.items():
            if age_days <= d:
                counts[w] += 1
        if age_days <= 7:
            power_7d += p
    n = len(members)
    return {
        "active_24h": counts["24h"],
        "active_72h": counts["72h"],
        "active_7d": counts["7d"],
        "active_7d_pct": round(100 * counts["7d"] / n, 1) if n else None,
        "power_share_active_7d_pct": round(100 * power_7d / total_power, 1) if total_power else None,
    }


def alliance_summary(tag, resp, members, now, anchor):
    tcs = sorted(m["town_center_level"] for m in members if isinstance(m.get("town_center_level"), (int, float)))
    return {
        "tag": tag,
        "members": len(members),
        "member_count_reported": resp.get("member_count"),
        "total_power": sum(m.get("power") or 0 for m in members),
        "median_tc_level": tcs[len(tcs) // 2] if tcs else None,
        "members_missing_last_active": sum(parse_ts(m.get("last_active_at")) is None for m in members),
        "online_now": sum(bool(m.get("online")) for m in members),
        "data_age_seconds": resp.get("age_seconds"),
        "vs_now": activity(members, now, use_online=True),
        "vs_snapshot": activity(members, anchor, use_online=False),
    }


def totals(alliances, key):
    t = {f: sum(a[key][f] for a in alliances) for f in ("active_24h", "active_72h", "active_7d")}
    n = sum(a["members"] for a in alliances)
    pw = sum(a["total_power"] for a in alliances)
    p7 = sum(a["total_power"] * (a[key]["power_share_active_7d_pct"] or 0) / 100 for a in alliances)
    t["active_7d_pct"] = round(100 * t["active_7d"] / n, 1) if n else None
    t["power_share_active_7d_pct"] = round(100 * p7 / pw, 1) if pw else None
    return t


def probe():
    """Print shapes of each endpoint (no values) so parsing can be checked."""
    kid = KINGDOMS[0]
    print(f"== /kingdoms/{kid}")
    print(json.dumps(shape(get(f"/kingdoms/{kid}")), indent=2))
    ranks = get(f"/kingdoms/{kid}/ranks", {"board": "alliance_power", "limit": 2})
    print(f"== /kingdoms/{kid}/ranks")
    print(json.dumps(shape(ranks), indent=2))
    rows = (ranks.get("board") or {}).get("rows") or []
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
    kingdoms, rosters = {}, {}
    for kid in KINGDOMS:
        k = get(f"/kingdoms/{kid}")["kingdom"]  # shape confirmed by --probe
        kingdoms[kid] = {f: k.get(f) for f in KINGDOM_FIELDS}
        kingdoms[kid]["boards"] = {bd: board_scores(kid, bd) for bd in SCORE_BOARDS}
        rosters[kid] = [(a, *fetch_roster(kid, a["tag"])) for a in top_alliances(kid)]
    # last_active_at may lag far behind "now" (seen: frozen at 15 Sep while responses say fresh).
    # Anchor a second set of windows on the newest timestamp seen across all rosters.
    all_ts = [t for rs in rosters.values() for _, _, ms in rs for m in ms
              if (t := parse_ts(m.get("last_active_at")))]
    anchor = max(all_ts)
    lag_days = (now - anchor).total_seconds() / 86400
    out = {"generated_at": now.isoformat(timespec="seconds"),
           "source": "MightPulse API",
           "activity_basis": "vs_now: online or last_active_at within window of generated_at; "
                             "vs_snapshot: last_active_at within window of activity_snapshot_at",
           "activity_snapshot_at": anchor.isoformat(timespec="seconds"),
           "activity_lag_days": round(lag_days, 1),
           "activity_stale": lag_days > 1,
           "kingdoms": {}}
    for kid in KINGDOMS:
        alliances = []
        for a, resp, members in rosters[kid]:
            row = alliance_summary(a["tag"], resp, members, now, anchor)
            row["rank_score"] = a["score"]
            alliances.append(row)
        top = {"members": sum(a["members"] for a in alliances),
               "total_power": sum(a["total_power"] for a in alliances),
               "vs_now": totals(alliances, "vs_now"),
               "vs_snapshot": totals(alliances, "vs_snapshot")}
        out["kingdoms"][str(kid)] = {"kingdom": kingdoms[kid], "top_alliances": alliances, "top6_totals": top}
    if out["activity_stale"]:
        print(f"WARNING: newest last_active_at is {lag_days:.1f} days old; vs_now counts are not meaningful",
              file=sys.stderr)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
