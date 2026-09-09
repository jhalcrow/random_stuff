#!/usr/bin/env python3
"""Crawl kingshotoptimizer.com for every hero's Expedition skills, at every skill level.

Two things this gets that no other source in this project has:
  1. MAX-LEVEL values for every hero, which is what heroes.py should hold -- the tooltips read off
     reports are whatever level that particular account had, and Narses' were Lv. 4.
  2. The per-level progression L1..L5, so an opponent's under-levelled hero can be modelled at its
     actual level instead of guessed at.

Only the "Expedition Skills (passive / proc)" group is taken; "Conquest Skills (base)" are the
other game mode and are not what sim.py models.

  python3 kingshot/crawl_heroes.py [--refresh]     # writes hero_skills.json
"""
import json, os, re, sys, time, urllib.request

BASE = 'https://kingshotoptimizer.com'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.hero_cache')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hero_skills.json')
DELAY = 1.0          # be polite: one page a second


def get(url, refresh=False):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, re.sub(r'\W+', '_', url) + '.html')
    if os.path.exists(path) and not refresh:
        return open(path, encoding='utf-8').read()
    req = urllib.request.Request(url, headers={'User-Agent': 'kingshot-sim-calibration/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        s = r.read().decode('utf-8', 'replace')
    open(path, 'w', encoding='utf-8').write(s)
    time.sleep(DELAY)
    return s


def slugs(refresh=False):
    html = get(f'{BASE}/heroes/browse/', refresh)
    found = re.findall(r'href="/heroes/([a-z0-9\-]+)/"', html)
    skip = {'browse', 'compare'}
    return sorted({s for s in found if s not in skip})


def expedition_block(html):
    """The page carries Conquest skills first, then Expedition; take only the latter."""
    i = html.find('Expedition Skills')
    if i < 0:
        return ''
    j = html.find('<h3', i + 10)
    return html[i:j if j > 0 else len(html)]


CARD = re.compile(r'skill-name[^>]*>(?P<name>[^<]+)</div>\s*'
                  r'<div class="skill-desc[^>]*>(?P<desc>.*?)</div>', re.S)
TIER = re.compile(r'skill-tier-label[^>]*>(?P<lvl>L\d)</span>'
                  r'<span class="skill-tier-value[^>]*>(?P<val>[^<]*)</span>')


STAT = re.compile(r'>((?:Infantry|Cavalry|Archer) (Attack|Defense|Lethality|Health))<')


def parse_stats(html):
    """Expedition stats.  The page splits them: star Attack/Defense sit under the 'Expedition'
    heading, the exclusive weapon's Lethality/Health under 'Expedition Stats'.  Both are taken;
    Conquest-mode tiles are skipped."""
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'<h3[^>]*>([^<]+)</h3>', html)]
    out = {}
    for m in STAT.finditer(html):
        prev = [t for p, t in marks if p < m.start()]
        if not (prev and prev[-1].startswith('Expedition')):
            continue
        v = re.search(r'\+?([\d,]+\.?\d*)%', html[m.start():m.start() + 300])
        if v:
            out[m.group(2).lower()] = float(v.group(1).replace(',', ''))
    return out


def parse(html):
    block = expedition_block(html)
    if not block:
        return []
    cards = list(CARD.finditer(block))
    out = []
    for n, m in enumerate(cards):
        end = cards[n + 1].start() if n + 1 < len(cards) else len(block)
        tiers = {t.group('lvl'): t.group('val').strip() for t in TIER.finditer(block[m.end():end])}
        desc = re.sub(r'<[^>]+>', '', m.group('desc'))
        out.append({'name': m.group('name').strip(),
                    'desc': ' '.join(desc.split()),
                    'levels': {k: tiers[k] for k in sorted(tiers)}})
    return out


def main():
    refresh = '--refresh' in sys.argv
    data = {}
    names = slugs(refresh)
    print(f'{len(names)} heroes')
    for i, s in enumerate(names, 1):
        page = get(f'{BASE}/heroes/{s}/', refresh)
        skills = parse(page)
        data[s] = {'skills': skills, 'stats': parse_stats(page)}
        print(f'  {i:3}/{len(names)}  {s:14} {len(skills)} expedition skills'
              + ('   <-- NONE PARSED' if not skills else ''))
    json.dump(data, open(OUT, 'w'), indent=1, sort_keys=True)
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
