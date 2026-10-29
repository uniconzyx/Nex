/**
 * Track408Page.tsx —— 考研 408 专轨总表 + 单章下钻（P4）
 * ============================================================================
 * 复用：
 *   - P2 的 buildTrack408Summary（四模块跨章聚合：已通关 / 平均掌握度 / 薄弱章 / 冲刺建议）
 *   - P3 的 ChapterSummaryPanel（单章 7 维总结表面板，仅 mastery===100 渲染）
 *
 * 路由：#track408（深链 #track408/<chapterId> 直接下钻到某章总结）
 * 与「图表总览」「知识试炼区」同属学习中枢，是 408 备考的跨章视角。
 * ============================================================================
 */
import { useMemo, useState } from 'react';

import { useProgress } from '../lib/progress';
import { buildTrack408Summary, trackSummaryToMarkdown, type TrackSummary } from '../lib/examTracks';
import { buildChapterSummary, contentOf, summaryToMarkdown } from '../lib/chapterSummary';
import { ChapterSummaryPanel } from './LearnPage';
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

      {/* ── 模块卡片 + 章节网格 ─────────────────────────────── */}
      {track.modules.map((m) => (
        <section className="km-card track408-module" key={m.module}>
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
      ))}

      {/* ── 单章下钻（7 维总结表） ─────────────────────────── */}
      {selRow && (
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
            <p className="km-summary-locked">
              通关三关（概念 / 演练 / BOSS 全绿）后，这里会解锁本章「7 维总结表」。
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
      )}
    </div>
  );
}

export default Track408Page;
