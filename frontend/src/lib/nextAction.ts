/**
 * nextAction.ts —— 「现在只做一件事」（C3）
 * ============================================================================
 * 首页大卡、侧栏徽标、「继续闯关」按钮共用这一个函数的结果。
 * 只推一件事而不是给一排入口：一排入口等于没有入口，玩家会自己去刷别的。
 *
 * 【P2 改了什么】
 *   P1 的顺序是「试炼 → 怪物 → 下一章 → T1 项目 → 签到」，
 *   其中「下一章」只会挑**第一个没掌握的章**，于是你学到第 5 章时，
 *   它还在推第 5 章「进入知识试炼区」—— 进去之后仍然不知道做哪一关。
 *
 *   现在第 3 步读三关：当前章还有没过完的关，就直接说清是哪一关、还差什么；
 *   第 4 步读依赖图：只推**前置章节都到 60** 的项目（而不是随便一个 T1）；
 *   第 5 步才轮到「开新章」，且要求这一章的前置已经满足。
 *
 * 优先级（方案 §5 C3 + P2 验收）：
 *   1 今日试炼未完成
 *   2 有野生怪物
 *   3 当前章有未通过的关   ← 新
 *   4 有解锁未开始的项目   ← 改成读 requires
 *   5 下一章（前置满足）
 *   6 未签到
 *   7 兜底：去图鉴读情报
 * ============================================================================
 */
import { BUNDLE } from '../data/bundle';
import { dailyProgress } from './daily';
import type { DailyRun, ProgressState } from './gameTypes';
import {
  UNLOCK_MASTERY,
  chapterDeps,
  chapterName,
  chapterRef,
  chaptersOfSubject,
  currentChapter,
  masteryOfChapter,
  nextChapter,
  projectGate,
  unlockedProjects,
} from './graph';
import { isUnlocked } from './logicChain';
import type { KmPage } from './nav';
import { subjectLabel } from './subject';
import { bestiaryStats } from './progress';
import { chapterStages, nextStageOf } from './stages';

export interface NextAction {
  kind: 'daily' | 'wild' | 'stage' | 'project' | 'chapter' | 'checkin' | 'clear';
  title: string;
  subtitle: string;
  cta: string;
  target: KmPage;
  tone: 'primary' | 'warn' | 'ok';
  /** 章节关：点 CTA 时直接打开的题（BOSS 关） */
  questionId?: string;
  /** 章节关：要定位的章节 */
  chapterId?: string;
  /**
   * 5b 档专用：这一章在别的学科里，点 CTA 时要先切学科。
   *
   * 为什么不得不加：data-ch01 的前置是 py-ch03（跨学科），
   * 只 focusChapter 不切学科的话，学习页会打开一个"当前学科里不存在"的章节，
   * 用户点完什么都没发生 —— 比不推还糟。
   */
  subject?: string;
}

