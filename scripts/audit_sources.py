# -*- coding: utf-8 -*-
"""全学科内容审计：严格按两条标准打分。

标准一（体系完善）——直接复用 content/_coverage.json 的 7 类门槛与三视角结果：
    goals>=1 / concept>=3 / pitfalls>=3 / exercises>=5 / examples>=10 / interview>=3 / project>=1
    且每个 concept 文件三视角齐全、标记规范（ZWJ + 行首锚定）。

标准二（来源完整）——本脚本自己算，这是 coverage 不覆盖的部分：
    1. GitHub：goals.md 里必须有 >=3 个真实 github.com/<owner>/<repo> 链接；
       且必须带 star 快照；且必须写明「对应本章哪一节」或「读什么」。
    2. B 站：必须有 >=2 个真实 bilibili.com/video/BV... 直链（搜索页不算）；
       且不能出现占位句（「建议结合本章示例与习题观看」「不写死 BV 号」）。
    3. 论文/书：>=2 条（溯源用）。
    4. 每章至少 1 条「本章专属」锚点：资源行里出现本章 concept 的真实小节号或标题关键词，
       用来证明这份路线不是学科级复制粘贴。

输出：
    content/_standards_audit.json    机器可读
    content/_standards_audit.md      人可读（按学科汇总 + 未达标清单）

用法：
    python scripts/audit_sources.py
    python scripts/audit_sources.py --verbose     # 打印每章明细
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

RE_GH = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
RE_BV = re.compile(r"bilibili\.com/video/(BV[0-9A-Za-z]{10})")
RE_BILI_SPACE = re.compile(r"(space\.bilibili\.com/\d+|search\.bilibili\.com)")
# star 快照有三种写法：`12345★` / `12345 star` / 表格单元格 `| 12345 |`
RE_STAR = re.compile(r"(\d[\d,]{2,})\s*(?:★|stars?)", re.I)
RE_STAR_CELL = re.compile(r"\|\s*(\d{2,3}(?:,\d{3})+|\d{4,7})\s*\|")
PLACEHOLDER_PATTERNS = [
    "建议结合本章示例与习题观看",
    "不写死 BV 号",
    "本学科配套视频",
    "待补充",
    "TODO",
    "（占位）",
    "资源占位",
    "占位待补",
]
# 「对应本章哪一节」的证据：出现 1.2 / 2.3 这类小节号，或「第 N 讲」「第 N 章」
RE_SECTION = re.compile(r"(?<![\d.])\d\.\d(?![\d.])")
RE_LECTURE = re.compile(r"第\s*\d+\s*[讲章集节]")


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def concept_headings(ch: Path) -> list[str]:
    """抽取本章 concept 里所有 ## / ### 标题，作为「本章专属锚点」的语料。"""
    out: list[str] = []
    for f in sorted((ch / "concept").glob("*.md")):
        for ln in read(f).split("\n"):
            if ln.startswith("## ") or ln.startswith("### "):
                t = ln.lstrip("#").strip()
                if t.startswith(("🧑", "🎓", "📚")):
                    continue
                out.append(t)
    return out


