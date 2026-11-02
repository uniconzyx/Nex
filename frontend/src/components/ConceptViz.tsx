/**
 * ConceptViz.tsx —— 章节内的「机制图解」（可驱动）
 * ============================================================================
 * 和独立工作台 viz/index.html 是同一套数据与同一套算法，区别只在**摆法**：
 *   工作台是三栏（学科/章/概念 | 图 | 场景），适合「逛」；
 *   这里是章节卡里的一块，宽度只有主栏那么多，所以改成纵向：
 *     图（可点、可滚） → 步进 → 这一节说了什么 → 哪些真题/事故/追问打在这里。
 *
 * 三条设计原则，改之前先读：
 *   1. **节点就是作者原来的小节**（concept/*.md 的 `##`），不是另造一套结构。
 *      所以正文里写「见 §2.3」，图上就是第三节，指的到。
 *   2. **场景是「照亮」不是「另画」**：切考试/事故/面谈只改配色与徽章，
 *      图的拓扑不动——同一张机制图被三种场景击中，才看得出「哪里最贵」。
 *   3. **真题只读**：exams 来自 exercises.json 的快照，答案默认折叠，
 *      组件从不写回。唯一真相在那三个源文件里。
 */
import { useEffect, useMemo, useRef, useState } from 'react';

import { loadVizChapters, peekVizChapters } from '../data/viz';
import type { VizChapter, VizConcept, VizMode, VizSec } from '../data/viz';
import './ConceptViz.css';

/* ── 命中算法：把章节级的题/坑/面经挂到某个小节 ────────────────────
 * 用字符二元组的「余弦式重合度」，阈值 0.055 是拿 165 章试出来的：
 * 再低会把所有条目都吸到第一节，再高则一半条目无处安放。
 * 命中不到如实回落第 0 节，由 UI 标注「未匹配到具体小节」，不硬凑。
 */
const HIT_THRESHOLD = 0.055;

function bigrams(s: string): Map<string, number> {
  const t = String(s || '').replace(/[^\u4e00-\u9fa5A-Za-z0-9]+/g, '');
  const out = new Map<string, number>();
  for (let i = 0; i < t.length - 1; i++) {
    const g = t.slice(i, i + 2);
    out.set(g, (out.get(g) ?? 0) + 1);
  }
  return out;
}

function affinity(a: Map<string, number>, b: Map<string, number>): number {
  if (!a.size || !b.size) return 0;
  let hit = 0;
  a.forEach((v, k) => {
    const w = b.get(k);
    if (w) hit += Math.min(v, w);
  });
  return hit / Math.sqrt(a.size * b.size);
}

/** 绑定到某一节的条目；score 是重合度，低于阈值表示「没有真正匹配」 */
export interface BoundExam {
  node: number;
  score: number;
  item: VizChapter['exams'][number];
}
export interface BoundWork {
  node: number;
  score: number;
  item: VizChapter['works'][number];
}
export interface BoundAsk {
  node: number;
  score: number;
  item: VizChapter['asks'][number];
}

export interface Bind {
  exam: BoundExam[];
  work: BoundWork[];
  ask: BoundAsk[];
}

const EMPTY_BIND: Bind = { exam: [], work: [], ask: [] };

export function mapItems(ch: VizChapter, con: VizConcept): Bind {
  const grams = con.secs.map((s) => bigrams(`${s.h} ${s.s}`));
  /** 返回 [命中的节, 重合度]；重合度低于阈值时节回落到 0 */
  const locate = (text: string): [number, number] => {
    const g = bigrams(text);
    let best = 0;
    let score = 0;
    grams.forEach((sg, i) => {
      const v = affinity(g, sg);
      if (v > score) {
        score = v;
        best = i;
      }
    });
    /* 低于阈值不再回落到第 0 节：回落会让第一节凭空背上「2 道真题」的徽章，
       而右侧列表又说这一节没被命中——两处口径必须一致，宁可不挂。 */
    return score >= HIT_THRESHOLD ? [best, score] : [-1, score];
  };
  return {
    exam: ch.exams.map((e) => {
      const [node, score] = locate(`${e.q} ${e.stem} ${e.opts.map((o) => o.t).join(' ')} ${e.why}`);
      return { node, score, item: e };
    }),
    work: ch.works.map((w) => {
      const [node, score] = locate(`${w.h} ${w.d}`);
      return { node, score, item: w };
    }),
    ask: ch.asks.map((a) => {
      const [node, score] = locate(`${a.q} ${a.a}`);
      return { node, score, item: a };
    }),
  };
}

