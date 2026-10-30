/**
 * agent/llmPlanner.ts —— 把「只会说话」的 /ai/chat 变成「按协议出动作」的 planner
 * ============================================================================
 * 为什么不放进 index.ts：
 *   这个文件依赖 lib/aiChat（fetch + SSE + localStorage），是「网络层」。
 *   index.ts 是纯逻辑包的入口（Node 验收脚本要能零副作用 import 它），
 *   把网络层挂在 index 上会导致「验逻辑时被迫加载 http 栈」。
 *   所以 UI 用：import { makeLlmPlanner } from './llmPlanner'。
 *
 * 为什么不改 provider 加 tools 字段（A6 才做）：
 *   provider 的请求体只有 {model, messages, stream}，没有 tools。
 *   但**协议完全可以由 prompt 承担**——我们让模型每轮只吐一个 JSON，
 *   前端解析后自己执行工具，效果与原生 function calling 等价，
 *   代价是多一次解析失败的可能（用一次内部重试兜住）。
 *
 * 为什么每步都要把 agent_system 重新发一遍：
 *   /ai/chat 是无状态的（每次请求自带 history），服务端不保存 system。
 *   attach.agent_system 覆盖服务端 PROMPTS，这是 A1 期的接法；
 *   代价是每轮多 ~1KB prompt，换来「不动 provider」。
 */

import type { AgentAction, Planner, PlannerMessage } from './types';
import { parseAction } from './loop';
import type { ChatTurn, UiAiMode } from '../aiChat';

export interface LlmPlannerOptions {
  /** 完整的 agent 协议 prompt（含工具目录与场景任务） */
  systemPrompt: string;
  /** 章节 id（数字）——后端按它做检索锚定；agent 模式下只用于上下文 */
  chapterId?: number | null;
  /** 增量文本回显（UI 上能看到「模型正在想」） */
  onDelta?: (text: string) => void;
  /** 解析失败时是否再问一次（默认 true） */
  retryOnce?: boolean;
  signal?: AbortSignal;
}

/** 后端契约里 mode 是枚举字符串，这里显式标注避免写成裸字面量后被误改 */
const AGENT_MODE: UiAiMode = 'agent';

/**
 * 历史裁剪：后端 MAX_CONTEXT_CHARS=6000，8 步的观察很容易超。
 * 只保留最近 6 条（3 轮）——更早的步骤结论已经体现在报告里，不需要每轮重看。
 */
const HISTORY_KEEP = 6;

export function makeLlmPlanner(opts: LlmPlannerOptions): Planner {
  let conversationId: number | null = null;

  return async (messages: PlannerMessage[]): Promise<AgentAction> => {
    const { streamChat } = await import('../aiChat');

    const history: ChatTurn[] = messages
      .filter((m) => m.role !== 'system')
      .map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content }));
    const last = history.pop();
    if (!last) throw new Error('planner 收到空对话');

    const ask = async (message: string, hist: ChatTurn[]): Promise<string> =>
      streamChat({
        mode: AGENT_MODE,
        message,
        history: hist.slice(-HISTORY_KEEP),
        chapterId: opts.chapterId ?? null,
        attach: { agent_system: opts.systemPrompt },
        conversationId,
        signal: opts.signal,
        callbacks: {
          onMeta: (meta) => {
            if (meta.conversation_id) conversationId = meta.conversation_id;
          },
          onDelta: opts.onDelta ?? (() => {}),
        },
      });

    const first = await ask(last.content, history);
    const action = parseAction(first);
    if (action || opts.retryOnce === false) {
      if (!action) throw new Error('模型输出不是合法动作 JSON');
      return action;
    }

    // 一次纠偏重试：把「你刚才输错了」讲清楚，比再降级到规则序列划算
    const corrective: ChatTurn[] = [
      ...history,
      { role: 'user', content: last.content },
      { role: 'assistant', content: first.slice(0, 800) },
      {
        role: 'user',
        content:
          '上一条不是合法的动作 JSON。请严格只输出一个 JSON 对象，不要任何解释、不要代码块：\n' +
          '{"type":"tool","thought":"...","tool":"工具名","args":{...}}\n' +
          '或 {"type":"final","thought":"...","report":{...}}',
      },
    ];
    const second = await ask(corrective[corrective.length - 1].content, corrective.slice(0, -1));
    const retried = parseAction(second);
    if (!retried) throw new Error('模型连续两次输出都不是合法动作 JSON');
    return retried;
  };
}
