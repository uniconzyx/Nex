/**
 * JudgePanel.tsx
 * ============================================================================
 * 判题台 —— 双端差异化 UI
 *
 * 桌面（exe）：Python / C / C++ / Java 全语言，走本机 go-judge 沙箱。
 * 移动（apk）：只有 Python 可跑（Pyodide/WASM，完全离线）；
 *              C / C++ / Java 选中即禁用「提交判题」并给出引导文案。
 *
 * 两个关键点：
 *
 * 【1】能力判定不在这个文件里写死。
 *   一律问 `capabilityOf()`。这样以后加语言（Go/Rust）只改 JudgeEngine
 *   的语言表，四个用到判题的地方自动跟上。
 *
 * 【2】「禁用」不能只靠 `disabled` 属性。
 *   按钮 disabled 后用户点不了，但如果没看到原因就会以为是 bug。
 *   所以额外渲染一条 banner，文案来自 capability.reason（唯一事实源）。
 * ============================================================================
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  RUNTIME,
  capabilityOf,
  judgeEngine,
  mapVerdictToUi,
  type TestCase,
  type TestCaseResult,
} from '../lib/JudgeEngine';
import { TONE_COLORS, type EnvReport, type JudgeLanguage } from '../lib/GoJudgeClient';
import { renderMarkdown } from '../lib/markdown';
import { recordAnswer } from '../lib/progress';
import { submitDaily } from '../lib/daily';
import { submitWeekly } from '../lib/weekly';
import { pushToast } from '../lib/feedback';
import type { AiMode } from './AiPanel';

/** 判题台支持的语言。顺序即下拉框顺序：先 Python（移动端唯一可用），再原三兄弟。 */
const LANGUAGES: { value: JudgeLanguage; label: string }[] = [
  { value: 'python', label: 'Python' },
  { value: 'c', label: 'C' },
  { value: 'cpp', label: 'C++' },
  { value: 'java', label: 'Java' },
];

const SAMPLE: Record<string, string> = {
  python: 'print(6 * 7)\n',
  py: 'print(6 * 7)\n',
  c: '#include <stdio.h>\n\nint main(void) {\n    printf("%d\\n", 6 * 7);\n    return 0;\n}\n',
  cpp: '#include <iostream>\nint main() { std::cout << 6 * 7 << std::endl; }\n',
  'c++': '#include <iostream>\nint main() { std::cout << 6 * 7 << std::endl; }\n',
  java: 'public class Main {\n  public static void main(String[] a) { System.out.println(6 * 7); }\n}\n',
};

/** 题目卡片：由练习页从题库带入。 */
export interface JudgeProblem {
  id: string;
  title: string;
  /** Markdown 题面 */
  content: string;
  /** 题库里推断出的语言（可能为 null：题目没写参考代码） */
  language?: string | null;
  /** 已就绪的用例（题库补过 cases 才有） */
  cases?: TestCase[];
  /** 起始代码（参考答案，用户可直接改） */
  starterCode?: string;
  /**
   * 以下四个字段是「判题 → 进度」的桥。
   * 有了它们，判题台才知道这次 AC 属于哪一章的哪道题，
   * 也才能把失败写进图鉴；没有它们（空白判题台）就只跑代码不记账。
   */
  chapterId?: string;
  subject?: string;
  qtype?: string;
  diff?: string;
}

