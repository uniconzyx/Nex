"""方言编译对照：不连数据库，直接看 40 张表在三种方言下被编译成什么 DDL。

这是回答"换 MySQL 行不行"最硬的证据——因为失败发生在**编译期**，
连驱动都不用装。MySQL 的 JSONB 变体在这里必然编译失败。

用法：python scripts/dialect_compile_matrix.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects import mysql, postgresql, sqlite  # noqa: E402
from sqlalchemy.schema import CreateTable  # noqa: E402

from app.db import Base  # noqa: E402
import app.models  # noqa: F401,E402

DIALECTS = [
    ("PostgreSQL", postgresql.dialect()),
    ("MySQL", mysql.dialect()),
    ("SQLite", sqlite.dialect()),
]


def main() -> None:
    total = len(Base.metadata.tables)
    print(f"表总数: {total}\n")

    for label, dialect in DIALECTS:
        ok, bad = 0, []
        for table in Base.metadata.sorted_tables:
            name = table.name
            try:
                str(CreateTable(table).compile(dialect=dialect))
                ok += 1
            except Exception as exc:  # noqa: BLE001
                bad.append((name, type(exc).__name__, str(exc).split("\n")[0][:140]))
        print(f"=== {label} ===")
        print(f"  可编译 {ok}/{total} | 失败 {len(bad)}")
        reasons = Counter(r[2] for r in bad)
        for reason, cnt in reasons.most_common(5):
            print(f"    x{cnt}  {reason}")
        if bad:
            print(f"    例: {bad[0][0]} -> {bad[0][2]}")
        print()


if __name__ == "__main__":
    main()
