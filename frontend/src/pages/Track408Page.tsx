/**
 * Track408Page.tsx —— 考研 408 专轨总表 + 单章下钻（P4）
 * ============================================================================
 * 复用：
 *   - P2 的 buildTrack408Summary（四模块跨章聚合：已通关 / 平均掌握度 / 薄弱章 / 冲刺建议）
 *   - P3 的 ChapterSummaryPanel（单章 7 维总结表面板，仅 mastery===100 渲染）
 *   - ConceptReader（章节概念全文，按学科懒加载、离线内置）
 *
 * 路由：#track408（深链 #track408/<chapterId> 直接下钻到某章）
 * 与「图表总览」「知识试炼区」同属学习中枢，是 408 备考的跨章视角。
 *
 * 2026-11-09 修「展开没内容」：原先下钻区挂在所有模块卡片之后（y≈1500，
 * 点开后视口里毫无变化），且未通关只显示一句锁定提示（全文 80 字）。
 * 现在下钻区紧跟所点模块就地展开，未通关也渲染本章内容速览 + 概念全文入口；
 * 7 维总结表仍只在三关全通后解锁，既有设计不推翻。
 * ============================================================================
 */
import { Fragment, useMemo, useState } from 'react';

import { useProgress } from '../lib/progress';
import { buildTrack408Summary, trackSummaryToMarkdown, type TrackSummary } from '../lib/examTracks';
import { buildChapterSummary, contentOf, summaryToMarkdown } from '../lib/chapterSummary';
import { ChapterSummaryPanel } from './LearnPage';
import { ConceptReader } from '../components/ConceptReader';
import { ConceptViz } from '../components/ConceptViz';
import type { KmPage } from '../lib/nav';
import './Track408Page.css';

/** 复制 Markdown 到剪贴板：安全上下文走 navigator.clipboard，否则降级 textarea+execCommand */
async function copyMarkdown(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
    } catch {
      /* 复制失败也不报错，用户可手动选文本 */
    }
    document.body.removeChild(ta);
  }
}

