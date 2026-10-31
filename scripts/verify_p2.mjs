/**
 * verify_p2.mjs —— P2 中环（章节三关 / 依赖图 / NextAction）的真浏览器验收
 * ============================================================================
 * 验的是「掌握度真的由做过的题算出来」，而不是页面自己写死一个数字：
 *
 *   A. 空进度 + 今日试炼已清空 → NextAction 只推「开新章」，不推不存在的关卡
 *   B. 只过概念 + 演练两关     → NextAction 推「BOSS 关」，并说清首领题
 *   C. 三关全通               → 节点 100%、三个 pip 全亮、章节进 doneChapters
 *   D. BOSS 关答错（真点 UI）  → 掌握度掉到 60%、弹「BOSS 关失守」、doneChapters 移除
 *   E. 项目页                  → 前置达标 / 未达标两种卡片、详情列出 requires 与百分比
 *   F. 学习页                  → 前置未满足的章节有提示，且能看到三关卡片
 *
 * 数据准备走「预置 localStorage」而不是点几十道题：三关的判定规则已在
 * scripts/audit_graph.py 与 lib/stages.ts 里单点定义，E2E 要验的是
 * 「状��� → 页面呈现 → 动作 → 状态变化」这条链，不是刷题耐力。
 *
 * 用法（需先起 dev server 127.0.0.1:1420）：
 *   node scripts/verify_p2.mjs
 * ============================================================================
 */
import { createRequire } from 'module';
import { mkdirSync, readFileSync } from 'fs';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:1420/';
const ROOT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind';
const OUT = `${ROOT}/scratch/p2-shots`;
mkdirSync(OUT, { recursive: true });

const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
}

/* ── 题库：拿本次要用的章节与题目（与 App 读的是同一份 exercises.ts） ── */
const src = readFileSync(`${ROOT}/frontend/src/data/exercises.ts`, 'utf8');
const marker = 'export const EXERCISES: BankExercise[] = ';
const arr = JSON.parse(src.slice(src.indexOf('[', src.indexOf(marker) + marker.length), src.lastIndexOf(']') + 1));
const byCh = {};
for (const e of arr) (byCh[e.ch] ||= []).push(e);

const DRILL = new Set(['coding', 'output', 'fix_error', 'design']);
const CH = 'data-ch02'; // 首领题恰好是选择题（可离线判），适合验「掉关」
const LIST = byCh[CH] ?? [];
const BOSS = (() => {
  for (const d of ['hard', 'medium', 'easy']) {
    const pool = LIST.filter((e) => e.diff === d);
    if (pool.length) return pool[pool.length - 1];
  }
  return LIST[LIST.length - 1];
})();
const CONCEPT_Q = LIST.find((e) => e.type === 'choice' || e.type === 'explain');
const DRILL_Q = LIST.filter((e) => DRILL.has(e.type));
const WRONG_OPT = (BOSS.options ?? []).map((o) => o.key).find((k) => !(BOSS.correct ?? []).includes(k));

const today = (() => {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
})();

/** 生成一份 v2 进度；correct 里的题记为答对 */
function makeState(correctIds) {
  const answers = {};
  for (const id of correctIds) {
    const ex = LIST.find((e) => e.id === id);
    if (ex) answers[id] = { chapterId: CH, ok: true, at: Date.now() };
  }
  return {
    theme: 'light',
    outfit: 'default',
    doneProjects: [],
    doneChapters: [],
    checkins: [],
    coins: 1280,
    coinLedger: [],
    bestiary: {},
    chapterRuns: {},
    answers,
    // 今日试炼预置为「已清空」：否则 NextAction 永远停在第 1 步（试炼），验不到后面的关卡
    daily: {
      date: today,
      qids: [LIST[0].id, LIST[1].id, LIST[2].id],
      done: [LIST[0].id, LIST[1].id, LIST[2].id],
      correct: [LIST[0].id, LIST[1].id, LIST[2].id],
      claimed: true,
    },
    shards: 0,
  };
}

const conceptOnly = [CONCEPT_Q.id, ...DRILL_Q.slice(0, 3).map((e) => e.id)];
const partial = conceptOnly; // 概念 + 演练，未过 BOSS
const full = LIST.map((e) => e.id);

console.log(`章节 ${CH}：${LIST.length} 题；首领 ${BOSS.id}（${BOSS.type}/${BOSS.diff}，正确 ${(BOSS.correct ?? []).join('')}，故意选 ${WRONG_OPT}）`);

