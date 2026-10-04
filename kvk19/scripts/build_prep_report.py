#!/usr/bin/env python3
"""Build the KvK 19 prep report: report/kvk19_prep.html (+ .body.html for hosting)."""
from datetime import date
from report_common import (US, THEM, ku, kt, mtu, mtt, stock, opt, PROJ, PULLED, SNAP, MU, MT, b, m, unconf, edge,
                           row, cmp_table, gauge, record_strip, numbered, bullets, write_page)

su, st = stock["kingdoms"]["203"], stock["kingdoms"]["365"]
lo, hi = PROJ["prep"]
ratio_lo, ratio_hi = stock["reserve_ratio_365_vs_203"]
ratio_mid = stock["reserve_ratio_mid"]
per_u = su["banked_hours_mid"] / (sum(su["active_30d"]) / 2)
per_t = st["banked_hours_mid"] / (sum(st["active_30d"]) / 2)
step = st["step_changes"][0] if st["step_changes"] else None

# ---------- reserve range chart (prep points) ----------
VMAX = 350e6


def range_bar(name, side, k):
    a, z = k["prep_points"]
    mid = k["prep_points_mid"]
    return (f'<div class="rg-row"><span class="pb-name {side}">{name}</span>'
            f'<span class="rg-track"><span class="rg-band {side}" style="left:{100 * a / VMAX:.1f}%;width:{100 * (z - a) / VMAX:.1f}%"></span>'
            f'<span class="rg-mid {side}" style="left:{100 * mid / VMAX:.1f}%"></span></span>'
            f'<span class="pb-val">{m(mid)}</span></div>')


rg_axis = "".join(f'<span style="left:{100 * t / VMAX:.1f}%">{t / 1e6:g}M</span>' for t in (0, 100e6, 200e6, 300e6))
reserve_chart = (f'<div class="rg">{range_bar("K203", "us", su)}{range_bar("K365", "them", st)}'
                 f'<div class="rg-axis"><div class="pb-axis-in">{rg_axis}</div></div></div>')

# ---------- growth since KvK 18 (SVG line chart) ----------
W, H, L, R, T, B = 640, 240, 44, 64, 16, 30
d0 = date.fromisoformat(su["tracking_since"])
d1 = date.fromisoformat(su["daily_series"][-1]["date"])
span = (d1 - d0).days
YMAX = 8


def pts(k):
    start = k["power_now"] - k["power_growth_since_tracking"]
    out = [(0, 0.0)] + [((date.fromisoformat(r["date"]) - d0).days, (r["power"] - start) / 1e9) for r in k["daily_series"]]
    return [(L + (W - L - R) * x / span, T + (H - T - B) * (1 - y / YMAX), y) for x, y in out]


def poly(p, cls, dcls):
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in p)
    dots = "".join(f'<circle class="{dcls}" cx="{x:.1f}" cy="{y:.1f}" r="3"/>' for x, y, _ in p)
    return f'<polyline class="{cls}" points="{path}"/>{dots}'


pu, pt = pts(su), pts(st)
grid = "".join(
    f'<line class="grid" x1="{L}" x2="{W - R}" y1="{T + (H - T - B) * (1 - v / YMAX):.1f}" y2="{T + (H - T - B) * (1 - v / YMAX):.1f}"/>'
    f'<text x="{L - 6}" y="{T + (H - T - B) * (1 - v / YMAX) + 4:.1f}" text-anchor="end">{v}B</text>' for v in (0, 2, 4, 6, 8))
xt = "".join(
    f'<text x="{L + (W - L - R) * dd / span:.1f}" y="{H - 8}" text-anchor="middle">{lbl}</text>'
    for dd, lbl in ((0, "15 Sep"), ((date(2026, 9, 27) - d0).days, "27 Sep"), (span, "4 Oct")))
step_note = ""
if step:
    sx = L + (W - L - R) * (date.fromisoformat(step["date"]) - d0).days / span
    step_note = (f'<line class="grid" x1="{sx:.1f}" x2="{sx:.1f}" y1="{T}" y2="{H - B}" stroke-dasharray="3 3"/>'
                 f'<text x="{sx - 4:.1f}" y="{T + 10}" text-anchor="end">+{step["players"]} accounts</text>')
