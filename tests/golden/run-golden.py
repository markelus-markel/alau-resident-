#!/usr/bin/env python3
"""Золотой набор фраз: точность определения ситуации (sitRank в приложении).
Использование: python3 tests/golden/run-golden.py [--lang ru] [--verbose]"""
import json, os, sys, pathlib
from playwright.sync_api import sync_playwright
root = pathlib.Path(__file__).resolve().parent.parent.parent
index = os.environ.get('ALAU_INDEX', str(root / 'index.html'))
data = json.load(open(root / 'tests' / 'golden' / 'phrases-ru.json', encoding='utf-8'))
reg = json.load(open(root / 'registry' / 'situations.json', encoding='utf-8'))
danger = {s['id'] for s in reg['situations'] if s['level'] == 'emergency'}
verbose = '--verbose' in sys.argv
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    pg = b.new_page(); pg.goto('file://' + index)
    ranked = pg.evaluate("t => Object.fromEntries(t.map(x => [x, sitRank(x).slice(0,3).map(s => s.id)]))", [c['text'] for c in data['cases']])
    b.close()
n = len(data['cases']); top1 = top3 = 0; dn = dhit = 0; miss = []
for c in data['cases']:
    r = ranked[c['text']]
    ok1 = bool(r) and r[0] == c['expect']; ok3 = c['expect'] in r
    top1 += ok1; top3 += ok3
    if c['expect'] in danger:
        dn += 1; dhit += ok1
    if not ok1: miss.append((c['text'], c['expect'], r))
print(f'Фраз: {n} | top-1: {top1/n:.0%} ({top1}) | top-3: {top3/n:.0%} ({top3}) | опасные recall: {dhit}/{dn}')
for t, e, r in miss:
    if verbose or e in danger: print(f'  промах: «{t}» ожидали {e}, получили {r}')
fail = (top1/n < 0.90) or (top3/n < 0.98) or dhit < dn
print('ПОРОГИ (top-1 ≥ 90 %, top-3 ≥ 98 %, опасные 100 %):', 'НЕ выполнены' if fail else 'выполнены')
sys.exit(1 if fail else 0)
