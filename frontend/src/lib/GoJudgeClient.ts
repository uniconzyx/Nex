/**
 * GoJudgeClient.ts
 * ============================================================================
 * Nex 前端判题接入层（双通道：Tauri invoke + 局域网 HTTP）
 *
 * 与 Rust 端的对应关系（改动任一侧都必须同步另一侧）：
 *   src-tauri/src/payload.rs      -> 线格式 DTO（camelCase）
 *   src-tauri/src/judge_client.rs -> `Verdict` 内部标签枚举（tag="verdict", snake_case）
 *   src-tauri/src/main.rs         -> invoke 命令名与参数
 *   src-tauri/src/lan_server.rs   -> 局域网 HTTP 服务（/api/ping | /api/judge）
 *   src-tauri/src/ws_handler.rs   -> `/ws/run` WebSocket 协议
 *   对接文档                     -> docs/Phase9-GoJudge-Frontend-API.md
 *
 * 双通道设计（移动端瘦客户端）：
 *   * 桌面端（Windows/macOS/Linux WebView）-> invoke('judge_batch')，本机沙箱。
 *   * 移动端（Android APK）/ 纯浏览器      -> fetch `http://<电脑局域网IP>:8080/api/judge`，
 *     请求 Windows 桌面端判题。地址存 localStorage（键见 LAN_BASE_URL_KEY）。
 *   * 由 {@link GoJudgeClient.submitCode} 自动选路，UI 层无感。
 *
 * ⚠️ 为什么不能只用 `window.__TAURI_INTERNALS__` 判断「桌面」：
 *   Android APK 也是 Tauri 应用，WebView 里同样有 `__TAURI_INTERNALS__`，
 *   但手机上没有 go-judge。误判会让 invoke 走进降级 mock 模式、在手机上
 *   **无隔离地本地直跑**用户代码。必须结合 UA 排除移动端（见 isMobileUa）。
 *
 * 前置条件：
 *   1. 依赖 `@tauri-apps/api`（npm i @tauri-apps/api）。
 *   2. capabilities/default.json 已放行 allow-judge / allow-judge-batch /
 *      allow-judge-ws-url / allow-check-environment / allow-get-status。
 *   3. 局域网通道：电脑端需在运行且防火墙放行 8080；Android 需在
 *      AndroidManifest.xml 放行明文 HTTP（usesCleartextTraffic），
 *      详见 docs/Phase9-GoJudge-Frontend-API.md 第六节。
 *   4. WS 走 127.0.0.1 回环。若开发期 Vite 走了 HTTP 代理，需把 127.0.0.1
 *      加进 no_proxy，否则浏览器会把 ws://127.0.0.1 丢给代理而连不上。
 * ============================================================================
 */

import { invoke } from '@tauri-apps/api/core';

/* ============================================================================
 * 1. 类型定义 —— 与 Rust 端逐字段对齐
 * ========================================================================== */

/** 判题语言。与 Rust `judge_client::build_request` 的分支一致。 */
export type JudgeLanguage = 'python' | 'py' | 'cpp' | 'c++' | 'c' | 'java';

/** 单条测试用例。 */
export interface TestCase {
  /** 用例输入（stdin）。省略 / undefined 表示空输入。 */
  stdin?: string;
  /** 期望输出（用于前端比对；不传则只判 verdict，不比对内容）。 */
  expected?: string;
  /** 用例名，仅用于 UI 展示。 */
  name?: string;
}

/** invoke('judge', ...) 的入参（与 Rust 命令签名一致）。 */
export interface SubmitRequest {
  lang: string;
  code: string;
  stdin?: string;
}

/**
 * Rust `judge_client::Verdict` 的 TS 镜像。
 *
 * Rust 侧：#[serde(tag = "verdict", rename_all = "snake_case")]
 *  => 序列化为 { "verdict": "accepted", "stdout": ..., "time_ms": ..., "memory_kb": ... }
 *  注意字段是 **snake_case**（不是 camelCase），这是 Rust 侧刻意为之，
 *  因为 Verdict 是「后端内部契约」，不像 payload.rs 那样要迁就 go-judge 线格式。
 */
