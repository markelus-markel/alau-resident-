# Проверка на настоящем телефоне (Android)

`android-smoke.js` открывает приложение в Chrome на телефоне через adb и Playwright, в чистом профиле (данные телефона не затрагиваются). Голос и камера не используются.

Условия: на ПК `adb` и `npm i playwright`; телефон по USB, «Отладка по USB» разрешена (`adb devices` показывает `device`); в Chrome телефона (`chrome://flags`) включено «Enable command line on non-rooted devices».

Запуск: `node tests/device/android-smoke.js [адрес]` (по умолчанию https://alau-concierge.housemasters.kz). Папка результата: переменная `ALAU_OUT`, иначе временная, путь печатается в конце.

В `tests/run-all.py` не входит: нужен физический телефон.
