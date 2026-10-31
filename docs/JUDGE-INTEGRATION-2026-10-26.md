# 判题沙箱端到端联调（B 选项）交付报告

- 日期：2026-10-26
- 项目：CppMind / Nex（D:\WB_Workspace\2026-09-19-21-42-03\CppMind）
- 目标：接 go-judge 判题沙箱联调，让**已生成的 test_cases 真正能端到端判题**。

## 1. 结论

判题链路已完整打通并端到端验证通过：**8/8 PASS**（`scripts/test_judge_e2e.py`，EXIT=0）。

```
前端/客户端 → POST /api/v1/judge/submissions
            → services/judge0.submit_batch（POST judge_local:2358）
            → arq worker poll_judge 轮询比对
            → _finalize 汇总状态 / 错题收录 / 诊断 → 落库
            → GET /api/v1/judge/submissions/{id} 可见结果
```

> 注：因本机 Docker 代理（127.0.0.1:31181，已停止）劫持镜像流量，真实 judge0/go-judge 镜像拉不下来。
> 采用**纯 D 盘的本地 judge0 协议兼容服务** `scripts/judge_local.py`（g++/javac 编译运行，端口 2358）
> 零改动对接 `services/judge0.py`。生产环境应换回 go-judge 侧车，仅需校准 `GET /languages` 即可。

## 2. 修复的 3 处阻塞 bug

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| 1 | `server/app/api/v1/judge.py` | `exercise.test_cases` 关系在 async 上下文外惰性加载 → `MissingGreenlet` → exercise_id 提交 500 | 改为 `select(Exercise).options(selectinload(Exercise.test_cases))` 预加载 |
| 2 | `server/app/api/v1/system.py` | `features.judge` 硬编码 `None`（注释称"判题由客户端沙箱负责"） | 改为实时 `GET {judge0_url}/languages` 探测，如实上报；`/system/health` 现返回 `judge.ok=true` |
| 3 | `server/app/services/judge0.py` | `LANG_MAP[lang]` 对未知 CodeStd 直接 KeyError | 改为 `LANG_MAP.get(lang, 54)` 回退 cpp |

## 3. 端到端验证（scripts/test_judge_e2e.py，8/8 PASS）

| 用例 | 期望 | 结果 |
|------|------|------|
| 种入 1 道带 2 个 test_case 的题目 | exercise_id 可用 | PASS（exercise_id=4） |
| 注册/登录拿到 access_token | 200 + token | PASS |
| 自由运行台（`exercise_id=null`）提交 cpp | status=ac, stdout 正确 | PASS（stdout='judge ok'） |
| exercise_id + 正确解（读两整数求和） | status=ac, **passed=2** | PASS ✅ 真实 test_cases 比对 |
| exercise_id + 错误解（打印乘积） | status=wa, passed=0 | PASS |
| exercise_id + 编译错误代码 | status=ce, stderr 已捕获 | PASS |
| 直接走 service 层 `submit_batch`/`fetch_results` | AC/WA 比对正确 [3,4] | PASS |

## 4. 本地联调一键起（判题三件套，缺一不可）

```bash
# ① 后端（注意：uvicorn 不带 --reload，改代码需重启）
cd server
../server/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# ② 本地 judge0 兼容服务（端口 2358；需 PATH 含 javapath；g++=D:\mingw64\bin\g++.exe）
cd <CppMind>
export PATH="/c/Program Files/Common Files/Oracle/Java/javapath:$PATH"
server/.venv/Scripts/python.exe scripts/judge_local.py

# ③ arq worker（判题轮询消费；dev_stack 默认不起，必须单独起）
cd server
../server/.venv/Scripts/python.exe -m arq app.workers.settings.WorkerSettings
```

> ⚠️ 隐藏缺口：`scripts/dev_stack.py` 只起 backend + frontend，**不起 arq worker**。
> 没有 worker，提交后永远停在 running，判题不闭环。这是此前联调未跑通的关键原因之一。

环境前置（沿用 Phase A/B）：`server/.venv` 依赖已装；PG(:5432)/Redis(:6379) 已起；
`.env` database_url 端口 5433→5432；alembic 已建 41 表。pip/Docker 流量需 `no_proxy=* HTTP_PROXY= HTTPS_PROXY=` 走直连。

## 5. 仍待办（非 B 范围，主人已点明"之后补充"）

1. **DB 中 exercises/test_cases 仍为空**（文件型内容未导入）。判题链路已验证可跑，
   但要让前端判题页"有题可做"，需把 `content/*/exercises.json` 导入 Postgres
   （admin 的 `/content/import` 或对应同步脚本）。
2. **Java 判题缺失**：`LANG_MAP` 与 `CodeStd` 枚举均无 java（第 3 项修复仅加回退，不新增 java）。
3. 缺口三类题仍未纳入判题：纯函数片段题（无 main）、文件 IO 题（fopen/ifstream）、
   无 reference_code 题——属主人明确的"之后补充"范围。
4. 生产应换回 go-judge 侧车并校准 `/languages`，本地兼容服务仅用于开发联调。
