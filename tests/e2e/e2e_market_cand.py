import os
import sys
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    pg = b.new_context(viewport={'width': 390, 'height': 844}).new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('file://' + os.environ.get('ALAU_INDEX', '/home/claude/alau-resident-/index.html')); pg.evaluate(SEED); pg.reload(); g = lambda js: pg.evaluate(js)
    # данные
    ok('кандидатов 26, проверенных 0', g("MARKET_CANDIDATES.length") == 26 and g("MARKET_PROVIDERS.length") == 0)
    ok('id уникальны', g("new Set(MARKET_CANDIDATES.map(c=>c.id)).size") == 26)
    bad = g("MARKET_CANDIDATES.filter(c=>!(c.id.startsWith('osm-')&&c.name&&c.cats.length&&c.cats.every(x=>MARKET_CATS.some(m=>m.id===x))&&c.lat>50.3&&c.lat<50.55&&c.lon>80.1&&c.lon<80.45)).map(c=>c.id)")
    ok('схема и координаты Семея', bad == [], bad)
    ok('телефонов в кандидатах нет', g("MARKET_CANDIDATES.every(c=>!('phone' in c))"))
    ok('мусора из OSM (ломбарды, страховые) нет', g("!MARKET_CANDIDATES.some(c=>/ломбард|страхов|трансойл/i.test(c.name))"))
    # вкладка «Карта»
    g("showScreen('screen-market')"); pg.click('#mk-tabs .chip:has-text("Карта")'); pg.wait_for_timeout(50)
    body = g("document.getElementById('mk-body').innerText")
    ok('на карте блок «Из OpenStreetMap, не проверены · 26»', 'Из OpenStreetMap, не проверены · 26' in body, body[:200])
    ok('кандидаты не под заголовком «Проверенные»', 'Проверенные поставщики' not in body and 'Проверенных поставщиков на карте пока нет' in body, body[:200])
    ok('26 карточек кандидатов', g("document.querySelectorAll('#mk-body .mk-cand').length") == 26)
    pg.click('#mk-body .mk-cand:has-text("Центр Кровли") .tkt-btn'); pg.wait_for_timeout(50)
    src = g("document.getElementById('mk-frame').src")
    ok('«На карте» у кандидата ставит маркер', 'marker=50.413206%2C80.25126' in src, src)
    pg.fill('#mk-search', 'кровл'); pg.wait_for_timeout(50)
    ok('поиск находит кандидата', g("document.querySelectorAll('#mk-body .mk-cand').length") == 1)
    pg.fill('#mk-search', '')
    # окно категории
    g("mkOpen('m-textile')"); t = g("document.getElementById('mk-body2').innerText")
    ok('категория «Текстиль»: 3 кандидата с пометкой', 'Из OpenStreetMap, не проверены' in t and all(n in t for n in ['Евротекстиль', 'Ткани Лидер', 'Шторы Ай-дана']), t)
    ok('в категории по-прежнему нет проверенных', 'Проверенных поставщиков в этой категории пока нет' in t and 'Проверенные поставщики' not in t)
    g("mkOpen('s-clean')"); t = g("document.getElementById('mk-body2').innerText")
    ok('категория без кандидатов: блока нет', 'OpenStreetMap' not in t)
    g("mkOpen('s-legal')"); ok('нотариусы без адреса: «адрес не указан»', 'адрес не указан' in g("document.getElementById('mk-body2').innerText"))
    # помощник
    g("mkClose(); showScreen('screen-chat'); switchChatTab('bot')")
    pg.fill('#bot-text', 'ищу шторы'); pg.press('#bot-text', 'Enter'); pg.wait_for_timeout(60)
    t = g("(()=>{const l=chatBox().box.bot; return l[l.length-1].text})()")
    ok('помощник перечисляет кандидатов как непроверенных', 'Из OpenStreetMap (не проверены)' in t and 'Евротекстиль' in t, t)
    ok('нет ошибок страницы', not errs, errs[:2])
    b.close()
bad = res.count(False); print('TOTAL', len(res), 'FAILED', bad); sys.exit(1 if bad else 0)
