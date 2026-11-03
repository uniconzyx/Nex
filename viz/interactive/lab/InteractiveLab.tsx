/**
 * ═══════════════════════════════════════════════════════════════════════════
 *  凯喵 Code 试炼录 · 全科目交互模块（数据驱动）
 * ───────────────────────────────────────────────────────────────────────────
 *  这个文件不认学科，只认 `interactive.json`。
 *  新增一章的交互，走 `python scripts/gen_interactive.py`，不改这里一行。
 *
 *  玩法（按 mod.kind 分派）
 *    sequence  时序连线   拖事件卡进时间轴槽，按时序回放，走完才判对错
 *    match     配对连线   左栏「出事的写法」↔ 右栏「正确做法」，一连连上
 *    boss      真题打靶   答对削一层护甲，三题清场
 *    fill      代码挖空   把缺失的标识符拖回代码里的空位
 *
 *  视觉与物理：全部复用 mw-ch04/CacheDesignLab.tsx 的令牌（单一色源）
 *    C / glass() / TAP(0.95) / SPRING(300,20) / DRAG_ELASTIC(0.2)
 *    ScenarioBar（工作现场 / 考场视角）· KaimaoBubble（右下常驻）
 * ═══════════════════════════════════════════════════════════════════════════
 */

import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { motion, useAnimationControls } from 'framer-motion';
import type { PanInfo } from 'framer-motion';

import {
  C,
  MONO,
  SANS,
  glass,
  TAP,
  SPRING,
  DRAG_ELASTIC,
  ScenarioBar,
  KaimaoBubble,
  useKaimao,
  Burst,
} from '../mw-ch04/CacheDesignLab';
import type { LabData, LabModule, DualScenario } from './types';

/* ───────────────────────────── 小工具 ───────────────────────────── */

