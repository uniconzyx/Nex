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
 *  视觉与物理：令牌来自 ./kit.tsx（单一色源 → lab.css 里的 --kmlab-*）
 *    C / glass() / TAP(0.95) / SPRING(300,20) / DRAG_ELASTIC(0.2)
 *    ScenarioBar（工作现场 / 考场视角）· KaimaoBubble（右下常驻）
 *
 *  这是 App 内的版本，和预览台 `viz/interactive/lab/InteractiveLab.tsx` 同源：
 *  差异只在「色源」—— 预览台要求单文件可拷贝，所以写死十六进制；App 要跟
 *  浅色/深色主题切换，所以全部指向 CSS 变量。改交互逻辑时两边都要改，
 *  改颜色只改 lab.css。
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
} from './kit';
import type { LabData, LabModule, DualScenario, SandboxModule, DebugModule } from '../../data/labs/types';
import { evalExpr, fmtNum } from './expr';
import './lab.css';

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
      <div style={glass({ padding: '10px 12px', marginBottom: 10, background: 'rgba(var(--kmlab-rgb),0.5)' })}>
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
                    ? 'rgba(var(--kmlab-coral-rgb),0.10)'
                    : active
                      ? 'rgba(var(--kmlab-mint-rgb),0.10)'
                      : v !== null
                        ? 'rgba(var(--kmlab-rgb),0.72)'
                        : 'rgba(var(--kmlab-rgb),0.35)',
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
              style={{ stroke: C.mint }}
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
                data-pair-linked={linked ? '1' : '0'}
                animate={
                  on
                    ? { borderColor: C.coral, x: 0, scale: 1.01 }
                    : { borderColor: linked ? C.mint : 'rgba(var(--kmlab-rgb),0.8)', x: 0, scale: 1 }
                }
                transition={SPRING}
                style={{
                  ...glass({ padding: '8px 10px', cursor: linked ? 'default' : 'pointer' }),
                  fontSize: 12,
                  lineHeight: 1.5,
                  color: linked ? C.mute : C.slate,
                  background: linked ? 'rgba(var(--kmlab-mint-rgb),0.10)' : 'rgba(var(--kmlab-rgb),0.62)',
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
                animate={{ borderColor: linked ? C.mint : 'rgba(var(--kmlab-rgb),0.8)' }}
                transition={SPRING}
                style={{
                  ...glass({ padding: '8px 10px', cursor: linked ? 'default' : 'pointer' }),
                  fontSize: 12,
                  lineHeight: 1.5,
                  color: linked ? C.mute : C.slate,
                  background: linked ? 'rgba(var(--kmlab-mint-rgb),0.10)' : 'rgba(var(--kmlab-rgb),0.62)',
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
        <div style={glass({ padding: '5px 11px', background: 'rgba(var(--kmlab-rgb),0.5)' })}>
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
              ? { b: C.mint, bg: 'rgba(var(--kmlab-mint-rgb),0.12)', fg: C.mintDeep }
              : chosen
                ? { b: C.coral, bg: 'rgba(var(--kmlab-coral-rgb),0.12)', fg: C.coralDeep }
                : { b: 'rgba(var(--kmlab-rgb),0.8)', bg: 'rgba(var(--kmlab-rgb),0.55)', fg: C.mute }
            : { b: 'rgba(var(--kmlab-rgb),0.8)', bg: 'rgba(var(--kmlab-rgb),0.62)', fg: C.slate };
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
                          ? 'rgba(var(--kmlab-coral-rgb),0.20)'
                          : good
                            ? 'rgba(var(--kmlab-mint-rgb),0.16)'
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

/* ═══════════════════════════ sandbox · 连续参数推演 ═══════════════════════════ */

interface SandboxProps {
  mod: SandboxModule;
  seed: number;
}

/**
 * 拖旋钮 → 三个指标实时重算 → 所有 checks 变绿才算通关。
 *
 * 关键取舍：指标不是写死的数字，而是 `expr` 表达式（见 ./expr.ts）。
 * 这样一张表能同时服务「32 位 4KB 页」和「48 位 64KB 页」两种参数组合，
 * 学生自己拖出来的反例才是真的反例，而不是作者编的。
 */
/* 沙盒是确定性的：同一组参数永远同一组指标，不需要 seed 洗牌 */
export const ParamSandbox: React.FC<SandboxProps> = ({ mod }) => {
  const [vals, setVals] = useState<Record<string, number>>(() =>
    Object.fromEntries(mod.params.map((p) => [p.key, p.value])),
  );
  const [burstAt, setBurstAt] = useState(0);
  const { line, say } = useKaimao(mod.brief);

  const { metrics, checks, err } = useMemo(() => {
    // 与旋钮展示用的 `vals[p.key] ?? p.value` 保持同一套缺省语义：
    // 某个参数还没被拖动/点选过（不在 vals 里）时，按它的默认值参与指标与判据求值，
    // 而不是让 evalExpr 因「未定义的量」抛错、整组指标变成「—」。
    // 否则 data 异步到货后 vals 只在首次挂载时用空 params 初始化过一次，
    // 用户不逐个点一遍旋钮就永远算不出指标。
    const env: Record<string, number> = {
      ...Object.fromEntries(mod.params.map((p) => [p.key, p.value])),
      ...vals,
    };
    const ms: { key: string; label: string; unit?: string; fmt?: string; v: number }[] = [];
    let e = '';
    for (const m of mod.metrics) {
      try {
        const v = evalExpr(m.expr, env);
        env[m.key] = v;
        ms.push({ key: m.key, label: m.label, unit: m.unit, fmt: m.fmt, v });
      } catch (x) {
        e = (x as Error).message;
        ms.push({ key: m.key, label: m.label, unit: m.unit, fmt: m.fmt, v: NaN });
      }
    }
    const cs = mod.checks.map((c) => {
      try {
        return { label: c.label, ok: evalExpr(c.expr, env) !== 0 };
      } catch (x) {
        e = e || (x as Error).message;
        return { label: c.label, ok: false };
      }
    });
    return { metrics: ms, checks: cs, err: e };
  }, [mod, vals]);

  const okCount = checks.filter((c) => c.ok).length;
  const passed = checks.length > 0 && okCount === checks.length;
  const prevPassed = useRef(false);

  useEffect(() => {
    if (passed && !prevPassed.current) {
      setBurstAt((x) => x + 1);
      say('sb_pass', '这组参数达标了 —— 把边界再往两边拖一次，看看它从哪一格开始崩。',
        '通关只是起点：真正记住的是「哪个参数一动，哪个指标就断崖」——考场问的就是这个断崖点。', 'ok');
      // TODO: play sandbox_pass.mp3
    }
    prevPassed.current = passed;
  }, [passed, say]);

  return (
    <div className="km-body" style={{ position: 'relative' }}>
      <div style={glass({ padding: '10px 12px', marginBottom: 10, background: 'rgba(var(--kmlab-rgb),0.55)' })}>
        <div style={{ fontSize: 12, color: C.mute, lineHeight: 1.65 }}>{mod.brief}</div>
      </div>

      {/* 旋钮 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }} data-sandbox-params>
        {mod.params.map((p) => {
          const v = vals[p.key] ?? p.value;
          const set = (nv: number) => {
            setVals((prev) => ({ ...prev, [p.key]: nv }));
            // TODO: play knob_tick.mp3
          };
          // 离散档位（顺序表/链表、三种布局）用分段按钮：滑块的 0/1/2 是裸数字，
          // 用户得自己记"2 是哪一种"；「double,int,char,char」这种长标签塞进右侧
          // 74px 还会溢出卡片外（实测 420px 下直接糊出边界）。
          if (p.labels && p.labels.length >= 2) {
            return (
              <div key={p.key} data-param-row={p.key} style={{ minWidth: 0 }}>
                <div style={{ fontSize: 12, color: C.slate, marginBottom: 5 }}>{p.label}</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {p.labels.map((lb, i) => {
                    const on = Math.abs(i - v) < 1e-9;
                    return (
                      <motion.button
                        key={lb}
                        type="button"
                        whileTap={TAP}
                        onClick={() => set(i)}
                        data-param-opt={i}
                        data-param-on={on ? '1' : '0'}
                        animate={{
                          backgroundColor: on ? 'rgba(var(--kmlab-rgb),0.95)' : 'rgba(var(--kmlab-rgb),0.42)',
                          borderColor: on ? C.iceDeep : 'rgba(var(--kmlab-rgb),0.7)',
                        }}
                        transition={SPRING}
                        style={{
                          border: '1px solid rgba(var(--kmlab-rgb),0.7)',
                          borderRadius: 9,
                          padding: '5px 10px',
                          fontSize: 11.5,
                          fontFamily: MONO,
                          color: on ? C.iceDeep : C.mute,
                          cursor: 'pointer',
                          maxWidth: '100%',
                          overflowWrap: 'anywhere',
                          textAlign: 'left',
                        }}
                      >
                        {lb}
                      </motion.button>
                    );
                  })}
                </div>
              </div>
            );
          }
          return (
            <div
              key={p.key}
              data-param-row={p.key}
              style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}
            >
              <span style={{ fontSize: 12, color: C.slate, flex: '0 0 96px', minWidth: 0 }}>{p.label}</span>
              <input
                type="range"
                min={p.min}
                max={p.max}
                step={p.step}
                value={v}
                aria-label={p.label}
                data-param={p.key}
                onChange={(ev) => set(Number(ev.target.value))}
                style={{ flex: '1 1 auto', minWidth: 0, accentColor: C.iceDeep, cursor: 'pointer' }}
              />
              <span
                data-param-val={p.key}
                style={{
                  fontFamily: MONO,
                  fontSize: 12,
                  color: C.iceDeep,
                  flex: '0 0 74px',
                  textAlign: 'right',
                  overflowWrap: 'anywhere',
                }}
              >
                {v}
                {p.unit ? ` ${p.unit}` : ''}
              </span>
            </div>
          );
        })}
      </div>

      {/* 指标 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 12 }} data-sandbox-metrics>
        {metrics.map((m) => (
          <div
            key={m.key}
            style={glass({ padding: '7px 11px', flex: '1 1 116px', minWidth: 0, background: 'rgba(var(--kmlab-rgb),0.66)' })}
          >
            <div style={{ fontSize: 10.5, color: C.mute, marginBottom: 2 }}>{m.label}</div>
            <div style={{ fontFamily: MONO, fontSize: 15, fontWeight: 600, color: C.slate, overflowWrap: 'anywhere' }}>
              {fmtNum(m.v, m.fmt as 'int' | 'fix2' | 'pct' | undefined)}
              {m.unit && <span style={{ fontSize: 10.5, color: C.mute, marginLeft: 3 }}>{m.unit}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* 判据 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginTop: 10 }} data-sandbox-checks>
        {checks.map((c, i) => (
          <motion.div
            key={i}
            animate={{ borderColor: c.ok ? C.mint : 'rgba(var(--kmlab-rgb),0.75)' }}
            transition={SPRING}
            style={glass({
              padding: '6px 10px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              border: `1px solid ${c.ok ? C.mint : 'rgba(var(--kmlab-rgb),0.75)'}`,
              background: c.ok ? 'rgba(var(--kmlab-mint-rgb),0.10)' : 'rgba(var(--kmlab-rgb),0.5)',
            })}
          >
            <span style={{ fontSize: 12, color: c.ok ? C.mintDeep : C.mute, flex: '0 0 14px' }}>{c.ok ? '✓' : '○'}</span>
            <span style={{ fontSize: 12, lineHeight: 1.5, color: c.ok ? C.mintDeep : C.slate, minWidth: 0 }}>
              {c.label}
            </span>
          </motion.div>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 11, flexWrap: 'wrap' }}>
        <span style={{ fontFamily: MONO, fontSize: 11.5, color: passed ? C.mintDeep : C.mute }} data-sandbox-score>
          {okCount} / {checks.length} 达标
        </span>
        <motion.button
          type="button"
          whileTap={TAP}
          data-sandbox-reset
          onClick={() => setVals(Object.fromEntries(mod.params.map((p) => [p.key, p.value])))}
          style={{
            border: `1px solid ${C.iceSoft}`,
            background: 'rgba(var(--kmlab-rgb),0.7)',
            borderRadius: 9,
            padding: '5px 12px',
            fontSize: 11.5,
            color: C.iceDeep,
            cursor: 'pointer',
            fontFamily: SANS,
          }}
        >
          复位
        </motion.button>
        {passed && <span style={{ fontSize: 12.5, fontWeight: 600, color: C.mintDeep }}>✓ 通关</span>}
        {err && <span style={{ fontSize: 11, color: C.coralDeep }}>公式错误：{err}</span>}
        <Burst play={burstAt} color={C.mint} />
      </div>

      {passed && (
        <div className="km-tail">
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={SPRING}
            style={{
              ...glass({ marginTop: 9, padding: '10px 12px', borderLeft: `3px solid ${C.mint}` }),
              fontSize: 12.5,
              lineHeight: 1.7,
              color: C.slate,
            }}
            data-sandbox-insight
          >
            {mod.insight}
          </motion.div>
        </div>
      )}

      <KaimaoBubble line={line} />
    </div>
  );
};

/* ═══════════════════════════ debug · 代码块拼装 ═══════════════════════════ */

interface DebugProps {
  mod: DebugModule;
  seed: number;
}

/**
 * 骨架里留 N 个整行空位，把托盘里的代码块拖进去。
 *
 * 和 fill 的区别：fill 挖的是「标识符」（拼写题），debug 补的是「整条语句」
 * （因果关系题）—— 所以每个错块都带自己的 `why`，落错时说的是
 * 「这块是修内存泄漏的，不是修并发」而不是笼统的"不对"。
 */
export const BlockAssemble: React.FC<DebugProps> = ({ mod, seed }) => {
  const [placed, setPlaced] = useState<Record<string, string>>({}); // slotId -> blockId
  const [wrongAt, setWrongAt] = useState<string | null>(null);
  const [burstAt, setBurstAt] = useState(0);
  const { line, say } = useKaimao(mod.symptom);

  const slots = useRef<Record<string, HTMLElement | null>>({});
  const slotIds = mod.slots.map((s) => s.id);
  const blocks = useMemo(() => shuffleSeeded(mod.blocks, seed), [mod.blocks, seed]);

  const okOf = (slot: string) => {
    const bid = placed[slot];
    if (!bid) return false;
    return mod.blocks.find((b) => b.id === bid)?.for === slot;
  };
  const used = new Set(Object.values(placed));
  const free = blocks.filter((b) => !used.has(b.id));
  const allOk = mod.slots.every((s) => okOf(s.id));

  useEffect(() => {
    if (!allOk || !mod.slots.length) return;
    setBurstAt((x) => x + 1);
    say('dbg_pass', mod.pass, '排查顺序永远是「先复现症状 → 再定位那一条语句 → 最后才谈优化」，跳步就会改错地方。', 'ok');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allOk]);

  const onDrop = (blk: { id: string; text: string; for: string; why?: string }) => (_: unknown, info: PanInfo) => {
    const k = hitTest(slots, info.point, slotIds);
    if (!k) {
      say('dbg_miss', '没落在空位上，再拖一次。', '落点按松手时的指针位置算 —— 对准那一整行虚线框再松手。', 'idle');
      return;
    }
    if (blk.for === k) {
      setPlaced((p) => {
        // 槽位已被占：把原来的块换出来（不然两个块抢一个位，托盘会空但缺口还在）
        const next = { ...p };
        for (const s of Object.keys(next)) if (next[s] === blk.id) delete next[s];
        next[k] = blk.id;
        return next;
      });
      setWrongAt(null);
      // TODO: play block_snap.mp3
    } else {
      setWrongAt(k);
      window.setTimeout(() => setWrongAt(null), 560);
      say('dbg_bad', blk.why || '这块放到这里不对。', '看这一行前后在做什么：谁产出、谁消费，缺的那句自然就定下来了。', 'warn');
      // TODO: play block_err.mp3
    }
  };

  const lines = mod.code.split('\n');

  return (
    <div className="km-body" style={{ position: 'relative' }}>
      <div
        style={glass({
          padding: '10px 12px',
          marginBottom: 9,
          borderLeft: `3px solid ${C.coral}`,
          background: 'rgba(var(--kmlab-coral-rgb),0.07)',
        })}
        data-debug-symptom
      >
        <div style={{ fontSize: 10.5, color: C.coralDeep, letterSpacing: 0.4, marginBottom: 2 }}>线上症状</div>
        <div style={{ fontSize: 12.5, lineHeight: 1.65, color: C.slate }}>{mod.symptom}</div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7, flexWrap: 'wrap' }}>
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
          {mod.lang}
        </span>
        {mod.file && <span style={{ fontSize: 11, color: C.mute, minWidth: 0, overflowWrap: 'anywhere' }}>{mod.file}</span>}
        <span style={{ flex: 1 }} />
        <span style={{ fontFamily: MONO, fontSize: 11, color: allOk ? C.mintDeep : C.mute }} data-debug-progress>
          {mod.slots.filter((s) => okOf(s.id)).length} / {mod.slots.length}
        </span>
      </div>

      <div
        style={glass({
          padding: '11px 13px',
          background: 'rgba(28,42,56,0.94)',
          border: '1px solid rgba(255,255,255,0.16)',
          overflowX: 'auto',
          overflowY: 'auto',
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
                {splitMarker(ln, mod.marker).map((seg, si) => {
                  if (seg.n === undefined) return <span key={si}>{seg.text}</span>;
                  const sid = mod.slots[seg.n - 1]?.id;
                  if (!sid) return <span key={si}>{seg.text}</span>;
                  const bid = placed[sid];
                  const blk = bid ? mod.blocks.find((b) => b.id === bid) : undefined;
                  const good = !!blk && blk.for === sid;
                  const bad = wrongAt === sid;
                  return (
                    <motion.span
                      key={si}
                      ref={(el) => {
                        slots.current[sid] = el as HTMLElement | null;
                      }}
                      data-slot={sid}
                      data-slot-ok={good ? '1' : '0'}
                      title={mod.slots[seg.n - 1]?.hint}
                      animate={bad ? { x: [0, -6, 6, -3, 0] } : { x: 0 }}
                      transition={{ duration: 0.3 }}
                      onClick={() => {
                        if (!bid) return;
                        setPlaced((p) => {
                          const n = { ...p };
                          delete n[sid];
                          return n;
                        });
                      }}
                      style={{
                        display: 'inline-block',
                        width: '100%',
                        minWidth: 120,
                        padding: '1px 8px',
                        borderRadius: 6,
                        border: `1.5px ${good ? 'solid' : 'dashed'} ${bad ? C.coral : good ? C.mint : 'rgba(140,200,255,0.55)'}`,
                        background: bad
                          ? 'rgba(var(--kmlab-coral-rgb),0.20)'
                          : good
                            ? 'rgba(var(--kmlab-mint-rgb),0.16)'
                            : 'rgba(140,200,255,0.08)',
                        color: good ? '#8EF0D2' : 'rgba(200,228,245,0.55)',
                        fontStyle: blk ? 'normal' : 'italic',
                        cursor: blk ? 'pointer' : 'default',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {blk ? blk.text : '␣ 拖一块代码到这里 ␣'}
                    </motion.span>
                  );
                })}
              </span>
            </div>
          ))}
        </pre>
      </div>

      {free.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 10 }} data-blocks>
          {free.map((b) => (
            <motion.div
              key={b.id}
              drag
              dragElastic={DRAG_ELASTIC}
              dragSnapToOrigin
              whileDrag={{ scale: 1.04, zIndex: 30, cursor: 'grabbing' }}
              whileTap={TAP}
              onDragEnd={onDrop(b)}
              data-block={b.id}
              style={{
                ...glass({ padding: '5px 11px', cursor: 'grab', borderRadius: 8, maxWidth: 340 }),
                fontFamily: MONO,
                fontSize: 11.5,
                lineHeight: 1.5,
                color: C.iceDeep,
                minWidth: 0,
                overflowWrap: 'anywhere',
              }}
            >
              {b.text}
            </motion.div>
          ))}
        </div>
      )}

      {allOk && (
        <div className="km-tail">
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={SPRING}
            style={glass({ marginTop: 10, padding: '10px 12px', borderLeft: `3px solid ${C.mint}` })}
            data-debug-expect
          >
            <div style={{ fontSize: 10.5, color: C.mintDeep, letterSpacing: 0.3, marginBottom: 4 }}>
              编译通过 · 期望输出
            </div>
            <pre
              style={{
                margin: 0,
                fontFamily: MONO,
                fontSize: 11.5,
                lineHeight: 1.7,
                color: C.slate,
                whiteSpace: 'pre-wrap',
                overflowWrap: 'anywhere',
              }}
            >
              {mod.expect}
            </pre>
          </motion.div>
        </div>
      )}

      <Burst play={burstAt} color={C.mint} />
      <KaimaoBubble line={line} />
    </div>
  );
};

/* ═══════════════════════════ 外壳 ═══════════════════════════ */

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
  if (mod.kind === 'sandbox') {
    return (
      <>
        {scenario && <ScenarioBar work={scenario.work} exam={scenario.exam} />}
        <ParamSandbox mod={mod} seed={seed} />
      </>
    );
  }
  if (mod.kind === 'debug') {
    return (
      <>
        {scenario && <ScenarioBar work={scenario.work} exam={scenario.exam} />}
        <BlockAssemble mod={mod} seed={seed} />
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
        background: 'var(--kmlab-panel)',
        border: '1px solid rgba(var(--kmlab-rgb),0.9)',
        boxShadow: '0 18px 44px rgba(var(--kmlab-shadow-rgb),0.20)',
        fontFamily: SANS,
      }}
    >
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
                  backgroundColor: on ? 'rgba(var(--kmlab-rgb),0.92)' : 'rgba(var(--kmlab-rgb),0.42)',
                  borderColor: on ? meta.tone : 'rgba(var(--kmlab-rgb),0.7)',
                }}
                transition={SPRING}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  gap: 1,
                  border: '1px solid rgba(var(--kmlab-rgb),0.7)',
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
