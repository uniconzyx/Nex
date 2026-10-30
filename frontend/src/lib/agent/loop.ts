/**
 * agent/loop.ts —— 执行循环：plan → act → observe → 回填
 * ============================================================================
 * 这个文件只有一件事要做：**保证每一轮的数字都来自工具，而不是模型**。
 * 具体靠三条机制：
 *
 *   1. **单步动作**：planner 每轮只输出一个动作（types.ts 已定），
 *      所以任何一步失败都能停在那里，不会出现「模型编了 8 步、你只验得动第 3 步」。
 *   2. **失败即观察**：工具失败也返回 Observation（ok=false + brief），
 *      照原样回填给 planner。模型看到「章节不存在，可用 ml-ch01..ml-ch09」才会改参数——
 *      这是 agent 与一次性生成的分界线。
 *   3. **降级不停摆**：planner 抛错、连续返回非法 JSON、或步数耗尽时，
 *      切到场景的规则序列（fallback）继续跑完，最后由 report.ts 从真实观察里拼报告。
 *      没有 LLM 也能出一份「数字全对、只是没有洞察」的报告。
 *
 * 变量回填（{{weak0}} / {{chapter}} / {{lab_code}}）：
 *   规则序列是静态数组，但「诊断最弱那一章」必须依赖上一步的结果。
 *   所以每步观察后把关键字段吸收进 vars，下一步的参数再做字符串替换。
 */

import { getTool, toolCatalog } from './tools';
import { TOOL_NAMES, type AgentAction, type AgentReport, type AgentRun, type AgentScenario, type AgentStep, type Observation, type Planner, type PlannerMessage, type PythonRunner, type ToolName } from './types';
import { labFor } from './scenarios';
import type { ProgressState } from '../gameTypes';

/* ============================================================================
 * 一、输入
 * ========================================================================== */

export interface RunAgentInput {
  scenario: AgentScenario;
  subject: string;
  chapterId?: string;
  /** 进度必须注入（工具层不 import progress.ts，见 types.ts 的说明） */
  progress: ProgressState;
  runner?: PythonRunner;
  planner: Planner;
  /** 默认 8 步 */
  maxSteps?: number;
  onStep?: (step: AgentStep) => void;
  onLog?: (line: string) => void;
  signal?: AbortSignal;
}

const DEFAULT_MAX_STEPS = 8;

/** brief 回填上限。planner 的上下文预算是硬约束，超了就直接截断 */
const OBS_MAX = 1200;

/* ============================================================================
 * 二、System prompt
 * ========================================================================== */

/**
 * 为什么把工具目录自动生成（toolCatalog）而不是手写：
 *   手写清单一定会漏工具或漏参数名，而这种漂移在运行时的表现是
 *   「模型瞎猜参数 → 连续失败 → 降级」，很难定位。自动生成 = 单一真源。
 */
export function buildSystemPrompt(scenario: AgentScenario, catalog: string, subject: string, chapterId?: string): string {
  return [
    '你是一个能**动手**的学习 agent，服务于 CppMind（凯喵 Code）的机器学习 / 深度学习学习板块。',
    '你不是聊天助手：你能查数据、能读章节、能真跑 Python，然后交一份可验证的报告。',
    '',
    '## 可用工具',
    catalog,
    '',
    '## 本次任务',
    `学科：${subject}${chapterId ? `；锁定章节：${chapterId}` : ''}`,
    scenario.task,
    '',
    '## 输出协议（必须严格遵守）',
    '每一轮只输出**一个 JSON 对象**，不要输出任何解释文字、不要用 markdown 代码块包住。',
    '',
    '调用工具时：',
    '{"type":"tool","thought":"为什么这一步要做它","tool":"工具名","args":{...}}',
    '',
    '任务完成时：',
    '{"type":"final","thought":"为什么可以停了","report":{...}}',
    '',
    'report 的结构：',
    '{"title":"标题","scenario":"' + scenario.id + '","headline":"一句话结论",',
    ' "sections":[{"heading":"小节标题","body":"markdown 正文","evidence":"工具名#步骤序号"}],',
    ' "labCode":"可选：主实验代码","labOutput":"可选：该代码的真实 stdout"}',
    '',
    '## 硬约束',
    '1. **不编数字**：百分比、题数、耗时、准确率，只能来自工具返回的 brief/data/raw。',
    '   报告里每个含数字的小节都必须写 evidence，指向产生它的那一步（如 "get_progress#1"）。',
    '2. **不假装跑过**：没调用 run_python 就不要在报告里出现运行结果。',
    '3. **失败要重试**：工具返回失败时，根据 brief 里的提示改参数再试；连续两次同样失败就换路子。',
    '4. **不越界**：只讲本学科章节里有的内容；不属于本学科的东西，说清它归哪一章。',
  ].join('\n');
}

