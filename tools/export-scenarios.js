// Выгружает тексты озвучки сценариев «вопрос-ответ» из index.html в registry/scenarios.json.
// По этому файлу tools/gen_voice.py заказывает запись голоса. Использование: node tools/export-scenarios.js [--check]
const fs = require('fs'), path = require('path'), vm = require('vm');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const sit = html.match(/const SIT_GROUPS = [\s\S]*?\nconst SITUATIONS = \[[\s\S]*?\n\];/);
const qa = html.match(/const SIT_QA = \{[\s\S]*?\n\};\nfunction sitById/);
const sp = html.match(/\/\/ <qa-speech>[\s\S]*?\/\/ <\/qa-speech>/);
if (!sit || !qa || !sp) { console.error('Не найден блок SITUATIONS, SIT_QA или qa-speech в index.html'); process.exit(2); }
const ctx = {};
const code = [sit[0], qa[0].replace(/\nfunction sitById$/, ''), sp[0]].join('\n').replace(/const (SIT_GROUPS|SIT_LEVELS|SITUATIONS|SIT_QA)/g, 'var $1');
vm.runInNewContext(code, ctx);
const clips = vm.runInContext('qaClips()', ctx);
const data = {
  schema: 'alau-scenarios/1',
  note: 'Источник: index.html (SIT_QA, функции qa-speech). Каждая запись: ключ файла audio/sit/<Голос>/<key>.mp3 и точный текст озвучки. Приложение играет запись, только если текст в manifest.json совпал.',
  count: clips.length,
  chars: clips.reduce((n, c) => n + c.text.length, 0),
  clips,
};
const out = JSON.stringify(data, null, 1) + '\n', file = path.join(root, 'registry', 'scenarios.json');
if (process.argv.includes('--check')) {
  if (!fs.existsSync(file) || fs.readFileSync(file, 'utf8') !== out) { console.error('registry/scenarios.json расходится с index.html: запустите node tools/export-scenarios.js'); process.exit(1); }
  console.log('registry/scenarios.json совпадает с index.html (' + data.count + ' реплик, ' + data.chars + ' знаков)');
} else { fs.writeFileSync(file, out); console.log('Записано ' + data.count + ' реплик, ' + data.chars + ' знаков'); }
