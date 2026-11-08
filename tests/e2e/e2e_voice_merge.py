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
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
power = next(s for s in json.load(open(os.path.join(ROOT, 'registry', 'situations.json'), encoding='utf-8'))['situations'] if s['id'] == 'power')['ru']['title']
nowater = 'Нет воды'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('file://' + os.environ.get('ALAU_INDEX', os.path.join(ROOT, 'index.html'))); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    j = lambda parts: g("p=>vrJoin(p)", parts)
    # склейка кусков распознавания
    ok('join: ordinary final + interim', j(['привет', 'как дела'])=='привет как дела', j(['привет', 'как дела']))
    ok('join: cumulative snapshots collapse into the last', j(['Отключи', 'отключился', 'отключился свет', 'отключился свет в кварти', 'отключился свет в квартире'])=='отключился свет в квартире')
    ok('join: repeated identical snapshots collapse', j(['отключился свет в квартире']*4)=='отключился свет в квартире')
    ok('join: tail repeat is skipped', j(['свет в квартире', 'квартире'])=='свет в квартире')
    ok('join: empty and blank parts', j([])=='' and j(['', '  '])=='')
    ok('join: different phrases are kept in order', j(['пахнет газом', 'на лестнице'])=='пахнет газом на лестнице')
    # живой сценарий с телефона: микрофон помощника на главном экране
    n0 = g("__recs.length"); pg.click('#home-mic')
    g("__recs[__recs.length-1].emit([['Отключи',false],['отключился',false],['отключился свет',false],['отключился свет что мне',false],['отключился свет что мне делать',false]])")
    live = g("document.getElementById('home-ask-in').value")
    ok('phone-style cumulative results show clean live text', live=='отключился свет что мне делать', live)
    pg.click('#home-mic'); pg.wait_for_timeout(400)
    th = g("document.getElementById('bot-thread').textContent")
    me = g("chatBox().box.bot.filter(x=>x.role==='me').map(x=>x.text)")
    ok('the question reaches the assistant once and without repeats', len(me)==1 and me[0].lower().count('отключился')==1, me)
    ok('"отключился свет" gets the power memo, not water', power in th and nowater not in th, th[-400:])
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
