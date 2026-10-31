/**
 * gameTypes.ts —— 玩法侧的数据契约（P0 打底）
 * ============================================================================
 * 这里只放「纯类型 + 纯常量 + 纯函数」，不 import 任何 React、不碰 localStorage。
 * 原因：progress.ts 要写状态、bestiary.ts 要读状态、feedback.ts 要播动画，
 * 三者都需要同一套类型。类型放在最底层，才不会出现 progress ↔ bestiary 的循环依赖。
 *
 * 与 progress.ts 的分工：
 *   gameTypes  定义"长什么样"
 *   progress   负责"怎么变"（唯一写入口 dispatch）
 *   bestiary   负责"怎么展示"（稀有度、素材、八股匹配）
 * ============================================================================
 */

export type Theme = 'light' | 'dark';

/* ------------------------------------------------------------------ 金币 */

/** 一笔金币变动。只保留最近 50 条，背包页展示最近 10 笔。 */
export interface CoinEntry {
  ts: number;
  /** 正数是收入，负数是支出 */
  delta: number;
  /** 必须写人能看懂的原因，否则「结晶」就只是个装饰数字 */
  reason: string;
}

/* ---------------------------------------------------------------- 怪物 */

export type MonsterState = 'wild' | 'tamed';

/**
 * 一只怪物 = 一道做错过的题。
 * 为什么以 questionId 为 key：题库 id 稳定（cpp-ch01-03），
 * 图鉴、每日试炼、错题重做三处都靠它对齐，不需要额外的关系表。
 */
export interface Monster {
  questionId: string;
  chapterId: string;
  subject: string;
  state: MonsterState;
  /** 累计失败次数 = 血量。答对一次即收服，但会记住它曾经多难打 */
  fails: number;
  firstAt: number;
  lastAt: number;
  tamedAt?: number;
  /** 题目快照：题库改版后图鉴仍然可读，不会变成空白卡片 */
  title: string;
  /** easy / medium / hard，决定稀有度 */
  diff: string;
  /** choice / coding / output / fix_error / explain / design */
  qtype: string;
}

export type Rarity = 'common' | 'elite' | 'boss' | 'shiny';

export const RARITY_META: Record<
  Rarity,
  { label: string; color: string; coin: number; ring: string }
> = {
  common: { label: '普通', color: '#7f9bb5', coin: 6, ring: 'rgb(127 155 181 / 0.5)' },
  elite: { label: '精英', color: '#5b9bd5', coin: 12, ring: 'rgb(91 155 213 / 0.55)' },
  boss: { label: '首领', color: '#9b6ed8', coin: 24, ring: 'rgb(155 110 216 / 0.55)' },
  shiny: { label: '变异', color: '#c9971f', coin: 36, ring: 'rgb(201 151 31 / 0.6)' },
};

/**
 * 稀有度 = 题目难度，失败 ≥3 次再叠一层「变异」。
 *
 * 为什么用 fails 而不是随机数：随机闪光等于编数据；
 * 而「同一只怪反复打不过」是玩家真实制造的难度，标成变异才站得住。
 */
export function rarityOf(diff?: string, fails = 0): Rarity {
  const base: Rarity =
    diff === 'hard' ? 'boss' : diff === 'easy' ? 'common' : 'elite';
  return fails >= 3 ? 'shiny' : base;
}

/* ------------------------------------------------------------ 章节三关 */

/**
 * 一道题的「最近一次」作答。三关判定只认这个：
 *   ok=true  → 这题现在算会
 *   ok=false → 这题现在算不会（哪怕以前做对过）
 * 这正是「重做一次答错，关卡会掉」的原因 —— 不是惩罚，是如实记录。
 */
export interface AnswerMark {
  chapterId: string;
  ok: boolean;
  at: number;
}

/**
 * 每章三关：概念 30 / 演练 30 / BOSS 40 → mastery 0~100。
 * P1 只写入 attempts（记录尝试），三关判定在 P2 打开。
 * 先把结构放好，是为了让 P2 不再改 schema（改 schema = 用户掉档）。
 */
export interface ChapterRun {
  concept: 0 | 1;
  drill: 0 | 1;
  boss: 0 | 1;
  attempts: number;
  lastAt: number;
}

export const STAGE_WEIGHT = { concept: 30, drill: 30, boss: 40 } as const;
export type StageKey = keyof typeof STAGE_WEIGHT;

export function emptyChapterRun(): ChapterRun {
  return { concept: 0, drill: 0, boss: 0, attempts: 0, lastAt: 0 };
}

/** 掌握度：三关权重累加，0~100 */
export function masteryOf(run?: ChapterRun): number {
  if (!run) return 0;
  return (run.concept ? STAGE_WEIGHT.concept : 0) + (run.drill ? STAGE_WEIGHT.drill : 0) + (run.boss ? STAGE_WEIGHT.boss : 0);
}

/* ------------------------------------------------------------ 每日试炼 */

