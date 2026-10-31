import asyncio
import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./.smoke.db")

from httpx import ASGITransport, AsyncClient


async def main():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/auth/register",
            json={"email": "smoke2@nex.local", "password": "Passw0rd!", "nickname": "冒烟"},
        )
        print(r.status_code)
        print(json.dumps(r.json(), ensure_ascii=False, indent=1)[:2000])


asyncio.run(main())