const browser = await chromium.launch({
  executablePath: EDGE,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
});

/** 开一个干净的上下文，并把进度预置进去（只预置一次，reload 不清） */
async function open(seed, subject = 'data') {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => {
    const t = m.text();
    if (m.type() === 'error' && !/ERR_CONNECTION_REFUSED|Failed to load resource/i.test(t)) errors.push(t);
  });
  await page.addInitScript(
    (payload) => {
      if (sessionStorage.getItem('__km_seeded')) return;
      sessionStorage.setItem('__km_seeded', '1');
      for (const k of Object.keys(localStorage)) {
        if (k.startsWith('kaimao.') || k.startsWith('nex.')) localStorage.removeItem(k);
      }
      localStorage.setItem('kaimao.progress.v2', JSON.stringify(payload.state));
      localStorage.setItem('nex.subject', payload.subject);
      // 启动网关（未登录即全屏要求登录）：「本地模式」记一位，等价于点过「稍后体验」
      localStorage.setItem('nex.localMode', '1');
    },
    { state: seed, subject },
  );
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-app', { timeout: 20000 });
  await page.waitForTimeout(500);
  return { ctx, page, errors };
}

async function goLearn(page) {
  await page.getByRole('button', { name: /知识试炼区/ }).first().click();
  await page.waitForSelector('.km-map', { timeout: 15000 });
  await page.waitForTimeout(350);
}

/** 找到某一章的节点（按标题文本定位） */
function nodeOf(page, titlePart) {
  return page.locator('.km-node').filter({ hasText: titlePart }).first();
}

const readings = {};

/* ═════════════════ 1. 空进度：NextAction 只推「开新章」 ═════════════════ */
{
  const { ctx, page, errors } = await open(makeState([]));
  const next = page.locator('.km-next');
  const h2 = (await next.locator('h2').innerText()).trim();
  const cta = (await next.locator('.km-btn').first().innerText()).trim();
  /*
   * 2026-10-30 更新期望：data-ch01 的前置是 py-ch03（跨学科），
   * 所以"空进度 + 数据分析"根本开不了新章。旧版这里落到「去签到祭坛」，
   * 那是个死胡同（签完明天还是签到）。现在 nextAction 第 5b 档会指名
   * "还差哪一章前置"，并带上学科让 CTA 能跨学科打开。
   */
  check(
    '空进度时 NextAction 指名「缺哪一章前置」而不是让人去签到',
    /前置挡着/.test(h2) && cta.includes('去学那一章'),
    `${h2} / ${cta}`,
  );
  check('并说清缺几章', /共差 \d+ 章/.test((await next.locator('p').first().innerText()).trim()));

  await goLearn(page);
  // 标签文案在 P2 后期改成了「未解锁 · 需先过：xxx」，比"前置未满足"更能指导下一步
  const lockTags = await page.locator('.km-tag', { hasText: '未解锁' }).count();
  check('学习页标出被前置挡住的章节', lockTags > 0, `${lockTags} 章`);

  const pips = await page.locator('.km-node').first().locator('.km-pip').count();
  check('地图节点显示三个关卡 pip', pips === 3, `${pips} 个`);

  // 展开第一章看三关卡片
  await page.locator('.km-node-main').first().click();
  await page.waitForSelector('.km-stages', { timeout: 8000 });
  const stageCount = await page.locator('.km-stage').count();
  const stageTitles = await page.locator('.km-stage-head b').allInnerTexts();
  check('展开后有三张关卡卡', stageCount === 3, stageTitles.join(' / '));
  const weights = await page.locator('.km-stage-weight').allInnerTexts();
  check(
    '权重是 30 / 30 / 40',
    weights.length === 3 && /30/.test(weights[0]) && /30/.test(weights[1]) && /40/.test(weights[2]),
    weights.join(' / '),
  );
  await page.screenshot({ path: `${OUT}/01-learn-stages.png` });

  readings.empty = { errors };
  await ctx.close();
}

