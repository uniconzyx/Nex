/**
 * authBackend.ts —— 认证后端的「选择器」
 * ============================================================================
 * 项目里有两套登录后端，接口形状不同，不能混用同一个令牌：
 *
 *   nex   内置账号服务 —— Nex 内容服务（FastAPI），路径 /api/v1/auth/*
 *         支持注册、access 2h + refresh 自动续期、微信登录探测。
 *         这是默认值，行为与改动前完全一致。
 *
 *   local 本地账号服务 —— 独立部署的 auth-server（Node + Express + MySQL），
 *         路径 /api/auth/*。**不开放注册**（账号由管理员用脚本创建），
 *         无 refresh token（令牌 7 天），支持改密与登出黑名单。
 *
 * 为什么不做成「自动探测哪套能用」：
 *   两套的令牌互不通用。自动探测在「A 能用但登录失败」时会静默切到 B，
 *   用户看到的错误就变成了另一套的，排查成本极高。所以选择权明确交给使用者，
 *   切换时由 session.switchAuthBackend 主动清空令牌。
 */

import { getApiBase } from './api';

export type AuthBackendId = 'nex' | 'local';

const K_BACKEND = 'nex.authBackend';
const K_LOCAL_BASE = 'nex.authBaseUrl';

/**
 * auth-server 的默认地址。
 *
 * **必须与 auth-server/.env.example 的 PORT 一致（3000）**。
 * 曾经这里是 3999（那时是为了跑联调临时换的端口），结果"照 README 起服务、
 * 前端却连 3999"变成一个必然踩的坑 —— 默认值不一致，文档就只是文字。
 * 换端口时两边一起改：`PORT` + 这里（或让用户在设置页填）。
 */
export const LOCAL_AUTH_DEFAULT = 'http://127.0.0.1:3000';

export interface AuthBackendInfo {
  id: AuthBackendId;
  label: string;
  base: string;
  supportsRegister: boolean;
  supportsRefresh: boolean;
  supportsPasswordChange: boolean;
  supportsWechat: boolean;
}

function ls(key: string): string | null {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem(key);
}

function normalize(url: string): string {
  return url.trim().replace(/\/+$/, '');
}

export function getAuthBackendId(): AuthBackendId {
  // 只认字面量 'local'，其余一律回落默认值。
  // 不写 `!== 'nex' ? 'local' : 'nex'`：localStorage 里任何一个脏值都会
  // 把用户悄悄切到另一套后端上，而令牌并不通用。
  return ls(K_BACKEND) === 'local' ? 'local' : 'nex';
}

export function setAuthBackendId(id: AuthBackendId): void {
  if (typeof localStorage === 'undefined') return;
  if (id === 'local') localStorage.setItem(K_BACKEND, 'local');
  else localStorage.removeItem(K_BACKEND);
}

export function getLocalAuthBase(): string {
  const v = ls(K_LOCAL_BASE);
  return v && v.trim() ? normalize(v) : LOCAL_AUTH_DEFAULT;
}

export function setLocalAuthBase(url: string): void {
  if (typeof localStorage === 'undefined') return;
  const v = normalize(url);
  if (v) localStorage.setItem(K_LOCAL_BASE, v);
  else localStorage.removeItem(K_LOCAL_BASE);
}

/** 当前后端的完整画像：UI 靠它决定「显示注册 tab 吗 / 显示微信按钮吗」 */
export function authBackendInfo(): AuthBackendInfo {
  const id = getAuthBackendId();
  if (id === 'local') {
    return {
      id,
      label: '本地账号服务',
      base: getLocalAuthBase(),
      supportsRegister: false,
      supportsRefresh: false,
      supportsPasswordChange: true,
      supportsWechat: false,
    };
  }
  return {
    id,
    label: 'Nex 内容服务',
    base: getApiBase(),
    supportsRegister: true,
    supportsRefresh: true,
    supportsPasswordChange: false,
    supportsWechat: true,
  };
}
