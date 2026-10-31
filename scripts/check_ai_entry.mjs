/**
 * check_ai_entry.mjs —— AI 入口可见性验收（真浏览器）
 *
 * 验的是「用户第一眼能不能认出这是问 AI 的地方」：
 *   A. 桌面 1440 x 900：入口可见、文案完整、不压住右栏凯喵卡片与底部卡片
 *   B. 平板 1024：入口可见、不压内容
 *   C. 手机 390：入口可见、说明文字收起、不压底栏
 *   D. 点击 → 面板打开，标题与副标题按模式变化
 *   E. 切模式 → 副标题跟着换（六种模式的边界不同，不能共用一句）
 *
 * 用法：需先起 dev server 127.0.0.1:1420，然后 node scripts/check_ai_entry.mjs
 */
import { createRequire } from 'module';
import { mkdirSync } from 'fs';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:1420/';
const OUT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind/scratch/ai-entry';

const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? '  PASS' : '  FAIL'}  ${name}${detail ? ' · ' + detail : ''}`);
}

async function rect(page, sel) {
  return page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || Number(st.opacity) === 0) return null;
    return { x: r.x, y: r.y, w: r.width, h: r.height, bottom: r.bottom, right: r.right };
  }, sel);
}

function overlap(a, b) {
  if (!a || !b) return 0;
  const w = Math.min(a.right, b.right) - Math.max(a.x, b.x);
  const h = Math.min(a.bottom, b.bottom) - Math.max(a.y, b.y);
  return Math.max(0, w) * Math.max(0, h);
}

const browser = await chromium.launch({ executablePath: EDGE, headless: true });
mkdirSync(OUT, { recursive: true });

const viewports = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'tablet-1024', width: 1024, height: 800 },
  { name: 'phone-390', width: 390, height: 844 },
];

for (const vp of viewports) {
  const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(700);

  const fab = await rect(page, '.ai-fab');
  check(`${vp.name} · 入口可见`, Boolean(fab), fab ? `${Math.round(fab.w)}x${Math.round(fab.h)} @ ${Math.round(fab.x)},${Math.round(fab.y)}` : '不存在或不可见');

  if (fab) {
    const inside = fab.x >= 0 && fab.y >= 0 && fab.right <= vp.width + 0.5 && fab.bottom <= vp.height + 0.5;
    check(`${vp.name} · 完全在视口内`, inside);

    const label = (await page.locator('.ai-fab-text b').innerText()).trim();
    check(`${vp.name} · 主标签可见`, label === '问凯喵', `"${label}"`);

    const hintVisible = await page
      .locator('.ai-fab-text em')
      .evaluate((el) => getComputedStyle(el).display !== 'none')
      .catch(() => false);
    if (vp.width > 900) {
      check(`${vp.name} · 副说明可见`, hintVisible);
    } else {
      check(`${vp.name} · 窄屏收起副说明`, !hintVisible);
    }

    // 与右栏凯喵卡片重叠面积 = 0（桌面就是被这条坑过，才把圆球藏起来）
    const catCard = await rect(page, '.km-cat-card');
    const ov = overlap(fab, catCard);
    check(`${vp.name} · 不压凯喵卡片`, ov === 0, `重叠 ${Math.round(ov)}px²`);

    // 不压侧导航最后一项
    const navLast = await rect(page, '.km-nav-item:last-child');
    check(`${vp.name} · 不压导航项`, overlap(fab, navLast) === 0);
  }

  await page.screenshot({ path: `${OUT}/${vp.name}.png`, fullPage: false });
  await page.close();
}

/* ---- D. 打开面板：标题与副标题 ---- */
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  await page.locator('.ai-fab').click();
  await page.waitForTimeout(500);

  const panel = await rect(page, '.ai-panel');
  check('点击后打开面板', Boolean(panel));

  const title = (await page.locator('.ai-panel-title').innerText()).trim();
  check('面板标题说明身份', title === '凯喵 · 学习助手', `"${title}"`);

  const sub0 = (await page.locator('.ai-panel-sub').innerText()).trim();
  console.log(`        socratic 副标题: ${sub0}`);
  check('首屏副标题说明答什么', sub0.includes('锚定课程内容'));

  // E. 切到「编译诊断」，副标题必须换一句（不能是同一句通用话术）
  await page.locator('.ai-mode-chip', { hasText: '编译诊断' }).click();
  await page.waitForTimeout(300);
  const sub1 = (await page.locator('.ai-panel-sub').innerText()).trim();
  console.log(`        diagnose 副标题: ${sub1}`);
  check('切模式副标题随之变化', sub1 !== sub0 && sub1.includes('报错原文'));

  const ph = await page.locator('.ai-input-row input').getAttribute('placeholder');
  check('输入框占位带当前模式', Boolean(ph && ph.includes('编译诊断')), `"${ph}"`);

  await page.screenshot({ path: `${OUT}/panel-open.png` });
  await page.close();
}

await browser.close();

const fail = results.filter((r) => !r.ok);
console.log('\n' + '-'.repeat(56));
console.log(`AI 入口验收：${results.length - fail.length}/${results.length} 通过`);
if (fail.length) {
  console.log('失败项：');
  for (const f of fail) console.log(`  · ${f.name} ${f.detail}`);
  process.exitCode = 1;
}
