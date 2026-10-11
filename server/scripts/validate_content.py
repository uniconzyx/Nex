"""CppMind 章节内容完整性校验（CI 门禁）。

阶段 7「20 章内容填充」的核心验收工具：扫描 content/ 下每个章节目录，
校验 7 类内容是否齐备且达到最低数量门槛，并检查练习题的「真题依据」合规
（LeetCode/牛客 只存元数据与链接，不存题面正文）。输出：
  - 人类可读的覆盖率报告（stdout）
  - content/_coverage.json（机器可读，供 Web/Flutter 读取完成度）

覆盖率有两个口径，勿混淆：
  - `coverage_pct`：分母 = **磁盘上已开工**的章节 → 衡量「已产出的质量」；
  - `planning.coverage_pct`：分母 = **大纲规划的**全部单元（含未开工章节与
    clang 模块）→ 衡量「整体进度」。只看前者会得出虚假的 100%。

用法：
    python server/scripts/validate_content.py [--content-dir content]
        [--fail-on-incomplete] [--fail-on-planning-gap]

退出码：存在未完成章节且带 --fail-on-incomplete 时为 1；大纲仍有未达标单元
且带 --fail-on-planning-gap 时为 1；否则 0（仅打印报告）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# 7 类内容最低门槛（PRD §9：数量下限）
_THRESHOLDS = {
    "goals": 1,        # goals.md 存在
    "concept": 3,      # concept/*.md ≥3
    "pitfalls": 3,     # pitfalls.md 编号条目 ≥3
    "exercises": 5,    # exercises.json items ≥5
    "examples": 10,    # examples/*.json ≥10
    "interview": 3,    # interview.json items ≥3
    "project": 1,      # project.json items ≥1
}

_CONTENT_TYPES = list(_THRESHOLDS.keys())

# 习题分类（基础题 / 算法题）与来源平台
_VALID_CATEGORIES = ("基础题", "算法题")
_VALID_PLATFORMS = ("self", "github", "leetcode", "nowcoder", "book")
# 来自刷题平台的题：必须带 external_url（合规：只存元数据+链接）
_LINK_PLATFORMS = ("leetcode", "nowcoder", "github")

# 八股模块门槛（学科级 _bagua.json）
_BAGUA_MIN_CATEGORIES = 3
_BAGUA_MIN_ITEMS = 12


@dataclass
class ChapterReport:
    chapter_id: str
    subject: str
    present: dict[str, int] = field(default_factory=dict)   # 实际数量
    passed: dict[str, bool] = field(default_factory=dict)  # 是否达标
    issues: list[str] = field(default_factory=list)
    exercise_compliance: dict[str, bool] = field(default_factory=dict)
    exercise_classification: dict[str, int] = field(default_factory=dict)  # 基础题/算法题/平台分布
    tri_view: dict = field(default_factory=dict)  # 三视角覆盖度（报告项，不参与 complete 判定）
    output_sanity: dict = field(default_factory=dict)  # examples 输出健康度（脏数据一票否决）

    @property
    def complete(self) -> bool:
        return all(self.passed.values())


# 三视角标记（content/_template/README.md ② 节硬性要求）。
# ① 关键词检测：避开 emoji 的 ZWJ / 变体选择符差异，用于覆盖率统计。
_TRI_VIEW_MARKERS = ("程序员视角", "博士生视角", "考研者视角")

# ② 规范标记检测：规范要求逐字为 `### <emoji> <视角>`。
# 教训（2026-10-08）：早期脚本产出的 concept 用了**不带零宽连接符**的 🧑‍💻（U+1F9D1 U+1F4BB），
# 与规范标记（U+1F9D1 U+200D U+1F4BB）字节不同；只查关键词的门禁把这批「标记漂移」长期判为合格，
# 也掩盖了 clang-u06 三个 concept **完全没有三视角**的事实。故同时报告规范性。
_ZWJ_NONE = "\U0001F9D1\U0001F4BB"           # 漂移变体
_ZWJ_OK = "\U0001F9D1\u200D\U0001F4BB"       # 规范变体
_TRI_VIEW_CANONICAL = (
    f"### {_ZWJ_OK} 程序员视角",
    "### \U0001F393 博士生视角",
    "### \U0001F4DA 考研者视角",
)

# ③ 行首锚定：规范标记必须是**独立的一行**（允许行首空白）。
# 教训（2026-10-08 二次）：只做子串匹配会漏判「重复前缀」——
# `### ### 🧑‍💻 程序员视角` 内部含 `### 🧑‍💻 程序员视角`，渲染时却会多出一个字面 `###`。
# 因此改为 `^\s*### <emoji> <视角>` 的行首锚定匹配。
_TRI_VIEW_CANONICAL_RE = tuple(
    re.compile(r"^\s*" + re.escape(c), re.M) for c in _TRI_VIEW_CANONICAL
)


def _tri_view_stats(concepts: list[Path]) -> dict:
    """统计 concept/*.md 的三视角（程序员/博士生/考研者）覆盖情况。

    **报告项**：不计入 ChapterReport.passed，因此不会让存量章节判定失败。
    同时报告「标记规范性」——关键词命中但标记非规范（emoji 变体漂移）会被单列。
    """
    per_file: dict[str, dict[str, bool]] = {}
    canonical: dict[str, bool] = {}
    drifted: list[str] = []
    for p in concepts:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        per_file[p.name] = {m: (m in text) for m in _TRI_VIEW_MARKERS}
        canon = all(rx.search(text) for rx in _TRI_VIEW_CANONICAL_RE)
        canonical[p.name] = canon
        if not canon and all(per_file[p.name].values()):
            drifted.append(p.name)

    full = sum(1 for h in per_file.values() if all(h.values()))
    return {
        "files": len(per_file),
        "full": full,
        "partial": len(per_file) - full,
        "missing": sorted(n for n, h in per_file.items() if not all(h.values())),
        "canonical": sum(1 for v in canonical.values() if v),
        "drifted": sorted(drifted),
        "not_line_anchored": sorted(
            n for n, ok in canonical.items() if not ok
        ),
        "detail": per_file,
    }


_PITFALL_ITEM_RE = re.compile(r"^(?:\d+[.、)]|[-*])(?:\s|$)")


def _count_pitfalls(md_text: str) -> int:
    """统计 pitfalls.md 的编号条目数（形如 `1.` / `1、` / `1)` / `-` 开头的有效条目）。

    注意：早期实现用 `s.startswith(p) for p in ("1.", ..., "9.")` 硬编码前缀，
    **两位数编号（`10.` 及以后）会被漏计**，导致陷阱数量被系统性低估。
    改为正则匹配任意位数的编号 + 可选分隔符。
    """
    n = 0
    for line in md_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if _PITFALL_ITEM_RE.match(s):
            n += 1
    return n


# examples 输出健康度检测（防"假实测"）。
# 教训：子代理被限流截断时，曾把 harness 自身的报错输出（UTF-16 乱码 / bash 报错 /
# Python Traceback）当作 expected_output 落盘。旧的校验只查"输出非空"，脏数据于是
# 长期隐身（clang-u07 十个示例全部如此）。以下特征用于把这类脏数据判为阻塞项。
_OUTPUT_CORRUPT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # U+FFFD 替换符 / BOM：文本被按错误编码读写的典型特征
    ("编码损坏", ("\ufffd", "\ufeff")),
    # NUL 字节：UTF-16 输出被按单字节编码读入的典型特征（表现为字符间夹空格）
    ("编码损坏(NUL)", ("\x00",)),
    # harness 自身失败，而非被演示代码的正常输出
    ("harness 执行失败", (
        "/bin/bash: ",
        "bash: line",
        "Traceback (most recent call last)",
        "command not found",
    )),
)


def _check_example_outputs(examples: list[Path]) -> list[str]:
    """检查 examples/*.json 的 expected_output 是否为脏数据。

    两类判据：

    ① **特征匹配**：命中「明确的编码损坏 / harness 执行失败」特征。
       被演示代码正常的业务性文本（如 errno 演示里的 `No such file`）不会误判。

    ② **返回码一致性**（结构性判据，优先）：若示例落盘了 `_step_rc`（逐步返回码），
       则任何非零返回码都必须由 `_expect_fail: true` 显式声明——
       否则说明「命令其实是失败的，输出却被当成正常结果」。
       反之，声明了 `_expect_fail` 却没有任何步骤失败，说明标记已失效（示例被改坏了）。

    判据②的价值在于不依赖措辞：曾经 `size big.exe` 因写成 `size big` 而失败，
    报错文本是 `No such file`（不含 `or directory`），特征匹配漏掉了它。
    """
    issues: list[str] = []
    for p in examples:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            issues.append(f"{p.name} 解析失败：{str(e)[:80]}")
            continue
        out = obj.get("expected_output")
        if not isinstance(out, str) or not out:
            continue

        # ---- ② 返回码一致性 ----
        rcs = obj.get("_step_rc")
        expect_fail = bool(obj.get("_expect_fail"))
        if isinstance(rcs, list) and rcs:
            failed = [i for i, rc in enumerate(rcs) if rc not in (0, None)]
            if failed and not expect_fail:
                issues.append(
                    f"{p.name} 第 {failed} 步返回非零码，但未声明 _expect_fail —— "
                    f"疑似「命令失败被当成正常输出」"
                )
            if expect_fail and not failed:
                issues.append(
                    f"{p.name} 声明了 _expect_fail 但无任何步骤失败，标记已失效"
                )

        # ---- ① 特征匹配 ----
        # 例外：**教学性乱码**。乱码与编码损坏本身就是部分章节的演示对象
        # （如字符编码、数据采集的乱码排查），此时必须在示例里显式声明
        # `_intentional_corrupt: "<原因>"` 才豁免——强制填原因是为了防止
        # 用它掩盖真正的脏数据。豁免只作用于特征匹配，返回码一致性仍照常检查。
        intentional = obj.get("_intentional_corrupt")
        hits = [name for name, pats in _OUTPUT_CORRUPT_PATTERNS if any(x in out for x in pats)]
        if hits and not (isinstance(intentional, str) and intentional.strip()):
            sample = out[:40].replace("\n", " ")
            issues.append(
                f"{p.name} expected_output 疑似脏数据（{'/'.join(hits)}）：{sample!r}"
            )
    return issues


def _validate_exercises(
    items: list[dict], chapter_id: str
) -> tuple[list[str], dict[str, bool], dict[str, int]]:
    """校验练习题：真题依据合规 + 基础题/算法题分类 + 来源平台。

    返回 (issues, compliance, classification)。
    """
    issues: list[str] = []
    compliance: dict[str, bool] = {}
    classification: dict[str, int] = {"基础题": 0, "算法题": 0, "未分类": 0}

    for idx, it in enumerate(items):
        eid = f"{chapter_id}#ex{idx}"
        src = it.get("source", "self")
        has_ref = bool(it.get("source_ref"))

        # ---- ① 分类（基础题 / 算法题）+ 平台 ----
        cat = it.get("category")
        plat = it.get("platform", src if src in _VALID_PLATFORMS else "self")
        if cat in _VALID_CATEGORIES:
            classification[cat] += 1
        else:
            classification["未分类"] += 1
            issues.append(f"{eid}: 缺少/非法 category（应为 {'/'.join(_VALID_CATEGORIES)}）")
        if plat not in _VALID_PLATFORMS:
            issues.append(f"{eid}: 非法 platform={plat}（应为 {'/'.join(_VALID_PLATFORMS)}）")

        # ---- ② 平台题必须带链接（合规红线）----
        if plat in _LINK_PLATFORMS or src in ("leetcode", "nowcoder"):
            if not bool(it.get("external_url") or it.get("external_id")):
                issues.append(f"{eid}: {plat}/{src} 题缺少 external_url 元数据（合规红线）")
                compliance[eid] = False
            else:
                compliance[eid] = True
                if not has_ref:
                    issues.append(f"{eid}: 建议补充 source_ref 便于溯源")
            # 平台来源却标为基础题 → 提示（不阻断，允许教材改编题）
            if cat == "基础题" and plat in ("leetcode", "nowcoder"):
                issues.append(f"{eid}: 来自 {plat} 却标为「基础题」，请确认分类是否应为「算法题」")
        else:
            compliance[eid] = True

    # ---- ③ 章节层面：建议混合基础题与算法题 ----
    if classification["基础题"] == 0 and classification["算法题"] > 0:
        issues.append(f"{chapter_id}: 全章均为算法题，建议补充 ≥2 道基础题")
    if classification["算法题"] == 0 and classification["基础题"] > 0:
        issues.append(f"{chapter_id}: 全章均为基础题，建议补充 ≥1 道算法题（来自 LeetCode/牛客/GitHub）")

    return issues, compliance, classification


def validate_chapter(chapter_dir: Path, subject: str) -> ChapterReport:
    cid = chapter_dir.name
    rep = ChapterReport(chapter_id=cid, subject=subject)

    goals = chapter_dir / "goals.md"
    rep.present["goals"] = 1 if goals.exists() else 0
    rep.passed["goals"] = rep.present["goals"] >= _THRESHOLDS["goals"]
    if not goals.exists():
        rep.issues.append("缺少 goals.md")

    concept_dir = chapter_dir / "concept"
    concepts = sorted(concept_dir.glob("*.md")) if concept_dir.exists() else []
    rep.present["concept"] = len(concepts)
    rep.passed["concept"] = len(concepts) >= _THRESHOLDS["concept"]
    if len(concepts) < _THRESHOLDS["concept"]:
        rep.issues.append(f"concept 知识点不足：{len(concepts)}/{_THRESHOLDS['concept']}")
    rep.tri_view = _tri_view_stats(concepts) if concepts else {}

    pitfalls = chapter_dir / "pitfalls.md"
    n = _count_pitfalls(pitfalls.read_text(encoding="utf-8")) if pitfalls.exists() else 0
    rep.present["pitfalls"] = n
    rep.passed["pitfalls"] = n >= _THRESHOLDS["pitfalls"]
    if n < _THRESHOLDS["pitfalls"]:
        rep.issues.append(f"pitfalls 条目不足：{n}/{_THRESHOLDS['pitfalls']}")

    ex_file = chapter_dir / "exercises.json"
    ex_items: list[dict] = []
    if ex_file.exists():
        try:
            ex_items = json.loads(ex_file.read_text(encoding="utf-8")).get("items", [])
        except json.JSONDecodeError as e:
            rep.issues.append(f"exercises.json 解析失败：{e}")
    rep.present["exercises"] = len(ex_items)
    rep.passed["exercises"] = len(ex_items) >= _THRESHOLDS["exercises"]
    if len(ex_items) < _THRESHOLDS["exercises"]:
        rep.issues.append(f"exercises 题数不足：{len(ex_items)}/{_THRESHOLDS['exercises']}")
    if ex_items:
        ex_issues, ex_comp, ex_cls = _validate_exercises(ex_items, cid)
        rep.issues.extend(ex_issues)
        rep.exercise_compliance = ex_comp
        rep.exercise_classification = ex_cls

    ex_dir = chapter_dir / "examples"
    examples = sorted(ex_dir.glob("*.json")) if ex_dir.exists() else []
    rep.present["examples"] = len(examples)
    rep.passed["examples"] = len(examples) >= _THRESHOLDS["examples"]
    if len(examples) < _THRESHOLDS["examples"]:
        rep.issues.append(f"examples 示例不足：{len(examples)}/{_THRESHOLDS['examples']}")

    # 输出健康度：脏数据（编码损坏 / harness 报错）一票否决，计入 complete 判定
    output_issues = _check_example_outputs(examples) if examples else []
    rep.output_sanity = {"checked": len(examples), "bad": len(output_issues)}
    rep.passed["examples_clean"] = not output_issues
    rep.issues.extend(output_issues)

    iv_file = chapter_dir / "interview.json"
    iv_items: list[dict] = []
    if iv_file.exists():
        try:
            iv_items = json.loads(iv_file.read_text(encoding="utf-8")).get("items", [])
        except json.JSONDecodeError as e:
            rep.issues.append(f"interview.json 解析失败：{e}")
    rep.present["interview"] = len(iv_items)
    rep.passed["interview"] = len(iv_items) >= _THRESHOLDS["interview"]
    if len(iv_items) < _THRESHOLDS["interview"]:
        rep.issues.append(f"interview 题数不足：{len(iv_items)}/{_THRESHOLDS['interview']}")

    pj_file = chapter_dir / "project.json"
    pj_items: list[dict] = []
    if pj_file.exists():
        try:
            pj_items = json.loads(pj_file.read_text(encoding="utf-8")).get("items", [])
        except json.JSONDecodeError as e:
            rep.issues.append(f"project.json 解析失败：{e}")
    rep.present["project"] = len(pj_items)
    rep.passed["project"] = len(pj_items) >= _THRESHOLDS["project"]
    if len(pj_items) < _THRESHOLDS["project"]:
        rep.issues.append(f"project 任务不足：{len(pj_items)}/{_THRESHOLDS['project']}")

    return rep


def validate_bagua(subject_dir: Path) -> dict:
    """校验学科级八股模块 _bagua.json。

    要求：存在、可解析、categories ≥3、items 总数 ≥12。
    """
    f = subject_dir / "_bagua.json"
    res = {
        "subject": subject_dir.name,
        "exists": f.exists(),
        "categories": 0,
        "items": 0,
        "ok": False,
        "issues": [],
    }
    if not f.exists():
        res["issues"].append("缺少八股模块 _bagua.json")
        return res
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        res["issues"].append(f"_bagua.json 解析失败：{e}")
        return res

    cats = data.get("categories", [])
    total = sum(len(c.get("items", [])) for c in cats)
    res["categories"] = len(cats)
    res["items"] = total
    if len(cats) < _BAGUA_MIN_CATEGORIES:
        res["issues"].append(f"八股领域不足：{len(cats)}/{_BAGUA_MIN_CATEGORIES}")
    if total < _BAGUA_MIN_ITEMS:
        res["issues"].append(f"八股条目不足：{total}/{_BAGUA_MIN_ITEMS}")
    res["ok"] = not res["issues"]
    return res


def planning_coverage(base: Path, validated: dict[str, bool]) -> dict:
    """统计 manifest 规划总量 vs 实际达标量。

    盲区修补：`total_chapters` 只统计**磁盘上已存在**的章节，因此当大纲规划的
    章节尚未开工时，覆盖率会虚高为 100%。本函数读取各科 `_manifest.json`
    （含 `clang_module.units`），以「规划」为分母计算真实完成度，并检出
    「已达标但大纲未同步为 complete」的状态漂移。
    """
    units: list[dict] = []
    for subj_dir in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")):
        mf = subj_dir / "_manifest.json"
        if not mf.exists():
            continue
        try:
            manifest = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            units.append({
                "subject": subj_dir.name, "id": "_manifest.json", "title": "大纲解析失败",
                "module": "manifest", "declared_status": "error", "on_disk_complete": False,
                "expected_dir_exists": True, "issue": str(e),
            })
            continue
        raw: list[tuple[str, dict, Path]] = [
            ("chapter", ch, subj_dir / str(ch.get("id"))) for ch in manifest.get("chapters", [])
        ]
        clang_module = manifest.get("clang_module")
        if isinstance(clang_module, dict):
            # C 语言模块为与 C++ 并列的一级入口，按大纲 note 存于 content/clang/<unit_id>/
            raw.extend(
                ("clang_unit", u, base / "clang" / str(u.get("id")))
                for u in clang_module.get("units", [])
            )
        for module, item, expected_dir in raw:
            uid = item.get("id")
            units.append({
                "subject": subj_dir.name,
                "id": uid,
                "title": item.get("title"),
                "module": module,
                "declared_status": item.get("status"),
                "on_disk_complete": bool(validated.get(uid, False)),
                "expected_dir": str(expected_dir),
                "expected_dir_exists": expected_dir.exists(),
            })

    done = sum(1 for u in units if u["on_disk_complete"])
    drifted = [
        u["id"] for u in units
        if u["on_disk_complete"] != (u["declared_status"] == "complete")
    ]
    return {
        "planned_total": len(units),
        "planned_complete": done,
        "planned_missing": len(units) - done,
        "planning_coverage_pct": round(100.0 * done / len(units), 1) if units else 0.0,
        "declared_complete": sum(1 for u in units if u["declared_status"] == "complete"),
        "status_drifted": drifted,
        "missing_units": [u["id"] for u in units if not u["on_disk_complete"]],
        "units": units,
    }


def validate_all(content_dir: str | Path) -> dict:
    """扫描所有 subject/<chapter>/ 章节 + 学科级八股模块，返回覆盖率报告 dict。"""
    base = Path(content_dir)
    reports: list[ChapterReport] = []
    bagua_reports: list[dict] = []
    planning: dict = {}
    orphan_dirs: list[dict] = []
    if base.exists():
        for subject_dir in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")):
            bagua_reports.append(validate_bagua(subject_dir))
            for chapter_dir in sorted(d for d in subject_dir.iterdir() if d.is_dir()):
                if not any((chapter_dir / f).exists() for f in ("goals.md", "exercises.json", "project.json")):
                    # 被跳过的目录：空目录 / 只有部分文件（限流截断留下的"静默半成品"）
                    files = [f for f in chapter_dir.rglob("*") if f.is_file()]
                    orphan_dirs.append({
                        "subject": subject_dir.name,
                        "id": chapter_dir.name,
                        "files": len(files),
                        "kind": "empty" if not files else "orphan",
                        "detail": sorted(str(f.relative_to(chapter_dir)) for f in files)[:6],
                    })
                    continue
                reports.append(validate_chapter(chapter_dir, subject_dir.name))
        planning = planning_coverage(base, {r.chapter_id: r.complete for r in reports})

    complete = [r for r in reports if r.complete]
    incomplete = [r for r in reports if not r.complete]

    # 三视角覆盖度汇总（报告项，不阻塞达标判定）
    tv_files = sum(r.tri_view.get("files", 0) for r in reports)
    tv_full = sum(r.tri_view.get("full", 0) for r in reports)
    tv_canon = sum(r.tri_view.get("canonical", 0) for r in reports)
    drift = [
        f"{r.chapter_id}/{name}"
        for r in reports
        for name in (r.tri_view.get("drifted") or [])
    ]
    tri_view = {
        "concept_files": tv_files,
        "tri_view_complete": tv_full,
        "canonical_complete": tv_canon,
        "marker_drift": sorted(drift),
        "coverage_pct": round(100.0 * tv_full / tv_files, 1) if tv_files else 0.0,
        "chapters_pending": sorted(r.chapter_id for r in reports
                                   if r.tri_view and r.tri_view.get("full", 0) < r.tri_view.get("files", 0)),
    }

    report = {
        "total_chapters": len(reports),
        "complete": len(complete),
        "incomplete": len(incomplete),
        "coverage_pct": round(100.0 * len(complete) / len(reports), 1) if reports else 0.0,
        "planning": planning,
        "orphan_dirs": orphan_dirs,
        "thresholds": _THRESHOLDS,
        "tri_view": tri_view,
        "bagua": bagua_reports,
        "bagua_ok": sum(1 for b in bagua_reports if b["ok"]),
        "bagua_total": len(bagua_reports),
        "chapters": [
            {
                "id": r.chapter_id,
                "subject": r.subject,
                "complete": r.complete,
                "present": r.present,
                "passed": r.passed,
                "issues": r.issues,
                "exercise_compliance_ok": all(r.exercise_compliance.values()) if r.exercise_compliance else True,
                "exercise_classification": r.exercise_classification,
                "tri_view": r.tri_view,
                "output_sanity": r.output_sanity,
            }
            for r in reports
        ],
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="CppMind 内容完整性校验")
    ap.add_argument("--content-dir", default="content", help="content 目录（相对仓库根或绝对）")
    ap.add_argument("--fail-on-incomplete", action="store_true", help="存在未完成章节时退出码为 1")
    ap.add_argument("--fail-on-planning-gap", action="store_true",
                    help="大纲规划的单元存在未达标时退出码为 1（严格模式，用于终验）")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent
    cdir = Path(args.content_dir)
    if not cdir.is_absolute():
        cdir = (repo_root / args.content_dir) if (repo_root / args.content_dir).exists() else (here.parent / args.content_dir)

    report = validate_all(cdir)
    out = cdir / "_coverage.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== CppMind 内容覆盖率报告 ===")
    print(f"章节总数: {report['total_chapters']} · 完成: {report['complete']} · 未完成: {report['incomplete']} · 覆盖率: {report['coverage_pct']}%")
    print(f"门槛: {report['thresholds']}")
    print("-" * 60)
    for ch in report["chapters"]:
        status = "OK " if ch["complete"] else "MISS"
        cls = ch.get("exercise_classification") or {}
        cls_txt = f"习题[基础{cls.get('基础题',0)}/算法{cls.get('算法题',0)}/未分类{cls.get('未分类',0)}]" if cls else ""
        tv = ch.get("tri_view") or {}
        tv_txt = f" 三视角[{tv.get('full',0)}/{tv.get('files',0)}]" if tv else ""
        os_ = ch.get("output_sanity") or {}
        os_txt = f" 脏输出[{os_.get('bad',0)}]" if os_.get("bad") else ""
        print(f"[{status}] {ch['id']} ({ch['subject']})  present={ch['present']}  {cls_txt}{tv_txt}{os_txt}")
        for iss in ch["issues"]:
            print(f"        - {iss}")
    print("-" * 60)
    tvr = report.get("tri_view") or {}
    if tvr:
        pend = tvr.get("chapters_pending") or []
        print(
            f"三视角覆盖度（报告项，不阻塞达标）: "
            f"{tvr.get('tri_view_complete', 0)}/{tvr.get('concept_files', 0)} 个 concept 文件三视角齐备 "
            f"= {tvr.get('coverage_pct', 0.0)}%"
        )
        can, drift = tvr.get("canonical_complete", 0), tvr.get("marker_drift") or []
        print(
            f"  标记规范性: {can}/{tvr.get('concept_files', 0)} 个使用规范标记"
            f"（'### <emoji> <视角>'，emoji 需含零宽连接符）"
            + ("；漂移 0" if not drift else "")
        )
        if drift:
            print(f"  标记漂移 {len(drift)} 个（关键词在但标记非规范）: {drift[:8]}{' ...' if len(drift) > 8 else ''}")
        if pend:
            print(f"  待补齐三视角的章节 {len(pend)} 个: {pend[:12]}{' ...' if len(pend) > 12 else ''}")
    print("-" * 60)
    plan = report.get("planning") or {}
    if plan:
        print(
            f"规划覆盖（分母=大纲规划单元，含未开工）: "
            f"{plan['planned_complete']}/{plan['planned_total']} = {plan['planning_coverage_pct']}%"
        )
        if plan["missing_units"]:
            print(f"  未达标 {plan['planned_missing']} 个: {plan['missing_units']}")
        if plan["status_drifted"]:
            print(f"  [状态漂移] 已达标/大纲状态不一致: {plan['status_drifted']}")
    print("-" * 60)
    orphans = report.get("orphan_dirs") or []
    if orphans:
        empty = [o for o in orphans if o["kind"] == "empty"]
        half = [o for o in orphans if o["kind"] == "orphan"]
        print(f"孤儿目录（未被计入覆盖率，需处理）: 空目录 {len(empty)} 个 · 半成品 {len(half)} 个")
        for o in orphans[:12]:
            tag = "空目录" if o["kind"] == "empty" else f"半成品({o['files']} 文件)"
            print(f"  - [{tag}] {o['subject']}/{o['id']}  {o['detail']}")
    print("-" * 60)
    print(f"八股模块: {report['bagua_ok']}/{report['bagua_total']} 学科达标")
    for b in report["bagua"]:
        st = "OK " if b["ok"] else "MISS"
        print(f"  [{st}] {b['subject']}: 领域={b['categories']} 条目={b['items']}")
        for iss in b["issues"]:
            print(f"        - {iss}")
    print("-" * 60)
    print(f"coverage.json -> {out}")

    if args.fail_on_incomplete and report["incomplete"] > 0:
        return 1
    if args.fail_on_planning_gap and (report.get("planning") or {}).get("planned_missing", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
