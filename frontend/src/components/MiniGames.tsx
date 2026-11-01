/**
 * MiniGames.tsx —— 支线小屋的三个小游戏
 *
 * 三个游戏共用一条原则：**内容全部来自真实数据**，没有一个假题假图。
 *   1. 代码拼图盒：把某个真实开源项目 steps 的执行顺序还原（↑/↓ 按钮换位，键盘可用）。
 *   2. 记忆翻牌：真实章节标题 ↔ 该章的标志性资源（GitHub 仓库 / 推荐书）。
 *   3. 错题消消乐：真实错题（野生怪物）的题面 ↔ 所属章节；没有错题时用当前学科题库里的真题。
 *
 * 玩法不写进度、不发奖励——支线是放松区，结算与奖励只属于主线。
 */
import { useEffect, useMemo, useState } from 'react';

import { BUNDLE } from '../data/bundle';
import { chapterTitle, exercisesOfSubject } from '../lib/exerciseBank';
import { pushToast } from '../lib/feedback';
import { useProgress, wildMonsters } from '../lib/progress';
import { useSubject } from '../lib/subject';

/* ------------------------------------------------------------------ 工具 */

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

interface ChapterLite {
  id: string;
  title: string;
  res: string;
}

function allChapters(): ChapterLite[] {
  const out: ChapterLite[] = [];
  for (const pack of Object.values(BUNDLE.chapters)) {
    for (const c of pack.chapters) {
      const res = c.github?.[0] ?? c.books?.[0] ?? '';
      if (res) out.push({ id: c.id, title: c.title, res });
    }
  }
  return out;
}

/* ------------------------------------------------- 1. 代码拼图盒（还原步骤） */

