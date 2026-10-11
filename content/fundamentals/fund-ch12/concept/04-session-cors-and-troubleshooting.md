# 会话保持、跨域与分层排查

> 本章要点：状态在 HTTP 里是**外挂**的（Cookie），
> 跨域是**浏览器**施加的安全边界（不是服务器），
> 排查必须**从下层往上证伪**。

## 1. Cookie / Session / Token

### 1.1 为什么需要它们

HTTP 是**无状态**的：服务器不记得你上一次请求过什么。
但「登录后一直保持登录」是刚需，于是必须在协议之外引入状态载体。

### 1.2 三者对比

| 维度 | Cookie | Session | Token（JWT） |
|---|---|---|---|
| **存储位置** | **客户端**（浏览器） | **服务端**（内存/Redis/DB） | **客户端**（Cookie 或 localStorage） |
| **客户端存什么** | 实际数据 | 仅一个 `session_id` | **自包含的令牌**（含声明） |
| **服务端存什么** | 无 | **会话数据** | **无状态**（只验签） |
| **扩容难度** | — | **需要共享存储**（多机要 Redis） | **天然分布式友好** |
| **失效控制** | 客户端删除 | **服务端删除即可，立即生效** | **难**（签发后到期前一直有效，需黑名单） |
| **体积** | 有 4KB 上限 | 极小（一个 ID） | 较大（含 payload，且 Base64 不是压缩） |
| **典型场景** | 记住登录、埋点 | 传统 Web 应用 | 前后端分离 / 微服务 / 开放 API |

### 1.3 Cookie 的三个安全属性（**必须记住**）

服务器通过 `Set-Cookie` 头下发，属性写在后面：

```
Set-Cookie: session_id=abc123; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=3600
```

| 属性 | 作用 | 不设置的后果 |
|---|---|---|
| `HttpOnly` | 禁止 JS 通过 `document.cookie` 读取 | **XSS 可直接偷走会话** |
| `Secure` | 只在 HTTPS 下发送 | 明文 HTTP 下**被中间人嗅探** |
| `SameSite` | 限制跨站请求是否携带 Cookie | **CSRF 攻击**（见下） |

`SameSite` 的三个取值：

- `Strict`：任何跨站请求都不带——最安全，但**从外链点进来会显示未登录**；
- `Lax`（现代浏览器**默认值**）：**顶层导航的 GET 请求**带，`POST` 与 `iframe` 不带。
  这是「安全与体验的折中」；
- `None`：总是携带，但**必须同时加 `Secure`**（否则被浏览器拒绝）。

### 1.4 CSRF 与 XSS：一个必考的区分

这两个是**最容易混淆**的安全问题，区别在于**攻击代码跑在谁那儿**：

| | CSRF（跨站请求伪造） | XSS（跨站脚本） |
|---|---|---|
| **恶意代码在哪** | **攻击者的站点**上 | **受害者的页面**里 |
| **借用了什么** | 用户**已有的 Cookie** | 用户**对站点的信任** |
| **攻击前提** | 用户已登录目标站 | 站点有**未过滤的输入** |
| **典型手法** | `<img src="https://bank.com/transfer?to=evil&amt=1000">` | `<script>fetch('/api/me').then(...)</script>` 注入评论区 |
| **防御核心** | **CSRF Token** + `SameSite` + 校验 `Origin` | **输出转义** + CSP + `HttpOnly` |

**一句话区分**：
**CSRF 是「借你的身份」发请求**（攻击者不知道你的 Cookie，但浏览器会自动带上）；
**XSS 是「在你的页面里」执行代码**（攻击者能直接读 DOM，包括 Cookie——
所以 `HttpOnly` 是防 XSS 偷 Cookie 的关键）。

### 1.5 三视角：会话方案选型

### 🧑‍💻 程序员视角
**选型决策树**（按实际约束走，不要按潮流走）：

```
需要「立即踢下线」/ 强制登出？
├─ 是 → 用 Session（服务端存状态），并把 session 存 Redis
│        代价：多一次 Redis IO，且要处理 Redis 故障降级
└─ 否 → 用 JWT
         但必须处理「注销」的语义：短 access token（15min）
         + 长 refresh token（7d）+ 服务端存 refresh 黑名单
```

**JWT 有三个高频坑**：

1. **别把敏感信息放 payload**。`payload` 只是 **Base64URL 编码，不是加密**，
   任何人都能解出来；
