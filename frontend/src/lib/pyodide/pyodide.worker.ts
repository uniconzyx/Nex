/**
 * pyodide.worker.ts —— 在 Web Worker 里跑 Pyodide（移动端唯一的代码执行沙箱）
 * ============================================================================
 * 这个文件是「APK 能不能独立判题」的成败点，核心难点有四个，逐条说明：
 *
 * 【1】Worker 里怎么拿到 Pyodide？
 *   Vite 打包时 `import()` 一个来自 node_modules 的 ESM 包，会被 esbuild 预打包。
 *   但 pyodide 的 npm 包**不是普通 JS 库**：它的 `pyodide.mjs` 只负责加载
 *   `pyodide.asm.wasm` + `python_stdlib.zip`，这些大文件必须按原样放行。
 *   所以这里用**动态 import + @vite-ignore**：让打包器别插手，运行时直接从
 *   目标 URL（本地 assets 或 CDN）取。配合外层 `?worker&inline` 的导入方式，
 *   Worker 本体被打成同源 blob，再 import 同源/CDN 的 js，不会被 CORS 卡住。
 *
 * 【2】死循环怎么不卡死 UI？
 *   Worker 天然隔离主线程，UI 不会卡。但 Worker 里的死循环会**永远跑下去**，
 *   所以要有两级中断：
 *     a. SharedArrayBuffer + setInterruptBuffer：主线程写 byte[0]=2，
 *        CPython 在下一个字节码边界抛 KeyboardInterrupt。优雅、可控。
 *     b. worker.terminate()：主线程兜底（见 PyodideSandbox.ts）。
 *   这里负责 a 的一半——把中断缓冲区装到 Pyodide 上，并自己起一个
 *   看门狗计时器，到点就写中断字节。
 *
 * 【3】stdout 怎么拿？
 *   Pyodide 的 `setStdout({ batched })` 是**按行回调**，而且默认会**同时**
 *   打到浏览器控制台（很吵）。这里用 `raw` 回调自己拼接，既省一次字符串
 *   拷贝，又能立刻做长度限流——否则 `while True: print('x')` 会在中断生效前
 *   就把内存吃满。
 *
 * 【4】stdin 怎么喂？
 *   判题用例的输入是整段字符串。`setStdin({ stdin: () => nextLine() })`，
 *   每次 `input()` 取一行；耗尽后返回 null（Python 会得到 EOFError），
 *   这与真实 OJ 的行为一致——**不要**返回空串，否则 `while (l := input())`
 *   会死循环。
 * ============================================================================
 */

import {
  DEFAULT_INDEX_URL,
  type LoadOptions,
  type RunLimits,
  type WorkerInbound,
  type WorkerOutbound,
} from './protocol';

// 只用结构化声明，不引 DedicatedWorkerGlobalScope：
// tsconfig 的 lib 是 ES2020 + DOM，没有 webworker，直接写那个名字会找不到。
declare const self: {
  onmessage: ((ev: MessageEvent) => void) | null;
  postMessage(message: unknown, transfer?: Transferable[]): void;
  addEventListener(type: string, listener: () => void): void;
  importScripts?: (...urls: string[]) => void;
};

/* ----------------------------------------------------------------------------
 * Pyodide 的最小类型面
 * --------------------------------------------------------------------------
 * 不引入 `pyodide` 的 .d.ts 是为了让 tsc 不需要该包被安装（构建机器上
 * 可能没跑 npm i pyodide）。只声明我们真正用到的 API，少写一行注释就得
 * 自己去查文档那种，一律不声明。
 * -------------------------------------------------------------------------- */
interface PyodideAPI {
  version: string;
  runPythonAsync(code: string, options?: { globals?: unknown }): Promise<unknown>;
  setStdout(opts: { raw?: (ch: number) => void; batched?: (s: string) => void }): void;
  setStderr(opts: { raw?: (ch: number) => void; batched?: (s: string) => void }): void;
  setStdin(opts: {
    stdin?: () => string | null;
    autoEOF?: boolean;
  }): void;
  setInterruptBuffer(buffer: Uint8Array | undefined): void;
  loadPackagesFromImports(code: string): Promise<void>;
  globals: { get(name: string): unknown; set(name: string, value: unknown): void };
}

