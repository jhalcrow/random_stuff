#!/usr/bin/env python3
"""Build the KvK 19 battle report: report/kvk19_battle.html (+ .body.html for hosting)."""
from html import escape
from report_common import (US, THEM, MU, MT, ku, kt, mtu, mtt, simlev, PROJ, PULLED, SNAP, us_top5, th_top5,
                           us_ally5, th_ally5, b, unconf, edge, row, cmp_table, pair_bars, gauge, numbered, bullets,
                           write_page)

lo, hi = PROJ["castle"]

# ---------- battle-day timeline (UTC) ----------
SEG = [(10, 12, "Cross-kingdom fighting", "x"), (12, 17, "Castle window", "c"), (17, 22, "Cross-kingdom fighting", "x")]
W, H, L, R = 640, 92, 12, 12


def hx(h):
    return L + (W - L - R) * (h - 10) / 12


tl = "".join(
    f'<rect class="seg-{k}" x="{hx(a):.1f}" y="18" width="{hx(z) - hx(a):.1f}" height="34" rx="4"/>'
    f'<text class="seg-t-{k}" x="{(hx(a) + hx(z)) / 2:.1f}" y="40" text-anchor="middle">{escape(t if z - a > 2 else "Open")}</text>'
    for a, z, t, k in SEG)
tl += "".join(f'<line class="grid" x1="{hx(h):.1f}" x2="{hx(h):.1f}" y1="56" y2="62"/>'
              f'<text x="{hx(h):.1f}" y="76" text-anchor="{"start" if h == 10 else "end" if h == 22 else "middle"}">{h:02d}:00</text>'
              for h in (10, 12, 14.5, 17, 22) if h == int(h))
tl += (f'<line class="hold" x1="{hx(12):.1f}" x2="{hx(14.5):.1f}" y1="10" y2="10"/>'
       f'<text x="{hx(12):.1f}" y="8" class="hold-t">2.5 h continuous hold wins</text>')
timeline_svg = (f'<svg class="svgchart tl" viewBox="0 0 {W} {H}" role="img" aria-label="Battle day, 10:00 to 22:00 UTC. '
                f'Cross-kingdom fighting 10 to 12, castle window 12 to 17, cross-kingdom fighting 17 to 22.">{tl}</svg>')

# ---------- Town Centre bands ----------
BANDS = (("tc70+", "TC70+"), ("tc65_69", "TC65–69"), ("tc56_64", "TC56–64"), ("tc_le55", "TC55 and below"))


def band_tot(mk, key):
    return sum(a["tc_bands"][key] for a in mk["top_alliances"])


def band_table(mk, side):
    head = "".join(f'<th scope="col" class="num">{lbl}</th>' for _, lbl in BANDS)
    body = "".join(
        f'<tr><th scope="row" class="tagc {side}">{a["tag"]}</th>'
        + "".join(f'<td class="num">{a["tc_bands"][k]}</td>' for k, _ in BANDS)
        + f'<td class="num">{b(a["total_power"])}</td></tr>' for a in mk["top_alliances"])
    body += ('<tr class="tot"><th scope="row">Top 6</th>' + "".join(f'<td class="num">{band_tot(mk, k)}</td>' for k, _ in BANDS)
             + f'<td class="num">{b(mk["top6_totals"]["total_power"])}</td></tr>')
    return (f'<div class="tbl-wrap"><table class="bands"><thead><tr><th scope="col">Alliance</th>{head}'
            f'<th scope="col" class="num">Power</th></tr></thead><tbody>{body}</tbody></table></div>')


# ---------- quality vs quantity (battle simulator) ----------
lev_max = 4.0
lev_rows = "".join(
    f'<div class="lev-row{" lev-q" if "attack" in c["change"] or "Truegold" in c["change"] else ""}">'
    f'<span class="lev-lbl">{escape(c["change"])}</span>'
    f'<span class="pb-track"><span class="pb-bar lev" style="width:{100 * c["kill_ratio"] / lev_max:.1f}%"></span></span>'
    f'<span class="pb-val">{c["kill_ratio"]:.1f} : 1</span></div>' for c in simlev["cases"])
