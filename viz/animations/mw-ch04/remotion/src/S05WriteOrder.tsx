import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { Backdrop, Kaimao, Title } from './components';
import { C, FONT_CN, FONT_MONO, easeOut, glass, span } from './theme';

/**
 * S05 · 实战：Cache-Aside 的两种写顺序
 *
 * 深度落点：
 *  ① 差异不在「谁先谁后」的直觉，而在「DEL 之后、UPDATE 之前，读线程是否可能读到旧值并回填」这个窗口；
 *  ② 全交错枚举：先删缓存 6/10 残留旧值、先更库 1/10（ex09，同分母 10 可比）；
 *  ③ 两种都不是强一致：延迟双删只缩小窗口，回填更晚仍脏 —— 强一致要串行化或 binlog 订阅。
 *
 * 数据来源：examples/ex09-cache-aside-order.json（10 种合法交错，6 脏 / 1 脏）、
 *          examples/ex10-delayed-double-delete.json（A 60% / B 10% / C 0%，同一口径同一分母）。
 * 口径：只有「缓存残留旧值」算脏；缓存为空是 miss，下次读会回填新值，不算脏。
 */

type Step = { actor: 'W' | 'R'; text: string; bad?: boolean };

const LEFT: Step[] = [
  { actor: 'W', text: 'DEL cache' },
  { actor: 'R', text: 'GET → MISS' },
  { actor: 'R', text: 'READ db → OLD', bad: true },
  { actor: 'W', text: 'UPDATE db = NEW' },
  { actor: 'R', text: 'SET cache = OLD', bad: true },
];

const RIGHT: Step[] = [
  { actor: 'W', text: 'UPDATE db = NEW' },
  { actor: 'R', text: 'GET → MISS' },
  { actor: 'R', text: 'READ db = NEW' },
  { actor: 'R', text: 'SET cache = NEW' },
  { actor: 'W', text: 'DEL cache' },
];

const Row: React.FC<{ s: Step; i: number; p: number }> = ({ s, i, p }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      height: 34,
      opacity: p,
      transform: `translateX(${(1 - p) * -12}px)`,
    }}
  >
    <span
      style={{
        width: 15,
        fontFamily: FONT_MONO,
        fontSize: 11.5,
        color: C.mute,
        textAlign: 'right',
      }}
    >
      {i + 1}
    </span>
    <span
      style={{
        width: 20,
        height: 20,
        borderRadius: 6,
        display: 'grid',
        placeItems: 'center',
        fontFamily: FONT_MONO,
        fontSize: 11,
        fontWeight: 700,
        color: '#fff',
        background: s.actor === 'W' ? C.iceDeep : C.ice,
      }}
    >
      {s.actor}
    </span>
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 12.5,
        color: s.bad ? C.coral : C.slate,
        fontWeight: s.bad ? 500 : 400,
        whiteSpace: 'nowrap',
      }}
    >
      {s.text}
    </span>
    {s.bad && <span style={{ fontSize: 12, color: C.coral }}>← 脏</span>}
  </div>
);

const Panel: React.FC<{
  x: number;
  title: string;
  tone: string;
  steps: Step[];
  p0: number;
  f: number;
  state: React.ReactNode;
  ratio: number;
  ratioLabel: string;
}> = ({ x, title, tone, steps, p0, f, state, ratio, ratioLabel }) => (
  <div style={{ position: 'absolute', left: x, top: 128, width: 560 }}>
    <div style={{ ...glass({ padding: '10px 13px' }), display: 'flex', alignItems: 'center', gap: 9 }}>
      <span style={{ width: 9, height: 9, borderRadius: 9, background: tone, flexShrink: 0 }} />
      <span style={{ fontFamily: FONT_CN, fontSize: 14, fontWeight: 500, color: C.slate }}>{title}</span>
      <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: C.mute, marginLeft: 'auto' }}>
        cache-aside · 5 步交错
      </span>
    </div>

    <div style={{ marginTop: 10, paddingLeft: 4 }}>
      {steps.map((s, i) => (
        <Row key={i} s={s} i={i} p={easeOut(span(f, p0 + i * 7, p0 + i * 7 + 10))} />
      ))}
    </div>

    {/* 状态栏 */}
    <div
      style={{
        marginTop: 8,
        ...glass({
          padding: '9px 12px',
          background: 'rgba(255,255,255,0.7)',
        }),
      }}
    >
      {state}
    </div>

    {/* 脏比例 */}
    <div style={{ marginTop: 9, display: 'flex', alignItems: 'center', gap: 9 }}>
      <span style={{ fontFamily: FONT_CN, fontSize: 12, color: C.mute, width: 78 }}>
        交错脏比例
      </span>
      <div style={{ flex: 1, height: 7, borderRadius: 7, background: 'rgba(93,113,131,0.14)' }}>
        <div
          style={{
            width: `${ratio * 100}%`,
            height: 7,
            borderRadius: 7,
            background: ratio >= 0.5 ? C.coral : ratio <= 0.2 ? C.mint : '#E8A33D',
          }}
        />
      </div>
      <span
        style={{
          fontFamily: FONT_MONO,
          fontSize: 12.5,
          fontWeight: 700,
          color: ratio >= 0.5 ? C.coral : ratio <= 0.2 ? C.mint : '#C28419',
          width: 86,
          textAlign: 'right',
        }}
      >
        {ratioLabel}
      </span>
    </div>
  </div>
);

