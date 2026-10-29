/**
 * ReexamPage.tsx —— 考研复试板块（P6）
 * ============================================================================
 * 复用：
 *   - P6 的 buildReexamView（面试分类 + 机试题三层答案 + 工作场景）
 *   - copyMarkdown（与 EmploymentPage / Track408Page 同款剪贴板降级）
 *
 * 路由：#reexam
 * 结构：面试问题（非八股，按研究计划/项目陈述/英语/专业素养分四类）
 *       + 机试（高校真题 + ①大框架 ②核心算法思想 ③完整代码 + 工作场景）
 * ============================================================================
 */
import { useMemo, useState } from 'react';
import { buildReexamView, reexamToMarkdown } from '../lib/reexam';
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
            机试题 <b>{v.totalMachineTests}</b> 道（{v.universities.join('、')}）——
            复试 ≠ 就业八股：导师看研究潜力与表达，机试看编码闭环
          </p>
        </div>
        <button type="button" className="km-btn km-btn-sm km-btn-ghost" onClick={onExport}>
          {copied ? '已复制 ✓' : '导出复试清单 Markdown'}
        </button>
      </header>

      {/* ── 面板切换：面试 / 机试 ─────────────────────────── */}
      <div className="rx-tabs">
        <span className="rx-tab-title">复试板块包含：</span>
        <span className="rx-pill">面试问题（研究计划 / 项目陈述 / 英语 / 专业素养）</span>
        <span className="rx-pill rx-pill-warn">机试（置于复试内，编码测试）</span>
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

      {/* ── 二、机试题库 ───────────────────────────────── */}
      <section className="km-card rx-machine">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>二、机试题库（高校真题 · 三层答案 · 工作场景）</h3>
          <span className="km-tag km-tag-gray">{v.totalMachineTests} 题</span>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          答案固定三层：<b>① 大框架</b> → <b>② 核心算法思想</b> → <b>③ 完整代码（全注释）</b>；每题附
          <b>工作中具体实例</b>。点击展开。
        </p>
        <div className="rx-test-grid">
          {v.machineTests.map((t) => {
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
