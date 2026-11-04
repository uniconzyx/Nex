/**
 * ChapterLab.tsx —— 章节卡里的「交互实验」
 * ============================================================================
 * 位置上紧接在「机制图解」之后、三关之前：图讲清机制，实验让你亲手把它拖错
 * 一次 —— 先看结构、再动手，最后才是三关判定，这个顺序不能倒。
 *
 * 数据不在组件里：`content/<学科>/<章>/interactive.json` 经
 * `scripts/gen_interactive.py` 抽成 `data/labs/<学科>.ts`，按学科懒加载。
 * 所以新增章节不需要动这里一行 —— 重跑生成器即可。
 *
 * 三条约定：
 *   1. **只读素材**：组件从不写 exercises / pitfalls / concept；
 *   2. **本地判定**：所有对错都在浏览器里算，不依赖后端，断网也能玩；
 *   3. **空态说人话**：本章没有模块时，告诉他跑哪条命令能长出来，而不是空白。
 */
import { Suspense, lazy, useEffect, useMemo, useState } from 'react';

import { loadLabSubject, peekLabSubject } from '../data/labs';
import type { LabData } from '../data/labs/types';

/**
 * 拖拽引擎（framer-motion）单独成 chunk：它只服务实验模块，
 * 不该让首屏为一个「用户还没展开章节」的动画库付 100KB gzip。
 * 章节卡展开后才 import，届时数据也刚好在加载，两者并行。
 */
const InteractiveLab = lazy(() =>
  import('./lab/InteractiveLab').then((m) => ({ default: m.InteractiveLab })),
);

function useLabSubject(subject: string) {
  const [list, setList] = useState<LabData[]>(() => peekLabSubject(subject) ?? []);
  const [loading, setLoading] = useState(() => !peekLabSubject(subject));

  useEffect(() => {
    const cached = peekLabSubject(subject);
    if (cached) {
      setList(cached);
      setLoading(false);
      return;
    }
    let alive = true;
    setLoading(true);
    setList([]);
    loadLabSubject(subject)
      .then((rows) => {
        if (!alive) return;
        setList(rows);
        setLoading(false);
      })
      .catch(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [subject]);

  return { list, loading };
}

/** 六种玩法的中文名：头部那行「可玩 N 种」用它，不至于露英文 kind */
const KIND_NAME: Record<string, string> = {
  sequence: '时序连线',
  match: '配对连线',
  boss: '真题打靶',
  fill: '代码挖空',
  sandbox: '沙盒推演',
  debug: '代码拼装',
};

export function ChapterLab({ subject, chapterId }: { subject: string; chapterId: string }) {
  const { list, loading } = useLabSubject(subject);
  const data = useMemo(
    () => list.find((x) => x.chapter === chapterId) ?? null,
    [list, chapterId],
  );

  if (loading) {
    return (
      <section className="km-lab km-lab-skeleton" aria-busy="true">
        <span>正在装配本章实验…</span>
      </section>
    );
  }

  if (!data || !data.modules.length) {
    return (
      <section className="km-lab km-lab-empty">
        <b>本章暂无交互实验</b>
        <span>
          实验是从 exercises / pitfalls / concept 抽出来的；补齐素材后跑一次{' '}
          <code>python scripts/gen_interactive.py</code> 就会出现。
        </span>
      </section>
    );
  }

  const kinds = Array.from(new Set(data.modules.map((m) => m.kind)));
  const names = kinds.map((k) => KIND_NAME[k] ?? k);

  return (
    <section className="km-lab" aria-label="本章交互实验">
      <header className="km-lab-head">
        <span className="km-lab-eyebrow">交互实验</span>
        <span className="km-lab-meta">
          {data.modules.length} 个模块 · {names.join(' / ')}
        </span>
        <span className="km-lab-hint">可点可拖 · 判定在本机 · 素材只读</span>
      </header>
      <Suspense fallback={<div className="km-lab km-lab-skeleton">正在装配拖拽引擎…</div>}>
        <InteractiveLab data={data} />
      </Suspense>
    </section>
  );
}

export default ChapterLab;
