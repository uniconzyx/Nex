# 04 · 一次请求的完整链路：DNS、TCP、TLS、渲染与 CORS

## 一、理论根基：为什么必须知道「整条链路」

「输入 URL 到页面展示」之所以是经典面试题，是因为它**强制你把网络、操作系统、浏览器、后端串成一条线**。任何一段不清楚，都会在排查问题（慢？错？跨域？）时抓瞎。

**分层思维**：链路可以按「谁负责」切分——

| 阶段 | 负责方 | 典型耗时量级 |
|---|---|---|
| URL 解析 | 浏览器 | 微秒级 |
| DNS 解析 | 操作系统 + DNS 服务器 | 0–100ms（有缓存则近 0） |
| TCP 三次握手 | 内核 | 1 个 RTT |
| TLS 握手 | 浏览器 + 服务端 | 1–2 个 RTT |
| 发送请求 + 服务端处理 | 网络 + 后端 | 取决于业务（TTFB） |
| 下载响应 | 网络 | 取决于体积/带宽 |
| 解析/布局/绘制/合成 | 浏览器渲染引擎 | 取决于 DOM/CSS 复杂度 |

**优化要按量级下手**：DNS/TCP/TLS 是「固定成本」，靠**连接复用（Keep-Alive）、HTTP/2 多路复用、预连接（preconnect）、预热 DNS（dns-prefetch）**摊薄；业务处理是变量，靠缓存与索引；渲染靠减少 DOM 与重排。

## 二、实现机制

### DNS 与连接
- 浏览器 → 系统 DNS 缓存 → hosts → 本地 DNS 服务器（递归查询：根 → 顶级域 → 权威）；
- 拿到 IP 后建立 TCP 连接（三次握手）；HTTPS 再做 TLS 握手（证书校验 + 密钥协商，TLS 1.3 可 1-RTT、会话恢复下 0-RTT）。

### 排队与并发
- 浏览器对**同源**请求有限制并发（HTTP/1.1 通常 6 条连接/域名）；
- **域名分片（domain sharding）**曾用于突破此限制，但 HTTP/2 后已**反模式**（多连接反而削弱多路复用与头部压缩的收益）。

### 同源策略与 CORS

**同源** = 协议 + 域名 + 端口三者完全一致。

浏览器出于安全（防止 A 站点偷读 B 站点的数据）实施**同源策略**：跨源请求可以**发出**，但**响应被浏览器拦截**（除非服务端明确允许）。

**简单请求**（不触发预检）：方法是 `GET/HEAD/POST`，且头部仅限安全列表（`Accept`、`Accept-Language`、`Content-Language`、`Content-Type` 限三值），则直接发请求，浏览器检查响应头里的 `Access-Control-Allow-Origin`。

**预检请求（Preflight）**：不满足上述条件时，浏览器**先发 `OPTIONS`**：
```text
OPTIONS /api/data HTTP/1.1
Origin: https://app.example.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: authorization, content-type
```
服务端必须回答：
```text
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: authorization, content-type
Access-Control-Max-Age: 86400
Access-Control-Allow-Credentials: true      # 携带 Cookie 时必须
```

**关键点**：`Access-Control-Allow-Origin` **不能同时为 `*` 和携带凭证**（`Allow-Credentials: true` 时必须是具体源）。

## 三、工程实践

- **CORS 只能在服务端解决**：它是**响应头**机制，前端加什么头都没用（前端只能「不触发预检」或走代理）。开发期常用**开发服务器代理**（Vite/Webpack devServer proxy）把跨域变成同源。
- **`Allow-Credentials` + 具体 Origin**：需要 Cookie 时，服务端必须回显具体 Origin（不能 `*`），且前端要 `credentials: 'include'`。
- **预检缓存**：`Access-Control-Max-Age` 让预检结果被缓存，避免每个请求都多一次 OPTIONS 往返（默认值各浏览器不同，常配 86400）。
- **性能清单**：`dns-prefetch` / `preconnect` / `preload` 关键资源 / 压缩（gzip/br）/ HTTP/2 或 3 / CDN / 减少重定向链。
- **调试清单（Network 面板）**：看 **Timing** 分段（DNS/TCP/TLS/TTFB/Content Download）定位是「网络慢」还是「后端慢」——TTFB 高 → 后端；Content Download 高 → 体积/带宽；Stalled/Queueing 高 → 并发受限。

