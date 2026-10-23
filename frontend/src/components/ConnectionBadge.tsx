/**
 * ConnectionBadge.tsx —— 顶栏后端连接指示灯
 *
 * 打通后端之后，「页面一直转圈」最大的成因就是后端没起。
 * 顶栏常驻一个小圆点，让用户一眼看出服务通没通，点一下直达设置页去修。
 *
 * 三态：
 *   online  → 绿点，悬停显示后端版本与可用能力
 *   offline → 红点，悬停提示怎么修（点开设置）
 *   unknown → 灰点，正在探测
 */
import { useConnection, describeCapabilities } from '../lib/connection';

export function ConnectionBadge({ onNavigate }: { onNavigate: (page: 'settings') => void }) {
  const conn = useConnection();
  const h = conn.health;

  const label =
    conn.status === 'online'
      ? `后端已连接 · ${describeCapabilities(h)}`
      : conn.status === 'offline'
        ? '后端未连接 · 点击去设置里检查服务地址'
        : '正在检测后端…';

  const title =
    conn.status === 'online' && h?.backend
      ? `${label}\n${h.backend.name} v${h.backend.version}`
      : label;

  return (
    <button
      type="button"
      className={`km-conn-badge ${conn.status}`}
      title={title}
      aria-label={title}
      onClick={() => onNavigate('settings')}
    >
      <i />
    </button>
  );
}
