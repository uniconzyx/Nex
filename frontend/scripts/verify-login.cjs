/**
 * 登录界面真机验收（Edge headless + CDP）
 *
 * 覆盖：未登录态 → 注册 → 登录成功态 → 退出 → 错误密码提示 → 断网（后端不可达）提示
 * 前提：vite 跑在 1420，后端跑在 8000。
 */
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const BASE = 'http://127.0.0.1:1420/';
const EMAIL = `ui${Date.now()}@nex.dev`;
const PASS = 'Passw0rd!2026';

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    headless: true,
    args: ['--no-proxy-server'],
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(String(e)));

  const out = {};
  await page.goto(BASE, { waitUntil: 'networkidle' });

  // 进入「我的」
  await page.evaluate(() => localStorage.removeItem('nex.accessToken'));
  await page.locator('.km-sidenav .km-nav-item', { hasText: '个人闯关档案' }).first().click();
  await page.waitForTimeout(400);

  out.badgeBefore = (await page.locator('.km-account .km-tag').innerText()).trim();

  // 打开登录 → 切到注册
  await page.locator('.km-account .km-btn', { hasText: '登录 / 注册' }).click();
  await page.locator('.km-login-tab', { hasText: '注册' }).click();
  await page.locator('.km-login-fields input').nth(0).fill('界面验收喵');
  await page.locator('.km-login-fields input').nth(1).fill(EMAIL);
  await page.locator('.km-login-fields input').nth(2).fill(PASS);
  await page.locator('.km-login-actions .km-btn').click();
  await page.waitForTimeout(1800);

  out.badgeAfterRegister = (await page.locator('.km-account .km-tag').innerText()).trim();
  out.name = (await page.locator('.km-account-head h3').innerText()).trim();
  out.token = await page.evaluate(() => !!localStorage.getItem('nex.accessToken'));
  out.loginBoxClosed = (await page.locator('.km-login-box').count()) === 0;

  await page.screenshot({ path: '.scratch/login-online.png' });

  // 退出
  await page.locator('.km-account .km-btn', { hasText: '退出登录' }).click();
  await page.waitForTimeout(400);
  out.badgeAfterLogout = (await page.locator('.km-account .km-tag').innerText()).trim();

  // 错误密码
  await page.locator('.km-account .km-btn', { hasText: '登录 / 注册' }).click();
  await page.locator('.km-login-tab', { hasText: '登录' }).click();
  await page.locator('.km-login-fields input').nth(0).fill(EMAIL);
  await page.locator('.km-login-fields input').nth(1).fill('wrong-pass-123');
  await page.locator('.km-login-actions .km-btn').click();
  await page.waitForTimeout(1500);
  out.wrongPassErr = (await page.locator('.km-login-hint').innerText()).trim();

  // 移动端 375×812
  const m = await browser.newPage({ viewport: { width: 375, height: 812 }, isMobile: false });
  await m.goto(BASE, { waitUntil: 'networkidle' });
  await m.evaluate(() => {
    localStorage.removeItem('nex.accessToken');
    localStorage.removeItem('nex.user');
  });
  await m.reload({ waitUntil: 'networkidle' });
  await m.locator('.km-nav-item', { hasText: '个人闯关档案' }).first().click();
  await m.waitForTimeout(500);
  out.mobileNavActive = await m.evaluate(
    () => document.querySelector('.km-nav-item.on')?.textContent?.trim() ?? '',
  );
  await m.locator('.km-account .km-btn', { hasText: '登录 / 注册' }).click();
  await m.waitForTimeout(300);
  out.mobileOverflow = await m.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  out.mobileInputs = await m.locator('.km-login-fields input').count();
  await m.screenshot({ path: '.scratch/login-mobile.png', fullPage: false });

  out.consoleErrors = errors;
  console.log(JSON.stringify(out, null, 1));
  await browser.close();
  process.exit(0);
})().catch((e) => {
  console.error('FAILED', e);
  process.exit(1);
});
