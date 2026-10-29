/**
 * examTracks.ts —— 考研 408 专轨聚合（P2 · 章节总结表方案）纯函数层
 * ============================================================================
 * 读 TRACK_408（由 content/_tracks/408.json 经 gen_tracks.py 生成），按模块聚合章节
 * 掌握度，产出 408 总表 + 逐章下钻数据。纯函数、只读、零 dispatch，与 logicChain.ts
 * 同构，便于 verify_logic_chain.mjs --check-summary 断言。
 *
 * 与单章总结表的关系：单章表是「每章收尾」；本层是「四模块跨章汇总」，备考用。
 * 薄弱章判定复用 masteryOfChapter（<60），与首页 nextAction 同源。
 * ============================================================================
 */
import { TRACK_408, type TrackModule } from '../data/track408';
import { chapterName, masteryOfChapter } from './graph';
import type { ProgressState } from './gameTypes';

export interface ModuleChapterRow {
  id: string;
  title: string;
  mastery: number;
  done: boolean;
}

export interface TrackModuleSummary {
  module: string;
  chapterCount: number;
  chapters: ModuleChapterRow[];
  doneCount: number;
  avgMastery: number;
  /** 掌握度 < 60 的薄弱章 */
  weakChapters: ModuleChapterRow[];
  /** 冲刺建议 */
  sprint: string;
}

export interface TrackSummary {
  trackId: string;
  name: string;
  modules: TrackModuleSummary[];
  totalChapters: number;
  totalDone: number;
  overallAvg: number;
}

/** 根据模块当前状态推导冲刺建议 */
function sprintFor(m: Omit<TrackModuleSummary, 'sprint'>): string {
  if (m.doneCount === m.chapterCount && m.chapterCount > 0) return '已通关，进入真题模拟 / 查漏';
  if (m.weakChapters.length > 0) {
    const ids = m.weakChapters.map((c) => c.id).slice(0, 3).join('、');
    return `优先补薄弱章：${ids}`;
  }
  if (m.avgMastery < 60) return '系统过一遍，先冲概念 + 演练两关（≥60 解锁）';
  return '冲刺 BOSS 关，补齐三关全通';
}

/** 构建 408 专轨总表（按模块聚合） */
export function buildTrack408Summary(st: ProgressState): TrackSummary {
  const modules: TrackModuleSummary[] = TRACK_408.modules.map((mod: TrackModule) => {
    const chapters: ModuleChapterRow[] = mod.chapters.map((id) => {
      const m = masteryOfChapter(id, st);
      return { id, title: chapterName(id), mastery: m, done: m === 100 };
    });
    const doneCount = chapters.filter((c) => c.done).length;
    const avg = chapters.length
      ? Math.round(chapters.reduce((n, c) => n + c.mastery, 0) / chapters.length)
      : 0;
    const weak = chapters.filter((c) => c.mastery < 60);
    const base = {
      module: mod.module,
      chapterCount: chapters.length,
      chapters,
      doneCount,
      avgMastery: avg,
      weakChapters: weak,
    };
    return { ...base, sprint: sprintFor(base) };
  });

  const totalChapters = modules.reduce((n, m) => n + m.chapterCount, 0);
  const totalDone = modules.reduce((n, m) => n + m.doneCount, 0);
  const overallAvg = totalChapters
    ? Math.round(modules.reduce((n, m) => n + m.avgMastery * m.chapterCount, 0) / totalChapters)
    : 0;

  return {
    trackId: TRACK_408.trackId,
    name: TRACK_408.name,
    modules,
    totalChapters,
    totalDone,
    overallAvg,
  };
}

/** 单章在 408 中的考点行（供 408 考点表下钻） */
export function build408ChapterRow(chapterId: string, st: ProgressState): ModuleChapterRow | null {
  const inTrack = TRACK_408.modules.some((m) => m.chapters.includes(chapterId));
  if (!inTrack) return null;
  const m = masteryOfChapter(chapterId, st);
  return { id: chapterId, title: chapterName(chapterId), mastery: m, done: m === 100 };
}

/* ------------------------------------------------------------------ 导出 */

/** 把 408 总表渲染成 Markdown（用于导出 / 复盘） */
export function trackSummaryToMarkdown(t: TrackSummary): string {
  const head = [
    `### ${t.name} · 408 总表`,
    '',
    `> 进度：已通关 ${t.totalDone}/${t.totalChapters} 章 · 平均掌握度 ${t.overallAvg}`,
    '',
    '| 模块 | 章节数 | 已通关 | 平均掌握度 | 薄弱章(<60) | 冲刺建议 |',
    '|---|---|---|---|---|---|',
  ];
  const rows = t.modules.map((m) => {
    const weak = m.weakChapters.length ? m.weakChapters.map((c) => c.id).join('、') : '—';
    return `| ${m.module} | ${m.chapterCount} | ${m.doneCount} | ${m.avgMastery} | ${weak} | ${m.sprint} |`;
  });
  return [...head, ...rows, ''].join('\n');
}
