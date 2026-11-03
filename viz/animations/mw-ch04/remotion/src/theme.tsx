import { CSSProperties } from 'react';
import { staticFile } from 'remotion';
import { useEffect } from 'react';

/* ── 色板：与 API 端 viz/index.html、Manim style.py 同一套 ───────────── */
export const C = {
  bgTop: '#EBF4FA',
  bgBottom: '#F9FBFD',
  ice: '#5DB4E5',
  iceDeep: '#3E93C7',
  iceSoft: '#BFE1F3',
  slate: '#2B3E50',
  mute: '#5D7183',
  mint: '#31D0AA',
  coral: '#F87171',
  amber: '#E8A33D',
  glass: 'rgba(255,255,255,0.62)',
  glassStrong: 'rgba(255,255,255,0.82)',
};

export const FONT_CN =
  '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", system-ui, sans-serif';
export const FONT_MONO = '"JetBrains Mono", "Cascadia Mono", Consolas, monospace';

export const FONT_CSS = `
@font-face {
  font-family: 'JetBrains Mono';
  src: url('${staticFile('fonts/JetBrainsMono-Regular.ttf')}') format('truetype');
  font-weight: 400;
  font-style: normal;
}
@font-face {
  font-family: 'JetBrains Mono';
  src: url('${staticFile('fonts/JetBrainsMono-Medium.ttf')}') format('truetype');
  font-weight: 500;
  font-style: normal;
}
@font-face {
  font-family: 'JetBrains Mono';
  src: url('${staticFile('fonts/JetBrainsMono-Bold.ttf')}') format('truetype');
  font-weight: 700;
  font-style: normal;
}
`;

/**
 * 等字体真正可用再出第一帧。
 * 不做这一步，前几帧会用 Consolas 渲染，等宽与中文宽度全变，文字会跳一下。
 */
export const FontGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 只负责触发本地字体加载，绝不用 delayRender 门控：无头渲染里 delayRender 的
  // 释放时机与逐帧渲染非确定，极易挂死（首帧 30s 超时）。字体通常在前几帧内就绪，
  // 极少量首帧字形回退可接受，比整条渲染失败强。
  useEffect(() => {
    if (typeof document !== 'undefined' && document.fonts) {
      Promise.all([
        document.fonts.load('400 16px "JetBrains Mono"'),
        document.fonts.load('700 16px "JetBrains Mono"'),
      ]).catch(() => {});
    }
  }, []);

  return (
    <>
      <style>{FONT_CSS}</style>
      {children}
    </>
  );
};

/* ── 液态玻璃 ─────────────────────────────────────────────────────────
   注意：无头 Edge 软渲染下 backdrop-filter:blur() 对大面积元素极慢，会让
   页面在合成阶段卡死（整段渲染 30s 超时）。这里用「更不透明的半透明白卡 +
   细边 + 柔和投影」模拟玻璃感，去掉真实模糊，保证可稳定出帧。 */
export const glass = (extra: CSSProperties = {}): CSSProperties => ({
  background: 'rgba(255,255,255,0.78)',
  borderRadius: 14,
  border: '1px solid rgba(255,255,255,0.85)',
  boxShadow: '0 18px 44px rgba(43,62,80,0.12), 0 2px 6px rgba(43,62,80,0.06)',
  ...extra,
});

export const glassDark = (extra: CSSProperties = {}): CSSProperties => ({
  background: 'rgba(22,36,50,0.92)',
  borderRadius: 14,
  border: '1px solid rgba(255,255,255,0.12)',
  boxShadow: '0 18px 44px rgba(15,26,38,0.30)',
  ...extra,
});

/* ── 通用小工具 ─────────────────────────────────────────────────────── */
export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** 把 [a,b] 区间映射到 0..1，超出即夹紧；用来给每个元素算各自的入场进度 */
export const span = (f: number, a: number, b: number) => clamp01((f - a) / Math.max(1, b - a));

export const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
