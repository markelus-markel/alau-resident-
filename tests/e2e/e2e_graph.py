import os
import sys
import json
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', '/home/claude/alau-resident-/index.html')
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    g("showScreen('screen-chat')"); g("switchChatTab('bot')")
    last = lambda: g("(()=>{const m=chatBox().box.bot;return m[m.length-1]})()")
    graph = g("SIT_GRAPH"); sits = g("SITUATIONS.map(s=>({id:s.id,level:s.level,title:s.title}))")
    def run_to_end(sid, pick):
        g("botQa=null; botPending=null"); g("botSituation(%s)" % json.dumps(sid))
        for _ in range(8):
            qs = [a for a in last()['actions'] if a['do']=='qa']
            if not qs: break
            g("qaClick(%s)" % json.dumps(qs[0 if pick=='first' else -1]['arg']))
        return last()
    # 1. каждый сценарий можно пройти до конца по первым и по последним ответам
    bad = []
    for s in sits:
        for pick in ('first', 'last'):
            r = run_to_end(s['id'], pick); acts = r['actions']
            if any(a['do']=='qa' for a in acts): bad.append(s['id'] + ' ' + pick + ': не закончился')
            has_offer = [a['do'] for a in acts[:2]]==['yes', 'no']
            if (s['level']=='info') == has_offer: bad.append(s['id'] + ' ' + pick + ': предложение заявки: ' + str(has_offer) + ' для уровня ' + s['level'])
            if acts[-1]['do']!='sit': bad.append(s['id'] + ': нет кнопки «Подробно» в конце')
    ok('all 17 scenarios reach the end by first and by last answers, ticket offer except info memos', not bad, bad)
    # 2. кнопки связанных ситуаций: столько, сколько рёбер (не больше трёх), сначала опасное развитие
    bad = []
    for s in sits:
        r = run_to_end(s['id'], 'first'); links = [a for a in r['actions'] if a['do']=='sit-ask']
        edges = [e for e in graph if e[0]==s['id']]
        if len(links) != min(3, len(edges)): bad.append('%s: кнопок %d, связей %d' % (s['id'], len(links), len(edges)))
        order = [e[2] for e in sorted(edges, key=lambda e: 0 if e[2]=='escalates' else 1)][:3]
        if [next(e[2] for e in edges if e[4]==a['label']) for a in links] != order: bad.append(s['id'] + ': порядок связей')
    ok('related situations are offered as buttons: all edges, max three, escalations first', not bad, bad)
    # 3. переход по связи запускает сценарий другой ситуации
    run_to_end('leak', 'first'); lab = '💡 Вода у розеток: что со светом'
    pg.click('#bot-thread .tkt-btn:text-is("%s") >> nth=-1' % lab); pg.wait_for_timeout(200)
    ok('leak -> power: the linked scenario starts', 'запах гари' in last()['text'] and 'Нет света' in last()['text'], last()['text'][:150])
    ok('the user bubble names the linked situation', g("chatBox().box.bot.filter(x=>x.role==='me').slice(-1)[0].text").startswith('Что делать: Нет света'))
    run_to_end('gas', 'last'); pg.click('#bot-thread .tkt-btn:text-is("🔥 Загорелось или появился дым") >> nth=-1'); pg.wait_for_timeout(200)
    ok('gas -> fire: escalation opens the fire scenario', 'Пожар или задымление' in last()['text'] and 'Горит у вас в квартире' in last()['text'], last()['text'][:150])
    # 4. справочная ветка «Как оплатить»: кнопка раздела и связь, без заявки
    g("botQa=null"); g("botSituation('bill')"); g("qaClick(%s)" % json.dumps(last()['actions'][1]['arg']))
    labels = [a['label'] for a in last()['actions']]
    ok('bill / how to pay: opens "Счета" button + link to meeting, no ticket offer', '🧾 Открыть «Счета»' in labels and '📅 Внести вопрос на собрание' in labels and 'Создать заявку' not in last()['text'], labels)
    pg.click('#bot-thread .tkt-btn:text-is("🧾 Открыть «Счета»") >> nth=-1'); pg.wait_for_timeout(150)
    ok('the button opens the bills screen', g("document.querySelector('.screen.active').id")=='screen-bills')
    # 5. текст самого графа
    texts = [e[3] + e[4] for e in graph]
    ok('graph texts carry no foreign phones', all(not __import__('re').search(r'(?<!\d)(?!112|101|102|103|104)\d{3}(?!\d)', t) for t in texts))
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
