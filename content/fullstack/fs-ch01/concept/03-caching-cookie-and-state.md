# 03 · 缓存、Cookie 与状态：在无状态协议上模拟「记忆」

## 一、理论根基：HTTP 无状态，一切「记忆」都是外置的

HTTP 本身不记得你是谁。所有「记得」的假象，都来自三种外置机制：

1. **HTTP 缓存** —— 记住「这份资源的内容」，避免重复传输；
2. **Cookie** —— 客户端存一段小数据，每次请求**自动带上**；
3. **Session / Token** —— 服务端（或客户端）保存会话状态，靠 Cookie 或请求头传递引用。

理解这条主线，就能把「缓存、Cookie、Session、JWT」串成一个整体：**它们都是「在无状态协议上重建有状态语义」的不同层次方案**。

## 二、实现机制

### 缓存：强缓存 vs 协商缓存

**强缓存（不发请求）**：
```text
Cache-Control: max-age=3600          # 1 小时内直接用本地副本，不发请求
Cache-Control: no-store              # 完全不缓存（含敏感数据）
Cache-Control: no-cache              # 可缓存，但每次必须向服务端校验
Cache-Control: private / public      # 只有浏览器 / 允许 CDN 等共享缓存
Expires: Wed, 21 Oct 2026 07:28:00 GMT   # HTTP/1.0 旧式绝对时间（已被 Cache-Control 取代）
```

**协商缓存（发请求，服务端说「没变」）**：
```text
# 响应：服务端给出版本标识
ETag: "33a64df5"                     # 内容指纹（强/弱校验）
Last-Modified: Wed, 21 Oct 2026 07:28:00 GMT

# 下次请求：客户端带上标识
If-None-Match: "33a64df5"
If-Modified-Since: Wed, 21 Oct 2026 07:28:00 GMT

# 服务端判断未变 → 304 Not Modified（无主体，省掉传输）
HTTP/1.1 304 Not Modified
```

**优先级**：`Cache-Control` 优先于 `Expires`；协商时 `ETag`（`If-None-Match`）优先于 `Last-Modified`（`If-Modified-Since`）。

**ETag 为什么优于 Last-Modified**：① 文件内容没变但修改时间变了（如重新部署）会误判为「已修改」；② Last-Modified 精度只到**秒**，1 秒内多次修改无法区分。

### Cookie 的属性与安全

```text
Set-Cookie: sessionId=abc123; Domain=example.com; Path=/; Max-Age=3600;
            Secure; HttpOnly; SameSite=Lax
```

| 属性 | 作用 | 缺失的风险 |
|---|---|---|
| `HttpOnly` | 禁止 JS 读取（`document.cookie` 取不到） | XSS 可窃取会话 |
| `Secure` | 只在 HTTPS 下发送 | 明文链路被中间人窃取 |
| `SameSite=Lax/Strict/None` | 限制跨站携带 | CSRF 攻击 |
| `Domain`/`Path` | 控制发送范围 | 作用域过大，泄露面扩大 |
| `Max-Age`/`Expires` | 有效期（不设 = 会话 Cookie，关浏览器即失效） | 长期有效凭证被盗 |

### Session vs Token

| 维度 | Session（服务端存储） | Token / JWT（客户端携带） |
|---|---|---|
| 状态位置 | 服务端（内存/Redis） | 客户端（JWT 内含声明） |
| 传输方式 | Cookie 自动携带 | 通常 `Authorization: Bearer` |
| 横向扩展 | 需共享存储（否则会话粘滞） | 天然无状态、易扩展 |
| 撤销 | 服务端删除即可（即时） | 需黑名单/短过期+刷新令牌（**难即时撤销**） |
| 体积 | 小（只存 ID） | 大（含载荷，且随每次请求发送） |

## 三、工程实践

