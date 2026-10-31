/**
 * JudgeEngine.ts —— 双端分流判题引擎（方案 1：纯本地、零配置）
 * ============================================================================
 * 这是 UI 层唯一该 import 的判题入口。它不关心「代码在哪跑」，只回答：
 *   这段代码 + 这些用例 -> 每条用例的 Verdict 是什么。
 *
 * 分流表（按运行环境自动选，UI 无感）：
 *
 *   ┌──────────────────┬──────────┬──────────────────────────────────────┐
 *   │ 环境             │ 通道     │ 支持的语言                            │
 *   ├──────────────────┼──────────┼──────────────────────────────────────┤
 *   │ Windows/macOS    │ invoke   │ Python / C++ / C / Java（go-judge）  │
 *   │ 桌面 Tauri       │          │                                      │
 *   │ Android APK      │ pyodide  │ Python（WebAssembly 本地沙箱）        │
 *   │                  │          │ C++/Java -> 友好拦截，不假装能跑      │
 *   │ 纯浏览器预览     │ pyodide  │ 同 Android（便于开发期调试）          │
 *   └──────────────────┴──────────┴──────────────────────────────────────┘
 *
 * ⚠️ 三个必须踩准的坑：
 *
 * 【1】Android APK 也是 Tauri 应用，`__TAURI_INTERNALS__` 一样存在。
 *     只凭它判断「桌面」会让手机上走 invoke，Rust 侧找不到 go-judge 就在
 *     **手机无隔离地本地直跑**用户代码。判据必须是 internals 存在 **且** UA 非移动端。
 *
 * 【2】移动端不能"自动降级到局域网"。方案 1 要求彻底脱网，所以移动端
 *     的默认路径只有 Pyodide；局域网通道保留但必须用户显式开启（mode='lan'），
 *     供「手机想跑 C++ 时临时借用电脑算力」这种边缘场景。
 *
 * 【3】Verdict 是**跨端共用契约**。Pyodide 侧独立构造出与 Rust 完全同构的
 *     `Verdict`，这样 JudgePanel 的结果渲染、AI 上下文、进度落库全都不用分叉。
 *     Pyodide 没有内存统计，`memory_kb` 填 0——这是有意的，不是遗漏。
 * ============================================================================
 */

import {
  GoJudgeClient,
  JudgeClientError,
  mapVerdictToUi,
  normalizeOutput,
  type EnvReport,
  type JudgeStatus,
  type TestCase,
  type TestCaseResult,
  type Transport,
  type TransportMode,
  type Verdict,
} from './GoJudgeClient';
import { PyodideSandbox, type PyRunResult, type SandboxProgress } from './pyodide/PyodideSandbox';
import { DEFAULT_LIMITS, type RunLimits } from './pyodide/protocol';

/* ============================================================================
 * 1. 环境探测
 * ========================================================================== */

export type Runtime = 'desktop' | 'android' | 'web';

function hasTauriInternals(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

function isMobileUa(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent);
}

/**
 * 当前运行环境。
 *
 * `web` = 纯浏览器（vite dev / 预览页）：既没有 Tauri，也不是 APK。
 * 它走 Pyodide，纯粹是为了让开发机浏览器也能验证移动端链路。
 */
export function detectRuntime(): Runtime {
  if (!hasTauriInternals()) return 'web';
  return isMobileUa() ? 'android' : 'desktop';
}

export const RUNTIME: Runtime = detectRuntime();

/* ============================================================================
 * 2. 语言能力表
 * ========================================================================== */

/** 归一化后的语言标识。C 必须是独立一档，不能并进 cpp——详见 normalizeLang。 */
export type NormLang = 'python' | 'cpp' | 'c' | 'java';

