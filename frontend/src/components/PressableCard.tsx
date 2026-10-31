/**
 * PressableCard.tsx —— 按压下沉 + 柔光 的统一卡片外壳
 *
 * 任何「可点 / 可拖」的列表项、卡片、按钮都套它，保证全站按下反馈一致：
 *   · 按下 → 轻微下沉 + 冰蓝柔光环（见 interaction.css 的 .km-press）
 *   · 键盘可达：div 形态也支持 Enter / Space 触发
 * 不改视觉外观，只加交互反馈层。
 */
import type { CSSProperties, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  as?: 'div' | 'button';
  style?: CSSProperties;
  ariaLabel?: string;
  title?: string;
}

export function PressableCard({
  children,
  onClick,
  className = '',
  as = 'div',
  style,
  ariaLabel,
  title,
}: Props) {
  const cls = `km-press${onClick ? ' km-press--click' : ''} ${className}`.trim();

  const onKey = (e: React.KeyboardEvent) => {
    if (onClick && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onClick();
    }
  };

  if (as === 'button') {
    return (
      <button type="button" className={cls} onClick={onClick} style={style} aria-label={ariaLabel} title={title}>
        {children}
      </button>
    );
  }

  return (
    <div
      className={cls}
      onClick={onClick}
      style={style}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={ariaLabel}
      title={title}
      onKeyDown={onClick ? onKey : undefined}
    >
      {children}
    </div>
  );
}

export default PressableCard;
