/**
 * PyodideSandbox.ts —— 主线程侧 Pyodide 控制器
 * ============================================================================
 * 职责边界（和 worker.ts 严格分工）：
 *   * worker.ts   管「怎么在沙箱内跑 Python」
 *   * 本文件      管「什么时候创建/销毁 Worker、请求怎么配对、超时怎么兜底」
 *
 * 四个设计要点：
 *
 * 【1】懒加载 + 单例
 *   Pyodide 首次加载要拉 ~10MB（wasm + stdlib），绝不能进首屏 bundle。
 *   第一次点「运行」才启动，加载期间用 progress 回调驱动 UI 进度条。
 *
 * 【2】不终止就无法回收的死循环
 *   超时后先礼貌中断（写 SharedArrayBuffer），再等一个宽限期；
 *   宽限期到了还没回 done，就 `terminate()` 整个 Worker 并重建。
 *   重建是必要的——被强杀的 Worker 内部状态（含 pyodide 实例）已经不可信。
 *
 * 【3】请求串行化
 *   Pyodide 是单线程解释器，stdout 回调靠「当前活动 id」归属。
 *   两个 run 并发会互相污染输出。所以内部维护一条队列，一次只跑一个。
 *
 * 【4】Worker 创建用 `?worker` 后缀
 *   Vite 把它单独打成一个 chunk，主线程只拿 Worker 构造函数。
 *   `new Worker(new URL(...), { type: 'module' })` 的写法在某些 Android
 *   WebView 上不支持 module worker，用 Vite 的 `?worker` 更稳。
 * ============================================================================
 */

import PyodideWorkerCtor from './pyodide.worker?worker';
import {
  DEFAULT_LIMITS,
  type LoadOptions,
  type RunLimits,
  type WorkerInbound,
  type WorkerOutbound,
} from './protocol';

/* ============================================================================
 * 对外类型
 * ========================================================================== */

export interface PyRunResult {
  stdout: string;
  stderr: string;
  /** 被中断（超时或用户取消）；此时 stdout 是半成品，判定为 TLE */
  interrupted: boolean;
  /** 是否因超时被强杀（比 interrupted 更严重：Worker 已重建） */
  killed: boolean;
  durationMs: number;
  /** 用户代码抛的 Python 异常；null 表示正常跑完 */
  error: { name: string; message: string; traceback: string } | null;
}

export interface SandboxProgress {
  stage: 'downloading' | 'initializing' | 'ready';
  detail?: string;
}

export interface PyodideSandboxOptions extends LoadOptions {
  /** 超时后先礼貌中断，等这么久还没回音就强杀 Worker。默认 1200ms。 */
  gracePeriodMs?: number;
  onProgress?: (p: SandboxProgress) => void;
}

/** 主线程等待单次请求的绝对上限 = 用例超时 + 宽限期 + 这份缓冲。 */
const RESPONSE_BUFFER_MS = 3_000;

/**
 * WorkerInbound 是联合类型，直接 `Omit<WorkerInbound, 'id'>` 会把联合塌缩成
 * 「所有成员共有键」的单一对象 —— 于是 `op:'run'` 里的 code/stdin/limits
 * 全部报「不存在于该类型」。分发式 Omit 才对每个分支各去掉一次 id。
 */
type DistributiveOmit<T, K extends keyof T> = T extends unknown ? Omit<T, K> : never;

/* ============================================================================
 * 控制器
 * ========================================================================== */

export class PyodideSandbox {
  private worker: Worker | null = null;
  private seq = 0;
  /** 进行中的请求：id -> 结算函数。 */
  private pending = new Map<
    number,
    {
      resolve: (v: unknown) => void;
      reject: (e: unknown) => void;
      /** stdout 流式回调（UI 想边跑边显示时用） */
      onChunk?: (s: string) => void;
    }
  >();
  /** 请求串行队列的尾巴。 */
  private queue: Promise<unknown> = Promise.resolve();
  private loaded = false;
  private loadingPromise: Promise<string> | null = null;
  /** Worker 崩过一次就记下来，UI 可以提示「已重置」 */
  private restarts = 0;

