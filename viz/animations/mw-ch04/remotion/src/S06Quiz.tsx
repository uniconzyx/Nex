import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { Backdrop, Chip, Kaimao, Title } from './components';
import { C, FONT_CN, FONT_MONO, easeOut, glass, span } from './theme';

/**
 * S06 · 试题：三连 BOSS 战
 *
 * 三道题全部取自 content/middleware/mw-ch04/exercises.json（答案均为 B），
 * 但考的不是名词，而是三个方向性判断：
 *   Q1 布隆的「假阳性方向」     —— 概念/01 §①
 *   Q2 击穿与雪崩的「粒度分界」 —— 概念/02 §①
 *   Q3 代码找茬：少一行 return  —— 概念/01 §②（空值/布隆兜底缺失的后果）
 */

type Q = {
  ask: string;
  code?: string[];
  opts: { k: string; t: string }[];
  correct: string;
  why: string;
  src: string;
};

const QS: Q[] = [
  {
    ask: '关于缓存穿透与布隆过滤器，下列说法正确的是？',
    opts: [
      { k: 'A', t: '布隆判「存在」就可直接返回，不必再查库' },
      { k: 'B', t: '判「不存在」一定不存在；判「存在」可能不存在' },
      { k: 'C', t: '标准布隆支持直接删除元素' },
      { k: 'D', t: '有了布隆，空值缓存就完全没意义' },
    ],
    correct: 'B',
    why: '位由多个元素共享 → 无假阴性、有假阳性；删除要换 Counting Bloom。',
    src: 'concept/01 §①',
  },
  {
    ask: '击穿和雪崩的分界到底在哪？',
    opts: [
      { k: 'A', t: '两者都是「大量 key 同时失效」' },
      { k: 'B', t: '击穿=单个热点 key 失效；雪崩=大批 key 集体失效' },
      { k: 'C', t: '雪崩只能靠加锁解决，与 TTL 无关' },
      { k: 'D', t: '逻辑过期只能用在雪崩场景' },
    ],
    correct: 'B',
    why: '粒度不同 → 解法不同：单飞/逻辑过期 vs TTL 打散/多级/熔断。',
    src: 'concept/02 §①',
  },
  {
    ask: '这段代码少了「return」，会退化成哪种问题？',
    code: [
      'if ok, _ := bloom.Exists(key); !ok {',
      '    // 这里少了 return ErrNotFound',
      '}',
      'v, _ := cache.Get(key)   // 非法 key 继续往下走',
    ],
    opts: [
      { k: 'A', t: '没影响，布隆只是可选优化' },
      { k: 'B', t: '穿透：非法 key 仍然全部落到 DB' },
      { k: 'C', t: '击穿：单个热点 key 失效' },
      { k: 'D', t: '雪崩：大量 key 同时过期' },
    ],
    correct: 'B',
    why: '拦了却不返回 = 白拦；布隆的价值全在「判定不存在就直接短路」。',
    src: 'concept/01 §②',
  },
];

/* Q1 起 20 帧，之后每题 138 帧 */
const START = [20, 158, 296];
const LEN = 138;
const SELECT_AT = 62; // 题内相对帧：光标落到 B
const HIT_AT = 74; // 激光命中

