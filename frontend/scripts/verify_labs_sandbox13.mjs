/**
 * verify_labs_sandbox13.mjs —— 13 章 sandbox 专项真机验收
 * ============================================================
 * 不只要「能渲染、指标会变」，而是要确认：把参数拖到「通关解」后，
 * 所有判据真的从红变绿、出现「✓ 通关」—— 这才是 sandbox 玩法的交付标准。
 *
 * 通关解来自 scripts/solve_sandbox.py 预先从 labs.json 穷举出的
 * sandbox_solutions.json（每章一组让全部 checks 为真的参数）。
 *
 * 用法：node frontend/scripts/verify_labs_sandbox13.mjs http://localhost:5230
 */
import { readFileSync } from 'node:fs';

const BASE = process.argv[2] || 'http://localhost:5230';
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const SOL = JSON.parse(readFileSync('frontend/scripts/sandbox_solutions.json', 'utf8'));

async function loadPlaywright() {
  try { return await import('playwright-core'); } catch {
    return import('file:///C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core/index.mjs');
  }
}
const { chromium } = await loadPlaywright();

const browser = await chromium.launch({ executablePath: EDGE, args: ['--headless=new', '--disable-gpu'] });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 900 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => { try { localStorage.setItem('nex.localMode', '1'); } catch {} });
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/i.test(m.text())) errs.push(m.text()); });

async function openChapter(key) {
  const [subject, chapter] = key.split('/');
  await page.locator(`[data-lab-subject="${subject}"]`).click();
  await page.waitForTimeout(120);
  await page.locator(`[data-lab-pick="${key}"]`).click();
  await page.waitForFunction(
    (ch) => document.querySelector('[data-lab-stage]')?.getAttribute('data-lab-stage') === ch,
    chapter, { timeout: 15000 },
  );
  await page.waitForSelector('[data-lab-title]', { timeout: 15000 });
}

const results = [];
const fails = [];

// 只在有解、且是我们要验的 13 章里跑
const keys = Object.keys(SOL).filter((k) => SOL[k] && SOL[k].ok);

await page.goto(`${BASE}/#lab`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('.bank-tabs', { timeout: 20000 });
await page.locator('.bank-tab', { hasText: '实验台' }).first().click();
await page.waitForSelector('[data-lab-subject]', { timeout: 20000 });

for (const key of keys) {
  const sol = SOL[key];
  try {
    await openChapter(key);
    const tab = page.locator('[data-lab-tab="sandbox"]').first();
    if ((await tab.count()) === 0) { fails.push(`${key} 无 sandbox 页签`); continue; }
    await tab.click();
    await page.waitForTimeout(420);

    // 先把每个参数设到通关解
    for (const p of sol.params) {
      if (p.type === 'opt') {
        // 必须按「参数行」作用域点选：data-param-opt 只带索引 i、不带 param key，
        // 多 opt 参数的章里每个行都有 opt-0 按钮，用 .first() 会永远点中第一行。
        await page.locator(`[data-param-row="${p.key}"] [data-param-opt="${p.value}"]`).first().click();
      } else {
        await page.evaluate((pk) => {
          const el = document.querySelector(`[data-param="${pk}"]`);
          if (!el) return;
          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          setter.call(el, el.max); // 先顶到最大，确保可控
          el.dispatchEvent(new Event('input', { bubbles: true }));
        }, p.key);
        // 再精确设到解值
        await page.evaluate(({ pk, val }) => {
          const el = document.querySelector(`[data-param="${pk}"]`);
          if (!el) return;
          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          setter.call(el, String(val));
          el.dispatchEvent(new Event('input', { bubbles: true }));
        }, { pk: p.key, val: p.value });
      }
      await page.waitForTimeout(120);
    }
    await page.waitForTimeout(450);

    // 判据是否全绿 + 出现「通关」
    const state = await page.evaluate(() => {
      const score = document.querySelector('[data-sandbox-score]')?.textContent || '';
      const passed = !!document.querySelector('[data-sandbox-score]') &&
        /(\d+) \/ \1 达标|全部达标|通关/.test(score + (document.body.innerText.includes('✓ 通关') ? ' 通关' : ''));
      const allGreen = [...document.querySelectorAll('[data-sandbox-checks] > *')]
        .every((el) => el.textContent.trim().startsWith('✓'));
      const greenCnt = [...document.querySelectorAll('[data-sandbox-checks] > *')]
        .filter((el) => el.textContent.trim().startsWith('✓')).length;
      const total = document.querySelectorAll('[data-sandbox-checks] > *').length;
      const won = document.body.innerText.includes('✓ 通关');
      return { score, allGreen, greenCnt, total, won };
    });

    const ok = state.won && state.allGreen && state.total > 0;
    results.push({ key, ...state, ok });
    if (!ok) fails.push(`${key} 未通关：score="${state.score}" green=${state.greenCnt}/${state.total} won=${state.won}`);
    await page.screenshot({ path: `frontend/.shots/sb-${key.replace('/', '-')}.png` });
  } catch (e) {
    fails.push(`${key} 交互异常：${String(e).slice(0, 160)}`);
  }
}

await browser.close();
if (errs.length) fails.push(`控制台报错 ${errs.length} 条：${errs.slice(0, 2).join(' | ')}`);
console.log(JSON.stringify({ pass: fails.length === 0, total: keys.length, results, fails }, null, 1));
process.exit(fails.length === 0 ? 0 : 1);
