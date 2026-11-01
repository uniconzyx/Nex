/**
 * progress.ts —— 本地进度（离线可用，v2）
 * ============================================================================
 * 桌面端与手机端共用同一份实现：写 localStorage，不依赖后端。
 * 这样 .exe 和 .apk 在完全断网、没有 PostgreSQL 的情况下，功能与内容仍然一致。
 * 接后端后只需在同步层把这里的快照 POST 上去，UI 不用改。
 *
 * 【v1 → v2 改了什么，为什么】
 *   v1 只有 6 个字段，其中学习数据只有两个布尔集合（doneChapters / doneProjects）。
 *   于是「做错一道题」这件事在系统里不留痕迹：判题结果随会话消失，图鉴永远是空的，
 *   260 条八股没人读，979 道题做完就忘。可玩性缺的不是动画，是**因果没有被记录**。
 *
 *   v2 补四张表：
 *     bestiary    错题 → 怪物（questionId 为 key，含失败次数、首次/收服时间）
 *     chapterRuns 章节三关（concept/drill/boss + attempts），为掌握度做准备
 *     daily       今日试炼（3 题 + 完成/答对集合 + 是否已发奖）
 *     coinLedger  金币流水（每笔都有原因，余额不可为负）
 *
 * 【唯一写入口】
 *   所有变更走 dispatch(event) → reducer → commit。页面不直接 setState 存储，
 *   否则新增一个维度就要改 N 个页面（v1 的病根）。
 *
 * 【迁移策略】
 *   v2 键 kaimao.progress.v2；首次读取时从 v1 迁移，并**原样备份**到
 *   kaimao.progress.v1.backup。迁移只做加法：v1 里已掌握的章节直接置 100 掌握度，
 *   一个都不丢；任何脏数据都不许导致白屏，逐字段 sanitize 后回默认。
 * ============================================================================
 */
import { useEffect, useState } from 'react';

import {
  emptyChapterRun,
  masteryOf,
  RARITY_META,
  rarityOf,
  STAGE_WEIGHT,
  WEEKLY_REWARD,
  type AnswerMark,
  type AnswerResult,
  type ChapterRun,
  type CoinEntry,
  type Monster,
  type ProgressEvent,
  type ProgressState,
  type StageKey,
  type Theme,
} from './gameTypes';
import { chapterStages, STAGE_META } from './stages';
import { chapterName } from './graph';
import { pulseCoins, pushEncounter, pushSettlement, pushToast } from './feedback';
import { flashMood } from './mood';

export type { Theme, ProgressState, AnswerResult } from './gameTypes';

const KEY = 'kaimao.progress.v2';
const KEY_V1 = 'kaimao.progress.v1';
const KEY_V1_BACKUP = 'kaimao.progress.v1.backup';
const LEGACY_PROJECTS = 'kaimao.projects.done';

/** 金币流水只留最近 50 条：再多就是日志，不是流水 */
const LEDGER_LIMIT = 50;

const DEFAULT_STATE: ProgressState = {
  theme: 'light',
  outfit: 'default',
  ownedOutfits: ['default'],
  doneProjects: [],
  doneChapters: [],
  checkins: [],
  coins: 1280,
  coinLedger: [],
  bestiary: {},
  chapterRuns: {},
  answers: {},
  daily: null,
  weekly: null,
  shards: 0,
};

/* ------------------------------------------------------------ sanitize */

function strArray(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [];
}