const Monster: React.FC<{ hp: number; hitAge: number }> = ({ hp, hitAge }) => {
  const flash = hitAge >= 0 && hitAge < 12 ? 1 - hitAge / 12 : 0;
  const shrink = 1 - (3 - hp) * 0.06;
  const shake = hitAge >= 0 && hitAge < 10 ? Math.sin(hitAge * 2.2) * 4 : 0;
  const dead = hp <= 0;
  const body = dead ? '#B9C7D2' : C.ice;
  return (
    <svg
      width="224"
      height="197"
      viewBox="0 0 150 132"
      style={{
        transform: `translateX(${shake}px) scale(${shrink})`,
        filter: flash > 0 ? `drop-shadow(0 0 ${18 * flash}px rgba(93,180,229,0.9))` : 'none',
        opacity: dead ? 0.55 : 1,
      }}
    >
      {/* 三层棱锥：血量以「层」为单位掉 */}
      {[0, 1, 2].map((i) => {
        const on = hp > i;
        const pts = `${75 - 52 + i * 8},${112 - i * 30} ${75 + 52 - i * 8},${112 - i * 30} ${75},${112 - i * 30 - 34}`;
        return (
          <polygon
            key={i}
            points={pts}
            fill={on ? body : 'rgba(185,199,210,0.28)'}
            stroke="rgba(43,62,80,0.14)"
            strokeWidth="1"
            opacity={on ? 0.9 - i * 0.12 : 0.4}
          />
        );
      })}
      {/* 眼睛 */}
      {!dead ? (
        <>
          <circle cx="67" cy="96" r="4.2" fill={C.slate} />
          <circle cx="83" cy="96" r="4.2" fill={C.slate} />
          <path d="M70 105 Q75 109 80 105" stroke={C.slate} strokeWidth="2" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <path d="M63 92 l7 7 M70 92 l-7 7" stroke={C.slate} strokeWidth="2" strokeLinecap="round" />
          <path d="M80 92 l7 7 M87 92 l-7 7" stroke={C.slate} strokeWidth="2" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
};

export const S06Quiz: React.FC = () => {
  const f = useCurrentFrame();

  const qi = Math.min(2, Math.max(0, START.filter((s) => f >= s).length - 1));
  const q = QS[qi];
  const start = START[qi];
  const local = f - start;

  const resolved = START.filter((s) => f >= s + HIT_AT).length;
  const hp = Math.max(0, 3 - resolved);
  const hitAge = local >= HIT_AT ? local - HIT_AT : -1;

  const selected = local >= SELECT_AT;
  const laserT = span(local, HIT_AT - 4, HIT_AT + 6);
  const cardIn = easeOut(span(local, 0, 12));
  const optIn = (i: number) => easeOut(span(local, 8 + i * 3, 22 + i * 3));
  // 选项改成 flex 流后行高不再固定，B（右列第一行）的纵向位置按有无代码块估算
  const beamY = q.code ? 446 : 386;

  return (
    <AbsoluteFill style={{ fontFamily: FONT_CN }}>
      <Backdrop shift={f} />

      <Title kicker="S06 / 试题 · BOSS 战" text="三连问：答错就掉碎片" sub={`第 ${qi + 1} / 3 题`} />

      {/* 怪物 + 血条：右列整列垂直居中，别缩在角落 */}
      <div
        style={{
          position: 'absolute',
          left: 950,
          top: 108,
          width: 320,
          height: 420,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginBottom: 10 }}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                width: 66,
                height: 9,
                borderRadius: 9,
                background: i < hp ? C.coral : 'rgba(93,113,131,0.16)',
                transition: 'background .2s',
              }}
            />
          ))}
        </div>
        <Monster hp={hp} hitAge={hitAge} />
        <div
          style={{
            textAlign: 'center',
            fontFamily: FONT_MONO,
            fontSize: 13,
            color: C.mute,
            marginTop: 6,
          }}
        >
          HP {hp}/3
        </div>
      </div>

      {/* 正文列：题干 / 选项 / 解析 走一条 flex 流，整体垂直居中；不再各自绝对定位 */}
      <div
        style={{
          position: 'absolute',
          left: 56,
          top: 150,
          width: 880,
          height: 410,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 16,
        }}
      >
      {/* 题干卡 */}
      <div
        style={{
          opacity: cardIn,
          transform: `translateY(${(1 - cardIn) * 14}px)`,
          ...glass({ padding: '14px 16px' }),
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 6 }}>
          <Chip text={`Q${qi + 1}`} color={C.ice} size={11} mono />
          <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: C.mute }}>{q.src}</span>
          {local >= HIT_AT && (
            <Chip text="答对" color={C.mint} size={10.5} style={{ marginLeft: 'auto' }} />
          )}
        </div>
        <div style={{ fontSize: 17, fontWeight: 500, color: C.slate, lineHeight: 1.45 }}>{q.ask}</div>

        {q.code && (
          <div
            style={{
              marginTop: 9,
              background: 'rgba(32,48,63,0.94)',
              borderRadius: 10,
              padding: '9px 12px',
              fontFamily: FONT_MONO,
              fontSize: 12.5,
              lineHeight: 1.65,
              color: '#DBE9F4',
            }}
          >
            {q.code.map((ln, i) => (
              <div key={i} style={{ whiteSpace: 'pre' }}>
                {i === 1 ? (
                  <span style={{ color: C.coral, fontWeight: 500 }}>{ln}</span>
                ) : (
                  ln
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 选项 */}
      <div
        style={{
          width: '100%',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 12,
        }}
      >
        {q.opts.map((o, i) => {
          const isSel = selected && o.k === q.correct;
          const wrongSel = selected && o.k !== q.correct; // 只有 B 被选中，其余变暗
          return (
            <div
              key={o.k}
              style={{
                ...glass({
                  padding: '12px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  background: isSel ? 'rgba(49,208,170,0.16)' : 'rgba(255,255,255,0.62)',
                  border: isSel ? '1px solid rgba(49,208,170,0.55)' : '1px solid rgba(255,255,255,0.75)',
                  opacity: optIn(i) * (wrongSel ? 0.55 : 1),
                  transform: `translateY(${(1 - optIn(i)) * 10}px)`,
                }),
              }}
            >
              <span
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: 7,
                  display: 'grid',
                  placeItems: 'center',
                  fontFamily: FONT_MONO,
                  fontSize: 12,
                  fontWeight: 700,
                  color: isSel ? '#fff' : C.mute,
                  background: isSel ? C.mint : 'rgba(93,113,131,0.10)',
                  flex: '0 0 auto',
                }}
              >
                {o.k}
              </span>
              <span style={{ fontSize: 13.5, color: C.slate, lineHeight: 1.45 }}>{o.t}</span>
            </div>
          );
        })}
      </div>

      {/* 激光：从选中项射向怪物 */}
      {laserT > 0 && laserT < 1 && (
        <svg style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} width={1280} height={720}>
          <defs>
            <linearGradient id="beam" x1="0" x2="1">
              <stop offset="0%" stopColor={C.ice} stopOpacity="0.15" />
              <stop offset="100%" stopColor={C.ice} stopOpacity="0.95" />
            </linearGradient>
          </defs>
          <line
            x1={520}
            y1={beamY}
            x2={520 + (1080 - 520) * laserT}
            y2={beamY + (300 - beamY) * laserT}
            stroke="url(#beam)"
            strokeWidth={7}
            strokeLinecap="round"
            opacity={0.85}
          />
        </svg>
      )}

      {/* 解析：答对后出现 */}
      <div
        style={{
          width: '100%',
          opacity: span(local, HIT_AT + 6, HIT_AT + 22),
          ...glass({
            padding: '9px 13px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            background: 'rgba(49,208,170,0.12)',
            border: '1px solid rgba(49,208,170,0.35)',
          }),
        }}
      >
        <span style={{ fontFamily: FONT_MONO, fontSize: 12, fontWeight: 700, color: C.mint }}>
          {q.correct}
        </span>
        <span style={{ fontSize: 12.5, color: C.slate, lineHeight: 1.5 }}>{q.why}</span>
      </div>
      </div>

      {/* 通关 */}
      {hp === 0 && (
        <div
          style={{
            position: 'absolute',
            left: 1052,
            top: 448,
            opacity: span(f, START[2] + HIT_AT, START[2] + HIT_AT + 14),
            ...glass({
              padding: '7px 12px',
              background: 'rgba(49,208,170,0.18)',
              border: '1px solid rgba(49,208,170,0.5)',
            }),
          }}
        >
          <span style={{ fontFamily: FONT_MONO, fontSize: 13, fontWeight: 700, color: C.mint }}>
            3/3 PASS
          </span>
        </div>
      )}

      <div style={{ position: 'absolute', left: 936, top: 566, opacity: span(f, START[2] + HIT_AT, START[2] + HIT_AT + 16) }}>
        <Kaimao quote="三题都答 B，但三个 B 说的不是一回事哦喵。" style={{ position: 'relative' }} size={0.82} />
      </div>
    </AbsoluteFill>
  );
};
