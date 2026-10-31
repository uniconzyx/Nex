/**
 * exerciseBank.ts —— 题库索引与「题库 → 判题台」的桥
 * ============================================================================
 * 数据来自 data/exercises.ts（由 server/scripts/gen_exercise_bundle.py 生成，
 * 818 题 / 13 学科），不手改。
 *
 * 这一层只做四件事：
 *   1. 建索引：按学科、按章节、按 id 查题；
 *   2. 判断「这题现在能不能判」——不是有代码就能判，还得有用例、语言得支持；
 *   3. 把 BankExercise 转成 JudgePanel 认的 JudgeProblem（跨组件契约）；
 *   4. 承载「从学习页跳到判题台」的跨页目标（模块级 store，避免层层传 props）。
 *
 * 【为什么不把语言判断交给 JudgeEngine】
 *   JudgeEngine.capabilityOf 回答的是「当前设备能不能跑 X 语言」；
 *   这里回答的是「这道题本身够不够判」。两件事正交：
 *   桌面端能跑 Java，但一道没有用例的 Java 题仍然判不了 —— 判不了就别让
 *   用户白点一次「去判题台」再发现按钮是灰的。
 * ============================================================================
 */
import { useEffect, useState } from 'react';

import { EXERCISES, type BankExercise, type BankType } from '../data/exercises';
import { BUNDLE } from '../data/bundle';
import type { JudgeProblem } from '../components/JudgePanel';
import type { TestCase } from './JudgeEngine';
import type { JudgeLanguage } from './GoJudgeClient';
import { apiGet } from './api';

/* ------------------------------------------------------------------ 类型 */

export type { BankExercise, BankType };

/** 题库当前可判的语言集合，必须与 Rust judge_client.rs 的分支一一对应 */
const JUDGE_LANGS = new Set(['python', 'c', 'cpp', 'java']);

export interface BankFilter {
  subject: string;
  type: BankType | 'all';
  diff: 'all' | 'easy' | 'medium' | 'hard';
  /** 只看「现在就能判」的题 */
  judgeableOnly: boolean;
  /** 只看还没做过的题 */
  todoOnly: boolean;
  keyword: string;
  /** 从学习页某章跳进来时锁定章节；null/undefined 表示全学科 */
  chapter?: string | null;
}

/* ------------------------------------------------------------ 基础索引 */

const BY_ID = new Map<string, BankExercise>();
const BY_CHAPTER = new Map<string, BankExercise[]>();
const BY_SUBJECT = new Map<string, BankExercise[]>();

for (const e of EXERCISES) {
  BY_ID.set(e.id, e);
  let c = BY_CHAPTER.get(e.ch);
  if (!c) BY_CHAPTER.set(e.ch, (c = []));
  c.push(e);
  let s = BY_SUBJECT.get(e.subj);
  if (!s) BY_SUBJECT.set(e.subj, (s = []));
  s.push(e);
}

/** 章节 id → 标题。来源是各学科 _manifest.json（打包进 BUNDLE）。 */
const CHAPTER_TITLE = new Map<string, string>();
for (const pack of Object.values(BUNDLE.chapters)) {
  for (const c of pack.chapters) CHAPTER_TITLE.set(c.id, c.title);
}

export function exerciseById(id: string): BankExercise | undefined {
  return BY_ID.get(id);
}

export function exercisesOfSubject(subject: string): BankExercise[] {
  return BY_SUBJECT.get(subject) ?? [];
}

export function exercisesOfChapter(chapterId: string): BankExercise[] {
  return BY_CHAPTER.get(chapterId) ?? [];
}

export function chapterTitle(chapterId: string): string {
  return CHAPTER_TITLE.get(chapterId) ?? chapterId;
}

/** 某章在题库里的统计，供学习页展示「本章 N 题 · 可判 M 题」 */
export function chapterBankStats(chapterId: string): {
  total: number;
  byType: Record<string, number>;
  judgeable: number;
} {
  const list = exercisesOfChapter(chapterId);
  const byType: Record<string, number> = {};
  let judgeable = 0;
  for (const e of list) {
    byType[e.type] = (byType[e.type] ?? 0) + 1;
    if (isJudgeable(e)) judgeable += 1;
  }
  return { total: list.length, byType, judgeable };
}