function num(v: unknown, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function sanitizeBestiary(v: unknown): Record<string, Monster> {
  if (!v || typeof v !== 'object') return {};
  const out: Record<string, Monster> = {};
  for (const [key, raw] of Object.entries(v as Record<string, unknown>)) {
    if (!raw || typeof raw !== 'object') continue;
    const m = raw as Partial<Monster>;
    if (!m.questionId) continue;
    out[key] = {
      questionId: String(m.questionId),
      chapterId: String(m.chapterId ?? ''),
      subject: String(m.subject ?? ''),
      state: m.state === 'tamed' ? 'tamed' : 'wild',
      fails: Math.max(1, Math.round(num(m.fails, 1))),
      firstAt: num(m.firstAt, Date.now()),
      lastAt: num(m.lastAt, num(m.firstAt, Date.now())),
      tamedAt: m.tamedAt ? num(m.tamedAt) : undefined,
      title: String(m.title ?? m.questionId),
      diff: String(m.diff ?? 'medium'),
      qtype: String(m.qtype ?? 'choice'),
    };
  }
  return out;
}

function sanitizeRuns(v: unknown): Record<string, ChapterRun> {
  if (!v || typeof v !== 'object') return {};
  const out: Record<string, ChapterRun> = {};
  for (const [key, raw] of Object.entries(v as Record<string, unknown>)) {
    if (!raw || typeof raw !== 'object') continue;
    const r = raw as Partial<ChapterRun>;
    out[key] = {
      concept: r.concept ? 1 : 0,
      drill: r.drill ? 1 : 0,
      boss: r.boss ? 1 : 0,
      attempts: Math.max(0, Math.round(num(r.attempts, 0))),
      lastAt: num(r.lastAt, 0),
    };
  }
  return out;
}

function sanitizeAnswers(v: unknown): Record<string, AnswerMark> {
  if (!v || typeof v !== 'object') return {};
  const out: Record<string, AnswerMark> = {};
  for (const [key, raw] of Object.entries(v as Record<string, unknown>)) {
    if (!raw || typeof raw !== 'object') continue;
    const a = raw as Partial<AnswerMark>;
    out[key] = {
      chapterId: String(a.chapterId ?? ''),
      ok: a.ok === true,
      at: num(a.at, 0),
    };
  }
  return out;
}

function sanitizeLedger(v: unknown): CoinEntry[] {
  if (!Array.isArray(v)) return [];
  return v
    .filter((x): x is CoinEntry => !!x && typeof x === 'object' && Number.isFinite(Number((x as CoinEntry).delta)))
    .map((x) => ({
      ts: num(x.ts, Date.now()),
      delta: Math.round(num(x.delta)),
      reason: String(x.reason ?? ''),
    }))
    .slice(0, LEDGER_LIMIT);
}

function sanitizeDaily(v: unknown): ProgressState['daily'] {
  if (!v || typeof v !== 'object') return null;
  const d = v as Record<string, unknown>;
  const date = typeof d.date === 'string' ? d.date : '';
  if (!date) return null;
  return {
    date,
    qids: strArray(d.qids),
    done: strArray(d.done),
    correct: strArray(d.correct),
    claimed: !!d.claimed,
  };
}

/**
 * 周 BOSS 的状态清洗。
 *
 * 与 daily 的差别：weekly 多两个字段（chapterId / claimed / clearedAt），
 * 而且**必须校验 week 形状**。理由：weekly 决定"本周要不要重算题单"，
 * 一个脏 week（比如被手工改成空串）会让 shouldRebuild 永远为真，
 * 于是每次进首页都重新出题 —— 越修越乱。这里直接判成 null，让它重建。
 */
function sanitizeWeekly(v: unknown): ProgressState['weekly'] {
  if (!v || typeof v !== 'object') return null;
  const w = v as Record<string, unknown>;
  const week = typeof w.week === 'string' ? w.week : '';
  const chapterId = typeof w.chapterId === 'string' ? w.chapterId : '';
  if (!/^\d{4}-W\d{2}$/.test(week) || !chapterId) return null;
  return {
    week,
    chapterId,
    qids: strArray(w.qids),
    done: strArray(w.done),
    correct: strArray(w.correct),
    claimed: !!w.claimed,
    clearedAt: typeof w.clearedAt === 'number' ? w.clearedAt : undefined,
  };
}

/**
 * 三关是「作答记录」的投影，不是另一份独立数据。
 *
 * 这一条是 P2 的核心不变量：只要一章有作答记录，它的 concept/drill/boss
 * 三个标记就必须由 lib/stages.ts 的规则重新算出来，而不是信任磁盘上存的旧值。
 * 不这么做的后果，E2E 里真实出现过：
 *   预置了 answers（题都做对了）但没预置 chapterRuns →
 *   关卡卡片显示「三关全过」，顶上的掌握度却是 0%，两个数字互相打脸。
 *   真实世界里对应「旧版本升级上来」和「手动改过 localStorage」两种情形。
 *
 * 反过来，没有作答记录的章节（v1 迁移的 doneChapters、手动标记）保留现有标记，
 * 不会被这条投影抹掉。
 */
function deriveRuns(s: ProgressState): ProgressState {
  const ids = new Set<string>();
  const lastAtByChapter: Record<string, number> = {};
  for (const a of Object.values(s.answers ?? {})) {
    if (!a.chapterId) continue;
    ids.add(a.chapterId);
    lastAtByChapter[a.chapterId] = Math.max(lastAtByChapter[a.chapterId] ?? 0, a.at);
  }
  if (ids.size === 0) return s;

  const runs = { ...s.chapterRuns };
  for (const id of ids) {
    const run = { ...(runs[id] ?? emptyChapterRun()) };
    for (const view of chapterStages(id, s)) {
      run[view.key] = view.done ? 1 : 0;
    }
    run.lastAt = Math.max(run.lastAt, lastAtByChapter[id] ?? 0);
    runs[id] = run;
  }
  return { ...s, chapterRuns: runs };
}

/**
 * 保证「doneChapters ⇔ 掌握度 100」这条不变量（P2 起是**双向**的）。
 *
 *   只有 doneChapters、没有 chapterRuns 的章节（v1 迁移来的 / 手动标记的）→ 补成三关全通；
 *   有 chapterRuns 的章节 → doneChapters **由掌握度推出**，不再反过来覆盖它。
 *
 * 第二点是 P2 才修的：旧实现把 doneChapters 里的章节一律填成 100，
 * 于是「BOSS 关失守 → 掌握度掉到 60」会被下一行 normalize 又改回 100，
 * 掌握度永远不会掉。现在谁说了算很清楚：chapterRuns 是事实，doneChapters 是它的投影。
 */
function normalize(s: ProgressState): ProgressState {
  const derived = deriveRuns(s);
  const runs = { ...derived.chapterRuns };
  for (const id of derived.doneChapters) {
    if (!runs[id]) {
      runs[id] = { concept: 1, drill: 1, boss: 1, attempts: 1, lastAt: 0 };
    }
  }
  const done: string[] = [];
  for (const [id, r] of Object.entries(runs)) {
    if (masteryOf(r) === 100) done.push(id);
  }
  return { ...derived, chapterRuns: runs, doneChapters: done };
}

/* ------------------------------------------------------------------ 读 */

function migrateV1(raw: string): ProgressState {
  try {
    const parsed = JSON.parse(raw) as Partial<ProgressState>;
    const base: ProgressState = {
      ...DEFAULT_STATE,
      theme: parsed.theme === 'dark' ? 'dark' : 'light',
      outfit: typeof parsed.outfit === 'string' ? parsed.outfit : 'default',
      doneProjects: strArray(parsed.doneProjects),
      doneChapters: strArray(parsed.doneChapters),
      checkins: strArray(parsed.checkins),
      coins: Math.max(0, Math.round(num(parsed.coins, DEFAULT_STATE.coins))),
    };
    if (typeof localStorage !== 'undefined') {
      // 原样备份一份：迁移出问题时用户还能手工找回
      try {
        localStorage.setItem(KEY_V1_BACKUP, raw);
      } catch {
        /* 配额满就跳过备份，不能因此阻断迁移 */
      }
    }
    return normalize(base);
  } catch {
    return { ...DEFAULT_STATE };
  }
}

/**
 * 把任意来源的原始对象收敛成合法 ProgressState。
 *
 * 抽出来是为了让「启动时读盘」和「导入备份文件」走**同一套校验**。
 * 两条路径各写一份的结果一定是分叉：某天给某个字段加了约束，
 * 只改了一处，另一处就把脏数据放进来了。
 */
function sanitizeState(parsed: Partial<ProgressState>): ProgressState {
  const outfit = typeof parsed.outfit === 'string' ? parsed.outfit : 'default';
  /**
   * 已拥有 = 记录里的 + default + 当前正穿的那件。
   *
   * 补「当前正穿」这一项是在兼容老数据：装扮收费之前，任何人都能随便点着换，
   * 身上那件从来没花过钱。升级到收费版后不能突然把用户衣服扒掉——
   * 他现在穿着的，就当作已经拥有。
   */
  const owned = Array.from(new Set(['default', ...strArray(parsed.ownedOutfits), outfit]));
  return normalize({
    theme: parsed.theme === 'dark' ? 'dark' : 'light',
    outfit,
    ownedOutfits: owned,
    doneProjects: strArray(parsed.doneProjects),
    doneChapters: strArray(parsed.doneChapters),
    checkins: strArray(parsed.checkins),
    coins: Math.max(0, Math.round(num(parsed.coins, DEFAULT_STATE.coins))),
    coinLedger: sanitizeLedger(parsed.coinLedger),
    bestiary: sanitizeBestiary(parsed.bestiary),
    chapterRuns: sanitizeRuns(parsed.chapterRuns),
    answers: sanitizeAnswers(parsed.answers),
    daily: sanitizeDaily(parsed.daily),
    weekly: sanitizeWeekly(parsed.weekly),
    shards: Math.max(0, Math.round(num(parsed.shards, 0))),
  });
}

/**
 * 读取时顺手把「派生结果」写回去。
 *
 * 为什么要在启动时写一次：chapterRuns 是从 answers 推出来的投影，
 * 但磁盘上可能还是旧版本留下的空壳（升级用户、被手工改过的 localStorage）。
 * 内存里已经算对了，如果只停留在内存，那么刷新前任何读 localStorage 的地方
 * （同步层快照、调试面板）看到的都是「关卡数 0」——同一份数据两个答案。
 *
 * 只在内容真的变了才写，避免每次启动都触发一次无意义的序列化。
 */
function persistQuietly(state: ProgressState, prevRaw: string | null): void {
  if (typeof localStorage === 'undefined') return;
  try {
    const nextRaw = JSON.stringify(state);
    if (nextRaw !== prevRaw) localStorage.setItem(KEY, nextRaw);
  } catch {
    /* 隐私模式 / 配额满：内存里已经生效，不值得为此报错 */
  }
}

function read(): ProgressState {
  if (typeof localStorage === 'undefined') return { ...DEFAULT_STATE };
  const raw = localStorage.getItem(KEY);
  let state: ProgressState | null = null;
  try {
    if (raw) {
      state = sanitizeState(JSON.parse(raw) as Partial<ProgressState>);
    } else {
      const v1 = localStorage.getItem(KEY_V1);
      if (v1) {
        state = migrateV1(v1);
      } else {
        // 兼容设计稿时代的键，避免换壳后通关记录凭空消失
        const legacy = localStorage.getItem(LEGACY_PROJECTS);
        if (legacy) {
          const arr = JSON.parse(legacy);
          if (Array.isArray(arr)) state = normalize({ ...DEFAULT_STATE, doneProjects: arr.map(String) });
        }
      }
    }
  } catch {
    /* 坏数据直接回默认，不要因为一条脏记录白屏 */
  }
  const final = state ?? { ...DEFAULT_STATE };
  persistQuietly(final, raw);
  return final;
}

let current: ProgressState = read();
const listeners = new Set<(s: ProgressState) => void>();

/** 同步钩子由 sync.ts 注册，避免 progress ↔ session ↔ api 之间形成循环依赖 */
type SyncHook = (snapshot: ProgressState) => void;
let onCommit: SyncHook | null = null;

export function setProgressSyncHook(fn: SyncHook | null): void {
  onCommit = fn;
}

function commit(next: ProgressState): void {
  current = next;
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* 隐私模式 / 配额满：内存里仍然生效 */
    }
  }
  for (const fn of listeners) fn(next);
  // 推送失败一律吞掉：本地是事实源，网络只做镜像
  try {
    onCommit?.(next);
  } catch {
    /* noop */
  }
}

