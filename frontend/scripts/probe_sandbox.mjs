/**
 * probe_sandbox.mjs —— 直接 dump 运行时 DOM，确证 ai/ai-ch01 到底渲染了哪些玩法页签。
 * 不依赖 verify_labs_deep.mjs 的挑选逻辑，纯粹观测浏览器里实际出现的 [data-lab-tab]。
 */
async function loadPlaywright() {
  try {
    return await import('playwright-core');
  } catch {
    return import('file:///C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core/index.mjs');
  }
}
const { chromium } = await loadPlaywright();

const BASE = process.argv[2] || 'http://localhost:5230';
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

const browser = await chromium.launch({ executablePath: EDGE, args: ['--headless=new', '--disable-gpu'] });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 900 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => { try { localStorage.setItem('nex.localMode', '1'); } catch {} });
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/i.test(m.text())) errs.push(m.text()); });

const KEY = process.argv[3] || 'ai/ai-ch01';
const [subject, chapter] = KEY.split('/');

await page.goto(`${BASE}/#lab`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('.bank-tabs', { timeout: 20000 });
await page.locator('.bank-tab', { hasText: '实验台' }).first().click();
await page.waitForSelector('[data-lab-subject]', { timeout: 20000 });
await page.locator(`[data-lab-subject="${subject}"]`).click();
await page.waitForTimeout(200);
await page.locator(`[data-lab-pick="${KEY}"]`).click();
await page.waitForFunction(
  (ch) => document.querySelector('[data-lab-stage]')?.getAttribute('data-lab-stage') === ch,
  chapter,
  { timeout: 15000 },
);
await page.waitForTimeout(600);

const tabs = await page.locator('[data-lab-tab]').evaluateAll((els) => els.map((e) => e.getAttribute('data-lab-tab')));
const stage = await page.locator('[data-lab-stage]').getAttribute('data-lab-stage');
const meta = await page.locator('.km-lab-meta').first().innerText().catch(() => '(none)');
const hasSandboxParam = await page.locator('[data-sandbox-params]').count();
const hasSandboxChecks = await page.locator('[data-sandbox-checks]').count();

console.log(JSON.stringify({ KEY, stage, tabs, meta, hasSandboxParam, hasSandboxChecks, errs }, null, 1));

const servedSrc = await page.evaluate(async () => {
  try { const r = await fetch('/src/data/labs/ai.ts'); return await r.text(); } catch (e) { return 'FETCH_ERR ' + e; }
});
const servedSb = (servedSrc.match(/"kind":"sandbox"/g) || []).length;
const servedAiCh01HasSb = /ai-ch01[\s\S]*?"kind":"sandbox"/.test(servedSrc);
console.log('SERVED:', JSON.stringify({ servedSb, servedAiCh01HasSb, servedLen: servedSrc.length }));

await browser.close();
process.exit(0);