interface PyodideModule {
  loadPyodide(opts: { indexURL?: string; packages?: string[]; stdout?: unknown }): Promise<PyodideAPI>;
}

/* ----------------------------------------------------------------------------
 * 状态
 * -------------------------------------------------------------------------- */
let pyodide: PyodideAPI | null = null;
let loading: Promise<PyodideAPI> | null = null;

/** 共享中断缓冲区；不支持 SharedArrayBuffer 时为 null（降级为纯 terminate）。 */
let interruptBuffer: Uint8Array | null = null;

/** 请求在 PyodideSandbox 里是串行的，stdout 天然归属于正在执行的那一条，
 *  不需要额外的 activeId 来区分归属。 */
/** stdout/stderr 累积缓冲。 */
let outBuf = '';
let errBuf = '';
/** 是否已越过输出上限（越过之后停止累积，只保留前 N 字符）。 */
let outTruncated = false;
/** 看门狗句柄。 */
let watchdog: ReturnType<typeof setTimeout> | null = null;

function post(msg: WorkerOutbound, transfer?: Transferable[]): void {
  if (transfer && transfer.length > 0) self.postMessage(msg, transfer);
  else self.postMessage(msg);
}

/* ----------------------------------------------------------------------------
 * 加载解释器
 * -------------------------------------------------------------------------- */

/**
 * 动态 import pyodide 的 loader。
 *
 * `@vite-ignore` 是必需的：不加的话 Vite 会尝试静态分析这个表达式，
 * 在构建期报 "Failed to resolve import"。加了之后原样保留给运行时。
 *
 * 用 `/* @vite-ignore *\/` 形式而不是字符串拼接，是为了让注释紧贴
 * import 调用——Vite 的匹配规则要求注释就在 import( 前面。
 */
async function importPyodideLoader(indexURL: string): Promise<PyodideModule> {
  // 末尾斜杠必须保留，否则 pyodide 内部拼资源 URL 会得到 .../fullpyodide.asm.wasm
  const base = indexURL.endsWith('/') ? indexURL : `${indexURL}/`;
  return (await import(/* @vite-ignore */ `${base}pyodide.mjs`)) as PyodideModule;
}

async function ensureLoaded(options: LoadOptions): Promise<PyodideAPI> {
  if (pyodide) return pyodide;
  if (loading) return loading;

  const indexURL = options.indexURL ?? DEFAULT_INDEX_URL;

  loading = (async () => {
    post({ id: null, type: 'progress', stage: 'downloading', detail: indexURL });
    const mod = await importPyodideLoader(indexURL);

    post({ id: null, type: 'progress', stage: 'initializing' });

    // SharedArrayBuffer 在非跨源隔离环境不可用（普通 http:// 页面就是这种情况）。
    // 能用就用，用不了也不报错——主线程的 terminate 兜底依然成立。
    if (typeof SharedArrayBuffer !== 'undefined') {
      try {
        interruptBuffer = new Uint8Array(new SharedArrayBuffer(1));
      } catch {
        interruptBuffer = null;
      }
    }

    // ⚠️ packages **必须只在非空时才出现在 options 里**。
    // Pyodide 0.28 的 loadPyodide 会把 options.packages 原样交给 PackageManager，
    // 而 PackageManager 内部对它做 toStringArray(...)，不做 undefined 兜底：
    // 显式传 `packages: undefined` 会抛
    //   TypeError: Cannot read properties of undefined (reading 'toJs')
    // 发生在 initializePackageIndex 里，报错信息完全看不出跟 packages 有关。
    const loadOptions: Record<string, unknown> = { indexURL };
    if (options.packages && options.packages.length) loadOptions.packages = options.packages;
    const api = await mod.loadPyodide(loadOptions);

    // 装中断缓冲区。注意必须在 load 之后调用，load 之前 pyodide 实例还不存在。
    if (interruptBuffer) api.setInterruptBuffer(interruptBuffer);

    pyodide = api;
    post({ id: null, type: 'progress', stage: 'ready', detail: api.version });
    return api;
  })();

  try {
    return await loading;
  } catch (e) {
    // 失败后清空，允许用户重试（比如刚才是断网）
    loading = null;
    pyodide = null;
    throw e;
  }
}

