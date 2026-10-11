# fs-ch06 易错点（Pitfalls）

1. **把「认证」和「鉴权」混为一谈，失败码一律 401** —— 无凭证/坏凭证应是 401（并在响应带 `WWW-Authenticate`），凭证有效但权限不足应是 403。✅ 按 ex11 的链式职责分流：`no_token`/`bad_scheme` → 401，`valid_but_no_perm` → 403，`valid_with_perm` → 200；前端据此分别「跳登录」与「提示无权限」。

2. **只做接口级鉴权，不做资源级校验（水平越权 / IDOR / BOLA）** —— 「用户有 `article:write` 权限」不代表「这条 article 是他的」。✅ 在授权中间件之后再加资源级校验：比对 `resource.ownerId === actor.id`；ex12 中 `editor_delete_others=false`、`editor_delete_own=true` 正是这条规则。越权是 OWASP API Security 的 #1 风险。

3. **JWT 校验只验签名，不验 `exp`/`nbf`/`aud`/`iss`** —— 签名只保证「没被篡改」，不保证「没过期」「不是别家签发的」。✅ 上全清单：段数、alg 白名单、常量时间验签、`exp`、`nbf`、`aud`、`iss`。ex06 实跑：`expired`、`nbf_future`、`aud_wrong`、`iss_wrong`、`missing_exp` 全部被拒。

4. **让 token 头里的 `alg` 决定验签算法（或接受 `alg: none`）** —— 等于把安全决策参数交给攻击者。✅ alg 由服务端**写死/白名单**；ex05 中朴素实现 `alg_none_naive_accepts=true` 被打穿，安全实现 `alg_none_secure=alg-pinned-reject`。

5. **算法混淆：用 RS256 的公钥去验 HS256 的签名** —— 攻击者把「公钥字符串」当 HMAC 密钥自签一个 `alg=HS256` 的 token，按 token 头选算法的实现会验签通过。✅ 把 alg 钉死为 RS256 并绑定密钥类型；ex05 `pinned_alg_blocks_confusion=true`。

6. **以为 JWT 是加密的，往 payload 里塞敏感信息** —— base64url 只是编码，任何人 `split('.')` 后即可解码前两段。✅ 敏感数据不入 payload，或改用 JWE（加密）；ex01 `payload_is_readable_by_anyone=true` 就是反证。

7. **明文 / 可逆加密 / MD5 / SHA1 / 单轮 SHA256 存密码** —— 库一泄露就等同明文；快速哈希在 GPU 上每秒数十亿次。✅ 用 bcrypt/scrypt/argon2（或 PBKDF2）加盐 + 可调成本；ex09 演示 PBKDF2 加盐（`same_password_diff_salt_same_hash=False`）。

8. **密码哈希不加盐，或全站共用一个盐** —— 相同密码产生相同哈希，彩虹表与「撞库可见」双双失效。✅ 每用户随机唯一盐，随哈希一起存（盐不需要保密）；ex09 用两个不同盐演示同密码得到完全不同的哈希。

9. **用 `==` / 字符串相等比较签名或哈希（时序攻击）** —— 短路比较的比较次数随「相同前缀长度」变化，可被逐字节爆破。✅ 用 `crypto.timingSafeEqual` / `hmac.compare_digest`；ex10 实跑 `naive_prefix16_compares=17` vs `naive_allwrong_compares=1`，而常量时间比较恒为 32。

10. **登出只删前端 token，以为服务端一定失效了** —— 无状态 JWT 在 `exp` 之前始终有效，旧 token 复制出来照样能用。✅ 短 TTL + Refresh 轮换 + `jti` 黑名单三件套；ex07 演示「重放旧 refresh → 整族吊销」，ex08 演示黑名单 TTL。

11. **Refresh token 长寿命、不轮换、不复用检测** —— refresh 寿命更长、风险更大，一旦泄露就是长期后门。✅ 单次使用 + 轮换 + 复用即整族吊销；ex07 `old_refresh_replay_ok=false reason=reuse-detected-family-revoked`。

12. **密钥硬编码在代码里 / 提交进 Git** —— 任何拿到仓库的人都能伪造 token 或解密。✅ 密钥走环境变量或密钥管理服务（KMS），可轮转（配 `kid`）；HS256 密钥泄露或某个「只验签」的服务被攻破，即等于全员可被伪造。

13. **Cookie 不设 `HttpOnly` / `Secure` / `SameSite`** —— 会话凭证暴露给 JS（XSS 可窃取）且跨站请求自动携带（CSRF）。✅ 三属性齐上；ex13 `strict/lax_blocks_cross_site_post=true`，而 `SameSite=None` 且不校 CSRF token 时跨站 POST 直接 `status=200`（真实漏洞）。

14. **把 token 放进 URL、日志或 `localStorage`** —— URL 会进浏览器历史/Referer/服务器日志，`localStorage` 一次 XSS 即被读走。✅ 放 `HttpOnly` Cookie 或内存 + 短 TTL；日志对 token 打码；同时给状态变更接口加 CSRF 校验。
