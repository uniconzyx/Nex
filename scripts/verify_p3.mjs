/**
 * verify_p3.mjs —— P3 外环（周 BOSS / 141 幕旁白）的真浏览器验收
 * ============================================================================
 * 验的是「这两样东西真的接在进度上」，不是"页面上有张好看的卡"：
 *
 *   A. 空进度            → 首页出现本周 BOSS 卡，门槛 0/6、三行题目、按钮禁用
 *   B. 本周答对 6 题     → 门槛解锁、按钮可点（门槛来自 answers，不是按钮）
 *   C. 三个季度对照组     → 已通关态显示「已通关」，不再提示再打
 *   D. 剧情页 幕·旁白     → 13 学科 / 153 条；archive 未解锁时只给锚点、
 *                          掌握度 100 的那一条真的能读到
 *   E. 学习页章节详情     → 本章旁白块存在，pitfall 类未完成也可见
 *   F. 全程无 pageerror / console error
 *
 * 数据准备走「预置 localStorage」，理由同 verify_p2：判定规则已在 lib/weekly.ts
 * 与 lib/progress.ts 单点定义，E2E 要验的是「状态 → 呈现 → 门槛」这条链。
 *
 * 用法（需先起 dev server 127.0.0.1:1420）：
 *   node scripts/verify_p3.mjs
 * ============================================================================
 */
import { createRequire } from 'module';
import { mkdirSync, readdirSync, readFileSync } from 'fs';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:1420/';
const ROOT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind';
const OUT = `${ROOT}/scratch/p3-shots`;
mkdirSync(OUT, { recursive: true });

const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
}

/* ── 题库（与 App 读同一份 exercises.ts） ── */
const src = readFileSync(`${ROOT}/frontend/src/data/exercises.ts`, 'utf8');
const marker = 'export const EXERCISES: BankExercise[] = ';
const all = JSON.parse(src.slice(src.indexOf('[', src.indexOf(marker) + marker.length), src.lastIndexOf(']') + 1));
const byCh = {};
for (const e of all) (byCh[e.ch] ||= []).push(e);

/** 与 lib/weekly.ts 的 weekKey 同算法：ISO 周，周一起算 */
function weekKey(d = new Date()) {
  const t = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = (t.getDay() + 6) % 7;
  t.setDate(t.getDate() - day + 3);
  const year = t.getFullYear();
  const jan4 = new Date(year, 0, 4);
  const jan4Day = (jan4.getDay() + 6) % 7;
  const week1Monday = new Date(year, 0, 4 - jan4Day);
  const n = Math.round((t.getTime() - week1Monday.getTime()) / (7 * 86400000)) + 1;
  return `${year}-W${String(n).padStart(2, '0')}`;
}
const WEEK = weekKey();

const today = (() => {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
})();

/* 选一章有题的（data-ch02 在 P2 里已确认有 5+ 题、含选择题与动手题） */
const WCH = 'data-ch02';
const WQIDS = (byCh[WCH] ?? []).slice(0, 3).map((e) => e.id);
if (WQIDS.length < 3) {
  console.error(`章节 ${WCH} 不足 3 题，无法构造周 BOSS 夹具`);
  process.exit(1);
}

/* 旁白：挑一条 archive（需解锁）与一条 pitfall（不需解锁） */
const acts = JSON.parse(readFileSync(`${ROOT}/content/_story/acts.json`, 'utf8'));

/**
 * chapterId → 章节标题。acts.json 里只有 id，没有标题；
 * 页面上的节点是按标题渲染的，所以得从 content/<学科>/_manifest.json 补这一层。
 */
const chapterTitles = {};
for (const dir of readdirSync(`${ROOT}/content`)) {
  try {
    const m = JSON.parse(readFileSync(`${ROOT}/content/${dir}/_manifest.json`, 'utf8'));
    for (const c of m.chapters ?? []) chapterTitles[c.id] = c.title;
  } catch {
    /* 有的目录没有 manifest（_backup / _template 等），跳过 */
  }
}

let archiveLine = null;
let teaserLine = null;
let storyTotal = 0;
for (const [key, subj] of Object.entries(acts.subjects)) {
  for (const act of subj.acts) {
    for (const ch of act.chapters) {
      storyTotal += 1;
      if (!archiveLine && ch.tone === 'archive' && byCh[ch.id]) archiveLine = { ...ch, subject: key };
      if (!teaserLine && ch.tone === 'pitfall' && byCh[ch.id]) teaserLine = { ...ch, subject: key };
    }
  }
}
if (!archiveLine) {
  console.error('没有找到可测的 archive 台词');
  process.exit(1);
}

