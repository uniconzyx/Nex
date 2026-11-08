/**
 * ConceptReader.tsx —— 章节详情里的「概念全文」阅读面板
 * ============================================================================
 * 数据来自 frontend/src/data/concepts/（gen_concept_docs.py 从 content/ 生成）：
 * 723 篇概念正文按学科切成 16 个懒加载 chunk，用户点开折叠面板才 import，
 * 不占首屏主 chunk。渲染复用 lib/markdown.ts 的白名单转换器与 .md-body 样式，
 * 不引入新的 Markdown 依赖，也不新增色彩变量。
 *
 * 为什么默认折叠：一章正文平均 4~5 篇 / 40KB，平铺会把三关和图解推到屏幕外。
 */
import { useEffect, useMemo, useState } from 'react';
import { hasConceptDocs, loadConceptDocs, type ConceptDoc } from '../data/concepts';
import { renderMarkdown } from '../lib/markdown';

const FRAME = {
  margin: '14px 0',
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid var(--km-line2)',
  background: 'var(--km-sunk)',
} as const;

const HINT = { margin: '8px 0 0', color: 'var(--km-ink-soft)', fontSize: 13 } as const;

export function ConceptReader({ chapterId }: { chapterId: string }) {
  const available = hasConceptDocs(chapterId);
  const [open, setOpen] = useState(false);
  const [docs, setDocs] = useState<ConceptDoc[] | null>(null);
  const [error, setError] = useState('');

  // 切到别的章：收起并清掉上一章正文，避免短暂显示错章内容
  useEffect(() => {
    setOpen(false);
    setDocs(null);
    setError('');
  }, [chapterId]);

  useEffect(() => {
    if (!open || docs || !available) return;
    let alive = true;
    loadConceptDocs(chapterId)
      .then((list) => {
        if (alive) setDocs(list);
      })
      .catch((e: unknown) => {
        if (alive) setError(String(e));
      });
    return () => {
      alive = false;
    };
  }, [open, docs, available, chapterId]);

  const html = useMemo(() => (docs ?? []).map((d) => renderMarkdown(d.markdown)), [docs]);

  if (!available) return null;

  return (
    <details
      className="km-concept-full"
      onToggle={(e) => setOpen(e.currentTarget.open)}
      style={FRAME}
    >
      <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: 14 }}>
        {`概念全文 · ${docs ? `${docs.length} 篇` : `${chapterId}（点击加载）`}`}
      </summary>
      {error && <p style={HINT}>{`加载失败：${error}`}</p>}
      {open && !docs && !error && <p style={HINT}>正在加载本章概念正文…</p>}
      {docs && docs.length === 0 && <p style={HINT}>本章暂无概念正文。</p>}
      {docs?.map((d, i) => (
        <details key={d.name} open={i === 0} style={{ margin: '10px 0 0', paddingLeft: 8 }}>
          <summary style={{ cursor: 'pointer', fontSize: 13 }}>{d.title}</summary>
          <div
            className="md-body"
            style={{ fontSize: 14, lineHeight: 1.8 }}
            dangerouslySetInnerHTML={{ __html: html[i] ?? '' }}
          />
        </details>
      ))}
    </details>
  );
}
