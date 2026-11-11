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

import { apiHealth, isLoopbackBase, lastApiBase, setApiBase, setNetworkErrorHandler, type ApiHealth } from './api';
import { isClient, reconnectContentService } from './clientBridge';

export type ConnectionStatus = 'unknown' | 'online' | 'offline';

/** 一次后端状态变化。连接状态机对外广播的唯一事件形状。 */
export interface ConnEvent {
  type: 'online' | 'offline';
  /** 本次切换发生的时间戳（Date.now()） */
  at: number;
  /** 离线时：失败原因（不含地址前缀，UI 自己拼"当前连的是哪"） */
  reason?: string;
}

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

/**
 * 「从未连上过」时的探测间隔（毫秒）。
 *
 * 与 OFFLINE_BACKOFF 分开：那条阶梯是给「本来好好的、突然断了」用的，
 * 30s 封顶是怕无谓请求。但**冷启动从未连上**是另一回事 —— 后端正在被拉起、
 * 或者用户刚双击 EXE，30s 才试一次就是「等半分钟还是红的」。
 * 这里 2s ~ 3s 快探，最多连续 20 次（约 50s），之后回落到普通退避，
 * 避免真正没装后端时无限刷。
 */
const COLD_START_INTERVAL = 2_000;
const COLD_START_MAX_TRIES = 20;
let coldStartTries = 0;

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

/* ───────────────── 「后端又活了」广播 ───────────────── */

const eventListeners = new Set<(e: ConnEvent) => void>();

/** 订阅后端状态变化（online / offline）。返回取消订阅函数。 */
export function onConnectionEvent(fn: (e: ConnEvent) => void): () => void {
  eventListeners.add(fn);
  return () => {
    eventListeners.delete(fn);
  };
}

function broadcast(e: ConnEvent): void {
  for (const fn of eventListeners) {
    try {
      fn(e);
    } catch {
      /* 单个订阅者出错不能影响其他订阅者 */
    }
  }
}

/**
 * 探测一次后端，并**在结果变化时广播**。
 *
 * 为什么不直接 emit：
 *   「刚刚恢复在线」这个瞬间是多处 UI 需要知道的（登录框清掉过期红字、
 *   业务页重新拉数据、离线提示条自动收起）。让每一处自己 watch status
 *   就会出现「有的地方知道、有的地方还显示旧的」，所以统一在这里广播一次。
 */
export async function checkConnection(force = false): Promise<ConnectionState> {
  const prev = state.status;
  emit({ checking: true });

  // ── 客户端（桌面 EXE）：离线 → 在线这一步，先让 Rust 侧重探地址 ──
  // 冷启动竞态的老根因：api_probe 可能在 uvicorn 就绪前就返回了 reachable=false，
  // 前端因此锁在一个从没验证过的基址上，之后 60s 心跳打的还是那个错地址。
  // 所以「上一次离线」和「force（用户在设置页刚改完地址 / 点了重试）」两种
  // 情况都要重探一次，确保用的是后端**实际**所在的那台机器。
  //
  // ⚠️ 只在「上次离线的回环目标」上重探：用户把地址填成了远端服务器时，
  //    重探会用本机候选覆盖掉用户意志，这是不能接受的。
  const loopbackTarget = isLoopbackBase(lastApiBase());
  let h: ApiHealth;
  if (isClient() && loopbackTarget && (prev === 'offline' || force)) {
    // 重探成功 → 解析缓存已被刷新，下面这次 apiHealth 打的就是新地址；
    // 重探失败 → 仍按当前地址量，别把「探测超时」误当成「后端好了」。
    await reconnectContentService();
  }
  h = await apiHealth();

  // localhost 解析异常：Chromium/WebView2 在 IPv6 优先的机器上，
  // 「localhost」可能先试 ::1 而 uvicorn 只监听了 127.0.0.1，结果后端明明活着
  // 前端却报「无法连接后端」。命中这种情况时把地址纠正成 127.0.0.1 再试一次。
  if (!h.ok && isLoopbackBase(h.base) && /localhost/i.test(h.base)) {
    const fixed = h.base.replace(/\/\/localhost(\b|:)/i, '//127.0.0.1$1');
    const h2 = await apiHealth(false, fixed);
    // 通了就把这个地址固定下来，否则下一次心跳还会从 localhost 试起。
    if (h2.ok) {
      setApiBase(fixed);
      h = h2;
    }
  }

  emit({
    status: h.ok ? 'online' : 'offline',
    health: h,
    checking: false,
    failures: h.ok ? 0 : state.failures + 1,
    base: h.base,
  });

  if (h.ok && prev !== 'online') broadcast({ type: 'online', at: Date.now() });
  if (!h.ok && prev !== 'offline') {
    broadcast({ type: 'offline', at: Date.now(), reason: h.error });
  }
  return state;
}

/**
 * 地址自愈（只在本机回环目标上做，不碰用户手填的远端地址）。
 * 由 retryNow 在「完整重连 + 客户端重探都失败」后调用。
 */
async function recoverBase(): Promise<ConnectionState> {
  const current = lastApiBase();

  // 1. localhost ↔ 127.0.0.1 互换各试一次。
  //    Chromium/WebView2 在 IPv6 优先的机器上，「localhost」可能先试 ::1，
  //    而 uvicorn 只监听 127.0.0.1 —— 后端活着，前端却报连不上。
  const alts: string[] = [];
  if (/\/\/localhost(\b|:)/i.test(current)) {
    alts.push(current.replace(/\/\/localhost(\b|:)/i, '//127.0.0.1$1'));
  } else if (/\/\/127\.0\.0\.1(\b|:)/i.test(current)) {
    alts.push(current.replace(/\/\/127\.0\.0\.1(\b|:)/i, '//localhost$1'));
  }
  for (const cand of alts) {
    const h = await apiHealth(false, cand);
    if (h.ok) {
      // 换到能用的地址，并落进 localStorage —— 否则下次冷启动又回到脏值
      setApiBase(cand);
      return checkConnection();
    }
  }

  // 2. 回环全试过还不通：清掉自定义地址回落到默认。
  //    这一条是「脏配置钉死」的最终保险：宁可回到默认回环，也不留一个
  //    用户自己都不知道存在、且永远连不上的地址。
  if (typeof localStorage !== 'undefined' && localStorage.getItem('nex.apiBaseUrl')) {
    setApiBase('');
  }
  return checkConnection();
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
    let delay: number;
    if (state.status === 'offline') {
      if (state.failures === 0) {
        // 从未连上过（冷启动）：快探，让后端一起来就被发现
        delay = coldStartTries < COLD_START_MAX_TRIES ? COLD_START_INTERVAL : OFFLINE_BACKOFF[2];
        coldStartTries += 1;
      } else {
        delay = OFFLINE_BACKOFF[Math.min(state.failures - 1, OFFLINE_BACKOFF.length - 1)];
      }
    } else {
      delay = onlineIntervalMs;
      coldStartTries = 0;
    }
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
 * 先走完整重连（桌面端会重新探测地址），仍不通才做本机回环地址自愈 ——
 * 「重试只是重打同一个错地址」是这个功能以前最要命的毛病。
 */
export async function retryNow(): Promise<ConnectionState> {
  const first = await checkConnection(true);
  // 在线了、或目标是远端地址 → 不做本机回环自愈（别覆盖用户填的服务器）
  if (first.status === 'online' || !isLoopbackBase(lastApiBase())) return first;
  return recoverBase();
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
