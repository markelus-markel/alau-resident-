#!/usr/bin/env python3
"""Проверка графа ситуаций registry/situation-graph.json. Выход 1, если есть ошибки."""
import json, subprocess, sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
errs = []
def err(m): errs.append(m)
g = json.load(open(root / 'registry' / 'situation-graph.json', encoding='utf-8'))
reg = json.load(open(root / 'registry' / 'situations.json', encoding='utf-8'))
ids = {s['id'] for s in reg['situations']}
nodes = {n['id'] for n in g['nodes']}
if nodes != ids: err('узлы графа и реестр ситуаций расходятся: ' + str(sorted(nodes ^ ids)))
seen = set(); deg = {i: 0 for i in ids}
for e in g['edges']:
    a, b, k = e['from'], e['to'], e['kind']
    if a not in ids or b not in ids: err(f'связь {a}->{b}: неизвестная ситуация'); continue
    if a == b: err(f'связь {a}->{a}: петля')
    if k not in g['kinds']: err(f'связь {a}->{b}: неизвестный тип {k}')
    if (a, b) in seen: err(f'связь {a}->{b} повторяется')
    seen.add((a, b)); deg[a] += 1; deg[b] += 1
    if not e['why'].strip() or not e['button'].strip(): err(f'связь {a}->{b}: пустой текст')
    if len(e['button']) > 60: err(f'связь {a}->{b}: подпись кнопки длиннее 60 знаков')
for i, d in deg.items():
    if d == 0: err(f'{i}: ситуация без единой связи')
out = {}
for e in g['edges']: out[e['from']] = out.get(e['from'], 0) + 1
for i, c in out.items():
    if c > 3: print(f'ЗАМЕЧАНИЕ {i}: {c} исходящих связей, помощник покажет три')
sync = subprocess.run(['node', str(root / 'tools' / 'export-graph.js'), '--check'], capture_output=True, text=True)
if sync.returncode: err('граф расходится с index.html: ' + (sync.stderr.strip() or sync.stdout.strip()))
print(f'Граф: {len(g["nodes"])} узлов, {len(g["edges"])} связей, опасных развитий {sum(1 for e in g["edges"] if e["kind"]=="escalates")}')
for e in errs: print('ОШИБКА', e)
print('ИТОГО: ошибок', len(errs))
sys.exit(1 if errs else 0)