/**
 * 语言归一化。
 *
 * ⚠️ **C 与 C++ 必须分开**，这不是洁癖：
 *   * C 里 `int *p = malloc(sizeof(int));` 合法，C++ 里必须强转；
 *   * C99 的变长数组 `int a[n]` 在 C++ 里不合法；
 *   * `void f()` 在 C 里表示「参数未指定」，在 C++ 里表示「无参」。
 *   如果把学生的 C 代码丢进 g++，会冒出一堆莫名其妙的编译错误，
 *   而学生写的是对的语言。所以 clang 学科的题一律按 C 编译。
 */
export function normalizeLang(lang: string): NormLang {
  const l = lang.toLowerCase().trim();
  if (l === 'python' || l === 'py' || l === 'python3') return 'python';
  if (l === 'cpp' || l === 'c++' || l === 'cxx' || l === 'cc') return 'cpp';
  if (l === 'c' || l === 'c99' || l === 'c11' || l === 'c17' || l === 'gnu-c') return 'c';
  if (l === 'java') return 'java';
  // 未知语言不做猜测：交给后端报错，比默默当成 python 更好排查
  return 'python';
}

export type JudgeChannel = 'invoke' | 'pyodide' | 'lan';

/** 某种语言在当前环境下能不能跑，以及不能跑时给用户看的话。 */
export interface LangCapability {
  supported: boolean;
  channel: JudgeChannel | null;
  /** 不支持时的完整提示文案（直接渲染，不要再拼字符串） */
  reason?: string;
}

/** 移动端拦截文案（主人指定的口径，改这里即可全局生效）。 */
export const MOBILE_UNSUPPORTED_REASON =
  '移动端暂不支持该语言本地运行，请前往 Windows 桌面端体验全功能沙箱判题';

/**
 * 浏览器预览模式的拦截文案。
 *
 * 单独一条的理由：`npm run dev` / `vite preview` 下 RUNTIME 是 'web'，
 * 既没有 go-judge 也没有 invoke，但它**不是手机**。直接复用移动端文案，
 * 在电脑浏览器里会看到「移动端暂不支持」，排查问题时极易误判。
 */
export const WEB_UNSUPPORTED_REASON =
  '浏览器预览模式没有本地编译器，请使用桌面端 exe 体验全功能判题';

const LANG_LABEL: Record<NormLang, string> = {
  python: 'Python',
  c: 'C',
  cpp: 'C++',
  java: 'Java',
};

export interface CapabilityOptions {
  /**
   * 用户是否在设置里开启了局域网通道。
   * 方案 1 默认关闭——移动端不依赖任何网络。
   */
  lanEnabled?: boolean;
}

/**
 * 判定「当前环境 + 这个语言」能不能跑。
 *
 * 注意返回值里的 `reason` 包含完整句子，UI 直接 <p>{reason}</p> 即可。
 * 不要指望 UI 自己拼接语言名——那样三个页面就有三份文案，迟早不一致。
 */
export function capabilityOf(
  lang: string,
  runtime: Runtime = RUNTIME,
  opts: CapabilityOptions = {},
): LangCapability {
  const norm = normalizeLang(lang);

  if (runtime === 'desktop') {
    return { supported: true, channel: 'invoke' };
  }

  // 移动端 / 浏览器
  if (norm === 'python') {
    return { supported: true, channel: 'pyodide' };
  }

  if (opts.lanEnabled) {
    // 边缘场景：手机直连电脑判题（需要同一 Wi-Fi，方案 1 下默认关闭）
    return { supported: true, channel: 'lan' };
  }

  return {
    supported: false,
    channel: null,
    reason: `${LANG_LABEL[norm]} ${
      runtime === 'web' ? WEB_UNSUPPORTED_REASON : MOBILE_UNSUPPORTED_REASON
    }`,
  };
}

/** 当前环境支持的语言列表（给 UI 标灰用）。 */
export function supportedLanguages(runtime: Runtime = RUNTIME, opts: CapabilityOptions = {}) {
  const all: NormLang[] = ['python', 'c', 'cpp', 'java'];
  return all.map((l) => ({
    lang: l,
    label: LANG_LABEL[l],
    ...capabilityOf(l, runtime, opts),
  }));
}