/* ------------------------------------------------------------ 判题能力 */

/**
 * 这题能不能送进判题台真判。
 *
 * 三个条件缺一不可：
 *   - 有 cases（否则期望输出无从比对，只能自由运行）；
 *   - 语言在 JUDGE_LANGS 里（js/sql/shell 目前两端都没有运行时）；
 *   - 有参考代码或用户能自己写（没有 code 也允许，题面即约束）。
 */
export function isJudgeable(e: BankExercise): boolean {
  return !!e.cases?.length && !!e.lang && JUDGE_LANGS.has(e.lang);
}

/** 语言在两端都跑不了（JS/SQL/Shell），题面只能阅读 + 自评 */
export function isUnsupportedLang(e: BankExercise): boolean {
  return !!e.lang && !JUDGE_LANGS.has(e.lang);
}

export function languageLabel(lang?: string): string {
  switch (lang) {
    case 'python':
      return 'Python';
    case 'c':
      return 'C';
    case 'cpp':
      return 'C++';
    case 'java':
      return 'Java';
    case 'js':
      return 'JavaScript';
    case 'sql':
      return 'SQL';
    case 'shell':
      return 'Shell';
    default:
      return '未指定';
  }
}

/** 题型的中文名与配色标签 */
export const TYPE_META: Record<BankType, { label: string; short: string }> = {
  choice: { label: '选择题', short: '选择' },
  coding: { label: '编程题', short: '编程' },
  output: { label: '看码写输出', short: '输出' },
  fix_error: { label: '找错改错', short: '改错' },
  explain: { label: '问答题', short: '问答' },
  design: { label: '设计题', short: '设计' },
};

export const DIFF_META: Record<string, { label: string }> = {
  easy: { label: '简单' },
  medium: { label: '中等' },
  hard: { label: '困难' },
};

/* ------------------------------------------------- 转成判题台的题目对象 */

/**
 * BankExercise → JudgeProblem。
 *
 * 只对「能判」的题调用（isJudgeable 为真）：
 * language 必须落进 JudgeLanguage 的四个值，否则 JudgePanel 的下拉框会
 * 显示成 Python 却在跑 JS，那是最糟的错配。
 */
export function toJudgeProblem(e: BankExercise): JudgeProblem {
  const lang = (JUDGE_LANGS.has(e.lang ?? '') ? e.lang : 'python') as JudgeLanguage;
  const cases: TestCase[] = (e.cases ?? []).map((c) => ({
    name: c.name,
    stdin: c.stdin,
    expected: c.expected,
  }));
  return {
    id: e.id,
    title: e.title,
    content: composeProblemMarkdown(e),
    language: lang,
    cases,
    starterCode: e.code ?? '',
    // 判题结果要落进图鉴与每日试炼，必须把归属信息一起带过去
    chapterId: e.ch,
    subject: e.subj,
    qtype: e.type,
    diff: e.diff,
  };
}

/** 判题台的题面 = Markdown 题面 + 输入输出约定（题库没写约定时补一句）。
 *  标题不放进 markdown：JudgePanel 已经用 problem.title 渲染了一次 h2，
 *  这里再加一个会看到同一个标题连出两行。 */
function composeProblemMarkdown(e: BankExercise): string {
  const parts = [e.md || ''];
  if (e.cases?.length) {
    const sample = e.cases[0];
    parts.push(
      [
        '### 输入输出约定',
        '',
        '| 项目 | 内容 |',
        '| --- | --- |',
        '| 语言 | ' + languageLabel(e.lang) + ' |',
        '| 用例数 | ' + e.cases.length + ' |',
        '',
        '第一个用例：',
        '',
        '```text',
        'stdin:',
        sample.stdin === '' ? '(空)' : sample.stdin,
        '```',
        '',
        '```text',
        'expected:',
        sample.expected,
        '```',
      ].join('\n'),
    );
  } else if (e.lang && JUDGE_LANGS.has(e.lang)) {
    parts.push(
      '> 本题没有内置用例，判题台里请自行填写 stdin / 期望输出，或用「自由运行」看输出。',
    );
  }
  if (e.src) parts.push(`> 来源：${e.src}`);
  return parts.filter(Boolean).join('\n\n');
}

