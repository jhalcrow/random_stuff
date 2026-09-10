#!/usr/bin/env python3
"""Convert a planner end state into stat gains and score it in the battle simulator."""
import copy, re, subprocess, statistics, sys
from sim import Side, USER_STATS, TYPES, battle, ratio_troops, score, ATTACK_JOINERS, DEFENSE_JOINERS

# tech name -> (troop type, stat).  Each level is +3%.
MAP = {'Auric Mauls':('inf','attack'), 'Truegold Lances':('cav','attack'), 'Auric Arrowheads':('arch','attack'),
       'Auric Plating':('inf','defense'), 'Golden Mantle':('cav','defense'), 'Auric Pauldrons':('arch','defense'),
       'Auric Destruction':('inf','lethality'), 'True Shock':('cav','lethality'), 'Golden Bows':('arch','lethality'),
       'Golden Shield':('inf','health'), 'Golden Horseshoes':('cav','health'), 'Auric Bracers':('arch','health')}

def parse(args):
    out = subprocess.run([sys.executable,'plan.py']+args, capture_output=True, text=True).stdout
    tail = out[out.index('End state'):]
    gains = {t:{k:0.0 for k in ('attack','defense','lethality','health')} for t in TYPES}
    for line in tail.split('\n')[1:]:
        m = re.match(r'\s+(.+?)\s+L(\d+)$', line)
        if not m: continue
        name, lv = m.group(1).strip(), int(m.group(2))
        base = re.sub(r'\s+(I{1,3}|IV|V|VI)$','',name)
        if base in MAP:
            t,k = MAP[base]; gains[t][k] += 3.0*lv
    return gains, out

def with_gains(g):
    s = copy.deepcopy(USER_STATS)
    for t in TYPES:
        for k,v in g[t].items(): s[t][k] += v
    return s

enemy = {t:{k:v*0.9 for k,v in USER_STATS[t].items()} for t in TYPES}
DEF_PANEL=[['Charles','Sophia','Wee & Woo'],['Alcar','Margot','Vivian'],['Triton','Sophia','Vivian'],['Charles','Margot','Wee & Woo']]
ATT_PANEL=[['Amadeus','Ava','Yang'],['Triton','Thrud','Yang'],['Charles','Ava','Wee & Woo'],['Charles','Sophia','Yang']]
R=1_900_000
def atk(my):
    return statistics.geometric_mean([score(battle(
        Side('A',my,ratio_troops(R,60,40,0),heroes=['Charles','Sophia','Yang'],role='rally',joiners=ATTACK_JOINERS),
        Side('D',enemy,ratio_troops(R,60,15,25),heroes=d,role='garrison',joiners=DEFENSE_JOINERS)),'A') for d in DEF_PANEL])
def dfn(my):
    return statistics.geometric_mean([score(battle(
        Side('A',enemy,ratio_troops(R,*((55,45,0) if 'Sophia' in a else (50,20,30))),heroes=a,role='rally',joiners=ATTACK_JOINERS),
        Side('D',my,ratio_troops(R,60,40,0),heroes=['Charles','Sophia','Wee & Woo'],role='garrison',joiners=DEFENSE_JOINERS)),'D') for a in ATT_PANEL])

b_a, b_d = atk(USER_STATS), dfn(USER_STATS)
print(f'baseline (no advanced research): attack {b_a:.3f}  defense {b_d:.3f}\n')
for label, args in [('A  dust only 16651, 400d',   ['8','16651','400','1068']),
                    ('B  topped up, 400d cap',     ['8','34463','400','1068']),
                    ('C  topped up, 490d',         ['8','34463','490','1068'])]:
    g, out = parse(args)
    tot = re.search(r'^TOTAL: (\d+) dust, ([\d.]+) days, (\d+) tempered', out, re.M)
    s = with_gains(g)
    ga, gd = atk(s)/b_a-1, dfn(s)/b_d-1
    stat = ' '.join(f'{t}+{g[t]["lethality"]:.0f}/{g[t]["health"]:.0f}L/H' for t in TYPES)
    print(f'{label}: dust {tot.group(1)}  days {tot.group(2)}  TTG {tot.group(3)}')
    print(f'    attack kill ratio {ga*100:+5.1f}%   defense {gd*100:+5.1f}%   ({stat})')