export type Verdict =
  | { verdict: 'accepted'; stdout: string; time_ms: number; memory_kb: number }
  | { verdict: 'compile_error'; stderr: string }
  | { verdict: 'runtime_error'; stderr: string; signal: string | null }
  | { verdict: 'time_limit_exceeded' }
  | { verdict: 'memory_limit_exceeded' }
  | { verdict: 'output_limit_exceeded' }
  | { verdict: 'illegal_syscall'; msg: string }
  /** 宿主墙钟看门狗触发（sleep / 死循环，cpuLimit 防不住的那类） */
  | { verdict: 'wall_timeout' }
  /** 降级模式：无 go-judge，本地直跑的回显结果 */
  | { verdict: 'mock'; stdout: string };

/** Verdict 的判别键字面量联合。 */
export type VerdictKind = Verdict['verdict'];

/** invoke('check_environment') 返回：单语言探测结果。 */
export interface LangStatus {
  name: string;
  available: boolean;
  path: string | null;
  version: string | null;
}

/** invoke('check_environment') 返回：环境总览。 */
export interface EnvReport {
  languages: LangStatus[];
  go_judge: boolean;
  go_judge_path: string | null;
}

/** invoke('get_status') 返回：判题服务运行时状态。 */
export interface JudgeStatus {
  go_judge_available: boolean;
  mock_mode: boolean;
  port: number;
  pid: number;
  enable_network: boolean;
}

/** `/ws/run` 上行消息（与 Rust `ws_handler::WsJudgeReq` 完全一致）。 */
export interface WsJudgeReq {
  lang: string;
  code: string;
  /** 可省略；Rust 侧是 Option<String> 且带 #[serde(default)] */
  stdin?: string | null;
}

/* ============================================================================
 * 5. 双通道传输层 —— 桌面 invoke / 局域网 HTTP（移动端瘦客户端）
 * ========================================================================== */

/** 实际使用的传输通道。 */
export type Transport = 'invoke' | 'lan';

/** 通道模式：用户可在设置页强制指定；默认 `auto` 按环境自动判定。 */
export type TransportMode = 'auto' | 'invoke' | 'lan';

/** `GET /api/ping` 响应（Rust `lan_server::PingResp`）。 */
export interface LanPing {
  ok: boolean;
  service: string;
  version: string;
  /** go-judge 沙箱是否就绪；false = 电脑端在降级模式，不会受理判题 */
  go_judge: boolean;
  /** 当前是否受理判题 */
  accepting: boolean;
}

/** `POST /api/judge` 请求体（Rust `lan_server::JudgeHttpReq`，rename_all=camelCase）。 */
export interface LanJudgeReq {
  lang: string;
  code: string;
  /** 与 invoke('judge_batch') 的 stdins 同义；空数组按「一条空 stdin」处理 */
  stdins?: string[];
}

/** localStorage 键：电脑端局域网地址，形如 `http://192.168.1.5:8080`。 */
export const LAN_BASE_URL_KEY = 'nex.judge.lanBaseUrl';
/** localStorage 键：通道模式（auto / invoke / lan）。 */
export const LAN_MODE_KEY = 'nex.judge.transportMode';
/** 局域网默认端口，须与 Rust `lan_server::DEFAULT_LAN_PORT` 保持一致。 */
export const LAN_DEFAULT_PORT = 8080;

/** Tauri v2 在 WebView 中注入的内部对象（invoke 的载体）。 */
function hasTauriInternals(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

/**
 * 是否移动端 UA。
 *
 * ⚠️ 关键：Android APK **也是** Tauri 应用，WebView 里同样有
 * `__TAURI_INTERNALS__`，但手机上没有 go-judge 沙箱。若只凭这个对象判断
 * 「桌面」，invoke 会走进降级 mock 模式、在手机上无隔离地本地直跑用户代码。
 * 因此「桌面」的判据必须是 `__TAURI_INTERNALS__` 存在 **且** UA 不是移动端。
 */
function isMobileUa(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent);
}

/** 读通道模式；localStorage 不可用（隐私模式等）时静默回退 auto。 */
function readStoredMode(): TransportMode {
  try {
    const v = localStorage.getItem(LAN_MODE_KEY);
    if (v === 'invoke' || v === 'lan' || v === 'auto') return v;
  } catch {
    /* ignore */
  }
  return 'auto';
}

