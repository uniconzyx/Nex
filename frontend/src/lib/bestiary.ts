/**
 * bestiary.ts —— 图鉴的「展示层」：稀有度、素材参数、八股情报匹配
 * ============================================================================
 * 这一层只做纯函数，不写状态、不发请求：
 *   怪物本体存在 progress.bestiary（questionId 为 key），
 *   这里负责把它翻译成「长什么样、配哪几条八股」。
 *
 * 【素材为什么是程序化的】
 *   项目铁律是不做假数据。怪物美术如果塞 12 张预置图，就会出现「同一张图配不同题」
 *   的错位感；改成按 questionId 哈希生成参数（体型/眼距/角数），
 *   则每道题都有稳定且互不相同的形象，刷新前后一致，也不需要往安装包里加硬盘。
 * ============================================================================
 */
import { BAGUA, BAGUA_BY_SUBJECT, type BaguaItem } from '../data/bagua';
import { exerciseById } from './exerciseBank';
import { rarityOf, RARITY_META, type Monster, type Rarity } from './gameTypes';

/* ------------------------------------------------------------ 视觉参数 */

/** 稳定哈希：同一道题永远得到同一只怪，跟时间/随机数无关 */
export function seedOf(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i += 1) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

export interface MonsterVisual {
  rarity: Rarity;
  label: string;
  color: string;
  ring: string;
  /** 体型宽高比 0.86~1.14，让每只怪轮廓不同 */
  bodyW: number;
  bodyH: number;
  /** 角数量 0~4 */
  horns: number;
  /** 眼睛间距 */
  eyeGap: number;
  /** 眼睛高度 */
  eyeY: number;
  /** 头顶装饰的旋转角 */
  tilt: number;
  /** 是否已收服（决定表情与光环） */
  tamed: boolean;
}

export function visualOf(m: Monster): MonsterVisual {
  const seed = seedOf(m.questionId);
  const rarity = rarityOf(m.diff, m.fails);
  const meta = RARITY_META[rarity];
  return {
    rarity,
    label: meta.label,
    color: meta.color,
    ring: meta.ring,
    bodyW: 0.9 + ((seed >> 3) % 22) / 100,
    bodyH: 0.9 + ((seed >> 7) % 22) / 100,
    // 稀有度直接决定角数：一眼能看出这题有多难
    horns: rarity === 'boss' ? 4 : rarity === 'shiny' ? 3 : rarity === 'elite' ? 2 : seed % 2,
    eyeGap: 15 + ((seed >> 11) % 7),
    eyeY: 50 + ((seed >> 13) % 6),
    tilt: ((seed >> 17) % 24) - 12,
    tamed: m.state === 'tamed',
  };
}

/* --------------------------------------------------------- 八股情报匹配 */

/**
 * 给一只怪配 1~2 条八股。
 *
 * 匹配规则（可解释，不靠模糊猜）：
 *   1. 同学科优先 —— 跨学科的八股配上去就是噪音；
 *   2. 题目标签与八股 tags 双向包含 +2（"指针" 命中 "指针" / "智能指针"）；
 *   3. 热度 hot 作为同分时的排序依据（面试高频先看）。
 * 匹配不到时**不硬凑**：退回同学科最热的两条，并标记 match=false，
 * UI 上显示「同学科高频」而不是「本题相关」—— 这是不编数据的具体做法。
 */
export interface IntelHit {
  item: BaguaItem;
  /** 命中的标签数，0 表示这是"同学科兜底"而不是真命中 */
  score: number;
  matchedTags: string[];
}

export function intelFor(m: Monster, limit = 2): IntelHit[] {
  const ex = exerciseById(m.questionId);
  const qTags = (ex?.tags ?? []).map((t) => t.toLowerCase());
  const subject = m.subject || ex?.subj || '';
  const pool = subject ? BAGUA_BY_SUBJECT[subject] ?? [] : BAGUA;
  const candidates = pool.length ? pool : BAGUA;

  const scored = candidates.map((item) => {
    let score = 0;
    const matched: string[] = [];
    for (const t of item.tags) {
      const lt = t.toLowerCase();
      const hit = qTags.some((q) => q === lt || q.includes(lt) || lt.includes(q));
      if (hit) {
        score += 2;
        matched.push(t);
      }
    }
    return { item, score, matchedTags: matched };
  });

  const hits = scored.filter((s) => s.score > 0).sort((a, b) => b.score - a.score || b.item.hot - a.item.hot);
  if (hits.length >= limit) return hits.slice(0, limit);

  const fallback = scored
    .filter((s) => !hits.includes(s))
    .sort((a, b) => b.item.hot - a.item.hot)
    .slice(0, Math.max(0, limit - hits.length));
  return [...hits, ...fallback];
}

/** 某只怪的题目标签，图鉴详情里展示「匹配依据」 */
export function tagsOf(qid: string): string[] {
  return exerciseById(qid)?.tags ?? [];
}

/* --------------------------------------------------------------- 统计 */

/** 图鉴收录率：已收服 / 该学科题库总量（用来显示"这一科还有多少没打"） */
export function tamedRatio(total: number, tamed: number): number {
  if (!total) return 0;
  return Math.min(100, Math.round((tamed / total) * 100));
}

export { RARITY_META };
