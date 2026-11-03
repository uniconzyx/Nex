import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C, FONT_CN, FONT_MONO, glass } from './theme';

/* ── 背景：冰蓝→奶白 + 两团柔光，避免大面积纯色板结 ─────────────────── */
export const Backdrop: React.FC<{ shift?: number }> = ({ shift = 0 }) => (
  <AbsoluteFill
    style={{
      background: `linear-gradient(178deg, ${C.bgTop} 0%, #F2F8FC 46%, ${C.bgBottom} 100%)`,
    }}
  >
    <div
      style={{
        position: 'absolute',
        width: 720,
        height: 720,
        left: -160 + shift * 0.25,
        top: -260,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(93,180,229,0.26), rgba(93,180,229,0) 66%)',
      }}
    />
    <div
      style={{
        position: 'absolute',
        width: 620,
        height: 620,
        right: -180 - shift * 0.18,
        bottom: -300,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(49,208,170,0.16), rgba(49,208,170,0) 68%)',
      }}
    />
  </AbsoluteFill>
);

/* ── 凯喵：几何拼出的 Q 版头像 + 台词气泡 ──────────────────────────── */
export const Kaimao: React.FC<{
  quote: string;
  style?: React.CSSProperties;
  size?: number;
  opacity?: number;
}> = ({ quote, style, size = 1, opacity = 1 }) => {
  const head = 46 * size;
  return (
    <div
      style={{
        position: 'absolute',
        display: 'flex',
        alignItems: 'flex-end',
        gap: 8 * size,
        opacity,
        ...style,
      }}
    >
      {/* 气泡 */}
      <div
        style={{
          ...glass({ borderRadius: 12 * size, padding: `${9 * size}px ${13 * size}px` }),
          fontFamily: FONT_CN,
          fontSize: 15 * size,
          lineHeight: 1.45,
          color: C.slate,
          maxWidth: 330 * size,
          position: 'relative',
        }}
      >
        {quote}
        <span
          style={{
            position: 'absolute',
            right: -6 * size,
            bottom: 12 * size,
            width: 12 * size,
            height: 12 * size,
            background: 'rgba(255,255,255,0.82)',
            transform: 'rotate(45deg)',
            borderRadius: 2,
          }}
        />
      </div>
      {/* 头像 */}
      <svg width={head} height={head} viewBox="0 0 46 46" style={{ flex: '0 0 auto' }}>
        <polygon points="13,13 10,2 20,9" fill={C.ice} />
        <polygon points="33,13 36,2 26,9" fill={C.ice} />
        <circle cx="23" cy="26" r="16" fill={C.ice} />
        <circle cx="17" cy="25" r="2.6" fill={C.slate} />
        <circle cx="29" cy="25" r="2.6" fill={C.slate} />
        <path d="M20 32 Q23 34.5 26 32" stroke={C.slate} strokeWidth="1.7" fill="none" strokeLinecap="round" />
      </svg>
    </div>
  );
};

/* ── 胶囊标签 ───────────────────────────────────────────────────────── */
export const Chip: React.FC<{
  text: string;
  color?: string;
  fg?: string;
  size?: number;
  mono?: boolean;
  style?: React.CSSProperties;
}> = ({ text, color = C.ice, fg = '#fff', size = 13, mono = false, style }) => {
  // 胶囊只装**短标签**（≤6 个汉字）。实测（像素量墨迹宽度）排版宽度是对的：
  // 12px 时 8 个汉字 96px、胶囊 113px，正好等于字宽 + 两侧 padding；
  // 但白字压在高饱和色底上、12px 时笔画会互相粘连，长中文放进去就糊。
  // 所以：状态说明这类长文本用「纯文字 + 语义色」或「色点 + 正文」，不要塞胶囊。
  // 另：display 用 inline-block + lineHeight 垂直居中，不用 inline-flex。
  const sz = Math.max(12, size);
  const h = sz * 1.9;
  return (
    <span
      style={{
        display: 'inline-block',
        height: h,
        lineHeight: `${h}px`,
        padding: `0 ${sz * 0.72}px`,
        borderRadius: sz,
        background: color,
        color: fg,
        fontFamily: mono ? FONT_MONO : FONT_CN,
        fontSize: sz,
        fontWeight: 500,
        letterSpacing: mono ? 0.2 : 'normal',
        whiteSpace: 'nowrap',
        flexShrink: 0,
        ...style,
      }}
    >
      {text}
    </span>
  );
};

/* ── 代码高亮：只做够用的四种 token，不引第三方语法器 ───────────────── */
type Tok = { t: string; c: string };
const KEYWORDS = new Set([
  'func', 'if', 'return', 'err', 'var', 'const', 'for', 'range', 'defer', 'go',
  'type', 'struct', 'interface', 'map', 'chan', 'select', 'case', 'switch',
]);

/* 两套色板：暗色底上用深灰蓝当正文 = 隐形，必须换亮字。 */
const PALETTE = {
  light: { plain: C.slate, comment: '#7C93A6', string: '#2F9E7A', keyword: '#B4703F', type: '#3E93C7' },
  dark: { plain: '#DCEAF6', comment: '#7E93A6', string: '#7FD3B4', keyword: '#F0B37E', type: '#8CC8EA' },
};

