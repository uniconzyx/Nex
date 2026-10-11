from app.services.insight import analyze_weakness


def _wrong() -> list[dict]:
    return [
        {"chapter_id": 1, "question_type": "choice", "question_id": 1, "wrong_count": 5, "right_count": 1},
        {"chapter_id": 1, "question_type": "coding", "question_id": 2, "wrong_count": 3, "right_count": 0},
        {"chapter_id": 3, "question_type": "choice", "question_id": 3, "wrong_count": 2, "right_count": 4},
    ]


def test_weak_chapters_ranked_by_score():
    r = analyze_weakness(error_book=_wrong())
    assert r.weak_chapters
    # 第1章 wrong=8 应排第一
    assert r.weak_chapters[0].chapter_id == 1
    assert r.weak_chapters[0].wrong == 8
    # 分数随错误数递减
    scores = [c.score for c in r.weak_chapters]
    assert scores == sorted(scores, reverse=True)


def test_weak_types_aggregated():
    r = analyze_weakness(error_book=_wrong())
    by_type = {t["type"]: t["wrong"] for t in r.weak_types}
    assert by_type["choice"] == 7  # 第1章5 + 第3章2
    assert by_type["coding"] == 3


def test_recommendations_present():
    r = analyze_weakness(error_book=_wrong(), chapter_titles={1: "基础语法", 3: "多态"})
    assert r.recommendations
    assert "基础语法" in r.recommendations[0]  # 最弱章节建议


def test_no_data_graceful():
    r = analyze_weakness(error_book=[])
    assert r.total_wrong == 0
    assert r.recommendations  # 仍有兜底建议


def test_progress_adds_weak_signal():
    wrong = [{"chapter_id": 2, "question_type": "output", "question_id": 9, "wrong_count": 1, "right_count": 0}]
    progress = [{"chapter_id": 5, "mastery": 0}]  # 未学章节，弱信号
    r = analyze_weakness(error_book=wrong, progress=progress)
    ch_ids = {c.chapter_id for c in r.weak_chapters}
    assert 2 in ch_ids and 5 in ch_ids
