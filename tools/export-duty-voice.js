// Выгружает словарь голоса сводки напоминаний (DUTY_VOICE) из index.html в registry/duty-voice.json для tools/gen_voice.py (--only duty).
// Использование: node tools/export-duty-voice.js [--check]
// --check: ничего не пишет, завершается с кодом 1, если JSON расходится с index.html.
const fs = require('fs'), path = require('path'), vm = require('vm');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const m = html.match(/\/\/ DUTY_VOICE_BEGIN\n([\s\S]*?)\/\/ DUTY_VOICE_END/);
if (!m) { console.error('Не найден блок DUTY_VOICE в index.html'); process.exit(2); }
const ctx = {};
vm.runInNewContext(m[1].replace('const DUTY_VOICE', 'this.DUTY_VOICE'), ctx);
const clips = {}; Object.keys(ctx.DUTY_VOICE).forEach(k => { clips[k] = ctx.DUTY_VOICE[k]; });
const out = JSON.stringify({ schema: 'alau-duty-voice/1', note: 'Источник: index.html (DUTY_VOICE). Не править руками: node tools/export-duty-voice.js', clips }, null, 2) + '\n';
const file = path.join(root, 'registry', 'duty-voice.json');
if (process.argv.includes('--check')) {
  const cur = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
  if (cur !== out) { console.error('registry/duty-voice.json расходится с index.html: запустите node tools/export-duty-voice.js'); process.exit(1); }
  console.log('registry/duty-voice.json совпадает с index.html');
} else { fs.writeFileSync(file, out); console.log('Записано registry/duty-voice.json (' + Object.keys(clips).length + ' слов и фраз)'); }
