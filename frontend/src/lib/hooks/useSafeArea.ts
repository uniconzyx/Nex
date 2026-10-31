/**
 * useSafeArea.ts —— 手机安全区适配
 *
 * 返回统一的工具类名；组件也可直接用 `env(safe-area-inset-*)`。
 * 刘海/挖孔屏下，顶栏、底部 FAB、底部弹窗都靠它留出安全边距。
 */
export const SAFE_AREA_CLASS = 'km-safe-area';

export function useSafeArea(): string {
  return SAFE_AREA_CLASS;
}
