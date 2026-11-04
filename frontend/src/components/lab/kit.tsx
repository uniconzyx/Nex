/**
 * kit.tsx —— 交互实验的共用零件（前端版）
 * ============================================================================
 * 从 `viz/interactive/mw-ch04/CacheDesignLab.tsx` 的前 385 行抽出来，只保留
 * 通用件：设计令牌 / 液态玻璃 / 凯喵气泡 / 双场景条 / 粒子爆闪。
 *
 * **和预览台那版的唯一区别是色源**：预览台直接写死冰蓝奶白的十六进制，
 * 因为它要能单文件拷到任何工程里跑；而 App 里必须跟着主题走（浅色 / 深色
 * 运行时切换，见 SettingsPage），所以这里全部改成 CSS 变量，取值在
 * `lab.css` 的 `.kmlab` 作用域里定义一次 —— 改主题只改那一个文件。
 *
 * 两条不能改的约定：
 *   1. 凯喵台词是「先人设、后教学」：同一槽位第 3 次才说知识点（useKaimao）；
 *   2. 物理拖拽的弹性固定 0.2（DRAG_ELASTIC），这是主人定的手感基线。
 */
import React, { useCallback, useRef, useState } from 'react';
import { motion } from 'framer-motion';

/* ────────────────────────────── 设计令牌 ────────────────────────────── */

/** 全部指向 CSS 变量：值在 lab.css 里，浅色/深色两套 */
export const C = {
  bg: 'var(--kmlab-bg)',
  bgDeep: 'var(--kmlab-bg-deep)',
  ice: 'var(--km-primary)',
  iceDeep: 'var(--km-primary-deep)',
  iceSoft: 'var(--km-secondary)',
  slate: 'var(--km-title)',
  mute: 'var(--km-caption)',
  line: 'var(--kmlab-line)',
  mint: 'var(--km-success)',
  mintDeep: 'var(--kmlab-mint-deep)',
  coral: 'var(--km-danger)',
  coralDeep: 'var(--kmlab-coral-deep)',
  amber: 'var(--km-warning)',
  white: 'var(--kmlab-white)',
} as const;

export const MONO =
  "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace";
export const SANS =
  "'Microsoft YaHei', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Noto Sans SC', system-ui, sans-serif";

/** 液态玻璃材质 */
export const glass = (extra?: React.CSSProperties): React.CSSProperties => ({
  background: 'var(--kmlab-glass)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
  border: '1px solid var(--kmlab-glass-border)',
  boxShadow: 'var(--kmlab-shadow-soft)',
  borderRadius: 14,
  ...extra,
});

/** 弹簧回弹：所有可点元素共用 */
export const TAP = { scale: 0.95 } as const;
export const SPRING = { type: 'spring', stiffness: 300, damping: 20 } as const;
/** 拖拽边缘拉伸弹性（规范要求 0.2） */
export const DRAG_ELASTIC = 0.2;

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

/** 猫脸：SVG 的 fill/stroke 属性不解析 var()，所以统一走 style */
const KaimaoFace: React.FC<{ mood: KaimaoTone }> = ({ mood }) => {
  const eye =
    mood === 'ok' ? C.mint : mood === 'warn' ? C.coral : mood === 'teach' ? C.iceDeep : C.slate;
  const brow = mood === 'warn' || mood === 'teach';
  return (
    <svg width="38" height="38" viewBox="0 0 34 34" aria-hidden="true">
      {/* 六边形底：全站母题 */}
      <path
        d="M17 1 L31 8.6 L31 24.4 L17 32 L3 24.4 L3 8.6 Z"
        style={{ fill: 'var(--kmlab-face)', stroke: C.ice }}
        strokeWidth="1.4"
      />
      {/* 猫耳 */}
      <path d="M8.4 9 L10.8 2.8 L14.6 7.4 Z" style={{ fill: C.ice }} opacity="0.5" />
      <path d="M25.6 9 L23.2 2.8 L19.4 7.4 Z" style={{ fill: C.ice }} opacity="0.5" />
      {/* 眼 */}
      {brow ? (
        <>
          <path d="M10.6 15.4 L14.6 14.2" style={{ stroke: eye }} strokeWidth="1.4" strokeLinecap="round" />
          <path d="M23.4 15.4 L19.4 14.2" style={{ stroke: eye }} strokeWidth="1.4" strokeLinecap="round" />
        </>
      ) : null}
      <circle cx="12.6" cy="17.6" r="1.9" style={{ fill: eye }} />
      <circle cx="21.4" cy="17.6" r="1.9" style={{ fill: eye }} />
      {/* 嘴 */}
      <path
        d="M15.2 22 Q17 23.8 18.8 22"
        style={{ stroke: C.slate }}
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
        // 窄屏（≤420）放不下一行：按钮组固定宽、文案列给 240 的 flex-basis，
        // 挤不下时整列换到第二行占满宽度，而不是被压成 166px 的窄条
        flexWrap: 'wrap',
        background: 'rgba(var(--kmlab-rgb),0.52)',
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
                    ? 'rgba(var(--kmlab-coral-rgb),0.16)'
                    : 'rgba(var(--kmlab-ice-rgb),0.18)'
                  : 'rgba(var(--kmlab-rgb),0.5)',
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

      <div className="km-sb-div" style={{ width: 1, height: 26, background: C.line, flex: '0 0 auto' }} />

      <motion.div
        key={mode}
        initial={{ opacity: 0, x: 6 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.16 }}
        style={{ minWidth: 0, flex: '1 1 240px' }}
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
          {/* 场景标题里会带 `header/nav/main/article/aside/footer` 这类无空格长 token，
              不给 anywhere 会在 420px 下按 min-content 撑出卡片外 */}
          <span style={{ fontSize: 13, fontWeight: 500, color: C.slate, minWidth: 0, overflowWrap: 'anywhere' }}>
            {cur.head}
          </span>
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
