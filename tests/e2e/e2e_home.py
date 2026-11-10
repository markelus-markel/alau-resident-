import os
import sys
import json
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
MOCK = """
window.__recs=[];
class FakeSR{constructor(){window.__recs.push(this);} start(){} stop(){setTimeout(()=>this.onend&&this.onend(),10);} abort(){}
 emit(a){this.onresult({results:a.map(([t,f])=>{const r=[{transcript:t}]; r.isFinal=f; return r;})});} }
window.SpeechRecognition=FakeSR; window.webkitSpeechRecognition=FakeSR;
window.SpeechSynthesisUtterance=function(t){this.text=t};
Object.defineProperty(window,'speechSynthesis',{value:{speaking:false,speak(){},cancel(){}},configurable:true});
"""
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', '/home/claude/alau-resident-/index.html')
def fresh(b, w, h):
    ctx = b.new_context(viewport={'width': w, 'height': h}); ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); return ctx, pg, errs
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    # маленький телефон: помощник виден без прокрутки
    ctx, pg, errs = fresh(b, 360, 640); g = pg.evaluate
    rect = lambda sel: g("(s=>{const r=document.querySelector(s).getBoundingClientRect();return {top:r.top,bottom:r.bottom}})(%s)" % json.dumps(sel))
    ok('small phone: assistant input visible without scrolling', rect('#home-ask-in')['bottom'] <= 640, rect('#home-ask-in'))
    ok('small phone: ask button visible without scrolling', rect('#home-ask-go')['bottom'] <= 640, rect('#home-ask-go'))
    ok('small phone: welcome visible without scrolling for a new resident', rect('#welcome-card')['bottom'] <= 640, rect('#welcome-card'))
    pg.wait_for_timeout(300); pg.screenshot(path=S + '/home_small.png'); ctx.close()
    # обычный телефон
    ctx, pg, errs = fresh(b, 390, 844); g = pg.evaluate
    ok('no big profile strip on home', g("!document.querySelector('.profile-strip')"))
    ok('header shows name and address', g("document.getElementById('home-who').textContent")=='Иванов Тест · Семей, ул. Найманбаева, д. 12, кв. 23', g("document.getElementById('home-who').textContent"))
    ok('header shows the apartment badge', g("document.getElementById('home-apt').textContent")=='Кв. №23')
    ok('calendar button sits in the header, to the right of the name block, with the apartment badge after it', g("(()=>{const w=document.getElementById('home-who').getBoundingClientRect(),c=document.getElementById('home-cal'),a=document.getElementById('home-apt').getBoundingClientRect(),r=c.getBoundingClientRect();return !!c.closest('.topbar')&&r.left>w.left&&r.right<=a.left+1&&r.top<90})()"))
    ok('the old calendar card is gone from the home body', g("!document.getElementById('cal-card')"))
    ok('assistant block comes before announcements', g("(()=>{const a=document.getElementById('home-ask'),n=[...document.querySelector('#screen-home .home-content').children],ia=n.indexOf(a),io=n.findIndex(e=>e.textContent.includes('Объявления и обсуждения'));return ia>=0&&io>ia})()"))
    ok('welcome comes before the assistant block for a new resident', g("(()=>{const w=document.getElementById('welcome-card'),a=document.getElementById('home-ask');return !!(w.compareDocumentPosition(a)&Node.DOCUMENT_POSITION_FOLLOWING)})()"))
    ok('navigator has 8 tiles (voice, contacts, profile moved to the header menu)', g("document.querySelectorAll('#screen-home .quick-btn').length")==8)
    ok('assistant block is titled «Спросите у консьержа»', 'Спросите у консьержа' in g("document.querySelector('#home-ask > div').textContent") and 'Чем помочь' not in g("document.getElementById('home-ask').textContent"))
    ok('question field and microphone sit in one dashed frame', g("(()=>{const r=document.querySelector('#home-ask .ask-row');return getComputedStyle(r).borderTopStyle==='dashed'&&r.contains(document.getElementById('home-ask-in'))&&r.contains(document.getElementById('home-mic'))})()"))
    ok('question field shows the full hint when it grows on hover', (pg.hover('#home-ask-in'), pg.wait_for_timeout(350), g("(()=>{const e=document.getElementById('home-ask-in');return e.placeholder==='Например: пахнет газом, где мои счета'&&e.getBoundingClientRect().height>=80})()"))[2])
    ok('question field is smaller again when the pointer leaves', (pg.mouse.move(5, 5), pg.wait_for_timeout(350), g("document.getElementById('home-ask-in').getBoundingClientRect().height<50"))[2])
    pg.fill('#home-ask-in', 'a'); ok('typed text keeps the field big', (pg.mouse.move(5, 5), pg.wait_for_timeout(350), g("document.getElementById('home-ask-in').getBoundingClientRect().height>=80"))[2]); pg.fill('#home-ask-in', '')
    ok('microphone is 50% bigger than the old 38 px button', g("(()=>{const r=document.getElementById('home-mic').getBoundingClientRect();return Math.round(r.width)==57&&Math.round(r.height)==57})()"))
    ok('mic state label says off when not recording', g("(()=>{const e=document.querySelector('#home-ask .ms-off'),o=document.querySelector('#home-ask .ms-on');return getComputedStyle(e).display!=='none'&&getComputedStyle(o).display==='none'&&e.textContent==='выкл'})()"))
    pg.wait_for_timeout(300); pg.screenshot(path=S + '/home.png')
    # профиль достижим из шапки
    pg.click('#home-who'); ok('tap on name in header opens profile', g("document.querySelector('.screen.active').id")=='screen-profile')
    g("showScreen('screen-home')"); pg.click('#home-apt'); ok('tap on apartment badge opens profile', g("document.querySelector('.screen.active').id")=='screen-profile')
    g("showScreen('screen-home')")
    # пустой запрос
    pg.click('#home-ask-go'); ok('empty ask: stays on home and shows a hint', g("document.querySelector('.screen.active').id")=='screen-home' and 'Напишите или скажите' in g("document.getElementById('toast').textContent"))
    # текстовый запрос
    pg.fill('#home-ask-in', 'пахнет газом'); pg.press('#home-ask-in', 'Enter'); pg.wait_for_timeout(200)
    ok('typed question opens the assistant chat', g("document.querySelector('.screen.active').id")=='screen-chat' and g("document.getElementById('chatpane-bot').style.display")=='flex')
    th = g("document.getElementById('bot-thread').textContent")
    ok('assistant answers the typed question', 'пахнет газом' in th and 'Запах газа' in th, th[-300:])
    ok('input is cleared after sending', g("(showScreen('screen-home'),document.getElementById('home-ask-in').value)")=='')
    # «где мои счета»
    pg.fill('#home-ask-in', 'где мои счета'); pg.click('#home-ask-go'); pg.wait_for_timeout(200)
    ok('"где мои счета" gets the Счета button', 'Открыть «Счета»' in g("document.getElementById('bot-thread').textContent"))
    # голос
    g("showScreen('screen-home')"); n0 = g("__recs.length")
    pg.click('#home-mic'); ok('mic starts recording', g("document.getElementById('home-mic').classList.contains('rec')") and g("__recs.length")==n0+1)
    ok('mic state label says on while recording', g("(()=>{const e=document.querySelector('#home-ask .ms-off'),o=document.querySelector('#home-ask .ms-on');return getComputedStyle(e).display==='none'&&getComputedStyle(o).display!=='none'&&o.textContent==='вкл'})()"))
    g("__recs[__recs.length-1].emit([['пахнет газом на лестнице',true]])")
    ok('live text appears in the field', 'пахнет газом' in g("document.getElementById('home-ask-in').value"))
    pg.click('#home-mic'); pg.wait_for_timeout(400)
    ok('voice question goes to the assistant and is answered', g("document.querySelector('.screen.active').id")=='screen-chat' and 'на лестнице' in g("document.getElementById('bot-thread').textContent"))
    ok('voice question opens the dialog screen over the chat', g("getComputedStyle(document.getElementById('dlg')).display")!='none')
    g("dlgClose(false)")
    # быстрые кнопки
    g("showScreen('screen-home')"); pg.click('#home-chip-sit'); ok('chip "Что-то случилось" opens the situations', g("document.getElementById('sit-modal').classList.contains('open')")); g("closeSituations()")
    pg.click('#home-chip-bills'); ok('chip "Мои счета" opens the bills screen', g("document.querySelector('.screen.active').id")=='screen-bills')
    # нижняя панель
    g("showScreen('screen-home')")
    navs = g("[...document.querySelectorAll('.bottom-nav')].map(n=>[...n.querySelectorAll('.nav-label')].map(l=>l.textContent))")
    ok('every bottom bar has "Помощник" and no "Маркетплейс"', navs and all('Помощник' in n and 'Маркетплейс' not in n for n in navs), navs)
    ok('bottom bar keeps four items', all(len(n)==4 for n in navs), navs)
    pg.click('#screen-home .bottom-nav >> text=Помощник'); pg.wait_for_timeout(100)
    ok('"Помощник" in the bottom bar opens the assistant chat tab', g("document.querySelector('.screen.active').id")=='screen-chat' and g("document.getElementById('chatpane-bot').style.display")=='flex')
    # маркетплейс остаётся доступным из навигатора
    g("showScreen('screen-home')"); g("[...document.querySelectorAll('#screen-home .quick-btn')].find(b=>b.textContent.includes('Маркетплейс')).click()")
    ok('marketplace is still reachable from the navigator', g("document.querySelector('.screen.active').id")=='screen-market')
    # после закрытия знакомства помощник остаётся первым блоком
    g("showScreen('screen-home')"); pg.click('#welcome-later')
    ok('after "later" the assistant block stays on top', g("getComputedStyle(document.getElementById('welcome-card')).display")=='none' and g("document.getElementById('home-ask').getBoundingClientRect().top")<260, g("document.getElementById('home-ask').getBoundingClientRect().top"))
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
