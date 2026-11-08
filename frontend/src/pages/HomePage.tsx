/**
 * HomePage.tsx —— 主城首页（凯喵外壳版）
 *
 * 数字全部来自真实数据：
 *   章节总数 / 已掌握 → BUNDLE.chapters + 本地进度
 *   项目 / 工时 / T4 → BUNDLE.projects
 *   今日试炼 / 野生怪物 → progress.daily / progress.bestiary
 * 没有学习记录时显示 0，不拿示例数字冒充进度。
 *
 * 【P1 改了什么】
 *   1. 原来的「继续闯关」是第二条静态文案，看完还是不知道该点哪。
 *      现在由 lib/nextAction.ts 按优先级算出**唯一**动作：今日试炼 → 收服怪物
 *      → 下一章 → 能开的项目 → 签到。首页大卡、侧栏徽标、右栏目标读的是同一个结果。
 *   2. 「今日试炼」不再是硬编码推荐项目，而是今天的 3 道真题（一半来自错题），
 *      点一条直接进对应的判题台/题库。
 */
import { useMemo, useState } from 'react';
import type { CSSProperties } from 'react';

import { ZoomLightbox } from '../components/ZoomLightbox';

import { BUNDLE } from '../data/bundle';
import { DIFF_META, TYPE_META, chapterTitle, exerciseById, focusChapter } from '../lib/exerciseBank';
import { challengeQuestion } from '../lib/challenge';
import { useDaily, dailyProgress } from '../lib/daily';
import { masterySummary, unlockedProjects } from '../lib/graph';
import { nextAction } from '../lib/nextAction';
import type { KmPage } from '../lib/nav';
import { SUBJECTS, useSubject } from '../lib/subject';
import { bestiaryStats, streakOf, todayKey, useProgress } from '../lib/progress';
import { MOODS, moodImage, resolveMood, useMoodFlash, type MoodCtx } from '../lib/mood';
import { useWeekly } from '../lib/weekly';

const RING_R = 54;
const RING_C = 2 * Math.PI * RING_R;

function Ring({ percent }: { percent: number }) {
  return (
    <div className="km-ring">
      <svg width="128" height="128" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={RING_R} fill="none" stroke="rgb(91 155 213 / 0.16)" strokeWidth="12" />
        <circle
          cx="64"
          cy="64"
          r={RING_R}
          fill="none"
          stroke="var(--km-accent)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={RING_C}
          strokeDashoffset={RING_C * (1 - Math.min(percent, 100) / 100)}
          style={{ transition: 'stroke-dashoffset .6s ease' }}
        />
      </svg>
      <div className="km-ring-num">
        {percent}%<small>平均掌握</small>
      </div>
    </div>
  );
}

const TIER_NAME: Record<string, string> = {
  t1: 'T1 能跑起来',
  t2: 'T2 能独立写',
  t3: 'T3 能讲原理',
  t4: 'T4 能进简历',
};

