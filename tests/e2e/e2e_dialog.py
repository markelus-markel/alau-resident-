import os
import sys
import json
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
MOCK = """
window.__recs=[]; window.__spoken=[]; window.__ticks=0;
class FakeSR{constructor(){window.__recs.push(this);} start(){} stop(){setTimeout(()=>this.onend&&this.onend(),10);} abort(){}
 emit(a){this.onresult({results:a.map(([t,f])=>{const r=[{transcript:t}]; r.isFinal=f; return r;})});} }
window.SpeechRecognition=FakeSR; window.webkitSpeechRecognition=FakeSR;
window.SpeechSynthesisUtterance=function(t){this.text=t};
Object.defineProperty(window,'speechSynthesis',{value:{speaking:false,speak:u=>{window.__spoken.push(u.text)},cancel(){window.__cancelled=(window.__cancelled||0)+1}},configurable:true});
window.AudioContext=function(){this.state='running';this.currentTime=0;this.destination={};this.resume=()=>{};
  this.createOscillator=()=>{window.__ticks++;return {type:'',frequency:{value:0},connect(){},start(){},stop(){}}};
  this.createGain=()=>({gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){}});};
"""
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', '/home/claude/alau-resident-/index.html')
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    shown = lambda: g("getComputedStyle(document.getElementById('dlg')).display")!='none'
    txt = lambda: g("document.getElementById('dlg-text').textContent")
    last = lambda: g("(()=>{const m=chatBox().box.bot;return m[m.length-1]})()")
    opts = lambda: g("[...document.querySelectorAll('#dlg-opts button')].map(b=>b.textContent)")
    g("showScreen('screen-chat')"); g("switchChatTab('bot')")
    # 1. вопрос набран руками: экран диалога не открывается
    g("botAsk('сломался замок','text')"); pg.wait_for_timeout(200)
    ok('typed question: no dialog screen', not shown())
    g("botQa=null")
    # 2. голосовой вопрос открывает экран и печатает ответ постепенно
    g("dlgCps=60"); g("void(window.__ticks=0)"); g("botAsk('сломался замок входной двери','voice')"); pg.wait_for_timeout(250)
    ok('voice question opens the dialog screen', shown())
    mid = txt(); full = last()['text']
    ok('text is being typed: a part of the answer is on the screen', 0 < len(mid.replace('▍','')) < len(full), (len(mid), len(full)))
    ok('answer buttons are hidden until the text is typed', opts()==[], opts())
    ok('light tap sounds are played while typing', g("__ticks")>0, g("__ticks"))
    ok('the question the user asked is shown', 'Вы: сломался замок входной двери' in g("document.getElementById('dlg-me').textContent"), g("document.getElementById('dlg-me').textContent"))
    pg.wait_for_timeout(10000)
    ok('typed text equals what the assistant says (the same message)', txt()==full and '\u0301' not in txt(), txt()[:80])
    ok('spoken text carries the same words', g("__spoken[0]").replace('\u0301','').startswith(full.replace('\n','. ')[:60]), g("__spoken[0]")[:80])
    ok('typing is over: cursor gone, answer buttons shown', '▍' not in txt() and opts()[:3]==['Внутри, дверь не открывается', 'Снаружи, не могу войти', 'Замок в подъезде или общая дверь'], opts())
    # 3. ответ кнопкой на экране диалога: следующий вопрос печатается там же
    g("dlgCps=3000"); pg.click('#dlg-opts button:text-is("Внутри, дверь не открывается")'); pg.wait_for_timeout(500)
    ok('button answer: next question is typed on the same screen', shown() and 'ребёнок, пожилой или больной' in txt(), txt()[:100])
    ok('user line shows the chosen answer', 'Вы: Внутри, дверь не открывается' in g("document.getElementById('dlg-me').textContent"))
    ok('new answer buttons: Да, Нет and the mic', opts()[:2]==['Да', 'Нет'] and '🎙️ Ответить голосом' in opts(), opts())
    # 4. звук можно выключить
    g("dlgSound()"); g("void(window.__ticks=0)"); g("dlgCps=30"); pg.click('#dlg-opts button:text-is("Нет")'); pg.wait_for_timeout(600)
    ok('sound switched off: no taps, icon changed', g("__ticks")==0 and g("document.getElementById('dlg-snd').textContent")=='🔕', g("__ticks"))
    ok('sound choice is stored', g("lsGet(LS_DLGSND,true)")==False)
    g("dlgSound()")
    # 5. нажатие на текст допечатывает его сразу
    g("dlgCps=3"); g("botQa=null"); g("botAsk('сломался замок','voice')"); pg.wait_for_timeout(300)
    ok('slow typing in progress', '▍' in txt())
    pg.click('#dlg-text'); ok('tap on the text finishes it at once and shows the buttons', '▍' not in txt() and len(opts())>=3 and txt()==last()['text'], (txt()[-40:], opts()))
    # 6. микрофон: полоса «Слушаю…» видна в диалоге
    g("dlgCps=3000"); pg.click('#dlg-mic'); pg.wait_for_timeout(200)
    ok('listening bar is visible inside the dialog', g("getComputedStyle(document.getElementById('dlg-listen')).display")!='none')
    g("__recs[__recs.length-1].emit([['снаружи',false],['снаружи не могу войти',false]])")
    ok('live words are shown in the dialog bar', 'снаружи не могу войти' in g("document.getElementById('dlg-listen-text').textContent"))
    g("__recs[__recs.length-1].stop()"); pg.wait_for_timeout(800)
    ok('voice answer moves the dialog on', 'следы взлома' in txt(), txt()[:80])
    # 7. конец: заявка создаётся с экрана диалога
    pg.click('#dlg-opts button:text-is("Нет следов")'); pg.wait_for_timeout(500)
    pg.click('#dlg-opts button:text-is("Нет")'); pg.wait_for_timeout(500)
    ok('end of questions: ticket offer with yes and no', 'Создать заявку' in txt() and '✅ Да' in opts(), txt()[-120:])
    n0 = g("ticketBox().box.list.length"); pg.click('#dlg-opts button:text-is("✅ Да")'); pg.wait_for_timeout(500)
    ok('ticket is created from the dialog screen', g("ticketBox().box.list.length")==n0+1 and shown(), (g("ticketBox().box.list.length"), n0))
    # 8. закрытие
    g("botMic()"); pg.wait_for_timeout(100); g("void(window.__cancelled=0)")
    pg.click('#dlg-close'); pg.wait_for_timeout(200)
    ok('close: screen hidden, mic and speech stopped', not shown() and not g("botListening") and g("__cancelled")>=1)
    g("botAsk('сломался замок','voice')"); pg.wait_for_timeout(300)
    pg.click('#dlg-chat'); pg.wait_for_timeout(200)
    ok('"Открыть чат" closes the dialog and keeps the chat on the last answer', not shown() and g("document.querySelector('.screen.active').id")=='screen-chat' and g("(()=>{const t=document.getElementById('bot-thread');return t.scrollHeight-t.scrollTop-t.clientHeight<5})()"))
    # 9. другая голосовая команда тоже показывается на экране диалога
    g("botQa=null"); g("dlgCps=3000"); g("botAsk('где мои счета','voice')"); pg.wait_for_timeout(500)
    ok('any voice command gets the dialog screen', shown() and 'Счета' in txt() and any('Открыть «Счета»' in o for o in opts()), (txt()[:60], opts()))
    pg.screenshot(path=S + '/dialog.png')
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
