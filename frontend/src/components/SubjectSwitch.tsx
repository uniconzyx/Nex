/**
 * SubjectSwitch.tsx —— 全局学科切换器（顶栏）
 *
 * 解决三个具体问题：
 *   1. 13 个学科原来只在项目页排成一行胶囊，切走后无法跨页保持；
 *   2. 项目页筛选与「我在学什么」是两回事，用户需要的是后者；
 *   3. 窄屏上 13 个胶囊会铺成三行，把内容顶下去。
 *
 * 交互：点开是两列学科面板，每项带项目数；选中即写入全局状态（localStorage 持久化），
 * 项目页立即跟随，学习/练习页后续接入时读同一个值即可。
 */
import { useEffect, useMemo, useRef, useState } from 'react';

import { BUNDLE } from '../data/bundle';
import { SUBJECTS, subjectLabel, useSubject } from '../lib/subject';

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

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
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

      {open && (
        <div className="ss-panel" role="listbox" aria-label="选择学科">
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
        </div>
      )}
    </div>
  );
}

export default SubjectSwitch;
