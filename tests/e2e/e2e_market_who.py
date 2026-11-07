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
    g("showScreen('screen-chat'); switchChatTab('bot')")
    last = lambda: g("(()=>{const l=chatBox().box.bot; return l[l.length-1]})()")
    acts = lambda: [a['do'] + ':' + str(a.get('arg')) for a in (last().get('actions') or [])]
    ask = lambda q: (pg.fill('#bot-text', q), pg.press('#bot-text', 'Enter'), pg.wait_for_timeout(50))
    # человек ищет исполнителя
    for q, cat in [('найди мне того кто починит кран', 's-plumb'), ('найди мастера починить кран', 's-plumb'), ('кто починит кран', 's-plumb'),
                   ('найди кто установит смеситель', 's-plumb'), ('найди мне того кто поклеит обои', 's-finish'), ('кто сделает ремонт', 's-repair')]:
        ask(q); ok('«%s» -> исполнитель %s' % (q, cat), 'mk-near:' + cat in acts() and 'mk-req:' + cat in acts(), (last()['text'][:60], acts()))
    ask('нужны обои'); ok('«нужны обои» по-прежнему материалы', 'mk-near:m-finish' in acts(), acts())
    # аварии не перехватываются
    ask('течёт кран'); ok('«течёт кран» остаётся ситуацией (протечка)', 'Протечка' in last()['text'] and not any(a.startswith('mk-') for a in acts()), last()['text'][:60])
    ask('пахнет газом'); ok('газ остаётся ситуацией', 'газ' in last()['text'].lower() and not any(a.startswith('mk-') for a in acts()), last()['text'][:60])
    # записи из открытых источников (OSM) жильцам не показываются: они не на платформе
    ask('ищу шторы'); ok('помощник не называет магазины из OSM', not any(n in last()['text'] for n in ['Евротекстиль', 'Ткани Лидер', 'Шторы Ай-дана']) and 'не проверены' not in last()['text'], last()['text'])
    g("showScreen('screen-market'); mkOpen('m-textile')"); t = g("document.getElementById('mk-body2').innerText")
    ok('в окне категории нет блока OSM', 'Евротекстиль' not in t and 'OpenStreetMap' not in t, t)
    g("mkClose()"); pg.click('#mk-tabs .chip:has-text("Карта")'); pg.wait_for_timeout(50)
    ok('на карте нет кандидатов OSM', g("document.querySelectorAll('#mk-body .mk-prov').length") == 0 and 'не проверены' not in g("document.getElementById('mk-body').innerText"))
    g("showScreen('screen-chat'); switchChatTab('bot')")
    # аккаунт поставщика обязателен для выдачи
    g("MARKET_PROVIDERS.push({id:'p1',cats:['s-plumb'],name:'Без аккаунта',desc:'',address:'ул. А',lat:50.42,lon:80.26})")
    g("MARKET_PROVIDERS.push({id:'p2',acc:'acc-2',cats:['s-plumb'],name:'С аккаунтом',desc:'',address:'ул. Б',lat:50.43,lon:80.27})")
    ask('кто починит кран'); t = last()['text']
    ok('в ответе помощника только исполнитель с аккаунтом', 'С аккаунтом' in t and 'Без аккаунта' not in t, t)
    g("showScreen('screen-market'); mkOpen('s-plumb')"); t = g("document.getElementById('mk-body2').innerText")
    ok('в окне категории только с аккаунтом', 'С аккаунтом' in t and 'Без аккаунта' not in t, t)
    pg.click('#mk-tabs .chip:has-text("Карта")') if g("!!document.querySelector('#mk-modal.open')") is False else (g("mkClose()"), pg.click('#mk-tabs .chip:has-text("Карта")'))
    pg.wait_for_timeout(50); t = g("document.getElementById('mk-body').innerText")
    ok('на карте только с аккаунтом', 'С аккаунтом' in t and 'Без аккаунта' not in t, t)
    pg.fill('#mk-search', 'без аккаунта'); pg.wait_for_timeout(50)
    ok('поиск не находит запись без аккаунта', 'Без аккаунта' not in g("document.getElementById('mk-body').innerText"))
    ok('нет ошибок страницы', not errs, errs[:2])
    b.close()
bad = res.count(False); print('TOTAL', len(res), 'FAILED', bad); sys.exit(1 if bad else 0)
