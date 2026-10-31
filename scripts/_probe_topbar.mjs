import { createRequire } from 'module';
const require = createRequire('C:/Users/zyx/.workbuddy/binaries/node/workspace/');
const { chromium } = require('playwright-core');

const browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
await page.goto('http://127.0.0.1:1420/#home', { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
const info = await page.evaluate(() => {
  const bar = document.querySelector('.km-topbar');
  if (!bar) return { err: 'no topbar' };
  const br = bar.getBoundingClientRect();
  const kids = Array.from(bar.children).map((el) => {
    const r = el.getBoundingClientRect();
    return {
      cls: String(el.className).slice(0, 40),
      left: Math.round(r.left),
      right: Math.round(r.right),
      w: Math.round(r.width),
      clipped: r.right > br.right + 1 || r.left < br.left - 1,
    };
  });
  return { barW: Math.round(br.width), kids };
});
console.log(JSON.stringify(info, null, 2));
await page.screenshot({ path: 'C:/temp/topbar.png', clip: { x: 0, y: 0, width: 1440, height: 70 } });
await browser.close();
