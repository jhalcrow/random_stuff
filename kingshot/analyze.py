#!/usr/bin/env python3
"""Focused comparisons on top of run.py: candidate trios vs community meta, ratio search for the
chosen trios, and which reinforcement (joiner) skills to request for garrison defense.

  PROC_SCALE=0.75 python3 kingshot/analyze.py
"""
import os
from run import (eval_attack, eval_defense, summarize, ratio_search, DEF_PANEL, ATT_PANEL)
from sim import ATTACK_JOINERS, DEFENSE_JOINERS

ATTACK_TRIOS = {
    'sim pick A   Charles / Ava / Wee & Woo': ['Charles', 'Ava', 'Wee & Woo'],
    'sim pick B   Charles / Sophia / Wee & Woo': ['Charles', 'Sophia', 'Wee & Woo'],
    'sim pick C   Charles / Sophia / Marlin': ['Charles', 'Sophia', 'Marlin'],
    'sim pick D   Charles / Ava / Yang': ['Charles', 'Ava', 'Yang'],
    'sim pick E   Charles / Sophia / Yang': ['Charles', 'Sophia', 'Yang'],
    'meta Gen7    Amadeus / Ava / Wee & Woo': ['Amadeus', 'Ava', 'Wee & Woo'],
    'meta Gen6    Triton / Thrud / Yang': ['Triton', 'Thrud', 'Yang'],
    'meta Gen5    Long Fei / Thrud / Rosa': ['Long Fei', 'Thrud', 'Rosa'],
    'meta Gen4    Amadeus / Petra / Rosa': ['Amadeus', 'Petra', 'Rosa'],
}
DEFENSE_TRIOS = {
    'sim pick A   Charles / Sophia / Wee & Woo': ['Charles', 'Sophia', 'Wee & Woo'],
    'sim pick B   Alcar / Sophia / Wee & Woo': ['Alcar', 'Sophia', 'Wee & Woo'],
    'sim pick C   Charles / Ava / Wee & Woo': ['Charles', 'Ava', 'Wee & Woo'],
    'sim pick D   Long Fei / Sophia / Wee & Woo': ['Long Fei', 'Sophia', 'Wee & Woo'],
    'sim pick E   Charles / Jabel / Wee & Woo': ['Charles', 'Jabel', 'Wee & Woo'],
    'meta Gen6    Triton / Sophia / Vivian': ['Triton', 'Sophia', 'Vivian'],
    'meta Gen5    Alcar / Margot / Vivian': ['Alcar', 'Margot', 'Vivian'],
    'meta Gen4    Alcar / Margot / Jaeger': ['Alcar', 'Margot', 'Jaeger'],
}
JOINER_SETS = {
    'sim default   Charles / Eric / Triton / Gordon': ['Charles', 'Eric', 'Triton', 'Gordon'],
    'community     Saul / Gordon / Howard / Fahd': ['Saul', 'Gordon', 'Howard', 'Fahd'],
    'four Saul': ['Saul'] * 4,
    'four Gordon': ['Gordon'] * 4,
    'Charles / Eric / Howard / Fahd': ['Charles', 'Eric', 'Howard', 'Fahd'],
    'Charles / Eric / Saul / Gordon': ['Charles', 'Eric', 'Saul', 'Gordon'],
    'no reinforcements': [],
}

print(f"PROC_SCALE={os.environ.get('PROC_SCALE', '1.0')}  (weight on chance-based skill expected values)")
print('\n=== CASTLE ATTACK (rally leader, 50/20/30, joiners %s) ===' % '/'.join(ATTACK_JOINERS))
print('  trio                                      geo-mean kill ratio   wins   per enemy lineup')
for label, trio in ATTACK_TRIOS.items():
    res = eval_attack(trio)
    g, w = summarize(res)
    print(f'  {label:42s} {g:6.3f}   {w}/4   ' + ' '.join(f'{r[0]:5.2f}' for r in res))
print('  enemy garrisons: ' + ' | '.join('/'.join(p) for p in DEF_PANEL))

print('\n=== GARRISON DEFENSE (garrison leader, 60/15/25, reinforcement skills %s) ===' % '/'.join(DEFENSE_JOINERS))
print('  trio                                      geo-mean kill ratio   wins   per enemy lineup')
for label, trio in DEFENSE_TRIOS.items():
    res = eval_defense(trio)
    g, w = summarize(res)
    print(f'  {label:42s} {g:6.3f}   {w}/4   ' + ' '.join(f'{r[0]:5.2f}' for r in res))
print('  enemy rallies: ' + ' | '.join('/'.join(p) for p in ATT_PANEL))

print('\n=== Which reinforcement first-skills to ask for (garrison Charles / Sophia / Wee & Woo) ===')
for label, js in JOINER_SETS.items():
    g, w = summarize(eval_defense(['Charles', 'Sophia', 'Wee & Woo'], joiners=js))
    print(f'  {label:48s} {g:6.3f}   {w}/4')

ratio_search(eval_attack, ['Charles', 'Ava', 'Wee & Woo'], 'CASTLE ATTACK rally')
ratio_search(eval_attack, ['Charles', 'Sophia', 'Wee & Woo'], 'CASTLE ATTACK rally')
ratio_search(eval_attack, ['Charles', 'Sophia', 'Marlin'], 'CASTLE ATTACK rally')
ratio_search(eval_defense, ['Charles', 'Sophia', 'Wee & Woo'], 'GARRISON DEFENSE')
ratio_search(eval_defense, ['Charles', 'Ava', 'Wee & Woo'], 'GARRISON DEFENSE')
