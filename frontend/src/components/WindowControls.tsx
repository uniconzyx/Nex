/**
 * WindowControls.tsx —— EXE 桌面端窗口控件（最小化 / 最大化 / 关闭）
 *
 * 只在 Tauri 桌面端生效：浏览器里 `isTauri()` 为 false，按钮点下去会提示
 * 「仅桌面端可用」——不给一个点了没反应的按钮，也不假装在浏览器里能关窗。
 *
 * 权限：Tauri v2 需要在 src-tauri/capabilities/default.json 里显式允许
 *   core:window:allow-minimize / allow-toggle-maximize / allow-close / allow-is-maximized
 */
import { useEffect, useState } from 'react';

import { isTauri } from '@tauri-apps/api/core';
import { getCurrentWindow } from '@tauri-apps/api/window';

import { pushToast } from '../lib/feedback';

export function WindowControls() {
  const [desktop, setDesktop] = useState(false);
  const [maxed, setMaxed] = useState(false);

  useEffect(() => {
    const ok = isTauri();
    setDesktop(ok);
    if (!ok) return;
    getCurrentWindow()
      .isMaximized()
      .then(setMaxed)
      .catch(() => {});
  }, []);

  const notDesktop = () => {
    pushToast({ kind: 'info', title: '窗口控件仅在 EXE 桌面端可用', desc: '浏览器与 APK 版没有系统窗口。' });
  };

  const minimize = () => {
    if (!desktop) return notDesktop();
    getCurrentWindow().minimize().catch(() => {});
  };
  const toggleMaximize = () => {
    if (!desktop) return notDesktop();
    getCurrentWindow()
      .toggleMaximize()
      .then(() => getCurrentWindow().isMaximized().then(setMaxed).catch(() => {}))
      .catch(() => {});
  };
  const close = () => {
    if (!desktop) return notDesktop();
    getCurrentWindow().close().catch(() => {});
  };

  return (
    <div className="km-win" role="group" aria-label="窗口控件">
      <button type="button" className="km-win-btn" onClick={minimize} aria-label="最小化" title="最小化">
        <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
          <line x1="2.5" y1="9.5" x2="9.5" y2="9.5" />
        </svg>
      </button>
      <button
        type="button"
        className="km-win-btn"
        onClick={toggleMaximize}
        aria-label={maxed ? '还原' : '最大化'}
        title={maxed ? '还原' : '最大化'}
      >
        <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
          {maxed ? (
            <>
              <rect x="2.5" y="4.5" width="7" height="5" rx="1" />
              <path d="M4.2 4.5V3.4a1 1 0 0 1 1-1h3.4a1 1 0 0 1 1 1v3.4a1 1 0 0 1-1 1H7.5" />
            </>
          ) : (
            <rect x="2.5" y="2.5" width="7" height="7" rx="1" />
          )}
        </svg>
      </button>
      <button type="button" className="km-win-btn is-close" onClick={close} aria-label="关闭" title="关闭">
        <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
          <line x1="3" y1="3" x2="9" y2="9" />
          <line x1="9" y1="3" x2="3" y2="9" />
        </svg>
      </button>
    </div>
  );
}
