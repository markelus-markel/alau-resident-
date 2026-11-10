import os
import sys
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');lsSet(LS_WELCOME,{'77011234567':1});}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'index.html'))
PUT = """(o)=>{const iso=n=>{const d=new Date();d.setDate(d.getDate()+n);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')};
const p='77011234567';
lsSet(LS_BILLS,{[p]:(o.bills||[]).map((b,i)=>({id:'S-t'+i,kind:b.kind,amount:b.amount,due:b.off===null?'':iso(b.off),paid:!!b.paid,period:'',account:'',photo:null,created:new Date().toISOString()}))});
const day=o.day===undefined?0:(o.day==='today'?Math.min(new Date().getDate(),28):o.day);
lsSet(LS_METERS,{[p]:{readings:[],day:day}});}"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    # словарь
    V = g("DUTY_VOICE")
    ok('vocabulary has about a hundred words and every text is non-empty and unique', 90 <= len(V) <= 120 and all(V.values()) and len(set(V.values())) == len(V), len(V))
    ok('every bill kind has a recorded word equal to its name', g("BILL_KINDS.every(k => DUTY_VOICE['d-k-' + k[0]] === k[1].replace(/^\\S+\\s/, ''))"))
    ok('months come out in the genitive', V['d-m11'] == 'ноября' and V['d-m1'] == 'января' and V['d-m12'] == 'декабря', (V['d-m11'], V['d-m1']))
    # числа словами
    nk = lambda n: g("(n)=>dutyNumKeys(n)", n)
    words = lambda n: ' '.join(V['d-' + k] for k in nk(n))
    for n, w in [(1, 'один'), (12, 'двенадцать'), (21, 'двадцать один'), (100, 'сто'), (2000, 'две тысячи'), (3000, 'три тысячи'), (5000, 'пять тысяч'),
                 (8000, 'восемь тысяч'), (12500, 'двенадцать тысяч пятьсот'), (21000, 'двадцать одна тысяча'), (22345, 'двадцать две тысячи триста сорок пять'),
                 (100000, 'сто тысяч'), (999999, 'девятьсот девяносто девять тысяч девятьсот девяносто девять'), (1000, 'одна тысяча')]:
        ok(f'{n} -> «{w}»', words(n) == w, words(n))
    ok('zero and a million are not assembled', nk(0) is None and nk(1000000) is None)
    dk = lambda iso: g("(i)=>dutyDateKeys(i)", iso)
    ok('dates: 15th, 21st, 30th, 31st, 1st', dk('2026-11-15') == ['o15', 'm11'] and dk('2026-11-21') == ['n20', 'o1', 'm11'] and dk('2026-12-30') == ['o30', 'm12'] and dk('2026-01-31') == ['n30', 'o1', 'm1'] and dk('2026-02-01') == ['o1', 'm2'], [dk('2026-11-21'), dk('2026-01-31')])
    ok('bad date is not assembled', dk('сегодня') is None and dk('2026-13-01') is None)
    ik = lambda n: g("(n)=>dutyInKeys(n)", n)
    ok('days: today, tomorrow, 5, 21, 22, 11', ik(0) == ['today'] and ik(1) == ['tomorrow'] and ik(5) == ['in', 'n5', 'day5'] and ik(21) == ['in', 'n20', 'n1', 'day1'] and ik(22) == ['in', 'n20', 'n2', 'day2'] and ik(11) == ['in', 'n11', 'day5'], [ik(21), ik(11)])
    # сборка фразы
    g(PUT, {'bills': [{'kind': 'elec', 'amount': 12500, 'off': -3}, {'kind': 'water', 'amount': 8000, 'off': 5}], 'day': 'today'})
    q = g("dutyClipSeq()")
    ok('sequence: greeting, overdue count and sum, nearest deadline, meters', q[:11] == ['hello', '.', 'late', 'n1', 'bill1', 'on', 'n12', 't5', 'n500', 'tenge', '.'] and q[11:15] == ['near', 'k-water', 'n8', 't5'] and q[-2:] == ['meterdue', '.'] and 'in' in q and 'day5' in q, q)
    sentence = ' '.join(V['d-' + k] if k != '.' else '|' for k in q)
    ok('the assembled sentence reads like the phone text', sentence.startswith('Здравствуйте | Просрочено один счёт на двенадцать тысяч пятьсот тенге | Ближайший срок Вода и водоотведение восемь тысяч тенге до'), sentence)
    g(PUT, {'bills': [], 'day': 0}); ok('nothing to say: nothing is assembled', g("dutyClipSeq()") is None)
    g(PUT, {'bills': [{'kind': 'other', 'amount': 2500000, 'off': -2}]}); ok('amount over a million falls back to the phone voice', g("dutyClipSeq()") is None)
    g(PUT, {'bills': [{'kind': 'strange', 'amount': 1000, 'off': 2}]}); ok('unknown bill kind is read as «Другое»', 'k-other' in g("dutyClipSeq()"), g("dutyClipSeq()"))
    # проигрывание: подмена Audio и списка записей
    SETUP = """(full)=>{
      window.__played=[]; window.__spoke=null; window.__ended=[];
      window.Audio=function(src){const a={src:src,currentTime:0,paused:true,pause(){a.paused=true;},play(){a.paused=false;window.__played.push(src.split('/').pop());setTimeout(()=>{a.paused=true;a.onended&&a.onended();},1);return Promise.resolve();}};return a;};
      window.speak=function(t){window.__spoke=t;return Promise.resolve();};
      const man={}; Object.keys(DUTY_VOICE).forEach(k=>{ if (full || k!=='d-tenge') man[k]=DUTY_VOICE[k]; });
      window.voiceManifest=()=>Promise.resolve(man);
      voicesOk=['Sarah'];
    }"""
    g(PUT, {'bills': [{'kind': 'elec', 'amount': 12500, 'off': -3}, {'kind': 'water', 'amount': 8000, 'off': 5}], 'day': 'today'})
    g(SETUP, True); g("lsSet(LS_VOICE, 'Sarah')")
    g("dutyPlay()"); pg.wait_for_timeout(4000)
    played = g("window.__played"); exp = [f'd-{k}.mp3' for k in g("dutyClipSeq()") if k != '.']
    ok('all recorded words are played in order, nothing read by the phone', played == exp and g("window.__spoke") is None, (played[:6], exp[:6], g("window.__spoke")))
    # не хватает одной записи: читает телефон
    g(SETUP, False); g("window.__played=[]"); g("dutyPlay()"); pg.wait_for_timeout(300)
    ok('a missing word: the phone voice reads the whole summary, no half-played clips', g("window.__played") == [] and (g("window.__spoke") or '').startswith('Здравствуйте, Тест'), (g("window.__played"), g("window.__spoke")))
    # выбран голос телефона
    g(SETUP, True); g("lsSet(LS_VOICE, '')"); g("dutyPlay()"); pg.wait_for_timeout(300)
    ok('phone voice chosen: the phone reads', g("window.__played") == [] and bool(g("window.__spoke")))
    # остановка
    g(SETUP, True); g("lsSet(LS_VOICE, 'Sarah')"); g("dutyPlay()"); g("clipStop()"); pg.wait_for_timeout(400)
    ok('stopping cuts the chain short', len(g("window.__played")) < len(exp), (len(g("window.__played")), len(exp)))
    # ошибка файла: телефон дочитывает
    g(SETUP, True); g("window.Audio=function(src){const a={src:src,currentTime:0,paused:true,pause(){},play(){return Promise.reject(new Error('x'));}};return a;}")
    g("dutyPlay()"); pg.wait_for_timeout(300)
    ok('a file that cannot play: falls back to the phone voice', bool(g("window.__spoke")))
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
