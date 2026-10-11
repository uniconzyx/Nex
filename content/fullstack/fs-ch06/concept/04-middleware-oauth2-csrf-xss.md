# fs-ch06 · 四、中间件鉴权与权限模型；OAuth2、CSRF/XSS 与常见漏洞

## 一、中间件鉴权链与 RBAC / ABAC

鉴权是一个**链式职责**：每个中间件要么判定通过（返回空），要么短路返回一个响应（401/403）：

```
authenticate(ctx)             -> 无/坏凭证: 401, 并把 ctx.user 挂上
authorize("article:write")    -> 已认证但无权: 403
resourceGuard(ctx, article)   -> 不是你的资源: 404（隐藏存在性）
handler(ctx)                  -> 200
```

**RBAC** 把「主体 → 权限」压缩成「主体 → 角色 → 权限」；**ABAC** 直接在属性（主体/资源/环境）上求值，表意更强但策略更复杂。工程里常见的是二者混合：RBAC 定粗粒度角色，`own` 后缀把「资源归属」这一 ABAC 属性引进来。

### 🧑‍💻 程序员视角
- 链的顺序不能错：**先认证后授权**。先判权限再验凭证，会得到「无凭证也返回 403」这类信息泄漏。
- RBAC 判定写成**纯函数**（ex12 的 `can(actor, action, resource)`）：输入角色、动作、资源，输出布尔——这样权限逻辑可以单元测试、可以审计，而不是散落在各 handler 里的 `if`。
- `own` 归属判定是防水平越权的关键：编辑者能 `article:write`（改任意文章），但只能 `article:delete:own`（删自己的）——ex12 中 `editor_delete_others=false`、`editor_delete_own=true`。
- **默认拒绝**：未知角色、未知 action 一律 `false`（ex12 `unknown_role got=false`）。白名单，不是黑名单。
- 越权两类：**水平越权**（同级用户互相访问，即 IDOR/BOLA，OWASP API #1）、**垂直越权**（普通用户访问管理员功能）。防法是「接口级鉴权 + 资源级归属校验」双管齐下。

### 🎓 博士生视角
- RBAC 的价值是把权限管理规模从 O(用户×资源) 降到 O(角色×权限)，代价是**角色爆炸**（role explosion）与「最小权限」难以精细落地。
- ABAC 直接在 `(subject, resource, action, environment)` 属性上求值（策略是谓词），表达力最强；代价是策略集的**可判定性与一致性**成为核心难题（策略冲突消解、策略组合代数、策略可达性分析）。这是访问控制从 RBAC 走向 ABAC 的理论代价。
- 二者都能表达成「访问控制矩阵」：RBAC 的矩阵由角色-权限表**显式**生成（可枚举、可审计）；ABAC 的矩阵是**隐式**的、由属性动态求值得到（无法预先枚举，只能按需判定）。ex12 的 `can()` 同时体现了两者：角色级权限是 RBAC，`ownerId === actor.id` 是 ABAC。

### 📚 考研者视角
- **面试考点**：RBAC / ABAC 区别的标准答——RBAC 基于角色（粗粒度、易管理、可能角色爆炸）；ABAC 基于属性（细粒度、动态、策略复杂）。工程上常混用。
- **常考漏洞**：越权。水平越权 = 同级用户互访问（IDOR / BOLA）；垂直越权 = 普通用户触达管理员能力。
- **易混点**：401 / 403 / 404 的选择。对「无权访问且不想暴露存在性」的资源，工程上常返回 **404 而非 403**，以免通过状态码枚举出资源是否存在。
- **延伸**：最小权限原则、职责分离（SoD）、以及「默认拒绝」作为安全设计公理。

## 二、OAuth2 授权码 + PKCE，CSRF/XSS 与常见漏洞

OAuth2（RFC 6749）是**授权**框架，不是认证协议。授权码流程（第三方登录骨架）：

```
客户端 --重定向--> 授权服务器  (带 client_id, redirect_uri, state, code_challenge)
用户登录并授权
授权服务器 --回调--> 客户端   (带 code, state)
客户端后端 --POST code + code_verifier--> 授权服务器换取 access_token
```

