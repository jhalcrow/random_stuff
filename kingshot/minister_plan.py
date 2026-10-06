#!/usr/bin/env python3
"""Advanced (Truegold) research plan for a research-speed buff window.

State read off the player's War Academy screens, 2026-10-06: tier I maxed, Truegold Provisions I
maxed, tier II all 9/10, Provisions II 9/10, tier III 6/10 (cavalry defense and infantry health
7/10), Generation Truegold I 9/10, tier IV 0/10.  (The block under Provisions I is tier II per
tree.json's requirements, not tier I.)  Balances: 6,438 Dust, 19,665 Truegold, 1,271 Tempered.

Value per +3% level = simulated combined kill-ratio gain (gear.py rally + garrison scenarios,
60/40/0 compositions) from +9% on that stat, divided by 3.  Gate levels carry their own (small)
value.  Greedy by value per Dust, buying any prerequisite levels as part of the bundle.
"""
import json, sys
T = json.load(open('tree.json'))
VAL = {('cav','lethality'):1.97/3, ('cav','attack'):1.54/3, ('inf','health'):0.68/3, ('inf','defense'):0.63/3,
       ('inf','lethality'):0.05/3, ('inf','attack'):0.05/3, ('cav','health'):0.04/3, ('cav','defense'):0.03/3}
NAMES = {'inf':['Auric Mauls','Auric Plating','Auric Destruction','Golden Shield'],
         'cav':['Truegold Lances','Golden Mantle','True Shock','Golden Horseshoes'],
         'arch':['Auric Arrowheads','Auric Pauldrons','Golden Bows','Auric Bracers']}
STATS = ['attack','defense','lethality','health']
TIERS = ['II','III','IV']
cur = {}
for typ, ns in NAMES.items():
    for i, n in enumerate(ns):
        cur[f'{n} II'] = 9; cur[f'{n} III'] = 6; cur[f'{n} IV'] = 0
cur['Golden Mantle III'] = 7; cur['Golden Shield III'] = 7
GEN1 = 9   # Generation Truegold I level (tier IV gate), Provisions I = 10
node = {n['name']: n for n in T}
meta = {f'{n} {tr}': (typ, STATS[i], tr) for typ, ns in NAMES.items() for i, n in enumerate(ns) for tr in TIERS}

def need(name, lv):
    """Levels that must exist before `name` can go to `lv`: predecessor in its column, at the band
    threshold (1 for L1-2, 3 for L3-5, 6 for L6-9, 10 for L10)."""
    typ, stat, tr = meta[name]
    band = 1 if lv <= 2 else 3 if lv <= 5 else 6 if lv <= 9 else 10
    if tr == 'IV' and band > GEN1:
        return None                                   # Generation Truegold I gate
    i = STATS.index(stat)
    return None if i == 0 else (f'{NAMES[typ][i-1]} {tr}', band)

def bundle(name, state):
    """Cheapest list of (node, level) purchases that ends with name -> state[name]+1."""
    lv = state[name] + 1
    if lv > 10: return None
    out, s = [], dict(state)
    def get(nm, target):
        while s[nm] < target:
            req = need(nm, s[nm] + 1)
            if req is None and meta[nm][2] == 'IV' and (1 if s[nm]+1 <= 2 else 3 if s[nm]+1 <= 5 else 6 if s[nm]+1 <= 9 else 10) > GEN1:
                raise ValueError
            if req: get(*req)
            s[nm] += 1; out.append((nm, s[nm]))
    try: get(name, lv)
    except ValueError: return None
    return out

def cost(nm, lv):
    c = node[nm]['levels'][lv-1]; return c['cost']['Truegold Dust'], c['cost'].get('Tempered Truegold', 0), c['hours']

def plan(budget):
    state, spent, temp, hrs, val, steps = dict(cur), 0, 0, 0, 0.0, []
    while True:
        best = None
        for nm in meta:
            if meta[nm][0] == 'arch': continue
            b = bundle(nm, state)
            if not b: continue
            d = sum(cost(*x)[0] for x in b); v = sum(VAL.get(meta[x[0]][:2], 0) for x in b)
            if spent + d > budget: continue
            if best is None or v/d > best[0]: best = (v/d, b, d, v)
        if best is None: break
        for x in best[1]:
            dd, tt, hh = cost(*x); spent += dd; temp += tt; hrs += hh; state[x[0]] = x[1]
            val += VAL.get(meta[x[0]][:2], 0)
            steps.append((x[0], x[1], dd, tt, hh, spent, VAL.get(meta[x[0]][:2], 0)))
    return steps, spent, temp, hrs, val

if __name__ == '__main__':
    budget = int(sys.argv[1]) if len(sys.argv) > 1 else 6438
    steps, spent, temp, hrs, val = plan(budget)
    for nm, lv, d, t, h, cum, v in steps:
        print(f'  {nm:24s} -> L{lv:<2d}  {d:4d} Dust  {t} Temp  {h:3d}h   cum {cum:6,d}   {"value" if v > 0.05 else "gate "} {v:.3f}')
    print(f'TOTAL budget {budget:,}: {len(steps)} levels, {spent:,} Dust, {temp} Tempered, {hrs:,} base hours ({hrs/24:.0f} days), value {val:.2f}')
