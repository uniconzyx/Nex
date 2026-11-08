/**
 * MiscPages.tsx —— 行囊与冒险者分组里的页面
 *
 * 这些页面不做假数据：
 *   签到 / 成就 / 支线 / 剧情里程碑 → 全部由本地真实进度推导；
 *   排行榜 → 展示真实的「学科内容体量榜」，个人榜明确标注需账号；
 *   怪物图鉴 → 读 progress.bestiary（错题落库后的真实记录）+ 260 条八股情报。
 *
 * 【P1 的关键变化】
 *   上一版图鉴页写着「判题结果只保存在会话内，所以图鉴是空的」——
 *   那句话本身就是该修的东西。现在判题/答题都会写进 bestiary，
 *   图鉴因此有内容可展示：怪物卡片、稀有度、失败次数、相关八股、去收服入口。
 *   八股情报库把 content/<学科>/_bagua.json 的 260 条全部接上，不再是"零消费资产"。
 */
import { useMemo, useState } from 'react';

import { BUNDLE } from '../data/bundle';
import { BAGUA_BY_SUBJECT, BAGUA_SUBJECTS, baguaOfSubject } from '../data/bagua';
import { SUBJECTS, subjectLabel, useSubject } from '../lib/subject';
import { checkinToday, streakOf, todayKey, useProgress } from '../lib/progress';
import { bestiaryStats, tamedMonsters, wildMonsters } from '../lib/progress';
import { intelFor, visualOf, tagsOf } from '../lib/bestiary';
import { chapterMastery } from '../lib/progress';
import { STORY, isTeaser, type StoryAct } from '../data/story';
import { challengeQuestion } from '../lib/challenge';
import { chapterTitle } from '../lib/exerciseBank';
import { RARITY_META, type Monster } from '../lib/gameTypes';
import type { KmPage } from '../lib/nav';
import { MonsterSprite } from '../components/MonsterSprite';
import { ZoomLightbox } from '../components/ZoomLightbox';
import { LongPressPreview } from '../components/LongPressPreview';
import { useParticles } from '../components/Particles';
import { usePageFade } from '../lib/hooks/usePageFade';
import { BottomSheet } from '../components/BottomSheet';
import { MemoryGame, MonsterMatchGame, PuzzleGame } from '../components/MiniGames';
import { OUTFITS } from './DressPage';

/* ── 签到祭坛 ─────────────────────────────────────────────────────────── */
export function CheckinPage() {
  const p = useProgress();
  const today = todayKey();
  const signed = p.checkins.includes(today);
  const streak = streakOf(p.checkins);
  /** 与 progress.applyCheckin 保持一致：20 + min(连击,6)×5 */
  const reward = 20 + Math.min(streak + 1, 6) * 5;

  const days = useMemo(() => {
    const out: { key: string; label: string; on: boolean; isToday: boolean }[] = [];
    for (let i = 13; i >= 0; i -= 1) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = todayKey(d);
      out.push({
        key,
        label: `${d.getMonth() + 1}/${d.getDate()}`,
        on: p.checkins.includes(key),
        isToday: key === today,
      });
    }
    return out;
  }, [p.checkins, today]);

  return (
    <div className="km-view">
      <section className="km-card">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>签到祭坛</h3>
          <span className="pct">连续 {streak} 天</span>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          每天签到得结晶：基础 20，连击每多一天 +5（最多加 30）。断一天连击归零，但结晶不会收回。
        </p>
        <div className="km-signin" style={{ marginTop: 14 }}>
          {days.map((d) => (
            <div key={d.key} className={`km-day${d.on ? ' on' : ''}${d.isToday ? ' today' : ''}`}>
              <i>{d.on ? '✓' : d.isToday ? '☆' : '·'}</i>
              <span>{d.label}</span>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16 }}>
          <button
            type="button"
            className={`km-btn km-btn-sm ${signed ? 'km-btn-ghost' : 'km-btn-primary'}`}
            onClick={checkinToday}
            disabled={signed}
          >
            {signed ? '今天已签到，明天再来' : `签到（+${reward} 结晶）`}
          </button>
        </div>
      </section>

      <section className="km-card">
        <h3>累计签到</h3>
        <div className="km-stat-row" style={{ marginTop: 0 }}>
          <div className="km-stat">
            <b>{p.checkins.length}</b>
            <span>总签到天数</span>
          </div>
          <div className="km-stat">
            <b>{streak}</b>
            <span>当前连击</span>
          </div>
          <div className="km-stat">
            <b>{p.coins}</b>
            <span>经验结晶</span>
          </div>
        </div>
      </section>
    </div>
  );
}

