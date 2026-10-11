"""内容完整性校验测试（阶段 7）。

验证：
1. 真实 content/ 下已创作的章节全部通过 7 类校验；
2. 课程大纲 manifest 定义的 20 章 + 7 个 C 模块单元，与磁盘上已落地章节数量一致；
3. 练习题真题依据合规（LeetCode/牛客 题必须有 external_url 元数据，不存题面正文）；
4. 缺 goals.md 等缺失会被校验器捕获（负向）。
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from scripts import validate_content as vc

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONTENT_DIR = REPO_ROOT / "content"
MANIFEST = CONTENT_DIR / "cpp" / "_manifest.json"


def test_real_authored_chapters_all_complete():
    """已落地的章节必须全部通过 7 类校验（不写死数量，随增量扩展仍成立）。"""
    report = vc.validate_all(CONTENT_DIR)
    assert report["total_chapters"] >= 9, report          # 当前：cpp×5 + 其余 4 科各 1
    assert report["incomplete"] == 0, [c["id"] for c in report["chapters"] if not c["complete"]]
    assert report["complete"] == report["total_chapters"]
    for ch in report["chapters"]:
        assert ch["complete"], ch
        assert ch["exercise_compliance_ok"], ch["id"]


def test_manifest_defines_20_chapters_plus_clang():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(manifest["chapters"]) == 20
    assert len(manifest["clang_module"]["units"]) == 7
    # 已落地的 C++ 章节目录必须都在 manifest 中声明（避免"有目录无大纲"）
    declared = {c["id"] for c in manifest["chapters"]}
    authored = sorted(
        p.name for p in (CONTENT_DIR / "cpp").iterdir()
        if p.is_dir() and p.name.startswith("cpp-ch")
    )
    assert authored, "应至少有一个已落地章节"
    for cid in authored:
        assert cid in declared, f"{cid} 未在大纲中声明"
    # 已落地的章节在大纲中应标记为 complete
    status = {c["id"]: c["status"] for c in manifest["chapters"]}
    for cid in authored:
        assert status[cid] == "complete", f"{cid} 已落地但大纲仍标为 {status[cid]}"


def test_exercise_classification_present():
    """每道习题必须标注 category（基础题/算法题）与合法 platform。"""
    report = vc.validate_all(CONTENT_DIR)
    for ch in report["chapters"]:
        cls = ch.get("exercise_classification") or {}
        assert cls.get("未分类", 1) == 0, f"{ch['id']} 存在未分类习题"
        total = cls.get("基础题", 0) + cls.get("算法题", 0)
        assert total >= 5, f"{ch['id']} 习题数不足: {cls}"


def test_bagua_module_all_subjects_ok():
    """每个学科必须提供合规的八股模块（领域≥3、条目≥12）。"""
    report = vc.validate_all(CONTENT_DIR)
    assert report["bagua_total"] >= 5
    assert report["bagua_ok"] == report["bagua_total"], [
        (b["subject"], b["issues"]) for b in report["bagua"] if not b["ok"]
    ]


def test_planning_coverage_denominator_is_manifest():
    """规划覆盖率必须以大纲为分母，未开工章节要计入缺失，不得虚高为 100%。

    回归点：早期版本只统计「磁盘上已存在的章节」作分母，导致 20 章只写了 11 章
    时仍报 100%，掩盖了真实进度。
    """
    report = vc.validate_all(CONTENT_DIR)
    plan = report["planning"]
    # cpp 20 + java 9 + db 8 + py 8 + fs 8 = 53 章，加 clang 7 单元 = 60
    assert plan["planned_total"] >= 60, plan
    assert plan["planned_complete"] == report["complete"], (plan, report["complete"])
    assert plan["planned_missing"] > 0, "大纲仍有未开工单元，不应全绿"
    assert plan["planning_coverage_pct"] < 100.0, plan
    # 磁盘口径可以 100%（已开工的都达标），但规划口径不可以——两者必须分开
    assert report["coverage_pct"] == 100.0, report["coverage_pct"]
    # 已达标单元与大纲状态必须一致（无状态漂移）
    assert plan["status_drifted"] == [], f"以下单元状态漂移: {plan['status_drifted']}"


def test_clang_module_units_are_tracked():
    """C 语言独立模块 7 单元必须纳入规划统计（即使尚未开工）。"""
    report = vc.validate_all(CONTENT_DIR)
    units = {
        u["id"]: u for u in report["planning"]["units"] if u["module"] == "clang_unit"
    }
    assert len(units) == 7, sorted(units)
    for uid, u in units.items():
        norm = u["expected_dir"].replace("\\", "/")
        assert norm.endswith(f"clang/{uid}"), (uid, u["expected_dir"])


def test_exercise_source_ref_compliance():
    """LeetCode/牛客 映射题必须带 external_url 元数据（合规红线）。"""
    for ch_id in ("cpp-ch02", "cpp-ch03", "cpp-ch04"):
        data = json.loads((CONTENT_DIR / "cpp" / ch_id / "exercises.json").read_text(encoding="utf-8"))
        for it in data["items"]:
            if it.get("source") in ("leetcode", "nowcoder"):
                assert it.get("external_url") or it.get("external_id"), (ch_id, it.get("title"))


def test_missing_goals_is_flagged():
    """负向：缺少 goals.md 的章节必须被标记。"""
    with tempfile.TemporaryDirectory() as td:
        chap = Path(td) / "cpp" / "cpp-chX"
        chap.mkdir(parents=True)
        # 只放 exercises.json，故意缺 goals.md / concept / pitfalls 等
        (chap / "exercises.json").write_text(
            json.dumps({"items": [{"type": "coding", "title": "t", "content_md": "x",
                                   "answer": {"reference_code": "int main(){}"}, "tags": []}]}),
            encoding="utf-8",
        )
        rep = vc.validate_chapter(chap, "cpp")
        assert not rep.complete
        assert any("goals.md" in iss for iss in rep.issues)
        assert rep.passed["goals"] is False


def test_pitfalls_count_threshold():
    """pitfalls.md 条目不足 3 时不应通过。"""
    with tempfile.TemporaryDirectory() as td:
        chap = Path(td) / "cpp" / "cpp-chY"
        chap.mkdir(parents=True)
        (chap / "goals.md").write_text("# goals", encoding="utf-8")
        (chap / "concept").mkdir()
        (chap / "concept" / "01.md").write_text("# c", encoding="utf-8")
        (chap / "pitfalls.md").write_text("1. only one\n", encoding="utf-8")  # 仅 1 条
        (chap / "exercises.json").write_text(
            json.dumps({"items": [{"type": "coding", "title": "t", "content_md": "x",
                                   "answer": {"reference_code": "int main(){}"}, "tags": []}]}),
            encoding="utf-8",
        )
        ex = chap / "examples"
        ex.mkdir()
        for i in range(10):
            (ex / f"ex{i}.json").write_text(
                json.dumps({"title": "t", "code_lang": "cpp", "code_std": "cpp17",
                            "stdin": "", "expected_output": "", "code": "int main(){}"}),
                encoding="utf-8",
            )
        (chap / "interview.json").write_text(
            json.dumps({"items": [{"question": "q", "answer_md": "a", "follow_ups": [],
                                   "difficulty": "easy", "company_tags": []}]}),
            encoding="utf-8",
        )
        (chap / "project.json").write_text(
            json.dumps({"items": [{"title": "p", "requirement_md": "r", "tasks": []}]}),
            encoding="utf-8",
        )
        rep = vc.validate_chapter(chap, "cpp")
        assert rep.passed["pitfalls"] is False
        assert rep.present["pitfalls"] == 1
