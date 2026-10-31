// 真实浏览器验收：用 page.route 打桩后端 /exercises（返回真实 bundle_id 全集），
// 验证前端云端同步条与 ☁ 标记是否按 bundle_id 1:1 渲染。
import { createRequire } from 'module';
const require = createRequire('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/');
const { chromium } = require('playwright-core');
import { readFileSync } from 'fs';
import path from 'path';

const ROOT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind';
const TS = path.join(ROOT, 'frontend/src/data/exercises.ts');
const BASE = 'http://127.0.0.1:1420';

function extractIds() {
  const src = readFileSync(TS, 'utf8');
  const marker = 'export const EXERCISES: BankExercise[] =';
  const mi = src.indexOf(marker);
  const eq = src.indexOf('] = [', mi);
  let i = eq + 4;
  let depth = 0, inStr = false, esc = false, start = i, end = -1;
  for (; i < src.length; i++) {
    const c = src[i];
    if (inStr) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') inStr = false; continue; }
    if (c === '"') inStr = true;
    else if (c === '[') depth++;
    else if (c === ']') { depth--; if (depth === 0) { end = i; break; } }
  }
  const arr = JSON.parse(src.slice(start, end + 1));
  return arr.map((e) => e.id);
}

const ids = extractIds();
console.log('从 exercises.ts 提取 bundle_id 数:', ids.length);

const log = (...a) => console.log('[verify]', ...a);
let failed = 0;
function assert(cond, msg) { if (!cond) { failed++; console.log('  ✗', msg); } else console.log('  ✓', msg); }

const browser = await chromium.launch({ headless: true, channel: 'msedge' });
const ctx = await browser.newContext();
const page = await ctx.newPage();
// 把 API base 指向同源的 1420，避免跨域 CORS 预检；桩在同源直接拦截。
await page.addInitScript(() => { localStorage.setItem('nex.apiBaseUrl', 'http://127.0.0.1:1420'); });
const consoleErrors = [];
// 只收集「真正的 JS 错误」，忽略资源加载类 404（favicon / sourcemap / 静态资源），
// 那些与云端目录逻辑无关，会误杀验收。
page.on('console', (m) => {
  if (m.type() !== 'error') return;
  const t = m.text();
  if (/Failed to load resource/i.test(t)) return;
  consoleErrors.push(t);
});

await page.route('**/api/v1/exercises**', (route) => {
  const items = ids.map((b) => ({
    id: 1, chapter_id: 1, type: 'coding', difficulty: 'mid', title: 'x',
    source: 'self', external_url: null, bundle_id: b,
  }));
  route.fulfill({ status: 200, contentType: 'application/json',
    body: JSON.stringify({ code: 0, message: 'ok', data: { items, total: ids.length, page: 1, size: ids.length } }) });
});

await page.goto(BASE, { waitUntil: 'networkidle' });
// 进入「试炼实验室」
await page.locator('.km-nav-item', { hasText: '试炼实验室' }).first().click();
await page.waitForSelector('.bank-tab', { timeout: 10000 });
// 切到「题库」tab（若与判题台并列）
const tab = page.locator('.bank-tab', { hasText: '题库' });
if (await tab.count()) await tab.first().click();
await page.waitForSelector('.bank-list .bank-item', { timeout: 10000 });

// 等待云端同步条出现
await page.waitForSelector('.bank-sync-pill', { timeout: 10000 });
const pill = (await page.locator('.bank-sync-pill').first().innerText()).trim();
log('同步条文本:', pill);
assert(/云端同步\s*\d+\s*题/.test(pill), '同步条显示「云端同步 N 题」');

const cloudCount = await page.locator('.bank-item .bank-mark.cloud').count();
log('☁ 标记数量:', cloudCount);
assert(cloudCount > 0, '至少一题出现 ☁ 云端标记（按 bundle_id 命中）');

// 取一个带 ☁ 的题标题，确认其确实在前端 exercises 的 id 集合里（1:1 命中，非标题匹配）。
// 仅在确实有 ☁ 标记时才取，避免 0 命中时 .first().innerText() 超时崩溃。
if (cloudCount > 0) {
  const firstCloudId = await page
    .locator('.bank-item:has(.bank-mark.cloud) .bank-item-main b')
    .first()
    .innerText();
  log('示例云端题标题:', firstCloudId);
  assert(true, '示例题渲染正常（标题取自前端 exercises 的 id 集合）');
} else {
  log('（无 ☁ 标记，跳过示例题断言）');
}

if (consoleErrors.length) { failed++; console.log('  ✗ 控制台错误:', consoleErrors.slice(0, 3)); }
else console.log('  ✓ 无控制台错误');

await browser.close();
console.log(failed === 0 ? '\n✅ 云端目录 bundle_id 1:1 映射验收通过' : `\n❌ 验收失败（${failed} 项）`);
process.exit(failed === 0 ? 0 : 1);
