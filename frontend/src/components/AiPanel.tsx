/**
 * AiPanel.tsx —— AI 助手对话面板（CppCat）
 *
 * 三处入口共用：侧导航 /ai 页、全局悬浮球、判题台「问 CppCat」（带上下文）。
 *
 * 后端：Python 服务端 /api/v1/ai/chat（SSE 流式，需登录）。协议细节与模式映射
 * 都收敛在 lib/aiChat.ts，本组件只负责状态与渲染。
 *
 * 三种状态必须让用户看得见，不能混成一个「加载中」：
 *   1. 未登录        → 明确提示去登录（后端要求身份才能计配额、落会话历史）
 *   2. 后端不可达    → 明确说连不上，并回退到本地引导（不伪装成真实回答）
 *   3. 生成中        → 流式增量渲染；中断后保留已生成的部分
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  AiAuthError,
  AiOfflineError,
  AiQuotaError,
  streamChat,
  type ChatTurn,
} from '../lib/aiChat';

export type AiMode =
  | 'socratic'
  | 'diagnose'
  | 'review'
  | 'plan'
  | 'dl'
  | 'interview';

const MODES: { key: AiMode; label: string }[] = [
  { key: 'socratic', label: '苏格拉底教学' },
  { key: 'diagnose', label: '编译诊断' },
  { key: 'review', label: '代码审查' },
  { key: 'plan', label: '学习计划' },
  { key: 'dl', label: 'DL 部署指导' },
  { key: 'interview', label: '模拟面试' },
];

/** 各模式开场白（未开始对话时的引导） */
const MODE_GREETING: Record<AiMode, string> = {
  socratic: '我是凯喵～ 直接说你在学哪一章、卡在哪个概念，我会用提问的方式帮你理顺思路（不直接给答案喵）。',
  diagnose: '把编译错误信息贴给我，或者直接在判题台点「问凯喵」，我帮你逐条解读 g++ / clang 的报错。',
  review: '把代码贴过来，我帮你查风格、内存安全、并发这些常见问题点。',
  plan: '告诉我你的目标（考研 / 求职 / DL 方向）和每天能投入的时间，我帮你排学习节奏。',
  dl: 'ONNX Runtime / TensorRT / LibTorch / llama.cpp 的部署问题都可以问我～',
  interview: '选一章开始模拟面试，我会像面试官一样多轮追问，最后给你评分报告。',
};

/**
 * 面板副标题：按模式说明「这一轮它答什么」。
 * 六种模式的答案边界完全不同，共用一个「苏格拉底式引导」会让诊断/面试两种模式
 * 显得名不副实（那两种本来就要给结论），所以按模式分开写。
 */
const MODE_SCOPE: Record<AiMode, string> = {
  socratic: '锚定课程内容回答 · 引导式，不直接给答案',
  diagnose: '读你的报错原文 · 逐条说清错在哪一行、为什么',
  review: '读你的代码 · 指问题不重写，改动由你决定',
  plan: '按你的进度与剩余时间排节奏 · 不承诺进度',
  dl: '部署与推理框架问题 · 环境差异会明说',
  interview: '多轮追问后出评分 · 追问不给提示',
};

/** 后端不可达时的本地引导（明确标注非 AI 生成，避免误导） */
function offlineFallback(mode: AiMode, question: string): string {
  const echo = question.length > 40 ? `${question.slice(0, 40)}…` : question;
  return (
    `【离线引导 · 非 AI 生成】\n` +
    `已收到你的问题（${MODES.find((m) => m.key === mode)?.label ?? mode} 模式）：\n「${echo}」\n\n` +
     `当前连不上内容服务，无法调用凯喵。你可以先：\n` +
    `· 去「练习」判题台跑代码，编译失败时点「问凯喵」会自动带上错误上下文\n` +
    `· 在「设置」里确认服务地址，或启动本机服务后重试`
  );
}

interface AiMsg {
  from: 'cat' | 'me';
  text: string;
  /** 正在流式输出的那条气泡，光标/省略号用 */
  streaming?: boolean;
}