growth_svg = (f'<svg class="svgchart" viewBox="0 0 {W} {H}" role="img" aria-label="Power gained since 15 September: '
              f'K203 {su["power_growth_since_tracking"] / 1e9:.1f}B, K365 {st["power_growth_since_tracking"] / 1e9:.1f}B">'
              f'{grid}{xt}{step_note}{poly(pt, "l-them", "d-them")}{poly(pu, "l-us", "d-us")}'
              f'<text class="lbl-us" x="{pu[-1][0] + 6:.1f}" y="{pu[-1][1] + 14:.1f}">K203</text>'
              f'<text class="lbl-them" x="{pt[-1][0] + 6:.1f}" y="{pt[-1][1] - 4:.1f}">K365</text></svg>')

# ---------- prep rating rank history ----------
# ---------- who is active ----------
from report_common import load
kg = {k: load(f"external/kingshotguide_{k}.json")["series"] for k in ("203", "365")}


def span_fmt(a, z):
    return f"{a:,}" if a == z else f"{min(a, z):,}–{max(a, z):,}"


def act_kingdom_rows():
    rows = []
    gu, gt = kg["203"][-1], kg["365"][-1]
    for lbl, fu, ft, note in (
        ("Governors, all accounts", (gu["playerCount"], ku["player_count"]), (gt["playerCount"], kt["player_count"]), ""),
        ("Cities on the map", (ku["located"],) * 2, (kt["located"],) * 2, ""),
    ):
        rows.append(f'<tr><th scope="row">{lbl}{note}</th><td class="num">{span_fmt(*fu)}</td><td class="num">{span_fmt(*ft)}</td></tr>')
    pu = 100 * ku["active_30d"] / ku["player_count"]
    pt_ = 100 * kt["active_30d"] / kt["player_count"]
    rows.append(f'<tr class="key"><th scope="row">Active in the last 30 days</th><td class="num">{span_fmt(gu["active30d"], ku["active_30d"])} <span class="note">({pu:.0f}%)</span></td>'
                f'<td class="num">{span_fmt(gt["active30d"], kt["active_30d"])} <span class="note">({pt_:.0f}%)</span></td></tr>')
    rows.append(f'<tr><th scope="row">Active in the last 7 days {unconf("Narrow count")}</th><td class="num">{span_fmt(gu["active7d"], ku["active_7d"])}</td><td class="num">{span_fmt(gt["active7d"], kt["active_7d"])}</td></tr>')
    ou = ku["active_30d"] - MU["top6_totals"]["members"]
    ot = kt["active_30d"] - MT["top6_totals"]["members"]
    rows.append(f'<tr><th scope="row">Active in 30 days, outside the top 6 alliances (approx.)</th><td class="num">~{round(ou, -1):,}</td><td class="num">~{round(ot, -1):,}</td></tr>')
    return "".join(rows), ou, ot


act_rows_html, out_u, out_t = act_kingdom_rows()
dormant_u = ku["player_count"] - ku["active_30d"]


def top6_table(mk, side):
    body = ""
    for a in mk["top_alliances"]:
        s, n = a["vs_snapshot"], a["members"]
        body += (f'<tr><th scope="row" class="tagc {side}">{a["tag"]}</th><td class="num">{n}</td>'
                 f'<td><div class="barcell"><span class="mini"><span class="mini-bar {side}" style="width:{100 * s["active_24h"] / n:.0f}%"></span></span><span class="num">{s["active_24h"]}</span></div></td>'
                 f'<td class="num">{s["active_72h"]}</td><td class="num">{s["active_7d"]}</td></tr>')
    t = mk["top6_totals"]
    s, n = t["vs_snapshot"], t["members"]
    body += (f'<tr class="tot"><th scope="row">Top 6</th><td class="num">{n}</td>'
             f'<td><div class="barcell"><span class="mini"><span class="mini-bar {side}" style="width:{100 * s["active_24h"] / n:.0f}%"></span></span><span class="num">{s["active_24h"]}</span></div></td>'
             f'<td class="num">{s["active_72h"]}</td><td class="num">{s["active_7d"]} <span class="note">({s["active_7d_pct"]:.0f}%)</span></td></tr>')
    return (f'<div class="tbl-wrap"><table class="act"><thead><tr><th scope="col">Alliance</th><th scope="col" class="num">Size</th>'
            f'<th scope="col">24h</th><th scope="col" class="num">72h</th><th scope="col" class="num">7d</th></tr></thead><tbody>{body}</tbody></table></div>')


