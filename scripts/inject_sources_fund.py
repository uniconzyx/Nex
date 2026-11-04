# -*- coding: utf-8 -*-
"""fundamentals 学科来源锚点重写（23 章 89 条）。

依据：逐章 dump 出 concept/*.md 的真实 `##` 标题，按「文件序号.文件内小节序号」重编 §。

本批清掉四类历史问题：
  1) 学科级复制（fund-ch01~ch12 最严重）：12 章的 36 条笔记共用同一套模板
     「§3.1 讲某话题时读 `docs/算法/` 的某篇」——章与章之间、章与自身小节之间
     都对不上。例：fund-ch07（数据表示）写「§2.3 讲位运算技巧」，
     而该章 §2.3 真实是「无符号数的溢出其实是模回绕」；
     fund-ch08（存储系统）写「§4.2 讲多级缓存的设计」，该章 §4 是「指令周期与流水线」。
  2) 编号越界：fund-ch05/ch06/ch07/ch08/ch09/ch10/ch11/ch12/ch13/ch14/ch15 原 notes
     引用的 §x.y 大量超出本章 concept 文件数（如 fund-ch01 写 §4.1 但只有 4 个文件、
     §3.1 与 §1.2 的位置也全错）。
  3) 泛化锚点：fund-ch13~ch18 用「§性能指标｜先读…」这种只有关键词、没有编号的写法，
     「对应本章」列在读者页面看不出对应哪一节 → 本批统一改成 `§x.y 真实标题 · 读什么`。
  4) 仓库错配：fund-ch13 的 QEMU 笔记挂在 system-design-primer 行；fund-ch22 的
     Linux PHY 笔记挂在 torvalds/linux 行但章节仓库列表里没有 linux 前置说明。
     本批逐条核对「仓库 i 的笔记只说仓库 i 里有的路径」。

分隔符：本学科历史写法混用 `｜`（全角竖线）与 ` · `，统一改为 ` · `。
"""
import json
import os
import re

MANIFEST = "content/fundamentals/_manifest.json"
CH_DIR = "content/fundamentals"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)


def split_note(note: str) -> tuple[str, str]:
    """兼容历史 `｜` 分隔（fund 多章用它），统一按 ` · ` 拆分。"""
    if "｜" in note and " · " not in note:
        head, tail = note.split("｜", 1)
        return head.strip(), tail.strip()
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
    """只改「## 本章 GitHub」小节内的 `| n |` 表格行（B 站表格同形，须框定范围）。"""
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
    """从同级 _notes_fund_part*.py 汇总（拆分只为单文件可读性）。"""
    import importlib.util

    here = os.path.dirname(os.path.abspath(__file__))
    merged: dict[str, list[str]] = {}
    for n in (1, 2, 3):
        p = os.path.join(here, f"_notes_fund_part{n}.py")
        if not os.path.exists(p):
            continue
        spec = importlib.util.spec_from_file_location(f"_nf{n}", p)
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
    print(f"\n完成 {changed}/23 章")


if __name__ == "__main__":
    main()
