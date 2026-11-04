# -*- coding: utf-8 -*-
"""cpp 批次：给 notes 补 § 锚点后，把 goals.md 的「对应本章 / 读什么」两列同步到同源。

幂等：重复执行只会把表格重写成同样内容。
"""
import re

GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)


def split_note(note: str) -> tuple[str, str]:
    """把 "<对应本章> · <读什么>" 拆成两栏；无分隔符则整条进「读什么」。"""
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(ch_dir: str, cid: str, notes: list[str]) -> tuple[bool, str]:
    """按 notes 重写 goals.md「## 本章 GitHub」小节下连续的 `| n |` 行。"""
    path = f"{ch_dir}/{cid}/goals.md"
    s = open(path, encoding="utf-8").read()
    lines = s.splitlines()

    # 定位「## 本章 GitHub」小节范围，避免误伤 B 站表格（B 站表同样 5 列、同样 | 1 |）
    try:
        start = next(
            i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub")
        )
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = [i for i in range(start, end) if GH_ROW.match(lines[i])]
    if len(row_idx) != len(notes):
        return False, f"表格 {len(row_idx)} 行、notes {len(notes)} 条，不匹配"

    new_lines = []
    for i, note in zip(row_idx, notes):
        m = GH_ROW.match(lines[i])
        head, tail = split_note(note)
        new_lines.append(
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )

    for i, txt in zip(row_idx, new_lines):
        lines[i] = txt

    out = "\n".join(lines)
    if not s.endswith("\n"):
        out += "\n"
    if out == s:
        return True, "已是同源，未改"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    return True, f"重写 {len(row_idx)} 行"


def main() -> None:
    import json

    manifest = json.load(open("content/cpp/_manifest.json", encoding="utf-8"))

    TARGETS = ["cpp-ch01", "cpp-ch03", "cpp-ch04", "cpp-ch08"]

    print("=" * 62)
    for ch in manifest.get("chapters", []):
        cid = ch.get("id") or ch.get("chapter_id")
        if cid not in TARGETS:
            continue
        notes = ch.get("resources", {}).get("github_notes", [])
        if not notes:
            print(f"!! {cid} 无 notes")
            continue
        ok, msg = rewrite_goals_table("content/cpp", cid, notes)
        print(f"{'OK ' if ok else '!! '}{cid}: {msg}（notes {len(notes)} 条）")
    print("=" * 62)


if __name__ == "__main__":
    main()
