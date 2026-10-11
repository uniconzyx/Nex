"""题库 JSON 导入脚本（命令行版，与 /admin/content/import 同逻辑）。

用法：python -m scripts.import_bank path/to/bank.json
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal  # noqa: E402
from app.services.sync.importer import import_package  # noqa: E402


async def main(path: str) -> int:
    raw = Path(path).read_text(encoding="utf-8")
    async with SessionLocal() as db:
        try:
            result = await import_package(db, raw)
        except ValueError as exc:
            print(f"导入失败：{exc}")
            return 1
    print(f"导入成功：{result}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python -m scripts.import_bank <bank.json>")
        sys.exit(1)
    sys.exit(asyncio.run(main(sys.argv[1])))
