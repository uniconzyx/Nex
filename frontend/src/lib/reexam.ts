/**
 * reexam.ts —— 考研复试板块（P6）纯函数层
 * ============================================================================
 * 读 REEXAM（由 content/_tracks/reexam.json 经 gen_tracks.py 生成），
 * 把「复试专属面试问题（非八股）+ 机试题库（三层答案 + 工作场景）」
 * 整理成视图模型，供 ReexamPage 渲染、供 --check-reexam 断言。
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

export interface ReexamView {
  trackId: string;
  name: string;
  interview: InterviewSection;
  machineTests: MachineTestView[];
  /** 去重后的高校列表（机试题来源） */
  universities: string[];
  /** 去重后的关联模块（与 408 模块呼应） */
  modules: string[];
  totalQuestions: number;
  totalMachineTests: number;
}

/** 构建复试视图：面试分类 + 机试题三层答案 */
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
    totalQuestions,
    totalMachineTests: machineTests.length,
  };
}

/* ------------------------------------------------------------------ 导出 */

/** 把复试视图渲染成 Markdown（用于导出 / 复盘） */
export function reexamToMarkdown(v: ReexamView): string {
  const head = [
    `### ${v.name}`,
    '',
    `> 面试问题 ${v.totalQuestions} 道（${v.interview.categories.length} 类，非八股） · 机试题 ${v.totalMachineTests} 道（来源：${v.universities.join('、')}）`,
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

  const mtHead = ['## 二、机试题库（高校真题 · 三层答案 · 工作场景）', ''];
  const mtBlocks = v.machineTests.map((t, i) => {
    const lines = [
      `### ${i + 1}. ${t.title}`,
      '',
      `- 来源：${t.university}（${t.year}）｜关联模块：${t.module}`,
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

  return [...head, ...ivHead, ...catBlocks, ...mtHead, ...mtBlocks, ''].join('\n');
}
