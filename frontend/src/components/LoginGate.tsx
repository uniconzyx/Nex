/**
 * LoginGate.tsx —— 启动强制登录网关
 *
 * 打开 App 第一时间要求登录：未登录即展示全屏网关，登录后才进入主界面。
 * 同时保留「本地模式 / 稍后体验」兜底——后端不可用时绝不 brick 整个 App，
 * 用户点一下即可进入本机模式（进度照常、仅缺云端同步）。
 *
 * 网关用 LoginForm（与账号抽屉同一份逻辑），所以登录成功会自动关掉自己。
 */
import { LoginForm } from './LoginForm';

interface Props {
  /** 用户选择本地模式，绕过登录直接进入 */
  onLocalMode: () => void;
}

export function LoginGate({ onLocalMode }: Props) {
  return (
    <div className="km-gate" role="dialog" aria-modal="true" aria-label="登录以继续使用">
      <div className="km-gate-card km-glass">
        <div className="km-gate-brand">
          <img src="/assets/kaimao/mood-happy.png" alt="凯喵" />
          <div>
            <b>凯喵Code试炼录</b>
            <span>登录后即可同步进度、收服怪物、挑战 BOSS</span>
          </div>
        </div>

        <LoginForm onSuccess={() => { /* 状态变 online，外层会自动收起网关 */ }} />

        <button type="button" className="km-gate-skip" onClick={onLocalMode}>
          稍后体验（本地模式）
        </button>
        <p className="km-gate-note">
          本地模式下进度仅存本机，功能完整可用；随时可在「我的 → 账号管理」登录同步。
        </p>
      </div>
    </div>
  );
}

export default LoginGate;
