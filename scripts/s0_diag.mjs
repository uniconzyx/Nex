import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const b = await chromium.launch({ executablePath: EDGE, headless: true, args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'] });
const page = await b.newPage({ viewport: { width: 820, height: 900 } });
await page.goto('http://127.0.0.1:1420/', { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForSelector('.ai-fab', { state: 'attached' });
const info = await page.$eval('.ai-fab', (el) => {
  const cs = getComputedStyle(el);
  return {
    n: document.querySelectorAll('.ai-fab').length,
    cls: el.className,
    display: cs.display,
    boxShadow: cs.boxShadow,
    shadowProp: cs.getPropertyValue('--km-sh-pop'),
    glowProp: cs.getPropertyValue('--km-glow'),
    lineProp: cs.getPropertyValue('--km-line'),
    sheetShadow: getComputedStyle(document.querySelector('.km-sheet') || document.body).boxShadow,
  };
});
console.log(JSON.stringify(info, null, 2));
await b.close();