export const S05WriteOrder: React.FC = () => {
  const f = useCurrentFrame();
  const T = {
    title: [0, 16],
    left: [14, 34],
    right: [30, 50],
    stateL: [96, 118],
    stateR: [120, 142],
    ratio: [150, 190],
    why: [230, 262],
    talk: [300, 330],
  };

  const shake = f >= T.stateL[1] && f < T.stateL[1] + 14
    ? Math.sin(f * 2.4) * 3 * (1 - span(f, T.stateL[1], T.stateL[1] + 14))
    : 0;

  return (
    <AbsoluteFill style={{ fontFamily: FONT_CN }}>
      <Backdrop shift={f} />
      <Title
        kicker="S05 / 实战 · 一致性"
        text="先更库再删缓存：窗口差在哪"
        sub="同一次并发的 5 步交错，两种顺序留下的脏窗口宽度不同"
        style={{ opacity: span(f, T.title[0], T.title[1]) }}
      />

      {/* 抖动只在 T.stateL[1] 之后十几帧发生，其余时间不挂 transform：
          常驻的 translateX(0) 会让整幅多出一层无谓的合成层 */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: '100%',
          height: '100%',
          ...(shake !== 0 ? { transform: `translateX(${shake}px)` } : null),
        }}
      >
        <Panel
          x={56}
          title="A · 先删缓存 → 再更库"
          tone={C.coral}
          steps={LEFT}
          p0={T.left[1]}
          f={f}
          ratio={0.6}
          ratioLabel="6/10 · 60%"
          state={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontFamily: FONT_MONO, fontSize: 12.5, color: C.slate }}>
                cache = <b style={{ color: C.coral }}>OLD</b>
              </span>
              <span style={{ fontFamily: FONT_MONO, fontSize: 12.5, color: C.slate }}>
                db = <b style={{ color: C.mint }}>NEW</b>
              </span>
              <span
                style={{
                  fontFamily: FONT_CN,
                  fontSize: 12,
                  fontWeight: 500,
                  color: C.coral,
                  marginLeft: 2,
                  opacity: span(f, T.stateL[0], T.stateL[1]),
                }}
              >
                长期不一致
              </span>
            </div>
          }
        />

        <Panel
          x={664}
          title="B · 先更库 → 再删缓存"
          tone={C.mint}
          steps={RIGHT}
          p0={T.right[1]}
          f={f}
          ratio={0.1}
          ratioLabel="1/10 · 10%"
          state={
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontFamily: FONT_MONO, fontSize: 12.5, color: C.slate }}>
                cache = <b style={{ color: C.mute }}>∅（已删）</b>
              </span>
              <span style={{ fontFamily: FONT_CN, fontSize: 12, color: C.mute }}>
                下次读回填 NEW
              </span>
              <span
                style={{
                  fontFamily: FONT_CN,
                  fontSize: 12,
                  fontWeight: 500,
                  color: C.mint,
                  marginLeft: 2,
                  opacity: span(f, T.stateR[0], T.stateR[1]),
                }}
              >
                10 种里仅 1 种会留旧值
              </span>
            </div>
          }
        />
      </div>

      {/* 关键结论：两种都不是强一致 */}
      <div
        style={{
          position: 'absolute',
          left: 56,
          top: 574,
          width: 1168,
          opacity: span(f, T.why[0], T.why[1]),
          transform: `translateY(${(1 - span(f, T.why[0], T.why[1])) * 8}px)`,
          ...glass({
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            background: 'rgba(255,255,255,0.72)',
          }),
        }}
      >
        <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: C.iceDeep, fontWeight: 700 }}>
          注意
        </span>
        <span style={{ fontSize: 12.5, color: C.slate, lineHeight: 1.5 }}>
          10% 不是「零」：两种顺序都只做到最终一致。写时<span style={{ color: C.coral }}>删</span>缓存而非
          <span style={{ color: C.coral }}>更新</span>缓存，是因为并发写会互相覆盖、聚合值还要重算；
          真要强一致，只能串行化或订阅 binlog。
        </span>
      </div>

      <div style={{ position: 'absolute', left: 56, top: 636, opacity: span(f, T.talk[0], T.talk[1]) }}>
        <Kaimao
          quote="先删缓存那一下，刚好给了读线程把旧值写回去的机会喵。"
          style={{ position: 'relative' }}
          size={0.9}
        />
      </div>
    </AbsoluteFill>
  );
};
