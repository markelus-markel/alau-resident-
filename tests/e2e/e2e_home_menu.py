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
    ctx = b.new_context(viewport={'width': 360, 'height': 700}, device_scale_factor=2)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    act = lambda: g("document.querySelector('.screen.active').id")
    openm = lambda: g("document.getElementById('home-menu').classList.contains('open')")
    ok('menu button is in the header, left of the app name', pg.is_visible('#home-menu-btn') and g("(()=>{const m=document.getElementById('home-menu-btn').getBoundingClientRect(),h=document.querySelector('#screen-home h1').getBoundingClientRect();return m.right<=h.left+1&&m.top<90})()"))
    ok('360px: name is not clipped and does not overlap the date button', g("(()=>{const h=document.querySelector('#screen-home h1'),c=document.getElementById('home-cal').getBoundingClientRect(),r=h.getBoundingClientRect();return h.scrollWidth<=h.clientWidth+1&&r.right<=c.left&&document.getElementById('home-apt').getBoundingClientRect().right<=360})()"))
    ok('menu is closed by default', not openm() and not pg.is_visible('#home-menu') and g("document.getElementById('home-menu-btn').getAttribute('aria-expanded')") == 'false')
    # открыть и проверить состав
    pg.click('#home-menu-btn')
    ok('menu opens', openm() and pg.is_visible('#home-menu') and g("document.getElementById('home-menu-btn').getAttribute('aria-expanded')") == 'true')
    items = g("[...document.querySelectorAll('#home-menu [role=menuitem]')].map(b=>b.querySelector('.hm-ico').textContent+'|'+b.lastChild.textContent.trim())")
    ok('four items in the requested order', items == ['📖|Что умеет приложение', '🎙️|Голосовой помощник', '📞|Контакты', '👤|Мой профиль'], items)
    ok('menu fits inside the phone screen', g("(()=>{const r=document.getElementById('home-menu').getBoundingClientRect();return r.left>=0&&r.right<=360&&r.bottom<=700})()"))
    pg.screenshot(path=S + '/home_menu.png')
    # повторное нажатие закрывает
    pg.click('#home-menu-btn'); ok('second tap on the menu button closes it', not openm())
    # снаружи и Esc
    pg.click('#home-menu-btn'); pg.click('#screen-home h1'); ok('tap outside closes the menu', not openm())
    pg.click('#home-menu-btn'); pg.keyboard.press('Escape'); ok('Escape closes the menu', not openm())
    # каждый пункт открывает своё
    pg.click('#home-menu-btn'); pg.click('#hm-guide')
    ok('«Что умеет приложение» opens the guide and closes the menu', g("document.getElementById('guide-modal').classList.contains('open')") and not openm())
    g("guideClose()")
    for btn, scr, name in [('#hm-voice', 'screen-voice', 'voice assistant'), ('#hm-contacts', 'screen-contacts', 'contacts'), ('#hm-profile', 'screen-profile', 'profile')]:
        g("showScreen('screen-home')"); pg.click('#home-menu-btn'); pg.click(btn)
        ok(name + ' opens from the menu', act() == scr, act())
    # вернулись на главную: меню закрыто
    g("showScreen('screen-home')"); ok('menu is closed after coming back to home', not openm())
    # убранные с главной элементы
    ok('old navigator tiles and link are gone', g("!document.getElementById('guide-link') && ![...document.querySelectorAll('#screen-home .quick-btn')].some(b=>/Голос\\. помощник|Контакты|Мой профиль/.test(b.textContent))"))
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