/** 用云端快照合并本地（并集语义），只往回补，不删本地记录 */
export function mergeRemote(remote: {
  done_chapters?: string[];
  done_projects?: string[];
  checkins?: string[];
  coins?: number;
}): boolean {
  const doneChapters = Array.from(new Set([...current.doneChapters, ...(remote.done_chapters ?? [])]));
  const doneProjects = Array.from(new Set([...current.doneProjects, ...(remote.done_projects ?? [])]));
  const checkins = Array.from(new Set([...current.checkins, ...(remote.checkins ?? [])])).sort();
  const coins = Math.max(current.coins, remote.coins ?? 0);
  const same =
    doneChapters.length === current.doneChapters.length &&
    doneProjects.length === current.doneProjects.length &&
    checkins.length === current.checkins.length &&
    coins === current.coins;
  if (same) return false;
  // 用 silent commit：合并结果不该反过来再推一次（会造成回环）
  current = normalize({ ...current, doneChapters, doneProjects, checkins, coins });
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(KEY, JSON.stringify(current));
    } catch {
      /* noop */
    }
  }
  for (const fn of listeners) fn(current);
  return true;
}

/* ------------------------------------------------------ 云端整份快照 */

/**
 * 用云端**整份快照**合并本地（本地账号服务 auth-server 走这条）。
 *
 * 与 mergeRemote 的区别：
 *   mergeRemote 只认 5 个字段（Nex 后端的历史形状）——章节/项目/打卡/金币，
 *   带不来 answers / bestiary / chapterRuns，换设备后掌握度会归零（题白做）。
 *   这里走 sanitizeState，接受完整 ProgressState，于是「换机」真的能换回来。
 *
 * 合并方向刻意写成 mergeStates(remote, local)：
 *   把**云端当底、本机当覆盖**。于是
 *     · answers / bestiary 逐键并集，同键时本机优先（本机刚答的题不会被打回旧状态）；
 *     · theme / outfit 跟本机走（换到新设备不该被别人电脑上的外观覆盖）；
 *     · coins 取 max（进度只能变多，不能因为换设备变少）。
 *   反过来传（local 当底）会让云端旧答案覆盖本机新答案，是数据倒退，别改。
 *
 * @returns 是否真的改变了本机数据（用于决定要不要回推）
 */
