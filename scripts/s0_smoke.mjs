/**
 * s0_smoke.mjs —— S0 统一交互骨架 运行时冒烟测试
 * 用 Edge + playwright-core 跑真浏览器，验证：
 *   1) 首页能渲染、无代码级 console error / pageerror（捕获 Provider 等运行期崩溃）
 *   2) 右下凯喵 FAB（移动宽屏可见）冰蓝辉光已生效（box-shadow 非空）
 *   3) 切到 #bestiary 不崩溃（LongPressPreview / useParticles 不报错）
 *   4) 窄屏（≤900）点「全部」能拉起统一 BottomSheet
 * 截图存到 scratch/s0-shots。
 */
import { createRequire } from 'module';
import { mkdirSync } from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:1420/';
const OUT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind/scratch/s0-shots';
mkdirSync(OUT, { recursive: true });

const errors = [];
const log = (...a) => console.log(...a);

// 离线跑浏览器时，前端会去连后端（content service / judge），这些是网络错误，
// 不是代码错误，冒烟测试应忽略；只保留真正的 JS / 渲染错误。
const isNetworkNoise = (t) =>
  /Failed to load resource/i.test(t) || /ERR_CONNECTION_REFUSED/i.test(t) || /net::ERR/i.test(t);

const b = await chromium.launch({
  executablePath: EDGE,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
});
const page = await b.newPage({ viewport: { width: 820, height: 900 } });
page.on('console', (m) => { if (m.type() === 'error' && !isNetworkNoise(m.text())) errors.push('console: ' + m.text()); });
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));

// 1) 首页渲染（820 宽：FAB 可见、且 >900? 否 → 仍是窄栏，但 FAB 在 <1181 显示）
await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForSelector('.km-app', { timeout: 15000 });
await page.waitForSelector('.ai-fab', { state: 'attached', timeout: 15000 });
const fab = await page.$eval('.ai-fab', (el) => {
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  return { display: cs.display, shadow: cs.boxShadow };
});
log('FAB info:', JSON.stringify(fab));
if (fab.display === 'none') errors.push('FAB is display:none even on mobile width (unexpected)');
if (!/rgb/.test(fab.shadow)) errors.push('FAB glow missing (box-shadow empty)');
await page.screenshot({ path: `${OUT}/01-home.png` });
log('home rendered');

// 2) bestiary（验证 LongPressPreview / useParticles 不崩）
await page.goto(BASE + '#bestiary', { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForSelector('.km-view', { timeout: 15000 });
await page.screenshot({ path: `${OUT}/02-bestiary.png` });
log('bestiary rendered');

// 3) 窄屏拉起 BottomSheet
await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForSelector('.km-nav-all', { state: 'attached', timeout: 15000 });
await page.click('.km-nav-all');
await page.waitForSelector('.km-sheet', { timeout: 8000 });
const sheetTitle = await page.$eval('.km-sheet-head b', (el) => el.textContent).catch(() => '(no title)');
await page.screenshot({ path: `${OUT}/03-nav-sheet.png` });
log('BottomSheet opened, title =', sheetTitle);
if (sheetTitle !== '全部导航') errors.push('BottomSheet title unexpected: ' + sheetTitle);

await b.close();

if (errors.length) {
  console.log('\n=== ERRORS ===');
  errors.forEach((e) => console.log(' -', e));
  console.log('S0_SMOKE_FAIL');
  process.exit(1);
} else {
  console.log('\nS0_SMOKE_OK');
}
