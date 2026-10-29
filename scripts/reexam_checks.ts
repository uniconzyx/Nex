// reexam_checks.ts —— P6 考研复试板块 断言入口
// ============================================================================
// 被 scripts/verify_logic_chain.mjs --check-reexam 通过 esbuild 打包后由 node 执行。
// 驱动 lib/reexam.ts，验证：
//   1) buildReexamView 面试分类数 / 面试题总数 / 机试题数 / 高校数 / 模块数
//   2) 机试题三层答案齐全（framework/algorithm/code 均非空）
//   3) 每题附工作场景（scene 非空），且关联模块非空
//   4) 面试每类有 desc + 至少 1 题，每题有 tip（导师视角）
//   5) markdown 导出不抛错
// 任意断言失败 → process.exit(1)。
// ============================================================================
import { buildReexamView, reexamToMarkdown } from '../frontend/src/lib/reexam';
import { REEXAM } from '../frontend/src/data/reexam';

let fail = 0;
const assert = (cond: boolean, msg: string) => {
  if (!cond) {
    fail++;
    console.error('  ✗ ' + msg);
  } else {
    console.log('  ✓ ' + msg);
  }
};

console.log('[1] buildReexamView：面试 / 机试 总体结构');
const v = buildReexamView();
assert(v.interview.categories.length === REEXAM.interview.categories.length, `面试分类数（实际 ${v.interview.categories.length}）`);
const expectQ = REEXAM.interview.categories.reduce((n, c) => n + c.questions.length, 0);
assert(v.totalQuestions === expectQ, `面试题总数 ${expectQ}（实际 ${v.totalQuestions}）`);
assert(v.machineTests.length === REEXAM.machineTests.length, `机试题数 ${REEXAM.machineTests.length}（实际 ${v.machineTests.length}）`);
assert(v.universities.length > 0, `机试高校来源非空（${v.universities.length} 所）`);
assert(v.modules.length > 0, `机试关联模块非空（${v.modules.length} 个）`);

console.log('[2] 机试题三层答案齐全 + 工作场景 + 关联模块');
for (const t of v.machineTests) {
  assert(!!t.framework && !!t.algorithm && !!t.code, `机试题「${t.title}」三层答案齐全`);
  assert(t.parts.length === 3, `机试题「${t.title}」拆成 3 段渲染`);
  assert(!!t.scene, `机试题「${t.title}」附工作场景`);
  assert(!!t.module, `机试题「${t.title}」关联 408 模块`);
  assert(!!t.university && !!t.year, `机试题「${t.title}」标注来源高校+年份`);
}

console.log('[3] 面试分类：desc + 每题 tip');
for (const c of v.interview.categories) {
  assert(!!c.desc, `面试类「${c.category}」有 desc`);
  assert(c.questions.length > 0, `面试类「${c.category}」非空`);
  for (const q of c.questions) assert(!!q.tip, `面试类「${c.category}」每题有导师视角 tip`);
}

console.log('[4] markdown 导出不抛错');
try {
  reexamToMarkdown(v);
  assert(true, 'reexamToMarkdown 正常执行');
} catch (e) {
  assert(false, 'markdown 导出抛错：' + String(e));
}

console.log(fail === 0 ? '\nREEXAM_OK' : `\nREEXAM_FAIL (${fail})`);
if (fail > 0) process.exit(1);
