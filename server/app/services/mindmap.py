from collections.abc import Mapping


def derive_node_state(
    kp_id: int | None,
    mastery_by_kp: Mapping[int, int],
    weak_kps: set[int],
    chapter_mastery_avg: float | None = None,
) -> str:
    """导图节点四态推导（不落库）。

    mastered=已掌握(mastery>=2)  learning=学习中(mastery==1)
    weak=薄弱(近期该知识点练习正确率<50%)  unlearned=未学习
    """
    if kp_id is not None:
        if kp_id in weak_kps:
            return "weak"
        m = mastery_by_kp.get(kp_id, 0)
        if m >= 2:
            return "mastered"
        if m == 1:
            return "learning"
        return "unlearned"
    # 章节级节点：按子知识点平均掌握度
    if chapter_mastery_avg is None:
        return "unlearned"
    if chapter_mastery_avg >= 2:
        return "mastered"
    if chapter_mastery_avg >= 0.5:
        return "learning"
    return "unlearned"
