import os
import sys
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};u['77019999999']={phone:'77019999999',last:'Петров',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Абая',house:'5',apt:'7'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');lsSet(LS_WELCOME,{'77011234567':1,'77019999999':1});}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'index.html'))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    opened = lambda: g("document.getElementById('mgmt-modal').classList.contains('open')")
    # карточка в «Объявления и обсуждения»
    titles = g("[...document.querySelectorAll('#ann-carousel .ann-card-module .amc-title')].map(e=>e.textContent.trim())")
    ok('card «Управление домом» is in the announcements carousel (second)', titles[:2] == ['Если случилось…', 'Управление домом'] and len(titles) == 4, titles)
    ok('carousel dots match the cards', g("document.querySelectorAll('.ann-dot-ind').length") == 4)
    ok('card pill asks to choose a form when nothing chosen', g("document.getElementById('mgmt-pill').textContent") == 'Выбрать форму')
    # окно и три формы
    g("document.getElementById('mgmt-card').click()")
    ok('window opens', opened() and pg.is_visible('#mgmt-modal'))
    forms = g("[...document.querySelectorAll('#mgmt-opts .mgmt-opt b')].map(e=>e.textContent)")
    ok('three forms in the requested order', forms == ['ОСИ', 'Простое товарищество', 'НСУ'], forms)
    ok('nothing selected, hint shown, disclaimer and sources present', g("document.querySelectorAll('#mgmt-opts .mgmt-opt.sel').length") == 0 and 'Нажмите на форму' in g("document.getElementById('mgmt-info').textContent") and 'не проверена владельцем проекта и юристом' in g("document.getElementById('mgmt-info').textContent"))
    ok('sources are external links that open safely', g("[...document.querySelectorAll('#mgmt-info a')].length") == 3 and g("[...document.querySelectorAll('#mgmt-info a')].every(a=>a.target=='_blank'&&/noopener/.test(a.rel)&&a.href.startsWith('https://'))"))
    # справка по каждой форме
    pg.click('#mgmt-opts [data-form=osi]')
    t = g("document.getElementById('mgmt-info').textContent")
    ok('OSI: legal entity, assembly, registration', 'Юридическое лицо' in t and 'собрание собственников' in t and 'государственную регистрацию' in t and g("document.querySelector('#mgmt-opts .sel').dataset.form") == 'osi', t[:200])
    pg.click('#mgmt-opts [data-form=pt]')
    t = g("document.getElementById('mgmt-info').textContent")
    ok('simple partnership: not a legal entity, and the abolition warning is shown', 'Не является юридическим лицом' in t and 'упразднил' in t and 'не проверены' in t and pg.is_visible('#mgmt-info .mgmt-warn'), t[:200])
    pg.click('#mgmt-opts [data-form=nsu]')
    t = g("document.getElementById('mgmt-info').textContent")
    ok('NSU: expansion and the honest gap about the decision procedure', 'непосредственно и совместно' in t and 'пока не описаны' in t, t[:200])
    ok('only one form is marked selected', g("document.querySelectorAll('#mgmt-opts .mgmt-opt.sel').length") == 1 and g("document.querySelector('#mgmt-opts .sel').getAttribute('aria-pressed')") == 'true')
    pg.screenshot(path=S + '/mgmt_nsu.png')
    pg.click('#mgmt-opts [data-form=pt]'); pg.screenshot(path=S + '/mgmt_pt.png')
    # закрыть, карточка показывает выбор, выбор переживает перезагрузку
    pg.click('#mgmt-modal .btn-primary'); ok('window closes', not opened())
    pg.click('#mgmt-card') if False else g("showScreen('screen-home')")
    ok('card pill shows the chosen form', g("document.getElementById('mgmt-pill').textContent") == 'Простое товарищество')
    pg.reload(); ok('choice survives reload', g("lsGet(LS_MGMT,{})['77011234567']") == 'pt' and g("document.getElementById('mgmt-pill').textContent") == 'Простое товарищество')
    g("document.getElementById('mgmt-card').click()")
    ok('reopened with the chosen form and its reference', g("document.querySelector('#mgmt-opts .sel').dataset.form") == 'pt' and 'упразднил' in g("document.getElementById('mgmt-info').textContent"))
    g("mgmtClose()")
    # выбор хранится отдельно для каждого жителя
    g("lsSet(LS_SESSION,'77019999999')"); pg.reload()
    ok('another resident on the same device has his own (empty) choice', g("document.getElementById('mgmt-pill').textContent") == 'Выбрать форму' and g("mgmtChoice()") == '')
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