/* ============================================================================
 * 3. PyRunResult -> Verdict
 * ========================================================================== */

/**
 * 把 Pyodide 的执行结果翻译成与 Rust 侧同构的 Verdict。
 *
 * 映射规则（与 go-judge 的语义对齐）：
 *   * 被中断/强杀          -> time_limit_exceeded
 *   * 有异常              -> runtime_error（stderr 放 name: message）
 *   * 正常退出            -> accepted（stdout 交给上层做归一化比对）
 *
 * 这里**不做**用例内容比对。「跑通了但答案错」在 OJ 里叫 Wrong Answer，
 * 但 Rust 侧的 Verdict 本来就没有 wrong_answer 这个变体——
 * 它返回的是 accepted + stdout，由前端比对出对错。保持一致。
 */
export function pyResultToVerdict(r: PyRunResult): Verdict {
  if (r.interrupted || r.killed) {
    return { verdict: 'time_limit_exceeded' };
  }
  if (r.error) {
    return {
      verdict: 'runtime_error',
      // traceback 完整保留：初学者最需要的就是最后几行行号
      stderr: r.error.traceback || `${r.error.name}: ${r.error.message}`,
      signal: null,
    };
  }
  return {
    verdict: 'accepted',
    stdout: r.stdout,
    time_ms: r.durationMs,
    // Pyodide 跑在 wasm 线性内存里，拿不到真实 RSS。
    // 填 0 而不是编一个数字：UI 会判断 0 就不显示内存那一栏。
    memory_kb: 0,
  };
}

/* ============================================================================
 * 4. JudgeEngine
 * ========================================================================== */

export interface JudgeEngineOptions {
  /** 强制通道（调试 / 设置页用）；不传则按环境自动判定 */
  forceChannel?: JudgeChannel;
  /** Pyodide 资源地址（离线包指向 local assets，默认走 CDN） */
  pyodideIndexURL?: string;
  /** 移动端单用例超时（毫秒） */
  timeoutMs?: number;
  /** Pyodide 加载进度回调 */
  onSandboxProgress?: (p: SandboxProgress) => void;
  /** 诊断日志 */
  onLog?: (msg: string) => void;
}

export class JudgeEngine {
  private readonly judge: GoJudgeClient;
  private readonly sandbox: PyodideSandbox;
  private readonly forceChannel?: JudgeChannel;
  private readonly log: (m: string) => void;
  private readonly timeoutMs: number;

  constructor(opts: JudgeEngineOptions = {}) {
    this.forceChannel = opts.forceChannel;
    this.log = opts.onLog ?? ((m) => console.log('[JudgeEngine]', m));
    this.timeoutMs = opts.timeoutMs ?? DEFAULT_LIMITS.timeoutMs;

    this.judge = new GoJudgeClient({ onLog: this.log });
    this.sandbox = new PyodideSandbox({
      indexURL: opts.pyodideIndexURL,
      onProgress: opts.onSandboxProgress,
    });
  }

  /** 当前会自动使用的通道。 */
  get channel(): JudgeChannel {
    if (this.forceChannel) return this.forceChannel;
    return RUNTIME === 'desktop' ? 'invoke' : 'pyodide';
  }

  /** 环境探测：桌面查编译器；移动端只报告 Pyodide 状态（无需任何外部依赖）。 */
  async checkEnvironment(): Promise<EnvReport> {
    if (this.channel === 'invoke') return this.judge.checkEnvironment();

    // 移动端：不依赖 go-judge / g++ / java，环境永远是"就绪"的。
    // 但 Pyodide 解释器是懒加载的，这里不主动拉 10MB——只报状态。
    return {
      languages: [{ name: 'Python (Pyodide/WASM)', available: true, path: 'wasm', version: null }],
      go_judge: false,
      go_judge_path: null,
    };
  }

