#!/usr/bin/env python3
"""
db_status.py —— 一眼看清"现在到底用的哪个库"。

主人在双轨并存下最容易被绕晕的问题：5433 和 5432 都有同名 cppmind 库，
谁在生效？哪边有数据？这个脚本把三件事一起打出来：

    1. `.env` 里配的（后端启动时实际会连的）
    2. 环境变量临时覆盖的（如果有）
    3. 两边各自的体积与关键表行数

用法：
    python scripts/db_status.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg  # noqa: E402
from app.core.config import settings  # noqa: E402

# 双轨两侧的固定坐标（与 docker-compose.yml / 原生安装一致）
SIDES = [
    ("容器 PG16", "postgresql://cppmind:cppmind@127.0.0.1:5432/cppmind"),
    ("原生 PG17", "postgresql://cppmind:cppmind@127.0.0.1:5433/cppmind"),
]
TABLES = ["courses", "chapters", "career_projects", "guide_items", "users"]


def _plain(url: str) -> str:
    """SQLAlchemy 的 +asyncpg 后缀 asyncpg 不认。"""
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def probe(label: str, url: str) -> None:
    try:
        c = await asyncpg.connect(url, timeout=4)
    except Exception as exc:  # noqa: BLE001
        print(f"  {label}  ✗ 连不上（{type(exc).__name__}）")
        return
    size = await c.fetchval("select pg_size_pretty(pg_database_size(current_database()))")
    cells = []
    for t in TABLES:
        try:
            cells.append(f"{t}={await c.fetchval(f'select count(*) from {t}')}")
        except Exception:  # noqa: BLE001  表不存在
            cells.append(f"{t}=—")
    await c.close()
    print(f"  {label}  ✓ {size:<8}  " + " ".join(cells))


async def main() -> None:
    active = _plain(str(settings.database_url))
    override = os.environ.get("DATABASE_URL")

    print("当前生效（后端启动时会连的库）")
    print(f"  {active}")
    if override:
        print(f"  ⚠ 注意：本次 shell 有 DATABASE_URL 覆盖 → {_plain(override)}")

    print("\n双轨两侧实况")
    for label, url in SIDES:
        mark = "  ← 当前" if _plain(url) == active else ""
        await probe(label + mark, url)


if __name__ == "__main__":
    asyncio.run(main())
