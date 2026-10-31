/**
 * KaoyanPage.tsx —— 考研 · 备考中枢（三板块拼图）
 *
 * 三块玻璃卡片对应考研的三条线，逻辑天然闭环、无需新增内容数据：
 *   专业课（考研 408）→ track408，并显示「真实均掌握度」（来自四模块跨章汇总）
 *   复试（面试向）     → reexam
 *   公共课（数英政）   → guides（考研手札）
 * 点击任一卡片跳到对应页面，进度全网互通。
 */
import { useMemo } from 'react';

import { useProgress } from '../lib/progress';
import { buildTrack408Summary } from '../lib/examTracks';
import type { KmPage } from '../lib/nav';

interface Board {
  key: KmPage;
  title: string;
  role: string;
  badge: string;
  cta: string;
  mastery?: number;
}

export function KaoyanPage({ onNavigate }: { onNavigate: (p: KmPage) => void }) {
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
    },
    {
      key: 'reexam',
      title: '考研复试',
      role: '面试向：简历打磨、项目深挖、英语口语与综合问答。',
      badge: '面试',
      cta: '去复试备战',
    },
    {
      key: 'guides',
      title: '公共课 · 考研手札',
      role: '数学 · 英语 · 政治 的笔记与八股导航，按科翻查。',
      badge: '数英政',
      cta: '翻手札',
    },
  ];

  return (
    <div className="km-view kaoyan-view">
      <section className="km-glass kaoyan-hero">
        <h2>考研 · 备考中枢</h2>
        <p>一套进度，三块拼图：专业课（408）、复试（面试）、公共课（数学·英语·政治）。哪里弱，先攻哪。</p>
      </section>

      <div className="kaoyan-grid">
        {boards.map((b) => (
          <button
            type="button"
            key={b.key}
            className="km-card km-glass kaoyan-board"
            onClick={() => onNavigate(b.key)}
          >
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
            <span className="kb-cta">{b.cta} →</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default KaoyanPage;
