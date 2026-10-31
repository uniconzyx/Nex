/**
 * _probe_badge.mjs —— 探针：打印 data 学科「NumPy 进阶」节点上
 * .km-tag-gray 徽章的真实合成背景色，并就地试验若干候选文字色，
 * 看哪个在深浅两套主题下都能过 4.5:1。
 */
import { createRequire } from 'module';
import { mkdirSync } from 'fs';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/zyx/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = 'http://127.0.0.1:1420/';
const ROOT = 'D:/WB_Workspace/2026-09-19-21-42-03/CppMind';
const OUT = `${ROOT}/scratch/p2-shots`;
mkdirSync(OUT, { recursive: true });

const src = require('fs').readFileSync(`${ROOT}/frontend/src/data/exercises.ts`, 'utf8');
const marker = 'export const EXERCISES: BankExercise[] = ';
const arr = JSON.parse(src.slice(src.indexOf('[', src.indexOf(marker) + marker.length), src.lastIndexOf(']') + 1));
const CH = 'data-ch02';
const LIST = arr.filter((e) => e.ch === CH);
const today = (() => { const d = new Date(); const p = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; })();

function makeState(theme) {
  const answers = {};
  const DRILL = new Set(['coding', 'output', 'fix_error', 'design']);
  const concept = LIST.find((e) => e.type === 'choice' || e.type === 'explain');
  const drills = LIST.filter((e) => DRILL.has(e.type)).slice(0, 3);
  for (const e of [concept, ...drills]) answers[e.id] = { chapterId: CH, ok: true, at: Date.now() };
  return { theme, outfit: 'default', doneProjects: [], doneChapters: [], checkins: [], coins: 1280, coinLedger: [], bestiary: {}, chapterRuns: {}, answers, daily: { date: today, qids: LIST.slice(0, 3).map((e) => e.id), done: [LIST[0].id], correct: [LIST[0].id], claimed: false }, shards: 0 };
}

const hex2rgb = (h) => { const n = parseInt(h.slice(1), 16); return `rgb(${(n>>16)&255},${(n>>8)&255},${n&255})`; };
const CANDIDATES = {
  light: ['#3c4d61', '#37485c', '#33485d', '#2f4357', '#3a4b5e'].map(hex2rgb),
  dark: ['#d8e6f2', '#e0ebf5', '#e6eef6', '#cfe0ef', '#f0f5fa'].map(hex2rgb),
};

const PROBE = `(sel, cand) => {
  const parse = (c) => { if(!c) return null; const m = c.match(/rgba?\\\\(([^)]+)\\\\)/); if(!m) return null; const p = m[1].split(/[,\\\\s/]+/).filter(Boolean).map(Number); return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}; };
  const safe = (c) => parse(c) || {r:0,g:0,b:0,a:0};
  const over = (fg,bg) => ({ r: fg.r*fg.a+bg.r*(1-fg.a), g: fg.g*fg.a+bg.g*(1-fg.a), b: fg.b*fg.a+bg.b*(1-fg.a), a:1 });
  const lum = ({r,g,b}) => { const f=(v)=>{v/=255; return v<=0.03928? v/12.92: Math.pow((v+0.055)/1.055,2.4);}; return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b); };
  const bgOf = (el) => { const stack=[]; let node=el; while(node){ const c=parse(getComputedStyle(node).backgroundColor); if(c&&c.a>0) stack.push(c); if(c&&c.a>=0.999) break; node=node.parentElement; } let base={r:255,g:255,b:255,a:1}; for(let i=stack.length-1;i>=0;i--) base=over(stack[i],base); return base; };
  const el = document.querySelector(sel);
  if(!el) return { missing:true };
  const bg = bgOf(el);
  const realColor = getComputedStyle(el).color;
  const out = { realColor, bgStack: (()=>{ const s=[]; let n=el; while(n){ const cc=getComputedStyle(n).backgroundColor; if(cc&&cc!=='rgba(0, 0, 0, 0)') s.push(cc); n=n.parentElement; } return s.slice(0,6); })(), bg: \`rgb(\${Math.round(bg.r)},\${Math.round(bg.g)},\${Math.round(bg.b)})\` };
  const ratioFor = (col) => {
    const fc = safe(col); const f = over(fc, bg);
    const l1 = lum(f)+0.05, l2 = lum(bg)+0.05;
    return Math.round((l1>l2? l1/l2 : l2/l1)*100)/100;
  };
  out.realRatio = ratioFor(realColor);
  out.cands = cand.map((c)=>({ c, ratio: ratioFor(c) }));
  return out;
}`;

const browser = await chromium.launch({ executablePath: EDGE, headless: true, args: ['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'] });
for (const theme of ['light','dark']) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await ctx.newPage();
  await page.addInitScript((payload) => {
    if (sessionStorage.getItem('__km_c')) return;
    sessionStorage.setItem('__km_c','1');
    for (const k of Object.keys(localStorage)) if (k.startsWith('kaimao.')||k.startsWith('nex.')) localStorage.removeItem(k);
    localStorage.setItem('kaimao.progress.v2', JSON.stringify(payload.state));
    localStorage.setItem('nex.subject','data');
  }, { state: makeState(theme) });
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.km-app', { timeout: 20000 });
  await page.waitForTimeout(500);
  await page.getByRole('button', { name: /知识试炼区/ }).first().click();
  await page.waitForSelector('.km-map', { timeout: 15000 });
  await page.locator('.km-node').filter({ hasText: 'NumPy 进阶' }).first().locator('.km-node-main').click();
  await page.waitForSelector('.km-stages', { timeout: 8000 });
  await page.waitForTimeout(400);
  const r = await page.evaluate(`(${PROBE})('.km-node .km-tag-gray', ${JSON.stringify(CANDIDATES[theme])})`);
  console.log(`\n=== ${theme} ===`);
  console.log('  real color:', r.realColor, ' synthesized bg:', r.bg, ' realRatio:', r.realRatio);
  for (const c of r.cands) console.log(`  cand ${c.c} -> ${c.ratio}:1 ${c.ratio>=4.5?'OK':'XX'}`);
  await ctx.close();
}
await browser.close();
