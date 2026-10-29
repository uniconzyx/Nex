// employment_checks.ts —— P5 就业八股专轨 断言入口
// ============================================================================
// 被 scripts/verify_logic_chain.mjs --check-employment 通过 esbuild 打包后由 node 执行。
// 驱动 lib/employment.ts，验证：
//   1) buildInterviewGraph 四区 / 资源总数 / Agent 模块数 / 模拟卷数
//   2) 每区有 color 且非空、每资源有 url+role（无悬空节点）
//   3) sourceById 索引覆盖全部节点
//   4) markdown 导出不抛错
// 任意断言失败 → process.exit(1)，与 summary_checks 同一套守门哲学。
// ============================================================================
import { buildInterviewGraph, interviewGraphToMarkdown } from '../frontend/src/lib/employment';
import { EMPLOYMENT } from '../frontend/src/data/employment';

let fail = 0;
const assert = (cond: boolean, msg: string) => {
  if (!cond) {
    fail++;
    console.error('  ✗ ' + msg);
  } else {
    console.log('  ✓ ' + msg);
  }
};

console.log('[1] buildInterviewGraph：四区 / 资源 / Agent 专项 结构');
const g = buildInterviewGraph();
assert(g.zones.length === 4, `四区（实际 ${g.zones.length}）`);
const expectTotal = EMPLOYMENT.zones.reduce((n, z) => n + z.sources.length, 0);
assert(g.totalSources === expectTotal, `资源总数 ${expectTotal}（实际 ${g.totalSources}）`);
assert(g.agentLayers.length === 4, `Agent 四层骨架（实际 ${g.agentLayers.length}）`);
assert(g.agentModules.length === 6, `Agent ${g.agentModules.length} 模块`);
assert(g.mockPapers.length === 3, `模拟考卷 3 张（实际 ${g.mockPapers.length}）`);

console.log('[2] 无悬空：每区有 color 且非空、每资源有 url+role');
for (const z of g.zones) {
  assert(!!z.color, `区 ${z.zone} 有颜色`);
  assert(z.sources.length > 0, `区 ${z.zone} 非空`);
  for (const s of z.sources) {
    assert(!!s.url, `资源 ${s.id} 有 url`);
    assert(!!s.role, `资源 ${s.id} 有 role`);
  }
}

console.log('[3] sourceById 索引覆盖全部节点');
const allIds = g.zones.flatMap((z) => z.sources.map((s) => s.id));
for (const id of allIds) assert(!!g.sourceById[id], `节点 ${id} 入索引`);

console.log('[4] markdown 导出不抛错');
try {
  interviewGraphToMarkdown(g);
  assert(true, 'interviewGraphToMarkdown 正常执行');
} catch (e) {
  assert(false, 'markdown 导出抛错：' + String(e));
}

console.log(fail === 0 ? '\nEMPLOYMENT_OK' : `\nEMPLOYMENT_FAIL (${fail})`);
if (fail > 0) process.exit(1);
