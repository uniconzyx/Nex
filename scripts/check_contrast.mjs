/**
 * check_contrast.mjs —— 深浅两套主题下关键文字的对比度自查
 * ============================================================================
 * 为什么不靠截图看：P2 新增了 12 组小字号文字（关卡提示、前置百分比、pip、
 * 掌握度 chip），它们全都继承 --km-* 令牌，深浅主题各一套。人眼在两种背景上
 * 都会"觉得还行"，但 11px 的 --km-warn 落在深色底上经常掉到 3:1 以下。
 *
 * 这里在真浏览器里取 computedStyle，逐层把半透明背景合成到最底层，
 * 再按 WCAG 公式算对比度。阈值 4.5（正文），加粗大字号放宽到 3.0。
 *
 * 用法（需先起 dev server 127.0.0.1:1420）：
 *   node scripts/check_contrast.mjs
 * ============================================================================
 */
import { createRequire } from 'module';
import { mkdirSync, readFileSync } from 'fs';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:1420/';
const ROOT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind';
const OUT = `${ROOT}/scratch/p2-shots`;
mkdirSync(OUT, { recursive: true });

const src = readFileSync(`${ROOT}/frontend/src/data/exercises.ts`, 'utf8');
const marker = 'export const EXERCISES: BankExercise[] = ';
const arr = JSON.parse(src.slice(src.indexOf('[', src.indexOf(marker) + marker.length), src.lastIndexOf(']') + 1));
const CH = 'data-ch02';
const LIST = arr.filter((e) => e.ch === CH);

const today = (() => {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
})();

/** 半通关：概念 + 演练过、BOSS 没过 → 三张卡同时有「已通过」和「未通过」两种状态 */
function makeState(theme) {
  const answers = {};
  const DRILL = new Set(['coding', 'output', 'fix_error', 'design']);
  const concept = LIST.find((e) => e.type === 'choice' || e.type === 'explain');
  const drills = LIST.filter((e) => DRILL.has(e.type)).slice(0, 3);
  for (const e of [concept, ...drills]) answers[e.id] = { chapterId: CH, ok: true, at: Date.now() };
  return {
    theme,
    outfit: 'default',
    doneProjects: [],
    doneChapters: [],
    checkins: [],
    coins: 1280,
    coinLedger: [],
    bestiary: {},
    chapterRuns: {},
    answers,
    daily: { date: today, qids: LIST.slice(0, 3).map((e) => e.id), done: [LIST[0].id], correct: [LIST[0].id], claimed: false },
    shards: 0,
  };
}

/** 在页面里算：元素文字色 vs 合成后的背景色 */
const MEASURE = `(selectors) => {
  const parse = (c) => {
    const m = c.match(/rgba?\\(([^)]+)\\)/);
    if (!m) return null;
    const p = m[1].split(/[,\\s/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });
  const lum = ({ r, g, b }) => {
    const f = (v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const bgOf = (el) => {
    const stack = [];
    let node = el;
    while (node) {
      const c = parse(getComputedStyle(node).backgroundColor);
      if (c && c.a > 0) stack.push(c);
      if (c && c.a >= 0.999) break;
      node = node.parentElement;
    }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = stack.length - 1; i >= 0; i--) base = over(stack[i], base);
    return base;
  };
  const out = [];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (!el) { out.push({ sel, missing: true }); continue; }
    const cs = getComputedStyle(el);
    const fg = parse(cs.color);
    const bg = bgOf(el);
    const f = over(fg, bg);
    const l1 = lum(f) + 0.05;
    const l2 = lum(bg) + 0.05;
    const ratio = l1 > l2 ? l1 / l2 : l2 / l1;
    out.push({
      sel,
      ratio: Math.round(ratio * 100) / 100,
      color: cs.color,
      fontSize: cs.fontSize,
      bold: Number(cs.fontWeight) >= 600,
      text: (el.textContent || '').trim().slice(0, 18),
    });
  }
  return out;
}`;