/* ============================================================================
 * 三、动作解析（模型输出不可信，必须容错）
 * ========================================================================== */

const VALID_TOOLS = new Set<string>(TOOL_NAMES);

/** 从模型输出里抠出 JSON 对象。允许前后有杂字、允许 ```json 围栏。 */
export function parseAction(text: string): AgentAction | null {
  if (!text) return null;
  const clean = text.replace(/^```(?:json)?/gm, '').replace(/```$/gm, '').trim();
  const start = clean.indexOf('{');
  const end = clean.lastIndexOf('}');
  if (start < 0 || end <= start) return null;
  let raw: unknown;
  try {
    raw = JSON.parse(clean.slice(start, end + 1));
  } catch {
    return null;
  }
  if (!raw || typeof raw !== 'object') return null;
  const o = raw as Record<string, unknown>;
  const thought = typeof o.thought === 'string' ? o.thought : '';

  if (o.type === 'final') {
    const rep = o.report as AgentReport | undefined;
    if (!rep || typeof rep !== 'object') return null;
    return { type: 'final', thought, report: normalizeReport(rep) };
  }
  if (o.type === 'tool' || (o.type === undefined && typeof o.tool === 'string')) {
    const tool = String(o.tool ?? '');
    if (!VALID_TOOLS.has(tool)) return null;
    const args = (o.args && typeof o.args === 'object' ? o.args : {}) as Record<string, unknown>;
    return { type: 'tool', thought, tool: tool as ToolName, args };
  }
  return null;
}

/** 报告字段可能缺项（模型经常漏 headline / sections），补齐成可渲染的结构 */
export function normalizeReport(rep: Partial<AgentReport>): AgentReport {
  const sections = Array.isArray(rep.sections)
    ? rep.sections
        .filter((s) => s && typeof s === 'object')
        .map((s) => ({
          heading: String(s.heading ?? '未命名小节'),
          body: String(s.body ?? ''),
          evidence: typeof s.evidence === 'string' ? s.evidence : undefined,
        }))
    : [];
  return {
    title: String(rep.title ?? '未命名报告'),
    scenario: (rep.scenario ?? 'diagnose') as AgentReport['scenario'],
    headline: String(rep.headline ?? ''),
    sections,
    labCode: typeof rep.labCode === 'string' ? rep.labCode : undefined,
    labOutput: typeof rep.labOutput === 'string' ? rep.labOutput : undefined,
    images: Array.isArray(rep.images) ? rep.images.filter((x): x is string => typeof x === 'string') : undefined,
  };
}

/* ============================================================================
 * 四、变量回填
 * ========================================================================== */

type Vars = Record<string, string>;

function absorb(vars: Vars, obs: Observation): void {
  const d = obs.data as Record<string, unknown> | undefined;
  if (!d) return;
  // get_progress 的 weak 是「按掌握度升序的前 5 章」，规则序列最常引用 weak0
  if (Array.isArray(d.weak)) {
    d.weak.forEach((w, i) => {
      if (typeof w === 'string') vars[`weak${i}`] = w;
    });
  }
  // list_chapters 的 items 每项有 chapter_id，取第一项作为兜底
  if (Array.isArray(d.items)) {
    const first = d.items[0] as Record<string, unknown> | undefined;
    if (first && typeof first.chapter_id === 'string') vars.first_chapter = first.chapter_id;
  }
  if (typeof d.chapter_id === 'string') vars.last_chapter = d.chapter_id;
}

