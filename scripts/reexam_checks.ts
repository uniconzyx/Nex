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
import { buildReexamView, filterMachineTests, reexamToMarkdown } from '../frontend/src/lib/reexam';
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

console.log('[1b] 覆盖度下限（防止内容回退）');
assert(v.machineTests.length >= 30, `机试题 ≥30 道（实际 ${v.machineTests.length}）`);
assert(v.universities.length >= 23, `机试来源高校 ≥23 所（实际 ${v.universities.length}）`);
assert(v.modules.length >= 12, `机试覆盖模块 ≥12 个（实际 ${v.modules.length}）`);
assert(v.types.length >= 25, `机试题型 ≥25 类（实际 ${v.types.length}）`);
assert(v.interview.categories.length >= 6, `面试分类 ≥6（实际 ${v.interview.categories.length}）`);
assert(v.totalQuestions >= 28, `面试题 ≥28 道（实际 ${v.totalQuestions}）`);
for (const must of ['研究计划', '项目陈述', '英语口语', '专业素养', '选导与联系导师', '科研潜质与读博']) {
  assert(
    v.interview.categories.some((c) => c.category === must),
    `面试包含「${must}」类`,
  );
}
// 机试必须覆盖王道四大件里最难考的几个专题，避免只剩「排序/查找」这类容易题
for (const mod of ['数据结构 · 图', '数据结构 · 树', '数据结构 · 串', '算法 · 动态规划']) {
  assert(v.modules.includes(mod), `机试覆盖「${mod}」专题`);
}
// 题型维度必须覆盖「考场真正会撞上」的几类，缺一类就是有整块盲区
for (const ty of [
  '模拟', '搜索', '贪心', '二分查找', '二分答案', '双指针', '滑动窗口',
  '前缀和与差分', '栈', '单调栈', '堆', '哈希与链表', '链表', '遍历与重建',
  '图论拓扑', '图论最短路', '并查集', '动态规划', '回溯', '分治', '字符串',
  '位运算', '树状数组', '数学', '高精度',
]) {
  assert(v.types.some((t) => t.type === ty), `题型覆盖「${ty}」`);
}