/* ── 文本测量：中文与拉丁混排时按字数估宽度必然溢出，必须真测量 ── */
let mctx: CanvasRenderingContext2D | null = null;
let mfont = '';

function fontStack(): string {
  if (typeof document === 'undefined') return 'sans-serif';
  return getComputedStyle(document.body).fontFamily || 'sans-serif';
}

function measure(s: string, px: number, weight: number): number {
  if (typeof document === 'undefined') return s.length * px;
  if (!mctx) mctx = document.createElement('canvas').getContext('2d');
  if (!mctx) return s.length * px;
  const f = `${weight} ${px}px ${fontStack()}`;
  if (f !== mfont) {
    mctx.font = f;
    mfont = f;
  }
  return mctx.measureText(s).width;
}

/** 按像素宽度折行，最多 maxLines 行；超出用省略号收尾 */
function wrap(s: string, maxPx: number, px: number, maxLines = 2): string[] {
  const t = String(s || '').replace(/\s+/g, ' ').trim();
  if (!t) return [];
  const out: string[] = [];
  let cur = '';
  for (const ch of t) {
    if (measure(cur + ch, px, 600) > maxPx && cur) {
      out.push(cur);
      cur = ch;
      if (out.length === maxLines) break;
    } else {
      cur += ch;
    }
  }
  if (out.length < maxLines) {
    if (cur) out.push(cur);
    return out;
  }
  let last = out[maxLines - 1] ?? '';
  while (last && measure(`${last}…`, px, 600) > maxPx) last = last.slice(0, -1);
  out[maxLines - 1] = `${last}…`;
  return out;
}

/* ── 几何：把「怎么摆」和「怎么画」分开，React 只负责画 ────────── */
type Kind = 'flow' | 'stack' | 'timeline' | 'compare';

interface NodeGeo {
  i: number;
  x: number;
  y: number;
  w: number;
  h: number;
  lines: string[];
  sub: string;
}

interface LinkGeo {
  d: string;
  kind: 'arrow' | 'axis';
}

export interface Layout {
  /** 实际生效的图形（窄屏会把 timeline/compare 降级成 flow） */
  kind: Kind;
  nodes: NodeGeo[];
  links: LinkGeo[];
  dots: { cx: number; cy: number; i: number }[];
  labels: { x: number; y: number; text: string }[];
  height: number;
}

const NODE_H: Record<Kind, number> = { flow: 74, stack: 76, timeline: 72, compare: 78 };

