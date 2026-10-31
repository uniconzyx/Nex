import { createRequire } from 'module';
import { mkdirSync } from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:1420/';
const ROOT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind';
mkdirSync(`${ROOT}/scratch/p2-shots`, { recursive: true });
const src = require('fs').readFileSync(`${ROOT}/frontend/src/data/exercises.ts`, 'utf8');
const marker = 'export const EXERCISES: BankExercise[] = ';
const arr = JSON.parse(src.slice(src.indexOf('[', src.indexOf(marker) + marker.length), src.lastIndexOf(']') + 1));
const CH = 'data-ch02';
const LIST = arr.filter((e) => e.ch === CH);
const today = (() => { const d = new Date(); const p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`; })();
function makeState(theme){ const answers={}; const DRILL=new Set(['coding','output','fix_error','design']); const concept=LIST.find(e=>e.type==='choice'||e.type==='explain'); const drills=LIST.filter(e=>DRILL.has(e.type)).slice(0,3); for(const e of [concept,...drills]) answers[e.id]={chapterId:CH,ok:true,at:Date.now()}; return {theme,outfit:'default',doneProjects:[],doneChapters:[],checkins:[],coins:1280,coinLedger:[],bestiary:{},chapterRuns:{},answers,daily:{date:today,qids:LIST.slice(0,3).map(e=>e.id),done:[LIST[0].id],correct:[LIST[0].id],claimed:false},shards:0}; }
const PROBE = `(sel) => {
  const el = document.querySelector(sel);
  if (!el) return { missing: true };
  const chain = [];
  let n = el;
  while (n && chain.length < 8) { chain.push({ cls: n.className && n.className.toString ? n.className.toString() : (n.tagName||''), color: getComputedStyle(n).color }); n = n.parentElement; }
  return { matchedClass: el.className && el.className.toString ? el.className.toString() : el.tagName, ownColor: getComputedStyle(el).color, chain };
}`;
const browser = await chromium.launch({ executablePath: EDGE, headless: true, args: ['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'] });
for (const theme of ['light','dark']) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await ctx.newPage();
  await page.addInitScript((payload) => { if (sessionStorage.getItem('__km_c')) return; sessionStorage.setItem('__km_c','1'); for (const k of Object.keys(localStorage)) if (k.startsWith('kaimao.')||k.startsWith('nex.')) localStorage.removeItem(k); localStorage.setItem('kaimao.progress.v2', JSON.stringify(payload.state)); localStorage.setItem('nex.subject','data'); }, { state: makeState(theme) });
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-app', { timeout: 20000 });
  await page.waitForTimeout(500);
  await page.getByRole('button', { name: /知识试炼区/ }).first().click();
  await page.waitForSelector('.km-map', { timeout: 15000 });
  await page.locator('.km-node').filter({ hasText: 'NumPy 进阶' }).first().locator('.km-node-main').click();
  await page.waitForSelector('.km-stages', { timeout: 8000 });
  await page.waitForTimeout(400);
  const r = await page.evaluate(`(${PROBE})('.km-node .km-tag-gray')`);
  console.log(`\n=== ${theme} ===`);
  console.log('matched:', r.matchedClass, '| own color:', r.ownColor);
  for (const c of (r.chain||[])) console.log('  anc:', JSON.stringify(c.cls).slice(0,70), '| color:', c.color);
  await ctx.close();
}
await browser.close();
