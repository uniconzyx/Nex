/**
 * ProjectsPage.tsx —— BOSS项目实战（就业级项目库）
 *
 * 数据源改为**打包进客户端的 BUNDLE**，不再依赖后端：
 *   .exe / .apk 都是离线客户端，不能要求用户先起 FastAPI + PostgreSQL；
 *   打包后两端读到的是同一份常量，功能与内容天然一致。
 *
 * 后端 `/api/v1/career-projects` 仍然保留，用于将来做账号同步与增量更新，
 * 但页面在无网、无库的情况下必须完整可用。
 *
 * 通关状态写本地进度（progress.ts），影响首页 EXP 与右栏凯喵。
 *
 * 【P2：项目有了前置章节】
 *   每个项目带 `requires`（由 scripts/gen_graph.py 按 stack / learn 与章节标题的
 *   术语重合度算出）。门槛是「相关章节掌握度 ≥ 60」= 概念 + 演练两关。
 *
 *   注意这是**建议门槛，不是禁止令**：前置没达标时仍然可以标记通关
 *   （你在别处做过这个项目是合理的），但页面会明确写清「还缺哪几章」，
 *   免得把「项目做完了、但基础章节还是 0」当成正常状态。
 */
import { useMemo, useState } from 'react';

import { BUNDLE } from '../data/bundle';
import { subjectLabel, useSubject } from '../lib/subject';
import { toggleProject, useProgress } from '../lib/progress';
import { focusChapter } from '../lib/exerciseBank';
import { projectGate, UNLOCK_MASTERY } from '../lib/graph';
import type { KmPage } from '../lib/nav';

type TierKey = 't1' | 't2' | 't3' | 't4';

const TIERS: { key: TierKey; label: string; hint: string }[] = [
  { key: 't1', label: 'T1 能跑起来', hint: '4-12h · 跑通并改一处小功能' },
  { key: 't2', label: 'T2 能独立写', hint: '12-30h · 脱教程做同构小系统' },
  { key: 't3', label: 'T3 能讲原理', hint: '30-60h · 读源码 + 改造 + 压测' },
  { key: 't4', label: 'T4 能进简历', hint: '60-120h · 可量化结果 + 个人贡献边界' },
];

const TIER_SHORT: Record<TierKey, string> = {
  t1: 'T1 入门',
  t2: 'T2 进阶',
  t3: 'T3 核心',
  t4: 'T4 门槛',
};

const TRACK_LABEL: Record<string, string> = Object.fromEntries(
  BUNDLE.projects.tracks.map((t) => [t.key, t.label]),
);