/* ═════════════════ 2. 概念+演练：NextAction 推 BOSS 关 ═════════════════ */
{
  const { ctx, page, errors } = await open(makeState(partial));
  const next = page.locator('.km-next');
  const h2 = (await next.locator('h2').innerText()).trim();
  const sub = (await next.locator('p').first().innerText()).trim();
  const cta = (await next.locator('.km-btn').first().innerText()).trim();
  check('只过两关时 NextAction 指向 BOSS 关', /BOSS 关/.test(h2), h2);
  check('并说清还差什么', /掌握度 60%|已过 2\/3 关/.test(sub), sub);
  check('CTA 是「打这一关的首领」', cta.includes('首领'), cta);

  await goLearn(page);
  const node = nodeOf(page, 'NumPy 进阶');
  const hasPartial = (await node.getAttribute('class'))?.includes('partial');
  check('节点进入 partial 态（有进度未通关）', !!hasPartial);
  const pipsOn = await node.locator('.km-pip.on').count();
  check('节点上亮 2 个 pip', pipsOn === 2, `${pipsOn} 个`);
  await page.screenshot({ path: `${OUT}/02-partial-node.png` });
  readings.partial = { errors };
  await ctx.close();
}

/* ═════════════════ 3~4. 三关全通 → 答错掉关 ═════════════════ */
{
  const { ctx, page, errors } = await open(makeState(full));
  await goLearn(page);
  const node = nodeOf(page, 'NumPy 进阶');
  const cls = (await node.getAttribute('class')) ?? '';
  check('全通章节节点是 done 态', cls.includes('done'), cls);

  await node.locator('.km-node-main').click();
  await page.waitForSelector('.km-stages', { timeout: 8000 });
  const chip = (await page.locator('.km-mastery-chip').innerText()).trim();
  const doneStages = await page.locator('.km-stage.done').count();
  check('掌握度显示 100%', chip.includes('100%'), chip);
  check('三张关卡卡全部通过', doneStages === 3, `${doneStages}/3`);
  await page.screenshot({ path: `${OUT}/03-chapter-100.png` });

  const st1 = await page.evaluate(() => {
    const s = JSON.parse(localStorage.getItem('kaimao.progress.v2') ?? '{}');
    return { runs: s.chapterRuns?.['data-ch02'], done: s.doneChapters ?? [] };
  });
  check('chapterRuns 三关写满', JSON.stringify(st1.runs) && st1.runs.concept === 1 && st1.runs.drill === 1 && st1.runs.boss === 1, JSON.stringify(st1.runs));
  check('章节进入 doneChapters', st1.done.includes('data-ch02'));

  // —— BOSS 关故意打错 ——
  const bossCard = page.locator('.km-stage').filter({ hasText: 'BOSS 关' }).first();
  await bossCard.locator('.km-btn').click();
  await page.waitForSelector('.bank-detail', { timeout: 15000 });
  await page.waitForTimeout(400);
  const openedTitle = (await page.locator('.bank-detail h3').innerText()).trim();
  check('BOSS 关直接打开首领题', openedTitle === BOSS.title, openedTitle.slice(0, 30));

  const keys = await page.locator('.bank-opt i').allInnerTexts();
  const wrongIdx = keys.findIndex((k) => k.trim() === WRONG_OPT);
  if (wrongIdx < 0) throw new Error(`选项里找不到 ${WRONG_OPT}：${keys.join(',')}`);
  await page.locator('.bank-opt').nth(wrongIdx).click();
  await page.getByRole('button', { name: '对照答案' }).click();
  await page.waitForTimeout(700);

  const toastText = (await page.locator('.km-toast').allInnerTexts()).join(' | ');
  check('答错后提示「BOSS 关失守」', /失守/.test(toastText), toastText.replace(/\n/g, ' ').slice(0, 90));

  // 遭遇卡会盖住页面：按 Esc 关掉再回学习页
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  await goLearn(page);
  const node2 = nodeOf(page, 'NumPy 进阶');
  await node2.locator('.km-node-main').click();
  await page.waitForSelector('.km-stages', { timeout: 8000 });
  const chip2 = (await page.locator('.km-mastery-chip').innerText()).trim();
  check('BOSS 失守后掌握度回落到 60%', chip2.includes('60%'), chip2);

  const st2 = await page.evaluate(() => {
    const s = JSON.parse(localStorage.getItem('kaimao.progress.v2') ?? '{}');
    return { runs: s.chapterRuns?.['data-ch02'], done: s.doneChapters ?? [], wild: Object.values(s.bestiary ?? {}).filter((m) => m.state === 'wild').length };
  });
  check('chapterRuns.boss 回落到 0', st2.runs && st2.runs.boss === 0, JSON.stringify(st2.runs));
  check('doneChapters 移除该章', !st2.done.includes('data-ch02'), JSON.stringify(st2.done));
  check('答错的题变成野生怪物', st2.wild >= 1, `${st2.wild} 只`);
  await page.screenshot({ path: `${OUT}/04-boss-lost.png` });
  readings.regression = { errors };
  await ctx.close();
}

