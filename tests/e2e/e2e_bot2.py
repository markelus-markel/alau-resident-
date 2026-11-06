import os
import sys
from playwright.sync_api import sync_playwright
S=sys.argv[1]; res=[]
def ok(n,c,x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ')+n+(' | '+str(x)[:300] if not c else ''))
MOCK="""
window.__recs=[]; window.__spoken=[];
class FakeSR{constructor(){window.__recs.push(this);} start(){} stop(){setTimeout(()=>this.onend&&this.onend(),10);} abort(){}
 emit(a){this.onresult({results:a.map(([t,f])=>{const r=[{transcript:t}]; r.isFinal=f; return r;})});} }
window.SpeechRecognition=FakeSR; window.webkitSpeechRecognition=FakeSR;
window.SpeechSynthesisUtterance=function(t){this.text=t};
Object.defineProperty(window,'speechSynthesis',{value:{speaking:false,speak:u=>{window.__spoken.push(u.text)}, cancel(){}},configurable:true});
"""
SEED="""()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    ctx=b.new_context(viewport={'width':390,'height':844}); ctx.add_init_script(MOCK)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    g("showScreen('screen-chat'); switchChatTab('bot')")
    last=lambda: g("(()=>{const l=chatBox().box.bot; return l[l.length-1].text})()")
    acts=lambda: g("(()=>{const l=chatBox().box.bot; return (l[l.length-1].actions||[]).map(a=>a.do+':'+(a.arg||''))})()")
    def ask(q): pg.fill('#bot-text',q); pg.press('#bot-text','Enter'); pg.wait_for_timeout(40)
    cases=[('ощущается запах газа. Подскажи что мне делать','Запах газа'),('чувствую запах газа','Запах газа'),('у нас пожар на кухне','Пожар'),('горит проводка и дым','Пожар'),
      ('топят соседи сверху, помогите','Протечка'),('капает потолок','Протечка'),('застрял в лифте','Лифт'),('лифт не работает','Лифт'),('в подъезде не горит свет','Нет света'),('нет воды с утра','Нет воды'),
      ('очень холодные батареи','Холодные батареи'),('соседи громко орут ночью','Шум'),('забился унитаз','Засор'),('у подъезда чужие люди, подозрительные','Посторонние'),('течёт крыша на верхнем этаже','Течёт кровля'),('не понимаю квитанцию','квитанции')]
    for q,exp in cases:
        ask(q); ok(f'«{q}» -> {exp}', exp in last().split('\n')[0] or exp in last(), last()[:90])
    ask('газета на столе'); ok('"газета" is not gas', 'Запах газа' not in last(), last()[:80])
    ask('ощущается запах газа. Подскажи что мне делать')
    ok('emergency answer: phones first, steps, ticket offer', 'позвоните 104 или 112' in last() and '1. Не включайте' in last() and 'Создать заявку «ощущается запах газа' in last() and acts()[:2]==['yes:','no:'] and 'sit:gas' in acts(), (last(), acts()))
    n0=g("ticketBox().box.list.length"); ask('да')
    ok('yes creates urgent ticket with category and user words', g("ticketBox().box.list.length")==n0+1 and g("ticketBox().box.list[0].prio")=='urgent' and 'запах газа' in g("ticketBox().box.list[0].text") and 'Безопасность' in g("ticketBox().box.list[0].cat"), g("JSON.stringify(ticketBox().box.list[0])"))
    ok('gas memo pops up after emergency ticket', g("document.getElementById('sit-modal').classList.contains('open')")); g("closeSituations()")
    ask('капает потолок'); ask('нет'); ok('decline -> no ticket', g("ticketBox().box.list.length")==n0+1 and 'отменила' in last())
    ask('не горит свет в подъезде, создай заявку'); ok('explicit create still wins', 'Создать заявку' in last() and 'Категория: Электрика' in last(), last()); ask('нет')
    ask('Мои заявки'); ok('my tickets still works', 'Ваших заявок' in last(), last()[:80])
    ask('Ближайшие события'); ok('events still works', 'пока нет событий' in last())
    ask('привет'); ok('greeting still works', 'Здравствуйте' in last())
    ask('помощь'); ok('help word works', 'локальный помощник' in last())
    ask('нужна помощь, пахнет газом'); ok('"нужна помощь" + gas -> gas answer', 'Запах газа' in last(), last()[:80])
    ask('абракадабра'); ok('unknown: guidance + registry button', 'Опишите, что случилось' in last() and 'sit:' in acts(), (last(), acts()))
    ask('странно с лифтом что-то'); ok('weak match: suggestions as buttons', 'Возможно' in last() or 'Лифт' in last(), last()[:80])
    ask('шумит что-то непонятное'); 
    pg.click('#bot-thread button:has-text("Реестр ситуаций") >> nth=-1'); ok('registry button opens popup', g("document.getElementById('sit-modal').classList.contains('open')")); g("closeSituations()")
    # voice: placeholder not sent as message
    pg.click('#bot-mic'); ok('placeholder says Слушаю, value empty', g("document.getElementById('bot-text').placeholder")=='Слушаю…' and g("document.getElementById('bot-text').value")=='')
    n=g("chatBox().box.bot.length"); pg.press('#bot-text','Enter'); ok('Enter during listening sends nothing', g("chatBox().box.bot.length")==n)
    g("stopAllMics()"); ok('placeholder restored after stop', 'Напишите или скажите' in g("document.getElementById('bot-text').placeholder"))
    pg.click('#bot-mic'); g("__recs[__recs.length-1].emit([['ощущается запах газа',true],[' подскажи что мне делать',true]])"); pg.click('#bot-mic'); pg.wait_for_timeout(300)
    ok('voice phrase understood and spoken', 'Запах газа' in last() and g("__spoken.length")>=1 and 'позвоните 104' in g("__spoken[__spoken.length-1]"), last()[:80])
    ok('placeholder restored after voice', 'Напишите или скажите' in g("document.getElementById('bot-text').placeholder"))
    ok('no page errors', not errs, errs); b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
