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
import type { KmPage } from './lib/nav';

export interface AiInvocation {
  open: boolean;
  context?: string;
  mode?: AiMode;
}

export function App() {
  const [page, setPage] = useState<KmPage>('home');
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
    // 切页时关掉 AI 面板，避免遮挡新页面
    setAi((prev) => ({ ...prev, open: false }));
  }, []);

  return (
    <>
      <KaimaoShell active={page} onNavigate={navigate} onOpenAi={() => openAi()}>
        {page === 'home' && <HomePage onNavigate={navigate} />}
        {page === 'learn' && <LearnPage onNavigate={navigate} />}
        {page === 'projects' && <ProjectsPage />}
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
        {page === 'settings' && <SettingsPage onNavigate={navigate} />}
        {page === 'help' && <HelpPage onNavigate={navigate} />}
      </KaimaoShell>

      <CppCatFab onClick={() => openAi()} active={ai.open} />
      {ai.open && <AiPanel initialContext={ai.context} initialMode={ai.mode} onClose={closeAi} />}
    </>
  );
}

export default App;
