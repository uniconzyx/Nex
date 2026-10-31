#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判题链路端到端验证（B 选项交付验证）。

验证范围：
  1. 在 DB 中种入 1 道带 2 个 test_case 的题目（引用现有 chapter）；
  2. 注册/登录拿到 access_token；
  3. 自由运行台提交 -> 轮询直到终态（验证 auth/rate/worker/_finalize/落库）；
  4. exercise_id 提交正确解 -> 期望 AC(passed=2)；
  5. exercise_id 提交错误解 -> 期望 WA(passed=0)；
  6. exercise_id 提交编译错误 -> 期望 CE；
  7. 直接调用 judge0.submit_batch/fetch_results 验证 AC/WA 比对逻辑。

运行：cd server && ../server/.venv/Scripts/python.exe ../scripts/test_judge_e2e.py
依赖：server/.venv（httpx/sqlalchemy/asyncpg 已装），且 judge_local(:2358) 与 arq worker 已起。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"))

import httpx
from sqlalchemy import text

from app.db import SessionLocal
from app.models.enums import CodeStd, Difficulty, ExerciseSource, ExerciseType
from app.models.exercise import Exercise, TestCase
from app.services import judge0

BASE = "http://127.0.0.1:8000/api/v1"
EMAIL = "judge_e2e_2026@example.com"
PW = "JudgeE2E123"

REF = (
    "#include <iostream>\n"
    "using namespace std;\n"
    "int main(){int a,b;cin>>a>>b;cout<<a+b<<endl;return 0;}\n"
)
WRONG = (
    "#include <iostream>\n"
    "using namespace std;\n"
    "int main(){int a,b;cin>>a>>b;cout<<a*b<<endl;return 0;}\n"
)
CECODE = "int main(){ retturn 0; }\n"
# 直接走 service 比对时用：固定打印 "A"，便于构造 AC/WA 两种预期
CODE_PRINT_A = '#include <iostream>\nusing namespace std;\nint main(){cout<<"A";return 0;}\n'
FREERUN = (
    '#include <iostream>\nusing namespace std;\n'
    'int main(){cout<<"judge ok";return 0;}\n'
)

SUMMARY = []


def log(name, ok, detail=""):
    SUMMARY.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


async def seed() -> int:
    async with SessionLocal() as db:
        ch = await db.scalar(text("SELECT id FROM chapters ORDER BY id LIMIT 1"))
        ex = Exercise(
            chapter_id=ch, type=ExerciseType.coding, difficulty=Difficulty.easy,
            title="E2E 验证题：两数之和",
            content_md="读入两个整数 a b，输出 a+b。",
            time_limit_ms=2000, memory_limit_mb=256,
        )
        db.add(ex)
        await db.flush()
        db.add(TestCase(exercise_id=ex.id, input="3 4\n", expected_output="7\n", is_sample=True, sort=1))
        db.add(TestCase(exercise_id=ex.id, input="10 20\n", expected_output="30\n", is_sample=False, sort=2))
        await db.commit()
        return ex.id


async def cleanup(ex_id: int):
    async with SessionLocal() as db:
        await db.execute(text("DELETE FROM submissions WHERE exercise_id=:e"), {"e": ex_id})
        await db.execute(text("DELETE FROM exercises WHERE id=:e"), {"e": ex_id})
        await db.commit()


async def wait_sub(cli, headers, sub_id, limit=40):
    for _ in range(limit):
        await asyncio.sleep(0.7)
        r = await cli.get(f"/judge/submissions/{sub_id}", headers=headers)
        if r.status_code != 200:
            return {"status": f"http{r.status_code}", "raw": r.text}
        d = r.json()["data"]
        if d["status"] not in ("queued", "running"):
            return d
    return None


async def submit(cli, headers, payload):
    r = await cli.post("/judge/submissions", headers=headers, json=payload)
    if r.status_code != 202:
        return None, r.text
    return r.json()["data"]["submission_id"], None


async def main():
    ex_id = await seed()
    log("seed exercise + 2 test_cases", True, f"exercise_id={ex_id}")

    async with httpx.AsyncClient(base_url=BASE, timeout=30) as cli:
        r = await cli.post("/auth/register", json={"email": EMAIL, "password": PW})
        # 200=新建；400/409=已存在（上一轮残留），登录即可，视为通过
        log("register/lookup test user", r.status_code in (200, 400, 409), f"status={r.status_code}")
        r = await cli.post("/auth/login", json={"account": EMAIL, "password": PW})
        if r.status_code != 200:
            log("login", False, r.text[:200])
            await cleanup(ex_id)
            return
        token = r.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        log("login -> access_token", True)

        # 3. 自由运行台
        sub_id, err = await submit(cli, headers, {"exercise_id": None, "lang": "cpp17",
                                                 "source_code": FREERUN, "stdin": ""})
        if err:
            log("free-run submit", False, err[:200])
        else:
            d = await wait_sub(cli, headers, sub_id)
            ok = d and d["status"] == "ac" and "judge ok" in (d.get("stdout") or "")
            log("free-run end-to-end", ok,
                f"status={d['status'] if d else None} stdout={(d.get('stdout') if d else None)!r}")

        # 4. exercise_id 正确解 -> AC(passed=2)
        sub_id, err = await submit(cli, headers, {"exercise_id": ex_id, "lang": "cpp17",
                                                  "source_code": REF})
        if err:
            log("exercise AC submit", False, err[:200])
        else:
            d = await wait_sub(cli, headers, sub_id)
            ok = d and d["status"] == "ac" and d.get("passed") == 2 and d.get("total") == 2
            log("exercise AC (passed=2)", ok,
                f"status={d['status'] if d else None} passed={d.get('passed') if d else None}")

        # 5. exercise_id 错误解 -> WA(passed=0)
        sub_id, err = await submit(cli, headers, {"exercise_id": ex_id, "lang": "cpp17",
                                                  "source_code": WRONG})
        if err:
            log("exercise WA submit", False, err[:200])
        else:
            d = await wait_sub(cli, headers, sub_id)
            ok = d and d["status"] == "wa" and d.get("passed") == 0
            log("exercise WA (passed=0)", ok,
                f"status={d['status'] if d else None} passed={d.get('passed') if d else None}")

        # 6. exercise_id 编译错误 -> CE
        sub_id, err = await submit(cli, headers, {"exercise_id": ex_id, "lang": "cpp17",
                                                  "source_code": CECODE})
        if err:
            log("exercise CE submit", False, err[:200])
        else:
            d = await wait_sub(cli, headers, sub_id)
            ok = d and d["status"] == "ce"
            log("exercise CE", ok,
                f"status={d['status'] if d else None} stderr={((d.get('stderr') or '')[:60] if d else None)!r}")

    # 7. 直接走 service 层比对逻辑（不经过 HTTP/worker）
    #    CODE_PRINT_A 固定打印 "A"：预期 "A" -> AC(3)，预期 "B" -> WA(4)
    try:
        tokens = await judge0.submit_batch(CODE_PRINT_A, CodeStd.cpp17, [("", "A"), ("", "B")], 2.0, 256 * 1024)
        res = await judge0.fetch_results(tokens)
        sts = [r["status"]["id"] for r in res]
        log("direct judge0 service compare (AC/WA)", sts == [3, 4], f"status_ids={sts}")
    except Exception as e:  # noqa: BLE001
        log("direct judge0 service compare", False, repr(e)[:200])

    await cleanup(ex_id)
    failed = [n for n, o, _ in SUMMARY if not o]
    print("\n=== SUMMARY ===")
    print(f"total={len(SUMMARY)} failed={len(failed)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
