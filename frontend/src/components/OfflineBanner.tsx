/**
 * OfflineBanner.tsx —— 全局「后端未连接」提示（单行条，不是三行横幅）
 *
 * 演变原因（2026-10-30 UI 评审）：原先是一块三行的横幅，贴在每个页面内容区顶部，
 * 还 sticky。它把首屏最好的一块位置拿去显示「运维信息」，而且 uvicorn 那行命令
 * 对普通用户毫无用处——那是给自己看的。结果每页首屏都被它切一刀。
 *
 * 现在压成一行（高约 40px）：
 *   [红点] 后端未连接 · 127.0.0.1:8000   [重试] [怎么修]
 * 把「怎么修」折进一个 details：需要的人点开，不需要的人不被挡。
 *
 * 视觉仍只用 km-* 令牌：底色 --km-surf1、左描边 --km-bad、圆角 --km-r-sm。
 */
import { useState } from 'react';
import { useConnection } from '../lib/connection';

export function OfflineBanner({ onNavigate }: { onNavigate: (page: 'settings') => void }) {
  const conn = useConnection();
  const [open, setOpen] = useState(false);
  // unknown 是「刚启动、正在探测」，不是「不通」，不提示。
  if (conn.status !== 'offline') return null;

  const base = conn.base ?? '（尚未确定地址）';
  const times = conn.failures;

  return (
    <div className="km-offline" role="status" data-testid="offline-banner">
      <div className="km-offline-row">
        <span className="km-offline-dot" aria-hidden="true" />
        <b>后端未连接</b>
        <code className="km-offline-base" title={base}>
          {base}
        </code>
        {times > 1 && <span className="km-offline-times">已重试 {times} 次</span>}
        <span className="km-offline-spacer" />
        <button
          type="button"
          className="km-btn km-btn-primary km-btn-sm"
          disabled={conn.checking}
          data-testid="offline-retry"
          onClick={() => {
            void conn.retry();
          }}
        >
          {conn.checking ? '重试中…' : '重试'}
        </button>
        <button
          type="button"
          className="km-btn km-btn-ghost km-btn-sm"
          data-testid="offline-help"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? '收起' : '怎么修'}
        </button>
      </div>

      {open && (
        <div className="km-offline-help">
          <p>
            内容服务没起时，学习进度、判题、陪练都能用本地数据，只有需要服务端的功能（账号同步 /
            云端判题 / AI 对话）不可用。
          </p>
          <p>
            在 <code>server</code> 目录执行{' '}
            <code>uvicorn app.main:app --host 127.0.0.1 --port 8000</code> 即可；
            地址不对就去{' '}
            <button type="button" className="km-offline-link" onClick={() => onNavigate('settings')}>
              设置 → 内容服务
            </button>
            改。
          </p>
        </div>
      )}
    </div>
  );
}
