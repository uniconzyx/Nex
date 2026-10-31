/**
 * feedback.ts —— 全局即时反馈（toast + 怪物遭遇 + 金币飘字）
 * ============================================================================
 * 为什么单独一层而不是每个页面自己 setState：
 *   1. 反馈必须"任何入口都出得来"——题库、判题台、自评、签到都会触发，
 *      页面各自实现一定会漏；
 *   2. 一次动作可能同时产生「怪物出现 + 金币 + 图鉴更新」三条信息，
 *      只有集中队列才能保证顺序与不打架；
 *   3. progress.ts 是纯 reducer，让它直接 import UI 会反过来被 UI 依赖，
 *      所以这里做成「无 React 依赖的模块级 store」，谁都能 push。
 *
 * 依赖方向：gameTypes ← feedback ← progress ← 页面
 * ============================================================================
 */
import { useEffect, useState } from 'react';

/* ---------------------------------------------------------------- 类型 */

export type ToastKind = 'ok' | 'bad' | 'info' | 'coin' | 'tame';

export interface Toast {
  id: string;
  kind: ToastKind;
  title: string;
  desc?: string;
  /** 金币变化：正数显示 +N，负数显示 −N */
  coin?: number;
  /** 头像/图标；不传按 kind 取默认图标 */
  icon?: string;
  /** 毫秒；0 表示不自动消失 */
  ttl: number;
}

/** 遭遇一只新怪物时的全屏提示（比 toast 更重，因为它值得被打断） */
export interface Encounter {
  id: string;
  questionId: string;
  chapterId: string;
  title: string;
  fails: number;
  diff?: string;
  qtype?: string;
}

/* ---------------------------------------------------------------- 存储 */

let seq = 0;
const nextId = () => `f${Date.now().toString(36)}${(seq += 1).toString(36)}`;

const toasts: Toast[] = [];
const toastListeners = new Set<(list: Toast[]) => void>();

let encounter: Encounter | null = null;
const encounterListeners = new Set<(e: Encounter | null) => void>();

const timers = new Map<string, ReturnType<typeof setTimeout>>();

function emitToasts(): void {
  const snapshot = [...toasts];
  for (const fn of toastListeners) fn(snapshot);
}

function emitEncounter(): void {
  for (const fn of encounterListeners) fn(encounter);
}

/* ---------------------------------------------------------------- API */

export function pushToast(t: Omit<Toast, 'id' | 'ttl'> & { ttl?: number }): string {
  const id = nextId();
  const item: Toast = { ...t, id, ttl: t.ttl ?? 3000 };
  toasts.unshift(item);
  // 最多同时显示 4 条：再多就会盖住页面，玩家反而看不到内容
  while (toasts.length > 4) {
    const dropped = toasts.pop();
    if (dropped) {
      const timer = timers.get(dropped.id);
      if (timer) clearTimeout(timer);
      timers.delete(dropped.id);
    }
  }
  emitToasts();
  if (item.ttl > 0) {
    timers.set(
      id,
      setTimeout(() => dismissToast(id), item.ttl),
    );
  }
  return id;
}

export function dismissToast(id: string): void {
  const i = toasts.findIndex((t) => t.id === id);
  if (i < 0) return;
  toasts.splice(i, 1);
  const timer = timers.get(id);
  if (timer) clearTimeout(timer);
  timers.delete(id);
  emitToasts();
}

export function clearToasts(): void {
  for (const t of [...toasts]) dismissToast(t.id);
}

/** 新怪物登场。同一只怪只弹一次（由 progress 侧保证），这里不查重。 */
export function pushEncounter(e: Omit<Encounter, 'id'>): void {
  encounter = { ...e, id: nextId() };
  emitEncounter();
}

export function dismissEncounter(): void {
  if (!encounter) return;
  encounter = null;
  emitEncounter();
}

/* -------------------------------------------------------------- hooks */

export function useToasts(): Toast[] {
  const [list, setList] = useState<Toast[]>(toasts);
  useEffect(() => {
    toastListeners.add(setList);
    setList([...toasts]);
    return () => {
      toastListeners.delete(setList);
    };
  }, []);
  return list;
}

export function useEncounter(): Encounter | null {
  const [value, setValue] = useState<Encounter | null>(encounter);
  useEffect(() => {
    encounterListeners.add(setValue);
    setValue(encounter);
    return () => {
      encounterListeners.delete(setValue);
    };
  }, []);
  return value;
}

/** 金币飘字：不占 toast 位，只在顶栏数字上冒一下 +N */
let coinPulse: { id: string; delta: number } | null = null;
const coinListeners = new Set<(v: { id: string; delta: number } | null) => void>();

export function pulseCoins(delta: number): void {
  if (!delta) return;
  coinPulse = { id: nextId(), delta };
  for (const fn of coinListeners) fn(coinPulse);
}

export function useCoinPulse(): { id: string; delta: number } | null {
  const [v, setV] = useState(coinPulse);
  useEffect(() => {
    coinListeners.add(setV);
    return () => {
      coinListeners.delete(setV);
    };
  }, []);
  return v;
}