function buildLayout(rawKind: Kind, secs: VizSec[], W: number): Layout {
  /* 窄屏上徽章退化成「只显示数字」的小胶囊，给标题腾回 ~44px */
  const room = W < 460 ? 44 : 88;
  /* 窄屏（手机上主栏 ~360px）两列布局会把标题挤成一行几个字，直接降级成纵向链 */
  /* ① 窄屏两列会挤成一列几个字，降级成纵向链；
     ② compare 实际只是「把一串小节排成两列」，节点太少时两列没有意义。 */
  const kind: Kind =
    ((rawKind === 'timeline' || rawKind === 'compare') && W < 560) || (rawKind === 'compare' && secs.length < 3)
      ? 'flow'
      : rawKind;
  const H = NODE_H[kind];
  const nodes: NodeGeo[] = [];
  const links: LinkGeo[] = [];
  const dots: { cx: number; cy: number; i: number }[] = [];
  const labels: { x: number; y: number; text: string }[] = [];

  if (kind === 'stack') {
    /* 原工作台在左侧印了一列 0x7ff0 之类的假地址；嵌入后宽度只有一半，
       那列字会被节点压住，而且地址是编的——不如不留。层次靠堆叠本身表达。 */
    const X = 24;
    const NW = W - 48;
    const y0 = 18;
    secs.forEach((s, i) => {
      nodes.push({
        i,
        x: X,
        y: y0 + i * (H + 10),
        w: NW,
        h: H,
        lines: wrap(s.h, NW - 36 - room, 15),
        sub: s.s ? wrap(s.s, NW - 36, 13, 1)[0] ?? '' : '',
      });
    });
    return { kind, nodes, links, dots, labels, height: y0 + secs.length * (H + 10) };
  }

  if (kind === 'timeline') {
    const X = 28;
    const NW = (W - 56 - 44) / 2;
    const y0 = 24;
    const AX = X + NW + 22;
    links.push({ d: `M${AX} ${y0 - 4} V${y0 + secs.length * (H + 22)}`, kind: 'axis' });
    secs.forEach((s, i) => {
      const y = y0 + i * (H + 22);
      const left = i % 2 === 0;
      dots.push({ cx: AX, cy: y + 16, i });
      nodes.push({
        i,
        x: left ? X : AX + 16,
        y,
        w: NW,
        h: H,
        lines: wrap(s.h, NW - 30 - room, 15),
        sub: s.s ? wrap(s.s, NW - 30, 13, 1)[0] ?? '' : '',
      });
    });
    return { kind, nodes, links, dots, labels, height: y0 + secs.length * (H + 22) };
  }

  if (kind === 'compare') {
    const X = 26;
    const GAPC = 24;
    const CW = (W - 52 - GAPC) / 2;
    const y0 = 48;
    /* 原工作台写的是「A 侧 / B 侧」，但 compare 的判定只来自标题里的 vs/区别，
       小节本身仍是一串顺序——两列只是排版，不是两个阵营。标签据实写。 */
    const half = Math.ceil(secs.length / 2);
    labels.push({ x: X, y: 24, text: `前半 · 第 1–${half} 节` });
    labels.push({ x: X + CW + GAPC, y: 24, text: `后半 · 第 ${half + 1}–${secs.length} 节` });
    secs.forEach((s, i) => {
      const right = i >= half;
      nodes.push({
        i,
        x: right ? X + CW + GAPC : X,
        y: y0 + (right ? i - half : i) * (H + 14),
        w: CW,
        h: H,
        lines: wrap(s.h, CW - 30 - room, 15),
        sub: s.s ? wrap(s.s, CW - 30, 13, 1)[0] ?? '' : '',
      });
    });
    return { kind, nodes, links, dots, labels, height: y0 + half * (H + 14) };
  }

  // flow
  /* 手机上主栏只有 ~340px，左右各留 16px 就够；桌面留 24px 更透气 */
  const narrow = W < 460;
  const X = narrow ? 16 : 24;
  const NW = W - X * 2;
  const GAP = 26;
  const y0 = 16;
  secs.forEach((s, i) => {
    const y = y0 + i * (H + GAP);
    nodes.push({
      i,
      x: X,
      y,
      w: NW,
      h: H,
      lines: wrap(s.h, NW - 36 - room, 15),
      sub: s.s ? wrap(s.s, NW - 36, 13, 1)[0] ?? '' : '',
    });
    if (i < secs.length - 1) {
      links.push({ d: `M${X + 22} ${y + H} v${GAP}`, kind: 'arrow' });
      links.push({ d: `M${X + 16} ${y + H + GAP - 8} L${X + 22} ${y + H + GAP} L${X + 28} ${y + H + GAP - 8}`, kind: 'arrow' });
    }
  });
  return { kind, nodes, links, dots, labels, height: y0 + secs.length * (H + GAP) - GAP + 14 };
}