console.log('[2] 机试题三层答案齐全 + 工作场景 + 关联模块 + 题型');
for (const t of v.machineTests) {
  assert(!!t.framework && !!t.algorithm && !!t.code, `机试题「${t.title}」三层答案齐全`);
  assert(t.parts.length === 3, `机试题「${t.title}」拆成 3 段渲染`);
  assert(!!t.scene, `机试题「${t.title}」附工作场景`);
  assert(!!t.module, `机试题「${t.title}」关联 408 模块`);
  assert(!!t.type, `机试题「${t.title}」标注题型`);
  assert(!!t.university && !!t.year, `机试题「${t.title}」标注来源高校+年份`);
  assert(/O\(/.test(t.algorithm), `机试题「${t.title}」核心思想标注复杂度`);
  assert(/[\u4e00-\u9fa5]/.test(t.code), `机试题「${t.title}」代码含中文注释`);
}

console.log('[3] 面试分类：desc + 每题 tip');
for (const c of v.interview.categories) {
  assert(!!c.desc, `面试类「${c.category}」有 desc`);
  assert(c.questions.length > 0, `面试类「${c.category}」非空`);
  for (const q of c.questions) assert(!!q.tip, `面试类「${c.category}」每题有导师视角 tip`);
}

console.log('[4] 常考算法思想与框架：五步 + 分组模板 + 自检清单');
const pb = v.playbook;
assert(pb.steps.length >= 5, `解题步骤 ≥5 步（实际 ${pb.steps.length}）`);
for (const s of pb.steps) {
  assert(!!s.name && !!s.detail, `步骤「${s.name}」有名称与说明`);
  assert(s.detail.length >= 40, `步骤「${s.name}」说明足够具体（≥40 字）`);
}
assert(pb.groups.length >= 18, `框架分组 ≥18 组（实际 ${pb.groups.length}）`);
assert(pb.totalPatterns >= 34, `框架模板 ≥34 个（实际 ${pb.totalPatterns}）`);
assert(pb.checklist.length >= 8, `提交前自检 ≥8 条（实际 ${pb.checklist.length}）`);
// 每个分组必须有模板；每个模板五项字段齐、且 template 真的像代码
const seenPattern = new Set<string>();
for (const g of pb.groups) {
  assert(!!g.group, '框架分组名非空');
  assert(g.patterns.length > 0, `框架分组「${g.group}」至少 1 个模板`);
  assert(g.count === g.patterns.length, `框架分组「${g.group}」count 与模板数一致`);
  for (const p of g.patterns) {
    assert(!seenPattern.has(p.name), `框架模板名唯一：${p.name}`);
    seenPattern.add(p.name);
    assert(!!p.name && !!p.when, `模板「${p.name}」有名称/何时用`);
    assert(!!p.template, `模板「${p.name}」有代码骨架`);
    assert(!!p.trap, `模板「${p.name}」标注易错点`);
    assert(/O\(/.test(p.complexity), `模板「${p.name}」标注复杂度`);
    assert(
      /[;{}（(]/.test(p.template) || /\n/.test(p.template),
      `模板「${p.name}」骨架是多行代码而非一句话`,
    );
  }
}
// 分组通过 types 映射到具体题型：既保证每个框架能指出它对哪类题，
// 也保证每个题型都有框架可依（不留盲区）。
const typeSet = new Set(v.types.map((t) => t.type));
const coveredTypes = new Set<string>();
for (const g of pb.groups) {
  assert(g.types.length > 0, `框架分组「${g.group}」声明覆盖的题型`);
  for (const ty of g.types) {
    assert(typeSet.has(ty), `框架分组「${g.group}」映射的题型「${ty}」真实存在`);
    coveredTypes.add(ty);
  }
}
const orphanTypes = v.types.map((t) => t.type).filter((ty) => !coveredTypes.has(ty));
assert(
  orphanTypes.length === 0,
  `每类题型都有框架覆盖（缺框架的题型：${orphanTypes.join('、') || '无'}）`,
);

console.log('[5] filterMachineTests：题型 / 关键词 / 清空');
const all = filterMachineTests(v.machineTests, {});
assert(all.length === v.machineTests.length, `空筛选返回全部（${all.length}）`);
const t0 = v.types[0].type;
const only = filterMachineTests(v.machineTests, { type: t0 });
assert(only.length === v.types[0].count, `按题型「${t0}」筛出 ${v.types[0].count} 道（实际 ${only.length}）`);
assert(only.every((t) => t.type === t0), `按题型「${t0}」结果不含其它题型`);
const KW = '最短路';
const kw = filterMachineTests(v.machineTests, { keyword: KW });
assert(kw.length > 0, `关键词「${KW}」能命中题目（${kw.length} 道）`);
assert(
  kw.every((t) => `${t.title}${t.scene}${t.algorithm}${t.framework}`.includes(KW)),
  `关键词「${KW}」结果确实包含该词`,
);
assert(
  filterMachineTests(v.machineTests, { keyword: 'zzz不可能命中的词zzz' }).length === 0,
  '无匹配关键词返回空数组',
);
assert(filterMachineTests(v.machineTests, { type: t0 }).length !== v.machineTests.length, '筛选不改变原数组长度');

console.log('[6] markdown 导出不抛错，且含框架与题型');
try {
  const md = reexamToMarkdown(v);
  assert(true, 'reexamToMarkdown 正常执行');
  assert(md.includes('常考算法思想与框架'), '导出含「常考算法思想与框架」小节');
  assert(md.includes('提交前自检清单'), '导出含自检清单');
  assert(md.includes('题型分布'), '导出含题型分布');
  for (const g of pb.groups.slice(0, 3)) {
    assert(md.includes(g.group), `导出含框架分组「${g.group}」`);
  }
  assert(md.includes(v.machineTests[0].type), '导出含机试题型标注');
} catch (e) {
  assert(false, 'markdown 导出抛错：' + String(e));
}

console.log(fail === 0 ? '\nREEXAM_OK' : `\nREEXAM_FAIL (${fail})`);
if (fail > 0) process.exit(1);
