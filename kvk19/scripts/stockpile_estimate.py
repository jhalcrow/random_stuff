#!/usr/bin/env python3
"""Rough estimate of the speedup reserve each kingdom brings into KvK 19 prep.

Method (every input below is either measured or a labelled assumption):
  1. Saving window: KvK 18 prep ended Fri 11 Sep; KvK 19 prep opens Mon 5 Oct -> 23 days.
  2. Free speedup income per active player: 80-200 h per month (kingshotmastery.com free
     resources guide, its own rough range) -> 2.67-6.67 h/day.
  3. Active base: governors active in the last 30 days (kingshotguide.org and MightPulse).
  4. Gross income = actives x income x days.
  5. Banked share: how much of that income was saved rather than spent. Inferred from power
     growth per active player since 15 Sep (spending shows up as power). ASSUMPTION ranges.
  6. Prep points: speedups score 30 points per minute (1,800 per hour) on the days they count.
Paid accounts are assumed to cancel out (top-100 governor power is within 2%).

Writes data/stockpile_estimate.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
mp = json.loads((D / "mightpulse_summary.json").read_text())
ext = {k: json.loads((D / f"external/kingshotguide_{k}.json").read_text()) for k in ("203", "365")}

DAYS = 23
INCOME_H_PER_DAY = (80 / 30, 200 / 30)
PTS_PER_H = 30 * 60
# Banked-share assumptions, set from the spending signal computed below.
BANKED = {"203": (0.50, 0.75), "365": (0.60, 0.85)}

out = {"saving_window_days": DAYS, "income_h_per_day": [round(x, 2) for x in INCOME_H_PER_DAY],
       "points_per_hour": PTS_PER_H, "kingdoms": {}}
for k in ("203", "365"):
    s = ext[k]
    series = s["series"]
    now = series[-1]
    a30 = sorted({now["active30d"], mp["kingdoms"][k]["kingdom"]["active_30d"]})
    growth = s["deltas"]["power"]
    # Step changes: a day-over-day jump together with a jump in player count looks like an intake
    # of accounts (or a batch refresh), not organic growth. Separate it out.
    steps = []
    for prev, cur in zip(series, series[1:]):
        dp, dn = cur["power"] - prev["power"], cur["playerCount"] - prev["playerCount"]
        if dn >= 50 and dp >= 2e9:
            steps.append({"date": cur["date"], "power": dp, "players": dn})
    step_power = sum(x["power"] for x in steps)
    organic = growth - step_power
    a30_before = series[0]["active30d"]
    per_active = (organic / a30_before, growth / a30[-1])
    gross_h = (a30[0] * INCOME_H_PER_DAY[0] * DAYS, a30[-1] * INCOME_H_PER_DAY[1] * DAYS)
    mid_gross = sum(a30) / 2 * sum(INCOME_H_PER_DAY) / 2 * DAYS
    lo_b, hi_b = BANKED[k]
    banked_h = (gross_h[0] * lo_b, gross_h[1] * hi_b)
    mid_h = mid_gross * (lo_b + hi_b) / 2
    out["kingdoms"][k] = {
        "active_30d": a30,
        "power_now": now["power"],
        "power_growth_since_tracking": growth,
        "tracking_since": s["trackingSince"],
        "step_changes": steps,
        "organic_growth": organic,
        "growth_per_active_m": [round(x / 1e6, 1) for x in per_active],
        "gross_hours": [round(x) for x in gross_h],
        "banked_share": [lo_b, hi_b],
        "banked_hours": [round(x) for x in banked_h],
        "banked_hours_mid": round(mid_h),
        "prep_points": [round(x * PTS_PER_H) for x in banked_h],
        "prep_points_mid": round(mid_h * PTS_PER_H),
        "daily_series": [{"date": r["date"], "power": r["power"], "players": r["playerCount"]} for r in series],
    }

u, t = out["kingdoms"]["203"], out["kingdoms"]["365"]
n_ratio = (t["active_30d"][0] / u["active_30d"][-1], t["active_30d"][-1] / u["active_30d"][0])
share_ratio = (1.0, 1.4)   # ASSUMPTION: K365 banked the same to 40% more of its income than K203
out["reserve_ratio_365_vs_203"] = [round(n_ratio[0] * share_ratio[0], 2), round(n_ratio[1] * share_ratio[1], 2)]
out["reserve_ratio_mid"] = round(t["banked_hours_mid"] / u["banked_hours_mid"], 2)
(D / "stockpile_estimate.json").write_text(json.dumps(out, indent=2) + "\n")
for k, v in out["kingdoms"].items():
    print(f"K{k}: actives {v['active_30d']}, growth {v['power_growth_since_tracking']/1e9:.2f}B "
          f"(organic {v['organic_growth']/1e9:.2f}B, steps {v['step_changes']}), per active {v['growth_per_active_m']}M, "
          f"banked {v['banked_hours'][0]:,}-{v['banked_hours'][1]:,} h (mid {v['banked_hours_mid']:,}), "
          f"points {v['prep_points'][0]/1e6:.0f}M-{v['prep_points'][1]/1e6:.0f}M (mid {v['prep_points_mid']/1e6:.0f}M)")
print("ratio", out["reserve_ratio_365_vs_203"], "mid", out["reserve_ratio_mid"])
