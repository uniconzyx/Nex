/**
 * agent/tools.ts —— Agent 的「手」
 * ============================================================================
 * 设计原则（与 docs/MLDL-Agent-Plan.md §4.2 对齐，但按 A 期范围裁剪）：
 *
 *   1. **纯数据依赖**：只 import data/* 与 graph.ts，绝不 import progress.ts。
 *      原因见 types.ts：progress.ts 在模块顶层就读 localStorage + 碰 document，
 *      Node 里跑验收会直接炸。进度由 ToolContext 注入。
 *
 *   2. **数字只由工具算**：mastery、错题数、命中数全在这里算完再交给模型，
 *      模型只负责选参数与解释。这是「报告里每个数字都能溯源」的前提。
 *
 *   3. **失败也要返回 Observation**：ok=false + brief 说明原因。
 *      模型看到「章节不存在，可用 ml-ch01..ml-ch09」才会改参数重试——
 *      这正是 agent 与「一次性生成」的区别。
 *
 *   4. **结果分级**：brief 进 prompt（短、可截断），data 给报告拼接用，
 *      raw 存真实 stdout（产物的物证）。
 *
 * 【关于「学科」的一个坑，务必注意】
 *   BUNDLE 里 ml / agent / ai 三类章节**同属 `ai` 一个包**（共 39 章），
 *   但用户心里「机器学习」和「深度学习」是两件事。所以 resolveChapters()
 *   既接受学科键（ai），也接受章节族前缀（ml / agent / ai），
 *   否则 subject='ml' 会拿到 0 章 —— 这是本仓数据组织方式决定的，不是笔误。
 */

import { CHAPTER_CONTENT, type ChapterContent } from '../../data/chapterContent';
import { EXERCISES, type BankExercise } from '../../data/exercises';
import { allChapters, chapterName, chaptersOfSubject, masteryOfChapter } from '../graph';
import {
  TOOL_NAMES,
  type Observation,
  type ToolName,
  type ToolSpec,
} from './types';

/* ============================================================================
 * 一、通用小工具
 * ========================================================================== */

/** mastery 到 100 即「三关全通」，与 progress.ts 的 doneChapters 推导口径一致 */
const MASTERY_DONE = 100;

/** brief 只进 prompt，长度必须有上限，否则 8 步就能把上下文塞爆 */
const BRIEF_MAX = 600;

const clip = (s: string, n: number) => (s.length <= n ? s : `${s.slice(0, n)}…(+${s.length - n}字)`);

const ok = (brief: string, data?: unknown, raw?: string): Observation => ({
  ok: true,
  brief: clip(brief, BRIEF_MAX),
  data,
  raw,
});

const fail = (brief: string): Observation => ({ ok: false, brief: clip(brief, BRIEF_MAX) });

function asString(v: unknown): string | undefined {
  return typeof v === 'string' && v.trim() ? v.trim() : undefined;
}

function asNumber(v: unknown, dflt: number): number {
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : dflt;
}

/* ============================================================================
 * 二、章节解析：学科键 与 章节族前缀 双通道
 * ========================================================================== */

export interface ResolvedChapter {
  id: string;
  title: string;
  subject: string;
  order: number;
  group: string;
}

/**
 * 把「用户嘴里的学科」解析成章节列表。
 *
 * 解析顺序：
 *   1. 当作 bundle 学科键（ai / cpp / fundamentals …）——命中就用
 *   2. 当作章节族前缀（ml / agent / dm …）——按 id 前缀过滤
 *   3. 都没有 → 返回空，由调用方给出「可用取值」提示
 */
export function resolveChapters(subject?: string): ResolvedChapter[] {
  const all = allChapters();
  if (!subject) {
    return all.map((c) => ({ id: c.id, title: c.title, subject: c.subject, order: c.order, group: c.group }));
  }
  const byKey = chaptersOfSubject(subject);
  if (byKey.length) {
    return byKey.map((c) => ({ id: c.id, title: c.title, subject: c.subject, order: c.order, group: c.group }));
  }
  const prefix = `${subject}-ch`;
  const byPrefix = all.filter((c) => c.id.startsWith(prefix));
  return byPrefix.map((c) => ({ id: c.id, title: c.title, subject: c.subject, order: c.order, group: c.group }));
}

