# -*- coding: utf-8 -*-
"""cpp 学科来源笔记 · 第 1 部分（cpp-ch02 / 05 / 06 / 07 / 08 / 09）。

cpp 与 ai/fund 的病因不同：notes 的技术内容基本成立，问题全在「编号—标题错位」——
写 §2.1 讲重载、但该章 §2.1 真实是「重载解决的是什么问题」之外的别节；
另有少数仓库错配（`geometry.h` 属 tinyrenderer 却挂在 nlohmann 行）。
本批只做两件事：把 §x.y 对齐真实标题、把每条归回正确的仓库。
"""
import json
import os
import re

MANIFEST = "content/cpp/_manifest.json"
CH_DIR = "content/cpp"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)


def split_note(note: str) -> tuple[str, str]:
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
    path = os.path.join(CH_DIR, cid, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")

    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    if not row_idx:
        return False, "小节内无表格行"
    if len(row_idx) != len(notes):
        return False, f"表格 {len(row_idx)} 行、notes {len(notes)} 条，不匹配"

    for i, note in zip(row_idx, notes):
        m = RE_GH_ROW.match(lines[i])
        head, tail = split_note(note)
        lines[i] = (
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )

    out = "\n".join(lines)
    if out == s:
        return True, "已是同源"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    return True, f"表格 {len(row_idx)} 行已同步"


def load_notes() -> dict[str, list[str]]:
    import importlib.util

    here = os.path.dirname(os.path.abspath(__file__))
    merged: dict[str, list[str]] = {}
    for n in (1, 2, 3):
        p = os.path.join(here, f"_notes_cpp_part{n}.py")
        if not os.path.exists(p):
            continue
        spec = importlib.util.spec_from_file_location(f"_nc{n}", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        merged.update(mod.NOTES)
    return merged


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        raw = fb.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    data = json.loads(raw.decode("utf-8"))
    notes_map = load_notes()
    changed = 0
    for ch in data.get("chapters", []):
        cid = ch.get("id") or ch.get("chapter_id")
        notes = notes_map.get(cid)
        if not notes:
            continue
        res = ch.get("resources") or {}
        cur = res.get("github_notes") or []
        if len(cur) != len(notes):
            print(f"!! {cid}: 原 {len(cur)} 条 / 新 {len(notes)} 条，不匹配，跳过")
            continue
        res["github_notes"] = notes
        ch["resources"] = res
        ok, msg = rewrite_goals_table(cid, notes)
        print(f"{'ok' if ok else '!!'} {cid}: manifest 已改，goals {msg}")
        changed += 1

    out = json.dumps(data, ensure_ascii=False, indent=2)
    if nl == "\r\n":
        out = out.replace("\n", "\r\n")
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print(f"\n完成 {changed} 章")


if __name__ == "__main__":
    main()
