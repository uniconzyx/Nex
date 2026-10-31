/**
 * EmploymentPage.tsx —— 就业 · 求职作战室（P5+）
 * ============================================================================
 * 就业页拆成三块，对应求职链路的三件事：
 *   1) 八股     —— 面试知识点图谱（四区资源 + Agent 专项，保留原 EmploymentPage 内容）
 *   2) 简历打磨 —— 自检清单 + STAR + 分模块写法 + 雷区 + 模板/ATS（本项目新增）
 *   3) 项目     —— 轻量入口：聚焦「全栈开发 agent 开发」，卡片 + 跳转 BOSS 实战库
 *
 * 路由：#employment
 * 三块都在同一页切换（tablist），不新增路由；「项目」只做入口，重活在 BOSS 项目实战库。
 * ============================================================================
 */
import { useMemo, useState, type CSSProperties } from 'react';
import { buildInterviewGraph, interviewGraphToMarkdown } from '../lib/employment';
import {
  RESUME_LEDIT,
  RESUME_CHECKLIST,
  RESUME_STAR,
  RESUME_MODULES,
  RESUME_PITFALLS,
  RESUME_TEMPLATES,
} from '../data/resume';
import { AGENT_PROJECTS, AGENT_PATH, AGENT_AUDIENCES } from '../data/agentProjects';
import type { KmPage } from '../lib/nav';
import './EmploymentPage.css';

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

type EmpTab = 'bagua' | 'resume' | 'project';

const TABS: { key: EmpTab; label: string; hint: string }[] = [
  { key: 'bagua', label: '八股', hint: '面试知识点图谱' },
  { key: 'resume', label: '简历打磨', hint: '自检 + STAR + 写法' },
  { key: 'project', label: '项目', hint: '全栈 Agent 开发入口' },
];

