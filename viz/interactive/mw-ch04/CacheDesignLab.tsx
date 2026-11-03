/**
 * ═══════════════════════════════════════════════════════════════════════════
 *  凯喵 Code 试炼录 · mw-ch04《缓存设计与三大经典问题》
 *  交互组件集（单文件 · 可直接运行）
 * ───────────────────────────────────────────────────────────────────────────
 *  依赖：react >= 18、framer-motion >= 10
 *  视觉：液态玻璃 · 冰蓝奶白（底 #EBF4FA，卡 bg-white/60 + blur(12px)）
 *
 *  三个模块
 *    01  AvalancheSandbox   沙盒推演  TTL 抖动 vs 缓存雪崩
 *    02  SingleflightDebug  代码 Debug  singleflight 补全
 *    03  CacheBossRaid      闯关试炼  三道真题 BOSS 战
 *
 *  数据锚点（全部可回溯，不自创数值）
 *    01 → content/middleware/mw-ch04/examples/ex08-ttl-jitter-benchmark.json
 *    02 → examples/ex04 / ex05（已勘误的屏障式并发模型：200 → 1，−99.5%）
 *    03 → exercises.json（只读取题干，**文件不修改**；选项运行时确定性洗牌）
 *
 *  为什么玻璃质感写内联 style 而不是 Tailwind 类
 *    为了让这个文件在没有装 Tailwind 的工程里也能跑起来。等价的 Tailwind 写法：
 *      background:            bg-white/60
 *      backdrop-filter:       backdrop-blur-md
 *      border:                border border-white/80
 *      box-shadow:            shadow-[0_8px_24px_rgba(160,190,220,0.15)]
 *      radius:                rounded-[14px]
 *    迁到 Tailwind 工程时，把 glass() 的返回值替换成上面这串类名即可，结构不用动。
 * ═══════════════════════════════════════════════════════════════════════════
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { PanInfo } from 'framer-motion';

/* ────────────────────────────── 设计令牌 ────────────────────────────── */

export const C = {
  bg: '#EBF4FA',
  bgDeep: '#DCEBF7',
  ice: '#5DB4E5',
  iceDeep: '#2E7FB0',
  iceSoft: '#BFDDF1',
  slate: '#2B3E50',
  mute: '#7A93A8',
  line: '#CFE2EF',
  mint: '#31D0AA',
  mintDeep: '#0F8A6C',
  coral: '#F87171',
  coralDeep: '#C2413C',
  amber: '#E8A33D',
  white: '#FFFFFF',
} as const;

export const MONO =
  "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace";
export const SANS =
  "'Microsoft YaHei', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Noto Sans SC', system-ui, sans-serif";

/** 液态玻璃材质 */
export const glass = (extra?: React.CSSProperties): React.CSSProperties => ({
  background: 'rgba(255,255,255,0.60)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
  border: '1px solid rgba(255,255,255,0.80)',
  boxShadow: '0 8px 24px rgba(160,190,220,0.15)',
  borderRadius: 14,
  ...extra,
});

/** 弹簧回弹：所有可点元素共用 */
export const TAP = { scale: 0.95 } as const;
export const SPRING = { type: 'spring', stiffness: 300, damping: 20 } as const;
/** 拖拽边缘拉伸弹性（规范要求 0.2） */
export const DRAG_ELASTIC = 0.2;

/* ─────────────────────────── 全局注入的最小样式 ─────────────────────────── */

const GlobalStyle: React.FC = () => (
  <style>{`
.kmlab, .kmlab *{ box-sizing: border-box; }
.kmlab{ font-family: ${SANS}; -webkit-font-smoothing: antialiased; }
.kmlab input[type=range]{
  -webkit-appearance:none; appearance:none; width:100%; height:6px;
  border-radius:3px; background:${C.bgDeep}; outline:none; cursor:pointer;
}
.kmlab input[type=range]::-webkit-slider-thumb{
  -webkit-appearance:none; width:22px; height:22px; border-radius:50%;
  background:#fff; border:2px solid ${C.ice};
  box-shadow:0 2px 8px rgba(93,180,229,.4); cursor:grab; transition:transform .12s;
}
.kmlab input[type=range]::-webkit-slider-thumb:active{ cursor:grabbing; transform:scale(1.1); }
.kmlab input[type=range]::-moz-range-thumb{
  width:20px; height:20px; border-radius:50%; background:#fff;
  border:2px solid ${C.ice}; box-shadow:0 2px 8px rgba(93,180,229,.4); cursor:grab;
}
.kmlab .km-scroll::-webkit-scrollbar{ width:6px; height:6px; }
.kmlab .km-scroll::-webkit-scrollbar-thumb{ background:rgba(93,180,229,.35); border-radius:3px; }
.kmlab .km-scroll::-webkit-scrollbar-track{ background:transparent; }
@keyframes km-pulse{ 0%,100%{ opacity:.45 } 50%{ opacity:1 } }
`}</style>
);

/* ───────────────────────────────── 凯喵 ───────────────────────────────── */

export type KaimaoTone = 'idle' | 'ok' | 'warn' | 'teach';

export interface KaimaoLine {
  text: string;
  tone: KaimaoTone;
}

/**
 * 分层台词：同一个槽位第 1~2 次触发说人设台词，第 3 次起自动升级为知识点讲解。
 * 主人选的正是「先人设后教学」，所以卡壳三次就会被知识点点醒。
 */
export function useKaimao(initial: string) {
  const [line, setLine] = useState<KaimaoLine>({ text: initial, tone: 'idle' });
  const hits = useRef<Record<string, number>>({});

  const say = useCallback(
    (slot: string, persona: string, teach: string, tone: KaimaoTone = 'idle') => {
      const n = (hits.current[slot] = (hits.current[slot] ?? 0) + 1);
      if (n >= 3) setLine({ text: teach, tone: 'teach' });
      else setLine({ text: persona, tone });
    },
    [],
  );

  return { line, say };
}

