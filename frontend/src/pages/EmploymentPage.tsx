/**
 * EmploymentPage.tsx —— 就业 · 八股面试专轨图谱（P5）
 * ============================================================================
 * 复用：
 *   - P5 的 buildInterviewGraph（四区资源 + Agent 专项，节点按区着色）
 *   - copyMarkdown（与 Track408Page 同款剪贴板降级）
 *
 * 路由：#employment
 * 与「考研 408」「图表总览」同属学习中枢，是求职向的跨资源视角。
 * 八股归就业（不归考研）：本页只呈现就业专轨资源，考研面试见复试板块。
 * ============================================================================
 */
import { useMemo, useState, type CSSProperties } from 'react';
import { buildInterviewGraph, interviewGraphToMarkdown } from '../lib/employment';
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

export function EmploymentPage() {
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
    <div className="emp-root">
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

      {/* ── 四区资源卡片 ─────────────────────────────────── */}
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

      {/* ── Agent 八股专项 ──────────────────────────────── */}
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

export default EmploymentPage;
