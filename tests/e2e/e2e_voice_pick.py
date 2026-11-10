import os
import sys
from playwright.sync_api import sync_playwright
res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x)[:300] if not c else ''))
URL = 'file://' + os.environ.get('ALAU_INDEX', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'index.html'))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}); pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); g = pg.evaluate
    pick = lambda arr: g("(a)=>{const v=pickRuVoice(a);return v?v.name:null}", arr)
    V = lambda name, lang='ru-RU', local=True: {'name': name, 'lang': lang, 'voiceURI': name, 'localService': local}
    ok('no voices: no pick', pick([]) is None)
    ok('no Russian voices: no pick', pick([V('English US', 'en-US')]) is None)
    ok('only one Russian voice is taken', pick([V('English', 'en-US'), V('Русский')]) == 'Русский')
    ok('Google network voice beats a plain local one', pick([V('Русский'), V('Google русский', 'ru-RU', False)]) == 'Google русский')
    ok('natural/neural voice beats a plain one', pick([V('Русский'), V('Microsoft Svetlana Online (Natural)', 'ru-RU', False)]) == 'Microsoft Svetlana Online (Natural)')
    ok('compact/espeak voice is the last choice', pick([V('espeak ru compact'), V('Русский')]) == 'Русский')
    ok('ru_RU with underscore is recognised', pick([V('Русский', 'ru_RU')]) == 'Русский')
    # speak() подставляет выбранный голос в реплику
    g("""()=>{window.__u=null; window.SpeechSynthesisUtterance=function(t){this.text=t;}; speechSynthesis.getVoices=()=>[{name:'Русский',lang:'ru-RU',voiceURI:'a',localService:true},{name:'Google русский',lang:'ru-RU',voiceURI:'b',localService:false}]; speechSynthesis.cancel=()=>{}; speechSynthesis.speak=u=>{window.__u=u;}; speak('Проверка голоса');}""")
    pg.wait_for_timeout(100)
    ok('speak() uses the picked voice', g("window.__u && window.__u.voice && window.__u.voice.name") == 'Google русский', g("window.__u && window.__u.voice && window.__u.voice.name"))
    ok('speak() keeps Russian language', g("window.__u && window.__u.lang").lower().startswith('ru'))
    g("""()=>{window.__u=null; speechSynthesis.getVoices=()=>[]; speak('Без голосов');}"""); pg.wait_for_timeout(100)
    ok('speak() still works with no voice list', g("window.__u && window.__u.lang") == 'ru-RU')
    # ударения для слов консьержа
    st = lambda w: g("(w)=>ttsStress(w)", w)
    ok('stress mark on «просрочено»', st('просрочено') == 'просро\u0301чено', st('просрочено'))
    ok('capital letter is kept', st('Просрочено: 1 счёт') == 'Просро\u0301чено: 1 счёт', st('Просрочено: 1 счёт'))
    ok('«показания» and «передать»', 'показа\u0301ния' in st('передать показания') and 'переда\u0301ть' in st('передать показания'))
    ok('other words are untouched', st('дом лифт замена') == 'дом лифт замена', st('дом лифт замена'))
    ok('a word is not stressed inside a longer word', st('показаниями') == 'показаниями', st('показаниями'))
    ok('old stress for «замок» still works', 'замо\u0301к' in st('замок'))
    ok('no page errors', not errs, errs)
    ctx.close(); b.close()
print('TOTAL', len(res), 'FAILED', res.count(False))
