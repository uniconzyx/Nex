#!/usr/bin/env python
"""生成数学、英语、政治的「题目分类总结」（阶段16）。

为什么不手写：每科的专题、题型、步骤、陷阱、考点提示都已经在 frameworks/ 与 knowledge/ 里，
总结再抄一遍就会出现「总结说 A、框架说 B」的两套口径。这里按专题聚合：
  识别特征 ← 该专题所有题型的 ask
  通用框架 ← 第一个题型的 steps
  技巧     ← 该专题知识点的 tip
  陷阱     ← 所有题型的 traps（去重）
  题目清单 ← 从 questions/ 反查，保证不漏不重
408 的总结是手写的（更细），本脚本不覆盖它们。
"""

from __future__ import annotations

import json
from pathlib import Path

from exam_ordering import order_questions

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"

POOLS = [
    ("math", "m2"), ("math", "m1"),
    ("english", "e1"), ("english", "e2"),
    ("politics", "pol"),
    ("discrete", "dm"), ("algorithm", "algo"),
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    for exam, subj in POOLS:
        fw = load(EXAM / "frameworks" / f"{subj}.json")
        kn = load(EXAM / "knowledge" / f"{exam}-{subj}.json")
        qs = load(EXAM / "questions" / f"{exam}-{subj}.json")

        titles = {t["topic"]: t["chapter"] for t in kn["items"]}
        kids = {t["topic"]: t["knowledge"] for t in kn["items"]}
        by_topic: dict[str, list[dict]] = {}
        for q in qs["items"]:
            by_topic.setdefault(q["topic"], []).append(q)

        groups = []
        for t in fw["topics"]:
            tid = t["id"]
            items = by_topic.get(tid) or []
            if not items:
                continue
            pats = t["patterns"]
            steps = pats[0]["steps"]
            traps: list[str] = []
            for p in pats:
                for x in p["traps"]:
                    if x not in traps:
                        traps.append(x)

            skills = [{"title": k["title"], "body": k["tip"]}
                      for k in kids.get(tid, [])][:3]
            if not skills:
                skills = [{"title": p["title"], "body": p["ask"]} for p in pats][:2]

            qids = [q["id"] for q in items]
            groups.append({
                "topic": tid,
                "title": titles.get(tid, t["title"]),
                "recognize": "本专题常见问法：" + "；".join(p["ask"] for p in pats)
                             + "。看到这类问法先归到本专题，再套下面的固定步骤，不要从题目细节重新想。",
                "framework": steps,
                "skills": skills,
                "traps": traps[:4],
                "questionIds": qids,
                "suggestedOrder": order_questions(items),
            })

        out = EXAM / "summaries" / f"{exam}-{subj}.json"
        out.write_text(json.dumps({"subject": subj, "exam": exam, "groups": groups},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{exam}-{subj}: {len(groups)} 组总结 / {sum(len(g['questionIds']) for g in groups)} 题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
