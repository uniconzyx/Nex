import React from 'react';
import { useEffect, useRef } from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { Backdrop, Chip, CodeBlock, Kaimao, Title } from './components';
import { C, FONT_CN, FONT_MONO, easeOut, glass, glassDark, span } from './theme';

/**
 * S03 · 实战：热点 key 过期的那一瞬间
 *
 * 深度落点（对应分镜表）：
 *  ① singleflight 的语义是「同 key 同刻只允许一个在途回源，其余等待并复用同一份结果」，
 *    不是「加锁串行」——排队者不会各自再查一次库；
 *  ② 被挡住的那 199 个请求付出的是「等待」而不是「正确性」，所以锁/单飞都要有超时；
 *  ③ 回源后要双检缓存再写，否则后到的请求会用旧值覆盖刚写好的新值。
 *
 * 数据来源：content/middleware/mw-ch04/examples/ex05-singleflight.json（结论），
 * 并发数按 200 画（ex04/ex05 的顺序模拟无法复现并发，分镜已说明按正确语义重画）。
 */

const CODE = [
  'func GetUser(ctx context.Context, id int64) (*User, error) {',
  '\tkey := fmt.Sprintf("user:%d", id)',
  '',
  '\tif v, ok := cache.Get(key); ok {',
  '\t\treturn v.(*User), nil          // 命中：直接返回',
  '\t}',
  '',
  '\tv, err := sf.Do(key, func() (any, error) {',
  '\t\tu, err := db.QueryUser(ctx, id)  // 回源只发生一次',
  '\t\tif err != nil { return nil, err }',
  '\t\tcache.Set(key, u, 5*time.Minute)',
  '\t\treturn u, nil',
  '\t})',
  '\tif err != nil { return nil, err }',
  '\treturn v.(*User), nil',
  '}',
];

// 每行字符数累加，用来把「全局已敲字数」摊到各行
const OFFSETS = CODE.reduce<number[]>((acc, ln, i) => {
  acc.push(i === 0 ? 0 : acc[i - 1] + CODE[i - 1].length);
  return acc;
}, []);
const TOTAL_CHARS = CODE.reduce((a, l) => a + l.length, 0);

/* ── 200 并发请求点阵：用单个 canvas 画，避免 200 个 React span 在软渲染下卡死 ── */
const DOT_COLS = 20;
const DOT_N = 200;
const DOT_CELL = 11;
const DOT_GAP = 4.5;
const DOT_W = DOT_COLS * DOT_CELL + (DOT_COLS - 1) * DOT_GAP;
const DOT_ROWS = Math.ceil(DOT_N / DOT_COLS);
const DOT_H = DOT_ROWS * DOT_CELL + (DOT_ROWS - 1) * DOT_GAP;

const dotRoundRect = (ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) => {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
};

const DotField: React.FC<{ f: number; T: Record<string, number[]> }> = ({ f, T }) => {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    const dpr = 2;
    cv.width = DOT_W * dpr;
    cv.height = DOT_H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, DOT_W, DOT_H);

    const waiting = f >= T.pass[0] ? span(f, T.pass[0], T.pass[1] - 8) : 0;
    const pulse = 1 + 0.25 * Math.sin(f / 6);

    for (let i = 0; i < DOT_N; i++) {
      const col = i % DOT_COLS;
      const row = Math.floor(i / DOT_COLS);
      const x = col * (DOT_CELL + DOT_GAP);
      const y = row * (DOT_CELL + DOT_GAP);
      const wave = span(f, T.stampede[0] + i * 0.18, T.stampede[0] + i * 0.18 + 12);
      const arrived = f < T.pass[0] ? wave : 0;
      const isLeader = i === 0 && f >= T.pass[0];

      let r = 203, g = 214, b = 226, a = 0.30 + 0.62 * arrived;
      if (waiting > 0) {
        r = 93; g = 180; b = 229; a = 0.30 + 0.40 * (1 - waiting);
      } else {
        r = 203 + 45 * arrived; g = 214 - 101 * arrived; b = 226 - 113 * arrived;
      }

      const sz = isLeader ? DOT_CELL * pulse : DOT_CELL;
      const off = (DOT_CELL - sz) / 2;
      if (isLeader) {
        ctx.fillStyle = C.coral;
        dotRoundRect(ctx, x + off, y + off, sz, sz, 3);
        ctx.fill();
        ctx.strokeStyle = 'rgba(248,113,113,0.35)';
        ctx.lineWidth = 2;
        ctx.stroke();
      } else {
        ctx.fillStyle = `rgba(${Math.round(r)},${Math.round(g)},${Math.round(b)},${a})`;
        dotRoundRect(ctx, x, y, DOT_CELL, DOT_CELL, 3);
        ctx.fill();
      }
    }
  }, [f, T]);
  return <canvas ref={ref} style={{ width: DOT_W, height: DOT_H, display: 'block', marginTop: 7 }} />;
};

const N = 200;