/* ----------------------------------------------------------------------------
 * stdin：把整段输入切成行，逐行喂
 * -------------------------------------------------------------------------- */

function makeStdinFeeder(input: string): () => string | null {
  // 统一换行符；末尾多余的换行不产生空行（否则最后一行会多读一个 ''）
  const normalized = input.replace(/\r\n?/g, '\n').replace(/\n$/, '');
  const lines = normalized === '' ? [] : normalized.split('\n');
  let i = 0;
  return () => (i < lines.length ? (lines[i++] as string) : null);
}

/* ----------------------------------------------------------------------------
 * 一个用例的执行
 * -------------------------------------------------------------------------- */

function resetBuffers(limits: RunLimits): void {
  outBuf = '';
  errBuf = '';
  outTruncated = false;
  void limits;
}

function interrupt(api: PyodideAPI): void {
  if (interruptBuffer) {
    // 2 = KeyboardInterrupt，1 = SIGINT（CPython 内部语义，别改成别的值）
    interruptBuffer[0] = 2;
  } else {
    // 没有共享内存：跳过 loadPackagesFromImports 这个异步点，主线程会 terminate
    void api;
  }
}

async function runOnce(
  api: PyodideAPI,
  id: number,
  code: string,
  stdin: string,
  limits: RunLimits,
): Promise<void> {
  const started = Date.now();
  resetBuffers(limits);

  const stdoutLimit = limits.maxOutputChars;
  const pushOut = (s: string) => {
    if (s === '') return;
    if (outTruncated) return;
    const room = stdoutLimit - outBuf.length;
    if (s.length >= room) {
      outBuf += s.slice(0, room);
      outTruncated = true;
      post({ id, type: 'stdout', chunk: s.slice(0, room) });
      return;
    }
    outBuf += s;
    post({ id, type: 'stdout', chunk: s });
  };

  // ⚠️ raw 回调给的是**字节**，不是字符。
  // Python 的 stdout 是 UTF-8 字节流，中文一个字 3 个字节、会被拆成 3 次回调。
  // 用 String.fromCharCode 逐字节转字符 = 把 UTF-8 当 latin-1 解释，中文必乱码
  // （曾表现为报告里「最终 w」变成「æç» w」）。
  // TextDecoder 的 stream:true 会缓存跨调用的半个字符，是逐字节场景的正确解法。
  const outDecoder = new TextDecoder('utf-8');
  const errDecoder = new TextDecoder('utf-8');
  api.setStdout({
    raw: (ch: number) => {
      const s = outDecoder.decode(new Uint8Array([ch]), { stream: true });
      if (s) pushOut(s);
    },
  });
  api.setStderr({
    raw: (ch: number) => {
      const s = errDecoder.decode(new Uint8Array([ch]), { stream: true });
      if (!s) return;
      if (errBuf.length >= stdoutLimit) return;
      errBuf += s;
    },
  });
  api.setStdin({ stdin: makeStdinFeeder(stdin), autoEOF: true });

  // 看门狗：到点写中断字节。用 setTimeout 而不是轮询 CPU 时间，
  // 因为这里拦的是「墙钟太久」而不是「算得太多」。
  watchdog = setTimeout(() => interrupt(api), limits.timeoutMs);

  let interrupted = false;
  let error: { name: string; message: string; traceback: string } | null = null;

  try {
    // 顶层代码可能 import 三方包。先扫一遍 import 语句按需安装，
    // 否则 `import numpy` 会抛 ModuleNotFoundError。失败不致命——用户可能
    // 只是 import 了一个不存在的东西，让后面的 runPythonAsync 抛真实错误。
    try {
      await api.loadPackagesFromImports(code);
    } catch {
      /* 交给下面的 runPythonAsync 给出更准确的报错 */
    }

    // 用 runPythonAsync 而不是 runPython：需要 await 用户代码里的顶层 await
    // （少数题会用到），同时它会把异常转成 JS 侧 reject，便于统一捕获。
    await api.runPythonAsync(code);
  } catch (e) {
    const kind = classifyPyError(e);
    if (kind === 'interrupt') {
      interrupted = true;
      // 只清掉「KeyboardInterrupt」那两行噪声，保留用户自己打印的内容
      error = null;
    } else {
      error = describePyError(e);
    }
  } finally {
    if (watchdog !== null) {
      clearTimeout(watchdog);
      watchdog = null;
    }
    // 复位中断字节，否则下一次 run 一进入就被打断
    if (interruptBuffer) interruptBuffer[0] = 0;
  }

  post({
    id,
    type: 'done',
    stdout: outBuf,
    stderr: errBuf,
    interrupted,
    durationMs: Date.now() - started,
    error,
  });
}

