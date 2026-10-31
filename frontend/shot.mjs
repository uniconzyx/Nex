/* 用系统 Edge（headless）+ playwright-core 走一遍关键路径并截图。
   用法：node shot.mjs <baseUrl> <outDir>
   要点（踩过的坑）：
   - ESM 里 import Windows 绝对路径必须写 file:///C:/...，否则 ERR_UNSUPPORTED_ESM_URL_SCHEME；
   - 本机系统代理指向死端口，Edge 必须加 --no-proxy-server，否则连 127.0.0.1 都是 CONNECTION_REFUSED；
   - 应用外壳是 100dvh + 内部滚动，fullPage 截不到折叠区，得先 scrollIntoView；
   - 结尾 process.exit(0)，否则 CDP 连接不关会让进程挂住。 */
import { chromium } from 'file:///C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core/index.mjs';

const base = process.argv[2] ?? 'http://127.0.0.1:4173';
const out = process.argv[3] ?? '.';
const errs = [];
const facts = {};

const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  args: ['--headless=new', '--disable-gpu', '--no-proxy-server', '--proxy-bypass-list=*'],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
page.on('console', (m) => {
  if (m.type() === 'error') errs.push(m.text());
});
page.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));

await page.goto(base, { waitUntil: 'networkidle' });

/* ---------- 1. 学习页：展开第一章，滚到「本章题目」块 ---------- */
await page.getByRole('button', { name: /知识试炼区/ }).first().click();
await page.waitForTimeout(400);
await page.locator('.km-node-main').first().click();
await page.waitForTimeout(300);
const learnBank = page.locator('.learn-bank').first();
if (await learnBank.count()) {
  await learnBank.scrollIntoViewIfNeeded();
  await page.waitForTimeout(200);
  facts.learnBank = (await learnBank.innerText()).replace(/\s+/g, ' ').slice(0, 160);
}
await page.screenshot({ path: `${out}/03-learn-open.png` });

/* ---------- 2. 「做本章这 N 题」→ 应落到题库并锁定章节 ---------- */
const doBtn = page.getByRole('button', { name: /做本章这/ }).first();
if (await doBtn.count()) {
  await doBtn.click();
  await page.waitForTimeout(500);
  facts.focusBar = (await page.locator('.bank-focus').first().innerText().catch(() => '')).replace(/\s+/g, ' ');
  facts.chapterRows = await page.locator('.bank-item').count();
  await page.screenshot({ path: `${out}/04-bank-chapter.png` });
}

/* ---------- 3. 清掉章节锁，看全学科 + 勾「仅可判」 ---------- */
const clearBtn = page.locator('.bank-focus button').first();
if (await clearBtn.count()) await clearBtn.click();
await page.waitForTimeout(200);
facts.allRows = await page.locator('.bank-item').count();
facts.allChip = (await page.locator('.bank-chip').first().innerText()).replace(/\s+/g, ' ');

await page.getByText(/^仅可判/, { exact: false }).first().click();
await page.waitForTimeout(300);
facts.judgeableRows = await page.locator('.bank-item').count();
await page.screenshot({ path: `${out}/05-bank-judgeable.png` });

/* ---------- 4. 点开一道可判题，检查详情 ---------- */
const firstItem = page.locator('.bank-item').first();
if (await firstItem.count()) {
  await firstItem.click();
  await page.waitForTimeout(300);
  facts.detailCtas = await page.locator('.bank-cta').count();
  await page.screenshot({ path: `${out}/06-bank-detail.png` });
}

/* ---------- 5. 「去判题台」→ 判题台应带题面 ---------- */
const goJudge = page.getByRole('button', { name: '去判题台' }).first();
if (await goJudge.count()) {
  await goJudge.click();
  await page.waitForTimeout(800);
  facts.judgeTitle = await page.locator('.jp-title').first().innerText().catch(() => '');
  facts.hasProblem = await page.locator('.jp-problem').count();
  facts.caseRows = await page.locator('.jp-case-row').count();
  await page.screenshot({ path: `${out}/07-judge.png` });
}

/* ---------- 6. 选择题：不应出现判题入口 ---------- */
await page.getByRole('button', { name: /^题库/ }).first().click();
await page.waitForTimeout(300);
await page.locator('.bank-chip', { hasText: '选择' }).first().click();
await page.waitForTimeout(200);
await page.locator('.bank-item').first().click();
await page.waitForTimeout(300);
facts.choiceCtas = await page.locator('.bank-cta').count();
facts.choiceOpts = await page.locator('.bank-opt').count();
await page.screenshot({ path: `${out}/08-choice.png` });

/* ---------- 7. 手机视口 ---------- */
await page.setViewportSize({ width: 390, height: 844 });
await page.waitForTimeout(400);
await page.screenshot({ path: `${out}/09-mobile.png` });

console.log(JSON.stringify({ facts, errors: errs.slice(0, 12) }, null, 2));
await browser.close();
process.exit(0);