lev_axis = "".join(f'<span style="left:{100 * t / lev_max:.1f}%">{t:g}</span>' for t in (0, 1, 2, 3, 4))
lev_chart = f'<div class="lev">{lev_rows}<div class="lev-axis"><div class="pb-axis-in">{lev_axis}</div></div></div>'
HL = simlev["hero"]
c2x = next(c for c in simlev["cases"] if c["change"] == "2x troops")["kill_ratio"]
c20 = next(c for c in simlev["cases"] if c["change"] == "+20% attack and lethality")["kill_ratio"]

strength = cmp_table([
    row("Mystic Trial, top 100 combined", mtu["total"], mtt["total"], lambda v: f"{v:,}", cls="key"),
    row("Top 5 players, real power", us_top5, th_top5, lambda v: f"{v:,}M"),
    row("Top 5 alliances, real power", us_ally5, th_ally5, lambda v: f"{v:.1f}B"),
    row("Top 6 alliances, total power", MU["top6_totals"]["total_power"], MT["top6_totals"]["total_power"], b, tol=2e9),
    row("Top 6 members at Town Centre 70+", band_tot(MU, "tc70+"), band_tot(MT, "tc70+")),
    row("Hero power, top 100", ku["hero_total"], kt["hero_total"], b, tol=0.15e9),
    f'<tr><th scope="row">KvK castle record</th><td class="num">{US["castle_record"]}</td><td class="num">{THEM["castle_record"]}</td><td>{edge(1, 1)}</td></tr>',
    row("Troop power, top 100", ku["troop_power"], kt["troop_power"], b, tol=1e9, cls="minor",
        note='<span class="tag-low">Less weight in KvK</span>'),
])

ally = {a["tag"]: a for a in MU["top_alliances"]}
them = {a["tag"]: a for a in MT["top_alliances"]}

castle_plan = numbered([
    ("One alliance holds the castle",
     "Hold time counts per alliance, not per kingdom, so passing the castle between our alliances restarts the clock. "
     f"ORM should be the holder: our largest alliance ({b(ally['ORM']['total_power'])}), {ally['ORM']['tc_bands']['tc70+']} members at TC70+, and the most active in our snapshot. "
     "If K365 knocks ORM out, retake it with an ORM-led rally. A different alliance retaking it starts that alliance's clock from zero."),
    ("Take all four turrets",
     "Enemy turrets fire on the castle about every 4 minutes, speeding up to every minute, at roughly 2% casualties per turret. "
     "Our own turrets don't fire on us and give our troops +8%, +12%, +15% or +20% Lethality for 1 to 4 turrets. "
     "In our battle model a bonus that size swings a fight as much as a large troop advantage. BR4 and SRT take two turrets each; HnG and BR1 keep refilling them."),
    ("Rally in pairs",
     "Send an attack rally with offensive heroes, then a garrison rally with defensive heroes about 5 seconds behind it, so the castle is refilled the moment it falls. "
     "The player with the longest march opens their rally first, so all rallies land 1 to 5 seconds apart."),
    ("PRO runs counter-rallies",
     f"PRO has the most combat history of our top three ({b(ally['PRO']['total_kills'])} kills on its roster). "
     "Its job is to rally straight onto any K365 rally that takes the castle or a turret, before their garrison settles in."),
    ("Plan for SCC",
     f"SCC is K365's #4 alliance and out-sizes SRT by {(them['SCC']['total_power'] - ally['SRT']['total_power']) / 1e9:.1f}B. "
     "Expect it on the turrets. SRT should not hold a turret alone against it: keep a PRO or BR4 counter-rally ready for whichever turret SCC hits."),
    ("Pick joiner heroes with the right first skill",
     "Only the joiner's first hero's first skill counts, and only the four highest-level skills in a rally apply. Skills of the same type add together, while different types multiply, so spread them out. "
     "Attack joiners: Amane (+25% attack), Chenko (+25% lethality), Ava (−25% enemy defence), Vivian (+25% damage to the enemy). "
     "Garrison joiners: Triton (+25% defence), Ava, Alcar, Petra. Each joiner sends their highest-level option."),
    ("Rally leaders are our biggest accounts",
     f"The leader's own stats govern the whole rally. Our top 5 players carry {100 * (us_top5 / th_top5 - 1):.0f}% more real power than K365's, so put them at the front of every rally."),
])

