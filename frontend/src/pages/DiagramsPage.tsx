/**
 * DiagramsPage.tsx —— 图表总览（按逻辑学习链）
 *
 * 把各章 concept 里用 ```` ```text ```` 绘制的 ASCII/Unicode 结构图集中成一张可浏览的图谱，
 * 顺序沿「基础 → 语言 → 数据 → 存储 → 框架 → 中间件 → 大数据 → 工具 → ML → AI → 全栈 → 智能体」铺开。
 *
 * 设计（沿用 design-taste-frontend 的构图原则，不破坏凯喵蓝白品牌）：
 *  - 左侧「学习脊」(spine)：15 个学科按学习链排布，色点即学科主题色；点击跳转、滚动联动高亮，是页面的「活物」。
 *  - 实时搜索：按图名 / 章节 / 说明过滤，整页与脊的计数同步。
 *  - 每学科一块整版：学科名 + 在学习链里的定位 + 该学科下的结构图卡片（主题色带 + 说明 + 源码）。
 *  - 入场：滚动进入视口时整块上浮淡入，卡片按序错峰；hover 上浮与主题色描边；尊重 prefers-reduced-motion。
 */
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';

import { DIAGRAM_SUBJECTS } from '../data/diagrams';
import type { DiagramSubject } from '../data/diagrams';
import './DiagramsPage.css';

type CSSVars = React.CSSProperties & Record<`--${string}`, string>;

export function DiagramsPage() {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState('');
  const [anim, setAnim] = useState(false);
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});

  const q = query.trim().toLowerCase();
  const filtered = useMemo<DiagramSubject[]>(() => {
    if (!q) return DIAGRAM_SUBJECTS;
    return DIAGRAM_SUBJECTS.map((s) => ({
      ...s,
      entries: s.entries.filter(
        (e) =>
          e.title.toLowerCase().includes(q) ||
          e.desc.toLowerCase().includes(q) ||
          e.chapter.toLowerCase().includes(q),
      ),
    })).filter((s) => s.entries.length > 0);
  }, [q]);

  const totalShown = useMemo(
    () => filtered.reduce((n, s) => n + s.entries.length, 0),
    [filtered],
  );

  // 进入视口后才打开动画类，避免无 JS 时内容隐藏（渐进增强）
  useLayoutEffect(() => {
    setAnim(true);
  }, []);

  // 滚动联动：section 进入视口→点亮对应脊项；[data-reveal] 元素→揭幕上浮
  useEffect(() => {
    const nodes = Array.from(
      document.querySelectorAll<HTMLElement>('[data-reveal]'),
    );
    if (typeof IntersectionObserver === 'undefined') {
      nodes.forEach((n) => n.classList.add('is-revealed'));
      return;
    }
    // 揭幕：进入视口即上浮淡入，之后不再观察
    const rObs = new IntersectionObserver(
      (entries) => {
        for (const en of entries) {
          if (en.isIntersecting) {
            en.target.classList.add('is-revealed');
            rObs.unobserve(en.target);
          }
        }
      },
      { rootMargin: '0px 0px -6% 0px', threshold: 0.04 },
    );
    nodes.forEach((n) => rObs.observe(n));
    // 脊联动：section 顶到视口上部时点亮对应脊项
    const sObs = new IntersectionObserver(
      (entries) => {
        for (const en of entries) {
          if (en.isIntersecting) {
            const key = (en.target as HTMLElement).dataset.subject;
            if (key) setActive(key);
          }
        }
      },
      { rootMargin: '-28% 0px -62% 0px', threshold: 0 },
    );
    for (const el of Object.values(sectionRefs.current)) {
      if (el) sObs.observe(el);
    }
    return () => {
      rObs.disconnect();
      sObs.disconnect();
    };
  }, [filtered]);

  const scrollToSubject = (key: string) => {
    const el = sectionRefs.current[key];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setActive(key);
  };

  const spineItems = DIAGRAM_SUBJECTS.map((s) => {
    const hit = filtered.find((f) => f.key === s.key);
    return { key: s.key, name: s.name, hue: s.hue, count: hit ? hit.entries.length : 0 };
  });

  return (
    <div className={`dgv-root${anim ? ' dgv-anim' : ''}`}>
      <header className="dgv-head">
        <div className="dgv-head-main">
          <h1 className="dgv-title">图表总览</h1>
          <p className="dgv-lede">
            {totalShown} 张结构图，沿 {filtered.length} 个学科的学习链，从地基一直铺到会干活的智能体。
            {q && <span className="dgv-lede-q"> · 命中「{query.trim()}」</span>}
          </p>
        </div>
        <label className="dgv-search">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <line x1="16.5" y1="16.5" x2="21" y2="21" />
          </svg>
          <input
            type="search"
            value={query}
            placeholder="搜索图名 / 章节 / 说明…"
            onChange={(e) => setQuery(e.target.value)}
            aria-label="搜索图表"
          />
        </label>
      </header>

      <div className="dgv-body">
        <nav className="dgv-spine" aria-label="学习链">
          <span className="dgv-spine-cap">学习链</span>
          {spineItems.map((it) => {
            const disabled = it.count === 0;
            return (
              <button
                type="button"
                key={it.key}
                className={`dgv-spine-item${active === it.key && !disabled ? ' on' : ''}`}
                style={{ '--hue': it.hue, '--hue-a': `${it.hue}26` } as CSSVars}
                disabled={disabled}
                onClick={() => scrollToSubject(it.key)}
              >
                <span className="dgv-dot" />
                <span className="dgv-spine-name">{it.name}</span>
                <span className="dgv-spine-n">{it.count}</span>
              </button>
            );
          })}
        </nav>

        <div className="dgv-content">
          {filtered.length === 0 && (
            <div className="dgv-empty">没有命中「{query.trim()}」的图，换个关键词试试。</div>
          )}
          {filtered.map((s) => (
            <section
              key={s.key}
              className="dgv-subject"
              data-subject={s.key}
              data-reveal
              ref={(el) => {
                sectionRefs.current[s.key] = el;
              }}
              style={{ '--hue': s.hue, '--hue-a': `${s.hue}24` } as CSSVars}
            >
              <header className="dgv-subject-head">
                <span className="dgv-subject-bar" />
                <div className="dgv-subject-titles">
                  <h2 className="dgv-subject-name">{s.name}</h2>
                  <p className="dgv-subject-note">{s.note}</p>
                </div>
                <span className="dgv-subject-count">{s.entries.length} 张</span>
              </header>

              <div className="dgv-cards">
                {s.entries.map((e, i) => (
                  <article
                    className="dgv-card"
                    data-reveal
                    key={`${e.chapter}-${i}`}
                    style={{ transitionDelay: `${Math.min(i, 9) * 55}ms` } as CSSVars}
                  >
                    <span className="dgv-card-band" />
                    <div className="dgv-card-head">
                      <span className="dgv-ch">{e.chapter}</span>
                      <h3 className="dgv-card-title">{e.title}</h3>
                    </div>
                    {e.desc && <p className="dgv-card-desc">{e.desc}</p>}
                    <pre className="dgv-code">{e.code}</pre>
                    <div className="dgv-card-foot">{e.source}</div>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}

export default DiagramsPage;
