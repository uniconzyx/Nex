/**
 * clientBridge.ts —— 客户端（Tauri）与前端的桥接
 *
 * 桌面端 .exe / Android .apk 都是 Tauri 应用，WebView 里能 invoke Rust 命令。
 * 浏览器里没有这套能力，所以本模块**所有调用都必须能被安全降级**：
 * 探测不到客户端时，api.ts 走 localStorage / 默认回环地址，功能照常。
 *
 * 当前接的线：
 *   Rust `api_probe` → 返回后端候选地址与可达性
 *        ↓
 *   api.ts 的 registerBaseResolver → 前端所有 HTTP 请求自动打到正确地址
 *
 * 另外顺带把「判题通道」的选择也收敛到这里，UI 层不再自己判断平台。
 */
import { registerBaseResolver } from './api';

/** Rust 侧 api_probe 的返回形状（与 api_client.rs 的 ApiTarget 对齐）。 */
export interface ApiTarget {
  baseUrl: string;
  reachable: boolean;
  candidates: string[];
  backendVersion: string | null;
  elapsedMs: number;
}

/** 是否运行在 Tauri 客户端里。 */
export function isClient(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

let probed: ApiTarget | null = null;

/**
 * 探测后端地址并注册到 api.ts。
 *
 * 调用时机：App 启动时调用一次即可。
 * 失败不抛——探测不通只说明后端没起，前端该显示「离线」而不是崩掉。
 */
export async function connectContentService(): Promise<ApiTarget | null> {
  if (!isClient()) return null;
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    const target = (await invoke('api_probe')) as ApiTarget;

    // 只有探测通了才注册。探测不通时保持前端自身的兜底地址，
    // 免得把一个错的地址钉死、把 localStorage 里用户手填的正确地址也盖掉。
    if (target?.reachable && target.baseUrl) {
      registerBaseResolver(() => target.baseUrl);
    }
    probed = target;
    return target;
  } catch {
    return null;
  }
}

/** 最近一次探测结果（没有探测过返回 null）。 */
export function lastProbe(): ApiTarget | null {
  return probed;
}

/**
 * 重新探测。用户在设置里改了地址后调用，用于立刻验证新地址通不通。
 */
export async function reprobe(): Promise<ApiTarget | null> {
  return connectContentService();
}
