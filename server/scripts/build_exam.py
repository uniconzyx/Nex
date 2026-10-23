#!/usr/bin/env python
"""考研题库全量构建：从生成器到校验到样张，一条命令跑完。

    python server/scripts/build_exam.py

顺序有意义：题目 → 知识点层回填 → 单科专项卷 → 整卷组合 → 副本同步 → 总结 → 总结补登 → 校验 → 样张。
套卷里内嵌的是题目快照，所以回填必须早于组卷，并在组卷后再同步一次。
408 遵循「先按单科整理齐全、再组合成套卷」：专项卷与整卷的题源都是四科单科题库。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

STEPS = [
    ("题型框架（英语 / 政治）", "gen_exam_frameworks.py"),
    ("题型框架（数学）", "gen_math_frameworks.py"),
    ("知识点表", "gen_exam_knowledge.py"),
    ("数学题库", "gen_math_questions.py"),
    ("英语一题库", "gen_english_questions.py"),
    ("英语二题库", "gen_english_e2.py"),
    ("政治题库", "gen_politics_questions.py"),
    ("离散数学题库", "gen_discrete_questions.py"),
    ("算法题库", "gen_algorithm_questions.py"),
    ("英语阅读精读指南", "gen_reading_guides.py"),
    ("知识点层回填", "enrich_exam_points.py"),
    ("408 专项模拟卷", "gen_mock_papers.py"),
    ("408 全真模拟卷", "gen_408_full_papers.py"),
    ("其他科目模拟卷", "gen_exam_papers.py"),
    ("套卷题目副本同步", "sync_paper_copies.py"),
    ("分类总结", "gen_exam_summaries.py"),
    ("总结题目补登", "sync_exam_summaries.py"),
    ("全量校验", "validate_exam.py"),
    ("生成样张", "render_exam_preview.py"),
]


def main() -> int:
    for label, script in STEPS:
        print(f"\n==> {label}", flush=True)
        r = subprocess.run([sys.executable, str(HERE / script)], cwd=ROOT)
        if r.returncode != 0:
            print(f"构建中断：{script} 退出码 {r.returncode}", file=sys.stderr)
            return r.returncode
    print("\n构建完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
