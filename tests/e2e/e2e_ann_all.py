import os
import sys
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');lsSet(LS_WELCOME,{'77011234567':1});}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'index.html'))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    car = g("[...document.querySelectorAll('#ann-carousel .ann-card-module .amc-title')].map(e=>e.textContent.trim())")
    pg.click('text=Все →'); pg.wait_for_timeout(150)
    ok('«Все →» opens the announcements screen', g("document.querySelector('.screen.active').id") == 'screen-announcements')
    full = g("[...document.querySelectorAll('#screen-announcements .ann-full-card .ann-full-title')].map(e=>e.textContent.trim())")
    ok('the full list has a card for every carousel card', len(full) == len(car) == 4, (car, full))
    ok('the full list names the same things in the same order (situations, management, chat, repair)', [x[:6] for x in full] == [x[:6] for x in ['Если случилось: типичные ситуации', 'Управление домом', 'Общедомовой чат МКД', 'Заявка мастеру']], full)
    pg.screenshot(path=S + '/ann_all.png')
    pg.click('#mgmt-card-all'); ok('«Управление домом» opens from the full list', g("document.getElementById('mgmt-modal').classList.contains('open')")); g("mgmtClose()")
    pg.click('#repair-card-all'); pg.wait_for_timeout(200)
    ok('«Заявка мастеру» opens the same request screen as the carousel card', g("document.querySelector('.screen.active').id") == 'screen-module-voice' or g("document.getElementById('mv-title-text').textContent").startswith('🔧') , g("document.querySelector('.screen.active').id + ' | ' + document.getElementById('mv-title-text').textContent"))
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
