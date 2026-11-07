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
open(S+'/bill_ocr.png','wb').write(PNG)
ELEC="КВИТАНЦИЯ ЗА ЭЛЕКТРОЭНЕРГИЮ\nПериод: октябрь 2026\n\nЛицевой счет: 123456789\n\nПотреблено: 245 кВтч\n\nТариф: 20,87 тенге\n\nНачислено: 5 113,15\n\nИтого к оплате: 12 345,50 тенге\nОплатить до 10.11.2026\n"
WATER="Счёт-извещение\nВодоснабжение и водоотведение\nза 09.2026\nЛ/с № 55 02 17\nСумма к оплате:\n4 870,00 тг\nСрок оплаты: 15.10.2026\n"
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    ctx=b.new_context(viewport={'width':390,'height':844}); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    dialogs=[]; pg.on('dialog',lambda d:(dialogs.append(d.message),d.dismiss()))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    # --- разбор текста ---
    r=g("blParse(%r)"%ELEC)
    ok('parse electricity bill', r=={'kind':'elec','amount':12345.5,'due':'2026-11-10','account':'123456789','period':'2026-10'}, r)
    r=g("blParse(%r)"%WATER)
    ok('parse water bill (amount on next line, spaced account, mm.yyyy)', r=={'kind':'water','amount':4870,'due':'2026-10-15','account':'550217','period':'2026-09'}, r)
    ok('garbage -> nothing guessed', g("blParse('asdf 12 qwe')")=={} and g("blParse('')")=={} and g("blParse(null)")=={})
    ok('no amount keyword -> amount not guessed', 'amount' not in g("blParse('Электроэнергия\\nпотреблено 245 кВтч\\nтариф 20,87')"))
    ok('invalid date not accepted', 'due' not in g("blParse('оплатить до 45.13.2026')"))
    ok('earliest keyword decides kind', g("blParse('Вывоз мусора (ТБО)\\nК оплате 1 200')")['kind']=='trash' and g("blParse('Отопление\\nк оплате 9 000,5')")['kind']=='heat')
    ok('amount with comma decimals and thin groups', g("blParse('К оплате: 1 234 567,89')")['amount']==1234567.89)
    g("showScreen('screen-bills')")
    # --- интерфейс: распознано ---
    g("void(window.BL_OCR=async()=>%r)"%ELEC)
    pg.click('#bl-add'); pg.set_input_files('#bl-file', S+'/bill_ocr.png'); pg.wait_for_function("document.getElementById('bl-amount').value!==''")
    ok('fields prefilled from photo', g("[$('bl-kind').value,$('bl-period').value,$('bl-amount').value,$('bl-due').value,$('bl-account').value]")==['elec','2026-10','12345.5','2026-11-10','123456789'])
    ok('all 5 marked as auto, none missing', g("document.querySelectorAll('#bl-modal .bl-auto').length")==5 and g("document.querySelectorAll('#bl-modal .bl-miss').length")==0)
    ok('banner says recognized 5 of 5', 'Распознано полей: 5 из 5' in g("$('bl-banner').textContent"))
    pg.screenshot(path=S+'/bills_ocr_review.png')
    pg.fill('#bl-amount','12000'); ok('editing a field clears its mark', g("!$('bl-amount').classList.contains('bl-auto')"))
    pg.click('#bl-modal button.modal-submit')
    bill=g("lsGet(LS_BILLS,{})['77011234567'][0]")
    ok('saved with user-corrected amount', bill['amount']==12000 and bill['account']=='123456789' and bill['paid']==False, bill)
    # --- частично распознано ---
    g("void(window.BL_OCR=async()=>'Квитанция\\nК оплате 700')")
    pg.click('#bl-add'); pg.set_input_files('#bl-file', S+'/bill_ocr.png'); pg.wait_for_function("document.getElementById('bl-amount').value!==''")
    ok('partial: found amount auto, others red', g("$('bl-amount').classList.contains('bl-auto')") and g("$('bl-due').classList.contains('bl-miss')") and g("$('bl-account').classList.contains('bl-miss')"))
    ok('partial: unrecognized fields stay empty, not invented', g("$('bl-due').value")=='' and g("$('bl-account').value")=='')
    pg.click('#bl-modal >> text=Отмена')
    # --- ничего не распознано ---
    g("void(window.BL_OCR=async()=>'zzz')")
    pg.click('#bl-add'); pg.set_input_files('#bl-file', S+'/bill_ocr.png'); pg.wait_for_function("document.getElementById('bl-banner').textContent.includes('не распознаны')")
    ok('nothing recognized: banner asks manual entry', 'вручную' in g("$('bl-banner').textContent") and g("$('bl-amount').value")=='')
    pg.click('#bl-modal button.modal-submit'); ok('photo alone can still be saved', g("lsGet(LS_BILLS,{})['77011234567'].length")==2)
    # --- сбой движка ---
    g("void(window.BL_OCR=async()=>{throw new Error('offline')})")
    pg.click('#bl-add'); pg.set_input_files('#bl-file', S+'/bill_ocr.png'); pg.wait_for_function("document.getElementById('bl-banner').textContent.includes('Распознать не удалось')")
    ok('engine failure: clear message, form still usable', g("$('bl-modal').classList.contains('open')") and g("$('bl-amount').value")=='')
    pg.fill('#bl-amount','100'); pg.click('#bl-modal button.modal-submit'); ok('manual entry after failure works', g("lsGet(LS_BILLS,{})['77011234567'].length")==3)
    # --- устаревший результат не заполняет другое окно ---
    g("void(window.BL_OCR=()=>new Promise(r=>setTimeout(()=>r(%r),600)))"%ELEC)
    pg.click('#bl-add'); pg.set_input_files('#bl-file', S+'/bill_ocr.png'); pg.click('#bl-modal >> text=Отмена'); pg.wait_for_timeout(1000)
    pg.click('#bl-add'); ok('late OCR result does not fill a reopened form', g("$('bl-amount').value")=='' and g("$('bl-banner').style.display")=='none')
    pg.click('#bl-modal >> text=Отмена')
    ok('library not loaded without a photo', g("typeof window.Tesseract")=='undefined')
    ok('no alert dialogs', not dialogs, dialogs)
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
