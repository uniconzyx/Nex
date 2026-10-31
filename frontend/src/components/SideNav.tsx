/**
 * SideNav.tsx —— 左侧 7 模块导航（PRD §6 信息架构）
 * 宽屏：垂直侧栏；窄屏（≤860px）：CSS 折叠为顶部横向滚动条。
 */

export type PageKey =
  | 'home'
  | 'learn'
  | 'practice'
  | 'projects'
  | 'guides'
  | 'resources'
  | 'ai'
  | 'me';

interface NavEntry {
  key: PageKey;
  label: string;
  icon: string;
  badge?: string;
}

const ENTRIES: NavEntry[] = [
  { key: 'home', label: '首页', icon: '⌂' },
  { key: 'learn', label: '学习', icon: '✎' },
  { key: 'practice', label: '练习', icon: '▶' },
  { key: 'projects', label: '项目', icon: '▤' },
  { key: 'guides', label: '笔记', icon: '❏', badge: '11408' },
  { key: 'resources', label: '资源', icon: '⛁' },
  { key: 'ai', label: 'AI 助手', icon: '✦', badge: 'New' },
  { key: 'me', label: '我的', icon: '◉' },
];

export function SideNav({
  active,
  onNavigate,
}: {
  active: PageKey;
  onNavigate: (key: PageKey) => void;
}) {
  return (
    <nav className="side-nav" aria-label="主导航">
      <div className="nav-brand">
        <img src="/assets/cppcat-avatar.png" alt="CppCat" />
        <div>
          <div className="nav-brand-name">Nex</div>
          <div className="nav-brand-sub">CppCat 陪你学习</div>
        </div>
      </div>

      {ENTRIES.map((e) => (
        <button
          key={e.key}
          type="button"
          className={`nav-item${e.key === active ? ' active' : ''}`}
          aria-current={e.key === active ? 'page' : undefined}
          onClick={() => onNavigate(e.key)}
        >
          <span className="nav-item-icon" aria-hidden="true">
            {e.icon}
          </span>
          <span>{e.label}</span>
          {e.badge && <span className="nav-item-badge">{e.badge}</span>}
        </button>
      ))}
    </nav>
  );
}

export default SideNav;