/** 提示「你可以用哪些 subject」——失败分支靠它让模型自我纠正 */
function subjectHints(): string {
  const keys = new Set<string>();
  for (const c of allChapters()) keys.add(c.subject);
  return `可用学科键：${[...keys].sort().join(' / ')}；也可用章节族前缀：ml / agent / ai / dm / fund`;
}

function contentOf(chapterId: string): ChapterContent | undefined {
  return CHAPTER_CONTENT[chapterId];
}

/* ============================================================================
 * 三、工具 1：list_chapters
 * ========================================================================== */

const listChapters: ToolSpec = {
  name: 'list_chapters',
  desc: '列出某学科/章节族下的全部章节，附带掌握度与是否通关',
  argsDoc: 'subject?: string（学科键或章节族前缀，省略则全部）',
  async run(args, ctx) {
    const subject = asString(args.subject) ?? ctx.subject;
    const rows = resolveChapters(subject);
    if (!rows.length) {
      return fail(`没有找到「${subject}」下的章节。${subjectHints()}`);
    }
    const st = ctx.progress;
    const items = rows.map((c) => {
      const mastery = masteryOfChapter(c.id, st);
      return {
        chapter_id: c.id,
        title: chapterName(c.id) || c.title,
        group: c.group,
        order: c.order,
        mastery,
        done: mastery >= MASTERY_DONE,
      };
    });
    const doneCount = items.filter((i) => i.done).length;
    const avg = Math.round(items.reduce((s, i) => s + i.mastery, 0) / items.length);
    const head = items
      .slice(0, 8)
      .map((i) => `${i.chapter_id}(${i.mastery}%)`)
      .join('、');
    return ok(
      `「${subject}」共 ${items.length} 章，已通关 ${doneCount} 章，平均掌握度 ${avg}%。` +
        `前几章：${head}${items.length > 8 ? ' …' : ''}`,
      items,
    );
  },
};

/* ============================================================================
 * 四、工具 2：get_progress
 * ========================================================================== */

const getProgress: ToolSpec = {
  name: 'get_progress',
  desc: '读用户学习进度：逐章掌握度、通关状态、错题数、答题尝试数',
  argsDoc: 'subject?: string（省略则用会话学科）',
  async run(args, ctx) {
    const subject = asString(args.subject) ?? ctx.subject;
    const rows = resolveChapters(subject);
    if (!rows.length) return fail(`没有找到「${subject}」下的章节。${subjectHints()}`);

    const st = ctx.progress;
    // 先把答题记录按章节聚合，避免在循环里反复扫 answers（1000+ 条）
    const perChapter = new Map<string, { total: number; wrong: number }>();
    for (const mark of Object.values(st.answers ?? {})) {
      const cid = mark.chapterId;
      if (!cid) continue;
      const rec = perChapter.get(cid) ?? { total: 0, wrong: 0 };
      rec.total += 1;
      if (!mark.ok) rec.wrong += 1;
      perChapter.set(cid, rec);
    }

    const items = rows.map((c) => {
      const mastery = masteryOfChapter(c.id, st);
      const rec = perChapter.get(c.id) ?? { total: 0, wrong: 0 };
      return {
        chapter_id: c.id,
        title: chapterName(c.id) || c.title,
        mastery,
        done: mastery >= MASTERY_DONE,
        attempts: rec.total,
        wrong_count: rec.wrong,
        /** 只刷了题但没通关：说明卡在某一关 */
        stuck: rec.total > 0 && mastery < MASTERY_DONE,
      };
    });

    // 诊断要的是「薄弱在哪」，所以这里替模型把排序做了（数字由工具算，不由模型猜）
    // 排序口径：**先补「学了但没通」的章，再补完全没开始的**。
    // 理由：未开始的章 mastery 也是 0，若只按 mastery 升序，诊断会把「去开第 6 章」
    // 排在「把 ch03 的演练关补上」前面——后者才是用户当下真正该做的事。
    const weak = [...items]
      .sort((a, b) => Number(b.stuck) - Number(a.stuck) || a.mastery - b.mastery || b.wrong_count - a.wrong_count)
      .slice(0, 5);
    const untouched = items.filter((i) => i.attempts === 0);
    const done = items.filter((i) => i.done).length;
    // 汇总数字必须**在工具里算完并放进 data**：报告的 auditReport 只认「证据里出现过的数字」，
    // 让模型自己 sum/len 出来的平均值会被判定为「无法溯源」——这是刻意的。
    const avg = Math.round(items.reduce((s, i) => s + i.mastery, 0) / items.length);
    const wrongTotal = items.reduce((s, i) => s + i.wrong_count, 0);
    const weakTxt = weak.map((w) => `${w.chapter_id}(${w.mastery}%,错${w.wrong_count})`).join('、');
    return ok(
      `「${subject}」${items.length} 章：已通关 ${done} 章，平均掌握度 ${avg}%，错题 ${wrongTotal} 道，` +
        `未开始 ${untouched.length} 章；最该补的 5 章：${weakTxt}`,
      {
        items,
        weak: weak.map((w) => w.chapter_id),
        untouched: untouched.map((i) => i.chapter_id),
        stats: { total: items.length, done, avg_mastery: avg, wrong_total: wrongTotal },
      },
    );
  },
};