const KaimaoFace: React.FC<{ mood: KaimaoTone }> = ({ mood }) => {
  const eye =
    mood === 'ok' ? C.mint : mood === 'warn' ? C.coral : mood === 'teach' ? C.iceDeep : C.slate;
  const brow = mood === 'warn' || mood === 'teach';
  return (
    <svg width="38" height="38" viewBox="0 0 34 34" aria-hidden="true">
      {/* 六边形底：全站母题 */}
      <path
        d="M17 1 L31 8.6 L31 24.4 L17 32 L3 24.4 L3 8.6 Z"
        fill="#F2FAFF"
        stroke={C.ice}
        strokeWidth="1.4"
      />
      {/* 猫耳 */}
      <path d="M8.4 9 L10.8 2.8 L14.6 7.4 Z" fill={C.ice} opacity="0.5" />
      <path d="M25.6 9 L23.2 2.8 L19.4 7.4 Z" fill={C.ice} opacity="0.5" />
      {/* 眼 */}
      {brow ? (
        <>
          <path d="M10.6 15.4 L14.6 14.2" stroke={eye} strokeWidth="1.4" strokeLinecap="round" />
          <path d="M23.4 15.4 L19.4 14.2" stroke={eye} strokeWidth="1.4" strokeLinecap="round" />
        </>
      ) : null}
      <circle cx="12.6" cy="17.6" r="1.9" fill={eye} />
      <circle cx="21.4" cy="17.6" r="1.9" fill={eye} />
      {/* 嘴 */}
      <path
        d="M15.2 22 Q17 23.8 18.8 22"
        stroke={C.slate}
        strokeWidth="1.2"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
};

/** 右下角常驻气泡 */
export const KaimaoBubble: React.FC<{ line: KaimaoLine }> = ({ line }) => {
  const accent =
    line.tone === 'ok'
      ? C.mint
      : line.tone === 'warn'
        ? C.coral
        : line.tone === 'teach'
          ? C.iceDeep
          : C.ice;
  return (
    <div
      style={{
        position: 'absolute',
        right: 14,
        bottom: 10,
        display: 'flex',
        alignItems: 'flex-end',
        gap: 8,
        maxWidth: 330,
        pointerEvents: 'none',
        zIndex: 40,
      }}
    >
      {/* key 变化即重挂重播进场，不用 AnimatePresence：mode="wait" 一旦卡住就会出现空气泡 */}
      <motion.div
        key={line.text}
        initial={{ opacity: 0, y: 10, scale: 0.94 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={SPRING}
        style={glass({
          borderRadius: 14,
          padding: '9px 12px',
          borderLeft: `3px solid ${accent}`,
        })}
      >
        <p style={{ margin: 0, fontSize: 13, lineHeight: 1.55, color: C.slate }}>{line.text}</p>
      </motion.div>
      <motion.div
        animate={{ y: [0, -3, 0] }}
        transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }}
        style={{ flex: '0 0 auto' }}
      >
        <KaimaoFace mood={line.tone} />
      </motion.div>
    </div>
  );
};

/* ─────────────────────── 双场景包装：工作现场 / 考场视角 ─────────────────────── */

export interface Scenario {
  /** 场景标签，如「线上告警」「408 考点」 */
  tag: string;
  /** 一句话情境 */
  head: string;
  /** 具体数字或追问，让场景落地 */
  body: string;
}

/**
 * 同一个知识点有两种进入方式：
 *   工作现场 —— 从告警/工单进入，关心「先止血还是先查根因」；
 *   考场视角 —— 从题干进入，关心「判别标准与选项陷阱」。
 * 两个视角共享同一套交互，只是换了叙事外壳，所以学习者在任意一侧练完都能迁移。
 */
export const ScenarioBar: React.FC<{ work: Scenario; exam: Scenario }> = ({ work, exam }) => {
  const [mode, setMode] = useState<'work' | 'exam'>('work');
  const cur = mode === 'work' ? work : exam;
  const accent = mode === 'work' ? C.coral : C.iceDeep;

  return (
    <div
      style={glass({
        padding: '9px 12px',
        marginBottom: 11,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        background: 'rgba(255,255,255,0.52)',
      })}
    >
      <div style={{ display: 'flex', gap: 5, flex: '0 0 auto' }}>
        {(['work', 'exam'] as const).map((k) => {
          const on = mode === k;
          return (
            <motion.button
              key={k}
              type="button"
              whileTap={TAP}
              onClick={() => {
                setMode(k);
                // TODO: play tab_switch.mp3
              }}
              animate={{
                backgroundColor: on
                  ? k === 'work'
                    ? 'rgba(248,113,113,0.16)'
                    : 'rgba(93,180,229,0.18)'
                  : 'rgba(255,255,255,0.5)',
                color: on ? (k === 'work' ? C.coralDeep : C.iceDeep) : C.mute,
              }}
              transition={SPRING}
              style={{
                border: `1px solid ${on ? accent : C.line}`,
                borderRadius: 999,
                padding: '3px 10px',
                fontFamily: SANS,
                fontSize: 11.5,
                fontWeight: 500,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {k === 'work' ? '工作现场' : '考场视角'}
            </motion.button>
          );
        })}
      </div>

      <div style={{ width: 1, height: 26, background: C.line, flex: '0 0 auto' }} />

      <motion.div
        key={mode}
        initial={{ opacity: 0, x: 6 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.16 }}
        style={{ minWidth: 0 }}
      >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span
              style={{
                fontFamily: MONO,
                fontSize: 10.5,
                letterSpacing: 0.3,
                color: accent,
                border: `1px solid ${accent}`,
                borderRadius: 4,
                padding: '0 5px',
                opacity: 0.9,
              }}
            >
              {cur.tag}
            </span>
            <span style={{ fontSize: 13, fontWeight: 500, color: C.slate }}>{cur.head}</span>
          </div>
        <div style={{ fontSize: 12, color: C.mute, marginTop: 2, lineHeight: 1.5 }}>{cur.body}</div>
      </motion.div>
    </div>
  );
};

/* ─────────────────────────── 粒子爆闪（成功反馈） ─────────────────────────── */

/**
 * 成功时的冰蓝碎片飞溅。play 每次递增就重放一次；父容器需 position:relative。
 * 纯 CSS transform 动画，不触发 layout。
 */
export const Burst: React.FC<{ play: number; n?: number; color?: string; size?: number }> = ({
  play,
  n = 16,
  color = C.ice,
  size = 6,
}) => {
  if (!play) return null;
  return (
    <div
      key={play}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
        zIndex: 35,
      }}
    >
      {Array.from({ length: n }).map((_, i) => {
        const a = (i / n) * Math.PI * 2 + (i % 3) * 0.12;
        const r = 46 + (i % 4) * 22;
        return (
          <motion.span
            key={i}
            initial={{ opacity: 1, x: 0, y: 0, scale: 1 }}
            animate={{
              opacity: 0,
              x: Math.cos(a) * r,
              y: Math.sin(a) * r,
              scale: 0.2,
              rotate: (i % 2 ? 1 : -1) * 120,
            }}
            transition={{ duration: 0.72, ease: 'easeOut' }}
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              width: i % 3 === 0 ? size + 3 : size,
              height: i % 3 === 0 ? size + 3 : size,
              borderRadius: i % 2 ? '50%' : 2,
              background: i % 4 === 0 ? C.mint : color,
              boxShadow: `0 0 8px ${i % 4 === 0 ? C.mint : color}`,
            }}
          />
        );
      })}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════════════
 *  模块 01 · 沙盒推演：TTL 抖动 vs 缓存雪崩
 * ═══════════════════════════════════════════════════════════════════════════ */

const TOTAL_KEYS = 2000;
const BASE_TTL = 600; // 秒
const BIN_COUNT = 31;

/** ex08 实测六档：抖动幅度 → 单一 10s 窗口内最大失效 key 数 */
const JITTER_STEPS = [
  { jitter: 0, peak: 2000 },
  { jitter: 60, peak: 342 },
  { jitter: 120, peak: 191 },
  { jitter: 300, peak: 80 },
  { jitter: 600, peak: 46 },
  { jitter: 1200, peak: 27 },
] as const;

const PEAK_INDEX = Math.floor(BIN_COUNT / 2);

/**
 * 示意分布：峰值严格取 ex08 实测值，剩余 key 摊到其余档位（向两端轻微衰减）。
 * 不伪造随机数——真实分布是随机的，这里只表达「峰值 + 摊平」两件事。
 */
function buildBins(peak: number): number[] {
  const bins = new Array<number>(BIN_COUNT).fill(0);
  if (peak >= TOTAL_KEYS) {
    bins[PEAK_INDEX] = TOTAL_KEYS;
    return bins;
  }
  const rest = TOTAL_KEYS - peak;
  const w: number[] = [];
  for (let i = 0; i < BIN_COUNT; i++) {
    if (i === PEAK_INDEX) continue;
    w.push(1 - Math.abs(i - PEAK_INDEX) / (BIN_COUNT * 1.7));
  }
  const wSum = w.reduce((a, b) => a + b, 0);
  let acc = 0;
  let k = 0;
  for (let i = 0; i < BIN_COUNT; i++) {
    if (i === PEAK_INDEX) continue;
    const v = Math.round((rest * w[k]) / wSum);
    bins[i] = v;
    acc += v;
    k++;
  }
  bins[PEAK_INDEX] = peak;
  // 把四舍五入的误差补到最后一档，保证总和恒为 2000
  if (acc !== rest) {
    for (let i = BIN_COUNT - 1; i >= 0; i--) {
      if (i !== PEAK_INDEX) {
        bins[i] += rest - acc;
        break;
      }
    }
  }
  return bins;
}

const CHART_H = 132;

export const AvalancheSandbox: React.FC = () => {
  const [step, setStep] = useState(0);
  const [sfOn, setSfOn] = useState(false);
  const [sfShake, setSfShake] = useState(0);
  const { line, say } = useKaimao('拖这个滑块，看 2000 个 key 的失效时刻都挤在哪一格喵');

  const cur = JITTER_STEPS[step];
  const bins = useMemo(() => buildBins(cur.peak), [cur.peak]);
  const ideal = cur.jitter > 0 ? TOTAL_KEYS / (cur.jitter / 10) : null;
  const peakPct = (cur.peak / TOTAL_KEYS) * 100;
  const drop = (1 - cur.peak / TOTAL_KEYS) * 100;
  const freshness = cur.jitter / BASE_TTL; // 0 ~ 2.0

  const px = (v: number) => Math.max(2, (v / TOTAL_KEYS) * (CHART_H - 6));

  const onSlide = (v: number) => {
    // TODO: play slide_tick.mp3
    setStep(v);
    const next = JITTER_STEPS[v];
    if (v === 0) {
      say(
        'slide-0',
        '整整齐齐，全挤在 600 秒那一格——这就是雪崩喵',
        '统一 TTL：1000~2000 个 key 在同一秒过期，瞬时全部回源，DB 直接被打穿',
        'warn',
      );
    } else if (next.jitter >= 600) {
      say(
        `slide-${v}`,
        `摊平了！峰值掉到 ${next.peak}，降了 ${((1 - next.peak / TOTAL_KEYS) * 100).toFixed(1)}%`,
        `抖动 ${next.jitter}s 时峰值 ${next.peak} 个，但 TTL 极差已达 ${(next.jitter * 2) / 60} 分钟，冷数据会被读成旧值`,
        'ok',
      );
    } else {
      say(
        `slide-${v}`,
        `峰值 ${next.peak} 个，散开了点喵`,
        `抖动 ${next.jitter}s：失效窗口被拉宽到 ${(next.jitter * 2) / 10} 个 10s 档，峰值从 2000 降到 ${next.peak}`,
        'ok',
      );
    }
  };

  const toggleSf = () => {
    // TODO: play toggle_click.mp3
    const next = !sfOn;
    setSfOn(next);
    setSfShake((n) => n + 1);
    say(
      'sf',
      next ? '开了保护……咦，柱子一根没动喵？' : '关掉了，反正它本来也没帮上忙',
      'singleflight 只能合并「同一个 key」的并发回源；雪崩是「大量不同 key 同时过期」，它管不着——治雪崩要靠 TTL 抖动或多级缓存',
      'warn',
    );
  };

  return (
    <div style={{ position: 'relative', paddingBottom: 62 }}>
      <ScenarioBar
        work={{
          tag: '线上告警',
          head: '14:02 商品详情页 P99 从 80ms 冲到 12s',
          body: '2000 个热 key 在同一秒过期，DB QPS 从 200 飙到 2000。值班的第一步是先止血还是先查根因？',
        }}
        exam={{
          tag: '408 考点',
          head: '统一 TTL 的 2000 个 key，为什么会同时失效',
          body: '考点在「雪崩 / 击穿 / 穿透」的判别：本题是雪崩。抖动把峰值换成极差，不能消除总量。',
        }}
      />
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 232px', gap: 14 }}>
        {/* 直方图 */}
        <div style={glass({ padding: '16px 18px 18px' })}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              marginBottom: 12,
            }}
          >
            <div>
              <div style={{ fontSize: 14, fontWeight: 500, color: C.slate }}>key 失效时刻分布</div>
              <div style={{ fontSize: 12, color: C.mute, marginTop: 2 }}>
                2000 个 key · 基础 TTL 600s · 每档 10s
              </div>
            </div>
            <div style={{ fontFamily: MONO, fontSize: 12, color: C.mute }}>
              峰值档 <b style={{ color: peakPct > 20 ? C.coralDeep : C.mintDeep }}>{cur.peak}</b>
            </div>
          </div>

          <motion.div
            key={sfShake}
            animate={{ x: [0, -3, 3, 0] }}
            transition={{ duration: 0.26 }}
            style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'flex-end',
              gap: 2,
              height: CHART_H,
              borderBottom: `1px solid ${C.line}`,
            }}
          >
            {bins.map((v, i) => (
              <motion.div
                key={i}
                animate={{ height: px(v) }}
                transition={{ type: 'spring', stiffness: 260, damping: 26 }}
                style={{
                  flex: 1,
                  borderRadius: 1.5,
                  background:
                    i === PEAK_INDEX
                      ? v >= 1000
                        ? C.coral
                        : v >= 100
                          ? C.amber
                          : C.mint
                      : C.iceSoft,
                }}
              />
            ))}

            {/* 理想摊平值虚线（ex08 口径：2000 / (jitter/10)） */}
            {ideal !== null && (
              <motion.div
                animate={{ bottom: (ideal / TOTAL_KEYS) * (CHART_H - 6) }}
                transition={{ type: 'spring', stiffness: 260, damping: 26 }}
                style={{
                  position: 'absolute',
                  left: 0,
                  right: 0,
                  borderTop: `1px dashed ${C.mint}`,
                  pointerEvents: 'none',
                }}
              >
                <span
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: -15,
                    fontFamily: MONO,
                    fontSize: 11,
                    color: C.mintDeep,
                    background: 'rgba(255,255,255,0.9)',
                    padding: '0 3px',
                    borderRadius: 3,
                  }}
                >
                  理想 {ideal.toFixed(1)}
                </span>
              </motion.div>
            )}
          </motion.div>

          {/* 滑块 */}
          <div style={{ marginTop: 18 }}>
            <input
              type="range"
              min={0}
              max={JITTER_STEPS.length - 1}
              step={1}
              value={step}
              onChange={(e) => onSlide(Number(e.target.value))}
              aria-label="TTL 抖动幅度"
            />
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginTop: 7,
                fontFamily: MONO,
                fontSize: 11,
                color: C.mute,
              }}
            >
              {JITTER_STEPS.map((s, i) => (
                <span
                  key={s.jitter}
                  style={{
                    color: i === step ? C.iceDeep : C.mute,
                    fontWeight: i === step ? 500 : 400,
                  }}
                >
                  {s.jitter === 0 ? '统一' : `±${s.jitter}s`}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* 右侧：指标 + 三个开关 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={glass({ padding: '13px 14px' })}>
            <Metric label="单一窗口峰值" value={`${cur.peak}`} unit="个" tone={peakPct > 20 ? C.coralDeep : C.mintDeep} />
            <div style={{ height: 10 }} />
            <Metric
              label="较统一 TTL"
              value={step === 0 ? '—' : `−${drop.toFixed(1)}`}
              unit={step === 0 ? '' : '%'}
              tone={C.iceDeep}
            />
            <div style={{ height: 10 }} />
            <Metric
              label="TTL 最大偏差"
              value={`±${(cur.jitter * 2) / 60}`}
              unit="分钟"
              tone={freshness > 0.5 ? C.amber : C.slate}
            />
          </div>

          <div style={glass({ padding: '12px 14px' })}>
            <div style={{ fontSize: 12, color: C.mute, marginBottom: 9 }}>防护手段</div>
            <Switch
              label="统一 TTL"
              desc="问题源头"
              on={step === 0}
              disabled
              tone={C.coral}
            />
            <div style={{ height: 7 }} />
            <Switch label="TTL 抖动" desc="摊平失效窗口" on={step > 0} disabled tone={C.mint} />
            <div style={{ height: 7 }} />
            <motion.div whileTap={sfOn || true ? TAP : undefined}>
              <Switch
                label="singleflight"
                desc="治击穿，不治雪崩"
                on={sfOn}
                onClick={toggleSf}
                tone={sfOn ? C.mint : C.ice}
              />
            </motion.div>
          </div>
        </div>
      </div>

      <KaimaoBubble line={line} />
    </div>
  );
};

const Metric: React.FC<{ label: string; value: string; unit: string; tone: string }> = ({
  label,
  value,
  unit,
  tone,
}) => (
  <div>
    <div style={{ fontSize: 11, color: C.mute }}>{label}</div>
    <div style={{ fontFamily: MONO, fontSize: 20, fontWeight: 500, color: tone, lineHeight: 1.25 }}>
      {value}
      <span style={{ fontSize: 11, marginLeft: 3, color: C.mute, fontWeight: 400 }}>{unit}</span>
    </div>
  </div>
);

const Switch: React.FC<{
  label: string;
  desc: string;
  on: boolean;
  disabled?: boolean;
  tone: string;
  onClick?: () => void;
}> = ({ label, desc, on, disabled, tone, onClick }) => (
  <div
    data-switch={label}
    role="switch"
    aria-checked={on}
    onClick={disabled ? undefined : onClick}
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: 9,
      cursor: disabled ? 'default' : 'pointer',
      opacity: disabled ? 0.72 : 1,
      userSelect: 'none',
    }}
  >
    <div
      style={{
        width: 30,
        height: 17,
        borderRadius: 9,
        background: on ? tone : 'rgba(122,147,168,0.22)',
        padding: 2,
        display: 'flex',
        justifyContent: on ? 'flex-end' : 'flex-start',
        transition: 'background .18s',
        flex: '0 0 auto',
      }}
    >
      <motion.div
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 32 }}
        style={{ width: 13, height: 13, borderRadius: '50%', background: '#fff' }}
      />
    </div>
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 12.5, color: C.slate, lineHeight: 1.3 }}>{label}</div>
      <div style={{ fontSize: 11, color: C.mute, lineHeight: 1.3 }}>{desc}</div>
    </div>
  </div>
);

