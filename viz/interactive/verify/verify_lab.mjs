/**
 * 交互模块全量验收（真浏览器 · Edge headless）
 *
 *   node viz/interactive/verify/verify_lab.mjs http://localhost:5190
 *
 * 覆盖：
 *   ① 索引页 165 章
 *   ② 通用驱动版（database/db-ch02）：配对连线 → 真题打靶 → 代码挖空
 *   ③ 精修版（#/mw-ch04）：四个模块 + 延迟双删时序（拖 6 卡 → 回放 → 判定）
 *   ④ 错序必须判脏（不是"怎么排都过"）
 *   ⑤ 控制台零报错
 */
/* 依赖解析：优先用本机全局装的 playwright-core，其次项目 node_modules。
   Edge 路径可用 EDGE_PATH 覆盖（不同机器/CI 不一样）。 */
const _resolve = async () => {
  const hard = 'file:///C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core/index.mjs';
  for (const p of ['playwright-core', hard]) {
    try {
      return (await import(p)).chromium;
    } catch {
      /* 试下一个 */
    }
  }
  throw new Error('找不到 playwright-core：请 npm i -D playwright-core，或改本文件的 hard 路径');
};
const chromium = await _resolve();
export const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

const BASE = process.argv[2] || 'http://localhost:5190';
const OUT = 'viz/interactive/.shots';
const R = {};

const browser = await chromium.launch({
  executablePath: EDGE,
  args: ['--headless=new', '--disable-gpu', '--no-proxy-server', '--proxy-bypass-list=*'],
});
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
page.on('console', (m) => {
  if (m.type() === 'error' && !m.text().includes('404')) errs.push(m.text());
});

/** 真鼠标拖拽：分步移动，framer 才能收到连续的 pointermove */
async function dragTo(fromSel, toSel) {
  const a = await page.locator(fromSel).first().boundingBox();
  const b = await page.locator(toSel).first().boundingBox();
  if (!a || !b) throw new Error(`drag: 找不到 ${fromSel} 或 ${toSel}`);
  await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
  await page.mouse.down();
  for (let i = 1; i <= 12; i++) {
    await page.mouse.move(
      a.x + a.width / 2 + ((b.x + b.width / 2 - a.x - a.width / 2) * i) / 12,
      a.y + a.height / 2 + ((b.y + b.height / 2 - a.y - a.height / 2) * i) / 12,
    );
    await page.waitForTimeout(12);
  }
  await page.waitForTimeout(60);
  await page.mouse.up();
  await page.waitForTimeout(220);
}

/* ─────────────────── ① 索引页 ─────────────────── */
await page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
await page.waitForTimeout(400);
R.indexCards = await page.locator('[data-index-card]').count();
R.indexHasMw = (await page.locator('[data-index-card="middleware/mw-ch04"]').count()) > 0;
await page.screenshot({ path: `${OUT}/20-index.png`, fullPage: true });

/* ─────────────────── ② 通用驱动版 db-ch02 ─────────────────── */
await page.goto(`${BASE}/#/database/db-ch02`, { waitUntil: 'networkidle' });
await page.waitForSelector('[data-lab-tabs]', { timeout: 10000 });
await page.waitForTimeout(400);
R.genericTitle = (await page.locator('[data-lab-title]').first().innerText()).trim();
R.genericTitleOk = R.genericTitle.length >= 4;
R.genericTabs = await page.locator('[data-lab-tab]').count();

// 配对连线：id 相同即正确配对
const pairCount = await page.locator('[data-pair-left]').count();
for (let i = 1; i <= pairCount; i++) {
  await page.locator(`[data-pair-left="${i}"]`).click();
  await page.waitForTimeout(90);
  await page.locator(`[data-pair-right="${i}"]`).click();
  await page.waitForTimeout(140);
}
R.matchDone = (await page.locator('text=全部配对完成').count()) > 0;
R.matchLines = await page.locator('svg path[stroke="#31D0AA"]').count();
await page.screenshot({ path: `${OUT}/21-generic-match.png`, fullPage: true });

// 真题打靶
await page.locator('[data-lab-tab="boss"]').click();
await page.waitForTimeout(400);
const armor0 = await page.locator('[data-armor]').getAttribute('data-armor');
// db-ch02 首题答案是 B（key 跟文本走，洗牌后 key 不变）
await page.locator('[data-opt="B"]').click();
await page.waitForTimeout(500);
const armor1 = await page.locator('[data-armor]').getAttribute('data-armor');
R.bossArmor = `${armor0}->${armor1}`;
R.bossHit = Number(armor1) < Number(armor0);
R.bossExplain = (await page.locator('text=解析').count()) > 0;
await page.screenshot({ path: `${OUT}/22-generic-boss.png`, fullPage: true });

// 代码挖空（db-ch02: dept → b1, salary → b2）
await page.locator('[data-lab-tab="fill"]').click();
await page.waitForTimeout(400);
await dragTo('[data-token="dept"]', '[data-blank="b1"]');
await dragTo('[data-token="salary"]', '[data-blank="b2"]');
await page.waitForTimeout(300);
R.fillProgress = await page.locator('[data-fill-progress]').innerText().catch(() => '');
R.fillDone = (await page.locator('text=全部归位').count()) > 0;
await page.screenshot({ path: `${OUT}/23-generic-fill.png`, fullPage: true });

