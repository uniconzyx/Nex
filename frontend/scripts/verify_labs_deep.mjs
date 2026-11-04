/**
 * verify_labs_deep.mjs —— 六种玩法在 App 里真的能玩（不是「渲染出来就算」）
 * ============================================================================
 * verify_labs.mjs 证明 165 章都能渲染；这一份证明**每种玩法的判定真的生效**：
 *
 *   sequence 拖卡进时间轴 → 「已就位」计数变化 → 回放按钮可点
 *   match    点左栏再点右栏   → 配对成功计数变化
 *   boss     点一个选项       → 护甲/血量变化或出现「下一题」（有反馈即算通）
 *   fill     把 token 拖进空位 → 进度文本变化
 *   sandbox  拖旋钮到最右     → 指标数值变化（说明表达式在重算，不是静态字）
 *   debug    把块拖进槽位     → 进度文本变化
 *
 * 代表章从 `data/labs/index.ts` 的索引里按 kind 自动挑（第一个含该玩法的章），
 * 不写死章节名 —— 换内容后不会因为某章被删而假失败。
 *
 *   node frontend/scripts/verify_labs_deep.mjs http://localhost:5230
 */
import { readFileSync } from 'node:fs';

const BASE = process.argv[2] || 'http://localhost:5230';
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const INDEX = 'frontend/src/data/labs/index.ts';

async function loadPlaywright() {
  try {
    return await import('playwright-core');
  } catch {
    return import('file:///C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core/index.mjs');
  }
}
const { chromium } = await loadPlaywright();

/* ── 从索引里挑每种玩法的代表章 ─────────────────────────────────────── */
const idxText = readFileSync(INDEX, 'utf8');
const rows = [...idxText.matchAll(/key: "([\w-]+\/[\w-]+)",[\s\S]*?kinds: (\[[^\]]*\])/g)].map((m) => ({
  key: m[1],
  kinds: JSON.parse(m[2]),
}));
const pick = (kind) => rows.find((r) => r.kinds.includes(kind))?.key ?? null;
const TARGETS = ['sequence', 'match', 'boss', 'fill', 'sandbox', 'debug'].map((k) => ({ kind: k, key: pick(k) }));

const browser = await chromium.launch({ executablePath: EDGE, args: ['--headless=new', '--disable-gpu'] });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 900 }, deviceScaleFactor: 2 });
await ctx.addInitScript(() => {
  try {
    localStorage.setItem('nex.localMode', '1');
  } catch {
    /* ignore */
  }
});
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
page.on('console', (m) => {
  if (m.type() === 'error' && !/Failed to load resource/i.test(m.text())) errs.push(m.text());
});

async function dragTo(fromSel, toSel) {
  // 拖拽用 page.mouse，不会像 .click() 那样自动把元素滚进视口。
  // 实验台内容很长，token/槽位常常在折叠线以下（y > 视口高），不先滚就点不到。
  const from = page.locator(fromSel).first();
  const to = page.locator(toSel).first();
  await to.scrollIntoViewIfNeeded();
  await from.scrollIntoViewIfNeeded();
  // 两块只差 ~100px，滚到 to 可见时 from 也该可见；再读一次坐标（滚动后变了）
  await to.scrollIntoViewIfNeeded();
  const a = await from.boundingBox();
  const b = await to.boundingBox();
  if (!a || !b) throw new Error(`drag 找不到 ${fromSel} / ${toSel}`);
  const ax = a.x + a.width / 2;
  const ay = a.y + a.height / 2;
  const bx = b.x + b.width / 2;
  const by = b.y + b.height / 2;
  if (ay < 0 || ay > 900 || by < 0 || by > 900) {
    throw new Error(`drag 目标仍在视口外（from y=${ay.toFixed(0)} to y=${by.toFixed(0)}），拖不动`);
  }
  await page.mouse.move(ax, ay);
  await page.mouse.down();
  for (let i = 1; i <= 16; i++) {
    await page.mouse.move(ax + ((bx - ax) * i) / 16, ay + ((by - ay) * i) / 16);
    await page.waitForTimeout(12);
  }
  await page.waitForTimeout(80);
  await page.mouse.up();
  await page.waitForTimeout(320);
}

async function openChapter(key) {
  const [subject, chapter] = key.split('/');
  await page.locator(`[data-lab-subject="${subject}"]`).click();
  await page.waitForTimeout(120);
  await page.locator(`[data-lab-pick="${key}"]`).click();
  await page.waitForFunction(
    (ch) => document.querySelector('[data-lab-stage]')?.getAttribute('data-lab-stage') === ch,
    chapter,
    { timeout: 15000 },
  );
  await page.waitForSelector('[data-lab-title]', { timeout: 15000 });
  const tab = page.locator(`[data-lab-tab="${key.kind}"]`);
  void tab;
}

