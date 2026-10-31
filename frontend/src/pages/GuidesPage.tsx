/**
 * GuidesPage.tsx —— 考研手札（11408 笔记与经验贴）
 *
 * 定位：这是「别人的笔记」索引，不是课程内容。所以页面不抄正文，
 * 只做三件事：按学科定位 → 看要点提炼 → 跳原文。
 *
 * 数据源改为打包的 BUNDLE.guides（content/_guides/11408.json），
 * 离线可用；合规要求不变：408 单篇最大 44MB 且依赖同目录 assets，
 * 整篇内联会断图，正文一律跳 GitHub 原文。
 */
import { useMemo, useState } from 'react';

import { BUNDLE } from '../data/bundle';
import { ExamPage } from './ExamPage';

type Kind = 'note' | 'experience' | 'external';

interface GuideItem {
  slug: string;
  kind: Kind;
  subject: string;
  title: string;
  summary: string;
  points: string[];
  url: string;
  read_min: number;
  recommended: boolean;
}

const KIND_ORDER: Kind[] = ['note', 'experience', 'external'];

const KIND_LABEL: Record<Kind, string> = {
  note: '笔记',
  experience: '经验贴',
  external: '外部文档',
};

const SUBJECT_LABEL: Record<string, string> = {
  math: '数学',
  english: '英语',
  politics: '政治',
  '408': '408 计算机',
  cs408: '408 计算机',
  '11408': '11408',
  ds: '数据结构',
  os: '操作系统',
  co: '计算机组成',
  network: '计算机网络',
  general: '通用',
  plan: '备考规划',
};

function labelOfSubject(k: string): string {
  return SUBJECT_LABEL[k] ?? k;
}

export function GuidesPage() {
  const all = BUNDLE.guides.items as unknown as GuideItem[];
  const meta = BUNDLE.guides.source;
  const [subject, setSubject] = useState('');
  const [kind, setKind] = useState<Kind | ''>('');
  const [openSlugs, setOpenSlugs] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState<'notes' | 'bank'>('notes');

  const facets = useMemo(() => {
    const m = new Map<string, number>();
    for (const it of all) m.set(it.subject, (m.get(it.subject) ?? 0) + 1);
    return [...m.entries()]
      .map(([key, count]) => ({ key, label: labelOfSubject(key), count }))
      .sort((a, b) => b.count - a.count);
  }, [all]);

  const items = useMemo(
    () => all.filter((i) => (!subject || i.subject === subject) && (!kind || i.kind === kind)),
    [all, subject, kind],
  );

  const grouped = useMemo(() => {
    const map = new Map<Kind, GuideItem[]>();
    for (const k of KIND_ORDER) {
      const arr = items.filter((i) => i.kind === k);
      if (arr.length) map.set(k, arr);
    }
    return [...map.entries()];
  }, [items]);

  const toggle = (slug: string) => {
    setOpenSlugs((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };

  return (
    <div className="cp-wrap">
      <header className="cp-head">
        <div>
          <h2 className="cp-title">{meta.title || '考研手札'}</h2>
          <p className="cp-sub">
            {all.length} 条 · 笔记 {all.filter((i) => i.kind === 'note').length} / 经验贴{' '}
            {all.filter((i) => i.kind === 'experience').length} / 外链{' '}
            {all.filter((i) => i.kind === 'external').length} · 只存要点与原文链接，不搬运正文
          </p>
        </div>
        {meta.url && (
          <a className="gd-src" href={meta.url} target="_blank" rel="noreferrer">
            <span className="gd-src-repo">{meta.repo}</span>
            <span className="gd-src-meta">
              ★ {meta.stars} · {meta.license ?? '无许可证'}
            </span>
            <span className="gd-src-go">↗</span>
          </a>
        )}
      </header>

      <div className="ex-tabs" role="tablist" aria-label="考研板块">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'notes'}
          className={`ex-tab${tab === 'notes' ? ' on' : ''}`}
          onClick={() => setTab('notes')}
        >
          手札笔记
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'bank'}
          className={`ex-tab${tab === 'bank' ? ' on' : ''}`}
          onClick={() => setTab('bank')}
        >
          考研题库
        </button>
      </div>

      {tab === 'notes' && (
        <>
          <div className="cp-chips" role="tablist" aria-label="学科筛选">
        <button
          type="button"
          role="tab"
          aria-selected={subject === ''}
          className={`cp-chip${subject === '' ? ' on' : ''}`}
          onClick={() => setSubject('')}
        >
          全部
        </button>
        {facets.map((f) => (
          <button
            key={f.key}
            type="button"
            role="tab"
            aria-selected={subject === f.key}
            className={`cp-chip${subject === f.key ? ' on' : ''}`}
            onClick={() => setSubject(f.key)}
          >
            {f.label}
            <span className="cp-chip-n">{f.count}</span>
          </button>
        ))}
      </div>

      <div className="cp-chips cp-tier-row" role="tablist" aria-label="形态筛选">
        <span className="cp-tier-label">形态</span>
        <button
          type="button"
          role="tab"
          aria-selected={kind === ''}
          className={`cp-chip${kind === '' ? ' on' : ''}`}
          onClick={() => setKind('')}
        >
          全部
        </button>
        {KIND_ORDER.map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={kind === k}
            className={`cp-chip${kind === k ? ' on' : ''}`}
            onClick={() => setKind(k)}
          >
            {KIND_LABEL[k]}
          </button>
        ))}
      </div>

      {items.length === 0 && (
        <div className="cp-state">
          <b>这个筛选下没有条目</b>
          <p>换一个学科，或点「全部」。</p>
        </div>
      )}

      {grouped.map(([k, arr]) => (
        <section key={k} className="gd-group">
          <h3 className="gd-group-title">
            {KIND_LABEL[k]}
            <span>{arr.length}</span>
          </h3>
          <div className="gd-list">
            {arr.map((it) => {
              const open = openSlugs.has(it.slug);
              const shown = open ? it.points : it.points.slice(0, 2);
              return (
                <article key={it.slug} className={`gd-item ${it.kind}`}>
                  <div className="gd-item-head">
                    <span className={`gd-dot ${it.kind}`} aria-hidden="true" />
                    <h4>{it.title}</h4>
                    {it.recommended && <span className="gd-rec">推荐</span>}
                    <span className="gd-min">{it.read_min} 分钟</span>
                  </div>

                  <p className="gd-summary">{it.summary}</p>

                  <ul className="gd-points">
                    {shown.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>

                  <div className="gd-item-foot">
                    {it.points.length > 2 && (
                      <button type="button" className="gd-more" onClick={() => toggle(it.slug)}>
                        {open ? '收起' : `展开其余 ${it.points.length - 2} 条要点`}
                      </button>
                    )}
                    <a href={it.url} target="_blank" rel="noreferrer" className="gd-link">
                      看原文 · {labelOfSubject(it.subject)} ↗
                    </a>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ))}

      {meta.note && <p className="gd-footnote">{meta.note}</p>}
        </>
      )}

      {tab === 'bank' && <ExamPage embedded />}
    </div>
  );
}

export default GuidesPage;