/* ─────────────────── ③ 精修版 mw-ch04 时序模块 ─────────────────── */
await page.goto(`${BASE}/#/mw-ch04`, { waitUntil: 'networkidle' });
await page.waitForSelector('.kmlab', { timeout: 10000 });
await page.waitForTimeout(400);
R.refinedTabs = await page.locator('.kmlab button').filter({ hasText: '时序连线' }).count();
await page.locator('.kmlab button', { hasText: '时序连线' }).first().click();
await page.waitForTimeout(600);
R.ddSlots = await page.locator('[data-dd-slot]').count();
R.ddCards = await page.locator('[data-dd-card]').count();

// 正确时序：卡 1..6 → 槽 0..5（干扰卡 9 不放入）
for (let i = 1; i <= 6; i++) {
  await dragTo(`[data-dd-card="${i}"]`, `[data-dd-slot="${i - 1}"]`);
}
await page.waitForTimeout(300);
R.ddFilled = await page.locator('[data-dd-slot][data-dd-filled="1"]').count();
await page.screenshot({ path: `${OUT}/24-dd-arranged.png`, fullPage: true });

await page.locator('[data-dd-run]').click();
await page.waitForTimeout(4600);
const txt = await page.locator('.kmlab').innerText();
R.ddOk = txt.includes('时序正确');
R.ddHealed = txt.includes('自愈');
R.ddFinalCache = await page.locator('.kmlab').innerText().then((t) => /CACHE\s*(v\d|∅)/.exec(t)?.[1] || '');
await page.screenshot({ path: `${OUT}/25-dd-passed.png`, fullPage: true });

/* ─────────────────── ④ 错序必须判脏 ─────────────────── */
await page.locator('.kmlab button', { hasText: '重来' }).first().click();
await page.waitForTimeout(400);
// 把「A 更新库」提前到第一格（最容易犯的错），其余按原序
await dragTo('[data-dd-card="3"]', '[data-dd-slot="0"]');
await dragTo('[data-dd-card="1"]', '[data-dd-slot="1"]');
await dragTo('[data-dd-card="2"]', '[data-dd-slot="2"]');
await dragTo('[data-dd-card="4"]', '[data-dd-slot="3"]');
await dragTo('[data-dd-card="5"]', '[data-dd-slot="4"]');
await dragTo('[data-dd-card="6"]', '[data-dd-slot="5"]');
await page.waitForTimeout(200);
await page.locator('[data-dd-run]').click();
await page.waitForTimeout(4600);
const txt2 = await page.locator('.kmlab').innerText();
R.ddWrongDetected = txt2.includes('错位') || txt2.includes('顺序错了');
R.ddWrongNotPass = !txt2.includes('时序正确');
await page.screenshot({ path: `${OUT}/26-dd-wrong.png`, fullPage: true });

/* ─────────────────── ⑤ 其余三个精密模块仍在 ─────────────────── */
await page.locator('.kmlab button', { hasText: '沙盒推演' }).first().click();
await page.waitForTimeout(500);
R.sandboxAlive = (await page.locator('input[type=range]').count()) > 0;
await page.locator('.kmlab button', { hasText: '代码 Debug' }).first().click();
await page.waitForTimeout(500);
R.debugAlive = (await page.locator('[data-block]').count()) > 0;
await page.locator('.kmlab button', { hasText: '闯关试炼' }).first().click();
await page.waitForTimeout(500);
const bossTxt = await page.locator('.kmlab').innerText();
R.bossAlive = /Q\d\/\d/.test(bossTxt) && /HP\s*\d\/\d/.test(bossTxt);

/* ─────────────────── ⑥ 窄屏不溢出 ─────────────────── */
await page.setViewportSize({ width: 420, height: 900 });
await page.goto(`${BASE}/#/database/db-ch02`, { waitUntil: 'networkidle' });
await page.waitForSelector('[data-lab-tabs]', { timeout: 10000 });
await page.waitForTimeout(500);
R.narrowOverflow = await page.evaluate(
  () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
);
await page.screenshot({ path: `${OUT}/27-narrow.png`, fullPage: true });

R.pass =
  R.indexCards === 165 &&
  R.genericTitleOk &&
  R.matchDone &&
  R.matchLines >= 4 &&
  R.bossHit &&
  R.fillDone &&
  R.ddFilled === 6 &&
  R.ddOk &&
  R.ddHealed &&
  R.ddWrongDetected &&
  R.ddWrongNotPass &&
  R.sandboxAlive &&
  R.debugAlive &&
  R.bossAlive &&
  R.narrowOverflow <= 1 &&
  errs.length === 0;

R.errors = errs.slice(0, 6);
console.log(JSON.stringify(R, null, 2));
await browser.close();
process.exit(R.pass ? 0 : 1);
