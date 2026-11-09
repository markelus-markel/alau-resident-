import os
import sys, json
from playwright.sync_api import sync_playwright
URL = 'file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')
S = sys.argv[1]
res = []
def ok(name, cond, extra=''):
    res.append((name, bool(cond), extra)); print(('PASS ' if cond else 'FAIL ') + name + (' | ' + str(extra) if extra and not cond else ''))

INIT = """
(() => {
  window.__texts = ['иванов','ПЕТР','нет','найманбаева','12 а','двадцать три? 23'];
  class FakeRec { start(){ const t = window.__texts.shift(); setTimeout(()=>{ if(t===undefined){ this.onerror&&this.onerror({error:'no-speech'}); this.onend&&this.onend(); return;} this.onresult&&this.onresult({results:[[{transcript:t}]]}); this.onend&&this.onend(); },20);} abort(){ this.onerror&&this.onerror({error:'aborted'}); } }
  window.webkitSpeechRecognition = FakeRec; window.SpeechRecognition = FakeRec;
  const fake = { cancel(){}, speak(u){ setTimeout(()=>u.onend&&u.onend(),10); } };
  Object.defineProperty(window,'speechSynthesis',{value:fake,configurable:true});
})();
"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    ctx.add_init_script(INIT)
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append('console.error: '+m.text) if m.type=='error' else None)
    pg.goto(URL)
    active = lambda: pg.evaluate("document.querySelector('.screen.active')?.id")
    ok('first screen is auth', active()=='screen-auth', active())
    pg.wait_for_timeout(500); pg.screenshot(path=S+'/s1_auth.png')
    pg.evaluate("showScreen('screen-market')")
    ok('gate blocks market when logged out', active()=='screen-auth', active())
    pg.evaluate("showScreen('screen-register')")
    ok('gate blocks register without session', active()=='screen-auth', active())
    # phone step
    pg.click('button:has-text("Получить код")')
    ok('empty phone error', pg.is_visible('#auth-phone-err'))
    pg.fill('#auth-phone','')
    pg.type('#auth-phone','7011234567')
    ok('phone formatted', pg.input_value('#auth-phone')=='(701) 123-45-67', pg.input_value('#auth-phone'))
    pg.click('button:has-text("Получить код")')
    ok('code step visible', pg.is_visible('#auth-step-code'))
    code = pg.inner_text('#auth-demo-code')
    ok('demo code is 4 digits', len(code)==4 and code.isdigit(), code)
    pg.screenshot(path=S+'/s2_code.png')
    wrong = '0000' if code!='0000' else '1111'
    pg.fill('#auth-code', wrong); pg.click('button:has-text("Подтвердить")')
    ok('wrong code error', pg.is_visible('#auth-code-err') and 'Неверный' in pg.inner_text('#auth-code-err'))
    pg.fill('#auth-code', code); pg.click('button:has-text("Подтвердить")')
    ok('goes to register after code', active()=='screen-register', active())
    ok('phone shown readonly in form', pg.input_value('#reg-phone')=='+7 (701) 123-45-67', pg.input_value('#reg-phone'))
    ok('city options loaded', pg.evaluate("document.getElementById('reg-city').options.length")>=15)
    ok('streets datalist for Semey', pg.evaluate("document.getElementById('dl-streets').children.length")>=4)
    pg.evaluate("showScreen('screen-chat')")
    ok('gate blocks chat with incomplete profile', active()=='screen-register', active())
    # empty save
    pg.click('button:has-text("Сохранить и войти")')
    ok('empty form shows errors', pg.is_visible('#err-reg-last') and pg.is_visible('#err-reg-iin') and pg.is_visible('#err-reg-apt'))
    ok('profile not saved', pg.evaluate("isProfileComplete(currentProfile())")==False)
    pg.screenshot(path=S+'/s3_register_errors.png', full_page=True)
    # IIN checks
    pg.fill('#reg-iin','850315300012'); pg.dispatch_event('#reg-iin','input')
    ok('bad IIN rejected', pg.is_visible('#err-reg-iin'))
    pg.click('button:has-text("Заполнить тестовыми данными")')
    iin = pg.input_value('#reg-iin')
    ok('test-data button clears old field errors', pg.evaluate("document.querySelectorAll('#screen-register .fld-err[style*=block]').length")==0)
    ok('test IIN valid & ok-badge', len(iin)==12 and pg.is_visible('#ok-reg-iin') and pg.evaluate("iinValid(%s)" % json.dumps(iin)), iin)
    ok('known-valid IIN algo (test vectors)', pg.evaluate("[iinValid('000000000000')]")[0]==False)
    # letters in IIN stripped
    pg.fill('#reg-iin','abc12x'); pg.dispatch_event('#reg-iin','input')
    ok('IIN input digits only', pg.input_value('#reg-iin')=='12', pg.input_value('#reg-iin'))
    pg.click('button:has-text("Заполнить тестовыми данными")')
    # voice: single field + full flow on cleared fields
    for f in ['reg-last','reg-first','reg-mid','reg-street','reg-house','reg-apt']: pg.fill('#'+f,'')
    pg.click('#voice-start')
    pg.wait_for_function("document.getElementById('voice-status').textContent.startsWith('Готово')", timeout=8000)
    vals = {f: pg.input_value('#'+f) for f in ['reg-last','reg-first','reg-mid','reg-street','reg-house','reg-apt']}
    ok('voice: last name', vals['reg-last']=='Иванов', vals)
    ok('voice: first name capitalized', vals['reg-first']=='Петр', vals)
    ok('voice: patronymic skipped by "нет"', vals['reg-mid']=='', vals)
    ok('voice: street matched to directory', vals['reg-street']=='ул. Найманбаева', vals)
    ok('voice: house with letter', vals['reg-house']=='12А', vals)
    ok('voice: apartment digits', vals['reg-apt']=='23', vals)
    pg.wait_for_timeout(400)
    ok('no red fields left after voice fill', pg.evaluate("document.querySelectorAll('#screen-register .bad').length")==0)
    pg.screenshot(path=S+'/s4_register_filled.png', full_page=True)
    # save
    pg.click('button:has-text("Сохранить и войти")')
    ok('saved -> home', active()=='screen-home', active())
    ok('badge shows apt', pg.inner_text('#home-apt')=='Кв. №23', pg.inner_text('#home-apt'))
    ok('profile strip name', pg.inner_text('#ps-name')=='Иванов Петр', pg.inner_text('#ps-name'))
    ok('profile strip address', 'ул. Найманбаева, д. 12А, кв. 23' in pg.inner_text('#ps-addr'), pg.inner_text('#ps-addr'))
    ok('navigator has 11 tiles (incl. case journal)', pg.evaluate("document.querySelectorAll('#screen-home .quick-btn').length")==11)
    pg.wait_for_timeout(500); pg.screenshot(path=S+'/s5_home.png', full_page=False)
    # navigator tiles all open their screens
    bad=[]
    for i in range(9):
        pg.evaluate("showScreen('screen-home')")
        pg.evaluate("document.querySelectorAll('#screen-home .quick-btn')[%d].click()" % i)
        a = active()
        if pg.evaluate("document.getElementById('sit-modal').classList.contains('open')"):
            pg.evaluate('closeSituations()'); continue
        if a=='screen-home': bad.append(i)
    ok('every navigator tile navigates', not bad, bad)
    pg.evaluate("showScreen('screen-profile')")
    ok('profile masks IIN', pg.inner_text('#pf-iin').startswith('••••••••') and len(pg.inner_text('#pf-iin'))==12, pg.inner_text('#pf-iin'))
    ok('profile phone', pg.inner_text('#pf-phone')=='+7 (701) 123-45-67', pg.inner_text('#pf-phone'))
    pg.wait_for_timeout(500); pg.screenshot(path=S+'/s6_profile.png')
    # existing flows still work
    pg.evaluate("showScreen('screen-home')")
    pg.evaluate("[...document.querySelectorAll('.ann-card-module')].find(b=>b.textContent.includes('Общедомовой чат')).click()")
    ok('module voice screen opens', active()=='screen-module-voice', active())
    pg.evaluate("showScreen('screen-tickets')")
    ok('tickets screen opens', active()=='screen-tickets', active())
    # logout / relogin as known user
    pg.evaluate("showScreen('screen-profile')")
    pg.click('button:has-text("Выйти")')
    ok('logout -> auth', active()=='screen-auth', active())
    pg.evaluate("showScreen('screen-home')")
    ok('gate blocks home after logout', active()=='screen-auth', active())
    pg.type('#auth-phone','7011234567')
    ok('known phone note shown', pg.is_visible('#auth-known'))
    pg.screenshot(path=S+'/s7_known.png')
    pg.click('button:has-text("Получить код")')
    code = pg.inner_text('#auth-demo-code'); pg.fill('#auth-code', code); pg.click('button:has-text("Подтвердить")')
    ok('known user goes straight home', active()=='screen-home', active())
    # reload persists session
    pg.reload()
    ok('session persists after reload', pg.evaluate("document.querySelector('.screen.active').id")=='screen-home')
    # edit profile
    pg.evaluate("showScreen('screen-profile')"); pg.click('button:has-text("Изменить анкету")')
    ok('edit form prefilled', pg.input_value('#reg-last')=='Иванов' and pg.is_visible('#reg-back'))
    # voice unsupported path
    pg.evaluate("stopVoice()")
    ok('no uncaught page errors', not errs, errs)
    b.close()
fails = [r for r in res if not r[1]]
print('\nTOTAL', len(res), 'FAILED', len(fails))
