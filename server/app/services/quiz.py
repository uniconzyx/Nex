"""自适应测验生成（Phase 6）。

根据用户的薄弱章节 / 薄弱题型，从真实题库中抽题组成个性化练习卷。
- 纯函数：输入 exercises（题库行）+ weak_chapters / weak_types（错题本聚合结果），
  输出结构化题目，**每题都带真题依据**，绝不凭空捏题。
- 无弱项数据时退化为「按难度均衡抽样」，保证新用户也能用。
- 用确定性随机（seed）保证同一输入可复现，便于单测与服务端缓存。
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class QuizQuestion:
    exercise_id: int
    type: str
    title: str
    prompt: str
    options: list | None
    difficulty: str
    subject: str
    source_ref: str
    chapter_id: int | None


_SOURCE_LABEL = {
    "self": "CppMind 自编",
    "leetcode": "LeetCode 真题",
    "nowcoder": "牛客真题",
}


def _source_ref(row: dict) -> str:
    src = row.get("source") or "self"
    label = _SOURCE_LABEL.get(src, "CppMind 自编")
    if row.get("external_url"):
        return f"{label}（{row['external_url']}）"
    if row.get("external_id"):
        return f"{label}（编号 {row['external_id']}）"
    return label


def generate_quiz(
    *,
    exercises: list[dict],
    weak_chapters: list[int] | None = None,
    weak_types: list[str] | None = None,
    n: int = 5,
    rng_seed: int | None = None,
) -> list[QuizQuestion]:
    """从 exercises 抽取最多 n 道真题依据题目，严格限定在薄弱范围内。

    候选池优先级：
      弱章节 ∩ 弱题型 > 仅弱章节 > 仅弱题型 > 全库（无弱项时）。
    候选池不足 n 时返回池内全部，不做跨学科/跨题型外溢（保证练习有的放矢）。
    难度在池内做 easy/mid/hard 轮转均衡。
    """
    if not exercises:
        return []

    rng = random.Random(rng_seed)

    # 1) 构建候选池（按薄弱范围收敛）
    if weak_chapters and weak_types:
        pool = [r for r in exercises if r.get("chapter_id") in weak_chapters and r.get("type") in weak_types]
        if not pool:  # 交集为空 → 退化到弱章节（再退化到弱题型）
            pool = [r for r in exercises if r.get("chapter_id") in weak_chapters] or \
                   [r for r in exercises if r.get("type") in weak_types]
    elif weak_chapters:
        pool = [r for r in exercises if r.get("chapter_id") in weak_chapters]
    elif weak_types:
        pool = [r for r in exercises if r.get("type") in weak_types]
    else:
        pool = list(exercises)
    if not pool:
        pool = list(exercises)

    # 2) 池内难度均衡抽样
    by_diff: dict[str, list[dict]] = {"easy": [], "mid": [], "hard": []}
    for r in pool:
        by_diff.setdefault(r.get("difficulty", "mid"), []).append(r)

    picked: list[dict] = []
    idx = {k: 0 for k in by_diff}
    diff_cycle = ["easy", "mid", "hard"]
    target = min(n, len(pool))
    guard = 0
    while len(picked) < target and guard <= len(pool) * 3:
        guard += 1
        d = diff_cycle[guard % 3]
        bucket = by_diff.get(d, [])
        if idx[d] < len(bucket):
            picked.append(bucket[idx[d]])
            idx[d] += 1
    # 难度不全导致未抽满 → 顺序补
    if len(picked) < target:
        for r in pool:
            if r not in picked:
                picked.append(r)
            if len(picked) >= target:
                break

    rng.shuffle(picked)  # 打乱顺序，避免每次都先易后难

    return [
        QuizQuestion(
            exercise_id=r["id"],
            type=r.get("type", "choice"),
            title=r.get("title") or f"题 {r['id']}",
            prompt=(r.get("content_md") or "").strip()[:600],
            options=r.get("options"),
            difficulty=r.get("difficulty", "mid"),
            subject=r.get("subject", ""),
            source_ref=_source_ref(r),
            chapter_id=r.get("chapter_id"),
        )
        for r in picked[:target]
    ]
