/**
 * SettlementOverlay.tsx —— 全屏结算仪式
 *
 * 触发点是「值得停下来看一眼」的三件事：章节三关全通、项目通关、签到。
 * 动效按规范走四步：
 *   1. 背景压暗（冰蓝遮罩 + 模糊）
 *   2. 星级逐颗从上方掉落（带弹跳阻尼，依次延迟）
 *   3. 经验条急速注入冰蓝液体（波浪液面 + 斜向流动）
 *   4. 数字滚动增加（等宽字体）
 * 数据全部来自 feedback 层的结算事件，不自己算进度。
 */
import { useEffect, useRef, useState } from 'react';

import { dismissSettlement, useSettlement } from '../lib/feedback';

const STAR = ['★', '★', '★'];

export function SettlementOverlay() {
  const s = useSettlement();
  const [shown, setShown] = useState(0);
  const raf = useRef<number | null>(null);

  /** 数字滚动：从 0 滚到目标值（等宽数字，不跳格） */
  useEffect(() => {
    if (!s) return;
    const target = s.coins;
    const start = performance.now();
    const dur = 900;
    setShown(0);
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(Math.round(target * eased));
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [s?.id]);

  // 结算面板停留 5 秒后自动收起，也可以手动点「继续」
  useEffect(() => {
    if (!s) return;
    const t = setTimeout(() => dismissSettlement(), 5000);
    return () => clearTimeout(t);
  }, [s?.id]);

  if (!s) return null;

  const pct = s.expGoal > 0 ? Math.min(100, Math.round((s.exp / s.expGoal) * 100)) : 0;

  return (
    <div className="km-settle" role="dialog" aria-modal="true" aria-label="结算">
      <div className="km-settle-scrim" onClick={dismissSettlement} aria-hidden="true" />
      <div className="km-settle-card">
        <div className="km-settle-stars" aria-label={`评价 ${s.stars} 星`}>
          {STAR.map((_, i) => (
            <span key={i} className={i < s.stars ? 'on' : ''} style={{ animationDelay: `${i * 0.18}s` }}>
              ★
            </span>
          ))}
        </div>

        <h3>{s.title}</h3>
        <p className="km-settle-desc">{s.desc}</p>

        <div className="km-settle-exp">
          <div className="km-settle-exp-fill" style={{ width: `${pct}%` }}>
            <i />
          </div>
          <span className="km-settle-exp-text">
            经验 +{s.exp} / {s.expGoal}
          </span>
        </div>

        <div className="km-settle-coin">
          <span className="km-settle-coin-ico" aria-hidden="true" />
          <b>{shown.toLocaleString('zh-CN')}</b>
          <em>经验结晶</em>
        </div>

        <button type="button" className="km-btn km-btn-primary" onClick={dismissSettlement}>
          继续
        </button>
      </div>
    </div>
  );
}