/* -------------------------------------------------------- 过滤 / 统计 */

export function filterExercises(subject: string, f: BankFilter, done: Set<string> = new Set()): BankExercise[] {
  const kw = f.keyword.trim().toLowerCase();
  return exercisesOfSubject(subject).filter((e) => {
    if (f.chapter && e.ch !== f.chapter) return false;
    if (f.type !== 'all' && e.type !== f.type) return false;
    if (f.diff !== 'all' && e.diff !== f.diff) return false;
    if (f.judgeableOnly && !isJudgeable(e)) return false;
    if (f.todoOnly && done.has(e.id)) return false;
    if (kw) {
      const hay = `${e.title}\n${e.md}\n${(e.tags ?? []).join(' ')}\n${chapterTitle(e.ch)}`;
      if (!hay.toLowerCase().includes(kw)) return false;
    }
    return true;
  });
}

/** 某学科的题型分布，用于筛选条上的计数 */
export function subjectStats(subject: string): {
  total: number;
  judgeable: number;
  byType: Record<string, number>;
} {
  const list = exercisesOfSubject(subject);
  const byType: Record<string, number> = {};
  let judgeable = 0;
  for (const e of list) {
    byType[e.type] = (byType[e.type] ?? 0) + 1;
    if (isJudgeable(e)) judgeable += 1;
  }
  return { total: list.length, judgeable, byType };
}

/* ------------------------------------------- 跨页跳转：题库 → 判题台 */

let pendingTarget: JudgeProblem | null = null;
const targetListeners = new Set<(p: JudgeProblem | null) => void>();

/** 学习页/题库点「去判题台」时调用；PracticePage 会即时收到 */
export function sendToJudge(p: JudgeProblem): void {
  pendingTarget = p;
  for (const fn of targetListeners) fn(p);
}

/** 判题台消费掉目标后清空，避免切回练习页又弹一次旧题 */
export function clearJudgeTarget(): void {
  pendingTarget = null;
  for (const fn of targetListeners) fn(null);
}

export function usePendingJudgeProblem(): JudgeProblem | null {
  const [p, setP] = useState<JudgeProblem | null>(pendingTarget);
  useEffect(() => {
    targetListeners.add(setP);
    setP(pendingTarget);
    return () => {
      targetListeners.delete(setP);
    };
  }, []);
  return p;
}

export function peekJudgeTarget(): JudgeProblem | null {
  return pendingTarget;
}

/* ------------------------------ 跨页跳转：学习页某章 → 题库（锁定章节） */

let focusedChapter: string | null = null;
const chapterListeners = new Set<(ch: string | null) => void>();

/** 学习页点「本章 N 题」时调用；PracticePage 切到题库 Tab 并锁定该章 */
export function focusChapter(ch: string | null): void {
  focusedChapter = ch;
  for (const fn of chapterListeners) fn(ch);
}

export function peekFocusedChapter(): string | null {
  return focusedChapter;
}

/* --------------------------- 跨页跳转：直接打开某一道题（图鉴 / 每日试炼用） */

/**
 * 与 focusChapter 的区别：
 *   focusChapter 只锁定章节，玩家还得在列表里找到那道题；
 *   这里直接把详情面板打开到指定题（challenge.ts 在题目不能判时使用）。
 * 分开两个 store 是因为它们语义不同：一个是"缩小范围"，一个是"指名道姓"。
 */
let focusedExercise: string | null = null;
const exerciseListeners = new Set<(id: string | null) => void>();

export function focusExercise(id: string | null): void {
  focusedExercise = id;
  for (const fn of exerciseListeners) fn(id);
}

export function useFocusedExercise(): string | null {
  const [id, setId] = useState<string | null>(focusedExercise);
  useEffect(() => {
    exerciseListeners.add(setId);
    setId(focusedExercise);
    return () => {
      exerciseListeners.delete(setId);
    };
  }, []);
  return id;
}