/** 归一化用户填写的地址：补 `http://` 协议、去尾斜杠。 */
export function normalizeLanBaseUrl(input: string): string {
  const s = input.trim();
  if (!s) return '';
  const withProto = /^https?:\/\//i.test(s) ? s : `http://${s}`;
  return withProto.replace(/\/+$/, '');
}

/**
 * 带超时的 fetch。
 * 判题 + 编译可能要几十秒，不能用浏览器默认的「永不超时」等待；
 * 也不能用太短的超时把正常的 C++ 编译掐掉。
 */
async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

/** 把 fetch 的网络层失败翻译成「用户能照着做」的中文提示。 */
export function describeLanFetchError(e: unknown, baseUrl: string, timeoutMs: number): string {
  const base = `无法连接到电脑（${baseUrl}）`;
  if (e instanceof DOMException && e.name === 'AbortError') {
    return `${base}：请求超过 ${Math.round(timeoutMs / 1000)} 秒无响应。判题可能仍在电脑端进行，请稍后重试。`;
  }
  // 浏览器把「拒连 / 无路由 / DNS 失败」统一报成 TypeError，无法进一步区分，
  // 所以这里给出排查清单而不是猜原因。
  if (e instanceof TypeError) {
    return (
      `${base}。请依次检查：\n` +
      '1) 手机与电脑是否连接同一个 Wi-Fi（不要用 5G/2.4G 混连，部分路由器开启了 AP 隔离）；\n' +
      '2) 电脑端 Nex 是否在运行，日志里有没有 "[lan] 局域网判题服务: http://<IP>:8080"；\n' +
      '3) Windows 防火墙是否放行了 8080（首次启动 Nex 时的弹窗要选「允许」，\n' +
      '   或在管理员 PowerShell 里执行：\n' +
      '   New-NetFirewallRule -DisplayName "Nex Judge LAN" -Direction Inbound `\n' +
      '     -LocalPort 8080 -Protocol TCP -Action Allow）；\n' +
      '4) 地址是否填错（应为 http://<电脑局域网IP>:8080，不要带结尾斜杠）。'
    );
  }
  return `${base}：${describeError(e)}`;
}

/* ============================================================================
 * 2. UI 状态映射 —— 底层 verdict -> 文案 / 色调
 * ========================================================================== */

export type Tone = 'success' | 'error' | 'warning' | 'info' | 'neutral';

export interface VerdictUi {
  kind: VerdictKind;
  /** 徽章短文案 */
  label: string;
  /** 语义色调（前端据此选配色） */
  tone: Tone;
  /** 悬浮提示：解释这个状态到底意味着什么 */
  hint: string;
}

/**
 * 全量映射表。新增 Rust Verdict 变体时，TS 会在这里报编译错
 * （Record<VerdictKind, ...> 要求穷尽），不会静默漏配。
 */
export const VERDICT_UI: Record<VerdictKind, VerdictUi> = {
  accepted: {
    kind: 'accepted',
    label: '通过',
    tone: 'success',
    hint: '程序正常退出（exit code 0）',
  },
  compile_error: {
    kind: 'compile_error',
    label: '编译错误',
    tone: 'error',
    hint: '编译器报错，请查看 stderr',
  },
  runtime_error: {
    kind: 'runtime_error',
    label: '运行错误',
    tone: 'error',
    hint: '运行时崩溃或非零退出，请查看 stderr',
  },
  time_limit_exceeded: {
    kind: 'time_limit_exceeded',
    label: '超时',
    tone: 'warning',
    hint: '超出 go-judge CPU 时间上限',
  },
  memory_limit_exceeded: {
    kind: 'memory_limit_exceeded',
    label: '内存超限',
    tone: 'warning',
    hint: '超出内存上限',
  },
  output_limit_exceeded: {
    kind: 'output_limit_exceeded',
    label: '输出超限',
    tone: 'warning',
    hint: '输出量超过 go-judge 上限，疑似死循环打印',
  },
  illegal_syscall: {
    kind: 'illegal_syscall',
    label: '危险操作',
    tone: 'error',
    hint: '沙箱拦截了非法系统调用（如直接操作进程 / 网络）',
  },
  wall_timeout: {
    kind: 'wall_timeout',
    label: '超时',
    tone: 'warning',
    hint: '墙钟看门狗触发：进程已被强制结束（sleep/死循环）',
  },
  mock: {
    kind: 'mock',
    label: '通过',
    tone: 'info',
    hint: '本地直跑结果（未启用 go-judge 沙箱）',
  },
};