const TARGETS = [
  '.km-stage-hint',
  '.km-stage-desc',
  '.km-stage-weight',
  '.km-stage-blockers',
  '.km-pip:not(.on)',
  '.km-mastery-chip',
  '.km-node .km-tag-gray',
  '.km-dep-bad',
  '.km-node-main > span',
];

const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
}

const browser = await chromium.launch({
  executablePath: EDGE,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
});

for (const theme of ['light', 'dark']) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.addInitScript(
    (payload) => {
      if (sessionStorage.getItem('__km_c')) return;
      sessionStorage.setItem('__km_c', '1');
      for (const k of Object.keys(localStorage)) {
        if (k.startsWith('kaimao.') || k.startsWith('nex.')) localStorage.removeItem(k);
      }
      localStorage.setItem('kaimao.progress.v2', JSON.stringify(payload.state));
      localStorage.setItem('nex.subject', 'data');
    },
    { state: makeState(theme) },
  );
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-app', { timeout: 20000 });
  await page.waitForTimeout(600);

  await page.getByRole('button', { name: /知识试炼区/ }).first().click();
  await page.waitForSelector('.km-map', { timeout: 15000 });
  await page.locator('.km-node').filter({ hasText: 'NumPy 进阶' }).first().locator('.km-node-main').click();
  await page.waitForSelector('.km-stages', { timeout: 8000 });
  await page.waitForTimeout(400);

  const measured = await page.evaluate(`(${MEASURE})(${JSON.stringify(TARGETS)})`);
  const missing = measured.filter((m) => m.missing).map((m) => m.sel);
  check(`${theme} · 取样元素都在`, missing.length === 0, missing.join(', '));

  const rows = measured.filter((m) => !m.missing);
  const worst = rows.reduce((a, b) => (a.ratio <= b.ratio ? a : b));
  const low = rows.filter((m) => m.ratio < 4.5);
  console.log(
    `  ${theme} 对比度：` + rows.map((m) => `${m.sel.replace('.km-', '')}=${m.ratio}`).join('  '),
  );
  check(
    `${theme} · 最差对比度 ≥ 4.5`,
    worst.ratio >= 4.5,
    `${worst.sel} ${worst.ratio}:1「${worst.text}」`,
  );
  if (low.length) {
    console.log(`  低于 4.5 的元素：` + low.map((m) => `${m.sel}(${m.ratio})`).join(', '));
  }

  await page.screenshot({ path: `${OUT}/07-${theme}-learn.png`, fullPage: false });

  // 项目详情页也取一次（前置百分比是本轮新增的小字）
  await page.getByRole('button', { name: /BOSS项目实战/ }).first().click();
  await page.waitForSelector('.cp-grid', { timeout: 15000 });
  await page.locator('.cp-card').first().click();
  await page.waitForSelector('.cp-requires', { timeout: 8000 });
  await page.waitForTimeout(300);
  const proj = await page.evaluate(`(${MEASURE})(${JSON.stringify(['.cp-requires button', '.cp-mastery', '.cp-hint'])})`);
  console.log(`  ${theme} 项目页：` + proj.map((m) => `${m.sel}=${m.ratio}`).join('  '));
  const projWorst = proj.reduce((a, b) => (a.ratio <= b.ratio ? a : b));
  check(`${theme} · 项目前置文字对比度 ≥ 4.5`, projWorst.ratio >= 4.5, `${projWorst.sel} ${projWorst.ratio}:1`);
  await page.screenshot({ path: `${OUT}/08-${theme}-project.png` });

  check(`${theme} · 无 JS 错误`, errors.length === 0, errors.slice(0, 1).join(''));
  await ctx.close();
}

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} 项通过`);
if (failed.length) {
  for (const f of failed) console.log(`  - ${f.name} ${f.detail}`);
  process.exit(1);
}
console.log('CONTRAST_OK');
