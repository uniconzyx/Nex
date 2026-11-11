/**
 * api.ts —— 内容服务（FastAPI）访问层
 *
 * 与 GoJudgeClient 的区别：
 *   GoJudgeClient 打的是 go-judge 沙箱（局域网直连，端口 8080）；
 *   本文件打的是 Nex 自己的 HTTP 服务（默认 127.0.0.1:8000）。
 *
 * 地址可覆盖：localStorage["nex.apiBaseUrl"]，便于局域网/真机调试。
 *
 * ── 打通前后端与客户端的三件事 ─────────────────────────────────────
 *  1. **地址只此一处**：getApiBase() 是全站唯一的基址来源。
 *     客户端（Tauri）可以通过 registerBaseResolver 注入 Rust 侧探测到的地址，
 *     浏览器/纯前端则回落到 localStorage / 默认回环地址。
 *  2. **401 自动续期**：apiGet/apiPost 收到 401 时调用 session.ts 注册的
 *     refresh 钩子，成功后原样重放一次请求。钩子注册在 session.ts 里，
 *     避免 api.ts ← session.ts 的循环依赖。
 *  3. **健康探测**：apiHealth() 打 /api/v1/system/health（浅探测，不连数据库），
 *     供设置页与顶栏展示「后端在线 / 离线 / 哪些功能可用」。
 */

// 分发版后端地址：构建期由 Vite 注入 VITE_NEX_API_BASE（见 deploy/package/prepare_app.py）。
// 这样烤进 EXE/APK 的默认地址就是线上服务（如 https://api.你的域名.com），
// 装到别人电脑上也会默认连线上后端，而不是写死的 127.0.0.1（只有本机才有后端）。
// 缺省回落 127.0.0.1:8000（本机 Docker 后端），仍可被 localStorage / 客户端解析器覆盖。
const DEFAULT_BASE = (import.meta.env as Record<string, string | undefined>).VITE_NEX_API_BASE
  || 'http://127.0.0.1:8000';

/** 客户端注入的基址解析器（Rust 侧探测结果）。返回 null 表示客户端没意见。 */
type BaseResolver = () => string | null | Promise<string | null>;
let baseResolver: BaseResolver | null = null;

/**
 * 注册客户端侧的基址解析器。
 * Tauri 客户端用它把「本机后端实际在哪」告诉前端；纯浏览器不注册。
 * 优先级：客户端解析器 > localStorage > 默认回环地址。
 */
export function registerBaseResolver(fn: BaseResolver | null): void {
  baseResolver = fn;
}

let cachedResolvedBase: string | null = null;

/** 归一化：去尾斜杠。 */
function normalize(url: string): string {
  return url.trim().replace(/\/+$/, '');
}

/** 判断一个地址是否指向本机回环（127.0.0.0/8、localhost、[::1]）。 */
export function isLoopbackBase(url: string): boolean {
  try {
    const h = new URL(url).hostname.toLowerCase();
    return h === 'localhost' || h === '::1' || h === '[::1]' || h.startsWith('127.');
  } catch {
    return false;
  }
}

/** 同步取基址（不等待客户端解析器）。 */
export function getApiBase(): string {
  if (typeof localStorage !== 'undefined') {
    const custom = localStorage.getItem('nex.apiBaseUrl');
    if (custom && custom.trim()) return normalize(custom);
  }
  return DEFAULT_BASE;
}

/**
 * 异步取基址：先问客户端，再回落本地配置。
 * 请求前统一走这个，保证客户端探测到的地址真的被用上。
 */
export async function resolveApiBase(): Promise<string> {
  if (baseResolver) {
    try {
      const v = await baseResolver();
      if (v && v.trim()) {
        cachedResolvedBase = normalize(v);
        return cachedResolvedBase;
      }
    } catch {
      /* 客户端探测失败 → 回落本地配置 */
    }
  }
  cachedResolvedBase = getApiBase();
  return cachedResolvedBase;
}

