// Выгружает реестр ситуаций из index.html в registry/situations.json.
// Использование: node tools/export-registry.js [--check]
// --check: ничего не пишет, завершается с кодом 1, если JSON расходится с index.html.
const fs = require('fs'), path = require('path'), vm = require('vm');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const m = html.match(/const SIT_GROUPS = [\s\S]*?\nconst SITUATIONS = \[[\s\S]*?\n\];/);
if (!m) { console.error('Не найден блок SIT_GROUPS/SITUATIONS в index.html'); process.exit(2); }
const ctx = {};
vm.runInNewContext(m[0].replace(/const (SIT_GROUPS|SIT_LEVELS|SITUATIONS)/g, 'this.$1'), ctx);
const reg = {
  schema: 'alau-situations/1',
  version: 1,
  note: 'Источник: index.html (SITUATIONS). Казахские поля kk не заполнены: нужен эксперт по терминологии, переводы памяток об опасных ситуациях без проверки не вносить.',
  groups: ctx.SIT_GROUPS.map(([id, title]) => ({ id, title })),
  levels: Object.fromEntries(Object.entries(ctx.SIT_LEVELS).map(([k, v]) => [k, { label: v[0] }])),
  situations: ctx.SITUATIONS.map(s => ({
    id: s.id, group: s.grp, level: s.level, icon: s.icon, category: s.cat,
    ru: { title: s.title, now: s.now, next: s.next },
    kk: null,
    keywords_ru: s.kw,
    calls: (s.call || []).map(([number, label]) => ({ number, label })),
  })),
};
const out = JSON.stringify(reg, null, 2) + '\n';
const file = path.join(root, 'registry', 'situations.json');
if (process.argv.includes('--check')) {
  const cur = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
  if (cur !== out) { console.error('registry/situations.json расходится с index.html: запустите node tools/export-registry.js'); process.exit(1); }
  console.log('registry/situations.json совпадает с index.html (' + reg.situations.length + ' ситуаций)');
} else {
  fs.writeFileSync(file, out); console.log('Записано ' + reg.situations.length + ' ситуаций в registry/situations.json');
}
