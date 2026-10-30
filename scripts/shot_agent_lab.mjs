/**
 * shot_agent_lab.mjs —— S2 实验场景的真浏览器端到端（会真加载 Pyodide）
 * ============================================================================
 * 这是唯一能证明「实验报告里的 stdout 不是编的」的验收：
 *   页面 → 点「实验陪跑」→ 真 Pyodide 跑 numpy → 报告里出现真实输出 → 导出 .ipynb
 *
 * 为什么单独一个脚本：Pyodide 首次要下 ~10MB 解释器，30~90 秒；
 * 塞进 shot_agent.mjs 会让那个「2 秒级」的验收变成分钟级，失去快速回归的价值。
 *
 * 用法（先起 dev server 127.0.0.1:1420，且能联网）：
 *   node scripts/shot_agent_lab.mjs
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

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
};

const browser = await chromium.launch({
  executablePath: EDGE,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
});
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));

await page.goto(`${BASE}#agent`, { waitUntil: 'networkidle' });
await page.waitForTimeout(500);

// 选一个有专属实验模板的章
await page.locator('.ag-field select').nth(1).selectOption('ml-ch01');

console.log('点「实验陪跑」，等 Pyodide 加载（最多 150 秒）…');
await page.locator('.ag-scenario').nth(1).click();

const okReport = await page
  .locator('.ag-report .ag-headline')
  .waitFor({ timeout: 150_000 })
  .then(() => true)
  .catch(() => false);
check('实验报告生成', okReport);

if (okReport) {
  const trail = await page.locator('.ag-step .ag-tool').allInnerTexts();
  check('轨迹里有 run_python', trail.includes('run_python'), trail.join(','));

  const codeCount = await page.locator('.ag-report .ag-code').count();
  check('报告里有代码与真实输出两个块', codeCount >= 2, `${codeCount} 个`);

  const out = await page.locator('.ag-report .ag-code.ag-out').innerText().catch(() => '');
  check('真实输出非空', out.trim().length > 20, out.slice(0, 80).replace(/\n/g, ' / '));
  // 模板会打印学习率表头，这是「真跑过」的物证
  check('输出是本实验的内容（含 lr 表头或损失比）', /lr|损失|收敛/.test(out), out.slice(0, 60));

  const auditText = await page.locator('.ag-audit').innerText();
  check('数据自检非红', (await page.locator('.ag-audit.is-bad').count()) === 0, auditText.slice(0, 60));

  // 导出按钮：拦一次下载，确认文件真的生成
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 15_000 }).catch(() => null),
    page.locator('.ag-export').click(),
  ]);
  check('点了导出有文件下载', !!download, download ? download.suggestedFilename() : '无');
  if (download) {
    check('文件名是 .ipynb', download.suggestedFilename().endsWith('.ipynb'), download.suggestedFilename());
  }
}

await page.screenshot({ path: `${OUT}/4-lab-1440.png`, fullPage: true });

const realErrors = errors.filter((e) => !/ERR_CONNECTION_REFUSED|Failed to load resource/.test(e));
check('无 JS 运行时错误', realErrors.length === 0, realErrors.slice(0, 2).join(' | '));

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log('\n' + '─'.repeat(60));
console.log(failed.length ? `AGENT_LAB_FAIL ${results.length - failed.length}/${results.length}` : `AGENT_LAB_OK ${results.length}/${results.length}`);
if (failed.length) process.exit(1);
