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
import { registerBaseResolver, resolveApiBase } from './api';

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

    // 客户端是「后端在哪」的权威来源，两种结果都要注册：
    //
    //  * 探测通 → 注册它给的地址，前端请求打到客户端确认过的那台机器；
    //  * 探测不通 → **也必须注册**。以前的写法是「不通就什么都不做」，
    //    结果是前端继续用 localStorage / 默认兜底地址，而桌面端最常见的
    //    「连不上 http://127.0.0.1:8000」正是这么来的：
    //      1. 冷启动时 api_probe 等不到后端（Rust 侧最多等 6s，uvicorn 起得慢就超时），
    //         reachable=false → 不注册 → 前端锁死在兜底地址；
    //      2. 之后即使 Rust 侧确认后端 ready，前端也永远不会再问一次，
    //         只能靠 60s 心跳干等，且注册表里的错误地址不会自己修好。
    //    现在改成「不通也注册」+ 交给 connection.ts 的重连逻辑：
    //    后端一旦起来立刻 reprobe，把地址和离线状态一起纠正。
    const resolverBase = target?.baseUrl || null;
    if (resolverBase) {
      registerBaseResolver(() => resolverBase);
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

/**
 * 客户端侧的重连：探测 + 同步解析缓存。
 *
 * 与 reprobe 的区别是它会把结果应用到 api.ts 的解析缓存上：
 * api.ts 每次请求都会调 resolveApiBase()，客户端解析器生效时它会重算，
 * 所以这里还要调用一次 resolveApiBase() 让缓存立刻跟上新地址，
 * 否则「刚重连成功、下一个请求还打旧地址」还会再多错一次。
 */
let reconnecting: Promise<ApiTarget | null> | null = null;

export function reconnectContentService(): Promise<ApiTarget | null> {
  // 并发去重：心跳 + 用户点重试 + 网络错误上报可能在同一个瞬间一起触发
  if (reconnecting) return reconnecting;
  reconnecting = (async () => {
    try {
      const t = await reprobe();
      if (t?.reachable) await resolveApiBase();
      return t;
    } finally {
      reconnecting = null;
    }
  })();
  return reconnecting;
}
