# -*- coding: utf-8 -*-
"""深度审计：量化「学习内容是否深入、完整、透彻」，而不是只数文件个数。

为什么需要它：validate_content.py 守的是**门槛**（concept>=3、examples>=10…），
门槛过了不代表内容有深度——3 篇各 1200 字的 concept 也能过。本脚本换一组
「密度指标」来找出真正薄的章节。

每章测 8 个维度：
    1. 概念字数      concept/*.md 去空白后的中文字符+英文单词数
    2. 公式块数      $$...$$ 与 $...$ 的数量（推导密度的代理指标）
    3. 代码块数      ``` 围栏数（是否给可运行的对照实现）
    4. 三级标题数    ### 的数量（是否把知识点拆到可检索粒度）
    5. 陷阱条数      pitfalls.md 的列表项数
    6. 示例真实输出  examples/*.json 里 expected_output 非空的比例
    7. 题目类型分布  exercises.json 的 type 集合（choice/output/coding/fix_error/design）
    8. 目标与边界    goals.md 是否有「边界」声明（与相邻章节的划界）

分级（阈值见 THRESH）：
    A 扎实 / B 合格 / C 偏薄 —— C 级就是需要补的清单。

用法：
    python scripts/audit_depth.py
    python scripts/audit_depth.py --min-grade B     # 只列 C 级
    python scripts/audit_depth.py --subject ml
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

RE_ZH = re.compile(r"[\u4e00-\u9fa5]")
RE_EN = re.compile(r"[A-Za-z][A-Za-z\-]{2,}")
RE_DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.S)
RE_INLINE_MATH = re.compile(r"(?<!\$)\$(?!\$)([^$\n]{2,80})\$(?!\$)")
RE_FENCE = re.compile(r"^```", re.M)
RE_H3 = re.compile(r"^### ", re.M)
RE_LI = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\S", re.M)

# 分级阈值：B 级=合格线（低于它就是「薄」），A 级=扎实线。
# 阈值取自 141 章的真实分布（2026-10-28）：concept 字数中位 5621、四分位 4123、
# 代码块中位 8、H3 中位 18、陷阱中位 14。B 线放在中位数下方一档，
# A 线放在 p75 附近——这样「A」确实代表这批内容里的前四分之一，而不是人人有奖。
# 公式数不进分级：cpp/java/python 这类工程学科本来就少公式，拿它判薄是错的，
# 只作为参考指标输出。
THRESH = {
    "concept_chars": (3200, 6000),    # (B, A)
    "code_blocks": (5, 12),
    "h3": (10, 20),
    "pitfalls": (8, 15),
    "example_real_pct": (100, 100),
    "exercise_types": (3, 4),
}


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def grade(value: float, key: str) -> str:
    b, a = THRESH[key]
    if value >= a:
        return "A"
    if value >= b:
        return "B"
    return "C"


def count_chars(text: str) -> int:
    """中文字符 + 英文单词，去掉代码块（代码不计入「讲解密度」）。"""
    no_code = re.sub(r"```.*?```", "", text, flags=re.S)
    return len(RE_ZH.findall(no_code)) + len(RE_EN.findall(no_code))


def audit_chapter(ch: Path) -> dict:
    concepts = sorted((ch / "concept").glob("*.md"))
    ctext = "\n".join(read(f) for f in concepts)
    chars = count_chars(ctext)
    formulas = len(RE_DISPLAY_MATH.findall(ctext)) + len(RE_INLINE_MATH.findall(ctext))
    codes = len(RE_FENCE.findall(ctext)) // 2
    h3 = len(RE_H3.findall(ctext))

    pit_text = read(ch / "pitfalls.md")
    pitfalls = len(RE_LI.findall(re.sub(r"```.*?```", "", pit_text, flags=re.S)))

    exs = sorted((ch / "examples").glob("*.json"))
    real = 0
    for f in exs:
        d = json.loads(f.read_text(encoding="utf-8"))
        if (d.get("expected_output") or "").strip():
            real += 1
    real_pct = 100.0 * real / len(exs) if exs else 0.0

    types: set[str] = set()
    try:
        ej = json.loads(read(ch / "exercises.json") or "{}")
        items = ej.get("exercises") or ej.get("items") or (ej if isinstance(ej, list) else [])
        for it in items:
            if isinstance(it, dict) and it.get("type"):
                types.add(it["type"])
    except json.JSONDecodeError:
        pass

    goals = read(ch / "goals.md")
    has_boundary = ("边界" in goals) or ("不展开" in goals) or ("不在本章" in goals)

    m = {
        "concept_chars": chars,
        "formulas": formulas,   # 仅参考，不进分级
        "code_blocks": codes,
        "h3": h3,
        "pitfalls": pitfalls,
        "example_real_pct": real_pct,
        "exercise_types": len(types),
    }
    g = {k: grade(v, k) for k, v in m.items() if k in THRESH}
    # 注意用 max 不是 min：等级是字符串，'A'<'B'<'C'，取最差必须用 max。
    worst = max(g.values())
    return {
        "id": ch.name,
        "subject": ch.parent.name,
        "metrics": m,
        "grades": g,
        "boundary_declared": has_boundary,
        "worst": worst,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-grade", default="C", choices=["A", "B", "C"])
    ap.add_argument("--subject", default="")
    args = ap.parse_args()

    rows: list[dict] = []
    for subj in sorted(CONTENT.iterdir()):
        if not subj.is_dir() or subj.name.startswith("_"):
            continue
        if args.subject and subj.name != args.subject:
            continue
        for ch in sorted(subj.iterdir()):
            if ch.is_dir() and (ch / "goals.md").exists():
                rows.append(audit_chapter(ch))

    by_subj: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        s = by_subj[r["subject"]]
        s["n"] += 1
        s[r["worst"]] += 1

    (CONTENT / "_depth_audit.json").write_text(
        json.dumps({"thresholds": THRESH, "chapters": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    L = ["# 全学科「深度」审计（深入 / 完整 / 透彻）", "",
         "> 与 `_standards_audit.md` 的区别：那份查**有没有**（7 类内容 + 来源），"
         "这份查**够不够厚**（讲解密度、推导密度、实现密度、陷阱密度）。", "",
         "## 阈值", "", "| 指标 | B 级（合格） | A 级（扎实） | 含义 |", "|---|---|---|---|"]
    desc = {
        "concept_chars": "concept 讲解字数（不含代码）",
        "formulas": "公式块数（$$ 与 $）",
        "code_blocks": "concept 里的代码块数",
        "h3": "三级标题数（知识点可检索粒度）",
        "pitfalls": "陷阱条数",
        "example_real_pct": "示例带真实输出的比例",
        "exercise_types": "题型种类数",
    }
    L.append("> 公式数只报告不评级：工程学科（cpp/java/python）本来就少公式。")
    for k, (b, a) in THRESH.items():
        L.append(f"| {k} | {b} | {a} | {desc[k]} |")
    L += ["", "## 分学科分级", "",
          "| 学科 | 章数 | A 扎实 | B 合格 | C 偏薄 |", "|---|---|---|---|---|"]
    for s, v in by_subj.items():
        L.append(f"| {s} | {v['n']} | {v['A']} | {v['B']} | {v['C']} |")

    weak = [r for r in rows if r["worst"] == "C"]
    L += ["", f"## C 级清单（{len(weak)} 章）", "",
          "| 章节 | 字数 | 公式 | 代码块 | H3 | 陷阱 | 示例真输出 | 题型 | 短板 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(weak, key=lambda x: x["metrics"]["concept_chars"]):
        bad = [k for k, v in r["grades"].items() if v == "C"]
        m = r["metrics"]
        L.append(f"| {r['id']} | {m['concept_chars']} | {m['formulas']} | {m['code_blocks']} | "
                 f"{m['h3']} | {m['pitfalls']} | {m['example_real_pct']:.0f}% | "
                 f"{m['exercise_types']} | {'/'.join(bad)} |")
    (CONTENT / "_depth_audit.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"章节 {len(rows)}；A {sum(r['worst']=='A' for r in rows)} / "
          f"B {sum(r['worst']=='B' for r in rows)} / C {len(weak)}")
    for s, v in by_subj.items():
        print(f"  {s:12s} n={v['n']:2d} A={v['A']:2d} B={v['B']:2d} C={v['C']:2d}")
    if weak:
        print("\nC 级（按字数升序）:")
        for r in sorted(weak, key=lambda x: x["metrics"]["concept_chars"])[:20]:
            m = r["metrics"]
            bad = [k for k, v in r["grades"].items() if v == "C"]
            print(f"  {r['id']:16s} chars={m['concept_chars']:5d} f={m['formulas']:3d} "
                  f"code={m['code_blocks']:2d} h3={m['h3']:2d} pit={m['pitfalls']:2d} "
                  f"| {','.join(bad)}")
    print("\n写出 content/_depth_audit.json 与 _depth_audit.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
