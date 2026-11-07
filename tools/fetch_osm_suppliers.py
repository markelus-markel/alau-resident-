#!/usr/bin/env python3
"""Выгрузка магазинов и мастеров Семея из OpenStreetMap (Overpass) в JSON.
Запускать на компьютере с доступом в интернет: python fetch_osm_suppliers.py osm_semey.json
Данные открытые, личных данных в запросе нет. Результат НЕ проверен: это черновик для реестра."""
import json, sys, urllib.request, urllib.parse
BBOX = (50.33, 80.10, 50.50, 80.45)  # юг, запад, север, восток: Семей с окраинами
URL = 'https://overpass-api.de/api/interpreter'
# Теги категорий. Копия osm-полей MARKET_CATS в index.html: при правке там обновлять и здесь.
CATS = {
 'm-build': [('shop', 'building_materials')], 'm-finish': [('shop', 'doityourself|tiles|flooring|wallpaper|building_materials')],
 'm-paint': [('shop', 'paint')], 'm-plumb': [('shop', 'doityourself|bathroom_furnishing|plumbing')],
 'm-electro': [('shop', 'electrical')], 'm-security': [('shop', 'security')],
 'm-furniture': [('shop', 'furniture|kitchen|bed')], 'm-hardware': [('shop', 'hardware|doityourself')],
 'm-glazing': [('craft', 'glaziery')], 'm-textile': [('shop', 'curtain|fabric|textile|carpet')],
 's-design-project': [('office', 'architect')], 's-plumb': [('craft', 'plumber')], 's-electro': [('craft', 'electrician')],
 's-finish': [('craft', 'painter|plasterer|tiler|carpenter')], 's-build': [('craft', 'builder|construction')],
 's-clean': [('shop', 'dry_cleaning|laundry'), ('office', 'cleaning')], 's-realty': [('office', 'estate_agent')],
 's-legal': [('office', 'lawyer|notary')],
}
def query():
    b = ','.join(map(str, BBOX))
    parts = sorted({'nwr["%s"~"^(%s)$"](%s);' % (k, v, b) for tags in CATS.values() for k, v in tags})
    return '[out:json][timeout:60];(' + ''.join(parts) + ');out center tags;'
def cats_of(tags):
    import re
    return [c for c, ts in CATS.items() if any(k in tags and re.fullmatch(v, tags[k]) for k, v in ts)]
def parse(data):
    out = []
    for e in data.get('elements', []):
        t = e.get('tags', {}); lat = e.get('lat', (e.get('center') or {}).get('lat')); lon = e.get('lon', (e.get('center') or {}).get('lon'))
        if not t.get('name') or lat is None or lon is None: continue
        cats = cats_of(t)
        if not cats: continue
        out.append({'id': 'osm-%s-%s' % (e['type'], e['id']), 'name': t['name'], 'cats': cats,
                    'address': ', '.join(x for x in [t.get('addr:street'), t.get('addr:housenumber')] if x),
                    'phone': t.get('phone') or t.get('contact:phone') or '', 'website': t.get('website') or t.get('contact:website') or '',
                    'hours': t.get('opening_hours', ''), 'lat': round(lat, 6), 'lon': round(lon, 6),
                    'source': 'OpenStreetMap', 'status': 'не проверено'})
    return sorted(out, key=lambda x: x['name'].lower())
def main(path):
    req = urllib.request.Request(URL, data=('data=' + urllib.parse.quote(query())).encode(), headers={'User-Agent': 'AlauConcierge-fetch/1.0'})
    with urllib.request.urlopen(req, timeout=90) as r: data = json.load(r)
    items = parse(data)
    json.dump(items, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('Записей:', len(items), '->', path)
    for c in CATS: print('  %-18s %d' % (c, sum(c in i['cats'] for i in items)))
if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'osm_semey.json')
