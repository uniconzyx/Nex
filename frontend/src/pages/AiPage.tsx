/**
 * AiPage.tsx —— AI 助手一级入口页（PRD §7 页面 16：/ai）
 *
 * 内嵌大版 AiPanel；右侧说明 6 种模式各自干什么。
 * 对话走后端 /api/v1/ai/chat（SSE 流式），需要登录；未登录时面板内会给出「去登录」。
 */
import { AiPanel } from '../components/AiPanel';
import type { AiMode } from '../components/AiPanel';
import { useSession } from '../lib/session';
import type { KmPage } from '../lib/nav';

const CAPABILITIES: { mode: AiMode; title: string; desc: string }[] = [
  { mode: 'socratic', title: '苏格拉底教学', desc: '只引导不给答案，顺着你的思路追问' },
  { mode: 'diagnose', title: '编译诊断', desc: 'g++/clang 报错逐条解读，规则库优先' },
  { mode: 'review', title: '代码审查', desc: '风格 / 内存安全 / 并发问题检查' },
  { mode: 'plan', title: '学习计划', desc: '按目标方向 + 进度 + 每日时间生成节奏' },
  { mode: 'dl', title: 'DL 部署指导', desc: 'ONNX / TensorRT / LibTorch / llama.cpp' },
  { mode: 'interview', title: '模拟面试', desc: '多轮追问 + 评分报告' },
];

export function AiPage({ onNavigate }: { onNavigate?: (p: KmPage) => void }) {
  const s = useSession();

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 260px', gap: 16 }}>
      <AiPanel embedded onRequireLogin={onNavigate ? () => onNavigate('me') : undefined} />

      <aside style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <section className="card">
          <h2 className="card-title">凯喵能做的六件事</h2>
          {CAPABILITIES.map((c) => (
            <div key={c.mode} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{c.title}</div>
              <div style={{ fontSize: 12, color: 'var(--nex-text-2)' }}>{c.desc}</div>
            </div>
          ))}
        </section>

        <section className="card">
          <h2 className="card-title">当前状态</h2>
          <p style={{ fontSize: 12, color: 'var(--nex-text-2)', margin: 0 }}>
            {s.status === 'online'
              ? '已登录：回答由真实模型流式生成，并锚定课程章节与题库依据；每日剩余额度显示在面板顶部。'
              : s.status === 'offline'
                ? '连不上内容服务：凯喵暂不可用，会回退为本地引导。本地题库与判题不受影响。'
                : '未登录：登录后即可使用。配额与会话历史绑定账号，登录入口在「个人闯关档案」。'}
          </p>
          {s.status !== 'online' && onNavigate && (
            <button
              type="button"
              className="km-btn km-btn-ghost km-btn-sm"
              style={{ marginTop: 10 }}
              onClick={() => onNavigate('me')}
            >
              去登录 / 检查连接
            </button>
          )}
        </section>
      </aside>
    </div>
  );
}

export default AiPage;
