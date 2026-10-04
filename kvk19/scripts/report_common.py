"""Shared data loading, styling and HTML helpers for the KvK 19 prep and battle reports.

Aggregate numbers only: no player names anywhere.
"""
import json
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load(name):
    return json.loads((DATA / name).read_text())


known = load("known_data.json")
mp = load("mightpulse_summary.json")
simlev = load("sim_levers.json")
stock = load("stockpile_estimate.json")
opt = {k: load(f"external/kingshotoptimizer_{k}.json")["result"] for k in ("203", "365")}

US, THEM = known["kingdoms"]["203"], known["kingdoms"]["365"]
MU, MT = mp["kingdoms"]["203"], mp["kingdoms"]["365"]
ku, kt = MU["kingdom"], MT["kingdom"]
mtu, mtt = ku["boards"]["mystic_trial"], kt["boards"]["mystic_trial"]

_snap = datetime.fromisoformat(mp["activity_snapshot_at"])
_pulled = datetime.fromisoformat(mp["generated_at"])
SNAP = f"{_snap.day} {_snap:%b}"
PULLED = f"{_pulled.day} {_pulled:%b %Y}"

# Judgement estimates, % chance K203 wins the phase.
PROJ = {"prep": (42, 52), "castle": (47, 57)}

us_top5 = sum(US["top5_player_power_m"])
th_top5 = sum(THEM["top5_player_power_m"])
us_ally5 = sum(a["real_power_b"] for a in US["top_alliances"])
th_ally5 = sum(a["real_power_b"] for a in THEM["top_alliances"])


def b(n):
    return f"{n / 1e9:.1f}B"


def m(n):
    return f"{n / 1e6:,.0f}M"


def pct(a, n):
    return round(100 * a / n) if n else 0


def unconf(text="Unconfirmed"):
    return f'<span class="tag-unc">{escape(text)}</span>'


def edge(a, c, higher_better=True, tol=0.0):
    if abs(a - c) <= tol:
        return '<span class="edge even">Even</span>'
    us_lead = (a > c) == higher_better
    return f'<span class="edge {"us" if us_lead else "them"}">{"K203" if us_lead else "K365"}</span>'


def cmp_table(rows, first_col="Measure"):
    """rows: list of pre-rendered <tr> strings."""
    return (f'<div class="tbl-wrap"><table class="cmp"><thead><tr><th scope="col">{first_col}</th>'
            '<th scope="col" class="num colh us">K203</th><th scope="col" class="num colh them">K365</th>'
            f'<th scope="col">Edge</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def row(lbl, u, t, fmt=lambda v: f"{v:,}", higher=True, tol=0, cls="", note=""):
    return (f'<tr class="{cls}"><th scope="row">{lbl}{" " + note if note else ""}</th><td class="num">{fmt(u)}</td>'
            f'<td class="num">{fmt(t)}</td><td>{edge(u, t, higher, tol)}</td></tr>')


def pair_bars(rows, unit, vmax, ticks):
    """Paired horizontal bars on one shared 0..vmax scale. rows: [(label, us_val, us_name, them_val, them_name)]."""
    out = []
    for lbl, uv, un, tv, tn in rows:
        out.append(f'''<div class="pb-row"><div class="pb-lbl">{lbl}</div><div class="pb-bars">
<div class="pb-line"><span class="pb-name us">{un}</span><span class="pb-track"><span class="pb-bar us" style="width:{100 * uv / vmax:.1f}%"></span></span><span class="pb-val">{uv:,g}{unit}</span></div>
<div class="pb-line"><span class="pb-name them">{tn}</span><span class="pb-track"><span class="pb-bar them" style="width:{100 * tv / vmax:.1f}%"></span></span><span class="pb-val">{tv:,g}{unit}</span></div>
</div></div>''')
    axis = "".join(f'<span style="left:{100 * t / vmax:.1f}%">{t:,g}{unit}</span>' for t in ticks)
    return f'<div class="pb">{"".join(out)}<div class="pb-axis"><div class="pb-axis-in">{axis}</div></div></div>'


def gauge(lo, hi, label):
    return f'''<div class="gauge" role="img" aria-label="{escape(label)}: {lo} to {hi} percent chance K203 wins">
  <span class="g-mid"></span><span class="g-new" style="left:{lo}%;width:{hi - lo}%"></span>
</div><div class="gauge-axis"><span>K365 favoured</span><span>Even</span><span>K203 favoured</span></div>'''


def record_strip(k):
    cells = "".join(
        f'<li><span class="opp">K{r["opponent"]}</span>'
        f'<span class="res {r["prep"]}" title="Prep {"win" if r["prep"] == "W" else "loss"}">{r["prep"]}</span>'
        f'<span class="res {r["castle"]}" title="Castle {"win" if r["castle"] == "W" else "loss"}">{r["castle"]}</span></li>'
        for r in k["kvk_history"])
    return f'<ol class="rec">{cells}</ol>'


def numbered(items):
    return '<ol class="recs">' + "".join(f"<li><h3>{escape(t)}</h3><p>{d}</p></li>" for t, d in items) + "</ol>"


def bullets(items):
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700'
         '&family=Source+Sans+3:wght@400;600;700&family=IBM+Plex+Mono:wght@500&display=swap">')

