import { createRequire } from 'module';
const require = createRequire('C:/Users/zyx/.workbuddy/binaries/node/workspace/');
const { chromium } = require('playwright-core');

const browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--no-sandbox'] });
const page = await browser.newPage();
const logs = [];
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));
await page.addInitScript(() => {
  localStorage.setItem('nex.accessToken', 'fake-jwt-token');
  localStorage.setItem('nex.refreshToken', 'fake-refresh');
  localStorage.setItem('nex.user', JSON.stringify({ uuid: 'u1', email: 't@e.com', profile: { nickname: 'tester', avatar_url: '', direction: null, daily_minutes: 0, plan: 'free', theme: 'light', reduced_motion: false, font_scale: 1 } }));
});
await page.goto('http://127.0.0.1:1420', { waitUntil: 'networkidle' });
await page.waitForTimeout(4000);
const info = await page.evaluate(() => {
  const navs = Array.from(document.querySelectorAll('[class*="km-nav"]')).slice(0, 30).map((el) => ({ cls: el.className, txt: (el.innerText || '').trim().slice(0, 30) }));
  return {
    title: document.title,
    bodyLen: document.body?.innerText?.length ?? -1,
    bodyHead: (document.body?.innerText || '').slice(0, 400),
    navs,
    hasPractice: !!Array.from(document.querySelectorAll('*')).find((e) => (e.innerText || '').includes('练习')),
    allButtons: Array.from(document.querySelectorAll('button')).slice(0, 20).map((b) => b.innerText.trim().slice(0, 20)),
  };
});
console.log('=== PAGE INFO ===');
console.log(JSON.stringify(info, null, 2));
console.log('=== CONSOLE/ERRORS ===');
console.log(logs.slice(0, 40).join('\n'));
await page.screenshot({ path: 'C:/temp/debug_nav.png', fullPage: true });
await browser.close();