/** 一份 v2 进度骨架 */
function makeState({ correct = [], weekly = null, chapterRuns = {} } = {}) {
  const answers = {};
  for (const id of correct) answers[id] = { chapterId: (all.find((e) => e.id === id) || {}).ch ?? '', ok: true, at: Date.now() };
  return {
    theme: 'light',
    outfit: 'default',
    ownedOutfits: ['default'],
    doneProjects: [],
    doneChapters: [],
    checkins: [],
    coins: 1280,
    coinLedger: [],
    bestiary: {},
    chapterRuns,
    answers,
    // 今日试炼置为已清空，否则首页第一大卡永远是"去做今日试炼"
    daily: { date: today, qids: [all[0].id], done: [all[0].id], correct: [all[0].id], claimed: true },
    weekly,
    shards: 0,
  };
}

/** 本周题单夹具（chapterId + 真存在的 3 道题） */
function weeklyFixture({ claimed = false, correct = [], done = [] } = {}) {
  return { week: WEEK, chapterId: WCH, qids: WQIDS, done, correct, claimed };
}

const browser = await chromium.launch({
  executablePath: EDGE,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
});

async function open(state, subject = 'data') {
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
      // 启动网关：不点这一位就永远停在登录页，验不到主界面。
      // 置 1 = "用户已选过本地模式"，与真机上点一次「稍后体验」等价。
      localStorage.setItem('nex.localMode', '1');
    },
    { state, subject },
  );
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-app', { timeout: 20000 });
  await page.waitForTimeout(600);
  return { ctx, page, errors };
}

console.log(`本周 = ${WEEK}；夹具章节 ${WCH}，题目 ${WQIDS.join(', ')}`);
console.log(`旁白 archive 样本：${archiveLine.id}（${archiveLine.subject}）；pitfall 样本：${teaserLine?.id}`);

/* ═════════════════ A. 空进度：门槛未解锁 ═════════════════ */
{
  const { ctx, page, errors } = await open(makeState());
  const card = page.locator('.km-weekly');
  check('首页出现本周 BOSS 卡', (await card.count()) === 1);

  const rows = card.locator('.km-daily-row');
  check('卡里正好三行题目', (await rows.count()) === 3, `${await rows.count()} 行`);

  const gateText = (await card.locator('.km-weekly-gate-label').innerText()).trim();
  check('门槛从 0 起算（本周还没答对）', /0\/6/.test(gateText), gateText);
  check('门槛未达时标注「未解锁」', (await card.locator('.km-tag', { hasText: '未解锁' }).count()) === 1);

  const disabled = await rows.first().isDisabled();
  check('门槛未达时题目按钮禁用（不给"点了却没算"的错觉）', disabled === true);

  const heading = (await card.locator('h3').innerText()).trim();
  check('卡片标题带目标章节名', /本周 BOSS · /.test(heading) && heading.length > 8, heading);
  await page.screenshot({ path: `${OUT}/A-weekly-locked.png`, fullPage: false });
  check('A 段无 JS 报错', errors.length === 0, errors.slice(0, 2).join(' | '));
  await ctx.close();
}

/* ═════════════════ B. 本周答对 6 题：门槛解锁 ═════════════════ */
{
  // 取 6 道真实存在的题，记为本周答对
  const six = Object.values(byCh).flat().slice(0, 6).map((e) => e.id);
  const { ctx, page, errors } = await open(
    makeState({ correct: six, weekly: weeklyFixture() }),
  );
  const card = page.locator('.km-weekly');
  const gateText = (await card.locator('.km-weekly-gate-label').innerText()).trim();
  check('答对 6 题后门槛显示 6/6', /6\/6/.test(gateText), gateText);
  check('门槛达成后标「已解锁」', (await card.locator('.km-tag', { hasText: '已解锁' }).count()) === 1);

  const rows = card.locator('.km-daily-row');
  const enabled = !(await rows.first().isDisabled());
  check('门槛达成后题目按钮可点', enabled === true);

  // 题目文本来自题库，不是占位符
  const firstTitle = (await rows.first().locator('b').innerText()).trim();
  const expected = all.find((e) => e.id === WQIDS[0])?.title ?? '';
  check('第一行显示真实题目标题', firstTitle === expected, `${firstTitle.slice(0, 24)}…`);

  await page.screenshot({ path: `${OUT}/B-weekly-open.png` });
  check('B 段无 JS 报错', errors.length === 0, errors.slice(0, 2).join(' | '));
  await ctx.close();
}

