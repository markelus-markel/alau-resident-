import os
import sys
import json
import shutil
import tempfile
import threading
import functools
import http.server
import importlib.util
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INDEX = os.environ.get('ALAU_INDEX', os.path.join(ROOT, 'index.html'))
spec = importlib.util.spec_from_file_location('gen_voice', os.path.join(ROOT, 'tools', 'gen_voice.py'))
gv = importlib.util.module_from_spec(spec); spec.loader.exec_module(gv)
GUIDE = json.load(open(os.path.join(ROOT, 'registry', 'guide.json'), encoding='utf-8'))['text']
sits = json.load(open(os.path.join(ROOT, 'registry', 'situations.json'), encoding='utf-8'))['situations']
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
MOCK = """
window.__spoken=[]; window.__clips=[];
window.SpeechSynthesisUtterance=function(t){this.text=t};
let sp=false; Object.defineProperty(window,'speechSynthesis',{value:{get speaking(){return sp},speak:u=>{window.__spoken.push(u.text)}, cancel(){}},configurable:true});
window.Audio=function(src){this.src=src;this.paused=true;this.ended=false;this.play=()=>{this.paused=false;window.__clips.push(src);return Promise.resolve()};this.pause=()=>{this.paused=true};};
"""
# готовим папку с записями: у Sarah и Brian есть всё, у Alice и George нет; у Brian текст «пожар» устарел
tmp = tempfile.mkdtemp(prefix='alau-voice-')
shutil.copy(INDEX, os.path.join(tmp, 'index.html'))
def put(voice, stale=()):
    d = os.path.join(tmp, 'audio', 'sit', voice); os.makedirs(d)
    man = {'hello': gv.HELLO, 'guide': GUIDE}
    for s in sits:
        man[s['id']] = gv.now_text(s); man[s['id'] + '-full'] = gv.full_text(s)
    for k in stale: man[k] = 'устаревший текст'
    for k in man: open(os.path.join(d, k + '.mp3'), 'wb').write(b'ID3')
    json.dump(man, open(os.path.join(d, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False)
put('Sarah'); put('Brian', stale=('fire', 'guide'))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory=tmp))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = 'http://127.0.0.1:%d/index.html' % srv.server_address[1]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    # 1. без записей (файл открыт напрямую, fetch недоступен): раздела выбора нет, память читает голос телефона
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('file://' + INDEX); pg.evaluate(SEED); pg.reload(); g = pg.evaluate; pg.wait_for_timeout(300)
    g("showScreen('screen-profile')")
    ok('no recordings: voice card hidden', g("getComputedStyle(document.getElementById('voice-card')).display")=='none')
    g("openSituations('gas')"); pg.wait_for_timeout(200)
    ok('no recordings: system voice reads', len(g("__spoken"))==1 and g("__clips.length")==0)
    ok('no recordings: no voice-choice button in memo', not g("!!document.getElementById('sit-voice')"))
    ok('no page errors (no recordings)', not errs, errs); ctx.close()
    # 2. с записями
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate; pg.wait_for_timeout(500)
    ok('app text equals generator text for every memo (now and full)', all(g("(id=>[sitNowText(sitById(id)),sitFullText(sitById(id))])(%s)" % json.dumps(s['id']))==[gv.now_text(s), gv.full_text(s)] for s in sits))
    ok('hello phrase equals generator phrase', g("VOICE_HELLO")==gv.HELLO)
    ok('guide text in registry/guide.json equals the app text', g("guideText()")==GUIDE)
    g("showScreen('screen-profile')")
    ok('voice card visible', g("getComputedStyle(document.getElementById('voice-card')).display")!='none')
    ok('title asks to choose a voice', 'Выберите, пожалуйста, голос помощника' in g("document.getElementById('voice-card').textContent"))
    ok('only voices with recordings offered (+ phone voice)', g("[...document.querySelectorAll('#voice-list input')].map(i=>i.value)")==['', 'Sarah', 'Brian'], g("[...document.querySelectorAll('#voice-list input')].map(i=>i.value)"))
    ok('phone voice selected by default', g("document.querySelector('#voice-list input:checked').value")=='')
    pg.screenshot(path=S + '/voice_card.png')
    pg.click('#voice-list input[value=Sarah]'); pg.wait_for_timeout(300)
    ok('choice saved', g("lsGet(LS_VOICE,'')")=='Sarah')
    ok('choosing a voice plays its hello clip', g("__clips")==['audio/sit/Sarah/hello.mp3'], g("__clips"))
    g("void(window.__clips=[])")
    pg.click('#voice-list >> text=Послушать >> nth=1'); pg.wait_for_timeout(300)
    ok('preview of another voice plays its own clip', g("__clips")==['audio/sit/Brian/hello.mp3'], g("__clips"))
    g("void(window.__clips=[])"); g("void(window.__spoken=[])")
    g("openSituations('gas')"); pg.wait_for_timeout(300)
    ok('danger memo auto-read with chosen recorded voice', g("__clips")==['audio/sit/Sarah/gas.mp3'] and g("__spoken.length")==0, (g("__clips"), g("__spoken")))
    g("clipStop()"); g("void(window.__clips=[])"); pg.click('#sit-tts'); pg.wait_for_timeout(300)
    ok('read-aloud button plays the full recording', g("__clips")==['audio/sit/Sarah/gas-full.mp3'] and g("__spoken.length")==0, (g("__clips"), g("__spoken")))
    pg.click('#sit-tts'); pg.wait_for_timeout(200)
    ok('second press stops the recording', g("clipPlaying()")==False)
    ok('voice button in memo opens profile voice card', (pg.click('#sit-voice'), g("document.querySelector('.screen.active').id")=='screen-profile')[1])
    # окно «Что умеет приложение» читает выбранный голос
    g("showScreen('screen-home')"); g("guideOpen()"); g("void(window.__clips=[])"); g("void(window.__spoken=[])")
    pg.click('#guide-tts'); pg.wait_for_timeout(300)
    ok('guide read aloud with the chosen recorded voice', g("__clips")==['audio/sit/Sarah/guide.mp3'] and g("__spoken.length")==0, (g("__clips"), g("__spoken")))
    pg.click('#guide-tts'); pg.wait_for_timeout(200)
    ok('second press stops the guide recording', g("clipPlaying()")==False)
    g("guideClose()"); g("showScreen('screen-profile')")
    # устаревший текст у Brian -> читает голос телефона
    pg.click('#voice-list input[value=Brian]'); pg.wait_for_timeout(200)
    g("void(window.__clips=[])"); g("void(window.__spoken=[])")
    g("openSituations('fire')"); pg.wait_for_timeout(300)
    ok('stale recording text -> system voice reads, clip not played', g("__clips.length")==0 and g("__spoken.length")==1 and 'пожар' in g("__spoken[0]").lower(), (g("__clips"), g("__spoken")))
    g("closeSituations()")
    g("guideOpen()"); g("void(window.__clips=[])"); g("void(window.__spoken=[])"); pg.click('#guide-tts'); pg.wait_for_timeout(300)
    ok('stale guide recording -> system voice reads the guide', g("__clips.length")==0 and g("__spoken.length")==1 and 'Я помощник AlauConcierge' in g("__spoken[0]"), (g("__clips"), g("__spoken")))
    g("guideClose()"); g("showScreen('screen-profile')")
    pg.click('#voice-list input[value=""]'); pg.wait_for_timeout(200)
    ok('phone voice choice saved', g("lsGet(LS_VOICE,'x')")=='')
    g("void(window.__clips=[])"); g("void(window.__spoken=[])")
    g("openSituations('gas')"); pg.wait_for_timeout(300)
    ok('phone voice: system voice reads, no clips', g("__clips.length")==0 and g("__spoken.length")==1)
    g("closeSituations()")
    # выбор переживает перезагрузку
    g("lsSet(LS_VOICE,'Sarah')"); pg.reload(); pg.wait_for_timeout(500)
    ok('choice survives reload', g("voiceChoice()")=='Sarah')
    # выбранный голос, файлов которого нет (Alice), не используется
    g("lsSet(LS_VOICE,'Alice')"); ok('voice without recordings is ignored', g("voiceChoice()")=='')
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
srv.shutdown(); shutil.rmtree(tmp, ignore_errors=True)
print('TOTAL', len(res), 'FAILED', res.count(False))
