import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'tools'))
import fetch_osm_suppliers as f
res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x) if not c else ''))
q = f.query()
ok('запрос с bbox Семея и тегом curtain', '50.33,80.1,50.5,80.45' in q and 'curtain' in q and q.endswith('out center tags;'), q[:120])
data = {'elements': [
 {'type': 'node', 'id': 1, 'lat': 50.42, 'lon': 80.26, 'tags': {'name': 'А', 'shop': 'curtain', 'addr:street': 'ул. Х', 'addr:housenumber': '3'}},
 {'type': 'way', 'id': 2, 'center': {'lat': 50.43, 'lon': 80.27}, 'tags': {'name': 'Б', 'shop': 'doityourself'}},
 {'type': 'node', 'id': 3, 'lat': 50.4, 'lon': 80.2, 'tags': {'shop': 'curtain'}},
 {'type': 'node', 'id': 4, 'lat': 50.4, 'lon': 80.2, 'tags': {'name': 'В', 'shop': 'bakery'}}]}
r = f.parse(data)
ok('без названия и чужие метки отброшены', [x['name'] for x in r] == ['А', 'Б'], r)
ok('адрес собран', r[0]['address'] == 'ул. Х, 3' and r[0]['cats'] == ['m-textile'])
ok('doityourself в нескольких категориях', set(r[1]['cats']) == {'m-finish', 'm-plumb', 'm-hardware'}, r[1]['cats'])
ok('центр области берётся из center', r[1]['lat'] == 50.43)
ok('статус «не проверено», источник OSM', all(x['status'] == 'не проверено' and x['source'] == 'OpenStreetMap' for x in r))
# теги скрипта совпадают с index.html
import re
html = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').read_text(encoding='utf-8')
mine = {}
for m in re.finditer(r"id: '([ms]-[a-z-]+)', grp.*?osm: (\[\[.*?\]\])", html):
    mine[m.group(1)] = [tuple(x) for x in eval(m.group(2).replace('[[', '[(').replace(']]', ')]').replace('],[', '),(').replace('], [', '), ('))]
ok('теги в скрипте совпадают с index.html', mine == f.CATS, set(mine) ^ set(f.CATS))
print('TOTAL', len(res), 'FAILED', res.count(False)); sys.exit(1 if False in res else 0)