city_plan = numbered([
    ("Shield before prep ends",
     "Cities can be hit in the gap between prep and battle. Everyone without a battle-day role shields before Day 5 closes, and keeps a shield running through 22:00 UTC Saturday."),
    ("Battle roles stay off the map",
     "Attacking drops your shield and starts a cooldown, so rally leaders, joiners and holders can't rely on shields. "
     "Keep their troops in rallies, garrisons and turrets, not sitting at home, and heal continuously so the Infirmary never fills."),
    ("No gathering on battle day",
     "Shields don't protect troops on resource tiles or in alliance buildings. Recall gatherers before 10:00 UTC."),
    ("Spend or protect resources",
     "Anything above Storehouse protection can be plundered. Spend it in prep or keep it under the protected amount."),
    ("Punish hitters inside our kingdom",
     "A K365 player who teleports into K203 to hit cities leaves their city sitting in our kingdom. Each alliance names a watcher who calls hits, and a nearby rally leader goes after the hitter's city. "
     "Do this in the cross-kingdom windows, never with castle or turret troops."),
    ("Recover after the battle",
     "Field Triage returns 30% of troops lost beyond the Infirmary by default. Medical Satchels add 10% and alliance Rescue Orders up to 50%, for as much as 90%. Line these up before Saturday."),
])

rules = bullets([
    "<strong>Propose: castle and turrets only, no city hits.</strong> A castle fight rewards quality, where we lead on Mystic Trial and top players. City hits reward the side with more active hitters, which is K365.",
    "<strong>Fallback: no zeroing.</strong> No repeat hits on the same city, and no hits on cities below an agreed Town Centre level.",
    "Put any agreement in writing and post it in both kingdoms' channels with a named contact on each side, so a breach can be called out fast.",
    "Prepare as if any agreement will be broken. The shield plan below applies either way.",
])

scenarios = f'''<div class="cards">
  <div class="card"><h3 class="us-t">If we win prep</h3>
    <ul><li>We attack K365's castle, in K365's kingdom. Our own castle is safe all day.</li>
    <li>K365 can still teleport into K203 in the cross-kingdom windows (10:00–12:00 and 17:00–22:00 UTC) and hit our cities.</li>
    <li>Goal: ORM takes the castle as early as possible after 12:00 and holds it for 2.5 hours, with turrets covering it.</li></ul></div>
  <div class="card risk"><h3 class="them-t">If K365 wins prep</h3>
    <ul><li>K365 attacks our castle, inside our kingdom. Their castle is safe, so we can only defend.</li>
    <li>Their forces are in K203 all day, close to our cities. City defence matters most in this case.</li>
    <li>Goal: never let one K365 alliance hold for 2.5 hours, and keep their total hold time short. Garrison the castle and all four turrets before 12:00, and counter-rally every time they take it.</li></ul></div>
</div>'''

tc_notes = bullets([
    "A city hit only scores kill points when the two Town Centres are within 3 levels of each other. A hit outside that range still happens and still costs troops, but scores nothing.",
    f"So K365's strongest hitters (their top 6 have {band_tot(MT, 'tc70+')} members at TC70+) can only score on our strongest cities (TC67 and up). "
    f"Those are exactly our rally and holder accounts, with {band_tot(MU, 'tc70+')} members at TC70+ in our top 6.",
    f"Our smaller cities give K365's big accounts no points. The real threat to them is griefing, plus K365's own small accounts: {band_tot(MT, 'tc_le55')} members at TC55 or below in their top 6, against our {band_tot(MU, 'tc_le55')}. "
    f"Most of theirs sit in WYW and SDH, which show almost no kills ({b(them['WYW']['total_kills'] + them['SDH']['total_kills'])} between them).",
    f"K365 has {kt['located']:,} cities on the map to our {ku['located']:,}, so if city fighting breaks out they have more accounts to send.",
])