export function mergeRemoteSnapshot(remote: unknown): boolean {
  if (!remote || typeof remote !== 'object' || Array.isArray(remote)) return false;
  const o = remote as Record<string, unknown>;
  // 与 parseProgressFile 同一套签名：宁可拒绝，也不要把一个空对象 merge 进来
  const signature = ['doneChapters', 'doneProjects', 'checkins', 'answers', 'chapterRuns', 'bestiary', 'coins'];
  if (!signature.some((k) => k in o)) return false;

  const before = JSON.stringify(current);
  const incoming = sanitizeState(o as Partial<ProgressState>);
  const merged = sanitizeState(mergeStates(incoming, current));
  // 用整份序列化比较：只比计数会漏掉「同一题从错变对」这种长度不变的变化
  if (JSON.stringify(merged) === before) return false;

  current = merged;
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(KEY, JSON.stringify(current));
    } catch {
      /* noop */
    }
  }
  for (const fn of listeners) fn(current);
  return true;
}

/* ------------------------------------------------------ 导入（换机迁移） */

export interface ImportPreview {
  chapters: number;
  projects: number;
  checkins: number;
  coins: number;
  answers: number;
  monsters: number;
}

export type ImportResult =
  | { ok: true; mode: 'merge' | 'replace'; state: ProgressState }
  | { ok: false; error: string };

/**
 * 只解析 + 校验，不落盘。
 * 先让用户看清「这个文件里到底有多少东西」再决定要不要吃进来——
 * 直接覆盖是最容易造成不可逆损失的一步，不能藏在一次点击里。
 */
export function parseProgressFile(
  payload: unknown,
): { ok: true; state: ProgressState } | { ok: false; error: string } {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return { ok: false, error: '这不是一个 JSON 对象：请选择导出的 kaimao-progress-*.json 文件' };
  }
  const o = payload as Record<string, unknown>;
  // 导出文件本身就是 ProgressState；顺手兼容被包在 { progress: ... } 里的写法
  const inner =
    o.progress && typeof o.progress === 'object' && !Array.isArray(o.progress)
      ? (o.progress as Record<string, unknown>)
      : o;
  const signature = ['doneChapters', 'doneProjects', 'checkins', 'answers', 'chapterRuns', 'bestiary', 'coins'];
  if (!signature.some((k) => k in inner)) {
    return {
      ok: false,
      error: '字段对不上：缺 doneChapters / answers / coins 这类进度字段，这不是进度备份文件',
    };
  }
  return { ok: true, state: sanitizeState(inner as Partial<ProgressState>) };
}

export function previewOf(s: ProgressState): ImportPreview {
  return {
    chapters: s.doneChapters.length,
    projects: s.doneProjects.length,
    checkins: s.checkins.length,
    coins: s.coins,
    answers: Object.keys(s.answers ?? {}).length,
    monsters: Object.keys(s.bestiary ?? {}).length,
  };
}

/**
 * 合并语义（默认）：集合取并集、对象浅合并（备份优先）、金币取大。
 * 绝不因为导入而抹掉本机已有记录——导入是为了「找回来」，不是为了「换掉」。
 */
function mergeStates(local: ProgressState, incoming: ProgressState): ProgressState {
  const uniq = (a: string[], b: string[]) => Array.from(new Set([...a, ...b]));
  return {
    // theme / outfit 跟备份走：换机的人希望自己的外观一起回来
    ...incoming,
    doneChapters: uniq(local.doneChapters, incoming.doneChapters),
    doneProjects: uniq(local.doneProjects, incoming.doneProjects),
    checkins: uniq(local.checkins, incoming.checkins).sort(),
    coins: Math.max(local.coins, incoming.coins),
    shards: Math.max(local.shards, incoming.shards),
    answers: { ...local.answers, ...incoming.answers },
    bestiary: { ...local.bestiary, ...incoming.bestiary },
    chapterRuns: { ...local.chapterRuns, ...incoming.chapterRuns },
    daily: incoming.daily ?? local.daily,
    coinLedger: incoming.coinLedger.length ? incoming.coinLedger : local.coinLedger,
  };
}

/** 只写本地并广播给 UI，不触发云端推送（原因见 importProgress 注释） */
function commitLocalOnly(next: ProgressState): void {
  current = next;
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* 隐私模式 / 配额满：内存里已生效 */
    }
  }
  for (const fn of listeners) fn(next);
}

/**
 * 从导出的 JSON 还原进度。
 *
 * 为什么不同步推云端：导入的是「某台设备某一天的备份」，直接覆盖远端可能把
 * 服务器上更新的进度抹掉，而且是用户看不见的静默覆盖。所以只写本机，
 * 之后任何一次正常答题都会走常规同步把差异并上去（同步是并集语义，不会丢数据）。
 */
export function importProgress(payload: unknown, mode: 'merge' | 'replace' = 'merge'): ImportResult {
  const parsed = parseProgressFile(payload);
  if (!parsed.ok) return parsed;
  const incoming = parsed.state;
  const base = mode === 'replace' ? incoming : mergeStates(current, incoming);
  const next = sanitizeState(base);
  commitLocalOnly(next);
  return { ok: true, mode, state: next };
}

