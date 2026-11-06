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
    dialogs=[]; pg.on('dialog',lambda d:(dialogs.append(d.message),d.dismiss()))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    g("showScreen('screen-market')")
    names=['Строительные материалы','Отделочные материалы','Лакокрасочные материалы','Сантехнические материалы','Электрика','Системы телеметрии','Системы охраны и наблюдения','Мебель','Фурнитура','Остекление','Текстиль','Проектирование','Дизайн','Общестроительные работы','Сантехнические работы','Отделочные работы','Электромонтаж','Сигнализация и связь','Ремонт','Перевозка мебели','Переезд из квартиры','Клининг','Фумигация','Санитария','Жилищный консалтинг','Риэлтерские услуги','Юридические услуги']
    shown=g("[...document.querySelectorAll('#mk-body .mk-name')].map(e=>e.textContent)")
    ok('all requested categories shown, none extra', sorted(shown)==sorted(names), set(names)^set(shown))
    ok('11 materials / 16 services', g("MARKET_CATS.filter(c=>c.grp==='mat').length")==11 and g("MARKET_CATS.filter(c=>c.grp==='srv').length")==16)
    body=g("document.body.textContent")
    ok('no fabricated partners left', not any(w in body for w in ['CleanCity','КазГарант','МастерБригада','Абай Недвижимость','Прошёл модерацию','−20%','−15%']))
    ok('old carousel/order modal gone', g("!document.getElementById('cards-track')&&!document.getElementById('order-modal')"))
    pg.screenshot(path=S+'/mk_list.png')
    pg.click('#mk-tabs >> text=Услуги'); ok('tab services -> 16', g("document.querySelectorAll('#mk-body .mk-cat').length")==16)
    pg.click('#mk-tabs >> text=Материалы'); ok('tab materials -> 11', g("document.querySelectorAll('#mk-body .mk-cat').length")==11)
    pg.click('#mk-tabs >> text=Все')
    pg.fill('#mk-search','кран'); ok('search by synonym "кран"', 'Сантехнические материалы' in g("document.getElementById('mk-body').textContent"))
    pg.fill('#mk-search','тараканы'); ok('search "тараканы" -> Фумигация', g("[...document.querySelectorAll('#mk-body .mk-name')].map(e=>e.textContent).join()")=='Фумигация')
    pg.fill('#mk-search','ЮРИСТ'); ok('search is case-insensitive', 'Юридические услуги' in g("document.getElementById('mk-body').textContent"))
    pg.fill('#mk-search','zzzz'); ok('empty search state with request button', 'Ничего не найдено' in g("document.getElementById('mk-body').textContent"))
    pg.click('#mk-body >> text=Оставить запрос')
    ok('free request opens M flow', g("document.getElementById('screen-module-voice').classList.contains('active')") and 'zzzz' in g("document.getElementById('mv-desc-text').textContent"))
    g("showScreen('screen-market')"); pg.fill('#mk-search','')
    # category modal
    pg.click('.mk-cat[data-cat="s-clean"]')
    ok('category popup empty state', g("document.getElementById('mk-modal').classList.contains('open')") and 'Клининг' in g("document.getElementById('mk-title').textContent") and 'пока нет' in g("document.getElementById('mk-body2').textContent"))
    pg.screenshot(path=S+'/mk_cat.png')
    pg.click('#mk-body2 >> text=Рекомендовать поставщика')
    pg.click('#mk-body2 >> text=Сохранить'); ok('name required', 'Укажите' in g("document.getElementById('toast').textContent") and g("lsGet(LS_RECS,{})['77011234567']")==None)
    pg.fill('#mk-r-name','Тестовая клининговая'); pg.fill('#mk-r-phone','+7 700 000 00 00'); pg.fill('#mk-r-note','убирали подъезд'); pg.click('#mk-body2 >> text=Сохранить')
    ok('recommendation saved, shown as unverified', 'Тестовая клининговая' in g("document.getElementById('mk-body2').textContent") and 'не проверены' in g("document.getElementById('mk-body2').textContent"))
    ok('recommendation escaped & per phone', g("lsGet(LS_RECS,{})['77011234567'].length")==1 and g("lsGet(LS_RECS,{})['77019999999']")is None)
    pg.click('#mk-body2 >> text=Оставить запрос в ОСИ')
    ok('request from category opens M flow with category text', g("document.getElementById('screen-module-voice').classList.contains('active')") and 'Клининг' in g("document.getElementById('mv-desc-text').textContent") and not g("document.getElementById('mk-modal').classList.contains('open')"))
    g("showScreen('screen-market')")
    ok('badge counter on category', g("document.querySelector('.mk-cat[data-cat=\"s-clean\"] .mk-cnt').textContent")=='1')
    # extensibility: provider added to registry appears
    g("MARKET_PROVIDERS.push({id:'t1',cats:['s-legal'],name:'ТестЮр',phone:'+77010000000',desc:'тест'}); renderMarket()")
    pg.fill('#mk-search','тестюр'); ok('provider search finds category', g("document.querySelectorAll('#mk-body .mk-cat').length")==1)
    pg.click('.mk-cat'); ok('provider card with tel link', 'ТестЮр' in g("document.getElementById('mk-body2').textContent") and g("!!document.querySelector('#mk-body2 a[href^=\"tel:\"]')"))
    g("mkClose()")
    # announcements cleaned
    g("showScreen('screen-announcements')"); ok('promo removed from announcements', 'Скидка' not in g("document.getElementById('screen-announcements').textContent"))
    g("showScreen('screen-home')"); ok('home ann carousel: 3 modules and 3 dots', g("document.querySelectorAll('#ann-carousel .ann-card-module').length")==3 and g("document.querySelectorAll('.ann-dot-ind').length")==3, (g("document.querySelectorAll('#ann-carousel .ann-card-module').length"),g("document.querySelectorAll('.ann-dot-ind').length")))
    ok('no alert dialogs', not dialogs, dialogs)
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
