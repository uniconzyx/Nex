/**
 * authLocal.ts —— 本地账号服务（auth-server）的 HTTP 客户端
 * ============================================================================
 * 对接的是本机另一套后端：Node + Express + MySQL，路径前缀 /api/auth。
 * 四个接口：login / me / password / logout，外加一个无鉴权的 health 探针。
 *
 * 设计原则与 api.ts 保持一致：
 *   · 网络层失败抛 ApiNetworkError，业务失败抛 ApiError —— 让上层
 *     session.ts 的 friendly() 能用同一套规则翻译成人话；
 *   · 不在这里做任何重试。登录失败重试会加速触发「5 次锁定」，必须由用户决定。
 *   · 服务端的附加数据（剩余尝试次数 / 解锁倒计时）直接并进错误文案，
 *     而不是让调用方去猜 —— 这几个数字是用户唯一能据此行动的信息。
 */

import { ApiError, ApiNetworkError } from './api';
import { getLocalAuthBase } from './authBackend';

interface Envelope<T> {
  code: number;
  message: string;
  data: T;
}

/** GET /api/auth/me 的返回 */
export interface LocalUser {
  id: number;
  username: string;
  nickname: string;
  lastLoginAt: string | null;
  createdAt: string;
}

/** login / password 的返回：令牌 + 有效期 + 精简用户 */
export interface LocalTokenResult {
  token: string;
  expiresIn: number;
  user: { id: number; username: string; nickname: string };
}

export interface LocalHealth {
  ok: boolean;
  base: string;
  db?: { ok: boolean; error?: string | null };
  error?: string;
}

/** 服务端附加信息 → 一句能指导下一步动作的补充说明 */
function decorate(message: string, data: unknown): string {
  if (!data || typeof data !== 'object') return message;
  const d = data as { retryAfter?: number; remaining?: number };
  if (typeof d.retryAfter === 'number' && d.retryAfter > 0) {
    const min = Math.max(1, Math.ceil(d.retryAfter / 60));
    return `${message}（约 ${min} 分钟后解锁）`;
  }
  if (typeof d.remaining === 'number' && d.remaining > 0) {
    return `${message}（还可再试 ${d.remaining} 次，之后将锁定账号）`;
  }
  return message;
}

async function call<T>(
  method: 'GET' | 'POST' | 'PUT',
  path: string,
  opts: { token?: string; body?: unknown } = {},
): Promise<T> {
  const base = getLocalAuthBase();
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;

  let res: Response;
  try {
    res = await fetch(base + path, {
      method,
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    });
  } catch {
    throw new ApiNetworkError(`请确认 auth-server 已在 ${base} 启动`, base);
  }

  const body = (await res.json().catch(() => null)) as Envelope<T> | null;

  if (!res.ok || !body || body.code !== 0) {
    const msg = body?.message || `请求失败（HTTP ${res.status}）`;
    throw new ApiError(decorate(msg, body?.data), body?.code ?? -1, res.status);
  }
  return body.data;
}

/**
 * 探活。永不抛异常 —— 调用方只想知道「通没通」，原因放在 error 字段里。
 */
export async function localHealth(): Promise<LocalHealth> {
  const base = getLocalAuthBase();
  try {
    const r = await call<{ service: string; db: { ok: boolean; error: string | null } }>(
      'GET',
      '/api/auth/health',
    );
    return { ok: true, base, db: r.db };
  } catch (exc) {
    return {
      ok: false,
      base,
      error: exc instanceof ApiError ? exc.message : `无法连接 ${base}`,
    };
  }
}

export function localLogin(username: string, password: string): Promise<LocalTokenResult> {
  return call<LocalTokenResult>('POST', '/api/auth/login', { body: { username, password } });
}

export function localMe(token: string): Promise<LocalUser> {
  return call<LocalUser>('GET', '/api/auth/me', { token });
}

export function localLogout(token: string): Promise<null> {
  return call<null>('POST', '/api/auth/logout', { token });
}

export function localChangePassword(
  token: string,
  oldPassword: string,
  newPassword: string,
): Promise<LocalTokenResult> {
  return call<LocalTokenResult>('PUT', '/api/auth/password', {
    token,
    body: { oldPassword, newPassword },
  });
}

/**
 * 改昵称。返回改完后的完整个人信息（服务端刻意回整份，省一次 /me）。
 * 昵称允许传空串，语义是「清除自定义昵称，显示用户名」。
 */
export function localUpdateProfile(token: string, nickname: string): Promise<LocalUser> {
  return call<LocalUser>('PUT', '/api/auth/profile', { token, body: { nickname } });
}

/* ───────────────────────── 进度快照 ───────────────────────── */

export interface LocalProgress {
  /** 云端还没有进度时为 null（不是错误状态） */
  snapshot: unknown;
  rev: number;
  updatedAt: string | null;
}

export function localGetProgress(token: string): Promise<LocalProgress> {
  return call<LocalProgress>('GET', '/api/auth/progress', { token });
}

/**
 * 整份覆盖云端快照。
 *
 * 注意**不要**在这里做「先拉后推」：调用方（sync.ts）已经在上层做过并集合并，
 * 这里再拉一次就成了两次往返 + 两个真相源。本函数只负责把给定的字节送上去。
 */
export function localPutProgress(
  token: string,
  snapshot: unknown,
  clientRev: number,
): Promise<{ rev: number; updatedAt: string | null }> {
  return call<{ rev: number; updatedAt: string | null }>('PUT', '/api/auth/progress', {
    token,
    body: { snapshot, client_rev: clientRev },
  });
}
