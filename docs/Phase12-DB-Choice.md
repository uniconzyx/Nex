# 阶段12 · 数据库选型与本地依赖说明

> 回答两个问题：**本机 Docker 配置完不完整**、**为什么后端要 PG 而不是 MySQL**。
> 所有结论都有可复跑的命令，不靠记忆。

---

## 1. 本机 Docker 配置实测

### 1.1 现状盘点

| 项目 | 实测结果 | 判定 |
| --- | --- | --- |
| Docker Desktop 安装 | `C:\Program Files\Docker\Docker\Docker Desktop.exe` 存在，15.1MB | ✅ 已装 |
| Docker CLI | 29.6.1 / API 1.55 / go1.26.4 | ✅ 正常 |
| Docker Engine | `npipe:////./pipe/dockerDesktopLinuxEngine` 管道不存在 | ❌ **未运行** |
| WSL2 发行版 | `Ubuntu` Stopped、`docker-desktop` Stopped | ❌ 未启动 |
| `.wslconfig` | `memory=6GB, processors=4, swap=2GB, localhostForwarding=true, sparseVhd=true` | ⚠️ 见 1.3 |
| 开机自启 | `"AutoStart": false` | ⚠️ 不会自动拉起 |
| 数据盘位置 | `D:\DockerBigData\DockerDesktopWSL\DockerDesktopWSL` | ✅ 已迁到 D 盘 |
| containerd 快照器 | `UseContainerdSnapshotter: true` | ✅ 已启用 |

### 1.2 为什么起不来：两个独立故障

**故障 A：系统代理指向已死端口（主因）**

```
[ERR] GET https://mcp.docker.com/oauth/providers/config request failed:
  connecting to 127.0.0.1:31181: connectex: No connection could be made
because the target machine actively refused it.
```

系统代理 `ProxyEnable=1`、`ProxyServer=https://127.0.0.1:31181`，但 31181 **无监听**
（`netstat` 只有一条 `SYN_SENT`，说明有进程在反复尝试连接一个没人监听的端口）。
Docker Desktop 的 OAuth 配置拉取因此进入无限重试（日志里 `29 left`、`28 left` 递减），
卡在启动早期阶段，引擎因此永远起不来。

> 临时把 `ProxyEnable` 置 0 再启动，仍未能拉起引擎——说明代理之外还有第二层问题。
> 已把 `ProxyEnable` **恢复为 1**，本机网络配置未做持久改动。

**故障 B：`docker-desktop` 发行版里只有 init，没有 dockerd**

直接手动拉起发行版可以成功：

```bash
wsl.exe -d docker-desktop -u root -e /bin/true   # STATE 变成 Running
wsl.exe -d docker-desktop -u root -e ps aux
```

输出只有 `init`、`plan9`、`SessionLeader`、`Relay` —— **没有 `dockerd`**。
说明发行版被拉起后，bootstrap 没有继续把引擎进程拉起来，卡在
`enginedependencies: waiting for init control API to respond`。

### 1.3 `.wslconfig` 的一个隐性问题

启动时 WSL 打印：

```
wsl: wsl2.sparseVhd:C:\Users\zyx\.wslconfig - 无法识别的配置项
wsl: 检测到 localhost 转发设置项，但 NAT 模式下 WSL 不支持 localhost 转发
```

两个点：

1. `sparseVhd=true` 在当前 WSL 版本下**不被识别**（键名可能已变，或被合并进 Docker Desktop 自身设置），属于无效配置，建议删掉。
2. `localhostForwarding=true` 在 **NAT 模式**下 WSL 明确提示不支持。这就是之前 WSL 里跑 PG、Windows 侧 `localhost:55432` 时通时断的根因——**不是网络抖动，是这条配置本身不生效**。

### 1.4 结论与建议

**配置完整性判定：组件齐全，但运行时不可用，且存在 2 个真实配置错误。**

修复顺序（按性价比）：

1. 停掉那个把流量指向 `127.0.0.1:31181` 的代理软件，或改成直连；这是 Docker 起不来的直接原因。
2. 删掉 `.wslconfig` 里的 `sparseVhd=true`；`localhostForwarding` 保留无害但别指望它生效。
3. Docker Desktop → Settings → Troubleshoot → **Reset to factory defaults**（会清掉本地镜像，项目不依赖，可接受）。
4. 确认 `wsl.exe --shutdown` 后重新启动 Docker Desktop，`docker info` 能看到 `ServerVersion`。

**但对本项目来说，Docker 不是必需品** —— 见下一节。