function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** 确定性洗牌：同一个 seed 每次刷新都是同一顺序，E2E 断言才稳 */
function shuffleSeeded<T>(arr: readonly T[], seed: number): T[] {
  const a = arr.slice();
  let s = seed || 1;
  for (let i = a.length - 1; i > 0; i--) {
    s = (s * 1664525 + 1013904223) >>> 0;
    const j = s % (i + 1);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

type Pt = { x: number; y: number };

/**
 * 落点判定。
 * 用 getBoundingClientRect 与 pointer 视口坐标比对 —— 不要用 offsetParent 链，
 * 拖拽元素在 transform 里，祖先偏移会让"看着在框上其实差 100px"。
 */
function hitTest(
  refs: React.MutableRefObject<Record<string, HTMLElement | null>>,
  point: Pt,
  keys: string[],
): string | null {
  for (const k of keys) {
    const el = refs.current[k];
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (point.x >= r.left && point.x <= r.right && point.y >= r.top && point.y <= r.bottom) {
      return k;
    }
  }
  return null;
}

/** 把一行里的 `‹n›` 占位符切开：`marker` 形如 `‹%n›`，`%n` 是通配 */
function splitMarker(line: string, marker: string): { text: string; n?: number }[] {
  const at = marker.indexOf('%n');
  const open = marker.slice(0, at);
  const close = marker.slice(at + 2);
  const out: { text: string; n?: number }[] = [];
  let i = 0;
  while (i < line.length) {
    const a = line.indexOf(open, i);
    if (a < 0) {
      out.push({ text: line.slice(i) });
      break;
    }
    const b = close ? line.indexOf(close, a + open.length) : -1;
    if (b < 0) {
      out.push({ text: line.slice(i) });
      break;
    }
    if (a > i) out.push({ text: line.slice(i, a) });
    const num = parseInt(line.slice(a + open.length, b), 10);
    out.push({ text: '', n: Number.isFinite(num) ? num : undefined });
    i = b + close.length;
  }
  return out;
}

const Node: React.FC<{ on: boolean; tone?: string; size?: number }> = ({ on, tone = C.ice, size = 9 }) => (
  <span
    style={{
      display: 'inline-block',
      width: size,
      height: size,
      background: on ? tone : 'transparent',
      border: `1.5px solid ${on ? tone : C.line}`,
      clipPath: 'polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%)',
      transition: 'background .18s, border-color .18s',
    }}
  />
);

/* ═══════════════════════════ 玩法 B · 时序连线 ═══════════════════════════ */

interface SeqProps {
  heading: string;
  steps: string[];
  seed: number;
}

/**
 * 时间轴从左到右（窄屏从上到下）是一条竖轨：每格左侧是节点 + 轨道，右侧是事件卡。
 * 卡片全部落位后才能「按时序执行」—— 回放会逐格点亮轨道，走到尽头才给结论。
 * 只判「槽位编号 === 步骤编号」，所以没有模糊地带。
 */
export const SequenceLine: React.FC<SeqProps> = ({ heading, steps, seed }) => {
  const n = steps.length;
  const [order, setOrder] = useState<(number | null)[]>(() => Array(n).fill(null));
  const [tray, setTray] = useState<number[]>(() => shuffleSeeded(steps.map((_, i) => i), seed));
  const [phase, setPhase] = useState<'idle' | 'run' | 'ok' | 'bad'>('idle');
  const [cursor, setCursor] = useState(-1);
  const [burstAt, setBurstAt] = useState(0);
  const { line, say } = useKaimao('把事件按真实发生顺序拖进轨道，我再按时序回放一遍。');

  const slots = useRef<Record<string, HTMLElement | null>>({});
  const slotKeys = useMemo(() => Array.from({ length: n }, (_, i) => `s${i}`), [n]);

  const filled = order.every((x) => x !== null);

  /** 回放：逐格推进，最后一格停住再判定 */
  useEffect(() => {
    if (phase !== 'run') return;
    if (cursor >= n - 1) {
      const firstBad = order.findIndex((v, i) => v !== i);
      if (firstBad < 0) {
        setPhase('ok');
        setBurstAt((x) => x + 1);
        say('seq', '时序全对！这条链路可以交付了。', '时序只要有一格错位，整条链的因果就断了；先记住每条规则自己走完的顺序，再谈优化。', 'ok');
      } else {
        setPhase('bad');
        say('seqbad', `第 ${firstBad + 1} 格就错位了 —— 因果链从这里断的。`,
          '顺序题不要背全表：先找「谁必须先发生」的锚点（通常是读/写的起点），再往后推依赖。', 'warn');
      }
      return;
    }
    const t = window.setTimeout(() => setCursor((c) => c + 1), 420);
    return () => window.clearTimeout(t);
  }, [phase, cursor, n, order, say]);

  const start = () => {
    if (!filled) {
      say('seqneed', '还有格子空着，先把卡都放上去。', '空槽在回放时会变成「什么都没发生」，那整条时序就没有意义了。', 'warn');
      return;
    }
    setCursor(-1);
    setPhase('run');
    // TODO: play run_timeline.mp3
  };

  const place = (stepId: number, slotIdx: number) => {
    setOrder((prev) => {
      const next = prev.slice();
      const from = next.indexOf(stepId);
      if (from >= 0) next[from] = null;
      const evicted = next[slotIdx];
      next[slotIdx] = stepId;
      if (evicted !== null && evicted !== stepId) {
        setTray((t) => (t.includes(evicted) ? t : [...t, evicted]));
      }
      return next;
    });
    setTray((t) => t.filter((x) => x !== stepId));
    setPhase('idle');
    setCursor(-1);
    // TODO: play drop_snap.mp3
  };

  const pullOut = (slotIdx: number) => {
    const v = order[slotIdx];
    if (v === null) return;
    setOrder((prev) => {
      const next = prev.slice();
      next[slotIdx] = null;
      return next;
    });
    setTray((t) => (t.includes(v) ? t : [...t, v]));
    setPhase('idle');
    setCursor(-1);
  };

  const onDragEnd = (stepId: number) => (_: unknown, info: PanInfo) => {
    const k = hitTest(slots, info.point, slotKeys);
    if (k) place(stepId, Number(k.slice(1)));
    else say('seqmiss', '没落在轨道上，再拖一次。', '拖拽的落点按松手时的指针位置算 —— 松手前先看清目标格。', 'idle');
  };

  const firstBad = phase === 'bad' ? order.findIndex((v, i) => v !== i) : -1;

  return (
    <div style={{ position: 'relative', paddingBottom: 54 }}>
      <div style={glass({ padding: '10px 12px', marginBottom: 10, background: 'rgba(255,255,255,0.5)' })}>
        <div style={{ fontSize: 12, color: C.mute, lineHeight: 1.6 }}>
          时序来源：<span style={{ color: C.iceDeep, fontWeight: 500 }}>{heading}</span>
          <span style={{ marginLeft: 6, opacity: 0.8 }}>· {n} 步</span>
        </div>
      </div>

      {/* 轨道 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }} data-seq-track>
        {Array.from({ length: n }, (_, i) => {
          const v = order[i];
          const active = phase === 'run' && cursor >= i;
          const wrong = phase === 'bad' && i === firstBad;
          const right = (phase === 'run' && cursor >= i) || phase === 'ok';
          const tone = wrong ? C.coral : right ? C.mint : C.ice;
          return (
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'stretch' }}>
              {/* 节点列：竖轨 + 六边形节点 */}
              <div
                style={{
                  position: 'relative',
                  width: 20,
                  flex: '0 0 20px',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    top: i === 0 ? '50%' : 0,
                    bottom: i === n - 1 ? '50%' : 0,
                    width: 2,
                    background: active
                      ? `linear-gradient(180deg, ${tone}, ${tone})`
                      : `repeating-linear-gradient(180deg, ${C.line} 0 4px, transparent 4px 8px)`,
                    transition: 'background .2s',
                  }}
                />
                <Node on={v !== null || active} tone={tone} size={active ? 13 : 10} />
              </div>

              {/* 槽位 */}
              <div
                ref={(el) => {
                  slots.current[`s${i}`] = el;
                }}
                data-seq-slot={i}
                data-seq-filled={v !== null ? '1' : '0'}
                style={{
                  flex: 1,
                  minWidth: 0,          // 没有它，长 token（$k+(n-1)$ / URL）会把整行撑出视口
                  minHeight: 46,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: v !== null ? '9px 12px' : '9px 12px',
                  borderRadius: 12,
                  border: `1.5px ${v !== null ? 'solid' : 'dashed'} ${
                    wrong ? C.coral : active ? C.mint : v !== null ? C.iceSoft : C.line
                  }`,
                  background: wrong
                    ? 'rgba(248,113,113,0.10)'
                    : active
                      ? 'rgba(49,208,170,0.10)'
                      : v !== null
                        ? 'rgba(255,255,255,0.72)'
                        : 'rgba(255,255,255,0.35)',
                  transition: 'border-color .18s, background .18s',
                }}
                onClick={() => pullOut(i)}
              >
                <span
                  style={{
                    fontFamily: MONO,
                    fontSize: 10.5,
                    color: v !== null ? C.iceDeep : C.mute,
                    flex: '0 0 22px',
                  }}
                >
                  {String(i + 1).padStart(2, '0')}
                </span>
                {v !== null ? (
                  <motion.span
                    key={`${i}-${v}`}
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={SPRING}
                    style={{ fontSize: 13, lineHeight: 1.5, color: C.slate, overflowWrap: 'anywhere' }}
                  >
                    {steps[v]}
                  </motion.span>
                ) : (
                  // 只在第一个空槽给引导语 —— 六行都写一遍太吵
                  i === 0 && (
                    <span style={{ fontSize: 12, color: C.mute, opacity: 0.7 }}>
                      把事件卡按发生顺序拖进来
                    </span>
                  )
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 托盘 */}
      {tray.length > 0 && (
        <div style={{ marginTop: 11 }}>
          <div style={{ fontSize: 11, color: C.mute, marginBottom: 6, letterSpacing: 0.2 }}>
            待放置 · {tray.length}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }} data-seq-tray>
            {tray.map((sid) => (
              <motion.div
                key={sid}
                drag
                dragElastic={DRAG_ELASTIC}
                dragSnapToOrigin
                whileDrag={{ scale: 1.04, zIndex: 30, cursor: 'grabbing' }}
                whileTap={TAP}
                onDragEnd={onDragEnd(sid)}
                data-seq-card={sid}
                style={{
                  ...glass({ padding: '8px 11px', cursor: 'grab', maxWidth: 320 }),
                  fontSize: 12.5,
                  lineHeight: 1.5,
                  color: C.slate,
                }}
              >
                {steps[sid]}
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* 操作条 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 12, flexWrap: 'wrap' }}>
        <motion.button
          type="button"
          whileTap={TAP}
          onClick={start}
          data-seq-run
          style={{
            border: 'none',
            borderRadius: 10,
            padding: '8px 16px',
            fontSize: 12.5,
            fontWeight: 600,
            color: '#fff',
            cursor: 'pointer',
            background: filled ? `linear-gradient(135deg, ${C.ice}, ${C.iceDeep})` : C.iceSoft,
            fontFamily: SANS,
          }}
        >
          {phase === 'run' ? '回放中…' : '按时序执行'}
        </motion.button>
        {phase === 'ok' && (
          <span style={{ fontSize: 12.5, color: C.mintDeep, fontWeight: 600 }}>✓ 时序正确，链路打通</span>
        )}
        {phase === 'bad' && (
          <span style={{ fontSize: 12.5, color: C.coralDeep, fontWeight: 600 }}>
            第 {firstBad + 1} 格错位 · 点卡片可取出重放
          </span>
        )}
        <Burst play={burstAt} color={C.mint} />
      </div>

      <KaimaoBubble line={line} />
    </div>
  );
};

/* ═══════════════════════════ 玩法 B · 配对连线 ═══════════════════════════ */

interface MatchProps {
  pairs: { id: number; left: string; right: string }[];
  seed: number;
  tip?: string;
}

/**
 * 左「出事的写法」右「正确做法」，点左再点右即连线。
 * 线是真的线：SVG 覆盖层按 ref 实测卡片圆心画贝塞尔，窗口 resize 会重算。
 */
export const PairLink: React.FC<MatchProps> = ({ pairs, seed, tip }) => {
  const [pickLeft, setPickLeft] = useState<number | null>(null);
  const [links, setLinks] = useState<{ l: number; r: number }[]>([]);
  const [burstAt, setBurstAt] = useState(0);
  const [geo, setGeo] = useState<{ l: Pt; r: Pt }[]>([]);
  const shake = useAnimationControls();
  const { line, say } = useKaimao(tip || '先把左边的「事故」读完，再去右边找它唯一对应的正解。');

  const rightOrder = useMemo(() => shuffleSeeded(pairs, seed), [pairs, seed]);
  const leftOrder = pairs; // 左栏保持原序：易错点在原文里本来就是递进的
  const box = useRef<HTMLDivElement | null>(null);
  const lrefs = useRef<Record<string, HTMLElement | null>>({});
  const rrefs = useRef<Record<string, HTMLElement | null>>({});

  const done = links.length === pairs.length;

  const measure = useCallback(() => {
    const b = box.current;
    if (!b) return;
    const bb = b.getBoundingClientRect();
    const next: { l: Pt; r: Pt }[] = [];
    for (const { l, r } of links) {
      const le = lrefs.current[`l${l}`];
      const re = rrefs.current[`r${r}`];
      if (!le || !re) continue;
      const a = le.getBoundingClientRect();
      const c = re.getBoundingClientRect();
      next.push({
        l: { x: a.right - bb.left, y: a.top - bb.top + a.height / 2 },
        r: { x: c.left - bb.left, y: c.top - bb.top + c.height / 2 },
      });
    }
    setGeo(next);
  }, [links]);

  useLayoutEffect(() => {
    measure();
    const ro = new ResizeObserver(measure);
    if (box.current) ro.observe(box.current);
    window.addEventListener('resize', measure);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [measure]);

  const clickRight = (id: number) => {
    if (pickLeft === null) {
      say('matchright', '先在左边挑一条事故，再来右边配正解。', '配对题的顺序是「先定位症状，再找对策」——反过来容易被选项牵着走。', 'idle');
      return;
    }
    if (links.some((x) => x.l === pickLeft)) return;
    if (pickLeft === id) {
      const next = [...links, { l: pickLeft, r: id }];
      setLinks(next);
      setPickLeft(null);
      // TODO: play pair_ok.mp3
      if (next.length === pairs.length) {
        setBurstAt((x) => x + 1);
        say('matchdone', '全连上了 —— 这套「症状 → 正解」就是考场上最快的反射。',
          '易错点记得按「症状」索引而不是按章节索引：考场上你看到的是症状，不是目录。', 'ok');
      } else {
        say('matchok', '配对成功，继续。', '配对的本质是因果唯一性：一个症状通常只有一个正解，多解说明还没读透前提。', 'ok');
      }
    } else {
      shake.start({ x: [0, -7, 7, -4, 0], transition: { duration: 0.3 } });
      setPickLeft(null);
      say('matchbad', '这两条不是一对。', '注意区分「同一类问题」和「同一个问题」——选项常常在类别上做手脚。', 'warn');
    }
  };

  const colW = '47%';

  return (
    <motion.div style={{ position: 'relative', paddingBottom: 54 }} ref={box} animate={shake}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
        <div style={{ width: colW, fontSize: 11, color: C.coralDeep, letterSpacing: 0.3 }}>出事的写法</div>
        <div style={{ width: colW, fontSize: 11, color: C.mintDeep, letterSpacing: 0.3, textAlign: 'right' }}>
          正确做法
        </div>
      </div>

      {/* 连线层 */}
      <svg
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 5 }}
        aria-hidden="true"
      >
        {geo.map((g, i) => {
          const mid = (g.l.x + g.r.x) / 2;
          return (
            <motion.path
              key={`${g.l}-${g.r}`}
              d={`M ${g.l.x} ${g.l.y} C ${mid} ${g.l.y}, ${mid} ${g.r.y}, ${g.r.x} ${g.r.y}`}
              stroke={C.mint}
              strokeWidth={2}
              fill="none"
              strokeLinecap="round"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.85 }}
              transition={{ duration: 0.32, delay: i * 0.03 }}
            />
          );
        })}
      </svg>

      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6, marginTop: 4 }}>
        <div style={{ width: colW, display: 'flex', flexDirection: 'column', gap: 7 }}>
          {leftOrder.map((p) => {
            const on = pickLeft === p.id;
            const linked = links.find((x) => x.l === p.id);
            return (
              <motion.div
                key={p.id}
                ref={(el) => {
                  lrefs.current[`l${p.id}`] = el;
                }}
                whileTap={TAP}
                onClick={() => {
                  if (linked) return;
                  setPickLeft(on ? null : p.id);
                  // TODO: play select.mp3
                }}
                data-pair-left={p.id}
                data-pair-on={on ? '1' : '0'}
                animate={
                  on
                    ? { borderColor: C.coral, x: 0, scale: 1.01 }
                    : { borderColor: linked ? C.mint : 'rgba(255,255,255,0.8)', x: 0, scale: 1 }
                }
                transition={SPRING}
                style={{
                  ...glass({ padding: '8px 10px', cursor: linked ? 'default' : 'pointer' }),
                  fontSize: 12,
                  lineHeight: 1.5,
                  color: linked ? C.mute : C.slate,
                  background: linked ? 'rgba(49,208,170,0.10)' : 'rgba(255,255,255,0.62)',
                  minWidth: 0,
                  overflowWrap: 'anywhere',
                }}
              >
                <span style={{ fontFamily: MONO, fontSize: 10, color: C.coral, marginRight: 5 }}>{p.id}</span>
                {p.left}
              </motion.div>
            );
          })}
        </div>

        <div style={{ width: colW, display: 'flex', flexDirection: 'column', gap: 7 }}>
          {rightOrder.map((p) => {
            const linked = links.some((x) => x.r === p.id);
            return (
              <motion.div
                key={p.id}
                ref={(el) => {
                  rrefs.current[`r${p.id}`] = el;
                }}
                whileTap={TAP}
                onClick={() => !linked && clickRight(p.id)}
                data-pair-right={p.id}
                animate={{ borderColor: linked ? C.mint : 'rgba(255,255,255,0.8)' }}
                transition={SPRING}
                style={{
                  ...glass({ padding: '8px 10px', cursor: linked ? 'default' : 'pointer' }),
                  fontSize: 12,
                  lineHeight: 1.5,
                  color: linked ? C.mute : C.slate,
                  background: linked ? 'rgba(49,208,170,0.10)' : 'rgba(255,255,255,0.62)',
                  minWidth: 0,
                  overflowWrap: 'anywhere',
                }}
              >
                {p.right}
              </motion.div>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 12 }}>
        <div style={glass({ padding: '5px 11px', background: 'rgba(255,255,255,0.5)' })}>
          <span style={{ fontFamily: MONO, fontSize: 11.5, color: done ? C.mintDeep : C.mute }}>
            {links.length} / {pairs.length}
          </span>
        </div>
        {done && <span style={{ fontSize: 12.5, color: C.mintDeep, fontWeight: 600 }}>✓ 全部配对完成</span>}
        <Burst play={burstAt} color={C.mint} />
      </div>

      <KaimaoBubble line={line} />
    </motion.div>
  );
};

/* ═══════════════════════════ boss · 真题打靶 ═══════════════════════════ */

interface BossProps {
  questions: { id: string; stem: string; title: string; options: { key: string; text: string }[]; correct: string[]; explain: string }[];
  seed: number;
}

export const LabBossRaid: React.FC<BossProps> = ({ questions, seed }) => {
  const [qi, setQi] = useState(0);
  const [pick, setPick] = useState<string | null>(null);
  const [judged, setJudged] = useState(false);
  const [armor, setArmor] = useState(questions.length);
  const [hits, setHits] = useState(0);
  const [burstAt, setBurstAt] = useState(0);
  const shake = useAnimationControls();
  const { line, say } = useKaimao('护甲还剩 ' + questions.length + ' 层，按真题口径打。');

  const q = questions[qi];
  const opts = useMemo(() => shuffleSeeded(q.options, seed + qi * 977), [q, seed, qi]);
  const cleared = armor <= 0;

  const submit = (key: string) => {
    if (judged) return;
    setPick(key);
    setJudged(true);
    const ok = q.correct.includes(key);
    if (ok) {
      setHits((x) => x + 1);
      setArmor((x) => x - 1);
      setBurstAt((x) => x + 1);
      // TODO: play boss_hit.mp3
      say('bosshit', '破了！这题就是标准口径。', '记住解析里的「判据」而不只是答案：判据能迁移到新题，答案不能。', 'ok');
    } else {
      shake.start({ x: [0, -9, 9, -6, 0], transition: { duration: 0.3 } });
      // TODO: play boss_miss.mp3
      say('bossmiss', `打偏了 —— 正确是 ${q.correct.join('、')}。`, '错题的价值在解析：看它把干扰项错在哪个前提上，下次就能一眼排除。', 'warn');
    }
  };

  const next = () => {
    setPick(null);
    setJudged(false);
    setQi((i) => Math.min(i + 1, questions.length - 1));
  };

  return (
    <div style={{ position: 'relative', paddingBottom: 54 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <div style={{ display: 'flex', gap: 4 }} data-armor={armor}>
          {Array.from({ length: questions.length }, (_, i) => (
            <Node key={i} on={i >= armor} tone={i < hits ? C.mintDeep : C.ice} size={11} />
          ))}
        </div>
        <span style={{ fontFamily: MONO, fontSize: 11.5, color: C.mute }}>
          第 {Math.min(qi + 1, questions.length)} / {questions.length} 题
        </span>
        {cleared && (
          <motion.span
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={SPRING}
            style={{ fontSize: 12.5, fontWeight: 700, color: C.mintDeep }}
          >
            本章通关 · {hits} 击
          </motion.span>
        )}
      </div>

      <motion.div animate={shake} style={glass({ padding: '12px 14px' })}>
        <div style={{ fontSize: 11, color: C.iceDeep, fontFamily: MONO, marginBottom: 6 }}>{q.title}</div>
        <p style={{ margin: 0, fontSize: 13, lineHeight: 1.7, color: C.slate, whiteSpace: 'pre-wrap' }}>{q.stem}</p>
      </motion.div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginTop: 9 }}>
        {opts.map((o) => {
          const right = q.correct.includes(o.key);
          const chosen = pick === o.key;
          const tone = judged
            ? right
              ? { b: C.mint, bg: 'rgba(49,208,170,0.12)', fg: C.mintDeep }
              : chosen
                ? { b: C.coral, bg: 'rgba(248,113,113,0.12)', fg: C.coralDeep }
                : { b: 'rgba(255,255,255,0.8)', bg: 'rgba(255,255,255,0.55)', fg: C.mute }
            : { b: 'rgba(255,255,255,0.8)', bg: 'rgba(255,255,255,0.62)', fg: C.slate };
          return (
            <motion.button
              key={o.key}
              type="button"
              whileTap={judged ? undefined : TAP}
              onClick={() => submit(o.key)}
              data-opt={o.key}
              animate={{ borderColor: tone.b, backgroundColor: tone.bg }}
              transition={SPRING}
              style={{
                ...glass({ padding: '9px 12px', cursor: judged ? 'default' : 'pointer' }),
                display: 'flex',
                gap: 9,
                alignItems: 'flex-start',
                textAlign: 'left',
                borderColor: tone.b,
                background: tone.bg,
                fontFamily: SANS,
              }}
            >
              <span style={{ fontFamily: MONO, fontSize: 11.5, color: tone.fg, flex: '0 0 16px', marginTop: 1 }}>
                {o.key}
              </span>
              <span style={{ fontSize: 12.5, lineHeight: 1.6, color: tone.fg }}>{o.text}</span>
            </motion.button>
          );
        })}
      </div>

      {judged && (
        <motion.div
          key={`ex${qi}`}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={SPRING}
          style={glass({
            marginTop: 9,
            padding: '10px 12px',
            borderLeft: `3px solid ${q.correct.includes(pick || '') ? C.mint : C.coral}`,
          })}
        >
          <div style={{ fontSize: 11, color: C.mute, marginBottom: 3 }}>解析</div>
          <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.7, color: C.slate }}>{q.explain}</p>
          {qi < questions.length - 1 && (
            <motion.button
              type="button"
              whileTap={TAP}
              onClick={next}
              data-boss-next
              style={{
                marginTop: 9,
                border: 'none',
                borderRadius: 9,
                padding: '6px 14px',
                fontSize: 12,
                fontWeight: 600,
                color: '#fff',
                cursor: 'pointer',
                background: `linear-gradient(135deg, ${C.ice}, ${C.iceDeep})`,
                fontFamily: SANS,
              }}
            >
              下一题
            </motion.button>
          )}
        </motion.div>
      )}

      <Burst play={burstAt} color={C.mint} />
      <KaimaoBubble line={line} />
    </div>
  );
};

