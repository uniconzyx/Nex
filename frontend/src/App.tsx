/**
 * App.tsx —— 凯喵Code试炼录 主界面
 *
 * 结构：KaimaoShell（顶栏 / 三栏 / 右栏凯喵）+ 各业务页。
 * 桌面端（.exe）与 Android（.apk）共用这一份入口，不做平台分叉；
 * 数据全部来自打包的 BUNDLE + 本地进度，离线可用，两端表现一致。
 *
 * AI 助手保留三处入口：右下悬浮球、判题台失败时的「问凯喵」、以及独立面板。
 */
import { useCallback, useEffect, useState } from 'react';

import { KaimaoShell } from './components/KaimaoShell';
import { CppCatFab } from './components/CppCatFab';
import { ToastHost } from './components/ToastHost';
import { AiPanel, type AiMode } from './components/AiPanel';
import { HomePage } from './pages/HomePage';
import { LearnPage } from './pages/LearnPage';
import { PracticePage } from './pages/PracticePage';
import { ProjectsPage } from './pages/ProjectsPage';
import { GuidesPage } from './pages/GuidesPage';
import { DressPage } from './pages/DressPage';
import { ProfilePage } from './pages/ProfilePage';
import { SettingsPage } from './pages/SettingsPage';
import { HelpPage } from './pages/HelpPage';
import { AiPage } from './pages/AiPage';
import { DiagramsPage } from './pages/DiagramsPage';
import { Track408Page } from './pages/Track408Page';
import { EmploymentPage } from './pages/EmploymentPage';
import { ReexamPage } from './pages/ReexamPage';
import { AgentPage } from './pages/AgentPage';
import {
  AchievementsPage,
  BagPage,
  BestiaryPage,
  CheckinPage,
  MiniPage,
  RankPage,
  StoryPage,
} from './pages/MiscPages';
import { applyStoredTheme } from './lib/progress';
import { installProgressSync, pullProgress } from './lib/sync';
import { setSignedInHook } from './lib/session';
import { connectContentService } from './lib/clientBridge';
import { installConnectionWatch } from './lib/connection';
import { setAppNavigator } from './lib/challenge';
import type { KmPage } from './lib/nav';

export interface AiInvocation {
  open: boolean;
  context?: string;
  mode?: AiMode;
}

export function App() {
  const [page, setPage] = useState<KmPage>(() => {
    const raw = (location.hash || '').replace(/^#/, '');
    // 考研 408 专轨支持深链：#track408 与 #track408/<chapterId>
    const isTrack = raw === 'track408' || raw.startsWith('track/') || raw.startsWith('track408/');
    const h = raw as KmPage;
    const VALID: KmPage[] = [
      'home', 'learn', 'projects', 'bestiary', 'story', 'bag', 'rank', 'mini',
      'checkin', 'dress', 'lab', 'me', 'achievements', 'guides', 'ai',
      'settings', 'help', 'diagrams', 'track408', 'employment', 'reexam', 'agent',
    ];
    return isTrack ? 'track408' : (VALID.includes(h) ? h : 'home');
  });
  const [ai, setAi] = useState<AiInvocation>({ open: false });

  // 首屏恢复主题，避免刷新时白闪
  useEffect(() => {
    applyStoredTheme();
    // 装上"进度变更 → 账号镜像"的钩子；未登录时它是空转的
    installProgressSync();
    // 反方向：登录成功后由 session 通知这里拉一次云端进度。
    // 通过钩子而不是在 session.ts 里 import sync.ts，是为了打断循环依赖
    // （sync.ts 需要 getSession 拿身份），同时不破坏 Vite 的拆包。
    setSignedInHook(() => {
      void pullProgress();
    });
  }, []);

  // 打通后端：客户端先探明后端在哪（Rust 侧探测），再启动全局健康轮询。
  // 顺序很重要——先探测再轮询，否则第一轮会用兜底地址打一次。
  useEffect(() => {
    let dispose: (() => void) | undefined;
    let cancelled = false;
    void (async () => {
      await connectContentService();
      if (cancelled) return;
      dispose = installConnectionWatch();
    })();
    return () => {
      cancelled = true;
      dispose?.();
    };
  }, []);

  const openAi = useCallback((context?: string, mode?: AiMode) => {
    setAi({ open: true, context, mode });
  }, []);

  const closeAi = useCallback(() => {
    setAi((prev) => ({ ...prev, open: false }));
  }, []);

  const navigate = useCallback((p: KmPage) => {
    setPage(p);
    // 把当前页写进 URL hash，支持直接深链（如 #diagrams 直达图表总览）
    // 用 replaceState 而非直接赋值，避免每次切页都塞一条历史记录
    if (location.hash !== `#${p}`) {
      history.replaceState(null, '', `#${p}`);
    }
    // 切页时关掉 AI 面板，避免遮挡新页面
    setAi((prev) => ({ ...prev, open: false }));
  }, []);

  /**
   * 把导航函数注入 challenge.ts。
   * 图鉴卡片、遭遇弹窗、每日试炼都要「带着题目跳到试炼实验室」，
   * 但它们不该各自拿一份 navigate props；lib 层拿不到 React 上下文，
   * 所以由 App 这里单向注册。
   */
  useEffect(() => {
    setAppNavigator(navigate);
    return () => setAppNavigator(null);
  }, [navigate]);

  return (
    <>
      <KaimaoShell active={page} onNavigate={navigate} onOpenAi={() => openAi()}>
        {/*
          key={page} 让每次切页都重新挂载，配合 .km-page 的入场动画：
          没有 key 时 React 会复用节点，动画只在首次出现，切换就变成"硬切"。
        */}
        <div className="km-page" key={page}>
          {page === 'home' && <HomePage onNavigate={navigate} />}
          {page === 'learn' && <LearnPage onNavigate={navigate} />}
          {page === 'projects' && <ProjectsPage onNavigate={navigate} />}
          {page === 'bestiary' && <BestiaryPage onNavigate={navigate} />}
          {page === 'story' && <StoryPage />}
          {page === 'bag' && <BagPage />}
          {page === 'rank' && <RankPage />}
          {page === 'mini' && <MiniPage />}
          {page === 'checkin' && <CheckinPage />}
          {page === 'dress' && <DressPage />}
          {page === 'lab' && <PracticePage onAskCat={openAi} />}
          {page === 'me' && <ProfilePage onNavigate={navigate} />}
          {page === 'achievements' && <AchievementsPage />}
          {page === 'guides' && <GuidesPage />}
          {page === 'ai' && <AiPage onNavigate={navigate} />}
          {page === 'settings' && <SettingsPage onNavigate={navigate} />}
          {page === 'help' && <HelpPage onNavigate={navigate} />}
          {page === 'diagrams' && <DiagramsPage />}
          {page === 'track408' && <Track408Page onNavigate={navigate} />}
          {page === 'employment' && <EmploymentPage />}
          {page === 'reexam' && <ReexamPage />}
          {page === 'agent' && <AgentPage />}
        </div>
      </KaimaoShell>

      {/* 全局反馈层：toast + 怪物遭遇，任何页面的动作都从这里出声 */}
      <ToastHost />

      <CppCatFab onClick={() => openAi()} active={ai.open} />
      {ai.open && (
        <AiPanel
          initialContext={ai.context}
          initialMode={ai.mode}
          onClose={closeAi}
          onRequireLogin={() => navigate('me')}
        />
      )}
    </>
  );
}

export default App;
