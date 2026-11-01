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
      {/* 背景层：冰蓝弥散光晕 + 漂浮的六边形符文，纯装饰不参与阅读 */}
      <div className="km-gate-bg" aria-hidden="true">
        <i />
        <i />
        <span className="km-gate-rune r1" />
        <span className="km-gate-rune r2" />
        <span className="km-gate-rune r3" />
        <span className="km-gate-rune r4" />
      </div>

      <div className="km-gate-card">
        <div className="km-gate-hero">
          <div className="km-gate-avatar">
            <img src="/assets/kaimao/mood-happy.png" alt="凯喵" />
            <span className="km-gate-ring" aria-hidden="true" />
          </div>
          <h1>凯喵Code试炼录</h1>
          <p>登录后同步进度、收服怪物、挑战周 BOSS</p>
        </div>

        <LoginForm onSuccess={() => { /* 状态变 online，外层会自动收起网关 */ }} />

        <button type="button" className="km-gate-skip" onClick={onLocalMode}>
          先逛逛 · 本地模式
        </button>
        <p className="km-gate-note">
          本地模式下进度仅存本机，功能完整可用；随时可在「我的 → 账号管理」登录同步。
        </p>
      </div>
    </div>
  );
}

export default LoginGate;
