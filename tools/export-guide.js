// Выгружает текст окна «Что умеет приложение» из index.html в registry/guide.json (для озвучки tools/gen_voice.py).
// Использование: node tools/export-guide.js [--check]
// --check: ничего не пишет, завершается с кодом 1, если JSON расходится с index.html.
const fs = require('fs'), path = require('path'), vm = require('vm');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const m = html.match(/const GUIDE_INTRO = [\s\S]*?\nfunction guideText\(\) \{[^\n]*\}\n/);
if (!m) { console.error('Не найден блок GUIDE_INTRO/APP_CAPS/guideText в index.html'); process.exit(2); }
const ctx = {};
vm.runInNewContext(m[0].replace(/const (GUIDE_INTRO|APP_CAPS)/g, 'this.$1') + '\nthis.text = guideText();', ctx);
const out = JSON.stringify({ schema: 'alau-guide/1', note: 'Источник: index.html (APP_CAPS, guideText). Не править руками: node tools/export-guide.js', text: ctx.text }, null, 2) + '\n';
const file = path.join(root, 'registry', 'guide.json');
if (process.argv.includes('--check')) {
  const cur = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
  if (cur !== out) { console.error('registry/guide.json расходится с index.html: запустите node tools/export-guide.js'); process.exit(1); }
  console.log('registry/guide.json совпадает с index.html');
} else { fs.writeFileSync(file, out); console.log('Записано registry/guide.json (' + ctx.text.length + ' знаков)'); }
