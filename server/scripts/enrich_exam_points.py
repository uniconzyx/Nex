#!/usr/bin/env python
"""把 questions 里 points 的「知识点层」补成可读的三段：名称、核心结论、本题易错。

生成器最初只写了 points[].id 和一句 note，其中多数 note 其实是「易错点」，
导致讲解页的知识点层只剩一串 id。这里统一从 knowledge 表回填 title / core，
把原来的 note 收进 pitfall，并在与框架 trap 重复时去掉。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def meaningful(text: str, already: str) -> bool:
    """旧 note 是否还带新信息：非空、且没有被框架 trap / 解析中的错误说明覆盖。"""
    t = (text or "").strip().rstrip("。;；")
    if len(t) < 10:
        return False
    return t not in (already or "")


def apply_points(q: dict, index: dict, touched: list[str]) -> None:
    fw = q["walkthrough"]["framework"]
    for p in q["walkthrough"]["points"]:
        k = index.get(p.get("id"))
        if not k:
            touched.append(p.get("id", "?"))
            continue
        old = p.get("note", "")
        p["title"] = k["title"]
        p["core"] = k["core"]
        p["note"] = k["core"]
        if meaningful(old, fw.get("trap")) and old.strip() != k["core"].strip():
            p["pitfall"] = old.strip()
        else:
            p.pop("pitfall", None)


def main() -> int:
    meta = load(EXAM / "_meta.json")
    # 知识点 id 全局唯一，用一张总表，408 套卷跨四科引用时也能对上
    global_index: dict[str, dict] = {}
    for path in (EXAM / "knowledge").glob("*.json"):
        for block in load(path)["items"]:
            for k in block["knowledge"]:
                global_index[k["id"]] = k

    touched = 0
    for e in meta["exams"]:
        for s in e["subjects"]:
            path = EXAM / "questions" / f"{e['key']}-{s['key']}.json"
            data = load(path)
            for q in data["items"]:
                apply_points(q, global_index, [])
                touched += 1
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 套卷里内嵌的整段快照也要补：它们不经过 questions 文件
    patched = 0
    for path in sorted((EXAM / "papers").glob("*.json")):
        data = load(path)
        for sec in data.get("sections", []):
            for item in sec.get("items", []):
                if isinstance(item, dict) and "walkthrough" in item:
                    apply_points(item, global_index, [])
                    patched += 1
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"回填知识点层：{touched} 题 / 套卷快照 {patched} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