a7u = [r["active7d"] for r in kg["203"]]
a7t = [r["active7d"] for r in kg["365"]]

rh = {k: {r["kvk"]: r["rank_prep"] for r in opt[k]["rating_history"]} for k in ("203", "365")}
kvks = [k for k in range(11, 19) if k in rh["203"] and k in rh["365"]]
better = sum(rh["203"][k] < rh["365"][k] for k in kvks)
rank_rows = "".join(
    f'<tr><th scope="row">KvK {k}</th><td class="num">{rh["203"][k]}</td><td class="num">{rh["365"][k]}</td>'
    f'<td>{edge(rh["203"][k], rh["365"][k], higher_better=False)}</td></tr>' for k in kvks)

# ---------- scorecard ----------
n0 = lambda v: f"{v:,}"
scorecard = cmp_table([
    row("Estimated speedup reserve, prep points", su["prep_points_mid"], st["prep_points_mid"], m, cls="key",
        note=unconf("Estimate")),
    row("Governors active, last 30 days", ku["active_30d"], kt["active_30d"], n0),
    row("Town Centre upgrades, last 7 days", ku["tc_pushers_7d"], kt["tc_pushers_7d"], n0),
    row("Mystic Trial, top 100 combined", mtu["total"], mtt["total"], n0),
    row("Research power, top 100", ku["research_power"], kt["research_power"], b),
    row("Hero power, top 100", ku["hero_total"], kt["hero_total"], b, tol=0.15e9),
    row("Governor power, top 100", ku["gov_power"], kt["gov_power"], b, tol=1.2e9),
    f'<tr><th scope="row">KvK prep record</th><td class="num">{US["prep_record"]}</td><td class="num">{THEM["prep_record"]}</td><td>{edge(16 / 16, 14 / 15)}</td></tr>',
])

# ---------- scoring guide ----------
days = [
    ("Day 1", "City Construction", "Construction speedups (30 points per minute), Truegold used on buildings (2,000 each), Tempered Truegold (30,000), Intel missions (6,000)"),
    ("Day 2", "Basic Skills Up", "Research speedups (30 points per minute), Hero Roulette spins (8,000), Mythic hero shards (3,040), Master Emblems (6,000)"),
    ("Day 3", "Pet Training", "Advanced Taming Marks (15,000), Common Taming Marks (1,150), pet advancement (50 per point)"),
    ("Day 4", "Hero Development", "Mithril (40,000), Widgets (8,000), Forgehammers (4,000), troop training (T11 75 per troop, T10 60)"),
    ("Day 5", "Power Boost", "Speedups of every type (30 points per minute), Governor Gear (36 per point), plus items from earlier days"),
]
days_html = "".join(f'<tr><th scope="row">{d}</th><td>{t}</td><td>{x}</td></tr>' for d, t, x in days)

why = f'''<h4>Against us</h4>
<ul>
<li>K365's speedup reserve is likely about <strong>{ratio_mid:.1f}×</strong> ours (range {ratio_lo:.1f}–{ratio_hi:.1f}×): more active players, and slower growth since KvK 18, which points to banking.</li>
<li>K365 has {kt["active_30d"] - ku["active_30d"]:,} more governors active over 30 days. If every active account reaches the 200,000-point daily chest, that alone is about {(kt["active_30d"] - ku["active_30d"]) * 0.2:,.0f}M points a day in K365's favour.</li>
</ul>
<h4>For us</h4>
<ul>
<li>Across all kingdoms, our prep rating has ranked above K365's in {better} of the last {len(kvks)} KvKs ({rh["203"][kvks[-1]]} vs {rh["365"][kvks[-1]]} after KvK {kvks[-1]}).</li>
<li>Our top 100 are slightly stronger: Mystic Trial +{100 * (mtu["total"] / mtt["total"] - 1):.1f}%, research power +{100 * (ku["research_power"] / kt["research_power"] - 1):.0f}%. Bigger accounts score more per day on hero, gear and training items.</li>
<li>We have never lost a prep phase (16-0).</li>
</ul>
<p class="note">Net: near even with a slight lean to K365. The reserve estimate rests on assumptions, and our record says we turn a smaller base into more points.</p>'''

