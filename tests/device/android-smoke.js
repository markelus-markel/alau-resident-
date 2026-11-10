// Проверка AlauConcierge на настоящем Chrome телефона (Android) через adb + Playwright.
// Запуск на ПК, телефон по USB, «Отладка по USB» разрешена:
//   npm i playwright        (один раз, в этой папке)
//   node android-smoke.js [адрес]
// По умолчанию проверяется https://alau-concierge.housemasters.kz
// Результат: report.json и скриншоты *.png в папке ALAU_OUT (по умолчанию временная папка, путь печатается в конце). Приложение открывается в чистом
// профиле Chrome, ваши данные на телефоне не затрагиваются. Ничего не отправляется, голос и камера не используются.
const { _android: android } = require('playwright');
const fs = require('fs');
const path = require('path');
const os = require('os');

const URL = process.argv[2] || 'https://alau-concierge.housemasters.kz';
const OUT = process.env.ALAU_OUT || path.join(os.tmpdir(), 'alau-android-smoke');
fs.mkdirSync(OUT, { recursive: true });
const report = { url: URL, started: new Date().toISOString(), device: null, checks: [], pageErrors: [], consoleErrors: [] };
const ok = (name, cond, extra) => { report.checks.push({ name, pass: !!cond, extra: cond ? undefined : String(extra === undefined ? '' : extra).slice(0, 300) }); console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : ' | ' + extra)); };

(async () => {
  const devices = await android.devices();
  if (!devices.length) { console.error('Телефон не найден. Проверьте кабель, «Отладку по USB» и команду adb devices (статус должен быть device).'); process.exit(2); }
  const device = devices[0];
  report.device = { model: device.model(), serial: device.serial() };
  console.log('Телефон:', device.model());
  const context = await device.launchBrowser();
  const page = await context.newPage();
  page.on('pageerror', e => report.pageErrors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') report.consoleErrors.push(m.text()); });
  const shot = async name => { const p = path.join(OUT, name + '.png'); await page.screenshot({ path: p }); };
  const active = () => page.evaluate(() => document.querySelector('.screen.active') && document.querySelector('.screen.active').id);
  const g = fn => page.evaluate(fn);

  await page.goto(URL, { waitUntil: 'load' });
  // демо-жилец в чистом профиле (так же, как в автотестах)
  await g(() => { const u = {}; u['77011234567'] = { phone: '77011234567', last: 'Иванов', first: 'Тест', middle: '', iin: makeTestIIN(), city: 'Семей', street: 'ул. Найманбаева', house: '12', apt: '23' }; lsSet(LS_USERS, u); lsSet(LS_SESSION, '77011234567'); lsSet(LS_WELCOME, { '77011234567': 1 }); });
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(500);
  ok('открылась главная', (await active()) === 'screen-home', await active());
  const vw = await g(() => [innerWidth, document.documentElement.scrollWidth]);
  ok('нет горизонтальной прокрутки на главной', vw[1] <= vw[0] + 1, vw);
  const ask = await g(() => { const e = document.getElementById('home-ask-in'), m = document.getElementById('home-mic'); return { ask: !!e, mic: m ? Math.round(m.getBoundingClientRect().width) : 0 }; });
  ok('поле вопроса и микрофон на главной', ask.ask && ask.mic >= 50, ask);
  ok('микрофон распознаётся браузером телефона (SpeechRecognition)', await g(() => !!(window.SpeechRecognition || window.webkitSpeechRecognition)));
  ok('озвучка телефона доступна (speechSynthesis)', await g(() => 'speechSynthesis' in window));
  await shot('01-home');

  // набранная команда не переходит сама, голосовая переходит сразу (имитация голосового ввода)
  await g(() => { showScreen('screen-chat'); switchChatTab('bot'); botAsk('контакты', 'text'); });
  ok('набранная команда не переходит сама', (await active()) === 'screen-chat', await active());
  await g(() => botAsk('контакты', 'voice'));
  ok('голосовая команда «контакты» открывает экран сразу', (await active()) === 'screen-contacts', await active());
  await shot('02-contacts');
  await g(() => { showScreen('screen-chat'); switchChatTab('bot'); botAsk('передать показания', 'voice'); });
  ok('голосовая команда «передать показания» открывает приборы учёта', (await active()) === 'screen-meters', await active());
  await shot('03-meters');
  await g(() => { showScreen('screen-chat'); switchChatTab('bot'); botAsk('пахнет газом', 'voice'); });
  ok('«пахнет газом» не уводит на другой экран', (await active()) === 'screen-chat', await active());
  await shot('04-gas');
  await g(() => { dlgClose(false); showScreen('screen-announcements'); });
  await shot('05-announcements');
  ok('нет ошибок страницы', report.pageErrors.length === 0, report.pageErrors);

  report.finished = new Date().toISOString();
  report.total = report.checks.length; report.failed = report.checks.filter(c => !c.pass).length;
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log('Отчёт и скриншоты:', OUT);
  console.log('ИТОГО', report.total, 'проверок, упало', report.failed);
  await context.close(); await device.close();
  process.exit(report.failed ? 1 : 0);
})().catch(e => { console.error(e); process.exit(3); });