CSS = """
/* Layout: one reading column; verdict first, detail tables scroll inside their own frames. */
:root {
  --bg: #F3F5F8; --surface: #FFFFFF; --line: #D9DEE6; --fg: #17202C; --muted: #5A6577;
  --us: #2453C9; --us-soft: #DCE5FA; --them: #B5481A; --them-soft: #F6E2D7;
  --win: #1E7A4C; --loss: #B42335; --unc-bg: #FFF2C9; --unc-fg: #6B4E00; --risk: #B42335; --risk-soft: #F8E1E4;
  --f-display: "Barlow Condensed", "Arial Narrow", "Roboto Condensed", sans-serif;
  --f-body: "Source Sans 3", "Segoe UI", system-ui, -apple-system, sans-serif;
  --f-data: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #10151C; --surface: #18202A; --line: #2B3644; --fg: #E6EBF2; --muted: #9AA6B8;
  --us: #7EA2FF; --us-soft: #22325A; --them: #F2995F; --them-soft: #4A2A1A;
  --win: #5CCB8F; --loss: #F2788A; --unc-bg: #3E3410; --unc-fg: #F3D57A; --risk: #F2788A; --risk-soft: #44202A; color-scheme: dark;
} }
:root[data-theme="dark"] {
  --bg: #10151C; --surface: #18202A; --line: #2B3644; --fg: #E6EBF2; --muted: #9AA6B8;
  --us: #7EA2FF; --us-soft: #22325A; --them: #F2995F; --them-soft: #4A2A1A;
  --win: #5CCB8F; --loss: #F2788A; --unc-bg: #3E3410; --unc-fg: #F3D57A; --risk: #F2788A; --risk-soft: #44202A; color-scheme: dark;
}
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--fg); font: 400 1rem/1.55 var(--f-body); margin: 0; }
.wrap { max-width: 60rem; margin: 0 auto; padding-inline: 16px; padding-block: 2rem 4rem; display: grid; gap: 3rem; }
h1, h2, h3 { font-family: var(--f-display); text-wrap: balance; margin: 0; line-height: 1.1; }
h1 { font-size: clamp(2.4rem, 7vw, 3.6rem); font-weight: 700; letter-spacing: .01em; }
h2 { font-size: 1.9rem; font-weight: 700; }
h3 { font-size: 1.3rem; font-weight: 600; }
h4 { font: 700 .78rem/1.3 var(--f-body); text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin: 1rem 0 .35rem; }
p { margin: 0; max-width: 68ch; }
ul { margin: 0; padding-left: 1.15rem; display: grid; gap: .4rem; max-width: 68ch; }
strong { font-weight: 700; }
.num { font-variant-numeric: tabular-nums; }
.eyebrow { font: 600 .8rem/1 var(--f-body); text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }
section { display: grid; gap: 1.1rem; min-width: 0; }
.lede { color: var(--muted); }
.note { font-size: .92rem; color: var(--muted); }
.us-t { color: var(--us); } .them-t { color: var(--them); }
.hero { display: grid; gap: 1rem; }
.vs { display: flex; flex-wrap: wrap; align-items: baseline; gap: .2em .5em; }
.vs .k { font-family: var(--f-display); font-weight: 700; }
.meta { display: flex; flex-wrap: wrap; gap: .5rem 1.5rem; color: var(--muted); font-size: .92rem; }
.meta strong { color: var(--fg); font-weight: 600; }
.verdict { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: 1rem; }
.verdict > div { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1rem 1.1rem; display: grid; gap: .2rem; align-content: start; min-width: 0; }
.verdict .v-main { border-color: var(--us); }
.verdict .big { font: 700 2.2rem/1 var(--f-display); }
.verdict .lbl { font-size: .9rem; color: var(--muted); }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1rem 1.1rem; display: grid; gap: .6rem; align-content: start; min-width: 0; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr)); gap: 1.25rem; }
.card.risk { border-color: var(--risk); }
.tbl-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }
.tbl-wrap.flat { border: 0; }
table { border-collapse: collapse; width: 100%; font-size: .95rem; }
th, td { padding: .6rem .75rem; text-align: left; border-bottom: 1px solid var(--line); vertical-align: middle; }
tbody tr:last-child > * { border-bottom: 0; }
thead th { font: 600 .75rem/1.2 var(--f-body); text-transform: uppercase; letter-spacing: .07em; color: var(--muted); white-space: nowrap; }
tbody th { font-weight: 600; }
td.num, th.num { text-align: right; white-space: nowrap; }
.cmp tbody th { font-weight: 400; min-width: 11rem; }
.cmp tr.key > * { background: var(--us-soft); font-weight: 700; }
.cmp tr.minor > * { color: var(--muted); }
.colh.us { color: var(--us); } .colh.them { color: var(--them); }
.edge { display: inline-block; font: 600 .75rem/1 var(--f-body); padding: .3rem .5rem; border-radius: 999px; white-space: nowrap; }
.edge.us { background: var(--us-soft); color: var(--us); }
.edge.them { background: var(--them-soft); color: var(--them); }
.edge.even { background: transparent; color: var(--muted); border: 1px solid var(--line); }
.tag-unc, .tag-low { display: inline-block; font: 600 .68rem/1 var(--f-body); text-transform: uppercase; letter-spacing: .06em; padding: .25rem .4rem; border-radius: 4px; vertical-align: .1em; white-space: nowrap; }
.tag-unc { background: var(--unc-bg); color: var(--unc-fg); }
.tag-low { border: 1px solid var(--line); color: var(--muted); }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr)); gap: 1.25rem; }
.chart { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1rem; display: grid; gap: .75rem; min-width: 0; }
.chart h3 { font-size: 1.15rem; }
.pb { display: grid; gap: .6rem; }
.pb-row { display: grid; grid-template-columns: 2.9rem 1fr; gap: .5rem; align-items: center; }
.pb-lbl { font: 500 .78rem var(--f-data); color: var(--muted); }
.pb-bars { display: grid; gap: 3px; min-width: 0; }
.pb-line, .pb-axis { display: grid; grid-template-columns: 2.6rem 1fr 3.6rem; gap: .5rem; align-items: center; }
.pb-axis { margin-left: 3.4rem; }
.pb-name { font: 500 .74rem var(--f-data); }
.pb-name.us { color: var(--us); } .pb-name.them { color: var(--them); }
.pb-track { height: .7rem; background: linear-gradient(to right, var(--line) 1px, transparent 1px) 0 0 / 25% 100%; position: relative; display: block; }
.pb-bar { display: block; height: 100%; border-radius: 0 3px 3px 0; }
.pb-bar.us { background: var(--us); } .pb-bar.them { background: var(--them); }
.pb-val { font: 500 .74rem var(--f-data); text-align: right; font-variant-numeric: tabular-nums; }
.pb-axis-in { grid-column: 2; position: relative; height: 1rem; font: 500 .65rem var(--f-data); color: var(--muted); }
.pb-axis-in span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
.pb-axis-in span:first-child { transform: none; }
.pb-axis-in span:last-child { transform: translateX(-100%); }
.gauge { position: relative; height: 1.1rem; border-radius: 4px; background: linear-gradient(to right, var(--them-soft), var(--surface) 50%, var(--us-soft)); border: 1px solid var(--line); margin-top: .4rem; }
.g-mid { position: absolute; left: 50%; top: -3px; bottom: -3px; width: 2px; background: var(--muted); }
.g-new { position: absolute; top: 3px; bottom: 3px; background: var(--us); border-radius: 2px; opacity: .85; }
.gauge-axis { display: flex; justify-content: space-between; font-size: .72rem; color: var(--muted); }
.proj-range { display: flex; flex-wrap: wrap; align-items: baseline; gap: .5rem; }
.proj-range .num { font: 700 2.4rem/1 var(--f-display); color: var(--us); }
ol.rec { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(4.3rem, 1fr)); gap: .4rem; }
ol.rec li { display: grid; grid-template-columns: 1fr 1fr; gap: 2px; border: 1px solid var(--line); border-radius: 6px; padding: .3rem; }
.opp { grid-column: 1 / -1; font: 500 .72rem var(--f-data); text-align: center; color: var(--muted); }
.res { font: 700 .8rem/1.5 var(--f-data); text-align: center; border-radius: 3px; }
.res.W { color: var(--win); background: color-mix(in srgb, var(--win) 14%, transparent); }
.res.L { color: var(--surface); background: var(--loss); }
ol.recs { list-style: none; counter-reset: r; margin: 0; padding: 0; display: grid; gap: .9rem; }
ol.recs li { counter-increment: r; display: grid; grid-template-columns: 2.2rem 1fr; gap: .15rem .75rem; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: .9rem 1rem; }
ol.recs li::before { content: counter(r); grid-row: span 2; font: 700 1.6rem/1 var(--f-display); color: var(--us); }
ol.recs h3 { font-size: 1.2rem; }
.svgchart { width: 100%; height: auto; display: block; }
.svgchart text { fill: var(--muted); font: 500 11px var(--f-data); }
.svgchart .grid { stroke: var(--line); stroke-width: 1; }
.svgchart .l-us { stroke: var(--us); fill: none; stroke-width: 2.5; }
.svgchart .l-them { stroke: var(--them); fill: none; stroke-width: 2.5; }
.svgchart .d-us { fill: var(--us); } .svgchart .d-them { fill: var(--them); }
.svgchart .lbl-us { fill: var(--us); font-weight: 700; } .svgchart .lbl-them { fill: var(--them); font-weight: 700; }
.legend { display: flex; flex-wrap: wrap; gap: .4rem 1rem; font-size: .85rem; color: var(--muted); align-items: center; }
.sw { display: inline-block; width: .9rem; height: .9rem; border-radius: 2px; vertical-align: -.1rem; margin-right: .3rem; }
.sw.us { background: var(--us); } .sw.them { background: var(--them); }
.caveats { font-size: .92rem; color: var(--muted); }
.caveats ul { max-width: 75ch; }
footer { font-size: .82rem; color: var(--muted); border-top: 1px solid var(--line); padding-top: 1rem; }
a { color: var(--us); }
:focus-visible { outline: 2px solid var(--us); outline-offset: 2px; }
@media (max-width: 30rem) { .cmp tbody th { min-width: 8.5rem; } th, td { padding: .5rem .55rem; } }
"""


def write_page(slug, title, body_html, extra_css=""):
    """Write report/<slug>.html (standalone) and report/<slug>.body.html (for hosting)."""
    head = f"<title>{escape(title)}</title>\n{FONTS}\n<style>{CSS}{extra_css}</style>\n"
    out = ROOT / "report"
    out.mkdir(exist_ok=True)
    (out / f"{slug}.body.html").write_text(head + body_html)
    (out / f"{slug}.html").write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + head + "</head>\n<body>\n" + body_html + "\n</body>\n</html>\n")
    print("wrote", out / f"{slug}.html")
