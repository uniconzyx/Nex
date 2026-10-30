/**
 * agent/pyodideRunner.ts —— 把判题用的 Pyodide 沙箱适配成 agent 的 PythonRunner
 * ============================================================================
 * 为什么复用全局单例 pyodideSandbox：
 *   Pyodide 解释器 ~80MB WASM 内存，多一个实例手机上直接 OOM。
 *   判题和 agent 用的是同一类「跑一段 Python 拿 stdout」，没有必须隔离的理由；
 *   真正需要隔离的是**超时与内存上限**，那由每次 run 的 limits 参数控制。
 *
 * 一处诚实的缺口：**沙箱目前不回传图片**。
 *   PyodideSandbox 的 PyRunResult 只有 stdout/stderr/error，没有 matplotlib 的
 *   savefig 产物。所以这里的 images 恒为 []，agent 报告里也不会有图。
 *   在 ML 教学里图的缺失是真实损失——这件事记在 docs/MLDL-Agent-Plan.md 的
 *   遗留项里，不在这里假装有。
 */

import { pyodideSandbox } from '../pyodide/PyodideSandbox';
import type { PyResult, PythonRunner } from './types';

export interface PyodideRunnerOptions {
  /** 沙箱加载进度（首次要下 ~10MB 解释器），UI 可以显示进度条 */
  onProgress?: (p: { stage: string; detail?: string }) => void;
  /** stdout 流式回调：长实验能边跑边看 */
  onChunk?: (s: string) => void;
}

export function makePyodideRunner(opts: PyodideRunnerOptions = {}): PythonRunner {
  return async (code: string, timeoutMs = 20_000): Promise<PyResult> => {
    const r = await pyodideSandbox.run(code, '', { timeoutMs }, opts.onChunk);
    return {
      stdout: r.stdout,
      stderr: r.stderr,
      // killed 是「Worker 被强杀」，对调用方等价于 interrupted：
      // 两种情况 stdout 都不完整，报告里必须标注「不完整」
      interrupted: r.interrupted || r.killed,
      durationMs: r.durationMs,
      error: r.error ? { name: r.error.name, message: r.error.message } : null,
      images: [],
    };
  };
}
