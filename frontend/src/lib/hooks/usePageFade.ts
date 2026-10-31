/**
 * usePageFade.ts —— 任意容器挂载时顺滑淡入（复用 game.css 的 km-page-in 关键帧）
 *
 * 页面级淡入已由 .km-page 承担；但当某个局部容器（非 .km-view 直接子节点）
 * 需要自己入场时，挂上这个 ref 即可重放同样顺滑的淡入，保证全站动效一致。
 */
import { useEffect, useRef } from 'react';

export function usePageFade<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.classList.remove('km-fade-in');
    // 强制回流，确保动画在每次挂载都重新播放（而非只在首次）
    void el.offsetWidth;
    el.classList.add('km-fade-in');
  }, []);
  return ref;
}
