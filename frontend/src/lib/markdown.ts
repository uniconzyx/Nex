/**
 * markdown.ts —— 极简 Markdown -> HTML（题目展示用）
 * ============================================================================
 * 为什么不用 marked / markdown-it：
 *   1. APK 体积敏感：marked 约 40KB（gzip 后 12KB），只为渲染题面不值。
 *   2. 安全面：题面数据来自我们自己的 content/，但用户可能粘贴外部题目。
 *      引入完整解析器就要连带处理一堆 XSS 面；自己写反而更容易保证
 *      "只产出白名单标签"。
 *
 * 覆盖范围（刻意克制，够用即止）：
 *   标题 #~######、段落、粗体 **x**、斜体 *x*、行内代码 `x`、
 *   围栏代码块 ```lang、无序/有序列表、引用 >、水平线 ---、
 *   表格（GFM 管道表）、链接 [t](u)、图片 ![alt](u)
 *
 * ⚠️ 安全铁律：**先转义，再加标签**。
 *   所有用户文本先过 escapeHtml，之后插入的只有我们自己写的标签字符串。
 *   链接 href 额外做协议白名单（javascript: / data: 一律丢弃）。
 * ============================================================================
 */

const ESCAPE_MAP: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ESCAPE_MAP[c] as string);
}

