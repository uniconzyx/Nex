/**
 * session.ts —— 账号会话
 *
 * 定位：
 *   进度仍然以本机 localStorage 为准（离线可用，见 progress.ts）；
 *   账号只负责"多设备同步 + 身份"。所以未登录、连不上后端都是**合法状态**，
 *   UI 显示"本地模式"而不是报错。
 *
 * 两套认证后端（详见 lib/authBackend.ts）：
 *   nex   内置账号服务（默认）—— Nex 内容服务，支持注册 + 自动续期；
 *   local 本地账号服务 —— 独立 auth-server，不开放注册，令牌 7 天。
 *   两者的令牌**互不通用**，所以切换后端时必须清空令牌（switchAuthBackend）。
 *
 * 令牌存储：
 *   access/refresh 放 localStorage（桌面 WebView 单用户场景可接受）；
 *   真正多租户的产品应换成 httpOnly cookie，这里不做，是因为 Tauri 的
 *   WebView 与浏览器共享 origin 限制不同，cookie 会引入额外的调试成本。
 *
 * 自动续期：
 *   仅 nex 后端有 refresh（access 2h）。每次 apiGet/apiPost 收到 401 时
 *   尝试 refresh 一次再重放请求，避免"用着用着突然退出登录"。
 *   local 后端没有 refresh 接口 —— 令牌到期就是重新登录，不做伪续期。
 */
import { useCallback, useEffect, useState } from 'react';

import { ApiError, ApiNetworkError, apiGet, apiHealth, apiPatch, apiPost, setRefreshHandler } from './api';
import { getAuthBackendId, setAuthBackendId, type AuthBackendId } from './authBackend';
import { localChangePassword, localHealth, localLogin, localLogout, localMe, localUpdateProfile, type LocalUser } from './authLocal';
import { onConnectionEvent } from './connection';

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

/**
 * 只存 access（local 后端没有 refresh token 可存）。
 * 顺手删掉 K_REFRESH：万一之前是 nex 后端留下的，留着会让 api.ts 的
 * 401 续期逻辑拿一个无用令牌去换，白白多打一次请求。
 */
function saveAccessOnly(access: string): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(K_ACCESS, access);
  localStorage.removeItem(K_REFRESH);
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

/**
 * 当前 access 令牌（没有则 null）。
 *
 * 只给 sync.ts 用：进度同步要直接调 local 后端的 /api/auth/progress，
 * 而那条路径不走 api.ts（api.ts 只认 Nex 的 base 与 401 续期逻辑）。
 * 与其让 sync 自己 `localStorage.getItem('nex.accessToken')`（键名散落两处），
 * 不如把「令牌存在哪」这件事继续只留在本文件里。
 */
export function getAccessToken(): string | null {
  return ls(K_ACCESS);
}

function friendly(exc: unknown): string {
  const local = getAuthBackendId() === 'local';
  const svc = local ? '本地账号服务' : '内容服务';
  // 地址前缀统一由这一处加，不在文案里重复（否则会出现
  // 「连不上内容服务：无法连接后端（http://127.0.0.1:8000）。(http://127.0.0.1:8000)」）
  if (exc instanceof ApiNetworkError) {
    return `连不上${svc}（${exc.base}）：后端未响应。请稍候重试，或在「设置」里修正服务地址。`;
  }
  if (exc instanceof ApiError) {
    if (exc.status === 0) return `连不上${svc}：请确认服务已启动。`;
    // 服务端返回的中文说明可直接展示（含「还可再试 N 次」「约 N 分钟后解锁」）
    return exc.message;
  }
  return '请求失败，请稍后再试';
}

/** local 后端的用户 → 统一的 Account 形状（UI 只认这一种） */
function mapLocalUser(u: LocalUser): Account {
  return {
    uuid: `local-${u.id}`,
    email: null,
    profile: {
      nickname: u.nickname || u.username,
      avatar_url: '',
      direction: null,
      daily_minutes: 0,
      plan: 'free',
      theme: 'light',
      reduced_motion: false,
      font_scale: 1,
    },
  };
}

