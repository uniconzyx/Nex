/**
 * chapterSummary.ts —— 单章总结表（7 维）纯函数生成层（P2 · 章节总结表方案）
 * ============================================================================
 * 复用 progress.ts / graph.ts / exerciseBank.ts；本层纯函数、只读、零 dispatch，
 * 与 logicChain.ts 同构，便于 verify_logic_chain.mjs --check-summary 断言。
 *
 * 设计要点：
 *   - 仅当章 mastery===100（对应 doneChapters）才生成总结；未达标返回 null
 *     （与 plan §2 不变量一致：掌握度 100 ⇔ done，总结面板仅本人达标后可见）。
 *   - 7 维：目标 / 核心概念 / 易错点 / 例题 / 面试真题 / 实战项目 / 总掌握度。
 *   - 正文切片来自生成数据 CHAPTER_CONTENT（gen_chapter_content.py）；
 *     例题题量来自 exerciseBank；掌握度/作答来自 progress 的 chapterRuns/answers。
 *   - 额外提供 Markdown 导出，对齐主人「导出进 E 盘 .ipynb」的习惯。
 * ============================================================================
 */
import { CHAPTER_CONTENT, type ChapterContent } from '../data/chapterContent';
import { allChapters, chapterName, masteryOfChapter } from './graph';
import { chapterBankStats } from './exerciseBank';
import type { ProgressState } from './gameTypes';

export interface SummaryDim {
  /** 该维度素材条数 */
  count: number;
  /** 达标所需最低条数（如例题要求 ≥5） */
  required?: number;
  /** 已满足条数（例题=已答对题数；项目=0/1） */
  done?: number;
  /** 关键条目（取前 3，用于「关键条目」列） */
  items: string[];
  /** 是否满足最低标准（概念/易错/面试题 ≥3；例题 ≥required；项目 ≥1） */
  ok: boolean;
}

export interface ChapterSummary {
  chapterId: string;
  title: string;
  mastery: number;
  goals: SummaryDim;
  concepts: SummaryDim;
  pitfalls: SummaryDim;
  exercises: SummaryDim;
  interview: SummaryDim;
  project: SummaryDim;
  /** 总掌握度（仅 mastery===100 时生成，恒为 100） */
  totalMastery: number;
}

const MIN_ITEMS = 3;
const TOP = 3;
const EXERCISE_REQUIRED = 5;

/** 文本型维度（目标/概念/易错/面试）：取条目切片 + 是否满足 ≥MIN_ITEMS */
function textDim(items: string[]): SummaryDim {
  return {
    count: items.length,
    items: items.slice(0, TOP),
    ok: items.length >= MIN_ITEMS,
  };
}

/** 本章已答对的题数（从 progress.answers 反查本章 chapterId） */
function passedOfChapter(chapterId: string, st: ProgressState): number {
  let n = 0;
  for (const a of Object.values(st.answers ?? {})) {
    if (a.chapterId === chapterId && a.ok) n += 1;
  }
  return n;
}

export function contentOf(chapterId: string): ChapterContent | undefined {
  return CHAPTER_CONTENT[chapterId];
}

/**
 * 构建单章总结表。仅当 mastery===100 返回；否则返回 null（未通关不生成）。
 */
export function buildChapterSummary(chapterId: string, st: ProgressState): ChapterSummary | null {
  const m = masteryOfChapter(chapterId, st);
  if (m !== 100) return null;

  const c = CHAPTER_CONTENT[chapterId];
  const stats = chapterBankStats(chapterId);
  const passed = passedOfChapter(chapterId, st);
  const projectCount = c?.projects?.length ?? 0;

  return {
    chapterId,
    title: chapterName(chapterId),
    mastery: m,
    goals: textDim(c?.goals ?? []),
    concepts: textDim(c?.concepts ?? []),
    pitfalls: textDim(c?.pitfalls ?? []),
    exercises: {
      count: stats.total,
      required: EXERCISE_REQUIRED,
      done: passed,
      items: [],
      ok: stats.total >= EXERCISE_REQUIRED,
    },
    interview: textDim(c?.interviews ?? []),
    project: {
      count: projectCount,
      done: projectCount >= 1 ? 1 : 0,
      items: (c?.projects ?? []).slice(0, TOP),
      ok: projectCount >= 1,
    },
    totalMastery: 100,
  };
}

/** 所有已通关章的总结（用于总览 / 批量导出） */
export function buildAllChapterSummaries(st: ProgressState): ChapterSummary[] {
  const out: ChapterSummary[] = [];
  for (const c of allChapters()) {
    const s = buildChapterSummary(c.id, st);
    if (s) out.push(s);
  }
  return out;
}

/* ------------------------------------------------------------------ 导出 */

/** 把单章总结渲染成 Markdown 表格（可直接粘进 E 盘 .ipynb） */
export function summaryToMarkdown(s: ChapterSummary): string {
  const rows: string[] = [];
  const push = (dim: string, d: SummaryDim, extra = '') => {
    const status = d.ok ? '✅' : '⚠️';
    const head = extra ? `${d.done ?? d.count}/${d.required ?? d.count} ${extra}` : `${d.count}`;
    const key = d.items.length ? d.items.join(' / ') : '—';
    rows.push(`| ${dim} | ${head} | ${status} | ${key} |`);
  };
  push('目标 Goals', s.goals);
  push('核心概念 Concepts', s.concepts);
  push('易错点 Pitfalls', s.pitfalls);
  push('例题 Exercises', s.exercises, '已答对');
  push('面试/真题 Interview', s.interview);
  push('实战 Project', s.project);
  return [
    `### ${s.title} · 单章总结表（掌握度 ${s.totalMastery}）`,
    '',
    '| 维度 | 数量/状态 | 达标 | 关键条目（前 3） |',
    '|---|---|---|---|',
    ...rows,
    `| **总掌握度** | **${s.totalMastery}** | ✅ | BOSS 通过、三关全绿 |`,
    '',
  ].join('\n');
}
