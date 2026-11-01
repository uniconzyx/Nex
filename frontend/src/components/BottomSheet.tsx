/**
 * BottomSheet.tsx —— 底部上滑弹窗（统一次级操作载体）
 *
 * 设计：磨砂玻璃 + 14px 顶部圆角 + 柔和阴影（复用既有 --km-* 令牌），
 *   · 抓手 drag-to-dismiss（拖动超过阈值即关闭，未达阈值回弹）
 *   · 点击遮罩 / 关闭键 / Esc 关闭
 *   · 打开时锁背景滚动
 *   · 尊重 prefers-reduced-motion（关掉位移动画，仅淡入）
 * 这是 S1–S12 所有「Build / 词条 / 事件 / 派遣 / 合成 / 复盘 / 赛季」弹层的标准底座。
 */
import { useCallback, useEffect, useRef, useState } from 'react';

interface Props {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  /** 套到 sheet 框的额外类（如复用已有 km-nav-sheet 栅格样式） */
  className?: string;
  /** 套到内容区的额外类 */
  bodyClassName?: string;
  ariaLabel?: string;
}

const DISMISS_PX = 110;

export function BottomSheet({
  open,
  onClose,
  title,
  children,
  className = '',
  bodyClassName = '',
  ariaLabel,
}: Props) {
  const [dragY, setDragY] = useState(0);
  const [dragging, setDragging] = useState(false);
  const startY = useRef(0);

  useEffect(() => {
    if (!open) {
      setDragY(0);
      setDragging(false);
    }
  }, [open]);

  // 打开时锁定背景滚动，避免弹层内滚动带动整页
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Esc 关闭：弹层是模态，键盘用户必须能退出去（原来只有点遮罩和点叉）
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const onGrabDown = useCallback((e: React.PointerEvent) => {
    startY.current = e.clientY;
    setDragging(true);
    (e.target as Element).setPointerCapture?.(e.pointerId);
  }, []);

  const onGrabMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging) return;
      setDragY(Math.max(0, e.clientY - startY.current));
    },
    [dragging],
  );

  const onGrabUp = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging) return;
      const dy = e.clientY - startY.current;
      setDragging(false);
      if (dy > DISMISS_PX) {
        setDragY(0);
        onClose();
      } else {
        setDragY(0);
      }
    },
    [dragging, onClose],
  );

  if (!open) return null;

  return (
    <>
      <div className="km-sheet-scrim" onClick={onClose} aria-hidden="true" />
      <div
        className={`km-sheet ${className}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel ?? (typeof title === 'string' ? title : '弹窗')}
        style={{
          transform: dragY ? `translateY(${dragY}px)` : undefined,
          transition: dragging ? 'none' : undefined,
        }}
      >
        <div
          className="km-sheet-grab"
          onPointerDown={onGrabDown}
          onPointerMove={onGrabMove}
          onPointerUp={onGrabUp}
          onPointerCancel={onGrabUp}
          aria-hidden="true"
        />
        <div className="km-sheet-head">
          <b>{title}</b>
          <button type="button" onClick={onClose} aria-label="关闭">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <div className={`km-sheet-body km-scroll-hide ${bodyClassName}`.trim()}>{children}</div>
      </div>
    </>
  );
}

export default BottomSheet;
