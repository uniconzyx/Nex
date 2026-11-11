/**
 * useDragScroll —— 给任意可滚动容器加「按住拖动平移」
 * ============================================================================
 * 用于机制图解的概念切换条 / 小节圆点条 / ASCII 内容图 / 代码块。
 * 这些容器本来只有 overflow:auto 的滚动条（概念条的滚动条甚至是藏掉的），
 * 宽内容右侧被裁掉时用户会以为「不能动」；按住拖动改 scrollLeft / scrollTop
 * 后，整条内容都能平移查看。
 *
 * 关键实现约束（11-11 踩过的坑）：
 *   **不能用 setPointerCapture**。捕获会把后续的 click 事件重定向到容器本身，
 *   容器里可点击的子元素（概念胶囊、小节圆点）就再也收不到 click——
 *   「拖动修好了、点击坏了」。因此这里用 window 级 pointermove/pointerup
 *   监听跟踪拖动，命中测试与点击完全不受影响。
 *
 * 拖动位移超过阈值后，松手那一下的 click 会被 onClickCapture 拦掉，
 * 避免拖完误触发子元素的点击（正常点击位移≈0，不受影响）。
 * 拖拽期间加 .dragging 类切 cursor / 禁选中，松手即恢复。
 */
import { useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent, MouseEvent as ReactMouseEvent } from 'react';

interface DragStart {
  x: number;
  y: number;
  sl: number;
  st: number;
  moved: boolean;
}

export function useDragScroll<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const start = useRef<DragStart | null>(null);
  /* 刚结束的这次交互是否算「拖动」——click 在 pointerup 之后才派发，
     靠它把拖出来的那次点击拦掉。 */
  const suppressClick = useRef(false);
  const [dragging, setDragging] = useState(false);

  const onPointerDown = (e: ReactPointerEvent<T>) => {
    const el = ref.current;
    if (!el) return;
    if (el.scrollWidth <= el.clientWidth + 2 && el.scrollHeight <= el.clientHeight + 2) return;
    // 只接管主键 / 触摸，右键菜单不拦
    if (e.button !== 0) return;
    start.current = { x: e.clientX, y: e.clientY, sl: el.scrollLeft, st: el.scrollTop, moved: false };
    suppressClick.current = false;
    setDragging(true);
    const onMove = (ev: PointerEvent) => {
      const s = start.current;
      if (!el || !s) return;
      const dx = ev.clientX - s.x;
      const dy = ev.clientY - s.y;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) s.moved = true;
      el.scrollLeft = s.sl - dx;
      el.scrollTop = s.st - dy;
    };
    const onUp = () => {
      const s = start.current;
      suppressClick.current = !!s?.moved;
      start.current = null;
      setDragging(false);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
  };

  /* 拖动松手时的那次 click（派发在容器上，冒泡前先捕获拦截） */
  const onClickCapture = (e: ReactMouseEvent<T>) => {
    if (suppressClick.current) {
      e.preventDefault();
      e.stopPropagation();
      suppressClick.current = false;
    }
  };

  return {
    ref,
    dragging,
    handlers: {
      onPointerDown,
      onClickCapture,
    },
  };
}

export default useDragScroll;