export const S03Breakdown: React.FC = () => {
  const f = useCurrentFrame();

  /* ── 阶段边界（帧） ─────────────────────────────────────────── */
  const T = {
    title: [0, 18],
    ide: [8, 40],
    type: [22, 168],
    panel: [40, 74],
    expire: [78, 104],
    stampede: [104, 168],
    banner: [168, 198],
    focus: [200, 236],
    gate: [244, 276],
    pass: [286, 336],
    badge: [336, 378],
    talk: [382, 424],
  };

  // 不逐字打字：每帧都渲染完整代码，避免 80+ span 逐帧 Reconcile 在无头软渲染下把单帧成本推过临界
  // （之前逐字 typing 在 f≈80 触发确定性渲染卡死）。代码随卡片淡入即可。
  const typed = TOTAL_CHARS;
  const focusAmount = span(f, T.focus[0], T.focus[1]);
  const expired = f >= T.expire[0] + 8;

  const ideIn = easeOut(span(f, T.ide[0], T.ide[1]));
  const panelIn = easeOut(span(f, T.panel[0], T.panel[1]));

  // 无保护：0 → 200；单飞：重置为 0，只放 1 个
  const rampA = easeOut(span(f, T.stampede[0] + 6, T.stampede[1]));
  const rampB = easeOut(span(f, T.pass[0] + 10, T.pass[1]));
  const dbCount = f < T.pass[0] ? Math.round(N * rampA) : Math.round(1 * rampB);

  const gateIn = easeOut(span(f, T.gate[0], T.gate[1]));
  const leaderProgress = span(f, T.pass[0], T.pass[1] - 8);

  const badPulse = 1 - Math.abs(Math.sin(((f - T.banner[0]) / 22) * Math.PI)) * 0.5;

  return (
    <AbsoluteFill style={{ fontFamily: FONT_CN }}>
      <Backdrop />

      <Title
        kicker="S03 / 实战 · 击穿"
        text="热点 key 过期的那 3 秒"
        sub="同一个 key，200 个并发请求；单飞把回源压成 1 次"
        style={{ opacity: span(f, T.title[0], T.title[1]) }}
      />

      {/* ── 左：IDE ──────────────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          left: 56,
          top: 118,
          width: 700,
          height: 486,
          transform: `translateX(${(1 - ideIn) * -36}px)`,
          opacity: ideIn,
          ...glassDark({ borderRadius: 16, padding: 0, overflow: 'hidden' }),
        }}
      >
        {/* 标题栏 */}
        <div
          style={{
            height: 34,
            display: 'flex',
            alignItems: 'center',
            gap: 7,
            padding: '0 14px',
            background: 'rgba(255,255,255,0.06)',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          {['#F87171', '#E8C33D', '#31D0AA'].map((c) => (
            <span key={c} style={{ width: 9, height: 9, borderRadius: 9, background: c, opacity: 0.85 }} />
          ))}
          <span
            style={{
              marginLeft: 8,
              fontFamily: FONT_MONO,
              fontSize: 12,
              color: 'rgba(219,233,244,0.72)',
            }}
          >
            internal/user/service.go
          </span>
          <span
            style={{
              marginLeft: 'auto',
              fontFamily: FONT_MONO,
              fontSize: 11,
              color: 'rgba(219,233,244,0.45)',
            }}
          >
            go 1.22
          </span>
        </div>

        <CodeBlock
          lines={CODE}
          typed={typed}
          width={700}
          height={452}
          fontSize={14.5}
          lineHeight={26}
          theme="dark"
          focus={[7, 8, 10]}
          focusAmount={focusAmount}
          showCursor={false}
        />
      </div>

      {/* ── 右：缓存 / 200 并发 / 数据库 ─────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          left: 796,
          top: 118,
          width: 428,
          height: 486,
          opacity: panelIn,
          transform: `translateY(${(1 - panelIn) * 16}px)`,
        }}
      >
        {/* 缓存卡 */}
        <div style={{ ...glass({ padding: '11px 13px' }), display: 'flex', alignItems: 'center', gap: 9 }}>
          <span style={{ fontFamily: FONT_MONO, fontSize: 13, color: C.mute }}>cache</span>
          <span style={{ fontFamily: FONT_MONO, fontSize: 13.5, color: C.slate, fontWeight: 500 }}>
            user:42
          </span>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 7 }}>
            <span
              style={{
                fontFamily: FONT_MONO,
                fontSize: 11.5,
                color: expired ? C.coral : C.mint,
                opacity: 0.9,
              }}
            >
              TTL {expired ? '0s' : '3s'}
            </span>
            <Chip
              text={expired ? 'EXPIRED' : 'HIT'}
              color={expired ? C.coral : C.mint}
              size={11.5}
              mono
            />
          </div>
        </div>

        {/* TTL 条：过期瞬间要能看见「归零」 */}
        <div style={{ height: 3, margin: '6px 2px 0', background: 'rgba(93,113,131,0.16)', borderRadius: 3 }}>
          <div
            style={{
              height: 3,
              borderRadius: 3,
              width: `${interpolate(f, [T.panel[1], T.expire[0]], [100, 0], { extrapolateRight: 'clamp' })}%`,
              background: expired ? C.coral : C.ice,
              transition: 'background .2s',
            }}
          />
        </div>

        {/* 200 个并发请求 */}
        <div style={{ marginTop: 12, display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontSize: 13, color: C.slate, fontWeight: 500 }}>
            {f < T.pass[0] ? '200 个并发请求' : '199 个等待复用'}
          </span>
          <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: C.mute }}>同一 key</span>
        </div>

        <DotField f={f} T={T} />

        {/* 闸门：singleflight */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 292,
            opacity: gateIn,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <div style={{ flex: 1, height: 2, background: `rgba(49,208,170,${0.5 * gateIn})` }} />
          <Chip
            text="singleflight · 仅 1 个在途"
            color={`rgba(49,208,170,${0.16 * gateIn})`}
            fg="#0F7F66"
            size={11}
            mono
            style={{ border: `1px solid rgba(49,208,170,${0.45 * gateIn})` }}
          />
          <div style={{ flex: 1, height: 2, background: `rgba(49,208,170,${0.5 * gateIn})` }} />
        </div>

        {/* 领头请求穿过闸门 */}
        {f >= T.pass[0] && leaderProgress < 1 && (
          <span
            style={{
              position: 'absolute',
              left: 6,
              top: 236 + leaderProgress * 96,
              width: 11,
              height: 11,
              borderRadius: 3,
              background: C.coral,
              boxShadow: '0 0 12px rgba(248,113,113,0.6)',
            }}
          />
        )}

        {/* 数据库卡 */}
        <div
          style={{
            ...glass({
              position: 'absolute',
              left: 0,
              right: 0,
              top: 330,
              padding: '12px 14px',
              border: `1px solid ${
                f >= T.banner[0] && f < T.pass[0]
                  ? `rgba(248,113,113,${0.25 + 0.5 * badPulse})`
                  : f >= T.pass[0]
                    ? 'rgba(49,208,170,0.55)'
                    : 'rgba(255,255,255,0.75)'
              }`,
            }),
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span style={{ fontFamily: FONT_MONO, fontSize: 12.5, color: C.mute }}>db.query</span>
            <span
              style={{
                marginLeft: 'auto',
                fontFamily: FONT_CN,
                fontSize: 12,
                color: f >= T.pass[0] ? C.mint : f >= T.stampede[0] ? C.coral : C.mute,
              }}
            >
              {f >= T.pass[0] ? '只剩 1 次' : f >= T.stampede[0] ? '并发回源中' : '待命中'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, marginTop: 2 }}>
            <span
              style={{
                fontFamily: FONT_MONO,
                fontSize: 44,
                fontWeight: 700,
                lineHeight: 1.05,
                color: f >= T.pass[0] ? C.mint : f >= T.stampede[0] ? C.coral : C.slate,
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {String(dbCount).padStart(3, '0')}
            </span>
            <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: C.mute, marginBottom: 7 }}>
              {f >= T.pass[0] ? '次 / 200 请求' : '次 / 200 请求'}
            </span>
          </div>
        </div>

        {/* 结论徽章 */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 434,
            opacity: span(f, T.badge[0], T.badge[1]),
            transform: `translateY(${(1 - span(f, T.badge[0], T.badge[1])) * 10}px)`,
            ...glass({
              padding: '9px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              background: 'rgba(49,208,170,0.14)',
              border: '1px solid rgba(49,208,170,0.45)',
            }),
          }}
        >
          <span style={{ fontFamily: FONT_MONO, fontSize: 15, fontWeight: 700, color: C.mint }}>
            200 → 1
          </span>
          <span style={{ fontSize: 12.5, color: C.slate, lineHeight: 1.45 }}>
            回源 −99.5%，199 个请求复用同一份结果（代价是等待，所以要设超时）
          </span>
        </div>
      </div>

      {/* 击穿告警：只在无保护阶段出现 */}
      {f >= T.banner[0] && f < T.pass[0] && (
        <div
          style={{
            position: 'absolute',
            left: 56,
            top: 616,
            width: 700,
            opacity: span(f, T.banner[0], T.banner[0] + 10),
            ...glass({
              padding: '10px 14px',
              background: 'rgba(248,113,113,0.14)',
              border: '1px solid rgba(248,113,113,0.42)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }),
          }}
        >
          <span style={{ fontFamily: FONT_MONO, fontSize: 13, fontWeight: 700, color: C.coral }}>
            MISS × 200
          </span>
          <span style={{ fontSize: 12.5, color: C.slate }}>
            缓存失效瞬间全部回源 —— 这就是击穿；加锁串行只会把 3 秒变成 30 秒
          </span>
        </div>
      )}

      {/* 凯喵 */}
      <div style={{ position: 'absolute', left: 56, top: 616, opacity: span(f, T.talk[0], T.talk[1]) }}>
        <Kaimao
          quote="注意看，这个热点 key 刚过期，200 个请求同时要回源了喵！"
          style={{ position: 'relative' }}
          size={0.94}
        />
      </div>
    </AbsoluteFill>
  );
};
