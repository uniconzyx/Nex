const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE = 'C:/Users/zyx/WorkBuddy/2026-09-19-21-42-03/CppMind/web-preview';
const OUT = 'C:/Users/zyx/WorkBuddy/2026-09-19-21-42-03/.taste-skill/inspect/kaimao-art';
fs.mkdirSync(OUT, { recursive: true });
const logs = [];

async function run(browser, name, file, vp, steps) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') logs.push('[' + name + '] ' + m.text()); });
  page.on('pageerror', e => logs.push('[' + name + '][pageerror] ' + e.message));
  await page.goto('file:///' + BASE + '/' + file, { waitUntil: 'networkidle' });
  await page.waitForTimeout(700);
  await steps(page);
  await ctx.close();
}

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');

  // ---------- 桌面 ----------
  await run(browser, 'desktop', 'kaimao-desktop.html', { width: 1280, height: 800 }, async page => {
    await page.screenshot({ path: path.join(OUT, 'd1-home-idle.png') });
    // 神态切换
    await page.evaluate(() => setMood('sleepy'));
    await page.waitForTimeout(500);
    const src = await page.$eval('#catImg', el => el.src);
    logs.push('[desktop] sleepy src=' + src.split('/').pop());
    await page.screenshot({ path: path.join(OUT, 'd2-home-sleepy.png') });
    // 衣柜
    await page.evaluate(() => { setMood('idle'); openDress(); });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(OUT, 'd3-dress-modal.png') });
    const cards = await page.$$eval('.dress-card', els => els.length);
    logs.push('[desktop] dress cards=' + cards);
    // 穿斗篷
    await page.evaluate(() => { wearDress(1); closeModal(); });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(OUT, 'd4-home-cape.png') });
    const src2 = await page.$eval('#catImg', el => el.src);
    logs.push('[desktop] cape src=' + src2.split('/').pop());
    // 回到默认
    await page.evaluate(() => { wearDress(0); });
    await page.waitForTimeout(400);
  });

  // ---------- 移动 ----------
  await run(browser, 'mobile', 'kaimao-mobile.html', { width: 390, height: 844 }, async page => {
    await page.evaluate(() => goTab('dress'));
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT, 'm1-dress.png') });
    const cards = await page.$$eval('.dress-card', els => els.length);
    logs.push('[mobile] dress cards=' + cards);
    // 穿赛博朋克
    await page.evaluate(() => { wearDress(5); });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(OUT, 'm2-dress-cyber.png') });
    // 凯喵面板（神态）
    await page.evaluate(() => { wearDress(0); setMood('happy'); openCat(); });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(OUT, 'm3-cat-happy.png') });
    const src = await page.$eval('#catImg', el => el.src);
    logs.push('[mobile] happy src=' + src.split('/').pop());
    // 主城 + FAB
    await page.evaluate(() => { closeCat(); goTab('home'); });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT, 'm4-home.png') });
  });

  fs.writeFileSync(path.join(OUT, '_console.txt'), logs.join('\n'));
  console.log('DONE');
  await browser.close();
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, '_console.txt'), logs.join('\n') + '\nFATAL ' + e.message); process.exit(1); });