export function getProgressSnapshot(): ProgressState {
  return current;
}

export function todayKey(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** 连续打卡天数：从今天（或昨天）往前数 */
export function streakOf(checkins: string[]): number {
  const set = new Set(checkins);
  const d = new Date();
  if (!set.has(todayKey(d))) d.setDate(d.getDate() - 1);
  let n = 0;
  while (set.has(todayKey(d))) {
    n += 1;
    d.setDate(d.getDate() - 1);
  }
  return n;
}

/* ------------------------------------------------------------ 金币工具 */

function shortTitle(t: string, max = 14): string {
  const s = t.replace(/\s+/g, ' ').trim();
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

/** 记账 + 顶栏飘字。余额不足时返回 null，调用方负责提示 */
function withCoins(s: ProgressState, delta: number, reason: string): ProgressState | null {
  if (!delta) return s;
  if (s.coins + delta < 0) return null;
  const entry: CoinEntry = { ts: Date.now(), delta, reason };
  pulseCoins(delta);
  return {
    ...s,
    coins: s.coins + delta,
    coinLedger: [entry, ...s.coinLedger].slice(0, LEDGER_LIMIT),
  };
}

/* -------------------------------------------------------------- 派生态 */

export function wildMonsters(s: ProgressState = current): Monster[] {
  return Object.values(s.bestiary)
    .filter((m) => m.state === 'wild')
    .sort((a, b) => b.fails - a.fails || b.lastAt - a.lastAt);
}

export function tamedMonsters(s: ProgressState = current): Monster[] {
  return Object.values(s.bestiary)
    .filter((m) => m.state === 'tamed')
    .sort((a, b) => (b.tamedAt ?? 0) - (a.tamedAt ?? 0));
}

export function bestiaryStats(s: ProgressState = current): {
  wild: number;
  tamed: number;
  total: number;
  fails: number;
  shiny: number;
} {
  const all = Object.values(s.bestiary);
  let wild = 0;
  let tamed = 0;
  let fails = 0;
  let shiny = 0;
  for (const m of all) {
    if (m.state === 'wild') wild += 1;
    else tamed += 1;
    fails += m.fails;
    if (rarityOf(m.diff, m.fails) === 'shiny') shiny += 1;
  }
  return { wild, tamed, total: all.length, fails, shiny };
}

export function chapterMastery(chapterId: string, s: ProgressState = current): number {
  return masteryOf(s.chapterRuns[chapterId]);
}

export function isChapterDone(chapterId: string, s: ProgressState = current): boolean {
  return s.doneChapters.includes(chapterId) || masteryOf(s.chapterRuns[chapterId]) === 100;
}

/** 经验值：章节 20 / 项目 30 / 签到 50 / 收服 8（收服也要给反馈，否则图鉴只是个相册） */
export function expOf(s: ProgressState = current): number {
  const tamed = tamedMonsters(s).length;
  return s.doneChapters.length * 20 + s.doneProjects.length * 30 + s.checkins.length * 50 + tamed * 8;
}

/* ---------------------------------------------------------------- 事件 */

/**
 * 唯一写入口。所有页面都调它，不再直接改字段。
 * 返回 AnswerResult 只对 'answer' 有意义，其余返回 null。
 */
export function dispatch(e: ProgressEvent): AnswerResult | null {
  switch (e.type) {
    case 'answer':
      return applyAnswer(e);
    case 'stage':
      return applyStage(e.chapterId, e.stage, e.ok);
    case 'chapter':
      return applyChapter(e.chapterId, e.ok);
    case 'project':
      return applyProject(e.slug, e.ok);
    case 'checkin':
      return applyCheckin(e.date);
    case 'daily':
      return applyDaily(e.questionId, e.ok);
    case 'dailyReset':
      commit(normalize({ ...current, daily: e.run }));
      return null;
    case 'weekly':
      return applyWeekly(e.questionId, e.ok);
    case 'weeklyReset':
      commit(normalize({ ...current, weekly: e.run }));
      return null;
    case 'coin':
      return applyCoin(e.delta, e.reason);
    default:
      return null;
  }
}

/* -------------------------------------------------------- answer：错题即怪物 */

function applyAnswer(e: Extract<ProgressEvent, { type: 'answer' }>): AnswerResult {
  const now = Date.now();
  const prev = current.bestiary[e.questionId];
  const bestiary = { ...current.bestiary };
  const chapterId = e.chapterId ?? prev?.chapterId ?? '';
  const title = e.title ?? prev?.title ?? e.questionId;
  const diff = e.diff ?? prev?.diff ?? 'medium';
  const qtype = e.qtype ?? prev?.qtype ?? 'choice';

  let next = current;
  let created = false;
  let tamed = false;
  let coins = 0;
  let message = '';

  if (e.ok) {
    if (prev?.state === 'tamed') {
      message = '这道题已经收服过了';
    } else if (prev) {
      // 打过败仗的题终于做对 → 收服。奖励随难度与被打败次数上浮。
      tamed = true;
      const rarity = rarityOf(prev.diff, prev.fails);
      const reward = RARITY_META[rarity].coin + prev.fails * 2;
      bestiary[prev.questionId] = { ...prev, state: 'tamed', tamedAt: now, lastAt: now };
      const after = withCoins(next, reward, `收服「${shortTitle(prev.title)}」`);
      if (after) {
        next = after;
        coins = reward;
      }
      message = `收服成功：${shortTitle(prev.title, 20)}`;
      pushToast({
        kind: 'tame',
        title: `收服 · ${RARITY_META[rarity].label}`,
        desc: prev.title,
        coin: coins,
        icon: '⚔️',
        ttl: 3600,
      });
    } else {
      // 一次就对的题不产生怪物，只给一点即时正反馈
      const reward = 4;
      const after = withCoins(next, reward, `首次答对「${shortTitle(title)}」`);
      if (after) {
        next = after;
        coins = reward;
      }
      message = '答对了';
      pushToast({ kind: 'ok', title: '答对了', desc: title, coin: coins, icon: '✓' });
    }
  } else if (prev) {
    // 同一只怪再被打一次：血量 +1，稀有度可能升级成「变异」
    const fails = prev.fails + 1;
    bestiary[prev.questionId] = { ...prev, fails, lastAt: now };
    const becameShiny = rarityOf(prev.diff, fails) === 'shiny' && rarityOf(prev.diff, prev.fails) !== 'shiny';
    message = `怪物强化 ×${fails}`;
    pushToast({
      kind: 'bad',
      title: becameShiny ? `变异了 ×${fails}` : `怪物强化 ×${fails}`,
      desc: becameShiny ? '失败 3 次以上，它开始发光了' : prev.title,
      icon: '☠',
    });
  } else {
    const monster: Monster = {
      questionId: e.questionId,
      chapterId,
      subject: e.subject ?? '',
      state: 'wild',
      fails: 1,
      firstAt: now,
      lastAt: now,
      title,
      diff,
      qtype,
    };
    bestiary[e.questionId] = monster;
    created = true;
    message = `野生怪物出现：${shortTitle(title, 20)}`;
    pushEncounter({ questionId: e.questionId, chapterId, title, fails: 1, diff, qtype });
  }

  // —— P2：一次作答同时推进三关 ——
  // 这里不再「只记 attempts」。三关的判定规则在 stages.ts，本函数只负责：
  //   1) 记下这道题的最近一次结果（answers 是唯一输入）；
  //   2) 拿新状态重算这一章的三关，写进 chapterRuns；
  //   3) 把「新通过的关 / 掉下去的关 / 第一次三关全通」变成即时反馈 + 奖励。
  const answers: Record<string, AnswerMark> = {
    ...next.answers,
    [e.questionId]: { chapterId, ok: e.ok, at: now },
  };

  const chapterRuns = { ...next.chapterRuns };
  const passed: StageKey[] = [];
  const lost: StageKey[] = [];
  let firstComplete = false;

  if (chapterId) {
    const run = { ...(chapterRuns[chapterId] ?? emptyChapterRun()) };
    const before = masteryOf(run);
    // 用「已经写入本次作答」的临时快照去判定，保证和页面显示同一套规则
    const probe: ProgressState = { ...next, bestiary, answers, chapterRuns };
    for (const view of chapterStages(chapterId, probe)) {
      const flag = view.done ? 1 : 0;
      if (flag && !run[view.key]) passed.push(view.key);
      if (!flag && run[view.key]) lost.push(view.key);
      run[view.key] = flag;
    }
    run.attempts += 1;
    run.lastAt = now;
    chapterRuns[chapterId] = run;
    firstComplete = before < 100 && masteryOf(run) === 100;
  }

  next = normalize({ ...next, bestiary, answers, chapterRuns });

  if (firstComplete) {
    const withReward = withCoins(next, 60, `章节三关全通 ${chapterId}`);
    if (withReward) {
      next = withReward;
      coins += 60;
    }
  }

  commit(next);

  // 反馈放在 commit 之后：commit 会触发页面重渲染，toast 跟着最新状态说话
  for (const key of passed) {
    pushToast({
      kind: 'ok',
      title: `${STAGE_META[key].label}通过`,
      desc: `${chapterNameSafe(chapterId)} · +${STAGE_WEIGHT[key]} 掌握度`,
      icon: STAGE_META[key].icon,
    });
  }
  for (const key of lost) {
    pushToast({
      kind: 'bad',
      title: `${STAGE_META[key].label}失守`,
      desc: `${chapterNameSafe(chapterId)} · 掌握度回落到 ${masteryOf(chapterRuns[chapterId])}`,
      icon: '⚠',
    });
  }
  if (firstComplete) {
    pushToast({
      kind: 'coin',
      title: '三关全通 +60',
      desc: `${chapterNameSafe(chapterId)} · 这一章进图鉴目录了`,
      icon: '★',
      ttl: 4200,
    });
    // 值得停下来看一眼的里程碑 → 全屏结算
    pushSettlement({
      title: '三关全通',
      desc: `${chapterNameSafe(chapterId)} · 这一章进了图鉴目录`,
      stars: 3,
      coins: 60,
      exp: 20,
      expGoal: 300,
      kind: 'chapter',
    });
  }

  return {
    created,
    tamed,
    monster: bestiary[e.questionId] ?? null,
    coins,
    message,
  };
}

/** 章节标题：只在 toast 里用，拿不到就退回 id，绝不让提示变成空白 */
function chapterNameSafe(id: string): string {
  if (!id) return '未归属章节';
  return chapterName(id) || id;
}

/* -------------------------------------------------------------- stage */

function applyStage(chapterId: string, stage: StageKey, ok: boolean): AnswerResult | null {
  const now = Date.now();
  const runs = { ...current.chapterRuns };
  const run = { ...(runs[chapterId] ?? emptyChapterRun()) };
  const before = masteryOf(run);
  if (ok) run[stage] = 1;
  else run[stage] = 0;
  run.attempts += 1;
  run.lastAt = now;
  runs[chapterId] = run;
  const after = masteryOf(run);

  let next: ProgressState = { ...current, chapterRuns: runs };
  const firstComplete = before < 100 && after === 100;
  if (firstComplete) {
    const withReward = withCoins(next, 60, `章节三关全通 ${chapterId}`);
    if (withReward) next = withReward;
    pushToast({ kind: 'ok', title: '章节掌握', desc: `${chapterId} · 三关全通 +60`, icon: '★' });
  }
  commit(normalize(next));
  return null;
}

/* ------------------------------------------------------------- chapter */

function applyChapter(chapterId: string, ok: boolean): AnswerResult | null {
  const has = current.doneChapters.includes(chapterId);
  if (ok === has) return null;
  let next: ProgressState = {
    ...current,
    doneChapters: ok
      ? [...current.doneChapters, chapterId]
      : current.doneChapters.filter((s) => s !== chapterId),
    chapterRuns: {
      ...current.chapterRuns,
      [chapterId]: ok
        ? { concept: 1, drill: 1, boss: 1, attempts: (current.chapterRuns[chapterId]?.attempts ?? 0) + 1, lastAt: Date.now() }
        : emptyChapterRun(),
    },
  };
  if (ok) {
    const after = withCoins(next, 20, `掌握章节 ${chapterId}`);
    if (after) next = after;
    pushToast({ kind: 'ok', title: '章节掌握', desc: `+20 结晶`, icon: '📘' });
  }
  commit(normalize(next));
  return null;
}

/* ------------------------------------------------------------- project */

function applyProject(slug: string, ok: boolean): AnswerResult | null {
  const has = current.doneProjects.includes(slug);
  if (ok === has) return null;
  let next: ProgressState = {
    ...current,
    doneProjects: ok ? [...current.doneProjects, slug] : current.doneProjects.filter((s) => s !== slug),
  };
  if (ok) {
    const after = withCoins(next, 30, `通关项目 ${slug}`);
    if (after) next = after;
    pushToast({ kind: 'ok', title: '项目通关', desc: `+30 结晶 · ${slug}`, icon: '🏆' });
    pushSettlement({
      title: '项目通关',
      desc: `${slug} · 战利品已入库`,
      stars: 3,
      coins: 30,
      exp: 30,
      expGoal: 300,
      kind: 'project',
    });
  }
  commit(normalize(next));
  return null;
}

/* ------------------------------------------------------------- checkin */

function applyCheckin(date: string): AnswerResult | null {
  if (current.checkins.includes(date)) return null;
  const checkins = [...current.checkins, date].sort();
  const streak = streakOf(checkins);
  const reward = 20 + Math.min(streak, 6) * 5;
  let next: ProgressState = { ...current, checkins };
  const after = withCoins(next, reward, `签到 · 连续 ${streak} 天`);
  if (after) next = after;
  pushToast({ kind: 'coin', title: `签到 +${reward}`, desc: `连续 ${streak} 天，明天继续`, icon: '🕯️' });
  pushSettlement({
    title: '签到成功',
    desc: `连续 ${streak} 天 · 明天继续`,
    stars: 1,
    coins: reward,
    exp: 50,
    expGoal: 300,
    kind: 'checkin',
  });
  commit(normalize(next));
  return null;
}

/* --------------------------------------------------------------- daily */

function applyDaily(questionId: string, ok: boolean): AnswerResult | null {
  const daily = current.daily;
  if (!daily || !daily.qids.includes(questionId)) return null;
  const done = daily.done.includes(questionId) ? daily.done : [...daily.done, questionId];
  const correct = ok
    ? daily.correct.includes(questionId)
      ? daily.correct
      : [...daily.correct, questionId]
    : daily.correct.filter((id) => id !== questionId);

  const finished = daily.qids.length > 0 && daily.qids.every((id) => done.includes(id));
  const allCorrect = finished && daily.correct.length === daily.qids.length;
  let next: ProgressState = { ...current, daily: { ...daily, done, correct } };

  if (finished && !daily.claimed) {
    const base = 50;
    const bonus = allCorrect ? 20 : 0;
    const after = withCoins(next, base + bonus, `每日试炼清空${allCorrect ? ' · 全对' : ''}`);
    if (after) next = after;
    next = { ...next, daily: { ...next.daily!, claimed: true } };
    pushToast({
      kind: 'coin',
      title: `今日试炼清空 +${base + bonus}`,
      desc: allCorrect ? '三题全对，额外 +20' : '明天会按错题重新出题',
      icon: '🌙',
      ttl: 4000,
    });
  }
  commit(normalize(next));
  return null;
}

/* -------------------------------------------------------------- weekly */

/**
 * 周 BOSS 的一题作答。
 *
 * 与 applyDaily 的三处不同（都是刻意的）：
 *   1. 没有"门槛判定"。门槛（本周答对 N 题）在 lib/weekly.ts 里由 UI 检查，
 *      reducer 只信 received 的事件 —— 门槛是"展示规则"，不该在写入口重复一遍，
 *      否则两处阈值不同步就会出现「按钮亮了但 reducer 不认」。
 *   2. 答错不撤销已得的奖励，也不降难度：周 BOSS 只有通关/未通关两态。
 *   3. 通关一次性发金币 + 碎片，claimed 落盘防刷新重复领。
 */
function applyWeekly(questionId: string, ok: boolean): AnswerResult | null {
  const weekly = current.weekly;
  if (!weekly || !weekly.qids.includes(questionId)) return null;

  const done = weekly.done.includes(questionId) ? weekly.done : [...weekly.done, questionId];
  const correct = ok
    ? weekly.correct.includes(questionId)
      ? weekly.correct
      : [...weekly.correct, questionId]
    : weekly.correct.filter((id) => id !== questionId);

  const finished = weekly.qids.length > 0 && weekly.qids.every((id) => done.includes(id));
  const allCorrect = finished && correct.length === weekly.qids.length;

  let next: ProgressState = { ...current, weekly: { ...weekly, done, correct } };

  if (allCorrect && !weekly.claimed) {
    const after = withCoins(next, WEEKLY_REWARD.coins, `周 BOSS 通关 · ${weekly.chapterId}`);
    if (after) next = after;
    next = {
      ...next,
      weekly: { ...(next.weekly as NonNullable<ProgressState['weekly']>), claimed: true, clearedAt: Date.now() },
      shards: next.shards + WEEKLY_REWARD.shards,
    };
    pushToast({
      kind: 'coin',
      title: `周 BOSS 通关 +${WEEKLY_REWARD.coins}`,
      desc: `${weekly.chapterId} · 另得 ${WEEKLY_REWARD.shards} 枚碎片`,
      icon: '👑',
      ttl: 4200,
    });
  } else if (finished && !allCorrect) {
    pushToast({
      kind: 'bad',
      title: '周 BOSS 未清空',
      desc: '三道题必须全对；答错的那道会留在原地，重打一次即可',
      icon: '🛡️',
      ttl: 3600,
    });
  }

  commit(normalize(next));
  return null;
}

/* ---------------------------------------------------------------- coin */

function applyCoin(delta: number, reason: string): AnswerResult | null {
  const after = withCoins(current, delta, reason);
  if (!after) {
    pushToast({
      kind: 'bad',
      title: '结晶不足',
      desc: `还差 ${Math.abs(current.coins + delta)} 枚`,
      icon: '◇',
    });
    return null;
  }
  commit(normalize(after));
  return null;
}

/* ------------------------------------------------- 兼容 v1 的页面 API */

export function toggleProject(slug: string): void {
  dispatch({ type: 'project', slug, ok: !current.doneProjects.includes(slug) });
}

export function toggleChapter(id: string): void {
  dispatch({ type: 'chapter', chapterId: id, ok: !current.doneChapters.includes(id) });
}

export function checkinToday(): void {
  dispatch({ type: 'checkin', date: todayKey() });
}

/**
 * 重置一章：三关、作答记录、这一章的怪物一起清掉。
 * 只给「想把这章重打一遍」用，不做成「取消掌握」——
 * 取消掌握会让掌握度归零但答案还在，玩家再答一次同样的题会被判「首次答对」，
 * 等于白拿一次结晶，账就对不上了。要清就清干净。
 */
export function resetChapter(chapterId: string): void {
  const answers: Record<string, AnswerMark> = {};
  for (const [qid, a] of Object.entries(current.answers)) {
    if (a.chapterId !== chapterId) answers[qid] = a;
  }
  const bestiary: Record<string, Monster> = {};
  for (const [qid, m] of Object.entries(current.bestiary)) {
    if (m.chapterId !== chapterId) bestiary[qid] = m;
  }
  const chapterRuns = { ...current.chapterRuns };
  delete chapterRuns[chapterId];
  commit(
    normalize({
      ...current,
      answers,
      bestiary,
      chapterRuns,
      doneChapters: current.doneChapters.filter((id) => id !== chapterId),
    }),
  );
  pushToast({ kind: 'info', title: '本章已重置', desc: chapterNameSafe(chapterId), icon: '↺' });
}

export function spendCoins(delta: number, reason: string): void {
  dispatch({ type: 'coin', delta: -Math.abs(delta), reason });
}

/** 答错/答对统一入口（题库、判题台、自评都走这里） */
export function recordAnswer(input: {
  questionId: string;
  chapterId?: string;
  subject?: string;
  title?: string;
  diff?: string;
  qtype?: string;
  ok: boolean;
  mode?: 'objective' | 'judge' | 'self';
}): AnswerResult {
  const r = dispatch({ type: 'answer', ...input });
  /**
   * 情绪当场变一下，再回落到常态情绪（见 lib/mood.ts）。
   * 三档而不是两档：答错 = 委屈（4.2s，多留一点时间让人注意到），
   * 收服野怪 = 庆祝，普通答对 = 开心。都放在 dispatch 之后，
   * 因为「收服」这个事实只有 reducer 算得出来。
   */
  if (!input.ok) flashMood('aggrieved', 4200);
  else if (r?.tamed) flashMood('celebrate', 4200);
  else flashMood('happy', 3000);

  return (
    r ?? { created: false, tamed: false, monster: current.bestiary[input.questionId] ?? null, coins: 0, message: '' }
  );
}

export function setOutfit(id: string): void {
  commit({ ...current, outfit: id });
}

/**
 * 购买装扮（买完自动换上）。
 *
 * 返回可读原因而不是抛异常：调用方是 UI，需要拿到「还差 180 结晶」这种具体结论
 * 才能直接显示给用户，而不是 catch 一段英文报错。
 * 余额不足时**不改任何状态**，包括不掉 coinLedger——失败的尝试不该留痕。
 */
export function buyOutfit(
  id: string,
  price: number,
  name?: string,
): { ok: true; paid: number } | { ok: false; reason: string } {
  // 已拥有：不重复扣钱，直接换
  if (current.ownedOutfits.includes(id)) {
    setOutfit(id);
    return { ok: true, paid: 0 };
  }
  const cost = Math.max(0, Math.round(price));
  if (current.coins < cost) {
    return { ok: false, reason: `还差 ${cost - current.coins} 结晶` };
  }
  commit({
    ...current,
    coins: current.coins - cost,
    ownedOutfits: [...current.ownedOutfits, id],
    outfit: id,
    coinLedger: [
      { ts: Date.now(), delta: -cost, reason: `购买装扮：${name ?? id}` },
      ...current.coinLedger,
    ].slice(0, LEDGER_LIMIT),
  });
  return { ok: true, paid: cost };
}

export function setTheme(theme: Theme): void {
  commit({ ...current, theme });
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.kmTheme = theme;
    document.documentElement.style.colorScheme = theme;
  }
}

export function resetProgress(): void {
  commit({ ...DEFAULT_STATE, theme: current.theme, outfit: current.outfit });
}

export function useProgress(): ProgressState {
  const [value, setValue] = useState(current);
  useEffect(() => {
    const fn = (s: ProgressState) => setValue(s);
    listeners.add(fn);
    setValue(current);
    return () => {
      listeners.delete(fn);
    };
  }, []);
  return value;
}

/** 首屏把主题打到 <html>，避免刷新时闪一下白底 */
export function applyStoredTheme(): void {
  if (typeof document === 'undefined') return;
  document.documentElement.dataset.kmTheme = current.theme;
  document.documentElement.style.colorScheme = current.theme;
}