BODY = f'''<main class="wrap">
  <header class="hero">
    <span class="eyebrow">KvK #19 · Battle day</span>
    <h1 class="vs"><span class="k us-t">K203</span><span>vs</span><span class="k them-t">K365</span></h1>
    <p class="lede">The castle is won by holding it. Our edge is quality: stronger top players and a deeper hero base. We need one alliance holding, all four turrets, and a city-defence plan, since no rules have been agreed.</p>
    <div class="meta"><span>Battle <strong>Sat 10 Oct 2026, 10:00–22:00 UTC</strong> {unconf("Estimated")}</span><span>Data as of <strong>{PULLED}</strong></span></div>
    <div class="verdict">
      <div class="v-main"><span class="lbl">Castle day</span><span class="big num">{lo}–{hi}%</span><span class="lbl">chance K203 wins. Close, slight lean K203.</span></div>
      <div><span class="lbl">To win the castle</span><span class="big num">2.5 h</span><span class="lbl">continuous hold by one alliance, or the longest total hold by 17:00 UTC.</span></div>
      <div><span class="lbl">Mystic Trial, top 100</span><span class="big num">+{100 * (mtu["total"] / mtt["total"] - 1):.1f}%</span><span class="lbl">K203 ahead: the best current measure of combat quality.</span></div>
    </div>
  </header>

  <section id="how">
    <h2>How battle day works</h2>
    <div class="chart">{timeline_svg}
      <div class="legend"><span><span class="sw seg-c-sw"></span>Castle window</span><span><span class="sw seg-x-sw"></span>Cross-kingdom fighting only</span></div></div>
    <ul>
      <li><strong>Prep decides the ground.</strong> The prep winner attacks. The fight happens in the loser's kingdom, and the winner's castle cannot be attacked.</li>
      <li><strong>What is fought over:</strong> the King's Castle and four turrets. Turrets alone don't win, but they decide who survives on the castle.</li>
      <li><strong>How it is won:</strong> one alliance holds the castle for 2.5 hours in a row, or has the longest total hold when the window closes. {unconf("Some guides say 3 hours")}</li>
      <li><strong>Losses:</strong> wounded troops go to the Infirmary. Beyond its capacity, 70% go to the Enlistment Office (recoverable) and 30% are lost until Field Triage.</li>
      <li><strong>Kill points by tier:</strong> T6 5, T7 7, T8 9, T9 11, T10 13. Points for Truegold troops are not published.</li>
    </ul>
  </section>

  <section id="scenarios">
    <h2>Two ways the day can go</h2>
    {scenarios}
  </section>

  <section id="cities">
    <h2>Town Centre hits</h2>
    <p class="lede">No rules have been agreed, so K365 can hit our cities. Here is where that threat is real.</p>
    {tc_notes}
    <h3 class="us-t">K203 top 6 by Town Centre level</h3>
    {band_table(MU, "us")}
    <h3 class="them-t">K365 top 6 by Town Centre level</h3>
    {band_table(MT, "them")}
  </section>

  <section id="rules">
    <h2>Rules to propose to K365</h2>
    {rules}
  </section>

  <section id="city-plan">
    <h2>City defence plan</h2>
    {city_plan}
  </section>

  <section id="castle-plan">
    <h2>Castle plan</h2>
    <p class="lede">Alliance roles below are a starting point for leadership to adjust.</p>
    {castle_plan}
  </section>

  <section id="strength">
    <h2>Strength check</h2>
    {strength}
    <div class="chart why">
      <h3>Why quality beats quantity in a fight</h3>
      <p>Our alliance's battle simulator, calibrated on real battle reports, shows that troop count only counts under a square root, while attack and lethality multiply each other. In an otherwise even fight, <strong>+20% attack and lethality wins as decisively as twice the troops</strong> ({c20:.1f} vs {c2x:.1f} enemy losses per own loss).</p>
      {lev_chart}
      <p class="note">Enemy losses per own loss when one side of an otherwise identical fight gets the change shown. Troop-count changes in grey, quality changes in colour. No heroes on either side.</p>
      <p>Heroes are the biggest single multiplier. A maxed Gen 7 hero with full gear adds about <strong>+{HL["hero_attack_defense_pct"]}%</strong> attack and defence and <strong>+{HL["hero_lethality_health_pct"]}%</strong> lethality and health to its troop type, which roughly doubles the stats of the troops it leads. Mystic Trial, a hero combat score, tracks that strength better than troop power does.</p>
    </div>
  </section>

  <section id="projection">
    <h2>Castle projection</h2>
    <div class="card"><p class="proj-range"><span class="num">{lo}–{hi}%</span><span class="note">chance K203 wins castle day</span></p>{gauge(lo, hi, "Castle")}
      <h4>For us</h4><ul>
        <li>Mystic Trial lead at every depth of the top 100, and {100 * (us_top5 / th_top5 - 1):.0f}% more real power in our top 5 players.</li>
        <li>More of our top-6 members at TC70+ ({band_tot(MU, "tc70+")} vs {band_tot(MT, "tc70+")}).</li></ul>
      <h4>Against us</h4><ul>
        <li>K365 leads real power at each of the top 5 alliance ranks ({th_ally5:.1f}B vs {us_ally5:.1f}B), and SCC out-sizes SRT.</li>
        <li>K365 has more active players, which matters if city fighting spreads.</li></ul>
      <p class="note">Losing prep doesn't decide the castle: across kingdoms the two results line up only about 31% of the time. It does move the fight into our kingdom.</p></div>
  </section>

  <section class="caveats" id="caveats"><h2>About the data</h2>{bullets([
    "Battle rules come from community guides (kingshotdata.com, kingshotguide.org, kingshotmastery.com, kingshotbattlemaster.com and others). Guides disagree in places, and none states a game version. Confirm timings and the hold requirement in-game.",
    "Whether plunder applies across kingdoms, how players return home after teleporting, and kill points for Truegold troops are not confirmed.",
    f"Town Centre levels, kills and power come from MightPulse alliance rosters ({PULLED}). Roster kill counts use different counting from the kingdom leaderboards, so we compare them only within the same source.",
    "Battle-model figures come from our alliance's simulator in heroless, otherwise identical fights. It shows which stats decide combat. It does not simulate Mystic Trial or castle mechanics.",
    "The battle date is estimated from the four-week cycle. Projections are judgement estimates.",
  ])}</section>
  <footer>Sources: MightPulse ({PULLED}); StratForge and Kingshot.net (early Oct 2026); community KvK guides; our alliance battle simulator. Aggregate figures only.</footer>
</main>'''

