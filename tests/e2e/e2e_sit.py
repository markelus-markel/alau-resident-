import os
import sys
from playwright.sync_api import sync_playwright
S=sys.argv[1]; res=[]
def ok(n,c,x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ')+n+(' | '+str(x)[:300] if not c else ''))
SEED="""()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
URL='file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    ctx=b.new_context(viewport={'width':390,'height':844}); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    opened=lambda: g("document.getElementById('sit-modal').classList.contains('open')")
    g("showScreen('screen-home')")
    ok('registry has >=14 situations, unique ids', g("SITUATIONS.length")>=14 and g("new Set(SITUATIONS.map(s=>s.id)).size")==g("SITUATIONS.length"))
    ok('every situation has steps, level, cat', g("SITUATIONS.every(s=>s.now.length&&s.next.length&&SIT_LEVELS[s.level]&&mvCatMap[s.cat])"), g("SITUATIONS.filter(s=>!(s.now.length&&s.next.length&&SIT_LEVELS[s.level]&&mvCatMap[s.cat])).map(s=>s.id)"))
    ok('emergency ones have phone buttons', g("SITUATIONS.filter(s=>s.level==='emergency').every(s=>s.call.length)"))
    # entry points
    for name,js in [('home tile',"[...document.querySelectorAll('#screen-home .quick-btn')].find(b=>b.textContent.includes('Ситуации')).click()"),('announcement module',"[...document.querySelectorAll('.ann-card-module')].find(b=>b.textContent.includes('Если случилось')).click()"),('announcement list card',"[...document.querySelectorAll('.ann-full-card')].find(b=>b.textContent.includes('типичные ситуации')).click()")]:
        g("closeSituations()"); g(js)
        ok('popup via '+name, opened() and 'Типичные ситуации' in g("document.getElementById('sit-title').textContent"))
    ok('list view has all rows and search', g("document.querySelectorAll('#sit-body .sit-row').length")==g("SITUATIONS.length") and g("document.getElementById('sit-search-wrap').style.display")=='block')
    pg.screenshot(path=S+'/sit_list.png')
    pg.fill('#sit-search','лифт'); ok('search narrows', g("document.querySelectorAll('#sit-body .sit-row').length")==1)
    pg.fill('#sit-search','абвгд'); ok('search empty state', 'ничего не нашлось' in g("document.getElementById('sit-body').textContent"))
    pg.fill('#sit-search','')
    # detail
    pg.click('#sit-body .sit-row[data-sit="gas"]')
    ok('detail shows gas steps + alarm + tel links', 'Запах газа' in g("document.getElementById('sit-title').textContent") and g("!!document.querySelector('.sit-alarm')") and g("[...document.querySelectorAll('.sit-call')].map(a=>a.getAttribute('href')).join()")=='tel:104,tel:112')
    pg.screenshot(path=S+'/sit_gas.png')
    pg.click('text=← Все ситуации'); ok('back to list', g("document.querySelectorAll('#sit-body .sit-row').length")==g("SITUATIONS.length"))
    # create ticket from situation
    pg.click('#sit-body .sit-row[data-sit="lift"]'); pg.fill('#sit-text','Лифт застрял на 3 этаже'); pg.click('#sit-modal >> text=Отправить заявку')
    ok('send closes popup, creates О-001 with lift category, goes to tickets', not opened() and g("ticketBox().box.list[0].id")=='О-001' and 'Лифт' in g("ticketBox().box.list[0].cat") and g("document.querySelector('.screen.active').id")=='screen-tickets', g("JSON.stringify(ticketBox().box.list[0]).slice(0,160)"))
    ok('non-emergency send has no popup', not opened())
    # auto popup for emergency text
    g("showScreen('screen-voice'); resetVoice()"); pg.click('#vstate-idle >> text=Ввести текст руками'); pg.fill('#transcript-text','Сильно пахнет газом в подъезде'); pg.click('#vstate-review >> text=Отправить заявку')
    ok('emergency ticket text auto-pops gas memo', opened() and 'Запах газа' in g("document.getElementById('sit-title').textContent") and g("ticketBox().box.list[0].id")=='В-001')
    g("closeSituations()")
    g("showScreen('screen-voice'); resetVoice()"); pg.click('#vstate-idle >> text=Ввести текст руками'); pg.fill('#transcript-text','Не горит свет в подъезде'); pg.click('#vstate-review >> text=Отправить заявку')
    ok('"не горит свет" does NOT trigger fire popup', not opened())
    # matcher
    m=lambda t: g("(()=>{const s=sitFind(%r);return s?s.id:null})()"%t)
    ok('matcher: gas not in "магазин"', m('иду в магазин')!='gas')
    ok('matcher: examples', m('пахнет газом')=='gas' and m('пожар на кухне')=='fire' and m('затопили соседи')=='leak' and m('шум ночью')=='noise' and m('лифт застрял')=='lift' and m('холодные батареи')=='heat' and m('не горит свет')=='power' and m('нет воды')=='nowater', [m(x) for x in ['пахнет газом','пожар на кухне','затопили соседи','шум ночью','лифт застрял','холодные батареи','не горит свет','нет воды']])
    # agenda situation
    g("showScreen('screen-home')"); g("openSituations('meeting')"); pg.click('#sit-body >> text=Внести вопрос на повестку')
    ok('meeting situation leads to agenda modal', not opened() and g("document.getElementById('agenda-modal').classList.contains('open')"))
    # overlay click closes
    g("openSituations()"); g("document.getElementById('sit-modal').click()"); ok('overlay click closes', not opened())
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