export function useFocusedChapter(): string | null {
  const [ch, setCh] = useState<string | null>(focusedChapter);
  useEffect(() => {
    chapterListeners.add(setCh);
    setCh(focusedChapter);
    return () => {
      chapterListeners.delete(setCh);
    };
  }, []);
  return ch;
}

/* ------------------------------------------------ 题库完成度（本地） */

/**
 * 单独一个 key，不复用 kaimao.progress.v1。
 *
 * 理由：progress.ts 是「章节/项目/打卡」的粗粒度进度，818 道题的完成集合
 * 塞进去会让每次 setProgress 都序列化一个大数组；而且题库是新增域，
 * 混进去后将来想按题域同步到云端会很难拆。
 */
const DONE_KEY = 'nex.bank.done.v1';

function loadDone(): Set<string> {
  if (typeof localStorage === 'undefined') return new Set();
  try {
    const raw = localStorage.getItem(DONE_KEY);
    const arr = raw ? (JSON.parse(raw) as unknown) : [];
    return new Set(Array.isArray(arr) ? arr.map(String) : []);
  } catch {
    return new Set();
  }
}

let doneSet: Set<string> = loadDone();
const doneListeners = new Set<(s: Set<string>) => void>();

function commitDone(next: Set<string>): void {
  doneSet = next;
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(DONE_KEY, JSON.stringify([...next]));
    } catch {
      /* 配额满不影响内存态，只是重启后丢，不该因此报错 */
    }
  }
  for (const fn of doneListeners) fn(next);
}

export function markBankDone(id: string): void {
  if (doneSet.has(id)) return;
  const next = new Set(doneSet);
  next.add(id);
  commitDone(next);
}

export function toggleBankDone(id: string): void {
  const next = new Set(doneSet);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  commitDone(next);
}

export function isBankDone(id: string): boolean {
  return doneSet.has(id);
}

export function useBankDone(): Set<string> {
  const [s, setS] = useState<Set<string>>(doneSet);
  useEffect(() => {
    doneListeners.add(setS);
    setS(doneSet);
    return () => {
      doneListeners.delete(setS);
    };
  }, []);
  return s;
}

/* ----------------------------------------- 云端目录（后端 GET /exercises）*/

export interface CloudCatalog {
  /** 后端题库里带 bundle_id 的题，与本地 BankExercise.id 1:1 对齐 */
  ids: Set<string>;
  status: 'idle' | 'loading' | 'ok' | 'error';
  error?: string;
}

/**
 * 拉取后端题库目录，仅收集 bundle_id（分页拉全）。
 * 这是「云端目录」与本地 bundle 的精确桥梁：不再靠标题模糊匹配，
 * 而是用和 gen_exercise_bundle.py 同源的稳定 id 做 1:1 映射。
 */
export async function fetchBackendCatalog(): Promise<CloudCatalog> {
  const ids = new Set<string>();
  try {
    let page = 1;
    const size = 100;
    for (;;) {
      const data = await apiGet<{ items: Array<{ bundle_id?: string | null }>; total: number }>(
        `/api/v1/exercises?page=${page}&size=${size}`,
      );
      const items = data?.items ?? [];
      for (const it of items) if (it.bundle_id) ids.add(it.bundle_id);
      if (items.length === 0 || page * size >= (data?.total ?? 0)) break;
      page += 1;
    }
    return { ids, status: 'ok' };
  } catch (e) {
    return { ids, status: 'error', error: e instanceof Error ? e.message : String(e) };
  }
}

/** 挂载即拉一次云端目录；离线/失败时回落「本地题库」，不阻塞本地浏览。 */
export function useCloudCatalog(): CloudCatalog {
  const [cat, setCat] = useState<CloudCatalog>({ ids: new Set(), status: 'idle' });
  useEffect(() => {
    let alive = true;
    setCat((c) => ({ ...c, status: 'loading' }));
    fetchBackendCatalog()
      .then((r) => { if (alive) setCat(r); })
      .catch((e) => { if (alive) setCat({ ids: new Set(), status: 'error', error: String(e) }); });
    return () => {
      alive = false;
    };
  }, []);
  return cat;
}

