# Phase 10 · 就业级项目库 / 考研笔记 / 学科切换

本阶段解决三件事：项目库从「每学科 3 个」铺成按能力梯度分层的完整链路；把 11408 仓库的笔记与经验贴接成独立导航；把「当前学科」提升为跨页面的全局状态。

---

## 1. 项目库：13 学科 × 4 梯度 = 110 个项目

### 1.1 分层口径

| 梯度 | 名字 | 工时带 | 判断标准 | 典型产出 |
|---|---|---|---|---|
| T1 | 入门 · 能跑起来 | 4–12h | 跑通主流程，能改一处小功能 | 本地截图 + 主流程图 |
| T2 | 进阶 · 能独立写 | 12–30h | 脱教程实现同构小系统 | 可运行最小实现 + 3 个自测 |
| T3 | 核心 · 能讲清原理 | 30–60h | 读源码画链路，做改造或压测 | 架构图 + PR 级 diff + 数据表 |
| T4 | 门槛 · 能写进简历 | 60–120h | 生产级复杂度，有可量化结果 | QPS/P99/准确率/成本曲线 |

梯度不是难度标签，而是**产出要求**：T2 与 T3 的差别不是「代码更难」，而是「有没有自己产生的数据」。

### 1.2 覆盖现状

| 学科 | 项目 | T1 | T2 | T3 | T4 | 工时 |
|---|--:|--:|--:|--:|--:|--:|
| C 语言 | 7 | 2 | 2 | 2 | 1 | 234h |
| C / C++ | 10 | 2 | 3 | 3 | 2 | 391h |
| Java | 10 | 3 | 3 | 2 | 2 | 354h |
| Spring 生态 | 9 | 2 | 3 | 2 | 2 | 341h |
| Python | 9 | 2 | 3 | 2 | 2 | 326h |
| 全栈开发 | 10 | 2 | 3 | 3 | 2 | 391h |
| 数据库 | 8 | 2 | 2 | 2 | 2 | 330h |
| 中间件 | 8 | 2 | 2 | 2 | 2 | 326h |
| AI / Agent | 12 | 2 | 4 | 3 | 3 | 506h |
| 大数据 | 8 | 2 | 2 | 2 | 2 | 324h |
| 数据分析 | 8 | 2 | 3 | 2 | 1 | 256h |
| 计算机基础 | 6 | 2 | 2 | 2 | 0 | 155h |
| 工具链 | 5 | 2 | 2 | 1 | 0 | 96h |
| **合计** | **110** | **27** | **34** | **28** | **21** | **4030h** |

计算机基础与工具链按规划不设 T4（这两科的项目很难产出独立的量化指标，硬凑会变成假项目）。其余 11 科都有 T4。

### 1.3 数据流（为什么分片）

```
content/_projects/career/<track>.json     人工撰写：summary / learn / steps / accept / interview
        │
        ├── .scratch/gh_discover/*.json   GitHub 实测元数据（stars / license / pushed / language）
        │                                 由 gh_discover.py + verify_extra.py 产出，不手抄
        ▼
scripts/build_career_library.py            合并 + 校验（slug 唯一、梯度覆盖、元数据齐备）
        ▼
content/_projects/career-projects.json     生成物，勿手改
        ▼
scripts/seed_career_projects.py            写 career_projects / career_project_steps / career_routes
```

- `scripts/merge_career_pieces.py`：把增量 JSON 按 slug 幂等合并进分片（跳过已存在，不覆盖人工修改）。
- 校验会拦住三类错误：slug 重复、仓库不在检索结果里、规划要的梯度缺失。

### 1.4 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/career-tracks` | 学科 + 项目数，供筛选条与学科切换器使用 |
| GET | `/api/v1/career-routes` | 6 条岗位路线：要求哪些学科的哪些梯度 |
| GET | `/api/v1/career-coverage` | 学科 × 梯度的供给与工时（回答「要练多少」） |
| GET | `/api/v1/career-projects` | 列表：`track` / `tier` / `level` / `q` / `sort=default\|stars\|level\|recent\|tier` |
| GET | `/api/v1/career-projects/{slug}` | 详情：learn / career_value / accept / interview / steps（含打卡状态） |
| POST | `/api/v1/career-steps/{id}/complete` | 步骤打卡 |