/* ═══════════════════════════ fill · 代码挖空 ═══════════════════════════ */

interface FillProps {
  code: string;
  marker: string;
  blanks: { id: string; answer: string; line: number }[];
  distractors: string[];
  lang: string;
  file?: string;
  tip?: string;
  seed: number;
}

export const CodeFill: React.FC<FillProps> = ({ code, marker, blanks, distractors, lang, file, tip, seed }) => {
  const [placed, setPlaced] = useState<Record<string, string>>({}); // blankId -> token
  const [wrongAt, setWrongAt] = useState<string | null>(null);
  const [burstAt, setBurstAt] = useState(0);
  const { line, say } = useKaimao(tip || '把缺的标识符拖回空位 —— 位置对、词对才算补回来。');

  const slots = useRef<Record<string, HTMLElement | null>>({});
  const slotIds = blanks.map((b) => b.id);

  const tokens = useMemo(() => {
    const all = [...blanks.map((b) => b.answer), ...distractors];
    return shuffleSeeded(all, seed);
  }, [blanks, distractors, seed]);

  const used = new Set(Object.values(placed));
  const free = tokens.filter((t) => !used.has(t));
  const done = blanks.every((b) => placed[b.id] === b.answer);

  useEffect(() => {
    if (!done || !blanks.length) return;
    setBurstAt((x) => x + 1);
    say('filldone', '全部补回来了，代码能跑通了。', '挖的这几处都是「换个名字就崩」的地方——API 名记准比记概念更救命。', 'ok');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done]);

  const onDrop = (tok: string) => (_: unknown, info: PanInfo) => {
    const k = hitTest(slots, info.point, slotIds);
    if (!k) return;
    const want = blanks.find((b) => b.id === k)?.answer;
    if (want === tok) {
      setPlaced((p) => ({ ...p, [k]: tok }));
      setWrongAt(null);
      // TODO: play fill_ok.mp3
    } else {
      setWrongAt(k);
      window.setTimeout(() => setWrongAt(null), 520);
      say('fillbad', '这个位置不对，读一下上下文。', '看不懂就把这一行的调用链读一遍：谁产出、谁消费，标识符自然就定下来了。', 'warn');
      // TODO: play fill_err.mp3
    }
  };

  const lines = code.split('\n');

  return (
    <div style={{ position: 'relative', paddingBottom: 54 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span
          style={{
            fontFamily: MONO,
            fontSize: 10.5,
            color: C.iceDeep,
            border: `1px solid ${C.iceSoft}`,
            borderRadius: 4,
            padding: '0 5px',
          }}
        >
          {lang}
        </span>
        {file && <span style={{ fontSize: 11, color: C.mute }}>{file}</span>}
        <span style={{ flex: 1 }} />
        <span style={{ fontFamily: MONO, fontSize: 11, color: done ? C.mintDeep : C.mute }} data-fill-progress>
          {Object.keys(placed).length} / {blanks.length}
        </span>
      </div>

      <div
        style={glass({
          padding: '11px 13px',
          background: 'rgba(28,42,56,0.94)',
          border: '1px solid rgba(255,255,255,0.16)',
          overflowX: 'auto',
          overflowY: 'auto',
          // 概念文件里的代码块可能 40 行，不封顶会把空位和托盘一起顶出屏幕
          maxHeight: 380,
        })}
        className="km-scroll"
      >
        <pre style={{ margin: 0, fontFamily: MONO, fontSize: 12, lineHeight: 1.75, color: '#DDEBF6' }}>
          {lines.map((ln, li) => (
            <div key={li} style={{ display: 'flex', gap: 10 }}>
              <span style={{ color: 'rgba(160,200,230,0.35)', flex: '0 0 22px', textAlign: 'right', userSelect: 'none' }}>
                {li + 1}
              </span>
              <span style={{ whiteSpace: 'pre-wrap', flex: 1, minWidth: 0 }}>
                {splitMarker(ln, marker).map((seg, si) => {
                  if (seg.n === undefined) {
                    return <span key={si}>{seg.text}</span>;
                  }
                  const bid = blanks[seg.n - 1]?.id;
                  if (!bid) return <span key={si}>{seg.text}</span>;
                  const val = placed[bid];
                  const bad = wrongAt === bid;
                  const good = !!val;
                  return (
                    <motion.span
                      key={si}
                      ref={(el) => {
                        slots.current[bid] = el as HTMLElement | null;
                      }}
                      data-blank={bid}
                      data-blank-ok={good ? '1' : '0'}
                      animate={bad ? { x: [0, -5, 5, -3, 0] } : { x: 0 }}
                      transition={{ duration: 0.28 }}
                      style={{
                        display: 'inline-block',
                        minWidth: 64,
                        padding: '0 7px',
                        margin: '0 2px',
                        borderRadius: 6,
                        border: `1.5px ${good ? 'solid' : 'dashed'} ${
                          bad ? C.coral : good ? C.mint : 'rgba(140,200,255,0.55)'
                        }`,
                        background: bad
                          ? 'rgba(248,113,113,0.20)'
                          : good
                            ? 'rgba(49,208,170,0.16)'
                            : 'rgba(140,200,255,0.10)',
                        color: good ? '#8EF0D2' : 'rgba(200,228,245,0.6)',
                        fontStyle: good ? 'normal' : 'italic',
                        textAlign: 'center',
                        cursor: good ? 'pointer' : 'default',
                      }}
                      onClick={() => {
                        if (!good) return;
                        setPlaced((p) => {
                          const n = { ...p };
                          delete n[bid];
                          return n;
                        });
                      }}
                    >
                      {good ? val : '????'}
                    </motion.span>
                  );
                })}
              </span>
            </div>
          ))}
        </pre>
      </div>

      {free.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 10 }} data-tokens>
          {free.map((t) => (
            <motion.div
              key={t}
              drag
              dragElastic={DRAG_ELASTIC}
              dragSnapToOrigin
              whileDrag={{ scale: 1.06, zIndex: 30, cursor: 'grabbing' }}
              whileTap={TAP}
              onDragEnd={onDrop(t)}
              data-token={t}
              style={{
                ...glass({ padding: '5px 12px', cursor: 'grab', borderRadius: 9 }),
                fontFamily: MONO,
                fontSize: 12,
                color: C.iceDeep,
              }}
            >
              {t}
            </motion.div>
          ))}
        </div>
      )}

      {done && <div style={{ marginTop: 10, fontSize: 12.5, fontWeight: 600, color: C.mintDeep }}>✓ 全部归位，代码可运行</div>}
      <Burst play={burstAt} color={C.mint} />
      <KaimaoBubble line={line} />
    </div>
  );
};