- **静态资源用指纹文件名 + 强缓存**：`app.3f2a1b.js` 配 `Cache-Control: max-age=31536000, immutable`。内容变了文件名就变，**URL 成为天然的缓存版本号**——这是前端构建产物缓存的标准方案。
- **HTML 入口用 `no-cache`（协商缓存）**：保证用户总能拿到指向最新资源的引用，同时用 ETag 省流量。
- **CDN 与 `private/public`**：含用户信息的响应必须 `private`（或 `no-store`），否则共享缓存可能把 A 的数据发给 B——这是**严重的越权事故**。
- **SPA + Token 的存储权衡**：`localStorage` 便利但易被 XSS 窃取；`HttpOnly` Cookie 免疫 XSS 读取但需处理 CSRF（`SameSite` + CSRF Token）。没有「绝对安全」的选项，只有权衡。
- **`Vary` 头部**：内容按 `Accept-Encoding`/`Accept-Language`/`Cookie` 变化时，必须声明 `Vary`，否则缓存会把「给 A 的变体」发给 B。

## 四、边界与陷阱

- **`no-cache` 不是「不缓存」**：它是「可缓存但每次必须校验」；真正「不缓存」是 `no-store`。这是最常被搞反的一组。
- **`max-age=0` 与 `no-cache` 的区别**：前者是「立刻过期但仍可协商」，后者语义更明确。
- **修改资源后忘了让 ETag 变化**：会导致客户端永远命中 304、看不到更新（典型是「改了配置但页面没变」）。
- **Cookie 跨域与 `SameSite=None`**：现代浏览器要求 `SameSite=None` **必须同时 `Secure`**，否则 Cookie 被丢弃。
- **`Domain` 设成顶级域**：`.com` 之类的设置会被浏览器拒绝或造成 Cookie 泄露面过大。
- **JWT 存敏感信息**：JWT 载荷只是 **Base64 编码（非加密）**，任何人可解——绝不能放密码等敏感数据。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **缓存策略模板**：`index.html` → `no-cache`（协商）；`*.hash.js/css` → `max-age=1y, immutable`；API 的 GET → 视业务设 `max-age=0~60` 或 `no-store`（含用户数据时）。
- **登录态选型**：服务端可水平扩展且需即时登出 → Session + Redis；无状态、跨域、移动端 → JWT（配短过期 + refresh token）。
- 落地建议：**先定「谁能看到这份缓存」**（`private` / `public` / `no-store`），再定过期策略——顺序反了就容易出越权事故。

### 🎓 博士生视角
- HTTP 缓存是一套**由元数据驱动的分布式缓存协议**：`Cache-Control` 是**策略**、`ETag`/`Last-Modified` 是**版本向量**、`Vary` 是**变体维度**。三者组合构成了「如何在无中心协调的情况下保证缓存一致性」的经典答案。
- 强缓存与协商缓存在**一致性-延迟**上做了不同的取舍：强缓存把延迟压到零但容忍过期窗口；协商缓存保证内容新鲜但至少付一个 RTT。这不是缺陷，而是**显式的可调参数**。
- Cookie 的安全属性本质是**在「自动携带」这一便利上打补丁**：自动携带是 CSRF 的根源（`SameSite` 来修），JS 可读是 XSS 的放大器（`HttpOnly` 来修），明文传输是窃听面（`Secure` 来修）。三个属性分别对应三类攻击，非常工整。

### 📚 考研者视角
- 408 缓存考点（**高频大题**）：**强缓存 vs 协商缓存**的判定流程、`Cache-Control` 常用指令、`ETag`/`Last-Modified` 对应的请求头（`If-None-Match`/`If-Modified-Since`）、`304` 的产生时机。
- 常考辨析：**`no-cache` ≠ 不缓存**（要校验）；**Cookie 存在客户端、Session 存在服务端**；**Cookie 随请求自动发送、Token 需手动加头**。
- 记忆锚点：**「强缓存不发请求，协商缓存发请求但可能只回 304」**——这句话能覆盖大部分选择题。
- 与体系结构结合：可联系**代理服务器（Proxy Cache）**考点——`private`/`public` 正是为区分「浏览器私有缓存」与「共享（代理/CDN）缓存」而设。