/* ═════════════════ 5. 项目前置达标 / 未达标 ═════════════════ */
{
  // 未达标：空进度
  {
    const { ctx, page, errors } = await open(makeState([]));
    await page.getByRole('button', { name: /BOSS项目实战/ }).first().click();
    await page.waitForSelector('.cp-grid', { timeout: 15000 });
    await page.waitForTimeout(400);
    const lock = await page.locator('.cp-lock-tag').count();
    const ready = await page.locator('.cp-ready-tag').count();
    check('空进度时项目全是「未达标」', lock > 0 && ready === 0, `锁 ${lock} / 达标 ${ready}`);

    await page.locator('.cp-card').first().click();
    await page.waitForSelector('.cp-requires', { timeout: 8000 });
    const rows = await page.locator('.cp-requires li').count();
    const badRows = await page.locator('.cp-requires li.bad').count();
    check('详情列出前置章节', rows > 0, `${rows} 章`);
    check('未达标的前置标出来', badRows > 0, `${badRows} 章未达标`);

    await page.locator('.cp-detail-close').click();
    await page.waitForTimeout(200);
    const beforeAll = await page.locator('.cp-card').count();
    await page.locator('.cp-open-only input').check();
    await page.waitForTimeout(300);
    const onlyOpen = await page.locator('.cp-card').count();
    check(
      '「只看前置达标」在空进度下把项目全筛掉',
      beforeAll > 0 && onlyOpen === 0,
      `${beforeAll} → ${onlyOpen}`,
    );
    await page.screenshot({ path: `${OUT}/05-project-locked.png` });
    readings.projectLocked = { errors };
    await ctx.close();
  }

  // 达标：把 data 全 6 章都刷到 100
  {
    const allIds = [];
    for (const ch of Object.keys(byCh).filter((c) => c.startsWith('data-ch'))) {
      for (const e of byCh[ch]) allIds.push(e.id);
    }
    const state = makeState(allIds);
    // makeState 里 answers 的 chapterId 固定写成 CH，这里按真实章节重写
    for (const id of allIds) {
      const ex = arr.find((e) => e.id === id);
      state.answers[id] = { chapterId: ex.ch, ok: true, at: Date.now() };
    }
    const { ctx, page, errors } = await open(state);
    await page.getByRole('button', { name: /BOSS项目实战/ }).first().click();
    await page.waitForSelector('.cp-grid', { timeout: 15000 });
    await page.waitForTimeout(400);
    const ready = await page.locator('.cp-ready-tag').count();
    check('学科章节全通后项目出现「前置已达标」', ready > 0, `${ready} 个`);

    const beforeAll = await page.locator('.cp-card').count();
    await page.locator('.cp-open-only input').check();
    await page.waitForTimeout(300);
    const onlyOpen = await page.locator('.cp-card').count();
    check('全通后「只看前置达标」不再筛掉项目', onlyOpen > 0 && onlyOpen <= beforeAll, `${beforeAll} → ${onlyOpen}`);

    const firstReady = page.locator('.cp-card').filter({ has: page.locator('.cp-ready-tag') }).first();
    await firstReady.click();
    await page.waitForSelector('.cp-requires', { timeout: 8000 });
    const okRows = await page.locator('.cp-requires li.ok').count();
    check('详情里前置全部标绿', okRows > 0, `${okRows} 章达标`);
    await page.screenshot({ path: `${OUT}/06-project-ready.png` });
    readings.projectReady = { errors };
    await ctx.close();
  }
}

await browser.close();

/* ═════════════════ 汇总 ═════════════════ */
const allErrors = Object.values(readings).flatMap((r) => r.errors ?? []);
check('全程无 JS 运行时错误', allErrors.length === 0, allErrors.slice(0, 2).join(' | '));

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} 项通过`);
if (failed.length) {
  console.log('失败项：');
  for (const f of failed) console.log(`  - ${f.name} ${f.detail}`);
  process.exit(1);
}
console.log('P2_OK');
