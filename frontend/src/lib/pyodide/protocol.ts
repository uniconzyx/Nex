/**
 * protocol.ts —— 主线程 <-> Pyodide Worker 的消息协议
 * ============================================================================
 * 为什么单独一个文件：
 *   Worker 和主线程两侧都要 import 这些类型，放进 worker.ts 里会让主线程
 *   把整个 worker 模块（含 importScripts 相关逻辑）也拖进打包依赖图，
 *   Vite 会误以为主线程也要加载 pyodide 的 loader 脚本。
 *
 * 协议是「请求-响应 + 主动事件」混合模型：
 *   * 请求-响应：{ id, op } 进 -> { id, type } 出，用 id 配对。
 *   * 主动事件：{ id: null, type: 'progress' }，用于「正在下载解释器」这类进度。
 *
 * ⚠️ 死循环防护的分工（两侧必须配合，缺一不可）：
 *   * Worker 侧：`setInterruptBuffer` + 主线程写 SharedArrayBuffer 的字节 0
 *     -> `KeyboardInterrupt`，能**优雅**中断 Python 循环，用户还能拿到已经
 *     打印出来的部分 stdout。这是主路径。
 *   * 主线程侧：兜底 `worker.terminate()`，覆盖「C 扩展里死循环」这种
 *     Python 层无法响应中断的情况。代价是 Worker 整体销毁，需重建。
 */

/* ============================================================================
 * 运行参数
 * ========================================================================== */

export interface RunLimits {
  /** 单个用例的墙钟上限（毫秒）。Pyodide 比原生慢一个量级，别照搬 OJ 的 1s。 */
  timeoutMs: number;
  /**
   * stdout 截断阈值（字符数）。
   * Pyodide 的 stdout 回调是**全量累积**的，死循环打印会在终止前把
   * 手机内存吃光——必须在第一个字符进来时就限流。
   */
  maxOutputChars: number;
}

export interface LoadOptions {
  /** 解释器资源地址（indexURL），默认 CDN。离线包场景可指向本地 assets 目录。 */
  indexURL?: string;
  /** 要预装的官方包名（如 'micropip'）。用户代码 import 不到时才需要。 */
  packages?: string[];
}

/* ============================================================================
 * Worker -> 主线程
 * ========================================================================== */

export type WorkerOutbound =
  | { id: null; type: 'progress'; stage: 'downloading' | 'initializing' | 'ready'; detail?: string }
  | { id: null; type: 'fatal'; message: string }
  | { id: number; type: 'stdout'; chunk: string }
  /** 解释器已就绪；id 对应 load 请求 */
  | { id: number; type: 'loaded'; version: string }
  /** 单个用例结束 */
  | {
      id: number;
      type: 'done';
      stdout: string;
      stderr: string;
      /** 是否被中断/超时打断（此时 stdout 是「半成品」） */
      interrupted: boolean;
      /** 毫秒 */
      durationMs: number;
      /** 用户代码抛了异常（不是中断） */
      error: { name: string; message: string; traceback: string } | null;
    };

/* ============================================================================
 * 主线程 -> Worker
 * ========================================================================== */

export type WorkerInbound =
  | { id: number; op: 'load'; options: LoadOptions }
  | { id: number; op: 'run'; options: LoadOptions; code: string; stdin: string; limits: RunLimits }
  | { id: number; op: 'interrupt' };

/* ============================================================================
 * 常量
 * ========================================================================== */

/** 与 pyodide 官方 CDN 对齐。升级 SDK 版本时只改这里。 */
export const PYODIDE_VERSION = '0.28.3';
export const DEFAULT_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

/**
 * 判题用默认限额。
 *
 * 为什么 timeout 是 5000ms 而不是 OJ 常见的 1000ms：
 * Pyodide 首次 import 要编译字节码，纯 Python 解释执行大约慢 3~10 倍。
 * 给 5s 既能拦住死循环，又不会冤枉「O(n²) 但 n=1000」的初学者代码。
 */
export const DEFAULT_LIMITS: RunLimits = {
  timeoutMs: 5_000,
  maxOutputChars: 64 * 1024,
};
