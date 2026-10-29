/**
 * ReexamPage.tsx —— 考研复试板块（P6 + 题型/框架扩充）
 * ============================================================================
 * 复用：
 *   - buildReexamView（面试分类 + 机试题三层答案 + 工作场景 + 题型聚合 + 算法框架）
 *   - filterMachineTests（按题型/高校/关键词筛选，纯函数）
 *   - copyMarkdown（与 EmploymentPage / Track408Page 同款剪贴板降级）
 *
 * 路由：#reexam
 * 结构：
 *   一、复试专属面试问题（非八股：研究计划/项目陈述/英语/专业素养/选导/科研潜质）
 *   二、常考算法思想与框架（五步解题 + 18 组模板 + 提交前自检）
 *   三、机试题库（高校真题 + ①大框架 ②核心算法思想 ③完整代码 + 工作场景）
 * ============================================================================
 */
import { useMemo, useState } from 'react';
import { buildReexamView, filterMachineTests, reexamToMarkdown } from '../lib/reexam';
import './ReexamPage.css';

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

export function ReexamPage() {
  const v = useMemo(() => buildReexamView(), []);
  const [copied, setCopied] = useState(false);
  const [openInterview, setOpenInterview] = useState<string | null>(null);
  const [openTest, setOpenTest] = useState<string | null>(null);
  const [openGroup, setOpenGroup] = useState<string | null>(v.playbook.groups[0]?.group ?? null);
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [keyword, setKeyword] = useState('');

  const shown = useMemo(
    () => filterMachineTests(v.machineTests, { type: typeFilter, keyword }),
    [v.machineTests, typeFilter, keyword],
  );

  const onExport = async () => {
    await copyMarkdown(reexamToMarkdown(v));
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="rx-root">
      <header className="rx-head">
        <div>
          <h1>{v.name}</h1>
          <p className="rx-lede">
            面试问题 <b>{v.totalQuestions}</b> 道（{v.interview.categories.length} 类，<b>非八股</b>）·
            机试题 <b>{v.totalMachineTests}</b> 道 / <b>{v.universities.length}</b> 所高校 ·{' '}
            <b>{v.types.length}</b> 类题型 · 算法框架 <b>{v.playbook.totalPatterns}</b> 个 ——
            复试 ≠ 就业八股：导师看研究潜力与表达，机试看「题型识别 → 框架套用 → 编码闭环」
          </p>
        </div>
        <button type="button" className="km-btn km-btn-sm km-btn-ghost" onClick={onExport}>
          {copied ? '已复制 ✓' : '导出复试清单 Markdown'}
        </button>
      </header>

      {/* ── 概览标签 ───────────────────────────────────── */}
      <div className="rx-tabs">
        <span className="rx-tab-title">复试板块包含：</span>
        <span className="rx-pill">面试问题（研究计划 / 项目陈述 / 英语 / 专业素养 / 选导 / 科研潜质）</span>
        <span className="rx-pill">常考算法思想与框架（{v.playbook.groups.length} 组 · {v.playbook.totalPatterns} 个模板）</span>
        <span className="rx-pill rx-pill-warn">机试（{v.totalMachineTests} 题 · {v.types.length} 类题型）</span>
      </div>

      {/* ── 一、复试专属面试问题 ─────────────────────────── */}
      <section className="km-card rx-interview">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>一、复试专属面试问题（非八股）</h3>
          <span className="km-tag km-tag-gray">{v.totalQuestions} 题</span>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          {v.interview.desc}
        </p>
        <div className="rx-cat-list">
          {v.interview.categories.map((c) => {
            const open = openInterview === c.category;
            return (
              <div className="rx-cat" key={c.category}>
                <button
                  type="button"
                  className={`rx-cat-head${open ? ' active' : ''}`}
                  onClick={() => setOpenInterview(open ? null : c.category)}
                >
                  <b>{c.category}</b>
                  <span className="rx-cat-count">{c.count}</span>
                  <span className="rx-cat-caret">{open ? '▾' : '▸'}</span>
                </button>
                {open && (
                  <div className="rx-cat-body">
                    <p className="rx-cat-desc">{c.desc}</p>
                    <ol className="rx-q-list">
                      {c.questions.map((q, i) => (
                        <li key={i}>
                          <span className="rx-q">{q.q}</span>
                          {q.tip && <span className="rx-q-tip">导师视角：{q.tip}</span>}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ── 二、常考算法思想与框架 ───────────────────────── */}
      <section className="km-card rx-playbook">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>二、常考算法思想与框架（速查）</h3>
          <span className="km-tag km-tag-gray">
            {v.playbook.groups.length} 组 · {v.playbook.totalPatterns} 个
          </span>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          {v.playbook.intro}
        </p>

        {/* 五步解题法 */}
        <div className="rx-steps">
          {v.playbook.steps.map((s) => (
            <div className="rx-step" key={s.name}>
              <div className="rx-step-name">{s.name}</div>
              <p className="rx-step-detail">{s.detail}</p>
            </div>
          ))}
        </div>

        {/* 框架分组手风琴 */}
        <div className="rx-groups">
          {v.playbook.groups.map((g) => {
            const open = openGroup === g.group;
            return (
              <div className="rx-group" key={g.group}>
                <button
                  type="button"
                  className={`rx-group-head${open ? ' active' : ''}`}
                  onClick={() => setOpenGroup(open ? null : g.group)}
                >
                  <b>{g.group}</b>
                  <span className="rx-group-count">{g.count}</span>
                  <span className="rx-group-caret">{open ? '▾' : '▸'}</span>
                </button>
                {open && (
                  <div className="rx-group-body">
                    <div className="rx-group-types">
                      <span className="rx-group-types-label">对应题型</span>
                      {g.types.map((ty) => {
                        const n = v.types.find((x) => x.type === ty)?.count ?? 0;
                        return (
                          <button
                            type="button"
                            key={ty}
                            className={`rx-type-chip rx-type-chip-sm${typeFilter === ty ? ' active' : ''}`}
                            onClick={() => {
                              setTypeFilter(ty);
                              setOpenTest(null);
                              document
                                .querySelector('.rx-machine')
                                ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }}
                            title={`筛出「${ty}」类题目`}
                          >
                            {ty} <span className="rx-type-num">{n}</span>
                          </button>
                        );
                      })}
                    </div>
                    {g.why && <p className="rx-group-why">{g.why}</p>}
                    {g.patterns.map((p) => (
                      <div className="rx-pattern" key={p.name}>
                        <div className="rx-pattern-name">{p.name}</div>
                        <dl className="rx-pattern-meta">
                          <dt>何时用</dt>
                          <dd>{p.when}</dd>
                          <dt>复杂度</dt>
                          <dd>{p.complexity}</dd>
                          <dt>易错</dt>
                          <dd>{p.trap}</dd>
                        </dl>
                        <pre className="rx-code">{p.template}</pre>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* 提交前自检 */}
        <div className="rx-checklist">
          <div className="rx-checklist-title">提交前自检清单</div>
          <ol>
            {v.playbook.checklist.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ol>
        </div>
      </section>

      {/* ── 三、机试题库 ───────────────────────────────── */}
      <section className="km-card rx-machine">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>三、机试题库（高校真题 · 三层答案 · 工作场景）</h3>
          <span className="km-tag km-tag-gray">
            {shown.length === v.totalMachineTests
              ? `${v.totalMachineTests} 题`
              : `${shown.length} / ${v.totalMachineTests} 题`}
          </span>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          答案固定三层：<b>① 大框架</b> → <b>② 核心算法思想</b> → <b>③ 完整代码（全注释）</b>；每题附
          <b>工作中具体实例</b>。先按题型筛，再点击展开。
        </p>

        {/* 题型筛选 */}
        <div className="rx-filter">
          <button
            type="button"
            className={`rx-type-chip${typeFilter === '' ? ' active' : ''}`}
            onClick={() => setTypeFilter('')}
          >
            全部 <span className="rx-type-num">{v.totalMachineTests}</span>
          </button>
          {v.types.map((t) => (
            <button
              type="button"
              key={t.type}
              className={`rx-type-chip${typeFilter === t.type ? ' active' : ''}`}
              onClick={() => setTypeFilter(typeFilter === t.type ? '' : t.type)}
            >
              {t.type} <span className="rx-type-num">{t.count}</span>
            </button>
          ))}
        </div>
        <div className="rx-search">
          <input
            type="search"
            value={keyword}
            placeholder="搜标题 / 场景 / 算法思想，例如「最短路」「区间」「第 k 大」"
            onChange={(e) => setKeyword(e.target.value)}
            aria-label="搜索机试题"
          />
          {(keyword || typeFilter) && (
            <button
              type="button"
              className="km-btn km-btn-sm km-btn-ghost"
              onClick={() => {
                setKeyword('');
                setTypeFilter('');
              }}
            >
              清空筛选
            </button>
          )}
        </div>

        {shown.length === 0 ? (
          <p className="km-hint rx-empty">没有匹配的题目，换个题型或关键词试试。</p>
        ) : (
          <div className="rx-test-grid">
            {shown.map((t) => {
              const open = openTest === t.id;
              return (
                <div className={`rx-test${open ? ' active' : ''}`} key={t.id}>
                  <button
                    type="button"
                    className="rx-test-head"
                    onClick={() => setOpenTest(open ? null : t.id)}
                  >
                    <span className="rx-test-title">{t.title}</span>
                    <span className="rx-test-meta">
                      <span className="rx-type-tag">{t.type}</span>
                      {t.university} · {t.year} · {t.module}
                    </span>
                    <span className="rx-test-caret">{open ? '▾' : '▸'}</span>
                  </button>
                  {open && (
                    <div className="rx-test-body">
                      <div className="rx-scene">
                        <span className="rx-scene-tag">工作场景</span>
                        <span className="rx-scene-text">{t.scene}</span>
                      </div>
                      {t.parts.map((p) => (
                        <div className="rx-part" key={p.label}>
                          <div className="rx-part-label">{p.label}</div>
                          {p.label.startsWith('③') ? (
                            <pre className="rx-code">{p.text}</pre>
                          ) : (
                            <p className="rx-part-text">{p.text}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ── 关联模块脚注 ───────────────────────────────── */}
      <p className="rx-foot">
        机试关联模块：{v.modules.join(' · ')} —— 与「考研 408」四模块形成
        <b>学→练→考</b>闭环：在相应章节通关后，回到这里用高校真题做编码验收。
      </p>
    </div>
  );
}

export default ReexamPage;