/** 色调 -> CSS 变量/十六进制（与 Nex 蓝白设计系统兼容，浅色主题）。 */
export const TONE_COLORS: Record<Tone, { bg: string; fg: string; border: string }> = {
  success: { bg: '#ECFDF5', fg: '#047857', border: '#A7F3D0' },
  error: { bg: '#FEF2F2', fg: '#B91C1C', border: '#FECACA' },
  warning: { bg: '#FFFBEB', fg: '#B45309', border: '#FDE68A' },
  info: { bg: '#EFF6FF', fg: '#1D4ED8', border: '#BFDBFE' },
  neutral: { bg: '#F8FAFC', fg: '#475569', border: '#E2E8F0' },
};

/** 把底层 Verdict 映射成 UI 可直接渲染的结构。未知 kind 有兜底，不会抛。 */
export function mapVerdictToUi(v: Verdict): VerdictUi {
  const ui = VERDICT_UI[v.verdict];
  if (ui) return ui;
  // 防御：Rust 端新增了变体而前端没跟上
  return {
    kind: v.verdict,
    label: '未知状态',
    tone: 'neutral',
    hint: `未识别的判定类型：${String(v.verdict)}`,
  };
}

/** 是否算「这条用例通过」。mock 模式同样按内容比对。 */
export function isVerdictPassed(v: Verdict, expected?: string): boolean {
  if (v.verdict !== 'accepted' && v.verdict !== 'mock') return false;
  if (expected === undefined) return true;
  const actual = v.verdict === 'accepted' ? v.stdout : v.stdout;
  return normalizeOutput(actual) === normalizeOutput(expected);
}

/**
 * OJ 标准归一化：去掉每行首尾空白 + 去掉末尾空行。
 * 判题系统普遍这样做，否则 `print(42)` 和 `print(42, end="")` 会被误判为不同。
 */
export function normalizeOutput(s: string): string {
  return s
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((line) => line.replace(/[ \t]+$/g, ''))
    .join('\n')
    .replace(/\n+$/g, '');
}

/* ============================================================================
 * 3. 错误类型 —— 把 Tauri 的 Promise 拒绝转成友好结构
 * ========================================================================== */

export type JudgeErrorKind =
  /** invoke 本身失败：命令不存在 / 权限未放行 / Rust 端返回 Err(String) */
  | 'invoke'
  /** 前端主动取消（WS 断开） */
  | 'cancelled'
  /** 环境缺失（go-judge / 编译器没装） */
  | 'env'
  /** WebSocket 连接失败 */
  | 'transport'
  /** 局域网 HTTP 通道失败（连不上电脑 / 电脑端 4xx·5xx / 未配置地址） */
  | 'lan'
  /** 请求超时（含 fetch 的 AbortController） */
  | 'timeout'
  /** 其它 */
  | 'unknown';

export class JudgeClientError extends Error {
  readonly kind: JudgeErrorKind;
  readonly raw?: unknown;

  constructor(kind: JudgeErrorKind, message: string, raw?: unknown) {
    super(message);
    this.name = 'JudgeClientError';
    this.kind = kind;
    this.raw = raw;
  }
}

/** 从任意异常里榨出可读信息（Tauri 的 reject 经常只是一个裸 string）。 */
function describeError(e: unknown): string {
  if (typeof e === 'string') return e;
  if (e instanceof Error) return e.message;
  try {
    return JSON.stringify(e);
  } catch {
    return String(e);
  }
}

/** 把 Rust 端错误字符串归类成 kind。Rust 侧 NexError 的 Display 前缀可作判据。 */
function classifyRustError(msg: string): JudgeErrorKind {
  const m = msg.toLowerCase();
  if (m.includes('permission') || m.includes('not allowed') || m.includes('not found')) {
    return 'invoke';
  }
  if (m.includes('go-judge') || m.includes('sidecar') || m.includes('mock')) {
    return 'env';
  }
  return 'invoke';
}