/* ═══════════════════════════════════════════════════════════════════════════
 *  模块 02 · 代码 Debug：singleflight 补全
 * ═══════════════════════════════════════════════════════════════════════════ */

type SlotId = 'A' | 'B' | 'C';
type Phase = 'idle' | 'running' | 'pass' | 'warn' | 'fail';

interface CodeBlock {
  id: string;
  label: string;
  owner: SlotId;
  bad?: boolean;
}

const BLOCKS: CodeBlock[] = [
  { id: 'read', label: 'if v, ok := cache.Get(key); ok { return v }', owner: 'A' },
  { id: 'sf', label: 'v, err := sf.Do(key, func() (any, error) { … })', owner: 'B' },
  { id: 'set5m', label: 'cache.Set(key, v, 5*time.Minute)', owner: 'C' },
  { id: 'set0', label: 'cache.Set(key, v, 0)', owner: 'C', bad: true },
  { id: 'db', label: 'v, err := db.QueryUser(ctx, id)', owner: 'B', bad: true },
];

const SLOT_HINT: Record<SlotId, string> = {
  A: '先读缓存',
  B: '未命中→回源',
  C: '回填缓存',
};

interface Verdict {
  kind: 'pass' | 'warn' | 'fail';
  hits: number;
  title: string;
  why: string;
}

