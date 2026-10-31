/**
 * LongPressPreview.tsx —— 长按预览浮层（统一「长按看详情」交互）
 *
 * 包裹任意元素；指针长按时在锚点附近浮出只读小卡（不挡操作、pointer-events:none），
 *   再次点击 / 滚动 / Esc 即收起。与点击各自的 onClick 互不干扰：
 *   长按触发后，本次抬手产生的 click 会被吞掉，避免「刚弹出又立刻被关」。
 * 鼠标与触摸统一走 Pointer 事件。
 */
import { useEffect, useRef, useState } from 'react';
import { useLongPress } from '../lib/hooks/useLongPress';

interface Props {
  children: React.ReactNode;
  /** 浮层内容；长按时调用一次 */
  render: () => React.ReactNode;
  delay?: number;
  ariaLabel?: string;
}

export function LongPressPreview({ children, render, delay = 380, ariaLabel }: Props) {
  const [pos, setPos] = useState<{ x: number; y: number; below: boolean } | null>(null);
  const anchorRef = useRef<HTMLSpanElement | null>(null);
  const didLong = useRef(false);

  const show = () => {
    const el = anchorRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const below = r.top < 140;
    const x = Math.min(Math.max(r.left + r.width / 2, 12), window.innerWidth - 12);
    const y = below ? r.bottom + 8 : r.top - 8;
    didLong.current = true;
    setPos({ x, y, below });
  };

  const lp = useLongPress(show, { ms: delay });

  // 浮层出现后：点击别处 / 滚动 / Esc 都收起
  useEffect(() => {
    if (!pos) return;
    const close = () => setPos(null);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    window.addEventListener('scroll', close, { passive: true, capture: true });
    window.addEventListener('pointerdown', close);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('scroll', close, { capture: true } as EventListenerOptions);
      window.removeEventListener('pointerdown', close);
      window.removeEventListener('keydown', onKey);
    };
  }, [pos]);

  const onClick = (e: React.MouseEvent) => {
    if (didLong.current) {
      // 长按后的那次 click 吞掉，避免立刻关闭
      didLong.current = false;
      e.preventDefault();
      e.stopPropagation();
    }
  };

  return (
    <>
      <span ref={anchorRef} className="km-lp-anchor" aria-label={ariaLabel} {...lp} onClick={onClick}>
        {children}
      </span>
      {pos && (
        <div
          className="km-lp-pop"
          role="tooltip"
          style={{
            left: pos.x,
            top: pos.y,
            transform: `translate(-50%, ${pos.below ? '0' : '-100%'})`,
          }}
        >
          {render()}
        </div>
      )}
    </>
  );
}

export default LongPressPreview;
