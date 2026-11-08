import os
import sys, zlib, struct
from playwright.sync_api import sync_playwright
S=sys.argv[1]; res=[]
def ok(n,c,x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ')+n+(' | '+str(x)[:300] if not c else ''))
def png(w=40,h=30):
    raw=b''.join(b'\x00'+bytes([200,60,60])*w for _ in range(h))
    def ch(t,d): c=struct.pack('>I',len(d))+t+d; return c+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b'')
MOCK="""
window.__recs=[]; window.__spoken=[];
class FakeSR{constructor(){window.__recs.push(this);} start(){} stop(){setTimeout(()=>this.onend&&this.onend(),10);} abort(){}
 emit(a){this.onresult({results:a.map(([t,f])=>{const r=[{transcript:t}]; r.isFinal=f; return r;})});} }
window.SpeechRecognition=FakeSR; window.webkitSpeechRecognition=FakeSR;
window.SpeechSynthesisUtterance=function(t){this.text=t};
let sp=false; Object.defineProperty(window,'speechSynthesis',{value:{get speaking(){return sp},speak:u=>{sp=true;window.__spoken.push(u.text)}, cancel(){sp=false;window.__cancelled=(window.__cancelled||0)+1}},configurable:true});
"""
SEED="""()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    ctx=b.new_context(viewport={'width':390,'height':844}); ctx.add_init_script(MOCK)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    img=lambda n: {'name':n,'mimeType':'image/png','buffer':png()}
    g("openSituations('leak')")
    ok('report block present: textarea, mic, camera, tts', g("!!document.getElementById('sit-text')&&!!document.getElementById('sit-mic')&&!!document.getElementById('sit-file')&&!!document.getElementById('sit-tts')"))
    ok('camera input uses camera capture and images only', g("document.getElementById('sit-file').getAttribute('capture')")=='environment' and g("document.getElementById('sit-file').accept")=='image/*')
    pg.screenshot(path=S+'/sit_report.png')
    # voice dictation
    pg.click('#sit-mic'); ok('mic recording state', g("document.getElementById('sit-mic').classList.contains('rec')") and g("__recs.length")==1)
    g("__recs[0].emit([['вода течёт с потолка',true],[' на кухне',false]])")
    ok('live dictation into textarea', 'вода течёт' in g("document.getElementById('sit-text').value"))
    pg.click('#sit-mic'); pg.wait_for_timeout(200)
    ok('stop keeps text, mic off', 'на кухне' in g("document.getElementById('sit-text').value") and not g("document.getElementById('sit-mic').classList.contains('rec')"), g("document.getElementById('sit-text').value"))
    # photos
    pg.set_input_files('#sit-file',[img('a.png'),img('b.png')]); pg.wait_for_timeout(400)
    ok('2 photo thumbnails', g("document.querySelectorAll('#sit-photos .sit-photo').length")==2, g("sitPhotos.length"))
    ok('photos stored as downscaled jpeg', g("sitPhotos.every(d=>d.startsWith('data:image/jpeg'))"))
    pg.set_input_files('#sit-file',[img('c.png'),img('d.png')]); pg.wait_for_timeout(400)
    ok('capped at 3 photos', g("sitPhotos.length")==3 and 'до 3' in g("document.getElementById('toast').textContent"))
    pg.click('#sit-photos .sit-photo button >> nth=0'); ok('remove photo', g("sitPhotos.length")==2 and g("document.querySelectorAll('#sit-photos .sit-photo').length")==2)
    pg.set_input_files('#sit-file',[{'name':'x.txt','mimeType':'text/plain','buffer':b'hi'}]); pg.wait_for_timeout(200)
    ok('non-image ignored', g("sitPhotos.length")==2)
    # tts
    pg.click('#sit-tts'); ok('read aloud speaks steps', g("__spoken.length")==1 and 'Перекройте вентили' in g("__spoken[0]") and 'Протечка' in g("__spoken[0]"))
    pg.click('#sit-tts'); ok('second tap stops speech', g("__cancelled||0")>=1)
    # send
    pg.click('#sit-modal >> text=Отправить заявку')
    ok('ticket created О-001, urgent, photos kept', g("ticketBox().box.list[0].id")=='О-001' and g("ticketBox().box.list[0].prio")=='urgent' and g("ticketBox().box.list[0].photos.length")==2 and g("ticketBox().box.list[0].cat")=='💧 Вода и трубы' or g("ticketBox().box.list[0].cat.includes('Вода')"), g("JSON.stringify(ticketBox().box.list[0]).slice(0,200)"))
    ok('text has situation title and dictated words', 'Протечка' in g("ticketBox().box.list[0].text") and 'на кухне' in g("ticketBox().box.list[0].text"))
    ok('popup closed, tickets screen shown with thumbs', not g("document.getElementById('sit-modal').classList.contains('open')") and g("document.querySelector('.screen.active').id")=='screen-tickets' and g("document.querySelectorAll('#tickets-list .sit-photo img').length")==2)
    ok('download text mentions photos', 'Фото: 2' in g("buildTicketText(findTicket('О-001'))"))
    pg.screenshot(path=S+'/sit_ticket_photos.png')
    # empty send
    g("openSituations('lift')"); pg.click('#sit-modal >> text=Отправить заявку')
    ok('empty report refused', 'Опишите ситуацию' in g("document.getElementById('toast').textContent") and g("document.getElementById('sit-modal').classList.contains('open')") and g("ticketBox().box.list.length")==1)
    # photo only
    pg.set_input_files('#sit-file',[img('p.png')]); pg.wait_for_timeout(300); pg.click('#sit-modal >> text=Отправить заявку')
    ok('photo-only report allowed', g("ticketBox().box.list.length")==2 and 'Лифт' in g("ticketBox().box.list[0].text") and g("ticketBox().box.list[0].photos.length")==1)
    # reset on close / switch
    g("openSituations('noise')"); pg.set_input_files('#sit-file',[img('q.png')]); pg.wait_for_timeout(300); g("openSituations('gas')")
    ok('photos reset when another situation opened', g("sitPhotos.length")==0)
    ok('emergency popup also has report block + calls', g("!!document.getElementById('sit-text')") and g("document.querySelectorAll('.sit-call').length")==2)
    g("closeSituations()")
    g("openSituations('meeting')"); ok('meeting situation has no report block', g("!document.getElementById('sit-text')"))
    # ask assistant
    g("closeSituations()"); g("showScreen('screen-home')"); g("openSituations('roof')")
    pg.click('#sit-ask')
    ok('ask assistant: popup closed, chat bot tab open', not g("document.getElementById('sit-modal').classList.contains('open')") and g("document.querySelector('.screen.active').id")=='screen-chat' and g("document.getElementById('chatpane-bot').style.display")=='flex')
    ok('assistant thread has question and steps for the situation', 'Что делать: Течёт кровля' in g("document.getElementById('bot-thread').textContent") and 'Сфотографируйте пятна' in g("document.getElementById('bot-thread').textContent"))
    ok('details action offered and works', g("chatBox().box.bot.slice(-1)[0].actions.slice(-1)[0].do+':'+chatBox().box.bot.slice(-1)[0].actions.slice(-1)[0].arg")=='sit:roof')
    pg.click('#bot-thread button:has-text("Подробно") >> nth=-1'); ok('details reopen popup', g("document.getElementById('sit-modal').classList.contains('open')"))
    g("closeSituations()")
    g("openSituations('meeting')"); ok('ask-assistant also in meeting memo', g("!!document.getElementById('sit-ask')")); g("closeSituations()")
    ok('no page errors', not errs, errs); ctx.close()
    # no speech support
    ctx=b.new_context(viewport={'width':390,'height':844}); ctx.add_init_script("window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;")
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    g("openSituations('leak')"); pg.click('#sit-mic')
    ok('unsupported browser: toast, typing still works', 'не поддерживает' in g("document.getElementById('toast').textContent"))
    pg.fill('#sit-text','капает'); pg.click('#sit-modal >> text=Отправить заявку'); ok('typed report works without speech', g("ticketBox().box.list.length")==1)
    ok('no page errors (no SR)', not errs, errs); b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
