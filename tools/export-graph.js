// Выгружает граф связей ситуаций из index.html в registry/situation-graph.json и registry/situation-graph.mmd (схема Mermaid).
// Использование: node tools/export-graph.js [--check]
const fs = require('fs'), path = require('path'), vm = require('vm');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const m = html.match(/const SIT_GROUPS = [\s\S]*?\nconst SITUATIONS = \[[\s\S]*?\n\];/);
const g = html.match(/const SIT_GRAPH_KINDS = [\s\S]*?\nconst SIT_GRAPH = \[[\s\S]*?\n\];/);
if (!m || !g) { console.error('Не найден блок SITUATIONS или SIT_GRAPH в index.html'); process.exit(2); }
const ctx = {};
vm.runInNewContext((m[0] + '\n' + g[0]).replace(/const (SIT_GROUPS|SIT_LEVELS|SITUATIONS|SIT_GRAPH_KINDS|SIT_GRAPH)/g, 'this.$1'), ctx);
const groups = Object.fromEntries(ctx.SIT_GROUPS);
const data = {
  schema: 'alau-situation-graph/1',
  note: 'Источник: index.html (SIT_GRAPH). Ребро escalates: ситуация может перейти в другую; related: обычная связь. Тексты кнопок видит жилец.',
  kinds: ctx.SIT_GRAPH_KINDS,
  nodes: ctx.SITUATIONS.map(s => ({ id: s.id, group: s.grp, level: s.level, icon: s.icon, title: s.title })),
  edges: ctx.SIT_GRAPH.map(([from, to, kind, why, button]) => ({ from, to, kind, why, button })),
};
// схема Mermaid: подграфы по группам, сплошная жирная стрелка для опасного развития, пунктир для связей
const lines = ['flowchart LR'];
Object.keys(groups).forEach(gid => {
  const ns = ctx.SITUATIONS.filter(s => s.grp === gid); if (!ns.length) return;
  lines.push('  subgraph ' + gid + '["' + groups[gid].replace(/"/g, '') + '"]');
  ns.forEach(s => lines.push('    ' + s.id + '["' + s.icon + ' ' + s.title.replace(/"/g, '') + '"]'));
  lines.push('  end');
});
ctx.SIT_GRAPH.forEach(([f, t, k, why]) => lines.push('  ' + f + (k === 'escalates' ? ' ==>|"' : ' -.->|"') + why.replace(/"/g, '') + '"| ' + t));
lines.push('  classDef emergency fill:#fde7e7,stroke:#c62828,color:#7f1d1d');
lines.push('  classDef urgent fill:#fff4e0,stroke:#b45309,color:#78350f');
lines.push('  class ' + ctx.SITUATIONS.filter(s => s.level === 'emergency').map(s => s.id).join(',') + ' emergency');
lines.push('  class ' + ctx.SITUATIONS.filter(s => s.level === 'urgent').map(s => s.id).join(',') + ' urgent');
const outJson = JSON.stringify(data, null, 2) + '\n', outMmd = lines.join('\n') + '\n';
const fj = path.join(root, 'registry', 'situation-graph.json'), fm = path.join(root, 'registry', 'situation-graph.mmd');
if (process.argv.includes('--check')) {
  const ok = fs.existsSync(fj) && fs.readFileSync(fj, 'utf8') === outJson && fs.existsSync(fm) && fs.readFileSync(fm, 'utf8') === outMmd;
  if (!ok) { console.error('registry/situation-graph.* расходится с index.html: запустите node tools/export-graph.js'); process.exit(1); }
  console.log('registry/situation-graph совпадает с index.html (' + data.nodes.length + ' узлов, ' + data.edges.length + ' связей)');
} else {
  fs.writeFileSync(fj, outJson); fs.writeFileSync(fm, outMmd); console.log('Записано: ' + data.nodes.length + ' узлов, ' + data.edges.length + ' связей');
}