export function JudgePanel({
  onAskCat,
  problem,
}: {
  /** 「问 CppCat」内嵌入口：带判题上下文唤起全局 AI 面板 */
  onAskCat?: (context?: string, mode?: AiMode) => void;
  /** 从题库带入的题目；不传则只是一个空白判题台 */
  problem?: JudgeProblem;
} = {}) {
  const [lang, setLang] = useState<JudgeLanguage>(
    (problem?.language as JudgeLanguage) ?? 'python',
  );
  const [code, setCode] = useState<string>(problem?.starterCode ?? SAMPLE.python);
  const [cases, setCases] = useState<TestCase[]>(
    problem?.cases?.length
      ? problem.cases
      : [
          { name: '样例 1', stdin: '', expected: '42' },
          { name: '样例 2', stdin: '', expected: '42' },
        ],
  );
  const [results, setResults] = useState<TestCaseResult[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [env, setEnv] = useState<EnvReport | null>(null);
  /** Pyodide 首次加载进度（移动端 Python 才用） */
  const [sandboxStage, setSandboxStage] = useState<string>('');
  const alive = useRef(true);

  /* ---------- 当前语言在本环境能不能跑 ---------- */
  const capability = useMemo(() => capabilityOf(lang, RUNTIME), [lang]);
  const blocked = !capability.supported;

  /* ---------- 题目切换时重置状态 ---------- */
  useEffect(() => {
    if (!problem) return;
    const next = (problem.language as JudgeLanguage) ?? 'python';
    setLang(next);
    setCode(problem.starterCode ?? SAMPLE[next] ?? '');
    setCases(
      problem.cases?.length
        ? problem.cases
        : [
            { name: '样例 1', stdin: '', expected: '' },
          ],
    );
    setResults([]);
    setError(null);
  }, [problem?.id, problem?.language, problem?.starterCode, problem?.cases, problem]);

  /* ---------- 环境预检 ---------- */
  useEffect(() => {
    alive.current = true;
    judgeEngine
      .checkEnvironment()
      .then((r) => {
        if (alive.current) setEnv(r);
      })
      .catch((e) => {
        if (alive.current) {
          setError(`环境检测失败：${e instanceof Error ? e.message : String(e)}`);
        }
      });
    return () => {
      alive.current = false;
    };
  }, []);

  const missing = useMemo(() => {
    if (!env) return [];
    const out: string[] = [];
    // 移动端没有 go-judge，这是设计使然，不该报成「缺失」
    if (RUNTIME === 'desktop') {
      if (!env.go_judge) out.push('go-judge（未找到将进入本地直跑降级模式）');
      for (const l of env.languages) {
        if (!l.available) out.push(l.name);
      }
    }
    return out;
  }, [env]);

  /* ---------- 切语言 ---------- */
  const switchLang = useCallback((next: JudgeLanguage) => {
    setLang(next);
    // 只在代码还是「另一个语言的样例」时才替换，避免覆盖用户已经写的内容
    setCode((prev) => {
      const isSample = Object.values(SAMPLE).includes(prev);
      return isSample ? (SAMPLE[next] ?? '') : prev;
    });
    setResults([]);
    setError(null);
    // 移动端切到 Python：顺手预热 Pyodide，点「运行」时就不用等 10MB
    if (next === 'python' && RUNTIME !== 'desktop') judgeEngine.warmUp();
  }, []);

  /* ---------- 提交 ---------- */
  const run = useCallback(async () => {
    if (blocked || running) return;
    setRunning(true);
    setError(null);
    setResults([]);
    setSandboxStage(RUNTIME !== 'desktop' && lang === 'python' ? '准备解释器…' : '');
    try {
      const res = await judgeEngine.submitCode(code, lang, cases);
      if (!alive.current) return;
      setResults(res.results);

      /**
       * 判题结果落库（P1 的核心动作）。
       * 只在内置用例存在时记账：没有用例的「自由运行」本来就无从判定对错，
       * 拿它算失败会平白给图鉴塞一堆假怪物。
       */
      const realCases = (problem?.cases?.length ?? 0) > 0;
      if (problem?.id && realCases && res.results.length > 0) {
        const allPassed = res.results.every((r) => r.passed);
        recordAnswer({
          questionId: problem.id,
          chapterId: problem.chapterId,
          subject: problem.subject,
          title: problem.title,
          diff: problem.diff,
          qtype: problem.qtype ?? 'coding',
          ok: allPassed,
          mode: 'judge',
        });
        submitDaily(problem.id, allPassed);
        submitWeekly(problem.id, allPassed);
        if (allPassed) {
          pushToast({ kind: 'ok', title: '全部用例通过', desc: problem.title, icon: '✓' });
        }
      }
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (alive.current) {
        setRunning(false);
        setSandboxStage('');
      }
    }
  }, [blocked, running, lang, code, cases, problem]);

  const cancel = useCallback(() => {
    judgeEngine.cancel();
    setRunning(false);
  }, []);

  const passedCount = results.filter((r) => r.passed).length;
  const isMobile = RUNTIME !== 'desktop';

  return (
    <div className="jp-page">
      <div className="jp-head">
        <h2 className="jp-title">{problem ? problem.title : 'Nex 判题台'}</h2>
        <span className="jp-channel" title={judgeEngine.describeChannel()}>
          {isMobile ? '本地 WASM 沙箱' : '本机沙箱'}
        </span>
      </div>

      {/* 题面：Markdown 渲染（先转义再加标签，见 lib/markdown.ts） */}
      {problem?.content ? (
        <div
          className="jp-problem md-body"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(problem.content) }}
        />
      ) : null}

      {missing.length > 0 && (
        <div className="jp-banner">
          检测到缺失：{missing.join('、')}。判题可能降级为本地直跑，结果仅供参考。
        </div>
      )}

      {/* 移动端语言拦截：文案来自 capabilityOf，全 App 唯一事实源 */}
      {blocked && (
        <div className="jp-blocked">
          <span className="jp-blocked-icon" aria-hidden="true">
            ⓘ
          </span>
          <span>{capability.reason}</span>
        </div>
      )}

      <div className="jp-row">
        <label className="jp-label">语言</label>
        <select
          className="jp-select"
          value={lang}
          onChange={(e) => switchLang(e.target.value as JudgeLanguage)}
        >
          {LANGUAGES.map((l) => {
            const cap = capabilityOf(l.value, RUNTIME);
            return (
              <option key={l.value} value={l.value}>
                {l.label}
                {cap.supported ? '' : '（仅桌面端）'}
              </option>
            );
          })}
        </select>

        <button
          className="jp-btn jp-btn--primary"
          onClick={run}
          disabled={running || blocked}
          title={blocked ? capability.reason : undefined}
        >
          {running ? '判题中…' : blocked ? '当前设备不支持' : '提交判题'}
        </button>
        <button className="jp-btn jp-btn--ghost" onClick={cancel} disabled={!running}>
          取消
        </button>
      </div>

      {running && sandboxStage && <div className="jp-progress">{sandboxStage}</div>}

      <textarea
        className="jp-editor"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        spellCheck={false}
        placeholder={blocked ? capability.reason : ''}
      />

      <h3 className="jp-subtitle">测试用例</h3>
      {cases.map((c, i) => (
        <div key={i} className="jp-case-row">
          <input
            className="jp-case-name"
            value={c.name ?? ''}
            placeholder="用例名"
            onChange={(e) =>
              setCases((prev) => prev.map((p, j) => (j === i ? { ...p, name: e.target.value } : p)))
            }
          />
          <input
            value={c.stdin ?? ''}
            placeholder="stdin"
            onChange={(e) =>
              setCases((prev) => prev.map((p, j) => (j === i ? { ...p, stdin: e.target.value } : p)))
            }
          />
          <input
            value={c.expected ?? ''}
            placeholder="期望输出"
            onChange={(e) =>
              setCases((prev) =>
                prev.map((p, j) => (j === i ? { ...p, expected: e.target.value } : p)),
              )
            }
          />
        </div>
      ))}

      {error && <div className="jp-error">{error}</div>}

      {results.length > 0 && (
        <>
          <h3 className="jp-subtitle">
            结果：{passedCount} / {results.length} 通过
          </h3>
          <ul className="jp-list">
            {results.map((r) => {
              const ui = r.verdict ? mapVerdictToUi(r.verdict) : r.ui;
              const color = TONE_COLORS[ui.tone];
              return (
                <li key={r.index} className="jp-item" style={{ borderColor: color.border }}>
                  <span
                    className="jp-badge"
                    style={{ background: color.bg, color: color.fg, borderColor: color.border }}
                    title={ui.hint}
                  >
                    {ui.label}
                  </span>
                  <span className="jp-case-title">{r.name}</span>

                  {r.verdict.verdict === 'accepted' && r.verdict.memory_kb > 0 && (
                    <span className="jp-meta">
                      {r.verdict.time_ms} ms · {r.verdict.memory_kb} KB
                    </span>
                  )}
                  {r.verdict.verdict === 'accepted' && r.verdict.memory_kb === 0 && (
                    <span className="jp-meta">{r.verdict.time_ms} ms</span>
                  )}
                  {r.reason && <span className="jp-reason">{r.reason}</span>}

                  {!r.passed && r.actual !== '' && <pre className="jp-output">{r.actual}</pre>}
                </li>
              );
            })}
          </ul>

          {results.some((r) => !r.passed) ? (
            <div className="cat-inline">
              <img src="/assets/cppcat-avatar.png" alt="" />
              <span className="cat-inline-text">
                别灰心，错误信息里藏着线索喵。让凯喵带着这份报错逐条看看？
              </span>
              <button
                type="button"
                onClick={() =>
                  onAskCat?.(
                    `判题失败求助：语言=${lang}，` +
                      results
                        .filter((r) => !r.passed)
                        .map((r) => `${r.name}(${r.ui.label}${r.reason ? ':' + r.reason : ''})`)
                        .join('；') +
                      `；代码：${code.slice(0, 200)}`,
                    'diagnose',
                  )
                }
              >
                让凯喵看这份报错
              </button>
            </div>
          ) : (
            <div className="cat-inline" style={{ background: '#F0FDF4', borderColor: '#BBF7D0' }}>
              <img src="/assets/cppcat-avatar.png" alt="" />
              <span className="cat-inline-text" style={{ color: '#15803D' }}>
                全部通过。想让凯喵看看还能怎么优化吗？
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default JudgePanel;
