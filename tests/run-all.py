#!/usr/bin/env python3
"""Запуск всех e2e-тестов прототипа одной командой.
Использование: python3 tests/run-all.py [папка_для_скриншотов]
Переменная ALAU_INDEX задаёт путь к index.html (по умолчанию рядом с репозиторием)."""
import os, subprocess, sys, tempfile, time, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
os.environ.setdefault('ALAU_INDEX', str(root / 'index.html'))
shots = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix='alau-shots-')
os.makedirs(shots, exist_ok=True)
total = failed = 0; bad = []
for f in sorted((root / 'tests' / 'e2e').glob('e2e*.py')):
    t = time.time()
    r = subprocess.run([sys.executable, str(f), shots], capture_output=True, text=True)
    last = [l for l in r.stdout.splitlines() if l.startswith('TOTAL')]
    n = fl = 0
    if last:
        p = last[-1].split(); n, fl = int(p[1]), int(p[3])
    else:
        fl = 1
    total += n; failed += fl
    fails = [l for l in r.stdout.splitlines() if l.startswith('FAIL')]
    print(f'{"OK  " if not fl and r.returncode == 0 else "FAIL"} {f.name:22} {n:3} проверок, упало {fl}  ({time.time()-t:.0f} c)')
    for l in fails: print('     ', l)
    if fl or r.returncode: bad.append(f.name); print(r.stderr[-400:])
v = subprocess.run([sys.executable, str(root / 'tests' / 'validate-registry.py')], capture_output=True, text=True)
print(('OK  ' if v.returncode == 0 else 'FAIL') + ' validate-registry.py')
if v.returncode: bad.append('validate-registry.py'); print(v.stdout)
v2 = subprocess.run([sys.executable, str(root / 'tests' / 'validate-onboarding.py')], capture_output=True, text=True)
print(('OK  ' if v2.returncode == 0 else 'FAIL') + ' validate-onboarding.py')
if v2.returncode: bad.append('validate-onboarding.py'); print(v2.stdout)
v3 = subprocess.run([sys.executable, str(root / 'tests' / 'validate-graph.py')], capture_output=True, text=True)
print(('OK  ' if v3.returncode == 0 else 'FAIL') + ' validate-graph.py')
if v3.returncode: bad.append('validate-graph.py'); print(v3.stdout)
v4 = subprocess.run(['node', str(root / 'tools' / 'export-scenarios.js'), '--check'], capture_output=True, text=True)
print(('OK  ' if v4.returncode == 0 else 'FAIL') + ' export-scenarios --check (тексты озвучки сценариев совпадают с реестром)')
if v4.returncode: bad.append('export-scenarios'); print(v4.stderr or v4.stdout)
print(f'ИТОГО: {total} проверок, упало {failed}; скриншоты: {shots}')
sys.exit(1 if bad else 0)
