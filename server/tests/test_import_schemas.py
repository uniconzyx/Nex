import pytest

from app.services.sync.schemas import ExercisePackage, ExternalPackage


def _exercise_pkg(items):
    return {"meta": {"format": "cppmind-exercise-v1", "chapter": "cpp-ch01"}, "items": items}


def test_external_package_ok():
    pkg = ExternalPackage.model_validate({
        "meta": {"format": "cppmind-external-v1", "source": "leetcode"},
        "items": [{"external_id": "leetcode:1", "title": "Two Sum",
                   "url": "https://leetcode.cn/problems/two-sum/",
                   "difficulty": "easy", "mapped_chapters": ["cpp-ch01"]}],
    })
    assert len(pkg.items) == 1


def test_external_package_bad_source():
    with pytest.raises(Exception):
        ExternalPackage.model_validate({
            "meta": {"format": "cppmind-external-v1", "source": "baidu"}, "items": []})


def test_coding_requires_test_cases():
    with pytest.raises(Exception, match="测试用例"):
        ExercisePackage.model_validate(_exercise_pkg([
            {"type": "coding", "title": "无测试用例的编程题"},
        ]))


def test_coding_ok_with_cases():
    pkg = ExercisePackage.model_validate(_exercise_pkg([
        {"type": "coding", "title": "求和",
         "test_cases": [{"input": "1 2", "expected_output": "3", "is_sample": True}]},
    ]))
    assert pkg.items[0].test_cases[0].expected_output == "3"


def test_choice_answer_must_be_subset():
    with pytest.raises(Exception, match="子集"):
        ExercisePackage.model_validate(_exercise_pkg([
            {"type": "choice", "title": "坏题",
             "options": [{"key": "A", "text": "x"}, {"key": "B", "text": "y"}],
             "answer": {"correct": ["C"]}},
        ]))
