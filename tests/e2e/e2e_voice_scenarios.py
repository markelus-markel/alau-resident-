import os
import sys
import json
import shutil
import tempfile
import threading
import functools
import http.server
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INDEX = os.environ.get('ALAU_INDEX', os.path.join(ROOT, 'index.html'))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
MOCK = """
window.__clips=[]; window.__spoken=[]; window.__recs=[]; window.__aud=null;
class FakeSR{constructor(){window.__recs.push(this);} start(){} stop(){setTimeout(()=>this.onend&&this.onend(),10);} abort(){}
 emit(a){this.onresult({results:a.map(([t,f])=>{const r=[{transcript:t}]; r.isFinal=f; return r;})});} }
window.SpeechRecognition=FakeSR; window.webkitSpeechRecognition=FakeSR;
window.SpeechSynthesisUtterance=function(t){this.text=t};
Object.defineProperty(window,'speechSynthesis',{value:{speaking:false,speak:u=>{window.__spoken.push(u.text)},cancel(){}},configurable:true});
window.Audio=function(src){this.src=src;this.paused=true;this.ended=false;window.__aud=this;this.play=()=>{this.paused=false;window.__clips.push(src);return Promise.resolve()};this.pause=()=>{this.paused=true};};
"""
scen = json.load(open(os.path.join(ROOT, 'registry', 'scenarios.json'), encoding='utf-8'))['clips']
HELLO = 'Здравствуйте! Я помощник AlauConcierge. Так я буду читать вам подсказки.'
tmp = tempfile.mkdtemp(prefix='alau-scen-')
shutil.copy(INDEX, os.path.join(tmp, 'index.html'))
d = os.path.join(tmp, 'audio', 'sit', 'Sarah'); os.makedirs(d)
man = {'hello': HELLO}
for c in scen: man[c['key']] = c['text']
man['qa-lock-where-1'] = 'устаревший текст'
for k in man: open(os.path.join(d, k + '.mp3'), 'wb').write(b'ID3')
json.dump(man, open(os.path.join(d, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory=tmp))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = 'http://127.0.0.1:%d/index.html' % srv.server_address[1]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate; pg.wait_for_timeout(500)
    # 1. тексты реплик в приложении равны реестру, по которому заказывается запись
    app = g("qaClips()")
    ok('app clip texts equal registry/scenarios.json (the order for recording)', app==scen, (len(app), len(scen)))
    ok('every clip key is unique and file-safe', len({c['key'] for c in app})==len(app) and all(__import__('re').fullmatch(r'qa-[a-z]+(-[a-z]+-\d+|-start)', c['key']) for c in app), [c['key'] for c in app][:3])
    ok('no digits-only phones outside the national list in spoken texts', all(set(__import__('re').findall(r'(?<!\d)\d{3}(?!\d)', c['text'])) <= {'112','101','102','103','104'} for c in app))
    g("lsSet(LS_VOICE,'Sarah')"); g("showScreen('screen-chat')"); g("switchChatTab('bot')")
    last = lambda: g("(()=>{const m=chatBox().box.bot;return m[m.length-1]})()")
    ok('voice Sarah is available', g("voiceChoice()")=='Sarah')
    # 2. начало сценария играет запись, системный голос молчит
    g("botAsk('сломался замок входной двери','voice')"); pg.wait_for_timeout(500)
    ok('scenario start plays the recorded clip, not the phone voice', g("__clips")==['audio/sit/Sarah/qa-lock-start.mp3'] and g("__spoken.length")==0, (g("__clips"), g("__spoken")))
    # 3. микрофон ждёт, пока запись играет
    ok('mic does not start while the recording is playing', g("__recs.length")==0, g("__recs.length"))
    g("__aud.paused=true; __aud.ended=true"); pg.wait_for_timeout(1200)
    ok('mic starts after the recording has ended', g("__recs.length")==1 and g("document.getElementById('bot-mic').classList.contains('rec')"), g("__recs.length"))
    # 4. ответ кнопкой в диалоге: следующая реплика тоже записанная
    g("stopAllMics()"); g("void(window.__clips=[])")
    pg.click('#dlg-opts button:text-is("Внутри, дверь не открывается")'); pg.wait_for_timeout(500)
    ok('button answer plays its own recorded clip', g("__clips")==['audio/sit/Sarah/qa-lock-where-0.mp3'], g("__clips"))
    g("__aud.paused=true; __aud.ended=true"); g("stopAllMics()"); g("void(window.__clips=[])")
    # 5. ответ голосом тоже
    g("botAsk('да','voice')"); pg.wait_for_timeout(500)
    ok('voice answer plays the end clip with the ticket question', g("__clips")==['audio/sit/Sarah/qa-lock-inside-0.mp3'] and 'Создать заявку по этому вопросу' in scen[[c['key'] for c in scen].index('qa-lock-inside-0')]['text'], g("__clips"))
    g("__aud.paused=true; __aud.ended=true")
    # 6. устаревшая запись -> системный голос с тем же текстом
    g("botQa=null"); g("dlgClose(false)"); g("void(window.__clips=[])"); g("void(window.__spoken=[])")
    g("botAsk('сломался замок','voice')"); pg.wait_for_timeout(400); g("__aud.paused=true; __aud.ended=true"); g("stopAllMics()"); g("void(window.__clips=[])")
    g("botAsk('снаружи','voice')"); pg.wait_for_timeout(500)
    sp = g("__spoken")
    ok('stale recording -> the phone voice says the same words', g("__clips.length")==0 and len(sp)==1 and 'запасной ключ' not in sp[0] and 'следы взлома' in sp[0].replace('́',''), sp)
    # 7. без выбранного голоса: системный голос, текст озвучки без эмодзи и нумерации
    g("lsSet(LS_VOICE,'')"); g("dlgClose(false)"); g("botQa=null"); g("void(window.__clips=[])"); g("void(window.__spoken=[])")
    g("botAsk('отключился свет','voice')"); pg.wait_for_timeout(400)
    sp = g("__spoken")
    ok('phone voice: clean spoken text (no emoji, no numbering) with the answer options', len(sp)==1 and '💡' not in sp[0] and not __import__('re').search(r'(?<!\d)\d\. ', sp[0]) and 'Ответьте: Да, или Нет' in sp[0], sp)
    ok('no clips without a chosen recorded voice', g("__clips.length")==0)
    ok('no page errors', not errs, errs)
    b.close()
srv.shutdown(); shutil.rmtree(tmp, ignore_errors=True)
print('TOTAL', len(res), 'FAILED', res.count(False))