/* ============================================================================
 * 4. GoJudgeClient —— Tauri 通信封装
 * ========================================================================== */

export interface GoJudgeClientOptions {
  /** 判题有副作用（会起进程），默认**不重试**。 */
  retries?: number;
  /** 诊断日志回调。 */
  onLog?: (msg: string) => void;
  /** 通道模式，默认 'auto'（按运行环境自动选 invoke / 局域网）。 */
  mode?: TransportMode;
  /** 局域网地址；不传则读 localStorage（键 LAN_BASE_URL_KEY）。 */
  lanBaseUrl?: string;
  /**
   * 局域网请求超时（毫秒），默认 120s。
   * C++ 首用例编译 + N 个用例运行可能较久，别设太短。
   */
  lanTimeoutMs?: number;
}

/** 一条用例的完整判定结果（含 UI 映射与内容比对）。 */
export interface TestCaseResult {
  index: number;
  name: string;
  verdict: Verdict;
  ui: VerdictUi;
  passed: boolean;
  expected?: string;
  actual?: string;
  /** 未通过时的简短原因 */
  reason?: string;
}

export class GoJudgeClient {
  private readonly retries: number;
  private readonly log: (msg: string) => void;
  private wsUrlCache: string | null = null;
  private activeWs: WebSocket | null = null;
  private readonly mode: TransportMode;
  private readonly lanTimeoutMs: number;

  constructor(opts: GoJudgeClientOptions = {}) {
    this.retries = opts.retries ?? 0;
    this.log = opts.onLog ?? ((m) => console.log('[GoJudgeClient]', m));
    this.mode = opts.mode ?? readStoredMode();
    this.lanTimeoutMs = opts.lanTimeoutMs ?? 120_000;
    if (opts.lanBaseUrl) this.setLanBaseUrl(opts.lanBaseUrl);
  }

  /* -------------------- 局域网通道管理 -------------------- */

  /** 读取电脑端局域网地址（已归一化；未配置返回空串）。 */
  getLanBaseUrl(): string {
    try {
      return normalizeLanBaseUrl(localStorage.getItem(LAN_BASE_URL_KEY) ?? '');
    } catch {
      return '';
    }
  }

  /** 设置/清除电脑端局域网地址。手机端首次使用前必须调用。 */
  setLanBaseUrl(url: string): void {
    const norm = normalizeLanBaseUrl(url);
    try {
      if (norm) localStorage.setItem(LAN_BASE_URL_KEY, norm);
      else localStorage.removeItem(LAN_BASE_URL_KEY);
    } catch {
      /* ignore */
    }
    this.log(`LAN 地址已${norm ? `设置为 ${norm}` : '清除'}`);
  }

  /** 强制指定通道模式（设置页用）。 */
  setMode(mode: TransportMode): void {
    try {
      localStorage.setItem(LAN_MODE_KEY, mode);
    } catch {
      /* ignore */
    }
  }

  /** 当前配置的模式（auto 时返回 'auto'，不代表实际通道）。 */
  getMode(): TransportMode {
    return this.mode;
  }

  /** 读不到地址时抛出带引导文案的错误。 */
  private requireLanBaseUrl(): string {
    const base = this.getLanBaseUrl();
    if (!base) {
      throw new JudgeClientError(
        'lan',
        '尚未配置电脑端地址。请填写电脑端日志里显示的 http://<局域网IP>:8080',
      );
    }
    return base;
  }

  /**
   * 判定本次用哪条通道。
   *
   * 判据（'auto' 模式）：
   *   * 桌面 Tauri（有 `__TAURI_INTERNALS__` 且 UA 非移动端）-> invoke
   *   * 否则（Android APK / 纯浏览器）-> 局域网 HTTP
   * 详见 isMobileUa() 的注释：Android 上也有 `__TAURI_INTERNALS__`，
   * 但不能走 invoke，否则会在手机上无隔离地本地直跑用户代码。
   */
  private resolveTransport(): Transport {
    if (this.mode === 'invoke') return 'invoke';
    if (this.mode === 'lan') {
      this.requireLanBaseUrl();
      return 'lan';
    }

    const lan = this.getLanBaseUrl();
    if (hasTauriInternals() && !isMobileUa()) return 'invoke';
    if (lan) return 'lan';

    if (hasTauriInternals()) {
      // 移动端 Tauri（APK）：没有沙箱，绝不能走 invoke 的本地直跑
      throw new JudgeClientError(
        'lan',
        '检测到移动端环境：请先配置电脑端的局域网地址（http://<IP>:8080）',
      );
    }
    throw new JudgeClientError(
      'lan',
      '当前不在 Tauri 桌面环境：请配置电脑端的局域网地址（http://<IP>:8080）',
    );
  }

