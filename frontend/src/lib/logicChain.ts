/**
 * logicChain.ts —— 游戏逻辑链的「严密性」地基（可玩性增强 · 第 1 项）
 * ============================================================================
 * 这一层只做三件事，且全部是**纯函数 + 只读 state**，不 import React、不碰
 * localStorage、不 dispatch：
 *
 *   1) isUnlocked(chapterId, st)      —— 章节是否解锁的【唯一事实来源】
 *   2) dependencyIssues()             —— 依赖图本身的完整性（环 / 悬空 / 自环）
 *   3) stateViolations(st)            —— 运行时进度状态的不变量校验
 *
 * 为什么单独成层：
 *   之前「解锁」逻辑散落在 graph.ts 的 nextChapter / currentChapter 和
 *   nextAction.ts 里，各自内联一份 `deps.every(d => mastery >= 60)`。
 *   一旦要加「硬锁」「跨学科依赖」「项目链」就会处处改、处处漏。
 *   现在全部收敛到 isUnlocked，后续收紧规则只改一处。
 *
 * 与现有不变量的关系（见 docs/Playability-Coherence-Plan.md 两条不变量）：
 *   - 三关是 answers 的投影（deriveRuns 保证）
 *   - doneChapters ⇔ mastery===100（normalize 保证）
 *   本模块把第三条钉死：**进度不能超前于前置**（已到 60+ 的章，其前置也必须到 60+），
 *   并补充「依赖图无环」「doneChapters 必须真 100」「已通关项目前置必须达标」。
 * ============================================================================
 */
import { chapterDeps, masteryOfChapter, projectRequires, UNLOCK_MASTERY, allChapters } from './graph';
import type { ProgressState } from './gameTypes';
import { chapterStages } from './stages';

export interface UnlockOptions {
  /** 硬锁模式：默认 false（沿用现有软门槛，可见可读但 NextAction 不推） */
  hard?: boolean;
  /** 覆盖解锁门槛，默认用 graph.ts 的 UNLOCK_MASTERY(60) */
  threshold?: number;
}

/** 章节解锁的单一事实来源：所有前置章节掌握度达到门槛即解锁 */
export function isUnlocked(chapterId: string, st: ProgressState, opts: UnlockOptions = {}): boolean {
  const threshold = opts.threshold ?? UNLOCK_MASTERY;
  return chapterDeps(chapterId).every((d) => masteryOfChapter(d, st) >= threshold);
}

export type GraphIssueType = 'cycle' | 'dangling' | 'self';

export interface GraphIssue {
  type: GraphIssueType;
  detail: string;
}

/**
 * 依赖图完整性检查（与运行时 state 无关，只查图本身）。
 * 返回所有问题；空数组即「图是健康的」。应在 dev 启动与 audit_graph.py 双向校验。
 */
export function dependencyIssues(): GraphIssue[] {
  const issues: GraphIssue[] = [];
  const all = allChapters();
  const ids = new Set(all.map((c) => c.id));

  for (const c of all) {
    for (const d of chapterDeps(c.id)) {
      if (d === c.id) issues.push({ type: 'self', detail: `${c.id} 自依赖` });
      else if (!ids.has(d)) issues.push({ type: 'dangling', detail: `${c.id} 依赖不存在的 ${d}` });
    }
  }

  // 环检测：DFS 三色标记，遇到 GRAY 即回边
  const depsMap = new Map<string, string[]>();
  for (const c of all) depsMap.set(c.id, chapterDeps(c.id));
  const WHITE = 0, GRAY = 1, BLACK = 2;
  const color = new Map<string, number>();
  for (const c of all) color.set(c.id, WHITE);
  const stack: string[] = [];

  const dfs = (u: string): void => {
    color.set(u, GRAY);
    stack.push(u);
    for (const v of depsMap.get(u) ?? []) {
      if (!ids.has(v)) continue;
      const cv = color.get(v) ?? WHITE;
      if (cv === GRAY) {
        issues.push({ type: 'cycle', detail: `检测到环: ${[...stack, v].join(' → ')}` });
      } else if (cv === WHITE) {
        dfs(v);
      }
    }
    stack.pop();
    color.set(u, BLACK);
  };
  for (const c of all) if (color.get(c.id) === WHITE) dfs(c.id);

  return issues;
}

export interface StateViolation {
  rule: string;
  detail: string;
}

/**
 * 运行时不变量校验。任何一条命中都说明 state 处于「逻辑链断裂」状态。
 * 在每次 dispatch 之后（dev 下）跑一次，命中即报错，防止脏数据悄悄累积。
 */
export function stateViolations(st: ProgressState): StateViolation[] {
  const v: StateViolation[] = [];

  for (const c of allChapters()) {
    const m = masteryOfChapter(c.id, st);
    const gates = chapterStages(c.id, st);
    const allDone = gates.every((g) => g.done);

    // ① mastery===100 必须三关全过
    if (m === 100 && !allDone) {
      v.push({ rule: 'mastery100⇒gates', detail: `${c.id} mastery=100 但三关未全过` });
    }
    // ② doneChapters 必须真 100
    if (st.doneChapters.includes(c.id) && m !== 100) {
      v.push({ rule: 'done⇒mastery100', detail: `${c.id} 在 doneChapters 但 mastery=${m}` });
    }
    // ③ 严密核心：进度不能超前于前置（已到门槛的章，其前置也必须到门槛）
    if (m >= UNLOCK_MASTERY) {
      for (const d of chapterDeps(c.id)) {
        const dm = masteryOfChapter(d, st);
        if (dm < UNLOCK_MASTERY) {
          v.push({ rule: 'prereq', detail: `${c.id} 已到 ${m} 但前置 ${d} 仅 ${dm}` });
        }
      }
    }
  }

  // ④ 已通关项目：其前置章节必须达标
  for (const slug of st.doneProjects) {
    for (const r of projectRequires(slug)) {
      const rm = masteryOfChapter(r, st);
      if (rm < UNLOCK_MASTERY) {
        v.push({ rule: 'projectPrereq', detail: `项目 ${slug} 已通关但前置 ${r} 仅 ${rm}` });
      }
    }
  }

  return v;
}