plan = numbered([
    ("Treat prep as one five-day total",
     "Prep is won on total points after Day 5, not on daily wins. Don't overspend to win a day by a wide margin. "
     "A point banked for a closer day is worth the same and buys more."),
    ("Keep general speedups for Day 5",
     "General speedups score on Day 5 along with every other type. Hold them as the kingdom's reserve "
     "to close whatever gap is left after Day 4."),
    ("Match each item to its day",
     "Construction speedups and Truegold on Day 1. Research speedups and Roulette spins on Day 2. Taming Marks on Day 3. "
     "Mithril, Widgets, Forgehammers and troop training on Day 4. Check the in-game event tab first: guides disagree on a few items."),
    ("Get every account to the daily chest",
     f"K365 has about {kt['active_30d'] - ku['active_30d']:,} more active governors. Our answer is turnout: "
     f"we have {ku['player_count']:,} governors but only {ku['active_30d']:,} active in the last month. "
     "Message every alliance, not only the top 6, and set the 200,000-point daily chest as each member's minimum."),
    ("Stop spending speedups now",
     f"Our power grew {b(su['organic_growth'])} since KvK 18 to K365's {b(st['organic_growth'])} (excluding their account intake). "
     "Every speedup used before Monday is gone from the prep total. Hold everything until the matching day opens."),
    ("Post the gap every reset",
     "Share the running total and the gap in every alliance chat at each daily reset, so members can see whether to push or hold."),
    ("Shield before prep ends",
     "Prep decides where battle day is fought. Cities can be hit in the gap between prep and battle, so shield before Day 5 closes. "
     "The battle report covers the rest."),
])

caveats = bullets([
    "The speedup reserve is an estimate, not a measurement. It multiplies active players by a guide's range for free speedup income (80–200 hours a month) over the 23 days since KvK 18 prep, then assumes a share that was saved: 50–75% for K203 and 60–85% for K365, set from each kingdom's growth per active player. Paid accounts are assumed to balance out, since top-100 governor power differs by under 2%.",
    f"K365's power rose {b(step['power'])} in one day on {int(step['date'][-2:])} Oct, as {step['players']} accounts joined. We treat that jump as an intake, not as spending. If it was organic growth, K365 saved less and its reserve is closer to ours." if step else "",
    "Prep ranks are Bradley-Terry ratings from kingshotoptimizer.com, built from wins and losses against rated opponents. They are not point totals: no public source publishes prep scores.",
    "Point values per item come from community guides (kingshotdata.com, kingshotmastery.com, kingshotguide.org) and can differ by server age or event version.",
    f"Kingdom growth and activity come from kingshotguide.org (daily since 15 Sep) and MightPulse ({PULLED}). Their 7-day active counts look too low against alliance activity, so this report uses 30-day actives.",
    "The prep days (Mon 5 to Fri 9 Oct) are estimated from the four-week cycle. Projections are judgement estimates.",
])

