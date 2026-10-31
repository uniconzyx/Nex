/**
 * KaimaoShell.tsx —— 「凯喵Code试炼录」React 外壳
 *
 * 三栏为主（主人 2026-10-30 定）：
 *   顶栏 64px（品牌 / 等级经验 / 经验结晶 / 搜索·主题·设置）
 *   左栏 220px（冒险 / 行囊 / 考研 / 求职 / AI / 冒险者 六组导航）
 *   中间自适应（业务页）
 *   右栏 300px（凯喵伙伴 / 今日目标〔含内容体量〕）
 *
 * 悬浮入口只有一颗球：App 里的「AI 助手」（CppCatFab，已由长条胶囊改成圆形悬浮球）。
 * 右栏凯喵卡保持原样，两者分工不同——卡是伙伴面板，球是 AI 唤起。
 *
 * 聚焦页（FOCUS_PAGES，当前只有「就业」）：右栏整列收起、内容居中，
 * 让求职三块（八股 / 简历 / 项目）能按门户式居中版式铺开。
 *
 * 响应式：<1180px 收掉右栏；<900px 侧栏变顶部横滑条。
 * 桌面端与 Android 端共用这一份代码，不做平台分叉。
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';

import { BUNDLE } from '../data/bundle';
import { NAV_FLAT, NAV_GROUPS, type KmPage, type NavItem } from '../lib/nav';
import { bestiaryStats, expOf, streakOf, todayKey, useProgress } from '../lib/progress';
import { masterySummary } from '../lib/graph';
import { useCoinPulse } from '../lib/feedback';
import { dailyProgress, useDaily } from '../lib/daily';
import { useSubject } from '../lib/subject';
import {
  MOODS,
  moodImage,
  resolveMood,
  useMoodFlash,
  type MoodCtx,
  type MoodDef,
  type MoodKey,
} from '../lib/mood';
import { ConnectionBadge } from './ConnectionBadge';
import { OfflineBanner } from './OfflineBanner';
import { BottomSheet } from './BottomSheet';

function Icon({ paths, size = 18 }: { paths: string[]; size?: number }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths.map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}

const OUTFIT_IMG: Record<string, string> = {
  default: '/assets/kaimao/mood-idle.png',
  cape: '/assets/kaimao/outfit-cape.png',
  scarf: '/assets/kaimao/outfit-scarf.png',
  glasses: '/assets/kaimao/outfit-glasses.png',
  nightprowler: '/assets/kaimao/outfit-nightprowler.png',
  cyberpunk: '/assets/kaimao/outfit-cyberpunk.png',
  panda: '/assets/kaimao/outfit-panda.png',
  wizard: '/assets/kaimao/outfit-wizard.png',
};

const OUTFIT_NAME: Record<string, string> = {
  default: '日常便装',
  cape: '见习披风',
  scarf: '绒线围巾',
  glasses: '黑框眼镜',
  nightprowler: '暗夜行者',
  cyberpunk: '赛博朋克',
  panda: '熊猫卫衣',
  wizard: '魔法学院长袍',
};

export interface ShellProps {
  active: KmPage;
  onNavigate: (page: KmPage) => void;
  /** 点右侧凯喵立绘 → 打开 AI 对话框（替代桌面端那颗浮动按钮） */
  onOpenAi?: () => void;
  children: React.ReactNode;
}

/**
 * 聚焦页：右栏收起、正文居中。
 * 目前只有「就业」——它是求职作战室，三块内容本身就是门户式居中版式，
 * 右侧再压一列会把它挤成窄条。以后有同类页面往这里加即可。
 */
const FOCUS_PAGES: KmPage[] = ['employment'];

