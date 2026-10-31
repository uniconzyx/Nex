/**
 * ToastHost.tsx —— 全局反馈层（toast + 怪物遭遇）
 * ============================================================================
 * 挂在 App 根部，任何页面 push 的反馈都在这里统一渲染：
 *   - toast：右上角滑入，金币变化带 +N 飘字
 *   - encounter：新怪物出现时的全屏遭遇卡（值得打断，所以做得重一点）
 *
 * 「去收服」不在这里做跳转判断，交给 lib/challenge.ts 统一处理：
 * 能判的进判题台，不能判的锁章节进题库——三处入口一套行为。
 * ============================================================================
 */
import { useEffect } from 'react';

import { chapterTitle } from '../lib/exerciseBank';
import { challengeQuestion } from '../lib/challenge';
import { dismissEncounter, dismissToast, useEncounter, useToasts, type ToastKind } from '../lib/feedback';
import type { Monster } from '../lib/gameTypes';
import { MonsterSprite } from './MonsterSprite';

const KIND_ICON: Record<ToastKind, string> = {
  ok: '✓',
  bad: '✕',
  info: 'i',
  coin: '◇',
  tame: '⚔',
};

export function ToastHost() {
  const toasts = useToasts();
  const encounter = useEncounter();

  // Esc 关闭遭遇卡：弹窗盖住全屏时必须给一个键盘出口
  useEffect(() => {
    if (!encounter) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismissEncounter();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [encounter]);

  const ghost: Monster | null = encounter
    ? {
        questionId: encounter.questionId,
        chapterId: encounter.chapterId,
        subject: '',
        state: 'wild',
        fails: encounter.fails,
        firstAt: Date.now(),
        lastAt: Date.now(),
        title: encounter.title,
        diff: encounter.diff ?? 'medium',
        qtype: encounter.qtype ?? 'choice',
      }
    : null;

  return (
    <>
      <div className="km-toasts" aria-live="polite" aria-atomic="false">
        {toasts.map((t) => (
          <div key={t.id} className={`km-toast k-${t.kind}`} role="status">
            <span className="km-toast-ico">{t.icon ?? KIND_ICON[t.kind]}</span>
            <div className="km-toast-body">
              <b>{t.title}</b>
              {t.desc && <span>{t.desc}</span>}
            </div>
            {typeof t.coin === 'number' && t.coin !== 0 && (
              <span className={`km-toast-coin${t.coin < 0 ? ' neg' : ''}`}>
                {t.coin > 0 ? '+' : '−'}
                {Math.abs(t.coin)}
              </span>
            )}
            <button type="button" className="km-toast-x" onClick={() => dismissToast(t.id)} aria-label="关闭提示">
              ×
            </button>
          </div>
        ))}
      </div>

      {encounter && ghost && (
        <div className="km-encounter" role="dialog" aria-modal="true" aria-label="野生怪物出现">
          <div className="km-enc">
            <div className="km-enc-spark" aria-hidden="true">
              {Array.from({ length: 10 }).map((_, i) => (
                <i key={i} style={{ ['--i' as string]: i }} />
              ))}
            </div>
            <span className="km-enc-kicker">野生怪物出现</span>
            <MonsterSprite monster={ghost} size={168} mood="hit" />
            <b className="km-enc-title">{encounter.title}</b>
            <span className="km-enc-sub">
              {chapterTitle(encounter.chapterId)} · HP 1 · 答对它即可收服
            </span>
            <div className="km-enc-actions">
              <button
                type="button"
                className="km-btn km-btn-primary"
                onClick={() => {
                  const r = challengeQuestion(encounter.questionId);
                  dismissEncounter();
                  if (!r.ok) {
                    /* challenge 内部已 fallback；失败时保留弹窗更诚实，这里不重复处理 */
                  }
                }}
              >
                去收服
              </button>
              <button type="button" className="km-btn km-btn-ghost" onClick={dismissEncounter}>
                稍后再说
              </button>
            </div>
            <p className="km-enc-hint">做错的题会被记进图鉴，重做通过即收服；失败越多，它越强。</p>
          </div>
        </div>
      )}
    </>
  );
}

export default ToastHost;