BODY = f'''<main class="wrap">
  <header class="hero">
    <span class="eyebrow">KvK #19 · Prep phase</span>
    <h1 class="vs"><span class="k us-t">K203</span><span>vs</span><span class="k them-t">K365</span></h1>
    <p class="lede">K365 has more active players and has been banking speedups since KvK 18. We have the stronger accounts and the better prep record. Prep will come down to turnout and discipline.</p>
    <div class="meta"><span>Prep <strong>Mon 5 – Fri 9 Oct 2026</strong> {unconf("Estimated")}</span><span>Data as of <strong>{PULLED}</strong></span></div>
    <div class="verdict">
      <div class="v-main"><span class="lbl">Prep phase</span><span class="big num">{lo}–{hi}%</span><span class="lbl">chance K203 wins. Near even, slight lean K365.</span></div>
      <div><span class="lbl">K365 speedup reserve vs ours</span><span class="big num">~{ratio_mid:.1f}×</span><span class="lbl">Estimated range {ratio_lo:.1f}–{ratio_hi:.1f}×.</span></div>
      <div><span class="lbl">Prep rating rank, all kingdoms</span><span class="big num">#{rh["203"][kvks[-1]]} vs #{rh["365"][kvks[-1]]}</span><span class="lbl">We have ranked higher in {better} of the last {len(kvks)} KvKs.</span></div>
    </div>
  </header>

  <section id="reserve">
    <h2>What each kingdom has stored</h2>
    <p class="lede">No source publishes speedup stockpiles, so this estimate builds them up from what each kingdom earned and spent since KvK 18. {unconf("Estimate")}</p>
    <div class="cards">
      <div class="card"><h3>Estimated reserve in prep points</h3>{reserve_chart}
        <p class="note">Bands show the range; the marker shows the central estimate. That works out to about {per_u:.0f} hours of speedups per active K203 player and {per_t:.0f} hours per active K365 player.</p></div>
      <div class="card"><h3>How the estimate is built</h3>
        <ol class="steps">
          <li><strong>Saving window.</strong> {stock["saving_window_days"]} days from the end of KvK 18 prep to the start of KvK 19 prep.</li>
          <li><strong>Income.</strong> {stock["income_h_per_day"][0]}–{stock["income_h_per_day"][1]} hours of free speedups per active player per day.</li>
          <li><strong>Players.</strong> {su["active_30d"][0]:,}–{su["active_30d"][-1]:,} active in K203, {st["active_30d"][0]:,}–{st["active_30d"][-1]:,} in K365.</li>
          <li><strong>Saved share.</strong> Spending shows up as power. Since 15 Sep, each active K203 player added about {su["growth_per_active_m"][-1]:.0f}M power against {st["growth_per_active_m"][0]:.0f}–{st["growth_per_active_m"][-1]:.0f}M for K365, so K365 likely kept more of its income.</li>
          <li><strong>Points.</strong> Speedups score 30 points per minute on the days they count.</li>
        </ol></div>
    </div>
    <div class="tbl-wrap"><table class="cmp">
      <thead><tr><th scope="col">Step</th><th scope="col" class="num colh us">K203</th><th scope="col" class="num colh them">K365</th></tr></thead>
      <tbody>
        <tr><th scope="row">Governors active, last 30 days</th><td class="num">{su["active_30d"][0]:,}–{su["active_30d"][-1]:,}</td><td class="num">{st["active_30d"][0]:,}–{st["active_30d"][-1]:,}</td></tr>
        <tr><th scope="row">Free speedups earned since KvK 18, hours</th><td class="num">{su["gross_hours"][0] / 1e3:.0f}k–{su["gross_hours"][1] / 1e3:.0f}k</td><td class="num">{st["gross_hours"][0] / 1e3:.0f}k–{st["gross_hours"][1] / 1e3:.0f}k</td></tr>
        <tr><th scope="row">Power gained since 15 Sep</th><td class="num">{b(su["organic_growth"])}</td><td class="num">{b(st["organic_growth"])} + {b(st["power_growth_since_tracking"] - st["organic_growth"])} intake</td></tr>
        <tr><th scope="row">Power gained per active player</th><td class="num">{su["growth_per_active_m"][-1]:.1f}M</td><td class="num">{st["growth_per_active_m"][0]:.1f}M</td></tr>
        <tr><th scope="row">Share saved {unconf("Assumption")}</th><td class="num">{su["banked_share"][0]:.0%}–{su["banked_share"][1]:.0%}</td><td class="num">{st["banked_share"][0]:.0%}–{st["banked_share"][1]:.0%}</td></tr>
        <tr><th scope="row">Speedups in reserve, hours</th><td class="num">{su["banked_hours"][0] / 1e3:.0f}k–{su["banked_hours"][1] / 1e3:.0f}k</td><td class="num">{st["banked_hours"][0] / 1e3:.0f}k–{st["banked_hours"][1] / 1e3:.0f}k</td></tr>
        <tr class="key"><th scope="row">Reserve in prep points (central)</th><td class="num">{m(su["prep_points_mid"])}</td><td class="num">{m(st["prep_points_mid"])}</td></tr>
      </tbody></table></div>
  </section>

  <section id="actives">
    <h2>Who is active</h2>
    <p class="lede">Our top alliances are as active as K365's. The gap is everywhere else: K365's extra active players sit outside its top 6 alliances.</p>
    <div class="tbl-wrap"><table class="cmp">
      <thead><tr><th scope="col">Kingdom-wide</th><th scope="col" class="num colh us">K203</th><th scope="col" class="num colh them">K365</th></tr></thead>
      <tbody>{act_rows_html}</tbody></table></div>
    <ul>
      <li>We have a large dormant tail: about {round(dormant_u, -2):,} K203 accounts have not been active in the last month. K365 has fewer accounts, but more of them are live.</li>
      <li>Outside the top 6 alliances, K365 has roughly {round(out_t, -1):,} active players to our {round(out_u, -1):,}. That is where the gap in active players comes from.</li>
      <li>Our 7-day count rose from {a7u[0]} to {a7u[-1]} over the last week as players returned ahead of KvK. K365's jumped from {a7t[2]} to {a7t[3]} on 1 Oct, the day about 100 new accounts arrived.</li>
    </ul>
    <h3>Top 6 alliances, members active ({SNAP} snapshot)</h3>
    <p class="note">Size is the alliance's member count; the other columns count members active within 24 hours, 72 hours and 7 days.</p>
    <h4 class="us-t">K203</h4>
    {top6_table(MU, "us")}
    <h4 class="them-t">K365</h4>
    {top6_table(MT, "them")}
    <ul>
      <li>Our top 6 are slightly more active overall: {MU["top6_totals"]["vs_snapshot"]["active_7d_pct"]:.0f}% within 7 days against {MT["top6_totals"]["vs_snapshot"]["active_7d_pct"]:.0f}%.</li>
      <li>K365's top four log in more often day to day: PRO, BR4 and SRT trail LTR, AOS and ORG on 24-hour activity.</li>
      <li>Further down, HnG and BR1 are more active than WYW and SDH.</li>
    </ul>
    <p class="note">The 7-day counts cannot be ordinary logins: our top 6 alone had about {MU["top6_totals"]["vs_snapshot"]["active_7d"]} members active within 7 days in the {SNAP} snapshot. Read them as a trend only. Alliance activity is the newest per-member data available, from {SNAP}.</p>
  </section>

  <section id="growth">
    <h2>Growth since KvK 18</h2>
    <p class="lede">Power added since 15 Sep. A kingdom that is saving for prep grows slowly between KvKs.</p>
    <div class="chart">{growth_svg}
      <div class="legend"><span><span class="sw us"></span>K203</span><span><span class="sw them"></span>K365</span></div></div>
    <p class="note">Our growth is steady and has continued into the last week. Most of K365's growth arrived in one jump on 1 Oct with about 100 new accounts. Apart from that jump, K365 grew {b(st["organic_growth"])} to our {b(su["organic_growth"])}. That fits a kingdom holding speedups for prep. Both kingdoms show 18 days of data; earlier history is not public.</p>
  </section>

  <section id="record">
    <h2>Prep track record</h2>
    <p class="lede">Both kingdoms win prep almost every time. Ranked against every kingdom by prep results, we have been ahead of K365 in most recent KvKs.</p>
    <div class="charts">
      <div class="chart"><h3>Prep rating rank, lower is better</h3><div class="tbl-wrap flat"><table class="cmp">
        <thead><tr><th scope="col">KvK</th><th scope="col" class="num colh us">K203</th><th scope="col" class="num colh them">K365</th><th scope="col">Better</th></tr></thead>
        <tbody>{rank_rows}</tbody></table></div></div>
      <div class="chart"><h3>Every KvK, prep then castle</h3>
        <p class="note"><span class="us-t"><strong>K203</strong></span> prep {US["prep_record"]}, castle {US["castle_record"]}</p>{record_strip(US)}
        <p class="note"><span class="them-t"><strong>K365</strong></span> prep {THEM["prep_record"]}, castle {THEM["castle_record"]}</p>{record_strip(THEM)}</div>
    </div>
  </section>

  <section id="scorecard">
    <h2>Prep scorecard</h2>
    {scorecard}
  </section>

  <section id="scoring">
    <h2>How prep scores</h2>
    <p class="lede">Five themed days. The kingdom with the most total points after Day 5 wins prep, and attacks on battle day. The battle is fought in the losing kingdom, and the winner's own castle cannot be attacked.</p>
    <div class="tbl-wrap"><table class="days"><thead><tr><th scope="col">Day</th><th scope="col">Theme</th><th scope="col">What scores most</th></tr></thead><tbody>{days_html}</tbody></table></div>
    <p class="note">Each player unlocks the daily chests at 200,000 points. Values from community guides {unconf("Check in-game")}</p>
  </section>

  <section id="projection">
    <h2>Prep projection</h2>
    <div class="card"><p class="proj-range"><span class="num">{lo}–{hi}%</span><span class="note">chance K203 wins prep</span></p>{gauge(lo, hi, "Prep")}{why}</div>
  </section>

  <section id="plan">
    <h2>Prep plan for K203</h2>
    {plan}
  </section>

  <section class="caveats" id="caveats"><h2>About the data</h2>{caveats}</section>
  <footer>Sources: MightPulse ({PULLED}); kingshotguide.org daily kingdom stats; kingshotoptimizer.com KvK ratings; StratForge and Kingshot.net (early Oct 2026); community prep guides. Aggregate figures only.</footer>
</main>'''

