/**
 * KaimaoShell.tsx —— 「凯喵Code试炼录」React 外壳
 *
 * 结构对齐 web-preview/kaimao-desktop.html 的三栏：
 *   顶栏 64px（品牌 / 等级经验 / 经验结晶 / 搜索·主题·设置）
 *   左栏 220px（冒险 / 行囊 / 冒险者 三组导航）
 *   中间自适应（业务页）
 *   右栏 300px（凯喵伙伴 / 今日目标〔含内容体量〕）
 *
 * 响应式：<1180px 收掉右栏；<900px 侧栏变顶部横滑条。
 * 桌面端与 Android 端共用这一份代码，不做平台分叉。
 */
import { useEffect, useMemo, useRef, useState } from 'react';

import { BUNDLE } from '../data/bundle';
import { NAV_FLAT, NAV_GROUPS, type KmPage } from '../lib/nav';
import { setTheme, streakOf, todayKey, useProgress } from '../lib/progress';
import { ConnectionBadge } from './ConnectionBadge';

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

export function KaimaoShell({ active, onNavigate, onOpenAi, children }: ShellProps) {
  const p = useProgress();
  const [searchOpen, setSearchOpen] = useState(false);
  const [kw, setKw] = useState('');
  /** ≤1180 右栏隐藏后，凯喵/目标/快捷改从这里进来 */
  const [railOpen, setRailOpen] = useState(false);
  /** ≤900 导航横条只有一小截可见，用「全部」打开分组面板 */
  const [navOpen, setNavOpen] = useState(false);
  /** 移动端横滑条：切页时把当前项滑进视野，否则选中项可能藏在滚动区外 */
  const navRef = useRef<HTMLElement | null>(null);

  

  const totalChapters = useMemo(
    () => Object.values(BUNDLE.chapters).reduce((n, s) => n + s.chapters.length, 0),
    [],
  );
  const doneChapters = p.doneChapters.length;
  const doneProjects = p.doneProjects.length;
  const exp = doneChapters * 20 + doneProjects * 30 + p.checkins.length * 50;
  const level = 1 + Math.floor(exp / 300);
  const levelName = ['初入试炼', '语法学徒', '指针学徒', '容器行者', '并发术士', '源码猎人', '架构导师'][
    Math.min(level - 1, 6)
  ];
  const levelPct = Math.round(((exp % 300) / 300) * 100);
  const streak = streakOf(p.checkins);

  const catMood = p.checkins.includes(todayISO())
    ? '开心'
    : doneChapters > 0
      ? '陪伴中'
      : '待唤醒';
  const catSrc = OUTFIT_IMG[p.outfit] ?? OUTFIT_IMG.default;

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
            title={p.theme === 'light' ? '切换到深色' : '切换到浅色'}
            onClick={() => setTheme(p.theme === 'light' ? 'dark' : 'light')}
            aria-label="切换主题"
          >
            {p.theme === 'light' ? (
              <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="4.5" />
                <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" />
              </svg>
            )}
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

      <div className="km-main">
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
                  {n.badge && <span className="km-nav-badge">{n.badge}</span>}
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

        <main className="km-content">{children}</main>

        <aside className="km-right">
          <RightRail
            catSrc={catSrc}
            catMood={catMood}
            outfitName={OUTFIT_NAME[p.outfit] ?? '日常便装'}
            doneChapters={doneChapters}
            doneProjects={doneProjects}
            streak={streak}
            totalChapters={totalChapters}
            checkins={p.checkins}
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
              catMood={catMood}
              outfitName={OUTFIT_NAME[p.outfit] ?? '日常便装'}
              doneChapters={doneChapters}
              doneProjects={doneProjects}
              streak={streak}
              totalChapters={totalChapters}
              checkins={p.checkins}
              onOpenAi={onOpenAi}
            />
          </aside>
        </>
      )}

      {/* ≤900：横条放不下 15 项，用「全部」按原分组展开 */}
      {navOpen && (
        <>
          <div className="km-nav-scrim" onClick={() => setNavOpen(false)} />
          <div className="km-nav-sheet" role="dialog" aria-modal="true" aria-label="全部导航">
            <div className="km-rail-head">
              <b>全部导航</b>
              <button type="button" onClick={() => setNavOpen(false)} aria-label="关闭">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>
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
          </div>
        </>
      )}
    </div>
  );
}

function todayISO(): string {
  return todayKey();
}

interface RightRailProps {
  catSrc: string;
  catMood: string;
  outfitName: string;
  doneChapters: number;
  doneProjects: number;
  streak: number;
  totalChapters: number;
  checkins: string[];
  onOpenAi?: () => void;
}

/**
 * 右栏内容。桌面直接放进 aside；≤1180 时同一份内容放进抽屉，
 * 避免「隐藏右栏 = 删掉功能」。
 */
function RightRail({
  catSrc,
  catMood,
  outfitName,
  doneChapters,
  doneProjects,
  streak,
  totalChapters,
  checkins,
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
        <div className="km-cat-stage">
          <div className="km-cat-aura" />
          <img src={catSrc} alt={`凯喵 · ${outfitName}`} />
        </div>
        <div className="km-cat-name">凯喵</div>
        <div className="km-cat-mood">{catMood}</div>
        <div className="km-aff-row">
          <span>好感度</span>
          <b>{affection}%</b>
        </div>
        <div className="km-aff-bar">
          <i style={{ width: `${affection}%` }} />
        </div>
        <div className="km-cat-say">
          {doneChapters === 0 && doneProjects === 0
            ? '第一次见面！先从「知识试炼区」挑一章开个头，我会在旁边陪着你。'
            : `你已经掌握 ${doneChapters} 章、通关 ${doneProjects} 个项目了。继续保持，别让连击断了～`}
        </div>
      </div>

      <div className="km-side-card">
        <h4>
          <Icon size={16} paths={['M8 21h8M12 17v4', 'M7 4h10v5a5 5 0 0 1-10 0z']} />
          今日目标
        </h4>
        <div className="km-goal">
          <div className="km-goal-row">
            <span className={`km-tick${checkins.includes(todayISO()) ? ' on' : ''}`}>✓</span>
            签到祭坛打卡
          </div>
          <div className="km-goal-row">
            <span className={`km-tick${doneChapters > 0 ? ' on' : ''}`}>✓</span>
            掌握 1 个章节
          </div>
          <div className="km-goal-row">
            <span className={`km-tick${doneProjects > 0 ? ' on' : ''}`}>✓</span>
            通关 1 个项目
          </div>
          <div className="km-goal-row">
            <span className="km-tick" />
            连续打卡 {streak} 天
          </div>
        </div>
        <div className="km-side-meta">
          <span>
            章节 <b>{totalChapters}</b> · 已掌握 <b>{doneChapters}</b>
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
