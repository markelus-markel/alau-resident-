import os
import sys
import base64
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');lsSet(LS_WELCOME,{'77011234567':1});}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'index.html'))
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
open(S + '/meter.png', 'wb').write(PNG)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    # «распознавание» подменяем: на фото цифры «0012 3456 и мусор 7»
    pg.add_init_script("window.MT_OCR=async()=>'Счётчик 00123 456 № 7 заводской 20250813'")
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    # вход из экрана «Счета»
    g("showScreen('screen-bills')"); ok('bills screen has the meters button', pg.is_visible('#mt-open'))
    pg.click('#mt-open'); ok('meters screen opens', g("document.querySelector('.screen.active').id") == 'screen-meters')
    ok('empty state, no invented readings', 'Показаний пока нет' in g("document.getElementById('mt-list').textContent") and g("lsGet(LS_METERS,{})['77011234567']") == None)
    # разбор чисел на фото
    ok('candidates: leading zeros count as digits, equal length keeps text order, one-digit junk ignored', g("mtCandidates('00123 456 № 7 заводской 20250813')") == [123456, 20250813], g("mtCandidates('00123 456 № 7 заводской 20250813')"))
    ok('candidates: a longer chain goes before a shorter one', g("mtCandidates('1234 и 98765')") == [98765, 1234], g("mtCandidates('1234 и 98765')"))
    ok('candidates: decimal separator kept, short numbers dropped', g("mtCandidates('12 3456,789 и 55')") == [3456.789] or g("mtCandidates('12 3456,789 и 55')")[0] == 123456.789, g("mtCandidates('12 3456,789 и 55')"))
    ok('candidates: nothing found gives an empty list, never a guess', g("mtCandidates('нет цифр')") == [])
    # окно и фото
    pg.click('#mt-add'); ok('window opens', g("document.getElementById('mt-modal').classList.contains('open')"))
    ok('four kinds offered: cold water, hot water, electricity, gas', g("[...document.querySelectorAll('#mt-kind option')].map(o=>o.textContent)") == ['💧 Холодная вода', '🔥 Горячая вода', '⚡ Электричество', '🔵 Газ'])
    pg.set_input_files('#mt-file', S + '/meter.png'); pg.wait_for_selector('#mt-cands button', timeout=8000)
    ok('photo preview shown', g("document.querySelectorAll('#mt-photo-box img').length") == 1)
    ok('recognized number is put in the field and marked yellow for confirmation', g("document.getElementById('mt-value').value") != '' and g("document.getElementById('mt-value').classList.contains('bl-auto')"))
    ok('other candidates offered as buttons', g("document.querySelectorAll('#mt-cands button').length") >= 2)
    pg.screenshot(path=S + '/meters_modal.png')
    # ручная правка снимает пометку «распознано»
    pg.fill('#mt-value', '100,5'); ok('manual edit clears the recognition mark', not g("document.getElementById('mt-value').classList.contains('bl-auto')"))
    # проверки ввода
    pg.fill('#mt-value', 'abc'); pg.click('#mt-modal >> text=Всё верно'); ok('letters rejected', 'Проверьте показание' in g("document.getElementById('toast').textContent") and g("lsGet(LS_METERS,{})['77011234567']") == None)
    pg.fill('#mt-value', '100,5'); pg.fill('#mt-date', ''); pg.click('#mt-modal >> text=Всё верно'); ok('date required', 'дату' in g("document.getElementById('toast').textContent"))
    # первое показание
    pg.fill('#mt-date', '2026-09-10'); pg.fill('#mt-label', '<b>кухня</b>'); pg.click('#mt-modal >> text=Всё верно')
    ok('first reading saved on the device', g("lsGet(LS_METERS,{})['77011234567'].readings.length") == 1 and g("lsGet(LS_METERS,{})['77011234567'].readings[0].value") == 100.5)
    ok('first row has no consumption (no previous reading)', '—' in g("document.querySelector('#mt-list .mt-table tr[data-id]').textContent"))
    ok('label is shown as text, not as markup', '<b>кухня</b>' in g("document.getElementById('mt-list').textContent") and g("document.querySelectorAll('#mt-list b').length") == 1)
    # второе показание: расход
    pg.click('#mt-add'); pg.fill('#mt-value', '112,25'); pg.fill('#mt-date', '2026-10-10'); pg.fill('#mt-label', '<b>кухня</b>'); pg.click('#mt-modal >> text=Всё верно')
    t = g("document.getElementById('mt-list').textContent")
    ok('consumption is the difference to the previous reading', '+11,75 м³' in t, t)
    ok('newest reading is on top', g("[...document.querySelectorAll('#mt-list tr[data-id] td:first-child')].map(e=>e.textContent)") == ['2026-10-10', '2026-09-10'])
    # показание меньше предыдущего не принимается
    pg.click('#mt-add'); pg.fill('#mt-value', '50'); pg.fill('#mt-date', '2026-11-10'); pg.fill('#mt-label', '<b>кухня</b>'); pg.click('#mt-modal >> text=Всё верно')
    ok('reading lower than the previous one is refused with an explanation', 'меньше предыдущего' in g("document.getElementById('mt-banner').textContent") and g("document.getElementById('mt-modal').classList.contains('open')") and g("lsGet(LS_METERS,{})['77011234567'].readings.length") == 2, g("document.getElementById('mt-banner').textContent"))
    pg.fill('#mt-label', 'новый'); pg.click('#mt-modal >> text=Всё верно')
    ok('a replaced meter (another name) starts its own table', g("document.querySelectorAll('#mt-list .mt-card').length") == 2)
    # другое устройство учёта: электричество в отдельной таблице с единицей
    pg.click('#mt-add'); pg.select_option('#mt-kind', 'elec'); pg.fill('#mt-value', '5000'); pg.fill('#mt-date', '2026-11-01'); pg.click('#mt-modal >> text=Всё верно')
    ok('electricity table uses kWh', 'кВт·ч' in g("document.getElementById('mt-list').textContent"))
    pg.click('#mt-add'); pg.select_option('#mt-kind', 'gas'); pg.fill('#mt-value', '800'); pg.fill('#mt-date', '2026-09-01'); pg.click('#mt-modal >> text=Всё верно')
    pg.click('#mt-add'); pg.select_option('#mt-kind', 'gas'); pg.fill('#mt-value', '812,4'); pg.fill('#mt-date', '2026-10-01'); pg.click('#mt-modal >> text=Всё верно')
    ok('gas has its own table, cubic metres and consumption', '🔵 Газ' in g("document.getElementById('mt-list').textContent") and '+12,4 м³' in g("document.getElementById('mt-list').textContent"), g("document.getElementById('mt-list').textContent"))
    # правка и удаление
    g("document.querySelector('#mt-list tr[data-id]').click()"); ok('tap on a row opens it for editing', g("document.getElementById('mt-modal').classList.contains('open')") and g("document.getElementById('mt-del').style.display") == 'block')
    pg.click('#mt-del'); ok('reading can be deleted', g("lsGet(LS_METERS,{})['77011234567'].readings.length") == 5)
    # хранение по жителям
    ok('readings stored per resident', g("Object.keys(lsGet(LS_METERS,{}))") == ['77011234567'])
    # календарь: напоминание и сроки оплаты
    ok('no reminder in the calendar until a day is chosen', g("houseEvents().filter(e=>e.type==='meter').length") == 0)
    pg.select_option('#mt-day', '25'); ok('reminder day saved', g("lsGet(LS_METERS,{})['77011234567'].day") == 25)
    ev = g("houseEvents().filter(e=>e.type==='meter')")
    ok('reminder appears in the calendar on the chosen day of month, today or later', len(ev) == 1 and ev[0]['off'] >= 0 and g("evDay(houseEvents().find(e=>e.type==='meter')).getDate()") == 25, ev)
    g("blStore(a=>{a.push({id:'S-t1',kind:'elec',period:'2026-10',amount:12000,due:blTodayIso(),account:'',photo:null,paid:false})}); blStore(a=>{a.push({id:'S-t2',kind:'water',period:'2026-10',amount:3000,due:blTodayIso(),account:'',photo:null,paid:true})})")
    pay = g("houseEvents().filter(e=>e.type==='pay')")
    ok('unpaid bill is a payment event on its due date; paid bill is not', len(pay) == 1 and pay[0]['off'] == 0 and 'Электричество' in pay[0]['title'] and '12' in pay[0]['title'], pay)
    g("showScreen('screen-calendar')"); cal = g("document.getElementById('cal-list').textContent")
    ok('calendar shows both events', 'Передать показания' in cal and 'Оплатить' in cal, cal[:200])
    ok('ics export of own events is valid', g("(()=>{const t=icsBuild(houseEvents());return t.includes('BEGIN:VEVENT')&&t.includes('Оплатить')&&t.split('BEGIN:VEVENT').length===3})()"))
    pg.screenshot(path=S + '/meters_calendar.png')
    pg.select_option('#mt-day', '0') if False else None
    # другой житель не видит чужих показаний
    g("lsSet(LS_SESSION,'77019999999')"); ok('another resident has no readings', g("mtBox().readings.length") == 0 and g("mtBox().day") == 0)
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
