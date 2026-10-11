from app.services.quiz import generate_quiz


def _exercises() -> list[dict]:
    return [
        {"id": 1, "chapter_id": 1, "type": "choice", "difficulty": "easy", "title": "指针题", "content_md": "q1", "source": "self"},
        {"id": 2, "chapter_id": 1, "type": "coding", "difficulty": "mid", "title": "引用题", "content_md": "q2", "source": "leetcode", "external_url": "https://leetcode.cn/p/2"},
        {"id": 3, "chapter_id": 2, "type": "choice", "difficulty": "hard", "title": "虚函数题", "content_md": "q3", "source": "nowcoder"},
        {"id": 4, "chapter_id": 2, "type": "output", "difficulty": "easy", "title": "输出题", "content_md": "q4", "source": "self"},
        {"id": 5, "chapter_id": 3, "type": "fix_error", "difficulty": "mid", "title": "改错题", "content_md": "q5", "source": "self"},
    ]


def test_quiz_grounded_in_weak_chapters():
    qs = generate_quiz(exercises=_exercises(), weak_chapters=[1], n=5, rng_seed=1)
    assert qs
    assert all(q.chapter_id == 1 for q in qs)  # 全部来自弱章节
    assert all(q.source_ref for q in qs)  # 每题都有真题依据


def test_quiz_respects_size():
    qs = generate_quiz(exercises=_exercises(), n=3, rng_seed=2)
    assert len(qs) == 3


def test_quiz_intersects_weak_chapter_and_type_first():
    # 同时满足弱章节(2)与弱题型(coding)的题只有 id=... 无 coding@ch2，故退化为弱章节
    qs = generate_quiz(exercises=_exercises(), weak_chapters=[2], weak_types=["coding"], n=5, rng_seed=3)
    # 弱章节 2 的题：id3(choice), id4(output)；无 coding，故抽这两道
    assert {q.exercise_id for q in qs}.issubset({3, 4})


def test_quiz_fallback_when_no_weak():
    qs = generate_quiz(exercises=_exercises(), n=5, rng_seed=4)
    assert len(qs) == 5  # 无弱项 → 全库均衡抽样
    assert len({q.difficulty for q in qs}) >= 2  # 难度有覆盖


def test_quiz_deterministic_with_seed():
    a = generate_quiz(exercises=_exercises(), n=5, rng_seed=7)
    b = generate_quiz(exercises=_exercises(), n=5, rng_seed=7)
    assert [q.exercise_id for q in a] == [q.exercise_id for q in b]