2. **`alg: none` 攻击**。老库若不校验 `alg`，攻击者改成 `none` 就能伪造签名。
   修复：**服务端强制只接受白名单算法**；
3. **无法撤销**。签发后在有效期内一直有效，所以要用**短有效期 + 黑名单**。

**存储位置的选择**（前端常问）：

| 位置 | XSS 风险 | CSRF 风险 | 结论 |
|---|---|---|---|
| `localStorage` | **高**（JS 可读） | 无（不会自动发送） | 需严格防 XSS |
| `HttpOnly Cookie` | **低**（JS 读不到） | **高**（自动发送） | 需 `SameSite` + CSRF Token |

**没有免费的午餐**：这两条路各堵一半，标准做法是
**`HttpOnly` + `SameSite=Lax` + CSRF Token** 三者叠加。

### 🎓 博士生视角
「无状态」与「可撤销」在**分布式系统中存在根本张力**，
这可以用 CAP 的语言重新表述：

- **Session（服务端状态）**：把会话状态集中存储 →
  换取**强一致的可撤销性**，代价是**可用性与分区容忍**下降
  （Redis 挂了，全站登录态失效）。
- **JWT（无状态）**：把状态**编码进令牌**（本质是**把状态复制到每个客户端**）→
  换取**极高的水平扩展能力**，代价是**放弃了撤销能力**
  （你必须引入黑名单，于是又变回有状态）。

这正是 CAP 中「**一致性 vs 可用性**」在会话管理上的具体投影：
**你无法同时得到「无状态」和「可立即撤销」**。

从密码学角度看，JWT 的价值在于**「可验证的自我描述数据」**：
签名保证了完整性与来源，但**不保证机密性**
（若要机密性必须用 JWE，即加密的 JWT）。
这一点常被误解，也是把敏感信息写进 payload 这一错误的根源。

### 📚 考研者视角
408 **不考** Cookie/Session/JWT，但**考 CSRF/XSS 的区分**这一类型的思路
（更常见于「网络安全」章节的选择题）。标准口径：

- **Cookie 是 HTTP 的状态管理机制**，由服务器通过 `Set-Cookie` 下发，
  浏览器在后续请求的 `Cookie` 头中自动携带；
- **Cookie 存在客户端**，**Session 数据存在服务端**，
  客户端只存 `session_id` —— 这是**最能体现两者区别的一句话**；
- **同一个 Cookie 受同源策略约束**：默认只发给**设置它的域**及其子域（取决于 `Domain` 属性）。

易错点：
- *「Session 存在客户端」* → **错**（存在客户端的只有 ID）；
- *「Cookie 有大小限制吗」* → 有，**单个 Cookie 约 4KB**，且每个域名下的数量也有限制。

---

## 2. 同源策略与跨域（CORS）

### 2.1 什么是「同源」

```
https://www.example.com:443/path?a=1
└─┬─┘   └───────┬──────┘└┬┘
scheme        host      port
```

**三者全部相同**才叫同源。注意：

- `http://` 与 `https://` **不同源**（scheme 不同）；
- `example.com` 与 `www.example.com` **不同源**（host 不同）；
- `https://example.com` 与 `https://example.com:8443` **不同源**（port 不同）。

### 2.2 同源策略到底限制什么

**关键澄清：同源策略是浏览器的行为，不是服务器的。**
所以：

- `curl` / Postman / 服务端到服务端调用**完全不受同源策略影响**；
- 受限制的是**浏览器里的 JS 发起的跨源请求的「读取」**——
  请求**发出去了**，服务端**处理了**，只是浏览器**不把响应交给 JS**。

这就是为什么「后端日志里有记录，但前端报 CORS 错误」——
请求确实成功了，是浏览器**拦在了返回值那一步**。

### 2.3 简单请求 vs 预检请求

浏览器把跨源请求分成两类：

**简单请求**（同时满足：方法为 `GET`/`HEAD`/`POST`；
且 `Content-Type` 为 `text/plain`、`multipart/form-data`、
`application/x-www-form-urlencoded`；且无自定义头）——
**直接发送**，服务端回 `Access-Control-Allow-Origin` 即可。

**预检请求（preflight）**：其他情况（比如 `PUT`、
`Content-Type: application/json`、带自定义头 `Authorization`）——
浏览器**先发一个 `OPTIONS`**，问服务器「我能不能这么发」。

