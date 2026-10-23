/**
 * session.ts —— 账号会话（真实后端）
 *
 * 定位：
 *   进度仍然以本机 localStorage 为准（离线可用，见 progress.ts）；
 *   账号只负责"多设备同步 + 身份"。所以未登录、连不上后端都是**合法状态**，
 *   UI 显示"本地模式"而不是报错。
 *
 * 令牌存储：
 *   access/refresh 放 localStorage（桌面 WebView 单用户场景可接受）；
 *   真正多租户的产品应换成 httpOnly cookie，这里不做，是因为 Tauri 的
 *   WebView 与浏览器共享 origin 限制不同，cookie 会引入额外的调试成本。
 *
 * 自动续期：
 *   access 2h。每次 apiGet/apiPost 收到 401 时尝试 refresh 一次再重放请求，
 *   避免"用着用着突然退出登录"。
 */
import { useCallback, useEffect, useState } from 'react';

import { ApiError, ApiNetworkError, apiGet, apiHealth, apiPatch, apiPost, setRefreshHandler } from './api';

const K_ACCESS = 'nex.accessToken';
const K_REFRESH = 'nex.refreshToken';
const K_USER = 'nex.user';

export interface AccountProfile {
  nickname: string;
  avatar_url: string;
  direction: string | null;
  daily_minutes: number;
  plan: string;
  theme: string;
  reduced_motion: boolean;
  font_scale: number;
}

export interface Account {
  uuid: string;
  email: string | null;
  profile: AccountProfile;
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export type SessionStatus = 'anonymous' | 'online' | 'offline';

export interface SessionState {
  status: SessionStatus;
  account: Account | null;
  /** 最近一次失败原因（用于登录框提示）；成功后清空 */
  error: string;
  pending: boolean;
}

const listeners = new Set<(s: SessionState) => void>();

/**
 * 「登录成功后拉取云端进度」的钩子。
 *
 * 为什么不直接 `import { pullProgress } from './sync'`：
 *   sync.ts 反向依赖本文件（要 getSession 拿身份），直接静态导入就是
 *   **ESM 循环依赖**；而原来的 `void import('./sync')` 又让 Vite 拆包彻底失效
 *   （sync.ts 已被 App/ProfilePage 静态引用，动态导入只会退化成同步）。
 *
 * 折中方案沿用 progress.ts 的既有做法：定义方注册、使用方调用，
 * 两边只依赖事件顺序，不依赖模块图。由 App.tsx 在启动时接线。
 */
type SignedInHook = () => void;
let onSignedIn: SignedInHook | null = null;

export function setSignedInHook(fn: SignedInHook | null): void {
  onSignedIn = fn;
}

function ls(key: string): string | null {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem(key);
}

function readCachedAccount(): Account | null {
  const raw = ls(K_USER);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Account;
  } catch {
    return null;
  }
}

let state: SessionState = {
  status: readCachedAccount() && ls(K_ACCESS) ? 'online' : 'anonymous',
  account: readCachedAccount(),
  error: '',
  pending: false,
};

/** 探测只做一次：多组件同时挂载时不重复打后端 */
let probed = false;

function emit(patch: Partial<SessionState>): void {
  state = { ...state, ...patch };
  for (const fn of listeners) fn(state);
}

function saveTokens(pair: TokenPair): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(K_ACCESS, pair.access_token);
  localStorage.setItem(K_REFRESH, pair.refresh_token);
}

function clearTokens(): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.removeItem(K_ACCESS);
  localStorage.removeItem(K_REFRESH);
  localStorage.removeItem(K_USER);
}

export function getSession(): SessionState {
  return state;
}

function friendly(exc: unknown): string {
  if (exc instanceof ApiNetworkError) {
    return `连不上内容服务：${exc.message}`;
  }
  if (exc instanceof ApiError) {
    if (exc.status === 0) return '连不上内容服务：请确认 Nex 服务已启动，或先在「设置」里填写服务地址。';
    return exc.message;
  }
  return '请求失败，请稍后再试';
}

/** 登录成功后拉取账号资料 */
async function loadAccount(): Promise<Account> {
  const me = await apiGet<Account>('/api/v1/users/me');
  if (typeof localStorage !== 'undefined') localStorage.setItem(K_USER, JSON.stringify(me));
  return me;
}

