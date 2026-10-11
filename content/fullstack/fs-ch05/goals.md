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


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Node.js 全套入门教程 | [视频](https://www.bilibili.com/video/BV1a34y167AZ/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Vue3 全家桶（张天禹） | [视频](https://www.bilibili.com/video/BV1Zy4y1K7SH/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · React 全家桶 | [视频](https://www.bilibili.com/video/BV1wy4y1D7JT/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · HTML5+CSS3 前端零基础（李立超） | [视频](https://www.bilibili.com/video/BV14J4114768/) | 本学科配套视频，建议结合本章示例与习题观看 |

## 软前置（可选，不阻断学习）
- 无。本章 `prerequisites` 仅引用本学科已完成章节 fs-ch04；SQL 语法本章从零讲到够用为止，不需要额外的数据库先修课。

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
