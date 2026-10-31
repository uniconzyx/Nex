# Nex 后端能力对齐（昵称 / 进度）

> 日期：2026-10-31
> 背景：此前「双后端」中，本地账号服务 `auth-server` 已支持「改昵称校验」与「整份进度快照」，
> 而 Nex 内置后端只做到了「昵称无校验」「进度仅 5 个扁平字段」。本变更把 Nex 后端
> 升级到与 `auth-server` **同等能力**，实现真正的双后端对齐。

## 一、改动清单

### 1. 昵称校验（与 auth-server 对齐）
- 新增 `server/app/core/validate.py`：`assert_nickname(raw)`，规则与 `auth-server/src/utils/validate.js` 的 `assertNicknameInput` 一致：
  - 连续空白（含换行/制表符）折叠为单个空格并两端 trim；
  - 长度上限 **24**（折叠后）；
  - 除空白以外的控制字符（`\u0000-\u0008 \u000b-\u001f \u007f`）一律拒绝，返回 400；
  - 空串语义为「清除自定义昵称（回退到用户名显示）」，返回 `""`。
- `server/app/api/v1/auth.py`：
  - `register`：注册时的 `nickname` 也走同一校验；
  - `patch_me`：PATCH `/api/v1/users/me` 在写入前 sanitize `nickname`。
- 前端 `frontend/src/lib/session.ts` 的 `updateNickname` 此前已做 ≤24 / 非空客户端校验，与服务端一致；双后端行为现在完全对齐。

### 2. 进度整份快照（与 auth-server 对齐）
- 模型 `server/app/models/progress.py`：`StudyState` 新增 `snapshot: Mapped[dict|None]`（`JSONType`，可空），用于存整份 `ProgressState`。
- 入参 `server/app/schemas/content.py`：`StudyStateIn` 新增可选 `snapshot: dict|None`。
- 路由 `server/app/api/v1/progress.py`：
  - `PUT /progress/state`：若 `body.snapshot` 存在，则按整份处理——校验为对象、序列化 ≤1MB、存入 `snapshot`，并从快照派生平铺字段（`done_chapters/done_projects/coins/outfit/theme`）供看板/旧客户端复用；否则走历史 5 字段路径（并集语义，向后兼容）。
  - `GET /progress/state`：返回 `snapshot`（整份或 `null`）以及去规范化平铺字段；前端据此判断走哪条合并路径。
- 前端 `frontend/src/lib/sync.ts` 的 nex 分支：
  - `push` 时附带整份 `snapshot`（同时保留 5 字段供兼容）；
  - `doPull` 中若 `remote.snapshot` 存在，走 `mergeRemoteSnapshot`（云端当底、本机覆盖，全量恢复 `answers/bestiary/chapterRuns/weekly`），否则回退到旧的 `mergeRemote` 5 字段路径。
- **价值**：此前 Nex 后端只存 5 字段，换设备后 `answers` 等丢失、掌握度归零；现在 Nex 与 `auth-server` 一样能全量恢复。

### 3. 迁移脚本
- 新增 `server/scripts/migrate_add_study_state_snapshot.py`：为既有 `study_state` 表加 `snapshot` 列。
  - PostgreSQL → `JSONB`；SQLite → `JSON`（离线冒烟/演示库）。
  - 幂等：列已存在则跳过。
- 运行（server 目录，venv 已激活）：
  ```bash
  python -m scripts.migrate_add_study_state_snapshot
  # 指定库：
  DATABASE_URL="sqlite+aiosqlite:///./.smoke.db" python -m scripts.migrate_add_study_state_snapshot
  ```
- 全新库用 `python -m scripts.init_db`（`Base.metadata.create_all`）即已含该列，无需迁移。

## 二、验收

- `server/tests/test_nex_account_parity.py`（pytest，SQLite，10 passed）：
  - 昵称：控制字符→400、超长→400、空白折叠（`a\nb`→`a b`）、空串清除、正常生效；
  - 进度：整份快照 GET/PUT 往返一致（含 `answers/bestiary/chapterRuns/weekly` 等此前会丢的字段）、更新后反映、非对象→400、旧 5 字段回退（snapshot=null 且走并集）；
  - 迁移脚本：DROP 列后重跑能补回、再跑幂等不报错。
- 前端：`tsc --noEmit` 0 error；`vite build` OK。

> 注：SQLite 上 `BigInteger` 主键不自增是本项目测试环境的既有限制（`users/study_state/checkin` 表插入均受影响），
> 与本次改动无关；生产目标库为 PostgreSQL，自增正常。pytest 通过显式指定 id 预置行绕过该限制以验证路由逻辑。

## 三、真 Postgres 端到端验收（2026-10-31 补）

Docker 在本机起不来（主机级安全策略拦截 `com.docker.service`），改用 `embedded-postgres` 18.6.3 内嵌 PG 二进制（含完整 PG 18.6 可执行文件，无需联网下载）起临时库，做真实 Postgres 端到端复核：

- 脚本：`server/scripts/verify_nex_parity_pg.py`（自动起 PG → 建表 → DROP 旧 `snapshot` 列 → 跑迁移 `ADD` → 用 httpx 真打 Nex 路由）。
- 结果（5 项全过，末尾打印 `PG_PARITY_OK`）：
  1. 迁移脚本在真 PG 上 `ALTER TABLE study_state ADD COLUMN snapshot JSONB` 成功，类型经 `information_schema` 确认为 `jsonb`；
  2. 昵称校验：控制字符 / 超长 → 400，空白折叠（`  hello  world  ` → `hello world`，经 `GET /users/me` 验证落库），空串清除；
  3. 整份进度快照 `PUT /progress/state` 后 `GET` 往返一致（含 `answers/chapterRuns/bestiary/weekly`）；
  4. 非对象 `snapshot` → 400；
  5. legacy 5 字段回退（`snapshot=null` 且扁平字段走并集）。
- 运行（server 目录，venv 已激活）：
  ```bash
  python scripts/verify_nex_parity_pg.py
  ```
- 坑：`embedded-postgres` 18.x 的 API 是 `get_server(pgdata, cleanup_mode='stop')` → `ensure_pgdata_inited()` + `ensure_postgres_running()` + `get_uri()`（**不是**旧版 `EmbeddedPostgres().start()`）。`get_uri()` 返回 `postgresql://...`，测异步后端时把 driver 换成 `postgresql+asyncpg://` 即可。

## 四、上线步骤（针对已有 Nex 后端库）

1. 部署新后端代码；
2. 对生产/开发 Postgres 执行迁移：
   ```bash
   DATABASE_URL="postgresql+asyncpg://cppmind:cppmind@127.0.0.1:5432/cppmind" \
     python -m scripts.migrate_add_study_state_snapshot
   ```
3. 前端发布后，nex 用户的进度会自动以整份快照形式落库；旧 5 字段数据在 GET 时以 `snapshot=null` 形式兼容，首次带 snapshot 的 PUT 即升级。