export async function login(account: string, password: string): Promise<{ ok: boolean; error: string }> {
  emit({ pending: true, error: '' });
  try {
    const pair = await apiPost<TokenPair>('/api/v1/auth/login', { account, password });
    saveTokens(pair);
    const me = await loadAccount();
    emit({ status: 'online', account: me, pending: false, error: '' });
    // 登录即对齐云端进度。钩子由 App.tsx 在启动时注册（见 setSignedInHook），
    // 这里只负责"通知"，不关心进度模块怎么实现。
    void onSignedIn?.();
    return { ok: true, error: '' };
  } catch (exc) {
    clearTokens();
    const msg = friendly(exc);
    emit({ status: 'anonymous', account: null, pending: false, error: msg });
    return { ok: false, error: msg };
  }
}

export async function register(
  email: string,
  password: string,
  nickname?: string,
): Promise<{ ok: boolean; error: string }> {
  emit({ pending: true, error: '' });
  try {
    await apiPost('/api/v1/auth/register', { email, password, nickname: nickname || undefined });
  } catch (exc) {
    const msg = friendly(exc);
    emit({ pending: false, error: msg });
    return { ok: false, error: msg };
  }
  // 注册成功后直接登录，少一步操作
  return login(email, password);
}

/** 换新 access；失败返回 false 并由调用方决定是否踢回本地模式 */
async function refreshTokens(): Promise<boolean> {
  const rt = ls(K_REFRESH);
  if (!rt) return false;
  try {
    const pair = await apiPost<TokenPair>('/api/v1/auth/refresh', { refresh_token: rt });
    saveTokens(pair);
    return true;
  } catch {
    return false;
  }
}

// 把续期能力交给 api.ts：任何 apiGet/apiPost 收到 401 都会自动续期并重放一次。
// 这里注册而不是让 api.ts import session.ts，是为了避开 ESM 循环依赖。
setRefreshHandler(refreshTokens);

export function logout(): void {
  clearTokens();
  emit({ status: 'anonymous', account: null, error: '', pending: false });
}

/** 启动时探测：有令牌就校验一次，没令牌就判离线/匿名 */
export async function probe(): Promise<void> {
  const token = ls(K_ACCESS);
  if (!token) {
    // 无令牌也可能只是没登录；探一下服务是否在线，用于文案区分
    const h = await apiHealth();
    emit({ status: h.ok ? 'anonymous' : 'offline', account: null });
    return;
  }
  try {
    const me = await loadAccount();
    emit({ status: 'online', account: me, error: '' });
  } catch (exc) {
    if (exc instanceof ApiError && exc.status === 401) {
      if (await refreshTokens()) {
        try {
          const me = await loadAccount();
          emit({ status: 'online', account: me, error: '' });
          return;
        } catch {
          /* 落到下面清空 */
        }
      }
      clearTokens();
      emit({ status: 'anonymous', account: null });
      return;
    }
    // 网络问题：保留本地缓存账号，标记为离线（进度/内容仍可用）
    emit({ status: 'offline', account: readCachedAccount() });
  }
}

export async function updateNickname(nickname: string): Promise<boolean> {
  try {
    await apiPatch('/api/v1/users/me', { nickname });
    const me = await loadAccount();
    emit({ account: me });
    return true;
  } catch {
    return false;
  }
}

export function useSession(): SessionState & {
  signIn: (a: string, p: string) => Promise<{ ok: boolean; error: string }>;
  signUp: (e: string, p: string, n?: string) => Promise<{ ok: boolean; error: string }>;
  signOut: () => void;
  retry: () => void;
} {
  const [value, setValue] = useState(state);

  useEffect(() => {
    const fn = (s: SessionState) => setValue(s);
    listeners.add(fn);
    setValue(state);
    // 只探一次，避免每次挂载都打后端
    if (!probed) {
      probed = true;
      void probe();
    }
    return () => {
      listeners.delete(fn);
    };
  }, []);

  const retry = useCallback(() => {
    probed = true;
    void probe();
  }, []);

  return {
    ...value,
    signIn: login,
    signUp: register,
    signOut: logout,
    retry,
  };
}