export const highlight = (line: string, theme: 'light' | 'dark' = 'light'): Tok[] => {
  const pal = PALETTE[theme];
  const out: Tok[] = [];
  const isWord = (c: string) => /[A-Za-z0-9_]/.test(c);
  let i = 0;
  while (i < line.length) {
    // ① 行注释：吃掉剩余整行
    if (line.startsWith('//', i)) {
      out.push({ t: line.slice(i), c: pal.comment });
      break;
    }
    const ch = line[i];
    // ② 字符串：支持反斜杠转义（用 charCode 判断，避免在源码里堆反斜杠）
    if (ch === '"') {
      let j = i + 1;
      while (j < line.length) {
        if (line.charCodeAt(j) === 92) j += 2;
        else if (line[j] === '"') { j += 1; break; }
        else j += 1;
      }
      out.push({ t: line.slice(i, j), c: pal.string });
      i = j;
      continue;
    }
    // ③ 标识符（含数字：数字必须在此被消费，否则会落入 ④ 且 isWord 含数字导致无法推进而无限循环）
    if (/[A-Za-z0-9_]/.test(ch)) {
      let j = i;
      while (j < line.length && isWord(line[j])) j += 1;
      const w = line.slice(i, j);
      out.push({ t: w, c: KEYWORDS.has(w) ? pal.keyword : /^[A-Z]/.test(w) ? pal.type : pal.plain });
      i = j;
      continue;
    }
    // ④ 其余（标点、空白）：连续同类字符并成一段，减少 span 数量
    let j = i;
    while (j < line.length && !isWord(line[j]) && line[j] !== '"' && !line.startsWith('//', j)) j += 1;
    out.push({ t: line.slice(i, j || i + 1), c: pal.plain });
    i = j || i + 1;
  }
  return out;
};

/* ── 代码块：逐字出现 + 行高亮 + 光标 ──────────────────────────────── */
export const CodeBlock: React.FC<{
  lines: string[];
  /** 全局已敲出的字符数（可为浮点，用于平滑推进） */
  typed: number;
  fontSize?: number;
  lineHeight?: number;
  width: number;
  height: number;
  /** 需要打光的行号（0 基） */
  focus?: number[];
  /** 打光强度 0..1 */
  focusAmount?: number;
  theme?: 'light' | 'dark';
  showCursor?: boolean;
}> = ({
  lines,
  typed,
  fontSize = 15,
  lineHeight = 25,
  width,
  height,
  focus = [],
  focusAmount = 0,
  theme = 'light',
  showCursor = true,
}) => {
  const dark = theme === 'dark';
  let budget = typed;
  const rendered = lines.map((ln) => {
    const n = Math.max(0, Math.min(ln.length, Math.ceil(budget)));
    budget -= ln.length;
    return ln.slice(0, n);
  });
  const cursorLine = Math.max(
    0,
    rendered.findIndex((r, i) => lines[i].length > r.length),
  );

  return (
    <div
      style={{
        width,
        height,
        padding: '10px 0',
        fontFamily: FONT_MONO,
        fontSize,
        lineHeight: `${lineHeight}px`,
        color: dark ? '#DBE9F4' : C.slate,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {rendered.map((txt, i) => {
        const isFocus = focus.includes(i);
        const dim = focus.length > 0 && !isFocus ? 1 - 0.42 * focusAmount : 1;
        return (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              height: lineHeight,
              paddingRight: 12,
              background: isFocus
                ? `rgba(49,208,170,${0.14 * focusAmount})`
                : 'transparent',
              borderLeft: isFocus
                ? `${2 * focusAmount}px solid rgba(49,208,170,${focusAmount})`
                : '2px solid transparent',
              opacity: dim,
            }}
          >
            <span
              style={{
                width: 34,
                textAlign: 'right',
                paddingRight: 12,
                color: 'rgba(93,113,131,0.55)',
                fontSize: fontSize - 1.5,
                flex: '0 0 auto',
              }}
            >
              {i + 1}
            </span>
            <span style={{ whiteSpace: 'pre', flex: 1 }}>
              {highlight(txt, theme).map((tk, k) => (
                <span key={k} style={{ color: tk.c }}>
                  {tk.t}
                </span>
              ))}
              {showCursor && i === cursorLine && (
                <span
                  style={{
                    display: 'inline-block',
                    width: 7,
                    height: fontSize + 3,
                    background: C.ice,
                    verticalAlign: 'text-bottom',
                    marginLeft: 1,
                  }}
                />
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
};

/* ── 章节标题（左上角，kicker 用等宽） ─────────────────────────────── */
export const Title: React.FC<{ kicker: string; text: string; sub?: string; style?: React.CSSProperties }> = ({
  kicker,
  text,
  sub,
  style,
}) => (
  <div style={{ position: 'absolute', left: 56, top: 34, ...style }}>
    <div
      style={{
        fontFamily: FONT_MONO,
        fontSize: 12.5,
        letterSpacing: 1.4,
        color: C.iceDeep,
        textTransform: 'uppercase',
      }}
    >
      {kicker}
    </div>
    <div style={{ fontFamily: FONT_CN, fontSize: 25, fontWeight: 700, color: C.slate, marginTop: 5 }}>
      {text}
    </div>
    {sub && (
      <div style={{ fontFamily: FONT_CN, fontSize: 14, color: C.mute, marginTop: 5 }}>{sub}</div>
    )}
  </div>
);