/* ═══════════════════════════ 外壳 ═══════════════════════════ */

/** lab 版最小样式：CacheDesignLab 的 GlobalStyle 只在自己的树上，这里补一份滚动条 */
const LabStyle: React.FC = () => (
  <style>{`
.kmlab .km-scroll::-webkit-scrollbar{ width:8px; height:8px; }
.kmlab .km-scroll::-webkit-scrollbar-thumb{ background:rgba(93,180,229,.35); border-radius:4px; }
.kmlab .km-scroll::-webkit-scrollbar-track{ background:transparent; }
.kmlab, .kmlab *{ box-sizing:border-box; }
/* 同 CacheDesignLab/GlobalStyle：窄屏场景条换行后隐藏竖分隔线 */
@media (max-width: 560px){ .kmlab .km-sb-div{ display:none } }
`}</style>
);

const KIND_LABEL: Record<string, { name: string; hint: string; tone: string }> = {  sequence: { name: '时序连线', hint: '按真实发生顺序排事件', tone: C.iceDeep },
  match: { name: '配对连线', hint: '症状 ↔ 正解 一对一', tone: C.coralDeep },
  boss: { name: '真题打靶', hint: '答对削一层护甲', tone: C.ice },
  fill: { name: '代码挖空', hint: '把标识符拖回原位', tone: C.mintDeep },
  sandbox: { name: '沙盒推演', hint: '调参数看结果', tone: C.iceDeep },
  debug: { name: '代码拼装', hint: '把缺的块补进骨架', tone: C.mintDeep },
};

