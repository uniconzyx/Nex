/**
 * challenge.ts —— 「去收服这道题」的统一入口
 * ============================================================================
 * 图鉴卡片、怪物遭遇弹窗、每日试炼三处都要做同一件事：
 *   找到题目 → 能判就带进判题台，不能判就锁到该章题库 → 跳到试炼实验室。
 *
 * 这段逻辑写在页面里会有三份实现、三种行为（曾经就是这样：学习页能跳，
 * 图鉴页只能干看）。集中成一个函数后，三处入口的行为天然一致。
 *
 * 导航函数由 App 在启动时注入，避免 lib 反向依赖 React 组件树。
 * ============================================================================
 */
import { exerciseById, focusChapter, focusExercise, isJudgeable, sendToJudge, toJudgeProblem } from './exerciseBank';
import type { KmPage } from './nav';

let navigator: ((page: KmPage) => void) | null = null;

/** App 启动时注册一次；未注册时退化：只准备题目，不切页 */
export function setAppNavigator(fn: ((page: KmPage) => void) | null): void {
  navigator = fn;
}

export interface ChallengeResult {
  ok: boolean;
  /** judge = 已带进判题台；bank = 只能锁章节去题库 */
  mode?: 'judge' | 'bank';
  reason?: string;
}

/**
 * 打开一道题的挑战入口。
 * 注意：题库里已经找不到这道题时不静默失败——图鉴可能来自旧版本数据，
 * 这时要告诉玩家原因，而不是点了一下什么都没发生。
 */
export function challengeQuestion(questionId: string): ChallengeResult {
  const ex = exerciseById(questionId);
  if (!ex) return { ok: false, reason: '题库里已找不到这道题（可能是旧版本记录）' };

  const mode = isJudgeable(ex) ? 'judge' : 'bank';
  if (mode === 'judge') {
    sendToJudge(toJudgeProblem(ex));
  } else {
    // 不能判的题：锁章节 + 指名打开这道题，玩家不用再在列表里翻
    focusChapter(ex.ch);
    focusExercise(ex.id);
  }

  if (navigator) navigator('lab');
  return { ok: true, mode };
}