/* ============================================================================
 * 五、工具 3：read_chapter
 * ========================================================================== */

/** 维度名 → 取内容的函数，供 focus 参数与渲染共用 */
const DIMS = {
  goals: (c: ChapterContent) => c.goals,
  concepts: (c: ChapterContent) => c.concepts,
  pitfalls: (c: ChapterContent) => c.pitfalls,
  interviews: (c: ChapterContent) => c.interviews,
  projects: (c: ChapterContent) => c.projects,
} as const;

type DimKey = keyof typeof DIMS;

const readChapter: ToolSpec = {
  name: 'read_chapter',
  desc: '读某一章的正文切片（目标/概念/易错点/面试题/项目），可用 focus 只取需要的维度',
  argsDoc: 'chapter_id: string（必填）, focus?: "goals"|"concepts"|"pitfalls"|"interviews"|"projects"',
  async run(args, ctx) {
    const cid = asString(args.chapter_id) ?? ctx.chapterId;
    if (!cid) return fail('缺少 chapter_id；如需全部章节请先调用 list_chapters');
    const c = contentOf(cid);
    if (!c) {
      const near = resolveChapters(ctx.subject).slice(0, 6).map((x) => x.id).join('、');
      return fail(`章节「${cid}」没有正文切片。本学科可用：${near || subjectHints()}`);
    }
    const focus = asString(args.focus) as DimKey | undefined;
    const picked: DimKey[] = focus && focus in DIMS ? [focus] : (Object.keys(DIMS) as DimKey[]);

    const data: Record<string, string[]> = {};
    let total = 0;
    for (const k of picked) {
      const arr = DIMS[k](c);
      data[k] = arr;
      total += arr.length;
    }
    if (!total) return fail(`章节「${cid}」的${picked.join('/')}维度为空（内容可能未生成完整）`);

    // brief 只报「有什么、多少条、首条长什么样」，细节放 data 里按需取
    const shape = picked.map((k) => `${k} ${(data[k] ?? []).length} 条`).join('，');
    const firstLine = (data[picked[0]] ?? [])[0] ?? '';
    return ok(
      `《${chapterName(cid) || cid}》正文已读到：${shape}。首条示例：${clip(firstLine, 120)}`,
      { chapter_id: cid, title: chapterName(cid) || cid, dims: data },
    );
  },
};

/* ============================================================================
 * 六、工具 4：search_local（前端 BM25，不依赖后端）
 * ========================================================================== */

/**
 * 为什么要在前端再实现一份 BM25：
 *   服务端的 KnowledgeIndex 走 /ai/chat，那条路只返回拼好的 prompt，拿不到
 *   结构化命中；而 agent 需要「命中哪一章、哪一句」才能把结论溯源。
 *   纯函数索引还能在 Node 里单测，不依赖后端在线。
 */

