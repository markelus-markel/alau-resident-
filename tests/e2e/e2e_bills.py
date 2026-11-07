import os
import sys
import base64
from playwright.sync_api import sync_playwright
S=sys.argv[1]; res=[]
def ok(n,c,x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ')+n+(' | '+str(x)[:300] if not c else ''))
SEED="""()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
URL='file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
open(S+'/bill.png','wb').write(PNG)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    ctx=b.new_context(viewport={'width':390,'height':844}); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    dialogs=[]; pg.on('dialog',lambda d:(dialogs.append(d.message),d.dismiss()))
    pg.add_init_script('window.BL_OCR=async()=>""')
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    ok('home has Счета button', g("[...document.querySelectorAll('#screen-home .quick-label')].some(e=>e.textContent==='Счета')"))
    pg.click('#screen-home .quick-btn:has-text("Счета")')
    ok('bills screen opens', g("document.getElementById('screen-bills').classList.contains('active')"))
    ok('empty state, no invented bills', 'Счетов пока нет' in g("$('bl-total').textContent") and g("document.querySelectorAll('.bl-card').length")==0)
    pg.screenshot(path=S+'/bills_empty.png')
    # validation
    pg.click('#bl-add'); ok('modal opens', g("$('bl-modal').classList.contains('open')"))
    pg.click('#bl-modal >> text=Сохранить'); ok('amount or photo required', 'Укажите сумму' in g("$('toast').textContent") and g("lsGet(LS_BILLS,{})['77011234567']")==None)
    pg.fill('#bl-amount','-5'); pg.click('#bl-modal >> text=Сохранить'); ok('negative amount rejected', 'Проверьте сумму' in g("$('toast').textContent"))
    # save a bill with photo
    pg.select_option('#bl-kind','elec'); pg.fill('#bl-amount','12345.5'); pg.fill('#bl-due','2020-01-10'); pg.fill('#bl-account','<b>123456</b>')
    pg.set_input_files('#bl-file', S+'/bill.png'); pg.wait_for_selector('#bl-photo-box img')
    ok('photo preview shown', g("document.querySelectorAll('#bl-photo-box img').length")==1)
    pg.click('#bl-modal >> text=Сохранить')
    ok('bill saved per phone', g("lsGet(LS_BILLS,{})['77011234567'].length")==1 and g("lsGet(LS_BILLS,{})['77019999999']")is None)
    ok('photo stored as data url on device', g("lsGet(LS_BILLS,{})['77011234567'][0].photo.startsWith('data:image/jpeg')"))
    ok('card shows amount, kind, overdue', '12' in g("document.querySelector('.bl-card').textContent") and 'Электричество' in g("document.querySelector('.bl-card').textContent") and 'просрочен' in g("document.querySelector('.bl-card').textContent"))
    ok('account escaped (no html injection)', g("document.querySelectorAll('.bl-card b').length")==0)
    ok('total counts unpaid', 'К оплате: 1 счёт' in g("$('bl-total').textContent"))
    pg.screenshot(path=S+'/bills_list.png')
    # pay hint
    pg.click('.bl-card >> text=Оплатить в Kaspi.kz'); ok('pay hint opens, says app does not pay', g("$('bl-pay').classList.contains('open')") and 'не проводит платёж' in g("$('bl-pay').textContent"))
    ok('no card data fields anywhere', g("[...document.querySelectorAll('#bl-modal input,#bl-modal select,#bl-pay input')].filter(e=>/карт|card|cvv|cvc|pan/i.test((e.placeholder||'')+e.id+(e.name||'')+(e.autocomplete||''))).length")==0)
    pg.screenshot(path=S+'/bills_pay.png')
    pg.click('#bl-pay button:has-text("Отметить оплаченным")')
    ok('marked paid by user', g("lsGet(LS_BILLS,{})['77011234567'][0].paid")==True and 'оплачен' in g("document.querySelector('.bl-card').textContent"))
    ok('paid bill has no pay button', g("document.querySelectorAll('.bl-card .tkt-btn').length")==0)
    ok('total after paid', 'К оплате: 0' in g("$('bl-total').textContent"))
    # edit + delete
    pg.click('.bl-card .bl-row'); ok('edit opens with values', g("$('bl-amount').value")=='12345.5' and g("$('bl-del').style.display")=='block')
    pg.fill('#bl-amount','999'); pg.click('#bl-modal >> text=Сохранить'); ok('edit saved, not duplicated', g("lsGet(LS_BILLS,{})['77011234567'].length")==1 and g("lsGet(LS_BILLS,{})['77011234567'][0].amount")==999)
    pg.click('.bl-card .bl-row'); pg.click('#bl-del'); ok('delete works', g("lsGet(LS_BILLS,{})['77011234567'].length")==0 and 'Счетов пока нет' in g("$('bl-total').textContent"))
    # persistence
    pg.click('#bl-add'); pg.fill('#bl-amount','500'); pg.click('#bl-modal >> text=Сохранить'); pg.reload()
    g("showScreen('screen-bills')"); ok('persists after reload', g("document.querySelectorAll('.bl-card').length")==1)
    # no invented data
    body=g("document.body.textContent")
    ok('no fabricated utility phones/companies', not any(w in body for w in ['Алсеко','КЕGОС','Водоканал-Сервис','Казахтелеком']))
    ok('no alert dialogs', not dialogs, dialogs)
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
