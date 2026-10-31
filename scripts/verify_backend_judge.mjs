// 真浏览器验收：前端 backend 降级判题通道（云端判题）
// 策略：用 Playwright page.route() 在网络层打桩后端（含 CORS 预检），
// 在真实 Edge(Chromium) 里走完整前端链路，验证“降级模式”在浏览器 UI 真的打通。
// 不依赖 Docker/Postgres/Redis（后端判题逻辑本身已由 test_backend_free_cases.py ALL PASS 覆盖）。
import { createRequire } from 'module';
const require = createRequire('C:/Users/zyx/.workbuddy/binaries/node/workspace/');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:1420';
const C = {
  'access-control-allow-origin': '*',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': '*',
  'access-control-allow-credentials': 'true',
};
const JSONH = { ...C, 'content-type': 'application/json' };
const USER = {
  uuid: 'u1', email: 'tester@nex.dev',
  profile: { nickname: 'tester', avatar_url: '', direction: null, daily_minutes: 0, plan: 'free', theme: 'light', reduced_motion: false, font_scale: 1 },
};

// 捕获前端实际发出的提交负载 + 轮询次数
const captured = { submission: null, polls: 0 };

async function handle(route, request) {
  const url = request.url();
  const method = request.method();
  if (method === 'OPTIONS') return route.fulfill({ status: 204, headers: C });
  if (!url.includes('/api/v1/')) return route.continue();

  const path = new URL(url).pathname;
  const ok = (data) => route.fulfill({ status: 200, headers: JSONH, body: JSON.stringify({ code: 0, message: 'ok', data, traceId: 'x' }) });

  if (method === 'POST' && path === '/api/v1/judge/submissions') {
    captured.submission = JSON.parse(request.postData() || '{}');
    return ok({ submission_id: 101, status: 'queued' });
  }
  const m = path.match(/\/api\/v1\/judge\/submissions\/(\d+)$/);
  if (m && method === 'GET') {
    captured.polls += 1;
    const terminal = captured.polls >= 2; // 第一次轮询返回 running，第二次返回终态，验证轮询循环真的跑
    if (!terminal) {
      return ok({ id: Number(m[1]), status: 'running', passed: null, total: null, time_ms: null, memory_kb: null, diagnosis_md: null, lang: 'cpp17', case_results: null });
    }
    return ok({
      id: Number(m[1]), status: 'wrong_answer', passed: 1, total: 2, time_ms: 4, memory_kb: 2048,
      diagnosis_md: null, lang: 'cpp17', stdout: null, stderr: null,
      case_results: [
        { status: 'ac', stdout: '5', time_ms: 2, memory_kb: 1024 },
        { status: 'wa', stdout: '999', time_ms: 2, memory_kb: 1024 },
      ],
    });
  }
  if (path === '/api/v1/system/health') return ok({ backend: { name: 'mock', version: '0', elapsed_ms: 1 }, database: { ok: true, checked: true }, features: {} });
  if (path === '/api/v1/users/me') return ok(USER);
  return ok({});
}

const log = (...a) => console.log('[verify]', ...a);
const fails = [];
function check(name, cond, extra = '') {
  if (cond) log('PASS:', name, extra);
  else { fails.push(name); log('FAIL:', name, extra); }
}

const browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--no-sandbox'] });
const page = await browser.newPage();
await page.addInitScript(() => {
  localStorage.setItem('nex.accessToken', 'fake-jwt-token');
  localStorage.setItem('nex.refreshToken', 'fake-refresh');
  localStorage.setItem('nex.user', JSON.stringify({ uuid: 'u1', email: 'tester@nex.dev', profile: { nickname: 'tester', avatar_url: '', direction: null, daily_minutes: 0, plan: 'free', theme: 'light', reduced_motion: false, font_scale: 1 } }));
});
await page.route('**/*', handle);

try {
  log('打开前端', BASE);
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });

  log('进入「试炼实验室」（练习/判题页）');
  await page.locator('.km-nav-item', { hasText: '试炼实验室' }).first().click();
  await page.waitForSelector('.bank-tab', { timeout: 10000 });

  log('切到「判题台」');
  await page.locator('.bank-tab', { hasText: '判题台' }).first().click();
  await page.waitForSelector('.jp-select', { timeout: 10000 });

  log('选语言 C++');
  await page.selectOption('.jp-select', 'cpp');

  log('断言：云端判题已启用（backend 通道 banner）');
  const banner = page.locator('.jp-banner--info');
  await banner.waitFor({ timeout: 8000 });
  const bannerText = await banner.first().innerText();
  check('backend 通道 banner 可见', true, JSON.stringify(bannerText));
  check('banner 文案含“云端判题已启用”', bannerText.includes('云端判题已启用'));

  const channelLabel = await page.locator('.jp-channel').first().innerText();
  check('通道标签=云端判题', channelLabel.includes('云端判题'), JSON.stringify(channelLabel));

  log('填 C++ 代码 + 两个用例');
  const code = '#include <iostream>\nusing namespace std;\nint main(){ int a,b; cin>>a>>b; cout<<a+b<<endl; return 0; }';
  await page.fill('.jp-editor', code);
  const rows = page.locator('.jp-case-row');
  await rows.nth(0).locator('input').nth(1).fill('2 3');   // stdin
  await rows.nth(0).locator('input').nth(2).fill('5');     // expected
  await rows.nth(1).locator('input').nth(1).fill('10 20');
  await rows.nth(1).locator('input').nth(2).fill('999');

  log('点「提交判题」→ 触发 backend 通道');
  await page.locator('button.jp-btn--primary').click();

  log('等待逐用例结果渲染');
  await page.waitForSelector('.jp-list .jp-item', { timeout: 20000 });
  const items = page.locator('.jp-list .jp-item');
  const count = await items.count();
  check('渲染 2 条用例结果', count === 2, `count=${count}`);

  const subtitle = await page.locator('.jp-subtitle', { hasText: '结果' }).first().innerText();
  check('副标题显示“1 / 2 通过”', subtitle.includes('1 / 2'), JSON.stringify(subtitle));

  const reasons = await page.locator('.jp-item .jp-reason').allInnerTexts();
  check('存在一条 WA（输出与期望不一致）', reasons.some((r) => r.includes('输出与期望不一致')), JSON.stringify(reasons));

  log('断言：前端真的走了 POST /judge/submissions（backend 通道）');
  check('捕获到提交负载', !!captured.submission);
  check('exercise_id=null（自由运行台）', captured.submission?.exercise_id === null);
  check('lang=cpp17', captured.submission?.lang === 'cpp17', JSON.stringify(captured.submission?.lang));
  check('携带 2 条 test_cases', Array.isArray(captured.submission?.test_cases) && captured.submission.test_cases.length === 2, `len=${captured.submission?.test_cases?.length}`);
  check('轮询≥1次 GET 详情', captured.polls >= 1, `polls=${captured.polls}`);
} catch (e) {
  fails.push('exception:' + e.message);
  log('EXCEPTION', e.message);
  try { await page.screenshot({ path: 'C:/temp/verify_fail.png', fullPage: true }); log('截图已存 C:/temp/verify_fail.png'); } catch {}
} finally {
  await browser.close();
}

if (fails.length) {
  console.log('\n=== RESULT: FAIL (' + fails.length + ') ===');
  console.log(fails.join('\n'));
  process.exit(1);
} else {
  console.log('\n=== RESULT: ALL PASS ===');
}