const KIND_NAME: Record<Kind, string> = {
  flow: '机制链',
  stack: '内存 / 层次',
  timeline: '时序',
  compare: '双列阅读',
};

const MODE_NAME: Record<VizMode, string> = { exam: '考试真题', work: '线上事故', ask: '面试追问' };
const MODE_SHORT: Record<VizMode, string> = { exam: '真题', work: '事故', ask: '追问' };
const MODE_ORDER: VizMode[] = ['exam', 'work', 'ask'];

function tidyTitle(t: string): string {
  return String(t || '')
    .replace(/^§[\d.]+\s*/, '')
    .replace(/^[一二三四五六七八九十]+、/, '')
    .replace(/^[\d.]+\s*[·•]?\s*/, '')
    .replace(/^[·•]\s*/, '');
}

/* ── 数据加载：按学科懒加载，组件卸载后不 setState ───────────────── */
function useVizSubject(subject: string) {
  const [chapters, setChapters] = useState<VizChapter[]>(() => peekVizChapters(subject) ?? []);
  const [loading, setLoading] = useState(() => !peekVizChapters(subject));

  useEffect(() => {
    const cached = peekVizChapters(subject);
    if (cached) {
      setChapters(cached);
      setLoading(false);
      return;
    }
    let alive = true;
    setLoading(true);
    setChapters([]);
    loadVizChapters(subject)
      .then((list) => {
        if (!alive) return;
        setChapters(list);
        setLoading(false);
      })
      .catch(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [subject]);

  return { chapters, loading };
}

/* ── 主组件 ─────────────────────────────────────────────────────── */
export function ConceptViz({ subject, chapterId }: { subject: string; chapterId: string }) {
  const { chapters, loading } = useVizSubject(subject);
  const chapter = useMemo(() => chapters.find((c) => c.id === chapterId), [chapters, chapterId]);

  const [con, setCon] = useState(0);
  const [step, setStep] = useState(0);
  const [mode, setMode] = useState<VizMode>('exam');
  const [item, setItem] = useState(-1);
  const [revealed, setRevealed] = useState(false);
  const hostRef = useRef<HTMLDivElement>(null);

  // 章节换了 → 回到第一个概念第一节
  useEffect(() => {
    setCon(0);
    setStep(0);
    setMode('exam');
    setItem(-1);
    setRevealed(false);
  }, [chapterId]);

  const concept = chapter?.concepts[con];
  const secs = concept ? concept.secs : [];

  const width = useMeasureWidth(hostRef, concept?.id ?? '');

  const bind = useMemo(() => (chapter && concept ? mapItems(chapter, concept) : EMPTY_BIND), [chapter, concept]);

  const marks = useMemo(() => {
    const m: Record<VizMode, Map<number, number>> = { exam: new Map(), work: new Map(), ask: new Map() };
    MODE_ORDER.forEach((k) => {
      bind[k].forEach((it) => {
        if (it.node < 0) return;
        m[k].set(it.node, (m[k].get(it.node) ?? 0) + 1);
      });
    });
    return m;
  }, [bind]);

  const layout = useMemo(
    () => buildLayout((concept?.kind ?? 'flow') as Kind, secs, Math.max(280, width)),
    [concept, secs, width],
  );

  const current = secs[step];
  const list = bind[mode];
  const cur = item >= 0 && list[item] ? list[item] : null;
  const hitHere = list.map((h, i) => ({ h, i })).filter((x) => x.h.node === step && x.h.score >= HIT_THRESHOLD);

  const goto = (i: number) => {
    if (!secs.length) return;
    const next = Math.max(0, Math.min(i, secs.length - 1));
    setStep(next);
    const hit = list.findIndex((x) => x.node === next && x.score >= HIT_THRESHOLD);
    setItem(hit);
    setRevealed(false);
  };

  const pickConcept = (i: number) => {
    setCon(i);
    setStep(0);
    setItem(-1);
    setRevealed(false);
  };

  const pickMode = (m: VizMode) => {
    setMode(m);
    const hit = bind[m].findIndex((x) => x.node === step && x.score >= HIT_THRESHOLD);
    setItem(hit);
    setRevealed(false);
  };

  if (loading) {
    return (
      <div className="km-viz km-viz-skeleton" aria-busy="true">
        <span>正在装配本章机制图…</span>
      </div>
    );
  }

  if (!chapter || !concept || !secs.length) {
    return (
      <div className="km-viz km-viz-empty">
        <b>本章暂无机制图</b>
        <span>图解是从 concept 的 `##` 小节抽的；补齐正文后重跑一次生成器就会出现。</span>
      </div>
    );
  }

  const modeLabel = MODE_NAME[mode];
  const hitCount = [...marks[mode].keys()].length;
  /* 手机上徽章只放得下一个数字：文字留给标题，工具提示仍给完整说明 */
  const narrowBadge = Math.max(280, width) < 460;
  const badgeW = narrowBadge ? 34 : BADGE_W;

  return (
    <section className="km-viz" data-mode={mode} aria-label="本章机制图解">
      {/* 头：这是哪张图、几个节点、被几个场景打中 */}
      <header className="km-viz-head">
        <span className="km-viz-eyebrow">机制图解</span>
        <h4 className="km-viz-title">{tidyTitle(concept.title)}</h4>
        <div className="km-viz-meta">
          <span className="km-viz-chip k">{KIND_NAME[layout.kind]}</span>
          <span className="km-viz-chip">{secs.length} 节</span>
          <span className="km-viz-chip hit">
            {hitCount}/{secs.length} 节被击中
          </span>
        </div>
      </header>

      {/* 本章概念切换：一章通常 3~6 个概念 */}
      {chapter.concepts.length > 1 && (
        <div className="km-viz-cons" role="tablist" aria-label="本章概念">
          {chapter.concepts.map((c, i) => (
            <button
              key={c.id}
              type="button"
              role="tab"
              aria-selected={i === con}
              className={i === con ? 'on' : ''}
              onClick={() => pickConcept(i)}
              title={tidyTitle(c.title)}
            >
              {tidyTitle(c.title)}
            </button>
          ))}
        </div>
      )}

      {/* 三个场景灯 */}
      <div className="km-viz-modes" role="tablist" aria-label="场景">
        {MODE_ORDER.map((m) => (
          <button key={m} type="button" role="tab" aria-selected={m === mode} className={m === mode ? 'on' : ''} onClick={() => pickMode(m)}>
            {MODE_NAME[m]}
            <em>{bind[m].length}</em>
          </button>
        ))}
      </div>

      {/* 图 */}
      <div className={`km-viz-canvas${layout.height > 720 ? ' tall' : ''}`} ref={hostRef}>
        <svg
          viewBox={`0 0 ${Math.max(280, width)} ${layout.height}`}
          width="100%"
          role="img"
          style={{ fontFamily: fontStack() }}
          aria-label={`${concept.title} 的${KIND_NAME[layout.kind]}图`}
        >
          {layout.labels.map((l, i) => (
            <text key={`lb${i}`} x={l.x} y={l.y} className="vz-axis-label">
              {l.text}
            </text>
          ))}
          {layout.links.map((l, i) => (
            <path key={`lk${i}`} d={l.d} className={l.kind === 'axis' ? 'vz-axis' : 'vz-arrow'} />
          ))}
          {layout.dots.map((d) => (
            <circle key={`dt${d.i}`} cx={d.cx} cy={d.cy} r={d.i === step ? 9 : 6} className={`vz-dot${d.i === step ? ' on' : ''}`} />
          ))}
          {layout.nodes.map((n) => {
            const hits = marks[mode].get(n.i) ?? 0;
            const active = n.i === step;
            return (
              <g
                key={`nd${n.i}`}
                className="vz-node"
                data-hit={hits > 0 ? '1' : '0'}
                data-active={active ? '1' : '0'}
                tabIndex={0}
                role="button"
                aria-label={`第 ${n.i + 1} 节 ${secs[n.i]?.h ?? ''}`}
                aria-pressed={active}
                onClick={() => goto(n.i)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    goto(n.i);
                  }
                }}
              >
                <rect className="vz-bg" x={n.x} y={n.y} width={n.w} height={n.h} rx={12} />
                {hits > 0 && !active && <rect className="vz-flag" x={n.x} y={n.y + 10} width={4} height={n.h - 20} rx={2} />}
                {n.lines.map((ln, k) => (
                  <text
                    key={`t${k}`}
                    className="vz-node-title"
                    x={n.x + 18}
                    y={n.y + (n.lines.length === 1 ? n.h / 2 + (n.sub ? -4 : 5) : 24 + k * 20)}
                  >
                    {ln}
                  </text>
                ))}
                {n.sub && n.lines.length === 1 && (
                  <text className="vz-node-sub" x={n.x + 18} y={n.y + n.h - 12}>
                    {n.sub}
                  </text>
                )}
                {hits > 0 && (
                  <g className="vz-badge" aria-label={`${MODE_SHORT[mode]} ${hits} 条`}>
                    <rect
                      x={n.x + n.w - badgeW - 12}
                      y={n.y + 12}
                      width={badgeW}
                      height={24}
                      rx={12}
                    />
                    <text x={n.x + n.w - badgeW / 2 - 12} y={n.y + 29}>
                      {narrowBadge ? hits : `${MODE_SHORT[mode]} ${hits}`}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {layout.height > 720 && <span className="km-viz-scrollhint">图比较高，可上下滚动；也可以直接用下面的「下一节」逐节走</span>}

      {/* 步进 */}
      <div className="km-viz-step">
        <button type="button" className="km-viz-nav" onClick={() => goto(step - 1)} disabled={step === 0} aria-label="上一节">
          上一节
        </button>
        <div className="km-viz-dots" role="tablist" aria-label="小节">
          {secs.map((s, i) => (
            <button
              key={`p${i}`}
              type="button"
              role="tab"
              aria-selected={i === step}
              aria-label={s.h}
              className={i === step ? 'on' : ''}
              onClick={() => goto(i)}
            />
          ))}
        </div>
        <button
          type="button"
          className="km-viz-nav"
          onClick={() => goto(step + 1)}
          disabled={step === secs.length - 1}
          aria-label="下一节"
        >
          下一节
        </button>
        <span className="km-viz-count">
          {step + 1} / {secs.length} 节
        </span>
      </div>

      {/* 当前节正文快照 */}
      <div className="km-viz-nodebox">
        <h5>{current?.h ?? ''}</h5>
        <p>{current?.s || '这一节以代码 / 表格为主，点上面的节点或下面的条目，看它被怎么考、怎么翻车。'}</p>
        {current?.c && (
          <pre>
            <code>{current.c.code}</code>
          </pre>
        )}
      </div>

      {/* 场景：本节命中项优先，本章全量可展开 */}
      <div className="km-viz-scene">
        <div className="km-viz-scene-head">
          <b>{modeLabel}</b>
          <span>
            只读引用 ·{' '}
            {mode === 'exam' ? '本章 exercises.json' : mode === 'work' ? '本章 pitfalls.md' : '本章 interview.json'}
          </span>
        </div>

        {hitHere.length > 0 ? (
          <ul className="km-viz-hits">
            {hitHere.map(({ h, i }) => (
              <li key={`h${i}`}>
                <button
                  type="button"
                  className={`km-viz-hit${i === item ? ' on' : ''}`}
                  onClick={() => {
                    setItem(i);
                    setRevealed(false);
                  }}
                >
                  <b>{itemTitle(mode, h)}</b>
                  <i>打在第 {h.node + 1} 节</i>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="km-viz-none">这一节没有被{modeLabel}直接命中。下面是本章的全部条目，点一条可以跳到它咬住的那一节。</p>
        )}

        {cur && revealed && <AnswerBox mode={mode} item={cur.item} />}

        {!revealed && cur && (
          <button type="button" className="km-viz-reveal" onClick={() => setRevealed(true)}>
            {mode === 'exam' ? '看答案与解析' : mode === 'ask' ? '看参考回答' : '看现场经过'}
          </button>
        )}

        <details className="km-viz-all">
          <summary>
            本章全部 {list.length} 条{modeLabel}
          </summary>
          <ul>
            {list.map((h, i) => (
              <li key={`a${i}`}>
                <button
                  type="button"
                  className={`km-viz-hit${i === item ? ' on' : ''}`}
                  onClick={() => {
                    setItem(i);
                    setRevealed(false);
                    if (h.node >= 0) goto(h.node);
                  }}
                >
                  <b>{itemTitle(mode, h)}</b>
                  <i>{h.score >= HIT_THRESHOLD ? `打在第 ${h.node + 1} 节` : '未匹配到具体小节'}</i>
                </button>
              </li>
            ))}
          </ul>
        </details>
      </div>

      <span className="km-viz-hint">点图上的任意一节，可以看它被哪些题 / 事故咬住。</span>
    </section>
  );
}

/* ── 小工具 ─────────────────────────────────────────────────────── */

function useMeasureWidth(ref: React.RefObject<HTMLDivElement | null>, key: string): number {
  const [w, setW] = useState(640);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    /* SVG 的可用宽度 = 内容盒宽度（clientWidth 含 padding，要减掉），
       否则 viewBox 比实际宽，右侧徽章与文字会溢出画布。 */
    const read = (cw?: number) => {
      let w = cw;
      if (w == null) {
        const cs = getComputedStyle(el);
        w = el.clientWidth - parseFloat(cs.paddingLeft || '0') - parseFloat(cs.paddingRight || '0');
      }
      if (w > 200) setW(Math.floor(w));
    };
    read();
    if (typeof ResizeObserver === 'undefined') {
      const onResize = () => read();
      window.addEventListener('resize', onResize);
      return () => window.removeEventListener('resize', onResize);
    }
    const ro = new ResizeObserver((entries) => read(entries[0]?.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref, key]);
  return w;
}

/* 徽章固定宽度：等宽出现得更整齐，也不必再赌 measure 与 SVG 渲染字体一致。
   78px 足够放下「事故 12」这种最长组合（13px × 5 字 + 内边距）。 */
const BADGE_W = 78;


function itemTitle(mode: VizMode, h: BoundExam | BoundWork | BoundAsk): string {
  if (mode === 'exam') return (h as BoundExam).item.q;
  if (mode === 'work') return (h as BoundWork).item.h;
  return (h as BoundAsk).item.q;
}

function AnswerBox({ mode, item }: { mode: VizMode; item: VizChapter['exams'][number] | VizChapter['works'][number] | VizChapter['asks'][number] }) {
  if (mode === 'exam') {
    const e = item as VizChapter['exams'][number];
    return (
      <div className="km-viz-answer">
        <p className="stem">{e.stem || e.q}</p>
        {e.opts.length > 0 && (
          <ul className="opts">
            {e.opts.map((o) => (
              <li key={o.k}>
                <b>{o.k}</b>
                {o.t}
              </li>
            ))}
          </ul>
        )}
        <p className="ans">
          <b>答案 {e.ans}</b>
          {e.why}
        </p>
      </div>
    );
  }
  if (mode === 'work') {
    const w = item as VizChapter['works'][number];
    return (
      <div className="km-viz-answer">
        <p className="stem">{w.d}</p>
      </div>
    );
  }
  const a = item as VizChapter['asks'][number];
  return (
    <div className="km-viz-answer">
      <p className="stem">{a.a}</p>
      {a.fu.length > 0 && <p className="fu">追问：{a.fu.join(' / ')}</p>}
    </div>
  );
}
