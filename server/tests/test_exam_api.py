# -*- coding: utf-8 -*-
"""考试 API 契约测试。

只钉三件最容易回归的事：
  1. 所有响应（含错误）都是统一信封 `{code, message, data, traceId}`；
  2. 题目列表不下发答案与讲解——否则「刷题」直接退化成「看答案」；
  3. 套卷条目的形状统一：字符串 id、内嵌快照、题库回查三种来源输出同一组字段。

四层顺序（framework → approach → points → solution）由 validate_exam.py 在数据层强制，
这里再从 API 出口验一次，防止序列化时把顺序打乱。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

WALKTHROUGH_ORDER = ["framework", "approach", "points", "solution"]
CARD_KEYS = {
    "order", "id", "topic", "topic_title", "type", "difficulty",
    "stem", "option_count", "has_passage", "knowledge_ids",
}
PAPER_ITEM_KEYS = {
    "id", "order", "type", "topic", "topic_title", "difficulty", "stem",
    "options", "ask", "answer", "explain", "walkthrough", "score", "in_bank",
}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def body(resp) -> dict:
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    assert set(data) == {"code", "message", "data", "traceId"}, data
    return data


def test_catalog_matches_content(client):
    data = body(client.get("/api/v1/exams"))["data"]
    assert data["content_version"] >= 1
    keys = [e["key"] for e in data["items"]]
    assert keys == ["408", "math", "english", "politics", "discrete", "algorithm"]
    for e in data["items"]:
        assert e["subjects"], f"{e['key']} 没有科目"
        assert e["counts"]["questions"] > 0


def test_four_layers_in_order_on_every_subject(client):
    catalog = body(client.get("/api/v1/exams"))["data"]
    for exam in catalog["items"]:
        for subj in exam["subjects"]:
            ex, sk = exam["key"], subj["key"]
            listing = body(client.get(
                f"/api/v1/exams/{ex}/subjects/{sk}/questions?size=1"
            ))["data"]
            assert listing["total"] > 0, f"{ex}/{sk} 没有题目"
            qid = listing["items"][0]["id"]
            detail = body(client.get(
                f"/api/v1/exams/{ex}/subjects/{sk}/questions/{qid}"
            ))["data"]

            w = detail["walkthrough"]
            assert list(w) == WALKTHROUGH_ORDER, f"{qid} 四层顺序不对：{list(w)}"
            assert w["framework"]["steps"], f"{qid} 缺少固定步骤"
            assert w["framework"]["trap"].strip(), f"{qid} 缺少陷阱"
            assert w["approach"].strip()
            assert w["solution"].strip()
            assert w["points"], f"{qid} 缺少知识点层"


def test_question_list_does_not_leak_answers(client):
    data = body(client.get("/api/v1/exams/algorithm/subjects/algo/questions?size=5"))["data"]
    assert data["items"]
    for card in data["items"]:
        assert set(card) == CARD_KEYS
        assert "answer" not in card and "walkthrough" not in card


def test_question_filters_and_pagination(client):
    p1 = body(client.get(
        "/api/v1/exams/algorithm/subjects/algo/questions?size=3&page=1"
    ))["data"]
    p2 = body(client.get(
        "/api/v1/exams/algorithm/subjects/algo/questions?size=3&page=2"
    ))["data"]
    assert p1["total"] == p2["total"]
    assert {i["id"] for i in p1["items"]}.isdisjoint({i["id"] for i in p2["items"]})

    filtered = body(client.get(
        "/api/v1/exams/algorithm/subjects/algo/questions?type=calc&size=100"
    ))["data"]
    assert filtered["items"]
    assert {i["type"] for i in filtered["items"]} == {"calc"}


def test_paper_items_are_uniform(client):
    for paper_id in ("408-mock-01", "algorithm-algo-mock-01"):
        detail = body(client.get(f"/api/v1/exams/{paper_id.split('-mock')[0]}/papers/{paper_id}"))["data"]
        assert detail["counts"]["questions"] > 0
        for sec in detail["sections"]:
            for item in sec["items"]:
                assert set(item) == PAPER_ITEM_KEYS, (paper_id, item["id"])
                assert item["type"], f"{paper_id}/{item['id']} 缺题型"
                assert isinstance(item["in_bank"], bool)

    # 408 已按「先单科后组合」整理：整卷的设计题从单科库选题，
    # 所有条目（含综合应用题快照）都应能在题库中解析到，in_bank 全为 true
    full = body(client.get("/api/v1/exams/408/papers/408-mock-01"))["data"]
    design = [i for s in full["sections"] for i in s["items"] if s["type"] == "design"]
    assert len(design) == 7 and all(i["in_bank"] is True for i in design)


def test_paper_scope_and_coverage(client):
    ds = body(client.get(
        "/api/v1/exams/408/papers?subject=ds&size=100"
    ))["data"]
    assert ds["total"] == 6  # 4 份专项 + 2 份整卷
    assert {p["scope"] for p in ds["items"]} == {"subject", "full"}
    whole = body(client.get("/api/v1/exams/408/papers?size=100"))["data"]
    assert whole["total"] == 18
    # 各考试卷数：408 18 + 数学 16 + 英语 16 + 政治 8 + 离散 8 + 算法 8 = 74
    per_exam = {
        e: body(client.get(f"/api/v1/exams/{e}/papers?size=100"))["data"]["total"]
        for e in ("408", "math", "english", "politics", "discrete", "algorithm")
    }
    assert per_exam == {"408": 18, "math": 16, "english": 16,
                        "politics": 8, "discrete": 8, "algorithm": 8}
    assert sum(per_exam.values()) == 74


def test_grade_objective_and_subjective(client):
    data = body(client.post(
        "/api/v1/exams/algorithm/subjects/algo/grade",
        json={"answers": [
            {"question_id": "q-algo-c01", "choice": 1},
            {"question_id": "q-algo-b01", "text": "  Θ(n log n)  "},
            {"question_id": "q-algo-k01", "text": "我的推导"},
        ]},
    ))["data"]

    verdicts = {i["question_id"]: i["verdict"] for i in data["items"]}
    assert verdicts["q-algo-c01"] == "CORRECT"
    assert verdicts["q-algo-b01"] == "CORRECT"  # 空白归一化后比较
    assert verdicts["q-algo-k01"] == "UNGRADED"
    assert data["summary"] == {
        "total": 3, "correct": 2, "incorrect": 0, "ungraded": 1, "accuracy": 1.0,
    }


def test_grade_rejects_bad_batches(client):
    cases = [
        ([{"question_id": "q-algo-c01", "choice": 1},
          {"question_id": "q-algo-c01", "choice": 2}], "duplicate_ids"),
        ([{"question_id": "q-algo-c01", "choice": 99}], None),
        ([{"question_id": "q-m2-c1-01", "choice": 1}], "unknown_ids"),
    ]
    for answers, marker in cases:
        resp = client.post(
            "/api/v1/exams/algorithm/subjects/algo/grade", json={"answers": answers},
        )
        data = body(resp)
        assert resp.status_code == 400 and data["code"] == 1001
        if marker:
            assert marker in data["data"]


def test_errors_are_enveloped(client):
    not_found = body(client.get("/api/v1/exams/nope"))
    assert not_found["code"] == 1004 and not_found["data"]["allowed"]

    bad_topic = body(client.get(
        "/api/v1/exams/algorithm/subjects/algo/questions?topic=not-a-topic"
    ))
    assert bad_topic["code"] == 1001 and "algo-complexity" in bad_topic["data"]["allowed"]

    bad_param = body(client.get("/api/v1/exams/math/subjects/m2/questions?size=0"))
    assert bad_param["code"] == 1001 and bad_param["data"]["errors"]

    typo = body(client.post(
        "/api/v1/exams/algorithm/subjects/algo/grade",
        json={"answers": [{"question_id": "q-algo-c01", "choise": 1}]},
    ))
    assert typo["code"] == 1001  # extra="forbid"：拼错字段立刻失败


def test_reading_is_empty_not_missing(client):
    empty = body(client.get("/api/v1/exams/politics/subjects/pol/reading"))["data"]
    assert empty["items"] == [] and empty["total"] == 0

    e1 = body(client.get("/api/v1/exams/english/subjects/e1/reading"))["data"]
    assert e1["total"] == 8
    pid = e1["items"][0]["id"]
    passage = body(client.get(
        f"/api/v1/exams/english/subjects/e1/reading/{pid}"
    ))["data"]
    assert passage["paragraphs"] and passage["vocab"] and passage["sentences"]
    assert "false_friends" in passage and "synonyms" in passage