const ModuleBody: React.FC<{ mod: LabModule; seed: number; sc?: DualScenario }> = ({ mod, seed, sc }) => {
  // 章节级场景优先复用；模块自己带了就用模块的（手工精修数据可能按模块换叙事）
  const scenario = ('scenario' in mod && mod.scenario) || sc;
  if (mod.kind === 'sequence') {
    return (
      <>
        {scenario && <ScenarioBar work={scenario.work} exam={scenario.exam} />}
        <SequenceLine heading={mod.heading} steps={mod.steps} seed={seed} />
      </>
    );
  }
  if (mod.kind === 'match') {
    return (
      <>
        {scenario && <ScenarioBar work={scenario.work} exam={scenario.exam} />}
        <PairLink pairs={mod.pairs} seed={seed} tip={mod.tip} />
      </>
    );
  }
  if (mod.kind === 'boss') {
    return (
      <>
        {scenario && <ScenarioBar work={scenario.work} exam={scenario.exam} />}
        <LabBossRaid questions={mod.questions} seed={seed} />
      </>
    );
  }
  if (mod.kind === 'fill') {
    return (
      <>
        {scenario && <ScenarioBar work={scenario.work} exam={scenario.exam} />}
        <CodeFill
          code={mod.code}
          marker={mod.marker}
          blanks={mod.blanks}
          distractors={mod.distractors}
          lang={mod.lang}
          file={mod.file}
          tip={mod.tip}
          seed={seed}
        />
      </>
    );
  }
  return (
    <div style={glass({ padding: 16, fontSize: 12.5, color: C.mute })}>
      这个模块（{(mod as { kind: string }).kind}）需要手工精修数据，尚未铺到这里。
    </div>
  );
};

