/**
 * stages.ts —— 章节三关的判定规则（P2 · S1）
 * ============================================================================
 * 【为什么三关要由「真做过的题」判定，而不是点一个「我学完了」】
 *   点按钮只能证明你来了，不能证明你会了。v1 的 doneChapters 就是这种布尔值：
 *   141 个开关，按一下全亮，于是首页永远「已掌握 141/141」，学习就结束了。
 *
 *   三关的输入只有两样，都不可伪造：
 *     answers  —— 每题最近一次作答是否正确（progress 在每次作答时写入）
 *     bestiary —— 这道题现在是不是还有一只没收服的野生怪物
 *
 * 【为什么是 30 / 30 / 40】
 *   概念关最容易（1 道概念题），演练关要动手（3 道动手题），BOSS 关最难
 *   （本章最硬的那道题 + 清掉本章所有野生怪物）。权重对应「读完 → 会做 → 打得过」，
 *   掌握度不是进度条，是这三件事的加权。
 *
 * 【判定表】（每章 5~10 题，实测 141 章全部满足前置条件）
 *   概念关 need=1：choice / explain 里答对 1 道（若一章没有概念题，退化为任意 1 道）
 *   演练关 need=min(3, 该章动手题数)：coding / output / fix_error / design 里答对 N 道
 *   BOSS 关 need=1：答对「本章最硬的题」，且该章 wild 怪物数 = 0
 *
 * 【为什么不给「答错就扣光」的惩罚】
 *   关卡只有 0/1 两态，重做答对就回来；已经发出去的结晶不回收。
 *   掉关只掉掌握度，掉不下的是你确实做对过的那次记录（answers 里还在，
 *   只是 `ok=false` 覆盖了它 —— 这正是「最近一次」的含义：你现在不会了）。
 * ============================================================================
 */
import { exercisesOfChapter, type BankExercise, type BankType } from './exerciseBank';
import { STAGE_WEIGHT, type ProgressState, type StageKey } from './gameTypes';

/** 概念题：读得懂就能选对 */
export const CONCEPT_TYPES: BankType[] = ['choice', 'explain'];
/** 动手题：得自己写出来 */
export const DRILL_TYPES: BankType[] = ['coding', 'output', 'fix_error', 'design'];
/** 演练关要答对几道动手题 */
export const DRILL_NEED = 3;

export const STAGE_META: Record<
  StageKey,
  { label: string; short: string; desc: string; icon: string }
> = {
  concept: {
    label: '概念关',
    short: '概念',
    desc: '答对 1 道概念题：证明你读懂了这一章在讲什么',
    icon: '①',
  },
  drill: {
    label: '演练关',
    short: '演练',
    desc: `答对 ${DRILL_NEED} 道动手题：编程 / 看输出 / 改错 / 设计，得自己写出来`,
    icon: '②',
  },
  boss: {
    label: 'BOSS 关',
    short: 'BOSS',
    desc: '答对本章最硬的那道题，并清掉本章所有野生怪物',
    icon: '③',
  },
};

export interface StageView {
  key: StageKey;
  label: string;
  icon: string;
  weight: number;
  done: boolean;
  /** 已完成的目标数 */
  got: number;
  /** 需要完成的目标数 */
  need: number;
  /** 一句话状态，直接显示在卡片上 */
  hint: string;
  /** 点「去攻这一关」时锁定的题型 */
  type: BankType | 'all';
  /** BOSS 关指名要打的那道题 */
  questionId?: string;
  /** 还差什么（BOSS 关的怪物挡路会写在这里） */
  blockers: string[];
}

/** 这一章的「最硬一题」：hard → medium → easy，取同档最后一题（题序通常由浅入深） */
export function bossQuestionOf(chapterId: string): BankExercise | null {
  const list = exercisesOfChapter(chapterId);
  if (list.length === 0) return null;
  for (const diff of ['hard', 'medium', 'easy'] as const) {
    const pool = list.filter((e) => e.diff === diff);
    if (pool.length) return pool[pool.length - 1];
  }
  return list[list.length - 1];
}

/** 这道题现在算不算「过了」——只在最近一次作答为正确时为真 */
export function isSolved(id: string, st: ProgressState): boolean {
  return st.answers?.[id]?.ok === true;
}

