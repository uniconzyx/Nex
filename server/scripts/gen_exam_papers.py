#!/usr/bin/env python
"""生成数学、英语、政治的专项模拟卷（阶段16）。

每科 8 套，题量按「专项卷」设计而非整卷：
  math    选择 3（5 分）+ 填空 1（5 分）+ 解答 1（10 分）= 30 分 / 40 分钟
  english 阅读 3（6 分）+ 翻译 1（12 分）+ 写作 1（12 分）= 30 分 / 50 分钟
  politics 单选 3（3 分）+ 多选 1（2 分）+ 分析 1（10 分）= 15 分 / 35 分钟

抽题规则：同一题型内顺序取用，不跨套复用；数量不足时直接报错，不静默少题。
408 的组卷在 gen_mock_papers.py，那边按章节轮转，逻辑不同，故分开。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"
N = 8

DISCLAIMER = ("本卷为按题型结构自编的专项练习卷，题目与解析均为原创，不是真题还原；"
              "考点年份为历年命题的归纳性标注，请以当年考试大纲为准。")


def load(exam: str, subj: str) -> dict:
    return json.loads((EXAM / "questions" / f"{exam}-{subj}.json").read_text(encoding="utf-8"))


def save(paper: dict) -> None:
    p = EXAM / "papers" / f"{paper['id']}.json"
    p.write_text(json.dumps(paper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def take(pool: list, n: int, label: str) -> list:
    if len(pool) < n:
        raise SystemExit(f"{label} 题目不足：需要 {n}，只有 {len(pool)}")
    out = pool[:n]
    del pool[:n]
    return out


def rr(lst: list) -> list:
    """按 topic 轮转重排，避免一套卷里三道题全来自同一板块。"""
    groups: dict[str, list] = {}
    for q in lst:
        groups.setdefault(q["topic"], []).append(q)
    out, i = [], 0
    while len(out) < len(lst):
        for g in groups.values():
            if i < len(g):
                out.append(g[i])
        i += 1
    return out


# ------------------------------------------------------------------ 数学
def math_papers(exam: str, subj: str, label: str) -> None:
    data = load(exam, subj)["items"]
    choice = [q for q in data if q["type"] == "choice"]
    blank = [q for q in data if q["type"] == "blank"]
    calc = [q for q in data if q["type"] == "calc"]

    for k in range(1, N + 1):
        cs = take(choice, 3, f"{subj} choice")
        bs = take(blank, 1, f"{subj} blank")
        ks = take(calc, 1, f"{subj} calc")
        save({
            "id": f"{exam}-{subj}-mock-{k:02d}",
            "exam": exam,
            "kind": "mock",
            "subject": subj,
            "title": f"{label} · 专项模拟卷（{k}）",
            "duration": 40,
            "totalScore": 30,
            "disclaimer": DISCLAIMER,
            "blueprint": [{"subject": subj, "name": label, "score": 30}],
            "sections": [
                {"no": 1, "name": "单项选择题", "type": "choice", "range": "1~3 题",
                 "score": 15, "perScore": 5,
                 "note": "每题 5 分，共 15 分。只有一个选项符合题目要求。",
                 "items": [q["id"] for q in cs]},
                {"no": 2, "name": "填空题", "type": "blank", "range": "4 题",
                 "score": 5, "note": "本题 5 分，直接写结果。",
                 "items": [{**bs[0], "score": 5}]},
                {"no": 3, "name": "解答题", "type": "calc", "range": "5 题",
                 "score": 10, "note": "本题 10 分，写出必要的推导过程。",
                 "items": [{**ks[0], "score": 10}]},
            ],
        })
    print(f"{exam}-{subj}: {N} 套")


# ------------------------------------------------------------------ 英语
def english_papers(subj: str, label: str) -> None:
    data = load("english", subj)["items"]
    reading = [q for q in data if q["topic"].endswith("-reading")]
    trans = [q for q in data if q["topic"].endswith("-translation")]
    writing = [q for q in data if q["topic"].endswith("-writing")]

    by_passage: dict[str, list[dict]] = {}
    for q in reading:
        by_passage.setdefault(q["passage"]["id"], []).append(q)
    groups = list(by_passage.values())

    for k in range(1, N + 1):
        if k > len(groups):
            raise SystemExit(f"{subj} 文章不足：需要 {N}，只有 {len(groups)}")
        g = groups[k - 1]
        tr = take(trans, 1, f"{subj} translation")[0]
        wr = take(writing, 1, f"{subj} writing")[0]
        save({
            "id": f"english-{subj}-mock-{k:02d}",
            "exam": "english",
            "kind": "mock",
            "subject": subj,
            "title": f"{label} · 阅读精读专项（{k}）",
            "duration": 50,
            "totalScore": 30,
            "disclaimer": DISCLAIMER,
            "blueprint": [{"subject": subj, "name": label, "score": 30}],
            "sections": [
                {"no": 1, "name": "阅读理解", "type": "choice", "range": "1~3 题",
                 "score": 6, "perScore": 2,
                 "note": "每题 2 分。阅读所给文章，从四个选项中选出最佳答案。",
                 "passage": g[0]["passage"],
                 "items": [q["id"] for q in g]},
                {"no": 2, "name": "翻译", "type": "calc", "range": "4 题",
                 "score": 12, "note": "本题 12 分。把划线句子译成汉语，要求准确、通顺。",
                 "items": [{**tr, "score": 12}]},
                {"no": 3, "name": "写作", "type": "design", "range": "5 题",
                 "score": 12, "note": "本题 12 分。按题目要求写一篇短文。",
                 "items": [{**wr, "score": 12}]},
            ],
        })
    print(f"english-{subj}: {N} 套")


# ------------------------------------------------------------------ 政治
def politics_papers() -> None:
    data = load("politics", "pol")["items"]
    single = rr([q for q in data if q["type"] == "choice"])
    multi = rr([q for q in data if q["type"] == "multi"])
    analysis = rr([q for q in data if q["type"] == "calc"])

    # 单选题 24 道覆盖 5 个板块，轮转后每套 3 题基本来自不同板块

    for k in range(1, N + 1):
        ss = take(single, 3, "pol single")
        ms = take(multi, 1, "pol multi")
        ans = take(analysis, 1, "pol analysis")
        save({
            "id": f"politics-pol-mock-{k:02d}",
            "exam": "politics",
            "kind": "mock",
            "subject": "pol",
            "title": f"政治 · 专项模拟卷（{k}）",
            "duration": 35,
            "totalScore": 15,
            "disclaimer": DISCLAIMER,
            "blueprint": [{"subject": "pol", "name": "思想政治理论", "score": 15}],
            "sections": [
                {"no": 1, "name": "单项选择题", "type": "choice", "range": "1~3 题",
                 "score": 3, "perScore": 1,
                 "note": "每题 1 分。只有一个选项符合题目要求。",
                 "items": [q["id"] for q in ss]},
                {"no": 2, "name": "多项选择题", "type": "multi", "range": "4 题",
                 "score": 2, "perScore": 2,
                 "note": "每题 2 分。至少有两个选项符合题目要求，多选、错选不得分。",
                 "items": [q["id"] for q in ms]},
                {"no": 3, "name": "材料分析题", "type": "analysis", "range": "5 题",
                 "score": 10, "note": "本题 10 分。结合材料回答问题。",
                 "items": [{**ans[0], "score": 10}]},
            ],
        })
    print(f"politics-pol: {N} 套")


if __name__ == "__main__":
    math_papers("math", "m2", "数学（二）")
    math_papers("math", "m1", "数学（一）")
    english_papers("e1", "英语（一）")
    english_papers("e2", "英语（二）")
    politics_papers()
    math_papers("discrete", "dm", "离散数学")
    math_papers("algorithm", "algo", "算法设计与分析")
