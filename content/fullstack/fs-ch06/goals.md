# fs-ch06 · 用户认证 / JWT / 鉴权 · 学习目标

## 学习目标
完成本章后，你能：
1. 说清**认证（Authentication）**与**鉴权（Authorization）**的区别，并把失败映射到正确状态码（401 未认证 / 403 已认证但无权），而不是一律 401。
2. 对比 **Session + Cookie** 与 **Token（JWT）** 两套凭证方案：状态放在哪、能否主动撤销、如何水平扩展，并给出可辩护的选型判据。
3. 手工构造并解析 JWT 三段结构 `base64url(header).base64url(payload).base64url(signature)`，说明 base64url 与标准 base64 的差异，以及「base64 是编码不是加密」。
4. 用标准库（Node `crypto` / Python `hmac`）实现 HS256 的签发与验签，并写出上线前的校验清单：alg 白名单、常量时间比较、`exp`/`nbf`/`aud`/`iss` 全验。
5. 复现 **`alg: none` 攻击**与 **RS256→HS256 算法混淆**，说明为什么 alg 必须由服务端钉死、绝不能读 token 头。
6. 说明 JWT **无法主动失效**这一固有缺陷，并用「短 TTL access + Refresh 轮换（含复用检测）+ jti 黑名单」三件套缓解。
7. 用 **bcrypt/scrypt/argon2**（或 PBKDF2）加盐 + 可调成本存密码，说清为什么绝不能用 MD5/SHA1，以及为什么比较必须常量时间。
8. 实现**认证中间件 → 授权中间件 → 资源级校验**的链路，用 RBAC（含 `own` 归属）判定权限，识别水平/垂直越权（IDOR/BOLA）。
9. 概述 **OAuth2 授权码流程 + PKCE（S256）** 如何保护公开客户端，以及 `state` 如何防 CSRF。
10. 说明 **CSRF**（SameSite + Double-Submit Token）与 **XSS**（HttpOnly、CSP）的防护边界，并列出常见认证漏洞（越权、硬编码密钥、token 泄露）。

## 前置
- **fs-ch04 Node.js 与后端 API**（HTTP 服务、路由、中间件、JSON body、状态码）——本章的鉴权链直接建立在其中间件模型之上。
- **fs-ch05 数据库与 REST API 设计**（用户/会话表、持久化、统一错误契约、401/403 语义）——本章把「存谁」变成「谁能做什么」。
## 软前置（可选，不阻断学习）
- 无。本章 `prerequisites` 仅引用本学科已完成章节 fs-ch04、fs-ch05；密码学背景本章从零讲到够用，不要求额外的密码学先修。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [trekhleb/javascript-algorithms](https://github.com/trekhleb/javascript-algorithms) | 196,715 | 全章 | JavaScript 算法与数据结构，含英文详解；本章先读与「JWT 三段结构与签名算法」「校验清单与 alg」相关的部分 |
| 2 | [Chalarangelo/30-seconds-of-code](https://github.com/Chalarangelo/30-seconds-of-code) | 129,384 | 全章 | 短小精悍的 JS/CSS/HTML 代码片段集，覆盖日常前端技巧；本章先读与「JWT 三段结构与签名算法」「校验清单与 alg」相关的部分 |
| 3 | [yangshun/front-end-interview-handbook](https://github.com/yangshun/front-end-interview-handbook) | 44,006 | 全章 | 前端面试手册：HTML/CSS/JS/浏览器/性能；本章先读与「JWT 三段结构与签名算法」「校验清单与 alg」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · JavaScript 基础与实战<br><sub>尚硅谷</sub> | [BV1YW411T7GX](https://www.bilibili.com/video/BV1YW411T7GX/) | 全章 | 主线：语法与类型 → 函数与作用域 → 原型与 this → DOM/BOM → ES6+ → 异步与 Promise；看完回 `ex01`（JWT 三段结构与 base64url ）核对 |
| 2 | 黑马程序员 · React 零基础到实战<br><sub>黑马程序员</sub> | [BV1gh411U7JD](https://www.bilibili.com/video/BV1gh411U7JD/) | 全章 | 组件与 props/state、Hooks 的依赖数组、路由与状态管理，最后落到一个完整项目；看完回 `ex02`（Python 标准库实现 HS256 签）核对 |
| 3 | HTML + CSS + JS + Vue 前端全套<br><sub>web前端自学官方</sub> | [BV1jj411P7Yp](https://www.bilibili.com/video/BV1jj411P7Yp/) | 全章 | 补页面那一层：盒模型、Flex/Grid 布局、响应式；做「能看的界面」时按需查；看完回 `ex03`（Node crypto.createHm）核对 |
| 4 | 黑马程序员 · AJAX + Node.js + webpack<br><sub>黑马程序员</sub> | [BV1MN411y7pw](https://www.bilibili.com/video/BV1MN411y7pw/) | 全章 | 前后端怎么接上：HTTP 请求、跨域、接口约定、打包构建；看完回 `ex04`（反例组）核对 |

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
- GitHub 资源（见 `_manifest.json`）：trekhleb/javascript-algorithms（196855★）、Chalarangelo/30-seconds-of-code（129326★）、yangshun/front-end-interview-handbook（44008★）。本章算法题引用 `src/algorithms/cryptography/caesar-cipher`（用于说明古典密码为何不安全）。
- 规范原文：RFC 7519（JWT）、RFC 7515（JWS）、RFC 7636（PKCE）、RFC 6749（OAuth2）、OWASP API Security Top 10（BOLA/IDOR）。
- LeetCode 题仅存元数据与链接，不搬运题面正文，详见 `exercises.json`。

## 验收标准
- 给定一个 JWT，能手工解出 header/payload、数出段数、判断其内容是否可被任意人读取。
- 给定一个「只验签名」的校验函数，能补全 `exp`/`nbf`/`aud`/`iss` 校验，并构造出至少三组被拒用例。
- 能复现 `alg: none` 与算法混淆两组攻击，并说明钉死 alg 后为何被拒（本章 ex05 输出布尔判据）。
- 能实现 Refresh 轮换，并用「重放旧 refresh」验证整族吊销（ex07）。
- 给定密码校验场景，能给出**加盐 + 成本 + 常量时间比较**三要素并用正反用例验证（ex09/ex10）。
- 给定接口与资源，能写出鉴权链并覆盖 401 / 403 / 200 三种结果，指出 IDOR 的修复点（ex11/ex12）。
- 能写出 OAuth2 授权码 + PKCE 的关键校验点（`state`、`code_verifier`、仅接受 S256），并用 RFC 7636 官方向量核对 `code_challenge`（ex14）。