---

## 2. 后端为什么用 Docker

### 2.1 Docker 在这里的真实角色

`server/docker-compose.yml` 只有两个服务：

```yaml
services:
  postgres:  image: postgres:16-alpine
  redis:     image: redis:7-alpine
```

它解决的是 **"新机器上少装两个服务"** 这个开发体验问题，**不是产品运行时依赖**。
证据：

- 桌面端 exe 内嵌 `go-judge`，判题完全离线，不连任何数据库；
- 手机端 APK 进度全部走 `localStorage`，断网 15 个页面全部正常渲染；
- 拆掉 Docker 后，改用 Windows 原生 PostgreSQL 17.2，`e2e_http.py` **34 项全绿**。

所以准确的说法是：**Docker 是"本地依赖的一键起法"之一，不是架构要求。**

### 2.2 当前实际在跑的（不依赖 Docker）

| 组件 | 实现 | 端口 |
| --- | --- | --- |
| PostgreSQL | Windows 原生 17.2（EnterpriseDB zip 解压即用） | 5433 |
| Redis | 无（`fail-open` 降级，限流/配额放行） | — |
| FastAPI | uvicorn | 8000 |

```bash
# 起 PG（数据在 .scratch/pgsql/data）
.scratch/pgsql/bin/pg_ctl.exe -D .scratch/pgsql/data \
  -o "-p 5433 -c listen_addresses=127.0.0.1" -l .scratch/pg.log start
```

Redis 没装也完全能跑，因为代码是这么写的：

```python
r = await try_redis()
if r is None:
    return          # 限流旁路，请求照常放行
```

> 这是刻意设计：限流和配额是**加固手段**，不该因为它们不可用就让业务 500。

---

## 3. MySQL 能不能替换 PostgreSQL

### 3.1 先说结论

**技术上可行，但不建议为零收益付出迁移成本；如果一定要换，改动量集中在三处类型映射上，业务代码几乎不用动。**

需要先纠正一个常见误解：**换 MySQL 并不会让部署更简单**。
Docker 在这里只是个起库手段，如果嫌 Docker 麻烦，Windows 原生装 PG 和装 MySQL 的步骤**完全一样**（都是解压/安装 + `initdb` + 起服务）。换库省不掉任何东西。

### 3.2 实测数据

本机数据库里实际的列类型分布（40 张表）：

| 类型 | 列数 | 说明 |
| --- | --- | --- |
| `timestamp with time zone` | 91 | 带时区时间戳 |
| `bigint` | 82 | 主键/外键 |
| `character varying` | 58 | 普通字符串 |
| `integer` | 40 | 计数、排序 |
| **`USER-DEFINED`（PG 原生枚举）** | **38** | 37 个独立枚举类型 |
| `text` | 35 | 长文本 |
| **`uuid`** | **27** | 用户对外 ID |
| **`jsonb`** | **24** | 结构化内容（stack/learn/accept/interview/章节列表…） |
| `boolean` | 10 | |
| `date` | 6 | 打卡日期 |

37 个 PG 原生枚举：`ai_mode, career_tier, career_track, code_lang, code_std, difficulty,
direction, dl_framework, dl_module_type, exercise_source, exercise_type, favorite_target,
guide_kind, iq_difficulty, lesson_type, message_role, note_target, plan_direction,
plan_generator, plan_status, plan_type, project_category, project_difficulty, question_type,
resource_difficulty, resource_source, resource_type, submission_lang, submission_status,
sync_mode, sync_source, sync_status, task_status, task_target, theme, user_role, user_status`

### 3.3 编译对照实验结果

```
$ python scripts/dialect_compile_matrix.py
表总数: 40

=== PostgreSQL ===
  可编译 40/40 | 失败 0

=== MySQL ===
  可编译 40/40 | 失败 0

=== SQLite ===
  可编译 40/40 | 失败 0
```

**三方言都能建表**。但"能建"和"等价"是两件事，看实际生成的 DDL：

**JSONB → JSON（静默降级）**

```sql
-- PostgreSQL
done_chapters  JSONB  NOT NULL
-- MySQL
done_chapters  JSON        NOT NULL
```

`models/types.py` 里写的是 `JSON().with_variant(JSONB(), "postgresql")`，
所以**只有 PG 走 JSONB，其它方言一律走普通 JSON**。这不是错误，是设计如此。

**枚举 → 内联 ENUM**

