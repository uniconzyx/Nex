/**
 * ZoomLightbox.tsx —— 通用可缩放查看器（图片 / SVG / 文本结构图）
 * ============================================================================
 * 解决「图标/图表点不了、看不清」：任意可点元素点一下弹出全屏查看器，
 * 支持放大 / 缩小 / 复位 / 拖拽平移 / 滚轮缩放 / Esc 关闭 / 点击遮罩关闭。
 *
 * 设计约束（沿用既有冰蓝体系，不引入新色源）：
 *   - 只用 --km-* 变量；遮罩用中性深色（只在浮层上，符合"阴影只给真正浮起的东西"）
 *   - 内容用 transform: scale + translate，不改布局，避免重排抖动
 *   - 尊重 prefers-reduced-motion：过渡关掉，功能保留
 *   - 关闭时恢复 body 滚动，键盘可聚焦
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import './ZoomLightbox.css';

const MIN = 0.5;
const MAX = 5;
const STEP = 0.25;

export interface ZoomLightboxProps {
  open: boolean;
  onClose: () => void;
  /** 标题，显示在顶部工具栏 */
  title?: string;
  /** 图片地址（与 children 二选一） */
  src?: string;
  alt?: string;
  /** 任意可缩放内容：SVG、<pre> 结构图、文本等 */
  children?: React.ReactNode;
}

export function ZoomLightbox({ open, onClose, title, src, alt, children }: ZoomLightboxProps) {
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  const reset = useCallback(() => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  }, []);

  // 打开时复位并锁滚动；关闭时恢复
  useEffect(() => {
    if (!open) return;
    reset();
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open, reset]);

  // Esc 关闭 / +/- 缩放 / 0 复位
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === '+' || e.key === '=') setScale((s) => Math.min(MAX, +(s + STEP).toFixed(2)));
      else if (e.key === '-' || e.key === '_') setScale((s) => Math.max(MIN, +(s - STEP).toFixed(2)));
      else if (e.key === '0') reset();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose, reset]);

  const zoom = (delta: number) => setScale((s) => Math.max(MIN, Math.min(MAX, +(s + delta).toFixed(2))));

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    zoom(e.deltaY < 0 ? STEP : -STEP);
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if (scale <= 1) return;
    dragRef.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    const d = dragRef.current;
    if (!d) return;
    setOffset({ x: d.ox + (e.clientX - d.x), y: d.oy + (e.clientY - d.y) });
  };
  const onPointerUp = () => {
    dragRef.current = null;
  };

  if (!open) return null;

  return (
    <div
      className="zl-root"
      role="dialog"
      aria-modal="true"
      aria-label={title || '放大查看'}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="zl-bar">
        <span className="zl-title">{title || '放大查看'}</span>
        <div className="zl-actions">
          <button type="button" onClick={() => zoom(-STEP)} aria-label="缩小" title="缩小（-）">−</button>
          <span className="zl-pct">{Math.round(scale * 100)}%</span>
          <button type="button" onClick={() => zoom(STEP)} aria-label="放大" title="放大（+）">＋</button>
          <button type="button" onClick={reset} aria-label="复位" title="复位（0）">复位</button>
          <button type="button" className="zl-close" onClick={onClose} aria-label="关闭" title="关闭（Esc）">✕</button>
        </div>
      </div>
      <div
        className="zl-stage"
        ref={stageRef}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        style={{ cursor: scale > 1 ? (dragRef.current ? 'grabbing' : 'grab') : 'default' }}
      >
        <div
          className="zl-content"
          style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})` }}
        >
          {src ? <img src={src} alt={alt ?? title ?? ''} draggable={false} /> : children}
        </div>
      </div>
      <div className="zl-tip">滚轮或 ＋/− 缩放 · 放大后可拖拽 · 0 复位 · Esc 关闭</div>
    </div>
  );
}

export default ZoomLightbox;
