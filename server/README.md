# CppMind Server（FastAPI 后端）

> 阶段 4 交付物。依据：`docs/Phase2-Architecture.md`、`docs/Phase3-Database-API.md`

## 快速开始

```bash
# 1. 准备环境变量
cp .env.example .env          # 按需修改 JWT_SECRET、AI Key、GitHub Token

# 2. 一键起全栈（在 deploy/ 目录）
cd ../deploy
docker compose up -d --build

# 3. 初始化数据库（二选一）
# 方式 A：开发快速建表 + 种子数据（2 门课程 / 27 章 / 4 个成就）
docker compose exec api python -m scripts.init_db
# 方式 B：Alembic 迁移（生产口径）
docker compose exec api alembic revision --autogenerate -m "init"
docker compose exec api alembic upgrade head

# 4. 验证
curl http://localhost/health
# API 文档： http://localhost:8000/docs（或经 nginx: http://localhost/api/v1/docs 需自行加路由）
```

## 服务清单（deploy/docker-compose.yml）

| 服务 | 说明 |
|---|---|
| nginx | 反代 + 第一层限流（10r/s/IP），SSE 长连接已配置 |
| api | FastAPI + uvicorn |
| worker | arq 消费者：判题轮询 / 资源同步 / AI 诊断兜底 + 每日 03:00 同步 cron |
| postgres / redis | 主库 / 缓存·限流·队列 |
| minio | 项目模板 tar 包等对象存储（console :9001） |
| judge0-server / judge0-workers / judge0-db / judge0-redis | Judge0 CE 判题栈（workers privileged，isolate 沙箱） |
| prometheus(:9090) / grafana(:3001) | 监控（api 暴露 /metrics） |

## 目录结构

```
app/
  core/       config / security(JWT) / responses(统一响应+错误码) / rate_limit(限流+配额) / deps(鉴权) / queue(arq)
  models/     26 概念实体 + 7 连接表（SQLAlchemy 2.0）
  schemas/    Pydantic v2 请求模型
  api/v1/     auth / content / exercises / judge / progress / projects / ai / resources / admin
  services/   judge0(沙箱客户端) / diagnosis(规则库) / ai_provider(双通道) / mindmap(四态推导) / sync/(GitHub·LeetCode·导入器)
  workers/    arq 任务（poll_judge / run_sync / ai_diagnose / daily_sync_cron）
scripts/      init_db.py / import_bank.py / validate_content.py
tests/        规则库 / 题库包校验 / 导图状态推导（纯逻辑，无需 DB）
```

## 关键流程

**判题**：`POST /api/v1/judge/submissions` → 限流+配额 → Judge0 批量提交（每用例一个 submission，沙箱参数：无网络/CPU/内存/输出 1MB）→ 202 返回 → arq `poll_judge` 轮询终态 → 汇总状态（CE>RE>TLE>MLE>WA>AC）→ 规则库诊断（未命中入队 AI 兜底）→ 错题自动收录（1d/3d/7d 间隔复习）。

**AI 对话**：`POST /api/v1/ai/conversations/{id}/messages` → SSE 流式（meta/delta/done 事件）→ 上下文注入（章节/代码/错题，6K 字符预算）→ 模型分级（诊断小模型，面试/审查/计划大模型）→ 消息全量落库支持断线续拉。

**资源同步**：`POST /api/v1/admin/sync`（管理员）或每日 cron → GitHub REST（仓库元数据）/ LeetCode GraphQL（题目元数据，**不存正文**）→ upsert `resources` + `resource_chapters` → `sync_jobs` 记录成败。

## 题库导入

```bash
# 命令行
python -m scripts.import_bank ../shared/samples/nowcoder_sample.json
# 或 API（管理员）：POST /api/v1/admin/content/import （multipart 上传 JSON）
```
两种包格式：`cppmind-external-v1`（外部题映射）、`cppmind-exercise-v1`（自建题，coding 题强制 ≥1 测试用例，选择题答案必须 ⊆ 选项）。校验失败**整包回滚**。

## 内容完整性校验（CI）

```bash
python -m scripts.validate_content ../content   # 退出码非 0 即存在缺口
```
规则见 `scripts/validate_content.py` 头部注释（7 类内容：goals/concept/pitfalls/examples≥10/exercises≥5 含 coding/interview≥3 含解析/project≥1）。

## ⚠️ 部署校准项

1. **Judge0 语言 ID**：`app/services/judge0.py` 的 `LANG_MAP` 默认按官方 1.13.x 镜像。部署后执行 `curl $JUDGE0_URL/languages` 核对并按实际 ID 修改（尤其要区分 gcc 版本以支撑 C++20/23）。
2. **nginx 暴露 /docs**：生产建议仅内网开放 FastAPI `/docs`，或加 Basic Auth。
3. **secret**：`.env` 中 JWT 双密钥、AI Key、GitHub Token 不得入库；生产用 Docker secrets 或 CI 注入。

## 逻辑漏洞自查（阶段 4）

| # | 检查点 | 结论 | 处理 |
|---|---|---|---|
| 1 | 判题轮询若永不终态，worker 会死循环 | 存在风险 | `_POLL_MAX=20`（约 30s）封顶，超时置 `ie` |
| 2 | 配额计数超限请求本身被计入 | 会误伤 | `check_daily_quota` 超限时 `decr` 回退 |
| 3 | 错题收录对自由运行台提交（exercise_id 为空） | 会误收录 | 仅 `exercise_id` 非空时收录 |
| 4 | 轮询与接口并发写 submissions | 可能竞态 | 终态写入只在 worker 进行；接口仅写 queued/running 与 token |
| 5 | SSE 结束时 DB session 已关闭 | 会报错 | event_stream 内使用 `db.begin()` 新事务写 assistant 消息（长连请求 session 由 FastAPI 保持至响应结束） |
| 6 | 历史消息全量注入导致 token 爆炸 | 存在风险 | 仅取最近 20 条 + 上下文 6K 字符预算 |
| 7 | refresh token 旋转但旧 token 未拉黑 | 已知折衷 | 代码内注明后续加 Redis 黑名单（P1 增强，不阻塞 MVP） |
| 8 | LeetCode slug 映射失效（题目下线） | 会 404 | 同步计入 `stats.failed`，单条失败不中断任务 |
| 9 | 章节缺失时导入自建题包 | 会脏写 | 导入先校验 chapter 存在，嵌套事务 + 整包回滚 |
| 10 | `projects.py` 游客依赖曾误用 get_current_user | 编码期发现 | 已改 `get_optional_user` |

**自查总结**：10 项检查，4 项编码期已修复（#1/#2/#9/#10），2 项设计性折衷已注明后续迭代位（#5 验证项、#7），其余为防御性确认。