```sql
-- PostgreSQL: 独立类型，全库共享
track  career_track  NOT NULL

-- MySQL: 内联到列定义，每个表各有一份
track  ENUM('cpp','clang','java','spring','python','fullstack',
            'database','middleware','ai','bigdata','data','fundamentals','tooling') NOT NULL
```

这是**语义差异**：PG 的 `ALTER TYPE ... ADD VALUE` 改一次全库生效；
MySQL 的表内 ENUM 要逐表 `ALTER`，且 MySQL 的 ENUM 值是**按位置**存储的。

**时间戳丢时区**

```sql
-- PostgreSQL
created_at  TIMESTAMP WITH TIME ZONE  DEFAULT now()
-- MySQL
created_at  DATETIME  DEFAULT now()
```

`DATETIME` 不存时区。这个项目有用户跨时区打卡/学习记录的语义，换成 MySQL 后
`datetime.now(UTC)` 写入、读出时**时区信息会丢**，需要应用层统一按 UTC 解释。

**`ILIKE` 自动降级（性能差异）**

```sql
-- PostgreSQL（可用 pg_trgm GIN 索引加速）
WHERE title ILIKE '%内存%'
-- MySQL（lower() 包裹，普通索引失效，必走全表扫）
WHERE lower(title) LIKE lower('%内存%')
```

代码里 `career.py` / `content.py` 有 5 处 `ilike` 搜索。功能等价，但数据量上来后
MySQL 侧会退化成全表扫描。

### 3.4 真要换 MySQL，改哪里

改动**只有一处**，因为跨方言适配已经集中收敛了：

```python
# server/app/models/types.py
JSONType = JSON().with_variant(JSONB(), "postgresql")
```

`UUIDType` 已经写了 `load_dialect_impl`，MySQL 会自动落到 `CHAR(36)`；
`Enum(...)` 已经自动落到内联 ENUM。**业务代码一行不用改**。

所以迁移成本约等于：

| 工作项 | 量级 |
| --- | --- |
| 改 `types.py` 一处 | 5 分钟 |
| `aiomysql` 驱动接进 `db.py` | 10 分钟 |
| 时间戳时区语义补丁（`DateTime(timezone=True)` → 应用层 UTC） | 半天，需逐接口验 |
| Docker compose / 部署文档改镜像 | 20 分钟 |
| 重跑 `e2e_http.py` 34 项回归 | 半天 |

**总价约 1 人日，换来的是零功能收益。** 这就是不建议换的核心理由。

### 3.5 什么情况下应该换

反向列一下，避免"一边倒"：

1. **公司/学校强制 MySQL** —— 这是唯一站得住的硬理由。
2. **需要和已有 MySQL 业务共库** —— 跨库事务在 PG 侧更麻烦。
3. **团队只会 MySQL** —— 运维熟悉度是有价值的。

如果命中任一条，按 3.4 改即可，代码架构是支持的。

### 3.6 为什么当初选的是 PG 而不是 MySQL（复盘）

诚实讲，按当前代码的实际用法，**MySQL 也完全够用** —— 没有用到 `jsonb` 的 `@>` 包含查询、
没有 GIN 索引、没有 `ARRAY` 类型、没有 `ON CONFLICT` 之外的 PG 专属语法。

选 PG 的实际理由是三条偏"防守"的：

1. **`jsonb` 先手**：24 个 JSON 列将来大概率要做"按字段筛选"（比如"难度=mid 且 方向=backend"）。
   `jsonb` 的 GIN 索引一条 `CREATE INDEX ... USING GIN` 就解决，MySQL 的 generated column + 索引要逐字段手写。
2. **原生 `uuid` 和原生 enum**：类型语义在库里表达，而不是靠应用层约定。
3. **`ILIKE` 直接可用**：中文搜索场景不用先 `lower()` 包一层。

这三条都是**将来会用、现在还没用**的能力。这是清醒的取舍，不是误判。

---

## 4. 一句话总结

- **Docker**：装了、CLI 正常、引擎起不来。根因是系统代理指向 `127.0.0.1:31181` 这个死端口 +
  `docker-desktop` 发行版 bootstrap 卡住。本项目**不依赖 Docker**，已用 Windows 原生 PG 17.2 完整跑通 34 项验收。
- **为什么用 Docker**：只是"少装两个服务"的开发便利，不是架构要求；拆掉后功能零损失。
- **MySQL 行不行**：能换，改 `types.py` 一处 + 补时区语义约 1 人日，但**换不来任何功能收益**，
  且会丢掉 `jsonb` 索引能力和时区语义。除非外部强制，否则保持 PG。