`tier` 排序直接用数据库枚举顺序（PG 枚举按声明顺序比较，正好 t1→t4）。

---

## 2. 考研笔记导航（11408）

### 2.1 为什么不搬正文

该仓库 408 笔记单篇最大 44MB，且依赖同目录 `assets` 图片。整篇入库：
1. 超出接口与数据库合理体积；
2. 图片相对路径会断，读者看到一堆破图；
3. 原作者更新后我方副本立刻过期。

因此只做**索引 + 要点提炼 + 原文跳转**。每条的 `points` 是改写后的可扫读要点，结论与原意一致，不改变作者判断。

### 2.2 结构

- 来源（`guide_sources`）：仓库元信息 + 学科分面（`subjects` JSONB 存中文名，全站只维护一份）。
- 条目（`guide_items`）：`kind` 三态 —— `note` 笔记 / `experience` 经验贴 / `external` 外部文档（幕布等）。
- 当前 18 条：笔记 10、经验贴 6、外链 2。

### 2.3 API 与页面

- `GET /api/v1/guides`：来源列表 + 各形态条数。
- `GET /api/v1/guides/{source_key}?subject=&kind=`：学科分面按全量算（不受当前筛选影响，否则切一次学科导航就塌了）。
- 前端 `GuidesPage`：左侧形态竖条区分（蓝=笔记 / 琥珀=经验贴 / 灰虚线=外链），默认只显示 2 条要点，可展开。

---

## 3. 学科切换：从「一排胶囊」到全局状态

### 3.1 原来的问题

1. 13 个学科只在项目页排一行胶囊，切走再切回状态丢失；
2. 顶栏没有「我在学什么」的概念，学习页写死 C++；
3. 窄屏上 13 个胶囊铺成四行，把正文顶到首屏之外；
4. 空态只说「没有匹配项目」，不说为什么、也不给出口。

### 3.2 现在的模型

- `lib/subject.ts`：模块级 store（不包 Provider），`useSubject()` 订阅，写 `localStorage["nex.subject"]`，刷新仍在原学科。
- `components/SubjectSwitch.tsx`：顶栏切换器，两列面板，13 项各带项目数，Esc / 点外部关闭。
- 页面归属：
  - **首页 / 学习 / 项目**：显示切换器，内容跟随（学习页标题与文案随学科变化）；
  - **笔记**：不显示 —— 考研科目（数学/408/英语/政治）与 13 个就业学科不是同一套分类，共用会串味；
  - **练习**：不显示 —— 判题台当前只接 C / C++ / Python / Java 四种语言，按学科切换没有意义。
- 项目页双向同步：顶栏切换 → 列表跟随；点学科胶囊 → 同时写全局学科。
- 「全部学科」是**本页筛选**，不改变全局学科（刷新后仍回到原学科），两排胶囊前置了「筛选 / 梯度」标签以区分层级。
- 窄屏：两排胶囊改横向滚动单行，纵向空间从 7 行压到 2 行。
- 空态给出口：清除梯度 / 看全部学科 / 清除关键词。

---

## 4. 自查（逻辑漏洞与未验证项）

### 4.1 已修的真实缺陷

| 问题 | 表现 | 处理 |
|---|---|---|
| `career.py` 漏 import | `CareerRoute` / `ProjectTier` 未定义，路由导入即 NameError，服务起不来 | 补齐 import，定义 `TIER_LABEL` / `_track_label` |
| 模型缺列 | API 用 `p.tier` / `p.hours`，表里没有这两列 | `CareerProject` 增 `tier`（`CAREER_TIER` 单例）与 `hours` |
| 种子脚本半成品 | `PLAN` / `route_new` 未定义，tier/hours 未写入 | 重写为项目 + 路线双 upsert，补齐字段 |
| `sort=tier` KeyError | 排序字典缺 `tier` 键 | 用枚举顺序 `CareerProject.tier.asc()` |
| 构建产物缺 `tracks` | 测试按 `doc["tracks"]` 断言，生成物没有该键 | 构建时输出实际覆盖的学科列表 |
| `gothinkster/realworld` 422 | 仓库已迁移到 `realworld-apps/realworld` | 改仓名并重新实测（★84.3k） |
| 卡片重复标学科 | 已按学科筛选时，每张卡还标一遍学科 | 有筛选时隐藏 track 徽标 |

