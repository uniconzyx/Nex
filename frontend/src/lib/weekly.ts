/**
 * weekly.ts —— 周 BOSS（P3 · S4）
 * ============================================================================
 * 【它是什么】
 *   一周一个跨章挑战：从「你正在推进」的章节里挑一章，出该章最硬的三道题，
 *   三道全对才算通关，奖励 150 结晶 + 2 碎片（一次性的）。
 *
 * 【为什么要有它 —— 内环缺一个"周期性目标"】
 *   P1/P2 已经把日循环（每日试炼）和章循环（三关）做完了，
 *   但它们都是"由进度触发的"：没进度就没目标，有进度也只会一章一章慢慢走。
 *   一周一次的大目标给的是另一种驱动——它不跟着你的进度涨，
 *   而是**每周重新开始**，所以"这周还没打"永远是一个悬着的事。
 *
 * 【门槛为什么由「本周答对题数」决定，而不是"点一下就进"】
 *   方案 §7 要求「周 BOSS 门槛可检查」。可检查的意思是：
 *   这个数字必须来自不可伪造的记录（answers 里 at 落在本周且 ok=true 的题），
 *   而不是一个可以点的按钮。于是它的作用是"证明你这周在学"，
 *   顺带解决了"周日晚上才发现有周 Boss"这种体验——反正门槛也得先做题。
 *
 * 【为什么题单要落盘（不像门槛那样每次算）】
 *   同一周内刷新页面必须看到同一套题。若每次现算，用户改一个章节的进度，
 *   题单就可能换一套，"我昨天打过一道"的记忆和界面对不上。
 *   落盘 + 只校验 week/qids 仍存在，既稳定又能在题库改版后自愈。
 * ============================================================================
 */
import { useEffect } from 'react';

import { allChapters } from './graph';
import {
  WEEKLY_GATE_CORRECT,
  WEEKLY_SIZE,
  type WeeklyRun,
} from './gameTypes';
import { chapterBankStats, chapterTitle, exerciseById, exercisesOfChapter } from './exerciseBank';
import { dispatch, getProgressSnapshot, todayKey, useProgress, type ProgressState } from './progress';

/* ------------------------------------------------------------ 时间 */

/** ISO 周编号，形如 2026-W44（周一 00:00 换周） */
export function weekKey(d = new Date()): string {
  // 复制一份并按"以周一为第一天"归一：ISO 周里周四决定归属年份
  const t = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = (t.getDay() + 6) % 7; // 周一 = 0
  t.setDate(t.getDate() - day + 3); // 挪到本周周四
  const year = t.getFullYear();
  const jan4 = new Date(year, 0, 4);
  const jan4Day = (jan4.getDay() + 6) % 7;
  const week1Monday = new Date(year, 0, 4 - jan4Day);
  const n = Math.round((t.getTime() - week1Monday.getTime()) / (7 * 86400000)) + 1;
  return `${year}-W${String(n).padStart(2, '0')}`;
}

/** 本周一 00:00 的时间戳（本地时区）——门槛统计的起点 */
export function weekStartMs(d = new Date()): number {
  const t = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = (t.getDay() + 6) % 7;
  t.setDate(t.getDate() - day);
  return t.getTime();
}

/** 稳定哈希：同一个 week string 永远得到同一个数，用于"本周挑哪一章" */
function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

/* ------------------------------------------------------- 门槛与选题 */

/** 本周答对了几道题（门槛的唯一输入，全部来自 answers） */
export function correctThisWeek(st: ProgressState, now = new Date()): number {
  const start = weekStartMs(now);
  let n = 0;
  for (const a of Object.values(st.answers ?? {})) {
    if (a.ok && a.at >= start) n += 1;
  }
  return n;
}

const DIFF_RANK: Record<string, number> = { hard: 0, medium: 1, easy: 2 };

/**
 * 本周打哪一章。
 *
 * 优先级刻意是「你正在攻的那一章」而不是随机：
 *   Boss 打的是已经学过的内容，才有"检验"的意义；
 *   随机抽一个没学过的章节，只会变成一道看不懂的题。
 * 三级退化保证任何状态下都有题可出（新用户 → 全库；老用户 → 差最后一关的）。
 */