/** 把 {{name}} 替换成 vars 里的值；缺失的占位保留原样，让工具报「参数不对」而不是静默变成空串 */
export function fillArgs(args: Record<string, unknown>, vars: Vars): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(args)) {
    if (typeof v !== 'string') {
      out[k] = v;
      continue;
    }
    const replaced = v.replace(/\{\{(\w+)\}\}/g, (m, name: string) =>
      Object.prototype.hasOwnProperty.call(vars, name) ? vars[name] : m,
    );
    out[k] = replaced;
  }
  return out;
}

/* ============================================================================
 * 五、主循环
 * ========================================================================== */

export async function runAgent(input: RunAgentInput): Promise<AgentRun> {
  const { scenario, subject, chapterId, progress, runner, planner, signal } = input;
  const maxSteps = Math.max(1, input.maxSteps ?? DEFAULT_MAX_STEPS);
  const log = input.onLog ?? (() => {});

  const steps: AgentStep[] = [];
  const vars: Vars = {};
  if (chapterId) vars.chapter = chapterId;
  vars.lab_code = labFor(chapterId).template.code;

  // 规则序列指针：planner 一旦不可用，就从这里继续
  let ruleIdx = 0;
  let degraded = false;

  const messages: PlannerMessage[] = [
    { role: 'system', content: buildSystemPrompt(scenario, toolCatalog(), subject, chapterId) },
    { role: 'user', content: `开始执行。目标场景：${scenario.name}。` },
  ];

  let stopped: AgentRun['stopped'] = 'max_steps';
  let error: string | undefined;
  let report: AgentReport | undefined;

  for (let i = 0; i < maxSteps; i++) {
    if (signal?.aborted) {
      stopped = 'aborted';
      break;
    }
    const t0 = Date.now();
    let action: AgentAction | null = null;

    if (!degraded) {
      try {
        action = await planner(messages);
        if (!action) {
          // 模型没按协议输出（常见：包了 markdown、字段名写成 tool_name）
          degraded = true;
          error = 'planner 输出无法解析为动作';
          log('planner 输出不合协议，切换到规则序列');
        }
      } catch (e) {
        degraded = true;
        error = `planner 失败：${(e as Error).message}`;
        log('planner 不可用，切换到规则序列');
      }
    }

    if (!action && degraded) {
      action = nextRuleAction(scenario, ruleIdx, vars, steps.length);
      ruleIdx += 1;
      if (!action) {
        // 规则序列跑完 = 正常收尾。降级路径没有「模型说可以停了」这个信号，
        // 所以由「证据够了」来代替：跑完既定步骤就直接出报告。
        report = buildFallbackReport(scenario, steps, vars, subject, chapterId);
        stopped = 'final';
        break;
      }
    }
    if (!action) {
      stopped = 'error';
      error = error ?? 'planner 返回了无法解析的动作';
      break;
    }

    if (action.type === 'final') {
      steps.push({ idx: steps.length + 1, thought: action.thought, ms: Date.now() - t0 });
      report = action.report;
      stopped = 'final';
      break;
    }

    const tool = getTool(action.tool);
    const args = degraded ? fillArgs(action.args, vars) : action.args;
    let obs: Observation;
    if (!tool) {
      obs = { ok: false, brief: `未知工具 ${action.tool}；可用：${TOOL_NAMES.join(' / ')}` };
    } else {
      try {
        obs = await tool.run(args, {
          subject,
          chapterId,
          progress,
          runner,
          onLog: log,
        });
      } catch (e) {
        obs = { ok: false, brief: `工具 ${action.tool} 抛异常：${(e as Error).message}` };
      }
    }
    absorb(vars, obs);

    const step: AgentStep = {
      idx: steps.length + 1,
      thought: action.thought,
      tool: action.tool,
      args,
      observation: obs,
      ms: Date.now() - t0,
    };
    steps.push(step);
    input.onStep?.(step);
    log(`[${step.idx}] ${action.tool} → ${obs.ok ? 'ok' : 'fail'}：${obs.brief.slice(0, 80)}`);

    // 回填给 planner：把「我做了什么 + 真实结果」写进对话
    messages.push({ role: 'assistant', content: JSON.stringify({ type: 'tool', thought: action.thought, tool: action.tool, args }) });
    messages.push({
      role: 'user',
      content: `第 ${step.idx} 步观察（${obs.ok ? '成功' : '失败'}）：\n${clipBrief(obs.brief)}`,
    });
  }

  // 没有 final（步数耗尽 / 被中断 / 出错）：用规则序列里「还没跑完的部分」补齐证据，再拼报告
  if (!report) {
    if (stopped === 'max_steps' && ruleIdx === 0) {
      // planner 一直没给 final 但也没崩：把规则序列跑完，保证报告有料
      log('步数耗尽且无 final，补跑规则序列生成报告');
      while (ruleIdx < scenario.fallback.length && steps.length < maxSteps + 3) {
        const a = nextRuleAction(scenario, ruleIdx, vars, steps.length);
        ruleIdx += 1;
        if (!a || a.type !== 'tool') break;
        const tool = getTool(a.tool);
        if (!tool) break;
        const args = fillArgs(a.args, vars);
        const t0 = Date.now();
        let obs: Observation;
        try {
          obs = await tool.run(args, { subject, chapterId, progress, runner, onLog: log });
        } catch (e) {
          obs = { ok: false, brief: `工具 ${a.tool} 抛异常：${(e as Error).message}` };
        }
        absorb(vars, obs);
        const step: AgentStep = { idx: steps.length + 1, thought: a.thought, tool: a.tool, args, observation: obs, ms: Date.now() - t0 };
        steps.push(step);
        input.onStep?.(step);
      }
    }
    report = buildFallbackReport(scenario, steps, vars, subject, chapterId);
    if (stopped === 'max_steps') stopped = 'max_steps';
  }

  return { scenario: scenario.id, task: scenario.task, subject, chapterId, steps, report, stopped, error };
}

