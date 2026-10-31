# -*- coding: utf-8 -*-
"""把已插入各章 concept 的 ```text 图表按「逻辑学习链条」归档成单文档。

学习链顺序：
  ① 基础学科(fundamentals) ch01→ch12：数组/链表→栈队列→树→图→查找哈希→排序
     →机器数表示→存储层次/CPU→进程线程→虚拟内存/文件→网络分层→应用层
  ② 全栈工程(fullstack) fs-ch10→fs-ch15：Vue 响应式→Spring Boot→服务拆分/网关
     →前端测试→Agent×全栈→Go+Gin
  ③ AI 工程(ai) ai-ch12→ai-ch14：SFT 数据→推理引擎/量化→多模态落地
输出：docs/Diagrams-Archive.md
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
OUT = ROOT / "docs" / "Diagrams-Archive.md"

# (group_title, [(subject, chapter_id), ...])
CHAIN = [
    ("一、基础学科（数据结构 / 计组 / 计网 / 操作系统）", [
        ("fundamentals", "fund-ch01"), ("fundamentals", "fund-ch02"),
        ("fundamentals", "fund-ch03"), ("fundamentals", "fund-ch04"),
        ("fundamentals", "fund-ch05"), ("fundamentals", "fund-ch06"),
        ("fundamentals", "fund-ch07"), ("fundamentals", "fund-ch08"),
        ("fundamentals", "fund-ch09"), ("fundamentals", "fund-ch10"),
        ("fundamentals", "fund-ch11"), ("fundamentals", "fund-ch12"),
    ]),
    ("二、全栈工程（前端 → 后端 → 工程化 → Agent 接缝）", [
        ("fullstack", "fs-ch10"), ("fullstack", "fs-ch11"),
        ("fullstack", "fs-ch12"), ("fullstack", "fs-ch13"),
        ("fullstack", "fs-ch14"), ("fullstack", "fs-ch15"),
    ]),
    ("三、AI 工程（数据 → 推理部署 → 多模态）", [
        ("ai", "ai-ch12"), ("ai", "ai-ch13"), ("ai", "ai-ch14"),
    ]),
]

FENCE = re.compile(r"^```text\s*$(.*?)^```\s*$", re.MULTILINE | re.DOTALL)

# 代码运行输出（非图表）的特征串：落入则视为「示例输出」而非「逻辑结构图」，归档时剔除
RUN_OUTPUT_MARKERS = [
    "比较次数", "移动次数", "交换次数", "运行结果", "排序结果",
    "趟无交换", "已有序序列", "逆序序列", "是否稳定 =", "输出：", "输出:",
]


def is_diagram(body: str) -> bool:
    return not any(k in body for k in RUN_OUTPUT_MARKERS)


def chapter_topic(subject: str, ch: str) -> str:
    d = CONTENT / subject / ch / "concept"
    files = sorted(d.glob("*.md"))
    if not files:
        return "(无 concept)"
    first = files[0].read_text(encoding="utf-8")
    for ln in first.splitlines():
        if ln.startswith("# "):
            t = ln[2:].strip()
            # 去掉章节首文件标题里可能带的前导 "01 · " 序号，避免 "fund-ch10 · 01 · …" 重复
            t = re.sub(r"^\d+\s*·\s*", "", t)
            return t
    return "(无标题)"


def extract(subject: str, ch: str):
    d = CONTENT / subject / ch / "concept"
    out = []
    for f in sorted(d.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        for m in FENCE.finditer(text):
            body = m.group(1).strip("\n")
            if not is_diagram(body):
                continue
            out.append((f.name, body))
    return out


def main() -> int:
    parts = []
    parts.append("# 图表归档 · 按逻辑学习链条\n")
    parts.append(
        "> 本档案汇集 CppMind 各章 concept 中用 ```` ```text ```` 围栏绘制的 ASCII/Unicode 图表，"
        "用于复习时按「由浅入深、由基础到工程」的顺序串成一条学习链。\n"
        "> 顺序遵循：① 基础学科（DS/计组/计网/OS）② 全栈工程 ③ AI 工程。\n"
    )
    total = 0
    for gtitle, chs in CHAIN:
        parts.append(f"\n## {gtitle}\n")
        for subject, ch in chs:
            topic = chapter_topic(subject, ch)
            diags = extract(subject, ch)
            total += len(diags)
            parts.append(f"### {ch} · {topic}\n")
            if not diags:
                parts.append("_(本章暂无图表)_\n")
                continue
            for i, (fname, body) in enumerate(diags, 1):
                if len(diags) > 1:
                    parts.append(f"**图 {i}**（来源：`{ch}/concept/{fname}`）\n")
                else:
                    parts.append(f"**来源**：`{ch}/concept/{fname}`\n")
                parts.append("```text\n" + body + "\n```\n")
    parts.append(f"\n---\n\n> 共归档 **{total}** 张图表，覆盖 21 章。\n")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"[ok] 写出 {OUT}  图表总数={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
