import { readFileSync } from 'fs';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

const src = readFileSync('D:/WB_Workspace/2026-09-19-21-42-03/CppMind/frontend/src/data/exercises.ts', 'utf8');
const mi = src.indexOf('EXERCISES: BankExercise[] =');
let i = src.indexOf('[', src.indexOf('=', mi)), depth = 0, inStr = false, esc = false, start = i, end = -1;
for (; i < src.length; i++) {
  const ch = src[i];
  if (inStr) { if (esc) esc = false; else if (ch === '\\') esc = true; else if (ch === '"') inStr = false; continue; }
  if (ch === '"') { inStr = true; continue; }
  if (ch === '[') depth++;
  else if (ch === ']') { depth--; if (depth === 0) { end = i; break; } }
}
const list = JSON.parse(src.slice(start, end + 1));

const cc = list.filter((e) => e.lang === 'cpp' || e.lang === 'c');
console.log('cpp/c 总数:', cc.length);
console.log('cpp/c 按 type:', JSON.stringify(cc.reduce((a, e) => { a[e.type] = (a[e.type] || 0) + 1; return a; }, {})));

const byTypeCases = (t) => cc.filter((e) => e.type === t && Array.isArray(e.cases) && e.cases.length > 0);
for (const t of ['coding', 'fix_error', 'output']) {
  const xs = byTypeCases(t);
  console.log(`cpp/c ${t} 带 cases:`, xs.length, '| 其中有 code:', xs.filter((e) => e.code).length);
}

// 能「去判题台」的 cpp/c 题：codeLike = (coding||fix_error) && code，且带 cases
const usable = cc.filter((e) => (e.type === 'coding' || e.type === 'fix_error') && e.code && Array.isArray(e.cases) && e.cases.length > 0);
console.log('cpp/c 可去判题台(带code+cases):', usable.length);
if (usable[0]) console.log('  示例:', JSON.stringify({ id: usable[0].id, type: usable[0].type, cases: usable[0].cases.length, title: usable[0].title }));

// 兜底：任意带 cases 的 coding 题（可能 python），进判题台后切 cpp
const anyCoding = list.filter((e) => (e.type === 'coding' || e.type === 'fix_error') && e.code && Array.isArray(e.cases) && e.cases.length > 0);
console.log('任意语言 可去判题台(带code+cases):', anyCoding.length, '| 其中 python:', anyCoding.filter((e) => e.lang === 'python').length);
