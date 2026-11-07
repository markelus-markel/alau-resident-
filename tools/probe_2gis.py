#!/usr/bin/env python3
"""Диагностика ключа 2ГИС: пробует несколько вариантов запроса и печатает код ответа. Ключ только из DGIS_KEY, в вывод не попадает.
PowerShell:  $env:DGIS_KEY = '<ключ>' ; python probe_2gis.py"""
import json, os, sys, urllib.error, urllib.parse, urllib.request
BASE = 'https://catalog.api.2gis.com/3.0/'
CITY = '70030076220469602'  # Семей (получен прошлой диагностикой)
VARIANTS = [
 ('city_id + q=магазин', 'items', {'q': 'магазин', 'city_id': CITY}),
 ('city_id + q=магазин, type=branch', 'items', {'q': 'магазин', 'city_id': CITY, 'type': 'branch'}),
 ('city_id + q=строительные материалы', 'items', {'q': 'строительные материалы', 'city_id': CITY, 'type': 'branch'}),
 ('q=Семей магазин, type=branch', 'items', {'q': 'Семей магазин', 'type': 'branch'}),
 ('city_id + q=риэлтор', 'items', {'q': 'риэлтор', 'city_id': CITY, 'type': 'branch'}),
 ('city_id + fields (адрес, точка)', 'items', {'q': 'магазин', 'city_id': CITY, 'type': 'branch', 'fields': 'items.point,items.address'}),
 ('city_id + q=аптека (контроль)', 'items', {'q': 'аптека', 'city_id': CITY, 'type': 'branch'}),
 ('geocode: тип (что вернёт по точке)', 'items/geocode', {'lon': '80.2667', 'lat': '50.4233', 'type': 'building'}),
]
def probe(key):
    for title, path, params in VARIANTS:
        url = BASE + path + '?' + urllib.parse.urlencode(dict(params, key=key, locale='ru_RU', page_size=5) if path.startswith('items') and path != 'items/geocode' else dict(params, key=key, locale='ru_RU'))
        try:
            with urllib.request.urlopen(url, timeout=40) as r: d = json.load(r)
        except urllib.error.HTTPError as e:
            try: d = json.load(e)
            except Exception: d = {'meta': {'code': e.code}}
        m = d.get('meta') or {}; res = d.get('result') or {}
        its = res.get('items', [])
        names = '; '.join('%s [%s] %s' % (i.get('name'), i.get('id'), i.get('type', '')) for i in its[:3])
        print('%-34s код %s %s | всего %s | %s' % (title, m.get('code'), (m.get('error') or {}).get('message', ''), res.get('total', '-'), names))
if __name__ == '__main__':
    k = os.environ.get('DGIS_KEY') or sys.exit('Задайте $env:DGIS_KEY')
    probe(k)
