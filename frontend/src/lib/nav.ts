/**
 * nav.ts —— 凯喵外壳的导航定义
 *
 * 14 个视图沿用设计稿（web-preview/kaimao-desktop.html）的分组与命名，
 * 另外补了「考研手札」：它是 11408 笔记导航，属于真实内容，不能因为换壳丢掉。
 * 考研三板块（408 / 复试 / 公共课手札）归并到独立的「— 考研 —」分组，
 * 三块天然对应、进度互通，不需要新增内容数据。
 */
export type KmPage =
  | 'home'
  | 'learn'
  | 'projects'
  | 'bestiary'
  | 'story'
  | 'bag'
  | 'rank'
  | 'mini'
  | 'checkin'
  | 'dress'
  | 'lab'
  | 'me'
  | 'achievements'
  | 'guides'
  | 'ai'
  | 'settings'
  | 'help'
  | 'diagrams'
  | 'track408'
  | 'employment'
  | 'reexam'
  | 'agent'
  | 'exam'
  | 'kaoyan';

export interface NavItem {
  key: KmPage;
  label: string;
  /** SVG path 集合，统一 24×24 线性图标 */
  paths: string[];
  badge?: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    title: '— 冒险 —',
    items: [
      {
        key: 'home',
        label: '主城首页',
        paths: ['M3 10.5 12 3l9 7.5', 'M5 9.5V21h14V9.5', 'M9.5 21v-6h5v6'],
      },
      {
        key: 'learn',
        label: '知识试炼区',
        paths: [
          'M4 4.5A2.5 2.5 0 0 1 6.5 2H20v15H6.5A2.5 2.5 0 0 0 4 19.5z',
          'M4 19.5A2.5 2.5 0 0 1 6.5 17H20',
          'M9 7h7',
        ],
      },
      {
        key: 'projects',
        label: 'BOSS项目实战',
        paths: [
          'M5 8c0-3 2-5 3-3s1 3 4 3 3-3 4-3 3 0 3 3v4a7 7 0 0 1-14 0z',
          'M9.5 16.5c1.5 1 3.5 1 5 0',
        ],
      },
      {
        key: 'bestiary',
        label: '怪物图鉴',
        paths: ['M3 4h7v7H3z', 'M14 4h7v7h-7z', 'M3 14h7v7H3z', 'M14 14h7v7h-7z'],
        badge: 'NEW',
      },
      {
        key: 'story',
        label: '剧情日志',
        paths: ['M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2z', 'M4 19a2 2 0 0 1 2-2h12'],
        badge: 'NEW',
      },
    ],
  },
  {
    title: '— 行囊 —',
    items: [
      {
        key: 'bag',
        label: '资源背包',
        paths: ['M6 8h12l1.5 12a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 20z', 'M9 8V6a3 3 0 0 1 6 0v2'],
      },
      {
        key: 'rank',
        label: '排行榜',
        paths: ['M8 21h8M12 17v4', 'M7 4h10v5a5 5 0 0 1-10 0z', 'M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3'],
      },
      {
        key: 'mini',
        label: '支线小屋',
        paths: ['M3 7h18v13H3z', 'M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2', 'M9 13h2M13 13h2M9 16.5h6'],
      },
      {
        key: 'checkin',
        label: '签到祭坛',
        paths: ['M3 5h18v16H3z', 'M8 3v4M16 3v4M3 10h18', 'm9 15 2 2 4-4'],
      },
      {
        key: 'dress',
        label: '装扮衣柜',
        paths: ['M8 3 4 6l2 3 2-1v11h8V8l2 1 2-3-4-3-3 2z'],
        badge: 'NEW',
      },
      {
        key: 'lab',
        label: '试炼实验室',
        paths: ['M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3'],
      },
      {
        key: 'diagrams',
        label: '图表总览',
        paths: ['M3 21h18', 'M5 21V8', 'M12 21V3', 'M19 21v-9'],
        badge: 'NEW',
      },
    ],
  },
  {
    title: '— 考研 —',
    items: [
      {
        key: 'kaoyan',
        label: '考研中枢',
        paths: ['M4 4h16v16H4z', 'M8 8h8M8 12h8M8 16h5'],
      },
      {
        key: 'track408',
        label: '考研 408',
        paths: ['M2 9l10-5 10 5-10 5z', 'M6 11v5c0 1 3 3 6 3s6-2 6-3v-5'],
        badge: '专业课',
      },
      {
        key: 'reexam',
        label: '考研复试',
        paths: ['M4 4h16v4H4z', 'M4 10h16v10H4z', 'M8 14h8'],
        badge: '面试',
      },
      {
        key: 'guides',
        label: '考研手札',
        paths: ['M4 4h16v16H4z', 'M8 8h8M8 12h8M8 16h5'],
        badge: '数英政',
      },
    ],
  },
  {
    /** 求职单独成组（主人 2026-10-30 定）：它和「考研」是同一条出路的两个岔口，
        埋在「冒险者」里等于跟档案/设置并列，权重明显不够。 */
    title: '— 求职 —',
    items: [
      {
        key: 'employment',
        label: '就业',
        paths: ['M3 7h18v12H3z', 'M8 7v12M12 7v12M16 7v12', 'M3 11h18'],
        badge: 'NEW',
      },
    ],
  },
  {
    /** 「凯喵陪练」与「问凯喵」合并成「AI 助手」一项：
        前者是跑循环（诊断/实验陪跑），后者是问一句答一句，都属于 AI 能力，
        分成两个导航项会让人以为是两套东西。合并后组内用 tab 区分。 */
    title: '— AI —',
    items: [
      {
        key: 'ai',
        label: 'AI 助手',
        paths: [
          'M12 3l2.2 5.6 6 .5-4.6 3.9 1.4 5.9L12 15.8 6.9 18.9l1.5-5.9L3.8 9.1l6-.5z',
          'M12 18.5V21',
        ],
        badge: 'AI',
      },
    ],
  },
  {
    title: '— 冒险者 —',
    items: [
      {
        key: 'me',
        label: '个人闯关档案',
        paths: ['M3 5h18v14H3z', 'M9 11a2.5 2.5 0 1 0 0-.01', 'M5.5 17a3.5 3.5 0 0 1 7 0', 'M14 9h5M14 13h5M14 17h3'],
      },
      {
        key: 'achievements',
        label: '成就殿堂',
        paths: ['M8 21h8M12 17v4', 'M7 4h10v5a5 5 0 0 1-10 0z', 'M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3'],
      },
      {
        key: 'settings',
        label: '冒险设置',
        paths: [
          'M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4z',
          'M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.7 15a1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.65 8.9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.08A1.7 1.7 0 0 0 10.12 3V3a2 2 0 1 1 4 0v.09c0 .68.4 1.3 1.03 1.56a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.08c.27.63.9 1.03 1.56 1.03H21a2 2 0 1 1 0 4h-.09c-.66 0-1.29.4-1.51 1.03z',
        ],
      },
    ],
  },
];

export const NAV_FLAT: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

export function pageLabel(key: KmPage): string {
  return NAV_FLAT.find((i) => i.key === key)?.label ?? key;
}
