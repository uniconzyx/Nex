/**
 * reexam.ts —— 考研复试板块（P6 + 题型/框架扩充）纯函数层
 * ============================================================================
 * 读 REEXAM（由 content/_tracks/reexam.json 经 gen_tracks.py 生成），
 * 把「复试专属面试问题（非八股）+ 机试题库（三层答案 + 工作场景）
 * + 常考算法思想与框架速查」整理成视图模型，供 ReexamPage 渲染、
 * 供 --check-reexam 断言。
 *
 * 与 employment.ts 同构：纯函数、只读、零 dispatch。
 * 机试答案固定三层（大框架 / 核心算法思想 / 完整代码），每题附工作场景，
 * 与 §12 机试题库规范一致。
 * ============================================================================
 */
import {
  REEXAM,
  type ReexamInterviewCategory,
  type ReexamMachineTest,
  type ReexamPlaybookGroup,
} from '../data/reexam';

export interface InterviewQuestion {
  q: string;
  tip?: string;
}

export interface InterviewCategoryView extends ReexamInterviewCategory {
  count: number;
}

export interface AnswerPart {
  /** ① 大框架 / ② 核心算法思想 / ③ 完整代码 */
  label: string;
  text: string;
}

export interface MachineTestView extends ReexamMachineTest {
  /** 把 framework/algorithm/code 拆成有序三层，便于逐层渲染 */
  parts: AnswerPart[];
}

export interface InterviewSection {
  name: string;
  desc: string;
  categories: InterviewCategoryView[];
  totalQuestions: number;
}

/** 题型聚合：题型名 -> 题目数（按数量降序，同量按名称） */
export interface TypeBucket {
  type: string;
  count: number;
}

/** 算法框架分组视图 */
export interface PlaybookGroupView extends ReexamPlaybookGroup {
  count: number;
}

export interface PlaybookView {
  title: string;
  intro: string;
  steps: { name: string; detail: string }[];
  groups: PlaybookGroupView[];
  checklist: string[];
  totalPatterns: number;
}

export interface ReexamView {
  trackId: string;
  name: string;
  interview: InterviewSection;
  machineTests: MachineTestView[];
  /** 去重后的高校列表（机试题来源） */
  universities: string[];
  /** 去重后的关联模块（与 408 模块呼应） */
  modules: string[];
  /** 去重后的题型列表（机试题分类维度） */
  types: TypeBucket[];
  playbook: PlaybookView;
  totalQuestions: number;
  totalMachineTests: number;
}

/** 构建复试视图：面试分类 + 机试题三层答案 + 题型聚合 + 算法框架 */
export function buildReexamView(): ReexamView {
  const interviewDef = REEXAM.interview;
  const categories: InterviewCategoryView[] = interviewDef.categories.map((c) => ({
    ...c,
    count: c.questions.length,
  }));
  const totalQuestions = categories.reduce((n, c) => n + c.count, 0);

  const machineTests: MachineTestView[] = REEXAM.machineTests.map((t) => ({
    ...t,
    parts: [
      { label: '① 大框架', text: t.framework },
      { label: '② 核心算法思想', text: t.algorithm },
      { label: '③ 完整代码（全注释）', text: t.code },
    ],
  }));

  const universities = Array.from(new Set(REEXAM.machineTests.map((t) => t.university)));
  const modules = Array.from(new Set(REEXAM.machineTests.map((t) => t.module)));

  const counter = new Map<string, number>();
  for (const t of REEXAM.machineTests) {
    const key = t.type || '未分类';
    counter.set(key, (counter.get(key) ?? 0) + 1);
  }
  const types: TypeBucket[] = Array.from(counter, ([type, count]) => ({ type, count })).sort(
    (a, b) => b.count - a.count || a.type.localeCompare(b.type, 'zh'),
  );

  const pbDef = REEXAM.algorithmPlaybook;
  const groups: PlaybookGroupView[] = pbDef.groups.map((g) => ({ ...g, count: g.patterns.length }));
  const playbook: PlaybookView = {
    title: pbDef.title,
    intro: pbDef.intro,
    steps: pbDef.steps,
    groups,
    checklist: pbDef.checklist,
    totalPatterns: groups.reduce((n, g) => n + g.count, 0),
  };

  return {
    trackId: REEXAM.trackId,
    name: REEXAM.name,
    interview: {
      name: interviewDef.name,
      desc: interviewDef.desc,
      categories,
      totalQuestions,
    },
    machineTests,
    universities,
    modules,
    types,
    playbook,
    totalQuestions,
    totalMachineTests: machineTests.length,
  };
}