export interface DailyRun {
  /** YYYY-MM-DD，跨日即重建 */
  date: string;
  qids: string[];
  done: string[];
  correct: string[];
  /** 3/3 后已发奖，防止刷新重复领 */
  claimed: boolean;
}

/* ------------------------------------------------------------ 周 BOSS */

/**
 * 一周一次的外环挑战（P3 · S4）。
 *
 * 为什么单独一个结构，而不是复用 DailyRun：
 *   每日试炼是「日常」，跨日即重建、不设门槛；
 *   周 BOSS 是「周考」，有前置门槛、有一次性大奖、跨章出题。
 *   两者生命周期不同（跨日 vs 跨周），合并只会让两边都别扭。
 *
 * qids 存在状态里而不是每次重算，理由同 DailyRun：
 *   一周内刷新页面必须看到同一套题，否则玩家会怀疑自己进度丢了。
 */
export interface WeeklyRun {
  /** ISO 周，形如 2026-W44（周一为界） */
  week: string;
  /** 本周 Boss 所在章节 */
  chapterId: string;
  /** 三道题（本章最硬的三道，hard 优先） */
  qids: string[];
  done: string[];
  correct: string[];
  /** 奖励是否已发，防刷新重复领 */
  claimed: boolean;
  /** 首次通关时刻 */
  clearedAt?: number;
}

/** 周 BOSS 通关奖励：比每日试炼（50~70）高一个量级，才对得起"一周一次" */
export const WEEKLY_REWARD = { coins: 150, shards: 2 } as const;
/** 门槛：本周答对多少题才有资格挑战 */
export const WEEKLY_GATE_CORRECT = 6;
/** 一周出几道题 */
export const WEEKLY_SIZE = 3;

/* -------------------------------------------------------------- 状态 */

export interface ProgressState {
  theme: Theme;
  /** 当前穿的套装 id（见 pages/DressPage 的 OUTFITS） */
  outfit: string;
  /**
   * 已拥有的套装 id。
   * `default` 永远在内；购买过的追加进来。
   * 单独一个字段而不是「看余额推断」，是因为金币会被花掉——
   * 余额低不代表没买过，那件衣服已经是你的了。
   */
  ownedOutfits: string[];
  /** 已通关的项目 slug */
  doneProjects: string[];
  /** 已掌握的章节 id —— v2 起是 mastery===100 的派生结果，保留字段用于同步与兼容 */
  doneChapters: string[];
  /** 打卡日期 YYYY-MM-DD */
  checkins: string[];
  /** 经验结晶 */
  coins: number;
  /** 金币流水（最近 50 条，最新在前） */
  coinLedger: CoinEntry[];
  /** 图鉴：key = questionId */
  bestiary: Record<string, Monster>;
  /** 章节三关进度：key = chapterId */
  chapterRuns: Record<string, ChapterRun>;
  /** 每题最近一次作答：三关判定的唯一输入（key = questionId） */
  answers: Record<string, AnswerMark>;
  /** 今日试炼；null 表示今天还没生成 */
  daily: DailyRun | null;
  /** 本周 BOSS；null 表示本周还没生成 */
  weekly: WeeklyRun | null;
  /** 装扮碎片（P3 抽取用，先留字段避免二次迁移） */
  shards: number;
}

/* -------------------------------------------------------------- 事件 */

/**
 * 所有玩家动作的唯一表达形式。页面不再直接改 doneChapters，
 * 而是 dispatch 一个事件，由 progress.ts 的 reducer 统一算派生状态。
 */
export type ProgressEvent =
  | {
      type: 'answer';
      questionId: string;
      chapterId?: string;
      subject?: string;
      title?: string;
      diff?: string;
      qtype?: string;
      ok: boolean;
      /** 判定来源：客观题 / 判题台 / 自评 */
      mode?: 'objective' | 'judge' | 'self';
    }
  | { type: 'stage'; chapterId: string; stage: StageKey; ok: boolean }
  | { type: 'project'; slug: string; ok: boolean }
  | { type: 'checkin'; date: string }
  | { type: 'daily'; questionId: string; ok: boolean }
  /** 生成/重置今日三题（跨日或首次进入时由 daily.ts 触发） */
  | { type: 'dailyReset'; run: DailyRun }
  | { type: 'weekly'; questionId: string; ok: boolean }
  /** 生成/重置本周 BOSS（跨周或首次进入时由 weekly.ts 触发） */
  | { type: 'weeklyReset'; run: WeeklyRun }
  | { type: 'chapter'; chapterId: string; ok: boolean }
  | { type: 'coin'; delta: number; reason: string };

/** dispatch 的回执，供调用方做就地提示（不依赖 toast） */
export interface AnswerResult {
  /** 这次动作是否产生了新怪物 */
  created: boolean;
  /** 这次动作是否完成收服 */
  tamed: boolean;
  /** 这只怪当前状态；没有怪物时为 null */
  monster: Monster | null;
  /** 本次获得的结晶（0 表示没有奖励） */
  coins: number;
  /** 一句话结果，UI 可以直接显示 */
  message: string;
}
