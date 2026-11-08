#!/usr/bin/env python3
"""Озвучка памяток через fal.ai (ElevenLabs Turbo v2.5). Запускается владельцем у себя.

Ключ берётся только из переменной окружения FAL_KEY. В файлы, в index.html и в чат он не попадает.

  python3 tools/gen_voice.py --sample                      # 4 голоса на одной фразе -> audio/samples/
  python3 tools/gen_voice.py --voices Sarah,Alice,Brian,George
  python3 tools/gen_voice.py --voices Sarah --only gas,fire
  python3 tools/gen_voice.py --voices Sarah --only qa      # только реплики сценариев «вопрос-ответ»
  python3 tools/gen_voice.py --stress-sample               # слово «замок» с ударением и без -> audio/samples/

Для каждого голоса создаётся папка audio/sit/<Голос>/:
  <id>.mp3       текст «Что делать сейчас» (как sitNowText() в index.html)
  <id>-full.mp3  то же + «Что дальше» (как sitFullText(), кнопка «Прочитать вслух»)
  hello.mp3      фраза для кнопки «Послушать» при выборе голоса
  guide.mp3      окно «Что умеет приложение» (текст из registry/guide.json, node tools/export-guide.js)
  qa-<id>-start.mp3, qa-<id>-<узел>-<N>.mp3  реплики сценариев (тексты из registry/scenarios.json, node tools/export-scenarios.js)
  manifest.json  ключ -> точный текст файла
Приложение проигрывает файл, только если текст в manifest.json совпадает с текущим реестром,
иначе читает системным голосом. Уже готовые файлы с тем же текстом повторно не генерируются.
"""
import argparse, json, os, re, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'https://fal.run/fal-ai/elevenlabs/tts/turbo-v2.5'
SAMPLE_VOICES = ['Sarah', 'Alice', 'Brian', 'George']
HELLO = 'Здравствуйте! Я помощник AlauConcierge. Так я буду читать вам подсказки.'


def now_text(s):
    ru = s['ru']
    pre = 'При угрозе жизни сначала звоните сто двенадцать. ' if s['level'] == 'emergency' else ''
    return pre + ru['title'] + '. Что делать сейчас. ' + ' '.join(ru['now'])


def full_text(s):
    return now_text(s) + ' Что дальше. ' + ' '.join(s['ru']['next'])


STRESS = {'замок': 'замо\u0301к', 'замка': 'замка\u0301', 'замку': 'замку\u0301', 'замком': 'замко\u0301м', 'замке': 'замке\u0301',
          'замки': 'замки\u0301', 'замков': 'замко\u0301в', 'замкам': 'замка\u0301м', 'замками': 'замка\u0301ми', 'замках': 'замка\u0301х'}


def stress(text):
    """Ставит знак ударения на «замок» (запирающее устройство). То же, что ttsStress() в index.html."""
    def f(m):
        w = m.group(0); r = STRESS.get(w.lower())
        return w if not r else (w[0] + r[1:] if w[0] == 'З' else r)
    return re.sub(r'(?<![а-яё])[Зз]ам(?:ок|к(?:а|у|ом|е|и|ов|ам|ами|ах))(?![а-яё])', f, text)


def tts(text, voice, key):
    body = json.dumps({'text': text, 'voice': voice, 'language_code': 'ru',
                       'stability': 0.55, 'similarity_boost': 0.75, 'speed': 0.95}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        'Authorization': 'Key ' + key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            audio_url = json.load(r)['audio']['url']
        with urllib.request.urlopen(audio_url, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit('fal.ai вернул %s: %s' % (e.code, e.read()[:300].decode('utf-8', 'replace')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', action='store_true')
    ap.add_argument('--voices')
    ap.add_argument('--only')
    ap.add_argument('--stress', action='store_true', help='ставить знак ударения на слово «замок» (сначала проверьте --stress-sample)')
    ap.add_argument('--stress-sample', action='store_true')
    a = ap.parse_args()
    key = os.environ.get('FAL_KEY')
    if not key:
        sys.exit('Задайте переменную окружения FAL_KEY (ключ в чат не отправлять).')
    sits = json.load(open(os.path.join(ROOT, 'registry/situations.json'), encoding='utf-8'))['situations']
    if a.sample:
        gas = next(s for s in sits if s['id'] == 'gas')
        out = os.path.join(ROOT, 'audio/samples'); os.makedirs(out, exist_ok=True)
        for v in SAMPLE_VOICES:
            audio = tts(now_text(gas), v, key)
            open(os.path.join(out, v + '.mp3'), 'wb').write(audio)
            print('готово', v)
        return
    if a.stress_sample:
        out = os.path.join(ROOT, 'audio/samples'); os.makedirs(out, exist_ok=True)
        t = 'Не бейте по замку. Если замок не запирается, не оставляйте квартиру без присмотра.'
        plain, marked = tts(t, 'Sarah', key), tts(stress(t), 'Sarah', key)
        open(os.path.join(out, 'lock-plain.mp3'), 'wb').write(plain)
        open(os.path.join(out, 'lock-stress.mp3'), 'wb').write(marked)
        print('готово lock-plain.mp3 и lock-stress.mp3: послушайте оба, какой правильнее произносит «замОк»')
        return
    if not a.voices:
        sys.exit('Укажите --voices Имя1,Имя2 (после --sample выберите по прослушиванию).')
    only = set(a.only.split(',')) if a.only else None
    qa_only = only == {'qa'}
    guide = json.load(open(os.path.join(ROOT, 'registry/guide.json'), encoding='utf-8'))['text']
    scen = json.load(open(os.path.join(ROOT, 'registry/scenarios.json'), encoding='utf-8'))['clips']
    for voice in a.voices.split(','):
        out = os.path.join(ROOT, 'audio/sit', voice); os.makedirs(out, exist_ok=True)
        mpath = os.path.join(out, 'manifest.json')
        man = json.load(open(mpath, encoding='utf-8')) if os.path.exists(mpath) else {}
        jobs = [] if qa_only else [('hello', HELLO), ('guide', guide)]
        for s in ([] if qa_only else sits):
            if only and s['id'] not in only:
                continue
            jobs += [(s['id'], now_text(s)), (s['id'] + '-full', full_text(s))]
        if not only or qa_only:
            jobs += [(c['key'], c['text']) for c in scen]
        for k, t in jobs:
            f = os.path.join(out, k + '.mp3')
            if man.get(k) == t and os.path.exists(f):
                continue
            audio = tts(stress(t) if a.stress else t, voice, key)  # файл создаём только после успешного ответа
            open(f, 'wb').write(audio)
            man[k] = t
            json.dump(man, open(mpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('готово', voice, k)


if __name__ == '__main__':
    main()
