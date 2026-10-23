#!/usr/bin/env python
"""408 单科专项模拟卷组卷器（阶段16 · 单科优先版）。

设计原则（2026-10-23 改）：「**先按单科整理题库，再组合成卷**」。
本脚本只做单科卷，题源**唯一**是 `questions/408-{subject}.json`：
  - 选择题存题目 id（卷子不存副本，改动自动生效）；
  - 综合应用题存「带分值的快照」，快照内容由 `sync_paper_copies.py` 与题库强制对齐，
    卷子里不允许出现题库中不存在的设计题。

题型结构对齐真实 408 的分值比例（选择 2 分/题）：
  ds  选择 6（12 分）+ 设计 3（16 分）= 28 分     真实 45 = 22 + 23
  co  选择 6（12 分）+ 设计 3（16 分）= 28 分     真实 45 = 22 + 23
  os  选择 5（10 分）+ 设计 2（14 分）= 24 分     真实 35 = 18 + 17
  cn  选择 5（10 分）+ 设计 1（ 7 分）= 17 分     真实 25 = 18 +  7

抽题规则：同一题型内按 topic 轮转，同套内不重复，跨套不重复（题池够用时）。
题量不足时**直接报错退出**，不静默少题。

用法：
    python server/scripts/gen_mock_papers.py            # 每科 4 套
    python server/scripts/gen_mock_papers.py --papers 2 # 指定套数
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"
OUT = EXAM / "papers"

SUBJECTS = {
    "ds": "数据结构",
    "co": "计算机组成原理",
    "os": "操作系统",
    "cn": "计算机网络",
}

DISCLAIMER = ("本卷按 408 该科目的题型结构自编组卷，题目与答案均为原创，不是真题还原；"
              "考点年份为历年命题的归纳性标注，请以当年考试大纲为准。")

# 每科专项卷的题型配额。design_scores 之和必须等于设计节总分。
PLAN = {
    "ds": {"choice": 6, "design": 3, "design_scores": [6, 5, 5], "duration": 50},
    "co": {"choice": 6, "design": 3, "design_scores": [6, 5, 5], "duration": 50},
    "os": {"choice": 5, "design": 2, "design_scores": [8, 6], "duration": 45},
    "cn": {"choice": 5, "design": 1, "design_scores": [7], "duration": 30},
}


def load_bank(subject: str) -> dict[str, list[dict]]:
    src = EXAM / "questions" / f"408-{subject}.json"
    data = json.loads(src.read_text(encoding="utf-8"))
    items = data["items"]
    return {
        "choice": [q for q in items if q["type"] == "choice"],
        "design": [q for q in items if q["type"] == "design"],
    }


def round_robin(items: list[dict]) -> list[dict]:
    """按 topic 轮转重排：让同一套卷里的题尽量来自不同专题。"""
    groups: dict[str, list[dict]] = collections.OrderedDict()
    for q in items:
        groups.setdefault(q["topic"], []).append(q)
    out, i = [], 0
    while len(out) < len(items):
        for g in groups.values():
            if i < len(g):
                out.append(g[i])
        i += 1
    return out


def take(pool: list[dict], n: int, label: str) -> list[dict]:
    """顺序取 n 题并出池；不足直接报错，不静默少题。"""
    if len(pool) < n:
        raise SystemExit(
            f"{label} 题目不足：需要 {n}，只有 {len(pool)}。"
            f"请先扩充 questions/408-*.json 再组卷。")
    out = pool[:n]
    del pool[:n]
    return out


def snapshot(q: dict, score: int) -> dict:
    """题库题 → 卷内快照。只保留卷子需要的字段，分值由卷子决定。"""
    snap = {
        "id": q["id"],
        "topic": q.get("topic"),
        "knowledge": q.get("knowledge"),
        "type": q.get("type"),
        "diff": q.get("diff"),
        "stem": q.get("stem"),
        "ask": q.get("ask") or [],
        "answer": q.get("answer"),
        "walkthrough": q.get("walkthrough"),
        "score": score,
    }
    return {k: v for k, v in snap.items() if v is not None}


def build(subject: str, label: str, n_papers: int) -> list[dict]:
    plan = PLAN[subject]
    bank = load_bank(subject)
    choice_pool = round_robin(bank["choice"])
    design_pool = round_robin(bank["design"])

    n_choice, n_design = plan["choice"], plan["design"]
    need_choice = n_choice * n_papers
    need_design = n_design * n_papers
    if len(choice_pool) < need_choice:
        raise SystemExit(f"408-{subject} 选择题不足：{n_papers} 套 × {n_choice} 题 "
                         f"需要 {need_choice}，只有 {len(choice_pool)}")
    if len(design_pool) < need_design:
        raise SystemExit(f"408-{subject} 设计题不足：{n_papers} 套 × {n_design} 题 "
                         f"需要 {need_design}，只有 {len(design_pool)}")

    scores = plan["design_scores"]
    papers = []
    for k in range(n_papers):
        cs = take(choice_pool, n_choice, f"408-{subject} 选择题")
        ds = take(design_pool, n_design, f"408-{subject} 设计题")
        choice_score = n_choice * 2
        design_score = sum(scores)
        papers.append({
            "id": f"408-{subject}-mock-{k + 1:02d}",
            "exam": "408",
            "kind": "mock",
            "subject": subject,
            "title": f"408 {label} · 专项模拟卷（{k + 1}）",
            "duration": plan["duration"],
            "totalScore": choice_score + design_score,
            "disclaimer": DISCLAIMER,
            "blueprint": [{
                "subject": subject, "name": label,
                "score": choice_score + design_score,
                "choice": choice_score, "analysis": design_score,
            }],
            "sections": [
                {
                    "no": 1, "name": "单项选择题", "type": "choice",
                    "range": f"1~{n_choice} 题",
                    "score": choice_score, "perScore": 2,
                    "note": "每题 2 分。下列每题给出的四个选项中，只有一个符合题目要求。",
                    "items": [q["id"] for q in cs],
                },
                {
                    "no": 2, "name": "综合应用题", "type": "design",
                    "range": f"{n_choice + 1}~{n_choice + n_design} 题",
                    "score": design_score,
                    "note": "按题目要求作答，写出设计思想、关键代码与复杂度分析。",
                    "items": [snapshot(q, scores[i]) for i, q in enumerate(ds)],
                },
            ],
        })
    used_c = sum(1 for _ in range(need_choice))
    print(f"{subject}: 选择 {len(bank['choice'])} 题 / 设计 {len(bank['design'])} 题 "
          f"→ {n_papers} 套 ×（选择 {n_choice} + 设计 {n_design}），"
          f"余 选择 {len(choice_pool)} / 设计 {len(design_pool)}")
    return papers


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", type=int, default=4, help="每科套数（默认 4）")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for subj, label in SUBJECTS.items():
        papers = build(subj, label, args.papers)
        total += len(papers)
        for p in papers:
            (OUT / f"{p['id']}.json").write_text(
                json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 清掉超出本次套数的旧单科卷，避免「加了设计题却还留着旧的选择题卷」
    import re as _re
    for stale in sorted(OUT.glob("408-*-mock-*.json")):
        m = _re.search(r"mock-(\d+)\.json$", stale.name)
        if m and int(m.group(1)) > args.papers:
            stale.unlink()
            print(f"[清理] 删除旧单科卷 {stale.name}")

    print(f"共生成 {total} 套单科专项卷 -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
