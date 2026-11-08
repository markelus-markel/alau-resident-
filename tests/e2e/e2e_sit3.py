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
    top=lambda: g("(document.querySelector('#sit-body .sit-row')||{dataset:{}}).dataset.sit")
    cnt=lambda: g("document.querySelectorAll('#sit-body .sit-row').length")
    g("openSituations()")
    ok('hint explains typing and voice', 'наберите' in g("document.getElementById('sit-search-wrap').textContent").lower() and 'голосом' in g("document.getElementById('sit-search-wrap').textContent"))
    ok('voice button next to search', g("!!document.getElementById('sit-vmic')"))
    pg.screenshot(path=S+'/sit_search.png')
    for q,exp in [('капает с потолка','leak'),('застрял лифт','lift'),('не горит свет','power'),('пахнет газом','gas'),('тараканы',None),('батареи холодные','heat'),('соседи шумят','noise'),('потекла крыша','roof'),('квитанция','bill')]:
        pg.fill('#sit-search',q)
        if exp: ok(f'"{q}" -> top suggestion {exp}', top()==exp, (top(), cnt()))
    pg.fill('#sit-search','протечка'); ok('suggestions label shown', 'Подсказки из реестра' in g("document.getElementById('sit-body').textContent"))
    pg.fill('#sit-search',''); ok('empty query restores grouped list', cnt()==g("SITUATIONS.length") and 'Опасные ситуации' in g("document.getElementById('sit-body').textContent"))
    pg.fill('#sit-search','абвгд'); ok('no match -> ask assistant button', 'ничего не нашлось' in g("document.getElementById('sit-body').textContent") and g("[...document.querySelectorAll('#sit-body button')].some(b=>b.textContent.includes('Спросить помощника'))"))
    pg.click('#sit-body >> text=Спросить помощника')
    ok('assistant button opens chat bot tab and answers the typed query', not g("document.getElementById('sit-modal').classList.contains('open')") and g("document.getElementById('chatpane-bot').style.display")=='flex' and 'абвгд' in g("document.getElementById('bot-thread').textContent") and 'Не поняла' in g("document.getElementById('bot-thread').textContent"))
    # voice
    g("showScreen('screen-home')"); g("openSituations()")
    pg.click('#sit-vmic'); ok('voice search recording', g("document.getElementById('sit-vmic').classList.contains('rec')") and g("__recs.length")==1 and g("__recs[0].lang")=='ru-RU')
    g("__recs[0].emit([['у меня пахнет газом на лестнице',true]])")
    ok('live text in search box', 'пахнет газом' in g("document.getElementById('sit-search').value"))
    pg.click('#sit-vmic'); pg.wait_for_timeout(300)
    ok('voice result filters registry, gas first', top()=='gas' and 'пахнет газом' in g("document.getElementById('sit-search').value"), (top(), g("document.getElementById('sit-search').value")))
    ok('assistant answers aloud with situation and steps', g("__spoken.length")==1 and 'Запах газа' in g("__spoken[0]") and 'Не включайте' in g("__spoken[0]"), g("__spoken"))
    pg.click('#sit-body .sit-row'); ok('suggestion opens the memo', 'Запах газа' in g("document.getElementById('sit-title').textContent"))
    g("openSituations()"); pg.click('#sit-vmic'); g("__recs[1].emit([['абракадабра',true]])"); pg.click('#sit-vmic'); pg.wait_for_timeout(300)
    ok('voice no match -> spoken hint, ask button', g("__spoken.some(t=>t.includes('не нашлось'))") and 'ничего не нашлось' in g("document.getElementById('sit-body').textContent"), g("__spoken"))
    g("closeSituations()"); ok('no page errors', not errs, errs); ctx.close()
    ctx=b.new_context(viewport={'width':390,'height':844}); ctx.add_init_script("window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;")
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    g("openSituations()"); pg.click('#sit-vmic'); ok('unsupported: toast', 'не поддерживает' in g("document.getElementById('toast').textContent"))
    pg.fill('#sit-search','лифт'); ok('typing search still works', g("document.querySelectorAll('#sit-body .sit-row').length")>=1)
    ok('no page errors (no SR)', not errs, errs); b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
