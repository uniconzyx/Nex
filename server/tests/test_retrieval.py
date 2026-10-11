from app.services.retrieval import (
    Doc,
    KnowledgeIndex,
    build_corpus_from_content,
    build_corpus_from_exercises,
)
from pathlib import Path
import tempfile, textwrap


def _docs() -> list[Doc]:
    return [
        Doc(id="1", title="指针与引用", text="指针保存地址，引用是别名。指针可为空，引用必须绑定。", subject="cpp", chapter_id=1),
        Doc(id="2", title="智能指针", text="unique_ptr 独占所有权，shared_ptr 引用计数，weak_ptr 打破循环。", subject="cpp", chapter_id=2),
        Doc(id="3", title="虚函数", text="虚函数通过虚表实现多态，纯虚函数使类成为抽象类。", subject="cpp", chapter_id=3),
        Doc(id="4", title="Python 列表", text="list 是动态数组，append 摊还 O(1)。", subject="python", chapter_id=1),
    ]


def test_retrieve_relevance():
    idx = KnowledgeIndex(_docs())
    hits = idx.retrieve("指针 引用 区别", k=2)
    assert hits
    assert hits[0].doc.id == "1"  # 最直接命中
    assert any(h.doc.id == "2" for h in hits)  # 智能指针同主题相关


def test_retrieve_subject_filter():
    idx = KnowledgeIndex(_docs())
    hits = idx.retrieve("列表 动态数组", k=4, subject="python")
    assert all(h.doc.subject == "python" for h in hits)
    assert hits and hits[0].doc.id == "4"


def test_retrieve_chapter_filter():
    idx = KnowledgeIndex(_docs())
    hits = idx.retrieve("指针", k=4, chapter_id=2)
    assert all(h.doc.chapter_id == 2 for h in hits)
    assert hits[0].doc.id == "2"


def test_retrieve_empty_query():
    idx = KnowledgeIndex(_docs())
    assert idx.retrieve("") == []
    assert idx.retrieve("zzzqqq") == []  # 无命中词


def test_build_corpus_from_exercises_embeds_source_ref():
    rows = [
        {
            "id": 10, "chapter_id": 1, "type": "choice", "difficulty": "easy",
            "title": "下列正确的是", "content_md": "关于指针的说法", "explanation": "引用必须初始化",
            "source": "leetcode", "external_url": "https://leetcode.cn/problems/x", "tags": [],
        }
    ]
    docs = build_corpus_from_exercises(rows)
    assert docs[0].meta["source_ref"].startswith("LeetCode 真题")
    assert "https://leetcode.cn/problems/x" in docs[0].meta["source_ref"]


def test_build_corpus_from_content_scans_markdown():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "cpp" / "cpp-ch01"
        p.mkdir(parents=True)
        (p / "goals.md").write_text(textwrap.dedent("""
        # 第一章目标
        掌握指针与引用的区别。
        """), encoding="utf-8")
        docs = build_corpus_from_content(d)
        assert len(docs) == 1
        assert docs[0].chapter_id == 1
        assert docs[0].subject == "cpp"
        hits = KnowledgeIndex(docs).retrieve("指针 引用")
        assert hits and "指针" in hits[0].snippet