```
OPTIONS /api/user HTTP/1.1
Origin: https://app.example.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: authorization,content-type
```

服务器必须回答：

```
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET,POST,PUT,DELETE
Access-Control-Allow-Headers: authorization,content-type
Access-Control-Max-Age: 86400          ← 预检结果缓存 24 小时，避免每次都 OPTIONS
```

**注意**：`Access-Control-Allow-Origin: *` 与
`Access-Control-Allow-Credentials: true` **不能同时使用**——
带凭证时必须**回显具体的 Origin**，不能通配。

### 2.4 三视角：跨域的本质

### 🧑‍💻 程序员视角
**CORS 报错的定位清单**（按出现频率）：

1. **`Access-Control-Allow-Origin` 缺失** → 服务端没配，或被 Nginx 吞了；
2. **通配符 + 凭证冲突**（`*` 与 `credentials: true` 同用）→ 改回显 Origin；
3. **预检失败但实际请求没问题** → `Allow-Methods` / `Allow-Headers` 没列全，
   特别注意自定义头（如 `Authorization`、`X-Request-Id`）**必须出现在
   `Access-Control-Allow-Headers`**；
4. **Nginx 把 `OPTIONS` 转发给了后端但后端返回 405** →
   在 Nginx 层直接 `if ($request_method = OPTIONS) { return 204; }`；
5. **多个 `Access-Control-Allow-Origin` 头**（网关和后端都加了一遍）→
   浏览器会因「重复头」直接判失败。用
   `curl -sI -H 'Origin: https://a.com' https://api/ | grep -i access-control` 数一下几行。

**开发环境最常见的误判**：本地 `localhost:3000` 调 `localhost:8000` 报跨域。
正确解法是**在后端加 CORS 中间件**，而不是「关掉浏览器安全策略」——
后者会让你在本地通过、线上踩坑。

### 🎓 博士生视角
同源策略是**「最小权限原则」在浏览器上的实现**，其目标是阻止
**「站点 A 的脚本读取站点 B 的数据」**。要理解它的必要性，
先要理解它的**威胁模型**：

浏览器会**自动携带 Cookie**，因此如果没有同源策略，
`evil.com` 的脚本可以：

```javascript
fetch('https://bank.com/api/balance').then(r => r.text())
  // 若允许读取，用户的余额就被窃取了
```

这被称为 **XSRF / 数据窃取**。同源策略的根本假设是：

> **「能读到跨源响应」= 「获得了跨源数据的访问权」**

因此它的粒度是**「读」而不是「发」**——请求本身是允许的
（这是 Web 的开放性所需），只有响应被拦下。

CORS 则是对这一策略的**受控放宽**：
它让**服务端**（而不是客户端）来声明「我允许哪些来源读我的响应」。
这是一个**由资源所有者授权的机制**，符合「谁的数据谁做主」的原则。

一个理论上有趣的点：同源策略本质上无法阻止**「跨站请求伪造」
（因为请求能发出去）**，所以 CSRF 需要**另外的**防御
（Token / SameSite），这正是「同源策略 ≠ CSRF 防护」的原因。

### 📚 考研者视角
408 不涉及 CORS，但**「同源策略」与「Cookie 的作用域」**可能出现在
网络安全相关的选择题里。记三个结论：

1. **同源 = 协议 + 域名 + 端口，三者全同**；任何一项不同都算跨源；
2. **同源策略由浏览器实施**，服务端调用不受限制；
3. **Cookie 的作用域**由 `Domain` 与 `Path` 决定，且遵循
   **「只发送给设置它的域或其子域」**的规则。

---

## 3. 分层排查：命令与顺序

### 3.1 命令与层的对应表（**背下来**）

| 层 | 命令 | 看什么 |
|---|---|---|
| 应用层 | `dig` / `nslookup` / `curl -v` / `openssl s_client` | DNS 记录、HTTP 状态码、TLS 证书 |
| 传输层 | `ss -tnp` / `netstat -anp` / `nc -vz` / `tcpdump` | 连接状态、端口监听、重传与丢包 |
| 网络层 | `ping` / `traceroute` / `mtr` / `ip route` | 可达性、路径、路由表 |
| 链路层 | `arp -a` / `ip link` / `tcpdump -e` | MAC 地址表、网卡状态、帧 |

