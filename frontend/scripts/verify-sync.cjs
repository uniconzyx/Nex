/**
 * 进度同步端到端验收（Edge headless）
 * 流程：注册登录 → 标记一章 → 服务端核对 → 清空本机 → 重新登录 → 云端补回
 */
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EMAIL = 'sync' + Date.now() + '@nex.dev';
const PASS = 'Passw0rd!2026';

(async () => {
  const b = await chromium.launch({
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    headless: true,
    args: ['--no-proxy-server'],
  });
  const p = await b.newPage({ viewport: { width: 1280, height: 950 } });
  const reqs = [];
  p.on('request', (r) => {
    if (r.url().includes('/progress/state')) reqs.push(r.method() + ' ' + r.url().split('/api')[1]);
  });

  await p.goto('http://127.0.0.1:1420/', { waitUntil: 'networkidle' });
  await p.evaluate(() => localStorage.clear());
  await p.reload({ waitUntil: 'networkidle' });
  await p.waitForTimeout(500);
  // localStorage.clear() 会连带清掉当前页，reload 后回到首页，需要重新导航

  // 登录（注册）
  await p.locator('.km-nav-item', { hasText: '个人闯关档案' }).first().click();
  await p.locator('.km-account .km-btn', { hasText: '登录 / 注册' }).click();
  await p.locator('.km-login-tab', { hasText: '注册' }).click();
  await p.locator('.km-login-fields input').nth(0).fill('同步验收喵');
  await p.locator('.km-login-fields input').nth(1).fill(EMAIL);
  await p.locator('.km-login-fields input').nth(2).fill(PASS);
  await p.locator('.km-login-actions .km-btn').click();
  await p.waitForTimeout(2000);
  const loggedIn = (await p.locator('.km-account .km-tag').innerText()).includes('已登录');

  // 标记一章：学习页的节点圆点就是「标记掌握」开关
  await p.locator('.km-nav-item', { hasText: '知识试炼区' }).first().click();
  await p.waitForTimeout(600);
  const markBtn = p.locator('.km-node-dot[aria-label="标记掌握"]').first();
  const hasMark = await markBtn.count();
  if (hasMark) {
    await markBtn.scrollIntoViewIfNeeded();
    await markBtn.click();
  }
  await p.waitForTimeout(1600);

  const localAfter = await p.evaluate(() => JSON.parse(localStorage.getItem('kaimao.progress.v1')));
  const token = await p.evaluate(() => localStorage.getItem('nex.accessToken'));
  const server = await p.evaluate(async (t) => {
    const r = await fetch('http://127.0.0.1:8000/api/v1/progress/state', {
      headers: { Authorization: 'Bearer ' + t },
    });
    return (await r.json()).data;
  }, token);

  // 模拟"换设备"：清掉本机进度再登录，看云端能否补回
  await p.evaluate(() => localStorage.removeItem('kaimao.progress.v1'));
  await p.reload({ waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);
  await p.locator('.km-nav-item', { hasText: '个人闯关档案' }).first().click();
  await p.waitForTimeout(400);
  const needLogin = await p.locator('.km-account .km-btn', { hasText: '登录 / 注册' }).count();
  if (needLogin === 0) {
    // 令牌还在、账号卡直接是已登录态：这里模拟"新装应用"——主动退出再登录一次
    await p.locator('.km-account .km-btn', { hasText: '退出登录' }).click();
    await p.waitForTimeout(300);
    await p.locator('.km-account .km-btn', { hasText: '登录 / 注册' }).click();
  }
  await p.locator('.km-login-fields input').nth(0).fill(EMAIL);
  await p.locator('.km-login-fields input').nth(1).fill(PASS);
  await p.locator('.km-login-actions .km-btn').click();
  await p.waitForTimeout(2200);
  const localRestored = await p.evaluate(
    () => JSON.parse(localStorage.getItem('kaimao.progress.v1'))?.doneChapters ?? [],
  );

  console.log(
    JSON.stringify(
      {
        loggedIn,
        hasMark,
        localChapters: localAfter?.doneChapters,
        serverChapters: server?.done_chapters,
        serverCoins: server?.coins,
        restoredChapters: localRestored,
        requests: reqs.slice(0, 8),
      },
      null,
      1,
    ),
  );
  await b.close();
  process.exit(0);
})().catch((e) => {
  console.error('FAILED', e.message);
  process.exit(1);
});
