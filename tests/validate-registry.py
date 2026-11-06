#!/usr/bin/env python3
"""Проверка реестра ситуаций registry/situations.json. Выход 1, если есть ошибки."""
import json, re, subprocess, sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
errs = []
def err(m): errs.append(m)
reg = json.load(open(root / 'registry' / 'situations.json', encoding='utf-8'))
html = (root / 'index.html').read_text(encoding='utf-8')
cats = set(re.findall(r"(\w+):\s*'[^']*'", re.search(r"const mvCatMap = \{(.*?)\};", html, re.S).group(1)))
groups = {g['id'] for g in reg['groups']}
levels = set(reg['levels'])
NATIONAL = {'112', '101', '102', '103', '104'}
ids = [s['id'] for s in reg['situations']]
if len(ids) != len(set(ids)): err('повторяются id ситуаций')
if reg.get('schema') != 'alau-situations/1': err('неверная schema')
# регулярные выражения проверяем в JS, как их применяет приложение
kws = [s['keywords_ru'] for s in reg['situations']]
js = "const k=JSON.parse(require('fs').readFileSync(0,'utf8'));k.forEach((x,i)=>{try{new RegExp(x,'i')}catch(e){console.log(i+': '+e.message)}})"
bad = subprocess.run(['node', '-e', js], input=json.dumps(kws), capture_output=True, text=True).stdout.strip()
if bad: err('не компилируются keywords_ru: ' + bad)
for s in reg['situations']:
    i = s['id']
    if s['group'] not in groups: err(f'{i}: неизвестная группа {s["group"]}')
    if s['level'] not in levels: err(f'{i}: неизвестный уровень {s["level"]}')
    if s['category'] not in cats: err(f'{i}: категория {s["category"]} нет в mvCatMap')
    ru = s.get('ru') or {}
    if not ru.get('title'): err(f'{i}: нет заголовка ru')
    if not ru.get('now'): err(f'{i}: пустой список «что делать сейчас»')
    if not ru.get('next'): err(f'{i}: пустой список «что дальше»')
    for c in s['calls']:
        if c['number'] not in NATIONAL: err(f'{i}: телефон {c["number"]} не национальный (разрешены {sorted(NATIONAL)})')
    if s['level'] == 'emergency':
        nums = {c['number'] for c in s['calls']}
        if '112' not in nums: err(f'{i}: у опасной ситуации нет 112')
        if len(nums) < 2: err(f'{i}: у опасной ситуации должна быть профильная служба и 112')
    kk = s.get('kk')
    if kk is not None:
        if not kk.get('title') or len(kk.get('now', [])) != len(ru.get('now', [])) or len(kk.get('next', [])) != len(ru.get('next', [])):
            err(f'{i}: казахский текст неполный: заголовок и число шагов должны совпадать с ru')
sync = subprocess.run(['node', str(root / 'tools' / 'export-registry.js'), '--check'], capture_output=True, text=True)
if sync.returncode: err('JSON расходится с index.html: ' + (sync.stderr.strip() or sync.stdout.strip()))
kk_done = sum(1 for s in reg['situations'] if s.get('kk'))
print(f'Реестр: {len(ids)} ситуаций, казахский заполнен: {kk_done}/{len(ids)}')
for e in errs: print('ОШИБКА', e)
print('ИТОГО: ошибок', len(errs))
sys.exit(1 if errs else 0)
