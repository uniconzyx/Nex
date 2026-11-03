/**
 * 手工精修模块验收（真浏览器 · Edge headless）
 *
 *   node viz/interactive/verify/verify_handmade.mjs http://localhost:5190
 *
 * 覆盖 sandbox / debug 两种"必须手写"的玩法：
 *
 *   sandbox  浏览器里把所有旋钮组合扫一遍，确认
 *            ① 开局不是已通关（否则一进来就"过关"，等于没玩）
 *            ② 存在一组参数让判据全绿（否则玩家拖到手抽筋也过不了）
 *            ③ 绿的那一刻 insight 真的出现（判据/文案没接错线）
 *   debug    症状条渲染、占位符与块数量对得上、错块拖进去不认、
 *            对块拖进去变成"编译通过 + 期望输出"
 *
 * 这套扫描和 scripts/audit_handmade_labs.py 用的是同一份数据、两套独立实现
 * （Python 一份、TS 一份）。两边结论一致才说明求值器没有语义漂移 ——
 * 只跑 Python 会漏掉"TS 里 log 没实现"这类事故。
 */
/* 依赖解析：优先 git 里的 playwright-core，其次本机全局装的 */
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
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

const BASE = process.argv[2] || 'http://localhost:5190';
const OUT = 'viz/interactive/.shots';
const R = {};

/** 挑几个有代表性的 sandbox 章：单旋钮 / 双旋钮 / 三旋钮 / 带离散档位 */
const SANDBOX = [
  'cpp/cpp-ch01', 'cpp/cpp-ch06', 'cpp/cpp-ch16', 'cpp/cpp-ch18',
  'fundamentals/fund-ch05', 'fundamentals/fund-ch08', 'fundamentals/fund-ch22',
];
/** debug：单空位、多空位、代码块里带 LaTeX/转义的情况 */
const DEBUG = ['cpp/cpp-ch09', 'cpp/cpp-ch14', 'cpp/cpp-ch02', 'fundamentals/fund-ch12'];