/** 最近一次实际使用的基址（供 UI 显示「当前连的是哪」）。 */
export function lastApiBase(): string {
  return cachedResolvedBase ?? getApiBase();
}

/**
 * 手动指定基址（设置页「保存」用）。
 *
 * 用户填了地址就是用户的意志，必须压过客户端探测结果 —— 否则在桌面端改了
 * 也没用（每次请求都被解析器改回去，这是「设置里改了还是连不上」的成因之一）。
 * 清空（传空串）时把解析器也恢复，交还给客户端探测。
 */
export function setApiBase(url: string): void {
  if (typeof localStorage === 'undefined') return;
  const v = normalize(url);
  if (v) {
    localStorage.setItem('nex.apiBaseUrl', v);
    const pinned = v;
    baseResolver = () => pinned;
  } else {
    localStorage.removeItem('nex.apiBaseUrl');
    baseResolver = null;
  }
  cachedResolvedBase = v || DEFAULT_BASE;
}

/** 后端统一响应包（见 app/core/responses.py） */
interface Envelope<T> {
  code: number;
  message: string;
  data: T;
  traceId: string;
}

/** 连接级错误：请求根本没发出去（后端没起 / 地址错 / 被墙）。 */
export class ApiNetworkError extends Error {
  readonly base: string;
  constructor(message: string, base: string) {
    super(message);
    this.name = 'ApiNetworkError';
    this.base = base;
  }
}

