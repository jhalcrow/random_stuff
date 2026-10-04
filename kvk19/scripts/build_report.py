#!/usr/bin/env python3
"""Build the shareable KvK 19 report from data/known_data.json + data/mightpulse_summary.json.

Writes report/kvk19_report.html (full standalone document) and
report/kvk19_report.body.html (same page without the document skeleton, for hosting).
Aggregate numbers only: no player names anywhere.
"""
import json
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
known = json.loads((ROOT / "data/known_data.json").read_text())
mp = json.loads((ROOT / "data/mightpulse_summary.json").read_text())
K = known["kingdoms"]
US, THEM = K["203"], K["365"]
MU, MT = mp["kingdoms"]["203"], mp["kingdoms"]["365"]
snap = datetime.fromisoformat(mp["activity_snapshot_at"])
pulled = datetime.fromisoformat(mp["generated_at"])
SNAP = f"{snap.day} {snap:%b}"
PULLED = f"{pulled.day} {pulled:%b %Y}"

# Projections (judgement estimates, % chance K203 wins the phase)
PROJ = {
    "prep": {"before": (50, 55), "after": (42, 52)},
    "castle": {"before": (45, 55), "after": (45, 55)},
}


def b(n):
    return f"{n / 1e9:.1f}B"


def pct(a, n):
    return round(100 * a / n) if n else 0


def unconf(text="Unconfirmed"):
    return f'<span class="tag-unc">{text}</span>'


# ---------- matchup table ----------
def edge(a, c, higher_better=True, tol=0.0):
    if abs(a - c) <= tol:
        return '<span class="edge even">Even</span>'
    us_lead = (a > c) == higher_better
    return f'<span class="edge {"us" if us_lead else "them"}">{"K203" if us_lead else "K365"}</span>'


def rec(r):
    w, l = map(int, r.split("-"))
    return w, l


us_top5 = sum(US["top5_player_power_m"])
th_top5 = sum(THEM["top5_player_power_m"])
us_ally5 = sum(a["real_power_b"] for a in US["top_alliances"])
th_ally5 = sum(a["real_power_b"] for a in THEM["top_alliances"])
ku, kt = MU["kingdom"], MT["kingdom"]

matchup_rows = [
    ("Kingdom age", f'~{US["age_days_approx"]} days', f'~{THEM["age_days_approx"]} days', '<span class="edge even">Even</span>', ""),
    ("Stage", "Adv. Truegold / Gen 7", "Adv. Truegold / Gen 7", '<span class="edge even">Even</span>', ""),
    ("Real power (kingdom)", f'{US["real_power_b"]}B', f'{THEM["real_power_b"]}B', edge(2.8, 2.7, tol=0.15), "def"),
    ("Top-10 total", f'{US["top10_total_b"]}B', f'{THEM["top10_total_b"]}B', edge(8.3, 8.4, tol=0.15), "def"),
    ("Top 5 players, combined real power", f"{us_top5:,}M", f"{th_top5:,}M", edge(us_top5, th_top5), ""),
    ("Top 5 alliances, combined real power", f"{us_ally5:.1f}B", f"{th_ally5:.1f}B", edge(us_ally5, th_ally5), ""),
    ("Top 6 alliances, total power (incl. troops)", b(MU["top6_totals"]["total_power"]), b(MT["top6_totals"]["total_power"]),
     edge(MU["top6_totals"]["total_power"], MT["top6_totals"]["total_power"], tol=2e9), ""),
    ("Cities on the map", f'{US["cities"]:,}', f'{THEM["cities"]:,}', edge(US["cities"], THEM["cities"]), "stale203"),
    ("Alliances", f'{US["alliances"]:,}', f'{THEM["alliances"]:,}', '<span class="edge neutral">n/a</span>', "stale203"),
    ("KvK prep record", US["prep_record"], THEM["prep_record"], edge(16 / 16, 14 / 15), ""),
    ("KvK castle record", US["castle_record"], THEM["castle_record"], edge(11 / 16, 10 / 15, tol=0.03), ""),
]
NOTES = {
    "def": unconf("Definition unclear"),
    "stale203": unconf("K203 figure 17 days old"),
}
matchup_html = "\n".join(
    f'<tr><th scope="row">{escape(lbl)}{" " + NOTES[n] if n else ""}</th>'
    f'<td class="num">{u}</td><td class="num">{t}</td><td>{e}</td></tr>'
    for lbl, u, t, e, n in matchup_rows
)

