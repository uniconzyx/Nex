/**
 * agent/types.ts —— Agent 层的类型契约
 *
 * 设计意图（与 docs/MLDL-Agent-Plan.md §3 对齐）：
 *   1. **能动手**：ToolSpec 是唯一的「手」，planner 只能通过它改变世界；
 *   2. **能循环**：AgentStep 记录每一步 plan → act → observe，可回放；
 *   3. **有产物**：AgentReport 是会话唯一的交付物，且每节都带 evidence；
 *   4. **能自证**：所有数字都在 Observation.data 里，报告只允许引用，不允许新造。
 *
 * 为什么 Observation 要同时有 brief / data / raw 三个字段：
 *   - brief：塞回给 planner 的短摘要（必须能截断到 2KB 以内，否则 token 爆）
 *   - data ：结构化数据，供 buildReport 拼接与断言用（不进 prompt）
 *   - raw  ：真实 stdout / base64 图，供产物逐字引用（这是「不许编数字」的物证）
 */

/* ------------------------------------------------------------------ 工具 */

export type ToolName =
  | 'list_chapters'
  | 'get_progress'
  | 'read_chapter'
  | 'search_local'
  | 'list_wrong_exercises'
  | 'list_chapter_exercises'
  | 'run_python';

export const TOOL_NAMES: ToolName[] = [
  'list_chapters',
  'get_progress',
  'read_chapter',
  'search_local',
  'list_wrong_exercises',
  'list_chapter_exercises',
  'run_python',
];

/** 工具执行结果。ok=false 也必须返回（失败信息就是 planner 的下一步输入）。 */
export interface Observation {
  ok: boolean;
  /** 给 planner 看的一行摘要；过长会被 loop 截断 */
  brief: string;
  /** 结构化数据（供报告与断言使用，不进 prompt） */
  data?: unknown;
  /** 真实产物：stdout、图片 base64 等。报告的 evidence 只能来自这里 */
  raw?: string;
}

/* ------------------------------------------------------- 可替换的执行后端 */

/**
 * Python 执行结果。刻意与 pyodide/PyodideSandbox 的 PyRunResult 保持同构，
 * 但**只取 agent 需要的那几个字段**——这样验收脚本可以用假 runner 注入，
 * 而浏览器里直接包一层真沙箱即可，两边不需要共享 Worker 类型。
 */
export interface PyResult {
  stdout: string;
  stderr: string;
  /** 超时/被中断：此时 stdout 是半成品，报告里必须标注「不完整」 */
  interrupted: boolean;
  durationMs: number;
  error: { name: string; message: string } | null;
  /** 代码里 savefig 出来的图（data:image/png;base64,...） */
  images?: string[];
}

/**
 * Python 运行器。为什么用注入而不是直接 import PyodideSandbox：
 *   1. 浏览器里要复用同一个 Worker（避免每次 import 都重新下载解释器）；
 *   2. Node 验收脚本里根本没有 Worker，需要一个确定性的假实现；
 *   3. 将来若要换服务端执行，只换这一层实现。
 */
export type PythonRunner = (code: string, timeoutMs?: number) => Promise<PyResult>;

export interface ToolContext {
  /** 学科 key（ml / ai / ...）；工具默认只看这个学科，避免跨学科串味 */
  subject: string;
  /** 会话当前锁定的章节（S2 实验通常锁定一章） */
  chapterId?: string;
  /**
   * 进度状态。**必须注入**，不让工具层 import progress.ts——
   * 那个模块在 import 时就会读 localStorage，Node 里没有，会污染验收。
   */
  progress: import('../gameTypes').ProgressState;
  /** Python 执行器（浏览器传真沙箱；验收传假实现） */
  runner?: PythonRunner;
  /** 运行日志（UI 可以边跑边显示） */
  onLog?: (line: string) => void;
}

export interface ToolSpec {
  name: ToolName;
  /** 一句话说明（会写进 planner 的 system prompt） */
  desc: string;
  /** 参数说明（同样进 prompt，务必短） */
  argsDoc: string;
  run(args: Record<string, unknown>, ctx: ToolContext): Promise<Observation>;
}

/* ------------------------------------------------------------------ 动作 */

/**
 * planner 每轮只允许输出一个动作。
 * 为什么不是「一次给一串动作」：串行便于在任意一步失败时回退，也便于把
 * 每步的真实输出回填——这正是 agent 与「一次性生成」的本质区别。
 */
export interface ToolAction {
  type: 'tool';
  /** 这一步在想什么（会显示在会话卡上，也是失败时的排查线索） */
  thought: string;
  tool: ToolName;
  args: Record<string, unknown>;
}

export interface FinalAction {
  type: 'final';
  thought: string;
  report: AgentReport;
}

export type AgentAction = ToolAction | FinalAction;

/* ------------------------------------------------------------------ 会话 */

export interface AgentStep {
  idx: number;
  thought: string;
  /** final 步骤没有工具调用 */
  tool?: ToolName;
  args?: Record<string, unknown>;
  observation?: Observation;
  /** 本步耗时（LLM + 工具） */
  ms: number;
}

export type StopReason = 'final' | 'max_steps' | 'error' | 'aborted';

export interface AgentRun {
  scenario: AgentScenarioId;
  task: string;
  subject: string;
  chapterId?: string;
  steps: AgentStep[];
  report?: AgentReport;
  stopped: StopReason;
  /** stopped==='error' 时的原因（planner 解析失败 / 工具崩了） */
  error?: string;
}

/* ------------------------------------------------------------------ 产物 */

export interface ReportSection {
  heading: string;
  /** Markdown 正文。禁止在这里出现「工具没算过的数字」 */
  body: string;
  /** 数据来源标注，如 `run_python#3`、`get_progress#1`。缺省即视为不可信 */
  evidence?: string;
}

export interface AgentReport {
  title: string;
  scenario: AgentScenarioId;
  /** 结论先行：一句话说清这份报告说了什么 */
  headline: string;
  sections: ReportSection[];
  /** 可选：主实验代码（会作为 .ipynb 的 code cell） */
  labCode?: string;
  /** 该代码的真实 stdout（会作为 code cell 的 output） */
  labOutput?: string;
  /** data:image/png;base64,... 会作为 ipynb 的 image output */
  images?: string[];
}

/* ------------------------------------------------------------------ 场景 */

export type AgentScenarioId = 'diagnose' | 'experiment';

export interface AgentScenario {
  id: AgentScenarioId;
  name: string;
  /** 一句话说明（列表页用） */
  tagline: string;
  /** 交给 planner 的任务描述 */
  task: string;
  /** 规则兜底时的固定动作序列（无 LLM / LLM 崩了时用） */
  fallback: PlanStep[];
}

/** 规则 planner 的一步：只是 ToolAction 的轻量形式 */
export interface PlanStep {
  thought: string;
  tool: ToolName;
  args: Record<string, unknown>;
}

/* ------------------------------------------------------------------ planner */

export interface PlannerMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

/**
 * Planner：给定对话历史，返回下一个动作。
 * 抽象成函数是为了让「真 LLM / 规则兜底 / 测试桩」三者可替换——
 * 验收脚本能完全离线跑通全链路，靠的就是这一层抽象。
 */
export type Planner = (messages: PlannerMessage[]) => Promise<AgentAction>;

export interface AgentOptions {
  scenario: AgentScenario;
  subject: string;
  chapterId?: string;
  planner: Planner;
  /** 默认 8：步数上限是成本与延迟的唯一闸门 */
  maxSteps?: number;
  onStep?: (step: AgentStep) => void;
  onLog?: (line: string) => void;
}
