// 真浏览器验收：题库列表接后端 GET /exercises（后端优先 + 本地 bundle 兜底）
// 验证两点：
//   1) happy：GET /exercises 真的被请求，云端徽章出现、本地列表（含判题数据）照常渲染、匹配题出现 ☁；
//   2) fallback：后端 500 时回落「离线 · 本地题库」，本地列表照样渲染（离线优先）。
import { createRequire } from 'module';
import { readFileSync } from 'fs';
const require = createRequire('C:/Users/zyx/.workbuddy/binaries/node/workspace/');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:1420';
const C = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*', 'access-control-allow-credentials': 'true' };
const JSONH = { ...C, 'content-type': 'application/json' };
const USER = { uuid: 'u1', email: 't@e.com', profile: { nickname: 'tester', avatar_url: '', direction: null, daily_minutes: 0, plan: 'free', theme: 'light', reduced_motion: false, font_scale: 1 } };

// 从本地 bundle 取一个 cpp 学科的真实标题，注入 mock 目录以便确定性验证 ☁ 标记
function firstCppTitle() {
  const src = readFileSync('D:/WB_Workspace/2026-09-19-21-42-03/CppMind/frontend/src/data/exercises.ts', 'utf8');
  const mi = src.indexOf('EXERCISES:');
  const start = src.indexOf('= [', mi) + 2;
  let i = start, depth = 0, inStr = false, esc = false, end = -1;
  for (; i < src.length; i++) {
    const ch = src[i];
    if (inStr) { if (esc) esc = false; else if (ch === '\\') esc = true; else if (ch === '"') inStr = false; continue; }
    if (ch === '"') inStr = true;
    else if (ch === '[') depth++;
    else if (ch === ']') { depth--; if (depth === 0) { end = i; break; } }
  }
  const arr = JSON.parse(src.slice(start, end + 1));
  const hit = arr.find((e) => e.subj === 'cpp' && e.title);
  return hit ? hit.title : arr[0].title;
}
const CPP_TITLE = firstCppTitle();
console.log('[verify] 注入的 cpp 标题 =', JSON.stringify(CPP_TITLE));

const fails = [];
const check = (n, c, extra = '') => { if (c) console.log('PASS:', n, extra); else { fails.push(n); console.log('FAIL:', n, extra); } };

async function run(mode) {
  const captured = { exercisesReq: false };
  const handler = async (route, request) => {
    const url = request.url(); const method = request.method();
    if (method === 'OPTIONS') return route.fulfill({ status: 204, headers: C });
    if (!url.includes('/api/v1/')) return route.continue();
    const path = new URL(url).pathname;
    const ok = (data) => route.fulfill({ status: 200, headers: JSONH, body: JSON.stringify({ code: 0, message: 'ok', data, traceId: 'x' }) });
    if (path === '/api/v1/system/health') return ok({ backend: { name: 'mock', version: '0', elapsed_ms: 1 }, database: { ok: true, checked: true }, features: {} });
    if (path === '/api/v1/users/me') return ok(USER);
    if (path === '/api/v1/exercises') {
      captured.exercisesReq = true;
      if (mode === 'fail') return route.fulfill({ status: 500, headers: JSONH, body: JSON.stringify({ code: 500, message: 'boom' }) });
      return ok({ items: [{ id: 1, chapter_id: 1, type: 'coding', difficulty: 'easy', title: CPP_TITLE, source: 'local', external_url: null }], total: 1 });
    }
    return ok({});
  };

  const browser = await chromium.launch({ channel: 'msedge', headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.addInitScript(() => {
    localStorage.setItem('nex.accessToken', 'fake-jwt-token');
    localStorage.setItem('nex.refreshToken', 'fake-refresh');
    localStorage.setItem('nex.user', JSON.stringify({ uuid: 'u1', email: 't@e.com', profile: { nickname: 'tester', avatar_url: '', direction: null, daily_minutes: 0, plan: 'free', theme: 'light', reduced_motion: false, font_scale: 1 } }));
  });
  await page.route('**/*', handler);
  const tag = `[${mode}]`;
  try {
    await page.goto(BASE, { waitUntil: 'domcontentloaded' });
    await page.locator('.km-nav-item', { hasText: '试炼实验室' }).first().click();
    await page.waitForSelector('.bank-tab', { timeout: 10000 });
    await page.locator('.bank-tab', { hasText: '题库' }).first().click();
    await page.waitForSelector('.bank-search', { timeout: 10000 });

    // 等云端同步状态稳定
    await page.waitForSelector('.bank-sync-pill', { timeout: 10000 });
    await page.waitForTimeout(500);

    if (mode === 'ok') {
      check(`${tag} GET /exercises 被请求`, captured.exercisesReq);
      const pill = await page.locator('.bank-sync-pill').first().innerText();
      check(`${tag} 云端同步徽章出现`, pill.includes('云端同步'), JSON.stringify(pill));
      const items = await page.locator('.bank-list .bank-item').count();
      check(`${tag} 本地列表照常渲染`, items > 0, `count=${items}`);
      const clouds = await page.locator('.bank-mark.cloud').count();
      check(`${tag} 匹配题出现 ☁ 标记`, clouds >= 1, `clouds=${clouds}`);
    } else {
      check(`${tag} GET /exercises 被请求`, captured.exercisesReq);
      const pill = await page.locator('.bank-sync-pill').first().innerText();
      check(`${tag} 离线回落徽章出现`, pill.includes('离线'), JSON.stringify(pill));
      const items = await page.locator('.bank-list .bank-item').count();
      check(`${tag} 本地列表照常渲染（离线优先）`, items > 0, `count=${items}`);
    }
  } catch (e) {
    fails.push(`${tag} exception: ${e.message}`);
    console.log('EXCEPTION', tag, e.message);
    try { await page.screenshot({ path: `C:/temp/verify_bank_${mode}.png`, fullPage: true }); } catch {}
  } finally {
    await browser.close();
  }
}

await run('ok');
await run('fail');

if (fails.length) { console.log('\n=== RESULT: FAIL (' + fails.length + ') ===\n' + fails.join('\n')); process.exit(1); }
console.log('\n=== RESULT: ALL PASS ===');