function fmtStars(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)} 万`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export function ProjectsPage({ onNavigate }: { onNavigate?: (p: KmPage) => void } = {}) {
  const [subject, changeSubject] = useSubject();
  const p = useProgress();
  const [activeTrack, setActiveTrack] = useState<string>(subject);
  const [activeTier, setActiveTier] = useState<TierKey | ''>('');
  const [keyword, setKeyword] = useState('');
  const [query, setQuery] = useState('');
  const [detailSlug, setDetailSlug] = useState<string | null>(null);
  /** 只看「前置已达标」的项目：默认关闭，否则新玩家会看到一张空页 */
  const [onlyOpen, setOnlyOpen] = useState(false);

  const tracks = BUNDLE.projects.tracks;

  const cards = useMemo(() => {
    const q = query.trim().toLowerCase();
    return BUNDLE.projects.items.filter((c) => {
      if (activeTrack && c.track !== activeTrack) return false;
      if (activeTier && c.tier !== activeTier) return false;
      if (onlyOpen && !projectGate(c.slug, p).ok) return false;
      if (q) {
        const hay = `${c.title} ${c.repo} ${c.summary} ${c.stack.join(' ')}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [activeTrack, activeTier, query, onlyOpen, p]);

  const detail = detailSlug ? BUNDLE.projects.items.find((i) => i.slug === detailSlug) ?? null : null;
  const detailGate = detail ? projectGate(detail.slug, p) : null;
  const doneCount = p.doneProjects.length;

  const activeLabel = activeTrack ? (TRACK_LABEL[activeTrack] ?? activeTrack) : '全部学科';

  return (
    <div className="cp-wrap">
      <header className="cp-head">
        <div>
          <h2 className="cp-title">BOSS 项目实战</h2>
          <p className="cp-sub">
            覆盖 {tracks.length} 个学科 · 共 {BUNDLE.projects.total} 个真实开源项目 ·{' '}
            {BUNDLE.projects.hours}h · 已通关 {doneCount} · 按 T1→T4 四层梯度排布，元数据来自 GitHub 实测
          </p>
        </div>
        <form
          className="cp-search"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(keyword);
          }}
        >
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜项目名 / 仓库 / 关键词"
            aria-label="搜索项目"
          />
          <button type="submit">搜索</button>
        </form>
      </header>

      <div className="cp-chips cp-tier-row" role="tablist" aria-label="学科筛选">
        <span className="cp-tier-label">筛选</span>
        <button
          type="button"
          role="tab"
          aria-selected={activeTrack === ''}
          className={`cp-chip${activeTrack === '' ? ' on' : ''}`}
          onClick={() => setActiveTrack('')}
        >
          全部学科
        </button>
        {tracks.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={activeTrack === t.key}
            className={`cp-chip${activeTrack === t.key ? ' on' : ''}`}
            onClick={() => {
              setActiveTrack(t.key);
              // 同时写全局学科：切到学习页时内容跟着走
              changeSubject(t.key);
            }}
          >
            {t.label}
            <span className="cp-chip-n">{t.n}</span>
          </button>
        ))}
      </div>

      <div className="cp-chips cp-tier-row" role="tablist" aria-label="能力梯度筛选">
        <span className="cp-tier-label">梯度</span>
        <button
          type="button"
          role="tab"
          aria-selected={activeTier === ''}
          className={`cp-chip${activeTier === '' ? ' on' : ''}`}
          onClick={() => setActiveTier('')}
        >
          全部梯度
        </button>
        {TIERS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            title={t.hint}
            aria-selected={activeTier === t.key}
            className={`cp-chip${activeTier === t.key ? ' on' : ''}`}
            onClick={() => setActiveTier(t.key)}
          >
            {t.label}
          </button>
        ))}
        <label className="cp-open-only" title={`只看前置章节掌握度 ≥ ${UNLOCK_MASTERY} 的项目`}>
          <input
            type="checkbox"
            checked={onlyOpen}
            onChange={(e) => setOnlyOpen(e.target.checked)}
          />
          <span>只看前置达标</span>
        </label>
      </div>

      {cards.length === 0 && (
        <div className="cp-state">
          <b>
            {activeLabel}
            {activeTier ? ` · ${TIER_SHORT[activeTier]}` : ''} 下没有匹配项目
          </b>
          <p>
            {activeTier
              ? `「${subjectLabel(activeTrack || subject)}」这一档还没铺内容，换个梯度或看全部学科。`
              : '换个关键词，或点「全部学科」看看。'}
          </p>
          <div className="cp-state-actions">
            {activeTier && (
              <button type="button" onClick={() => setActiveTier('')}>
                清除梯度筛选
              </button>
            )}
            {activeTrack && (
              <button type="button" onClick={() => setActiveTrack('')}>
                看全部学科
              </button>
            )}
            {query && (
              <button
                type="button"
                onClick={() => {
                  setKeyword('');
                  setQuery('');
                }}
              >
                清除关键词
              </button>
            )}
          </div>
        </div>
      )}

      {cards.length > 0 && (
        <div className="cp-grid">
          {cards.map((c) => {
            const done = p.doneProjects.includes(c.slug);
            const gate = projectGate(c.slug, p);
            const ready = gate.requires.filter((r) => r.ok).length;
            return (
              <button
                key={c.slug}
                type="button"
                className="cp-card"
                onClick={() => setDetailSlug(c.slug)}
              >
                <div className="cp-card-top">
                  <span className={`cp-tier ${c.tier}`} title={TIERS.find((t) => t.key === c.tier)?.hint}>
                    {TIER_SHORT[c.tier]}
                  </span>
                  {!activeTrack && <span className="cp-track">{TRACK_LABEL[c.track]}</span>}
                  {done && <span className="cp-done-tag">✓ 已通关</span>}
                  {!done && gate.ok && <span className="cp-ready-tag">前置已达标</span>}
                  {!done && !gate.ok && (
                    <span className="cp-lock-tag" title={`还缺 ${gate.missing.length} 章`}>
                      🔒 {ready}/{gate.requires.length}
                    </span>
                  )}
                  <span className="cp-stars">★ {fmtStars(c.stars)}</span>
                </div>
                <h3>{c.title}</h3>
                <p className="cp-card-desc">{c.summary}</p>
                <div className="cp-tags">{c.stack.slice(0, 4).map((s) => <span key={s}>{s}</span>)}</div>
                <div className="cp-card-foot">
                  <code>{c.repo}</code>
                  <span>
                    {c.hours}h · {c.lang || '—'}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {detail && detailGate && (
        <div className="cp-detail-mask" onClick={() => setDetailSlug(null)}>
          <aside
            className="cp-detail"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="项目详情"
          >
            <button
              type="button"
              className="cp-detail-close"
              onClick={() => setDetailSlug(null)}
              aria-label="关闭"
            >
              ✕
            </button>

            <div className="cp-detail-head">
              <span className={`cp-tier ${detail.tier}`}>{TIER_SHORT[detail.tier]}</span>
              <span className="cp-track">{TRACK_LABEL[detail.track]}</span>
              {detail.archived && <span className="cp-archived">已归档</span>}
            </div>
            <h2>{detail.title}</h2>
            <p className="cp-detail-summary">{detail.summary}</p>

            <div className="cp-meta">
              <span>★ {fmtStars(detail.stars)}</span>
              <span>预计投入 {detail.hours}h</span>
              <span>{detail.lang || '—'}</span>
              <span>{detail.license || '无许可证'}</span>
              <span>最近提交 {detail.pushed || '—'}</span>
            </div>

            <a className="cp-repo-link" href={detail.url} target="_blank" rel="noreferrer">
              {detail.repo} ↗
            </a>

            <section>
              <h4>为什么值得做</h4>
              <p>{detail.career}</p>
            </section>

            <section>
              <h4>能学到什么</h4>
              <ul>
                {detail.learn.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </section>

            <section>
              <h4>前置章节（{detailGate.requires.filter((r) => r.ok).length}/{detailGate.requires.length} 达标）</h4>
              <ul className="cp-requires">
                {detailGate.requires.map((r) => (
                  <li key={r.id} className={r.ok ? 'ok' : 'bad'}>
                    <button
                      type="button"
                      onClick={() => {
                        focusChapter(r.id);
                        setDetailSlug(null);
                        onNavigate?.('learn');
                      }}
                      title="去学这一章"
                    >
                      {r.title}
                    </button>
                    <span className={`cp-mastery${r.ok ? ' ok' : ''}`}>{r.mastery}%</span>
                  </li>
                ))}
              </ul>
              <p className="cp-hint">
                {detailGate.ok
                  ? `这些章节都已到 ${UNLOCK_MASTERY} 掌握度（概念 + 演练两关），可以开始动手了。`
                  : `还差 ${detailGate.missing.length} 章没到 ${UNLOCK_MASTERY} 掌握度。点章节名可以直接跳去学；照样能标记通关，只是别把「项目做完、基础还是 0」当常态。`}
              </p>
            </section>

            <section>
              <h4>复现步骤</h4>
              <ol className="cp-steps">
                {detail.steps.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            </section>

            <section>
              <h4>验收标准</h4>
              <ul className="cp-accept">
                {detail.accept.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </section>

            <section>
              <h4>面试可讲点</h4>
              <ul className="cp-interview">
                {detail.interview.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </section>

            <div className="cp-detail-foot">
              <button
                type="button"
                className={`km-btn km-btn-sm ${p.doneProjects.includes(detail.slug) ? 'km-btn-ghost' : 'km-btn-primary'}`}
                onClick={() => toggleProject(detail.slug)}
              >
                {p.doneProjects.includes(detail.slug) ? '取消已通关' : '标记已通关（+30 EXP）'}
              </button>
              <span className="cp-hint">
                {detailGate.ok
                  ? '通关记录只存本机，首页 EXP 与右栏凯喵会同步变化。'
                  : `前置还差 ${detailGate.missing.length} 章；现在标记只记项目本身，不会补章节掌握度。`}
              </span>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

export default ProjectsPage;