/** 四分支判定矩阵：四种失败给不同的错因，避免「错了但不知道为什么错」 */
function evaluate(placed: Record<SlotId, string | null>): Verdict {
  const { A, B, C: slotC } = placed;
  if (B !== 'sf') {
    return {
      kind: 'fail',
      hits: 200,
      title: '击穿未被挡住',
      why:
        B === 'db'
          ? '这里直接用 db.QueryUser 回源，等于没有单飞：200 个并发各自查库'
          : '缺少 singleflight：200 个并发同时发现 miss，各自回源 200 次',
    };
  }
  if (slotC === 'set0') {
    return {
      kind: 'fail',
      hits: 200,
      title: 'TTL=0 写入即过期',
      why: 'cache.Set(key, v, 0) 在多数客户端里等同于不缓存，下一个请求立刻又 miss',
    };
  }
  if (slotC !== 'set5m') {
    return {
      kind: 'fail',
      hits: 200,
      title: '缓存永不回填',
      why: '没有写回缓存，第一次单飞之后仍然每次都要走一遍回源路径',
    };
  }
  if (A !== 'read') {
    return {
      kind: 'warn',
      hits: 1,
      title: '能跑，但命中率为 0',
      why: '缺缓存读取：回源确实只有 1 次，但每个请求都要进 singleflight，白白多一跳',
    };
  }
  return {
    kind: 'pass',
    hits: 1,
    title: '击穿已挡住',
    why: '读缓存 → 未命中走单飞合并 → 回填 5 分钟。200 并发只打了 1 次库（−99.5%）',
  };
}

type ZoneRefs = React.MutableRefObject<Record<SlotId, HTMLElement | null>>;
interface RenderArgs {
  placed: Record<SlotId, string | null>;
  zr: ZoneRefs;
  rm: (slot: SlotId) => void;
}

const CODE_LINES: { n: number; render: (a: RenderArgs) => React.ReactNode }[] = [
  {
    n: 1,
    render: () => (
      <>
        <Kw>func</Kw> GetUser(ctx context.Context, id <Kw>int64</Kw>) (*User, <Kw>error</Kw>) {'{'}
      </>
    ),
  },
  { n: 2, render: () => <>&nbsp;&nbsp;key := fmt.Sprintf(<Str>"user:%d"</Str>, id)</> },
  { n: 3, render: () => <>&nbsp;&nbsp;<Cm>// 命中直接返回，不碰 DB</Cm></> },
  {
    n: 4,
    render: (a) => (
      <>&nbsp;&nbsp;
        <SlotBody slot="A" zr={a.zr} id={a.placed.A} onRemove={() => a.rm('A')} />
      </>
    ),
  },
  { n: 5, render: () => <>&nbsp;</> },
  { n: 6, render: () => <>&nbsp;&nbsp;<Cm>// 未命中：合并同一 key 的并发回源</Cm></> },
  {
    n: 7,
    render: (a) => (
      <>&nbsp;&nbsp;
        <SlotBody slot="B" zr={a.zr} id={a.placed.B} onRemove={() => a.rm('B')} />
      </>
    ),
  },
  {
    n: 8,
    render: () => (
      <>&nbsp;&nbsp;<Kw>if</Kw> err != <Kw>nil</Kw> {'{'} <Kw>return nil</Kw>, err {'}'}</>
    ),
  },
  {
    n: 9,
    render: (a) => (
      <>&nbsp;&nbsp;
        <SlotBody slot="C" zr={a.zr} id={a.placed.C} onRemove={() => a.rm('C')} />
      </>
    ),
  },
  { n: 10, render: () => <>&nbsp;&nbsp;<Kw>return</Kw> v.(*User), <Kw>nil</Kw></> },
  { n: 11, render: () => <>{'}'}</> },
];

const Kw: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ color: '#A855F7' }}>{children}</span>
);
const Str: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ color: C.mintDeep }}>{children}</span>
);
const Cm: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ color: C.mute }}>{children}</span>
);

const BlockInline: React.FC<{ id: string; onRemove?: () => void }> = ({ id, onRemove }) => {
  const b = BLOCKS.find((x) => x.id === id);
  if (!b) return null;
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.92, boxShadow: '0 0 0 0 rgba(93,180,229,0)' }}
      animate={{
        opacity: 1,
        scale: 1,
        boxShadow: [
          '0 0 0 0 rgba(93,180,229,0)',
          b.bad ? '0 0 0 5px rgba(248,113,113,0.26)' : '0 0 0 5px rgba(93,180,229,0.30)',
          '0 0 0 0 rgba(93,180,229,0)',
        ],
      }}
      whileHover={{ y: -1 }}
      whileTap={{ scale: 0.94 }}
      onClick={onRemove}
      data-placed={id}
      title="点一下退回托盘"
      transition={SPRING}
      style={{
        display: 'inline-block',
        background: b.bad ? 'rgba(248,113,113,0.14)' : 'rgba(93,180,229,0.16)',
        border: `1px solid ${b.bad ? 'rgba(248,113,113,0.45)' : 'rgba(93,180,229,0.42)'}`,
        borderRadius: 5,
        padding: '0 5px',
        color: b.bad ? C.coralDeep : C.slate,
        cursor: onRemove ? 'pointer' : 'default',
      }}
    >
      {b.label}
    </motion.span>
  );
};

/** 空槽位的呼吸提示（纯视觉，不承担落点，避免和 SlotBody 抢 ref） */
const DropHint: React.FC<{ slot: SlotId }> = ({ slot }) => (
  <motion.span
    animate={{ opacity: [0.55, 0.95, 0.55] }}
    transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
    style={{
      display: 'inline-block',
      border: `1px dashed ${C.ice}`,
      borderRadius: 5,
      padding: '0 10px',
      color: C.iceDeep,
      fontSize: 11.5,
      background: 'rgba(93,180,229,0.06)',
      pointerEvents: 'none',
    }}
  >
    {SLOT_HINT[slot]}
  </motion.span>
);

/**
 * 槽位容器：**空或已填都保持同一个落点**。
 * 旧写法把落点只挂在空槽的虚线框上，槽位一填满落点就消失，
 * 于是「拖一个新块把旧块顶掉」根本做不到，只能先点回旧块——真实用户不会这么猜。
 */
const SlotBody: React.FC<{
  slot: SlotId;
  zr: ZoneRefs;
  id: string | null;
  onRemove: () => void;
}> = ({ slot, zr, id, onRemove }) => (
  <span
    data-slot={slot}
    ref={(el) => {
      zr.current[slot] = el;
    }}
    style={{ display: 'inline-block', borderRadius: 5, verticalAlign: 'baseline' }}
  >
    {id ? <BlockInline id={id} onRemove={onRemove} /> : <DropHint slot={slot} />}
  </span>
);

