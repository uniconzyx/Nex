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


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Node.js 全套入门教程 | [视频](https://www.bilibili.com/video/BV1a34y167AZ/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Vue3 全家桶（张天禹） | [视频](https://www.bilibili.com/video/BV1Zy4y1K7SH/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · React 全家桶 | [视频](https://www.bilibili.com/video/BV1wy4y1D7JT/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · HTML5+CSS3 前端零基础（李立超） | [视频](https://www.bilibili.com/video/BV14J4114768/) | 本学科配套视频，建议结合本章示例与习题观看 |

## 软前置（可选，不阻断学习）
- 无。本章 `prerequisites` 仅引用本学科已完成章节 fs-ch04、fs-ch05；密码学背景本章从零讲到够用，不要求额外的密码学先修。

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