# ---------- paired bar charts ----------
def pair_bars(rows, unit, vmax, ticks):
    """rows: [(label, us_value, us_name, them_value, them_name)] drawn on one shared 0..vmax scale."""
    out = []
    for lbl, uv, un, tv, tn in rows:
        out.append(f'''<div class="pb-row">
  <div class="pb-lbl">{lbl}</div>
  <div class="pb-bars">
    <div class="pb-line"><span class="pb-name us">{un}</span><span class="pb-track"><span class="pb-bar us" style="width:{100 * uv / vmax:.1f}%"></span></span><span class="pb-val">{uv:g}{unit}</span></div>
    <div class="pb-line"><span class="pb-name them">{tn}</span><span class="pb-track"><span class="pb-bar them" style="width:{100 * tv / vmax:.1f}%"></span></span><span class="pb-val">{tv:g}{unit}</span></div>
  </div>
</div>''')
    axis = "".join(f'<span style="left:{100 * t / vmax:.1f}%">{t:g}{unit}</span>' for t in ticks)
    return f'<div class="pb">{"".join(out)}<div class="pb-axis"><div class="pb-axis-in">{axis}</div></div></div>'


players_chart = pair_bars(
    [(f"#{i + 1}", u, "K203", t, "K365") for i, (u, t) in
     enumerate(zip(US["top5_player_power_m"], THEM["top5_player_power_m"]))],
    "M", 400, [0, 100, 200, 300, 400])
alliance_chart = pair_bars(
    [(f"#{i + 1}", u["real_power_b"], u["tag"], t["real_power_b"], t["tag"]) for i, (u, t) in
     enumerate(zip(US["top_alliances"], THEM["top_alliances"]))],
    "B", 16, [0, 4, 8, 12, 16])

# ---------- prep scorecard ----------
mtu, mtt = ku["boards"]["mystic_trial"], kt["boards"]["mystic_trial"]


def srow(lbl, u, t, fmt, tol=0, cls="", note=""):
    return (f'<tr class="{cls}"><th scope="row">{lbl}{" " + note if note else ""}</th><td class="num">{fmt(u)}</td>'
            f'<td class="num">{fmt(t)}</td><td>{edge(u, t, True, tol)}</td></tr>')


n0 = lambda v: f"{v:,}"
scorecard_html = "\n".join([
    srow("Mystic Trial, top 100 combined", mtu["total"], mtt["total"], n0, cls="key"),
    srow("Power gained, last 7 days", ku["power_gain_7d"], kt["power_gain_7d"], b, note=unconf("Freshness unconfirmed")),
    srow("Town Centre upgrades, last 7 days", ku["tc_pushers_7d"], kt["tc_pushers_7d"], n0, note=unconf("Freshness unconfirmed")),
    srow("Governors active, last 30 days", ku["active_30d"], kt["active_30d"], n0, note=unconf("Freshness unconfirmed")),
    srow("Governors on the map", ku["located"], kt["located"], n0),
    srow("Research power, top 100", ku["research_power"], kt["research_power"], b),
    srow("Hero power, top 100", ku["hero_total"], kt["hero_total"], b, tol=0.15e9),
    srow("Pet power, top 100", ku["pet_power"], kt["pet_power"], b, tol=0.05e9),
    f'<tr><th scope="row">KvK prep record</th><td class="num">{US["prep_record"]}</td><td class="num">{THEM["prep_record"]}</td><td>{edge(16 / 16, 14 / 15)}</td></tr>',
    srow("Troop power, top 100", ku["troop_power"], kt["troop_power"], b, tol=1e9, cls="minor",
         note='<span class="tag-low">Less weight in KvK</span>'),
])

mystic_chart = pair_bars(
    [(lbl, round(mtu[k]), "K203", round(mtt[k]), "K365") for lbl, k in
     (("1–10", "avg_1_10"), ("11–50", "avg_11_50"), ("51–100", "avg_51_100"))],
    "", 4000, [0, 1000, 2000, 3000, 4000])
mystic_ranks = "".join(
    f'<tr><th scope="row">#{r}</th><td class="num">{mtu["at_rank"][r]:,}</td><td class="num">{mtt["at_rank"][r]:,}</td>'
    f'<td>{edge(mtu["at_rank"][r], mtt["at_rank"][r], True, 15)}</td></tr>'
    for r in ("1", "5", "10", "25", "50", "75", "100"))
mt_lead = lambda k: 100 * (mtu[k] / mtt[k] - 1)
mt_cap = datetime.fromisoformat(mtu["captured_at"])
MT_CAP = f"{mt_cap.day} {mt_cap:%b}"


# ---------- KvK records ----------
def record_strip(k):
    cells = []
    for r in k["kvk_history"]:
        cells.append(
            f'<li><span class="opp">K{r["opponent"]}</span>'
            f'<span class="res {r["prep"]}" title="Prep {"win" if r["prep"] == "W" else "loss"}">{r["prep"]}</span>'
            f'<span class="res {r["castle"]}" title="Castle {"win" if r["castle"] == "W" else "loss"}">{r["castle"]}</span></li>')
    return f'<ol class="rec">{"".join(cells)}</ol>'


def streak(k, phase):
    hist = k["kvk_history"]
    last = hist[-1][phase]
    n = 0
    for r in reversed(hist):
        if r[phase] != last:
            break
        n += 1
    return f"{last}{n}"