/** 八股面板：原 EmploymentPage 的图谱内容 */
function BaguaPanel() {
  const g = useMemo(() => buildInterviewGraph(), []);
  const [copied, setCopied] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);

  const onExport = async () => {
    await copyMarkdown(interviewGraphToMarkdown(g));
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const toggle = (id: string) => setOpenId((cur) => (cur === id ? null : id));

  return (
    <div className="emp-bagua">
      <header className="emp-head">
        <div>
          <h1>{g.name}</h1>
          <p className="emp-lede">
            四区 <b>{g.zones.length}</b> · 资源节点 <b>{g.totalSources}</b> · Agent 专项{' '}
            <b>{g.agentModules.length}</b> 模块 —— 按「区 / 专轨 / 模块」分区整理（八股归就业）
          </p>
        </div>
        <button type="button" className="km-btn km-btn-sm km-btn-ghost" onClick={onExport}>
          {copied ? '已复制 ✓' : '导出八股分区 Markdown'}
        </button>
      </header>

      {g.zones.map((z) => (
        <section
          className="km-card emp-zone"
          key={z.zone}
          style={{ '--zone': z.color } as CSSProperties}
        >
          <div className="km-cont-top">
            <span className="emp-zone-badge" style={{ background: z.color }}>
              {z.zone}
            </span>
            <h3 style={{ margin: 0 }}>{z.name}</h3>
            <span className="km-tag km-tag-gray">{z.count} 资源</span>
          </div>
          <p className="km-hint" style={{ marginTop: 6 }}>
            {z.desc}
          </p>
          <div className="emp-grid">
            {z.sources.map((s) => {
              const active = openId === s.id;
              return (
                <button
                  type="button"
                  key={s.id}
                  className={`emp-node${active ? ' active' : ''}`}
                  style={{ '--zone': z.color } as CSSProperties}
                  onClick={() => toggle(s.id)}
                  title={`${s.name} · ${s.role}`}
                >
                  <b>{s.name}</b>
                  <span className="emp-node-type">{s.type === 'repo' ? '仓库' : '站点'}</span>
                  {active && (
                    <span className="emp-node-detail">
                      <span className="emp-node-role">{s.role}</span>
                      {s.covers && <span className="emp-node-cover">覆盖：{s.covers}</span>}
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        打开资源 ↗
                      </a>
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </section>
      ))}

      <section className="km-card emp-agent">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>Agent 八股专项（独立体系）</h3>
          <span className="km-tag km-tag-gray">{g.agentModules.length} 模块</span>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          工程落地 / 系统设计 / 生产实践 —— 以 Prompt→Context→Agent→Harness 四层骨架为底层学科
        </p>
        <div className="emp-layers">
          {g.agentLayers.map((l) => (
            <span className="emp-layer" key={l.layer} title={`${l.desc}（${l.ref}）`}>
              {l.layer}
            </span>
          ))}
        </div>
        <table className="emp-modtable">
          <thead>
            <tr>
              <th>模块</th>
              <th>题库来源</th>
              <th>规模 / 特色</th>
            </tr>
          </thead>
          <tbody>
            {g.agentModules.map((m) => (
              <tr key={m.module}>
                <td>{m.module}</td>
                <td className="emp-mod-src">{m.sources.join('、')}</td>
                <td>{m.scale}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="emp-papers">
          <span className="emp-papers-title">模拟考卷（虚拟试卷）</span>
          {g.mockPapers.map((p) => (
            <span className="emp-paper" key={p.level}>
              <b>{p.level}</b> {p.rule}（{p.source}）
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}

/** 简历打磨面板：自检清单 + STAR + 分模块写法 + 雷区 + 模板/ATS */
function ResumePanel() {
  const [checked, setChecked] = useState<Set<string>>(() => new Set());
  const toggleItem = (id: string) =>
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const done = checked.size;
  const total = RESUME_CHECKLIST.length;
  const pct = Math.round((done / total) * 100);

  return (
    <div className="emp-resume">
      <header className="emp-head">
        <div>
          <h1>简历打磨</h1>
          <p className="emp-lede">{RESUME_LEDIT}</p>
        </div>
      </header>

      {/* 自检清单（可勾选，本地状态） */}
      <section className="km-card rp-check">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>简历自检清单</h3>
          <span className="km-tag km-tag-gray">
            {done}/{total} · {pct}%
          </span>
        </div>
        <div className="rp-progress" aria-hidden>
          <i style={{ width: `${pct}%` }} />
        </div>
        <ul className="rp-checklist">
          {RESUME_CHECKLIST.map((it) => {
            const on = checked.has(it.id);
            return (
              <li key={it.id} className={on ? 'on' : ''}>
                <label>
                  <input type="checkbox" checked={on} onChange={() => toggleItem(it.id)} />
                  <span className="rp-check-text">{it.text}</span>
                </label>
                {it.why && <span className="rp-check-why">{it.why}</span>}
              </li>
            );
          })}
        </ul>
      </section>

      {/* STAR 框架 */}
      <section className="km-card rp-star">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>STAR：把经历讲成结果</h3>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          {RESUME_STAR.intro}
        </p>
        <div className="rp-star-grid">
          {RESUME_STAR.cells.map((c) => (
            <div className="rp-star-cell" key={c.k}>
              <span className="rp-star-k">{c.k}</span>
              <b>{c.name}</b>
              <p>{c.d}</p>
            </div>
          ))}
        </div>
        <div className="rp-star-demo">
          <p className="rp-before">
            <span className="rp-tag rp-tag-bad">差</span>
            {RESUME_STAR.before}
          </p>
          <p className="rp-after">
            <span className="rp-tag rp-tag-good">好</span>
            {RESUME_STAR.after}
          </p>
        </div>
      </section>

      {/* 分模块写法 */}
      <section className="rp-modules">
        <h2 className="rp-section-title">分模块写法</h2>
        {RESUME_MODULES.map((m) => (
          <div className="km-card rp-mod" key={m.id}>
            <div className="km-cont-top">
              <h3 style={{ margin: 0 }}>{m.title}</h3>
            </div>
            <p className="km-hint" style={{ marginTop: 4 }}>
              {m.summary}
            </p>
            <div className="rp-cols">
              <div className="rp-col rp-col-good">
                <b className="rp-col-h">该写</b>
                <ul>
                  {m.good.map((x, i) => (
                    <li key={i}>{x}</li>
                  ))}
                </ul>
              </div>
              <div className="rp-col rp-col-bad">
                <b className="rp-col-h">别踩</b>
                <ul>
                  {m.bad.map((x, i) => (
                    <li key={i}>{x}</li>
                  ))}
                </ul>
              </div>
            </div>
            {m.example && <p className="rp-ex">范例：{m.example}</p>}
          </div>
        ))}
      </section>

      {/* 雷区 */}
      <section className="km-card rp-pit">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>常见雷区</h3>
        </div>
        <ul className="rp-pit-list">
          {RESUME_PITFALLS.map((p) => (
            <li key={p.id}>
              <b>{p.title}</b>
              <span className="rp-pit-fix">{p.fix}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* 模板 / ATS */}
      <section className="km-card rp-tpl">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>模板与 ATS</h3>
        </div>
        <div className="rp-tpl-grid">
          {RESUME_TEMPLATES.map((t) => (
            <div className="rp-tpl-card" key={t.id}>
              <b>{t.title}</b>
              <ul>
                {t.points.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

/** 项目面板：轻量入口，聚焦「全栈开发 agent 开发」 */
function ProjectPanel({ onNavigate }: { onNavigate?: (p: KmPage) => void }) {
  const [aud, setAud] = useState<(typeof AGENT_AUDIENCES)[number]>('全部');
  const [openId, setOpenId] = useState<string | null>(null);
  const list = aud === '全部' ? AGENT_PROJECTS : AGENT_PROJECTS.filter((p) => p.audience === aud);

  return (
    <div className="emp-project">
      <header className="emp-head">
        <div>
          <h1>全栈 Agent 开发实战</h1>
          <p className="emp-lede">
            面向全栈工程师的 Agent 项目入口 —— 既能写前端对话界面，也能写后端编排与工具调用，是求职项目经历的高含金量素材。
          </p>
        </div>
      </header>

      {/* 上手路径 */}
      <section className="km-card ag-path">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>上手路径</h3>
          <span className="km-tag km-tag-gray">三步从 0 到能写进简历</span>
        </div>
        <ol className="ag-steps">
          {AGENT_PATH.map((s) => (
            <li key={s.step} className="ag-step">
              <span className="ag-step-no">{s.step}</span>
              <div>
                <b>{s.title}</b>
                <p>{s.note}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* 人群筛选 */}
      <div className="ag-filter" role="group" aria-label="按人群筛选项目">
        {AGENT_AUDIENCES.map((a) => (
          <button
            type="button"
            key={a}
            className={`ag-filter-btn${aud === a ? ' on' : ''}`}
            onClick={() => setAud(a)}
          >
            {a}
          </button>
        ))}
      </div>

      {/* 项目卡片 */}
      <section className="ag-grid">
        {list.map((p) => {
          const open = openId === p.id;
          return (
            <article
              className={`km-card ag-card${open ? ' open' : ''}`}
              key={p.id}
              style={{ '--lvl': lvlColor(p.level) } as CSSProperties}
            >
              <div className="km-cont-top">
                <h3 className="ag-card-title" style={{ margin: 0 }}>
                  {p.title}
                </h3>
                <span className="ag-level">{p.level}</span>
              </div>
              <div className="ag-badges">
                <span className="ag-aud" style={{ '--aud': audColor(p.audience) } as CSSProperties}>
                  {p.audience}
                </span>
              </div>
              <p className="ag-tagline">{p.tagline}</p>
              <div className="ag-tags">
                {p.stack.map((t) => (
                  <span className="km-tag km-tag-gray" key={t}>
                    {t}
                  </span>
                ))}
              </div>
              <p className="ag-outcome">
                <span className="ag-outcome-k">产出</span>
                {p.outcome}
              </p>
              <p className="ag-why">{p.why}</p>

              {/* 展开详情 */}
              {open && (
                <div className="ag-detail">
                  <div className="ag-detail-block">
                    <b className="ag-detail-k">目标</b>
                    <p>{p.target}</p>
                  </div>
                  <div className="ag-detail-block">
                    <b className="ag-detail-k">技术选型</b>
                    <p>{p.techDetail}</p>
                  </div>
                  <div className="ag-detail-block">
                    <b className="ag-detail-k">验收标准</b>
                    <ul>
                      {p.acceptance.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              <div className="ag-actions">
                <button
                  type="button"
                  className="km-btn km-btn-sm km-btn-ghost ag-toggle"
                  onClick={() => setOpenId(open ? null : p.id)}
                  aria-expanded={open}
                >
                  {open ? '收起详情 ▲' : '展开详情 ▼'}
                </button>
                <button
                  type="button"
                  className="km-btn km-btn-sm km-btn-ghost ag-go"
                  onClick={() => onNavigate?.('projects')}
                >
                  去实战 →
                </button>
              </div>
            </article>
          );
        })}
      </section>

      {/* 进入完整实战库 */}
      <div className="ag-enter">
        <button type="button" className="km-btn km-btn-block" onClick={() => onNavigate?.('projects')}>
          进入完整 BOSS 项目实战库 →
        </button>
        <p className="ag-enter-note">完整版含进度追踪、前置依赖、章节联动与更多行业项目。</p>
      </div>
    </div>
  );
}

/** 难度配色：入门=绿 / 进阶=蓝 / 挑战=紫 */
function lvlColor(level: string): string {
  if (level === '入门') return '#2ea043';
  if (level === '挑战') return '#b98cff';
  return '#4f9dff';
}

/** 人群配色：校招=青 / 社招=橙 / 通用=灰蓝 */
function audColor(aud: string): string {
  if (aud === '校招') return '#11a8a8';
  if (aud === '社招') return '#e8913a';
  return '#6b7a90';
}

const ENTRIES: { key: EmpTab; emoji: string; label: string; desc: string }[] = [
  { key: 'bagua', emoji: '📚', label: '八股', desc: '面试知识点图谱，四区资源 + Agent 专项，可导出分区 Markdown。' },
  { key: 'resume', emoji: '📝', label: '简历打磨', desc: '自检清单 + STAR + 分模块写法 + 雷区 + 模板 ATS。' },
  { key: 'project', emoji: '🤖', label: '项目', desc: '全栈 Agent 开发轻量入口，6 个可实战项目 + 校招/社招筛选。' },
];

export function EmploymentPage({ onNavigate }: { onNavigate?: (p: KmPage) => void } = {}) {
  const [tab, setTab] = useState<EmpTab>('bagua');

  return (
    <div className="emp-root">
      <header className="emp-hero">
        <h1 className="emp-hero-title">就业作战室</h1>
        <p className="emp-hero-lede">
          八股 · 简历打磨 · 全栈 Agent 项目，求职三段一体。先从门面挑一块开始，再进对应专区深练。
        </p>
        <div className="emp-entry-grid">
          {ENTRIES.map((e) => (
            <button type="button" className="emp-entry" key={e.key} onClick={() => setTab(e.key)}>
              <span className="emp-entry-em">{e.emoji}</span>
              <b>{e.label}</b>
              <span className="emp-entry-desc">{e.desc}</span>
              <span className="emp-entry-go">进入 {e.label} →</span>
            </button>
          ))}
        </div>
      </header>

      <div className="emp-tabs" role="tablist" aria-label="就业板块">
        {TABS.map((t) => (
          <button
            type="button"
            role="tab"
            key={t.key}
            id={`emp-tab-${t.key}`}
            aria-selected={tab === t.key}
            aria-controls={`emp-panel-${t.key}`}
            className={`emp-tab${tab === t.key ? ' on' : ''}`}
            onClick={() => setTab(t.key)}
            title={t.hint}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 三块面板始终挂载，靠 hidden 切换，保留各自内部状态（如简历勾选） */}
      <div
        className="emp-panel"
        id="emp-panel-bagua"
        role="tabpanel"
        aria-labelledby="emp-tab-bagua"
        hidden={tab !== 'bagua'}
      >
        <BaguaPanel />
      </div>
      <div
        className="emp-panel"
        id="emp-panel-resume"
        role="tabpanel"
        aria-labelledby="emp-tab-resume"
        hidden={tab !== 'resume'}
      >
        <ResumePanel />
      </div>
      <div
        className="emp-panel"
        id="emp-panel-project"
        role="tabpanel"
        aria-labelledby="emp-tab-project"
        hidden={tab !== 'project'}
      >
        <ProjectPanel onNavigate={onNavigate} />
      </div>
    </div>
  );
}

export default EmploymentPage;
