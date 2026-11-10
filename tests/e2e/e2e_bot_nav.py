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
    g("showScreen('screen-chat'); switchChatTab('bot')")
    def ask(q): pg.fill('#bot-text', q); pg.press('#bot-text', 'Enter'); pg.wait_for_timeout(40)
    acts = lambda: g("(()=>{const l=chatBox().box.bot; return (l[l.length-1].actions||[]).map(a=>a.do+':'+(a.arg||''))})()")
    last = lambda: g("(()=>{const l=chatBox().box.bot; return l[l.length-1].text})()")
    def tap(i=0):
        g("(()=>{const l=chatBox().box.bot; botAction(l.length-1, %d)})()" % i)
    active = lambda: g("document.querySelector('.screen.active').id")
    # фразы -> первое действие
    for q, first in [('передать показания', 'meter-new:'), ('хочу передать показания счётчика воды', 'meter-new:'), ('сфотографируй счётчик', 'meter-new:'), ('приборы учёта', 'meter-new:'),
                     ('управление домом', 'mgmt:'), ('какая форма управления у нас', 'mgmt:'), ('что такое НСУ', 'mgmt:'),
                     ('контакты', 'go:screen-contacts'), ('телефоны служб', 'go:screen-contacts'),
                     ('сменить голос', 'go:screen-profile'), ('голос помощника', 'go:screen-profile'), ('мой профиль', 'go:screen-profile'),
                     ('объявления', 'go:screen-announcements'), ('открой общедомовой чат', 'go:screen-chat'), ('на главную', 'go:screen-home'),
                     ('где мои счета', 'go:screen-bills'), ('сфотографировать квитанцию', 'go:screen-bills')]:
        ask(q); a = acts(); ok(f'«{q}» -> {first}', a and a[0] == first, (a, last()[:80]))
    ask('где мои счета'); ok('bills reply also offers to add a bill', 'bill-new:' in acts())
    # действия ведут на экран и открывают окно
    ask('передать показания'); tap(0)
    ok('meter button opens the meters screen with the photo window', active() == 'screen-meters' and g("document.getElementById('mt-modal').classList.contains('open')")); g("mtClose()")
    g("showScreen('screen-chat'); switchChatTab('bot')"); ask('передать показания'); tap(1)
    ok('second meter button opens the table without the window', active() == 'screen-meters' and not g("document.getElementById('mt-modal').classList.contains('open')"))
    g("showScreen('screen-chat'); switchChatTab('bot')"); ask('где мои счета'); tap(1)
    ok('add-bill button opens the bills screen with the bill window', active() == 'screen-bills' and g("document.getElementById('bl-modal').classList.contains('open')"), g("document.getElementById('bl-modal') && document.getElementById('bl-modal').className")); g("blClose()")
    g("showScreen('screen-chat'); switchChatTab('bot')"); ask('управление домом'); tap(0)
    ok('management button opens the management window', g("document.getElementById('mgmt-modal').classList.contains('open')")); g("mgmtClose()")
    g("showScreen('screen-chat'); switchChatTab('bot')"); ask('контакты'); tap(0)
    ok('contacts button opens the contacts screen', active() == 'screen-contacts')
    # ответ про управляющего следует выбранной форме
    g("mgmtPick('pt')"); g("showScreen('screen-chat'); switchChatTab('bot')"); ask('контакты')
    ok('reply still sane after choosing a form', 'Контакты' in last())
    g("mgmtPick('osi')")
    # ничего лишнего: ситуации и прежние команды не перехвачены
    g("showScreen('screen-chat'); switchChatTab('bot')")
    for q, exp in [('пахнет газом на кухне', 'Запах газа'), ('счётчик электричества искрит', 'не вызывайте'), ('лифт не работает', 'Лифт'), ('создай заявку: не горит свет в подъезде', 'Создать заявку')]:
        ask(q); t = last().lower(); a = acts()
        ok(f'«{q}» is not hijacked by navigation', 'meter-new:' not in a and 'mgmt:' not in a and 'go:screen-contacts' not in a, (a, t[:80]))
    g("botPending=null")
    # голосовая команда-переход выполняется сразу, набранная - только кнопка
    g("showScreen('screen-chat'); switchChatTab('bot')"); g("botAsk('контакты', 'text')")
    ok('typed navigation command does not move by itself', active() == 'screen-chat', active())
    g("botAsk('контакты', 'voice')")
    ok('voice navigation command opens the screen at once', active() == 'screen-contacts', active())
    ok('voice command closes the dialog screen', g("document.getElementById('dlg').style.display") == 'none')
    ok('voice command keeps the reply with the button in the chat', 'Контакты' in last())
    g("showScreen('screen-chat'); switchChatTab('bot')"); g("botAsk('передать показания', 'voice')")
    ok('voice command opens the meters photo window', active() == 'screen-meters' and g("document.getElementById('mt-modal').classList.contains('open')")); g("mtClose()")
    g("showScreen('screen-chat'); switchChatTab('bot')"); g("botAsk('управление домом', 'voice')")
    ok('voice command opens the management window', g("document.getElementById('mgmt-modal').classList.contains('open')")); g("mgmtClose()")
    g("showScreen('screen-chat'); switchChatTab('bot')"); g("botAsk('пахнет газом на кухне', 'voice')")
    ok('voice situation is not auto-navigated', active() == 'screen-chat' and g("document.getElementById('dlg').style.display") != 'none', active())
    g("dlgClose(false)"); g("botPending=null")
    ask('что ты умеешь'); ok('intro mentions meters and the new commands', 'передать показания' in g("BOT_INTRO") and 'управление домом' in g("BOT_INTRO"))
    ok('guide asks the concierge to pass meter readings', 'передать показания' in g("guideText()"))
    pg.screenshot(path=S + '/bot_nav.png')
    # кнопка на экране «Счета» не растягивается
    g("showScreen('screen-bills')"); h = g("document.getElementById('mt-open').getBoundingClientRect().height")
    ok('meters button on the bills screen is a normal button, not a tall box', 38 <= h <= 70, h)
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
