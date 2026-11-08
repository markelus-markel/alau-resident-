#!/usr/bin/env python3
"""Озвучка памяток через fal.ai (ElevenLabs Turbo v2.5). Запускается владельцем у себя.

Ключ берётся только из переменной окружения FAL_KEY. В файлы, в index.html и в чат он не попадает.

  python3 tools/gen_voice.py --sample                      # 4 голоса на одной фразе -> audio/samples/
  python3 tools/gen_voice.py --voices Sarah,Alice,Brian,George
  python3 tools/gen_voice.py --voices Sarah --only gas,fire

Для каждого голоса создаётся папка audio/sit/<Голос>/:
  <id>.mp3       текст «Что делать сейчас» (как sitNowText() в index.html)
  <id>-full.mp3  то же + «Что дальше» (как sitFullText(), кнопка «Прочитать вслух»)
  hello.mp3      фраза для кнопки «Послушать» при выборе голоса
  guide.mp3      окно «Что умеет приложение» (текст из registry/guide.json, node tools/export-guide.js)
  manifest.json  ключ -> точный текст файла
Приложение проигрывает файл, только если текст в manifest.json совпадает с текущим реестром,
иначе читает системным голосом. Уже готовые файлы с тем же текстом повторно не генерируются.
"""
import argparse, json, os, sys, urllib.request, urllib.error

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
    a = ap.parse_args()
    key = os.environ.get('FAL_KEY')
    if not key:
        sys.exit('Задайте переменную окружения FAL_KEY (ключ в чат не отправлять).')
    sits = json.load(open(os.path.join(ROOT, 'registry/situations.json'), encoding='utf-8'))['situations']
    if a.sample:
        gas = next(s for s in sits if s['id'] == 'gas')
        out = os.path.join(ROOT, 'audio/samples'); os.makedirs(out, exist_ok=True)
        for v in SAMPLE_VOICES:
            open(os.path.join(out, v + '.mp3'), 'wb').write(tts(now_text(gas), v, key))
            print('готово', v)
        return
    if not a.voices:
        sys.exit('Укажите --voices Имя1,Имя2 (после --sample выберите по прослушиванию).')
    only = set(a.only.split(',')) if a.only else None
    guide = json.load(open(os.path.join(ROOT, 'registry/guide.json'), encoding='utf-8'))['text']
    for voice in a.voices.split(','):
        out = os.path.join(ROOT, 'audio/sit', voice); os.makedirs(out, exist_ok=True)
        mpath = os.path.join(out, 'manifest.json')
        man = json.load(open(mpath, encoding='utf-8')) if os.path.exists(mpath) else {}
        jobs = [('hello', HELLO), ('guide', guide)]
        for s in sits:
            if only and s['id'] not in only:
                continue
            jobs += [(s['id'], now_text(s)), (s['id'] + '-full', full_text(s))]
        for k, t in jobs:
            f = os.path.join(out, k + '.mp3')
            if man.get(k) == t and os.path.exists(f):
                continue
            open(f, 'wb').write(tts(t, voice, key))
            man[k] = t
            json.dump(man, open(mpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('готово', voice, k)


if __name__ == '__main__':
    main()
