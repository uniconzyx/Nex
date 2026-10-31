const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE = 'C:/Users/zyx/WorkBuddy/2026-09-19-21-42-03/CppMind/web-preview';
const OUT = 'C:/Users/zyx/WorkBuddy/2026-09-19-21-42-03/.taste-skill/inspect/kaimao-moods';
fs.mkdirSync(OUT, { recursive: true });
const logs = [];
const MOODS = ['idle', 'think', 'happy', 'shy', 'celebrate', 'aggrieved', 'sleepy'];

async function open(browser, name, file, vp) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') logs.push('[' + name + '][console] ' + m.text()); });
  page.on('pageerror', e => logs.push('[' + name + '][pageerror] ' + e.message));
  page.on('requestfailed', r => logs.push('[' + name + '][404] ' + r.url().split('/').pop()));
  await page.goto('file:///' + BASE + '/' + file, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  return { ctx, page };
}

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');

  // ---------- 桌面：7 神态立绘切换 ----------
  {
    const { ctx, page } = await open(browser, 'desktop', 'kaimao-desktop.html', { width: 1280, height: 800 });
    await page.evaluate(() => { if (typeof wearDress === 'function') wearDress(0); });
    await page.waitForTimeout(300);
    for (const m of MOODS) {
      await page.evaluate(mm => setMood(mm), m);
      await page.waitForTimeout(400);
      const src = await page.$eval('#catImg', el => el.src.split('/').pop());
      const loaded = await page.$eval('#catImg', el => el.complete && el.naturalWidth > 0);
      logs.push('[desktop] ' + m + ' -> ' + src + ' loaded=' + loaded);
      if (m === 'celebrate') await page.screenshot({ path: path.join(OUT, 'd-celebrate-page.png') });
      const el = await page.$('#catStage');
      if (el) await el.screenshot({ path: path.join(OUT, 'd-mood-' + m + '.png') }).catch(() => {});
    }
    await ctx.close();
  }

  // ---------- 移动：凯喵弹窗 7 神态 ----------
  {
    const { ctx, page } = await open(browser, 'mobile', 'kaimao-mobile.html', { width: 390, height: 844 });
    await page.evaluate(() => { if (typeof wearDress === 'function') wearDress(0); openCat(); });
    await page.waitForTimeout(500);
    for (const m of MOODS) {
      await page.evaluate(mm => setMood(mm), m);
      await page.waitForTimeout(400);
      const src = await page.$eval('#catImg', el => el.src.split('/').pop());
      const loaded = await page.$eval('#catImg', el => el.complete && el.naturalWidth > 0);
      logs.push('[mobile] ' + m + ' -> ' + src + ' loaded=' + loaded);
      if (m === 'celebrate') await page.screenshot({ path: path.join(OUT, 'm-celebrate-sheet.png') });
    }
    await page.evaluate(() => { closeCat(); goTab('home'); });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT, 'm-home.png') });
    await ctx.close();
  }

  fs.writeFileSync(path.join(OUT, '_console.txt'), logs.join('\n'));
  console.log(logs.join('\n'));
  await browser.close().catch(() => {});
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, '_console.txt'), logs.join('\n') + '\nFATAL ' + e.message); process.exit(1); });