  /** 桌面端运行时状态；移动端返回一份合成值，UI 不用判空。 */
  async getStatus(): Promise<JudgeStatus> {
    if (this.channel === 'invoke') return this.judge.getStatus();
    return {
      go_judge_available: false,
      // 移动端不需要 mock：Pyodide 就是真执行，只是语言受限
      mock_mode: false,
      port: 0,
      pid: 0,
      enable_network: false,
    };
  }

  /** 预加载 Pyodide（用户切到 Python 时后台偷偷拉，点运行就不用等）。 */
  warmUp(): void {
    if (this.channel !== 'pyodide') return;
    void this.sandbox.load().catch((e) => this.log(`预热失败：${describe(e)}`));
  }

  /** Pyodide 是否已就绪。 */
  get sandboxReady(): boolean {
    return this.sandbox.isReady;
  }

  /**
   * 批量判题 —— UI 层唯一入口。
   *
   * 与 GoJudgeClient.submitCases 的返回结构完全相同，可以互换。
   * 移动端拦截发生在**这里**而不是 UI：即使别的页面忘了判断，
   * 也不会出现"按钮能点但跑不了"的尴尬。
   */
  async submitCases(
    code: string,
    language: string,
    testCases: TestCase[] = [],
  ): Promise<TestCaseResult[]> {
    const cases: TestCase[] = testCases.length > 0 ? testCases : [{}];
    const cap = capabilityOf(language, RUNTIME, {
      lanEnabled: this.forceChannel === 'lan',
    });

    // 强制通道优先于环境能力（调试用）
    const channel = this.forceChannel ?? cap.channel;

    if (!channel) {
      return this.allFailed(cases, cap.reason ?? MOBILE_UNSUPPORTED_REASON);
    }

    if (channel === 'invoke' || channel === 'lan') {
      return this.judge.submitCases(code, language, cases);
    }

    return this.runOnPyodide(code, cases);
  }

  /** 便捷入口：是否全过 + 明细。 */
  async submitCode(
    code: string,
    language: string,
    testCases?: TestCase[],
  ): Promise<{ allPassed: boolean; results: TestCaseResult[] }> {
    const results = await this.submitCases(code, language, testCases);
    return { allPassed: results.every((r) => r.passed), results };
  }

  /* -------------------- Pyodide 通道 -------------------- */

  /**
   * 逐个用例在 WASM 沙箱里跑。
   *
   * 为什么串行而不是 Promise.all：
   *   Pyodide 只有一个解释器实例，stdout 回调全局共享。
   *   并行会让用例 A 的输出串到用例 B 里。串行还额外带来一个好处——
   *   某条用例超时被 kill 后，后面的用例会自动在新 Worker 上重跑。
   */
  private async runOnPyodide(code: string, cases: TestCase[]): Promise<TestCaseResult[]> {
    const limits: RunLimits = { ...DEFAULT_LIMITS, timeoutMs: this.timeoutMs };
    const results: TestCaseResult[] = [];

    for (let i = 0; i < cases.length; i += 1) {
      const c = cases[i] as TestCase;
      const name = c.name ?? `用例 ${i + 1}`;

      let py: PyRunResult;
      try {
        py = await this.sandbox.run(code, c.stdin ?? '', limits);
      } catch (e) {
        // 沙箱整体挂了（加载失败 / OOM）——后面的用例不用再试了
        const msg = describe(e);
        this.log(`Pyodide 执行失败：${msg}`);
        for (let j = i; j < cases.length; j += 1) {
          const cj = cases[j] as TestCase;
          results.push(this.failOne(j, cj.name ?? `用例 ${j + 1}`, msg, cj.expected));
        }
        break;
      }

      results.push(this.toCaseResult(i, name, c, py));
    }

    return results;
  }