  /**
   * 探测电脑端是否可达、沙箱是否就绪。
   * 手机端填完 IP 后应先调用这个，比直接判题的错误提示友好得多。
   */
  async probeLan(): Promise<LanPing> {
    const base = this.requireLanBaseUrl();
    let resp: Response;
    try {
      resp = await fetchWithTimeout(`${base}/api/ping`, { method: 'GET' }, this.lanTimeoutMs);
    } catch (e) {
      throw new JudgeClientError('lan', describeLanFetchError(e, base, this.lanTimeoutMs), e);
    }
    if (!resp.ok) {
      throw new JudgeClientError('lan', `电脑端返回 ${resp.status} ${resp.statusText}`);
    }
    return (await resp.json()) as LanPing;
  }

  /* -------------------- 底层 invoke -------------------- */

  private async call<T>(cmd: string, args: Record<string, unknown>): Promise<T> {
    let lastErr: unknown;
    for (let attempt = 0; attempt <= this.retries; attempt += 1) {
      try {
        this.log(`invoke ${cmd} (attempt ${attempt + 1})`);
        return await invoke<T>(cmd, args);
      } catch (e) {
        lastErr = e;
        this.log(`invoke ${cmd} failed: ${describeError(e)}`);
      }
    }
    const msg = describeError(lastErr);
    throw new JudgeClientError(classifyRustError(msg), msg, lastErr);
  }

  /* -------------------- 对外能力 -------------------- */

  /**
   * 取 WS 地址（Rust 侧 `judge-ws-url` 命令，形如 ws://127.0.0.1:14520/ws/run）。
   */
  async getWsUrl(): Promise<string> {
    if (!this.wsUrlCache) {
      this.wsUrlCache = await this.call<string>('judge_ws_url', {});
    }
    return this.wsUrlCache;
  }

  /**
   * 环境探测：go-judge 与 g++/python/java 是否就绪（用于引导弹窗）。
   * 桌面走 invoke；移动端走局域网 `GET /api/environment`——探测的是**电脑端**环境，
   * 因为判题发生在电脑上，手机端不需要编译器。
   */
  async checkEnvironment(): Promise<EnvReport> {
    if (this.resolveTransport() === 'lan') {
      const base = this.requireLanBaseUrl();
      let resp: Response;
      try {
        resp = await fetchWithTimeout(
          `${base}/api/environment`,
          { method: 'GET' },
          this.lanTimeoutMs,
        );
      } catch (e) {
        throw new JudgeClientError('lan', describeLanFetchError(e, base, this.lanTimeoutMs), e);
      }
      if (!resp.ok) {
        throw new JudgeClientError('lan', `电脑端返回 ${resp.status} ${resp.statusText}`);
      }
      return (await resp.json()) as EnvReport;
    }
    return this.call<EnvReport>('check_environment', {});
  }

  /** 运行时状态：端口 / PID / 是否 mock 模式。 */
  async getStatus(): Promise<JudgeStatus> {
    return this.call<JudgeStatus>('get_status', {});
  }

  /**
   * 单词判题。
   * 桌面端走 Rust `judge` 命令；移动端/浏览器走局域网 HTTP。
   * 多测试用例请用 {@link submitCases}，否则 C++/Java 每个用例都会重新编译。
   */
  async submitOne(req: SubmitRequest): Promise<Verdict> {
    if (this.resolveTransport() === 'lan') {
      const vs = await this.judgeOverLan(req.code, req.lang, [req.stdin ?? '']);
      return vs[0] ?? { verdict: 'runtime_error', stderr: '后端未返回判定结果', signal: null };
    }
    return this.call<Verdict>('judge', {
      lang: req.lang,
      code: req.code,
      // Option<String>：显式传 null 比省略更稳（Tauri 参数按 camelCase 对齐）
      stdin: req.stdin ?? null,
    });
  }