### 3.2 `ss` / `netstat` 的状态列要看什么

```bash
ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn
```

| 状态 | 含义 | 异常信号 |
|---|---|---|
| `LISTEN` | 正在监听 | — |
| `ESTABLISHED` | 已建立 | 数量暴涨 → 可能是连接池泄漏或攻击 |
| `TIME_WAIT` | 主动关闭方等待 2MSL | 大量出现 → 短连接过多，考虑连接复用 |
| `CLOSE_WAIT` | **被动关闭方还没调 `close()`** | **持续增长 → 应用代码忘了关闭连接（最常见的线上 bug）** |
| `SYN_RECV` | 收到 SYN，未完成握手 | 大量 → **SYN Flood 攻击**或半连接队列过小 |

**`CLOSE_WAIT` 堆积是 Java/Python 后端最常见的连接泄漏症状**——
它一定指向**应用层没关连接**，不是网络问题。
这是「分层排查」最有价值的一个判据：**现象在传输层，根因在应用层**。

### 3.3 抓包：只抓「该看的」

```bash
# 只看某个 TCP 连接的首部，不抓正文（避免刷屏 / 泄露数据）
tcpdump -i any -nn -A 'tcp port 443 and host 93.184.216.34'

# 看 TLS 握手的 SNI（不解密也能看出访问了哪个域名）
tcpdump -i any -nn -A 'tcp port 443' | grep -i -A2 "client hello"

# 抓 SYN 包，看谁在连你
tcpdump -i any -nn 'tcp[tcpflags] == tcp-syn'
```

### 3.4 三视角：排查方法论

### 🧑‍💻 程序员视角
**「网页打不开」的五分钟收敛剧本**（可直接抄进 runbook）：

```
[1] ping 8.8.8.8                      → 不通？本机网络问题，停。
[2] dig +short example.com            → 空？DNS 问题，看 /etc/resolv.conf 与 hosts。
[3] nc -vz example.com 443            → refused？服务/防火墙；timeout？路由黑洞。
[4] openssl s_client -connect ...     → 证书错误？看有效期与链。
[5] curl -sv -o /dev/null -w '...'    → 5xx？看服务端日志；超时？看上游耗时。
```

**每一步都必须「先证伪当前层，再往下走」**。
常见的错误跳步是：跳过 1~4 直接重启应用服务——运气好时问题被掩盖了，
但下次还会复发，而且你**永远不知道根因**。

另外两个实用的判据：

- **`ping` 通但 `curl` 不通** → 网络层 OK，看传输层及以上（防火墙、端口、TLS）；
- **`curl` 通但浏览器不通** → 大概率是**代理设置**、
  **浏览器 DNS（DoH）**、**证书例外**或**扩展拦截**。

### 🎓 博士生视角
分层排查之所以有效，根源在于**分层抽象保证了「层间可证伪」**：
每一层对上层提供**契约**，因此当契约被破坏时，
**故障必然可归属到某一层**——这就是「端到端原则（end-to-end principle）」
在诊断上的体现：**智能放在端点，中间网络只做转发**，
因此排障也应该**在端点上逐层验证**，而不是去猜中间设备。

形式化地看，把整条链路视为函数复合：

$$F = f_{\text{app}} \circ f_{\text{transport}} \circ f_{\text{network}} \circ f_{\text{link}}$$

排障的任务是**定位哪个 $f_i$ 不满足其契约**。
由于复合函数的性质，**只要在每一层单独测试 $f_i$，就能用至多 $n$ 次检查
定位 $n$ 层中的故障**——这是**二分/线性搜索**在工程诊断中的应用。

而 `ping`（ICMP）与 `curl`（TCP）的区别正是这个方法论的关键工具：
它们**分别探测不同的 $f_i$**，因此可以**单独验证网络层而排除传输层**。

### 📚 考研者视角
统考不考命令，但**「分层」的思想贯穿整张卷子**。
把命令与分层绑在一起的记法（面试可直接背）：

```
应用层 → dig / curl
传输层 → ss / netstat
网络层 → ping / traceroute
链路层 → arp
```

再补一个高频考点：**`ping` 用的是 ICMP 协议**，
**ICMP 属于网络层**（封装在 IP 包内），**不使用端口**——
所以「`ping` 不通但网页能开」是**完全可能的**（很多服务器禁 ICMP）。