/** 登录成功后拉取账号资料 */
async function loadAccount(): Promise<Account> {
  if (getAuthBackendId() === 'local') {
    const token = ls(K_ACCESS);
    if (!token) throw new ApiError('登录状态已失效，请重新登录', 1004, 401);
    const me = mapLocalUser(await localMe(token));
    if (typeof localStorage !== 'undefined') localStorage.setItem(K_USER, JSON.stringify(me));
    return me;
  }
  const me = await apiGet<Account>('/api/v1/users/me');
  if (typeof localStorage !== 'undefined') localStorage.setItem(K_USER, JSON.stringify(me));
  return me;
}

export async function login(account: string, password: string): Promise<{ ok: boolean; error: string }> {
  emit({ pending: true, error: '' });
  try {
    if (getAuthBackendId() === 'local') {
      const r = await localLogin(account, password);
      saveAccessOnly(r.token);
    } else {
      const pair = await apiPost<TokenPair>('/api/v1/auth/login', { account, password });
      saveTokens(pair);
    }
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
  // local 后端按设计不开放注册：账号只能由管理员在服务器上创建。
  // 这里明确拒绝，而不是打一个注定 404 的请求。
  if (getAuthBackendId() === 'local') {
    const msg = '本地账号服务不开放注册，账号需由管理员在服务器上用 create-user 脚本创建。';
    emit({ pending: false, error: msg });
    return { ok: false, error: msg };
  }

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
  // local 后端没有 refresh 接口：直接返回 false，让 401 走正常的「重新登录」路径
  if (getAuthBackendId() === 'local') return false;
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

/**
 * 登出。
 *
 * 本地立即清空（用户点了就该立刻回到未登录态，不能等服务端往返），
 * 服务端黑名单是**尽力而为**：local 后端会把这个令牌的 jti 写进黑名单，
 * 失败也不阻塞 UI —— 代价是那个令牌在原有效期内仍然可用，
 * 所以这里不静默吞掉，失败时通过 error 告知。
 */
export function logout(): void {
  const token = ls(K_ACCESS);
  const wasLocal = getAuthBackendId() === 'local';
  clearTokens();
  emit({ status: 'anonymous', account: null, error: '', pending: false });

  if (wasLocal && token) {
    void localLogout(token).catch((exc: unknown) => {
      emit({ error: `已在本机登出，但服务端令牌未作废：${friendly(exc)}` });
    });
  }
}

/** 启动时探测：有令牌就校验一次，没令牌就判离线/匿名 */
export async function probe(): Promise<void> {
  if (getAuthBackendId() === 'local') {
    const token = ls(K_ACCESS);
    if (!token) {
      const h = await localHealth();
      emit({ status: h.ok ? 'anonymous' : 'offline', account: null });
      return;
    }
    try {
      const me = await loadAccount();
      emit({ status: 'online', account: me, error: '' });
    } catch (exc) {
      if (exc instanceof ApiError && exc.status === 401) {
        // local 后端没有续期，401 就是真的失效了
        clearTokens();
        emit({ status: 'anonymous', account: null });
        return;
      }
      emit({ status: 'offline', account: readCachedAccount() });
    }
    return;
  }

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

/**
 * 改昵称。
 *
 * 两套后端都支持了：nex 是 PATCH /users/me，local 是 PUT /auth/profile。
 * 失败时把原因写进 state.error 再返回 false —— 上一版直接 `return false`，
 * 调用方（个人页）只能显示一句「改失败」，用户不知道是超长、掉线还是没登录。
 */
export async function updateNickname(nickname: string): Promise<{ ok: boolean; error: string }> {
  const trimmed = nickname.trim();
  if (!trimmed) return { ok: false, error: '昵称不能为空（想恢复默认请填用户名）' };
  if (trimmed.length > 24) return { ok: false, error: '昵称最多 24 个字符' };

  emit({ pending: true, error: '' });
  try {
    if (getAuthBackendId() === 'local') {
      const token = ls(K_ACCESS);
      if (!token) throw new ApiError('请先登录', 1004, 401);
      const me = mapLocalUser(await localUpdateProfile(token, trimmed));
      if (typeof localStorage !== 'undefined') localStorage.setItem(K_USER, JSON.stringify(me));
      emit({ account: me, pending: false, error: '' });
      return { ok: true, error: '' };
    }
    await apiPatch('/api/v1/users/me', { nickname: trimmed });
    const me = await loadAccount();
    emit({ account: me, pending: false, error: '' });
    return { ok: true, error: '' };
  } catch (exc) {
    const msg = friendly(exc);
    emit({ pending: false, error: msg });
    return { ok: false, error: msg };
  }
}

/* ───────────────── 多后端：切换与改密 ───────────────── */

/**
 * 切换认证后端。
 *
 * **必须先清令牌再切**：两套后端的令牌格式、密钥、用户 ID 空间全都不同。
 * 留着旧令牌切过去，下一次 probe 会拿 A 的令牌打 B，得到的 401 会被
 * 误判成「登录已过期」，用户就会看到一次莫名其妙的掉线。
 */
export function switchAuthBackend(id: AuthBackendId): void {
  if (getAuthBackendId() === id) return;
  clearTokens();
  setAuthBackendId(id);
  emit({ status: 'anonymous', account: null, error: '', pending: false });
  probed = true;
  void probe();
}

/**
 * 应用内改密（仅 local 后端）。
 *
 * 改密会让服务端 token_version + 1，旧令牌立即作废；
 * 服务端会返回一个**绑定新 version 的新令牌**，必须立刻替换掉本地那个，
 * 否则用户改完密码下一毫秒就掉线——这属于典型的"实现漏一半"。
 */
export async function changePassword(
  oldPassword: string,
  newPassword: string,
): Promise<{ ok: boolean; error: string }> {
  if (getAuthBackendId() !== 'local') {
    return { ok: false, error: '当前账号服务不支持在应用内修改密码。' };
  }
  const token = ls(K_ACCESS);
  if (!token) return { ok: false, error: '请先登录。' };
  emit({ pending: true, error: '' });
  try {
    const r = await localChangePassword(token, oldPassword, newPassword);
    saveAccessOnly(r.token);
    emit({ pending: false, error: '' });
    return { ok: true, error: '' };
  } catch (exc) {
    const msg = friendly(exc);
    emit({ pending: false, error: msg });
    return { ok: false, error: msg };
  }
}

export function useSession(): SessionState & {
  signIn: (a: string, p: string) => Promise<{ ok: boolean; error: string }>;
  signUp: (e: string, p: string, n?: string) => Promise<{ ok: boolean; error: string }>;
  signOut: () => void;
  retry: () => void;
  /** 清掉最近一次失败原因（后端恢复后由 connection 广播触发） */
  clearError: () => void;
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

  // 后端恢复在线 → 清掉「连不上内容服务」这类过期红字，并重探一次会话。
  // 为什么放在这里而不是各页面各写一遍：提示文案的归属地是本模块，
  // 谁来清也必须在这里，否则 LoginForm 的局部 msg 会一直挂到用户重开应用。
  useEffect(
    () =>
      onConnectionEvent((e) => {
        if (e.type !== 'online') return;
        if (state.error) emit({ error: '' });
        probed = true;
        void probe();
      }),
    [],
  );

  const retry = useCallback(() => {
    probed = true;
    void probe();
  }, []);

  const clearError = useCallback(() => {
    if (state.error) emit({ error: '' });
  }, []);

  return {
    ...value,
    signIn: login,
    signUp: register,
    signOut: logout,
    retry,
    clearError,
  };
}
