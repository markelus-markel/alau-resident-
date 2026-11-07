import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'tools'))
import fetch_2gis as f
res = []
def ok(n, c, x=''):
    res.append(c); print(('PASS ' if c else 'FAIL ') + n + (' | ' + str(x) if not c else ''))
u = f.build_url('риэлтор', 2, 'SECRET')
ok('URL: q, point, radius, page_size, page', all(s in u for s in ['q=%D1%80', 'point=80.2667%2C50.4233', 'radius=15000', 'page_size=10', 'page=2']), u)
data = {'result': {'total': 3, 'items': [
 {'id': '1', 'name': 'А', 'address_name': 'ул. Х, 1', 'point': {'lat': 50.4, 'lon': 80.2}, 'rubrics': [{'name': 'Риэлторы'}]},
 {'id': '2', 'point': {'lat': 50.4, 'lon': 80.2}}, {'id': '3', 'name': 'Б'}]}}
r = f.parse(data, 'Недвижимость', 'риэлтор')
ok('без названия и без координат отброшены', [x['id'] for x in r] == ['2gis-1'], r)
ok('поля и статус', r[0]['rubrics'] == ['Риэлторы'] and r[0]['status'] == 'не проверено' and r[0]['source'] == '2ГИС')
ok('total читается', f.total(data) == 3 and f.total({}) == 0)
ok('нет телефонов в запрашиваемых полях', 'contact_groups' not in f.FIELDS)
ok('ключ не зашит в код', 'key=' not in (pathlib.Path(f.__file__).read_text(encoding='utf-8').split('def build_url')[0]))
ok('ошибка API распознаётся', 'код 403' in f.api_error({'meta': {'code': 403, 'error': {'message': 'Invalid key'}}}) and 'Invalid key' in f.api_error({'meta': {'code': 403, 'error': {'message': 'Invalid key'}}}))
ok('успешный ответ без ошибки', f.api_error({'meta': {'code': 200}, 'result': {}}) == '' and f.api_error({}) == '')
ok('404 «не найдено» не считается ошибкой', f.not_found({'meta': {'code': 404}}) and f.api_error({'meta': {'code': 404, 'error': {'message': 'Results not found'}}}) == '')
ok('URL без fields по запросу', 'fields' not in f.build_url('x', 1, 'K', fields=False) and 'fields' in f.build_url('x', 1, 'K'))
print('TOTAL', len(res), 'FAILED', res.count(False)); sys.exit(1 if False in res else 0)