export const SingleflightDebug: React.FC = () => {
  const [placed, setPlaced] = useState<Record<SlotId, string | null>>({
    A: null,
    B: null,
    C: null,
  });
  const [phase, setPhase] = useState<Phase>('idle');
  const [log, setLog] = useState<string[]>([]);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [burst, setBurst] = useState(0);
  const [tray, setTray] = useState<string[]>(BLOCKS.map((b) => b.id));
  const [dragging, setDragging] = useState<string | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const zoneRefs = useRef<Record<SlotId, HTMLElement | null>>({
    A: null,
    B: null,
    C: null,
  });
  const { line, say } = useKaimao('这个接口正在被打穿，把空缺补上喵');

  const dropTo = (id: string, slot: SlotId) => {
    const block = BLOCKS.find((b) => b.id === id);
    if (!block) return;

    const reset = () => {
      setPhase('idle');
      setLog([]);
      setVerdict(null);
    };

    // ① 形状不匹配：不入位，块弹回托盘。// TODO: play reject_buzz.mp3
    if (block.owner !== slot) {
      setTray((t) => (t.includes(id) ? t : [...t, id]));
      reset();
      say(
        `wrong-${slot}`,
        '这块塞不进这儿啦，形状都不对喵',
        `${SLOT_HINT[slot]}的位置要放「${BLOCKS.find((x) => x.owner === slot && !x.bad)?.label}」这一类语句`,
        'warn',
      );
      return;
    }

    // ② 形状匹配：原子换位。旧块（被顶掉的）退回托盘，新块入位。
    //    注意 setTray 只依赖闭包里的当前值，不在 setPlaced 的更新函数里调 setTray，
    //    否则 StrictMode 下更新函数跑两次会把同一块塞进托盘两份。
    const displaced = placed[slot];
    setPlaced((prev) => ({ ...prev, [slot]: id }));
    setTray((t) => {
      const next = t.filter((x) => x !== id);
      if (displaced && displaced !== id && !next.includes(displaced)) next.push(displaced);
      return next;
    });
    reset();
    // TODO: play snap_sound.mp3
    if (block.bad) {
      say(`bad-${slot}`, '这块看着能跑，其实是个坑喵', '先点「运行」看看它会把回源次数变成什么样', 'warn');
    }
  };

  const onDragEnd = (id: string, info: PanInfo) => {
    setDragging(null);
    const { x, y } = info.point;
    for (const s of ['A', 'B', 'C'] as SlotId[]) {
      const el = zoneRefs.current[s];
      const r = el?.getBoundingClientRect();
      if (r && x >= r.left - 6 && x <= r.right + 6 && y >= r.top - 6 && y <= r.bottom + 6) {
        dropTo(id, s);
        return;
      }
    }
  };

  const removeFrom = (slot: SlotId) => {
    // TODO: play pop_back.mp3
    const id = placed[slot];
    setPlaced((prev) => ({ ...prev, [slot]: null }));
    if (id) setTray((t) => (t.includes(id) ? t : [...t, id]));
    setPhase('idle');
    setLog([]);
    setVerdict(null);
  };

  const run = () => {
    if (phase === 'running') return;
    // TODO: play compile_run.mp3
    const v = evaluate(placed);
    setVerdict(null);
    setLog([]);
    setPhase('running');

    const lines =
      v.kind === 'fail'
        ? [
            '$ go run getuser.go',
            '> 200 个并发请求 user:42（同一时刻到达）',
            '  缓存 GET ......... MISS ×200',
            `  回源 ............. ${v.hits} 次`,
            `[FAIL] ${v.title}`,
            v.why,
          ]
        : v.kind === 'warn'
          ? [
              '$ go run getuser.go',
              '> 200 个并发请求 user:42（同一时刻到达）',
              '  缓存 GET ......... 未启用',
              '  回源 ............. 1 次（单飞合并成功）',
              `[WARN] ${v.title}`,
              v.why,
            ]
          : [
              '$ go run getuser.go',
              '> 200 个并发请求 user:42（同一时刻到达）',
              '  缓存 GET ......... MISS ×200',
              '  回源 ............. 1 次（单飞合并）',
              '  回填 ............. TTL 300s',
              `[PASS] ${v.title} · DB 回源 = 1 次 (−99.5%)`,
            ];

    lines.forEach((l, i) => {
      window.setTimeout(() => setLog((prev) => [...prev, l]), i * 280);
    });
    window.setTimeout(
      () => {
        setPhase(v.kind === 'pass' ? 'pass' : v.kind === 'warn' ? 'warn' : 'fail');
        setVerdict(v);
        if (v.kind === 'pass') {
          // TODO: play success_chime.mp3
          setBurst((n) => n + 1);
        } else {
          // TODO: play error_thud.mp3
        }
        if (v.kind === 'pass') {
          say('run-pass', '一次！200 个并发只打了一次库喵', 'singleflight 用 key 做分组，同 key 的并发只放一个去回源，其余等待并共享结果', 'ok');
        } else if (v.kind === 'warn') {
          say('run-warn', '能跑，但缓存算是白建了喵…', '缺缓存读取时 singleflight 仍然挡住回源，但每个请求都要进一次 singleflight，命中率为 0', 'warn');
        } else {
          say(`run-fail-${v.title}`, '又 200 次，库要挂了喵', v.why, 'warn');
        }
      },
      lines.length * 280 + 220,
    );
  };

  const tone =
    phase === 'pass' ? C.mint : phase === 'warn' ? C.amber : phase === 'fail' ? C.coral : C.ice;

  return (
    <div ref={cardRef} style={{ position: 'relative', paddingBottom: 62 }}>
      <ScenarioBar
        work={{
          tag: '故障复盘',
          head: '热点商品下架瞬间，200 并发把库打挂',
          body: 'user:42 是首页 banner 的 key。把 GetUser 的三处空缺补上，让 200 个并发只回源 1 次。',
        }}
        exam={{
          tag: '软考 · 架构',
          head: 'singleflight 与互斥锁到底差在哪',
          body: '考点：单飞合并「同一个 key」的并发，锁是串行化所有请求；单飞治不了不同 key 的雪崩。',
        }}
      />
      <Burst play={burst} />
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 300px', gap: 14 }}>
        {/* IDE */}
        <div style={glass({ padding: 0, overflow: 'hidden' })}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '9px 13px',
              borderBottom: `1px solid ${C.line}`,
            }}
          >
            <Dot color="#F09595" />
            <Dot color="#EF9F27" />
            <Dot color="#5DCAA5" />
            <span style={{ fontFamily: MONO, fontSize: 11.5, color: C.mute, marginLeft: 4 }}>
              cache/getuser.go
            </span>
            <motion.button
              whileTap={TAP}
              onClick={run}
              disabled={phase === 'running'}
              style={{
                marginLeft: 'auto',
                border: 'none',
                borderRadius: 8,
                padding: '5px 14px',
                fontFamily: SANS,
                fontSize: 12.5,
                fontWeight: 500,
                color: '#fff',
                cursor: phase === 'running' ? 'wait' : 'pointer',
                background: phase === 'running' ? C.iceSoft : C.ice,
                boxShadow: '0 3px 10px rgba(93,180,229,0.35)',
              }}
            >
              {phase === 'running' ? '运行中…' : '运行'}
            </motion.button>
            <motion.button
              whileTap={TAP}
              onClick={() => {
                setPlaced({ A: null, B: null, C: null });
                setTray(BLOCKS.map((b) => b.id));
                setPhase('idle');
                setLog([]);
                setVerdict(null);
              }}
              style={{
                border: `1px solid ${C.line}`,
                borderRadius: 8,
                padding: '5px 11px',
                fontFamily: SANS,
                fontSize: 12.5,
                color: C.mute,
                background: 'transparent',
                cursor: 'pointer',
              }}
            >
              重置
            </motion.button>
          </div>

          <div style={{ background: 'rgba(247,251,254,0.72)', padding: '12px 0' }}>
            {CODE_LINES.map((ln) => (
              <div
                key={ln.n}
                style={{
                  display: 'flex',
                  gap: 12,
                  padding: '1.5px 14px',
                  fontFamily: MONO,
                  fontSize: 12.5,
                  lineHeight: 1.85,
                  color: C.slate,
                }}
              >
                <span
                  style={{
                    width: 18,
                    flex: '0 0 auto',
                    textAlign: 'right',
                    color: '#A8BFCE',
                    userSelect: 'none',
                  }}
                >
                  {ln.n}
                </span>
                <span style={{ minWidth: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {ln.render({ placed, zr: zoneRefs, rm: removeFrom })}
                </span>
              </div>
            ))}
          </div>

          {/* 托盘 */}
          <div style={{ borderTop: `1px solid ${C.line}`, padding: '11px 13px' }}>
            <div style={{ fontSize: 11.5, color: C.mute, marginBottom: 8 }}>
              代码块 · 拖进上面的空位；已放下的块点一下退回
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
              {tray.map((id) => {
                const b = BLOCKS.find((x) => x.id === id)!;
                return (
                  <motion.div
                    key={id}
                    data-block={id}
                    drag
                    dragSnapToOrigin
                    dragConstraints={cardRef}
                    dragElastic={DRAG_ELASTIC}
                    whileDrag={{ scale: 1.05, zIndex: 60, cursor: 'grabbing' }}
                    whileHover={{ y: -1 }}
                    onDragStart={() => setDragging(id)}
                    onDragEnd={(_, info) => onDragEnd(id, info)}
                    style={{
                      fontFamily: MONO,
                      fontSize: 11.5,
                      padding: '5px 9px',
                      borderRadius: 7,
                      background: '#fff',
                      border: `1px solid ${b.bad ? 'rgba(248,113,113,0.4)' : C.line}`,
                      color: b.bad ? C.coralDeep : C.slate,
                      cursor: 'grab',
                      boxShadow: '0 2px 6px rgba(160,190,220,0.18)',
                      userSelect: 'none',
                      opacity: dragging === id ? 0.6 : 1,
                    }}
                  >
                    {b.label}
                  </motion.div>
                );
              })}
              {tray.length === 0 && (
                <span style={{ fontSize: 12, color: C.mute }}>全部放上去了，点「运行」试试</span>
              )}
            </div>
          </div>
        </div>

        {/* Terminal */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div
            style={{
              borderRadius: 14,
              overflow: 'hidden',
              border: `1px solid ${tone}`,
              background: '#22384A',
              transition: 'border-color .25s',
            }}
          >
            <div
              style={{
                padding: '7px 12px',
                borderBottom: '1px solid rgba(255,255,255,0.10)',
                fontFamily: MONO,
                fontSize: 11,
                color: '#8FA9BD',
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <span>TERMINAL</span>
              <span style={{ color: tone }}>{phase === 'idle' ? 'ready' : phase}</span>
            </div>
            <div
              className="km-scroll"
              style={{
                height: 186,
                overflowY: 'auto',
                padding: '10px 12px',
                fontFamily: MONO,
                fontSize: 11.5,
                lineHeight: 1.75,
              }}
            >
              {log.length === 0 && phase !== 'running' && (
                <div style={{ color: '#6E899C' }}>点击「运行」，观察 200 个并发的回源次数</div>
              )}
              {log.map((l, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  style={{
                    color: l.startsWith('[PASS]')
                      ? C.mint
                      : l.startsWith('[FAIL]')
                        ? C.coral
                        : l.startsWith('[WARN]')
                          ? C.amber
                          : l.startsWith('$')
                            ? '#8FA9BD'
                            : '#DCEAF6',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {l}
                </motion.div>
              ))}
              {phase === 'running' && (
                <span style={{ color: C.ice, animation: 'km-pulse 1s infinite' }}>▌</span>
              )}
            </div>
          </div>

          {/* 200 格回源指示 */}
          <div style={glass({ padding: '11px 13px' })}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 11.5,
                color: C.mute,
                marginBottom: 8,
              }}
            >
              <span>回源请求（每格 = 1 次）</span>
              <span style={{ fontFamily: MONO, color: verdict && verdict.hits > 1 ? C.coralDeep : C.mintDeep }}>
                {verdict ? verdict.hits : 0}
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(40, 1fr)', gap: 2 }}>
              {Array.from({ length: 200 }).map((_, i) => {
                const lit = verdict ? i < verdict.hits : false;
                return (
                  <motion.div
                    key={i}
                    animate={{
                      background: lit ? C.coral : 'rgba(191,221,241,0.55)',
                      scaleY: lit ? 1 : 0.7,
                    }}
                    transition={{ delay: verdict ? i * 0.003 : 0, duration: 0.22 }}
                    style={{ height: 7, borderRadius: 1.5, transformOrigin: 'bottom' }}
                  />
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <KaimaoBubble line={line} />
    </div>
  );
};

const Dot: React.FC<{ color: string }> = ({ color }) => (
  <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, opacity: 0.85 }} />
);

/* ═══════════════════════════════════════════════════════════════════════════
 *  模块 03 · 闯关试炼：三道真题 BOSS 战
 * ═══════════════════════════════════════════════════════════════════════════ */

interface Option {
  key: string;
  text: string;
}

interface Question {
  id: string;
  src: string;
  stem: string;
  options: Option[];
  answer: string;
  why: string;
}

/** 题干逐字取自 exercises.json（只读引用，原文件不动） */
export const QUESTIONS: Question[] = [
  {
    id: 'q1',
    src: '真题 · 缓存穿透的成因与布隆过滤器的定位',
    stem: '关于缓存穿透与布隆过滤器，下列说法正确的是？',
    options: [
      { key: 'A', text: '布隆过滤器能确定某 key「一定存在」，可完全替代数据库查询' },
      {
        key: 'B',
        text: '布隆过滤器判定「不存在」时一定不存在（无假阴性）；判定「存在」时可能不存在（有假阳性）',
      },
      { key: 'C', text: '布隆过滤器支持直接删除元素，删除后不影响其他元素的判定' },
      { key: 'D', text: '缓存穿透只能用布隆过滤器解决，缓存空值没有意义' },
    ],
    answer: 'B',
    why: '布隆只有假阳性、没有假阴性：说不存在就一定不存在（可安全拦截），说存在则可能误判（仍要查库）。它支持不了删除（位图共享），空值缓存是另一条独立防线。',
  },
  {
    id: 'q2',
    src: '真题 · 缓存击穿与缓存雪崩的区别',
    stem: '关于击穿与雪崩，下列判断正确的是？',
    options: [
      { key: 'A', text: '击穿是「大量不同 key 同时失效」，雪崩是「单个热点 key 失效」' },
      { key: 'B', text: '击穿是「单个热点 key 失效后高并发全部回源」，雪崩是「大批 key 在同一时刻集体失效」' },
      { key: 'C', text: '雪崩只能通过加锁解决，与 TTL 设置无关' },
      { key: 'D', text: '逻辑过期（异步重建）只能用于雪崩，不能用于击穿' },
    ],
    answer: 'B',
    why: '击穿是「一个」热点 key：量集中，靠 singleflight / 逻辑过期。雪崩是「一批」key：面扩散，靠 TTL 抖动 / 多级缓存 / 熔断降级。两者防护手段几乎不通用。',
  },
  {
    id: 'q3',
    src: '真题 · 三种更新策略的一致性取舍',
    stem: '关于 Write-Through / Write-Behind / Cache-Aside，下列说法正确的是？',
    options: [
      { key: 'A', text: 'Write-Behind 是强一致策略，崩溃不丢数据' },
      { key: 'B', text: 'Write-Through 同步写缓存与库，一致性最好但写延迟高' },
      { key: 'C', text: 'Cache-Aside 由调用方维护缓存，写时通常「更新缓存」而非「删除缓存」' },
      { key: 'D', text: '三种策略对写延迟的影响相同' },
    ],
    answer: 'B',
    why: 'Write-Through 双写同步，一致性最好、延迟最高；Write-Behind 异步刷盘，快但崩溃可能丢数据；Cache-Aside 写时应「删缓存」而非「更新缓存」，否则并发交错会留下旧值（见 ex09：先删 60% 脏 / 先更库 10% 脏）。',
  },
];

/** 确定性洗牌：同一题每次打开顺序一致，可复现；避免「三题答案全选 B」送分 */
function shuffleSeeded<T>(arr: T[], seed: number): T[] {
  const a = [...arr];
  let s = seed * 7919 + 104729;
  const rnd = () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const Monster: React.FC<{ hp: number; hit: boolean }> = ({ hp, hit }) => (
  <motion.div
    animate={
      hit
        ? { x: [0, -9, 9, -5, 0], filter: ['brightness(1)', 'brightness(1.7)', 'brightness(1)'] }
        : { y: [0, -5, 0] }
    }
    transition={hit ? { duration: 0.42 } : { duration: 2.8, repeat: Infinity, ease: 'easeInOut' }}
    style={{ position: 'relative', width: 118, height: 108 }}
  >
    <svg viewBox="0 0 118 108" aria-hidden="true">
      <defs>
        <linearGradient id="km-slime" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={hp > 0 ? '#BFE9F7' : '#E8EEF3'} />
          <stop offset="100%" stopColor={hp > 0 ? '#7CC6E4' : '#CBD8E2'} />
        </linearGradient>
      </defs>
      {/* 六边形身体：全站母题 */}
      <path
        d="M59 6 L104 31 L104 77 L59 102 L14 77 L14 31 Z"
        fill="url(#km-slime)"
        stroke={hp > 0 ? C.iceDeep : C.mute}
        strokeWidth="2"
        opacity={hp > 0 ? 1 : 0.55}
      />
      {/* 眼 */}
      <circle cx="45" cy="48" r="5.4" fill={C.slate} opacity={hp > 0 ? 0.86 : 0.3} />
      <circle cx="73" cy="48" r="5.4" fill={C.slate} opacity={hp > 0 ? 0.86 : 0.3} />
      {hp <= 0 ? (
        <>
          <path d="M39 42 L51 54 M51 42 L39 54" stroke={C.mute} strokeWidth="2.4" strokeLinecap="round" />
          <path d="M67 42 L79 54 M79 42 L67 54" stroke={C.mute} strokeWidth="2.4" strokeLinecap="round" />
        </>
      ) : (
        <>
          <circle cx="47" cy="46" r="1.7" fill="#fff" />
          <circle cx="75" cy="46" r="1.7" fill="#fff" />
        </>
      )}
      {/* 嘴 */}
      <path
        d="M50 66 Q59 74 68 66"
        stroke={C.slate}
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        opacity={hp > 0 ? 0.8 : 0.35}
      />
    </svg>
  </motion.div>
);

export const CacheBossRaid: React.FC = () => {
  const [idx, setIdx] = useState(0);
  const [picked, setPicked] = useState<string | null>(null);
  const [wrongKeys, setWrongKeys] = useState<string[]>([]);
  const [hp, setHp] = useState(3);
  const [hit, setHit] = useState(false);
  const [stars, setStars] = useState<number | null>(null);
  const [solved, setSolved] = useState<Record<string, number>>({});
  const [missile, setMissile] = useState<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const arenaRef = useRef<HTMLDivElement>(null);
  const { line, say } = useKaimao('三题，全部答对才算通关喵');

  const q = QUESTIONS[idx];
  const shuffled = useMemo(() => shuffleSeeded(q.options, idx + 1), [q.id, idx]);
  const answered = picked === q.answer;
  const isLast = idx === QUESTIONS.length - 1;
  const cleared = Object.keys(solved).length === QUESTIONS.length;

  const onPick = (opt: Option, el: HTMLElement) => {
    if (answered) return;

    if (opt.key !== q.answer) {
      // TODO: play buzz_wrong.mp3
      setWrongKeys((k) => (k.includes(opt.key) ? k : [...k, opt.key]));
      say(
        `wrong-${q.id}`,
        '再想想喵~ 这只怪不吃这一套',
        q.why,
        'warn',
      );
      return;
    }

    // 答对：发射冰蓝飞弹
    // TODO: play laser_hit.mp3
    setPicked(q.answer);
    setSolved((s) => ({ ...s, [q.id]: s[q.id] ?? (wrongKeys.length === 0 ? 3 : 1) }));
    setStars(wrongKeys.length === 0 ? 3 : 1);

    const arena = arenaRef.current;
    if (arena) {
      const ar = arena.getBoundingClientRect();
      const or = el.getBoundingClientRect();
      setMissile({
        x: or.left + or.width / 2 - ar.left,
        y: or.top + or.height / 2 - ar.top,
        tx: ar.width * 0.79,
        ty: ar.height * 0.13,
      });
    }
    window.setTimeout(() => setHit(true), 380);
    window.setTimeout(() => {
      setHit(false);
      setHp((h) => Math.max(0, h - 1));
    }, 760);
    window.setTimeout(() => setMissile(null), 900);

    say(
      `right-${q.id}`,
      wrongKeys.length === 0 ? '一击命中！' : '终于对了喵……',
      q.why,
      'ok',
    );
  };

  const next = () => {
    if (isLast) return;
    setIdx((i) => i + 1);
    setPicked(null);
    setWrongKeys([]);
    setStars(null);
  };

  return (
    <div ref={arenaRef} style={{ position: 'relative', paddingBottom: 62 }}>
      <ScenarioBar
        work={{
          tag: '面试现场',
          head: '「缓存这块你踩过什么坑？」',
          body: '面试官通常连追三问：抖动会不会读到旧数据？单飞能不能治雪崩？延迟双删够不够？',
        }}
        exam={{
          tag: '本章真题',
          head: '三题定级，全对才算过关',
          body: '真题原始答案全是 B —— 已按题号确定性洗牌，选项顺序每轮固定但位置打乱，蒙不了。',
        }}
      />
      {/* 战斗区 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 200px', gap: 14 }}>
        <div style={glass({ padding: '16px 18px' })}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 12,
              fontSize: 11.5,
              color: C.mute,
            }}
          >
            <span
              style={{
                fontFamily: MONO,
                background: 'rgba(93,180,229,0.14)',
                color: C.iceDeep,
                padding: '2px 7px',
                borderRadius: 5,
              }}
            >
              Q{idx + 1}/{QUESTIONS.length}
            </span>
            <span>{q.src}</span>
          </div>

          <div style={{ fontSize: 14.5, lineHeight: 1.7, color: C.slate, marginBottom: 14 }}>
            {q.stem}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {shuffled.map((opt) => {
              const isWrong = wrongKeys.includes(opt.key);
              const isRight = answered && opt.key === q.answer;
              return (
                <motion.div
                  key={opt.key}
                  whileTap={answered ? undefined : TAP}
                  animate={
                    isWrong
                      ? { x: [0, -7, 7, -4, 0] }
                      : { x: 0 }
                  }
                  transition={{ duration: 0.36 }}
                  onClick={(e) => onPick(opt, e.currentTarget as HTMLElement)}
                  style={{
                    display: 'flex',
                    gap: 10,
                    alignItems: 'flex-start',
                    padding: '10px 12px',
                    borderRadius: 12,
                    cursor: answered ? 'default' : 'pointer',
                    userSelect: 'none',
                    background: isRight
                      ? 'rgba(49,208,170,0.14)'
                      : isWrong
                        ? 'rgba(248,113,113,0.12)'
                        : 'rgba(255,255,255,0.66)',
                    border: `1px solid ${
                      isRight ? C.mint : isWrong ? C.coral : 'rgba(207,226,239,0.9)'
                    }`,
                    boxShadow: isRight
                      ? '0 0 0 3px rgba(49,208,170,0.14)'
                      : isWrong
                        ? '0 0 0 3px rgba(248,113,113,0.12)'
                        : 'none',
                    transition: 'background .2s, border-color .2s',
                    opacity: answered && !isRight ? 0.55 : 1,
                  }}
                >
                  <span
                    style={{
                      flex: '0 0 auto',
                      width: 20,
                      height: 20,
                      borderRadius: 6,
                      display: 'grid',
                      placeItems: 'center',
                      fontFamily: MONO,
                      fontSize: 11.5,
                      background: isRight ? C.mint : isWrong ? C.coral : 'rgba(93,180,229,0.16)',
                      color: isRight || isWrong ? '#fff' : C.iceDeep,
                    }}
                  >
                    {opt.key}
                  </span>
                  <span style={{ fontSize: 13, lineHeight: 1.6, color: C.slate }}>{opt.text}</span>
                </motion.div>
              );
            })}
          </div>

          <AnimatePresence>
            {answered && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                style={{ overflow: 'hidden' }}
              >
                <div
                  style={{
                    marginTop: 12,
                    padding: '10px 12px',
                    borderRadius: 11,
                    background: 'rgba(49,208,170,0.09)',
                    border: `1px solid rgba(49,208,170,0.30)`,
                    fontSize: 12.5,
                    lineHeight: 1.65,
                    color: C.slate,
                  }}
                >
                  <b style={{ color: C.mintDeep }}>解析 </b>
                  {q.why}
                </div>
                {!isLast && (
                  <motion.button
                    whileTap={TAP}
                    onClick={next}
                    style={{
                      marginTop: 10,
                      width: '100%',
                      border: 'none',
                      borderRadius: 11,
                      padding: '9px 0',
                      fontFamily: SANS,
                      fontSize: 13,
                      fontWeight: 500,
                      color: '#fff',
                      background: C.ice,
                      cursor: 'pointer',
                      boxShadow: '0 4px 14px rgba(93,180,229,0.32)',
                    }}
                  >
                    下一题
                  </motion.button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* 怪物栏 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div
            style={glass({
              padding: '14px 12px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 10,
            })}
          >
            <div style={{ display: 'flex', gap: 4, width: '100%' }}>
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  animate={{
                    background: i < hp ? C.coral : 'rgba(93,113,131,0.16)',
                    scaleY: i < hp ? 1 : 0.72,
                  }}
                  transition={SPRING}
                  style={{ flex: 1, height: 8, borderRadius: 5 }}
                />
              ))}
            </div>
            <div style={{ fontFamily: MONO, fontSize: 11.5, color: C.mute }}>HP {hp}/3</div>
            <Monster hp={hp} hit={hit} />
            <div style={{ fontFamily: MONO, fontSize: 11, color: C.mute }}>
              {hp > 0 ? `剩 ${hp} 层护甲` : '已击破'}
            </div>
          </div>

          {/* 进度 */}
          <div style={glass({ padding: '11px 12px' })}>
            <div style={{ fontSize: 11.5, color: C.mute, marginBottom: 8 }}>通关进度</div>
            <div style={{ display: 'flex', gap: 5 }}>
              {QUESTIONS.map((qq, i) => {
                const done = solved[qq.id];
                return (
                  <div
                    key={qq.id}
                    style={{
                      flex: 1,
                      height: 5,
                      borderRadius: 3,
                      background: done
                        ? done >= 3
                          ? C.mint
                          : C.amber
                        : i === idx
                          ? C.ice
                          : 'rgba(93,113,131,0.16)',
                    }}
                  />
                );
              })}
            </div>
            <div style={{ marginTop: 9, display: 'flex', gap: 2 }}>
              {Array.from({ length: 9 }).map((_, i) => {
                const filled = i < Object.values(solved).reduce((a, b) => a + b, 0);
                return (
                  <span
                    key={i}
                    style={{
                      flex: 1,
                      height: 4,
                      borderRadius: 2,
                      background: filled ? C.ice : 'rgba(93,113,131,0.14)',
                    }}
                  />
                );
              })}
            </div>
            <div style={{ fontSize: 11, color: C.mute, marginTop: 7, fontFamily: MONO }}>
              {Object.values(solved).reduce((a, b) => a + b, 0)} / 9 ★
            </div>
          </div>
        </div>
      </div>

      {/* 飞弹 */}
      <AnimatePresence>
        {missile && (
          <motion.div
            initial={{ x: missile.x, y: missile.y, opacity: 1, scale: 1 }}
            animate={{
              x: [missile.x, (missile.x + missile.tx) / 2, missile.tx],
              y: [missile.y, Math.min(missile.y, missile.ty) - 64, missile.ty],
              opacity: [1, 1, 0],
              scale: [1, 1.35, 0.65],
              rotate: [0, 140, 260],
            }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.78, times: [0, 0.55, 1], ease: 'easeOut' }}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: 16,
              height: 16,
              borderRadius: '50%',
              background: 'radial-gradient(circle at 35% 32%, #ffffff 0%, #8FD3F4 42%, #3E9BD1 100%)',
              boxShadow: '0 0 16px rgba(93,180,229,0.85), 0 0 34px rgba(93,180,229,0.45)',
              pointerEvents: 'none',
              zIndex: 50,
            }}
          />
        )}
      </AnimatePresence>

      {/* 星级 */}
      <AnimatePresence>
        {stars !== null && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={SPRING}
            style={{
              position: 'absolute',
              left: '50%',
              top: 52,
              transform: 'translateX(-50%)',
              display: 'flex',
              gap: 5,
              padding: '6px 14px',
              borderRadius: 20,
              background: 'rgba(255,255,255,0.9)',
              border: `1px solid ${C.mint}`,
              boxShadow: '0 6px 20px rgba(49,208,170,0.25)',
              zIndex: 45,
            }}
          >
            {Array.from({ length: 3 }).map((_, i) => (
              <Star key={i} on={i < stars} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* 通关结算 */}
      <AnimatePresence>
        {cleared && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(235,244,250,0.72)',
              backdropFilter: 'blur(6px)',
              display: 'grid',
              placeItems: 'center',
              borderRadius: 14,
              zIndex: 60,
            }}
          >
            <motion.div
              initial={{ y: 16, scale: 0.94 }}
              animate={{ y: 0, scale: 1 }}
              transition={SPRING}
              style={glass({ padding: '26px 30px', textAlign: 'center', maxWidth: 360 })}
            >
              <div style={{ fontSize: 20, fontWeight: 500, color: C.slate }}>本章通关</div>
              <div style={{ fontSize: 13, color: C.mute, marginTop: 6, lineHeight: 1.6 }}>
                穿透 · 击穿 · 雪崩 · 写一致性
                <br />
                四道防线全部建立
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 4, marginTop: 14 }}>
                {Array.from({ length: 9 }).map((_, i) => (
                  <Star key={i} on={i < Object.values(solved).reduce((a, b) => a + b, 0)} />
                ))}
              </div>
              <motion.button
                whileTap={TAP}
                onClick={() => {
                  setSolved({});
                  setIdx(0);
                  setPicked(null);
                  setWrongKeys([]);
                  setStars(null);
                  setHp(3);
                }}
                style={{
                  marginTop: 16,
                  border: 'none',
                  borderRadius: 11,
                  padding: '9px 22px',
                  fontFamily: SANS,
                  fontSize: 13,
                  fontWeight: 500,
                  color: '#fff',
                  background: C.ice,
                  cursor: 'pointer',
                  boxShadow: '0 4px 14px rgba(93,180,229,0.32)',
                }}
              >
                再来一轮
              </motion.button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <KaimaoBubble line={line} />
    </div>
  );
};

const Star: React.FC<{ on: boolean }> = ({ on }) => (
  <svg width="16" height="16" viewBox="0 0 20 20" aria-hidden="true">
    <path
      d="M10 1.6 L12.6 7.2 L18.8 7.9 L14.2 12.2 L15.5 18.4 L10 15.2 L4.5 18.4 L5.8 12.2 L1.2 7.9 L7.4 7.2 Z"
      fill={on ? '#F5C451' : 'rgba(93,113,131,0.18)'}
      stroke={on ? '#D9A32B' : 'transparent'}
      strokeWidth="1"
    />
  </svg>
);

/* ═══════════════════════════════════════════════════════════════════════════
 *  默认导出：带 Tab 的整合容器
 * ═══════════════════════════════════════════════════════════════════════════ */

const TABS = [
  { id: 's1', label: '沙盒推演', sub: 'TTL 抖动 vs 雪崩', node: <AvalancheSandbox /> },
  { id: 's2', label: '代码 Debug', sub: 'singleflight 补全', node: <SingleflightDebug /> },
  { id: 's3', label: '闯关试炼', sub: '三道真题 BOSS', node: <CacheBossRaid /> },
];

export const CacheDesignLab: React.FC = () => {
  const [tab, setTab] = useState(0);

  return (
    <div
      className="kmlab"
      style={{
        minHeight: 520,
        padding: '22px 24px 24px',
        borderRadius: 20,
        background:
          'radial-gradient(120% 90% at 12% 0%, #F7FCFF 0%, #EBF4FA 46%, #E3EFF8 100%)',
        border: '1px solid rgba(255,255,255,0.9)',
        boxShadow: '0 18px 50px rgba(140,175,205,0.18)',
        fontFamily: SANS,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <GlobalStyle />

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 14, marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 11.5, color: C.iceDeep, letterSpacing: 0.6, fontFamily: MONO }}>
            mw-ch04
          </div>
          <div style={{ fontSize: 19, fontWeight: 500, color: C.slate, marginTop: 2 }}>
            缓存设计与三大经典问题
          </div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          {TABS.map((t, i) => (
            <motion.button
              key={t.id}
              whileTap={TAP}
              onClick={() => setTab(i)}
              style={{
                border: `1px solid ${i === tab ? C.ice : 'rgba(207,226,239,0.9)'}`,
                borderRadius: 11,
                padding: '7px 13px',
                background: i === tab ? 'rgba(93,180,229,0.13)' : 'rgba(255,255,255,0.62)',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background .18s, border-color .18s',
              }}
            >
              <div
                style={{
                  fontSize: 12.5,
                  fontWeight: 500,
                  color: i === tab ? C.iceDeep : C.slate,
                  lineHeight: 1.3,
                }}
              >
                {t.label}
              </div>
              <div style={{ fontSize: 10.5, color: C.mute, lineHeight: 1.3 }}>{t.sub}</div>
            </motion.button>
          ))}
        </div>
      </div>

      {/*
        这里**不能**用 <AnimatePresence mode="wait">：
        模块 02 里拖拽过的代码块在落位时会被移出托盘、随即卸载，framer 会留下一个
        没有跑完的 presence 子节点，导致退出动画永不结束 —— 表现为「切 Tab 后按钮高亮变了，
        但内容还是上一个模块，或者整块空白」。进场淡入不需要等旧内容退场，按 key 重挂即可。
      */}
      <motion.div
        key={tab}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22 }}
      >
        {TABS[tab].node}
      </motion.div>
    </div>
  );
};

export default CacheDesignLab;
