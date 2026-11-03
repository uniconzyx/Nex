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

const b = await chromium.launch({
  executablePath: EDGE,
  args: ['--headless=new', '--disable-gpu', '--no-proxy-server'],
});
const keys = [
  'fundamentals/fund-ch01', 'cpp/cpp-ch01', 'java/java-ch08', 'ml/ml-ch05',
  'data/data-ch02', 'ai/ai-ch06', 'fullstack/fs-ch02', 'database/db-ch05',
];
const out = [];
for (const vw of [1280, 420]) {
  const ctx = await b.newContext({ viewport: { width: vw, height: 900 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  for (const k of keys) {
    await p.goto('http://localhost:5190/#/' + k, { waitUntil: 'networkidle' });
    await p.waitForSelector('[data-page="chapter"] .kmlab', { timeout: 10000 });
    await p.waitForTimeout(350);
    const tabs = await p
      .locator('[data-lab-tab]')
      .evaluateAll((e) => e.map((x) => x.getAttribute('data-lab-tab')));
    let worst = await p.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    for (const t of tabs) {
      await p.locator(`[data-lab-tab="${t}"]`).click();
      await p.waitForTimeout(280);
      const o = await p.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (o > worst) worst = o;
    }
    out.push({ k, vw, overflow: worst, tabs: tabs.join(',') });
    if (vw === 1280) {
      await p.screenshot({ path: 'viz/interactive/.shots/lab-' + k.split('/').join('__') + '.png', fullPage: true });
    }
  }
  out.push({ vw, errs });
  await ctx.close();
}
console.log(JSON.stringify(out, null, 1));
await b.close();
