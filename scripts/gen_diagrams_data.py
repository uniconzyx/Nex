# -*- coding: utf-8 -*-
"""从各章 concept 抽取 ```text 图表，生成前端数据模块
frontend/src/data/diagrams.ts。

分组方式：按「学科（subject）」分组，学科顺序遵循一条学习链
（基础 → 语言 → 数据 → 存储 → 框架 → 中间件 → 大数据 → 工具 → ML → AI → 全栈 → 智能体）。
每张图抽取其前的 `> ` blockquote 作为详细说明 desc。

与 docs/Diagrams-Archive.md 同源；本脚本产出给 App 直接 import 的结构化数据。

判定「是否为图」采用了「图框字符 / 箭头 / ASCII 边框」正信号 + 「运行输出标记」负信号，
以避免把正文里的运行结果、调试输出、SQL 结果表误当图表捞进来。
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
OUT = ROOT / "frontend" / "src" / "data" / "diagrams.ts"

# content/ 目录名 -> 学科前缀（与章节目录名前缀一致）
DIR_PREFIX: dict[str, str] = {
    "agent": "agent",
    "ai": "ai",
    "bigdata": "bd",
    "clang": "clang",
    "cpp": "cpp",
    "data": "data",
    "database": "db",
    "fullstack": "fs",
    "fundamentals": "fund",
    "java": "java",
    "middleware": "mw",
    "ml": "ml",
    "python": "py",
    "spring": "spring",
    "tooling": "tool",
}

# 学科元信息：展示名 / 在学习链里的定位说明 / 主题色（克制、低饱和，与 kaimao 蓝白协调）
SUBJECT_META: dict[str, dict] = {
    "fund":    {"name": "基础学科", "note": "数据结构 / 计组 / 计网 / 操作系统 —— 一切的地基", "hue": "#34597a"},
    "cpp":     {"name": "C++",      "note": "从内存模型到并发，系统级编程的硬核", "hue": "#2c7a8c"},
    "java":    {"name": "Java",     "note": "JVM 与生态：企业级后端的主力", "hue": "#3f8a6b"},
    "py":      {"name": "Python",   "note": "胶水语言到数据科学的万金油", "hue": "#4a6fa5"},
    "data":    {"name": "数据分析", "note": "NumPy / Pandas：向量化与表格实战", "hue": "#4a8c6f"},
    "db":      {"name": "数据库",   "note": "SQL、索引与事务，数据的家", "hue": "#5a7d9a"},
    "spring":  {"name": "Spring",   "note": "IoC 与生态，Java 后端的骨架", "hue": "#2f8f7a"},
    "mw":      {"name": "中间件",   "note": "缓存与消息队列，系统的承上启下", "hue": "#7a6a4a"},
    "bd":      {"name": "大数据",   "note": "Hadoop / Spark：海量数据的批与流", "hue": "#4a8c8c"},
    "tool":    {"name": "工具链",   "note": "Linux / Git / Docker：工程化的手脚", "hue": "#5d6e8c"},
    "ml":      {"name": "机器学习", "note": "从拟合到泛化的数学与工程", "hue": "#3f6f9a"},
    "ai":      {"name": "AI 工程",  "note": "推理部署与多模态落地", "hue": "#3f6f8a"},
    "fs":      {"name": "全栈工程", "note": "前端到后端，把能力交到用户手里", "hue": "#5d7d9a"},
    "agent":   {"name": "智能体",   "note": "工具 / 记忆 / 规划，会干活的 AI", "hue": "#2c6e8f"},
    "clang":   {"name": "编译原理", "note": "从源码到机器码的全链路", "hue": "#6a7d5a"},
}

# 学习链顺序（只出现在有图学科里）
SUBJECT_ORDER = ["fund", "cpp", "java", "py", "data", "db", "spring",
                 "mw", "bd", "tool", "ml", "ai", "fs", "agent", "clang"]

CHAP_RE = re.compile(r"^([a-z]+)-(ch|u)\d", re.IGNORECASE)
FENCE = re.compile(r"^```text\s*$(.*?)^```\s*$", re.MULTILINE | re.DOTALL)

# 正信号：图框字符 / 流向箭头 / ASCII 边框
BOXRUNE = "─│┌┐└┘├┤┬┴┼╔╗╚╝║═╣╠╦╩╬"
ARROWS = "▶▼▲◆●○►⇄→⇒↳⇨⟶⟹➜«»"
# 负信号：运行输出 / 调试痕迹 / SQL 结果表（强信号，命中即判非图）
RUN_MARKERS = [
    "比较次数", "移动次数", "交换次数", "是否稳定 =",
    "趟无交换", "已有序序列", "逆序序列",
    "Query OK", "rows affected", "row affected",
]


def _ascii_border(line: str) -> bool:
    s = line.strip()
    # 真正的 ASCII 图框行通常以 | 或 + 起头（盒式边框），
    # 而 SQL 结果表的行以数据（数字/字母）起头，借此区分。
    return bool(s) and s[0] in "+|"


def is_diagram(body: str) -> bool:
    # 负信号优先：运行输出 / 调试痕迹一律不算图
    if any(k in body for k in RUN_MARKERS):
        return False
    lines = [l for l in body.splitlines() if l.strip() != ""]
    if not lines:
        return False
    # 极小块：只有出现图框字符才算图
    if len(lines) < 3:
        return any(any(c in BOXRUNE for c in l) for l in lines)
    if any(any(c in BOXRUNE for c in l) for l in lines):
        return True
    if sum(_ascii_border(l) for l in lines) >= 2:
        return True
    if sum(any(c in ARROWS for c in l) for l in lines) >= 2:
        return True
    return False


def chapter_topic(subject: str, ch: str) -> str:
    d = CONTENT / subject / ch / "concept"
    files = sorted(d.glob("*.md"))
    if not files:
        return ch
    first = files[0].read_text(encoding="utf-8")
    for ln in first.splitlines():
        if ln.startswith("# "):
            t = ln[2:].strip()
            t = re.sub(r"^学习目标[：: ]*", "", t)
            t = re.sub(r"^[a-z]+-(ch|u)\d+\s*[·•]\s*", "", t, flags=re.I)
            t = re.sub(r"\s*·\s*学习目标.*$", "", t)
            t = re.sub(r"\s*\([^)]*\)\s*$", "", t)
            return t.strip() or ch
    return ch


def grab_desc(text: str, start: int) -> str:
    pre = text[:start].rstrip("\n")
    lines = pre.split("\n")
    out = []
    for ln in reversed(lines):
        s = ln.strip()
        if s.startswith(">"):
            out.append(s.lstrip("> ").strip())
        elif s == "":
            # 允许图与说明之间有一个空行
            continue
        else:
            break
    out.reverse()
    return " ".join(out).strip()


def extract_chapter(subject_dir: str, ch: str):
    d = CONTENT / subject_dir / ch / "concept"
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        for m in FENCE.finditer(text):
            body = m.group(1).strip("\n")
            if not is_diagram(body):
                continue
            desc = grab_desc(text, m.start())
            out.append({
                "chapter": ch,
                "title": chapter_topic(subject_dir, ch),
                "source": f"{ch}/concept/{f.name}",
                "code": body,
                "desc": desc,
            })
    return out


def discover() -> dict[str, tuple[str, list[str]]]:
    """返回 {subject_prefix: (content_dir_name, [chapter_id, ...])}"""
    by_subject: dict[str, tuple[str, list[str]]] = {}
    for sub in sorted(CONTENT.iterdir()):
        if not (sub.is_dir() and not sub.name.startswith("_")):
            continue
        prefix = DIR_PREFIX.get(sub.name)
        if not prefix or prefix not in SUBJECT_META:
            continue
        chs = [c.name for c in sorted(sub.iterdir())
               if c.is_dir() and CHAP_RE.match(c.name)]
        if chs:
            by_subject[prefix] = (sub.name, chs)
    return by_subject


def main() -> int:
    by_subject = discover()
    subjects = []
    for key in SUBJECT_ORDER:
        found = by_subject.get(key)
        if not found:
            continue
        dir_name, chs = found
        meta = SUBJECT_META[key]
        entries = []
        for ch in chs:
            entries.extend(extract_chapter(dir_name, ch))
        if not entries:
            continue
        subjects.append({
            "key": key,
            "name": meta["name"],
            "note": meta["note"],
            "hue": meta["hue"],
            "entries": entries,
        })

    total = sum(len(s["entries"]) for s in subjects)
    ts = (
        "// AUTO-GENERATED by scripts/gen_diagrams_data.py — 不要把本文件当手改对象，改抽图脚本后重跑。\n"
        "export interface DiagramEntry {\n"
        "  chapter: string;\n"
        "  title: string;\n"
        "  source: string;\n"
        "  code: string;\n"
        "  desc: string;\n"
        "}\n"
        "export interface DiagramSubject {\n"
        "  key: string;\n"
        "  name: string;\n"
        "  note: string;\n"
        "  hue: string;\n"
        "  entries: DiagramEntry[];\n"
        "}\n"
        "export const DIAGRAM_SUBJECTS: DiagramSubject[] = "
        + json.dumps(subjects, ensure_ascii=False, indent=2)
        + ";\n"
    )
    OUT.write_text(ts, encoding="utf-8")
    print(f"[ok] 写出 {OUT}  学科数={len(subjects)}  图表总数={total}")
    for s in subjects:
        print(f"     {s['name']:>6} ({s['key']}): {len(s['entries'])} 张")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
