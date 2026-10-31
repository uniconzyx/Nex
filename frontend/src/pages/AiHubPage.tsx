/**
 * AiHubPage.tsx —— 「AI 助手」一级入口（#ai）
 * ============================================================================
 * 2026-10-30 主人定：把原来的两个导航项「问凯喵」(#ai) 与「凯喵陪练」(#agent)
 * 合到一处，叫「AI 助手」。
 *
 * 为什么是 tab 而不是合成一个页面：
 *   两者是两种交互范式，不是同一个功能的两种皮肤——
 *     · 问凯喵：问一句答一句，答案不可验证；
 *     · 陪练：跑一个循环，每步调真实工具，报告里每个数字都能追到某一步。
 *   硬融会做出一个「既不能连续追问、也不能完整跑完」的四不像。
 *   所以保留两套实现，只在入口层用 tab 收拢。
 *
 * 两个面板都常驻挂载、用 hidden 切换：切回来时对话上下文、陪练已跑完的
 * 执行轨迹都还在，不会因为点了下 tab 就白跑一次。
 * ============================================================================
 */
import { useState } from 'react';

import type { KmPage } from '../lib/nav';
import { AiPage } from './AiPage';
import { AgentPage } from './AgentPage';
import './AiHubPage.css';

type AiTab = 'chat' | 'coach';

const TABS: { key: AiTab; label: string; hint: string }[] = [
  { key: 'chat', label: '问凯喵', hint: '问一句答一句 · 六种模式' },
  { key: 'coach', label: '凯喵陪练', hint: '跑完整循环 · 出可核对报告' },
];

export function AiHubPage({ onNavigate }: { onNavigate?: (p: KmPage) => void }) {
  const [tab, setTab] = useState<AiTab>('chat');

  return (
    <div className="aih-root">
      <header className="aih-head">
        <h1>AI 助手</h1>
        <p className="aih-lede">
          两种用法：「问凯喵」适合随时抛一个问题过去；「凯喵陪练」会真的把诊断跑完，出一份每个数字都能核对报告。
        </p>
      </header>

      <div className="aih-tabs" role="tablist" aria-label="AI 助手模式">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            id={`aih-tab-${t.key}`}
            aria-selected={tab === t.key}
            aria-controls={`aih-panel-${t.key}`}
            className={`aih-tab${tab === t.key ? ' on' : ''}`}
            onClick={() => setTab(t.key)}
          >
            <b>{t.label}</b>
            <span>{t.hint}</span>
          </button>
        ))}
      </div>

      <div
        className="aih-panel"
        id="aih-panel-chat"
        role="tabpanel"
        aria-labelledby="aih-tab-chat"
        hidden={tab !== 'chat'}
      >
        <AiPage onNavigate={onNavigate} />
      </div>

      <div
        className="aih-panel"
        id="aih-panel-coach"
        role="tabpanel"
        aria-labelledby="aih-tab-coach"
        hidden={tab !== 'coach'}
      >
        <AgentPage />
      </div>
    </div>
  );
}
