# 本地账号服务运行手册（auth-server）

面向"这台机器上自用"的场景：不注册、不联网、账号由你手工创建，只为**多设备同步进度 + 身份**。
工程目录：`C:/Users/zyx/WorkBuddy/2026-10-24-20-23-46/auth-server`（独立于 CppMind 仓库）。

> 设计文档：`auth-server/README.md`（含建表 SQL、业务码表、安全取舍、上线检查）
> 交付记录：`auth-server/AUTH-MODULE-DESIGN.md`

---

## 0. 一句话说清它和 Nex 的关系

CppMind 前端有**两套**认证后端，在「设置 → 账号服务」里切换：

| 后端 | 地址 | 能力 |
|---|---|---|
| Nex 内容服务（默认） | 由 `nex.apiBaseUrl` 决定 | 注册、续期、微信扫码、容器化进度（5 个字段） |
| **本地账号服务**（本手册） | 默认 `http://127.0.0.1:3000` | 无注册、无第三方登录、令牌 7 天、**整份进度快照** |

切换后端会先清空令牌（两套令牌互不通用），所以切过去要重新登录一次。

---

## 1. 起服务（四步）

```bash
cd C:/Users/zyx/WorkBuddy/2026-10-24-20-23-46/auth-server

# 1) 依赖（首次）
npm install

# 2) 配置：复制模板后改三个值
cp .env.example .env
#   JWT_SECRET  → openssl rand -hex 32
#   DB_USER / DB_PASSWORD → 你的 MySQL 账号
#   DB_NAME     → 默认 auth_db 即可

# 3) 建库建表（需要 CREATE 权限，用管理员账号跑一次）
DB_USER=root DB_PASSWORD=xxx npm run db:init
#   输出应列出三张表：progress、token_blacklist、user

# 4) 建第一个账号（密码交互输入，不回显、不进 shell history）
npm run user:create
```

起服务：

```bash
npm start
# [auth-server] 已启动 http://127.0.0.1:3000
# [auth-server] 数据库 127.0.0.1:3306/auth_db
# [auth-server] 锁定策略 连续 5 次错误 → 锁 30 分钟
```

探活：

```bash
curl http://127.0.0.1:3000/api/auth/health
# {"code":0,"message":"ok","data":{"service":"auth-server","db":{"ok":true,"error":null},"time":"..."}}
```

`db.ok=false` 时不要怀疑服务没起——先看 `db.error`，九成是 `.env` 里的库名/密码不对。

---

## 2. 前端接上它

1. 打开 CppMind → 设置 → 账号服务 → 选「本地账号服务」。
2. 地址填 `http://127.0.0.1:3000`（改了 `PORT` 就跟着改）。
3. 点「检测」：应当显示服务在线 + 数据库连通。
4. 回登录页，用第 1 步创建的账号登录。

### CORS 是这里唯一的坑

浏览器会先发预检，`CORS_ORIGINS` 里没有当前来源时 `fetch` 直接抛 `TypeError`，
连 401 都看不到，表现是"点了没反应"。

- 默认白名单已包含 **1420**（vite dev server）、4173（preview）、8903 与 Tauri 协议。
- 换端口 / 打包成 EXE 用自定义协议时，把实际来源加进 `.env`：
  ```bash
  CORS_ORIGINS=http://127.0.0.1:1420,tauri://localhost,https://tauri.localhost
  ```

---

## 3. 登录之后会发生什么

| 动作 | 行为 |
|---|---|
| 登录 | 拉一次云端进度快照，与本地做**并集**合并；本机有云端没有的内容就回推一次 |
| 答题 / 通关 / 签到 | 500ms 节流后把整份 `ProgressState` 推到云端（失败静默，下次操作重试） |
| 改昵称 | 个人页「改昵称」→ `PUT /api/auth/profile`，返回整份资料，直接更新本地缓存 |
| 改密码 | 设置页 → 改密后**自动换新令牌**（旧令牌全端失效，token_version+1） |
| 登出 | 本地立即清空；服务端把 jti 写进黑名单（失败会提示"已登出但令牌未作废"） |

进度同步的三条不变量（改 `sync.ts` 前必读）：

1. **本机是事实源**。任何进度变更先本地生效，UI 立即更新；网络只做镜像。
2. **合并只做并集**，不删除任何记录；金币取 max；外观（theme/outfit）跟本机走。
3. **不比对字符串就重推**。云端是 MySQL JSON 列，键序会被重排，
   所以 `sync.ts` 用 `stable()` 做键序无关比较，避免每次登录白传 300KB。

---

## 4. 常见故障对照

| 现象 | 原因 | 处置 |
|---|---|---|
| 设置页「检测」失败，提示连接被拒 | 服务没起 / 端口不对 | `npm start`，核对 `PORT` 与地址 |
| 请求一律 `TypeError: Failed to fetch` | CORS 白名单没有当前来源 | 加进 `CORS_ORIGINS` 后重启 |
| 登录提示「还可再试 N 次」 | 密码错，快触发了账号锁定 | 输对即清零；锁了等 30 分钟或用 `user:create` 重置 |
| 登录成功但进度看起来"回到旧版本" | 用的是 Nex 后端（只同步 5 个字段，没有 answers） | 切到「本地账号服务」后重新登录，会走整份快照 |
| 改完密码立刻掉线 | 客户端没替换服务端返回的新令牌 | 已在 `session.changePassword` 里处理；若复现，查是否走了旧构建 |
| `db.ok=false` | 库名/账号/端口不对，或库未建 | 先跑 `npm run db:init`，再看 `db.error` 原文 |

---

## 5. 日常维护

```bash
# 重置某人的密码（同时踢掉他所有设备）
npm run user:create -- --reset dave

# 清理过期黑名单（令牌自然过期后那行就没用了）
npm run tokens:clean
# crontab: 0 4 * * * cd /path/to/auth-server && node scripts/clean-tokens.js
```

备份只需要两张表：`user`（账号）与 `progress`（进度快照）。`token_blacklist` 可随时清空。

---

## 6. 验收（想确认这套东西是好的）

```bash
# 后端 116 项端到端断言（真实 MySQL + 真实 HTTP，会另建 auth_e2e 库，不碰业务库）
E2E_DB_ENV=.env.e2e node test/e2e.mjs

# 前端页面级验收
cd D:/WB_Workspace/2026-09-19-21-42-03/CppMind
node scripts/verify_p3.mjs
```

`test/e2e.mjs` 会拒绝在名字不以 `_e2e` / `_test` 结尾的库上运行——它会 `DROP TABLE` 重建，
误连业务库等于"跑个测试把进度删了"。这条闸是刻意的，不要绕过。
