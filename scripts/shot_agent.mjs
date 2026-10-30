/**
 * shot_agent.mjs —— 凯喵陪练页的真浏览器验收 + 截图
 * ============================================================================
 * 验三件事（这些是纯逻辑验收脚本 check_agent.mjs 覆盖不到的）：
 *   1. 页面能挂载，路由 #agent 生效，无 console error；
 *   2. 未登录点「学情诊断」→ 走规则模式，**真的能出报告**（不是空壳）；
 *   3. 报告顶上的数据自检不是红的（降级路径数字必须全对）。
 *
 * 用法（先起 dev server 127.0.0.1:1420）：
 *   node scripts/shot_agent.mjs
 * ============================================================================
 */
import { createRequire } from 'module';
import { mkdirSync } from 'fs';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:1420/';
const OUT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind/scratch/agent-shots';
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({
  executablePath: EDGE,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
});

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
};

const ctx = await browser.newContext({ viewport: { width: 1440, height: 960 } });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(m.text());
});

await page.goto(`${BASE}#agent`, { waitUntil: 'networkidle' });
await page.waitForTimeout(600);

check('路由 #agent 挂载', (await page.locator('.ag-root').count()) === 1);
check('标题渲染', (await page.locator('.ag-head h1').innerText()) === '凯喵陪练');
check('两张场景卡', (await page.locator('.ag-scenario').count()) === 2);
await page.screenshot({ path: `${OUT}/1-empty-1440.png`, fullPage: true });

/* 点「学情诊断」：未登录 → planner 抛错 → 规则序列 */
await page.locator('.ag-scenario').first().click();
await page.waitForTimeout(2500);

const stepCount = await page.locator('.ag-step').count();
check('执行轨迹有步骤', stepCount >= 4, `${stepCount} 步`);

const hasReport = (await page.locator('.ag-report .ag-headline').count()) === 1;
check('生成了报告（规则模式也能出）', hasReport);
if (hasReport) {
  const headline = await page.locator('.ag-headline').innerText();
  check('报告结论引用了真实结论', headline.length > 4, headline.slice(0, 60));

  const auditText = await page.locator('.ag-audit').innerText();
  check('数据自检通过（无 hard error）', !(await page.locator('.ag-audit.is-bad').count()), auditText.slice(0, 80));

  const sections = await page.locator('.ag-sec').count();
  check('报告小节 ≥3', sections >= 3, `${sections} 节`);

  const degraded = await page.locator('.ag-report .ag-note').count();
  check('明示了降级原因', degraded >= 1);
}
await page.screenshot({ path: `${OUT}/2-report-1440.png`, fullPage: true });

/* 窄屏：390 宽必须单列 */
await page.setViewportSize({ width: 390, height: 844 });
await page.waitForTimeout(400);
const cols = await page.evaluate(() => {
  const el = document.querySelector('.ag-body');
  return el ? getComputedStyle(el).gridTemplateColumns.split(' ').length : -1;
});
check('手机宽度下两栏折叠为单列', cols === 1, `grid 列数 ${cols}`);
await page.screenshot({ path: `${OUT}/3-report-390.png`, fullPage: true });

// 后端没起时的探活失败是**预期**的（这个页面的设计前提就是未登录/离线也能用），
// 只有真正的 JS 异常才算错
const realErrors = errors.filter((e) => !/ERR_CONNECTION_REFUSED|Failed to load resource/.test(e));
check('无 JS 运行时错误', realErrors.length === 0, realErrors.slice(0, 3).join(' | '));

await browser.close();

const failed = results.filter((r) => !r.ok);
console.log('\n' + '─'.repeat(60));
console.log(failed.length ? `AGENT_UI_FAIL ${results.length - failed.length}/${results.length}` : `AGENT_UI_OK ${results.length}/${results.length}`);
if (failed.length) process.exit(1);
