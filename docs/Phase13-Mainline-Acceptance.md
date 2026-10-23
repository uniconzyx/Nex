# 阶段13 · 主线验收：登录、同步、后端、章节深度

> 本轮回答主线的四件事：登录界面做得如何、能否直接安装、后端是否真跑通、章节够不够完整深入。
> 所有数字都来自可复跑脚本，末尾附复跑命令。

---

## 1. 登录界面

### 1.1 做了什么

`ProfilePage` 的账号卡从"占位框"改成了**真实可用的登录/注册表单**：

- 分段切换：`登录` / `注册`（注册态多一个昵称输入框）
- 会话状态三态：`anonymous` / `online` / `offline`
- 已登录显示昵称 + `已登录 · 邮箱`
- 服务不可达时显示 `未连接服务 · 本地模式`，并提示"登录暂不可用，本地进度不受影响"
- 视觉：`.km-login-box` 去掉虚框改实底 `var(--km-sunk)`；560px 以下按钮与提示各占一行

### 1.2 验收结果（Edge headless 实测）

```
badgeBefore        : 未登录 · 本地模式
badgeAfterRegister : 已登录 · ui1792496113789@nex.dev
name               : 界面验收喵
token              : true
loginBoxClosed     : true
badgeAfterLogout   : 未登录 · 本地模式
wrongPassErr       : 账号或密码错误
mobileNavActive    : 个人闯关档案
mobileOverflow     : 0
mobileInputs       : 2
consoleErrors      : 1 条 401（错误密码用例的预期响应）
```

关键点：

- **注册 → 登录 → 昵称回显 → 退出 → 错误密码提示** 全链路走通
- 375×812 下 `overflowX = 0`，表单纵向铺开不挤压
- 唯一一条 console error 是**故意用错密码**触发的 401，属于测试预期，不是缺陷

---

## 2. 进度同步闭环

### 2.1 设计原则

写在 `frontend/src/lib/sync.ts` 的文件头：

```
1. localStorage 是事实源
2. 登录后并集合并
3. 只在确需时回推
4. 500ms 节流，失败静默
```

为什么 localStorage 是事实源而不是服务端：**用户断网时标记的章节不能丢**。
服务端做镜像，合并取并集 —— 换设备时旧记录不该被新设备的空列表抹掉。

服务端 `PUT /progress/state` 对应实现：

```python
st.done_chapters = sorted(set(st.done_chapters or []) | set(body.done_chapters))
st.done_projects = sorted(set(st.done_projects or []) | set(body.done_projects))
st.coins = max(st.coins or 0, body.coins)
st.client_rev = max(st.client_rev or 0, body.client_rev)
```

脏日期跳过而不是整批 500：

```python
for raw in body.checkins:
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        continue
```

### 2.2 验收结果

```
loggedIn           : true
hasMark            : 1
localChapters      : ["cpp-ch01"]
serverChapters     : ["cpp-ch01"]
serverCoins        : 1300
restoredChapters   : ["cpp-ch01"]
requests           : GET state → PUT state → PUT state → GET state → GET state
```

`restoredChapters` 这条是关键：**本机标记 → 服务端收到 → 退出重新登录（模拟新设备）→ 云端补回**。
这就是"换台设备进度还在"的完整链路。

`pulledAt` 1.5 秒去重的效果：登录 + 挂载 + 切页会连发三次 `pullProgress`，实际只发了一次请求。

---

## 3. 后端功能完整性

### 3.1 运行环境（不依赖 Docker）

| 组件 | 实现 | 端口 |
| --- | --- | --- |
| PostgreSQL | Windows 原生 17.2 | 5433 |
| Redis | 未安装（fail-open 降级） | — |
| FastAPI | uvicorn | 8000 |

### 3.2 验收结果：34 PASS / 0 FAIL

覆盖范围：

| 分组 | 用例数 | 代表项 |
| --- | --- | --- |
| 健康与内容 | 2 | `/health`、PG 真实查询 `courses=2` |
| 认证 | 10 | 注册重复被拒、弱密码 422、错误密码 401、伪造 token 401、refresh 换新、access 冒充 refresh 被拒 |
| 公开接口 | 5 | courses / guides / career-tracks / exercises / resources |
| 业务接口 | 8 | 进度看板、成就、错题本、计划、AI 配额、收藏、笔记 |
| 边界与校验 | 5 | 非法笔记类型 422（不再 500）、笔记读回 |
| 进度同步 | 4 | 上传、读回一致、并集不覆盖、脏日期不 500、未登录 401 |
| 路由覆盖 | 1 | OpenAPI 57 paths ≥ 40 |

