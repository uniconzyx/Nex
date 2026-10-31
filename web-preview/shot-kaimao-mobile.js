const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const FILE = 'file:///C:/Users/zyx/WorkBuddy/2026-09-19-21-42-03/CppMind/web-preview/kaimao-mobile.html';
const OUT = 'C:/Users/zyx/WorkBuddy/2026-09-19-21-42-03/.taste-skill/inspect/kaimao-mobile';
fs.mkdirSync(OUT, { recursive: true });

const TABS = ['home','learn','boss','bestiary','story','checkin','dress','lab','bag','rank','mini','achievements','me','settings'];

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') logs.push('[' + m.type() + '] ' + m.text()); });
  page.on('pageerror', e => logs.push('[pageerror] ' + e.message));

  await page.goto(FILE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(700);

  // home (light)
  await page.screenshot({ path: path.join(OUT, '00-home.png') });
  // home dark proof
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'));
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(OUT, '00-home-dark.png') });
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));

  // each tab
  for (let i = 0; i < TABS.length; i++) {
    const v = TABS[i];
    await page.evaluate(t => { if (window.goTab) goTab(t); }, v);
    await page.waitForTimeout(450);
    const n = String(i + 1).padStart(2, '0') + '-' + v;
    await page.screenshot({ path: path.join(OUT, n + '.png') });
  }

  fs.writeFileSync(path.join(OUT, '_console.txt'), logs.length ? logs.join('\n') : 'NO_CONSOLE_ERRORS');
  console.log('SHOTS_DONE=' + TABS.length + ' errors=' + logs.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
