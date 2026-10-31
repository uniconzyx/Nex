/**
 * motion.ts —— 动效偏好（跟随系统 / 强制减少 / 强制完整）
 *
 * 为什么需要它：项目里原本只有 CSS 的 `@media (prefers-reduced-motion: reduce)`，
 * 也就是**只能跟随操作系统**。可设置页里一直挂着一个「减少动效 · 跟随系统」的灰标签，
 * 用户点不动它——因为后端没有这一层。
 *
 * 现在三态由 <html data-km-motion> 驱动（见 styles/motion.css）：
 *   system  —— 不写属性，交给 CSS 媒体查询（默认值，行为与改造前一致）
 *   reduce  —— 写 data-km-motion="reduce"，强制关掉所有动画 / 过渡 / 平滑滚动
 *   full    —— 写 data-km-motion="full"，即使系统开了减少动效也照常播
 *
 * 为什么允许 full：系统级「减少动效」多为无障碍设置，但有人是为了省电或抗晕车才开，
 * 而 CppMind 的关卡动画本身是奖励反馈。给回控制权比替用户决定更合适，
 * 但默认仍尊重系统（system），不做未经允许的覆盖。
 */
const K_MOTION = 'nex.motionPref';

export type MotionPref = 'system' | 'reduce' | 'full';

export const MOTION_LABEL: Record<MotionPref, string> = {
  system: '跟随系统',
  reduce: '始终减少',
  full: '完整动效',
};

export function getMotionPref(): MotionPref {
  try {
    if (typeof localStorage !== 'undefined') {
      const v = localStorage.getItem(K_MOTION);
      if (v === 'reduce' || v === 'full') return v;
    }
  } catch {
    /* 忽略读取失败 */
  }
  return 'system';
}

export function setMotionPref(pref: MotionPref): void {
  try {
    if (typeof localStorage !== 'undefined') {
      if (pref === 'system') localStorage.removeItem(K_MOTION);
      else localStorage.setItem(K_MOTION, pref);
    }
  } catch {
    /* 忽略写入失败 */
  }
  applyMotionPref();
}

/** 把偏好写到 <html data-km-motion>；system 时移除属性，回落到 CSS 媒体查询 */
export function applyMotionPref(): void {
  if (typeof document === 'undefined') return;
  const el = document.documentElement;
  const pref = getMotionPref();
  if (pref === 'system') el.removeAttribute('data-km-motion');
  else el.setAttribute('data-km-motion', pref);
}

/**
 * 当前「是否应该减少动效」——给 JS 侧的动效代码用（如粒子喷射）。
 * 与 CSS 判定保持同一套规则：显式偏好优先，否则看系统媒体查询。
 */
export function shouldReduceMotion(): boolean {
  const pref = getMotionPref();
  if (pref === 'reduce') return true;
  if (pref === 'full') return false;
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