const browser = await chromium.launch({
  executablePath: EDGE,
  args: ['--headless=new', '--disable-gpu', '--no-proxy-server', '--proxy-bypass-list=*'],
});
const ctx = await browser.newContext({ viewport: { width: 1180, height: 1000 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
const http404 = [];
page.on('response', (r) => {
  if (r.status() >= 400) http404.push(`${r.status()} ${r.url()}`);
});
page.on('console', (m) => {
  // "Failed to load resource" 由上面的 response 钩子统一记（能拿到 URL），
  // 这里只收真正的脚本错 —— 否则 favicon 的 404 会以一行没 URL 的噪声混进来
  if (m.type() === 'error' && !/Failed to load resource/i.test(m.text())) errs.push('CONSOLE ' + m.text());
});

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
  await page.mouse.up();
  await page.waitForTimeout(120);
}

/* ═══════════════════ sandbox：旋钮全组合扫描 ═══════════════════ */

R.sandbox = {};
for (const key of SANDBOX) {
  // 只改 hash 不会重新加载：必须 reload，否则等到的是上一章的 DOM，
  // 断言就会拿 A 章的旋钮去评 B 章（第一版就是这么假通过的）
  await page.goto(`${BASE}/#/${key}`, { waitUntil: 'domcontentloaded' });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    (k) => !!document.querySelector(`[data-chapter="${k}"]`) && !!document.querySelector('[data-sandbox-params]'),
    key,
    { timeout: 15000 },
  );

  const res = await page.evaluate(async () => {
    // 两种旋钮都要认：连续量是 <input type=range>，离散档位是 data-param-opt 按钮
    const rows = [...document.querySelectorAll('[data-sandbox-params] [data-param-row]')];
    const kindOf = rows.map((r) => (r.querySelector('input[type=range]') ? 'range' : 'chips'));
    const axis = rows.map((r) => {
      const el = r.querySelector('input[type=range]');
      if (el) {
        const min = +el.min;
        const max = +el.max;
        const step = +el.step || 1;
        const out = [];
        for (let v = min; v <= max + 1e-9; v += step) out.push(+v.toFixed(6));
        return out;
      }
      return [...r.querySelectorAll('[data-param-opt]')].map((b) => +b.getAttribute('data-param-opt'));
    });
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    const setVal = (i, v) => {
      const row = rows[i];
      const el = row.querySelector('input[type=range]');
      if (el) {
        setter.call(el, String(v));
        el.dispatchEvent(new Event('input', { bubbles: true }));
      } else {
        row.querySelector(`[data-param-opt="${v}"]`).click();
      }
    };
    const passed = () => !!document.querySelector('[data-sandbox-insight]');
    const score = () => document.querySelector('[data-sandbox-score]')?.textContent || '';

    const defaultPass = passed();
    const defaultScore = score();

    // 组合全展开；超过 800 组就按"点最多的轴减半"抽样（与 python 守门同一策略）
    let axes = axis.map((a) => a.slice());
    const total = () => axes.reduce((n, a) => n * a.length, 1);
    while (total() > 800) {
      let worst = 0;
      for (let i = 1; i < axes.length; i++) if (axes[i].length > axes[worst].length) worst = i;
      if (axes[worst].length <= 2) break;
      axes[worst] = axes[worst].filter((_, i) => i % 2 === 0);
    }
    const combos = axes.reduce((acc, a) => acc.flatMap((p) => a.map((v) => [...p, v])), [[]]);

    let found = null;
    for (const c of combos) {
      c.forEach((v, i) => setVal(i, v));
      await new Promise((r) => setTimeout(r, 0));
      if (passed()) {
        found = c;
        break;
      }
    }
    return { defaultPass, defaultScore, found, combos: combos.length, axis, kindOf };
  });

  const ok = !res.defaultPass && !!res.found;
  R.sandbox[key] = { ...res, ok };
  if (key === 'cpp/cpp-ch18') {
    await page.screenshot({ path: `${OUT}/handmade-sandbox-cpp-ch18.png`, fullPage: false });
  }
  if (key === 'fundamentals/fund-ch05') {
    await page.screenshot({ path: `${OUT}/handmade-sandbox-fund-ch05.png`, fullPage: false });
  }
  console.log(
    `${ok ? '✓' : '✗'} sandbox ${key.padEnd(24)} 组合 ${String(res.combos).padStart(3)} 组 · ` +
      `开局「${res.defaultScore.trim()}」${res.defaultPass ? '（已通关，不合格）' : ''} · ` +
      `解 ${res.found ? JSON.stringify(res.found) : '（无解）'}`,
  );
}

/* ═══════════════════ debug：错块 → 对块 ═══════════════════ */

R.debug = {};
for (const key of DEBUG) {
  await page.goto(`${BASE}/#/${key}`, { waitUntil: 'domcontentloaded' });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(
    (k) => !!document.querySelector(`[data-chapter="${k}"]`) && !!document.querySelector('[data-debug-symptom]'),
    key,
    { timeout: 15000 },
  );

  const slots = await page.locator('[data-slot]').count();
  const blocks = await page.locator('[data-block]').count();

  // 先试一个干扰块，必须不被接受
  const wrongId = await page.evaluate(() => {
    const ok = document.querySelector('[data-block="b1"]');
    const other = [...document.querySelectorAll('[data-block]')].find((el) => el !== ok);
    return other?.getAttribute('data-block') || null;
  });
  if (wrongId) await dragTo(`[data-block="${wrongId}"]`, '[data-slot="s1"]');
  const wrongAccepted = (await page.locator('[data-slot="s1"][data-slot-ok="1"]').count()) > 0;

  await dragTo('[data-block="b1"]', '[data-slot="s1"]');
  const slotOk = (await page.locator('[data-slot="s1"][data-slot-ok="1"]').count()) > 0;
  const expectShown = (await page.locator('[data-debug-expect]').count()) > 0;
  const progress = (await page.locator('[data-debug-progress]').innerText()).trim();

  const ok = slots >= 1 && blocks >= 2 && !wrongAccepted && slotOk && expectShown;
  R.debug[key] = { slots, blocks, wrongId, wrongAccepted, slotOk, expectShown, progress, ok };
  if (key === 'cpp/cpp-ch09') {
    await page.screenshot({ path: `${OUT}/handmade-debug-cpp-ch09.png`, fullPage: false });
  }
  console.log(
    `${ok ? '✓' : '✗'} debug   ${key.padEnd(24)} ${slots} 空 / ${blocks} 块 · ` +
      `错块${wrongAccepted ? '竟然被接受' : '被拒'} · ${progress} · 期望输出${expectShown ? '已出现' : '缺失'}`,
  );
}

R.errs = errs;
R.http404 = http404.filter((x) => !/favicon/i.test(x));
R.pass =
  Object.values(R.sandbox).every((x) => x.ok) &&
  Object.values(R.debug).every((x) => x.ok) &&
  errs.length === 0 &&
  R.http404.length === 0;

console.log('\n' + JSON.stringify({ pass: R.pass, errs }, null, 1));
await browser.close();
process.exit(R.pass ? 0 : 1);
