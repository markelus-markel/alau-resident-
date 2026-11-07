#!/usr/bin/env python3
"""Проверка списка приглашений registry/onboarding-osm.json (кандидаты OSM, жильцам не показываются)."""
import json, pathlib, re, sys
root = pathlib.Path(__file__).resolve().parent.parent
d = json.loads((root / 'registry' / 'onboarding-osm.json').read_text(encoding='utf-8'))
html = (root / 'index.html').read_text(encoding='utf-8')
cats = set(re.findall(r"id: '([ms]-[a-z-]+)', grp:", html))
res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x) if not c else ''))
it = d['items']
ok('26 записей', len(it) == 26, len(it))
ok('id уникальны и начинаются с osm-', len({i['id'] for i in it}) == len(it) and all(i['id'].startswith('osm-') for i in it))
ok('категории существуют в маркетплейсе', all(c in cats for i in it for c in i['cats']), sorted({c for i in it for c in i['cats']} - cats))
ok('координаты в границах Семея', all(50.3 < i['lat'] < 50.55 and 80.1 < i['lon'] < 80.45 for i in it))
ok('телефонов нет', all('phone' not in i for i in it))
ok('мусора из OSM (ломбарды, страховые, АЗС) нет', not any(re.search('ломбард|страхов|трансойл', i['name'], re.I) for i in it))
ok('статус «не проверено», источник OSM', d['status'] == 'не проверено' and d['source'] == 'OpenStreetMap')
ok('приложение не загружает список (жильцам не показывается)', 'onboarding-osm' not in html and 'MARKET_CANDIDATES' not in html)
print('TOTAL', len(res), 'FAILED', res.count(False)); sys.exit(1 if False in res else 0)
