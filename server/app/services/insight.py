"""薄弱点诊断与学习建议（Phase 6）。

聚合用户的错题本（wrong_questions）与进度（progress），输出：
- 弱章节排名（按错误次数 + 最近结果加权）
- 弱题型排名
- 下一步学习建议（先补最弱章节、再练最弱题型、配合真题依据题目）
纯函数，可单测；端点层把它喂给 AI 或直接结构化返回给前端。
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class WeakChapter:
    chapter_id: int
    wrong: int
    right: int
    score: float  # 越高越该优先补（错误多、正确少）


@dataclass
class Insight:
    weak_chapters: list[WeakChapter] = field(default_factory=list)
    weak_types: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    total_wrong: int = 0


# 题型中文名
_TYPE_LABEL = {
    "choice": "选择题",
    "fix_error": "改错题",
    "output": "程序输出题",
    "coding": "编程题",
}


def _chapter_score(wrong: int, right: int) -> float:
    # 错误次数主导，正确次数做负向惩罚；避免除零。
    return wrong * 1.0 - right * 0.3


def analyze_weakness(
    *,
    error_book: list[dict],
    progress: list[dict] | None = None,
    chapter_titles: dict[int, str] | None = None,
) -> Insight:
    """error_book 每行：chapter_id/question_type/question_id/wrong_count/right_count。
    progress 每行：kp_id/chapter_id/mastery（可选，用于补充"学过但没掌握"信号）。
    """
    chapter_wrong: dict[int, int] = defaultdict(int)
    chapter_right: dict[int, int] = defaultdict(int)
    type_wrong: dict[str, int] = defaultdict(int)

    for w in error_book or []:
        ch = w.get("chapter_id")
        qt = w.get("question_type") or w.get("type") or "unknown"
        wc = int(w.get("wrong_count") or 0)
        rc = int(w.get("right_count") or 0)
        if ch is not None:
            chapter_wrong[ch] += wc
            chapter_right[ch] += rc
        type_wrong[qt] += wc

    # 进度补充：mastery<=1（未学/学过但没掌握）且对应章节无错题，也列入待巩固
    for p in progress or []:
        ch = p.get("chapter_id")
        mastery = int(p.get("mastery") or 0)
        if ch is not None and mastery <= 1 and ch not in chapter_wrong:
            chapter_wrong[ch] += 1  # 弱信号，计 1 次

    weak_chapters = [
        WeakChapter(
            chapter_id=ch,
            wrong=chapter_wrong[ch],
            right=chapter_right.get(ch, 0),
            score=round(_chapter_score(chapter_wrong[ch], chapter_right.get(ch, 0)), 2),
        )
        for ch in chapter_wrong
    ]
    weak_chapters.sort(key=lambda c: c.score, reverse=True)

    weak_types = [
        {"type": t, "label": _TYPE_LABEL.get(t, t), "wrong": cnt}
        for t, cnt in sorted(type_wrong.items(), key=lambda kv: kv[1], reverse=True)
    ]

    recommendations: list[str] = []
    if weak_chapters:
        top = weak_chapters[0]
        title = (chapter_titles or {}).get(top.chapter_id) or f"第 {top.chapter_id} 章"
        recommendations.append(f"优先巩固《{title}》（累计错误 {top.wrong} 次），重看概念与易错点。")
    if weak_types:
        wt = weak_types[0]
        recommendations.append(f"针对性练习「{wt['label']}」，你在该题型上错误最多（{wt['wrong']} 次）。")
    if weak_chapters and weak_types:
        recommendations.append("用「自适应测验」按弱章节+弱题型抽真题依据题目，集中突破。")
    if not recommendations:
        recommendations.append("暂无薄弱点数据，保持当前节奏，按计划推进即可。")

    return Insight(
        weak_chapters=weak_chapters,
        weak_types=weak_types,
        recommendations=recommendations,
        total_wrong=sum(chapter_wrong.values()),
    )
