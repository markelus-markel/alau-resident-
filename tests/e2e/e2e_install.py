import os
import sys
import json
import base64
from playwright.sync_api import sync_playwright
S=sys.argv[1]; res=[]
def ok(n,c,x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ')+n+(' | '+str(x)[:300] if not c else ''))
URL='file://'+os.environ.get('ALAU_INDEX','/home/claude/alau-resident-/index.html')
PNGSIG=b'\x89PNG\r\n\x1a\n'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    pg=b.new_context(viewport={'width':390,'height':844}).new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(URL); g=pg.evaluate
    ok('theme-color set', g("document.querySelector('meta[name=theme-color]').content")=='#0f5f52')
    ok('standalone meta for Android and iOS', g("!!document.querySelector('meta[name=mobile-web-app-capable]')") and g("document.querySelector('meta[name=apple-mobile-web-app-capable]').content")=='yes')
    ok('iOS title', g("document.querySelector('meta[name=apple-mobile-web-app-title]').content")=='AlauConcierge')
    ok('static svg favicon present', g("document.querySelector('link[rel=icon]').href.startsWith('data:image/svg+xml')"))
    t=g("document.querySelector('link[rel=apple-touch-icon]').href")
    ok('apple-touch-icon is a real PNG', t.startswith('data:image/png;base64,') and base64.b64decode(t.split(',',1)[1])[:8]==PNGSIG)
    man=g("fetch(document.querySelector('link[rel=manifest]').href).then(r=>r.json())")
    ok('manifest name and display', man['name']=='AlauConcierge' and man['display']=='standalone' and man['lang']=='ru', man)
    ok('manifest start_url is this page (no hash)', man['start_url']==URL.split('#')[0] and man['scope'].endswith('/'), man)
    sizes={i['sizes'] for i in man['icons']}
    ok('manifest has 192 and 512 icons', sizes=={'192x192','512x512'})
    ok('manifest icons are valid PNG data', all(i['src'].startswith('data:image/png;base64,') and base64.b64decode(i['src'].split(',',1)[1])[:8]==PNGSIG for i in man['icons']))
    ok('manifest colors match app', man['theme_color']=='#0f5f52' and man['background_color']=='#f0f2f5')
    # иконка не пустая: в PNG есть и фон, и белая буква
    ok('icon drawn (teal pixel and white pixel)', g("(async()=>{const m=await fetch(document.querySelector('link[rel=manifest]').href).then(r=>r.json());const im=new Image();im.src=m.icons[1].src;await im.decode();const c=document.createElement('canvas');c.width=c.height=512;const x=c.getContext('2d');x.drawImage(im,0,0);const a=x.getImageData(256,40,1,1).data,w=x.getImageData(0,0,512,512).data;let white=0;for(let i=0;i<w.length;i+=4)if(w[i]>240&&w[i+1]>240&&w[i+2]>240&&w[i+3]>240)white++;return a[1]>120&&a[0]<60&&white>3000})()"))
    ok('only one manifest and one touch icon (no duplicates)', g("document.querySelectorAll('link[rel=manifest]').length")==1 and g("document.querySelectorAll('link[rel=apple-touch-icon]').length")==1)
    ok('no page errors', not errs, errs)
    b.close()
print('TOTAL',len(res),'FAILED',res.count(False))
