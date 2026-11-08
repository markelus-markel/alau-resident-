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
    pg=b.new_context(viewport={'width':390,'height':844}).new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g=pg.evaluate
    g("void(window.__spoken=[], window.speak=t=>{window.__spoken.push(t);return Promise.resolve()})")
    spoken=lambda: g("window.__spoken")
    clear=lambda: g("void(window.__spoken=[])")
    emerg=g("SITUATIONS.filter(s=>s.level==='emergency').map(s=>s.id)"); calm=g("SITUATIONS.filter(s=>s.level!=='emergency'&&!s.go).map(s=>s.id)")
    ok('registry has emergency and calm memos', len(emerg)>=2 and len(calm)>=3, (emerg,calm))
    # 1. опасная ситуация читается сразу
    lab=g("(()=>{openSituations('gas');return document.getElementById('sit-tts').textContent})()"); sp=spoken()
    ok('gas memo read aloud on open', len(sp)==1 and 'Запах газа' in sp[0] and 'сто двенадцать' in sp[0], sp)
    ok('first step of the memo is in the spoken text', g("SITUATIONS.find(s=>s.id==='gas').now[0]") in sp[0])
    ok('stop label shown while speaking', lab.startswith('⏹'), lab)
    pg.wait_for_timeout(900); ok('label restored when speech ends', 'Прочитать вслух' in g("document.getElementById('sit-tts').textContent"))
    every=True
    for sid in emerg:
        clear(); g("openSituations(%r)"%sid); sp=spoken(); every=every and len(sp)==1 and g("sitById(%r).title"%sid) in sp[0]
    ok('every emergency memo is read on open', every)
    # 2. спокойные не читаются сами
    clear(); g("openSituations(%r)"%calm[0]); ok('non-emergency memo is not read automatically', spoken()==[])
    clear(); g("openSituations()"); ok('list view is silent', spoken()==[])
    # 3. диктовка вопроса в поле заявки
    g("openSituations('gas')"); clear()
    g("sitAfterDictate('Что делать если запах газа что мне делать')"); sp=spoken()
    ok('dictated question in report field -> memo read aloud', len(sp)==1 and 'Что делать сейчас' in sp[0], sp)
    ok('dictated text put into the field unchanged', g("document.getElementById('sit-text').value")=='Что делать если запах газа что мне делать')
    clear(); g("sitAfterDictate('На кухне пахнет газом с утра')")
    ok('plain description (not a question) stays silent', spoken()==[] and g("document.getElementById('sit-text').value")=='На кухне пахнет газом с утра')
    clear(); g("sitAfterDictate('Подскажите, куда звонить')"); ok('"подскажите" counts as a question', len(spoken())==1)
    ok('question detector: negatives', not g("sitIsQuestion('')") and not g("sitIsQuestion(null)") and not g("sitIsQuestion('труба течёт в подвале')"))
    # 4. переключатель озвучки выключает всё
    g("document.getElementById('bot-tts').checked=false"); clear()
    g("openSituations('gas')"); g("sitAfterDictate('что мне делать')")
    ok('voice switch off -> nothing spoken automatically', spoken()==[])
    pg.click('#sit-tts'); ok('manual read-aloud button still works with switch off', len(spoken())==1, spoken())
    g("document.getElementById('bot-tts').checked=true")
    # 5. закрытие памятки останавливает речь
    called=g("(()=>{let c=0;const o=speechSynthesis.cancel.bind(speechSynthesis);speechSynthesis.cancel=()=>{c++;return o()};closeSituations();speechSynthesis.cancel=o;return c})()")
    ok('closing the memo cancels speech', called>=1, called)
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