export function KaimaoShell({
  active,
  onNavigate,
  onOpenAi,
  children,
}: ShellProps) {
  const p = useProgress();
  const [searchOpen, setSearchOpen] = useState(false);
  const [kw, setKw] = useState('');
  /** ≤1180 右栏隐藏后，凯喵/目标/快捷改从这里进来 */
  const [railOpen, setRailOpen] = useState(false);
  /** ≤900 导航横条只有一小截可见，用「全部」打开分组面板 */
  const [navOpen, setNavOpen] = useState(false);
  /** 当前页是否走「聚焦」版式（右栏收起、正文居中） */
  const focus = FOCUS_PAGES.includes(active);
  /** 移动端横滑条：切页时把当前项滑进视野，否则选中项可能藏在滚动区外 */
  const navRef = useRef<HTMLElement | null>(null);

  

  // 章节总数与平均掌握度都从依赖图取：它包含 clang 的 7 个独立单元（141 章），
  // 只数 BUNDLE.chapters 会漏掉 C 语言模块（133 章）。
  const mastery = useMemo(() => masterySummary(p), [p]);
  const totalChapters = mastery.total;
  const avgMastery = mastery.avg;
  const doneChapters = p.doneChapters.length;
  const doneProjects = p.doneProjects.length;
  /** 经验口径统一到 progress.expOf：收服怪物也算经验，否则图鉴的成长感是断的 */
  const exp = expOf(p);
  const level = 1 + Math.floor(exp / 300);
  const levelName = ['初入试炼', '语法学徒', '指针学徒', '容器行者', '并发术士', '源码猎人', '架构导师'][
    Math.min(level - 1, 6)
  ];
  const levelPct = Math.round(((exp % 300) / 300) * 100);
  const streak = streakOf(p.checkins);

  /** 图鉴里的野生怪物数 → 导航徽标 + 右栏今日目标，让「有东西没做」一直可见 */
  const bs = bestiaryStats(p);
  const [subject] = useSubject();
  const daily = useDaily(subject);
  const dp = dailyProgress(daily);
  const coinPulse = useCoinPulse();

  const badgeOf = (n: NavItem): string | undefined => {
    if (n.key === 'bestiary') return bs.wild > 0 ? String(bs.wild) : n.badge;
    return n.badge;
  };

  /**
   * 情绪：常态由跨日进度算出，瞬时由答题结果打断（progress.recordAnswer 推 flash）。
   * flash 必须优先——刚答错时的「委屈」要盖住「今天已签到」的开心，
   * 否则脸在答错那一刻纹丝不动，情绪就成了摆设。
   */
  const moodFlash = useMoodFlash();
  const moodCtx: MoodCtx = {
    checkedIn: p.checkins.includes(todayISO()),
    streak,
    dailyDone: dp.done,
    dailyTotal: dp.total,
    wild: bs.wild,
    doneChapters,
    doneProjects,
    page: active,
    hour: new Date().getHours(),
  };
  const moodKey: MoodKey = moodFlash?.key ?? resolveMood(moodCtx);
  const mood = MOODS[moodKey];

  /**
   * 立绘：没穿装扮（default）时直接用心情图——这是玩家最看得清的「换脸」；
   * 穿了装扮（花结晶买的）就优先装扮图，心情退成角落一枚小徽章。
   * 素材是两套平行立绘、没有「装扮 × 情绪」的交叉图，这是唯一不偏心的解法。
   */
  const dressed = p.outfit !== 'default';
  const catSrc = dressed ? (OUTFIT_IMG[p.outfit] ?? OUTFIT_IMG.default) : moodImage(moodKey);

  const searchResults = useMemo(() => {
    const q = kw.trim().toLowerCase();
    if (!q) return [];
    const navHit = NAV_FLAT.filter((n) => n.label.toLowerCase().includes(q)).slice(0, 4);
    const projHit = BUNDLE.projects.items
      .filter(
        (it) =>
          it.title.toLowerCase().includes(q) ||
          it.repo.toLowerCase().includes(q) ||
          it.stack.join(' ').toLowerCase().includes(q),
      )
      .slice(0, 6);
    return [
      ...navHit.map((n) => ({ kind: '页面' as const, title: n.label, sub: '', go: n.key })),
      ...projHit.map((it) => ({
        kind: '项目' as const,
        title: it.title,
        sub: `${it.repo} · ★ ${it.stars}`,
        go: 'projects' as KmPage,
      })),
    ];
  }, [kw]);

  // 移动端横滑导航：切页后把当前项滑进可见区（桌面侧栏 scrollWidth==clientWidth，直接 return）
  useEffect(() => {
    const box = navRef.current;
    if (!box || box.scrollWidth <= box.clientWidth + 4) return;
    const el = box.querySelector<HTMLElement>('.km-nav-item.on');
    if (!el) return;
    box.scrollTo({ left: Math.max(0, el.offsetLeft - 14), behavior: 'smooth' });
  }, [active]);

  return (
    <div className="km-app" data-km-theme={p.theme}>
      <header className="km-topbar">
        <div className="km-brand" role="button" tabIndex={0} onClick={() => onNavigate('home')}>
          <img src="/assets/kaimao/mood-happy.png" alt="凯喵" />
          <span>凯喵Code试炼录</span>
        </div>

        <div className="km-xp">
          <div className="km-xp-label">
            <span>
              <b>
                Lv.{level} {levelName}
              </b>{' '}
              · 闯关经验
            </span>
            <span>{exp % 300} / 300 EXP</span>
          </div>
          <div className="km-xp-bar">
            <div className="km-xp-fill" style={{ width: `${Math.max(levelPct, 1)}%` }} />
            <div className="km-xp-text">累计 {exp} EXP</div>
          </div>
        </div>

        <div className="km-coin" title="经验结晶">
          <i />
          {p.coins.toLocaleString('zh-CN')}
          {/* 每一笔金币都先在这里冒一下：进账没有反馈，结晶就只是个装饰数字 */}
          {coinPulse && (
            <span key={coinPulse.id} className={`km-coin-pop${coinPulse.delta < 0 ? ' neg' : ''}`}>
              {coinPulse.delta > 0 ? '+' : '−'}
              {Math.abs(coinPulse.delta)}
            </span>
          )}
        </div>

        <div className="km-top-icons">
          <ConnectionBadge onNavigate={onNavigate} />
          <button
            type="button"
            className="km-rail-toggle"
            onClick={() => setRailOpen(true)}
            aria-label="打开凯喵与今日目标"
            title="凯喵 · 今日目标"
          >
            <Icon size={15} paths={['M8 21h8M12 17v4', 'M7 4h10v5a5 5 0 0 1-10 0z']} />
            <span>目标</span>
          </button>
          <button
            type="button"
            className="km-icon-btn"
            title="搜索（页面 / 项目）"
            onClick={() => setSearchOpen((v) => !v)}
            aria-label="搜索"
          >
            <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
          </button>
          <button
            type="button"
            className="km-icon-btn"
            title="设置"
            onClick={() => onNavigate('settings')}
            aria-label="设置"
          >
            <Icon size={19} paths={NAV_FLAT.find((n) => n.key === 'settings')?.paths ?? []} />
          </button>
        </div>

        {searchOpen && (
          <div className="km-search-pop">
            <input
              autoFocus
              value={kw}
              onChange={(e) => setKw(e.target.value)}
              placeholder="搜索页面 / 项目 / 技术栈…"
              aria-label="搜索关键词"
            />
            <div className="km-search-res">
              {!kw.trim() && <div className="km-search-empty">输入关键词，例如 redis、Java、排行榜</div>}
              {kw.trim() && searchResults.length === 0 && (
                <div className="km-search-empty">没有匹配结果</div>
              )}
              {searchResults.map((r, i) => (
                <button
                  type="button"
                  key={`${r.kind}-${r.title}-${i}`}
                  className="km-search-row"
                  onClick={() => {
                    onNavigate(r.go);
                    setSearchOpen(false);
                    setKw('');
                  }}
                >
                  <span className="km-search-kind">{r.kind}</span>
                  <span className="km-search-t">
                    <b>{r.title}</b>
                    {r.sub && <em>{r.sub}</em>}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </header>

      <div className={`km-main${focus ? ' km-main--focus' : ''}`}>
        <div className="km-nav-shell">
          <nav className="km-sidenav" aria-label="主导航" ref={navRef}>
          {NAV_GROUPS.map((g) => (
            <div key={g.title} className="km-nav-group">
              <div className="km-nav-sep">{g.title}</div>
              {g.items.map((n) => (
                <button
                  type="button"
                  key={n.key}
                  className={`km-nav-item${active === n.key ? ' on' : ''}`}
                  aria-current={active === n.key ? 'page' : undefined}
                  onClick={() => onNavigate(n.key)}
                >
                  <Icon paths={n.paths} />
                  {n.label}
                  {badgeOf(n) && <span className="km-nav-badge">{badgeOf(n)}</span>}
                </button>
              ))}
            </div>
          ))}
          <div className="km-nav-foot">
            判题沙箱 go-judge v1.13.3
            <br />
            客户端 v2.0.0 · Tauri
          </div>
          </nav>
          <button
            type="button"
            className="km-nav-all"
            onClick={() => setNavOpen(true)}
            aria-label="查看全部导航"
          >
            全部
          </button>
        </div>

        <main className="km-content">
          <OfflineBanner onNavigate={onNavigate} />
          {children}
        </main>

        <aside className="km-right">
          <RightRail
            catSrc={catSrc}
            mood={mood}
            moodKey={moodKey}
            moodCtx={moodCtx}
            dressed={dressed}
            outfitName={OUTFIT_NAME[p.outfit] ?? '日常便装'}
            doneChapters={doneChapters}
            doneProjects={doneProjects}
            streak={streak}
            totalChapters={totalChapters}
            avgMastery={avgMastery}
            checkins={p.checkins}
            dailyDone={dp.done}
            dailyTotal={dp.total}
            wild={bs.wild}
            onOpenAi={onOpenAi}
          />
        </aside>
      </div>

      {/* ≤1180：右栏被隐藏后，凯喵 / 今日目标从这里进来 */}
      {railOpen && (
        <>
          <div className="km-rail-scrim" onClick={() => setRailOpen(false)} />
          <aside
            className="km-rail-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="凯喵与今日目标"
          >
            <div className="km-rail-head">
              <b>凯喵 · 今日目标</b>
              <button type="button" onClick={() => setRailOpen(false)} aria-label="关闭">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>
            <RightRail
              catSrc={catSrc}
              mood={mood}
              moodKey={moodKey}
              moodCtx={moodCtx}
              dressed={dressed}
              outfitName={OUTFIT_NAME[p.outfit] ?? '日常便装'}
              doneChapters={doneChapters}
              doneProjects={doneProjects}
              streak={streak}
              totalChapters={totalChapters}
              avgMastery={avgMastery}
              checkins={p.checkins}
              dailyDone={dp.done}
              dailyTotal={dp.total}
              wild={bs.wild}
              onOpenAi={onOpenAi}
            />
          </aside>
        </>
      )}

      {/* ≤900：横条放不下 15 项，用「全部」按原分组展开（复用 S0 统一 BottomSheet） */}
      <BottomSheet
        open={navOpen}
        onClose={() => setNavOpen(false)}
        title="全部导航"
        className="km-nav-sheet"
        ariaLabel="全部导航"
      >
        {NAV_GROUPS.map((g) => (
          <div key={g.title} className="km-nav-sheet-group">
            <div className="km-nav-sep">{g.title}</div>
            <div className="km-nav-sheet-grid">
              {g.items.map((n) => (
                <button
                  type="button"
                  key={n.key}
                  className={`km-nav-item${active === n.key ? ' on' : ''}`}
                  onClick={() => {
                    onNavigate(n.key);
                    setNavOpen(false);
                  }}
                >
                  <Icon paths={n.paths} />
                  {n.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </BottomSheet>
    </div>
  );
}

function todayISO(): string {
  return todayKey();
}

interface RightRailProps {
  catSrc: string;
  /** 当前情绪（已含瞬时 flash 的择优结果） */
  mood: MoodDef;
  moodKey: MoodKey;
  /** 判定情绪用的快照，台词里的数字从这儿取，保证「说的」和「算的」一致 */
  moodCtx: MoodCtx;
  /** 穿装扮时主图是装扮，心情退成角落小徽章 */
  dressed: boolean;
  outfitName: string;
  doneChapters: number;
  doneProjects: number;
  streak: number;
  totalChapters: number;
  /** 全库平均掌握度（三关加权后的 0~100） */
  avgMastery: number;
  checkins: string[];
  dailyDone: number;
  dailyTotal: number;
  wild: number;
  onOpenAi?: () => void;
}

/**
 * 右栏内容。桌面直接放进 aside；≤1180 时同一份内容放进抽屉，
 * 避免「隐藏右栏 = 删掉功能」。
 */
function RightRail({
  catSrc,
  mood,
  moodKey,
  moodCtx,
  dressed,
  outfitName,
  doneChapters,
  doneProjects,
  streak,
  totalChapters,
  avgMastery,
  checkins,
  dailyDone,
  dailyTotal,
  wild,
  onOpenAi,
}: RightRailProps) {
  const affection = 64 + Math.min(doneChapters + doneProjects, 30);

  return (
    <>
      <div
        className={`km-cat-card${onOpenAi ? ' km-cat-card--btn' : ''}`}
        onClick={onOpenAi}
        role={onOpenAi ? 'button' : undefined}
        tabIndex={onOpenAi ? 0 : undefined}
        title={onOpenAi ? '和凯喵聊聊 / 打开 AI 解题' : undefined}
        onKeyDown={(e) => {
          if (onOpenAi && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            onOpenAi();
          }
        }}
      >
        <div
          className="km-cat-stage"
          style={{ '--mood-aura': mood.aura } as CSSProperties}
          data-mood={moodKey}
        >
          <div className={`km-cat-aura km-cat-aura--${moodKey}`} />
          {/* key 让换脸时 img 重新挂载，触发淡入——直接改 src 会硬切 */}
          <img key={moodKey} src={catSrc} alt={`凯喵 · ${dressed ? outfitName : mood.label}`} />
          {dressed && (
            <img
              className="km-cat-mood-badge"
              src={moodImage(moodKey)}
              alt={mood.label}
              title={mood.label}
            />
          )}
        </div>
        <div className="km-cat-name">凯喵</div>
        <div className="km-cat-mood">
          <span aria-hidden="true">{mood.emoji}</span> {mood.label}
        </div>
        <div className="km-aff-row">
          <span>好感度</span>
          <b>{affection}%</b>
        </div>
        <div className="km-aff-bar">
          <i style={{ width: `${affection}%` }} />
        </div>
        <div className="km-cat-say">{mood.say(moodCtx)}</div>
      </div>

      <div className="km-side-card">
        <h4>
          <Icon size={16} paths={['M8 21h8M12 17v4', 'M7 4h10v5a5 5 0 0 1-10 0z']} />
          今日目标
        </h4>
        <div className="km-goal">
          {/* 今日目标改成「今天真的能做完的三件事」，前两条直接读每日试炼与图鉴 */}
          <div className="km-goal-row">
            <span className={`km-tick${dailyTotal > 0 && dailyDone >= dailyTotal ? ' on' : ''}`}>✓</span>
            今日试炼 {dailyDone} / {dailyTotal || 3}
          </div>
          <div className="km-goal-row">
            <span className={`km-tick${wild === 0 && dailyDone > 0 ? ' on' : ''}`}>✓</span>
            {wild > 0 ? `收服 ${wild} 只野生怪物` : '图鉴里没有待收服的怪物'}
          </div>
          <div className="km-goal-row">
            <span className={`km-tick${checkins.includes(todayISO()) ? ' on' : ''}`}>✓</span>
            签到祭坛打卡
          </div>
          <div className="km-goal-row">
            <span className="km-tick" />
            连续打卡 {streak} 天
          </div>
        </div>
        <div className="km-side-meta">
          <span>
            章节 <b>{totalChapters}</b> · 已掌握 <b>{doneChapters}</b> · 平均 <b>{avgMastery}%</b>
          </span>
          <span>
            项目 <b>{BUNDLE.projects.total}</b> · 已通关 <b>{doneProjects}</b>
          </span>
          <span>
            累计工时 <b>{BUNDLE.projects.hours}</b> h
          </span>
        </div>
      </div>
    </>
  );
}
