/**
 * AccountDrawer.tsx —— 顶部 / 「我的」页点开后的登录 / 注册抽屉
 *
 * 表单逻辑统一收口到 LoginForm（单一事实来源）；本组件只负责把它装进底部抽屉。
 * 进度仍以本机为准，账号仅用于多端同步——未登录 / 离线都能用全部功能。
 */
import { BottomSheet } from './BottomSheet';
import { LoginForm } from './LoginForm';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function AccountDrawer({ open, onClose }: Props) {
  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      title="账号 · 登录 / 注册"
      className="km-account-drawer"
      ariaLabel="账号登录与注册"
    >
      <LoginForm onSuccess={onClose} />
    </BottomSheet>
  );
}

export default AccountDrawer;
