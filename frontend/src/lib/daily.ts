/**
 * daily.ts —— 每日试炼（S3）
 * ============================================================================
 * 规则（方案 §4 S3）：
 *   每天 3 题 = 错题里 fails 最高的 2 道 + 当前学科一道没做过的新题；
 *   3/3 清空 → +50 结晶，全对再 +20；
 *   跨日自动重建，同一天内刷新不变。
 *
 * 【为什么"新题"按日期轮转而不是随机】
 *   随机意味着同一天刷新两次会看到不同的题，玩家会以为进度丢了。
 *   用 dayIndex 取模：同一天恒定、每天不同、不需要存随机种子。
 * ============================================================================
 */
import { useEffect } from 'react';

import { exercisesOfSubject, isBankDone } from './exerciseBank';
import { dispatch, getProgressSnapshot, todayKey, useProgress, wildMonsters } from './progress';
import type { DailyRun } from './gameTypes';

/** 每次会话三题：5~8 分钟能做完的量 */
export const DAILY_SIZE = 3;

function dayIndex(d = new Date()): number {
  const start = new Date(d.getFullYear(), 0, 0);
  return Math.floor((d.getTime() - start.getTime()) / 86400000);
}

/** 纯函数：给定学科算今天的题单（不写状态，方便测试与预览） */
export function buildDaily(subject: string, st = getProgressSnapshot()): DailyRun {
  const qids: string[] = [];
  const push = (id?: string) => {
    if (!id || qids.length >= DAILY_SIZE || qids.includes(id)) return;
    qids.push(id);
  };

  // 1) 错题优先：先复习打不过的（fails 已排序）
  for (const m of wildMonsters(st).slice(0, 2)) push(m.questionId);

  // 2) 推进一步：当前学科里没做过的新题
  const pool = exercisesOfSubject(subject)
    .filter((e) => !st.bestiary[e.id] && !isBankDone(e.id))
    .sort((a, b) => (a.ch < b.ch ? -1 : a.ch > b.ch ? 1 : a.id < b.id ? -1 : 1));
  if (pool.length) push(pool[dayIndex() % pool.length].id);

  // 3) 不够三题：先用剩余错题补满
  for (const m of wildMonsters(st)) push(m.questionId);

  /**
   * 4) 还不够：用该学科任意题兜底，但**先挑没出现过的章节**。
   *    第一版直接从同一章里连续取三道，首页看起来像"题单坏了"；
   *    章节分散才符合"每天三道、覆盖三个知识点"的预期。
   */
  const all = exercisesOfSubject(subject);
  if (all.length && qids.length < DAILY_SIZE) {
    const start = dayIndex() % all.length;
    const rotated = [...all.slice(start), ...all.slice(0, start)];
    const chapterOf = new Map(all.map((e) => [e.id, e.ch] as const));
    const usedCh = () => new Set(qids.map((id) => chapterOf.get(id)));

    for (const e of rotated) {
      if (qids.length >= DAILY_SIZE) break;
      if (usedCh().has(e.ch)) continue;
      push(e.id);
    }
    for (const e of rotated) {
      if (qids.length >= DAILY_SIZE) break;
      push(e.id);
    }
  }

  return { date: todayKey(), qids, done: [], correct: [], claimed: false };
}

/** 今天没有题单/题单是昨天的 → 重建。已存在则原样返回。 */
export function ensureDaily(subject: string): DailyRun | null {
  const st = getProgressSnapshot();
  const today = todayKey();
  if (st.daily && st.daily.date === today && st.daily.qids.length > 0) return st.daily;
  const run = buildDaily(subject, st);
  if (run.qids.length === 0) return null;
  dispatch({ type: 'dailyReset', run });
  return run;
}

export interface DailyProgress {
  done: number;
  total: number;
  allDone: boolean;
  allCorrect: boolean;
}

export function dailyProgress(run: DailyRun | null): DailyProgress {
  if (!run) return { done: 0, total: DAILY_SIZE, allDone: false, allCorrect: false };
  const done = run.qids.filter((id) => run.done.includes(id)).length;
  return {
    done,
    total: run.qids.length,
    allDone: run.qids.length > 0 && done === run.qids.length,
    allCorrect: run.qids.length > 0 && run.correct.length === run.qids.length,
  };
}

/** 页面用：挂载时确保今天的题单存在，并返回属于今天的这一份 */
export function useDaily(subject: string): DailyRun | null {
  const st = useProgress();
  const today = todayKey();
  useEffect(() => {
    ensureDaily(subject);
  }, [subject, today]);
  return st.daily && st.daily.date === today ? st.daily : null;
}

/** 答完一题后记账（题目是否属于今日题单由 reducer 校验） */
export function submitDaily(questionId: string, ok: boolean): void {
  dispatch({ type: 'daily', questionId, ok });
}
