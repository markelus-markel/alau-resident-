import os
import sys
import json
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
MOCK = """
window.__recs=[]; window.__spoken=[]; window.__speaking=false;
class FakeSR{constructor(){window.__recs.push(this);} start(){} stop(){setTimeout(()=>this.onend&&this.onend(),10);} abort(){}
 emit(a){this.onresult({results:a.map(([t,f])=>{const r=[{transcript:t}]; r.isFinal=f; return r;})});} }
window.SpeechRecognition=FakeSR; window.webkitSpeechRecognition=FakeSR;
window.SpeechSynthesisUtterance=function(t){this.text=t};
Object.defineProperty(window,'speechSynthesis',{value:{get speaking(){return window.__speaking},speak:u=>{window.__spoken.push(u.text)},cancel(){}},configurable:true});
"""
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', '/home/claude/alau-resident-/index.html')
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    g("showScreen('screen-chat')"); g("switchChatTab('bot')")
    last = lambda: g("(()=>{const m=chatBox().box.bot;return m[m.length-1]})()")
    rec = lambda: g("document.getElementById('bot-mic').classList.contains('rec')")
    banner = lambda: g("getComputedStyle(document.getElementById('bot-listen')).display")!='none'
    nrec = lambda: g("__recs.length")
    # 1. вопрос набран руками: микрофон сам не включается
    g("botAsk('сломался замок','text')"); pg.wait_for_timeout(500)
    ok('typed question: mic stays off', nrec()==0 and not rec() and not banner(), nrec())
    g("botQa=null")
    # 2. вопрос голосом, озвучка идёт: микрофон ждёт её конца
    g("window.__speaking=true"); g("botAsk('сломался замок','voice')"); pg.wait_for_timeout(700)
    ok('voice question: mic waits while the assistant is still speaking', nrec()==0 and not rec(), nrec())
    g("window.__speaking=false"); pg.wait_for_timeout(700)
    ok('after the speech ends the mic turns on by itself', nrec()==1 and rec(), nrec())
    ok('a visible "listening" bar is shown', banner() and 'Слушаю' in g("document.getElementById('bot-listen-text').textContent"), g("document.getElementById('bot-listen-text').textContent"))
    # 3. ответ голосом продолжает разговор: следующий вопрос и снова включённый микрофон
    g("__recs[__recs.length-1].emit([['снаружи',false],['снаружи не могу',false],['снаружи не могу войти',false]])")
    ok('live words are shown in the bar', 'снаружи не могу войти' in g("document.getElementById('bot-listen-text').textContent"), g("document.getElementById('bot-listen-text').textContent"))
    g("__recs[__recs.length-1].stop()"); pg.wait_for_timeout(700)
    ok('voice answer is accepted: next question', 'следы взлома' in last()['text'], last()['text'][:120])
    ok('mic turns on again for the next question', nrec()==2 and rec() and banner(), nrec())
    # 4. тишина: микрофон выключается, кнопка остаётся
    g("__recs[__recs.length-1].stop()"); pg.wait_for_timeout(500)
    ok('silence: mic and bar turn off', not rec() and not banner())
    ok('answer buttons and mic button are still there', any(a['do']=='qa-mic' for a in last()['actions']), last()['actions'])
    # 5. нажатие кнопки ответа в голосовом разговоре: следующий вопрос, микрофон включается
    n = nrec(); pg.click('#bot-thread .tkt-btn:text-is("Нет следов") >> nth=-1'); pg.wait_for_timeout(700)
    ok('button answer in a voice chat: next question and the mic again', 'запасной ключ' in last()['text'] and nrec()==n+1 and rec(), (last()['text'][:80], nrec(), n))
    # 6. конец опроса: микрофон не включается
    g("__recs[__recs.length-1].emit([['нет',true]])"); g("__recs[__recs.length-1].stop()"); pg.wait_for_timeout(700)
    ok('end of questions: ticket offer, mic stays off', 'Создать заявку' in last()['text'] and not rec() and not banner(), last()['text'][-100:])
    # 7. кнопка «Ответить голосом» работает вручную
    g("botQa=null"); g("botAsk('сломался замок','text')"); n = nrec()
    pg.click('#bot-thread .tkt-btn:text-is("🎙️ Ответить голосом") >> nth=-1'); pg.wait_for_timeout(200)
    ok('manual "answer by voice" button turns the mic on', nrec()==n+1 and rec() and banner(), (nrec(), n))
    pg.click('#bot-listen'); pg.wait_for_timeout(300)
    ok('tap on the bar finishes listening', not rec() and not banner())
    pg.screenshot(path=S + '/qa_mic.png')
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