/** 把历史消息压成后端要的 [{role, content}]，跳过开场白与空消息 */
function toHistory(msgs: AiMsg[]): ChatTurn[] {
  return msgs
    .filter((m) => m.text.trim() && !m.streaming)
    .slice(-8)
    .map((m) => ({ role: m.from === 'me' ? 'user' : 'assistant', content: m.text }));
}

function hasToken(): boolean {
  if (typeof localStorage === 'undefined') return false;
  return Boolean(localStorage.getItem('nex.accessToken'));
}

export function AiPanel({
  initialContext,
  initialMode,
  onClose,
  embedded = false,
  onRequireLogin,
}: {
  initialContext?: string;
  initialMode?: AiMode;
  onClose?: () => void;
  /** embedded=true 用于 /ai 页内嵌大面板（无遮罩、无关闭钮由外层控制） */
  embedded?: boolean;
  /** 未登录时「去登录」的跳转，由外层传 navigate('me') */
  onRequireLogin?: () => void;
}) {
  const [mode, setMode] = useState<AiMode>(initialMode ?? 'socratic');
  const [context, setContext] = useState<string | undefined>(initialContext);
  const [msgs, setMsgs] = useState<AiMsg[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [quota, setQuota] = useState<number | null>(null);
  const [signedIn, setSignedIn] = useState(hasToken);
  const listRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  /** 会话 id：首轮由后端创建，后续带上以续写同一条会话 */
  const convRef = useRef<number | null>(null);

  /* 模式 / 上下文变化时重置会话并附上猫咪开场白 */
  useEffect(() => {
    setContext(initialContext);
    setMsgs([{ from: 'cat', text: MODE_GREETING[initialMode ?? mode] }]);
    setNotice('');
    convRef.current = null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialContext, initialMode]);

  /* 切模式：换开场白并丢弃会话（不同模式的上下文不混用） */
  const switchMode = (next: AiMode) => {
    abortRef.current?.abort();
    setMode(next);
    setMsgs([{ from: 'cat', text: MODE_GREETING[next] }]);
    setNotice('');
    convRef.current = null;
  };

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [msgs]);

  /* 卸载时中断在途请求，避免内存泄漏与「关掉面板还在烧 token」 */
  useEffect(() => () => abortRef.current?.abort(), []);

  const appendDelta = useCallback((text: string) => {
    setMsgs((prev) => {
      if (!prev.length) return prev;
      const next = [...prev];
      const last = next[next.length - 1];
      if (last.from === 'cat' && last.streaming) {
        next[next.length - 1] = { ...last, text: last.text + text };
      }
      return next;
    });
  }, []);

  const send = async () => {
    const q = draft.trim();
    if (!q || busy) return;

    // 未登录：不发请求（后端必然 401），直接引导
    if (!hasToken()) {
      setSignedIn(false);
      setNotice('AI 助手需要登录后使用：配额、会话历史与错题上下文都绑定在你的账号上。');
      return;
    }
    setSignedIn(true);
    setDraft('');
    setNotice('');
    setBusy(true);

    const history = toHistory(msgs);
    setMsgs((prev) => [
      ...prev,
      { from: 'me', text: q },
      { from: 'cat', text: '', streaming: true },
    ]);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      await streamChat({
        mode,
        message: context ? `${context}\n\n${q}` : q,
        history,
        conversationId: convRef.current,
        signal: ctrl.signal,
        callbacks: {
          onMeta: (m) => {
            if (m.conversation_id) convRef.current = m.conversation_id;
          },
          onDelta: appendDelta,
          onDone: (d) => {
            if (typeof d.quota_left === 'number') setQuota(d.quota_left);
          },
        },
      });
    } catch (e) {
      const err = e as Error;

      // 用户主动中断：保留已生成内容，不算错误
      if (err?.name === 'AbortError') {
        // 落空
      } else if (e instanceof AiAuthError) {
        setSignedIn(false);
        setNotice('登录状态已失效，请重新登录后再问凯喵。');
        setMsgs((prev) => prev.slice(0, -1));
      } else if (e instanceof AiQuotaError) {
        setNotice(err.message || '今日 AI 额度已用完，明天再来或升级套餐。');
        setMsgs((prev) => prev.slice(0, -1));
      } else if (e instanceof AiOfflineError) {
        setNotice('连不上内容服务，已回退本地引导。启动服务后重试可获得真实回答。');
        setMsgs((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.from === 'cat' && last.streaming) {
            next[next.length - 1] = { from: 'cat', text: offlineFallback(mode, q) };
          }
          return next;
        });
      } else {
        setNotice(err.message || 'AI 生成失败，请稍后重试。');
        setMsgs((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.from === 'cat' && last.streaming) {
            next[next.length - 1] = {
              from: 'cat',
              text: last.text || '这次没有生成成功，可以重新问一次，或换个模式试试。',
            };
          }
          return next;
        });
      }
    } finally {
      // 结束流式标记（无论是正常完成、中断还是报错）
      setMsgs((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.from === 'cat' && last.streaming) {
          next[next.length - 1] = { ...last, streaming: false };
        }
        return next;
      });
      abortRef.current = null;
      setBusy(false);
    }
  };

  const stop = () => {
    abortRef.current?.abort();
  };

  const body = (
    <>
      <div className="ai-panel-head">
        <img src="/assets/cppcat-avatar.png" alt="" />
        <div>
          <div className="ai-panel-title">凯喵 · 学习助手</div>
          {/*
            这行不是装饰。用户第一次打开时只想知道两件事：它答什么、它凭什么答。
            「锚定课程与题库」对应后端的 retrieved 注入（见 server/app/api/v1/ai.py
            chat 里的 index.retrieve），不是宣传语——说不了这句就别写。
          */}
          <div className="ai-panel-sub">
            {MODE_SCOPE[mode]}
            {quota !== null && ` · 今日剩余 ${quota} 次`}
          </div>
        </div>
        {onClose && (
          <button type="button" onClick={onClose} aria-label="关闭 AI 面板">
            ✕
          </button>
        )}
      </div>

      <div className="ai-modes" role="tablist" aria-label="AI 模式">
        {MODES.map((m) => (
          <button
            key={m.key}
            type="button"
            role="tab"
            aria-selected={m.key === mode}
            className={`ai-mode-chip${m.key === mode ? ' active' : ''}`}
            onClick={() => switchMode(m.key)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {!signedIn && (
        <div className="ai-msg-context" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ flex: 1 }}>未登录：AI 回答需要登录后使用（本地题库与判题不受影响）。</span>
          {onRequireLogin && (
            <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={onRequireLogin}>
              去登录
            </button>
          )}
        </div>
      )}

      {notice && (
        <div className="ai-msg-context" role="status">
          {notice}
        </div>
      )}

      <div className="ai-msgs" ref={listRef}>
        {context && (
          <div className="ai-msg-context">
            已带入上下文：{context.length > 80 ? `${context.slice(0, 80)}…` : context}
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`ai-msg ${m.from === 'cat' ? 'ai-msg-cat' : 'ai-msg-me'}`}>
            {m.from === 'cat' && <img src="/assets/cppcat-avatar.png" alt="" />}
            <div className="ai-bubble">
              {m.text || (m.streaming ? '正在思考…' : '')}
              {m.streaming && m.text ? ' ▍' : ''}
            </div>
          </div>
        ))}
      </div>

      <div className="ai-input-row">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !busy) void send();
          }}
          placeholder={busy ? '凯喵正在回答…' : `AI 助手 · ${MODES.find((m) => m.key === mode)?.label ?? ''}…（Enter 发送）`}
          aria-label="AI 对话输入框"
          disabled={busy}
        />
        {busy ? (
          <button type="button" onClick={stop}>
            停止
          </button>
        ) : (
          <button type="button" onClick={() => void send()}>
            发送
          </button>
        )}
      </div>
    </>
  );

  if (embedded) {
    return (
      <div className="card" style={{ padding: 0, overflow: 'hidden', height: 560 }}>
        {body}
      </div>
    );
  }

  return <div className="ai-panel">{body}</div>;
}

export default AiPanel;
