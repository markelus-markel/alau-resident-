import os
import sys
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');lsSet(LS_WELCOME,{'77011234567':1});}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'index.html'))
# данные жильца задаются в странице: даты считаются от сегодняшнего дня
PUT = """(o)=>{const iso=n=>{const d=new Date();d.setDate(d.getDate()+n);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')};
const p='77011234567';
lsSet(LS_BILLS,{[p]:(o.bills||[]).map((b,i)=>({id:'S-t'+i,kind:b.kind,amount:b.amount,due:b.off===null?'':iso(b.off),paid:!!b.paid,period:'',account:'',photo:null,created:new Date().toISOString()}))});
const day=o.day===undefined?0:(o.day==='today'?Math.min(new Date().getDate(),28):o.day);
const rd=(o.reads||[]).map((r,i)=>({id:'R'+i,kind:'water',label:'',value:100+i,date:iso(r),photo:null,auto:false,created:new Date().toISOString()}));
lsSet(LS_METERS,{[p]:{readings:rd,day:day}});
renderDuty();}"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    vis = lambda: g("document.getElementById('home-duty').style.display !== 'none'")
    txt = lambda: g("document.getElementById('home-duty').innerText")
    # 1. данных нет: карточки нет, чат не выдумывает
    ok('no data: no duty card on home', not vis())
    g("showScreen('screen-chat'); switchChatTab('bot')")
    def ask(q): pg.fill('#bot-text', q); pg.press('#bot-text', 'Enter'); pg.wait_for_timeout(40)
    last = lambda: g("(()=>{const l=chatBox().box.bot; return l[l.length-1].text})()")
    acts = lambda: g("(()=>{const l=chatBox().box.bot; return (l[l.length-1].actions||[]).map(a=>a.do+':'+(a.arg||''))})()")
    ask('что я должен'); ok('no data: concierge says there is nothing to remind, offers to add a bill', 'нечего напоминать' in last() and 'bill-new:' in acts(), last())
    # 2. просроченный и ближайший счёт, день показаний наступил, показаний нет
    g(PUT, {'bills': [{'kind': 'elec', 'amount': 12500, 'off': -3}, {'kind': 'water', 'amount': 8000, 'off': 5}, {'kind': 'gas', 'amount': 3000, 'off': -1, 'paid': True}], 'day': 'today'})
    g("showScreen('screen-home')"); t = txt()
    ok('card shown with real data', vis())
    ok('heading is «Консьерж напоминает:» without the name', 'Консьерж напоминает:' in t and 'напоминает, Тест' not in t, t)
    rows = g("[...document.querySelectorAll('#home-duty .duty-row')].map(r=>[...r.children].map(c=>c.innerText.replace(/\\s+/g,' ').trim()))")
    ok('table headers: marker, subject, sum, deadline', g("[...document.querySelectorAll('#home-duty th')].map(h=>h.innerText.trim())") == ['', 'Предмет', 'Сумма', 'Срок'])
    ok('three rows: overdue bill, upcoming bill, meters', len(rows) == 3, rows)
    ok('overdue row: marker, subject, sum, deadline with days late', rows[0][0] == '⚠️' and rows[0][1] == 'Электричество' and '12' in rows[0][2] and '500' in rows[0][2] and '₸' in rows[0][2] and '.' in rows[0][3] and 'просрочен на 3 дня' in rows[0][3], rows[0])
    ok('paid bill is not in the table', 'Газ' not in g("document.getElementById('home-duty').innerText"))
    ok('upcoming row: subject, sum, deadline and days left', rows[1][1] == 'Вода и водоотведение' and '8' in rows[1][2] and 'через 5 дней' in rows[1][3], rows[1])
    ok('meters row: marker, subject, no sum, reminder', rows[2][0] == '📟' and rows[2][1] == 'Показания приборов учёта' and rows[2][2] == '—' and 'пора передать' in rows[2][3], rows[2])
    ok('card greets by name only in the spoken text', 'Тест' not in t and g("dutySpeech()").startswith('Здравствуйте, Тест'), t)
    pg.screenshot(path=S + '/duty_home.png')
    # круглая кнопка «Послушать» в правом верхнем углу карточки
    bx = g("(()=>{const b=document.getElementById('duty-speak').getBoundingClientRect(), c=document.getElementById('home-duty').getBoundingClientRect(); return {w:b.width,h:b.height,r:getComputedStyle(document.getElementById('duty-speak')).borderRadius,dr:c.right-b.right,dt:b.top-c.top,dl:b.left-c.left,cw:c.width}})()")
    ok('listen button is round', abs(bx['w'] - bx['h']) < 1 and 30 <= bx['w'] <= 48 and bx['r'] in ('50%', '19px'), bx)
    ok('listen button sits in the top right corner of the card', bx['dr'] <= 20 and bx['dt'] <= 20 and bx['dl'] > bx['cw'] / 2, bx)
    ok('listen button has an accessible name and no text button for it remains below', g("document.getElementById('duty-speak').getAttribute('aria-label')") == 'Послушать' and not g("[...document.querySelectorAll('#home-duty button')].some(b=>b.id!=='duty-speak' && b.textContent.includes('Послушать'))"))
    g("(()=>{window.__spoke=null; window.speak=function(t){window.__spoke=t; return Promise.resolve();}})()")
    g("document.getElementById('duty-speak').click()"); ok('listen button reads the summary', (g("window.__spoke") or '').startswith('Здравствуйте, Тест'), g("window.__spoke"))
    # 3. кнопки карточки ведут в разделы
    g("[...document.querySelectorAll('#home-duty button')].find(b=>b.textContent.includes('Счета')).click()"); ok('card button Счета opens the bills screen', g("document.querySelector('.screen.active').id") == 'screen-bills')
    g("showScreen('screen-home')"); g("[...document.querySelectorAll('#home-duty button')].find(b=>b.textContent.includes('показания')).click()")
    ok('card button opens meters with the photo window', g("document.querySelector('.screen.active').id") == 'screen-meters' and g("document.getElementById('mt-modal').classList.contains('open')")); g("mtClose()")
    # 4. голос: короткая фраза без значков
    sp = g("dutySpeech()"); ok('speech text is plain: greeting by name, no emoji, no brackets', sp.startswith('Здравствуйте, Тест') and '⚠' not in sp and '(' not in sp and 'Просрочено' in sp, sp)
    ok('speech says money in words and dates as «15 ноября», no currency sign or dotted dates', '₸' not in sp and 'тенге' in sp and '12500 тенге' in sp and any(m in sp for m in ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря']), sp)
    ok('speech has no dotted dates or thousands separators', '.20' not in sp and '\xa0' not in sp, sp)
    # 5. вопросы консьержу
    g("showScreen('screen-chat'); switchChatTab('bot')")
    for q, must, first in [('что я должен', 'Задолженность', 'go:screen-bills'), ('сколько мне оплатить', 'Задолженность', 'go:screen-bills'), ('сроки оплаты', 'Ближайшие сроки', 'go:screen-bills'),
                           ('когда платить', 'Ближайшие сроки', 'go:screen-bills'), ('пора ли передавать показания', 'Пора передать показания', 'meter-new:'), ('что срочного', 'Задолженность', 'meter-new:')]:
        ask(q); a = acts(); ok(f'«{q}» -> reply and first button', must in last() and a and a[0] == first, (last()[:90], a))
    ask('что я должен'); ok('debt reply lists the overdue bill with the real amount and date', 'Электричество' in last() and 'до ' in last() and 'Газ' not in last(), last())
    ask('передать показания'); ok('plain «передать показания» still goes to meters', 'meter-new:' in acts())
    # 6. всё оплачено и показания переданы: карточка исчезает, чат говорит правду
    g(PUT, {'bills': [{'kind': 'elec', 'amount': 12500, 'off': -3, 'paid': True}], 'day': 'today', 'reads': [0]})
    g("showScreen('screen-home')"); ok('all paid and readings done: card is hidden', not vis(), txt())
    g("showScreen('screen-chat'); switchChatTab('bot')"); ask('что я должен'); ok('nothing overdue is stated honestly', 'Просроченных счетов нет' in last(), last())
    # 7. показания скоро: напоминание за 1–3 дня
    if g("new Date().getDate()") <= 25:
        g(PUT, {'bills': [], 'day': g("new Date().getDate()") + 2, 'reads': [0]}); g("showScreen('screen-home')")
        ok('meters day in two days: soon reminder in the table', vis() and 'через 2 дня' in txt() and 'Показания приборов учёта' in txt(), txt())
        g(PUT, {'bills': [], 'day': g("new Date().getDate()") + 6, 'reads': [0]}); g("showScreen('screen-home')")
        ok('meters day is far: no reminder yet', not vis(), txt())
    # 8. без срока оплаты
    g(PUT, {'bills': [{'kind': 'trash', 'amount': 1500, 'off': None}]}); g("showScreen('screen-home')")
    ok('bill without a deadline says so and does not invent one', vis() and 'срок не указан' in txt() and '.20' not in txt(), txt())
    g("showScreen('screen-chat'); switchChatTab('bot')"); ask('сроки оплаты'); ok('no deadline: says there are no upcoming deadlines', 'нет' in last().lower(), last())
    ok('intro mentions the new questions', 'что я должен' in g("BOT_INTRO"))
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
