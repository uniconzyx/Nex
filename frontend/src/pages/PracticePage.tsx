/**
 * PracticePage.tsx —— 练习模块
 * ============================================================================
 * 两个 Tab：
 *   题库    —— 818 道题按学科筛，点开就能作答 / 对答案 / 送判题台；
 *   判题台  —— 原来的 JudgePanel（本机 go-judge 或移动端 Pyodide）。
 *
 * 【为什么合并成一个页面而不是两个导航项】
 *   侧栏已被设计稿的 14 项占满，加项会破坏分组节奏。而题库和判题台本来就是
 *   同一件事的两半（选题 → 判题），做成 Tab 顺带解决「从题目跳过去后回不来」。
 *
 * 【跨页跳转怎么接】
 *   学习页/题库调 sendToJudge() 写入模块级目标，这里用 usePendingJudgeProblem()
 *   订阅。切到本页时若已有目标，直接落在判题台 Tab 并带上题面。
 *   judgeKey 保证同一道题重复点也会重置判题台（否则 React 认为 props 没变）。
 * ============================================================================
 */

import { useEffect, useRef, useState } from 'react';

import { LanSettingsBar } from '../components/LanSettingsBar';
import { JudgePanel } from '../components/JudgePanel';
import { ExerciseBank } from '../components/ExerciseBank';
import { subjectLabel, useSubject } from '../lib/subject';
import { clearJudgeTarget, peekJudgeTarget, usePendingJudgeProblem, useFocusedChapter } from '../lib/exerciseBank';
import type { AiMode } from '../components/AiPanel';

type Tab = 'bank' | 'judge';

export function PracticePage({
  onAskCat,
}: {
  onAskCat: (context?: string, mode?: AiMode) => void;
}) {
  const [subject] = useSubject();
  const target = usePendingJudgeProblem();
  const focusedChapter = useFocusedChapter();
  const [tab, setTab] = useState<Tab>(() => (peekJudgeTarget() ? 'judge' : 'bank'));

  // 学习页点「本章 N 题」→ 落到题库 Tab（章节锁定由 ExerciseBank 自己读）
  useEffect(() => {
    if (focusedChapter) setTab('bank');
  }, [focusedChapter]);

  // 有新目标就立刻切到判题台。用 ref 记「上一次消费的题目」，避免
  // 「在判题台里点题库再点同一题」被这条 effect 反复拉回。
  const lastTargetId = useRef<string | null>(peekJudgeTarget()?.id ?? null);
  useEffect(() => {
    if (!target) return;
    if (lastTargetId.current === target.id) return;
    lastTargetId.current = target.id;
    setTab('judge');
  }, [target]);

  /** 同一题重复送进来时换个 key，强制 JudgePanel 重建 */
  const [judgeKey, setJudgeKey] = useState(0);
  const goJudge = () => {
    setJudgeKey((k) => k + 1);
    setTab('judge');
  };

  return (
    <>
      <div className="bank-tabs">
        <button
          type="button"
          className={`bank-tab${tab === 'bank' ? ' on' : ''}`}
          onClick={() => setTab('bank')}
        >
          题库
          <i>{subjectLabel(subject)}</i>
        </button>
        <button
          type="button"
          className={`bank-tab${tab === 'judge' ? ' on' : ''}`}
          onClick={() => setTab('judge')}
        >
          判题台
          {target && <i>{target.title.slice(0, 14)}</i>}
        </button>
        {tab === 'judge' && target && (
          <button
            type="button"
            className="bank-tab-clear"
            onClick={() => {
              clearJudgeTarget();
              lastTargetId.current = null;
            }}
            title="清空带入的题目，回到空白判题台"
          >
            卸下题目
          </button>
        )}
      </div>

      {tab === 'bank' && (
        <div style={{ marginTop: 16 }}>
          <ExerciseBank subject={subject} onGoJudge={goJudge} />
        </div>
      )}

      {tab === 'judge' && (
        <>
          <div style={{ marginTop: 16 }}>
            <LanSettingsBar />
          </div>
          <div style={{ marginTop: 16 }}>
            <JudgePanel
              key={`${target?.id ?? 'blank'}-${judgeKey}`}
              onAskCat={onAskCat}
              problem={target ?? undefined}
            />
          </div>
        </>
      )}
    </>
  );
}

export default PracticePage;
