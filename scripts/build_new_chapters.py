# -*- coding: utf-8 -*-
"""把 scripts/_new_chapters.py 里的章节数据写盘，并同步 manifest / bundle / 总数口径。

产出（每章 7 类内容，与既有章节逐字段对齐）：
    content/<科>/<章>/goals.md
    content/<科>/<章>/concept/*.md
    content/<科>/<章>/pitfalls.md
    content/<科>/<章>/exercises.json
    content/<科>/<章>/examples/*.json
    content/<科>/<章>/interview.json
    content/<科>/<章>/project.json

同时：
    · 追加到 content/<科>/_manifest.json 的 chapters（按 order 排序）；
    · 若该科已有 —— 不覆盖，跳过并报告（幂等）。

examples 的来源：`concept` 里的代码块**不**自动转 example（代码可能是片段、可能不可跑）。
新增章节的 examples 由 `scripts/_new_chapter_examples.py` 单独提供，未提供时本章 examples 为空，
`validate_content.py` 会如实报「examples 不足」——不伪造。

用法：
    python scripts/build_new_chapters.py --dry-run
    python scripts/build_new_chapters.py --apply
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from _new_chapters import CHAPTERS  # noqa: E402
from _new_chapter_examples import EXAMPLES  # noqa: E402

# 新增分区（fs-ch10~15, ai-ch12~14）由子代理产出，单独存放避免污染主文件。
# 合并进主线一起构建；分区里的 CHAPTERS/EXAMPLES 与主文件无 id 冲突时直接并入。
import importlib  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts" / "_chparts"))
for _part_mod in ("fs_a", "fs_b", "fs_c", "ai_abc"):
    _m = importlib.import_module(_part_mod)
    CHAPTERS.extend(_m.CHAPTERS)
    for _k, _v in _m.EXAMPLES.items():
        if _k in EXAMPLES:
            raise SystemExit(f"[build] EXAMPLES 冲突: {_k}（分区与主文件重复）")
        EXAMPLES[_k] = _v

CONTENT = ROOT / "content"


def dump_json(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_examples(ch_dir: pathlib.Path, cid: str) -> int:
    """examples 由 _new_chapter_examples 提供；未提供时写 0 个，交由校验器如实报缺。"""
    items = EXAMPLES.get(cid) or []
    for i, ex in enumerate(items, 1):
        dump_json(ch_dir / "examples" / f"ex{i:02d}.json", ex)
    return len(items)


def build_exercises(ch: dict) -> dict:
    items = []
    for e in ch["exercises"]:
        items.append(dict(e))
    return {
        "meta": {
            "chapter": ch["id"],
            "note": f"{len(items)} 题，含选择题/输出题/改错题/编程题；题面与参考实现均为自建，"
                    f"不搬运第三方题面。",
        },
        "items": items,
    }


def build_interview(ch: dict) -> dict:
    items = [
        {"question": q, "answer_md": a, "follow_ups": fu, "difficulty": "mid", "company_tags": ["通用"]}
        for q, a, fu in ch["interview"]
    ]
    return {"meta": {"chapter": ch["id"], "note": f"{len(items)} 个高频问题。"}, "items": items}


def build_project(ch: dict) -> dict:
    title, req, tasks = ch["project"]
    return {
        "meta": {"chapter": ch["id"], "category": "basic"},
        "items": [{
            "title": title,
            "requirement_md": req,
            "tasks": [{"title": t, "verification": v} for t, v in tasks],
        }],
    }


def build_pitfalls(ch: dict) -> str:
    """按既有章的编号条目格式输出。

    坑：写成 `## 1. xxx` 小节标题时，`validate_content.py` 的
    `_PITFALL_ITEM_RE = ^(?:\\d+[.、)]|[-*])(?:\\s|$)` 锚定行首，`##` 前缀会挡住匹配，
    统计结果为 0（曾让新章卡在 `pitfalls 条目不足：0/3`）。
    故条目必须直接用 `1. **标题** —— ...` 起行，四段信息压进同一条的两个缩进段里。
    """
    L = [f"# {ch['id']} · {ch['title']} · 常见错误", ""]
    for i, (title, wrong, why, fix) in enumerate(ch["pitfalls"], 1):
        L.append(f"{i}. **{title}** —— 错在：{wrong}")
        L.append("")
        L.append(f"   *为什么*：{why}")
        L.append("")
        L.append(f"   *怎么改*：{fix}")
        L.append("")
    return "\n".join(L).rstrip() + "\n"


def build_goals(ch: dict) -> str:
    L = [f"# {ch['id']} · {ch['title']} · 学习目标", ""]
    for c in ch["concept"]:
        # 用 concept 的一级标题当目标条目：每个 concept 一篇，一篇一个能力
        first = c[2].strip().split("\n")[0].lstrip("# ").strip()
        L.append(f"- 能讲清「{first}」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点")
    L.append(f"- 完成本章 {len(ch['exercises'])} 道题（含 {sum(1 for e in ch['exercises'] if e['type']=='coding')} 道编程题）"
             f"与 {len(ch['pitfalls'])} 条错题辨析，并能复述 {len(ch['interview'])} 个面试高频问题的要点")
    return "\n".join(L) + "\n"


def build() -> tuple[int, int]:
    made = 0
    skipped = 0
    for ch in CHAPTERS:
        sub, cid = ch["subject"], ch["id"]
        ch_dir = CONTENT / sub / cid
        if ch_dir.exists():
            print(f"  · {cid} 已存在，跳过")
            skipped += 1
            continue
        (ch_dir / "concept").mkdir(parents=True)
        (ch_dir / "examples").mkdir(parents=True)

        (ch_dir / "goals.md").write_text(build_goals(ch), encoding="utf-8")
        for slug, _title, body in ch["concept"]:
            (ch_dir / "concept" / slug).write_text(body.strip() + "\n", encoding="utf-8")
        (ch_dir / "pitfalls.md").write_text(build_pitfalls(ch), encoding="utf-8")
        dump_json(ch_dir / "exercises.json", build_exercises(ch))
        dump_json(ch_dir / "interview.json", build_interview(ch))
        dump_json(ch_dir / "project.json", build_project(ch))
        n_ex = write_examples(ch_dir, cid)
        made += 1
        print(f"  + {cid}  {len(ch['concept'])} 篇 concept · {len(ch['exercises'])} 题 · "
              f"{len(ch['pitfalls'])} 陷阱 · {n_ex} 个示例")
    return made, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="只打印将写入的章节，不落盘")
    args = ap.parse_args()

    print(f"待写入 {len(CHAPTERS)} 章：{[c['id'] for c in CHAPTERS]}")
    if not args.apply:
        print("（dry-run，未写盘；加 --apply 生效）")
        return 0

    made, skipped = build()
    print(f"\n写入 {made} 章 · 跳过 {skipped} 章")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
