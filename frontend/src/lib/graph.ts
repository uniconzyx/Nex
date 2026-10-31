/**
 * graph.ts —— 依赖图的查询层（P2 · C2）
 * ============================================================================
 * data/graph.ts 是脚本生成的**数据**（章节前置边、项目 requires 边、章节→学科）；
 * 这里是把数据变成「现在能不能开」的**判断**。两层分开的原因：
 *   生成脚本要跑 Python，判断要跑在手机上；混在一起就没法各自回归。
 *
 * 【门槛用 60 而不是 100】
 *   100 = 三关全通 = 「这一章我彻底会了」；
 *   60  = 概念 + 演练过 = 「这一章我能用了」。
 *   项目要的是「能动手」，不是「能默写」；章节前置也同理，
 *   否则玩家会被迫把前置章刷到 100 才能看下一章，节奏直接断掉。
 *
 * 【前置只做提示，不做硬锁】
 *   软门槛：可以看到、可以读，但 NextAction 不会把「前置没满足的章」推给你，
 *   章节卡片上会写清楚「前置：ch03（掌握 30%）」。
 *   硬锁只会让 141 章的地图变成一堵墙。
 * ============================================================================
 */
import { BUNDLE } from '../data/bundle';
import { CLANG_CHAPTERS } from '../data/clangUnits';
import { GRAPH } from '../data/graph';
import { masteryOf, type ProgressState } from './gameTypes';

/** 解锁门槛：概念 + 演练两关通过（30 + 30） */
export const UNLOCK_MASTERY = 60;

export interface ChapterRef {
  id: string;
  subject: string;
  order: number;
  title: string;
  summary: string;
  group: string;
}

const CLANG_SUBJECT = 'clang';

const ALL: ChapterRef[] = (() => {
  const rows: ChapterRef[] = [];
  for (const [subject, pack] of Object.entries(BUNDLE.chapters)) {
    for (const c of pack.chapters) {
      rows.push({
        id: c.id,
        subject,
        order: c.order,
        title: c.title,
        summary: c.summary,
        group: pack.groups?.[c.group] ?? c.group,
      });
    }
  }
  for (const c of CLANG_CHAPTERS) {
    rows.push({
      id: c.id,
      subject: CLANG_SUBJECT,
      order: c.order,
      title: c.title,
      summary: c.summary,
      group: c.group,
    });
  }
  return rows;
})();

const BY_ID = new Map(ALL.map((c) => [c.id, c]));
const BY_SUBJECT = new Map<string, ChapterRef[]>();
for (const c of ALL) {
  let arr = BY_SUBJECT.get(c.subject);
  if (!arr) BY_SUBJECT.set(c.subject, (arr = []));
  arr.push(c);
}
for (const arr of BY_SUBJECT.values()) arr.sort((a, b) => a.order - b.order);

export function allChapters(): ChapterRef[] {
  return ALL;
}

export function chaptersOfSubject(subject: string): ChapterRef[] {
  return BY_SUBJECT.get(subject) ?? [];
}

export function chapterRef(id: string): ChapterRef | undefined {
  return BY_ID.get(id);
}

/** 章节标题：优先用图里带的（含 clang 单元），退回 id 本身 */
export function chapterName(id: string): string {
  return BY_ID.get(id)?.title ?? GRAPH.chapterTitle[id] ?? id;
}

export function chapterDeps(id: string): string[] {
  return GRAPH.chapterDeps[id] ?? [];
}

export function projectRequires(slug: string): string[] {
  return GRAPH.projectRequires[slug] ?? [];
}

/** 章节掌握度（0~100），progress 的 chapterRuns 是唯一来源 */
export function masteryOfChapter(id: string, st: ProgressState): number {
  return masteryOf(st.chapterRuns[id]);
}

/* ------------------------------------------------------------------ 项目 */

export interface GateItem {
  id: string;
  title: string;
  mastery: number;
  ok: boolean;
}

export interface ProjectGate {
  /** 全部 requires 达到 60 */
  ok: boolean;
  requires: GateItem[];
  /** 没达标的（用于显示「还差什么」） */
  missing: GateItem[];
}

export function projectGate(slug: string, st: ProgressState): ProjectGate {
  const requires = projectRequires(slug).map((id) => {
    const mastery = masteryOfChapter(id, st);
    return { id, title: chapterName(id), mastery, ok: mastery >= UNLOCK_MASTERY };
  });
  const missing = requires.filter((r) => !r.ok);
  return { ok: missing.length === 0, requires, missing };
}

/** 已解锁且没通关的项目：NextAction 的第 4 步从这里面挑 */
export function unlockedProjects(st: ProgressState, subject?: string) {
  return BUNDLE.projects.items.filter((p) => {
    if (st.doneProjects.includes(p.slug)) return false;
    if (subject && p.track !== subject) return false;
    return projectGate(p.slug, st).ok;
  });
}

/* ------------------------------------------------------------------ 章节 */

/**
 * 该学科「下一章该学哪一章」：
 *   未掌握 → 前置都到 60 → 章号最小的一章。
 * 前置没满足的章会被跳过（不是隐藏），所以即使中间某章卡住，
 * 也不会把后面 19 章一起堵死 —— 只要后面的章节不依赖它。
 */
export function nextChapter(subject: string, st: ProgressState): ChapterRef | null {
  const list = chaptersOfSubject(subject);
  for (const c of list) {
    if (masteryOfChapter(c.id, st) >= 100) continue;
    const deps = chapterDeps(c.id);
    if (deps.every((d) => masteryOfChapter(d, st) >= UNLOCK_MASTERY)) return c;
  }
  return null;
}

/**
 * 当前正在攻的章：第一章掌握度在 1~99 之间的。
 * NextAction 用它推「继续 ch05 · BOSS 关」而不是「开新章」。
 */
export function currentChapter(subject: string, st: ProgressState): ChapterRef | null {
  return (
    chaptersOfSubject(subject).find((c) => {
      const m = masteryOfChapter(c.id, st);
      return m > 0 && m < 100;
    }) ?? null
  );
}

/** 学科整体掌握度：各章 0~100 的平均（不是「通关章数 / 总章数」） */
export function subjectMastery(subject: string, st: ProgressState): number {
  const list = chaptersOfSubject(subject);
  if (!list.length) return 0;
  const sum = list.reduce((n, c) => n + masteryOfChapter(c.id, st), 0);
  return Math.round(sum / list.length);
}

/** 全局掌握度 + 已掌握章数，右栏与首页共用 */
export function masterySummary(st: ProgressState): {
  avg: number;
  done: number;
  total: number;
  touched: number;
} {
  let sum = 0;
  let done = 0;
  let touched = 0;
  for (const c of ALL) {
    const m = masteryOfChapter(c.id, st);
    sum += m;
    if (m >= 100) done += 1;
    if (m > 0) touched += 1;
  }
  return {
    avg: ALL.length ? Math.round(sum / ALL.length) : 0,
    done,
    total: ALL.length,
    touched,
  };
}
