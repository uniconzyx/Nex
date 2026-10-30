/**
 * AgentPage.tsx —— 凯喵陪练（ML/DL 的 S1 诊断 + S2 实验陪跑）
 * ============================================================================
 * 这个页面和 #ai（问凯喵）的根本区别：
 *   #ai 是「问一句答一句」，回答无法验证；
 *   这里是「跑一个循环」——每步都调真实工具，报告里每个数字都能追到某一步。
 *   页面上所以把「执行轨迹」和「报告」并排放：左边是物证，右边是结论。
 *
 * 三条产品决定：
 *   1. **未登录也能用**：没登录时 planner 直接抛错，loop 立刻降级到规则序列，
 *      仍出一份数字全对的诊断报告。登录后同一条路径换成真模型，多出「洞察」。
 *   2. **数字自检放在报告顶上**，不在底部藏起来。用户第一眼要看到「哪些数字可核对」。
 *   3. **导出 .ipynb 而不是 .md**：代码单元的输出来自 output 对象，
 *      回放时不会与代码脱节（主人的笔记习惯也是 ipynb）。
 *
 * 路由：#agent
 * ============================================================================
 */
import { useCallback, useMemo, useState } from 'react';

import { renderMarkdown } from '../lib/markdown';
import { useProgress } from '../lib/progress';
import { useSession } from '../lib/session';
import { auditReport, ipynbJson, summarizeAudit, toIpynb, type AuditIssue } from '../lib/agent/report';
import { SCENARIOS, getScenario } from '../lib/agent/scenarios';
import { resolveChapters } from '../lib/agent/tools';
import { runAgent } from '../lib/agent/loop';
import { makeLlmPlanner } from '../lib/agent/llmPlanner';
import { makePyodideRunner } from '../lib/agent/pyodideRunner';
import type { AgentRun, AgentScenarioId, AgentStep, Planner } from '../lib/agent/types';
import './AgentPage.css';

/** 只服务 ML / DL 两门；两个都在 bundle 的 `ai` 包里，用章节族前缀区分 */
const SUBJECTS = [
  { key: 'ml', label: '机器学习' },
  { key: 'ai', label: '深度学习' },
] as const;

