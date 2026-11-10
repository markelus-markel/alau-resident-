import os
import sys
from playwright.sync_api import sync_playwright
S = sys.argv[1]; res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
SEED = """()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');lsSet(LS_WELCOME,{'77011234567':1});}"""
URL = 'file://' + os.environ.get('ALAU_INDEX', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'index.html'))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g = pg.evaluate
    # без выбора и для ОСИ тексты не меняются
    ok('no choice: chairman wording unchanged', g("mgmtSub('Сообщите председателю ОСИ.')") == 'Сообщите председателю ОСИ.')
    ok('no choice: header line hidden', g("getComputedStyle(document.getElementById('home-form')).display") == 'none')
    g("mgmtPick('osi')")
    ok('OSI: wording unchanged', g("mgmtSub('Председатель ОСИ №14 и председателем ОСИ')") == 'Председатель ОСИ №14 и председателем ОСИ')
    ok('header form line is a light pill with dark text', g("(()=>{const c=getComputedStyle(document.getElementById('home-form'));const l=x=>x.match(/\\d+/g).slice(0,3).map(Number);const bg=l(c.backgroundColor),fg=l(c.color);return Math.min(...bg)>200&&Math.max(...fg)<80})()"))
    ok('OSI: header shows the form', g("document.getElementById('home-form').textContent") == '🏠 ОСИ')
    # простое товарищество: падежи
    g("mgmtPick('pt')")
    cases = g("['председатель ОСИ','председателя ОСИ','председателю ОСИ','председателем ОСИ','председателе ОСИ','Председатель ОСИ №14'].map(mgmtSub)")
    ok('PT: all five cases and the capital letter', cases == ['доверенное лицо', 'доверенного лица', 'доверенному лицу', 'доверенным лицом', 'доверенном лице', 'Доверенное лицо'], cases)
    ok('PT: other words with ОСИ are not touched', g("mgmtSub('Составьте акт с представителем ОСИ. Заявка в ОСИ.')") == 'Составьте акт с представителем ОСИ. Заявка в ОСИ.')
    g("mgmtPick('nsu')")
    ok('NSU: dative', g("mgmtSub('Сообщите председателю ОСИ')") == 'Сообщите уполномоченному собственнику')
    ok('NSU: header shows the form', g("document.getElementById('home-form').textContent") == '🏠 НСУ')
    # справка: к кому обращаться
    g("mgmtOpen()")
    ok('reference says whom to address', 'К кому обращаться: уполномоченный собственник' in g("document.getElementById('mgmt-info').textContent"))
    g("mgmtClose()")
    # контакты
    g("showScreen('screen-contacts')")
    ok('contacts: the house manager slot is renamed', 'Уполномоченный собственник' in g("document.getElementById('ct-house').textContent") and 'Председатель' not in g("document.getElementById('ct-house').textContent"), g("document.getElementById('ct-house').textContent"))
    g("mgmtPick('pt')")
    ok('contacts re-render at once after the choice changes', 'Доверенное лицо' in g("document.getElementById('ct-house').textContent"))
    g("ctOpen('chair')"); ok('contact window title follows the form', 'Доверенное лицо' in g("document.getElementById('ct-title').textContent")); g("ctClose()")
    # памятка
    g("openSituations('gas')")
    t = g("document.getElementById('sit-body').textContent")
    ok('memo shows the form wording, not «председателю ОСИ»', 'председателю ОСИ' not in t and 'доверенному лицу' in t, t[-300:])
    ok('memo speech text follows the form (recording will not match, phone voice reads)', 'доверенному лицу' in g("sitFullText(sitById('gas'))") and 'председателю' not in g("sitFullText(sitById('gas'))"))
    g("closeSituations()")
    # помощник
    g("showScreen('screen-chat')"); g("switchChatTab('bot')"); g("botAsk('дверь в подъезд сломана','text')")
    th = g("document.getElementById('bot-thread').textContent")
    ok('assistant answers use the form wording', 'председател' not in th, th[-300:])
    # календарь
    g("window.houseEvents=()=>[]; showScreen('screen-calendar'); renderCalendar()")
    ok('calendar: empty text names the right person', 'доверенное лицо' in g("document.getElementById('cal-list').textContent") and 'председатель' not in g("document.getElementById('cal-list').textContent"), g("document.getElementById('cal-list').textContent"))
    ok('calendar: static note follows the form', 'доверенное лицо' in g("document.querySelector('#screen-calendar .js-role').textContent"))
    # заявка: адресат по форме
    g("addTicket('v','gas','Тест',null)"); tid = g("ticketBox().box.list[0].id")
    ok('ticket file names the addressee by the form', 'Кому: доверенное лицо' in g("buildTicketText(findTicket(%r))" % tid), g("buildTicketText(findTicket(%r))" % tid))
    g("lsSet(LS_MGMT,{})")
    ok('no choice: ticket file has no addressee line', 'Кому:' not in g("buildTicketText(findTicket(%r))" % tid))
    g("mgmtPick('pt')")
    # вернуть ОСИ: всё как было
    g("mgmtPick('osi')")
    ok('back to OSI: static note restored', g("document.querySelector('#screen-calendar .js-role').textContent") == 'События добавляет председатель ОСИ.')
    g("showScreen('screen-contacts')"); ok('back to OSI: contact slot restored', 'Председатель ОСИ №14' in g("document.getElementById('ct-house').textContent"))
    g("showScreen('screen-home')"); pg.screenshot(path=S + '/mgmt_role_home.png')
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