export function nextAction(
  subject: string,
  st: ProgressState,
  daily: DailyRun | null,
  checkedToday: boolean,
): NextAction {
  const bs = bestiaryStats(st);

  // 1) 今天的三题没清空：这是最短的一次会话（5~8 分钟），必须先推
  const dp = dailyProgress(daily);
  if (daily && !dp.allDone) {
    return {
      kind: 'daily',
      title: `今日试炼 ${dp.done} / ${dp.total}`,
      subtitle:
        dp.done > 0
          ? `还剩 ${dp.total - dp.done} 题，清空即得 50 结晶`
          : bs.wild > 0
            ? '三题里有一半是错题复习，先把你打不过的收回来'
            : '三道新题，按当前学科由浅入深排好',
      cta: dp.done === 0 ? '开始今日试炼' : '继续今日试炼',
      target: 'lab',
      tone: 'primary',
    };
  }

  // 2) 有野生怪物：错题不处理，图鉴就只是个相册
  if (bs.wild > 0) {
    return {
      kind: 'wild',
      title: `${bs.wild} 只怪物等你收服`,
      subtitle: `累计被打败 ${bs.fails} 次，重做通过即可收进图鉴`,
      cta: '打开怪物图鉴',
      target: 'bestiary',
      tone: 'warn',
    };
  }

  // 3) 正在攻的章：把「哪一关、还差什么」说清楚
  const cur = currentChapter(subject, st);
  if (cur) {
    const stage = nextStageOf(cur.id, st);
    if (stage) {
      const mastery = masteryOfChapter(cur.id, st);
      const got = chapterStages(cur.id, st).filter((s) => s.done).length;
      return {
        kind: 'stage',
        title: `${cur.title} · ${stage.label}`,
        subtitle:
          stage.blockers.length > 0
            ? `${stage.blockers.join('；')}（掌握度 ${mastery}%，已过 ${got}/3 关）`
            : `${stage.hint}（掌握度 ${mastery}%，已过 ${got}/3 关）`,
        cta: stage.key === 'boss' && stage.questionId ? '打这一关的首领' : '继续这一关',
        target: 'learn',
        tone: 'primary',
        questionId: stage.questionId,
        chapterId: cur.id,
      };
    }
  }

  // 4) 有解锁未开始的项目：requires 里的章节都到 60 才算解锁
  const openNow = unlockedProjects(st, subject);
  const project = openNow.find((p) => p.tier === 't1') ?? openNow[0];
  if (project) {
    const gate = projectGate(project.slug, st);
    const ready = gate.requires.filter((r) => r.ok).length;
    return {
      kind: 'project',
      title: `可以开一个项目：${project.title}`,
      subtitle: `${project.hours}h · ${project.repo} · 前置 ${ready}/${gate.requires.length} 章已达标`,
      cta: '打开 BOSS 项目实战',
      target: 'projects',
      tone: 'primary',
    };
  }

  // 5) 开新章（前置已满足）—— 走 isUnlocked 单一事实来源，绝不推未解锁的章
  const fresh = nextChapter(subject, st);
  if (fresh && isUnlocked(fresh.id, st)) {
    return {
      kind: 'chapter',
      title: `${subjectLabel(subject)} · ${fresh.title}`,
      subtitle: `${fresh.summary || '新的一章'}（三关：概念 30 / 演练 30 / BOSS 40）`,
      cta: '开这一章',
      target: 'learn',
      tone: 'primary',
      chapterId: fresh.id,
    };
  }

  /**
   * 5b) 本科目一章都开不了 —— 说明卡在**跨学科**前置上。
   *
   * 真实场景：新用户选「数据分析」，而 data-ch01 的前置是 py-ch03。
   * 没有这一档时，前面 1~5 步全部落空，最后推的是「签到」——
   * 用户签完到，明天再进来还是签到。这不是激励，是死胡同。
   * 所以这里直接指名"先去学哪一章"，并带上它的学科，让 CTA 能跨学科打开。
   */
  const stranded = chaptersOfSubject(subject)
    .filter((c) => masteryOfChapter(c.id, st) < 100)
    .map((c) => ({ c, missing: chapterDeps(c.id).filter((d) => masteryOfChapter(d, st) < UNLOCK_MASTERY) }))
    .filter((x) => x.missing.length > 0)
    // 缺口最少的先修：只差一章就能开工，比"还差五章"更值得先动
    .sort((a, b) => a.missing.length - b.missing.length);

  if (stranded.length > 0) {
    const { c, missing } = stranded[0];
    const gap = missing[0];
    return {
      kind: 'chapter',
      title: `还有一章前置挡着：${chapterName(gap)}`,
      subtitle: `「${c.title}」需要它先到 ${UNLOCK_MASTERY}%（共差 ${missing.length} 章）`,
      cta: '去学那一章',
      target: 'learn',
      tone: 'warn',
      chapterId: gap,
      subject: chapterRef(gap)?.subject,
    };
  }

  // 6) 今天还没签到
  if (!checkedToday) {
    return {
      kind: 'checkin',
      title: '祭坛的火要灭了',
      subtitle: '签到 +20 结晶，连续天数越高奖励越多',
      cta: '去签到祭坛',
      target: 'checkin',
      tone: 'warn',
    };
  }

  // 7) 兜底：这一科确实清完了
  const otherSubject = Object.keys(BUNDLE.chapters).find((s) => s !== subject && nextChapter(s, st));
  return {
    kind: 'clear',
    title: otherSubject
      ? `${subjectLabel(subject)} 已经清完了`
      : '今天的线都清了',
    subtitle: otherSubject
      ? `换到「${subjectLabel(otherSubject)}」继续，或者去图鉴翻翻八股情报`
      : '去图鉴翻翻八股情报，或者挑战一个 T4 项目',
    cta: '看看图鉴',
    target: 'bestiary',
    tone: 'ok',
  };
}
