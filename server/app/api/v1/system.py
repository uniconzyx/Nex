"""系统状态接口（打通前后端与客户端的「探针」）。

为什么要单独一个接口：
  Nex 的功能分成两类数据源——
    * **文件型**（考研题库 / 指南 / 职业库）：只读 content/ 下的构建产物，不落库，
      后端起来就能用；
    * **数据库型**（课程 / 练习 / 进度 / 账号）：依赖 Postgres + Redis，
      没起数据库时整组接口会 500。
  客户端（桌面 .exe / Android .apk / 浏览器）拿到这份状态后就能：
    1. 明确告诉用户「哪部分能用、哪部分不能」，而不是笼统的「加载失败」；
    2. 只在需要时提示去起数据库，而不是每次请求都弹错。

设计约束：
  * **绝不因为探测失败而 500**。数据库挂了，本接口仍返回 200，
    只是把 db.ok 标成 false——否则客户端连「后端是否活着」都判断不了。
  * 默认**浅探测**（不连数据库），避免每个客户端首屏都去戳 Postgres。
    需要深探测时带 ?deep=1。
  * 不依赖请求头里的登录态，公开可读。
"""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Query

from app.core.responses import ok

router = APIRouter(tags=["system"])

# 后端对外宣称的能力清单。前端按这个表决定「哪些入口要点亮」。
FEATURES = ("exam", "guides", "projects", "career", "content", "exercises", "progress", "judge")


def _exam_snapshot() -> dict:
    """考研题库快照。题库缺失时只标 false，不抛异常——
    整个 content/ 没构建成功是部署问题，不是接口问题。"""
    try:
        from app.services import exam_bank

        cat = exam_bank.catalog()
        totals = {"questions": 0, "topics": 0, "summaries": 0, "papers": 0}
        for item in cat["items"]:
            for k in totals:
                totals[k] += item["counts"].get(k, 0)
        return {
            "ok": True,
            "content_version": cat.get("content_version", 1),
            "exams": len(cat["items"]),
            **totals,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}


async def _db_snapshot() -> dict:
    """深探测数据库。1.5s 超时——数据库没起时不该让客户端干等。"""
    try:
        from sqlalchemy import text

        from app.db import engine

        async with asyncio.timeout(1.5):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": type(exc).__name__}


@router.get("/system/health")
async def system_health(deep: bool = Query(False, description="是否顺带探测数据库连接")):
    """系统健康状态。

    返回体示例（浅探测）：
      {
        "backend": {"name": "Nex API", "version": "0.1.0", "uptime_ms": 12345},
        "exam": {"ok": true, "questions": 435, "topics": 260, ...},
        "database": {"ok": null, "checked": false},
        "features": {"exam": true, "content": false, ...}
      }
    """
    t0 = time.perf_counter()
    exam = _exam_snapshot()

    db: dict = {"ok": None, "checked": False}
    if deep:
        db = await _db_snapshot()
        db["checked"] = True

    # 能力判定：
    #   文件型能力跟着题库快照走；数据库型能力只在深探测确认后才点亮。
    exam_ok = exam.get("ok", False)
    db_ok = db.get("ok") is True
    features = {
        "exam": exam_ok,
        "guides": exam_ok,
        "projects": exam_ok,
        "career": exam_ok,
        "content": db_ok,
        "exercises": db_ok,
        "progress": db_ok,
        "judge": None,  # 判题由客户端本机沙箱负责，后端不判定
    }

    return ok({
        "backend": {
            "name": "Nex API",
            "version": "0.1.0",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        },
        "exam": exam,
        "database": db,
        "features": features,
    })