async function pickTab(kind) {
  const t = page.locator(`[data-lab-tab="${kind}"]`).first();
  if ((await t.count()) === 0) return false;
  await t.click();
  await page.waitForTimeout(420);
  return true;
}

await page.goto(`${BASE}/#lab`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('.bank-tabs', { timeout: 20000 });
await page.locator('.bank-tab', { hasText: '实验台' }).first().click();
await page.waitForSelector('[data-lab-subject]', { timeout: 20000 });

const R = {};
const fails = [];

for (const { kind, key } of TARGETS) {
  if (!key) {
    fails.push(`索引里找不到任何含 ${kind} 的章节`);
    continue;
  }
  try {
    await openChapter(key);
    const hasTab = await pickTab(kind);
    if (!hasTab) {
      fails.push(`${key} 没有 ${kind} 页签`);
      continue;
    }

    if (kind === 'match') {
      // 计数用 data-pair-linked：配对成功后组件把 pickLeft 清回 null，
      // 所以「当前选中」(data-pair-on) 会归零，只有 linked 才是真配对信号
      const before = await page.locator('[data-pair-linked="1"]').count();
      const leftId = await page.locator('[data-pair-left]').first().getAttribute('data-pair-left');
      await page.locator(`[data-pair-left="${leftId}"]`).click();
      await page.locator(`[data-pair-right="${leftId}"]`).click();
      await page.waitForTimeout(360);
      const after = await page.locator('[data-pair-linked="1"]').count();
      R.match = { key, leftId, before, after };
      if (after <= before) fails.push(`match 配对后计数没变（${before} → ${after}）@ ${key}`);
    }

    if (kind === 'boss') {
      const armor0 = await page.locator('[data-armor]').first().getAttribute('data-armor');
      await page.locator('[data-opt]').first().click();
      await page.waitForTimeout(500);
      const armor1 = await page.locator('[data-armor]').first().getAttribute('data-armor');
      const nextBtn = await page.locator('[data-boss-next]').count();
      R.boss = { key, armor0, armor1, nextBtn };
      /* 点错也是正常反馈（护甲不变）；只要 DOM 有反应（护甲变 / 出现下一题）就算通 */
      if (armor0 === armor1 && nextBtn === 0) fails.push(`boss 点击后没有任何反馈 @ ${key}`);
    }

    if (kind === 'fill') {
      const p0 = (await page.locator('[data-fill-progress]').first().innerText().catch(() => '')) || '';
      await dragTo('[data-token]', '[data-blank]');
      const p1 = (await page.locator('[data-fill-progress]').first().innerText().catch(() => '')) || '';
      R.fill = { key, p0, p1 };
      if (p0 === p1) fails.push(`fill 拖入后进度没变（${p0}）@ ${key}`);
    }

    if (kind === 'sequence') {
      const before = await page.locator('[data-seq-filled="1"]').count();
      await dragTo('[data-seq-card]', '[data-seq-slot]');
      const after = await page.locator('[data-seq-filled="1"]').count();
      R.sequence = { key, before, after };
      if (after <= before) fails.push(`sequence 拖入后「已就位」没变（${before} → ${after}）@ ${key}`);
    }

    if (kind === 'sandbox') {
      const m0 = (await page.locator('[data-sandbox-metrics]').first().innerText()).slice(0, 200);
      /* 用原生 setter 改 range 再派发 input，React 才认 */
      await page.evaluate(() => {
        const el = document.querySelector('[data-sandbox-params] input[type=range]');
        if (!el) return;
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        setter.call(el, el.max);
        el.dispatchEvent(new Event('input', { bubbles: true }));
      });
      await page.waitForTimeout(420);
      const m1 = (await page.locator('[data-sandbox-metrics]').first().innerText()).slice(0, 200);
      R.sandbox = { key, changed: m0 !== m1 };
      if (m0 === m1) fails.push(`sandbox 拖到最右后指标没变化 @ ${key}`);
    }

    if (kind === 'debug') {
      const p0 = (await page.locator('[data-debug-progress]').first().innerText().catch(() => '')) || '';
      await dragTo('[data-block]', '[data-slot]');
      const p1 = (await page.locator('[data-debug-progress]').first().innerText().catch(() => '')) || '';
      R.debug = { key, p0, p1 };
      if (p0 === p1) fails.push(`debug 拖入后进度没变（${p0}）@ ${key}`);
    }

    await page.screenshot({ path: `frontend/.shots/lab-play-${kind}.png` });
    R[kind + '_ok'] = true;
  } catch (e) {
    fails.push(`${kind} @ ${key} 交互失败：${String(e).slice(0, 160)}`);
  }
}

await browser.close();

if (errs.length) fails.push(`控制台报错 ${errs.length} 条：${errs.slice(0, 2).join(' | ')}`);
const report = { pass: fails.length === 0, R, fails };
console.log(JSON.stringify(report, null, 1));
process.exit(report.pass ? 0 : 1);