/* ----------------------------------------------------------------------------
 * 错误归一化
 * --------------------------------------------------------------------------
 * pyodide 抛的异常有三种形态：
 *   1. PythonError —— Python 层异常，message 里带 traceback，name 是类名
 *   2. 字符串 —— KeyboardInterrupt 有时以字符串形式抛出
 *   3. JS Error —— 加载失败 / OOM
 * 全部收敛成同一种结构，主线程就不用写三个分支。
 * -------------------------------------------------------------------------- */

function classifyPyError(e: unknown): 'interrupt' | 'python' | 'js' {
  const text = typeof e === 'string' ? e : e instanceof Error ? e.message : '';
  if (/KeyboardInterrupt/.test(text)) return 'interrupt';
  if (e && typeof e === 'object' && 'type' in (e as Record<string, unknown>)) return 'python';
  return text.includes('PythonError') ? 'python' : 'js';
}

function describePyError(e: unknown): { name: string; message: string; traceback: string } {
  if (typeof e === 'string') {
    return { name: 'Error', message: e, traceback: e };
  }
  const anyE = e as { name?: string; message?: string; type?: string; stack?: string };
  const traceback = anyE.message ?? anyE.stack ?? String(e);
  // PythonError 的 message 是「完整 traceback」，最后一行才是 "ValueError: ..."
  const lastLine = traceback.trim().split('\n').pop() ?? '';
  const m = /^(\w+(?:Error|Exception|Interrupt)):\s*(.*)$/.exec(lastLine);
  return {
    name: anyE.type ?? m?.[1] ?? anyE.name ?? 'Error',
    message: m?.[2] ?? lastLine,
    traceback,
  };
}

/* ----------------------------------------------------------------------------
 * 消息路由
 * -------------------------------------------------------------------------- */

self.onmessage = async (ev: MessageEvent<WorkerInbound>) => {
  const msg = ev.data;

  if (msg.op === 'load') {
    try {
      const api = await ensureLoaded(msg.options);
      post({ id: msg.id, type: 'loaded', version: api.version });
    } catch (e) {
      const detail = e instanceof Error ? e.message : String(e);
      post({ id: null, type: 'fatal', message: `Pyodide 加载失败：${detail}` });
    }
    return;
  }

  if (msg.op === 'interrupt') {
    if (pyodide) interrupt(pyodide);
    return;
  }

  if (msg.op === 'run') {
    try {
      // ⚠️ 必须把 options 一起传下来：Worker 是独立上下文，主线程那边
      // ensureLoaded() 成功后只是主线程的状态，Worker 里 pyodide 仍为 null。
      // 漏传会让首次 run 走默认 CDN，离线包场景直接 404。
      const api = await ensureLoaded(msg.options);
      await runOnce(api, msg.id, msg.code, msg.stdin, msg.limits);
    } catch (e) {
      // 加载失败 / 执行框架异常：也要回一条 done，否则主线程会一直等到超时
      post({
        id: msg.id,
        type: 'done',
        stdout: outBuf,
        stderr:
          errBuf ||
          (e instanceof Error ? e.message : String(e)),
        interrupted: false,
        durationMs: 0,
        error: {
          name: 'WorkerError',
          message: e instanceof Error ? e.message : String(e),
          traceback: e instanceof Error ? (e.stack ?? e.message) : String(e),
        },
      });
    }
    return;
  }
};

/** 让 Worker 在被 terminate 前有机会清理（目前只是复位中断字，占位以保持显式）。 */
self.addEventListener('close', () => {
  if (interruptBuffer) interruptBuffer[0] = 0;
});