  /**
   * 批量判题（自动选通道：桌面 invoke('judge_batch') / 移动端 fetch /api/judge）。
   * C++/Java 首用例编译并 copyOutCached 出 fileId，后续用例复用，只编译一次。
   *
   * @returns 与入参等长、同序的结果数组（含未通过原因）。
   */
  async submitCases(
    code: string,
    language: string,
    testCases: TestCase[] = [],
  ): Promise<TestCaseResult[]> {
    // 一个用例都没给：按「一条空 stdin」跑，至少拿到编译/运行结果
    const cases: TestCase[] = testCases.length > 0 ? testCases : [{}];
    const stdins = cases.map((c) => c.stdin ?? '');

    let verdicts: Verdict[];
    let transport: Transport;
    try {
      transport = this.resolveTransport();
    } catch (e) {
      return this.allCasesFailed(cases, e);
    }

    try {
      verdicts =
        transport === 'lan'
          ? await this.judgeOverLan(code, language, stdins)
          : await this.call<Verdict[]>('judge_batch', { lang: language, code, stdins });
    } catch (e) {
      // invoke 失败但配了局域网地址 → 兜底重试一次。
      // 覆盖的场景：桌面端判题服务异常，或环境判定把 Android APK 误认成桌面。
      if (transport === 'invoke' && this.getLanBaseUrl()) {
        this.log('invoke 失败，尝试局域网兜底');
        try {
          verdicts = await this.judgeOverLan(code, language, stdins);
        } catch (e2) {
          return this.allCasesFailed(cases, e2);
        }
      } else {
        return this.allCasesFailed(cases, e);
      }
    }

    // 防御：Rust 返回条数与请求不一致（理论上 judge_batch 保证等长）
    if (verdicts.length !== cases.length) {
      this.log(`verdict 数量(${verdicts.length}) 与用例数(${cases.length}) 不一致`);
    }

    return cases.map((c, i) => {
      const verdict = verdicts[i] ?? {
        verdict: 'runtime_error' as const,
        stderr: '后端未返回该用例的判定结果',
        signal: null,
      };
      const ui = mapVerdictToUi(verdict);
      const actual =
        verdict.verdict === 'accepted' || verdict.verdict === 'mock' ? verdict.stdout : '';
      const passed = isVerdictPassed(verdict, c.expected);
      return {
        index: i,
        name: c.name ?? `用例 ${i + 1}`,
        verdict,
        ui,
        passed,
        expected: c.expected,
        actual,
        reason: passed
          ? undefined
          : c.expected !== undefined && actual !== '' && verdict.verdict === 'accepted'
            ? '输出与期望不一致'
            : ui.hint,
      };
    });
  }

  /* -------------------- 局域网 HTTP 判题 -------------------- */

  /**
   * 走局域网 HTTP 判题（Rust `POST /api/judge`）。
   * 返回体与 invoke('judge_batch') 完全一致（裸 `Verdict[]`），UI 层共用解析。
   */
  private async judgeOverLan(
    code: string,
    language: string,
    stdins: string[],
  ): Promise<Verdict[]> {
    const base = this.requireLanBaseUrl();
    const body: LanJudgeReq = { lang: language, code, stdins };

    let resp: Response;
    try {
      resp = await fetchWithTimeout(
        `${base}/api/judge`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
        this.lanTimeoutMs,
      );
    } catch (e) {
      throw new JudgeClientError('lan', describeLanFetchError(e, base, this.lanTimeoutMs), e);
    }

    // 先取文本再判状态码：Rust 侧 4xx/5xx 也返回 JSON（{error, hint}），
    // 直接用 resp.json() 会在非 2xx 时丢掉这些信息。
    const text = await resp.text();
    if (!resp.ok) {
      let msg = `电脑端返回 ${resp.status} ${resp.statusText}`;
      try {
        const j = JSON.parse(text) as { error?: string; hint?: string };
        if (j.error) msg = j.error;
        if (j.hint) msg += `（${j.hint}）`;
      } catch {
        if (text) msg += `: ${text.slice(0, 200)}`;
      }
      throw new JudgeClientError('lan', msg);
    }

    try {
      return JSON.parse(text) as Verdict[];
    } catch (e) {
      throw new JudgeClientError('lan', `判定结果解析失败: ${describeError(e)}`, e);
    }
  }