export function AgentPage() {
  const progress = useProgress();
  const session = useSession();
  const online = session.status === 'online';

  const [subject, setSubject] = useState<string>('ml');
  const [chapterId, setChapterId] = useState<string>('');
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [run, setRun] = useState<AgentRun | null>(null);
  const [issues, setIssues] = useState<AuditIssue[]>([]);
  const [busy, setBusy] = useState<AgentScenarioId | null>(null);
  const [err, setErr] = useState<string>('');

  const chapters = useMemo(() => resolveChapters(subject), [subject]);
  const activeChapter = chapterId || chapters[0]?.id || '';

  const start = useCallback(
    async (id: AgentScenarioId) => {
      const scenario = getScenario(id);
      if (!scenario || busy) return;
      setBusy(id);
      setErr('');
      setSteps([]);
      setLogs([]);
      setRun(null);
      setIssues([]);

      const chapter = id === 'experiment' ? activeChapter : undefined;
      const runner = id === 'experiment' ? makePyodideRunner({ onChunk: () => undefined }) : undefined;

      // 登录且后端在线 → 真模型；否则一个必然抛错的 planner，让 loop 走规则序列。
      // 这不算「兜底 hack」：降级路径本身就是 A1 的验收项（无 key 也能出报告）。
      const llm = online ? makeLlmPlanner({}) : null;
      const planner: Planner = llm
        ? (messages) => llm(messages)
        : async () => {
            throw new Error('未登录或后端离线：使用规则模式');
          };

      try {
        const res = await runAgent({
          scenario,
          subject,
          chapterId: chapter || undefined,
          progress,
          runner,
          planner,
          maxSteps: id === 'experiment' ? 6 : 8,
          onStep: (s) => setSteps((prev) => [...prev, s]),
          onLog: (line) => setLogs((prev) => [...prev, line].slice(-30)),
        });
        setRun(res);
        setIssues(auditReport(res));
      } catch (e) {
        setErr((e as Error).message);
      } finally {
        setBusy(null);
      }
    },
    [activeChapter, busy, online, progress, subject],
  );

  const exportIpynb = useCallback(() => {
    if (!run?.report) return;
    const nb = toIpynb(run.report, { subject });
    const blob = new Blob([ipynbJson(nb)], { type: 'application/x-ipynb+json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${run.report.title || 'cppmind-agent'}.ipynb`;
    a.click();
    URL.revokeObjectURL(url);
  }, [run, subject]);

  const report = run?.report;
  const degraded = !!run?.error;
  const hardErr = issues.filter((i) => i.level === 'error');

  return (
    <div className="ag-root">
      <header className="ag-head">
        <div className="ag-head-main">
          <h1>凯喵陪练</h1>
          <p className="ag-lede">
            读你真实的进度与错题，定位最该补的那一章；或锁定一章，真跑一段 Python 再下结论。
            报告里每个数字都来自某一步工具调用，可逐条核对。
          </p>
        </div>
        <div className="ag-pickers">
          <label className="ag-field">
            <span>学科</span>
            <select value={subject} onChange={(e) => setSubject(e.target.value)}>
              {SUBJECTS.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="ag-field">
            <span>实验章节</span>
            <select value={activeChapter} onChange={(e) => setChapterId(e.target.value)}>
              {chapters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} {c.title}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <section className="ag-scenarios" aria-label="选择场景">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`ag-scenario${busy === s.id ? ' is-running' : ''}`}
            onClick={() => void start(s.id)}
            disabled={!!busy}
          >
            <span className="ag-scenario-name">{s.name}</span>
            <span className="ag-scenario-tag">{s.tagline}</span>
            <span className="ag-scenario-foot">
              {busy === s.id ? '正在跑…' : s.id === 'experiment' ? `锁章：${activeChapter}` : `学科：${subject}`}
            </span>
          </button>
        ))}
      </section>

      {!online && (
        <p className="ag-note">
          当前未登录或后端离线，将以<strong>规则模式</strong>运行：仍会读真实进度并出报告，但没有模型生成的洞察。
        </p>
      )}

      {err && <p className="ag-error">运行失败：{err}</p>}

      {(steps.length > 0 || report) && (
        <div className="ag-body">
          <section className="ag-trail" aria-label="执行轨迹">
            <div className="ag-sec-head">
              <h2>执行轨迹</h2>
              <span className="ag-count">{steps.length} 步</span>
            </div>
            <ol className="ag-steps">
              {steps.map((s) => (
                <li key={s.idx} className={`ag-step${s.observation && !s.observation.ok ? ' is-fail' : ''}`}>
                  <div className="ag-step-top">
                    <span className="ag-tool">{s.tool ?? 'final'}</span>
                    <span className="ag-ms">{s.ms} ms</span>
                  </div>
                  {s.thought && <p className="ag-thought">{s.thought}</p>}
                  {s.observation && <p className="ag-obs">{s.observation.brief}</p>}
                </li>
              ))}
              {busy && <li className="ag-step is-pending">等待下一步…</li>}
            </ol>
            {logs.length > 0 && (
              <details className="ag-logs">
                <summary>运行日志（{logs.length} 行）</summary>
                <pre>{logs.join('\n')}</pre>
              </details>
            )}
          </section>

          <section className="ag-report" aria-label="报告">
            {!report ? (
              <p className="ag-empty">还没有报告。点上面的场景开始。</p>
            ) : (
              <>
                <div className="ag-sec-head">
                  <h2>{report.title}</h2>
                  <button type="button" className="ag-export" onClick={exportIpynb}>
                    导出 .ipynb
                  </button>
                </div>

                <p className="ag-headline">{report.headline}</p>

                <div className={`ag-audit${hardErr.length ? ' is-bad' : issues.length ? ' is-warn' : ' is-ok'}`}>
                  {summarizeAudit(issues)}
                  {issues.length > 0 && (
                    <ul>
                      {issues.slice(0, 6).map((i, k) => (
                        <li key={k}>
                          [{i.level}] {i.section}：{i.message}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {degraded && <p className="ag-note">本次运行降级到规则序列：{run?.error}</p>}

                {report.sections.map((sec, i) => (
                  <article key={i} className="ag-sec">
                    <h3>{sec.heading}</h3>
                    <div className="ag-md" dangerouslySetInnerHTML={{ __html: renderMarkdown(sec.body) }} />
                    {sec.evidence && <p className="ag-ev">证据：{sec.evidence}</p>}
                  </article>
                ))}

                {report.labCode && (
                  <article className="ag-sec">
                    <h3>主实验代码</h3>
                    <pre className="ag-code">{report.labCode}</pre>
                    {report.labOutput && (
                      <>
                        <h4>真实输出</h4>
                        <pre className="ag-code ag-out">{report.labOutput}</pre>
                      </>
                    )}
                  </article>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export default AgentPage;
