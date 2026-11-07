"""Сквозная проверка настоящего OCR (Tesseract.js) на синтетическом счёте.
CDN подменяется локальными файлами из npm: нужна папка с node_modules (tesseract.js@5.1.1, tesseract.js-core, @tesseract.js-data/rus),
путь в переменной ALAU_OCR_NM. Без неё тест пропускается и честно сообщает об этом (0 проверок)."""
import os
import re
import sys
from playwright.sync_api import sync_playwright
S=sys.argv[1]; res=[]
def ok(n,c,x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ')+n+(' | '+str(x)[:300] if not c else ''))
NM=os.environ.get('ALAU_OCR_NM')
if not NM or not os.path.isdir(os.path.join(NM,'node_modules','tesseract.js')):
    print('SKIP real OCR: задайте ALAU_OCR_NM (папка с node_modules: tesseract.js, tesseract.js-core, @tesseract.js-data/rus)')
    print('TOTAL 0 FAILED 0'); sys.exit(0)
from PIL import Image, ImageDraw, ImageFont
f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',30); fb=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',34)
im=Image.new('RGB',(1100,900),'white'); d=ImageDraw.Draw(im); y=40
for t,ft in [("КВИТАНЦИЯ ЗА ЭЛЕКТРОЭНЕРГИЮ",fb),("Период: октябрь 2026",f),("Лицевой счет: 123456789",f),("Потреблено: 245 кВтч",f),("Тариф: 20,87 тенге",f),("Начислено: 5 113,15",f),("Итого к оплате: 12 345,50 тенге",fb),("Оплатить до 10.11.2026",f)]:
    d.text((50,y),t,fill='black',font=ft); y+=95
im.save(S+'/bill_real.png')
SEED="""()=>{const u={};u['77011234567']={phone:'77011234567',last:'Иванов',first:'Тест',middle:'',iin:makeTestIIN(),city:'Семей',street:'ул. Найманбаева',house:'12',apt:'23'};lsSet(LS_USERS,u);lsSet(LS_SESSION,'77011234567');}"""
URL='file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')
served=[]
def route(r):
    path=r.request.url.split('/npm/',1)[1]
    m=re.match(r'tesseract\.js@[^/]+/(.*)',path); local=None
    if m: local=os.path.join(NM,'node_modules','tesseract.js',m.group(1))
    m=re.match(r'tesseract\.js-core@[^/]+/(.*)',path)
    if m: local=os.path.join(NM,'node_modules','tesseract.js-core',m.group(1))
    m=re.match(r'(@tesseract\.js-data/.*)',path)
    if m: local=os.path.join(NM,'node_modules',m.group(1))
    if not local or not os.path.isfile(local): served.append(('404',path)); r.fulfill(status=404,body=''); return
    served.append(('ok',path))
    ct='application/wasm' if local.endswith('.wasm') else 'application/javascript' if local.endswith('.js') else 'application/octet-stream'
    r.fulfill(status=200,body=open(local,'rb').read(),headers={'access-control-allow-origin':'*','content-type':ct})
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    ctx=b.new_context(viewport={'width':390,'height':844}); ctx.route('https://cdn.jsdelivr.net/npm/**',route)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(URL); pg.evaluate(SEED); pg.reload(); g=lambda js: pg.evaluate(js)
    g("showScreen('screen-bills')"); pg.click('#bl-add')
    pg.set_input_files('#bl-file', S+'/bill_real.png')
    pg.wait_for_function("document.getElementById('bl-banner').textContent.includes('Распознано')||document.getElementById('bl-banner').textContent.includes('не удалось')||document.getElementById('bl-banner').textContent.includes('не распознаны')",timeout=150000)
    vals=g("[$('bl-kind').value,$('bl-period').value,$('bl-amount').value,$('bl-due').value,$('bl-account').value]")
    ok('real OCR filled all 5 fields from the photo', vals==['elec','2026-10','12345.5','2026-11-10','123456789'], (vals,g("$('bl-banner').textContent"),served[-5:]))
    ok('SRI-pinned library loaded from CDN path', any(x[1].startswith('tesseract.js@5.1.1/dist/tesseract.min.js') for x in served))
    pg.screenshot(path=S+'/bills_real_ocr.png')
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
