#!/usr/bin/env python
"""把套卷里内嵌的题目副本与题库重新对齐，并校验引用完整性。

选择题存的是题目 id 字符串，填空/设计存的是整段快照（需要单独计分与作答区），
快照会随题库修订而过期。这里按 id 回填，只在快照确实带该字段时更新，
避免把精简快照撑成整题。

硬校验（旧版在这里静默跳过，导致 408-mock-01 留过 7 道游离设计题）：
  1. 字符串引用：id 必须存在于题库，否则组卷器引用了不存在的题；
  2. 内联快照：必须带 id 且该 id 在题库中——
     「卷子里出现题库中不存在的设计题」直接退出非零，
     避免卷子靠游离快照活着、题库增删它都无感。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"
SYNC_FIELDS = ("stem", "ask", "options", "walkthrough", "type", "topic", "knowledge")


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    bank: dict[str, dict] = {}
    for p in (EXAM / "questions").glob("*.json"):
        for q in load(p)["items"]:
            bank[q["id"]] = q

    errors: list[str] = []
    changed = 0
    for p in sorted((EXAM / "papers").glob("*.json")):
        data = load(p)
        dirty = False
        for si, sec in enumerate(data.get("sections", [])):
            for ii, item in enumerate(sec.get("items", [])):
                where = f"{p.name} section[{si}] item[{ii}]"
                if isinstance(item, str):
                    if item not in bank:
                        errors.append(f"{where}: 引用题库中不存在的题目 id={item}")
                    continue
                if not isinstance(item, dict):
                    continue
                qid = item.get("id")
                if not qid:
                    errors.append(f"{where}: 内联快照缺少 id（题库中不存在的设计题）")
                    continue
                src = bank.get(qid)
                if not src:
                    errors.append(f"{where}: 卷子里出现题库中不存在的设计题 id={qid}")
                    continue
                for f in SYNC_FIELDS:
                    if f in item and f in src and item[f] != src[f]:
                        item[f] = src[f]
                        dirty = True
        if dirty:
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
            changed += 1

    if errors:
        print(f"同步中止：{len(errors)} 处引用异常", file=sys.stderr)
        for e in errors[:20]:
            print(f"  [ERR] {e}", file=sys.stderr)
        return 1
    print(f"同步套卷副本：{changed} 份更新，引用完整性通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
