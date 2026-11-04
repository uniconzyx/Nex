# -*- coding: utf-8 -*-
"""给 ai-ch09 / ai-ch10 补「## 本章 GitHub 学习路线」小节。

这两章的 goals.md 历史上漏了这一节（只有 B 站与论文两节），
但 manifest 里 github / github_stars / github_notes 都是齐的，
属于「机器源有、读者页面没有」的同源缺口 —— 本脚本按其余章节的
标准小节版式补全，插在「## 本章 B 站视频路线」之前。
"""
import json
import os

CH_DIR = "content/ai"
MANIFEST = "content/ai/_manifest.json"
HEAD = "## 本章 GitHub 学习路线（按阅读顺序）"


def section(repos, stars, notes, fetched):
    lines = [
        HEAD,
        "",
        f"> ★ 为 **{fetched}** 的 GitHub API 快照（已逐条验证仓库存在）。",
        "> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。"
        "「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；"
        "写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。",
        "",
        "| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |",
        "|---|---|---|---|---|",
    ]
    for i, (repo, star, note) in enumerate(zip(repos, stars, notes), 1):
        if " · " in note:
            h, t = note.split(" · ", 1)
            h, t = h.strip(), t.strip()
        else:
            h, t = "全章", note
        lines.append(
            f"| {i} | [{repo}](https://github.com/{repo}) | {star:,} | {h} | {t} |"
        )
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    data = json.load(open(MANIFEST, encoding="utf-8"))
    for ch in data["chapters"]:
        cid = ch.get("id")
        if cid not in ("ai-ch09", "ai-ch10"):
            continue
        path = os.path.join(CH_DIR, cid, "goals.md")
        with open(path, encoding="utf-8") as f:
            s = f.read()
        if HEAD in s:
            print(f"== {cid}: 已有该小节，跳过")
            continue
        anchor = "## 本章 B 站视频路线（与 GitHub 互补）"
        if anchor not in s:
            print(f"!! {cid}: 找不到 B 站小节锚点")
            continue
        r = ch["resources"]
        block = section(
            r["github"], r["github_stars"], r["github_notes"],
            r.get("github_fetched_at") or "2026-10-27",
        )
        s = s.replace(anchor, block + anchor, 1)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print(f"ok {cid}: 已插入 {len(r['github'])} 行表格")


if __name__ == "__main__":
    main()
