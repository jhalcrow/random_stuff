#!/usr/bin/env python3
"""Greedy planner for Kingshot Advanced Truegold Research.

Buys (tech, level) steps cheapest-per-stat first, respecting every prerequisite,
until the dust or time budget is exhausted. Edit WEIGHTS / TROOP / WA_LEVEL below.
"""
import json, re, sys
T = {t['name']: t for t in json.load(open(__import__('os').path.join(__import__('os').path.dirname(__file__),'tree.json')))}

WA_LEVEL = int(sys.argv[1]) if len(sys.argv) > 1 else 6   # your War Academy TG level
DUST_BUDGET = float(sys.argv[2]) if len(sys.argv) > 2 else 15000
DAY_BUDGET = float(sys.argv[3]) if len(sys.argv) > 3 else 400
TT_BUDGET = float(sys.argv[4]) if len(sys.argv) > 4 else 0   # tempered truegold on hand

# value of +1 level of each stat family (relative). Economy nodes handled as phase 1.
WEIGHTS = {'Lethality': 1.0, 'Health': 1.0, 'Attack': 0.75, 'Defense': 0.5,
           "Squads' Deployment Capacity": 0.6, 'Rally Capacity': 0.4,
           "Squads' Attack": 0.6, "Squads' Defense": 0.4, "Squads' Lethality": 0.8, "Squads' Health": 0.8}
TROOP = {'Infantry': 1.0, 'Cavalry': 1.0, 'Archer': 1.0}
ECON = ['Chests of Gold','Truegold Weaponry','Truegold Barracks','Truegold Intel',
        'Truegold Infirmaries','Quick Bandage','Limited Supply']

def stat_value(t):
    e = t['effect']
    for troop, tw in TROOP.items():
        for stat, w in WEIGHTS.items():
            if e.startswith(f'{troop} {stat}'): return w * tw
    for stat, w in WEIGHTS.items():
        if e.startswith(stat): return w
    return 0.0

lvl = {n: 0 for n in T}
def reqs_ok(t, l):
    r = t['levels'][l-1]['req']
    m = re.search(r'War Academy TG Lv\. (\d+)', r)
    if m and int(m.group(1)) > WA_LEVEL: return False
    for name, need in re.findall(r'(?:, )?([A-Z][A-Za-z\' ]+?(?: I{1,3}|IV|V|VI)?) Lv\. (\d+)', r):
        if name.startswith('War Academy'): continue
        if lvl.get(name, 0) < int(need): return False
    return True

dust = days = tt = 0.0
plan = []
# Phase 1: economy nodes, in a sensible order, to max.
econ_order = ['Chests of Gold','Truegold Weaponry','Truegold Barracks','Truegold Intel',
              'Limited Supply','Truegold Infirmaries','Quick Bandage']
progress = True
while progress:
    progress = False
    for n in econ_order:
        t = T[n]
        while lvl[n] < t['max'] and reqs_ok(t, lvl[n]+1):
            L = t['levels'][lvl[n]]; c = L['cost']
            dust += c.get('Truegold Dust',0); days += L['hours']/24; lvl[n] += 1
            plan.append(('econ', n, lvl[n], c.get('Truegold Dust',0), L['hours']/24))
            progress = True
econ_dust, econ_days = dust, days
print(f"Phase 1 (all 7 economy nodes maxed): {econ_dust:.0f} dust, {econ_days:.1f} days\n")

# Phase 2: greedy by dust per weighted stat point.
while True:
    best = None
    for n, t in T.items():
        if n in ECON or lvl[n] >= t['max']: continue
        l = lvl[n] + 1
        if not reqs_ok(t, l): continue
        L = t['levels'][l-1]; c = L['cost']
        d = c.get('Truegold Dust', 0); ttc = c.get('Tempered Truegold', 0)
        v = stat_value(t)
        if v <= 0: v = 0.3
        score = d / v
        if best is None or score < best[0]: best = (score, n, l, d, L['hours']/24, ttc)
    if best is None: break
    score, n, l, d, dd, ttc = best
    if dust + d > DUST_BUDGET or days + dd > DAY_BUDGET or tt + ttc > TT_BUDGET: break
    dust += d; days += dd; tt += ttc; lvl[n] = l
    plan.append(('combat', n, l, d, dd))

# Summarise phase 2 as waves (group consecutive same-cost steps)
print("Phase 2 order (grouped):")
cur = None
for kind, n, l, d, dd in plan:
    if kind != 'combat': continue
    key = (d,)
    if cur is None or cur['d'] != d:
        if cur: print(f"  {cur['n']:3d} steps @ {cur['d']:3d} dust ({cur['sum']:5.0f} dust, {cur['days']:5.1f} d): {cur['first']} ... {cur['last']}")
        cur = dict(d=d, n=0, sum=0, days=0, first=f"{n} L{l}", last='')
    cur['n'] += 1; cur['sum'] += d; cur['days'] += dd; cur['last'] = f"{n} L{l}"
if cur: print(f"  {cur['n']:3d} steps @ {cur['d']:3d} dust ({cur['sum']:5.0f} dust, {cur['days']:5.1f} d): {cur['first']} ... {cur['last']}")
print(f"\nTOTAL: {dust:.0f} dust, {days:.1f} days, {tt:.0f} tempered truegold")
print("\nEnd state (non-zero):")
for n in T:
    if lvl[n]: print(f"  {n:26s} L{lvl[n]}")
