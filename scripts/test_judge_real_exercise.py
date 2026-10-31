"""针对真实导入的 coding 题走完整判题链路（认证 -> 提交 -> arq worker -> judge_local -> 落库）。"""
import asyncio
import json
import urllib.request

BASE = "http://127.0.0.1:8000"
EMAIL = "pubby_real_e2e@example.com"
PW = "Test1234!"

# 真实导入的 coding 题：读取 n 个数求和（3 个 test_cases）
EX_ID = 1548

CORRECT = r"""#include <iostream>
using namespace std;
int main(){
    long long s=0,n,x;
    if(!(cin>>n)) return 0;
    while(n--){ cin>>x; s+=x; }
    cout<<s;
    return 0;
}"""

WRONG = r"""#include <iostream>
using namespace std;
int main(){ cout<<0; return 0; }"""


async def reset_quota():
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url("redis://localhost:6379/0")
        n = 0
        async for k in r.scan_iter("quota:judge:*"):
            await r.delete(k); n += 1
        await r.aclose()
        print(f"[quota] cleared {n} keys")
    except Exception as e:
        print("[quota] reset skipped:", e)


def req(method, path, token=None, data=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def get_id(resp):
    d = resp[1]
    if isinstance(d, dict):
        if "id" in d:
            return d["id"]
        data = d.get("data")
        if isinstance(data, dict):
            for k in ("id", "submission_id"):
                if k in data:
                    return data[k]
    return None


async def main():
    await reset_quota()
    # 1) 注册/登录
    st, r = req("POST", "/api/v1/auth/register", data={"email": EMAIL, "password": PW})
    if st not in (200, 201, 409) and not (st == 400 and "已注册" in str(r.get("message", ""))):
        print("register unexpected:", st, r); return
    st, r = req("POST", "/api/v1/auth/login", data={"account": EMAIL, "password": PW})
    if st not in (200, 201) or "access_token" not in (r.get("data") or {}):
        print("login failed:", st, r); return
    token = r["data"]["access_token"]
    print("[auth] login OK")

    # 2) 正确解 -> 期望 AC
    st, r = req("POST", "/api/v1/judge/submissions", token,
                {"exercise_id": EX_ID, "lang": "cpp17", "source_code": CORRECT, "stdin": ""})
    print("submit(correct):", st, r)
    sid = get_id((st, r))
    if not sid:
        print("NO submission id"); return
    # 3) 轮询直到终态
    final = None
    for _ in range(25):
        st, r = req("GET", f"/api/v1/judge/submissions/{sid}", token)
        d = r.get("data", r) if isinstance(r, dict) else r
        status = d.get("status") if isinstance(d, dict) else None
        if status in ("ac", "wa", "ce", "re", "tle", "mle", "ie"):
            final = d; break
        await asyncio.sleep(1.2)
    passed = (final or {}).get("passed")
    print(f"[REAL exercise_id={EX_ID}] correct -> status={(final or {}).get('status')} passed={passed}")
    assert (final or {}).get("status") == "ac", f"期望 AC，实际 {(final or {}).get('status')}"
    assert passed == 3, f"期望 passed=3，实际 {passed}"

    # 4) 错误解 -> 期望 WA
    st, r = req("POST", "/api/v1/judge/submissions", token,
                {"exercise_id": EX_ID, "lang": "cpp17", "source_code": WRONG, "stdin": ""})
    sid2 = get_id((st, r))
    final2 = None
    for _ in range(25):
        st, r = req("GET", f"/api/v1/judge/submissions/{sid2}", token)
        d = r.get("data", r) if isinstance(r, dict) else r
        status = d.get("status") if isinstance(d, dict) else None
        if status in ("ac", "wa", "ce", "re", "tle", "mle", "ie"):
            final2 = d; break
        await asyncio.sleep(1.2)
    print(f"[REAL exercise_id={EX_ID}] wrong -> status={(final2 or {}).get('status')} passed={(final2 or {}).get('passed')}")
    assert (final2 or {}).get("status") == "wa", f"期望 WA，实际 {(final2 or {}).get('status')}"

    print("\n✅ 真实导入题库端到端判题验证通过：AC(正确解,passed=3) + WA(错误解) 均正确")


if __name__ == "__main__":
    asyncio.run(main())
