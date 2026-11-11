/**
 * SubjectSwitch.tsx —— 全局学科切换器
 *
 * 解决三个具体问题：
 *   1. 14 个学科原来只在项目页排成一行胶囊，切走后无法跨页保持；
 *   2. 项目页筛选与「我在学什么」是两回事，用户需要的是后者；
 *   3. 窄屏上 14 个胶囊会铺成三行，把内容顶下去。
 *
 * 「切换学科被掩盖」修复（主人 11-10 验收反馈）：
 *   面板原来 absolute 定位在触发按钮的父级 .ss 里，而 .ss 实际挂在
 *   LearnPage 的 .km-card（带 transform + backdrop-filter）内，再往外是
 *   .km-content（overflow-x:hidden / overflow-y:auto）。这造成两个后果：
 *     - transform/filter 建立层叠上下文，z-index:60 被困在卡片内部，
 *       后面绘制的卡片会盖住面板；
 *     - 滚动容器会裁切超出可视区的面板下半部分。
 *   现在改为 Portal 到 document.body + position:fixed，按触发按钮的
 *   getBoundingClientRect() 定位并做上下翻转/边界收敛，脱离所有裁切与
 *   层叠上下文。Portal 后拿不到 .km-app 的 --nex-* 变量，故同步
 *   data-km-theme，并由 CSS 在 .ss-panel 上自给一套亮/暗令牌。
 */
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { BUNDLE } from '../data/bundle';
import { SUBJECTS, subjectLabel, useSubject } from '../lib/subject';

const PANEL_W = 440;
const PANEL_MAX_H = 420;

export function SubjectSwitch({ compact = false }: { compact?: boolean }) {
  const [subject, change] = useSubject();
  const [open, setOpen] = useState(false);
  // 计数直接读打包数据：离线（.exe / .apk）不发任何请求，也就不会有红色报错
  const counts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const t of BUNDLE.projects.tracks) m[t.key] = t.n;
    return m;
  }, []);
  const box = useRef<HTMLDivElement | null>(null);
  const panel = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState({ top: 0, left: 0, width: PANEL_W, maxH: PANEL_MAX_H });

  /** 面板位置随触发按钮走：内容区滚动、窗口缩放都要重算，避免「飘在别处」 */
  const place = useCallback(() => {
    const t = box.current?.querySelector<HTMLElement>('.ss-trigger');
    if (!t) return;
    const r = t.getBoundingClientRect();
    const w = Math.min(PANEL_W, window.innerWidth - 24);
    const left = Math.max(12, Math.min(r.left, window.innerWidth - w - 12));
    const below = window.innerHeight - r.bottom - 12;
    const above = r.top - 12;
    const cap = Math.min(PANEL_MAX_H, window.innerHeight - 24);
    if (below >= 180 || below >= above) {
      setPos({ top: r.bottom + 8, left, width: w, maxH: Math.max(120, Math.min(cap, below)) });
    } else {
      const h = Math.max(120, Math.min(cap, above));
      setPos({ top: Math.max(12, r.top - h - 8), left, width: w, maxH: h });
    }
  }, []);

  useLayoutEffect(() => {
    if (!open) return;
    place();
    // capture=true：.km-content 等内部滚动容器的 scroll 不冒泡，必须捕获阶段监听
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    return () => {
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
    };
  }, [open, place]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      const target = e.target as Node;
      // 面板已 Portal 出去，必须连它一起判，否则点学科会先被判定成「点外部」而关掉
      if (box.current?.contains(target) || panel.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const theme = document.querySelector('.km-app')?.getAttribute('data-km-theme') ?? '';

  return (
    <div className="ss" ref={box}>
      <button
        type="button"
        className={`ss-trigger${open ? ' open' : ''}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="ss-cap">学科</span>
        <span className="ss-cur">{compact ? subjectLabel(subject) : subjectLabel(subject)}</span>
        <span className="ss-caret" aria-hidden="true">
          ▾
        </span>
      </button>

      {open && createPortal(
        <div
          ref={panel}
          className="ss-panel"
          role="listbox"
          aria-label="选择学科"
          data-km-theme={theme || undefined}
          style={{ top: pos.top, left: pos.left, width: pos.width, maxHeight: pos.maxH }}
        >
          <div className="ss-panel-head">
            <span>切换学科</span>
            <span className="ss-panel-hint">项目筛选与学习页会同步</span>
          </div>
          <div className="ss-grid">
            {SUBJECTS.map((s) => {
              const on = s.key === subject;
              const n = counts[s.key];
              return (
                <button
                  key={s.key}
                  type="button"
                  role="option"
                  aria-selected={on}
                  className={`ss-item${on ? ' on' : ''}`}
                  onClick={() => {
                    change(s.key);
                    setOpen(false);
                  }}
                >
                  <span className="ss-item-name">{s.label}</span>
                  {typeof n === 'number' && <span className="ss-item-n">{n}</span>}
                </button>
              );
            })}
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}

export default SubjectSwitch;
