import os
import sys
import re
import json
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
MOCK = """
window.__spoken=[];
window.SpeechSynthesisUtterance=function(t){this.text=t};
Object.defineProperty(window,'speechSynthesis',{value:{speaking:false,speak:u=>{window.__spoken.push(u.text)},cancel(){}},configurable:true});
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
    labels = lambda: [a['label'] for a in last().get('actions', [])]
    ask = lambda q: g("botAsk(%s,'voice')" % json.dumps(q))
    click = lambda label: pg.click('#bot-thread .tkt-btn:text-is(%s) >> nth=-1' % json.dumps(label, ensure_ascii=False))
    # 1. целостность сценариев
    qa = g("SIT_QA"); bad = []
    for sid, sc in qa.items():
        if not g("!!sitById(%s)" % json.dumps(sid)): bad.append('нет ситуации ' + sid)
        if sc['start'] not in sc['nodes']: bad.append(sid + ': нет стартового узла')
        for nid, n in sc['nodes'].items():
            if not n['q'].endswith('?') or len(n['opts']) < 2: bad.append(sid + '.' + nid + ': вопрос или ответы')
            for o in n['opts']:
                if o.get('next') and o['next'] not in sc['nodes']: bad.append(sid + '.' + nid + ': нет узла ' + o['next'])
                if not re.search(o['m'], o['l'].lower().replace('ё', 'е')) and not g("(r=>new RegExp(r).test(%s))(%s)" % (json.dumps(o['l'].lower()), json.dumps(o['m']))): bad.append(sid + '.' + nid + ': кнопка «' + o['l'] + '» не проходит свой же шаблон')
                if not o['say'].strip(): bad.append(sid + '.' + nid + ': пустой совет')
                if set(re.findall(r'(?<!\d)\d{3}(?!\d)', o['say'])) - {'112', '101', '102', '103', '104'}: bad.append(sid + '.' + nid + ': ненациональный телефон')
    ok('every scenario is well-formed', not bad and len(qa) >= 4, bad)
    # 2. фраза с телефона: замок
    ask('сломался замок входной двери')
    r = last()
    ok('lock: memo for the broken lock, not water or break-in', 'Сломался замок или не открывается дверь' in r['text'] and 'воду' not in r['text'].lower(), r['text'][:200])
    ok('lock: concrete steps shown at once', 'Что делать сейчас' in r['text'] and 'Не ломайте дверь' in r['text'])
    ok('lock: first question with buttons', 'внутри квартиры или снаружи' in r['text'] and labels()[:3]==['Внутри, дверь не открывается', 'Снаружи, не могу войти', 'Замок в подъезде или общая дверь'], labels())
    click('Внутри, дверь не открывается')
    ok('lock: button -> next question', 'ребёнок, пожилой или больной' in last()['text'] and labels()[:2]==['Да', 'Нет'], last()['text'][-150:])
    ok('lock: user bubble shows the chosen answer', g("chatBox().box.bot.filter(x=>x.role==='me').slice(-1)[0].text")=='Внутри, дверь не открывается')
    click('Да')
    t = last()['text']
    ok('lock: danger branch says call 112', 'Звоните 112' in t, t)
    ok('lock: ends with a ticket offer carrying the answers', 'Создать заявку «сломался замок входной двери (Внутри, дверь не открывается; Да)»' in t and '✅ Да' in labels(), t[-200:])
    cnt = lambda: g("ticketBox().box.list.length"); n0 = cnt()
    click('✅ Да'); pg.wait_for_timeout(200)
    top = g("ticketBox().box.list[0]")
    ok('lock: confirming creates a ticket with the answers', cnt()==n0+1 and 'Внутри, дверь не открывается; Да' in top['text'] and top['prio']=='urgent', top)
    # способ ответа: голосом проговаривается, как отвечать, и есть кнопка микрофона
    g("void(window.__spoken=[])"); ask('сломался замок'); sp = [x.replace('\u0301', '') for x in g("__spoken")]
    ok('voice question: the assistant says how to answer', len(sp)==1 and 'Ответьте: Внутри, дверь не открывается, или Снаружи, не могу войти, или Замок в подъезде' in sp[0] and 'микрофон' in sp[0], sp)
    ok('every question has the voice-answer button', '🎙️ Ответить голосом' in labels(), labels())
    ok('typed question is not read aloud', (g("void(window.__spoken=[])"), g("botAsk('сломался замок','text')"), g("__spoken.length")==0)[2])
    # ударение: «замок» читается как замОк (знак ударения только в озвучке, на экране текст прежний)
    st = g("ttsStress('Сломался замок. Не бейте по замку, замка нет, Замок, замков, замкнуть, взломали')")
    ok('stress mark on the lock forms only', 'замо\u0301к' in st and 'замку\u0301' in st and 'замка\u0301' in st and 'Замо\u0301к' in st and 'замко\u0301в' in st and 'замкнуть' in st and 'взломали' in st, st)
    g("void(window.__spoken=[])"); ask('сломался замок входной двери')
    ok('spoken text carries the stress, screen text does not', 'замо\u0301к' in g("__spoken[0]") and '\u0301' not in last()['text'], g("__spoken[0]")[:80])
    # 3. ответы словами (голос), ветка «снаружи»
    ask('сломался замок'); ask('снаружи не могу войти')
    ok('voice answer "снаружи" is understood', 'следы взлома' in last()['text'], last()['text'][:150])
    ask('нет'); ok('voice "нет" moves to the spare-key question', 'запасной ключ' in last()['text'], last()['text'][:150])
    ask('нет'); ok('no spare key -> locksmith advice', 'мастера по вскрытию' in last()['text'] and 'паспорт' in last()['text'])
    ask('заклинило замок'); ask('снаружи'); ask('да есть царапины')
    ok('signs of break-in -> do not enter, call 102', 'Не входите' in last()['text'] and '102' in last()['text'])
    ask('сломался замок'); click('Замок в подъезде или общая дверь')
    ok('building door branch goes to the chairman and ticket', 'председателю ОСИ' in last()['text'] and 'Создать заявку' in last()['text'])
    click('✖ Нет')
    # 4. посторонняя реплика не застревает в опросе
    ask('сломался замок'); ask('привет')
    ok('unrelated phrase leaves the questionnaire', 'Здравствуйте' in last()['text'])
    ask('да'); ok('later "да" is not taken as an answer', 'нечего подтверждать' in last()['text'], last()['text'])
    # фразы, начинающиеся со слова «нет», раньше принимались за отказ и получали «нечего подтверждать»
    for q, want in [('нет воды', 'Нет воды'), ('нет света', 'Нет света'), ('нет газа', 'газ')]:
        ask(q); ok('"%s" is a situation, not a refusal' % q, 'нечего подтверждать' not in last()['text'] and want in last()['text'], last()['text'][:120])
    # 5. свет, вода, протечка
    ask('отключился свет, что мне делать?')
    ok('power: asks about smoke first', 'запах гари' in last()['text'] and 'Нет света' in last()['text'] and 'воду' not in last()['text'].lower(), last()['text'][:160])
    ask('да, искрит проводка'); ok('power: smoke -> 101 or 112', '101' in last()['text'] and 'Выведите людей' in last()['text'], last()['text'])
    ask('отключился свет'); ask('да пахнет гарью'); ok('another danger said mid-questions leaves the questionnaire for the fire memo', 'Пожар' in last()['text'], last()['text'][:100])
    ask('отключился свет'); ask('нет'); ask('только у меня'); ask('выбило')
    ok('power: own breaker branch', 'Поднимите рычаг' in last()['text'])
    ask('отключился свет'); click('Нет'); click('Во всём подъезде или доме')
    ok('power: whole building branch', 'диспетчеру' in last()['text'] and 'лифтом' in last()['text'])
    ask('нет воды'); click('Только у меня'); click('Только горячая')
    ok('no water: own flat, hot only', 'другому стояку' in last()['text'])
    ask('протекает кран'); click('Нет'); click('Заливает сверху')
    ok('leak: from above branch', 'соседям сверху' in last()['text'] and 'акт' in last()['text'])
    ask('залило, вода у розеток'); click('Да')
    ok('leak: water at sockets -> breaker off first, then asks where it flows from', 'отключите автомат' in last()['text'].lower() and 'течёт у вас или к вам сверху' in last()['text'], last()['text'])
    # 6. кнопка из реестра и «Подробно»
    g("openSituations('lock')"); body = g("document.getElementById('sit-body').textContent")
    ok('registry memo for the lock exists with 112', g("sitById('lock').title")=='Сломался замок или не открывается дверь' and '112' in body and 'Единая служба спасения' in body, body[:120])
    ok('no page errors', not errs, errs)
    pg.screenshot(path=S + '/qa_lock.png')
    b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
