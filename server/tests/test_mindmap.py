from app.services.mindmap import derive_node_state


def test_mastered():
    assert derive_node_state(1, {1: 2}, set()) == "mastered"


def test_learning():
    assert derive_node_state(1, {1: 1}, set()) == "learning"


def test_weak_overrides():
    assert derive_node_state(1, {1: 1}, {1}) == "weak"


def test_unlearned():
    assert derive_node_state(1, {}, set()) == "unlearned"


def test_chapter_node():
    assert derive_node_state(None, {}, set(), chapter_mastery_avg=2.1) == "mastered"
    assert derive_node_state(None, {}, set(), chapter_mastery_avg=1.0) == "learning"
    assert derive_node_state(None, {}, set(), chapter_mastery_avg=0.0) == "unlearned"
