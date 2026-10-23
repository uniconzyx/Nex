"""真实链路验收：对已启动的 uvicorn（真实 PostgreSQL + Redis）跑黑盒 HTTP 测试。

用法（工作目录 server/，先起服务）：
    python -m scripts.e2e_http

与 sqlite_smoke.py 的分工：
    sqlite_smoke —— 进程内 ASGI + SQLite，验证"无依赖机器上能起来"；
    e2e_http     —— 走真实 TCP + 真实 PG + 真实 Redis，验证"生产链路真的通"。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

# 允许用环境变量指定被测后端，便于"对着另一个实例验收"（如 Docker 容器库的临时实例）。
# 默认仍是 8000，原有的 `python -m scripts.e2e_http` 用法完全不变。
import os as _os

BASE = _os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
STAMP = str(int(time.time()))
EMAIL = f"e2e{STAMP}@nex.dev"
PASSWORD = "Passw0rd!2026"

PASS: list[str] = []
FAIL: list[str] = []
ROWS: list[dict] = []


def rec(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name)
    ROWS.append({"name": name, "ok": ok, "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


def envelope(r: httpx.Response) -> dict:
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {}


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=15, trust_env=False)

    # ---------- 0. 基础设施 ----------
    r = c.get("/health")
    rec("GET /health", r.status_code == 200 and envelope(r).get("data", {}).get("status") == "up", str(r.status_code))

    env = envelope(c.get("/api/v1/courses"))
    rec("内容库可读（PG 真实查询）", env.get("code") == 0, f"courses={len(env.get('data') or [])}")

    # ---------- 1. 注册 / 登录 ----------
    r = c.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD, "nickname": "验收员"})
    body = envelope(r)
    rec("注册", r.status_code == 200 and body.get("code") == 0, f"{r.status_code} {body.get('message')}")

    r = c.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    rec("重复注册被拒", envelope(r).get("code") not in (0, None), str(envelope(r).get("message"))[:30])

    r = c.post("/api/v1/auth/register", json={"email": "bad@x", "password": "1"})
    rec("非法邮箱/弱密码被拒 422", r.status_code == 422, str(r.status_code))

    r = c.post("/api/v1/auth/login", json={"account": EMAIL, "password": "wrong-pass"})
    rec("错误密码 401", r.status_code == 401, str(r.status_code))

    r = c.post("/api/v1/auth/login", json={"account": EMAIL, "password": PASSWORD})
    data = envelope(r).get("data") or {}
    token, refresh = data.get("access_token"), data.get("refresh_token")
    rec("登录签发 access+refresh", bool(token and refresh), f"expires_in={data.get('expires_in')}")

    h = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/v1/users/me", headers=h)
    me = envelope(r).get("data") or {}
    rec("GET /users/me", r.status_code == 200 and me.get("email") == EMAIL,
        f"nickname={(me.get('profile') or {}).get('nickname')}")

    r = c.patch("/api/v1/users/me", headers=h, json={"nickname": "凯喵验收", "daily_minutes": 90})
    r2 = c.get("/api/v1/users/me", headers=h)
    prof = (envelope(r2).get("data") or {}).get("profile") or {}
    rec("PATCH /users/me 生效", prof.get("nickname") == "凯喵验收" and prof.get("daily_minutes") == 90,
        f"{prof.get('nickname')}/{prof.get('daily_minutes')}")

    r = c.get("/api/v1/users/me")
    rec("未带 token 401", r.status_code == 401, str(r.status_code))

    r = c.get("/api/v1/users/me", headers={"Authorization": "Bearer garbage"})
    rec("伪造 token 401", r.status_code == 401, str(r.status_code))

    r = c.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    d2 = envelope(r).get("data") or {}
    rec("refresh 换新 token", bool(d2.get("access_token")), str(r.status_code))

    r = c.post("/api/v1/auth/refresh", json={"refresh_token": token})
    rec("access 当 refresh 用被拒", r.status_code == 401, str(r.status_code))

    # ---------- 2. 内容 ----------
    for path, key in [
        ("/api/v1/courses", "list"),
        ("/api/v1/guides", "list"),
        ("/api/v1/career-tracks", "list"),
        ("/api/v1/exercises?page=1&page_size=5", "list"),
        ("/api/v1/resources?page=1&page_size=5", "list"),
    ]:
        r = c.get(path)
        j = envelope(r)
        rec(f"公开接口 {path.split('?')[0]}", r.status_code == 200 and j.get("code") == 0,
            f"{r.status_code} items={len(j.get('data') or []) if isinstance(j.get('data'), list) else 'obj'}")

    # ---------- 3. 登录态业务 ----------
    authed = [
        ("/api/v1/progress/dashboard", "进度看板"),
        ("/api/v1/achievements/my", "成就"),
        ("/api/v1/wrong-questions", "错题本"),
        ("/api/v1/plans/current", "当前计划"),
        ("/api/v1/ai/quota", "AI 配额"),
    ]
    for path, label in authed:
        r = c.get(path, headers=h)
        rec(f"{label} {path}", r.status_code == 200 and envelope(r).get("code") == 0, str(r.status_code))

    # 收藏 / 笔记 写入后读回
    r = c.post("/api/v1/favorites", headers=h, json={"target_type": "exercise", "target_id": 1})
    rec("收藏写入", r.status_code == 200 and envelope(r).get("code") == 0, str(r.status_code))
    r = c.post("/api/v1/notes", headers=h, json={"target_type": "exercise", "target_id": 1, "content_md": "验收笔记"})
    rec("笔记写入", r.status_code == 200, str(r.status_code))
    r = c.post("/api/v1/notes", headers=h, json={"target_type": "chapter", "target_id": 1, "content_md": "x"})
    rec("非法笔记类型被 422 拦住（不再 500）", r.status_code == 422, str(r.status_code))
    r = c.get("/api/v1/notes?target_type=exercise&target_id=1", headers=h)
    notes = envelope(r).get("data") or []
    rec("笔记读回", isinstance(notes, list) and len(notes) >= 1, f"count={len(notes) if isinstance(notes, list) else '?'}")

    # 计划生成（依赖章节种子）
    r = c.post("/api/v1/plans/generate", headers=h, json={"direction": "exam", "weeks": 4, "weekly_hours": 10})
    rec("生成学习计划", r.status_code in (200, 404) and envelope(r).get("code") in (0, 3001),
        f"{r.status_code} {str(envelope(r).get('message'))[:28]}")

    # ---------- 4. 本机进度快照同步 ----------
    snap = {
        "done_chapters": ["cpp-ch01", "cpp-ch02"],
        "done_projects": ["mini-redis"],
        "checkins": ["2026-10-18", "2026-10-19"],
        "coins": 1500,
        "outfit": "wizard",
        "theme": "dark",
        "client_rev": 3,
    }
    r = c.put("/api/v1/progress/state", headers=h, json=snap)
    got = envelope(r).get("data") or {}
    rec("进度快照上传", r.status_code == 200 and got.get("coins") == 1500,
        f"chapters={len(got.get('done_chapters') or [])} checkins={len(got.get('checkins') or [])}")

    r2 = c.get("/api/v1/progress/state", headers=h)
    back = envelope(r2).get("data") or {}
    rec("进度快照读回一致",
        back.get("done_chapters") == ["cpp-ch01", "cpp-ch02"]
        and back.get("checkins") == ["2026-10-18", "2026-10-19"]
        and back.get("outfit") == "wizard",
        f"{back.get('done_chapters')} / {back.get('theme')}")

    # 只带增量再传一次：并集语义，旧记录不能丢
    r = c.put("/api/v1/progress/state", headers=h,
              json={"done_chapters": ["cpp-ch03"], "checkins": ["2026-10-20"], "coins": 100, "client_rev": 4})
    merged = envelope(r).get("data") or {}
    rec("增量上传取并集（不覆盖）",
        len(merged.get("done_chapters") or []) == 3 and len(merged.get("checkins") or []) == 3,
        f"chapters={merged.get('done_chapters')}")

    # 脏日期不炸
    r = c.put("/api/v1/progress/state", headers=h, json={"checkins": ["2026-13-45", "not-a-date"]})
    rec("脏日期被忽略而非 500", r.status_code == 200, str(r.status_code))

    r = c.get("/api/v1/progress/state")
    rec("快照接口需要登录", r.status_code == 401, str(r.status_code))

    # ---------- 5. OpenAPI 面 ----------
    spec = envelope(c.get("/openapi.json"))
    paths = spec.get("paths") or {}
    rec("OpenAPI 路由覆盖 ≥ 40", len(paths) >= 40, f"{len(paths)} paths")

    c.close()
    out = Path(".scratch/e2e-http.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"pass": len(PASS), "fail": len(FAIL), "rows": ROWS}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n合计 {len(PASS)} PASS / {len(FAIL)} FAIL")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