export function pickWeeklyChapter(st: ProgressState, week = weekKey()): string | null {
  const pool = allChapters().filter((c) => chapterBankStats(c.id).total > 0);
  if (pool.length === 0) return null;

  const ahead = pool.filter((c) => {
    const run = st.chapterRuns[c.id];
    if (!run) return false;
    // 概念关已过、但还没全通 —— 这是"主线上的下一关"
    return run.concept === 1 && run.boss !== 1;
  });
  const startedPool = pool.filter((c) => !!st.chapterRuns[c.id]);
  const list = ahead.length ? ahead : startedPool.length ? startedPool : pool;
  return list[hashStr(week) % list.length].id;
}

/** 该章最硬的三道题：hard → medium → easy，同档按 id 升序保证确定性 */
export function bossQidsOf(chapterId: string): string[] {
  const list = exercisesOfChapter(chapterId);
  return [...list]
    .sort((a, b) => {
      const d = (DIFF_RANK[a.diff] ?? 9) - (DIFF_RANK[b.diff] ?? 9);
      return d !== 0 ? d : a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
    })
    .slice(0, WEEKLY_SIZE)
    .map((e) => e.id);
}

/** 纯函数：给定状态产出本周题单（不写盘，方便测试/预览） */
export function buildWeekly(st: ProgressState, now = new Date()): WeeklyRun | null {
  const week = weekKey(now);
  const chapterId = pickWeeklyChapter(st, week);
  if (!chapterId) return null;
  const qids = bossQidsOf(chapterId);
  if (qids.length === 0) return null;
  return { week, chapterId, qids, done: [], correct: [], claimed: false };
}

/**
 * 本周题单是否需要重建。
 *
 * 三种情况都要重建：跨周了 / 从没生成过 / 题目在题库改版后消失了。
 * 第三种不重建的话，会出现"永远打不完"的题单——点进去发现题不存在，
 * 但它仍然占着 qids 的位置，通关判定永远为 false。
 */
function needsRebuild(run: WeeklyRun | null, now = new Date()): boolean {
  if (!run) return true;
  if (run.week !== weekKey(now)) return true;
  if (run.qids.length === 0) return true;
  return run.qids.some((id) => !exerciseById(id));
}

/** 页面挂载时调：必要时重建题单 */
export function ensureWeekly(now = new Date()): WeeklyRun | null {
  const st = getProgressSnapshot();
  if (needsRebuild(st.weekly, now)) {
    const run = buildWeekly(st, now);
    if (!run) return null;
    // 已通关的同一周不重建（否则会把 clearedAt 抹掉，奖励却能重复领）
    if (st.weekly && st.weekly.week === run.week && st.weekly.claimed) return st.weekly;
    dispatch({ type: 'weeklyReset', run });
    return run;
  }
  return st.weekly;
}

/* ------------------------------------------------------------- 视图 */

export interface WeeklyView {
  week: string;
  chapterId: string;
  chapterTitle: string;
  /** 门槛：本周答对 n / need */
  gateGot: number;
  gateNeed: number;
  gateOk: boolean;
  /** 题单完成度 */
  solved: number;
  total: number;
  cleared: boolean;
  /** 三道题各自的现状，直接渲染 */
  items: { id: string; title: string; diff: string; qtype: string; answered: boolean; ok: boolean }[];
}

export function weeklyView(st: ProgressState, now = new Date()): WeeklyView | null {
  const run = st.weekly;
  if (!run || needsRebuild(run, now)) return null;
  const gateGot = correctThisWeek(st, now);
  const solved = run.qids.filter((id) => run.correct.includes(id)).length;
  return {
    week: run.week,
    chapterId: run.chapterId,
    chapterTitle: chapterTitle(run.chapterId),
    gateGot,
    gateNeed: WEEKLY_GATE_CORRECT,
    gateOk: gateGot >= WEEKLY_GATE_CORRECT,
    solved,
    total: run.qids.length,
    cleared: run.claimed,
    items: run.qids.map((id) => {
      const ex = exerciseById(id);
      return {
        id,
        title: ex?.title ?? id,
        diff: ex?.diff ?? 'medium',
        qtype: ex?.type ?? 'choice',
        answered: run.done.includes(id),
        ok: run.correct.includes(id),
      };
    }),
  };
}

/** 页面用：挂载时确保本周题单存在 */
export function useWeekly(): WeeklyView | null {
  const st = useProgress();
  // 用今天当依赖：跨周后第一次进页面就会重建
  const today = todayKey();
  useEffect(() => {
    ensureWeekly();
  }, [today]);
  return weeklyView(st);
}

/** 答完一题后记账（题目是否属于本周题单由 reducer 校验） */
export function submitWeekly(questionId: string, ok: boolean): void {
  dispatch({ type: 'weekly', questionId, ok });
}