/** 链接协议白名单。相对路径（不以 scheme: 开头）放行。 */
function safeHref(raw: string): string | null {
  const url = raw.trim();
  if (!url) return null;
  // 允许 http/https/mailto/相对路径/锚点
  if (/^(https?:|mailto:|#|\/|\.\/|\.\.\/)/i.test(url)) return url;
  // 无 scheme 的裸域名不算安全（"example.com" 会被当相对路径），直接放行相对路径即可
  if (/^[\w.-]+(\/|$)/.test(url) && !/^[a-z][a-z0-9+.-]*:/i.test(url)) return url;
  return null;
}

/** 行内元素。必须在已转义的文本上调用。 */
function inline(escaped: string): string {
  let s = escaped;

  // 行内代码优先：里面不解析其他格式（`**x**` 应原样显示）
  const codes: string[] = [];
  s = s.replace(/`([^`]+)`/g, (_m, code: string) => {
    codes.push(`<code>${code}</code>`);
    return `\u0000CODE${codes.length - 1}\u0000`;
  });

  // 图片 ![alt](url)
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_m, alt: string, url: string) => {
    const href = safeHref(url);
    if (!href) return alt;
    return `<img src="${escapeHtml(href)}" alt="${alt}" loading="lazy" />`;
  });

  // 链接 [text](url)
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_m, text: string, url: string) => {
    const href = safeHref(url);
    if (!href) return text;
    const external = /^https?:/i.test(href);
    const attrs = external ? ' target="_blank" rel="noopener noreferrer"' : '';
    return `<a href="${escapeHtml(href)}"${attrs}>${text}</a>`;
  });

  // 粗体 / 斜体（粗体先，避免 **x** 被斜体规则吃成 *<em>x</em>*）
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');

  // 还原行内代码占位
  s = s.replace(/\u0000CODE(\d+)\u0000/g, (_m, i: string) => codes[Number(i)] ?? '');
  return s;
}

/** 表格分隔行：| --- | :---: | ---: | */
function isTableDivider(line: string): boolean {
  return /^\s*\|?[\s:-]*-[\s:|-]*\|?\s*$/.test(line) && line.includes('-');
}

function splitRow(line: string): string[] {
  const t = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  return t.split('|').map((c) => c.trim());
}

function alignOf(cell: string): 'left' | 'center' | 'right' {
  const l = cell.startsWith(':');
  const r = cell.endsWith(':');
  if (l && r) return 'center';
  if (r) return 'right';
  return 'left';
}

/**
 * 解析为 HTML 字符串。
 *
 * 输出可直接 dangerouslySetInnerHTML。**不要**把返回值再套一层
 * 未经转义的用户输入。
 */
export function renderMarkdown(src: string): string {
  const lines = src.replace(/\r\n?/g, '\n').split('\n');
  const out: string[] = [];
  let i = 0;

  const flushParagraph = (buf: string[]) => {
    if (buf.length === 0) return;
    // 段落内单换行按 <br> 处理：题面里「输入：」「输出：」经常靠换行排版
    out.push(`<p>${buf.map(inline).join('<br />')}</p>`);
    buf.length = 0;
  };

  const para: string[] = [];

  while (i < lines.length) {
    const raw = lines[i] as string;
    const line = raw.replace(/\s+$/, '');

    /* ---- 围栏代码块 ---- */
    const fence = /^\s*```(\w*)\s*$/.exec(line);
    if (fence) {
      flushParagraph(para);
      const langInfo = fence[1] ?? '';
      const body: string[] = [];
      i += 1;
      while (i < lines.length && !/^\s*```\s*$/.test(lines[i] as string)) {
        body.push(lines[i] as string);
        i += 1;
      }
      i += 1; // 跳过收尾的 ```
      const cls = langInfo ? ` class="language-${escapeHtml(langInfo)}"` : '';
      out.push(`<pre class="md-pre"><code${cls}>${escapeHtml(body.join('\n'))}</code></pre>`);
      continue;
    }

    /* ---- 空行 ---- */
    if (line.trim() === '') {
      flushParagraph(para);
      i += 1;
      continue;
    }

    /* ---- 标题 ---- */
    const h = /^(#{1,6})\s+(.*)$/.exec(line);
    if (h) {
      flushParagraph(para);
      const level = (h[1] as string).length;
      out.push(`<h${level}>${inline(escapeHtml(h[2] as string))}</h${level}>`);
      i += 1;
      continue;
    }

    /* ---- 水平线 ---- */
    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      flushParagraph(para);
      out.push('<hr />');
      i += 1;
      continue;
    }

    /* ---- 表格：当前行含 | 且下一行是分隔行 ---- */
    if (line.includes('|') && i + 1 < lines.length && isTableDivider(lines[i + 1] as string)) {
      flushParagraph(para);
      const head = splitRow(line);
      const aligns = splitRow(lines[i + 1] as string).map(alignOf);
      i += 2;

      const rows: string[][] = [];
      while (i < lines.length && (lines[i] as string).includes('|') && (lines[i] as string).trim() !== '') {
        rows.push(splitRow(lines[i] as string));
        i += 1;
      }

      const th = head
        .map((c, k) => `<th style="text-align:${aligns[k] ?? 'left'}">${inline(escapeHtml(c))}</th>`)
        .join('');
      const tbody = rows
        .map(
          (r) =>
            `<tr>${head
              .map(
                (_h, k) =>
                  `<td style="text-align:${aligns[k] ?? 'left'}">${inline(escapeHtml(r[k] ?? ''))}</td>`,
              )
              .join('')}</tr>`,
        )
        .join('');
      out.push(`<div class="md-table-wrap"><table><thead><tr>${th}</tr></thead><tbody>${tbody}</tbody></table></div>`);
      continue;
    }

    /* ---- 引用 ---- */
    if (/^\s*>\s?/.test(line)) {
      flushParagraph(para);
      const body: string[] = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i] as string)) {
        body.push((lines[i] as string).replace(/^\s*>\s?/, ''));
        i += 1;
      }
      out.push(`<blockquote>${body.map((b) => `<p>${inline(escapeHtml(b))}</p>`).join('')}</blockquote>`);
      continue;
    }

    /* ---- 列表 ---- */
    const ul = /^\s*[-*+]\s+(.*)$/.exec(line);
    if (ul) {
      flushParagraph(para);
      const items: string[] = [];
      while (i < lines.length) {
        const m = /^\s*[-*+]\s+(.*)$/.exec(lines[i] as string);
        if (!m) break;
        items.push(`<li>${inline(escapeHtml(m[1] as string))}</li>`);
        i += 1;
      }
      out.push(`<ul>${items.join('')}</ul>`);
      continue;
    }

    const ol = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    if (ol) {
      flushParagraph(para);
      const items: string[] = [];
      while (i < lines.length) {
        const m = /^\s*\d+[.)]\s+(.*)$/.exec(lines[i] as string);
        if (!m) break;
        items.push(`<li>${inline(escapeHtml(m[1] as string))}</li>`);
        i += 1;
      }
      out.push(`<ol>${items.join('')}</ol>`);
      continue;
    }

    /* ---- 普通段落行 ---- */
    para.push(line);
    i += 1;
  }

  flushParagraph(para);
  return out.join('\n');
}

/**
 * 去掉 Markdown 语法，得到纯文本（用于列表摘要、AI 上下文注入）。
 * 不做完整 AST —— 只需要「人读得懂的一行」。
 */
export function stripMarkdown(src: string): string {
  return src
    .replace(/```[\s\S]*?```/g, ' [代码] ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_`>|-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
