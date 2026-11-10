import os
import sys
import json
import re
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
MOCK = """
window.__spoken=[];
window.SpeechSynthesisUtterance=function(t){this.text=t};
Object.defineProperty(window,'speechSynthesis',{value:{speaking:false,speak:u=>{window.__spoken.push(u.text)}, cancel(){}},configurable:true});
"""
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', '/home/claude/alau-resident-/index.html')
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    vis = lambda sel: g("(s=>{const e=document.querySelector(s);return !!e&&getComputedStyle(e).display!=='none'})(%s)" % json.dumps(sel))
    active = lambda: g("document.querySelector('.screen.active').id")
    # 1. знакомство на главной
    ok('home: welcome card shown to a new resident', vis('#welcome-card') and active()=='screen-home')
    txt = g("document.getElementById('welcome-card').textContent")
    ok('assistant introduces itself and offers help', 'Я помощник AlauConcierge' in txt and 'Хотите, расскажу' in txt, txt)
    ok('welcome card does not change navigator tile count', g("document.querySelectorAll('#screen-home .quick-btn').length")==8)
    pg.wait_for_timeout(500); pg.screenshot(path=S + '/guide_welcome.png')
    # 2. «Позже» скрывает и запоминает для этого жильца
    pg.click('#welcome-later')
    ok('"later" hides the card', not vis('#welcome-card'))
    pg.reload(); ok('card stays hidden after reload', not vis('#welcome-card'))
    pg.click('#home-menu-btn')
    ok('permanent entry in the header menu', vis('#hm-guide'))
    # 3. окно «Что умеет приложение»
    pg.click('#hm-guide')
    ok('guide opens', g("document.getElementById('guide-modal').classList.contains('open')"))
    sub = g("document.getElementById('guide-sub').textContent")
    ok('guide explains the two ways to use the app', 'двумя способами' in sub and 'самому' in sub and 'вместе со мной' in sub, sub)
    n = g("APP_CAPS.length")
    ok('guide lists every capability', g("document.querySelectorAll('#guide-body .prof-row').length")==n and n>=9, n)
    body = g("document.getElementById('guide-body').textContent")
    ok('each capability shows how to use it alone', body.count('Самому:')==n)
    ok('capabilities with a phrase show how to use with the assistant', body.count('С помощником:')==g("APP_CAPS.filter(c=>c.ask).length"))
    pg.wait_for_timeout(500); pg.screenshot(path=S + '/guide_modal.png')
    # 4. целостность: каждая возможность ведёт на существующий экран, плитка есть на главной
    ids = g("APP_CAPS.map(c=>c.go)")
    scr = g("[...document.querySelectorAll('.screen')].map(s=>s.id)")
    ok('every capability points to an existing screen', all(i=='sit' or i in scr for i in ids), ids)
    tiles = g("[...document.querySelectorAll('#screen-home .quick-label')].map(e=>e.textContent)")
    named = re.findall(r'Плитка «([^»]+)»', body)
    ok('every named tile exists on the home screen', all(x in tiles for x in named), (named, tiles))
    # 5. «Открыть самому» ведёт в раздел
    for i, c in enumerate(g("APP_CAPS")):
        g("showScreen('screen-home')"); g("guideOpen()")
        pg.click('#guide-body .prof-row:nth-child(%d) >> text=Открыть самому' % (i + 1)); pg.wait_for_timeout(50)
        if c['go']=='sit': good = g("document.getElementById('sit-modal').classList.contains('open')"); g("closeSituations()")
        else: good = active()==c['go']
        if not good: ok('open alone: ' + c['title'], False, (c['go'], active())); break
    else: ok('"open alone" opens every section', True)
    # 6. «Показать с помощником» отправляет фразу и получает осмысленный ответ
    for i, c in enumerate(g("APP_CAPS")):
        if not (c['ask'] and c['try']): continue
        g("showScreen('screen-home')"); g("guideOpen()")
        pg.click('#guide-body .prof-row:nth-child(%d) >> text=Показать с помощником' % (i + 1)); pg.wait_for_timeout(100)
        last = g("(()=>{const m=chatBox().box.bot;return m[m.length-1].text})()")
        asked = g("(()=>{const m=chatBox().box.bot.filter(x=>x.role==='me');return m[m.length-1].text})()")
        ok('with assistant: "%s" gets a real answer' % c['ask'], active()=='screen-chat' and asked==c['ask'] and 'Не поняла' not in last, (asked, last))
    # фразы, которые что-то создают, не отправляются кнопкой автоматически
    ok('capabilities that create things have no one-tap send', all(not c['try'] for c in g("APP_CAPS") if re.match('(создай|внеси|напиши)', c['ask'])))
    # 7. помощник: вступление, кнопка и «что ты умеешь»
    g("showScreen('screen-chat')"); g("switchChatTab('bot')")
    first = g("document.querySelector('#bot-thread .chat-bubble').textContent")
    ok('assistant chat opens with a self-introduction', 'Здравствуйте! Я локальный помощник' in first and 'не нейросеть' in first and 'создай заявку' in first, first[:120])
    ok('assistant intro mentions the bills phrase', 'где мои счета' in first)
    pg.click('#bot-guide'); ok('intro button opens the guide', g("document.getElementById('guide-modal').classList.contains('open')")); g("guideClose()")
    g("botAsk('что ты умеешь','text')")
    ok('"что ты умеешь" offers the guide button', g("(()=>{const m=chatBox().box.bot;return (m[m.length-1].actions||[]).some(a=>a.do==='guide')})()"))
    pg.click('#bot-thread .tkt-btn >> text=Что умеет приложение >> nth=-1'); ok('answer button opens the guide', g("document.getElementById('guide-modal').classList.contains('open')")); g("guideClose()")
    # 8. маршрут «Счета» у помощника
    for q in ['где мои счета', 'как оплатить свет', 'сфотографировать квитанцию']:
        g("botAsk(%s,'text')" % json.dumps(q))
        ok('assistant routes "%s" to Счета' % q, g("(()=>{const m=chatBox().box.bot;return (m[m.length-1].actions||[]).some(a=>a.arg==='screen-bills')})()"))
    # 9. озвучка и закрытие
    g("showScreen('screen-home')"); g("guideOpen()"); g("void(window.__spoken=[])")
    pg.click('#guide-tts'); sp = g("__spoken")
    ok('guide is read aloud', len(sp)==1 and 'Я помощник AlauConcierge' in sp[0] and 'Самому:' in sp[0] and 'С помощником:' in sp[0], sp)
    ok('no invented phones in the guide', set(re.findall(r'\b\d{3}\b', g("guideText()")))<= {'112','101','102','103','104'}, re.findall(r'\b\d{3,}\b', g("guideText()")))
    pg.click('#guide-modal >> text=Закрыть'); ok('guide closes', not g("document.getElementById('guide-modal').classList.contains('open')"))
    # 10. второй жилец видит знакомство заново
    g("(()=>{const u=lsGet(LS_USERS,{});u['77012223344']=Object.assign({},u['77011234567'],{phone:'77012223344'});lsSet(LS_USERS,u);lsSet(LS_SESSION,'77012223344');})()")
    pg.reload(); ok('another resident sees the welcome again', vis('#welcome-card'))
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