### 4.2 口径上的取舍

- 110 条中 21 条 T4，够支撑「至少 2 个 T4 带量化数据」的毕业门槛，但**不代表做完 110 个才能投实习**：路线要求的学科达到 `track_pass` 即具备基本盘。
- 工时是个人估算的期望值，不是下限；T4 的 60–120h 差异取决于是否已有相关基础。
- 笔记页的 `read_min` 是读要点的时间，不是读原文的时间。

### 4.3 未验证项（明确留白）

1. **数据库实机未跑**：本机 Docker 守护进程未启动，`init_db` / `seed_career_projects` / `seed_guides` 只做了 `--dry-run` 与 DDL 编译校验；真实 PG 上的建表、upsert、枚举单例需有 Docker 时补一次。
2. **UI 验收用的是 mock 服务**：因为 1 的原因，前端截图里的数据来自 `content/` 直读的 mock（响应结构与 FastAPI 一致），不是真库。接口层用 openapi 路径 + 单测覆盖。
3. `career-coverage` 的页面消费尚未接入（接口已就绪），T4 数量目前要在列表筛选里数。

---

## 5. 复现步骤

```bash
# 1) 合并增量并构建项目库
cd server
python -m scripts.merge_career_pieces "../../.scratch/add_*.json"
python -m scripts.build_career_library --check
python -m scripts.build_career_library

# 2) 校验内容
python -m scripts.seed_career_projects --dry-run
python -m scripts.seed_guides --dry-run

# 3) 有数据库时写库
python -m scripts.init_db
python -m scripts.seed_career_projects
python -m scripts.seed_guides

# 4) 测试与前端构建
python -m pytest -q
cd ../frontend && npm run build
```

本阶段测试：`51 passed`（新增梯度覆盖、指南内容合规、路由可导入、DDL 四组用例）。
前端：`tsc --noEmit` 0 error，`vite build` 通过（CSS 20.3 KB / JS 185.9 KB）。

## 6. 桌面端设计稿：项目库嵌进「凯喵Code试炼录」

**问题**：`web-preview/kaimao-desktop.html`（凯喵Code试炼录设计稿）和 `frontend/`（React 工程壳）是两套界面，
项目库只在 React 侧存在，设计稿里的「BOSS项目实战」还是 3 条静态占位。

**处理**：不改设计稿的外壳（窗口三栏、导航分组、右侧凯喵伙伴、经验条、其余 13 个视图一律不动），
只把「BOSS项目实战」这一页的内容换成完整的就业级项目库。

- 数据：`web-preview/assets/career-data.js`，由 `python web-preview/kaimao_career_data.py`
  从 `content/_projects/career-projects.json` 生成（设计稿是 `file://` 直开，不能 fetch，所以打成 JS 全局量）。
- 页面结构：概览卡（学科/项目/工时/T4 计数 + 已通关环形进度）→ 检索与筛选卡（关键词、13 学科、T1–T4）
  → 结果条（计数 + 推荐/星标/工时排序）→ 双列项目卡 → 口径说明。
- 详情弹窗：一句话定位、为什么练这个、学习目标、落地步骤、验收标准、面试落点 + 打开仓库 / 标记已通关。
- 通关状态存 `localStorage["kaimao.projects.done"]`，只影响环形进度与卡片勾选，不写库。
- 卡片与弹窗沿用设计稿现有令牌（`--accent` / `--surf-*` / `--ink-*`），明暗主题都验证过。

**自查**：
- 导航文案与徽标保持原样（曾试过给 BOSS 加 110 徽标，会把 6 个字的标签挤成两行，已回退）。
- 首页「继续闯关」后的内容保持原样，没加任何入口卡，避免改动布局。
- 110 个项目全部渲染；按学科筛 AI 得 12 条、T4 得 21 条、搜 redis 得 8 条，与数据一致。
- 弹窗底部操作条 `position:sticky`，长内容滚动时不会把「打开仓库 / 标记已通关」顶出视口。
