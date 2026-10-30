/**
 * aiChat.ts —— CppCat 对话的流式客户端（真实后端 /api/v1/ai/chat）
 *
 * 为什么单独成文件而不是塞进 AiPanel：
 *   1. SSE 的帧解析（event/data/多行 data/跨 chunk 半帧）是纯文本逻辑，和 React 无关；
 *   2. 契约映射集中在一处——前端模式名与后端 AIMode 枚举**不完全一致**
 *      （前端 UI 用 'dl'，后端枚举是 'dl_guide'），散在组件里迟早漏一处；
 *   3. 错误分类要复用：未登录 / 配额用尽 / 网络不可达，UI 提示文案完全不同。
 *
 * 契约（见 server/app/api/v1/ai.py + app/schemas/ai.py）：
 *   POST /api/v1/ai/chat   Authorization: Bearer <access>
 *   body  { mode, message, history[{role,content}], chapter_id?, attach?, conversation_id? }
 *   响应  text/event-stream
 *     event: meta   {"model": "...", "mode": "...", "conversation_id": 1}
 *     event: delta  {"text": "..."}          ← 增量 token
 *     event: error  {"message": "..."}       ← 流中异常（非 HTTP 错误）
 *     event: done   {"quota_left": 19, "conversation_id": 1}
 */
import { resolveApiBase } from './api';

/** UI 侧模式（与 AiPanel 的 AiMode 保持一致） */
export type UiAiMode = 'socratic' | 'diagnose' | 'review' | 'plan' | 'dl' | 'interview' | 'agent';

/**
 * UI 模式 → 后端 AIMode 枚举值。
 * 'dl' 在 UI 上是短名，后端枚举叫 'dl_guide'；不做这层映射，
 * `AIMode(body.mode)` 会直接抛 ValueError（500）。
 */
const BACKEND_MODE: Record<UiAiMode, string> = {
  socratic: 'socratic',
  diagnose: 'diagnose',
  review: 'review',
  plan: 'plan',
  dl: 'dl_guide',
  interview: 'interview',
  // agent 模式没有独立 UI 入口（由 agent 循环内部调用），
  // 后端 AIMode 里同名，不做改名映射
  agent: 'agent',
};

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

/** 未登录 / 令牌失效：UI 应引导去登录，而不是当成普通错误重试 */
export class AiAuthError extends Error {
  constructor(message = '登录后才能使用 AI 助手') {
    super(message);
    this.name = 'AiAuthError';
  }
}

/** 当日配额用尽 */
export class AiQuotaError extends Error {
  constructor(message = '今日 AI 额度已用完') {
    super(message);
    this.name = 'AiQuotaError';
  }
}

/** 连不上后端（服务没起 / 地址错） */
export class AiOfflineError extends Error {
  readonly base: string;
  constructor(message: string, base: string) {
    super(message);
    this.name = 'AiOfflineError';
    this.base = base;
  }
}

export interface StreamMeta {
  model?: string;
  mode?: string;
  conversation_id?: number;
}

export interface StreamDone {
  quota_left?: number;
  conversation_id?: number;
}

export interface StreamCallbacks {
  /** 首帧元信息：模型名、会话 id */
  onMeta?: (meta: StreamMeta) => void;
  /** 增量文本，追加到当前气泡 */
  onDelta: (text: string) => void;
  /** 正常结束：拿到剩余配额 */
  onDone?: (done: StreamDone) => void;
}

export interface StreamChatOptions {
  mode: UiAiMode;
  message: string;
  history?: ChatTurn[];
  chapterId?: number | null;
  attach?: Record<string, unknown> | null;
  conversationId?: number | null;
  signal?: AbortSignal;
  callbacks: StreamCallbacks;
}

function accessToken(): string | null {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem('nex.accessToken');
}

/** 单帧里的 data 可能是多行（SSE 规范允许多个 data: 行，用 \n 拼接） */
function parseFrame(frame: string): { event: string; data: string } | null {
  let event = 'message';
  const dataLines: string[] = [];
  for (const rawLine of frame.split('\n')) {
    const line = rawLine.replace(/\r$/, '');
    if (!line || line.startsWith(':')) continue;
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
  }
  if (!dataLines.length) return null;
  return { event, data: dataLines.join('\n') };
}

/**
 * 发起一次流式对话。返回完整回答文本（便于调用方落库/复制）。
 * 异常分类：AiAuthError / AiQuotaError / AiOfflineError / DOMException(abort) / Error(流内 error 事件)
 */
export async function streamChat(opts: StreamChatOptions): Promise<string> {
  const token = accessToken();
  if (!token) throw new AiAuthError();

  const base = await resolveApiBase();
  const url = `${base}/api/v1/ai/chat`;

  let res: Response;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        mode: BACKEND_MODE[opts.mode] ?? opts.mode,
        message: opts.message,
        history: opts.history ?? [],
        chapter_id: opts.chapterId ?? null,
        attach: opts.attach ?? null,
        conversation_id: opts.conversationId ?? null,
      }),
      signal: opts.signal,
    });
  } catch (e) {
    if ((e as Error)?.name === 'AbortError') throw e;
    throw new AiOfflineError(`无法连接内容服务（${base}）`, base);
  }

  if (res.status === 401) throw new AiAuthError();
  if (res.status === 429) {
    // 后端把"配额用尽"和"限流"都映射到 429，用 message 区分
    const payload = (await res.json().catch(() => null)) as { message?: string } | null;
    throw new AiQuotaError(payload?.message || '今日 AI 额度已用完');
  }
  if (!res.ok || !res.body) {
    const payload = (await res.json().catch(() => null)) as { message?: string } | null;
    throw new Error(payload?.message || `AI 服务返回 HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let answer = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // 按空行切帧；最后一段可能是不完整的半帧，留在 buffer 里等下一个 chunk
      let sep = buffer.indexOf('\n\n');
      while (sep !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        sep = buffer.indexOf('\n\n');

        const parsed = parseFrame(frame);
        if (!parsed) continue;

        if (parsed.event === 'meta') {
          try {
            opts.callbacks.onMeta?.(JSON.parse(parsed.data) as StreamMeta);
          } catch {
            /* 元信息解析失败不影响正文 */
          }
        } else if (parsed.event === 'delta') {
          try {
            const { text } = JSON.parse(parsed.data) as { text?: string };
            if (text) {
              answer += text;
              opts.callbacks.onDelta(text);
            }
          } catch {
            /* 单个坏帧直接跳过，不让整轮回答失败 */
          }
        } else if (parsed.event === 'error') {
          let msg = 'AI 生成失败';
          try {
            msg = (JSON.parse(parsed.data) as { message?: string }).message || msg;
          } catch {
            /* 保留默认文案 */
          }
          throw new Error(msg);
        } else if (parsed.event === 'done') {
          try {
            opts.callbacks.onDone?.(JSON.parse(parsed.data) as StreamDone);
          } catch {
            /* done 帧解析失败无所谓 */
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  return answer;
}