公开客户端（SPA / 移动端）无法安全保存 `client_secret`，因此必须加 **PKCE**（RFC 7636）：先发 `code_challenge = base64url(SHA256(code_verifier))`，换 token 时带 `code_verifier` 让服务端重算比对——即使 `code` 被截获也无法兑换。

### 🧑‍💻 程序员视角
- PKCE 的三步：客户端生成随机 `code_verifier` → 授权请求带 `code_challenge=S256(verifier)` 与 `code_challenge_method=S256` → token 端点带 `verifier`。ex14 用 RFC 7636 附录 B 官方向量：verifier `dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk` → challenge `E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM`。
- `state` 必须校验：授权请求下发随机 `state`，回调原样比对（ex14 `state_ok=true` / `state_tampered_ok=false`）。不校 `state` = 给「授权码注入 + CSRF」开门。
- 只接受 `S256`，拒绝 `plain`（ex14 `exchange_plain_rejected`）——`plain` 等于没有 PKCE。
- **CSRF 防护**（ex13）：Cookie 设 `SameSite=Lax/Strict` 让跨站请求不自动带会话 Cookie（`strict/lax_blocks_cross_site_post=true`）；对状态变更请求再加 Double-Submit Token 校验。ex13 演示了真实漏洞场景：`SameSite=None` 且不校 token → 跨站 POST 直接 `status=200`。
- **XSS 防护**：输出按上下文编码 + 部署 CSP；会话凭证放 `HttpOnly` Cookie 让 JS 读不到。但注意 XSS 仍可「代用户发请求」，所以 CSRF token 不能省。
- 漏洞清单：越权 IDOR、JWT 硬编码/弱密钥、token 泄露（写进 URL / 日志 / `localStorage`）、开放重定向（`redirect_uri` 不校验白名单）、不校 `state`。

### 🎓 博士生视角
- PKCE 解决的是「公开客户端无法安全持有 `client_secret`」这一信任问题：把一次性随机数（`verifier`）与授权码绑定。攻击者即使截获 `code`，没有 `verifier` 也换不到 token（ex14 `pkce_blocks_code_interception=true`）。本质是把「凭证保密」**替换为**「一次性绑定 + 哈希承诺」——用计算假设替代保管假设。
- OAuth2 是**授权**框架而非**认证**协议：`access_token` 是给资源服务器用的「访问票据」，不是身份凭证。补上认证语义的是 **OpenID Connect**（在其上加 `id_token`，一个 JWT）。把 OAuth2 当登录直接用是经典误用，会引入「access_token 注入」等问题。
- CSRF 的根因是**浏览器自动携带凭证**这一隐式授权模型；SameSite 与 CSRF Token 分别从「凭证携带策略」和「请求来源证明」两个维度切断攻击链。XSS 的根因是「用户输入被当作代码执行」，防御靠**上下文相关的输出编码** + **CSP 收缩信任边界**（禁止内联脚本、限制 `script-src`）。

### 📚 考研者视角
- **面试考点**：OAuth2 四种授权模式（授权码 / 隐式 / 密码 / 客户端凭证）各自适用场景；以及「为何 PKCE 在 SPA / 移动端必需」（公开客户端无法保 `client_secret`）。
- **常考对比**：OAuth2（授权）vs OIDC（认证）；Session-Cookie 体系怕 CSRF、纯 Token 体系怕 XSS——两套威胁模型要分清。
- **易混点**：OIDC 的 `id_token`（JWT）用于**认证**；`access_token` 用于**访问资源**。用 `access_token` 当身份凭证是常见错误。
- **安全考点**：SameSite Cookie 三取值语义（`Strict` / `Lax` / `None`+`Secure`）是高频题干；`HttpOnly` 防 XSS 窃取、CSRF Token 防 CSRF 是两条独立的防线。

## 三视角小结
| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| 中间件与权限模型 | 认证→授权→资源级；RBAC 纯函数；默认拒绝 | RBAC⊂ABAC；显式矩阵 vs 隐式求值 | 水平/垂直越权；403 或 404 的选择 |
| OAuth2 / CSRF / XSS | PKCE 三步；校 state；SameSite + token；CSP | PKCE 用承诺替代保管；OAuth2≠认证 | 四模式 + PKCE；OIDC 与 access_token 区别 |
