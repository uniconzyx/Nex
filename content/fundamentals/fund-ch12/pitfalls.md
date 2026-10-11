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
