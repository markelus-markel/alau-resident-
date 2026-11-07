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
    nmsg=lambda: g("chatBox().box.bot.length")
    def ask(q): pg.fill('#bot-text',q); pg.press('#bot-text','Enter'); pg.wait_for_timeout(40)
    def tap(label):
        pg.click('#bot-thread .tkt-btn:has-text("%s") >> nth=-1' % label); pg.wait_for_timeout(60)
    # 1. три стандартные опции
    ask('маркетплейс'); ok('"маркетплейс" -> три стандартные опции', acts()==['mk-pick:mat','mk-pick:sup','mk-pick:srv'], acts())
    ask('найти исполнителя'); ok('"найти исполнителя" -> три опции', acts()[:1]==['mk-pick:mat'], acts())
    pg.click('#bot-chips .chip:has-text("Найти исполнителя")'); pg.wait_for_timeout(60)
    ok('чип "Найти исполнителя" есть и работает', acts()[:1]==['mk-pick:mat'], acts())
    # 2. кнопки: выбор вида и категории
    tap('Исполнителя услуг'); ok('услуги: кнопки услуг', all(a.startswith('mk-cat:prov:s-') or a=='go:screen-market' for a in acts()) and len(acts())==17, acts())
    tap('Клининг'); t=last()
    ok('исполнители: честное пустое состояние', 'пока нет' in t and 'Клининг' in t and 'исполнителей' in t, t[:120])
    ok('нет выдуманных людей и телефонов', not any(ch.isdigit() for ch in t), t)
    ok('предложен поиск рядом, запрос в ОСИ и рекомендация', acts()[:3]==['mk-near:s-clean','mk-req:s-clean','mk-rec:s-clean'], acts())
    ask('маркетплейс'); tap('Материалы'); ok('материалы: категории материалов', acts()[0].startswith('mk-cat:mat:m-') and len(acts())==12, acts())
    ask('маркетплейс'); tap('Поставщика'); ok('поставщик: сразу к поставщикам', acts()[0].startswith('mk-cat:prov:m-'), acts())
    tap('Строительные'); t=last(); ok('поставщики: пустое состояние', 'Проверенных поставщиков' in t and 'пока нет' in t, t[:120])
    # 3. свободная фраза
    ask('нужна плитка'); ok('«нужна плитка» неоднозначна (материал или работы): уточняет', 'Уточните' in last() and 'mk-cat:mat:m-finish' in acts() and 'mk-cat:prov:s-finish' in acts(), acts())
    tap('Отделочные материалы'); t=last()
    ok('после уточнения: отделочные материалы и состав категории', 'Отделочные материалы' in t and 'плитка' in t, t[:100])
    ok('для материалов: поставщик, рядом, запрос, категория', acts()==['mk-cat:prov:m-finish','mk-near:m-finish','mk-req:m-finish','mk-open:m-finish'], acts())
    tap('Найти поставщика'); ok('кнопка "Найти поставщика" ведёт к поставщикам', 'Проверенных поставщиков' in last() and 'Отделочные' in last(), last()[:100])
    ask('нужны обои'); t=last()
    ok('«нужны обои» -> отделочные материалы без уточнения', 'Отделочные материалы' in t and 'Уточните' not in t, t[:100])
    ask('нужна уборка после ремонта'); t=last()
    ok('«нужна уборка» -> клининг/исполнитель', 'Клининг' in t or acts()[0].startswith('mk-cat'), t[:100])
    ask('нужен электрик'); t=last()
    ok('«нужен электрик» -> Электромонтаж (или уточнение с ним)', 'Электромонтаж' in t or any(a.endswith('s-electro') for a in acts()), t[:100])
    ask('нужен сантехник'); ok('«нужен сантехник» неоднозначно: уточняет', 'Уточните' in last() and len(acts())>=2, last()[:80])
    ask('купить краску'); ok('«купить краску» -> лакокрасочные', 'Лакокрасочные' in last(), last()[:80])
    # 4. защита: ситуации и обычные команды не перехватываются
    ask('запах газа, нужна помощь'); ok('газ с "нужна" остаётся ситуацией', 'Запах газа' in last().split('\n')[0], last()[:80])
    ask('течёт кран, что делать'); ok('"течёт кран" остаётся ситуацией', 'Протечка' in last() or 'протеч' in last().lower(), last()[:80])
    ask('найди расписание'); ok('"найди расписание" не маркетплейс', 'Маркетплейс' not in last() and not acts()[:1]==['mk-pick:mat'], last()[:80])
    ask('ближайшие события'); ok('календарь не сломан', 'события' in last().lower() or 'календар' in last().lower(), last()[:80])
    ask('создай заявку: не горит свет в подъезде'); ok('заявка по-прежнему требует подтверждения', acts()==['yes:','no:'], acts())
    ask('нет')
    # 5. создаётся ли что-то без подтверждения
    before=g("lsGet('alauDemoTickets', {})"); n0=len(str(before))
    ask('нужны обои'); tap('Запрос в ОСИ'); pg.wait_for_timeout(120)
    ok('«Запрос в ОСИ» открывает форму модуля (без создания заявки)', g("document.getElementById('screen-module-voice').classList.contains('active')"))
    ok('заявка не создана без подтверждения', len(str(g("lsGet('alauDemoTickets', {})")))==n0)
    # 6. открыть категорию и рекомендацию
    g("showScreen('screen-chat'); switchChatTab('bot')"); ask('нужны обои'); tap('Открыть категорию'); pg.wait_for_timeout(80)
    ok('«Открыть категорию» открывает окно категории', g("document.getElementById('mk-modal').classList.contains('open')") and 'Отделочные' in g("document.getElementById('mk-title').textContent"))
    g("mkClose(); showScreen('screen-chat'); switchChatTab('bot')"); ask('нужны обои'); tap('Рекомендовать'); pg.wait_for_timeout(80)
    ok('«Рекомендовать» открывает форму рекомендации', g("!!document.getElementById('mk-r-name')"))
    # 7. рекомендации жильца показываются как непроверенные
    g("lsSet(LS_RECS,{'77011234567':[{cat:'s-clean',name:'Тестовая бригада',phone:'',note:'',ts:1}]})")
    g("showScreen('screen-chat'); switchChatTab('bot')"); ask('найди клининг'); t=last()
    ok('своя рекомендация помечена как непроверенная', 'не проверены' in t and 'Тестовая бригада' in t, t[:160])
    g("lsSet(LS_RECS,{'77011234567':[{cat:'s-clean',name:'<b>x</b>',phone:'',note:'',ts:1}]})")
    ask('найди клининг'); ok('HTML в названии не исполняется', g("!document.querySelector('#bot-thread b')"))
    ok('нет ошибок страницы', not errs, errs[:2])
    pg.screenshot(path=S+'/mk_bot.png'); b.close()
bad=res.count(False); print('TOTAL',len(res),'FAILED',bad); sys.exit(1 if bad else 0)