export class ApiError extends Error {
  readonly code: number;
  readonly status: number;
  constructor(message: string, code = -1, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

/* ───────────────────────── 401 自动续期 ───────────────────────── */

type RefreshHandler = () => Promise<boolean>;
let refreshHandler: RefreshHandler | null = null;

/**
 * 注册 access token 续期钩子。由 session.ts 在模块加载时调用。
 * 钩子返回 true 表示已换到新 token，api 层会重放原请求一次。
 */
export function setRefreshHandler(fn: RefreshHandler | null): void {
  refreshHandler = fn;
}

/* ───────────────────── 请求失败时的状态上报 ───────────────────── */

type NetworkErrorHandler = (err: ApiNetworkError) => void;
let networkErrorHandler: NetworkErrorHandler | null = null;

/**
 * 注册「连不上后端」的通知钩子。由 connection.ts 注册。
 *
 * 为什么需要：用户点某个功能报「无法连接后端」时，顶栏指示灯还亮着绿点，
 * 这在事实上是错的——后端已经断了。让 api 层把失败**主动**推给连接状态机，
 * 指示灯立刻变红、离线重试立刻加速，而不是等下一次心跳（最长 60s 后）才发现。
 *
 * 同样用钩子而非直接 import，是为了避免 api.ts ← connection.ts 的循环依赖。
 */
export function setNetworkErrorHandler(fn: NetworkErrorHandler | null): void {
  networkErrorHandler = fn;
}

function authHeaders(): Record<string, string> {
  const h: Record<string, string> = { Accept: 'application/json' };
  if (typeof localStorage !== 'undefined') {
    const token = localStorage.getItem('nex.accessToken');
    if (token) h.Authorization = `Bearer ${token}`;
  }
  return h;
}

/* ───────────────────────── 健康探测 ───────────────────────── */

export interface ApiHealth {
  ok: boolean;
  base: string;
  /** 后端名称与版本（连上时） */
  backend?: { name: string; version: string; elapsed_ms: number };
  /** 考研题库快照（文件型功能是否可用） */
  exam?: { ok: boolean; questions?: number; topics?: number; summaries?: number; papers?: number; exams?: number };
  /** 数据库状态（浅探测为 null） */
  database?: { ok: boolean | null; checked: boolean; error?: string };
  /** 逐功能可用性 */
  features?: Record<string, boolean | null>;
  /** 失败原因 */
  error?: string;
}

/**
 * 打后端健康检查。
 * 永不抛异常——调用方只想知道「通没通」，异常信息在 error 字段里。
 *
 * @param deep  深探测（连数据库）
 * @param baseOverride  指定基址（用于验证某个具体地址，不影响全局解析缓存）
 */
export async function apiHealth(deep = false, baseOverride?: string): Promise<ApiHealth> {
  const base = baseOverride ? normalize(baseOverride) : await resolveApiBase();
  try {
    const res = await fetch(`${base}/api/v1/system/health${deep ? '?deep=1' : ''}`, {
      headers: { Accept: 'application/json' },
    });
    const body = (await res.json().catch(() => null)) as Envelope<ApiHealth> | null;
    if (!res.ok || !body || body.code !== 0) {
      return { ok: false, base, error: body?.message || `HTTP ${res.status}` };
    }
    const d = body.data;
    return {
      ok: true,
      base,
      backend: d.backend,
      exam: d.exam,
      database: d.database,
      features: d.features,
    };
  } catch (e) {
    return {
      ok: false,
      base,
      error: `无法连接后端（${base}）：${(e as Error)?.message || '网络错误'}`,
    };
  }
}

/* ───────────────────────── 请求实现 ───────────────────────── */

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT';

interface SendOptions {
  method: Method;
  path: string;
  payload?: unknown;
  signal?: AbortSignal;
  /** 已重放过一次就不再重试，防止死循环 */
  retried?: boolean;
}

async function rawFetch(
  base: string,
  method: Method,
  path: string,
  payload: unknown,
  signal: AbortSignal | undefined,
): Promise<Response> {
  const init: RequestInit = { method, headers: authHeaders() };
  if (payload !== undefined) {
    (init.headers as Record<string, string>)['Content-Type'] = 'application/json';
    init.body = JSON.stringify(payload);
  }
  if (signal) init.signal = signal;
  return fetch(base + path, init);
}

async function send<T>(opts: SendOptions): Promise<T> {
  const base = await resolveApiBase();

  let res: Response;
  try {
    res = await rawFetch(base, opts.method, opts.path, opts.payload, opts.signal);
  } catch (e) {
    if ((e as Error)?.name === 'AbortError') throw e;
    const err = new ApiNetworkError(
      `无法连接后端（${base}）。请确认服务已启动，或在「设置」里修正服务地址。`,
      base,
    );
    // 主动上报：让顶栏指示灯立刻变红、离线重试立刻加速，
    // 而不是等下一次心跳才发现后端已经断了。
    networkErrorHandler?.(err);
    throw err;
  }

  const body = (await res.json().catch(() => null)) as Envelope<T> | null;

  // 401 → 换新 token 后重放一次。
  // 续期接口本身 401 时不能再去续期（会无限递归），故显式跳过。
  if (res.status === 401 && !opts.retried && refreshHandler && !opts.path.includes('/auth/refresh')) {
    const okRefresh = await refreshHandler();
    if (okRefresh) {
      return send<T>({ ...opts, retried: true });
    }
  }

  if (!res.ok) {
    throw new ApiError(body?.message || `请求失败（HTTP ${res.status}）`, body?.code ?? -1, res.status);
  }
  if (body && typeof body.code === 'number' && body.code !== 0) {
    throw new ApiError(body.message || '请求失败', body.code, res.status);
  }
  if (!body) {
    throw new ApiError('后端返回了非预期响应', -1, res.status);
  }
  return body.data;
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  return send<T>({ method: 'GET', path, signal });
}

export async function apiPost<T>(path: string, payload?: unknown): Promise<T> {
  return send<T>({ method: 'POST', path, payload });
}

export async function apiPatch<T>(path: string, payload?: unknown): Promise<T> {
  return send<T>({ method: 'PATCH', path, payload });
}

export async function apiPut<T>(path: string, payload?: unknown): Promise<T> {
  return send<T>({ method: 'PUT', path, payload });
}