两个重点回归：

```
PASS  非法笔记类型被 422 拦住（不再 500）
PASS  增量上传取并集（不覆盖）  chapters=['cpp-ch01', 'cpp-ch02', 'cpp-ch03']
```

第一条是之前 `invalid input value for enum note_target: "chapter"` 的修复验证 ——
根因是 schema 用裸 `str` 让非法值穿透到了 asyncpg，改成 `Literal[...]` 前置拦截。

---

## 4. 章节内容完整性与深度

### 4.1 结论先行

**107 / 107 章全部结构完整，深度 107 / 107 达标，缺口 0，偏浅 0。**

### 4.2 汇总数据

| 指标 | 数值 |
| --- | --- |
| 声明章节 / 磁盘章节 | 107 / 107 |
| 缺失章节 | 0 |
| 结构不全 | 0 |
| 体量中位数 | **71.0 KB** |
| 最小 / 最大 | 20.2 KB / 193.7 KB |
| 总体量 | **8.6 MB** |
| 示例中位数 | **12 个/章** |
| concept 篇数中位数 | **4 篇/章** |

### 4.3 分学科

| 学科 | 章数 | 中位体量 | 最薄 | 深度达标 |
| --- | --- | --- | --- | --- |
| tooling | 6 | 160.9 KB | 92.0 KB | 6/6 |
| database | 8 | 101.7 KB | 28.7 KB | 8/8 |
| data | 6 | 99.5 KB | 53.7 KB | 6/6 |
| fullstack | 8 | 97.8 KB | 44.3 KB | 8/8 |
| middleware | 8 | 85.4 KB | 50.1 KB | 8/8 |
| ai | 8 | 82.8 KB | 55.7 KB | 8/8 |
| fundamentals | 12 | 81.6 KB | 55.5 KB | 12/12 |
| python | 8 | 72.2 KB | 21.1 KB | 8/8 |
| bigdata | 6 | 64.7 KB | 50.1 KB | 6/6 |
| spring | 8 | 61.0 KB | 51.9 KB | 8/8 |
| java | 9 | 60.7 KB | 24.2 KB | 9/9 |
| **cpp** | 20 | **45.5 KB** | 20.2 KB | 20/20 |

### 4.4 需要关注的 7 章

| 章节 | 体量 | concept 篇 | 示例数 | 标记 | 缺口 |
| --- | --- | --- | --- | --- | --- |
| cpp-ch03 | 20.2 KB | 3 | 10 | 4 | 无 |
| cpp-ch01 | 20.7 KB | 3 | 10 | 4 | 无 |
| cpp-ch02 | 20.7 KB | 3 | 10 | 5 | 无 |
| cpp-ch04 | 21.0 KB | 3 | 10 | 2 | 无 |
| py-ch01 | 21.1 KB | 3 | 10 | 3 | 无 |
| java-ch01 | 24.2 KB | 3 | 10 | 5 | 无 |
| db-ch01 | 28.7 KB | 3 | 10 | 3 | 无 |

**这 7 章不是"没写完"，是"入门章天然篇幅小"。** 抽读 `cpp-ch03` 确认质量：

- `concept/01-c-array-vs-pointer.md` 有完整的**三视角解析**（程序员 / 博士生 / 考研者），
  讲清了 array-to-pointer decay 是**隐式转换**而非"数组就是指针"，`std::array` 把长度提升为类型的一部分，
  `std::span` 的 ABI 动机
- `pitfalls.md` 给出 4 条具体陷阱：数组传参退化、C 字符串忘 `\0`、`string_view` 悬空、下标越界无检查
- `examples/ex01-*.json` 带 `expected_output`，可被判题器直接执行验证

所以**不需要补写**。真正该注意的反而是反向问题：`cpp` 学科 20 章中位数 45.5KB，
明显低于其它学科的 60~160KB，**深度不均**是更值得关注的信号。

---

## 5. 复跑命令

