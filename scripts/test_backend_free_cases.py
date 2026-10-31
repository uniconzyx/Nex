"""后端增强验证：模拟前端 backend 降级通道的核心调用。

验证点：
  1) POST /judge/submissions (exercise_id=null, test_cases=[...]) 支持携带用例比对；
  2) 轮询 GET /judge/submissions/{id} 返回逐用例 case_results；
  3) AC / WA 判定正确。
"""
import asyncio
import httpx
import time

BASE = "http://127.0.0.1:8000"
EMAIL = f"pubby_verify_{int(time.time())}@example.com"
PW = "PubbyTest123!"

CPP_SUM = """#include <iostream>
using namespace std;
int main(){
  int n; cin>>n; int s=0,x;
  for(int i=0;i<n;i++){cin>>x;s+=x;}
  cout<<s<<endl;
  return 0;
}
"""


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # 1) 登录
        r = await c.post("/api/v1/auth/login", json={"account": EMAIL, "password": PW})
        if r.status_code not in (200, 201):
            # 先注册再登录
            await c.post("/api/v1/auth/register", json={"email": EMAIL, "password": PW})
            r = await c.post("/api/v1/auth/login", json={"account": EMAIL, "password": PW})
        token = r.json()["data"]["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        print(f"[auth] login ok, token len={len(token)}")

        # 2) AC：正确解 + 两个用例
        body = {
            "exercise_id": None,
            "lang": "cpp17",
            "source_code": CPP_SUM,
            "test_cases": [
                {"input": "3\n1 2 3\n", "expected_output": "6"},
                {"input": "2\n10 20\n", "expected_output": "30"},
            ],
        }
        r = await c.post("/api/v1/judge/submissions", json=body, headers=h)
        assert r.status_code == 202, f"submit AC status={r.status_code} body={r.text[:200]}"
        sub_id = r.json()["data"]["submission_id"]
        print(f"[submit] AC sub_id={sub_id}")

        # 3) 轮询至终态
        for _ in range(20):
            r = await c.get(f"/api/v1/judge/submissions/{sub_id}", headers=h)
            d = r.json()["data"]
            if d["status"] not in ("queued", "running"):
                break
            await asyncio.sleep(1)
        print(f"[poll] status={d['status']} passed={d['passed']} total={d['total']}")
        cr = d.get("case_results")
        print(f"[poll] case_results={cr}")
        assert d["status"] == "ac", f"期望 ac, 实际 {d['status']}"
        assert d["passed"] == 2 and d["total"] == 2, f"期望 2/2, 实际 {d['passed']}/{d['total']}"
        assert cr and len(cr) == 2 and all(x["status"] == "ac" for x in cr), f"逐用例异常: {cr}"
        print("[OK] AC + 逐用例明细正确")

        # 4) WA：期望写错
        body2 = {
            "exercise_id": None,
            "lang": "cpp17",
            "source_code": CPP_SUM,
            "test_cases": [{"input": "3\n1 2 3\n", "expected_output": "999"}],
        }
        r = await c.post("/api/v1/judge/submissions", json=body2, headers=h)
        sub_id2 = r.json()["data"]["submission_id"]
        for _ in range(20):
            r = await c.get(f"/api/v1/judge/submissions/{sub_id2}", headers=h)
            d = r.json()["data"]
            if d["status"] not in ("queued", "running"):
                break
            await asyncio.sleep(1)
        print(f"[poll] WA status={d['status']} passed={d['passed']}")
        cr2 = d.get("case_results")
        print(f"[poll] case_results={cr2}")
        assert d["status"] == "wa", f"期望 wa, 实际 {d['status']}"
        assert d["passed"] == 0, f"期望 passed=0, 实际 {d['passed']}"
        assert cr2 and cr2[0]["status"] == "wa", f"逐用例 WA 异常: {cr2}"
        print("[OK] WA + 逐用例明细正确")


if __name__ == "__main__":
    asyncio.run(main())
    print("ALL PASS")
