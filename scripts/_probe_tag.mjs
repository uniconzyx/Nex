import { createRequire } from 'module';
const require = createRequire('C:/Users/zyx/.workbuddy/binaries/node/workspace/');
const { chromium } = require('playwright-core');

const browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--no-sandbox'] });
for (const theme of ['light', 'dark']) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.addInitScript((t) => localStorage.setItem('km.theme', t), theme);
  // 学习页才有 .km-node / .km-tl
  await page.goto('http://127.0.0.1:1420/#learn', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  const info = await page.evaluate(() => {
    const tag = document.querySelector('.km-node .km-tag-gray');
    const span = document.querySelector('.km-node-main > span');
    const chain = (el) => {
      const out = [];
      let n = el;
      while (n && n !== document.body) {
        out.unshift(`${n.tagName.toLowerCase()}.${String(n.className).replace(/\s+/g, '.')}`);
        n = n.parentElement;
      }
      return out;
    };
    return {
      tagColor: tag ? getComputedStyle(tag).color : null,
      tagBg: tag ? getComputedStyle(tag).backgroundColor : null,
      tagChain: tag ? chain(tag).slice(-4) : null,
      spanColor: span ? getComputedStyle(span).color : null,
      spanChain: span ? chain(span).slice(-3) : null,
      theme: document.querySelector('.km-app')?.getAttribute('data-km-theme'),
    };
  });
  console.log(theme, JSON.stringify(info, null, 1));
  await page.close();
}
await browser.close();
