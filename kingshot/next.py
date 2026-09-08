#!/usr/bin/env python3
"""Greedy continuation of Advanced Truegold research from a known state.

  python3 next.py [dust_budget] [day_budget] [ttg_budget]

Tier is identified by the level-1 dust cost, which is unique per tier (46/73/86/135/213/426).
Name suffixes are unreliable: several TG8 techs end in "I" or "II" (Truegold Armaments I,
Heart of Gold I, ...) but belong to the Tier V/VI groups.
Current state in DONE below: economy maxed, Tier I L10, Tier II L6, Tier III L6.
"""
import json, os, re, sys

T = {t['name']: t for t in json.load(open(os.path.join(os.path.dirname(__file__), 'tree.json')))}
WA = 8
DUST = float(sys.argv[1]) if len(sys.argv) > 1 else 1e9
DAYS = float(sys.argv[2]) if len(sys.argv) > 2 else 1e9
TTG  = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9

ECON = ['Chests of Gold','Truegold Weaponry','Truegold Barracks','Truegold Intel',
        'Truegold Infirmaries','Quick Bandage','Limited Supply']
TIER_BY_L1_DUST = {46:'I', 73:'II', 86:'III', 135:'IV', 213:'V', 426:'VI'}

def tier_of(n):
    if n in ECON: return 'econ'
    return TIER_BY_L1_DUST.get(T[n]['levels'][0]['cost'].get('Truegold Dust'))

DONE = {'econ': 10, 'I': 10, 'II': 6, 'III': 6}
lvl = {n: DONE.get(tier_of(n), 0) for n in T}

def reqs_ok(t, l):
    r = t['levels'][l-1]['req']
    m = re.search(r'War Academy TG Lv\. (\d+)', r)
    if m and int(m.group(1)) > WA: return False
    for name, need in re.findall(r'(?:, )?([A-Z][A-Za-z\' ]+?(?: I{1,3}|IV|V|VI)?) Lv\. (\d+)', r):
        if name.startswith('War Academy'): continue
        if lvl.get(name, 0) < int(need): return False
    return True

dust = days = ttg = 0.0
steps = []
while True:
    best = None
    for n, t in T.items():
        if lvl[n] >= t['max']: continue
        l = lvl[n] + 1
        if not reqs_ok(t, l): continue
        L = t['levels'][l-1]; c = L['cost']
        d = c.get('Truegold Dust', 0); tt = c.get('Tempered Truegold', 0); dd = L['hours']/24
        if dust + d > DUST or days + dd > DAYS or ttg + tt > TTG: continue
        if best is None or d < best[0]: best = (d, n, l, tt, dd)
    if best is None: break
    d, n, l, tt, dd = best
    dust += d; days += dd; ttg += tt; lvl[n] = l
    steps.append((tier_of(n), n, l, d, tt, dd, dust, days, ttg))

print(f'{"band (tier / level / dust per step)":38s} {"techs":>5s} {"dust":>7s} {"TTG":>5s} {"days":>6s}   {"cum dust":>8s} {"cum days":>8s} {"cum TTG":>7s}')
cur = None
def flush(c):
    if c: print(f'  {c["lab"]:36s} {c["n"]:5d} {c["d"]:7.0f} {c["tt"]:5.0f} {c["dd"]:6.1f}   {c["cd"]:8.0f} {c["cdd"]:8.1f} {c["ctt"]:7.0f}')
for tier, n, l, d, tt, dd, cd, cdd, ctt in steps:
    key = (tier, d)
    if cur is None or cur['key'] != key:
        flush(cur)
        cur = dict(key=key, lab=f'Tier {tier} L{l} @ {d:.0f}/step', n=0, d=0, tt=0, dd=0)
    cur['n'] += 1; cur['d'] += d; cur['tt'] += tt; cur['dd'] += dd
    cur['cd'], cur['cdd'], cur['ctt'] = cd, cdd, ctt
flush(cur)
print(f'\nTOTAL: {dust:.0f} dust, {days:.1f} days, {ttg:.0f} tempered')
