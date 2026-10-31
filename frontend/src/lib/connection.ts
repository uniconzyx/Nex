/**
 * connection.ts —— 全局「后端连接状态」
 *
 * 打通后端之后，用户最常遇到的困惑是「页面空白 / 一直转圈」。
 * 根因往往是后端没起、地址不对、或只有部分功能可用（数据库没起）。
 *
 * 本模块给全站提供一份统一的状态：
 *   status: 'unknown' | 'online' | 'offline'
 *   health: 后端自报的能力快照（哪些功能可用）
 *
 * 用法：
 *   const conn = useConnection();
 *   <ConnectionBadge />                 // 顶栏小圆点
 *   <OfflineBanner />                   // 全局离线提示 + 重试入口
 *
 * ── 心跳为什么是分级的（Phase18）────────────────────────────────
 *   固定 60s 轮询在「后端正在启动」这个最常见场景下体感很差：
 *   用户起了服务，界面要最多等一分钟才恢复，期间所有请求都在报错。
 *   所以改成退避阶梯：
 *     在线      → 60s（稳定期不必频繁打扰后端）
 *     刚离线    → 3s（后端可能正在启动，要尽快接上）
 *     持续离线  → 3 → 6 → 12 → 24 → 30s（封顶，避免无谓请求）
 *     重新在线  → 立刻回到 60s
 *   另外，任何一次业务请求失败（api.ts 的网络错误）会**立刻**把状态
 *   标成离线并触发一次探测，不等心跳——这是用户点完按钮立刻看到红点的原因。
 */
import { useCallback, useEffect, useState } from 'react';

import { apiHealth, setNetworkErrorHandler, type ApiHealth } from './api';

export type ConnectionStatus = 'unknown' | 'online' | 'offline';

export interface ConnectionState {
  status: ConnectionStatus;
  health: ApiHealth | null;
  /** 正在探测 */
  checking: boolean;
  /** 连续失败次数（用于退避阶梯与文案） */
  failures: number;
  /** 最近一次探测的基址（连不上时告诉用户「在找哪台机器」） */
  base: string | null;
}

/** 在线时的轮询间隔。 */
const ONLINE_INTERVAL = 60_000;
/** 离线时的退避阶梯（毫秒）。最后一档是封顶。 */
const OFFLINE_BACKOFF = [3_000, 6_000, 12_000, 24_000, 30_000];

/** 全局共享状态（不含 refresh —— 那是 hook 层的便捷方法）。 */
let state: ConnectionState = {
  status: 'unknown',
  health: null,
  checking: false,
  failures: 0,
  base: null,
};

function emit(patch: Partial<ConnectionState>): void {
  state = { ...state, ...patch };
  for (const fn of listeners) fn(state);
}

const listeners = new Set<(s: ConnectionState) => void>();

/** 探测一次后端。永不抛异常——不通就把状态标成 offline。 */
export async function checkConnection(): Promise<ConnectionState> {
  emit({ checking: true });
  const h = await apiHealth();
  emit({
    status: h.ok ? 'online' : 'offline',
    health: h,
    checking: false,
    failures: h.ok ? 0 : state.failures + 1,
    base: h.base,
  });
  return state;
}

/**
 * 启动心跳。
 *
 * 用递归 setTimeout 而非 setInterval：每次探测完再按**新的**状态决定下一次
 * 间隔，这样「离线加速 / 在线减速」才能自然切换，也不会有重叠请求。
 */
export function installConnectionWatch(onlineIntervalMs = ONLINE_INTERVAL): () => void {
  let timer: number | undefined;
  let stopped = false;

  const schedule = () => {
    if (stopped) return;
    const delay =
      state.status === 'offline'
        ? OFFLINE_BACKOFF[Math.min(state.failures - 1, OFFLINE_BACKOFF.length - 1)]
        : onlineIntervalMs;
    timer = window.setTimeout(async () => {
      await checkConnection();
      schedule();
    }, delay);
  };

  void checkConnection().then(schedule);

  return () => {
    stopped = true;
    if (timer !== undefined) window.clearTimeout(timer);
  };
}

/**
 * 立刻重试一次（不管当前处于什么退避档）。
 *
 * 用户在后端重启期间最需要的动作：不用等退避计时器走完，点一下就试。
 * 无论这次成功还是失败，都会重新计算下一次心跳的间隔。
 */
export async function retryNow(): Promise<ConnectionState> {
  const s = await checkConnection();
  // 成功 → failures 归零，下一次心跳自动回到 60s。
  // 失败 → failures 继续累加，退避阶梯继续往上走。
  return s;
}

/**
 * 注册 api.ts 的网络错误通知。
 *
 * 业务请求失败说明后端**此刻**不可达，比心跳更及时：
 * 立刻标离线，并让下一次心跳走最短档（3s）。
 */
function installNetworkErrorHook(): void {
  setNetworkErrorHandler(() => {
    if (state.status === 'offline') return; // 已经是离线，不必重复广播
    emit({ status: 'offline', failures: Math.max(1, state.failures) });
  });
}

installNetworkErrorHook();

export function getConnection(): ConnectionState {
  return state;
}

export function useConnection(): ConnectionState & {
  refresh: () => Promise<void>;
  retry: () => Promise<void>;
} {
  const [value, setValue] = useState(state);

  useEffect(() => {
    const fn = (s: ConnectionState) => setValue(s);
    listeners.add(fn);
    setValue(state);
    return () => {
      listeners.delete(fn);
    };
  }, []);

  const refresh = useCallback(async () => {
    await checkConnection();
  }, []);

  const retry = useCallback(async () => {
    await retryNow();
  }, []);

  return { ...value, refresh, retry };
}

/**
 * 人类可读的能力说明。
 * 例：「题库可用 · 账号/进度不可用（数据库未连接）」
 */
export function describeCapabilities(health: ApiHealth | null): string {
  if (!health || !health.ok) return '后端未连接';
  const f = health.features;
  if (!f) return '后端已连接';
  const fileBased = ['exam', 'guides', 'projects', 'career'].some((k) => f[k] === true);
  const dbBased = ['content', 'exercises', 'progress'].some((k) => f[k] === true);
  if (fileBased && dbBased) return '全部功能可用';
  if (fileBased) return '题库可用 · 账号与进度需数据库';
  if (dbBased) return '账号与进度可用 · 题库未就绪';
  return '后端已连接';
}