def opp_range(k):
    o = [r["opponent"] for r in k["kvk_history"]]
    return f"K{min(o)}–K{max(o)}"


# ---------- activity table ----------
def act_rows(mk):
    rows = []
    for a in mk["top_alliances"]:
        s, n = a["vs_snapshot"], a["members"]
        rows.append((a["tag"], n, b(a["total_power"]), a["median_tc_level"],
                     pct(s["active_24h"], n), pct(s["active_72h"], n), pct(s["active_7d"], n),
                     s["power_share_active_7d_pct"]))
    return rows


def act_table(mk, side):
    body = []
    for tag, n, pw, tc, a24, a72, a7, p7 in act_rows(mk):
        body.append(f'''<tr><th scope="row" class="tagc {side}">{tag}</th><td class="num">{n}</td><td class="num">{pw}</td><td class="num">TC{tc}</td>
<td class="barcell"><span class="mini"><span class="mini-bar {side}" style="width:{a24}%"></span></span><span class="num">{a24}%</span></td>
<td class="num">{a72}%</td><td class="num">{a7}%</td><td class="num">{p7:.0f}%</td></tr>''')
    t = mk["top6_totals"]
    s = t["vs_snapshot"]
    n = t["members"]
    body.append(f'''<tr class="tot"><th scope="row">Top 6</th><td class="num">{n}</td><td class="num">{b(t["total_power"])}</td><td></td>
<td class="barcell"><span class="mini"><span class="mini-bar {side}" style="width:{pct(s["active_24h"], n)}%"></span></span><span class="num">{pct(s["active_24h"], n)}%</span></td>
<td class="num">{pct(s["active_72h"], n)}%</td><td class="num">{pct(s["active_7d"], n)}%</td><td class="num">{s["power_share_active_7d_pct"]:.0f}%</td></tr>''')
    return f'''<div class="tbl-wrap"><table class="act">
<thead><tr><th scope="col">Alliance</th><th scope="col" class="num">Members</th><th scope="col" class="num">Power</th><th scope="col" class="num">Median TC</th><th scope="col">Active 24h</th><th scope="col" class="num">72h</th><th scope="col" class="num">7d</th><th scope="col" class="num">Power held by 7d actives</th></tr></thead>
<tbody>{"".join(body)}</tbody></table></div>'''


def kstat(lbl, u, t, fmt=lambda v: f"{v:,}", higher=True, tol=0):
    return (f'<tr><th scope="row">{lbl}</th><td class="num">{fmt(u)}</td><td class="num">{fmt(t)}</td>'
            f'<td>{edge(u, t, higher, tol)}</td></tr>')


kingdom_stats = "\n".join([
    kstat("Power gained, last 7 days", ku["power_gain_7d"], kt["power_gain_7d"], b),
    kstat("Town Centre upgrades, last 7 days", ku["tc_pushers_7d"], kt["tc_pushers_7d"]),
    kstat("Governors active, last 7 days", ku["active_7d"], kt["active_7d"]),
    kstat("Governors active, last 30 days", ku["active_30d"], kt["active_30d"]),
    kstat("Governors on the map", ku["located"], kt["located"]),
    kstat("Troop power", ku["troop_power"], kt["troop_power"], b, tol=1e9),
    f'<tr><th scope="row">Health grade</th><td class="num">{ku["health"]}</td><td class="num">{kt["health"]}</td><td>{edge(1, 2)}</td></tr>',
])

ua, ta = act_rows(MU), act_rows(MT)
top4_24_us = sum(r[4] for r in ua[:4]) / 4
top4_24_th = sum(r[4] for r in ta[:4]) / 4


def proj_card(key, title, why):
    p = PROJ[key]
    lo0, hi0 = p["before"]
    lo, hi = p["after"]
    return f'''<article class="proj">
  <header><h3>{title}</h3><p class="proj-range"><span class="num">{lo}–{hi}%</span> <span class="proj-sub">chance K203 wins</span></p></header>
  <div class="gauge" role="img" aria-label="Previous estimate {lo0} to {hi0} percent, revised {lo} to {hi} percent">
    <span class="g-mid"></span>
    <span class="g-old" style="left:{lo0}%;width:{hi0 - lo0}%"></span>
    <span class="g-new" style="left:{lo}%;width:{hi - lo}%"></span>
  </div>
  <div class="gauge-axis"><span>K365 favoured</span><span>Even</span><span>K203 favoured</span></div>
  <p class="proj-was">Previous estimate: {lo0}–{hi0}%.</p>
  {why}
</article>'''


