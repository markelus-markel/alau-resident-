import os
import sys, datetime
from playwright.sync_api import sync_playwright
S=sys.argv[1]; res=[]
def ok(n,c,x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ')+n+(' | '+str(x) if not c else ''))
MOCK="""
window.__recs=[];
class FakeSR{constructor(){window.__recs.push(this);} start(){this.started=true;} stop(){this.stopped=true; setTimeout(()=>this.onend&&this.onend(),10);} abort(){this.aborted=true;}
 emit(a){this.onresult({results:a.map(([t,f])=>{const r=[{transcript:t}]; r.isFinal=f; return r;})});} }
window.SpeechRecognition=FakeSR; window.webkitSpeechRecognition=FakeSR;
"""
NOSR="window.SpeechRecognition=undefined; window.webkitSpeechRecognition=undefined;"
SEED="""(apt)=>{const mk=(ph,ln)=>({phone:ph,last:ln,first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'Найманбаева',house:'12',apt:apt});
 const u={}; u['77011234567']=mk('77011234567','Иванов'); lsSet(LS_USERS,u); lsSet(LS_SESSION,'77011234567'); }"""
URL='file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')
def ru(n):
    d=datetime.date.today()+datetime.timedelta(days=n)
    m=['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'][d.month-1]
    return f'{d.day} {m}'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    # ---------- no speech support ----------
    ctx=b.new_context(viewport={'width':390,'height':844}); ctx.add_init_script(NOSR)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED,'23'); pg.reload()
    g=lambda js: pg.evaluate(js)
    show=lambda s: pg.evaluate("s=>showScreen(s)",s)
    show('screen-voice')
    ok('voice idle: manual button exists', pg.is_visible('#vstate-idle >> text=Ввести текст руками'))
    ok('no fake "(в демо-версии это пример)" text', not g("/это пример/.test(document.getElementById('screen-voice').textContent)"))
    pg.click('#mic-orb')
    ok('unsupported -> review with empty textarea', g("document.getElementById('vstate-review').style.display")=='flex' and g("document.getElementById('transcript-text').value")=='')
    ok('note explains unsupported browser', 'не поддерживает' in g("document.getElementById('review-note').textContent"), g("document.getElementById('review-note').textContent"))
    ok('applicant label uses profile apt', 'кв. №23' in g("document.getElementById('vstate-review').textContent"))
    pg.click('#vstate-review button:has-text("Отправить заявку")')
    ok('empty text -> no ticket created', g("ticketBox().box.list.length")==0)
    ok('empty text -> toast shown', g("document.getElementById('toast').classList.contains('show')"))
    pg.fill('#transcript-text','В подъезде 2 не горит свет <b>на 4 этаже</b>')
    pg.click('#vstate-review >> text=Срочный'); pg.click('#vstate-review button:has-text("Отправить заявку")')
    ok('flow V first number В-001', g("document.getElementById('ticket-number').textContent")=='В-001', g("document.getElementById('ticket-number').textContent"))
    meta=g("document.getElementById('tc-meta').textContent")
    today=datetime.date.today()
    ok('meta has today date + кв.23', str(today.year) in meta and 'кв.23' in meta and ru(0) in meta, meta)
    # ---------- flow M ----------
    show('screen-home')
    g("openModuleVoice('water','💧 Вода','Уважаемый житель квартиры номер {apt}. Опишите.','Сегодня','Описание','','')")
    ok('invite shows apt from profile', 'номер 23' in g("document.getElementById('mv-invite-text').textContent"))
    ok('category preselected', g("document.getElementById('mv-category').value")=='💧 Вода и трубы')
    pg.click('#mv-idle >> text=Ввести текст руками')
    ok('mv manual -> review', g("document.getElementById('mv-review').style.display")=='flex')
    pg.click('#mv-review button:has-text("Отправить заявку")')
    ok('mv empty text -> no new ticket', g("ticketBox().box.list.length")==1)
    pg.fill('#mv-transcript','Течёт кран на кухне'); pg.click('#mv-review button:has-text("Отправить заявку")')
    ok('flow M first number О-001', g("document.getElementById('mv-ticket-num').textContent")=='О-001', g("document.getElementById('mv-ticket-num').textContent"))
    g("openModuleVoice('lift','🛗 Лифт','x','y','z','','')"); pg.click('#mv-idle >> text=Ввести текст руками'); pg.fill('#mv-transcript','Лифт шумит')
    pg.click('#mv-review button:has-text("Отправить заявку")')
    ok('flow M second О-002', g("document.getElementById('mv-ticket-num').textContent")=='О-002')
    g("showScreen('screen-voice'); resetVoice()"); pg.click('#vstate-idle >> text=Ввести текст руками'); pg.fill('#transcript-text','Вторая голосовая'); pg.click('#vstate-review button:has-text("Отправить заявку")')
    ok('flow V second В-002 (own counter, not shared)', g("document.getElementById('ticket-number').textContent")=='В-002', g("document.getElementById('ticket-number').textContent"))
    ok('counters stored per flow', g("JSON.stringify(ticketBox().box.cnt)")=='{"v":2,"m":2}', g("JSON.stringify(ticketBox().box.cnt)"))
    # ---------- history ----------
    show('screen-tickets')
    ids=g("[...document.querySelectorAll('.tkt-num')].map(e=>e.textContent)")
    ok('history lists 4 mine + 2 examples', len(ids)==6 and set(['В-001','В-002','О-001','О-002','#113','#128'])==set(ids), ids)
    ok('newest first', ids[0]=='В-002', ids)
    ok('html in text is escaped', g("!document.querySelector('.tkt-text b')") and 'на 4 этаже' in g("document.getElementById('tickets-list').textContent"))
    ok('urgent flag shown', 'Срочная' in g("document.getElementById('tickets-list').textContent"))
    metas=g("[...document.querySelectorAll('.tkt-meta')].map(e=>e.textContent)")
    ok('example dates relative (-8,-3 days)', any(ru(-8) in m for m in metas) and any(ru(-3) in m for m in metas), metas)
    ok('category names not empty', all(len(c)>0 for c in g("[...document.querySelectorAll('.tkt-meta')].map(e=>e.textContent.split(' · ').pop())")))
    ok('topbar apt', g("document.querySelector('#screen-tickets .topbar').textContent").strip().endswith('кв.23'))
    # download text
    txt=g("buildTicketText(findTicket('О-001'))")
    ok('download text: id, city, apt, no fake status', 'ЗАЯВКА О-001' in txt and 'Семей' in txt and 'кв. №23' in txt and 'Принята в обработку' not in txt, txt)
    # persistence + per phone
    pg.reload()
    ok('tickets survive reload', g("ticketBox().box.list.length")==4)
    g("lsSet(LS_SESSION,'77019999999')")
    ok('other phone has no tickets/counters', g("ticketBox().box.list.length")==0 and g("JSON.stringify(ticketBox().box.cnt)")=='{}')
    g("lsSet(LS_SESSION,'77011234567')")
    # ---------- static dates ----------
    show('screen-announcements')
    body=g("document.body.textContent")
    ok('no hardcoded May/June dates left', not any(w in body for w in ['мая','июня']), [w for w in ['мая','июня'] if w in body])
    ok('all data-rd filled', g("[...document.querySelectorAll('[data-rd]')].every(e=>e.textContent.length>3)"))
    ok('page source has no fake sample texts', not g("/sampleTexts|mvSamples|simulateTranscription/.test(document.documentElement.outerHTML)"))
    ok('no page errors (no-SR)', not errs, errs)
    ctx.close()
    # ---------- with (mock) speech recognition ----------
    ctx=b.new_context(viewport={'width':390,'height':844}); ctx.add_init_script(MOCK)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED,'45'); pg.reload()
    g=lambda js: pg.evaluate(js)
    pg.evaluate("showScreen('screen-voice')")
    ok('apt 45 from profile in applicant label', 'кв. №45' in g("document.getElementById('vstate-review').textContent"))
    pg.click('#mic-orb')
    ok('recording state shown', g("document.getElementById('vstate-recording').style.display")=='block')
    ok('recognizer ru-RU continuous', g("__recs[0].lang")=='ru-RU' and g("__recs[0].continuous") and g("__recs[0].interimResults"))
    g("__recs[0].emit([['В подъезде номер один',true],[' не работает лифт',false]])")
    ok('live transcript shows interim text', 'не работает лифт' in g("document.getElementById('live-transcript').textContent"), g("document.getElementById('live-transcript').textContent"))
    pg.click('#mic-orb-rec'); pg.wait_for_timeout(200)
    ta=g("document.getElementById('transcript-text').value")
    ok('stop -> textarea gets recognized text', 'В подъезде номер один' in ta and 'не работает лифт' in ta, ta)
    ok('review shown and editable', g("document.getElementById('vstate-review').style.display")=='flex' and g("!document.getElementById('transcript-text').readOnly"))
    pg.fill('#transcript-text',ta+' Прошу проверить.'); pg.click('#vstate-review button:has-text("Отправить заявку")')
    ok('submitted from speech: В-001 and кв.45 in meta', g("document.getElementById('ticket-number').textContent")=='В-001' and 'кв.45' in g("document.getElementById('tc-meta').textContent"))
    # permission denied
    g("resetVoice()"); pg.click('#mic-orb')
    g("__recs[1].onerror({error:'not-allowed'}); __recs[1].onend()")
    ok('mic denied -> manual input + message', g("document.getElementById('vstate-review').style.display")=='flex' and 'микрофон' in g("document.getElementById('review-note').textContent").lower(), g("document.getElementById('review-note').textContent"))
    # no speech
    g("resetVoice()"); pg.click('#mic-orb'); g("__recs[2].onerror({error:'no-speech'}); __recs[2].onend()")
    ok('no speech -> empty textarea + message', g("document.getElementById('transcript-text').value")=='' and 'не распознана' in g("document.getElementById('review-note').textContent"))
    # reset cancels recognizer without callback
    g("resetVoice()"); pg.click('#mic-orb'); g("resetVoice()")
    ok('reset aborts recognizer and returns to idle', g("__recs[3].aborted") and g("document.getElementById('vstate-idle').style.display")=='block')
    # flow M with speech
    g("openModuleVoice('electric','⚡ Свет','x','y','z','','')"); pg.click('#mv-orb')
    g("__recs[4].emit([['Нет света в подъезде',true]])"); pg.click('#mv-recording .orb'); pg.wait_for_timeout(200)
    ok('mv speech text in textarea', g("document.getElementById('mv-transcript').value")=='Нет света в подъезде', g("document.getElementById('mv-transcript').value"))
    pg.click('#mv-review button:has-text("Отправить заявку")')
    ok('mv: О-001 independent from В-001', g("document.getElementById('mv-ticket-num').textContent")=='О-001')
    ok('mv done meta has кв.45', 'кв.45' in g("document.getElementById('mv-done-meta').textContent"))
    pg.screenshot(path=S+'/t1_done.png')
    # chat uses profile apt
    g("showScreen('screen-chat')"); pg.fill('#chat-text','привет'); g("sendChatMsg()")
    ok('chat bubble uses apt 45', 'кв.45' in g("document.getElementById('chatpane-chat').textContent"))
    ok('no page errors (mock-SR)', not errs, errs)
    b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