EXTRA = """
.rg { display: grid; gap: .7rem; }
.rg-row, .rg-axis { display: grid; grid-template-columns: 2.6rem 1fr 3.6rem; gap: .5rem; align-items: center; }
.rg-track { position: relative; height: 1.1rem; background: linear-gradient(to right, var(--line) 1px, transparent 1px) 0 0 / 28.57% 100%; border-radius: 3px; display: block; }
.rg-band { position: absolute; top: 2px; bottom: 2px; border-radius: 3px; opacity: .35; }
.rg-band.us { background: var(--us); } .rg-band.them { background: var(--them); }
.rg-mid { position: absolute; top: -2px; bottom: -2px; width: 3px; margin-left: -1.5px; border-radius: 1px; }
.rg-mid.us { background: var(--us); } .rg-mid.them { background: var(--them); }
ol.steps { margin: 0; padding-left: 1.2rem; display: grid; gap: .45rem; font-size: .95rem; }
.act .tagc { font: 700 1rem var(--f-display); letter-spacing: .03em; }
.act .tagc.us { color: var(--us); } .act .tagc.them { color: var(--them); }
.act tr.tot > * { border-top: 2px solid var(--line); font-weight: 700; }
.barcell { display: flex; align-items: center; gap: .5rem; min-width: 7rem; }
.mini { flex: 1; height: .55rem; background: var(--line); border-radius: 3px; overflow: hidden; min-width: 3rem; }
.mini-bar { display: block; height: 100%; }
.mini-bar.us { background: var(--us); } .mini-bar.them { background: var(--them); }
@media (max-width: 30rem) {
  .cmp td .note { display: block; }
  .barcell { min-width: 4.5rem; gap: .35rem; }
  .mini { min-width: 1.6rem; }
  .act th, .act td { padding-inline: .45rem; }
  #actives .cmp tbody th { min-width: 0; }
  #actives .cmp td.num { white-space: normal; }
  .act td .note { display: none; }
}
.days td { min-width: 8rem; }
"""

write_page("kvk19_prep", "K203 vs K365 Prep", BODY, EXTRA)
