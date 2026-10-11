# -*- coding: utf-8 -*-
"""学习线审计：验证 13 条学习线是否「独立 + 完整 + 服务考研/学习/就业」。

审计口径
--------
1. **独立**：本线有自己的 manifest / 资源 / 八股题库；首章无前置；**无跨线硬依赖**
   （跨学科先修只允许出现在 `soft_prerequisites`，属于「建议」而非「必需」）。
2. **完整**：已完成章节 7 类文件齐全（goals / concept≥3 / pitfalls≥3 / exercises≥5 /
   examples≥10 / interview≥3 / project≥1），concept 三视角齐备，章节链从基础到实战。
3. **三元服务**：
   - 考研：三视角 100%（内含考研者视角考点）+ 八股题库 ≥10 题；
   - 学习：goals + concept + pitfalls + examples 齐全率 100%；
   - 就业：八股 ≥10 + 每章 interview ≥3 + project ≥1 + GitHub 资源非空。

用法
----
    python server/scripts/audit_learning_lines.py            # 打印矩阵
    python server/scripts/audit_learning_lines.py --json     # 额外落盘 content/_learning_lines.json
    python server/scripts/audit_learning_lines.py --only fundamentals
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"

# 学科 → 该线对应的考研科目（用于「考研服务」判定与展示）
EXAM_SUBJECT = {
    "fundamentals": "408 统考（数据结构 / 计组 / 操作系统 / 计算机网络）",
    "database": "408 数据库原理 + 复试数据库",
    "cpp": "程序设计（自命题 / 复试机试）",
    "clang": "C 语言程序设计（自命题 / 复试机试）",
    "python": "程序设计（自命题 / 复试机试）",
    "java": "程序设计（自命题 / 复试机试）",
    "tooling": "Linux 与工程基础（复试 / 上机）",
    "fullstack": "Web 开发（复试方向课 / 自命题）",
    "spring": "Java 后端方向（复试方向课 / 自命题）",
    "middleware": "分布式与中间件（复试方向课 / 自命题）",
    "bigdata": "大数据方向（复试方向课 / 自命题）",
    "ai": "人工智能方向（复试方向课 / 自命题）",
    "data": "数据分析方向（复试方向课 / 自命题）",
}

# 学科展示名
LINE_NAME = {
    "cpp": "C++", "clang": "C 语言", "java": "Java", "python": "Python",
    "database": "数据库", "fullstack": "全栈开发", "spring": "Spring 生态",
    "middleware": "中间件", "bigdata": "大数据", "fundamentals": "考研 408 基础",
    "tooling": "工具链", "data": "数据分析", "ai": "人工智能 / Agent",
}

TRIPLE = ("### 🧑‍💻 程序员视角", "### 🎓 博士生视角", "### 📚 考研者视角")

PITFALL_RE = re.compile(r"^\s*(?:\d+[.)、]|[-*])\s+\S")


def _count_pitfalls(p: pathlib.Path) -> int:
    if not p.exists():
        return 0
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        if PITFALL_RE.match(line):
            n += 1
    return n


def _load(p: pathlib.Path):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def scan_chapter(cdir: pathlib.Path) -> dict:
    """扫描单个章节目录，返回 7 类文件的计数。"""
    goals = (cdir / "goals.md").exists()
    concepts = sorted((cdir / "concept").glob("*.md")) if (cdir / "concept").is_dir() else []
    tri = 0
    for c in concepts:
        t = c.read_text(encoding="utf-8")
        if all(k in t for k in TRIPLE):
            tri += 1
    pitfalls = _count_pitfalls(cdir / "pitfalls.md")
    ex = _load(cdir / "exercises.json") or {}
    items = ex.get("items", []) if isinstance(ex, dict) else []
    basic = sum(1 for i in items if i.get("category") == "基础题")
    algo = sum(1 for i in items if i.get("category") == "算法题")
    examples = sorted((cdir / "examples").glob("*.json")) if (cdir / "examples").is_dir() else []
    itv = _load(cdir / "interview.json") or {}
    itv_items = itv.get("items", []) if isinstance(itv, dict) else []
    prj = _load(cdir / "project.json") or {}
    prj_items = prj.get("items", []) if isinstance(prj, dict) else []
    return {
        "exists": cdir.is_dir(),
        "goals": goals,
        "concepts": len(concepts),
        "tri_view": tri,
        "pitfalls": pitfalls,
        "exercises": len(items),
        "basic": basic,
        "algo": algo,
        "examples": len(examples),
        "interview": len(itv_items),
        "project": len(prj_items),
    }


def chapter_ok(m: dict) -> tuple[bool, list[str]]:
    """单个章节是否达到 7 类门槛。"""
    bad = []
    if not m["goals"]:
        bad.append("goals")
    if m["concepts"] < 3:
        bad.append(f"concept<3({m['concepts']})")
    if m["tri_view"] < m["concepts"]:
        bad.append(f"三视角{m['tri_view']}/{m['concepts']}")
    if m["pitfalls"] < 3:
        bad.append(f"pitfalls<3({m['pitfalls']})")
    if m["exercises"] < 5:
        bad.append(f"exercises<5({m['exercises']})")
    if m["basic"] < 2:
        bad.append(f"基础题<2({m['basic']})")
    if m["algo"] < 1:
        bad.append(f"算法题<1({m['algo']})")
    if m["examples"] < 10:
        bad.append(f"examples<10({m['examples']})")
    if m["interview"] < 3:
        bad.append(f"interview<3({m['interview']})")
    if m["project"] < 1:
        bad.append(f"project<1({m['project']})")
    return (not bad), bad


def load_line(subject: str):
    """返回 (chapters 列表, manifest)。clang 的单元定义在 cpp manifest 的 clang_module 中。"""
    if subject == "clang":
        mp = CONTENT / "cpp" / "_manifest.json"
        man = _load(mp) or {}
        units = man.get("clang_module", {}).get("units", [])
        chapters = [dict(u, _dir=CONTENT / "clang" / u["id"]) for u in units]
        return chapters, man
    mp = CONTENT / subject / "_manifest.json"
    man = _load(mp) or {}
    chapters = [dict(c, _dir=CONTENT / subject / c["id"]) for c in man.get("chapters", [])]
    return chapters, man


def audit(only=None):
    subjects = sorted(p.parent.name for p in CONTENT.glob("*/_manifest.json"))
    # clang 线独立成线，但单元定义在 content/cpp/_manifest.json 的 clang_module 中
    if "clang" not in subjects and (CONTENT / "clang").is_dir():
        subjects = sorted(subjects + ["clang"])
    # 全部章节 id → 学科，用于识别跨线硬前置
    all_ids = {}
    for s in subjects:
        chs, _ = load_line(s)
        for c in chs:
            all_ids[c["id"]] = s

    lines = {}
    for s in subjects:
        if only and s != only:
            continue
        chapters, man = load_line(s)
        done, planned = 0, len(chapters)
        agg = dict(concepts=0, tri_view=0, pitfalls=0, exercises=0, basic=0, algo=0,
                   examples=0, interview=0, project=0)
        incomplete = []
        hard_cross = []
        disk_done = 0
        for c in chapters:
            m = scan_chapter(c["_dir"])
            ok, bad = chapter_ok(m)
            if ok:
                disk_done += 1
                done += 1
            else:
                if m["exists"] and (m["concepts"] or m["examples"]):
                    incomplete.append((c["id"], bad))
            for k in agg:
                agg[k] += m[k]
            for pre in c.get("soft_prerequisites", []) or []:
                pass
            for pre in c.get("prerequisites", []) or []:
                if pre in all_ids and all_ids[pre] != s:
                    hard_cross.append((c["id"], pre, all_ids[pre]))
        bagua = _load(CONTENT / s / "_bagua.json") if s != "clang" else _load(CONTENT / "clang" / "_bagua.json")
        if bagua is None and s == "clang":
            bagua = _load(CONTENT / "cpp" / "_bagua.json")
        bagua_items = sum(len(c.get("items", [])) for c in (bagua or {}).get("categories", []))

        # GitHub 资源
        repos = man.get("github_resources") or []
        if not repos:
            repos = sorted({r for c in chapters for r in (c.get("resources", {}) or {}).get("github", [])})

        first_no_prereq = True
        if chapters:
            ordered = sorted(chapters, key=lambda c: c.get("order", 0))
            first_no_prereq = not (ordered[0].get("prerequisites") or [])

        tri_ok = agg["concepts"] > 0 and agg["tri_view"] == agg["concepts"]
        # 三元服务判定
        exam = tri_ok and bagua_items >= 10
        study = not incomplete and disk_done > 0
        job = bagua_items >= 10 and not any(
            m < 3 or p < 1
            for m, p in [(scan_chapter(c["_dir"])["interview"], scan_chapter(c["_dir"])["project"])
                         for c in chapters if scan_chapter(c["_dir"])["exists"]]
        ) and len(repos) > 0 if chapters else False
        independent = first_no_prereq and not hard_cross and bool(repos)

        lines[s] = {
            "name": LINE_NAME.get(s, s),
            "exam_subject": EXAM_SUBJECT.get(s, ""),
            "planned": planned,
            "complete": done,
            "gap": planned - done,
            "incomplete_chapters": incomplete,
            "hard_cross_prereq": hard_cross,
            "first_chapter_no_prereq": first_no_prereq,
            "bagua_items": bagua_items,
            "github_repos": repos,
            "agg": agg,
            "service": {"考研": exam, "学习": study, "就业": job},
            "independent": independent,
        }
    return lines, all_ids


def print_matrix(lines):
    print("=" * 132)
    print("学习线独立完整性审计（13 条线）")
    print("=" * 132)
    hdr = (f"{'学科':12s}{'线名':14s}{'完成/规划':>10s}{'缺口':>5s}{'concept':>8s}{'三视角':>9s}"
           f"{'题集':>6s}{'基础':>5s}{'算法':>5s}{'示例':>6s}{'面试':>6s}{'项目':>5s}{'八股':>6s}"
           f"{'仓库':>5s}  {'独立':4s}{'考研':4s}{'学习':4s}{'就业':4s}")
    print(hdr)
    print("-" * 132)
    for s, v in sorted(lines.items(), key=lambda kv: -(kv[1]["planned"] - kv[1]["complete"])):
        a = v["agg"]
        tri = f"{a['tri_view']}/{a['concepts']}"
        print(f"{s:12s}{v['name']:14s}{v['complete']:>5d}/{v['planned']:<4d}{v['gap']:>5d}"
              f"{a['concepts']:>8d}{tri:>9s}{a['exercises']:>6d}{a['basic']:>5d}{a['algo']:>5d}"
              f"{a['examples']:>6d}{a['interview']:>6d}{a['project']:>5d}{v['bagua_items']:>6d}"
              f"{len(v['github_repos']):>5d}  "
              f"{'✅' if v['independent'] else '⚠️':<4s}"
              f"{'✅' if v['service']['考研'] else '—':<4s}"
              f"{'✅' if v['service']['学习'] else '—':<4s}"
              f"{'✅' if v['service']['就业'] else '—':<4s}")

    print()
    print("=" * 132)
    print("风险清单（按类型）")
    print("=" * 132)
    problems = 0
    for s, v in sorted(lines.items()):
        msgs = []
        if v["hard_cross_prereq"]:
            msgs.append("跨线硬前置: " + ", ".join(f"{a}→{b}({c})" for a, b, c in v["hard_cross_prereq"]))
        if not v["first_chapter_no_prereq"]:
            msgs.append("首章带前置，无法从零起步")
        if not v["github_repos"]:
            msgs.append("缺 GitHub 资源")
        if v["bagua_items"] < 10:
            msgs.append(f"八股题库偏薄({v['bagua_items']} 题)")
        if v["incomplete_chapters"]:
            head = "; ".join(f"{cid}: {'/'.join(bad)}" for cid, bad in v["incomplete_chapters"][:4])
            more = "" if len(v["incomplete_chapters"]) <= 4 else f" …(+{len(v['incomplete_chapters']) - 4})"
            msgs.append(f"半成品章节 {len(v['incomplete_chapters'])} 个 → {head}{more}")
        if msgs:
            problems += 1
            print(f"\n【{s} · {v['name']}】")
            for m in msgs:
                print("   -", m)
    if problems == 0:
        print("\n无风险项。")
    print()
    print("=" * 132)
    print("三元服务口径")
    print("=" * 132)
    for s, v in sorted(lines.items()):
        print(f"{v['name']:16s} 考研方向：{v['exam_subject']}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="落盘 content/_learning_lines.json")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    lines, _ = audit(args.only)
    problems = print_matrix(lines)

    total_planned = sum(v["planned"] for v in lines.values())
    total_done = sum(v["complete"] for v in lines.values())
    print()
    print(f"合计：{total_done}/{total_planned} 单元达标（{total_done / max(total_planned, 1) * 100:.1f}%）；"
          f"有风险项的学习线 {problems}/{len(lines)}")

    if args.json:
        out = {
            "total_planned": total_planned,
            "total_complete": total_done,
            "lines": {k: {kk: vv for kk, vv in v.items() if kk != "incomplete_chapters"} for k, v in lines.items()},
            "incomplete": {k: v["incomplete_chapters"] for k, v in lines.items() if v["incomplete_chapters"]},
        }
        p = CONTENT / "_learning_lines.json"
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"已写 {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