  private readonly indexURL?: string;
  private readonly packages?: string[];
  private readonly gracePeriodMs: number;
  private readonly onProgress?: (p: SandboxProgress) => void;

  constructor(opts: PyodideSandboxOptions = {}) {
    this.indexURL = opts.indexURL;
    this.packages = opts.packages;
    this.gracePeriodMs = opts.gracePeriodMs ?? 1_200;
    this.onProgress = opts.onProgress;
  }

  private loadOptions(): LoadOptions {
    return { indexURL: this.indexURL, packages: this.packages };
  }

  /* -------------------- Worker 生命周期 -------------------- */

  private spawn(): Worker {
    const w = new PyodideWorkerCtor({ name: 'nex-pyodide' });
    w.onmessage = (ev: MessageEvent<WorkerOutbound>) => this.dispatch(ev.data);
    w.onerror = (ev: ErrorEvent) => {
      // Worker 顶层未捕获异常：该实例已不可用，全部请求按失败结算
      this.failAll(new Error(ev.message || 'Pyodide Worker 崩溃'));
      this.destroy(false);
    };
    return w;
  }

  private ensureWorker(): Worker {
    if (!this.worker) this.worker = this.spawn();
    return this.worker;
  }

  /**
   * 销毁 Worker。`resetLoaded=true` 表示下次要重新加载解释器
   * （terminate 之后内部 pyodide 实例肯定没了，必须重载）。
   */
  private destroy(resetLoaded = true): void {
    if (this.worker) {
      try {
        this.worker.terminate();
      } catch {
        /* ignore */
      }
      this.worker = null;
    }
    if (resetLoaded) {
      this.loaded = false;
      this.loadingPromise = null;
    }
  }

  private failAll(err: unknown): void {
    for (const [, p] of this.pending) p.reject(err);
    this.pending.clear();
  }

  /* -------------------- 消息分发 -------------------- */

  private dispatch(msg: WorkerOutbound): void {
    // 主动事件（无 id）
    if (msg.id === null) {
      if (msg.type === 'progress') {
        if (msg.stage === 'ready') this.loaded = true;
        this.onProgress?.({ stage: msg.stage, detail: msg.detail });
      } else if (msg.type === 'fatal') {
        this.loaded = false;
        this.loadingPromise = null;
        this.failAll(new Error(msg.message));
      }
      return;
    }

    const p = this.pending.get(msg.id);
    if (!p) return; // 已超时结算，迟到的消息直接丢

    if (msg.type === 'stdout') {
      p.onChunk?.(msg.chunk);
      return;
    }
    if (msg.type === 'loaded') {
      this.pending.delete(msg.id);
      this.loaded = true;
      p.resolve(msg.version);
      return;
    }
    if (msg.type === 'done') {
      this.pending.delete(msg.id);
      p.resolve({
        stdout: msg.stdout,
        stderr: msg.stderr,
        interrupted: msg.interrupted,
        killed: false,
        durationMs: msg.durationMs,
        error: msg.error,
      } satisfies PyRunResult);
    }
  }

