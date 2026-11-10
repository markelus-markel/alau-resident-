import os
import sys
import json
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'index.html'))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='ru-RU', timezone_id='Asia/Qyzylorda')
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time='2026-11-10T09:30:00+05:00')
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    txt = lambda: (g("document.getElementById('home-cal-wd').textContent"), g("document.getElementById('home-cal-day').textContent"))
    ok('shows today: Tuesday 10 Nov', txt() == ('📅 вт', '10 нояб'), txt())
    ok('accessible label has the full date', 'Календарь дома' in g("document.getElementById('home-cal').getAttribute('aria-label')") and '10 ноября 2026' in g("document.getElementById('home-cal').getAttribute('aria-label')"), g("document.getElementById('home-cal').getAttribute('aria-label')"))
    ok('button is in the top bar, right side, visible', pg.is_visible('#home-cal') and g("(()=>{const r=document.getElementById('home-cal').getBoundingClientRect();return r.left>195&&r.top<90})()"))
    pg.screenshot(path=S + '/home_date.png', clip={'x': 0, 'y': 0, 'width': 390, 'height': 140})
    # дата идёт за часами: после полуночи без перезагрузки обновляется сама
    pg.clock.fast_forward('15:00:00')
    ok('after midnight (no reload) shows Wednesday 11 Nov', txt() == ('📅 ср', '11 нояб'), txt())
    # возвращение на главную тоже обновляет дату
    g("showScreen('screen-profile')"); pg.clock.fast_forward('24:00:00'); g("showScreen('screen-home')")
    ok('next day shown after returning to home', txt() == ('📅 чт', '12 нояб'), txt())
    # конец года и месяца
    pg.clock.set_fixed_time('2026-12-31T23:59:00+05:00'); g("renderHomeDate()")
    ok('year end: 31 dec', txt() == ('📅 чт', '31 дек'), txt())
    # нажатие открывает календарь дома
    pg.click('#home-cal')
    ok('tap opens the house calendar', g("document.querySelector('.screen.active').id") == 'screen-calendar')
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
