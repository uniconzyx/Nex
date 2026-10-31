/**
 * shot_fontscale.mjs —— 字号上调后的布局回归（真 Edge）
 *
 * 为什么需要：kaimao.css + styles.css 里 293 处 font-size 统一 ×1.12。
 * 这类改动 tsc 和 vite build 都不会报错，但会在真机上把紧凑卡片挤溢出、
 * 把三栏布局顶出横向滚动条。所以这里同时在 1440 与 390 两个宽度上看四页，
 * 断言：documentElement 不出现横向滚动（scrollWidth <= innerWidth + 1）。
 *
 * 用法（需先起 dev server 127.0.0.1:1420）：
 *   node scripts/shot_fontscale.mjs
 */
import { createRequire } from 'module';
import { mkdirSync } from 'fs';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const BASE = 'http://127.0.0.1:1420/';
const OUT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind/scratch/fontscale';
mkdirSync(OUT, { recursive: true });

const PAGES = ['home', 'learn', 'employment', 'agent'];
const VIEWPORTS = [
  { name: 'desk', width: 1440, height: 900 },
  { name: 'mob', width: 390, height: 844 },
];

const browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--no-sandbox'] });
let fail = 0;

for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: 1 });
  for (const p of PAGES) {
    const page = await ctx.newPage();
    const errs = [];
    page.on('pageerror', (e) => errs.push(e.message));
    await page.goto(`${BASE}#${p}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    const m = await page.evaluate(() => {
      const de = document.documentElement;
      // 找出真正撑破容器的元素（只报最外层，避免整棵树刷屏）
      const over = [];
      for (const el of document.querySelectorAll('.km-main *, .km-page *')) {
        const r = el.getBoundingClientRect();
        if (r.width === 0) continue;
        if (r.right > de.clientWidth + 2) {
          over.push(`${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]} right=${Math.round(r.right)}`);
        }
      }
      const cs = getComputedStyle(document.body);
      return {
        scrollW: de.scrollWidth,
        innerW: window.innerWidth,
        bodyFont: cs.fontSize,
        overflow: over.slice(0, 6),
        overflowCount: over.length,
      };
    });
    const bad = m.scrollW > m.innerW + 1;
    if (bad) fail += 1;
    console.log(
      `${bad ? 'FAIL' : ' ok '} ${vp.name}/${p}  scrollW=${m.scrollW} innerW=${m.innerW} body=${m.bodyFont} overflowEls=${m.overflowCount}${errs.length ? ' pageerr=' + errs[0] : ''}`,
    );
    if (m.overflow.length) console.log('      ↳ ' + m.overflow.join(' | '));
    await page.screenshot({ path: `${OUT}/${vp.name}-${p}.png`, fullPage: false });
    await page.close();
  }
  await ctx.close();
}

await browser.close();
console.log(fail === 0 ? 'RESULT: 8/8 无横向溢出' : `RESULT: ${fail} 页横向溢出`);
process.exit(fail === 0 ? 0 : 1);