  /**
   * 发一条请求并等回复。
   *
   * @param timeoutMs   绝对等待上限
   * @param onChunk     stdout 流式回调
   * @param onTimeout   超时回调。**返回值会直接作为本次请求的结果 resolve**
   *                    （而不是 reject）——这样「超时」在业务层是一条正常的
   *                    verdict，不会被当成异常往上抛。
   *                    返回 undefined 则按 reject 处理。
   */
  private request<T>(
    payload: DistributiveOmit<WorkerInbound, 'id'>,
    timeoutMs: number,
    onChunk?: (s: string) => void,
    onTimeout?: (id: number) => T | undefined,
  ): Promise<T> {
    const id = ++this.seq;
    const w = this.ensureWorker();

    return new Promise<T>((resolve, reject) => {
      let settled = false;
      const finish = (fn: () => void) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        this.pending.delete(id);
        fn();
      };

      const timer = setTimeout(() => {
        finish(() => {
          const synthetic = onTimeout?.(id);
          if (synthetic !== undefined) resolve(synthetic);
          else reject(new Error(`请求超时（${timeoutMs}ms 未收到 Worker 响应）`));
        });
      }, timeoutMs);

      this.pending.set(id, {
        resolve: (v) => finish(() => resolve(v as T)),
        reject: (e) => finish(() => reject(e)),
        onChunk,
      });

      w.postMessage({ ...payload, id } as WorkerInbound);
    });
  }

  /* -------------------- 加载 -------------------- */

  /**
   * 确保解释器就绪。可重复调用，内部去重。
   * @returns Pyodide 版本号
   */
  load(): Promise<string> {
    if (this.loaded) return Promise.resolve('ready');
    if (this.loadingPromise) return this.loadingPromise;

    // 加载可能长达数十秒（弱网 + 10MB），上限给足 180s
    this.loadingPromise = this.request<string>(
      { op: 'load', options: this.loadOptions() },
      180_000,
    )
      .then((v) => {
        this.loaded = true;
        return v;
      })
      .catch((e) => {
        this.loadingPromise = null;
        this.loaded = false;
        throw e;
      });

    return this.loadingPromise;
  }

  /** 是否已就绪（不触发加载）。 */
  get isReady(): boolean {
    return this.loaded;
  }

  /** 已发生的强制重建次数（UI 可用于提示「沙箱已重置」）。 */
  get restartCount(): number {
    return this.restarts;
  }

  /* -------------------- 执行 -------------------- */

  /**
   * 跑一段 Python，拿回 stdout。
   *
   * 串行化：内部用 `queue` 串起来，避免两个用例同时占着解释器和 stdout 回调。
   *
   * 超时分两级（两级都要有，缺一不可）：
   *   1. **Worker 内部看门狗**（worker.ts 的 setTimeout）：到点写中断字节，
   *      CPython 在字节码边界抛 KeyboardInterrupt -> 正常回 done(interrupted)。
   *      这是主路径，用户还能拿到已经打印的内容。
   *   2. **主线程兜底**：如果 C 扩展里死循环，Python 层根本不响应中断，
   *      done 永远不会来。这里在 `timeout + grace` 处 terminate + 重建。
   *      terminate 后 pending 里的请求会悬空，必须手动结算成 killed。
   */
  async run(
    code: string,
    stdin = '',
    limits: Partial<RunLimits> = {},
    onChunk?: (s: string) => void,
  ): Promise<PyRunResult> {
    const lim: RunLimits = { ...DEFAULT_LIMITS, ...limits };

    const task = async (): Promise<PyRunResult> => {
      await this.load();

      return this.request<PyRunResult>(
        { op: 'run', options: this.loadOptions(), code, stdin, limits: lim },
        lim.timeoutMs + this.gracePeriodMs + RESPONSE_BUFFER_MS,
        onChunk,
        // 绝对上限到了：Worker 大概率卡死（C 扩展内部死循环，Python 层
        // 收不到中断）。重建它，并把「这一条」直接结算成 killed 结果。
        () => {
          this.destroy(true);
          this.restarts += 1;
          return {
            stdout: '',
            stderr: '执行超时：沙箱已强制重启（可能是 C 扩展内的死循环）',
            interrupted: true,
            killed: true,
            durationMs: lim.timeoutMs + this.gracePeriodMs,
            error: null,
          };
        },
      );
    };

    // 队列：前一个失败不阻塞后一个
    const run = this.queue.then(task, task);
    this.queue = run.catch(() => undefined);
    return run;
  }

  /**
   * 主动中断当前执行。
   * 先礼貌中断；宽限期后仍无响应则强杀重建（由调用方在超时逻辑里触发）。
   */
  interrupt(): void {
    if (!this.worker) return;
    this.worker.postMessage({ op: 'interrupt', id: ++this.seq } as WorkerInbound);
  }

  /** 彻底释放（页面卸载 / 切走判题页时调用）。 */
  dispose(): void {
    this.failAll(new Error('沙箱已释放'));
    this.destroy(true);
  }
}

/**
 * 判题专用的全局单例。
 *
 * 为什么是模块级单例：Pyodide 实例不能有多个——每多一个就多占 ~80MB
 * WASM 内存，手机上直接 OOM。整个 App 共用同一份解释器。
 */
export const pyodideSandbox = new PyodideSandbox();