  /** 批量调用整体失败 → 每个用例都标记同一条错误（返回结构稳定，UI 不用判空）。 */
  private allCasesFailed(cases: TestCase[], e: unknown): TestCaseResult[] {
    const err =
      e instanceof JudgeClientError ? e : new JudgeClientError('unknown', describeError(e), e);
    return cases.map((c, i) => ({
      index: i,
      name: c.name ?? `用例 ${i + 1}`,
      verdict: { verdict: 'runtime_error' as const, stderr: err.message, signal: null },
      ui: mapVerdictToUi({ verdict: 'runtime_error', stderr: err.message, signal: null }),
      passed: false,
      expected: c.expected,
      reason: `批量判题调用失败：${err.message}`,
    }));
  }

  /**
   * 便捷入口：一次性拿到「是否全过 + 每条明细」。
   * 自动选通道：桌面 invoke('judge_batch')，移动端/浏览器 fetch /api/judge。
   */
  async submitCode(
    code: string,
    language: string,
    testCases?: TestCase[],
  ): Promise<{ allPassed: boolean; results: TestCaseResult[] }> {
    const results = await this.submitCases(code, language, testCases);
    return { allPassed: results.every((r) => r.passed), results };
  }

  /* -------------------- WebSocket 通道（可取消） -------------------- */

  /**
   * 走 `/ws/run` 判题。相比 invoke，这条路**可以取消**：
   * 关闭 socket 时 Rust 侧会立即强杀正在运行的沙箱（防僵尸进程）。
   *
   * 注意：
   *   1. WS 路径在 Rust 侧走的是单词 `judge()`，多用例仍需 submitCases。
   *   2. WS 服务只听 127.0.0.1 回环，**仅桌面端可用**；
   *      移动端 / 浏览器下调用会直接 reject（请改用 HTTP 通道）。
   */
  runOverWebSocket(req: SubmitRequest): Promise<Verdict> {
    return new Promise<Verdict>((resolve, reject) => {
      if (!hasTauriInternals() || isMobileUa()) {
        reject(
          new JudgeClientError(
            'lan',
            'WebSocket 取消通道仅桌面端可用（只监听 127.0.0.1 回环）；移动端请使用 HTTP 判题。',
          ),
        );
        return;
      }

      let settled = false;
      const fail = (kind: JudgeErrorKind, msg: string) => {
        if (settled) return;
        settled = true;
        this.activeWs = null;
        reject(new JudgeClientError(kind, msg));
      };

      this.getWsUrl()
        .then((url) => {
          const ws = new WebSocket(url);
          this.activeWs = ws;

          ws.onopen = () => {
            const payload: WsJudgeReq = {
              lang: req.lang,
              code: req.code,
              stdin: req.stdin ?? null,
            };
            ws.send(JSON.stringify(payload));
          };

          ws.onmessage = (ev) => {
            if (settled) return;
            settled = true;
            this.activeWs = null;
            try {
              ws.close();
            } catch {
              /* ignore */
            }
            try {
              const verdict = JSON.parse(String(ev.data)) as Verdict;
              resolve(verdict);
            } catch (e) {
              reject(new JudgeClientError('unknown', `判定结果解析失败: ${describeError(e)}`, e));
            }
          };

          ws.onerror = () => fail('transport', 'WebSocket 连接失败（go-judge 服务是否已启动？）');
          ws.onclose = () => fail('cancelled', '连接已关闭：判题被取消或服务端断开');
        })
        .catch((e) => fail('transport', describeError(e)));
    });
  }

  /**
   * 取消当前 WS 判题。Rust 侧检测到客户端断开会强杀沙箱进程树。
   */
  cancelWebSocket(): void {
    const ws = this.activeWs;
    if (ws) {
      this.log('cancel: 关闭 WebSocket，Rust 侧将强杀当前沙箱');
      try {
        ws.close();
      } catch {
        /* ignore */
      }
      this.activeWs = null;
    }
  }
}

/** 默认单例（多数页面一个就够；需要独立配置时自行 new）。 */
export const goJudgeClient = new GoJudgeClient();
