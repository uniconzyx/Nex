#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""反向验证 verify_exercises.py 的「meta 自洽」判据（CI content-health 第 2 步）。

背景：2026-11-07 之前检查器只查 `meta.note` 里的「N 题」，`meta.count` 与
「基础题 N / 算法题 M」分解**完全没被任何门禁读取**，全库悄悄攒下 17 处
count 漂移 + 5 处分解漂移。本脚本用自造的漂移数据反向验证增强后的检查器
确实能拦下它们，再用真实 content/ 对照确认不误报。

为什么自造数据而不读备份：旧版脚本依赖 `scratch/backup-exercises-meta-*`
（scratch/ 整体 gitignore），干净 checkout 里根本不存在，别人跑不了。
这里改成临时目录里构造最小合法章节，零外部依赖、零工作区改动。

返回码：0 = 全部漂移被拦下且真实章节全绿；1 = 任一断言失败。
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server" / "scripts"))
from verify_exercises import check_chapter, ok  # noqa: E402


def item(iid, category):
    """最小合法题目：四类必填字段齐全，platform 非链接平台，无参考代码。"""
    return {
        "id": iid,
        "category": category,
        "platform": "self",
        "source": "self",
        "source_ref": "reverse-test",
        "answer": {},
    }


def chapter(td, tag, meta, n_basic=2, n_algo=2):
    """在临时目录里造一章（2 基础 + 2 算法 = 4 题），返回章节目录。"""
    items = ([item("q%02d" % i, "基础题") for i in range(1, n_basic + 1)]
             + [item("q%02d" % i, "算法题") for i in range(n_basic + 1, n_basic + n_algo + 1)])
    d = pathlib.Path(td) / "probe" / tag
    d.mkdir(parents=True, exist_ok=True)
    (d / "exercises.json").write_text(
        json.dumps({"meta": meta, "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return d


# 每个用例：说明 / meta 内容 / 期望在 meta_issues 里出现的关键字
CASES = [
    ("count 漂移（写 3 实为 4）",
     {"count": 3, "note": "4 题：基础题 2 + 算法题 2"}, "meta.count 为"),
    ("note 总题数漂移（称 3 题实为 4）",
     {"count": 4, "note": "3 题：基础题 2 + 算法题 2"}, "meta.note 称"),
    ("note 基础题分解漂移（称 3 实为 2）",
     {"count": 4, "note": "4 题：基础题 3 + 算法题 2"}, "基础题"),
    ("note 算法题分解漂移（称 1 实为 2）",
     {"count": 4, "note": "4 题：基础题 2 + 算法题 1"}, "算法题"),
    ("meta.count 非数字",
     {"count": "四", "note": "4 题：基础题 2 + 算法题 2"}, "meta.count 非数字"),
]

# 真实章节对照：覆盖上一轮修过的 5 章，确认当前工作区不误报
REAL = [
    "agent/agent-ch01", "ai/ai-ch09", "cpp/cpp-ch10",
    "fundamentals/fund-ch17", "tooling/tool-ch05",
]


def main() -> int:
    bad = 0
    with tempfile.TemporaryDirectory(prefix="verify-meta-") as td:
        # 基线：构造数据本身必须全绿，否则下面的「被拦下」可能是别的原因
        base = chapter(td, "baseline",
                       {"count": 4, "note": "4 题：基础题 2 + 算法题 2"})
        r = check_chapter(base)
        passed = ok(r) and r["total"] == 4
        print("  %s 基线构造数据全绿（4 题）" % ("PASS" if passed else "FAIL"))
        bad += not passed

        print("=== 自造漂移必须被拦下 ===")
        for i, (desc, meta, keyword) in enumerate(CASES, 1):
            r = check_chapter(chapter(td, "case%02d" % i, meta))
            caught = (not ok(r)
                      and any(keyword in m for m in r["meta_issues"])
                      and not r["field_issues"] and not r["compile_issues"])
            print("  %s %-34s meta_issues=%s" %
                  ("PASS" if caught else "FAIL", desc, r["meta_issues"]))
            bad += not caught

    print("=== 真实 content/ 对照（应全绿）===")
    for rel in REAL:
        p = ROOT / "content" / rel
        r = check_chapter(p)
        passed = ok(r)
        print("  %s %-28s meta_issues=%s" %
              ("PASS" if passed else "FAIL", rel, r["meta_issues"]))
        bad += not passed

    total = 1 + len(CASES) + len(REAL)
    passed = total - int(bad)
    print("RESULT: %s %d/%d" % ("PASS" if bad == 0 else "FAIL", passed, total))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
