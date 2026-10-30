# fs-ch05 · 数据库与 REST API 设计 · 学习目标

## 学习目标
完成本章后，你能：
1. 按「一致性约束强度 / 访问模式 / schema 演进 / 水平扩展」四组判据，在关系型（PostgreSQL/MySQL）与文档型（MongoDB）之间做出可辩护的选型，并说清什么条件下结论会反转。
2. 讲清 B+ 树为何成为数据库默认索引结构（矮胖、叶链、顺序 IO、路径长度稳定），并能推出最左前缀原则与覆盖索引的判定条件。
3. 用 `EXPLAIN QUERY PLAN` 判断一条 SQL：是否走索引、是否覆盖索引、是否因最左前缀失效而退化为扫描。
4. 权衡 ORM/ODM（Prisma/TypeORM/Sequelize/Mongoose）与原生 SQL：何时用类型安全换控制力，何时必须落回 SQL。
5. 用**操作计数**识别并消除 N+1（1+N 次查询 → 1 次 JOIN/批量预加载），而不是凭代码观感判断。
6. 按 REST 约束设计资源：名词复数命名、HTTP 方法的安全/幂等语义、状态码正确用法、POST 幂等键。
7. 实现并对比 offset 分页与游标（keyset）分页，说明深分页与并发写入下为什么必须用游标。
8. 实现请求校验（类型 + 必填 + 边界 + 枚举 + 正则 + 拒绝多余字段）与统一错误响应（RFC 9457 Problem Details）。
9. 从路由表生成 OpenAPI 3.1 文档，并用可自动化的判据做契约自检（operationId 唯一、路径参数必填、4xx 统一 problem+json、$ref 可解析）。
10. 制定版本策略（URL 版本 vs 媒体类型/Header 版本）并实现令牌桶限流与分级超时预算。

## 前置
- **fs-ch04 Node.js 与后端 API**（HTTP 服务、路由表、路径变量、中间件、JSON body、状态码）——本章在其 HTTP 层之上补齐「数据层 + 接口契约 + 生命周期治理」。
## 软前置（可选，不阻断学习）
- 无。本章 `prerequisites` 仅引用本学科已完成章节 fs-ch04；SQL 语法本章从零讲到够用为止，不需要额外的数据库先修课。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [trekhleb/javascript-algorithms](https://github.com/trekhleb/javascript-algorithms) | 196,855 | 全章 | JavaScript 算法与数据结构，含英文详解；本章先读与「关系型」「ORM / ODM」相关的部分 |
| 2 | [Chalarangelo/30-seconds-of-code](https://github.com/Chalarangelo/30-seconds-of-code) | 129,352 | 全章 | 短小精悍的 JS/CSS/HTML 代码片段集，覆盖日常前端技巧；本章先读与「关系型」「ORM / ODM」相关的部分 |
| 3 | [yangshun/front-end-interview-handbook](https://github.com/yangshun/front-end-interview-handbook) | 44,008 | 全章 | 前端面试手册：HTML/CSS/JS/浏览器/性能；本章先读与「关系型」「ORM / ODM」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · JavaScript 基础与实战<br><sub>尚硅谷</sub> | [BV1YW411T7GX](https://www.bilibili.com/video/BV1YW411T7GX/) | 全章 | 主线：语法与类型 → 函数与作用域 → 原型与 this → DOM/BOM → ES6+ → 异步与 Promise；看完回 `ex01`（RESTful 资源命名、HTTP 方法）核对 |
| 2 | 黑马程序员 · React 零基础到实战<br><sub>黑马程序员</sub> | [BV1gh411U7JD](https://www.bilibili.com/video/BV1gh411U7JD/) | 全章 | 组件与 props/state、Hooks 的依赖数组、路由与状态管理，最后落到一个完整项目；看完回 `ex02`（真实可跑的迷你 REST 服务（node）核对 |
| 3 | HTML + CSS + JS + Vue 前端全套<br><sub>web前端自学官方</sub> | [BV1jj411P7Yp](https://www.bilibili.com/video/BV1jj411P7Yp/) | 全章 | 补页面那一层：盒模型、Flex/Grid 布局、响应式；做「能看的界面」时按需查；看完回 `ex03`（分页实现对比）核对 |
| 4 | 黑马程序员 · AJAX + Node.js + webpack<br><sub>黑马程序员</sub> | [BV1MN411y7pw](https://www.bilibili.com/video/BV1MN411y7pw/) | 全章 | 前后端怎么接上：HTTP 请求、跨域、接口约定、打包构建；看完回 `ex04`（查询参数（sort/过滤/分页）解析 +）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《JavaScript 高级程序设计（第 4 版）》Zakas |
| 2 | 《深入浅出 Node.js》朴灵 |
| 3 | 《CSS 世界》张鑫旭 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。

## 真题依据（真实可查，仅存元数据）
- GitHub 资源（见 `_manifest.json`）：trekhleb/javascript-algorithms（196855★）、Chalarangelo/30-seconds-of-code（129326★）、yangshun/front-end-interview-handbook（44008★）。
- LeetCode 题仅存元数据与链接，不搬运题面正文，详见 `exercises.json`。
- 规范原文：RFC 9457（Problem Details for HTTP APIs）、RFC 9110（HTTP Semantics）、OpenAPI Specification 3.1.0。

## 验收标准
- 给定业务描述与访问模式，能给出选型结论并至少写出两条反例（什么情况下结论会反转）。
- 给定表结构与一条 SQL，能读出查询计划并指出：走没走索引、是否覆盖、是否最左前缀失效（本章示例均给真实计划串）。
- 给定一段 ORM 查询代码，能判定是否 N+1，并用操作计数验证修复效果（1+N → 1）。
- 给定一个资源，能写出完整 REST 接口表：方法 / 路径 / 成功码 / 失败码 / 是否幂等。
- 给定并发写入场景，能说明 offset 分页为何重复行、游标分页为何稳定，并用实跑结果佐证。
- 能对同一份请求体给出合法与非法两组校验结果，并输出符合 RFC 9457 的错误体。
