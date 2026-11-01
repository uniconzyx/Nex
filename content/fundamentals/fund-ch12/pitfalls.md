1. **把「同源策略」当成服务端的行为** —— 同源策略是**浏览器**施加的限制，
   服务端之间的调用（`curl`、Postman、微服务互调）根本不受影响。
   表现：后端日志里明明有请求记录、返回 200，前端仍报 CORS 错误——
   因为**请求成功发出了，只是浏览器拦住了响应不让 JS 读**。
   正确认识：CORS 只约束「浏览器里的 JS 能读什么」。

2. **`Access-Control-Allow-Origin: *` 与 `credentials: true` 同时使用** ——
   规范明确禁止这一组合，浏览器会直接拒绝。带凭证时必须**回显具体 Origin**：
   ```python
   allow = request.headers["Origin"]
   if allow in WHITELIST: resp.headers["Access-Control-Allow-Origin"] = allow
   resp.headers["Vary"] = "Origin"        # 必须加，否则 CDN 会缓存错源
   ```

3. **漏配 `Access-Control-Allow-Headers`** —— 预检失败但实际请求「看起来没问题」。
   最容易漏的是自定义头（`Authorization`、`X-Request-Id`、`X-Trace-Id`）。
   排查：`curl -X OPTIONS -H 'Origin: https://a.com' -H 'Access-Control-Request-Headers: authorization' -i https://api/`，
   看返回里有没有把该头列出来。

4. **把 `Set-Cookie` 的属性写反导致「登录成功但刷新就掉线」** ——
   典型三因：`SameSite=Strict`（外链进来不带 Cookie）、
   `Secure` 但站点还在 HTTP、`Domain` 写成了上级域却期望子域共享。
   修复顺序：先确认 `SameSite=Lax`，再确认全站 HTTPS，最后核对 `Domain`。

5. **以为 JWT 的内容是加密的** —— `payload` 只是 **Base64URL 编码**，
   任何人复制到 [jwt.io] 都能解出来。**绝不能放**手机号、身份证、内部 ID 等敏感信息。
   要机密性必须用 **JWE**（加密的 JWT），而不是 JWS。

6. **JWT 不校验 `alg` 字段** —— 经典漏洞：攻击者把头部改成 `{"alg":"none"}`，
   去掉签名即可伪造任意身份（`alg: none` 攻击）。
   修复：**服务端白名单只接受 `RS256`/`ES256` 等指定算法**，
   并且**用公钥验证时不要接受对称算法**（防止 RSA 公钥被当 HMAC 密钥使用）。

7. **把 `CLOSE_WAIT` 当成网络问题** —— `CLOSE_WAIT` 意味着
   **对端已发 FIN，本方还没调用 `close()`**。
   它一定指向**应用层连接泄漏**（HTTP 客户端没释放、数据库连接没还池）。
   判据：`ss -tan | grep CLOSE_WAIT | wc -l` 持续增长即为泄漏。
   对比：`TIME_WAIT` 是**主动关闭方**的正常状态，量大只说明短连接过多。

8. **改 DNS 记录时没先调小 TTL** —— 若原来的 TTL 是 24 小时，
   改完 IP 后**最长 24 小时**才会全网生效，期间用户会在新旧 IP 之间随机命中。
   标准流程：**先降 TTL 到 60s → 等一个旧 TTL 周期 → 再切 IP → 稳定后调回**。

9. **认为 `CNAME` 可以随便用在根域、也可以与其它记录共存** ——
   同一个名字上 `CNAME` **不能**与 `A`/`MX`/`TXT` 共存（DNS 规范要求），
   且根域通常不允许 `CNAME`（会破坏该域的 `NS`/`MX`）。
   需要「根域指向别处」时用 **`ALIAS`/`ANAME`**（厂商扩展）或直接写 `A` 记录。

10. **以为 HTTPS 能隐藏你访问的目标** —— TLS 加密的是**载荷**，
    但 **SNI（TLS 握手里的域名）在 TLS 1.3 之前是明文的**，
    且**目标 IP 始终可见**。所以中间人仍能知道你「访问了哪个站点」，
    只是不知道「访问了什么内容」。要隐藏 SNI 需 **ECH（Encrypted Client Hello）**。

11. **把 `Cache-Control: no-cache` 当成「不缓存」**
   `no-cache` 的准确含义是「**可以存，但每次使用前必须向服务器验证**（revalidate）」；真正禁止存储的是 `no-store`。把敏感响应标成 `no-cache` 后，它仍会落到浏览器与中间代理的磁盘缓存里。
   ✅ 要求「不留副本」用 `no-store`；要求「每次都验证」用 `no-cache`；要求「一段时间内直接用」才用 `max-age`。

12. **给 `304 Not Modified` 塞响应体**
   304 按定义**不能带响应体**（只允许带少量头部）。带体会让部分客户端把这段 body 当成下一个响应的开头，产生协议错位——表现为「偶发的 JSON 解析失败」，极难复现。
   ✅ 304 只回 `ETag`/`Date`/`Cache-Control` 等头部；`Content-Length` 也不要写。

13. **以为 HTTP/2 的多路复用消除了队头阻塞**
   它消除的是 **HTTP 层**的队头阻塞（一个连接上多个 stream 并发），但底下的 TCP 仍是单一字节流：丢一个包，该连接上所有 stream 一起等重传——这是**TCP 层**的队头阻塞。
   ✅ 真正要消除传输层队头阻塞需要 QUIC/HTTP3（以 UDP 为承载、按 stream 独立重传）；HTTP/2 的收益主要是省连接与省头部，不是抗丢包。

14. **漏写 `Vary`，让 CDN 缓存串味**
   响应内容随 `Accept-Encoding`、`Accept-Language`、`Cookie` 等请求头变化时，若不声明 `Vary`，CDN 会把「第一个请求者的版本」发给所有后来者——典型事故是英文页面发给中文用户、压缩版发给不支持 gzip 的客户端。
   ✅ 只要响应内容依赖某个请求头，就必须在 `Vary` 里列出它；含 `Cookie` 的个性化响应通常应 `private` + `no-store`，不交给共享缓存。

15. **只部署叶子证书，漏掉中间证书**
   桌面浏览器能通过证书里的 AIA 地址自动补齐中间证书，所以「本机测试一切正常」；但移动端、Java 客户端、部分服务间调用不带中间证书库，表现为「浏览器打得开、App 报证书链不完整」。
   ✅ 部署时用 `fullchain.pem`（叶子 + 全部中间证书），并用 `openssl s_client -connect host:443 -showcerts` 核对链是否完整。
