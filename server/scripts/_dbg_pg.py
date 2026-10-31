"""调试用：进程内跑真实 PG 的 ASGI，直接抛原始堆栈。"""

import asyncio
import os

os.environ.pop("DATABASE_URL", None)  # 用 .env 里的真实 PG

from httpx import ASGITransport, AsyncClient


async def main():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=True), base_url="http://t") as c:
        for path in ["/api/environment", "/api/v1/courses"]:
            try:
                r = await c.get(path)
                print(path, r.status_code, r.text[:300])
            except Exception as exc:  # noqa: BLE001
                import traceback

                print(path, "EXC")
                traceback.print_exc()
                break


asyncio.run(main())
