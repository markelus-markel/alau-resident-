import json
import os
import sys
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
DATA = {'elements': [
    {'type': 'node', 'lat': 50.4300, 'lon': 80.2700, 'tags': {'name': 'Дальний <b>магазин</b>', 'shop': 'curtain', 'addr:street': 'ул. Дальняя', 'addr:housenumber': '5'}},
    {'type': 'way', 'center': {'lat': 50.4240, 'lon': 80.2670}, 'tags': {'name': 'Ближний магазин', 'shop': 'curtain', 'phone': '+7 000 000 00 00'}},
    {'type': 'node', 'lat': 50.4235, 'lon': 80.2668, 'tags': {'shop': 'curtain'}}]}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    calls = []; mode = {'v': 'ok'}
    def handler(route):
        calls.append(route.request.post_data or '')
        if mode['v'] == 'ok': route.fulfill(status=200, content_type='application/json', body=json.dumps(DATA))
        elif mode['v'] == 'empty': route.fulfill(status=200, content_type='application/json', body='{"elements":[]}')
        else: route.fulfill(status=429, body='busy')
    pg.route('**/overpass-api.de/**', handler)
    pg.goto('file://' + os.environ.get('ALAU_INDEX', '/home/claude/alau-resident-/index.html')); pg.evaluate(SEED); pg.reload(); g = lambda js: pg.evaluate(js)
    g("showScreen('screen-chat'); switchChatTab('bot')")
    last = lambda: g("(()=>{const l=chatBox().box.bot; return l[l.length-1]})()")
    acts = lambda: [a['do'] + ':' + str(a.get('arg')) for a in (last().get('actions') or [])]
    ask = lambda q: (pg.fill('#bot-text', q), pg.press('#bot-text', 'Enter'), pg.wait_for_timeout(50))
    ok('при открытии запросов в сеть нет', len(calls) == 0)
    ask('ищу шторы')
    ok('конкретный запрос «ищу шторы» -> Текстиль + «Рядом со мной»', 'Текстиль' in last()['text'] and 'mk-near:m-textile' in acts(), acts())
    ok('запрос в сеть не ушёл без нажатия', len(calls) == 0)
    pg.click('#bot-thread .tkt-btn:has-text("Рядом со мной") >> nth=-1'); pg.wait_for_timeout(300)
    ok('нажатие -> один запрос к Overpass', len(calls) == 1, calls)
    q = calls[0] if calls else ''
    ok('запрос содержит теги категории и радиус', 'curtain' in q and 'around%3A3000' in q.replace(':', '%3A') or 'around:3000' in q, q[:200])
    ok('без точки дома ищет от центра Семея', '50.4233' in __import__('urllib.parse').parse.unquote(q), q[:200])
    body = g("document.getElementById('mk-near').innerText")
    ok('отмечено: данные OpenStreetMap, не проверены', 'не проверены' in body and 'OpenStreetMap' in body, body)
    ok('точка дома не задана -> предупреждение', 'центра Семея' in body, body)
    names = g("[...document.querySelectorAll('#mk-near .mk-prov-name')].map(e=>e.textContent)")
    ok('записи без названия отброшены', len(names) == 2, names)
    ok('сортировка по расстоянию', names[:1] == ['Ближний магазин'], names)
    ok('HTML в названии экранирован', g("!document.querySelector('#mk-near b')"))
    ok('показано расстояние и адрес', ' м' in body and 'ул. Дальняя, 5' in body, body)
    # профиль с точкой дома
    g("(()=>{const u=lsGet(LS_USERS,{}); u['77011234567'].lat=50.45; u['77011234567'].lon=80.30; lsSet(LS_USERS,u);})()")
    mode['v'] = 'empty'; g("mkNearby('m-textile')"); pg.wait_for_timeout(300)
    ok('есть точка дома -> поиск от неё', '50.45' in __import__('urllib.parse').parse.unquote(calls[-1]), calls[-1][:200])
    body = g("document.getElementById('mk-near').innerText")
    ok('пустой ответ -> честное сообщение', 'ничего не найдено' in body, body)
    mode['v'] = 'err'; g("mkNearby('m-textile')"); pg.wait_for_timeout(300)
    ok('ошибка сети -> сообщение, без падения', 'Не удалось' in g("document.getElementById('mk-near').innerText"))
    # перевозка: нет меток OSM
    n = len(calls)
    g("showScreen('screen-chat'); switchChatTab('bot')"); ask('хочу перевезти мебель')
    ok('«хочу перевезти мебель» -> Перевозка мебели', 'Перевозка мебели' in last()['text'] and 'mk-near:s-furnmove' in acts(), last()['text'][:80])
    g("showScreen('screen-market'); mkOpen('s-furnmove'); mkNearby('s-furnmove')"); pg.wait_for_timeout(100)
    ok('для категории без меток запрос не отправляется', len(calls) == n and 'нет подходящих меток' in g("document.getElementById('mk-near').innerText"))
    g("showScreen('screen-chat'); switchChatTab('bot')"); ok('общий вопрос «маркетплейс» не ищет рядом', (ask('маркетплейс'), 'mk-near' not in ' '.join(acts()))[1])
    ok('нет ошибок страницы', not errs, errs[:2])
    b.close()
bad = res.count(False); print('TOTAL', len(res), 'FAILED', bad); sys.exit(1 if bad else 0)
