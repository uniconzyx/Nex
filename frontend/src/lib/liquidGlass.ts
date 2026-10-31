/**
 * liquidGlass.ts —— 液体玻璃方案 + 强度档位运行时切换
 *
 * 两个维度，互相独立：
 *
 * ① 方案（LgMode）
 *   · A「冰蓝磨砂」—— 实底 + 中等模糊，重性能 / 低耗电（APK 默认）
 *   · B「通透折射」—— 重 blur + 色散边缘高光 + 流光动画（EXE 默认）
 *
 * ② 强度（LgIntensity）
 *   · light「轻磨砂」—— 模糊打 55%、白底更实，最省 GPU
 *   · mid  「标准」  —— 方案出厂值
 *   · heavy「重折射」—— 模糊 155%、白底更透，最通透也最吃性能
 *
 * 强度不是给每档重写一份 CSS，而是由两个调制量驱动（见 styles/liquidglass.css）：
 *   --lg-k   模糊半径乘数
 *   --lg-da  白底不透明度偏移
 * 所以 future 加档位 / 微调手感都只改数值，不用碰规则。
 *
 * 「高性能 / 省电模式」开启时强制回到 A + light —— 省电的意义不只是换方案，
 * 模糊半径才是 GPU 开销的大头。
 *
 * 实际生效由 <html> 上的 lg-a / lg-b 类与 data-lg-intensity 属性驱动。
 */
import { useEffect, useState } from 'react';

const K_POWER = 'nex.lgPowerSave';
const K_MODE = 'nex.lgMode';
const K_INTENSITY = 'nex.lgIntensity';

export type LgMode = 'a' | 'b';
export type LgIntensity = 'light' | 'mid' | 'heavy';

export const LG_INTENSITY_LABEL: Record<LgIntensity, string> = {
  light: '轻磨砂',
  mid: '标准',
  heavy: '重折射',
};

/** 平台默认：APK（Android WebView）→ A；EXE（桌面 Tauri）→ B */
function platformDefault(): LgMode {
  if (typeof navigator !== 'undefined' && /Android/i.test(navigator.userAgent)) return 'a';
  return 'b';
}

function isPowerSave(): boolean {
  try {
    if (typeof localStorage === 'undefined') return false;
    const ps = localStorage.getItem(K_POWER);
    return ps === 'true' || ps === '1';
  } catch {
    return false;
  }
}

export function getLgMode(): LgMode {
  try {
    if (typeof localStorage !== 'undefined') {
      // 省电模式优先：强制冰蓝磨砂 A
      if (isPowerSave()) return 'a';
      // 其次尊重用户在「设置」里显式选的方案
      const m = localStorage.getItem(K_MODE);
      if (m === 'a' || m === 'b') return m;
    }
  } catch {
    /* localStorage 不可用时退回到平台默认 */
  }
  return platformDefault();
}

export function getLgIntensity(): LgIntensity {
  try {
    if (typeof localStorage !== 'undefined') {
      // 省电模式连强度也压到最轻，否则「省电」只换了配色没省 GPU
      if (isPowerSave()) return 'light';
      const v = localStorage.getItem(K_INTENSITY);
      if (v === 'light' || v === 'mid' || v === 'heavy') return v;
    }
  } catch {
    /* 忽略读取失败 */
  }
  return 'mid';
}

/** 用户在设置里显式选定玻璃方案（A 冰蓝磨砂 / B 通透折射） */
export function setLgMode(mode: LgMode): void {
  try {
    if (typeof localStorage !== 'undefined') localStorage.setItem(K_MODE, mode);
  } catch {
    /* 忽略写入失败 */
  }
  applyLgMode();
}

/** 用户在设置里显式选定强度档位 */
export function setLgIntensity(intensity: LgIntensity): void {
  try {
    if (typeof localStorage !== 'undefined') localStorage.setItem(K_INTENSITY, intensity);
  } catch {
    /* 忽略写入失败 */
  }
  applyLgMode();
}

/** 把当前状态写到 <html>（lg-a / lg-b + data-lg-intensity），返回实际生效的方案 */
export function applyLgMode(): LgMode {
  const mode = getLgMode();
  const intensity = getLgIntensity();
  if (typeof document !== 'undefined') {
    const el = document.documentElement;
    el.classList.remove('lg-a', 'lg-b');
    el.classList.add(mode === 'a' ? 'lg-a' : 'lg-b');
    el.setAttribute('data-lg-intensity', intensity);
  }
  return mode;
}

/** 设置「高性能 / 省电模式」：开启 → 强制 A + light；关闭 → 回到用户选择 */
export function setPowerSave(on: boolean): void {
  try {
    if (typeof localStorage !== 'undefined') localStorage.setItem(K_POWER, on ? 'true' : 'false');
  } catch {
    /* 忽略写入失败 */
  }
  applyLgMode();
}

export function useLiquidGlass(): LgMode {
  const [mode, setMode] = useState<LgMode>(() => getLgMode());
  useEffect(() => {
    setMode(applyLgMode());
  }, []);
  return mode;
}