```bash
# 后端 34 项全链路
cd server && python scripts/e2e_http.py

# 章节严格审计（输出 .scratch/content-audit.json）
cd server && python scripts/audit_content_depth.py

# 登录界面（需 vite 1420）
cd frontend && npm run dev &
node scripts/verify-login.cjs

# 进度同步
cd frontend && node scripts/verify-sync.cjs

# 方言对照（DB 选型，见 Phase12-DB-Choice.md）
cd server && python scripts/dialect_compile_matrix.py
```

> 前端构建注意：`vite.config.ts` 设了 `emptyOutDir: false`，
> 每次 `vite build` 前必须先删旧的 `dist/assets/index-*.js|css`，
> 否则旧哈希会累积并被一起打进 `.so`。

---

## 6. 自查：本轮发现的逻辑漏洞

1. ~~**`sync.ts` 的静态/动态导入混用**~~ **（已修复，见 §7）**
   `session.ts` 里 `import('./sync')` 是动态的，但 `App.tsx` 和 `ProfilePage.tsx` 是静态导入。
   Vite 因此警告"dynamic import will not move module into another chunk"。
   **影响**：功能正确，但拆包失效。若将来 `sync.ts` 变大，会白白拖慢首屏。

2. **登录成功后的 401 出现在 console**
   错误密码用例的 401 是预期的，但它和真实故障在 console 里长得一样。
   **建议**：验收脚本里按 URL + 状态码白名单过滤，避免下次误判。

3. **Redis 未安装时配额显示的是"不限量"**
   `check_daily_quota` 在 Redis 不可用时 `return limit`。本机开发没问题，
   但**生产环境如果 Redis 挂了，配额的防线会静默失效**。
   **建议**：生产环境用 `fail-closed`，开发环境用 `fail-open`，按 `settings.env` 分支。

4. **`cpp` 学科深度显著低于其它学科**
   20 章中位 45.5KB，对比 tooling 的 160.9KB，差 3.5 倍。
   结构上全达标，但作为主打学科，**内容密度不该是最低的**。
   **建议**：下一轮内容生产优先补 `cpp-ch05~ch13`（中位 42KB 那一段）。

---

## 7. 后续修复（2026-10-20）

### 7.1 自查项 1 已修复：sync 钩子改为注入式

原写法在两个方案上都走不通，实现时才发现是个**双输局面**：

| 方案 | 问题 |
| --- | --- |
| 保留 `void import('./sync')` | Vite 报 "dynamic import will not move module into another chunk"，拆包失效 |
| 改成顶部静态 `import { pullProgress }` | `sync.ts` 本身 `import { getSession } from './session'`，形成 **ESM 循环依赖** |

**采用的做法**：沿用 `progress.ts` 里已有的 `setProgressSyncHook` 范式——
`session.ts` 只定义注册点 `setSignedInHook(fn)`，`App.tsx`（唯一同时引用两者、
且不构成循环的模块）在挂载时接线：

```ts
// session.ts —— 只通知，不认识 sync 模块
type SignedInHook = () => void;
let onSignedIn: SignedInHook | null = null;
export function setSignedInHook(fn: SignedInHook | null): void { onSignedIn = fn; }
// login() 内：void onSignedIn?.();

// App.tsx —— 唯一接线点
setSignedInHook(() => { void pullProgress(); });
```

**验证**：

- `tsc --noEmit` 通过
- `vite build` 输出 **不再有 dynamic-import 警告**，产物 `index-JeTi65ks.js` 368.27 kB（原 369.40 kB），
  `grep __vitePreload` 为 **0**，确认动态导入已彻底消除
- `verify-sync.cjs` 全绿：本机 `cpp-ch01` → 服务端 `cpp-ch01` → 清空本机重登后
  `restoredChapters: ["cpp-ch01"]`，请求序列含 3 次 `GET /v1/progress/state`
  （第二次登录后那次正是新钩子触发）
- `verify-login.cjs` 全绿，行为与重构前完全一致

### 7.2 自查项 3 未处理：Redis fail-closed

`check_daily_quota` 在 Redis 不可用时 `return limit`（放开）。
开发环境这是对的（不装 Redis 也能用），但生产环境 Redis 挂掉时配额防线会静默失效。
**留给下一轮**：按 `settings.env` 分支，生产走 fail-closed（拒绝请求并返回 503）。

### 7.3 自查项 4 未处理：cpp 学科深度

属于内容生产工作量，不在本次修复范围。绪论：这是**本仓库唯一需要"写"而不是"改"的欠账**。
