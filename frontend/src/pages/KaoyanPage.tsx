/**
 * KaoyanPage.tsx —— 考研 · 备考中枢
 *
 * 四块玻璃卡片对应考研的四条线：
 *   专业课（考研 408）→ track408，并显示「真实均掌握度」（来自四模块跨章汇总）
 *   复试（面试向）     → reexam
 *   公共课（数学/英语/政治）→ 三个直达入口，分别落到题库的 math / english / politics
 *
 * 为什么公共课不再跳「考研手札」：
 *   数英政的概念、题库、真题都在 _exam 数据里（后端 /exams 已全量提供），
 *   此前却只挂了一个「翻手札」按钮，用户点进去看到的是一堆笔记链接，
 *   自然得出「没有概念学习、没有真题题库」的结论。现在每科各给一个入口，
 *   直达「概念 / 题库 / 套卷」三视图。
 */
import { useMemo } from 'react';

import { useProgress } from '../lib/progress';
import { buildTrack408Summary } from '../lib/examTracks';
import type { KmPage } from '../lib/nav';

type ExamView = 'framework' | 'papers' | 'training';
type FrameworkSub = 'framework' | 'knowledge' | 'summary' | 'vocab' | 'listening' | 'formulas';

interface Board {
  key: string;
  title: string;
  role: string;
  badge: string;
  cta: string;
  mastery?: number;
  page?: KmPage;
  /** 公共课专用：直接落到 _exam 的哪一场考试 */
  exam?: string;
  subject?: string;
  view?: ExamView;
  sub?: FrameworkSub;
  /** 卡片下的细分入口（如数一/数二） */
  subs?: { label: string; subject: string; view?: ExamView; sub?: FrameworkSub; hint?: string }[];
}

export function KaoyanPage({
  onNavigate,
  onNavigateExams,
}: {
  onNavigate: (p: KmPage) => void;
  onNavigateExams: (exam: string, subject?: string, view?: ExamView, sub?: FrameworkSub) => void;
}) {
  const p = useProgress();
  const track408 = useMemo(() => buildTrack408Summary(p), [p]);

  const boards: Board[] = [
    {
      key: 'track408',
      title: '专业课 · 408',
      role: '数据结构 / 计组 / 操作系统 / 网络，四模块跨章汇总与薄弱章冲刺。',
      badge: '专业课',
      cta: '进入 408 总表',
      mastery: track408.overallAvg,
      page: 'track408',
    },
    {
      key: 'reexam',
      title: '考研复试',
      role: '面试向：简历打磨、项目深挖、英语口语听力与综合问答。',
      badge: '面试',
      cta: '去复试备战',
      page: 'reexam',
    },
    {
      key: 'math',
      title: '公共课 · 数学',
      role: '高数 / 线代 / 概率：概念精讲 → 解题框架 → 题库刷题 → 套卷模考。',
      badge: '数英政',
      cta: '进入数学',
      exam: 'math',
      subject: 'm1',
      subs: [
        { label: '数学（一）', subject: 'm1', hint: '高数+线代+概率' },
        { label: '数学（二）', subject: 'm2', hint: '高数+线代' },
        { label: '公式速查', subject: 'm1', view: 'framework', sub: 'formulas', hint: '全量公式 + 二级结论' },
        { label: '题库', subject: 'm1', view: 'training', hint: '按专题刷题与逐题讲解' },
      ],
    },
    {
      key: 'english',
      title: '公共课 · 英语',
      role: '做题方法 + 阅读高频词 + 精读实战；听力单列（复试 / 四六级方向）。',
      badge: '数英政',
      cta: '进入英语',
      exam: 'english',
      subject: 'e1',
      subs: [
        { label: '做题方法', subject: 'e1', view: 'framework', sub: 'framework', hint: '完形/阅读/新题型/翻译/写作' },
        { label: '阅读高频词', subject: 'e1', view: 'framework', sub: 'vocab', hint: '82 个阅读态度/逻辑/熟词僻义词' },
        { label: '听力', subject: 'e1', view: 'framework', sub: 'listening', hint: '场景词·信号词·同义替换·速记' },
        { label: '题库', subject: 'e1', view: 'training', hint: '刷题与逐题讲解' },
        { label: '英语（二）', subject: 'e2', view: 'framework' },
      ],
    },
    {
      key: 'politics',
      title: '公共课 · 政治',
      role: '马原 / 毛中特 / 史纲 / 思修法治 / 时政五大学科模块，主观题按肖四肖八方向组织。',
      badge: '数英政',
      cta: '进入政治',
      exam: 'politics',
      subject: 'pol',
      subs: [
        { label: '五大学科考点', subject: 'pol', view: 'framework', hint: '考点+易错点+模板' },
        { label: '选择题题库', subject: 'pol', view: 'training' },
        { label: '套卷', subject: 'pol', view: 'papers' },
      ],
    },
  ];

  return (
    <div className="km-view kaoyan-view">
      <section className="km-glass kaoyan-hero">
        <h2>考研 · 备考中枢</h2>
        <p>
          一套进度，四条线：专业课（408）、复试（面试）、公共课（数学 · 英语 · 政治）。
          公共课已全部接入概念学习、题库与套卷，点进任一科即可开始。
        </p>
      </section>

      <div className="kaoyan-grid">
        {boards.map((b) => (
          <article key={b.key} className="km-card km-glass kaoyan-board">
            <span className="km-tag-blue">{b.badge}</span>
            <h3>{b.title}</h3>
            <p className="kb-role">{b.role}</p>

            {typeof b.mastery === 'number' && (
              <div className="kaoyan-mastery" aria-label={`408 平均掌握度 ${b.mastery}%`}>
                <span className="km-track">
                  <i style={{ width: `${Math.max(b.mastery, 1)}%` }} />
                </span>
                <b className="kaoyan-mnum">{b.mastery}%</b>
              </div>
            )}

            <button
              type="button"
              className="kb-cta kaoyan-enter"
              onClick={() => {
                if (b.exam) onNavigateExams(b.exam, b.subject, b.view);
                else if (b.page) onNavigate(b.page);
              }}
            >
              {b.cta} →
            </button>

            {b.subs && (
              <div className="kaoyan-subs">
                {b.subs.map((s) => (
                  <button
                    key={`${s.subject}-${s.view ?? 'framework'}-${s.sub ?? ''}-${s.label}`}
                    type="button"
                    className="kaoyan-sub"
                    title={s.hint}
                    onClick={() => onNavigateExams(b.exam!, s.subject, s.view, s.sub)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

export default KaoyanPage;