def audit_chapter(subject: str, ch: Path, cov: dict) -> dict:
    cid = ch.name
    goals = read(ch / "goals.md")
    heads = concept_headings(ch)
    head_text = " ".join(heads)

    gh = sorted({f"{a}/{b}" for a, b in RE_GH.findall(goals)})
    bv = sorted(set(RE_BV.findall(goals)))
    spaces = sorted(set(RE_BILI_SPACE.findall(goals)))
    stars = RE_STAR.findall(goals) or RE_STAR_CELL.findall(goals)
    placeholders = [p for p in PLACEHOLDER_PATTERNS if p in goals]

    # 资源段（GitHub 段 + B 站段）里有没有本章专属内容：
    # 以「小节号出现」或「本章某个 concept 标题的前 6 个字出现」为证据
    resource_blob = goals[goals.find("## 本章 GitHub"):] if "## 本章 GitHub" in goals else goals
    if not resource_blob:
        resource_blob = goals
    section_hits = sorted(set(RE_SECTION.findall(resource_blob)))
    lecture_hits = sorted(set(RE_LECTURE.findall(resource_blob)))
    head_hits = [h for h in heads if len(h) >= 6 and h[:6] in resource_blob]

    books = 0
    mf = CONTENT / subject / "_manifest.json"
    manifest = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
    units = list(manifest.get("chapters", []))
    # clang 是独立一级入口，但单元登记在 content/cpp/_manifest.json 的 clang_module.units 里
    if subject == "clang":
        cpp_mf = CONTENT / "cpp" / "_manifest.json"
        if cpp_mf.exists():
            cpp_m = json.loads(cpp_mf.read_text(encoding="utf-8"))
            units = list(((cpp_m.get("clang_module") or {}).get("units")) or [])
    unit = next((c for c in units if c.get("id") == cid), None)
    res = (unit or {}).get("resources") or {}
    if isinstance(res.get("books"), list):
        books = len(res["books"])
    if isinstance(unit, dict) and isinstance(unit.get("books"), list):
        books = max(books, len(unit["books"]))

    ok_gh = len(gh) >= 3 and bool(stars)
    ok_bili = len(bv) >= 2
    ok_anchor = bool(section_hits or lecture_hits or head_hits)
    ok_clean = not placeholders
    ok_books = books >= 2
    sources_complete = ok_gh and ok_bili and ok_anchor and ok_clean

    # 标准一：从 coverage 取
    c = cov.get(cid) or {}
    body_complete = bool(c.get("complete"))
    tri_ok = bool(c.get("tri_view", {}).get("missing") == [] and c.get("tri_view", {}).get("full", 0) == c.get("tri_view", {}).get("files", -1))

    notes_key = tuple((res.get("github_notes") or []))
    return {
        "id": cid,
        "subject": subject,
        "in_manifest": unit is not None,
        "route_key": notes_key,
        "body_complete": body_complete,
        "tri_view_ok": tri_ok,
        "sources": {
            "github_n": len(gh),
            "github": gh,
            "has_star_snapshot": bool(stars),
            "bili_bv_n": len(bv),
            "bili_bv": bv,
            "bili_space_only": spaces,
            "books_n": books,
            "placeholders": placeholders,
            "anchor_sections": section_hits[:8],
            "anchor_lectures": lecture_hits[:8],
            "anchor_headings": head_hits[:4],
            "ok_github": ok_gh,
            "ok_bili": ok_bili,
            "ok_anchor": ok_anchor,
            "ok_clean": ok_clean,
            "ok_books": ok_books,
            "complete": sources_complete,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cov_raw = json.loads((CONTENT / "_coverage.json").read_text(encoding="utf-8"))
    cov = {c["id"]: c for c in cov_raw["chapters"]}

    rows: list[dict] = []
    for subj_dir in sorted(CONTENT.iterdir()):
        if not subj_dir.is_dir() or subj_dir.name.startswith("_"):
            continue
        for ch in sorted(subj_dir.iterdir()):
            if not ch.is_dir() or not (ch / "goals.md").exists():
                continue
            rows.append(audit_chapter(subj_dir.name, ch, cov))

    by_subj: dict[str, dict] = defaultdict(lambda: {"n": 0, "body": 0, "tri": 0, "src": 0,
                                                    "gh": 0, "bili": 0, "anchor": 0, "clean": 0, "books": 0})
    for r in rows:
        s = by_subj[r["subject"]]
        s["n"] += 1
        s["body"] += r["body_complete"]
        s["tri"] += r["tri_view_ok"]
        s["src"] += r["sources"]["complete"]
        s["gh"] += r["sources"]["ok_github"]
        s["bili"] += r["sources"]["ok_bili"]
        s["anchor"] += r["sources"]["ok_anchor"]
        s["clean"] += r["sources"]["ok_clean"]
        s["books"] += r["sources"]["ok_books"]

    total = {
        "chapters": len(rows),
        "body_complete": sum(r["body_complete"] for r in rows),
        "tri_view_ok": sum(r["tri_view_ok"] for r in rows),
        "sources_complete": sum(r["sources"]["complete"] for r in rows),
    }

    # —— 路线颗粒度：同一学科内读法完全相同的章，等于「学科级复制」，不是章级路线
    from collections import Counter as _C
    dup_total = 0
    route_report: dict[str, dict] = {}
    for subj in by_subj:
        keys = _C(r["route_key"] for r in rows if r["subject"] == subj)
        n = sum(keys.values())
        uniq = len(keys)
        copied = sum(v for v in keys.values() if v > 1)
        # 章节专属 = 该章读法在本学科内唯一
        per_ch = sum(1 for r in rows if r["subject"] == subj and keys[r["route_key"]] == 1)
        route_report[subj] = {"chapters": n, "unique_routes": uniq, "chapter_specific": per_ch,
                              "copied": copied}
        dup_total += copied

    out = {
        "generated_at": "2026-10-26",
        "standard_1_body": cov_raw["thresholds"],
        "total": total,
        "by_subject": by_subj,
        "route_granularity": route_report,
        "route_copied_chapters": dup_total,
        "chapters": rows,
    }
    (CONTENT / "_standards_audit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- markdown 报告
    L: list[str] = []
    L.append("# 全学科内容审计（两条标准）")
    L.append("")
    L.append(f"共 **{total['chapters']} 章**，覆盖 {len(by_subj)} 个学科。")
    L.append("")
    L.append("## 结论一览")
    L.append("")
    L.append("| 维度 | 达标 | 未达标 | 达标率 |")
    L.append("|---|---|---|---|")
    L.append(f"| 标准一 · 7 类内容齐备 | {total['body_complete']} | "
             f"{total['chapters'] - total['body_complete']} | "
             f"{total['body_complete'] / total['chapters'] * 100:.1f}% |")
    L.append(f"| 标准一 · 三视角齐全 | {total['tri_view_ok']} | "
             f"{total['chapters'] - total['tri_view_ok']} | "
             f"{total['tri_view_ok'] / total['chapters'] * 100:.1f}% |")
    L.append(f"| 标准二 · 来源完整（GitHub+B站+锚点） | {total['sources_complete']} | "
             f"{total['chapters'] - total['sources_complete']} | "
             f"{total['sources_complete'] / total['chapters'] * 100:.1f}% |")
    L.append("")
    L.append("## 分学科明细")
    L.append("")
    L.append("| 学科 | 章数 | 体系 | 三视角 | GitHub≥3 | B站直链≥2 | 本章锚点 | 无占位句 | 论文≥2 | **来源完整** |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for subj, s in by_subj.items():
        L.append(f"| {subj} | {s['n']} | {s['body']} | {s['tri']} | {s['gh']} | {s['bili']} | "
                 f"{s['anchor']} | {s['clean']} | {s['books']} | **{s['src']}/{s['n']}** |")
    L.append("")
    L.append("")
    L.append("## 路线颗粒度（章节级 vs 学科级）")
    L.append("")
    L.append("> 「来源完整」只说明有 3 个真实仓库 + 2 条真实视频；这一节查的是更严的一件事：")
    L.append("> **这一章的路线是不是只为这一章写的**。判据是同一学科内读法文本是否重复——")
    L.append("> 若 20 章共用同一组读法，那它就是学科级路线，不管它有没有 § 锚点。")
    L.append("")
    L.append("| 学科 | 章数 | 唯一路线数 | 章节专属章 | 被复制的章 |")
    L.append("|---|---|---|---|---|")
    for subj, v in route_report.items():
        L.append(f"| {subj} | {v['chapters']} | {v['unique_routes']} | "
                 f"{v['chapter_specific']} | {v['copied']} |")
    L.append(f"| **合计** | **{len(rows)}** | — | "
             f"**{sum(v['chapter_specific'] for v in route_report.values())}** | **{dup_total}** |")

    bad = [r for r in rows if not r["sources"]["complete"]]
    L.append(f"## 标准二未达标清单（{len(bad)} 章）")
    L.append("")
    L.append("| 章节 | GitHub | 有star | B站BV | 论文 | 占位句 | 缺什么 |")
    L.append("|---|---|---|---|---|---|---|")
    for r in bad:
        s = r["sources"]
        miss = []
        if not s["ok_github"]:
            miss.append("GitHub<3或缺star")
        if not s["ok_bili"]:
            miss.append("B站直链<2")
        if not s["ok_anchor"]:
            miss.append("缺本章锚点")
        if not s["ok_clean"]:
            miss.append("占位句:" + "/".join(s["placeholders"]))
        if not s["ok_books"]:
            miss.append("论文<2")
        L.append(f"| {r['id']} | {s['github_n']} | {'✓' if s['has_star_snapshot'] else '✗'} | "
                 f"{s['bili_bv_n']} | {s['books_n']} | {len(s['placeholders'])} | {'；'.join(miss)} |")
    L.append("")
    if args.verbose:
        L.append("## 逐章明细")
        L.append("")
        for r in rows:
            s = r["sources"]
            L.append(f"- `{r['id']}` gh={s['github_n']} bv={s['bili_bv_n']} books={s['books_n']} "
                     f"anchor={len(s['anchor_sections'])}~{len(s['anchor_lectures'])} "
                     f"clean={'✓' if s['ok_clean'] else '✗'}")
    (CONTENT / "_standards_audit.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"章节 {total['chapters']} / 13 项体系达标 {total['body_complete']} / "
          f"来源完整 {total['sources_complete']}")
    for subj, s in by_subj.items():
        print(f"  {subj:12s} n={s['n']:2d} body={s['body']:2d} tri={s['tri']:2d} "
              f"src={s['src']:2d} gh={s['gh']:2d} bili={s['bili']:2d} anchor={s['anchor']:2d} "
              f"clean={s['clean']:2d} books={s['books']:2d}")
    print("\n写出 content/_standards_audit.json 与 _standards_audit.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
