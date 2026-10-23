#!/usr/bin/env python
"""回填 / 更新所有分类总结的 suggestedOrder 字段（阶段16 第④步）。

对每份 summaries/{exam}-{subject}.json 的每个 group：
  1. 用同名的 questions/{exam}-{subject}.json 建 id→题目 索引（取 diff / knowledge）。
  2. 调用 exam_ordering.order_questions 计算「由易到难 + 相邻不重复考点」的顺序。
  3. 把 suggestedOrder 字段写回，紧跟在 questionIds 之后（保持其它字段顺序不变）。

本脚本幂等：每次都重算，可安全重复运行。生成式总结（gen_exam_summaries.py）
也已内置该字段，本脚本作为兜底 / 手写总结（408 四科）的回填入口。
"""

from __future__ import annotations

import json
from pathlib import Path

from exam_ordering import order_questions

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def backfill_group(g: dict, by_id: dict[str, dict]) -> dict:
    ids: list[str] = g.get("questionIds") or []
    qs = [by_id.get(i) or {"id": i, "diff": None, "knowledge": f"__missing__{i}"} for i in ids]
    order = order_questions(qs)
    ng: dict = {}
    for k, v in g.items():
        ng[k] = v
        if k == "questionIds":
            ng["suggestedOrder"] = order
    if "questionIds" not in g:
        ng["suggestedOrder"] = order
    return ng


def main() -> int:
    total_groups = 0
    for sp in sorted(EXAM.glob("summaries/*.json")):
        stem = sp.stem  # exam-subject
        qp = EXAM / "questions" / f"{stem}.json"
        by_id: dict[str, dict] = {}
        if qp.exists():
            qd = load(qp)
            for q in qd.get("items", []):
                if q.get("id"):
                    by_id[q["id"]] = q
        doc = load(sp)
        new_groups = [backfill_group(g, by_id) for g in doc.get("groups", [])]
        doc["groups"] = new_groups
        save(sp, doc)
        total_groups += len(new_groups)
        print(f"{stem}: {len(new_groups)} 组 -> suggestedOrder 已写回")
    print(f"合计 {total_groups} 组")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
