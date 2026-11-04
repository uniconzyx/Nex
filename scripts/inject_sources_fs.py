# -*- coding: utf-8 -*-
"""批次三 · 来源颗粒度补齐：fullstack fs-ch01

与 inject_sources_agent.py 同一套路（表格改写、CRLF 写盘、` · ` 拆分），
这里只写本批差异与内容。

为什么只有 fs-ch01
------------------
全学科复检后，fullstack 只有 fs-ch01 的 notes 是纯泛泛描述：
    「系统设计入门：HTTP/API/缓存/CDN/负载均衡的工程视角（英文）」
    「技术面试必备基础知识：计算机网络与 HTTP 专题的中文精华笔记」
读者看完不知道打开哪个文件、读哪一段。

fs-ch12 及 fundamentals 全系虽然也有个别条缺反引号，但主体已是
「§小节 + 文件 + 证明什么」的合格写法，不在本批范围内。

注意 fs-ch01 的小节是「一、二、三、四」而非 §x.y 编号，
锚点按实际标题写（§一 理论根基 / §二 实现机制 …），不要臆造 §1.1。

三要素
------
  §小节号 + `入口文件/目录` + 证明本章哪条结论

每条写成 "<对应本章> · <读什么>"，脚本按 ` · ` 切开：
前半进 goals.md 表格「对应本章」列，后半进「读什么」列。
**分隔符必须是前后各一个半角空格**（写成 `）· §` 会让 split 静默失败）。
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
FS_DIR = os.path.join(ROOT, "content", "fullstack")
MANIFEST = os.path.join(FS_DIR, "_manifest.json")

# GitHub 资源表行：| n | [owner/repo](url) | 12,345 | 对应本章 | 读什么 |
RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)

NOTES = {
    "fs-ch01": [
        "§一 理论根基 · §二 报文的确切结构："
        "`README.md` 的 HTTP 一节给了请求/响应报文的逐行拆解，"
        "对照本章「状态行 + 首部 + 空行 + 主体」四段结构，别只记「GET/POST」",
        "§二 高频头部 · §三 工程实践（缓存）："
        "`docs/` 里计算机网络专题把强缓存与协商缓存分成两节写，"
        "读它「304 为什么不带主体」，就懂本章「缓存省的是哪一段带宽」",
        "§二 报文结构 · §四 边界与陷阱（首部时序）："
        "`lib/_http_outgoing.js` 的 `writeHead` 决定首部何时定型，"
        "读它就知道本章「头部必须在主体前发完」不是约定而是实现约束",
        "§四 边界与陷阱（CORS 预检） · §三 工程实践："
        "`packages/` 里的请求模块能直接看/改请求头，"
        "手动构造一个 `OPTIONS` 预检，本章「简单请求 vs 预检请求」当场可见",
    ],
}
def split_note(note: str) -> tuple[str, str]:
    """把 "<对应本章> · <读什么>" 拆成两栏；无分隔符则整条进「读什么」。"""
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(ch_dir: str, cid: str) -> tuple[bool, str]:
    """只改「## 本章 GitHub」小节内的 `| n |` 表格行。

    B 站小节的表格同样 5 列、同样以 `| 1 |` 开头（区别是第 2 列是链接而非仓库名），
    全文件扫会把视频说明覆盖掉，所以必须先框定小节范围。
    """
    path = os.path.join(ch_dir, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"

    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    notes = NOTES.get(cid) or []
    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        # fs-ch01 缺失该小节标题：表格直接接在上一节后面。
        # 标题是 goals.md 的章节骨架（也是 audit 定位资源段的锚），必须补上，
        # 否则读者在页面里看到的是一张没有标题的裸表。
        anchor = next(
            (i for i, ln in enumerate(lines)
             if ln.startswith("## ") and "B 站" in ln),
            None,
        )
        first_row = next(
            (i for i, ln in enumerate(lines) if RE_GH_ROW.match(ln)), None
        )
        if first_row is None or anchor is None:
            return False, "找不到「## 本章 GitHub」小节且无法定位表格"
        lines.insert(first_row, "## 本章 GitHub 学习路线（按阅读顺序）")
        lines.insert(first_row + 1, "")
        start = first_row

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = 0
    for i in range(start, end):
        m = RE_GH_ROW.match(lines[i])
        if not m:
            continue
        num, name, url, star, _c, _r = m.groups()
        if row_idx >= len(notes):
            row_idx += 1
            continue
        corner, read = split_note(notes[row_idx])
        lines[i] = f"| {num} | [{name}]({url}) | {star} | {corner} | {read} |"
        row_idx += 1

    if row_idx == 0:
        return False, "GitHub 表格没匹配到任何行"

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    return True, f"表格 {row_idx} 行"


def main() -> int:
    with open(MANIFEST, encoding="utf-8") as f:
        data = json.load(f)

    by_id = {c.get("id"): c for c in (data.get("chapters") or [])}

    n = 0
    for cid, notes in NOTES.items():
        c = by_id.get(cid)
        if not c:
            print(f"!! 找不到章节 {cid}")
            continue
        res = c.setdefault("resources", {})
        repos = res.get("github") or []
        if len(repos) != len(notes):
            print(f"!! {cid} 仓库 {len(repos)} 个、notes {len(notes)} 条，不匹配，跳过")
            continue
        res["github_notes"] = notes
        n += 1
        ok, msg = rewrite_goals_table(os.path.join(FS_DIR, cid), cid)
        print(f"  {cid:<10} {len(notes)} 条 · {'✓' if ok else '✗'} {msg:<12} · {notes[0][:26]}…")

    # 换行格式**按学科探测**：agent/ml/cpp 是 CRLF，其余 11 个学科是 LF。
    # 写死任一种都会让另一种学科整份假 diff，这里统一读一次原文件判断。
    with open(MANIFEST, "rb") as fb:
        nl = "\r\n" if b"\r\n" in fb.read() else "\n"
    with open(MANIFEST, "w", encoding="utf-8", newline=nl) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n写入 {os.path.normpath(MANIFEST)}，共更新 {n} 章")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
