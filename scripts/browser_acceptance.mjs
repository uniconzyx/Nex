/**
 * scripts/browser_acceptance.mjs
 * ---------------------------------------------------------------------------
 * 真实浏览器验收：React 前端 ↔ FastAPI 后端 的实际交互链路。
 *
 * 为什么不用 curl 代替：
 *   curl 只能证明「接口通」，证明不了「页面真的能拿到数据并渲染出来」。
 *   这一版打通的核心恰恰是**前端在浏览器里能不能把后端数据画出来**，
 *   所以必须真跑一次 DOM。
 *
 * 覆盖场景：
 *   1. 首屏加载，顶栏出现连接指示灯（绿=已连接）；
 *   2. 设置页：内容服务状态卡显示「已连接」+ 后端版本 + 题库规模；
 *   3. 考研手札 → 考研题库 Tab：目录加载出 6 场考试；
 *   4. 分类总结：建议刷题顺序列表渲染出题目条目；
 *   5. 断网模拟：把后端地址改成坏端口 → 指示灯变红 + 页面给出可操作提示。
 *
 * 用法：
 *   node scripts/browser_acceptance.mjs
 *   node scripts/browser_acceptance.mjs --base http://127.0.0.1:1420
 *
 * 前置：vite dev server 在 1420，FastAPI 在 8000。
 */
// ESM 不认 NODE_PATH，必须用绝对路径导入 playwright-core。
// 它装在 managed workspace 里（本机 npm 被安全策略路由到 wsl.exe，装不进项目）。
const PLAYWRIGHT = 'file:///C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core/index.mjs';
const { chromium } = await import(PLAYWRIGHT);

const BASE = process.argv.includes('--base')
  ? process.argv[process.argv.indexOf('--base') + 1]
  : 'http://127.0.0.1:1420';

import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

/** 定位 Chromium 可执行文件。agent-browser 的安装目录结构随版本变过，
 *  这里做一层探测而不是写死路径。 */
function findChrome() {
  if (process.env.AGENT_BROWSER_CHROME && existsSync(process.env.AGENT_BROWSER_CHROME)) {
    return process.env.AGENT_BROWSER_CHROME;
  }
  const root = 'C:/Users/zyx/.agent-browser/browsers';
  if (!existsSync(root)) return undefined;
  const dirs = readdirSync(root)
    .filter((d) => d.startsWith('chrome-'))
    .sort()
    .reverse();
  for (const d of dirs) {
    for (const rel of [
      'chrome-win64/chrome.exe',
      'chrome-win/chrome.exe',
      'chrome.exe',
      'chrome-win32/chrome.exe',
    ]) {
      const p = join(root, d, rel);
      if (existsSync(p)) return p;
    }
  }
  return undefined;
}

const CHROME = findChrome();
if (!CHROME) {
  console.error('✗ 找不到 Chromium。先执行：agent-browser install');
  process.exit(2);
}
console.log(`浏览器：${CHROME}`);

const results = [];
function rec(ok, name, detail = '') {
  results.push({ ok, name, detail });
  console.log(`  ${ok ? '✓' : '✗'} ${name}${detail ? ' — ' + detail : ''}`);
}

const browser = await chromium.launch({
  executablePath: CHROME,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

const consoleErrors = [];
page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text());
});
page.on('pageerror', (e) => consoleErrors.push(String(e)));

try {
  // ── 1. 首屏 + 连接指示灯 ──────────────────────────────────────────
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-app', { timeout: 15000 });

  // 等连接指示灯出现（App 启动后异步探测）
  const badge = await page
    .waitForSelector('.km-conn-badge', { timeout: 15000 })
    .catch(() => null);
  rec(!!badge, '顶栏出现连接指示灯');

  if (badge) {
    await page
      .waitForFunction(
        () => {
          const el = document.querySelector('.km-conn-badge');
          return el && (el.classList.contains('online') || el.classList.contains('offline'));
        },
        { timeout: 15000 },
      )
      .catch(() => {});
    const cls = await page.getAttribute('.km-conn-badge', 'class');
    rec(cls.includes('online'), '指示灯为「已连接」状态', cls);
  }

  // ── 2. 设置页健康卡片 ─────────────────────────────────────────────
  await page.click('[aria-label="设置"]');
  await page.waitForTimeout(2000);

  const bodyText = await page.textContent('body');
  rec(bodyText.includes('内容服务'), '设置页有「内容服务」卡片');
  rec(bodyText.includes('判题服务'), '设置页有「判题服务」卡片（与内容服务分开）');
  rec(/已连接/.test(bodyText), '健康卡片显示「已连接」');
  rec(/Nex API v/.test(bodyText), '健康卡片显示后端名称与版本');
  rec(/\d+ 题/.test(bodyText), '健康卡片显示题库规模');

  // ── 3. 考研手札 → 考研题库 Tab ────────────────────────────────────
  await page.click('text=考研手札').catch(() => {});
  await page.waitForTimeout(800);
  const bankTab = page.locator('text=考研题库').first();
  if (await bankTab.count()) {
    await bankTab.click();
    await page.waitForTimeout(2500);
    const bankText = await page.textContent('body');
    rec(/408/.test(bankText), '题库 Tab 加载出 408 考试');
    rec(/数据结构|计算机组成原理|操作系统|计算机网络/.test(bankText), '题库 Tab 渲染出科目列表');
  } else {
    rec(false, '找到「考研题库」Tab');
  }

  // ── 4. 分类总结 + 建议刷题顺序 ─────────────────────────────────────
  // 进入「分类总结」视图（若存在），检查建议顺序区块
  const summaryTab = page.locator('text=分类总结').first();
  if (await summaryTab.count()) {
    await summaryTab.click();
    await page.waitForTimeout(2500);
    const st = await page.textContent('body');
    rec(st.includes('建议') || st.includes('顺序'), '分类总结出现「建议刷题顺序」区块');
    const bubbles = await page.locator('.ex-order-item, .ex-order li').count();
    rec(bubbles > 0, '建议顺序渲染出题目条目', `${bubbles} 项`);
  } else {
    rec(false, '找到「分类总结」视图');
  }

  // ── 5. 断网 → 指示灯变红 ─────────────────────────────────────────
  await page.evaluate(() => localStorage.setItem('nex.apiBaseUrl', 'http://127.0.0.1:59999'));
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-conn-badge', { timeout: 15000 });
  await page
    .waitForFunction(
      () => document.querySelector('.km-conn-badge')?.classList.contains('offline'),
      { timeout: 20000 },
    )
    .catch(() => {});
  const offCls = await page.getAttribute('.km-conn-badge', 'class');
  rec(offCls.includes('offline'), '后端不可达时指示灯变红', offCls);

  await page.click('[aria-label="设置"]').catch(() => {});
  await page.waitForTimeout(1500);
  const offText = await page.textContent('body');
  rec(/未连接|无法连接/.test(offText), '设置页显示「未连接」并给出指引');
} catch (e) {
  rec(false, '验收流程异常', String(e).slice(0, 200));
} finally {
  await browser.close();
}

const nPass = results.filter((r) => r.ok).length;
const nFail = results.filter((r) => !r.ok).length;
console.log(`\n=== 浏览器验收：${nPass} PASS / ${nFail} FAIL ===`);
if (consoleErrors.length) {
  console.log('\n控制台错误（前 5 条）：');
  for (const e of consoleErrors.slice(0, 5)) console.log('  ! ' + e.slice(0, 200));
}
process.exit(nFail ? 1 : 0);