function deepChapterFromHash(): string | null {
  const h = location.hash;
  const m = h.match(/^#track408\/(.+)$/) || h.match(/^#track\/408\/(.+)$/);
  return m ? decodeURIComponent(m[1]) : null;
}

export function Track408Page({ onNavigate }: { onNavigate?: (p: KmPage) => void }) {
  const p = useProgress();
  const track = useMemo<TrackSummary>(() => buildTrack408Summary(p), [p]);
  const [selected, setSelected] = useState<string | null>(() => deepChapterFromHash());
  const [copied, setCopied] = useState(false);
  const [sumCopied, setSumCopied] = useState(false);

  const onExport = async () => {
    await copyMarkdown(trackSummaryToMarkdown(track));
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const onCopySummary = async () => {
    if (!selSummary) return;
    await copyMarkdown(summaryToMarkdown(selSummary));
    setSumCopied(true);
    setTimeout(() => setSumCopied(false), 1800);
  };

  const selectChapter = (id: string | null) => {
    setSelected(id);
    history.replaceState(null, '', id ? `#track408/${id}` : '#track408');
  };

  const allChapters = track.modules.flatMap((m) => m.chapters);
  const selRow = selected ? allChapters.find((c) => c.id === selected) ?? null : null;
  const selSummary = selected ? buildChapterSummary(selected, p) : null;
  const selectedModuleName = selRow
    ? track.modules.find((m) => m.chapters.some((c) => c.id === selected))?.module
    : undefined;

  // 未通关时给「本章内容速览」：切片来自 gen_chapter_content.py 的全库产物，
  // 与 7 维总结表同源，但不要求 mastery===100，避免下钻区空着只有一句锁定提示。
  const content = selected ? contentOf(selected) : undefined;
  const briefGroups = content
    ? [
        { label: '本章目标', items: content.goals },
        { label: '核心概念', items: content.concepts },
        { label: '易错点', items: content.pitfalls },
        { label: '面试 / 真题', items: content.interviews },
        { label: '实战项目', items: content.projects },
      ].filter((g) => g.items.length > 0)
    : [];
  const briefTotal = briefGroups.reduce((n, g) => n + g.items.length, 0);

  const drillNode = selRow ? (
    <section className="km-card track408-drill" style={{ borderColor: 'var(--km-glow)' }}>
      <div className="km-cont-top">
        <h3 style={{ margin: 0 }}>下钻 · {selRow.title}</h3>
        <span className={`km-mastery-chip${selRow.done ? ' done' : ''}`}>掌握 {selRow.mastery}%</span>
        <button
          type="button"
          className="km-btn km-btn-sm km-btn-ghost"
          onClick={() => selectChapter(null)}
        >
          收起
        </button>
      </div>

      {selSummary ? (
        <ChapterSummaryPanel
          summary={selSummary}
          content={contentOf(selected!)}
          copied={sumCopied}
          onCopy={onCopySummary}
        />
      ) : (
        <div className="track408-brief">
          <p className="km-hint" style={{ marginTop: 0 }}>
            本章内容速览 · {briefTotal} 条正文切片 + {content?.concepts.length ?? 0} 篇概念全文
            （离线内置，下方展开即可读）
          </p>
          <div className="track408-brief-grid">
            {briefGroups.map((g) => (
              <details
                className="track408-brief-item"
                key={g.label}
                open={g.label === '本章目标' || g.label === '核心概念'}
              >
                <summary>
                  {g.label}
                  <span className="km-tag km-tag-gray">{g.items.length}</span>
                </summary>
                <ul>
                  {g.items.slice(0, 6).map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
        </div>
      )}

      {/* 机制图解：与学习页同一套 viz 数据/组件，按学科懒加载、可点开放大 */}
      {content && <ConceptViz subject={content.subject} chapterId={selected!} />}

      {/* 概念全文（懒加载学科 chunk）：通关与否都能读，是「展开有内容」的主体 */}
      <ConceptReader chapterId={selected!} />

      {!selSummary && (
        <p className="km-summary-locked" style={{ marginTop: 12 }}>
          通关三关（概念 / 演练 / BOSS 全绿）后，这里会额外解锁本章「7 维总结表」；
          上面的正文与切片现在就能读。
        </p>
      )}

      <div style={{ marginTop: 12 }}>
        <button
          type="button"
          className="km-btn km-btn-sm km-btn-primary"
          onClick={() => {
            selectChapter(null);
            onNavigate?.('learn');
          }}
        >
          去知识试炼区刷这一章
        </button>
      </div>
    </section>
  ) : null;

  return (
    <div className="track408-root">
      <header className="track408-head">
        <div>
          <h1>{track.name}</h1>
          <p className="track408-lede">
            四模块跨章汇总 · 已通关 <b>{track.totalDone}</b>/{track.totalChapters} · 平均掌握度{' '}
            <b>{track.overallAvg}%</b>
          </p>
        </div>
        <button type="button" className="km-btn km-btn-sm km-btn-ghost" onClick={onExport}>
          {copied ? '已复制 ✓' : '导出 408 总表 Markdown'}
        </button>
      </header>

      <div className="km-mini-bar track408-overall" aria-label={`总平均掌握度 ${track.overallAvg}%`}>
        <i style={{ width: `${Math.max(track.overallAvg, 1)}%` }} />
      </div>

      {/* ── 四模块总表 ───────────────────────────────────────── */}
      <section className="km-card">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>408 总表（四模块）</h3>
          <span className="km-tag km-tag-gray">{track.modules.length} 模块</span>
        </div>
        <div className="track408-master-wrap">
          <table className="track408-master">
            <thead>
              <tr>
                <th>模块</th>
                <th>章节数</th>
                <th>已通关</th>
                <th>平均掌握度</th>
                <th>薄弱章 (&lt;60)</th>
                <th>冲刺建议</th>
              </tr>
            </thead>
            <tbody>
              {track.modules.map((m) => (
                <tr key={m.module}>
                  <td className="track408-mod-name">{m.module}</td>
                  <td>{m.chapterCount}</td>
                  <td>
                    <span className={m.doneCount === m.chapterCount ? 'track408-done-all' : ''}>
                      {m.doneCount}/{m.chapterCount}
                    </span>
                  </td>
                  <td>
                    <span className="track408-bar">
                      <i style={{ width: `${m.avgMastery}%` }} />
                    </span>
                    <span className="track408-barnum">{m.avgMastery}</span>
                  </td>
                  <td>
                    {m.weakChapters.length
                      ? m.weakChapters.map((c) => c.title).join('、')
                      : '—'}
                  </td>
                  <td className="track408-sprint">{m.sprint}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── 模块卡片 + 章节网格；下钻区紧跟所点模块，点开即在视口内 ── */}
      {track.modules.map((m) => (
        <Fragment key={m.module}>
          <section className="km-card track408-module">
            <div className="km-cont-top">
              <h3 style={{ margin: 0 }}>{m.module}</h3>
              <span className="km-tag km-tag-gray">
                {m.doneCount}/{m.chapterCount} 通关
              </span>
            </div>
            <div className="track408-bar track408-module-bar" aria-label={`模块平均掌握度 ${m.avgMastery}%`}>
              <i style={{ width: `${m.avgMastery}%` }} />
            </div>
            <p className="km-hint" style={{ marginTop: 6 }}>
              {m.sprint}
            </p>
            <div className="track408-chgrid">
              {m.chapters.map((c) => {
                const active = selected === c.id;
                const weak = c.mastery < 60 && c.mastery > 0;
                const unstarted = c.mastery === 0;
                return (
                  <button
                    type="button"
                    key={c.id}
                    className={`track408-chip${c.done ? ' done' : ''}${weak ? ' weak' : ''}${
                      unstarted ? ' unstarted' : ''
                    }${active ? ' active' : ''}`}
                    onClick={() => selectChapter(active ? null : c.id)}
                    title={`${c.title} · 掌握度 ${c.mastery}%${c.done ? ' · 已三关全通' : ''}`}
                  >
                    <b>{c.title}</b>
                    <span className={`track408-chip-m${c.done ? ' done' : ''}`}>{c.mastery}%</span>
                  </button>
                );
              })}
            </div>
          </section>
          {m.module === selectedModuleName && drillNode}
        </Fragment>
      ))}
    </div>
  );
}

export default Track408Page;
