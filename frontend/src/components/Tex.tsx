/**
 * Tex.tsx —— KaTeX 公式渲染
 *
 * 为什么是异步：KaTeX 本身 ~280KB（含字体另有 1MB），只有「数学 → 公式速查」
 * 一个页面用得到。静态 import 会把它拖进主包，让每个打开 APP 的人先等它下载。
 * 这里改成首次遇到公式时才 import()，其余页面完全不付这个成本。
 *
 * 用 katex.renderToString 而不是运行时挂载 → 渲染是同步产出 HTML 字符串，
 * 布局不会先抖一下再撑开，滚动位置也就不会跳。
 *
 * throwOnError 关掉：公式是数据文件里手写的，一条写错不该让整页白屏，
 * 出错时 KaTeX 会把原文染红显示出来，反而更容易发现是哪条写错了。
 *
 * 两种用法：
 *   <Tex tex="\frac{a}{b}" />                    整段就是公式
 *   <TexMixed text="如 $\frac{a}{b}$ 所示" />    中英混排，只有 $...$ 里是公式
 * 说明文字（note）一律用 TexMixed：里面常出现「1^∞ 一律取对数」这种
 * 纯符号写法，整段丢给 KaTeX 会被当成上标脚本压成小字。
 */
import { useEffect, useMemo, useState } from 'react';

// @types/katex 用 `export = katex`，没有具名/默认导出，类型取模块本身
type Katex = typeof import('katex');

// 模块级缓存：一个页面里有几百条公式，只该 import 一次。
let katexPromise: Promise<Katex> | null = null;
function loadKatex(): Promise<Katex> {
  if (!katexPromise) {
    katexPromise = import('katex').then((m) => (m as { default?: Katex }).default ?? (m as unknown as Katex));
  }
  return katexPromise;
}

function renderTeX(katex: Katex, tex: string, display: boolean): string {
  // 行内模式默认把 \lim 的上下标压到右下方、把 \frac 压成斜杠，
  // 在「说明文字里夹公式」的场景下会缩成一团看不清。
  // 含堆叠类命令时自动加 \displaystyle：仍是行内，但上下标与分数按行间规则排版。
  const stacked = /\\(lim|sum|prod|int|iint|iiint|oint|frac|dfrac)/.test(tex);
  const source = display || !stacked ? tex : `\\displaystyle ${tex}`;
  try {
    return katex.renderToString(source, {
      displayMode: display,
      throwOnError: false,
      strict: false,
      trust: false,
      output: 'html',
    });
  } catch {
    return '';
  }
}

/** 等 KaTeX 就绪后把 tex 渲染成 HTML；未就绪时先渲染占位原文 */
function useTeX(tex: string, display: boolean): string {
  const [katex, setKatex] = useState<Katex | null>(null);

  useEffect(() => {
    let alive = true;
    loadKatex().then((k) => {
      if (alive) setKatex(k);
    });
    return () => {
      alive = false;
    };
  }, []);

  return useMemo(() => (katex ? renderTeX(katex, tex, display) : ''), [katex, tex, display]);
}

export function Tex({ tex, display = false }: { tex: string; display?: boolean }) {
  const html = useTeX(tex, display);

  if (!html) {
    // KaTeX 还没下载完（或渲染失败）：先按等宽原文显示，不跳版
    return <code className="km-tex-fallback">{tex}</code>;
  }
  // eslint-disable-next-line react/no-danger -- 内容来自本地数据文件，非用户输入
  return <span className="km-tex" dangerouslySetInnerHTML={{ __html: html }} />;
}

/**
 * 中英混排：把 $...$ 之间的内容渲染成公式，其余按原样输出。
 * 没有 $ 就完全按纯文本走，避免把正文里的 ^ 和 _ 误当公式语法。
 */
export function TexMixed({ text }: { text: string }) {
  const parts = useMemo(() => {
    const out: { tex: boolean; value: string }[] = [];
    const re = /\$([^$]+)\$/g;
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text))) {
      if (m.index > last) out.push({ tex: false, value: text.slice(last, m.index) });
      out.push({ tex: true, value: m[1] });
      last = m.index + m[0].length;
    }
    if (last < text.length) out.push({ tex: false, value: text.slice(last) });
    return out;
  }, [text]);

  if (parts.length === 1 && !parts[0].tex) {
    return <>{text}</>;
  }

  return (
    <>
      {parts.map((p, i) =>
        p.tex ? <Tex key={i} tex={p.value} /> : <span key={i}>{p.value}</span>,
      )}
    </>
  );
}