/* ── 成就殿堂 ─────────────────────────────────────────────────────────── */
interface Ach {
  id: string;
  name: string;
  desc: string;
  icon: string;
  done: boolean;
  progress: string;
}

export function AchievementsPage() {
  const p = useProgress();
  const bs = bestiaryStats(p);
  const t4Done = p.doneProjects.filter((slug) => {
    const it = BUNDLE.projects.items.find((i) => i.slug === slug);
    return it?.tier === 't4';
  }).length;

  const list: Ach[] = [
    {
      id: 'first-checkin',
      name: '初入祭坛',
      desc: '完成第一次签到',
      icon: '🕯️',
      done: p.checkins.length >= 1,
      progress: `${p.checkins.length}/1`,
    },
    {
      id: 'streak-7',
      name: '七日不断',
      desc: '连续签到 7 天',
      icon: '🔥',
      done: streakOf(p.checkins) >= 7,
      progress: `${streakOf(p.checkins)}/7`,
    },
    {
      id: 'chapter-1',
      name: '第一块拼图',
      desc: '掌握 1 个章节',
      icon: '📘',
      done: p.doneChapters.length >= 1,
      progress: `${p.doneChapters.length}/1`,
    },
    {
      id: 'chapter-10',
      name: '十章贯通',
      desc: '掌握 10 个章节',
      icon: '📚',
      done: p.doneChapters.length >= 10,
      progress: `${p.doneChapters.length}/10`,
    },
    {
      id: 'tame-1',
      name: '第一次收服',
      desc: '把一道错题重做通过',
      icon: '⚔️',
      done: bs.tamed >= 1,
      progress: `${bs.tamed}/1`,
    },
    {
      id: 'tame-10',
      name: '图鉴初成',
      desc: '收服 10 只怪物',
      icon: '🗂️',
      done: bs.tamed >= 10,
      progress: `${bs.tamed}/10`,
    },
    {
      id: 'wild-0',
      name: '一个不留',
      desc: '清空所有野生怪物（至少出现过 3 只）',
      icon: '🧹',
      done: bs.wild === 0 && bs.total >= 3,
      progress: `${bs.total - bs.wild}/${Math.max(bs.total, 3)}`,
    },
    {
      id: 'project-1',
      name: '首个战利品',
      desc: '通关 1 个项目',
      icon: '🏆',
      done: p.doneProjects.length >= 1,
      progress: `${p.doneProjects.length}/1`,
    },
    {
      id: 'project-5',
      name: '五连通关',
      desc: '通关 5 个项目',
      icon: '🏅',
      done: p.doneProjects.length >= 5,
      progress: `${p.doneProjects.length}/5`,
    },
    {
      id: 't4-1',
      name: '简历级挑战',
      desc: '通关 1 个 T4 项目',
      icon: '💎',
      done: t4Done >= 1,
      progress: `${t4Done}/1`,
    },
    {
      id: 'all-subject',
      name: '博览群书',
      desc: '在 5 个不同学科各掌握 1 章',
      icon: '🧭',
      done: (() => {
        let n = 0;
        for (const s of SUBJECTS) {
          const pack = BUNDLE.chapters[s.key as keyof typeof BUNDLE.chapters];
          if ((pack?.chapters ?? []).some((c) => p.doneChapters.includes(c.id))) n += 1;
        }
        return n >= 5;
      })(),
      progress: (() => {
        let n = 0;
        for (const s of SUBJECTS) {
          const pack = BUNDLE.chapters[s.key as keyof typeof BUNDLE.chapters];
          if ((pack?.chapters ?? []).some((c) => p.doneChapters.includes(c.id))) n += 1;
        }
        return `${n}/5`;
      })(),
    },
  ];

  const unlocked = list.filter((a) => a.done).length;

  return (
    <div className="km-view">
      <section className="km-card">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>成就殿堂</h3>
          <span className="pct">
            {unlocked} / {list.length}
          </span>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          成就条件全部取自真实进度（含图鉴收服记录），不发放「自动完成」的假徽章。
        </p>
      </section>

      <section className="km-card">
        <div className="km-ach-grid">
          {list.map((a) => (
            <div key={a.id} className={`km-ach${a.done ? ' on' : ''}`}>
              <span className="km-ach-ico">{a.done ? a.icon : '🔒'}</span>
              <b>{a.name}</b>
              <span>{a.desc}</span>
              <span className="km-tag km-tag-gray">{a.progress}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

/* ── 支线小屋 ─────────────────────────────────────────────────────────── */
export function MiniPage() {
  const p = useProgress();
  const bs = bestiaryStats(p);
  const dailyDone = p.daily?.done.length ?? 0;
  /** 当前打开的小游戏：null = 都没开 */
  const [game, setGame] = useState<'puzzle' | 'memory' | 'match' | null>(null);
  const tasks = [
    {
      id: 'daily',
      title: '清空今日试炼（3 题）',
      reward: '+50 结晶',
      done: (p.daily?.qids.length ?? 0) > 0 && dailyDone >= (p.daily?.qids.length ?? 0),
    },
    {
      id: 'tame',
      title: '收服 1 只野生怪物',
      reward: '+6~36 结晶',
      done: bs.tamed > 0,
    },
    {
      id: 'checkin',
      title: '去签到祭坛点亮今天',
      reward: '+20 起',
      done: p.checkins.includes(todayKey()),
    },
    {
      id: 'chapter3',
      title: '掌握任意 3 个章节',
      reward: '+60 结晶',
      done: p.doneChapters.length >= 3,
    },
  ];

  return (
    <div className="km-view">
      <section className="km-card">
        <h3>支线小屋</h3>
        <p className="km-hint" style={{ marginTop: 0 }}>
          支线是「今天顺手能做掉」的小事，状态实时反映你的真实进度。
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
          {tasks.map((t) => (
            <div key={t.id} className="km-task">
              <span className={`km-tick${t.done ? ' on' : ''}`}>✓</span>
              <span className={t.done ? 'km-task-done' : ''}>{t.title}</span>
              <span className="km-tag km-tag-lv">{t.reward}</span>
            </div>
          ))}
        </div>
      </section>

      {/* 支线小游戏：内容全部取自真实数据，玩法不影响进度 */}
      <section className="km-card">
        <h3>桌面上的三件玩具</h3>
        <p className="km-hint" style={{ marginTop: 0 }}>
          拼图盒还原真实项目的实施步骤，翻牌配对章节与它的主读书目，消消乐清理真实错题。玩坏了不扣任何东西。
        </p>
        <div className="kg-desk">
          <button type="button" className="kg-desk-item" onClick={() => setGame('puzzle')}>
            <span className="kg-desk-ico kg-ico-puzzle" aria-hidden="true" />
            <span className="kg-desk-text">
              <b>代码拼图盒</b>
              <em>把开源项目的实施步骤排回原位</em>
            </span>
            <span className="kg-desk-go" aria-hidden="true">→</span>
          </button>
          <button type="button" className="kg-desk-item" onClick={() => setGame('memory')}>
            <span className="kg-desk-ico kg-ico-memory" aria-hidden="true" />
            <span className="kg-desk-text">
              <b>记忆翻牌</b>
              <em>章节标题 ↔ 它的标志性资源</em>
            </span>
            <span className="kg-desk-go" aria-hidden="true">→</span>
          </button>
          <button type="button" className="kg-desk-item" onClick={() => setGame('match')}>
            <span className="kg-desk-ico kg-ico-match" aria-hidden="true" />
            <span className="kg-desk-text">
              <b>错题消消乐</b>
              <em>题面 ↔ 所属章节，错题优先登场</em>
            </span>
            <span className="kg-desk-go" aria-hidden="true">→</span>
          </button>
        </div>
      </section>

      <BottomSheet
        open={game !== null}
        onClose={() => setGame(null)}
        title={
          game === 'puzzle' ? '代码拼图盒' : game === 'memory' ? '记忆翻牌' : '错题消消乐'
        }
        ariaLabel="支线小游戏"
        className="kg-sheet"
      >
        {game === 'puzzle' && <PuzzleGame />}
        {game === 'memory' && <MemoryGame />}
        {game === 'match' && <MonsterMatchGame />}
      </BottomSheet>
    </div>
  );
}

/* ── 资源背包 ─────────────────────────────────────────────────────────── */
function fmtTime(ts: number): string {
  const d = new Date(ts);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export function BagPage() {
  const p = useProgress();
  const bs = bestiaryStats(p);
  const recent = p.coinLedger.slice(0, 10);

  return (
    <div className="km-view">
      <section className="km-card">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>资源背包</h3>
          <span className="pct">{p.coins} 结晶</span>
        </div>
        <p className="km-hint" style={{ marginTop: 6 }}>
          结晶来自清空试炼、收服怪物、掌握章节与签到；每一笔都能在下面查到原因。
          现在可以去「装扮衣柜」花掉它——买过的装扮永久归你，之后随便换不再收费。
        </p>
        <div className="km-stat-row" style={{ marginTop: 12 }}>
          <div className="km-stat">
            <b>{bs.tamed}</b>
            <span>已收服怪物</span>
          </div>
          <div className="km-stat">
            <b>{p.coinLedger.filter((e) => e.delta > 0).length}</b>
            <span>入账笔数</span>
          </div>
          <div className="km-stat">
            <b>{p.shards}</b>
            <span>装扮碎片</span>
          </div>
        </div>
      </section>

      <section className="km-card">
        <h3>结晶流水 · 最近 10 笔</h3>
        {recent.length === 0 ? (
          <div className="km-empty">
            <b>还没有入账记录</b>
            <span>去做一道题或签一次到，这里会立刻出现第一笔。</span>
          </div>
        ) : (
          <div className="km-ledger">
            {recent.map((e) => (
              <div key={`${e.ts}-${e.reason}`} className="km-ledger-row">
                <span className={`km-ledger-delta${e.delta < 0 ? ' neg' : ''}`}>
                  {e.delta > 0 ? '+' : '−'}
                  {Math.abs(e.delta)}
                </span>
                <span>{e.reason}</span>
                <time>{fmtTime(e.ts)}</time>
              </div>
            ))}
          </div>
        )}
        <p className="km-hint">
          流水只保留最近 50 笔，避免 localStorage 无限膨胀；余额不足时支出会被拒绝并提示差额。
        </p>
      </section>

      <section className="km-card">
        <h3>已拥有 · 套装 {OUTFITS.length}</h3>
        <div className="km-dress-grid">
          {OUTFITS.map((o) => (
            <div key={o.id} className={`km-dress${p.outfit === o.id ? ' on' : ''}`}>
              <img src={o.img} alt={o.name} loading="lazy" />
              <b>{o.name}</b>
              <span className="km-tag km-tag-gray">{p.outfit === o.id ? '穿着中' : o.tag}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

/* ── 排行榜 ───────────────────────────────────────────────────────────── */
export function RankPage() {
  const p = useProgress();
  const bs = bestiaryStats(p);
  const ranked = useMemo(() => [...BUNDLE.projects.tracks].sort((a, b) => b.n - a.n), []);
  const max = ranked[0]?.n ?? 1;

  return (
    <div className="km-view">
      <section className="km-card">
        <h3>学科内容体量榜</h3>
        <p className="km-hint" style={{ marginTop: 0 }}>
          这是本机真实数据（项目数），不是虚构的玩家排名。
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
          {ranked.map((t, i) => (
            <div key={t.key} className="km-rank">
              <span className={`km-rank-no${i < 3 ? ' top' : ''}`}>{i + 1}</span>
              <span className="km-rank-name">{t.label}</span>
              <span className="km-rank-bar">
                <i style={{ width: `${Math.round((t.n / max) * 100)}%` }} />
              </span>
              <b>{t.n}</b>
              <span className="km-rank-h">{t.hours}h</span>
            </div>
          ))}
        </div>
      </section>

      <section className="km-card">
        <h3>我的图鉴</h3>
        <div className="km-stat-row" style={{ marginTop: 0 }}>
          <div className="km-stat">
            <b>{bs.tamed}</b>
            <span>已收服</span>
          </div>
          <div className="km-stat">
            <b>{bs.wild}</b>
            <span>待收服</span>
          </div>
          <div className="km-stat">
            <b>{bs.shiny}</b>
            <span>变异个体</span>
          </div>
        </div>
      </section>

      <section className="km-card">
        <h3>好友排行榜</h3>
        <div className="km-empty">
          <b>当前是本地模式</b>
          <span>没有账号体系，无法聚合他人数据。接入登录后这里会显示好友 EXP 榜。</span>
        </div>
      </section>
    </div>
  );
}

/* ── 剧情日志 + 幕旁白（P3 · C4） ───────────────────────────────────────
   旁白不是装饰：每一条都锚在 goals.md 的一个认知点上（见 content/_story/acts.json），
   读完一章再看这一句，等于把"你刚学到什么"压缩成一行可复述的话。

   可见性规则（与 story.ts 的 isTeaser 一致）：
     pitfall / scene / field —— 没完成也能看。它们是"我当初怎么想错的"，
       提前读反而有钩子；剧透不成立，因为它说的是错误认知。
     archive —— 必须本章掌握度 ≥ 60% 才给看。它已经说了半个答案，
       没学过的人读到只会当成一句无意义的话，或者更糟：记住结论却不理解为什么。
   ──────────────────────────────────────────────────────────────────── */
const STORY_UNLOCK_MASTERY = 60;

function ActBlock({
  act,
  masteryOf,
}: {
  act: StoryAct;
  masteryOf: (id: string) => number;
}) {
  return (
    <div className="km-act">
      <div className="km-act-head">
        <b>{act.title}</b>
        <span className="km-tag km-tag-gray">{act.chapters.length} 幕</span>
      </div>
      <div className="km-act-lines">
        {act.chapters.map((l) => {
          const m = masteryOf(l.chapterId);
          const unlocked = m >= STORY_UNLOCK_MASTERY || isTeaser(l.tone);
          return (
            <div key={l.chapterId} className={`km-act-line${unlocked ? '' : ' locked'}`}>
              <span className="km-act-ch">{chapterTitle(l.chapterId)}</span>
              <span className="km-act-text">
                {unlocked ? l.line : '完成本章（掌握度 ≥ 60%）后解锁这段旁白。'}
              </span>
              {unlocked && (
                <span className={`km-act-tone t-${l.tone}`}>
                  {l.tone === 'archive' ? '已验证' : l.tone === 'pitfall' ? '当初的错' : '现场'}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function StoryPage() {
  const p = useProgress();
  const bs = bestiaryStats(p);
  const [subject] = useSubject();
  const [picked, setPicked] = useState(subject);

  const masteryOf = (id: string) => chapterMastery(id, p);

  /** 全局解锁进度：分母是 153 条台词，分子是"现在能读到"的条数 */
  const storyStat = useMemo(() => {
    let total = 0;
    let open = 0;
    for (const s of STORY) {
      for (const a of s.acts) {
        for (const l of a.chapters) {
          total += 1;
          if (masteryOf(l.chapterId) >= STORY_UNLOCK_MASTERY || isTeaser(l.tone)) open += 1;
        }
      }
    }
    return { total, open };
    // masteryOf 依赖 p，用 p 做依赖即可
  }, [p]);

  const current = STORY.find((s) => s.key === picked) ?? STORY[0];
  const milestones = [
    {
      title: '序章 · 凯喵苏醒',
      time: '客户端首次启动',
      done: true,
      desc: '你打开了凯喵Code试炼录，冒险从这里开始。',
    },
    {
      title: '第一章 · 第一次签到',
      time: p.checkins.length ? [...p.checkins].sort()[0] : '未解锁',
      done: p.checkins.length > 0,
      desc: '祭坛的火点亮了，凯喵记住了你的名字。',
    },
    {
      title: '第二章 · 第一块知识拼图',
      time: p.doneChapters.length ? '已达成' : '未解锁',
      done: p.doneChapters.length > 0,
      desc: '你掌握了第一个章节，知识树亮起一格。',
    },
    {
      title: '第三章 · 第一次收服',
      time: bs.tamed > 0 ? `${bs.tamed} 只已收服` : '未解锁',
      done: bs.tamed > 0,
      desc: '你把一道做错的题重新做了出来。图鉴里从此有了第一只属于你的怪物。',
    },
    {
      title: '第四章 · 首个作品',
      time: p.doneProjects.length ? '已达成' : '未解锁',
      done: p.doneProjects.length > 0,
      desc: '第一个项目通关，它已经可以写进作品集。',
    },
    {
      title: '终章 · 简历级挑战',
      time: '未解锁',
      done: p.doneProjects.some((s) => BUNDLE.projects.items.find((i) => i.slug === s)?.tier === 't4'),
      desc: '通关一个 T4 项目，你会拥有能讲 40 分钟的工程故事。',
    },
  ];

  return (
    <div className="km-view">
      <section className="km-card">
        <h3>剧情日志</h3>
        <div className="km-timeline" style={{ marginTop: 14 }}>
          {milestones.map((m) => (
            <div key={m.title} className={`km-tl${m.done ? '' : ' locked'}`}>
              <b>{m.title}</b>
              <span className="km-tl-time">{m.time}</span>
              <p>{m.desc}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="km-card">
        <div className="km-cont-top">
          <h3 style={{ margin: 0 }}>幕 · 旁白</h3>
          <span className="pct">
            {storyStat.open} / {storyStat.total} 已解锁
          </span>
        </div>
        <p className="km-hint" style={{ marginTop: 8 }}>
          每一幕对应一章：先读「当初的错」，学完拿「已验证」。绿色标记的条目已可读。
        </p>
        <div className="km-chips" style={{ marginTop: 10 }}>
          {STORY.map((s) => (
            <button
              key={s.key}
              type="button"
              className={`km-chip${s.key === picked ? ' on' : ''}`}
              onClick={() => setPicked(s.key)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="km-acts">
          {current.acts.map((a) => (
            <ActBlock key={a.id} act={a} masteryOf={masteryOf} />
          ))}
        </div>
      </section>
    </div>
  );
}

/* ── 怪物图鉴 ─────────────────────────────────────────────────────────── */
type BestTab = 'wild' | 'tamed' | 'all' | 'archive';

export function BestiaryPage({ onNavigate }: { onNavigate: (p: KmPage) => void }) {
  const p = useProgress();
  const bs = bestiaryStats(p);
  const wild = useMemo(() => wildMonsters(p), [p]);
  const tamed = useMemo(() => tamedMonsters(p), [p]);
  const [tab, setTab] = useState<BestTab>('wild');
  const [openId, setOpenId] = useState<string | null>(null);
  const [subject] = useSubject();
  const [archiveSubject, setArchiveSubject] = useState<string>(subject);
  // S0：长按预览 / 选中粒子反馈 / 整页淡入
  const particles = useParticles();
  const viewRef = usePageFade();

  const list: Monster[] = tab === 'wild' ? wild : tab === 'tamed' ? tamed : [...wild, ...tamed];
  const selected = list.find((m) => m.questionId === openId) ?? null;

  return (
    <div className="km-view" ref={viewRef}>
      {/* ── 头部统计 ── */}
      <section className="km-card">
        <div className="km-best-head">
          <div>
            <h3 style={{ margin: 0 }}>怪物图鉴</h3>
            <p className="km-hint" style={{ margin: '4px 0 0' }}>
              判题与答题都落库：做错一题生成一只怪物，重做通过即收服。
            </p>
          </div>
          <div className="km-best-stats">
            <div className="km-best-stat">
              <b style={{ color: 'var(--km-bad)' }}>{bs.wild}</b>
              <span>待收服</span>
            </div>
            <div className="km-best-stat">
              <b style={{ color: 'var(--km-ok)' }}>{bs.tamed}</b>
              <span>已收服</span>
            </div>
            <div className="km-best-stat">
              <b>{bs.fails}</b>
              <span>累计失败</span>
            </div>
            <div className="km-best-stat">
              <b style={{ color: 'var(--km-legend)' }}>{bs.shiny}</b>
              <span>变异个体</span>
            </div>
          </div>
        </div>

        <div className="km-best-tabs" role="tablist" aria-label="图鉴分类">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'wild'}
            className={`km-best-tab${tab === 'wild' ? ' on' : ''}`}
            onClick={() => {
              setTab('wild');
              setOpenId(null);
            }}
          >
            待收服 <i>{bs.wild}</i>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'tamed'}
            className={`km-best-tab${tab === 'tamed' ? ' on' : ''}`}
            onClick={() => {
              setTab('tamed');
              setOpenId(null);
            }}
          >
            已收服 <i>{bs.tamed}</i>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'all'}
            className={`km-best-tab${tab === 'all' ? ' on' : ''}`}
            onClick={() => {
              setTab('all');
              setOpenId(null);
            }}
          >
            全部 <i>{bs.total}</i>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'archive'}
            className={`km-best-tab${tab === 'archive' ? ' on' : ''}`}
            onClick={() => setTab('archive')}
          >
            八股情报库 <i>260</i>
          </button>
        </div>
      </section>

      {/* ── 怪物列表 ── */}
      {tab !== 'archive' && (
        <section className="km-card">
          {list.length === 0 ? (
            <div className="km-empty">
              <b>{tab === 'tamed' ? '还没有收服记录' : tab === 'wild' ? '没有待收服的怪物' : '图鉴还是空的'}</b>
              <span>
                {tab === 'wild'
                  ? '做错一道题，它就会变成怪物出现在这里；重做通过即可收服。'
                  : '去试炼实验室做题，答错的题会自动进图鉴。'}
              </span>
              <button
                type="button"
                className="km-btn km-btn-primary km-btn-sm"
                onClick={() => onNavigate('lab')}
              >
                去试炼实验室
              </button>
            </div>
          ) : (
            <div className="km-mon-grid">
              {list.map((m) => {
                const v = visualOf(m);
                const isJustTamed = m.state === 'tamed' && !!m.tamedAt && Date.now() - m.tamedAt < 6000;
                const meta = RARITY_META[v.rarity];
                return (
                  <button
                    type="button"
                    key={m.questionId}
                    className={`km-mon-card${openId === m.questionId ? ' on' : ''}${
                      isJustTamed ? ' just-tamed' : ''
                    }`}
                    onClick={(e) => {
                      const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
                      particles.emit(r.left + r.width / 2, r.top + r.height / 2, 'combo');
                      setOpenId(openId === m.questionId ? null : m.questionId);
                    }}
                    title={m.title}
                  >
                    <LongPressPreview
                      ariaLabel={`${m.title} 速览`}
                      render={() => (
                        <div className="km-lp-card">
                          <div className="km-lp-title">{m.title}</div>
                          <div className="km-lp-row">
                            <span className="km-rarity" style={{ background: meta.color }}>{meta.label}</span>
                            <span>{chapterTitle(m.chapterId)}</span>
                          </div>
                          <div className="km-lp-row">
                            <span>{m.state === 'tamed' ? '已收服' : `HP ${m.fails}`}</span>
                          </div>
                        </div>
                      )}
                    >
                      <MonsterSprite monster={m} size={84} />
                    </LongPressPreview>
                    <b>{m.title}</b>
                    <span className="km-mon-ch">{chapterTitle(m.chapterId)}</span>
                    <span className="km-mon-badges">
                      <span className="km-rarity" style={{ background: RARITY_META[v.rarity].color }}>
                        {v.label}
                      </span>
                      <span className={`km-hp${m.state === 'tamed' ? ' ok' : ''}`}>
                        {m.state === 'tamed' ? '已收服' : `HP ${m.fails}`}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {selected && <MonsterDetail monster={selected} onNavigate={onNavigate} />}
        </section>
      )}

      {/* ── 八股情报库：把 260 条内容全部接上 ── */}
      {tab === 'archive' && (
        <ArchivePanel subject={archiveSubject} onSubject={setArchiveSubject} />
      )}
    </div>
  );
}

/* 图鉴详情：怪物 + 相关八股 + 去收服 */
function MonsterDetail({ monster, onNavigate }: { monster: Monster; onNavigate: (p: KmPage) => void }) {
  const hits = useMemo(() => intelFor(monster, 2), [monster]);
  const tags = useMemo(() => tagsOf(monster.questionId), [monster.questionId]);
  const v = visualOf(monster);
  const meta = RARITY_META[v.rarity];
  const [zoom, setZoom] = useState(false);
  const fmt = (ts?: number) =>
    ts ? new Date(ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—';

  return (
    <div className="km-mon-detail">
      <ZoomLightbox open={zoom} onClose={() => setZoom(false)} title={`${monster.title} · ${meta.label}`}>
        <div className="km-mon-zoom-svg">
          <MonsterSprite monster={monster} size={320} />
          <p>{monster.title} · {meta.label}</p>
        </div>
      </ZoomLightbox>
      <div className="km-mon-detail-head">
        <button
          type="button"
          className="km-mon-spr-btn"
          onClick={() => setZoom(true)}
          title="放大 / 缩小查看怪物立绘"
          aria-label={`放大查看 ${monster.title} 立绘`}
        >
          <MonsterSprite monster={monster} size={76} />
        </button>
        <div style={{ minWidth: 0, flex: 1 }}>
          <h4>{monster.title}</h4>
          <div className="km-mon-meta">
            <span className="km-rarity" style={{ background: meta.color }}>
              {meta.label}
            </span>
            <span>{chapterTitle(monster.chapterId)}</span>
            <span>{monster.state === 'tamed' ? `收服于 ${fmt(monster.tamedAt)}` : `被打败 ${monster.fails} 次`}</span>
            <span>首次 {fmt(monster.firstAt)}</span>
          </div>
          {tags.length > 0 && (
            <div className="km-mon-meta" style={{ marginTop: 6 }}>
              {tags.slice(0, 6).map((t) => (
                <span key={t} className="km-tag km-tag-gray">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="km-mon-detail-actions">
          <button
            type="button"
            className="km-btn km-btn-sm km-btn-primary"
            onClick={() => challengeQuestion(monster.questionId)}
          >
            {monster.state === 'tamed' ? '再做一遍' : '去收服'}
          </button>
          <button type="button" className="km-btn km-btn-sm km-btn-ghost" onClick={() => onNavigate('learn')}>
            看所属章节
          </button>
        </div>
      </div>

      <div className="km-intel">
        <div className="km-intel-title">
          情报 · {hits.some((h) => h.score > 0) ? '按题目标签命中' : '同学科高频（本题无直接命中）'}
          <span>来自 content/&lt;学科&gt;/_bagua.json</span>
        </div>
        {hits.map((h) => (
          <details key={h.item.id} className="km-intel-item">
            <summary>{h.item.q}</summary>
            <div className="km-intel-a">{h.item.a}</div>
            <div className="km-intel-tags">
              {h.matchedTags.map((t) => (
                <span key={t} className="km-tag km-tag-lv">
                  {t}
                </span>
              ))}
              <span className="km-tag km-tag-gray">{h.item.difficulty}</span>
              <span className="km-tag km-tag-gray">热度 {h.item.hot}</span>
            </div>
            {h.item.src && <div className="km-intel-src">出处：{h.item.src}</div>}
          </details>
        ))}
      </div>
    </div>
  );
}

/* 八股情报库：按学科浏览，260 条全部可读 */
function ArchivePanel({ subject, onSubject }: { subject: string; onSubject: (s: string) => void }) {
  const items = useMemo(() => (subject ? baguaOfSubject(subject) : []), [subject]);
  const cats = useMemo(() => {
    const map = new Map<string, typeof items>();
    for (const it of items) {
      const arr = map.get(it.category) ?? [];
      arr.push(it);
      map.set(it.category, arr);
    }
    return [...map.entries()];
  }, [items]);

  const total = items.length;

  return (
    <section className="km-card">
      <h3>八股情报库 · {subjectLabel(subject)} 共 {total} 条</h3>
      <p className="km-hint" style={{ marginTop: 0 }}>
        这些是各学科真实的面试高频问题（含出处），平时藏在图鉴的「情报」里，
        这里按分类全量可读。选不同学科切换。
      </p>
      <div className="km-archive-sub">
        {BAGUA_SUBJECTS.map((s) => (
          <button
            key={s}
            type="button"
            className={`km-best-tab${s === subject ? ' on' : ''}`}
            onClick={() => onSubject(s)}
          >
            {subjectLabel(s)}
            <i>{BAGUA_BY_SUBJECT[s]?.length ?? 0}</i>
          </button>
        ))}
      </div>

      {cats.map(([cat, arr]) => (
        <div key={cat} className="km-archive-cat">
          <b>
            {cat} · {arr.length} 条
          </b>
          {arr.map((it) => (
            <details key={it.id} className="km-intel-item">
              <summary>{it.q}</summary>
              <div className="km-intel-a">{it.a}</div>
              <div className="km-intel-tags">
                {it.tags.map((t) => (
                  <span key={t} className="km-tag km-tag-gray">
                    {t}
                  </span>
                ))}
                <span className="km-tag km-tag-lv">热度 {it.hot}</span>
              </div>
              {it.src && <div className="km-intel-src">出处：{it.src}</div>}
            </details>
          ))}
        </div>
      ))}
    </section>
  );
}