/** 该章还没收服的怪物数：BOSS 关的门闩 */
export function wildInChapter(chapterId: string, st: ProgressState): number {
  let n = 0;
  for (const m of Object.values(st.bestiary)) {
    if (m.state === 'wild' && m.chapterId === chapterId) n += 1;
  }
  return n;
}

/**
 * 一章的三关状态。纯函数：只读 state，不写、不发事件。
 * LearnPage 展示、progress 的 reducer 判定、NextAction 选关都调它，
 * 保证「看到的」和「算进去的」是同一套规则。
 */
export function chapterStages(chapterId: string, st: ProgressState): StageView[] {
  const list = exercisesOfChapter(chapterId);
  const conceptPool = list.filter((e) => CONCEPT_TYPES.includes(e.type));
  const drillPool = list.filter((e) => DRILL_TYPES.includes(e.type));

  // 概念关：没有概念题时退化为「任意一题」，不然这一关永远无法完成
  const conceptTarget = conceptPool.length ? conceptPool : list;
  const conceptGot = conceptTarget.filter((e) => isSolved(e.id, st)).length;
  const conceptNeed = conceptTarget.length ? 1 : 0;

  const drillNeed = Math.min(DRILL_NEED, drillPool.length);
  const drillGot = drillPool.filter((e) => isSolved(e.id, st)).length;

  const boss = bossQuestionOf(chapterId);
  const wild = wildInChapter(chapterId, st);
  const bossOk = !!boss && isSolved(boss.id, st);
  const bossBlockers: string[] = [];
  if (boss && !bossOk) bossBlockers.push(`还没答对「${boss.title}」`);
  if (wild > 0) bossBlockers.push(`本章还有 ${wild} 只野生怪物没收服`);

  const views: StageView[] = [
    {
      key: 'concept',
      label: STAGE_META.concept.label,
      icon: STAGE_META.concept.icon,
      weight: STAGE_WEIGHT.concept,
      done: conceptNeed > 0 && conceptGot >= conceptNeed,
      got: Math.min(conceptGot, conceptNeed),
      need: conceptNeed,
      hint:
        conceptNeed === 0
          ? '这一章还没有配套题，去题库补充题目后才能判定'
          : conceptGot >= conceptNeed
            ? '概念已通过'
            : `答对 ${conceptNeed - conceptGot} 道概念题即可通过`,
      type: 'all',
      blockers: conceptNeed === 0 ? ['本章没有题目'] : [],
    },
    {
      key: 'drill',
      label: STAGE_META.drill.label,
      icon: STAGE_META.drill.icon,
      weight: STAGE_WEIGHT.drill,
      done: drillNeed > 0 && drillGot >= drillNeed,
      got: Math.min(drillGot, drillNeed),
      need: drillNeed,
      hint:
        drillNeed === 0
          ? '这一章没有动手题，靠 BOSS 关判定'
          : drillGot >= drillNeed
            ? '动手题已达标'
            : `还差 ${drillNeed - drillGot} 道动手题`,
      type: 'all',
      blockers: drillNeed === 0 ? ['本章没有动手题'] : [],
    },
    {
      key: 'boss',
      label: STAGE_META.boss.label,
      icon: STAGE_META.boss.icon,
      weight: STAGE_WEIGHT.boss,
      done: bossOk && wild === 0,
      got: (bossOk ? 1 : 0) + (wild === 0 ? 1 : 0),
      need: 2,
      hint:
        bossOk && wild === 0
          ? '首领已被击败，这一章收工'
          : boss
            ? `首领题：${boss.diff === 'hard' ? '困难' : boss.diff === 'medium' ? '中等' : '简单'} · ${boss.title}`
            : '本章没有题目',
      type: boss?.type ?? 'all',
      questionId: boss?.id,
      blockers: bossBlockers,
    },
  ];
  return views;
}

/** 三关里第一关没过的（给 CTA 用）；全过则返回 null */
export function nextStageOf(chapterId: string, st: ProgressState): StageView | null {
  return chapterStages(chapterId, st).find((v) => !v.done) ?? null;
}