function clipBrief(s: string): string {
  return s.length <= OBS_MAX ? s : `${s.slice(0, OBS_MAX)}…`;
}

function nextRuleAction(scenario: AgentScenario, idx: number, vars: Vars, stepCount: number): AgentAction | null {
  const plan = scenario.fallback[idx];
  if (!plan) return null;
  const args = fillArgs(plan.args, vars);
  // 占位没解析出来（例如 weak0 缺失）→ 这一条跳过，避免把 "{{weak0}}" 当章节 id 打给工具
  for (const v of Object.values(args)) {
    if (typeof v === 'string' && v.includes('{{')) return nextRuleAction(scenario, idx + 1, vars, stepCount);
  }
  return { type: 'tool', thought: plan.thought, tool: plan.tool, args };
}

/* ============================================================================
 * 六、兜底报告
 * ========================================================================== */

/**
 * 从真实观察里拼报告。这里的每个数字都直接读 observation.data，
 * **不做任何推断**——宁可少说，不可编造。
 */
export function buildFallbackReport(
  scenario: AgentScenario,
  steps: AgentStep[],
  vars: Vars,
  subject: string,
  chapterId?: string,
): AgentReport {
  const sections: AgentReport['sections'] = [];
  const find = (tool: ToolName) => steps.find((s) => s.tool === tool && s.observation?.ok);

  const prog = find('get_progress');
  if (prog) {
    const d = prog.observation?.data as
      | {
          items?: { chapter_id: string; title: string; mastery: number; wrong_count: number }[];
          weak?: string[];
          untouched?: string[];
          stats?: { total: number; done: number; avg_mastery: number; wrong_total: number };
        }
      | undefined;
    const stats = d?.stats;
    if (stats) {
      sections.push({
        heading: '整体进度',
        body: [
          `「${subject}」共 **${stats.total}** 章，已通关 **${stats.done}** 章，平均掌握度 **${stats.avg_mastery}%**。`,
          `累计错题 **${stats.wrong_total}** 道，未开始 **${(d?.untouched ?? []).length}** 章。`,
        ].join('\n\n'),
        evidence: `get_progress#${prog.idx}`,
      });
    }
  }

  const weak0 = vars.weak0;
  if (weak0) {
    const w = (prog?.observation?.data as { items?: { chapter_id: string; title: string; mastery: number; wrong_count: number }[] } | undefined)?.items?.find((i) => i.chapter_id === weak0);
    sections.push({
      heading: '最薄弱的一章',
      body: w
        ? `**${w.chapter_id}**（${w.title}）：掌握度 **${w.mastery}%**，累计错 **${w.wrong_count}** 道。`
        : `**${weak0}**（掌握度最低的一章）。`,
      evidence: `get_progress#${prog?.idx ?? '?'}`,
    });

    const pit = steps.find((s) => s.tool === 'read_chapter' && s.observation?.ok);
    const dims = pit?.observation?.data as { dims?: { pitfalls?: string[] } } | undefined;
    const firstPit = dims?.dims?.pitfalls?.[0];
    if (firstPit) {
      sections.push({
        heading: '先补这个易错点',
        body: `> ${firstPit.slice(0, 300)}`,
        evidence: `read_chapter#${pit?.idx}`,
      });
    }

    const ex = steps.find((s) => s.tool === 'list_chapter_exercises' && s.observation?.ok);
    const exData = ex?.observation?.data as { total?: number; items?: { id: string; type: string; title: string }[] } | undefined;
    if (exData?.total) {
      sections.push({
        heading: '下一步（可直接执行）',
        body: [
          `1. 打开 **${weak0}** 的「概念」关，重读上面那条易错点所在的 concept；`,
          `2. 做本章 **${exData.total}** 道题里你还没做对的：${(exData.items ?? []).slice(0, 3).map((x) => `\`${x.id}\``).join('、')}；`,
          '3. 三关全通（概念 / 演练 / BOSS）后本章掌握度才会满。',
        ].join('\n'),
        evidence: `list_chapter_exercises#${ex?.idx}`,
      });
    }
  }

  const run = steps.find((s) => s.tool === 'run_python' && s.observation?.ok);
  if (run) {
    const out = (run.observation?.raw ?? '').trim();
    const code = typeof run.args?.code === 'string' ? run.args.code : undefined;
    sections.push({
      heading: '实验与真实输出',
      body: out ? '见下方代码单元的真实 stdout（原样保留，未经改写）。' : '脚本运行成功但没有任何 stdout。',
      evidence: `run_python#${run.idx}`,
    });
    return {
      title: `${chapterId ?? subject} 实验记录`,
      scenario: scenario.id,
      headline: out
        ? `实验已跑通，stdout ${out.length} 字；结论以真实输出为准（见下方代码单元）`
        : '实验已跑通但没有输出，需要在代码里 print 才能引用数字',
      sections,
      labCode: code,
      labOutput: out || undefined,
    };
  }

  const weakList = (prog?.observation?.data as { weak?: string[] } | undefined)?.weak ?? [];
  const stats = (prog?.observation?.data as
    | { stats?: { total: number; done: number; avg_mastery: number; wrong_total: number } }
    | undefined)?.stats;
  // 三档语气，对应三种真实状态。中间那档才是「诊断」，另两档只是边界：
  //   fresh      —— 一章都没通、也没错题：说「最该补 ch01」是错的语气，用户根本没开始
  //   completed  —— 全部通关：此时 weak 排序已无意义（mastery 都是 100），
  //                 继续输出「最该补」会让人以为还有欠账
  const fresh = !!stats && stats.done === 0 && stats.wrong_total === 0;
  const completed = !!stats && stats.total > 0 && stats.done === stats.total;
  const firstChapter = weakList[0] ?? '';
  return {
    title: `${subject} 学情诊断`,
    scenario: scenario.id,
    headline: fresh
      ? `「${subject}」还没有开始记录：建议从 ${firstChapter} 开机，先过概念关再上 BOSS`
      : completed
        ? `「${subject}」已全部通关：接下来该做项目与面试题，而不是再补章节`
        : weakList.length
          ? `最该补的是 ${weakList.slice(0, 3).join('、')}；报告里的数字全部来自你的真实进度`
          : `「${subject}」暂时没有可诊断的数据（可能还没开始学）`,
    sections,
  };
}
