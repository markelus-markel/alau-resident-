import os
import sys, json
from playwright.sync_api import sync_playwright
URL = 'file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')
S = sys.argv[1]
res = []
def ok(name, cond, extra=''):
    res.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name + (' | ' + str(extra) if extra and not cond else ''))

INIT = "window.__opened=[]; window.open=function(u){window.__opened.push(u);return null;};"
NOMINATIM = {"address":{"house_number":"12А","road":"улица Найманбаева","city":"Семей","country":"Казахстан"}}

def register(pg, phone='7011234567'):
    pg.type('#auth-phone', phone)
    pg.click('button:has-text("Получить код")')
    pg.fill('#auth-code', pg.inner_text('#auth-demo-code'))
    pg.click('button:has-text("Подтвердить")')

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2,
                        geolocation={'latitude':50.4111,'longitude':80.2275,'accuracy':20}, permissions=['geolocation'])
    ctx.add_init_script(INIT)
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    dialogs = []
    def on_dialog(d):
        dialogs.append(d.message); d.accept()
    pg.on('dialog', on_dialog)
    reqs = []
    def handle(route):
        reqs.append(route.request.url)
        route.fulfill(status=200, content_type='application/json', headers={'access-control-allow-origin':'*'}, body=json.dumps(NOMINATIM, ensure_ascii=False))
    pg.route('**/nominatim.openstreetmap.org/**', handle)
    pg.goto(URL)
    register(pg)
    active = lambda: pg.evaluate("document.querySelector('.screen.active')?.id")
    ok('on register screen', active()=='screen-register', active())
    ok('geo box visible', pg.is_visible('.geo-box'))

    # 1. city offline
    pg.select_option('#reg-city','Астана')
    pg.click('button:has-text("🏙 Город")')
    pg.wait_for_function("document.getElementById('reg-city').value==='Семей'", timeout=5000)
    ok('city = Семей from coordinates', pg.input_value('#reg-city')=='Семей')
    ok('no network used for city', len(reqs)==0 and len(dialogs)==0, (reqs, dialogs))
    # 2. Almaty
    ctx.set_geolocation({'latitude':43.238,'longitude':76.945,'accuracy':30})
    pg.click('button:has-text("🏙 Город")'); pg.wait_for_function("document.getElementById('reg-city').value==='Алматы'", timeout=5000)
    ok('city = Алматы from coordinates', pg.input_value('#reg-city')=='Алматы')
    # 3. far from any city
    ctx.set_geolocation({'latitude':0,'longitude':0,'accuracy':30})
    pg.click('button:has-text("🏙 Город")'); pg.wait_for_function("document.getElementById('geo-status').textContent.includes('далеко')", timeout=5000)
    ok('far location: city NOT changed', pg.input_value('#reg-city')=='Алматы', pg.input_value('#reg-city'))
    # 4. low accuracy note
    ctx.set_geolocation({'latitude':50.4111,'longitude':80.2275,'accuracy':900})
    pg.click('button:has-text("🏙 Город")'); pg.wait_for_function("document.getElementById('geo-status').textContent.includes('Точность низкая')", timeout=5000)
    ok('low accuracy warned', True)

    # 5. consent declined -> no request
    ctx.set_geolocation({'latitude':50.4111,'longitude':80.2275,'accuracy':20})
    pg.remove_listener('dialog', on_dialog)
    pg.once('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
    pg.click('button:has-text("🏠 Улица и дом")'); pg.wait_for_timeout(400)
    ok('consent dialog mentions OpenStreetMap', len(dialogs)==1 and 'OpenStreetMap' in dialogs[0], dialogs)
    ok('declined consent: no request sent', len(reqs)==0, reqs)
    # 6. consent accepted -> request, fields filled
    pg.on('dialog', on_dialog)
    pg.click('button:has-text("🏠 Улица и дом")')
    pg.wait_for_function("document.getElementById('reg-house').value!==''", timeout=5000)
    ok('street matched to directory', pg.input_value('#reg-street')=='ул. Найманбаева', pg.input_value('#reg-street'))
    ok('house filled', pg.input_value('#reg-house')=='12А', pg.input_value('#reg-house'))
    ok('city set from OSM', pg.input_value('#reg-city')=='Семей')
    ok('apartment NOT guessed', pg.input_value('#reg-apt')=='')
    ok('request has rounded coords, no extra params', len(reqs)==1 and 'lat=50.41110' in reqs[0] and 'lon=80.22750' in reqs[0], reqs)
    ok('status warns about accuracy', 'неточны' in pg.inner_text('#geo-status'))
    # 7. consent remembered
    n = len(dialogs); pg.click('button:has-text("🏠 Улица и дом")'); pg.wait_for_timeout(500)
    ok('consent asked only once', len(dialogs)==n, (n, len(dialogs)))
    pg.screenshot(path=S+'/g1_register_geo.png', full_page=True)

    # 8. OSM errors
    pg.unroute('**/nominatim.openstreetmap.org/**')
    pg.route('**/nominatim.openstreetmap.org/**', lambda r: r.abort())
    pg.click('button:has-text("🏠 Улица и дом")'); pg.wait_for_function("document.getElementById('geo-status').textContent.includes('недоступен')", timeout=5000)
    ok('network failure message', True)
    pg.unroute('**/nominatim.openstreetmap.org/**')
    pg.route('**/nominatim.openstreetmap.org/**', lambda r: r.fulfill(status=429, body='x', headers={'access-control-allow-origin':'*'}))
    pg.click('button:has-text("🏠 Улица и дом")'); pg.wait_for_function("document.getElementById('geo-status').textContent.includes('429')", timeout=5000)
    ok('HTTP 429 message', True)
    pg.unroute('**/nominatim.openstreetmap.org/**')
    pg.route('**/nominatim.openstreetmap.org/**', lambda r: r.fulfill(status=200, content_type='application/json', headers={'access-control-allow-origin':'*'}, body=json.dumps({"address":{"city":"Нигде"}})))
    pg.fill('#reg-street',''); pg.fill('#reg-house','')
    pg.click('button:has-text("🏠 Улица и дом")'); pg.wait_for_function("document.getElementById('geo-status').textContent.includes('Внимание')", timeout=5000)
    ok('unknown city/road/house: warns, fields stay empty', pg.input_value('#reg-street')=='' and pg.input_value('#reg-house')=='' , pg.inner_text('#geo-status'))

    # 9. save WITHOUT checkbox -> no coordinates stored
    pg.click('button:has-text("Заполнить тестовыми данными")')
    pg.click('button:has-text("Сохранить и войти")')
    ok('saved', active()=='screen-home', active())
    prof = pg.evaluate("currentProfile()")
    ok('no coords stored when checkbox off', prof.get('lat') is None, prof)
    pg.evaluate("showScreen('screen-profile')")
    ok('profile: map actions hidden without point', not pg.is_visible('#hm-actions'))
    ok('profile: route hint hidden without point', not pg.is_visible('#hm-route-hint'))
    ok('profile: hint says point not set', 'не задана' in pg.inner_text('#hm-text'))

    # 10. set home here (declined, then accepted)
    pg.remove_listener('dialog', on_dialog)
    pg.once('dialog', lambda d: d.dismiss())
    pg.click('#hm-set'); pg.wait_for_timeout(400)
    ok('declined: nothing stored', pg.evaluate("currentProfile().lat")==None)
    pg.on('dialog', on_dialog)
    pg.click('#hm-set'); pg.wait_for_function("currentProfile().lat!=null", timeout=5000)
    prof = pg.evaluate("currentProfile()")
    ok('home point stored, 5 decimals', prof['lat']==50.4111 and prof['lon']==80.2275, prof)
    ok('map actions visible', pg.is_visible('#hm-actions'))
    # 11. map & route links
    ok('map iframe has no src before tap (no third-party load)', pg.get_attribute('#hm-frame','src') is None and not pg.is_visible('#hm-frame'))
    pg.click('button:has-text("🗺 Показать на карте")')
    src = pg.get_attribute('#hm-frame','src')
    ok('map iframe is OSM embed with marker', src.startswith('https://www.openstreetmap.org/export/embed.html?bbox=') and 'marker=50.4111%2C80.2275' in src, src)
    ok('route hint is visible under the route button (how to come back)', pg.is_visible('#hm-route-hint') and 'Назад' in pg.inner_text('#hm-route-hint'), pg.inner_text('#hm-route-hint'))
    pg.click('button:has-text("🧭 Построить маршрут")')
    ok('route tap shows a toast about returning with the phone Back button', 'другом приложении' in pg.inner_text('#toast') and 'Назад' in pg.inner_text('#toast') and 'show' in (pg.get_attribute('#toast','class') or ''), pg.inner_text('#toast'))
    pg.click('button:has-text("↗ Открыть в OpenStreetMap")')
    opened = pg.evaluate("window.__opened")
    ok('route link (Google Maps, destination only)', opened[0]=='https://www.google.com/maps/dir/?api=1&destination=50.4111,80.2275&travelmode=walking', opened)
    ok('OSM link', opened[1]=='https://www.openstreetmap.org/?mlat=50.4111&mlon=80.2275#map=18/50.4111/80.2275', opened)
    pg.wait_for_timeout(500); pg.screenshot(path=S+'/g2_profile_map.png', full_page=True)
    # 12. edit keeps point; checkbox prechecked
    pg.click('button:has-text("Изменить анкету")')
    ok('edit: checkbox prechecked when point exists', pg.is_checked('#geo-save'))
    pg.click('button:has-text("Сохранить и войти")')
    ok('edit save keeps point', pg.evaluate("currentProfile().lat")==50.4111)
    # 13. uncheck on edit removes point
    pg.evaluate("showScreen('screen-profile')"); pg.click('button:has-text("Изменить анкету")')
    pg.uncheck('#geo-save'); pg.click('button:has-text("Сохранить и войти")')
    ok('unchecking removes point', pg.evaluate("currentProfile().lat")==None)
    # 14. new fix + checkbox -> stored
    pg.evaluate("showScreen('screen-profile')"); pg.click('button:has-text("Изменить анкету")')
    ctx.set_geolocation({'latitude':50.4200,'longitude':80.2300,'accuracy':15})
    pg.click('button:has-text("🏙 Город")'); pg.wait_for_function("document.getElementById('geo-status').textContent.includes('Город:')", timeout=5000)
    pg.check('#geo-save'); pg.click('button:has-text("Сохранить и войти")')
    ok('new fix stored via checkbox', pg.evaluate("currentProfile().lat")==50.42 and pg.evaluate("currentProfile().geoAcc")==15, pg.evaluate("currentProfile()"))
    # 15. delete point
    pg.evaluate("showScreen('screen-profile')"); pg.click('button:has-text("Удалить сохранённую точку")')
    ok('delete point', pg.evaluate("currentProfile().lat")==None and not pg.is_visible('#hm-actions'))
    ok('no uncaught page errors', not errs, errs)

    # permission denied (separate context)
    ctx2 = b.new_context(viewport={'width':390,'height':844})
    pg2 = ctx2.new_page(); e2=[]
    pg2.on('pageerror', lambda e: e2.append(str(e)))
    pg2.on('dialog', lambda d: d.accept())
    pg2.goto(URL); register(pg2)
    pg2.click('button:has-text("🏙 Город")'); pg2.wait_for_function("document.getElementById('geo-status').textContent.length>0 && !document.getElementById('geo-status').textContent.includes('Определяю')", timeout=8000)
    t = pg2.inner_text('#geo-status')
    ok('denied permission: clear message, nothing changed', ('запрещён' in t) and pg2.input_value('#reg-city')=='Семей', t)
    ok('denied: no page errors', not e2, e2)
    b.close()
print('\nTOTAL', len(res), 'FAILED', res.count(False))
