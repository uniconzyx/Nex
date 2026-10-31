/**
 * Particles.tsx —— 冰蓝粒子层（连携 / 晋升 / 合成暴击 / 赛季升级 的轻反馈）
 *
 * 用法：在 App 根部包一层 <ParticleProvider>，任意组件用 useParticles().emit(x,y,kind)
 *   在指定屏幕坐标喷一束冰蓝粒子。粒子用完自动清理，超出上限回收最旧的。
 * prefers-reduced-motion 下直接不喷（避免对动效敏感用户造成干扰）。
 * 判定统一走 lib/motion 的 shouldReduceMotion()：它同时认系统媒体查询
 * 和设置页里手动选的「始终减少」，改完设置立即生效，不需要刷新。
 */
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

import { shouldReduceMotion } from '../lib/motion';

export type ParticleKind = 'combo' | 'promote' | 'crit' | 'season' | 'default';

interface Particle {
  id: number;
  x: number;
  y: number;
  dx: number;
  dy: number;
  color: string;
  size: number;
}

interface ParticleCtx {
  emit: (x: number, y: number, kind?: ParticleKind) => void;
}

const PContext = createContext<ParticleCtx | null>(null);

const KIND_COLOR: Record<ParticleKind, string> = {
  combo: 'rgba(91, 155, 213, 0.6)',
  promote: 'rgba(111, 211, 192, 0.7)',
  crit: 'rgba(243, 179, 91, 0.75)',
  season: 'rgba(91, 155, 213, 0.6)',
  default: 'rgba(91, 155, 213, 0.5)',
};

const KIND_COUNT: Record<ParticleKind, number> = {
  combo: 14,
  promote: 18,
  crit: 22,
  season: 26,
  default: 12,
};

const MAX_LIVE = 140;

export function ParticleProvider({ children }: { children: React.ReactNode }) {
  const [parts, setParts] = useState<Particle[]>([]);
  const idRef = useRef(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const emit = useCallback((x: number, y: number, kind: ParticleKind = 'default') => {
    if (shouldReduceMotion() || !mounted.current) return;
    const n = KIND_COUNT[kind];
    const color = KIND_COLOR[kind];
    const fresh: Particle[] = [];
    for (let i = 0; i < n; i++) {
      const ang = (Math.PI * 2 * i) / n + Math.random() * 0.5;
      const dist = 36 + Math.random() * 64;
      fresh.push({
        id: idRef.current++,
        x,
        y,
        dx: Math.cos(ang) * dist,
        dy: Math.sin(ang) * dist - 18,
        color,
        size: 5 + Math.random() * 6,
      });
    }
    setParts((prev) => [...prev, ...fresh].slice(-MAX_LIVE));
    window.setTimeout(() => {
      if (!mounted.current) return;
      const ids = new Set(fresh.map((p) => p.id));
      setParts((prev) => prev.filter((p) => !ids.has(p.id)));
    }, 760);
  }, []);

  return (
    <PContext.Provider value={{ emit }}>
      {children}
      <div className="km-particles" aria-hidden="true">
        {parts.map((p) => {
          const style = {
            left: `${p.x}px`,
            top: `${p.y}px`,
            width: `${p.size}px`,
            height: `${p.size}px`,
            background: p.color,
            boxShadow: `0 0 8px ${p.color}`,
            '--dx': `${p.dx}px`,
            '--dy': `${p.dy}px`,
          } as React.CSSProperties;
          return <span key={p.id} className="km-particle" style={style} />;
        })}
      </div>
    </PContext.Provider>
  );
}

export function useParticles(): ParticleCtx {
  const ctx = useContext(PContext);
  if (!ctx) return { emit: () => {} };
  return ctx;
}

export default ParticleProvider;
