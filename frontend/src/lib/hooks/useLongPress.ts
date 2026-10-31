/**
 * useLongPress.ts —— 长按手势（指针事件，鼠标/触摸统一）
 *
 * 用于「长按预览」等场景：按下开始计时，松手/移出/移动超阈值则取消。
 * 不依赖任何第三方库；返回的 handlers 直接展开到目标元素上。
 */
import { useCallback, useRef } from 'react';

export interface LongPressHandlers {
  onPointerDown: (e: React.PointerEvent) => void;
  onPointerUp: (e: React.PointerEvent) => void;
  onPointerLeave: (e: React.PointerEvent) => void;
  onPointerMove: (e: React.PointerEvent) => void;
}

export function useLongPress(
  onLongPress: (e: React.PointerEvent) => void,
  options: { ms?: number; moveTolerance?: number } = {},
): LongPressHandlers {
  const { ms = 450, moveTolerance = 10 } = options;
  const timer = useRef<number | null>(null);
  const start = useRef<{ x: number; y: number } | null>(null);

  const clear = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    start.current = null;
  }, []);

  const down = useCallback(
    (e: React.PointerEvent) => {
      start.current = { x: e.clientX, y: e.clientY };
      timer.current = window.setTimeout(() => {
        timer.current = null;
        onLongPress(e);
      }, ms);
    },
    [onLongPress, ms],
  );

  const move = useCallback(
    (e: React.PointerEvent) => {
      if (!start.current) return;
      const dx = Math.abs(e.clientX - start.current.x);
      const dy = Math.abs(e.clientY - start.current.y);
      if (Math.hypot(dx, dy) > moveTolerance) clear();
    },
    [clear, moveTolerance],
  );

  return {
    onPointerDown: down,
    onPointerUp: clear,
    onPointerLeave: clear,
    onPointerMove: move,
  };
}