export function PuzzleGame() {
  const [subject] = useSubject();
  const project = useMemo(() => {
    const all = BUNDLE.projects.items.filter((i) => i.steps.length >= 4);
    const mine = all.filter((i) => i.track === subject);
    return mine[0] ?? all[0] ?? null;
  }, [subject]);

  const answer = useMemo(() => project?.steps ?? [], [project]);
  const [order, setOrder] = useState<number[]>([]);
  const [result, setResult] = useState<'play' | 'ok' | 'bad'>('play');

  // 换项目就重开一局
  useEffect(() => {
    setOrder(shuffle(answer.map((_, i) => i)));
    setResult('play');
  }, [project?.slug, answer.length]);

  if (!project || answer.length === 0) {
    return <p className="kg-empty">项目库里还没有可用的步骤数据。</p>;
  }

  const move = (i: number, dir: -1 | 1) => {
    setResult('play');
    setOrder((o) => {
      const n = [...o];
      const j = i + dir;
      if (j < 0 || j >= n.length) return o;
      [n[i], n[j]] = [n[j], n[i]];
      return n;
    });
  };

  const check = () => {
    const ok = order.every((v, i) => v === i);
    setResult(ok ? 'ok' : 'bad');
    if (ok) {
      pushToast({ kind: 'ok', title: '拼图完成', desc: `${project.title} 的 ${answer.length} 步顺序全对` });
    }
  };

  return (
    <div className="kg">
      <p className="kg-desc">
        把 <b>{project.title}</b>（{project.repo}）的 {answer.length} 步还原成正确顺序。
      </p>
      <ol className="kg-puzzle">
        {order.map((stepIdx, i) => (
          <li key={`${stepIdx}-${i}`} className={result === 'ok' ? 'ok' : ''}>
            <span className="kg-no">{i + 1}</span>
            <span className="kg-text">{answer[stepIdx]}</span>
            <span className="kg-ops">
              <button type="button" onClick={() => move(i, -1)} disabled={i === 0} aria-label="上移">
                ↑
              </button>
              <button type="button" onClick={() => move(i, 1)} disabled={i === order.length - 1} aria-label="下移">
                ↓
              </button>
            </span>
          </li>
        ))}
      </ol>
      <div className="kg-actions">
        <button type="button" className="km-btn km-btn-primary km-btn-sm" onClick={check}>
          验证顺序
        </button>
        <button
          type="button"
          className="km-btn km-btn-ghost km-btn-sm"
          onClick={() => {
            setOrder(shuffle(answer.map((_, i) => i)));
            setResult('play');
          }}
        >
          重新打乱
        </button>
        {result === 'ok' && <span className="kg-verdict ok">顺序全对，这条路径你已经能复述了。</span>}
        {result === 'bad' && <span className="kg-verdict bad">还有步骤没排对，再看看前后依赖。</span>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------- 2. 记忆翻牌（章节 ↔ 资源） */

interface FlipCard {
  key: string;
  pairId: string;
  text: string;
  face: 'chapter' | 'resource';
}

export function MemoryGame() {
  const [subject] = useSubject();
  const cards = useMemo<FlipCard[]>(() => {
    const all = allChapters();
    const mine = all.filter((c) => c.id.startsWith(subject.replace(/[^a-z]/gi, '')));
    // 标题重名的章节会让翻牌出现两张一样的牌，按标题去重
    const seen = new Set<string>();
    const pool = (mine.length >= 4 ? mine : all)
      .filter((c) => (seen.has(c.title) ? false : (seen.add(c.title), true)))
      .slice(0, 4);
    const list: FlipCard[] = [];
    for (const c of pool) {
      list.push({ key: `${c.id}-t`, pairId: c.id, text: c.title, face: 'chapter' });
      list.push({ key: `${c.id}-r`, pairId: c.id, text: c.res, face: 'resource' });
    }
    return shuffle(list);
  }, [subject]);
  const [open, setOpen] = useState<string[]>([]);
  const [matched, setMatched] = useState<string[]>([]);
  const [moves, setMoves] = useState(0);

  useEffect(() => {
    setOpen([]);
    setMatched([]);
    setMoves(0);
  }, [subject]);

  const flip = (c: FlipCard) => {
    if (matched.includes(c.pairId) || open.includes(c.key)) return;
    const next = [...open, c.key];
    setOpen(next);
    if (next.length === 2) {
      setMoves((m) => m + 1);
      const [a, b] = next.map((k) => cards.find((x) => x.key === k)!);
      if (a.pairId === b.pairId) {
        setMatched((m) => [...m, c.pairId]);
        setOpen([]);
      } else {
        setTimeout(() => setOpen([]), 780);
      }
    }
  };

  return (
    <div className="kg">
      <p className="kg-desc">
        把 <b>章节标题</b> 和它的 <b>标志性资源</b> 配对（GitHub 仓库或推荐书）。已配对 {matched.length}/{cards.length / 2} · 翻牌 {moves} 次
      </p>
      <div className="kg-cards">
        {cards.map((c) => {
          const isOpen = open.includes(c.key) || matched.includes(c.pairId);
          return (
            <button
              key={c.key}
              type="button"
              className={`kg-card${isOpen ? ' open' : ''}${matched.includes(c.pairId) ? ' done' : ''}`}
              onClick={() => flip(c)}
              aria-label={`翻牌：${c.face === 'chapter' ? '章节' : '资源'}`}
            >
              <span className="kg-card-face">{isOpen ? c.text : '?'}</span>
            </button>
          );
        })}
      </div>
      {matched.length === cards.length / 2 && cards.length > 0 && (
        <p className="kg-verdict ok">全部配对成功——这些资源就是各章的主线读物。</p>
      )}
    </div>
  );
}

/* ------------------------------------------------- 3. 错题消消乐（题面 ↔ 章节） */

interface Tile {
  key: string;
  pairId: string;
  text: string;
  kind: 'q' | 'ch';
}

export function MonsterMatchGame() {
  const p = useProgress();
  const [subject] = useSubject();
  const tiles = useMemo<Tile[]>(() => {
    // 优先用真实错题（野生怪物），不够就拿当前学科题库里的真题补
    const clip = (t: string) => (t.length > 22 ? `${t.slice(0, 22)}…` : t);
    const seen = new Set<string>();
    const pairs: { id: string; q: string; ch: string }[] = [];
    const push = (id: string, q: string, ch: string) => {
      // 题库里不同章节可能有同名题；同名会让「消消乐」出现两张一样的牌，配对就乱了
      if (seen.has(q) || pairs.length >= 4) return;
      seen.add(q);
      pairs.push({ id, q: clip(q), ch: clip(ch) });
    };
    for (const m of wildMonsters(p)) push(m.questionId, m.title, chapterTitle(m.chapterId) || m.chapterId);
    for (const e of exercisesOfSubject(subject)) {
      if (pairs.length >= 4) break;
      push(e.id, e.title, chapterTitle(e.ch) || e.ch);
    }
    const list: Tile[] = [];
    for (const x of pairs) {
      list.push({ key: `${x.id}-q`, pairId: x.id, text: x.q, kind: 'q' });
      list.push({ key: `${x.id}-c`, pairId: x.id, text: x.ch, kind: 'ch' });
    }
    return shuffle(list);
  }, [p, subject]);

  const [picked, setPicked] = useState<string[]>([]);
  const [cleared, setCleared] = useState<string[]>([]);
  const [score, setScore] = useState(0);

  const tap = (t: Tile) => {
    if (cleared.includes(t.pairId) || picked.includes(t.key)) return;
    const next = [...picked, t.key];
    setPicked(next);
    if (next.length === 2) {
      const [a, b] = next.map((k) => tiles.find((x) => x.key === k)!);
      if (a.pairId === b.pairId) {
        setCleared((c) => [...c, t.pairId]);
        setPicked([]);
        setScore((s) => s + 10);
      } else {
        setTimeout(() => setPicked([]), 700);
      }
    }
  };

  const total = tiles.length / 2;

  return (
    <div className="kg">
      <p className="kg-desc">
        把 <b>题面</b> 和它来自的 <b>章节</b> 消掉（错题优先）。已消 {cleared.length}/{total} · 得分 {score}
      </p>
      <div className="kg-tiles">
        {tiles.map((t) => {
          const gone = cleared.includes(t.pairId);
          const on = gone || picked.includes(t.key);
          return (
            <button
              key={t.key}
              type="button"
              className={`kg-tile${on ? ' on' : ''}${gone ? ' gone' : ''} kind-${t.kind}`}
              onClick={() => tap(t)}
              disabled={gone}
            >
              {t.text}
            </button>
          );
        })}
      </div>
      {total > 0 && cleared.length === total && <p className="kg-verdict ok">全部消完——错题和章节的对应关系已经记住了。</p>}
    </div>
  );
}
