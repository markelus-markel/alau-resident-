import os
import sys
from playwright.sync_api import sync_playwright
S=sys.argv[1]; res=[]
def ok(n,c,x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ')+n+(' | '+str(x)[:300] if not c else ''))
SEED="""()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    pg=b.new_context(viewport={'width':390,'height':844}).new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    g("showScreen('screen-contacts')")
    t=g("document.getElementById('screen-contacts').textContent")
    ok('no invented people/phones', not any(w in t for w in ['Болтабеков','Хаусмастер','АбайГрупп','411-11-11','422-22-22','Электросбыт','онлайн']), t[:200])
    ok('7 empty slots "Не указан"', g("document.querySelectorAll('.contact-card').length")==7 and g("[...document.querySelectorAll('.contact-name')].every(e=>e.textContent==='Не указан')"))
    ok('national numbers 112/101/102/103/104', g("[...document.querySelectorAll('.emergency-btn')].map(a=>a.getAttribute('href')).join()")=='tel:112,tel:101,tel:102,tel:103,tel:104')
    pg.screenshot(path=S+'/ct_empty.png')
    pg.click('.contact-card[data-slot="chair"]'); ok('modal opens, no clear button', g("document.getElementById('ct-modal').classList.contains('open')") and g("document.getElementById('ct-clear').style.display")=='none' and 'Председатель' in g("document.getElementById('ct-title').textContent"))
    pg.click('#ct-modal >> text=Сохранить'); ok('name required', 'Укажите' in g("document.getElementById('toast').textContent") and g("document.getElementById('ct-modal').classList.contains('open')"))
    pg.fill('#ct-name','<b>Тестов Т.Т.</b>'); pg.fill('#ct-phone','+7 701 111 22 33'); pg.fill('#ct-note','пн-пт 10-17'); pg.click('#ct-modal >> text=Сохранить')
    ok('saved, shown escaped with tel link', not g("document.getElementById('ct-modal').classList.contains('open')") and '<b>Тестов' in g("document.querySelector('[data-slot=chair] .contact-name').textContent") and g("!!document.querySelector('[data-slot=chair] a[href=\"tel:+77011112233\"]')") and g("!document.querySelector('[data-slot=chair] b')"))
    pg.reload(); g("showScreen('screen-contacts')"); ok('persists after reload', 'Тестов' in g("document.querySelector('[data-slot=chair] .contact-name').textContent"))
    g("lsSet(LS_SESSION,'77019999999')"); g("renderContacts()"); ok('other phone sees empty', g("document.querySelector('[data-slot=chair] .contact-name').textContent")=='Не указан'); g("lsSet(LS_SESSION,'77011234567')"); g("renderContacts()")
    pg.click('.contact-card[data-slot="chair"]'); ok('edit prefilled + clear visible', g("document.getElementById('ct-name').value")=='<b>Тестов Т.Т.</b>' and g("document.getElementById('ct-clear').style.display")=='block')
    pg.click('#ct-clear'); ok('clear returns to empty', g("document.querySelector('[data-slot=chair] .contact-name').textContent")=='Не указан')
    ok('no page errors', not errs, errs); b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