export interface InteractiveLabProps {
  data: LabData;
  /** 只渲染某一个 kind（章节卡里按位置分开挂） */
  only?: LabModule['kind'];
}

/**
 * 章节级入口：标题条 + 模块页签 + 内容。
 * 不用 AnimatePresence mode="wait" —— 模块里有 drag 子节点被卸载时 exit 永不结束，
 * 表现是「页签高亮了，内容不换」。按 key 直接重挂最稳。
 */
export const InteractiveLab: React.FC<InteractiveLabProps> = ({ data, only }) => {
  const mods = useMemo(() => (only ? data.modules.filter((m) => m.kind === only) : data.modules), [data, only]);
  const [idx, setIdx] = useState(0);
  const cur = mods[Math.min(idx, mods.length - 1)];
  const seed = useMemo(() => hashStr(data.chapter + data.fingerprint), [data]);

  if (!mods.length) {
    return (
      <div style={glass({ padding: 16, fontSize: 12.5, color: C.mute })}>
        本章暂无交互模块，跑一次 <code style={{ fontFamily: MONO }}>scripts/gen_interactive.py</code> 试试。
      </div>
    );
  }

  return (
    <div
      className="kmlab"
      style={{
        borderRadius: 18,
        padding: 14,
        background: `radial-gradient(120% 90% at 50% 0%, ${C.white} 0%, ${C.bg} 55%, ${C.bgDeep} 100%)`,
        border: '1px solid rgba(255,255,255,0.9)',
        boxShadow: '0 18px 44px rgba(140,180,215,0.20)',
        fontFamily: SANS,
      }}
    >
      <LabStyle />
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 9, marginBottom: 11, flexWrap: 'wrap' }}>
        <span style={{ fontFamily: MONO, fontSize: 11, color: C.iceDeep, letterSpacing: 0.4 }}>
          {data.chapter.toUpperCase()}
        </span>
        {/* 标题里常有 `header/nav/main/section` 这类不含空格的长 token，
            不给 minWidth:0 + anywhere 会在 420px 下把整页撑出横向滚动条 */}
        <span
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: C.slate,
            minWidth: 0,
            flex: '1 1 auto',
            overflowWrap: 'anywhere',
          }}
          data-lab-title
        >
          {data.title}
        </span>
        <span style={{ fontSize: 11.5, color: C.mute }}>
          {mods.length} 个模块 · 可点可拖，判定在本地
        </span>
      </div>

      {mods.length > 1 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 11 }} data-lab-tabs>
          {mods.map((m, i) => {
            const meta = KIND_LABEL[m.kind] || { name: m.kind, hint: '', tone: C.ice };
            const on = i === idx;
            return (
              <motion.button
                key={`${m.kind}-${i}`}
                type="button"
                whileTap={TAP}
                onClick={() => {
                  setIdx(i);
                  // TODO: play tab_switch.mp3
                }}
                data-lab-tab={m.kind}
                animate={{
                  backgroundColor: on ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0.42)',
                  borderColor: on ? meta.tone : 'rgba(255,255,255,0.7)',
                }}
                transition={SPRING}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  gap: 1,
                  border: '1px solid rgba(255,255,255,0.7)',
                  borderRadius: 11,
                  padding: '6px 11px',
                  cursor: 'pointer',
                  fontFamily: SANS,
                }}
              >
                <span style={{ fontSize: 12.5, fontWeight: 600, color: on ? meta.tone : C.mute }}>
                  {String(i + 1).padStart(2, '0')} {meta.name}
                </span>
                <span style={{ fontSize: 10.5, color: C.mute, opacity: on ? 0.95 : 0.6 }}>{meta.hint}</span>
              </motion.button>
            );
          })}
        </div>
      )}

      <motion.div
        key={`${idx}-${cur.kind}`}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <ModuleBody mod={cur} seed={seed} sc={data.scenario} />
      </motion.div>
    </div>
  );
};

export default InteractiveLab;
