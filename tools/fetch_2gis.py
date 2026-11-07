#!/usr/bin/env python3
"""Исследовательская выгрузка организаций Семея из API 2ГИС (GET /3.0/items) в JSON. Запускать на ПК с интернетом.
Ключ берётся ТОЛЬКО из переменной окружения DGIS_KEY. В чат, в index.html и в репозиторий ключ не попадает.
PowerShell:  $env:DGIS_KEY = '<ключ>' ; python fetch_2gis.py 2gis_semey.json
Результат: черновик для проверки владельцем. В приложение не грузить, пока не проверены условия лицензии 2ГИС на хранение данных."""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request
URL = 'https://catalog.api.2gis.com/3.0/items'
POINT = '80.2667,50.4233'  # lon,lat центра Семея
RADIUS = 15000             # метры (до 50000 при наличии q)
PAGE_SIZE = 10             # демо-ключ 2ГИС принимает page_size от 1 до 10
FIELDS = 'items.point,items.address,items.rubrics,items.schedule'  # items.contact_groups (телефоны) нужно отдельное разрешение ключа
# группа -> поисковые фразы
QUERIES = {
 'Строительные материалы': ['строительные материалы', 'стройматериалы', 'цемент кирпич', 'строительный магазин', 'пиломатериалы'],
 'Отделочные материалы': ['плитка', 'обои', 'ламинат', 'гипсокартон', 'краски'],
 'Сантехника и электрика': ['сантехника', 'электротовары', 'светильники'],
 'Окна, двери, мебель': ['окна пластиковые', 'двери межкомнатные', 'мебель', 'шторы'],
 'Ремонт и строительство': ['ремонт квартир', 'строительная компания', 'отделочные работы', 'электромонтаж', 'сантехнические работы'],
 'Логистика': ['грузоперевозки', 'грузчики', 'переезд', 'транспортная компания', 'курьерская доставка'],
 'Недвижимость': ['риэлтор', 'агентство недвижимости'],
 'Кадровые агентства': ['кадровое агентство', 'подбор персонала'],
 'Прочие услуги': ['клининг', 'дезинфекция', 'юридические услуги', 'нотариус'],
}
def build_url(q, page, key, fields=True):
    p = {'q': q, 'point': POINT, 'radius': RADIUS, 'page': page, 'page_size': PAGE_SIZE, 'locale': 'ru_RU', 'key': key}
    if fields: p['fields'] = FIELDS
    return URL + '?' + urllib.parse.urlencode(p)
def parse(data, group, q):
    out = []
    for it in (data.get('result') or {}).get('items', []):
        pt = it.get('point') or {}
        if not it.get('name') or 'lat' not in pt: continue
        out.append({'id': '2gis-' + str(it.get('id')), 'name': it['name'], 'address': it.get('address_name') or '',
                    'rubrics': [r.get('name') for r in it.get('rubrics', []) if r.get('name')], 'lat': pt['lat'], 'lon': pt['lon'],
                    'group': group, 'query': q, 'source': '2ГИС', 'status': 'не проверено'})
    return out
def not_found(data): return (data.get('meta') or {}).get('code') == 404
def api_error(data):
    m = data.get('meta') or {}
    if m.get('code', 200) not in (200, 404): return 'код %s: %s' % (m.get('code'), (m.get('error') or {}).get('message') or m.get('error') or 'ошибка API')
    return ''
def total(data): return (data.get('result') or {}).get('total', 0)
FIELDS_ON = [True]
def call(q, page, key, fields=None):
    url = build_url(q, page, key, FIELDS_ON[0] if fields is None else fields)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'AlauConcierge-research/1.0'}), timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        try: return json.load(e)
        except Exception: return {'meta': {'code': e.code, 'error': {'message': e.reason}}}
def run(path, key, max_pages=5, pause=0.4):
    seen = {}
    for group, qs in QUERIES.items():
        for q in qs:
            for page in range(1, max_pages + 1):
                data = call(q, page, key)
                if not_found(data) and page == 1 and FIELDS_ON[0]:
                    d2 = call(q, page, key, fields=False)
                    if not not_found(d2):
                        FIELDS_ON[0] = False; data = d2
                        print('Примечание: с параметром fields 2ГИС ничего не вернул, дальше запрашиваю без него (будут координаты и адрес, возможно без рубрик и графика).')
                err = api_error(data)
                if err: sys.exit('Ошибка API 2ГИС, %s\nПроверьте ключ (нужен настоящий ключ, не слово ВАШ_КЛЮЧ) и права ключа на API поиска.' % err)
                items = parse(data, group, q)
                for i in items: seen.setdefault(i['id'], i)
                print('%-24s %-26s стр.%d: +%d (всего по запросу %s)' % (group, q, page, len(items), total(data)))
                time.sleep(pause)
                if len(data.get('result', {}).get('items', [])) < PAGE_SIZE: break
    res = sorted(seen.values(), key=lambda x: (x['group'], x['name'].lower()))
    json.dump(res, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('Уникальных организаций:', len(res), '->', path)
    if not res: print('Ни один запрос ничего не вернул (404 «Results not found»). Пришлите этот вывод целиком: подберём другие параметры (город вместо радиуса).')
if __name__ == '__main__':
    k = os.environ.get('DGIS_KEY')
    if k and k.upper().startswith('ВАШ'): sys.exit('В DGIS_KEY стоит слово-заглушка. Подставьте настоящий ключ 2ГИС вместо ВАШ_КЛЮЧ.')
    if not k: sys.exit('Задайте ключ: $env:DGIS_KEY = "<ключ>" (в чат его не присылайте)')
    run(sys.argv[1] if len(sys.argv) > 1 else '2gis_semey.json', k)
