// logic_chain_checks.ts —— 游戏逻辑链「严密性」断言入口
// ============================================================================
// 本文件被 scripts/verify_logic_chain.mjs 通过 esbuild 打包后由 node 直接执行。
// 它驱动 lib/logicChain.ts 的三个纯函数，验证「严密性」地基在运行时行为正确：
//
//   1) dependencyIssues()        —— 依赖图无环 / 无悬空 / 无自环
//   2) stateViolations(empty)    —— 干净进度不应有任何不变量违例
//   3) isUnlocked()              —— 根章解锁、未达标前置的章锁定
//   4) stateViolations(dirty)    —— 前置 0 却标 100 的脏数据必须被抓到
//
// 任何一条不过就 process.exit(1)，与 audit_graph.py / verify_p2.mjs 同一套守门哲学。
// ============================================================================
import { dependencyIssues, stateViolations, isUnlocked } from '../frontend/src/lib/logicChain';
import { allChapters, chapterDeps, masteryOfChapter, UNLOCK_MASTERY } from '../frontend/src/lib/graph';
import type { ProgressState } from '../frontend/src/lib/gameTypes';

function emptyState(): ProgressState {
  return {
    theme: 'light',
    outfit: '',
    doneProjects: [],
    doneChapters: [],
    checkins: [],
    coins: 0,
    coinLedger: [],
    bestiary: {},
    chapterRuns: {},
    answers: {},
    daily: null,
    shards: 0,
  } as ProgressState;
}

let fail = 0;
const assert = (cond: boolean, msg: string) => {
  if (!cond) {
    fail++;
    console.error('  ✗ ' + msg);
  } else {
    console.log('  ✓ ' + msg);
  }
};

console.log('[1] 依赖图完整性（dependencyIssues）');
const issues = dependencyIssues();
assert(
  issues.length === 0,
  `依赖图无环/无悬空/无自环（实际 ${issues.length} 个问题）${issues.length ? JSON.stringify(issues.slice(0, 3)) : ''}`,
);

console.log('[2] 干净状态下不变量（stateViolations）');
const empty = emptyState();
const v = stateViolations(empty);
assert(v.length === 0, `空进度不应有违例（实际 ${v.length} 条）${v.length ? JSON.stringify(v.slice(0, 3)) : ''}`);

console.log('[3] isUnlocked 单一事实来源');
const all = allChapters();
const root = all.find((c) => chapterDeps(c.id).length === 0);
assert(!!root, '存在无依赖的根章节');
if (root) assert(isUnlocked(root.id, empty), `${root.id} 无前置 → 应解锁`);
const leaf = all.find((c) => chapterDeps(c.id).length > 0);
assert(!!leaf, '存在有依赖的章节');
if (leaf) {
  assert(!isUnlocked(leaf.id, empty), `${leaf.id} 前置未达标 → 应锁定`);
  const blocking = chapterDeps(leaf.id).filter((d) => masteryOfChapter(d, empty) < UNLOCK_MASTERY);
  assert(blocking.length > 0, `${leaf.id} 应有 ${blocking.length} 条未达标前置`);
}

console.log('[4] 反例：前置 0 却标记掌握 100 → 应被 stateViolations 抓到');
const dirty = emptyState();
if (leaf) {
  dirty.doneChapters = [leaf.id];
  const vv = stateViolations(dirty);
  assert(
    vv.some((x) => x.rule === 'prereq' || x.rule === 'done⇒mastery100'),
    '脏数据触发 prereq/done 违例',
  );
}

console.log(fail === 0 ? '\nLOGIC_CHAIN_OK' : `\nLOGIC_CHAIN_FAIL (${fail})`);
if (fail > 0) process.exit(1);
