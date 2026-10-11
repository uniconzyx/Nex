"""同步各学科 _manifest.json 的 status 字段。

把「磁盘上已实际达标（7 类内容齐备且达门槛）」的单元标记为 complete，
并反向报告「标 complete 但磁盘不达标」的幽灵状态。
覆盖 `chapters` 与 `clang_module.units` 两种单元。

用法：
    python server/scripts/sync_manifest_status.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
CONTENT = REPO / "content"

THRESHOLDS = {
    "concept": 3,
    "exercises": 5,
    "examples": 10,
    "interview": 3,
    "project": 1,
}


def unit_ok(d: pathlib.Path) -> bool:
    """判定目录下 7 类内容是否齐备且达门槛（与 validate_content.py 一致）。"""
    if not d.is_dir():
        return False
    if not (d / "goals.md").exists():
        return False
    concept = d / "concept"
    if not concept.is_dir():
        return False
    if len(list(concept.glob("*.md"))) < THRESHOLDS["concept"]:
        return False
    pitfalls = d / "pitfalls.md"
    if not pitfalls.exists():
        return False
    for fname, key in (("exercises.json", "exercises"), ("interview.json", "interview"),
                       ("project.json", "project")):
        p = d / fname
        if not p.exists():
            return False
        try:
            items = json.loads(p.read_text(encoding="utf-8")).get("items", [])
        except (json.JSONDecodeError, AttributeError):
            return False
        if len(items) < THRESHOLDS[key]:
            return False
    ex = d / "examples"
    if len(list(ex.glob("*.json"))) < THRESHOLDS["examples"]:
        return False
    return True


def sync(dry_run: bool = False) -> int:
    problems = 0
    for mf in sorted(CONTENT.glob("*/_manifest.json")):
        subj_dir = mf.parent
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[ERR] {mf.relative_to(REPO)} 解析失败: {e}")
            problems += 1
            continue

        changed: list[str] = []
        on_disk: list[str] = []

        def handle(item: dict, base_dir: pathlib.Path, tag: str) -> None:
            uid = item.get("id")
            if not uid:
                return
            ok = unit_ok(base_dir / uid)
            if ok:
                on_disk.append(uid)
            if ok and item.get("status") != "complete":
                changed.append(f"{uid}: {item.get('status')} -> complete")
                if not dry_run:
                    item["status"] = "complete"
            elif (not ok) and item.get("status") == "complete":
                changed.append(f"{uid}: [幽灵] 标 complete 但磁盘不达标")

        for ch in data.get("chapters", []) or []:
            handle(ch, subj_dir, "chapter")

        cm = data.get("clang_module")
        if isinstance(cm, dict):
            # C 语言模块按大纲约定存放于 content/clang/<unit_id>/
            clang_dir = CONTENT / "clang"
            for u in cm.get("units", []) or []:
                handle(u, clang_dir, "clang_unit")

        if changed and not dry_run:
            mf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        flag = "" if not changed else "  <== 有变更"
        print(f"{subj_dir.name:10s} 磁盘达标={len(on_disk):2d} | {changed}{flag}")
        problems += sum(1 for c in changed if "幽灵" in c)

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="同步 _manifest.json 的 status")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写文件")
    args = ap.parse_args()
    problems = sync(args.dry_run)
    if problems:
        print(f"\n[WARN] 发现 {problems} 处幽灵状态（标 complete 但磁盘不达标），请人工确认。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