## 四、边界与陷阱

- **「跨域请求失败」有两层原因**：可能是**浏览器拦截**（CORS 头不全，请求已到服务端且服务端日志能看到）、也可能是**根本没发出去**（预检失败）。看 Network 面板里是否出现两条（OPTIONS + 实际请求）即可区分。
- **`Access-Control-Allow-Origin: *` 与凭证互斥**：需要 Cookie 时必须回显具体 Origin。
- **HTTPS 页面请求 HTTP 资源会被**：混合内容（mixed content）拦截（主动内容直接阻断）。
- **重定向会重新触发预检/重新计算缓存**：301/302 链路越长，耗时越不可控。
- **`Origin` 头部由浏览器注入且不可伪造（脚本无法设置）**：服务端用它做 CORS 判断是可靠的，但**不能**用它做认证（非浏览器客户端可以随便写）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **定位慢请求的口诀**：先在 Network → Timing 看分段——**TTFB 高 = 后端慢**（查 SQL/依赖），**Content Download 高 = 体积大**（查压缩/图片），**Stalled 高 = 并发或连接复用问题**（查同源并发与 Keep-Alive）。比盲目加机器有效得多。
- **跨域排查顺序**：① 是不是简单请求？（是 → 只查 `Allow-Origin`）② 预检出现了吗？（没有 → 请求被更早的地方挡了）③ 服务端有没有回 `Allow-Methods/Headers`？④ 要带 Cookie 吗？（要 → 必须具体 Origin + `Allow-Credentials`）。
- 落地建议：开发环境统一用**代理**（同源）避免 CORS 噪音；生产环境用**网关统一注入 CORS 头**，避免每个服务各写一套还写错。

### 🎓 博士生视角
- 同源策略是**浏览器的安全边界**，属于「**最小权限 + 隔离**」思想在 Web 上的落地：默认不信任跨源数据，跨源访问必须**显式授权**（CORS 就是授权协商协议）。它保护的是「用户的浏览器」，而非服务端——理解这一点就不会误以为「服务端加了 CORS 就安全了」。
- 「输入 URL 到展示」这条链路的每段都对应独立的**可优化维度**：DNS 是分布式系统问题（缓存层级、TTL）、TCP/TLS 是网络与密码学问题（握手 RTT、证书链）、TTFB 是应用与数据库问题、渲染是图形与布局问题。**分层归因**是排查复杂系统问题的通用方法论。
- CORS 的预检设计体现了**「先协商后执行」**：对可能产生副作用的跨源请求（非简单请求），先用无害的 OPTIONS 确认授权，避免「已执行才发现未授权」——这是幂等性与安全性互为约束的又一例证。

### 📚 考研者视角
- 408 这条链路是**综合题富矿**：DNS 查询过程（递归/迭代、本地缓存）、**TCP 三次握手/四次挥手**、**TLS/HTTPS 握手与对称+非对称混合加密**、HTTP 请求响应过程。
- 常考计算/简答：**握手 RTT 数量**（TCP 1 RTT、TLS 1.2 需 2 RTT、TLS 1.3 可 1 RTT）；**为什么三次握手而不是两次**（防止失效连接请求造成资源浪费）。
- 记忆锚点：**同源 = 协议 + 域名 + 端口三者全同**；**CORS 是浏览器行为，服务端只负责给响应头**。
- 与安全章节结合：**XSS（注入脚本，靠 HttpOnly/CSP 缓解）vs CSRF（冒用凭证，靠 SameSite/Token 缓解）**——两者的防御手段常成对出现，务必区分。

> 说明：DNS/TCP/TLS 的**更底层细节**（socket、进程、文件描述符、抓包）见 `tooling`（Linux/Git/Docker）与 `fundamentals`（计算机网络）学科；本章聚焦**浏览器与服务端交互视角**，避免与其他学科重复。