  /** 单条 Pyodide 结果 -> TestCaseResult（比对逻辑复用的 OJ 归一化）。 */
  private toCaseResult(
    index: number,
    name: string,
    c: TestCase,
    py: PyRunResult,
  ): TestCaseResult {
    const verdict = pyResultToVerdict(py);
    const ui = mapVerdictToUi(verdict);
    const actual = verdict.verdict === 'accepted' ? verdict.stdout : '';

    // 「跑通了」与「答对了」是两件事：
    //   passed 只有 accepted 且输出比对一致才为 true。
    //   没有 expected 时视为「只要求能跑通」，与 GoJudgeClient 保持一致。
    const passed =
      verdict.verdict === 'accepted' &&
      (c.expected === undefined || normalizeOutput(actual) === normalizeOutput(c.expected));

    let reason: string | undefined;
    if (!passed) {
      if (py.killed) {
        reason = '执行超时，沙箱已重启';
      } else if (py.interrupted) {
        reason = `超出 ${this.timeoutMs} ms 时限`;
      } else if (verdict.verdict === 'runtime_error') {
        reason = py.error ? `${py.error.name}: ${py.error.message}` : '运行时异常';
      } else if (c.expected !== undefined) {
        reason = '输出与期望不一致';
      } else {
        reason = ui.hint;
      }
    }

    return {
      index,
      name,
      verdict,
      ui,
      passed,
      expected: c.expected,
      actual,
      reason,
    };
  }

  private failOne(
    index: number,
    name: string,
    message: string,
    expected?: string,
  ): TestCaseResult {
    const verdict: Verdict = { verdict: 'runtime_error', stderr: message, signal: null };
    return {
      index,
      name,
      verdict,
      ui: mapVerdictToUi(verdict),
      passed: false,
      expected,
      reason: message,
    };
  }

  /** 整批在"进沙箱之前"就失败（例如移动端选了 C++）。 */
  private allFailed(cases: TestCase[], message: string): TestCaseResult[] {
    return cases.map((c, i) => this.failOne(i, c.name ?? `用例 ${i + 1}`, message, c.expected));
  }

  /* -------------------- 透传 -------------------- */

  /** 设置局域网地址（边缘场景：手机临时借用电脑算力）。 */
  setLanBaseUrl(url: string): void {
    this.judge.setLanBaseUrl(url);
  }

  getLanBaseUrl(): string {
    return this.judge.getLanBaseUrl();
  }

  getMode(): TransportMode {
    return this.judge.getMode();
  }

  /** 取消当前 WS 判题（仅桌面 invoke 通道有效）。 */
  cancel(): void {
    this.judge.cancelWebSocket();
    this.sandbox.interrupt();
  }

  /** 页面卸载时释放 WASM 内存（手机内存紧张，别常驻）。 */
  dispose(): void {
    this.sandbox.dispose();
  }

  /** 供设置页展示的当前通道描述。 */
  describeChannel(): string {
    const ch = this.channel;
    if (ch === 'invoke') return '本机 go-judge 沙箱（完整支持 C++/Python/Java）';
    if (ch === 'pyodide') return '本地 WASM 沙箱（Python，完全离线）';
    return `局域网判题（${this.judge.getLanBaseUrl() || '未配置地址'}）`;
  }
}

/** 结果里被传输层整批打回时，描述用的兜底。 */
function describe(e: unknown): string {
  if (e instanceof JudgeClientError) return e.message;
  if (e instanceof Error) return e.message;
  return String(e);
}

/** 默认单例：整个 App 共用一份，避免重复加载 Pyodide 吃光手机内存。 */
export const judgeEngine = new JudgeEngine();

/* 便于 UI 直接用的再导出（避免每个页面都去 import 两个模块） */
export { mapVerdictToUi, normalizeOutput };
export type { TestCase, TestCaseResult, Verdict, EnvReport, Transport, TransportMode };