EXTRA = """
.tl .seg-c { fill: var(--us); } .tl .seg-x { fill: var(--them-soft); stroke: var(--them); stroke-width: 1; }
.tl .seg-t-c { fill: var(--surface); font-weight: 700; } .tl .seg-t-x { fill: var(--them); font-weight: 700; }
.tl .hold { stroke: var(--fg); stroke-width: 2; } .tl .hold-t { fill: var(--fg); }
.sw.seg-c-sw { background: var(--us); } .sw.seg-x-sw { background: var(--them-soft); border: 1px solid var(--them); }
.bands .tagc { font: 700 1rem var(--f-display); letter-spacing: .03em; }
.bands .tagc.us { color: var(--us); } .bands .tagc.them { color: var(--them); }
.bands tr.tot > * { border-top: 2px solid var(--line); font-weight: 700; }
.why > p { max-width: 70ch; }
.lev { display: grid; gap: .45rem; }
.lev-row, .lev-axis { display: grid; grid-template-columns: 13rem 1fr 3.6rem; gap: .2rem .6rem; align-items: center; }
.lev-lbl { font-size: .88rem; }
.pb-bar.lev { background: var(--muted); }
.lev-q .pb-bar.lev { background: var(--us); }
.lev-q .lev-lbl { font-weight: 600; }
@media (max-width: 36rem) {
  .lev-row, .lev-axis { grid-template-columns: 1fr 3.6rem; }
  .lev-lbl { grid-column: 1 / -1; }
  .lev-axis .pb-axis-in { grid-column: 1; }
}
"""

write_page("kvk19_battle", "K203 vs K365 Battle", BODY, EXTRA)
