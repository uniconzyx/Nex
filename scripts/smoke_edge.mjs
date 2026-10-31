import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

const b = await chromium.launch({
  executablePath: EDGE,
  headless: true,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
});
const p = await b.newPage();
await p.goto('about:blank');
console.log('blank title:', JSON.stringify(await p.title()));
// 顺手验证能否访问我们的 dev server（同源/跨域都行，这里只测可达性）
try {
  const resp = await p.goto('http://127.0.0.1:5173/', { waitUntil: 'domcontentloaded', timeout: 15000 });
  console.log('dev server status:', resp && resp.status());
} catch (e) {
  console.log('dev server reach ERR:', e.message);
}
await b.close();
console.log('SMOKE_OK');
