import os
import sys
import json
import datetime
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
# проходит опрос по текущей ситуации, всегда выбирая первый ответ, пока помощник не предложит заявку
WALK = "(()=>{let n=0;while(botQa&&n<10){qaClick(botQa.id+'|'+botQa.node+'|0');n++;}return n})()"
def unfold(t): return t.replace('\r\n ', '')
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, accept_downloads=True); ctx.add_init_script(MOCK)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    active = lambda: g("document.querySelector('.screen.active').id")
    jl = lambda: g("journalBox().list")
    # 1. плитка и пустое состояние
    pg.click('#screen-home .quick-btn:has-text("Журнал случаев")')
    ok('home tile opens the journal screen', active() == 'screen-journal', active())
    txt = g("document.getElementById('journal-list').textContent")
    ok('empty state instead of example cases', 'Случаев пока нет' in txt and g("document.querySelectorAll('#journal-list .tkt-card').length") == 0, txt)
    # 2. обращение по газу: запись создаётся, ответы попадают в журнал
    g("showScreen('screen-home')"); g("botAsk('пахнет газом','text')")
    L = jl()
    ok('one entry after the first question', len(L) == 1, L)
    e = L[0]
    ok('entry has situation, text, status', e['sit'] == 'gas' and e['text'] == 'пахнет газом' and e['status'] == 'open' and e['outcome'] == 'viewed' and e['id'] == 'Ж-001', e)
    steps = g(WALK)
    ok('walked the questions', steps >= 2, steps)
    e = jl()[0]
    ok('answers recorded in the journal', len(e['path']) == steps and all(isinstance(x, str) and x for x in e['path']), e)
    ok('assistant offered a ticket', g("botPending && botPending.type") == 'ticket' and g("botPending.sit") == 'gas')
    g("botAsk('да','text')")
    g("closeSituations()")  # заявка по аварийной ситуации сама открывает памятку; для теста её закрываем
    e = jl()[0]; tid = g("ticketBox().box.list[0].id")
    ok('ticket created and linked to the case', e['outcome'] == 'ticket' and e['ticket'] == tid and tid.startswith('В-'), [e, tid])
    # 3. замок: отказ от заявки
    g("botAsk('сломался замок входной двери','text')"); g(WALK)
    g("botAsk('нет','text')")
    L = jl()
    ok('second case is a separate entry', len(L) == 2 and L[0]['sit'] == 'lock' and L[0]['id'] == 'Ж-002', [x['id'] for x in L])
    ok('declined ticket recorded', L[0]['outcome'] == 'declined' and L[0]['ticket'] is None, L[0])
    ok('first case is not touched by the decline', L[1]['outcome'] == 'ticket', L[1])
    # 4. тот же вопрос подряд не плодит записи
    g("botAsk('протекает кран','text')"); n1 = len(jl())
    g("botAsk('протекает кран','text')")
    ok('repeated question within 10 minutes is the same case', len(jl()) == n1 == 3, [n1, len(jl())])
    # 5. «нет» без вопроса о заявке не меняет итог
    ok('an unrelated "no" does not change outcomes', jl()[0]['outcome'] == 'viewed')
    # 6. экран журнала
    g("showScreen('screen-journal')")
    cards = g("[...document.querySelectorAll('#journal-list .tkt-card')].map(c=>c.textContent)")
    ok('three cards, newest first', len(cards) == 3 and 'Ж-003' in cards[0] and 'Ж-001' in cards[2], [c[:40] for c in cards])
    ok('card shows what the resident said', 'пахнет газом' in cards[2])
    ok('card shows answers', 'Ваши ответы:' in cards[2] and '→' in cards[2], cards[2])
    ok('card shows ticket outcome', 'Создана заявка ' + tid in cards[2], cards[2])
    ok('card shows declined outcome', 'От заявки отказались' in cards[1], cards[1])
    ok('card shows viewed-only outcome', 'заявка не создавалась' in cards[0], cards[0])
    ok('ticket link only on the ticket card', g("document.querySelectorAll('#journal-list [data-do=tickets]').length") == 1)
    pg.wait_for_timeout(300); pg.screenshot(path=S + '/journal_list.png')
    # 7. отметка «решён»
    pg.click('#journal-list .tkt-card:nth-child(1) button:has-text("Отметить решённым")')
    ok('mark solved persists', jl()[0]['status'] == 'done' and 'Решён' in g("document.querySelector('#journal-list .tkt-card').textContent"))
    pg.click('#journal-list .tkt-card:nth-child(1) button:has-text("Открыть снова")')
    ok('reopen works', jl()[0]['status'] == 'open')
    # 8. напоминание в календарь (.ics)
    now = datetime.datetime.now()
    with pg.expect_download() as d:
        pg.click('#journal-list .tkt-card:nth-child(1) button:has-text("Завтра 9:00")')
    dl = d.value
    ok('download file name', dl.suggested_filename == 'alau-case-003.ics', dl.suggested_filename)
    raw = open(dl.path(), 'rb').read(); ics = raw.decode('utf-8'); u = unfold(ics)
    tm = (now + datetime.timedelta(days=1)).strftime('%Y%m%d') + 'T090000'
    ok('ics is a calendar with one event and an alarm', ics.startswith('BEGIN:VCALENDAR') and u.count('BEGIN:VEVENT') == 1 and 'BEGIN:VALARM' in u and 'TRIGGER:PT0M' in u)
    ok('tomorrow 09:00 floating time', 'DTSTART:' + tm in u, re.findall(r'DTSTART:\S+', u))
    ok('summary names the case', 'SUMMARY:Проверить: ' in u and 'Ж-003' in u, u[:600])
    ok('lines are folded to RFC length (75 octets)', all(len(l.encode('utf-8')) <= 75 for l in ics.split('\r\n')), [len(l.encode('utf-8')) for l in ics.split('\r\n')])
    ok('toast tells what to do with the file', 'Напоминание скачано' in g("document.getElementById('toast').textContent"))
    with pg.expect_download() as d:
        pg.click('#journal-list .tkt-card:nth-child(3) button:has-text("Через 2 часа")')
    u = unfold(open(d.value.path(), 'rb').read().decode('utf-8'))
    m = re.search(r'DTSTART:(\d{8}T\d{6})', u)
    st = datetime.datetime.strptime(m.group(1), '%Y%m%dT%H%M%S') if m else None
    ok('in 2 hours', st is not None and abs((st - (datetime.datetime.now() + datetime.timedelta(hours=2))).total_seconds()) < 180, m and m.group(1))
    ok('first case reminder mentions answers and ticket', 'Ваши ответы:' in u and 'Заявка ' + tid in u, u[-500:])
    ok('no semicolons leak from answers into ics text', 'DESCRIPTION:Случай' in u and ';' not in re.search(r'DESCRIPTION:Случай[^\r\n]*', u).group(0))
    # 9. команда помощнику и переход из ответа
    r = g("botHandle('открой журнал')")
    ok('assistant knows the journal', isinstance(r, dict) and any(a['do'] == 'go' and a['arg'] == 'screen-journal' for a in r['actions']), r)
    # 10. хранение: после перезагрузки на месте, у другого жильца пусто
    pg.reload(); ok('journal survives reload', len(jl()) == 3)
    g("lsSet(LS_SESSION,'77019999999')")
    ok('another phone sees an empty journal', len(jl()) == 0)
    g("lsSet(LS_SESSION,'77011234567')")
    ok('first resident still sees own cases', len(jl()) == 3)
    # 11. предел записей
    g("(()=>{const b=journalBox();b.list=Array.from({length:230},(_, i)=>({id:'Ж-'+(i+1),ts:Date.now(),sit:'gas',title:'t',outcome:'viewed',status:'open',path:[]}));journalSave(b);})()")
    ok('journal is capped at 200 entries', len(jl()) == 200, len(jl()))
    # 12. XSS: текст жильца экранируется
    g("lsSet(LS_JOURNAL,{'77011234567':[{id:'Ж-001',ts:Date.now(),sit:'gas',title:'<b>x</b>',icon:'',text:'<img src=x onerror=window.__x=1>',outcome:'viewed',status:'open',path:['<i>a</i>']}]})")
    g("showScreen('screen-journal')")
    ok('journal escapes HTML', g("!document.querySelector('#journal-list img') && !window.__x && !document.querySelector('#journal-list b + b')"))
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
