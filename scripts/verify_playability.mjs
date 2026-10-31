/**
 * verify_playability.mjs —— P0/P1 的真浏览器验收
 * ============================================================================
 * 验的是一条完整因果链，而不是"页面能打开"：
 *   清空进度 → 做错一题 → 怪物遭遇弹窗 → 图鉴出现怪物 → 重做答对 → 收服
 *   → 金币入账 → 背包流水可追溯 → 刷新不丢
 * 外加 v1 → v2 迁移：旧 doneChapters 不能丢。
 *
 * 用法（需先起 dev server 127.0.0.1:1420）：
 *   node scripts/verify_playability.mjs
 * 退出码 0 = 全部通过。
 * ============================================================================
 */
import { createRequire } from 'module';
import { mkdirSync } from 'fs';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:1420/';
const OUT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind/scratch/playability-shots';
mkdirSync(OUT, { recursive: true });

const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
}

const browser = await chromium.launch({
  executablePath: EDGE,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
});

/* ══════════════════════════ 1. 主流程 ══════════════════════════ */
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => {
    const t = m.text();
    // 后端没起时前端会打一批 ERR_CONNECTION_REFUSED，那是离线模式的正常表现，
    // 不是 JS 运行时错误，不能算失败。
    if (m.type() === 'error' && !/ERR_CONNECTION_REFUSED|Failed to load resource/i.test(t)) {
      errors.push(t);
    }
  });

  // 干净起点：只清一次（sessionStorage 标记），否则 reload 时会把刚产生的进度也清掉，
  // 那样测的就不是"持久化"而是"清理脚本"了。
  await page.addInitScript(() => {
    if (sessionStorage.getItem('__km_cleared')) return;
    sessionStorage.setItem('__km_cleared', '1');
    for (const k of Object.keys(localStorage)) {
      if (k.startsWith('kaimao.') || k.startsWith('nex.bank')) localStorage.removeItem(k);
    }
  });
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-app', { timeout: 20000 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/01-home.png` });

  // 首页应该已经生成了今日试炼三题
  const dailyRows = await page.locator('.km-daily-row').count();
  check('首页今日试炼列出题目', dailyRows > 0, `${dailyRows} 条`);

  // 进试炼实验室
  await page.getByRole('button', { name: /试炼实验室/ }).first().click();
  await page.waitForSelector('.bank', { timeout: 15000 });
  await page.waitForTimeout(400);

  // 选一道选择题（客观题判分不依赖后端，离线可验）
  const choiceItem = page.locator('.bank-item').filter({ has: page.locator('.bank-type.t-choice') }).first();
  await choiceItem.click();
  await page.waitForSelector('.bank-detail', { timeout: 10000 });

  // 故意选第一个选项 → 对照答案
  await page.locator('.bank-opt').first().click();
  await page.locator('.bank-actions .km-btn-primary').first().click();
  await page.waitForTimeout(500);

  const wrong = (await page.locator('.bank-verdict.bad').count()) > 0;
  check('第一次作答被判错', wrong);

  // 怪物遭遇弹窗
  const encounter = page.locator('.km-encounter');
  const hasEnc = (await encounter.count()) > 0;
  check('答错后弹出「野生怪物出现」', hasEnc);
  if (hasEnc) {
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${OUT}/02-encounter.png` });
    await page.getByRole('button', { name: '稍后再说' }).click();
  }

  // 图鉴里应该已经有这只怪
  await page.getByRole('button', { name: /怪物图鉴/ }).first().click();
  await page.waitForSelector('.km-best-tabs', { timeout: 10000 });
  await page.waitForTimeout(500);
  const monCards = await page.locator('.km-mon-card').count();
  check('图鉴出现待收服怪物', monCards >= 1, `${monCards} 张卡`);

  const wildStat = await page.locator('.km-best-stat b').first().innerText();
  check('待收服计数 ≥ 1', Number(wildStat) >= 1, `待收服 ${wildStat}`);
  await page.screenshot({ path: `${OUT}/03-bestiary.png` });

  // 打开详情：应有八股情报
  await page.locator('.km-mon-card').first().click();
  await page.waitForSelector('.km-mon-detail', { timeout: 8000 });
  await page.waitForTimeout(400);
  const intelCount = await page.locator('.km-mon-detail .km-intel-item').count();
  check('详情里有相关八股情报', intelCount >= 1, `${intelCount} 条`);
  await page.locator('.km-mon-detail .km-intel-item summary').first().click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/04-monster-detail.png` });

  // 去收服：应带着这道题回到试炼实验室
  await page.getByRole('button', { name: '去收服' }).click();
  await page.waitForTimeout(900);
  const inLab = (await page.locator('.bank, .jp-page').count()) > 0;
  check('「去收服」回到实验室并带题', inLab);

  // 拿到正确答案：先随便答一次让 UI 标出 right，再按 right 选一遍
  const detailVisible = await page.locator('.bank-detail').count();
  if (detailVisible === 0) {
    // 可能落在题库 Tab 但详情没自动打开，重新点同类第一题
    const again = page.locator('.bank-item').filter({ has: page.locator('.bank-type.t-choice') }).first();
    if (await again.count()) await again.click();
    await page.waitForSelector('.bank-detail', { timeout: 8000 });
  }
  const optCount = await page.locator('.bank-opt').count();
  if ((await page.locator('.bank-verdict.bad, .bank-verdict.ok').count()) === 0) {
    await page.locator('.bank-opt').first().click();
    await page.locator('.bank-actions .km-btn-primary').first().click();
    await page.waitForTimeout(400);
  }
  if ((await page.locator('.km-encounter').count()) > 0) {
    await page.getByRole('button', { name: '稍后再说' }).click();
  }
  // 清空已选，按 UI 标出的正确项选
  const rightIdx = [];
  for (let i = 0; i < optCount; i += 1) {
    const cls = (await page.locator('.bank-opt').nth(i).getAttribute('class')) ?? '';
    if (cls.includes('right')) rightIdx.push(i);
  }
  if (rightIdx.length > 0) {
    for (let i = 0; i < optCount; i += 1) {
      const cls = (await page.locator('.bank-opt').nth(i).getAttribute('class')) ?? '';
      if (cls.includes('picked') && !cls.includes('right')) await page.locator('.bank-opt').nth(i).click();
    }
    for (const i of rightIdx) {
      const cls = (await page.locator('.bank-opt').nth(i).getAttribute('class')) ?? '';
      if (!cls.includes('picked')) await page.locator('.bank-opt').nth(i).click();
    }
    await page.locator('.bank-actions .km-btn-primary').first().click();
    await page.waitForTimeout(700);
  }
  const nowRight = (await page.locator('.bank-verdict.ok').count()) > 0;
  check('重做后判对', nowRight);

  const tameToast = await page.locator('.km-toast.k-tame, .km-toast.k-ok').count();
  check('收服有即时 toast 反馈', tameToast > 0);
  await page.screenshot({ path: `${OUT}/05-tamed-toast.png` });

  // 图鉴已收服
  await page.getByRole('button', { name: /怪物图鉴/ }).first().click();
  await page.waitForSelector('.km-best-tabs', { timeout: 10000 });
  await page.getByRole('tab', { name: /已收服/ }).click();
  await page.waitForTimeout(600);
  const tamedCards = await page.locator('.km-mon-card').count();
  check('已收服页出现该怪物', tamedCards >= 1, `${tamedCards} 张`);
  await page.screenshot({ path: `${OUT}/06-tamed-list.png` });

  // 金币流水
  await page.getByRole('button', { name: /资源背包/ }).first().click();
  await page.waitForSelector('.km-ledger, .km-empty', { timeout: 8000 });
  await page.waitForTimeout(400);
  const ledgerRows = await page.locator('.km-ledger-row').count();
  check('背包有结晶流水', ledgerRows >= 1, `${ledgerRows} 笔`);
  await page.screenshot({ path: `${OUT}/07-bag-ledger.png` });

  // 刷新后不丢
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-app', { timeout: 15000 });
  await page.waitForTimeout(800);
  const persisted = await page.evaluate(() => {
    const raw = localStorage.getItem('kaimao.progress.v2');
    if (!raw) return null;
    const s = JSON.parse(raw);
    return {
      monsters: Object.keys(s.bestiary ?? {}).length,
      tamed: Object.values(s.bestiary ?? {}).filter((m) => m.state === 'tamed').length,
      ledger: (s.coinLedger ?? []).length,
      coins: s.coins,
      daily: s.daily?.qids?.length ?? 0,
    };
  });
  check('刷新后图鉴记录不丢', !!persisted && persisted.monsters >= 1, JSON.stringify(persisted));
  check('刷新后金币流水不丢', !!persisted && persisted.ledger >= 1);
  check('今日试炼题单持久化', !!persisted && persisted.daily > 0);

  await page.getByRole('button', { name: /怪物图鉴/ }).first().click();
  await page.waitForSelector('.km-best-tabs', { timeout: 10000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/08-bestiary-after-reload.png` });

  // 八股情报库：260 条
  await page.getByRole('tab', { name: /八股情报库/ }).click();
  await page.waitForTimeout(500);
  const archiveItems = await page.locator('.km-archive-cat .km-intel-item').count();
  check('八股情报库按学科可读', archiveItems > 0, `${archiveItems} 条（当前学科）`);
  await page.screenshot({ path: `${OUT}/09-archive.png` });

  check('无 JS 运行时错误', errors.length === 0, errors.slice(0, 3).join(' | '));
  await ctx.close();
}

/* ══════════════════════════ 2. v1 → v2 迁移 ══════════════════════════ */
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.addInitScript(() => {
    for (const k of Object.keys(localStorage)) {
      if (k.startsWith('kaimao.') || k.startsWith('nex.bank')) localStorage.removeItem(k);
    }
    // 模拟老用户：v1 里已经掌握两章、有 999 结晶
    localStorage.setItem(
      'kaimao.progress.v1',
      JSON.stringify({
        theme: 'light',
        outfit: 'cape',
        doneProjects: ['clang-cjson'],
        doneChapters: ['cpp-ch01', 'cpp-ch02'],
        checkins: ['2026-10-26'],
        coins: 999,
      }),
    );
  });
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-app', { timeout: 20000 });
  await page.waitForTimeout(900);

  const migrated = await page.evaluate(() => {
    const v2 = JSON.parse(localStorage.getItem('kaimao.progress.v2') ?? 'null');
    const backup = localStorage.getItem('kaimao.progress.v1.backup');
    return {
      hasV2: !!v2,
      done: v2?.doneChapters ?? [],
      runs: v2?.chapterRuns ?? {},
      coins: v2?.coins,
      projects: v2?.doneProjects ?? [],
      outfit: v2?.outfit,
      backup: !!backup,
      ledger: v2?.coinLedger?.length ?? -1,
    };
  });
  check('v1 迁移生成 v2', migrated.hasV2);
  check('迁移不丢已掌握章节', migrated.done.includes('cpp-ch01') && migrated.done.includes('cpp-ch02'));
  check(
    '迁移补齐三关掌握度 100',
    (migrated.runs['cpp-ch01']?.concept ?? 0) === 1 && (migrated.runs['cpp-ch01']?.boss ?? 0) === 1,
  );
  check('迁移保留结晶/项目/装扮', migrated.coins === 999 && migrated.projects.length === 1 && migrated.outfit === 'cape');
  check('迁移保留 v1 原样备份', migrated.backup);
  check('迁移不伪造金币流水', migrated.ledger === 0);
  await page.screenshot({ path: `${OUT}/10-migration.png` });
  await ctx.close();
}

await browser.close();

/* ══════════════════════════ 汇总 ══════════════════════════ */
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} 项通过`);
if (failed.length) {
  console.log('失败项：');
  for (const f of failed) console.log(`  - ${f.name} ${f.detail}`);
  process.exit(1);
}
console.log('PLAYABILITY_OK');
