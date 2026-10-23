#!/usr/bin/env python
"""推荐刷题序列算法（阶段16 第④步）。

目标：给每个分类总结的 group 生成一份「由易到难、相邻题不重复考点」的刷题顺序。
- 由易到难：按题目的 diff 升序；diff 为 None（未标难度）排到最后。
- 相邻不重复考点：同难度桶内，按 knowledge 做 round-robin 打散，尽量让相邻两题不撞同一个细分考点。

输入：一组题目 dict（至少要带 id；diff/knowledge 尽量带，缺失会被兜底处理）。
输出：与输入等长的 id 排列，是 questionIds 的严格排列。
"""

from __future__ import annotations

from collections import defaultdict

# diff 为 None 时用的排序垫底值（保证它排在所有有难度题目之后）
_NONE_RANK = 10 ** 9


def _diff_rank(d) -> int:
    return _NONE_RANK if d is None else d


def _round_robin(bucket: list[dict]) -> list[dict]:
    """按 knowledge 分桶后交错输出，相邻尽量不同考点。

    桶按长度降序排列，循环轮流从每个非空桶取一个，直到取完。
    当某一 knowledge 占绝对多数时无法完全避免相邻重复，校验脚本会对此告警。
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for q in bucket:
        groups[q.get("knowledge") or "__none__"].append(q)
    ordered = sorted(groups.values(), key=lambda g: -len(g))
    result: list[dict] = []
    while any(g for g in ordered):
        for g in ordered:
            if g:
                result.append(g.pop(0))
    return result


def order_questions(questions: list[dict]) -> list[str]:
    """对一组题目计算推荐刷题序列。

    questions: 每个元素 dict，需含 id；可选 diff（int/None）、knowledge（str）。
    返回 id 的排列。
    """
    qs = list(questions)
    qs_sorted = sorted(qs, key=lambda q: _diff_rank(q.get("diff")))
    buckets: dict[int, list[dict]] = defaultdict(list)
    for q in qs_sorted:
        buckets[_diff_rank(q.get("diff"))].append(q)
    out: list[dict] = []
    for key in sorted(buckets):
        out.extend(_round_robin(buckets[key]))
    return [q.get("id") for q in out]


if __name__ == "__main__":
    # 自测：混合难度 + 同考点聚集，验证由易到难与打散效果
    sample = [
        {"id": "a", "diff": 3, "knowledge": "k1"},
        {"id": "b", "diff": 2, "knowledge": "k1"},
        {"id": "c", "diff": 2, "knowledge": "k2"},
        {"id": "d", "diff": None, "knowledge": "k2"},
        {"id": "e", "diff": 1, "knowledge": "k1"},
    ]
    print(order_questions(sample))
