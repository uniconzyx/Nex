import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { Backdrop, Kaimao } from './components';
import { C, FONT_CN, FONT_MONO, easeOut, glass, span } from './theme';

/**
 * S07 · 收束：一页速查卡
 * 强制用「问题 → 解法 → 代价」三列：只背解法不背代价，面试一追问就露。
 */
const ROWS = [
  { p: '穿透', s: '布隆过滤器 / 空值缓存', c: '假阳性仍在 → 必须能处理「查无此物」', tone: C.coral },
  { p: '击穿', s: '单飞 / 逻辑过期', c: '等待抬高 RT；逻辑过期会返回旧值', tone: C.ice },
  { p: '雪崩', s: 'TTL 抖动 / 多级 / 熔断', c: 'TTL 差异大 → 同批数据新鲜度分裂', tone: C.amber },
];

export const S07Recap: React.FC = () => {
  const f = useCurrentFrame();
  const head = easeOut(span(f, 0, 14));

  return (
    <AbsoluteFill style={{ fontFamily: FONT_CN }}>
      <Backdrop shift={f} />

      <div style={{ position: 'absolute', left: 72, top: 60, opacity: head }}>
        <div style={{ fontFamily: FONT_MONO, fontSize: 12.5, color: C.iceDeep, letterSpacing: 1.4 }}>
          S07 / RECAP
        </div>
        <div style={{ fontSize: 30, fontWeight: 700, color: C.slate, marginTop: 6 }}>
          缓存三大问题 · 三行记住
        </div>
      </div>

      {/* 表头 */}
      <div
        style={{
          position: 'absolute',
          left: 72,
          top: 160,
          width: 1136,
          display: 'grid',
          gridTemplateColumns: '120px 1fr 1fr',
          gap: 10,
          opacity: head,
        }}
      >
        {['问题', '解法', '代价（面试加分点）'].map((t) => (
          <div key={t} style={{ fontFamily: FONT_CN, fontSize: 12.5, color: C.mute }}>
            {t}
          </div>
        ))}
      </div>

      {ROWS.map((r, i) => {
        const p = easeOut(span(f, 12 + i * 12, 30 + i * 12));
        return (
          <div
            key={r.p}
            style={{
              position: 'absolute',
              left: 72,
              top: 192 + i * 108,
              width: 1136,
              display: 'grid',
              gridTemplateColumns: '120px 1fr 1fr',
              gap: 10,
              alignItems: 'center',
              opacity: p,
              transform: `translateY(${(1 - p) * 12}px)`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 4, height: 30, borderRadius: 4, background: r.tone }} />
              <span style={{ fontSize: 19, fontWeight: 600, color: C.slate }}>{r.p}</span>
            </div>
            <div style={{ ...glass({ padding: '11px 13px', fontSize: 14, color: C.slate }) }}>{r.s}</div>
            <div
              style={{
                ...glass({
                  padding: '11px 13px',
                  fontSize: 13,
                  color: C.mute,
                  lineHeight: 1.45,
                  background: 'rgba(255,255,255,0.5)',
                }),
              }}
            >
              {r.c}
            </div>
          </div>
        );
      })}

      {/* 一致性那一行单独说，因为它是「写路径」不是「失效」 */}
      <div
        style={{
          position: 'absolute',
          left: 72,
          top: 530,
          width: 1136,
          opacity: easeOut(span(f, 52, 70)),
          ...glass({ padding: '11px 14px', display: 'flex', alignItems: 'center', gap: 10 }),
        }}
      >
        <span style={{ fontFamily: FONT_MONO, fontSize: 12, fontWeight: 700, color: C.iceDeep }}>
          写路径
        </span>
        <span style={{ fontSize: 13, color: C.slate }}>
          先更库再删缓存：脏交错从 7/10 降到 5/10 —— 变窄，但<b>不是零</b>；强一致要串行化或 binlog 订阅。
        </span>
      </div>

      {/* 盖章 */}
      <div
        style={{
          position: 'absolute',
          right: 92,
          top: 44,
          opacity: easeOut(span(f, 72, 86)),
          transform: `scale(${0.86 + 0.14 * easeOut(span(f, 72, 86))}) rotate(-6deg)`,
          border: `2px solid ${C.mint}`,
          borderRadius: 10,
          padding: '7px 14px',
          fontFamily: FONT_MONO,
          fontSize: 15,
          fontWeight: 700,
          color: C.mint,
          letterSpacing: 2,
        }}
      >
        mw-ch04 · CLEARED
      </div>

      <div style={{ position: 'absolute', left: 72, top: 610, opacity: easeOut(span(f, 84, 100)) }}>
        <Kaimao quote="记住这张表，明天面试就问这个喵。" style={{ position: 'relative' }} size={0.86} />
      </div>
    </AbsoluteFill>
  );
};