prep_why = f'''<h4>Against us</h4>
<ul>
<li>K365 gained <strong>{b(kt["power_gain_7d"])}</strong> of power in the last 7 days against our <strong>{b(ku["power_gain_7d"])}</strong> (+{100 * (kt["power_gain_7d"] / ku["power_gain_7d"] - 1):.0f}%). Prep points come from exactly this kind of growth: building, training and research.</li>
<li>K365 had <strong>{kt["tc_pushers_7d"]}</strong> Town Centre upgrades in 7 days to our <strong>{ku["tc_pushers_7d"]}</strong>, and more governors active over 30 days ({kt["active_30d"]:,} vs {ku["active_30d"]:,}).</li>
<li>Prep is a whole-kingdom effort. K365 has {kt["located"]:,} governors on the map to our {ku["located"]:,}.</li>
</ul>
<h4>For us</h4>
<ul>
<li>We lead Mystic Trial at every depth of the top 100: +{mt_lead("avg_1_10"):.1f}% in ranks 1–10, +{mt_lead("avg_11_50"):.1f}% in 11–50 and +{mt_lead("avg_51_100"):.1f}% in 51–100. Our hero strength is deeper, not just stronger at the top.</li>
<li>Our top 100 carry {100 * (ku["research_power"] / kt["research_power"] - 1):.0f}% more research power, a sign of more sustained investment.</li>
<li>We have never lost a prep phase (16-0). K365's only loss (14-1) was its first KvK.</li>
<li>Our top 6 alliances were at least as active as theirs in the {SNAP} snapshot (97% vs 95% active within 7 days).</li>
</ul>
<p class="note">Net: K365's growth and wider player base outweigh our hero depth, but only just. The growth figures could not be confirmed as current {unconf()}; if they are stale, prep is closer to even.</p>'''

castle_why = f'''<ul>
<li>For us: our top 5 players carry {100 * (us_top5 / th_top5 - 1):.0f}% more real power, and ORM, PRO and BR4 all sit at Town Centre 70.</li>
<li>Against us: K365 leads real power at each of the top 5 alliance ranks ({th_ally5:.1f}B vs {us_ally5:.1f}B), and SCC out-sizes SRT by {(MT["top_alliances"][3]["total_power"] - MU["top_alliances"][3]["total_power"]) / 1e9:.1f}B.</li>
<li>Prep and castle results line up only about 31% of the time, so a prep loss would not decide castle day.</li>
</ul>'''

recs = [
    ("Bank speedups and resources for prep",
     f"K365 added {b(kt['power_gain_7d'])} of power in the last 7 days to our {b(ku['power_gain_7d'])}. "
     "We can't match that growth before prep, so make it count during prep: hold speedups, resources and upgrades until the matching prep day opens."),
    ("Get the whole kingdom scoring",
     f"K365 has {kt['located'] - ku['located']:,} more governors on the map and {kt['active_30d'] - ku['active_30d']:,} more active over 30 days. "
     "Prep points come from every account. Reach beyond the top 6 alliances: share the daily targets with every alliance in K203, not only the leading ones."),
    ("Use our hero depth",
     f"Our Mystic Trial lead is largest in ranks 51–100 (+{mt_lead('avg_51_100'):.1f}%). These mid-tier players are where we beat K365 head to head. "
     "Make sure each of them knows the daily targets and hits them, especially on hero-development days."),
    ("Time Town Centre and building completions for prep",
     f"K365 logged {kt['tc_pushers_7d']} Town Centre upgrades in 7 days to our {ku['tc_pushers_7d']}. "
     "Upgrades that finish before prep score nothing in it. Queue long builds so they complete inside the prep window."),
    ("Check standings every day",
     "Post the day's score gap in alliance chat each reset and shift effort to the next day's theme. A close day is decided in its final hours."),
    ("Keep castle day separate",
     "If prep goes to K365, castle day is still open. Prep and castle results line up only about 31% of the time."),
    ("Confirm the schedule in-game",
     "Castle day (Sat 10 Oct) and the prep days before it are estimated from the four-week cycle. Check the in-game KvK schedule."),
]
recs_html = "\n".join(f'<li><h3>{escape(t)}</h3><p>{escape(d)}</p></li>' for t, d in recs)

caveats = [
    f"Activity counts come from a MightPulse snapshot taken {SNAP} at {snap:%H:%M} UTC, three days after the last castle day. "
    "That is the newest activity data available for these alliances. Post-KvK activity tends to run high, so treat these as relative, not current.",
    f"MightPulse kingdom-wide figures (growth, Town Centre upgrades, active governors) were pulled {PULLED}. Their freshness could not be confirmed.",
    "StratForge's kingdom \"real power\" (2.8B / 2.7B) and \"top-10 total\" (8.3B / 8.4B) are smaller than single top alliances' real power, "
    "so the two metrics measure something narrower. They are compared like-for-like only.",
    "K203's city and alliance counts come from a snapshot 17 days old.",
    "The castle date is an estimate from the four-week cycle (23 May, 20 Jun, 18 Jul, 15 Aug, 12 Sep).",
    f"Mystic Trial, research, hero, pet and troop figures are sums over each kingdom's top 100 leaderboard, captured {MT_CAP}.",
    "Projections are judgement estimates, not model output.",
]
caveats_html = "\n".join(f"<li>{escape(c)}</li>" for c in caveats)