/* ═════════════════ C. 已通关态 ═════════════════ */
{
  const { ctx, page, errors } = await open(
    makeState({
      correct: Object.values(byCh).flat().slice(0, 6).map((e) => e.id),
      weekly: weeklyFixture({ claimed: true, done: WQIDS, correct: WQIDS }),
    }),
  );
  const card = page.locator('.km-weekly');
  check('通关后标「已通关」', (await card.locator('.km-tag', { hasText: '已通关' }).count()) === 1);
  const hints = (await card.locator('.km-hint').innerText()).trim();
  check('通关后文案改成「已收工 · 下周一换新的」', /已收工/.test(hints), hints.slice(0, 40));
  const doneRows = await card.locator('.km-daily-row.done').count();
  check('三行都显示为已击败', doneRows === 3, `${doneRows} 行`);
  await page.screenshot({ path: `${OUT}/C-weekly-cleared.png` });
  check('C 段无 JS 报错', errors.length === 0, errors.slice(0, 2).join(' | '));
  await ctx.close();
}

/* ═════════════════ D. 剧情页：幕 · 旁白 ═════════════════ */
{
  // 只让 archiveLine 那一章达成 100%，其余章节保持 0
  const runs = {
    [archiveLine.id]: { concept: 1, drill: 1, boss: 1, attempts: 1, lastAt: Date.now() },
  };
  const { ctx, page, errors } = await open(makeState({ chapterRuns: runs }), archiveLine.subject);

  await page.getByRole('button', { name: /剧情/ }).first().click();
  await page.waitForSelector('.km-acts', { timeout: 15000 });
  await page.waitForTimeout(300);

  const actsBlock = page.locator('.km-acts');
  check('剧情页出现「幕 · 旁白」区', (await actsBlock.count()) === 1);

  const chips = page.locator('.km-card', { hasText: '幕 · 旁白' }).locator('.km-chip');
  check('13 个学科可切换', (await chips.count()) === 13, `${await chips.count()} 个`);

  const pct = (await page.locator('.km-card', { hasText: '幕 · 旁白' }).locator('.pct').innerText()).trim();
  check(`解锁统计的分母是 ${storyTotal} 条台词`, pct.endsWith(`${storyTotal} 已解锁`), pct);

  // 已通关那一章的 archive 台词必须真的出现（说明可见性判的是掌握度而不是写死）
  const body = (await actsBlock.innerText()).replace(/\s+/g, ' ');
  const firstHalf = archiveLine.line.slice(0, 12);
  check('掌握度 100 的 archive 台词已解锁', body.includes(firstHalf), firstHalf);

  const lockedCount = await page.locator('.km-act-line.locked').count();
  check('未学过的 archive 仍为锁定态', lockedCount > 0, `${lockedCount} 条`);

  await page.screenshot({ path: `${OUT}/D-story-acts.png`, fullPage: false });
  check('D 段无 JS 报错', errors.length === 0, errors.slice(0, 2).join(' | '));
  await ctx.close();
}

/* ═════════════════ E. 学习页章节详情：本章旁白 ═════════════════ */
{
  const { ctx, page, errors } = await open(makeState(), teaserLine?.subject ?? 'data');
  await page.getByRole('button', { name: /知识试炼区/ }).first().click();
  await page.waitForSelector('.km-map', { timeout: 15000 });

  // 找含 pitfall 台词那一章的节点；该章若不在当前学科，退化为检查首章
  const title = teaserLine ? (chapterTitles[teaserLine.id] ?? '') : '';
  let node = page.locator('.km-node').filter({ hasText: title.slice(0, 6) }).first();
  if (!title || (await node.count()) === 0) node = page.locator('.km-node').first();
  await node.locator('.km-node-main').click();
  await page.waitForSelector('.km-chapter-open', { timeout: 8000 });
  await page.waitForTimeout(250);

  const lineBox = page.locator('.km-chapter-line');
  check('章节详情出现「本章旁白」块', (await lineBox.count()) === 1);
  if ((await lineBox.count()) === 1) {
    const text = (await lineBox.innerText()).replace(/\s+/g, ' ');
    check('旁白块带章节定位标记', /本章旁白|旁白未解锁/.test(text), text.slice(0, 30));
    if (teaserLine) {
      // pitfall 的卖点就是"没学过也能读"，这里验它真的没被 archive 的规则误伤
      check('pitfall 旁白在掌握度 0 时就可见', text.includes(teaserLine.line.slice(0, 10)), text.slice(0, 40));
    }
  }
  await page.screenshot({ path: `${OUT}/E-chapter-line.png` });
  check('E 段无 JS 报错', errors.length === 0, errors.slice(0, 2).join(' | '));
  await ctx.close();
}

await browser.close();

const failed = results.filter((r) => !r.ok);
console.log('\n' + '─'.repeat(60));
console.log(`${results.length - failed.length}/${results.length} 通过`);
if (failed.length) {
  console.log('失败明细：');
  for (const f of failed) console.log(`  · ${f.name}${f.detail ? ` — ${f.detail}` : ''}`);
  process.exitCode = 1;
}
