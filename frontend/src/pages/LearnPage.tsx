/**
 * LearnPage.tsx —— 知识试炼区（P2 三关版）
 * ============================================================================
 * 数据来自 content/<subject>/_manifest.json（打包进 BUNDLE），12 个学科；
 * C 语言的 7 个单元单独放在 cpp manifest 的 clang_module 里，由
 * data/clangUnits.ts 提供 —— 以前这里是一张空页，7 单元 105 道题无法到达。
 *
 * 【P2 改了什么，为什么】
 *   P1 之前，每章只有一个「标记为已掌握」按钮：按一下 = 100 掌握。
 *   于是「掌握」既不是读懂的证明，也不是会做的证明，只是一个开关。
 *
 *   现在每章拆成三关（概念 30 / 演练 30 / BOSS 40），判定规则在 lib/stages.ts，
 *   全部由「这一章哪些题最近一次答对了」推出来，页面不存任何自己的进度：
 *     - 关卡卡片直接说清「要做什么、还差几道」；
 *     - 点「继续这一关」直接锁定本章进题库，点 BOSS 直接打开那道首领题；
 *     - 三关全通 → +60 结晶（进度层发放，页面只负责展示）。
 *
 *   手动「标记已掌握」被移除：它和这套规则互相打架（点了又答错，到底算不算会）。
 *   真在别处学过的人，答完 5 道题也就 3 分钟；想重来则用「重置本章」。
 * ============================================================================
 */
import { useMemo, useState } from 'react';

import { BUNDLE, type BundleChapter } from '../data/bundle';
import { CLANG_CHAPTERS } from '../data/clangUnits';
import { SubjectSwitch } from '../components/SubjectSwitch';
import { subjectLabel, useSubject } from '../lib/subject';
import { chapterMastery, resetChapter, useProgress } from '../lib/progress';
import { chapterBankStats, focusChapter, TYPE_META, type BankType } from '../lib/exerciseBank';
import { challengeQuestion } from '../lib/challenge';
import { chapterDeps, chapterName, masteryOfChapter, subjectMastery, UNLOCK_MASTERY } from '../lib/graph';
import { isUnlocked } from '../lib/logicChain';
import { chapterStages, STAGE_META, type StageView } from '../lib/stages';
import { buildChapterSummary, contentOf, summaryToMarkdown, type ChapterSummary, type SummaryDim } from '../lib/chapterSummary';
import type { ChapterContent } from '../data/chapterContent';
import type { KmPage } from '../lib/nav';

const TYPE_ORDER: BankType[] = ['choice', 'coding', 'output', 'fix_error', 'explain', 'design'];