/* ------------------------------------------------------------------ 筛选 */

export interface MachineFilter {
  /** 题型；空串 = 全部 */
  type?: string;
  /** 来源高校；空串 = 全部 */
  university?: string;
  /** 关联模块；空串 = 全部 */
  module?: string;
  /** 关键词（标题/场景/算法思想大小写不敏感子串） */
  keyword?: string;
}

/** 按题型 / 高校 / 模块 / 关键词筛选机试题（纯函数，不改原数组） */
export function filterMachineTests(
  tests: MachineTestView[],
  f: MachineFilter,
): MachineTestView[] {
  const kw = (f.keyword ?? '').trim().toLowerCase();
  return tests.filter((t) => {
    if (f.type && t.type !== f.type) return false;
    if (f.university && t.university !== f.university) return false;
    if (f.module && t.module !== f.module) return false;
    if (kw) {
      const hay = `${t.title}\n${t.scene}\n${t.algorithm}\n${t.framework}`.toLowerCase();
      if (!hay.includes(kw)) return false;
    }
    return true;
  });
}

/* ------------------------------------------------------------------ 导出 */

/** 把复试视图渲染成 Markdown（用于导出 / 复盘） */
export function reexamToMarkdown(v: ReexamView): string {
  const typeLine = v.types.map((t) => `${t.type}×${t.count}`).join('、');
  const head = [
    `### ${v.name}`,
    '',
    `> 面试问题 ${v.totalQuestions} 道（${v.interview.categories.length} 类，非八股） · 机试题 ${v.totalMachineTests} 道（来源 ${v.universities.length} 所高校）`,
    '',
    `> 题型分布：${typeLine}`,
    '',
  ];

  const ivHead = [
    `## 一、复试专属面试问题（非八股）`,
    '',
    v.interview.desc,
    '',
  ];
  const catBlocks = v.interview.categories.map((c) => {
    const lines = [
      `### ${c.category}（${c.count}）`,
      '',
      `> ${c.desc}`,
      '',
    ];
    c.questions.forEach((q, i) => {
      lines.push(`${i + 1}. ${q.q}`);
      if (q.tip) lines.push(`   - 导师视角：${q.tip}`);
    });
    lines.push('');
    return lines.join('\n');
  });

  const pb = v.playbook;
  const pbHead = [
    '## 二、常考算法思想与框架（速查）',
    '',
    `> ${pb.intro}`,
    '',
    '### 拿到题先走的五步',
    '',
    ...pb.steps.map((s) => `- **${s.name}**：${s.detail}`),
    '',
    '### 框架速查',
    '',
  ];
  const pbBlocks = pb.groups.map((g) => {
    const lines = [`#### ${g.group}（${g.count}）`, ''];
    if (g.why) lines.push(`> ${g.why}`, '');
    if (g.types.length) lines.push(`- 对应题型：${g.types.join('、')}`, '');
    g.patterns.forEach((p, i) => {
      lines.push(`**${i + 1}. ${p.name}**`);
      lines.push('');
      lines.push(`- 何时用：${p.when}`);
      lines.push(`- 复杂度：${p.complexity}`);
      lines.push(`- 易错：${p.trap}`);
      lines.push('');
      lines.push('```cpp');
      lines.push(p.template.trimEnd());
      lines.push('```');
      lines.push('');
    });
    return lines.join('\n');
  });
  const pbTail = ['### 提交前自检清单', '', ...pb.checklist.map((c, i) => `${i + 1}. ${c}`), ''];

  const mtHead = ['## 三、机试题库（高校真题 · 三层答案 · 工作场景）', ''];
  const mtBlocks = v.machineTests.map((t, i) => {
    const lines = [
      `### ${i + 1}. ${t.title}`,
      '',
      `- 来源：${t.university}（${t.year}）｜题型：${t.type}｜关联模块：${t.module}`,
      `- 工作场景：${t.scene}`,
      '',
    ];
    t.parts.forEach((p) => {
      lines.push(`**${p.label}**`);
      lines.push('');
      lines.push(p.text);
      lines.push('');
    });
    return lines.join('\n');
  });

  return [
    ...head,
    ...ivHead,
    ...catBlocks,
    ...pbHead,
    ...pbBlocks,
    ...pbTail,
    ...mtHead,
    ...mtBlocks,
    '',
  ].join('\n');
}