export function HomePage({ onNavigate }: { onNavigate: (p: KmPage) => void }) {
  const p = useProgress();
  const [subject, setSubject] = useSubject();
  const [zoomCat, setZoomCat] = useState<string | null>(null);

  // 章节数改读 masterySummary：它把 clang 的 7 个独立单元也算进来（141 章），
  // 旧写法只数 BUNDLE.chapters（现在 160 章），少算了 C 语言模块。
  const summary = masterySummary(p);
  const totalChapters = summary.total;
  const done = summary.done;
  const percent = summary.avg;
  const streak = streakOf(p.checkins);
  const bs = bestiaryStats(p);

  const daily = useDaily(subject);
  const weekly = useWeekly();
  const dp = dailyProgress(daily);
  /** 今日三题里有几道是"错题复习" —— 决定文案说"一半是复习"还是"都是新题" */
  const dailyWild = (daily?.qids ?? []).filter((id) => p.bestiary[id]?.state === 'wild').length;
  const action = nextAction(subject, p, daily, p.checkins.includes(todayKey()));

  /** 今日推荐项目：优先推「前置章节已达标」的，其次才按 T1 + 星标挑 */
  const todayProject = useMemo(() => {
    const open = unlockedProjects(p);
    const mine = open.filter((i) => i.track === subject);
    const pool = mine.length ? mine : open;
    return [...pool].sort((a, b) => (a.tier === b.tier ? b.stars - a.stars : a.tier.localeCompare(b.tier)))[0] ?? null;
  }, [p, subject]);

  const t4 = BUNDLE.projects.items.filter((i) => i.tier === 't4').length;

  /**
   * 凯喵此刻的心情：跟右栏同一套判定（常态 resolveMood + 瞬时 flash 优先），
   * 主城立绘直接换成对应表情图，并把它的台词搬到场景里。
   */
  const moodCtx: MoodCtx = {
    checkedIn: p.checkins.includes(todayKey()),
    streak,
    dailyDone: dp.done,
    dailyTotal: dp.total,
    wild: bs.wild,
    doneChapters: done,
    doneProjects: p.doneProjects.length,
    page: 'home',
    hour: new Date().getHours(),
  };
  const moodFlash = useMoodFlash();
  const moodKey = moodFlash?.key ?? resolveMood(moodCtx);
  const mood = MOODS[moodKey];

  return (
    <div className="km-view km-home-view">
      <section className="km-home-scene" aria-label="赛博冰蓝学院">
        <div className="km-scene-city" aria-hidden="true">
          <i /><i /><i /><i /><i /><i /><i />
        </div>

        {/* A 版骨架：hero（门厅）/ meta（状态与秘境）/ stage（塔与凯喵） */}
        <div className="km-scene-hero">
          <span className="km-scene-weather"><i />{percent >= 70 ? '晴朗' : percent >= 30 ? '薄雾' : '晨露'} · 学习天气</span>
          <h2>冰蓝学院，今日开塔</h2>
          <p>{action.subtitle}</p>
          <button type="button" className="km-scene-cta" onClick={() => onNavigate('learn')}>
            进入试炼塔
            <span aria-hidden="true">→</span>
          </button>
        </div>

        <div className="km-scene-meta">
          <div className="km-scene-stats" aria-label="今日试炼状态">
            <span className="km-scene-stat">
              <small>今日活跃</small>
              <b>{dp.done}/{dp.total || 3}</b>
              <i className="km-scene-meter"><em style={{ width: `${dp.total ? (dp.done / dp.total) * 100 : 0}%` }} /></i>
            </span>
            <span className="km-scene-stat">
              <small>本周秘境</small>
              <b>{weekly ? `${weekly.solved}/${weekly.total}` : '未解锁'}</b>
              <i className="km-scene-meter">
                <em style={{ width: `${weekly && weekly.total ? (weekly.solved / weekly.total) * 100 : 0}%` }} />
              </i>
            </span>
          </div>

          <div className="km-scene-notice">
            <span className="km-scene-notice-k">每日秘境</span>
            <b>{action.title}</b>
            <em>{dp.allCorrect ? '全对掉落已触发' : '今日错题双倍收容'}</em>
          </div>
        </div>

        <div className="km-scene-stage" style={{ '--mood-aura': mood.aura } as CSSProperties}>
          <span className="km-scene-floor" aria-hidden="true" />
          <span className="km-scene-rune r1" aria-hidden="true" />
          <span className="km-scene-rune r2" aria-hidden="true" />
          <span className="km-scene-rune r3" aria-hidden="true" />
          <button
            type="button"
            className="km-trial-tower"
            onClick={() => onNavigate('learn')}
            aria-label="进入知识试炼章节列表"
          >
            <img className="km-trial-tower-img" src="/assets/kaimao/trial-tower.svg" alt="" />
            <em>进入试炼塔</em>
          </button>

          {/* 凯喵：表情 + 心情牌 + 台词气泡（桌面端在塔右侧，窄屏落到场景下方） */}
          <div className="km-scene-mood-card" style={{ '--mood-aura': mood.aura } as CSSProperties}>
            <button
              type="button"
              className="km-scene-cat-btn"
              onClick={() => setZoomCat(moodImage(moodKey))}
              title="放大 / 缩小查看凯喵立绘"
              aria-label={`放大查看凯喵立绘（${mood.label}）`}
            >
              <img className="km-scene-cat" src={moodImage(moodKey)} alt={`凯喵此刻的表情：${mood.label}`} />
            </button>
            <div className="km-scene-mood-text">
              <span className="km-scene-mood">
                <i aria-hidden="true">{mood.emoji}</i>
                {mood.label}
              </span>
              <p className="km-scene-bubble">{mood.say(moodCtx)}</p>
            </div>
          </div>
        </div>
      </section>

      <ZoomLightbox
        open={zoomCat !== null}
        onClose={() => setZoomCat(null)}
        title={`凯喵 · ${mood.label}`}
        src={zoomCat ?? undefined}
        alt={`凯喵此刻的表情：${mood.label}`}
      />

      <section className="km-card km-home-progress">
        <div className="km-prog-row">
          <Ring percent={percent} />
          <div className="km-prog-info">
            <div className="big">
              {done === 0 ? '冒险才刚刚开始' : `已掌握 ${done} / ${totalChapters} 个章节`}
            </div>
            <div className="sub">
              {bs.wild > 0
                ? `图鉴里有 ${bs.wild} 只野生怪物，累计打败你 ${bs.fails} 次。`
                : '图鉴暂时干净——做错的题会变成怪物，等你收服。'}
            </div>
            <div className="km-stat-row">
              <div className="km-stat">
                <b>{done}</b>
                <span>已掌握章节</span>
              </div>
              <div className="km-stat">
                <b>{bs.tamed}</b>
                <span>已收服怪物</span>
              </div>
              <div className="km-stat">
                <b>{streak} 天</b>
                <span>连续打卡</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 现在只做一件事 ─────────────────────────────────────────────── */}
      <section className={`km-card km-next tone-${action.tone}`}>
        <span className="km-next-kicker">现在只做一件事</span>
        <h2>{action.title}</h2>
        <p>{action.subtitle}</p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button
            type="button"
            className="km-btn km-btn-primary"
            onClick={() => {
              if (action.kind === 'daily' && daily?.qids.length) {
                // 直接打开今天的第一道未做题，而不是把玩家丢到题库首页
                const nextId = daily.qids.find((id) => !daily.done.includes(id)) ?? daily.qids[0];
                challengeQuestion(nextId);
                return;
              }
              if (action.kind === 'stage') {
                // BOSS 关指名那道首领题；概念 / 演练关先锁定本章再进题库
                if (action.questionId) {
                  challengeQuestion(action.questionId);
                  return;
                }
                if (action.chapterId) focusChapter(action.chapterId);
                onNavigate('learn');
                return;
              }
              if (action.kind === 'chapter' && action.chapterId) {
                // 跨学科前置（data-ch01 依赖 py-ch03）：先切学科再定位，
                // 否则学习页会去找一个"当前学科里不存在"的章节，点完像没反应
                if (action.subject && action.subject !== subject) setSubject(action.subject);
                focusChapter(action.chapterId);
              }
              onNavigate(action.target);
            }}
          >
            {action.cta}
          </button>
          <button type="button" className="km-btn km-btn-ghost" onClick={() => onNavigate('bestiary')}>
            看怪物图鉴 {bs.wild > 0 ? `(${bs.wild})` : ''}
          </button>
        </div>
      </section>

      {/* ── 本周 BOSS：一周一次的外环目标 ─────────────────────────────── */}
      {weekly && (
        <section className="km-card km-weekly">
          <div className="km-cont-top">
            <h3 style={{ margin: 0 }}>本周 BOSS · {weekly.chapterTitle}</h3>
            <span className={`km-tag ${weekly.cleared ? 'km-tag-ok' : 'km-tag-gray'}`}>
              {weekly.cleared ? '已通关' : `${weekly.solved}/${weekly.total} 题`}
            </span>
          </div>

          <div className="km-weekly-gate">
            <span className="km-weekly-gate-label">
              本周答对 {weekly.gateGot}/{weekly.gateNeed} 题
            </span>
            <span className="km-weekly-gate-bar">
              <i
                style={{
                  width: `${Math.min(100, weekly.gateNeed ? (weekly.gateGot / weekly.gateNeed) * 100 : 0)}%`,
                }}
              />
            </span>
            <span className={`km-tag ${weekly.gateOk ? 'km-tag-lv' : 'km-tag-gray'}`}>
              {weekly.gateOk ? '已解锁' : '未解锁'}
            </span>
          </div>

          <div className="km-daily">
            {weekly.items.map((it, i) => (
              <button
                key={it.id}
                type="button"
                className={`km-daily-row${it.ok ? ' done' : ''}`}
                // 门槛没到就不给打：按钮必须在"能不能点"上诚实，
                // 否则用户点进去做完才发现不算，比不放按钮更挫败
                disabled={!weekly.gateOk && !it.answered}
                onClick={() => challengeQuestion(it.id)}
                title={weekly.gateOk ? it.title : `先本周答对 ${weekly.gateNeed} 题再来`}
              >
                <span className="km-daily-no">{it.ok ? '✓' : i + 1}</span>
                <span className="km-daily-main">
                  <b>{it.title}</b>
                  <span>
                    {DIFF_META[it.diff]?.label ?? it.diff} · {TYPE_META[it.qtype as keyof typeof TYPE_META]?.label ?? it.qtype}
                  </span>
                </span>
                <span className="km-tag km-tag-gray">{it.ok ? '已击败' : it.answered ? '再打一次' : '开打'}</span>
              </button>
            ))}
          </div>

          <p className="km-hint">
            {weekly.cleared
              ? `${weekly.week} 已收工，下周一换新的 BOSS。`
              : `三道全对才清空，奖励 +150 结晶、2 枚碎片，每周一次；答错的那道可以重打。`}
          </p>
        </section>
      )}

      {/* ── 今日试炼：三题真数据 ───────────────────────────────────────── */}
      <section className="km-card">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>今日试炼 · {dp.done}/{dp.total || 3}</h3>
          <span className="pct">{dp.allCorrect ? '全对' : dp.allDone ? '已清空' : '进行中'}</span>
        </div>
        <div className="km-daily-bar" style={{ marginTop: 10 }}>
          <i style={{ width: `${dp.total ? (dp.done / dp.total) * 100 : 0}%` }} />
        </div>

        {daily && daily.qids.length > 0 ? (
          <div className="km-daily">
            {daily.qids.map((qid, i) => {
              const ex = exerciseById(qid);
              const isDone = daily.done.includes(qid);
              const isWild = !!p.bestiary[qid] && p.bestiary[qid].state === 'wild';
              return (
                <button
                  key={qid}
                  type="button"
                  className={`km-daily-row${isDone ? ' done' : ''}`}
                  onClick={() => challengeQuestion(qid)}
                  title={ex?.title ?? qid}
                >
                  <span className="km-daily-no">{isDone ? '✓' : i + 1}</span>
                  <span className="km-daily-main">
                    <b>{ex?.title ?? qid}</b>
                    <span>
                      {isWild ? '错题复习 · ' : ''}
                      {ex ? chapterTitle(ex.ch) : '题库'}
                      {ex ? ` · ${DIFF_META[ex.diff]?.label ?? ex.diff}` : ''}
                      {ex ? ` · ${TYPE_META[ex.type]?.label ?? ex.type}` : ''}
                    </span>
                  </span>
                  {isWild && <span className="km-hp">HP {p.bestiary[qid].fails}</span>}
                  <span className="km-tag km-tag-gray">{isDone ? '已完成' : '去做'}</span>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="km-empty">
            <b>今天还没有题单</b>
            <span>切换学科或稍后再来，题单会按你的错题自动生成。</span>
          </div>
        )}

        <p className="km-hint">
          {dailyWild > 0
            ? '今日三题 = 错题里失败最多的 2 道 + 当前学科一道新题。清空 +50 结晶，全对再 +20。'
            : '今天没有错题，三题都是当前学科的新题；清空 +50 结晶，全对再 +20。做错的题会进图鉴。'}
        </p>
      </section>

      {/* ── 顺手项目 ───────────────────────────────────────────────────── */}
      <section className="km-card">
        <h3>顺手项目 · 把知识换成作品</h3>
        {todayProject ? (
          <div className="km-today">
            <div className="km-today-main">
              <div className="km-chips" style={{ marginBottom: 8 }}>
                <span className="km-tag km-tag-lv">{TIER_NAME[todayProject.tier]}</span>
                <span className="km-tag km-tag-gray">{todayProject.hours}h</span>
                <span className="km-tag km-tag-lv">★ {todayProject.stars.toLocaleString('zh-CN')}</span>
              </div>
              <b>{todayProject.title}</b>
              <p>{todayProject.summary}</p>
              <code>{todayProject.repo}</code>
            </div>
            <button
              type="button"
              className="km-btn km-btn-primary km-btn-sm"
              onClick={() => onNavigate('projects')}
            >
              查看详情
            </button>
          </div>
        ) : (
          <div className="km-empty">
            <b>T1 项目全部通关</b>
            <span>去 T2 看看，开始脱离教程独立做同构系统。</span>
          </div>
        )}
      </section>

      <section className="km-card">
        <h3>内容体量 · 真实数据</h3>
        <div className="km-stat-row" style={{ marginTop: 0 }}>
          <div className="km-stat">
            <b>{SUBJECTS.length}</b>
            <span>学科方向</span>
          </div>
          <div className="km-stat">
            <b>{totalChapters}</b>
            <span>章节单元</span>
          </div>
          <div className="km-stat">
            <b>{BUNDLE.projects.total}</b>
            <span>开源项目</span>
          </div>
          <div className="km-stat">
            <b>{t4}</b>
            <span>简历级 T4</span>
          </div>
        </div>
        <p className="km-hint">
          项目累计 {BUNDLE.projects.hours} 小时；每个项目的 star / 语言 / 许可证均来自 GitHub 实测，
          仓库链接直接跳原文。
        </p>
      </section>
    </div>
  );
}
