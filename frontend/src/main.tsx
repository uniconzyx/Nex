/**
 * Nex 前端入口
 * ---------------------------------------------------------------------------
 * 桌面端（Windows/macOS/Linux）：Tauri WebView 加载 dist/index.html，
 *   判题走 invoke('judge-batch')。
 * 移动端（Android APK）：同一个 WebView，但本机没有 go-judge 沙箱，
 *   判题走 fetch -> http://<电脑局域网IP>:8080/api/judge。
 *   两种通道的切换由 GoJudgeClient 自动进行，UI 层无感。
 *
 * 主界面 = AppShell（PRD §6 七模块导航 + §14 蓝白猫咪版设计系统），
 * AI 助手三处入口：侧导航 /ai、右下 CppCat 悬浮球、判题台内嵌「问 CppCat」。
 */
import React from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import { ParticleProvider } from './components/Particles';
import { applyLgMode } from './lib/liquidGlass';
import { applyMotionPref } from './lib/motion';
import './styles.css';
// KaTeX 字体与版面：必须在业务样式之前，让 .km-tex 的尺寸微调能覆盖它
import 'katex/dist/katex.min.css';
// 凯喵外壳样式放在业务样式之后：令牌覆盖 + 三栏布局优先级更高
import './kaimao.css';
// 玩法层（动画 / 图鉴 / 每日试炼）在最后：它依赖 kaimao.css 定义的 --km-* 令牌
import './game.css';
// S0 统一交互骨架（底部弹窗 / 按压 / 长按预览 / 粒子 / 安全区）：必须最后加载，
// 才能覆盖并延展既有令牌，不破坏现有外观
import './styles/interaction.css';
// 液体玻璃系统（A/B 运行时切换 + 省电强制 A）：在交互骨架之后加载，
// 以便覆盖并延展既有令牌，不破坏现有外观
import './styles/liquidglass.css';
// 动效偏好（跟随系统 / 始终减少 / 完整动效）：放最后，才能压住前面各处的
// @media (prefers-reduced-motion) 规则（用户手动选「完整动效」时要能反悔）
import './styles/motion.css';

// 启动即按平台 / 省电开关确定玻璃方案与强度（APK→A 冰蓝磨砂，EXE→B 通透折射），
// 同时把动效偏好写到 <html>，避免首帧先播一遍动画再被关掉
applyLgMode();
applyMotionPref();

const container = document.getElementById('root');
if (!container) {
  throw new Error('找不到 #root 挂载点：请检查 frontend/index.html 是否被改动');
}

createRoot(container).render(
  <React.StrictMode>
    <ParticleProvider>
      <App />
    </ParticleProvider>
  </React.StrictMode>,
);
