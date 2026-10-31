/**
 * CppCatFab.tsx —— AI 助手全局悬浮入口（PRD §6「全局唤起」）
 *
 * 形态演进（主人 2026-10-30 定）：
 *   原来是「凯喵头像 + 问凯喵 + 一句副标题」的长条胶囊。
 *   主人要求「只保留这一个入口，把长条按钮改成悬浮球」——所以现在是圆形球：
 *     · 直径 58px（手机 52px），只有凯喵脸 + 一颗状态点；
 *     · 文字不再常驻，改成 hover / 键盘聚焦时浮出的气泡（data-tip），
 *       既守住「一眼能看出这是能问问题的地方」，又不占横向空间。
 *
 * 术语（2026-10-30 统一）：导航项叫「AI 助手」，入口气泡也叫「AI 助手」，
 * 不再一处叫「AI 助手」一处叫「问凯喵」。而「问凯喵 / 凯喵陪练」保留为
 * AI 助手页内的两个子功能名——它们描述的是两种用法，不是入口。
 *
 * 入口清单（共用本文件的文案）：
 *   · 悬浮球（本文件）
 *   · 侧导航「AI 助手」（lib/nav.ts）
 *   · 右栏凯喵立绘点击（KaimaoShell.tsx）
 * 改文案时一起看，别只改一处。
 */

/** 悬浮入口的说明：hover 气泡与 title 共用，一眼可辨，不做悬念 */
export const AI_ENTRY_LABEL = 'AI 助手';
export const AI_ENTRY_HINT = '苏格拉底式 · 不直接给答案';
export const AI_ENTRY_ARIA = '唤起 AI 助手';

import type { PointerEvent as ReactPointerEvent } from 'react';

export function CppCatFab({
  onClick,
  active,
  onPress,
}: {
  onClick: () => void;
  active: boolean;
  /** 按下瞬间（pointerdown）触发，用于谐振粒子等反馈；不影响 onClick 打开面板 */
  onPress?: (e: ReactPointerEvent<HTMLButtonElement>) => void;
}) {
  return (
    <button
      type="button"
      className={`ai-fab${active ? ' is-open' : ''}`}
      onClick={onClick}
      onPointerDown={onPress}
      aria-label={AI_ENTRY_ARIA}
      aria-expanded={active}
      title={active ? '收起凯喵对话面板' : `${AI_ENTRY_LABEL} — ${AI_ENTRY_HINT}`}
      data-tip={active ? '收起' : AI_ENTRY_LABEL}
    >
      <span className="ai-fab-face">
        <img src="/assets/cppcat-avatar.png" alt="" />
        {!active && <span className="ai-fab-dot" aria-hidden="true" />}
      </span>
    </button>
  );
}

export default CppCatFab;