const K1 = 1.2;
const B = 0.75;

interface Doc {
  id: string;
  parts: string[];
  tf: Map<string, number>;
  len: number;
}

interface Index {
  docs: Doc[];
  df: Map<string, number>;
  avgLen: number;
}

/**
 * 中文不分词，用二元组(bigram)是最省事且有效的做法：
 * 「梯度消失」→ 梯度/度消/消失，既能命中长词，也能命中「消失」这种半截查询。
 * 英文与数字按词切，避免 "conv2d" 被拆成单字母。
 */
function tokenize(text: string): string[] {
  const out: string[] = [];
  const lower = text.toLowerCase();
  for (const m of lower.matchAll(/[a-z][a-z0-9_+#.]*|\d+(?:\.\d+)?/g)) out.push(m[0]);
  for (const seg of lower.replace(/[^\u4e00-\u9fa5]+/g, ' ').split(/\s+/)) {
    if (!seg) continue;
    if (seg.length === 1) out.push(seg);
    else for (let i = 0; i + 1 < seg.length; i++) out.push(seg.slice(i, i + 2));
  }
  return out;
}

let INDEX: Index | null = null;

function index(): Index {
  if (INDEX) return INDEX;
  const docs: Doc[] = [];
  for (const [id, c] of Object.entries(CHAPTER_CONTENT)) {
    // 按「条目」而不是整章建 tf，这样 snippet 能直接取到命中的那一句
    const parts = [...c.goals, ...c.concepts, ...c.pitfalls, ...c.interviews, ...c.projects];
    const toks = tokenize(parts.join('\n'));
    const tf = new Map<string, number>();
    for (const t of toks) tf.set(t, (tf.get(t) ?? 0) + 1);
    docs.push({ id, parts, tf, len: toks.length });
  }
  const df = new Map<string, number>();
  for (const d of docs) for (const k of d.tf.keys()) df.set(k, (df.get(k) ?? 0) + 1);
  const avgLen = docs.reduce((s, d) => s + d.len, 0) / Math.max(1, docs.length);
  INDEX = { docs, df, avgLen };
  return INDEX;
}

export interface SearchHit {
  chapter_id: string;
  title: string;
  score: number;
  snippet: string;
}

export function searchLocal(query: string, k = 3, subject?: string): SearchHit[] {
  const q = tokenize(query);
  if (!q.length) return [];
  const { docs, df, avgLen } = index();
  const scope = subject ? new Set(resolveChapters(subject).map((c) => c.id)) : null;
  const N = docs.length;

  const scored = docs
    .filter((d) => !scope || scope.has(d.id))
    .map((d) => {
      let score = 0;
      for (const t of q) {
        const f = d.tf.get(t);
        if (!f) continue;
        const n = df.get(t) ?? 1;
        const idf = Math.log(1 + (N - n + 0.5) / (n + 0.5));
        score += (idf * f * (K1 + 1)) / (f + K1 * (1 - B + (B * d.len) / avgLen));
      }
      // snippet：取与该 query 词重叠最多的那一条（而不是整章开头），避免「命中但看不出命中什么」
      let best = '';
      let bestHit = 0;
      for (const p of d.parts) {
        const pt = new Set(tokenize(p));
        let hit = 0;
        for (const t of q) if (pt.has(t)) hit++;
        if (hit > bestHit) {
          bestHit = hit;
          best = p;
        }
      }
      return { chapter_id: d.id, title: chapterName(d.id) || d.id, score, snippet: best || d.parts[0] || '' };
    })
    .filter((h) => h.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, k);

  return scored.map((h) => ({ ...h, score: Math.round(h.score * 1000) / 1000 }));
}

const searchLocalTool: ToolSpec = {
  name: 'search_local',
  desc: '在本学科正文里做关键词检索（BM25），返回命中的章节与具体那一条原文',
  argsDoc: 'query: string（必填）, k?: number（默认 3）',
  async run(args, ctx) {
    const query = asString(args.query);
    if (!query) return fail('缺少 query');
    const k = Math.min(10, Math.max(1, asNumber(args.k, 3)));
    const hits = searchLocal(query, k, ctx.subject);
    if (!hits.length) {
      return fail(`「${query}」在本学科正文没有命中。可换用更具体的术语，或先 list_chapters 看有哪些章`);
    }
    const head = hits.map((h) => `${h.chapter_id}(${h.score})`).join('、');
    return ok(`命中 ${hits.length} 条：${head}；最相关原文：${clip(hits[0].snippet, 160)}`, hits);
  },
};

/* ============================================================================
 * 七、工具 5/6：错题 与 章节题目
 * ========================================================================== */

const listWrongExercises: ToolSpec = {
  name: 'list_wrong_exercises',
  desc: '列出用户答错过的题目（含题干摘要与所属章节），用于学习诊断',
  argsDoc: 'chapter_id?: string（限定某章）, limit?: number（默认 10）',
  async run(args, ctx) {
    const cid = asString(args.chapter_id);
    const limit = Math.min(50, Math.max(1, asNumber(args.limit, 10)));
    const st = ctx.progress;
    const byId = new Map(EXERCISES.map((e) => [e.id, e]));

    const wrongs: { id: string; chapter_id: string; title: string; md: string; type: string }[] = [];
    for (const [exId, mark] of Object.entries(st.answers ?? {})) {
      if (mark.ok) continue;
      if (cid && mark.chapterId !== cid) continue;
      const e = byId.get(exId);
      wrongs.push({
        id: exId,
        chapter_id: mark.chapterId || e?.ch || '',
        title: e?.title ?? exId,
        md: clip(e?.md ?? '', 120),
        type: e?.type ?? 'unknown',
      });
    }
    if (!wrongs.length) {
      return ok(
        cid ? `「${cid}」目前没有错题记录（可能还没做过题）` : '目前没有错题记录（可能还没做过题）',
        [],
      );
    }
    // 按章节聚合，直接给模型「哪个知识点最该补」
    const byChapter = new Map<string, number>();
    for (const w of wrongs) byChapter.set(w.chapter_id, (byChapter.get(w.chapter_id) ?? 0) + 1);
    const top = [...byChapter.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
    const sliced = wrongs.slice(0, limit);
    return ok(
      `错题共 ${wrongs.length} 道，集中在：${top.map(([c, n]) => `${c}(${n})`).join('、')}。` +
        `已返回前 ${sliced.length} 道，首题：${clip(sliced[0].title, 80)}`,
      { total: wrongs.length, by_chapter: Object.fromEntries(top), items: sliced },
    );
  },
};

const listChapterExercises: ToolSpec = {
  name: 'list_chapter_exercises',
  desc: '列出某章的练习题（默认不含答案；要判分时把 include_answer 设为 true）',
  argsDoc: 'chapter_id?: string（默认会话锁定的章）, limit?: number, include_answer?: boolean',
  async run(args, ctx) {
    const cid = asString(args.chapter_id) ?? ctx.chapterId;
    if (!cid) return fail('缺少 chapter_id');
    const limit = Math.min(20, Math.max(1, asNumber(args.limit, 5)));
    const withAnswer = args.include_answer === true;

    const pool = EXERCISES.filter((e) => e.ch === cid);
    if (!pool.length) {
      return fail(`「${cid}」在题库里没有题目（该章可能未生成题库，无法据此诊断）`);
    }
    // 优先取「用户还没做对」的题：诊断要的是未知，不是已掌握
    const st = ctx.progress;
    const marks = st.answers ?? {};
    const picked = [...pool]
      .sort((a, b) => {
        const sa = marks[a.id]?.ok === true ? 1 : 0;
        const sb = marks[b.id]?.ok === true ? 1 : 0;
        return sa - sb;
      })
      .slice(0, limit)
      .map((e) => toExerciseView(e, withAnswer));

    return ok(
      `「${cid}」题库共 ${pool.length} 题，返回 ${picked.length} 题（${withAnswer ? '含答案' : '不含答案'}）：` +
        picked.map((p) => `${p.id}[${p.type}]`).join('、'),
      { chapter_id: cid, total: pool.length, items: picked },
    );
  },
};

function toExerciseView(e: BankExercise, withAnswer: boolean) {
  const base = {
    id: e.id,
    type: e.type,
    diff: e.diff,
    title: e.title,
    /** 题干截断：完整题干在 UI 里显示，prompt 里不需要全文 */
    md: clip(e.md, 400),
    options: e.options,
  };
  if (!withAnswer) return base;
  return {
    ...base,
    correct: e.correct,
    expect: e.expect,
    explain: e.explain,
  };
}

/* ============================================================================
 * 八、工具 7：run_python（唯一「真执行」的能力）
 * ========================================================================== */

const runPython: ToolSpec = {
  name: 'run_python',
  desc: '在浏览器沙箱里真跑一段 Python（含 numpy/sklearn/matplotlib），返回真实 stdout；DL 侧无 torch',
  argsDoc: 'code: string（必填，完整可运行脚本，必须自己 print 出结果）, timeout_ms?: number（默认 20000）',
  async run(args, ctx) {
    const code = asString(args.code);
    if (!code) return fail('缺少 code');
    if (!ctx.runner) {
      return fail('当前会话没有挂载 Python 执行器（run_python 不可用）；请改用 read_chapter / search_local 取材');
    }
    const timeoutMs = Math.min(60000, Math.max(1000, asNumber(args.timeout_ms, 20000)));
    ctx.onLog?.(`run_python: ${code.split('\n')[0].slice(0, 60)}…`);

    const r = await ctx.runner(code, timeoutMs);
    const images = r.images ?? [];

    if (r.error) {
      // 失败要把 stderr 原样回填：模型看到 Traceback 才会改代码重试
      return ok(
        `运行报错 ${r.error.name}: ${clip(r.error.message, 200)}。请修代码后重跑。`,
        { ok: false, stdout: r.stdout, stderr: r.stderr, error: r.error, images },
        r.stdout,
      );
    }
    if (r.interrupted) {
      return ok(
        `运行被中断（超时 ${timeoutMs}ms），stdout 只有部分内容，不能当作完整结果引用`,
        { ok: false, interrupted: true, stdout: r.stdout, images },
        r.stdout,
      );
    }
    const out = r.stdout.trim();
    if (!out && !images.length) {
      return ok(
        '运行成功但没有任何 stdout 输出。如果要拿数字，请在代码里 print 出来（否则报告无法引用）',
        { ok: true, stdout: '', images },
        '',
      );
    }
    return ok(
      `运行成功，耗时 ${Math.round(r.durationMs)}ms，stdout ${out.length} 字` +
        `${images.length ? `，生成 ${images.length} 张图` : ''}。输出开头：${clip(out, 300)}`,
      { ok: true, stdout: r.stdout, stderr: r.stderr, durationMs: r.durationMs, images },
      r.stdout,
    );
  },
};

/* ============================================================================
 * 九、注册表
 * ========================================================================== */

export const TOOLS: ToolSpec[] = [
  listChapters,
  getProgress,
  readChapter,
  searchLocalTool,
  listWrongExercises,
  listChapterExercises,
  runPython,
];

const BY_NAME = new Map(TOOLS.map((t) => [t.name, t]));

export function getTool(name: ToolName): ToolSpec | undefined {
  return BY_NAME.get(name);
}

/**
 * 工具清单的 prompt 文本。由 TOOLS 自动生成，避免「加了工具忘了写进 prompt」
 * 这种最容易发生、又最难发现的漂移。
 */
export function toolCatalog(): string {
  return TOOLS.map((t, i) => `${i + 1}. ${t.name}(${t.argsDoc}) —— ${t.desc}`).join('\n');
}

/** 与 TOOL_NAMES 的一致性自检：漏注册的工具名会在这里暴露，验收脚本会断言 */
export function missingTools(): ToolName[] {
  return TOOL_NAMES.filter((n) => !BY_NAME.has(n));
}