export function LearnPage({ onNavigate }: { onNavigate?: (p: KmPage) => void }) {
  const [subject] = useSubject();
  const p = useProgress();
  const [openId, setOpenId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  /** 把单章总结复制成 Markdown 表格（对齐主人 E 盘笔记习惯） */
  const handleCopySummary = async (s: ChapterSummary) => {
    const md = summaryToMarkdown(s);
    try {
      await navigator.clipboard.writeText(md);
    } catch {
      // 非安全上下文（http/iframe）降级到 textarea + execCommand
      const ta = document.createElement('textarea');
      ta.value = md;
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
    setCopiedId(s.chapterId);
    setTimeout(() => setCopiedId((cur) => (cur === s.chapterId ? null : cur)), 1800);
  };

  const isClang = subject === 'clang';
  const pack = isClang ? undefined : BUNDLE.chapters[subject as keyof typeof BUNDLE.chapters];
  const chapters: BundleChapter[] = isClang ? CLANG_CHAPTERS : (pack?.chapters ?? []);
  const groups: Record<string, string> = isClang
    ? { 'C 语言独立模块': 'C 语言独立模块' }
    : (pack?.groups ?? {});

  const doneCount = chapters.filter((c) => chapterMastery(c.id, p) >= 100).length;
  const avg = subjectMastery(subject, p);
  const bankTotal = useMemo(
    () => chapters.reduce((n, c) => n + chapterBankStats(c.id).total, 0),
    [chapters],
  );

  const grouped = useMemo(() => {
    const map = new Map<string, BundleChapter[]>();
    for (const c of chapters) {
      const k = c.group || '未分组';
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(c);
    }
    return [...map.entries()];
  }, [chapters]);

  const openChapter = openId ? (chapters.find((x) => x.id === openId) ?? null) : null;

  /** 关卡 CTA：概念/演练锁定本章进题库；BOSS 直接打开首领题 */
  const goStage = (chapterId: string, stage: StageView) => {
    if (stage.key === 'boss' && stage.questionId) {
      challengeQuestion(stage.questionId);
      return;
    }
    focusChapter(chapterId);
    onNavigate?.('lab');
  };

  return (
    <div className="km-view">
      <section className="km-card">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>知识试炼区 · {subjectLabel(subject)}</h3>
          <span className="pct">
            {doneCount} / {chapters.length} 章全通
          </span>
        </div>
        <div className="km-mini-bar">
          <i style={{ width: `${Math.max(avg, 1)}%` }} />
        </div>
        <div className="km-stage-legend">
          <span className="km-hint" style={{ marginTop: 0 }}>
            学科平均掌握 <b>{avg}%</b>
          </span>
          <span className="km-legend-item">
            <i className="km-pip on">①</i> 概念 30
          </span>
          <span className="km-legend-item">
            <i className="km-pip on">②</i> 演练 30
          </span>
          <span className="km-legend-item">
            <i className="km-pip on">③</i> BOSS 40
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginTop: 10 }}>
          <SubjectSwitch />
          <span className="km-hint" style={{ marginTop: 0 }}>
            切换学科后，章节、资源与题目都会跟着换。
          </span>
        </div>
      </section>

      {chapters.length === 0 && (
        <div className="km-card km-empty">
          <b>这个学科还没有章节清单</b>
          <span>content/{subject}/_manifest.json 缺失或为空。</span>
        </div>
      )}

      {chapters.length > 0 && (
        <div className="learn-bank-bar">
          <span>
            本学科共 <b>{bankTotal}</b> 道题，按章节做或整科刷都行。
          </span>
          <button
            type="button"
            className="km-btn km-btn-sm km-btn-primary"
            onClick={() => {
              focusChapter(null);
              onNavigate?.('lab');
            }}
          >
            打开题库
          </button>
        </div>
      )}

      {grouped.map(([group, list]) => (
        <section className="km-card" key={group}>
          <h3>
            {groups[group] ?? group}
            <span className="km-tag km-tag-gray" style={{ marginLeft: 'auto' }}>
              {list.length} 章
            </span>
          </h3>
          <div className="km-map">
            {list.map((c) => {
              const mastery = chapterMastery(c.id, p);
              const stages = chapterStages(c.id, p);
              const open = openId === c.id;
              const st = chapterBankStats(c.id);
              const deps = chapterDeps(c.id);
              const unlocked = isUnlocked(c.id, p);
              const blocked = !unlocked;
              const blockingDeps = deps.filter((d) => masteryOfChapter(d, p) < UNLOCK_MASTERY);
              return (
                <div
                  key={c.id}
                  className={`km-node${mastery >= 100 ? ' done' : ''}${mastery > 0 ? ' partial' : ''}${open ? ' current' : ''}${blocked ? ' locked' : ''}`}
                >
                  <button
                    type="button"
                    className="km-node-dot"
                    aria-label={mastery >= 100 ? '已三关全通' : `掌握度 ${mastery}%`}
                    onClick={() => setOpenId(open ? null : c.id)}
                    title={`掌握度 ${mastery}%（点开看三关）`}
                  >
                    {mastery >= 100 ? '✓' : String(c.order).padStart(2, '0')}
                  </button>
                  <button
                    type="button"
                    className="km-node-main"
                    onClick={() => setOpenId(open ? null : c.id)}
                    style={{ textAlign: 'left', background: 'none' }}
                  >
                    <b>
                      {c.title}
                      {mastery >= 100 && (
                        <span className="km-tag km-tag-ok" style={{ marginLeft: 8 }}>
                          已掌握
                        </span>
                      )}
                      {mastery > 0 && mastery < 100 && (
                        <span className="km-tag km-tag-lv" style={{ marginLeft: 8 }}>
                          {mastery}%
                        </span>
                      )}
                      {blocked && (
                        <span
                          className="km-tag km-tag-lock"
                          style={{ marginLeft: 8 }}
                          title={`前置章节掌握度需达到 ${UNLOCK_MASTERY}% 才能解锁`}
                        >
                          未解锁 · 需先过：{blockingDeps.map((d) => chapterName(d)).join('、')}
                        </span>
                      )}
                      {st.total > 0 && (
                        <span className="km-tag km-tag-gray" style={{ marginLeft: 8 }}>
                          {st.total} 题
                        </span>
                      )}
                    </b>
                    <span>{c.summary}</span>
                  </button>
                  <span className="km-pips" aria-label="三关状态">
                    {stages.map((s) => (
                      <i
                        key={s.key}
                        className={`km-pip${s.done ? ' on' : ''}`}
                        title={`${s.label}：${s.done ? '已通过' : s.hint}`}
                      >
                        {s.icon}
                      </i>
                    ))}
                  </span>
                  <span className="km-tag km-tag-gray">{open ? '收起' : '展开'}</span>
                </div>
              );
            })}
          </div>
        </section>
      ))}

      {openChapter &&
        (() => {
          const c = openChapter;
          const st = chapterBankStats(c.id);
          const stages = chapterStages(c.id, p);
          const mastery = chapterMastery(c.id, p);
          const deps = chapterDeps(c.id);
          return (
            <section className="km-card km-chapter-open" style={{ borderColor: 'var(--km-glow)' }}>
              <div className="km-cont-top">
                <h3 style={{ margin: 0 }}>{c.title}</h3>
                <span className={`km-mastery-chip${mastery >= 100 ? ' done' : ''}`}>掌握 {mastery}%</span>
              </div>
              <div className="km-mastery-bar" aria-label={`掌握度 ${mastery}%`}>
                {stages.map((s) => (
                  <i
                    key={s.key}
                    className={`km-mastery-seg${s.done ? ' on' : ''}`}
                    style={{ flexGrow: s.weight }}
                    title={`${s.label} ${s.weight} 分`}
                  />
                ))}
              </div>

              <p style={{ margin: '12px 0 0', color: 'var(--km-ink-soft)', fontSize: 13, lineHeight: 1.8 }}>
                {c.summary}
              </p>
              {deps.length > 0 && (
                <p className="km-hint">
                  前置：
                  {deps.map((d, i) => {
                    const m = masteryOfChapter(d, p);
                    return (
                      <span key={d}>
                        {i > 0 ? ' / ' : ''}
                        <span className={m >= 60 ? 'km-dep-ok' : 'km-dep-bad'}>
                          {chapterName(d)}（{m}%）
                        </span>
                      </span>
                    );
                  })}
                </p>
              )}

              {/* ── 三关 ─────────────────────────────────────────────── */}
              <div className="km-stages">
                {stages.map((s) => (
                  <div key={s.key} className={`km-stage${s.done ? ' done' : ''}`}>
                    <div className="km-stage-head">
                      <i className={`km-pip${s.done ? ' on' : ''}`}>{s.icon}</i>
                      <b>{s.label}</b>
                      <span className="km-stage-weight">{s.weight} 分</span>
                      {s.done && <span className="km-tag km-tag-ok">已通过</span>}
                    </div>
                    <div className="km-stage-bar">
                      <i style={{ width: `${s.need ? (s.got / s.need) * 100 : 0}%` }} />
                    </div>
                    <p className="km-stage-desc">{STAGE_META[s.key].desc}</p>
                    <p className="km-stage-hint">{s.hint}</p>
                    {s.blockers.length > 0 && (
                      <ul className="km-stage-blockers">
                        {s.blockers.map((b) => (
                          <li key={b}>{b}</li>
                        ))}
                      </ul>
                    )}
                    <button
                      type="button"
                      className={`km-btn km-btn-sm ${s.done ? 'km-btn-ghost' : 'km-btn-primary'}`}
                      onClick={() => goStage(c.id, s)}
                    >
                      {s.done ? '再过一遍' : s.key === 'boss' ? '打首领' : '去攻这一关'}
                    </button>
                  </div>
                ))}
              </div>

              {c.github.length > 0 && (
                <>
                  <div className="km-hint" style={{ marginTop: 12, fontWeight: 600 }}>
                    延伸仓库（GitHub 实测）
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
                    {c.github.map((repo, i) => (
                      <a
                        key={repo}
                        href={`https://github.com/${repo}`}
                        target="_blank"
                        rel="noreferrer"
                        className="km-repo"
                      >
                        <b>{repo}</b>
                        <span>★ {(c.github_stars[i] ?? 0).toLocaleString('zh-CN')}</span>
                      </a>
                    ))}
                  </div>
                </>
              )}
              {c.books.length > 0 && <p className="km-hint">推荐：{c.books.join('；')}</p>}

              {/* ── 本章题目 ─────────────────────────────────────────── */}
              <div className="learn-bank">
                <div className="learn-bank-head">
                  <b>本章题目</b>
                  <span>
                    {st.total} 题
                    {st.judgeable > 0 ? ` · 可直接判 ${st.judgeable} 题` : ''}
                  </span>
                </div>
                {st.total === 0 ? (
                  <p className="km-hint" style={{ margin: 0 }}>
                    这一章暂未配套练习题。
                  </p>
                ) : (
                  <>
                    <div className="learn-bank-chips">
                      {TYPE_ORDER.filter((t) => (st.byType[t] ?? 0) > 0).map((t) => (
                        <span key={t} className={`bank-type t-${t}`}>
                          {TYPE_META[t].short} {st.byType[t]}
                        </span>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="km-btn km-btn-sm km-btn-primary"
                        onClick={() => {
                          focusChapter(c.id);
                          onNavigate?.('lab');
                        }}
                      >
                        做本章这 {st.total} 题
                      </button>
                      <button
                        type="button"
                        className="km-btn km-btn-sm km-btn-ghost"
                        onClick={() => {
                          if (masteryOfChapter(c.id, p) === 0) return;
                          resetChapter(c.id);
                        }}
                        disabled={mastery === 0}
                        title={mastery === 0 ? '这一章还没有任何记录' : '清空本章三关、作答记录与怪物，重新打一遍'}
                      >
                        重置本章
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* ── 本章总结（仅三关全通后可见，P3） ───────────── */}
              {(() => {
                const sum = buildChapterSummary(c.id, p);
                if (!sum) {
                  return (
                    <p className="km-summary-locked">
                      通关三关（概念 / 演练 / BOSS 全绿）后，这里会解锁「本章总结 · 7 维表」与一键导出 Markdown。
                    </p>
                  );
                }
                return (
                  <ChapterSummaryPanel
                    summary={sum}
                    content={contentOf(c.id)}
                    copied={copiedId === c.id}
                    onCopy={() => handleCopySummary(sum)}
                  />
                );
              })()}
            </section>
          );
        })()}
    </div>
  );
}

/* ── 本章总结 · 7 维表面板（P3） ─────────────────────────────
 * 仅当章 mastery===100（buildChapterSummary 返回非 null）时渲染。
 * 数据来自 chapterSummary.ts 的纯函数层，本组件只负责呈现与导出。
 */

function SummaryRow({ label, dim, extra }: { label: string; dim: SummaryDim; extra?: string }) {
  return (
    <tr>
      <td className="km-summary-dim">{label}</td>
      <td className="km-summary-num">
        {extra ? `${dim.done ?? dim.count}/${dim.required ?? dim.count} ${extra}` : `${dim.count} 条`}
      </td>
      <td>
        <span className={`km-summary-badge ${dim.ok ? 'ok' : 'warn'}`}>
          {dim.ok ? '✓ 达标' : '⚠ 待补'}
        </span>
      </td>
      <td>
        {dim.items.length ? (
          <ul className="km-summary-items">
            {dim.items.map((it, i) => (
              <li key={i}>{it}</li>
            ))}
          </ul>
        ) : (
          <span className="km-summary-empty">—</span>
        )}
      </td>
    </tr>
  );
}

function SummarySection({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="km-summary-sec">
      <b>{title}</b>
      <ul className="km-summary-items">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

export function ChapterSummaryPanel({
  summary,
  content,
  copied,
  onCopy,
}: {
  summary: ChapterSummary;
  content: ChapterContent | undefined;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <div className="km-summary">
      <div className="km-cont-top">
        <h3 style={{ margin: 0 }}>本章总结 · 7 维表</h3>
        <button type="button" className="km-btn km-btn-sm km-btn-ghost" onClick={onCopy}>
          {copied ? '已复制 ✓' : '复制为 Markdown 表格'}
        </button>
      </div>
      <p className="km-hint" style={{ marginTop: 8 }}>
        掌握度 100% 已解锁。下表逐维对照内容标准（概念 / 易错 / 面试题 ≥ 3，例题 ≥ 5，项目 ≥ 1）。
      </p>
      <div className="km-summary-table-wrap">
        <table className="km-summary-table">
          <thead>
            <tr>
              <th>维度</th>
              <th>数量 / 状态</th>
              <th>达标</th>
              <th>关键条目（前 3）</th>
            </tr>
          </thead>
          <tbody>
            <SummaryRow label="目标 Goals" dim={summary.goals} />
            <SummaryRow label="核心概念 Concepts" dim={summary.concepts} />
            <SummaryRow label="易错点 Pitfalls" dim={summary.pitfalls} />
            <SummaryRow label="例题 Exercises" dim={summary.exercises} extra="已答对" />
            <SummaryRow label="面试 / 真题 Interview" dim={summary.interview} />
            <SummaryRow label="实战 Project" dim={summary.project} />
            <tr className="km-summary-total">
              <td>总掌握度</td>
              <td>{summary.totalMastery}%</td>
              <td>
                <span className="km-summary-badge ok">✓</span>
              </td>
              <td>三关全通 · BOSS 通过</td>
            </tr>
          </tbody>
        </table>
      </div>
      {content && (
        <details className="km-summary-detail">
          <summary>展开全部条目（{content.goals.length + content.concepts.length + content.pitfalls.length + content.interviews.length + content.projects.length} 条）</summary>
          <SummarySection title="目标" items={content.goals} />
          <SummarySection title="核心概念" items={content.concepts} />
          <SummarySection title="易错点" items={content.pitfalls} />
          <SummarySection title="面试 / 真题" items={content.interviews} />
          <SummarySection title="实战项目" items={content.projects} />
        </details>
      )}
    </div>
  );
}
