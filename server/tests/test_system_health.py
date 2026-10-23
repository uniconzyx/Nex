# -*- coding: utf-8 -*-
"""系统健康接口（/api/v1/system/health）契约测试。

钉三件事：
  1. 响应是统一信封；
  2. **探测失败绝不 500**——数据库没起也要 200，只是把 db.ok 标 false；
  3. 能力表能把「文件型可用 / 数据库型不可用」区分开，
     否则客户端没法只灰掉一部分入口。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health_envelope(client):
    r = client.get("/api/v1/system/health")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"code", "message", "data", "traceId"}
    assert body["code"] == 0


def test_health_shape(client):
    r = client.get("/api/v1/system/health")
    d = r.json()["data"]
    assert "backend" in d
    assert d["backend"]["name"] == "Nex API"
    assert "exam" in d
    assert "database" in d
    assert "features" in d


def test_health_shallow_does_not_touch_database(client):
    """浅探测默认不连数据库——客户端首屏不该被 Postgres 拖住。"""
    d = client.get("/api/v1/system/health").json()["data"]
    assert d["database"]["checked"] is False
    assert d["database"]["ok"] is None


def test_health_deep_never_500(client):
    """深探测：连不上数据库也必须 200，只是 ok=false。"""
    r = client.get("/api/v1/system/health?deep=1")
    assert r.status_code == 200
    db = r.json()["data"]["database"]
    assert db["checked"] is True
    assert isinstance(db["ok"], bool)


def test_features_cover_all_declared_features(client):
    d = client.get("/api/v1/system/health").json()["data"]
    feats = d["features"]
    for key in ("exam", "guides", "content", "exercises", "progress", "judge"):
        assert key in feats
        assert isinstance(feats[key], bool) or feats[key] is None


def test_exam_snapshot_reports_counts(client):
    """题库是文件型数据源，后端起来就该有题——快照必须能报出题数。"""
    exam = client.get("/api/v1/system/health").json()["data"]["exam"]
    assert exam["ok"] is True
    assert exam["questions"] > 0
    assert exam["exams"] >= 1
