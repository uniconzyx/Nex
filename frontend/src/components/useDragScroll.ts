/**
 * useDragScroll —— 给任意可滚动容器加「按住拖动平移」
 * ============================================================================
 * 用于章节里的 ASCII 内容图 / 代码块（.km-viz-nodebox pre）。
 * 这些容器本来只有 overflow:auto 的滚动条，宽图右侧被裁掉时用户会以为
 * 「图不能动」；按住拖动改 scrollLeft / scrollTop 后，整张图都能平移查看。
 *
 * 只在真正溢出时才接管指针，不破坏普通文本的选择与点击。
 * 拖拽期间加 .dragging 类切 cursor / 禁选中，松手即恢复。
 */
import { useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';

interface DragStart {
  x: number;
  y: number;
  sl: number;
  st: number;
}

export function useDragScroll<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const start = useRef<DragStart | null>(null);
  const [dragging, setDragging] = useState(false);

  const onPointerDown = (e: ReactPointerEvent<T>) => {
    const el = ref.current;
    if (!el) return;
    if (el.scrollWidth <= el.clientWidth + 2 && el.scrollHeight <= el.clientHeight + 2) return;
    // 只接管主键 / 触摸，右键菜单不拦
    if (e.button !== 0) return;
    start.current = { x: e.clientX, y: e.clientY, sl: el.scrollLeft, st: el.scrollTop };
    el.setPointerCapture(e.pointerId);
    setDragging(true);
  };

  const onPointerMove = (e: ReactPointerEvent<T>) => {
    const el = ref.current;
    const s = start.current;
    if (!el || !s) return;
    el.scrollLeft = s.sl - (e.clientX - s.x);
    el.scrollTop = s.st - (e.clientY - s.y);
  };

  const end = () => {
    start.current = null;
    setDragging(false);
  };

  return {
    ref,
    dragging,
    handlers: {
      onPointerDown,
      onPointerMove,
      onPointerUp: end,
      onPointerCancel: end,
      onLostPointerCapture: end,
    },
  };
}

export default useDragScroll;
