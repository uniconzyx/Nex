"""为 study_state 增加 snapshot 列（Nex 后端整份进度快照，与 auth-server 对齐）。

幂等：列已存在则跳过。方言感知：
  PostgreSQL → JSONB（与 models.types.JSONType 的 with_variant 一致）
  SQLite     → JSON（离线冒烟 / 演示库）

用法（server/ 目录，venv 已激活）：
    python -m scripts.migrate_add_study_state_snapshot
或通过 DATABASE_URL 指定目标库：
    DATABASE_URL="sqlite+aiosqlite:///./.smoke.db" \
      python -m scripts.migrate_add_study_state_snapshot
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text

from app.db import engine


async def main() -> None:
    async with engine.begin() as conn:
        dialect = engine.dialect.name
        cols = await conn.run_sync(
            lambda c: [r["name"] for r in inspect(c).get_columns("study_state")]
        )
        if "snapshot" in cols:
            print("OK: study_state.snapshot 已存在，跳过")
            return
        coltype = "JSONB" if dialect == "postgresql" else "JSON"
        await conn.execute(text(f"ALTER TABLE study_state ADD COLUMN snapshot {coltype}"))
        print(f"OK: 已为 study_state 添加 snapshot 列（{coltype}）")


if __name__ == "__main__":
    asyncio.run(main())