TITLE = "K203 vs K365 Scouting"

BODY = f'''<title>{TITLE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Sans+3:wght@400;600;700&family=IBM+Plex+Mono:wght@500&display=swap">
<style>
/* Layout: one reading column; matchup and projections lead, detail tables scroll inside their own frames. */
:root {{
  --bg: #F3F5F8; --surface: #FFFFFF; --line: #D9DEE6; --fg: #17202C; --muted: #5A6577;
  --us: #2453C9; --us-soft: #DCE5FA; --them: #B5481A; --them-soft: #F6E2D7;
  --win: #1E7A4C; --loss: #B42335; --unc-bg: #FFF2C9; --unc-fg: #6B4E00;
  --f-display: "Barlow Condensed", "Arial Narrow", "Roboto Condensed", sans-serif;
  --f-body: "Source Sans 3", "Segoe UI", system-ui, -apple-system, sans-serif;
  --f-data: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #10151C; --surface: #18202A; --line: #2B3644; --fg: #E6EBF2; --muted: #9AA6B8;
  --us: #7EA2FF; --us-soft: #22325A; --them: #F2995F; --them-soft: #4A2A1A;
  --win: #5CCB8F; --loss: #F2788A; --unc-bg: #3E3410; --unc-fg: #F3D57A; color-scheme: dark;
}} }}
:root[data-theme="dark"] {{
  --bg: #10151C; --surface: #18202A; --line: #2B3644; --fg: #E6EBF2; --muted: #9AA6B8;
  --us: #7EA2FF; --us-soft: #22325A; --them: #F2995F; --them-soft: #4A2A1A;
  --win: #5CCB8F; --loss: #F2788A; --unc-bg: #3E3410; --unc-fg: #F3D57A; color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--fg); font: 400 1rem/1.55 var(--f-body); margin: 0; }}
.wrap {{ max-width: 60rem; margin: 0 auto; padding-inline: 16px; padding-block: 2rem 4rem; display: grid; gap: 3rem; }}
h1, h2, h3 {{ font-family: var(--f-display); text-wrap: balance; margin: 0; line-height: 1.1; }}
h1 {{ font-size: clamp(2.4rem, 7vw, 3.6rem); font-weight: 700; letter-spacing: .01em; }}
h2 {{ font-size: 1.9rem; font-weight: 700; }}
h3 {{ font-size: 1.3rem; font-weight: 600; }}
h4 {{ font: 700 .78rem/1.3 var(--f-body); text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 1rem 0 .35rem; }}
p {{ margin: 0; max-width: 65ch; }}
ul {{ margin: 0; padding-left: 1.15rem; display: grid; gap: .4rem; max-width: 65ch; }}
.num {{ font-variant-numeric: tabular-nums; }}
.eyebrow {{ font: 600 .8rem/1 var(--f-body); text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }}
section {{ display: grid; gap: 1.1rem; min-width: 0; }}
.lede {{ color: var(--muted); }}
.us-t {{ color: var(--us); }} .them-t {{ color: var(--them); }}

/* hero */
.hero {{ display: grid; gap: 1rem; }}
.vs {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: .2em .5em; }}
.vs .k {{ font-family: var(--f-display); font-weight: 700; }}
.meta {{ display: flex; flex-wrap: wrap; gap: .5rem 1.5rem; color: var(--muted); font-size: .92rem; }}
.meta strong {{ color: var(--fg); font-weight: 600; }}
.verdict {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: 1rem; }}
.verdict div {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1rem 1.1rem; display: grid; gap: .2rem; min-width: 0; }}
.verdict .big {{ font: 700 2.2rem/1 var(--f-display); }}
.verdict .lbl {{ font-size: .9rem; color: var(--muted); }}

/* tables */
.tbl-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; font-size: .95rem; }}
th, td {{ padding: .6rem .75rem; text-align: left; border-bottom: 1px solid var(--line); vertical-align: middle; }}
tbody tr:last-child > * {{ border-bottom: 0; }}
thead th {{ font: 600 .75rem/1.2 var(--f-body); text-transform: uppercase; letter-spacing: .07em; color: var(--muted); white-space: nowrap; }}
tbody th {{ font-weight: 600; }}
td.num, th.num {{ text-align: right; white-space: nowrap; }}
.matchup tbody th {{ font-weight: 400; min-width: 12rem; }}
.colh.us {{ color: var(--us); }} .colh.them {{ color: var(--them); }}
.edge {{ display: inline-block; font: 600 .75rem/1 var(--f-body); padding: .3rem .5rem; border-radius: 999px; white-space: nowrap; }}
.edge.us {{ background: var(--us-soft); color: var(--us); }}
.edge.them {{ background: var(--them-soft); color: var(--them); }}
.edge.even, .edge.neutral {{ background: transparent; color: var(--muted); border: 1px solid var(--line); }}
.tag-unc {{ display: inline-block; font: 600 .68rem/1 var(--f-body); text-transform: uppercase; letter-spacing: .06em; padding: .25rem .4rem; border-radius: 4px; background: var(--unc-bg); color: var(--unc-fg); vertical-align: .1em; white-space: nowrap; }}

/* paired bars */
.charts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr)); gap: 1.25rem; }}
.chart {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1rem; display: grid; gap: .75rem; min-width: 0; }}
.chart h3 {{ font-size: 1.15rem; }}
.pb {{ display: grid; gap: .6rem; }}
.pb-row {{ display: grid; grid-template-columns: 2.9rem 1fr; gap: .5rem; align-items: center; }}
.pb-lbl {{ font: 500 .78rem var(--f-data); color: var(--muted); }}
.pb-bars {{ display: grid; gap: 3px; min-width: 0; }}
.pb-line, .pb-axis {{ display: grid; grid-template-columns: 2.6rem 1fr 3.4rem; gap: .5rem; align-items: center; }}
.pb-axis {{ margin-left: 3.4rem; }}
.pb-name {{ font: 500 .74rem var(--f-data); }}
.pb-name.us {{ color: var(--us); }} .pb-name.them {{ color: var(--them); }}
.pb-track {{ height: .7rem; background: linear-gradient(to right, var(--line) 1px, transparent 1px) 0 0 / 25% 100%; position: relative; }}
.pb-bar {{ display: block; height: 100%; border-radius: 0 3px 3px 0; }}
.pb-bar.us {{ background: var(--us); }} .pb-bar.them {{ background: var(--them); }}
.pb-val {{ font: 500 .74rem var(--f-data); text-align: right; font-variant-numeric: tabular-nums; }}
.pb-axis-in {{ grid-column: 2; position: relative; height: 1rem; font: 500 .65rem var(--f-data); color: var(--muted); }}
.pb-axis-in span {{ position: absolute; transform: translateX(-50%); }}
.pb-axis-in span:first-child {{ transform: none; }}
.pb-axis-in span:last-child {{ transform: translateX(-100%); }}

/* records */
.records {{ display: grid; gap: 1.25rem; }}
.rec-card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1rem; display: grid; gap: .75rem; min-width: 0; }}
.rec-head {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: .5rem 1rem; align-items: baseline; }}
.rec-head h3 {{ font-size: 1.4rem; }}
.rec-stats {{ display: flex; flex-wrap: wrap; gap: .4rem 1.1rem; font-size: .9rem; color: var(--muted); }}
.rec-stats strong {{ color: var(--fg); font-variant-numeric: tabular-nums; }}
ol.rec {{ list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(4.3rem, 1fr)); gap: .4rem; }}
ol.rec li {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2px; border: 1px solid var(--line); border-radius: 6px; padding: .3rem; }}
.opp {{ grid-column: 1 / -1; font: 500 .72rem var(--f-data); text-align: center; color: var(--muted); }}
.res {{ font: 700 .8rem/1.5 var(--f-data); text-align: center; border-radius: 3px; }}
.res.W {{ color: var(--win); background: color-mix(in srgb, var(--win) 14%, transparent); }}
.res.L {{ color: var(--surface); background: var(--loss); }}
.legend {{ display: flex; flex-wrap: wrap; gap: .4rem 1rem; font-size: .85rem; color: var(--muted); align-items: center; }}
.legend .res {{ display: inline-block; width: 1.6rem; }}

/* activity */
.act .tagc {{ font: 700 1rem var(--f-display); letter-spacing: .03em; }}
.act .tagc.us {{ color: var(--us); }} .act .tagc.them {{ color: var(--them); }}
.act tr.tot > * {{ border-top: 2px solid var(--line); font-weight: 700; }}
.barcell {{ display: flex; align-items: center; gap: .5rem; min-width: 8rem; }}
.mini {{ flex: 1; height: .55rem; background: var(--line); border-radius: 3px; overflow: hidden; min-width: 3.5rem; }}
.mini-bar {{ display: block; height: 100%; }}
.mini-bar.us {{ background: var(--us); }} .mini-bar.them {{ background: var(--them); }}
.act-h {{ display: flex; flex-wrap: wrap; gap: .5rem; align-items: baseline; }}
.act-h h3 {{ font-size: 1.35rem; }}

/* projections */
.projs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); gap: 1.25rem; }}
.proj {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1.1rem; display: grid; gap: .5rem; align-content: start; min-width: 0; }}
.proj header {{ display: grid; gap: .2rem; }}
.proj-range {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem; }}
.proj-range .num {{ font: 700 2.4rem/1 var(--f-display); color: var(--us); }}
.proj-sub {{ color: var(--muted); font-size: .9rem; }}
.gauge {{ position: relative; height: 1.1rem; border-radius: 4px; background: linear-gradient(to right, var(--them-soft), var(--surface) 50%, var(--us-soft)); border: 1px solid var(--line); margin-top: .4rem; }}
.g-mid {{ position: absolute; left: 50%; top: -3px; bottom: -3px; width: 2px; background: var(--muted); }}
.g-old {{ position: absolute; top: 2px; bottom: 2px; border: 2px dashed var(--muted); border-radius: 3px; }}
.g-new {{ position: absolute; top: 3px; bottom: 3px; background: var(--us); border-radius: 2px; opacity: .85; }}
.gauge-axis {{ display: flex; justify-content: space-between; font-size: .72rem; color: var(--muted); }}
.proj-was {{ font-size: .88rem; color: var(--muted); }}
.note {{ font-size: .92rem; color: var(--muted); margin-top: .5rem; }}

/* recommendations */
ol.recs {{ list-style: none; counter-reset: r; margin: 0; padding: 0; display: grid; gap: .9rem; }}
ol.recs li {{ counter-increment: r; display: grid; grid-template-columns: 2.2rem 1fr; gap: .1rem .75rem; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: .9rem 1rem; }}
ol.recs li::before {{ content: counter(r); grid-row: span 2; font: 700 1.6rem/1 var(--f-display); color: var(--us); }}
ol.recs h3 {{ font-size: 1.2rem; }}
ol.recs p {{ color: var(--fg); }}

.score tr.key > * {{ background: var(--us-soft); font-weight: 700; }}
.score tr.key th {{ font-weight: 700; }}
.score tr.minor > * {{ color: var(--muted); }}
.tag-low {{ display: inline-block; font: 600 .68rem/1 var(--f-body); text-transform: uppercase; letter-spacing: .06em; padding: .25rem .4rem; border-radius: 4px; border: 1px solid var(--line); color: var(--muted); vertical-align: .1em; white-space: nowrap; }}
.tbl-wrap.flat {{ border: 0; }}
.verdict .v-main {{ border-color: var(--us); }}
.projs {{ grid-template-columns: 1fr; }}
.caveats {{ font-size: .92rem; color: var(--muted); }}
.caveats ul {{ max-width: 75ch; }}
footer {{ font-size: .82rem; color: var(--muted); border-top: 1px solid var(--line); padding-top: 1rem; }}
@media (max-width: 30rem) {{
  .matchup tbody th {{ min-width: 9rem; }}
  th, td {{ padding: .5rem .55rem; }}
}}
</style>

<main class="wrap">
  <header class="hero">
    <span class="eyebrow">KvK #19 · Prep phase scouting</span>
    <h1 class="vs"><span class="k us-t">K203</span><span>vs</span><span class="k them-t">K365</span></h1>
    <p class="lede">Prep is close. K365 is growing faster and has more active players; we have the deeper hero base, leading Mystic Trial at every level of the top 100. Prep comes down to turnout and timing.</p>
    <div class="meta">
      <span>Castle day <strong>Sat 10 Oct 2026</strong> {unconf("Estimated")}</span>
      <span>Data as of <strong>{PULLED}</strong></span>
    </div>
    <div class="verdict">
      <div class="v-main"><span class="lbl">Prep phase</span><span class="big num">{PROJ["prep"]["after"][0]}–{PROJ["prep"]["after"][1]}%</span><span class="lbl">chance K203 wins. Near even, slight lean K365.</span></div>
      <div><span class="lbl">Mystic Trial, top 100</span><span class="big num">+{100 * (mtu["total"] / mtt["total"] - 1):.1f}%</span><span class="lbl">K203 ahead, {mtu["total"]:,} to {mtt["total"]:,}.</span></div>
      <div><span class="lbl">Castle day</span><span class="big num">{PROJ["castle"]["after"][0]}–{PROJ["castle"]["after"][1]}%</span><span class="lbl">chance K203 wins. Even.</span></div>
    </div>
  </header>

  <section id="scorecard">
    <h2>Prep scorecard</h2>
    <p class="lede">The measures that matter most for prep, strongest signal first. Troop power is listed last because it carries less weight in KvK.</p>
    <div class="tbl-wrap"><table class="matchup score">
      <thead><tr><th scope="col">Measure</th><th scope="col" class="num colh us">K203</th><th scope="col" class="num colh them">K365</th><th scope="col">Edge</th></tr></thead>
      <tbody>{scorecard_html}</tbody>
    </table></div>
  </section>

  <section id="mystic">
    <h2>Mystic Trial</h2>
    <p class="lede">Mystic Trial scores reflect hero strength rather than troop count. We lead at every depth of the top 100, and the lead grows further down the rankings.</p>
    <div class="charts">
      <div class="chart"><h3>Average score by rank band</h3>{mystic_chart}</div>
      <div class="chart"><h3>Score at rank</h3><div class="tbl-wrap flat"><table class="matchup">
        <thead><tr><th scope="col">Rank</th><th scope="col" class="num colh us">K203</th><th scope="col" class="num colh them">K365</th><th scope="col">Edge</th></tr></thead>
        <tbody>{mystic_ranks}</tbody></table></div></div>
    </div>
    <p class="note">K365's #10 scores slightly higher than ours (2,994 vs 2,955), but our top 10 average is higher. Leaderboard captured {MT_CAP}.</p>
  </section>

  <section id="matchup">
    <h2>Kingdom profile</h2>
    <p class="lede">Real power counts heroes, gear, gems and pets, without troops.</p>
    <div class="tbl-wrap"><table class="matchup">
      <thead><tr><th scope="col">Measure</th><th scope="col" class="num colh us">K203</th><th scope="col" class="num colh them">K365</th><th scope="col">Edge</th></tr></thead>
      <tbody>{matchup_html}</tbody>
    </table></div>
    <div class="charts">
      <div class="chart"><h3>Top 5 players, real power</h3>{players_chart}</div>
      <div class="chart"><h3>Top 5 alliances, real power</h3>{alliance_chart}</div>
    </div>
  </section>

  <section id="records">
    <h2>KvK records</h2>
    <p class="lede">Every KvK, oldest to newest. Each box shows the opponent, then the prep and castle results.</p>
    <div class="legend"><span class="res W">W</span> win <span class="res L">L</span> loss</div>
    <div class="records">
      <div class="rec-card">
        <div class="rec-head"><h3 class="us-t">K203</h3>
          <div class="rec-stats"><span>Prep <strong>{US["prep_record"]}</strong></span><span>Castle <strong>{US["castle_record"]}</strong></span><span>Current castle streak <strong>{streak(US, "castle")}</strong></span><span>Opponents {opp_range(US)}</span></div></div>
        {record_strip(US)}
      </div>
      <div class="rec-card">
        <div class="rec-head"><h3 class="them-t">K365</h3>
          <div class="rec-stats"><span>Prep <strong>{THEM["prep_record"]}</strong></span><span>Castle <strong>{THEM["castle_record"]}</strong></span><span>Current castle streak <strong>{streak(THEM, "castle")}</strong></span><span>Opponents {opp_range(THEM)}</span></div></div>
        {record_strip(THEM)}
      </div>
    </div>
    <p class="note">Both kingdoms lose castle day about one time in three, at a similar rate. Neither has lost a prep phase since its first KvK.</p>
  </section>

  <section id="activity">
    <h2>Activity</h2>
    <p class="lede">Top 6 alliances by power in each kingdom, with members active within 24 hours, 72 hours and 7 days. {unconf(f"Snapshot of {SNAP}")}</p>
    <div class="act-h"><h3 class="us-t">K203</h3></div>
    {act_table(MU, "us")}
    <div class="act-h"><h3 class="them-t">K365</h3></div>
    {act_table(MT, "them")}
    <ul>
      <li>Both top-6 groups were almost fully active: {pct(MU["top6_totals"]["vs_snapshot"]["active_7d"], MU["top6_totals"]["members"])}% of our members within 7 days, {pct(MT["top6_totals"]["vs_snapshot"]["active_7d"], MT["top6_totals"]["members"])}% of theirs. Inactive members hold almost no power on either side.</li>
      <li>K365's top 4 log in more often day to day: {top4_24_th:.0f}% active within 24 hours against {top4_24_us:.0f}% for ours. ORM is our most active alliance; PRO, BR4 and SRT trail their counterparts.</li>
      <li>Further down, our HnG and BR1 were more active than K365's WYW and SDH.</li>
    </ul>
  </section>

  <section id="projections">
    <h2>Projections</h2>
    <p class="lede">The dashed outline shows the previous estimate; the solid bar shows the revised range.</p>
    <div class="projs">
      {proj_card("prep", "Prep phase", prep_why)}
      {proj_card("castle", "Castle day, for reference", castle_why)}
    </div>
  </section>

  <section id="plan">
    <h2>Prep plan for K203</h2>
    <ol class="recs">{recs_html}</ol>
  </section>

  <section class="caveats" id="caveats">
    <h2>About the data</h2>
    <ul>{caveats_html}</ul>
  </section>

  <footer>Sources: StratForge and Kingshot.net (early Oct 2026); MightPulse ({PULLED}). Aggregate figures only. Next transfer window opens 8 Nov 2026, and Gen 8 reaches K365's bracket on 9 Nov, both after this KvK.</footer>
</main>
'''

out = ROOT / "report"
out.mkdir(exist_ok=True)
(out / "kvk19_report.body.html").write_text(BODY)
(out / "kvk19_report.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    + BODY.replace("</style>", "</style>\n</head>\n<body>", 1) + "</body>\n</html>\n")
print("wrote", out / "kvk19_report.html")
