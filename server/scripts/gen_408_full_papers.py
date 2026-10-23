#!/usr/bin/env python
"""408 整卷组卷器：把四科单科题库组合成 150 分整卷。

设计原则（2026-10-23 新增）：「**先按单科整理题库，再组合成卷**」。
整卷不是另起一套题，而是从 `questions/408-{ds,co,os,cn}.json` 四个单科库里抽题组合：

  - 单项选择题（40 题 × 2 分 = 80 分）：ds 11 / co 11 / os 9 / cn 9
  - 综合应用题（7 道 = 70 分）：ds 2（13+10）/ co 2（12+11）/ os 2（9+8）/ cn 1（7）

即真实 408 的分值结构：ds 45 = 22 + 23，co 45 = 22 + 23，os 35 = 18 + 17，cn 25 = 18 + 7。

选择题存题目 id；综合应用题存「带分值的快照」，快照由 `sync_paper_copies.py`
与单科题库强制对齐——**整卷里不允许出现任何单科题库中不存在的题**。

抽题规则：按 topic 轮转，同套内不重复，跨套不重复；题量不足直接报错退出。

用法：
    python server/scripts/gen_408_full_papers.py            # 生成 2 套
    python server/scripts/gen_408_full_papers.py --papers 3 # 指定套数
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"
OUT = EXAM / "papers"

SUBJECTS = {"ds": "数据结构", "co": "计算机组成原理",
            "os": "操作系统", "cn": "计算机网络"}

DISCLAIMER = ("本卷按 408 真题的题型与分值结构自编组卷，题目与答案均为原创，不是真题还原；"
              "考点年份为历年命题的归纳性标注，请以当年考试大纲为准。")

# 整卷配额：选择题题数 + 设计题的单题分值序列（其和 = 该科应用题分）
FULL_PLAN = {
    "ds": {"choice": 11, "design_scores": [13, 10]},
    "co": {"choice": 11, "design_scores": [12, 11]},
    "os": {"choice": 9, "design_scores": [9, 8]},
    "cn": {"choice": 9, "design_scores": [7]},
}

# 真实 408 的科目分值，用于 blueprint
SUBJECT_SCORE = {"ds": 45, "co": 45, "os": 35, "cn": 25}


def load_pool(subject: str, qtype: str) -> list[dict]:
    data = json.loads((EXAM / "questions" / f"408-{subject}.json").read_text(encoding="utf-8"))
    return [q for q in data["items"] if q["type"] == qtype]


def round_robin(items: list[dict]) -> list[dict]:
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


def snapshot(q: dict, score: int) -> dict:
    snap = {
        "id": q["id"], "subject": None, "topic": q.get("topic"),
        "knowledge": q.get("knowledge"), "type": q.get("type"),
        "diff": q.get("diff"), "stem": q.get("stem"),
        "ask": q.get("ask") or [], "answer": q.get("answer"),
        "walkthrough": q.get("walkthrough"), "score": score,
    }
    snap.pop("subject")
    return {k: v for k, v in snap.items() if v is not None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", type=int, default=2, help="整卷套数（默认 2）")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    # ---- 题池：单科题库是唯一题源，先按 topic 轮转 ----
    pools: dict[str, dict[str, list[dict]]] = {}
    for subj in SUBJECTS:
        pools[subj] = {
            "choice": round_robin(load_pool(subj, "choice")),
            "design": round_robin(load_pool(subj, "design")),
        }
        plan = FULL_PLAN[subj]
        need_c = plan["choice"] * args.papers
        need_d = len(plan["design_scores"]) * args.papers
        if len(pools[subj]["choice"]) < need_c:
            raise SystemExit(f"408-{subj} 选择题不足：需要 {need_c}，"
                             f"只有 {len(pools[subj]['choice'])}")
        if len(pools[subj]["design"]) < need_d:
            raise SystemExit(f"408-{subj} 设计题不足：需要 {need_d}，"
                             f"只有 {len(pools[subj]['design'])}")

    total = 0
    for k in range(args.papers):
        choice_items: list[str] = []
        design_items: list[dict] = []
        blueprint = []
        choice_score_sum = 0
        design_score_sum = 0

        for subj, label in SUBJECTS.items():
            plan = FULL_PLAN[subj]
            cs = pools[subj]["choice"][:plan["choice"]]
            del pools[subj]["choice"][:plan["choice"]]
            ds = pools[subj]["design"][:len(plan["design_scores"])]
            del pools[subj]["design"][:len(plan["design_scores"])]
            choice_items.extend(q["id"] for q in cs)
            design_items.extend(snapshot(q, s) for q, s in zip(ds, plan["design_scores"]))
            c_score = plan["choice"] * 2
            d_score = sum(plan["design_scores"])
            choice_score_sum += c_score
            design_score_sum += d_score
            blueprint.append({
                "subject": subj, "name": label,
                "score": SUBJECT_SCORE[subj],
                "choice": c_score, "analysis": d_score,
            })

        n_choice = len(choice_items)
        paper = {
            "id": f"408-mock-{k + 1:02d}",
            "exam": "408",
            "kind": "mock",
            "title": f"408 计算机学科专业基础 · 全真模拟卷（{k + 1}）",
            "duration": 180,
            "totalScore": 150,
            "disclaimer": DISCLAIMER,
            "blueprint": blueprint,
            "sections": [
                {
                    "no": 1, "name": "单项选择题", "type": "choice",
                    "range": f"1~{n_choice} 题",
                    "score": choice_score_sum, "perScore": 2,
                    "note": "下列每题给出的四个选项中，只有一个符合题目要求。",
                    "items": choice_items,
                },
                {
                    "no": 2, "name": "综合应用题", "type": "design",
                    "range": f"{n_choice + 1}~{n_choice + len(design_items)} 题",
                    "score": design_score_sum,
                    "note": "按题目要求作答，写出设计思想、关键代码与复杂度分析。",
                    "items": design_items,
                },
            ],
        }
        (OUT / f"{paper['id']}.json").write_text(
            json.dumps(paper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"408-mock-{k + 1:02d}: 单选 {n_choice} 题（{choice_score_sum} 分）+ "
              f"综合应用 {len(design_items)} 题（{design_score_sum} 分）")
        total += 1

    for stale in sorted(OUT.glob(f"408-mock-{args.papers + 1:02d}.json")):
        stale.unlink()
        print(f"[清理] 删除旧整卷 {stale.name}")

    print(f"共生成 {total} 套 408 整卷 -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
