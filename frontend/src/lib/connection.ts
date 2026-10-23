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
 *   <StatusBadge />                 // 顶栏小圆点
 *   {conn.status !== 'online' && <Banner />}  // 全局提示条
 */
import { useCallback, useEffect, useState } from 'react';

import { apiHealth, type ApiHealth } from './api';

export type ConnectionStatus = 'unknown' | 'online' | 'offline';

export interface ConnectionState {
  status: ConnectionStatus;
  health: ApiHealth | null;
  /** 正在探测 */
  checking: boolean;
}

/** 全局共享状态（不含 refresh —— 那是 hook 层的便捷方法）。 */
let state: ConnectionState = {
  status: 'unknown',
  health: null,
  checking: false,
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
  });
  return state;
}

/** 启动时探测一次。 */
export function installConnectionWatch(intervalMs = 60_000): () => void {
  void checkConnection();
  const timer = window.setInterval(() => {
    void checkConnection();
  }, intervalMs);
  return () => window.clearInterval(timer);
}

export function getConnection(): ConnectionState {
  return state;
}

export function useConnection(): ConnectionState & { refresh: () => Promise<void> } {
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

  return { ...value, refresh };
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
