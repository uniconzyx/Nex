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
 *
 * 必须 Portal 到 body：.km-app / .km-card 上的 backdrop-filter、transform
 * 会为 position:fixed 创建包含块（CSS 规范），若不脱离该祖先，遮罩只会盖住
 * 主内容区、右栏漏出、工具栏被压在卡片顶部 —— 即「被覆盖 / 上下层错位」。
 * 脱离后拿不到 .km-app 上的 --km-* 变量，故同步 data-km-theme 供 CSS 自给配色。
 *
 * 「无法移动」修复（主人 11-10 验收反馈）：
 *   旧版 onPointerDown 有 `if (scale <= 1) return`，打开灯箱默认就是 100%，
 *   于是按住完全拖不动，提示却写着「放大后可拖拽」。现在任何比例都能平移；
 *   当内容是可滚动的 <pre>（ASCII 内容图）时，按住改为滚动它本身，
 *   这样右侧被裁掉的字符能拖出来看；滚轮在 <pre> 上也交还原生滚动。
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
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
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  /** 结构图是横向溢出的 <pre>：按住拖动应滚动内容本身，而不是整体平移 */
  const preDragRef = useRef<{ el: HTMLElement; x: number; y: number; sl: number; st: number } | null>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  const reset = useCallback(() => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  }, []);

  // 打开时复位并锁滚动；关闭时恢复
  useEffect(() => {
    if (!open) return;
    reset();
    setDragging(false);
    dragRef.current = null;
    preDragRef.current = null;
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
    // 结构图自身能滚时把滚轮还给它，别吞掉阅读体验
    const pre = (e.target as HTMLElement).closest?.('pre') as HTMLElement | null;
    if (pre && !e.ctrlKey && (pre.scrollWidth > pre.clientWidth + 2 || pre.scrollHeight > pre.clientHeight + 2)) return;
    e.preventDefault();
    zoom(e.deltaY < 0 ? STEP : -STEP);
  };

  const onPointerDown = (e: React.PointerEvent) => {
    const pre = (e.target as HTMLElement).closest?.('pre') as HTMLElement | null;
    if (pre && (pre.scrollWidth > pre.clientWidth + 2 || pre.scrollHeight > pre.clientHeight + 2)) {
      preDragRef.current = { el: pre, x: e.clientX, y: e.clientY, sl: pre.scrollLeft, st: pre.scrollTop };
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
      setDragging(true);
      return;
    }
    // 任何缩放比例都允许平移：默认 100% 时宽图同样能被拖着看
    dragRef.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    setDragging(true);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const p = preDragRef.current;
    if (p) {
      p.el.scrollLeft = p.sl - (e.clientX - p.x);
      p.el.scrollTop = p.st - (e.clientY - p.y);
      return;
    }
    const d = dragRef.current;
    if (!d) return;
    setOffset({ x: d.ox + (e.clientX - d.x), y: d.oy + (e.clientY - d.y) });
  };

  const onPointerUp = () => {
    dragRef.current = null;
    preDragRef.current = null;
    setDragging(false);
  };

  if (!open) return null;

  // 从 .km-app 同步主题：Portal 出去后不再继承其 CSS 变量，深色主题需 CSS 自给
  const theme = document.querySelector('.km-app')?.getAttribute('data-km-theme') ?? '';

  return createPortal(
    <div
      className="zl-root"
      data-km-theme={theme || undefined}
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
        style={{ cursor: dragging ? 'grabbing' : 'grab' }}
      >
        <div
          className="zl-content"
          style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})` }}
        >
          {src ? <img src={src} alt={alt ?? title ?? ''} draggable={false} /> : children}
        </div>
      </div>
      <div className="zl-tip">按住可拖动整张图 · 结构图可直接横向拖 · 滚轮或 ＋/− 缩放 · 0 复位 · Esc 关闭</div>
    </div>,
    document.body,
  );
}

export default ZoomLightbox;
