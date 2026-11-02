# 认证实战：签发、校验、撤销与防护

> JWT 的"无状态"是优点也是陷阱。本节用一段**可运行的最小实现**把三件事固定下来：
> 怎么签发与校验、怎么做到"登出即失效"、以及 CSRF/XSS 两道防线怎么落。

### 一、Token 结构与校验流程

```text
header.payload.signature
│      │        └── HMAC-SHA256(base64url(header) + "." + base64url(payload), secret)
│      └─────────── Claims：sub(用户) exp(过期) iat(签发) jti(唯一 id) aud/iss(受众/签发者)
└────────────────── alg:HS256 / RS256

校验五步：
1) 取 Authorization: Bearer <token>（或 HttpOnly Cookie）
2) 拆三段，base64url 解出 header/payload（**不要**在这里信任任何字段）
3) 验签：用密钥重算签名比对（HS256 用 secret，RS256 用公钥）
4) 查 claims：exp 未过期、iss/aud 匹配、nbf 未提前
5) 再查服务端状态：tokenVersion / 黑名单 / 用户是否被封禁
```

### 二、签发与校验（HS256 示例）

```js
const crypto = require('node:crypto');

const SECRET = process.env.JWT_SECRET;          // 至少 32 字节随机
const TTL = '15m';

const b64u = (buf) => Buffer.from(buf).toString('base64url');

function sign(payload, { expiresIn = TTL, secret = SECRET } = {}) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: 'HS256', typ: 'JWT' };
  const body = { iat: now, exp: now + 15 * 60, jti: crypto.randomUUID(), ...payload };
  const data = `${b64u(JSON.stringify(header))}.${b64u(JSON.stringify(body))}`;
  const sig = crypto.createHmac('sha256', secret).update(data).digest('base64url');
  return `${data}.${sig}`;
}

function verify(token, { secret = SECRET } = {}) {
  const parts = String(token || '').split('.');
  if (parts.length !== 3) throw new Error('malformed token');
  const [h, p, s] = parts;
  const expected = crypto.createHmac('sha256', secret).update(`${h}.${p}`).digest('base64url');
  // 定长比较，避免时序侧信道
  if (crypto.timingSafeEqual(Buffer.from(s), Buffer.from(expected)) === false) {
    throw new Error('bad signature');
  }
  const claims = JSON.parse(Buffer.from(p, 'base64url').toString('utf8'));
  if (claims.exp * 1000 < Date.now()) throw new Error('expired');
  return claims;
}
```

### 三、登出即失效：给"无状态"补上状态

```js
// 令牌版本号：用户改密码/封禁时 +1，旧令牌全部作废（不用逐条存黑名单）
async function issueTokens(user, store) {
  const tokenVersion = await store.getTokenVersion(user.id);
  const access = sign({ sub: user.id, name: user.nickname, tv: tokenVersion });
  const refresh = sign({ sub: user.id, kind: 'refresh', tv: tokenVersion }, { expiresIn: '30d' });
  // 刷新令牌只存哈希，落库/Redis
  await store.saveRefreshHash(user.id, hash(refresh));
  return { access, refresh };
}

async function authenticate(req, store) {
  const claims = verify(req.headers.authorization?.replace('Bearer ', '') || req.cookies.access);
  const user = await store.findById(claims.sub);
  if (!user || user.disabled) throw new Error('user invalid');
  const current = await store.getTokenVersion(user.id);
  if (current !== claims.tv) throw new Error('token revoked');   // 改密/登出后失效
  return user;
}
```

### 四、Cookie 与 CSRF：状态变更接口的双保险

```js
// 写 token 时三个属性齐全：HttpOnly(JS 读不到) + Secure(只走 https) + SameSite
res.cookie('access', accessToken, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',        // 同站才带 → 跨站 POST 默认不带 Cookie
  maxAge: 15 * 60 * 1000,
  path: '/',
});

// 双提交 Cookie：服务端下发随机 csrfToken（非 HttpOnly），变更请求必须带上
function issueCsrf(req, res) {
  const token = crypto.randomBytes(16).toString('hex');
  res.cookie('csrf', token, { httpOnly: false, sameSite: 'strict', secure: true, path: '/' });
  return token;
}

function requireCsrf(req, res, next) {
  const cookie = req.cookies.csrf;
  const header = req.get('x-csrf-token');
  if (!cookie || !header || cookie.length !== header.length ||
      crypto.timingSafeEqual(Buffer.from(cookie), Buffer.from(header)) === false) {
    return res.status(403).json({ error: 'csrf token mismatch' });
  }
  next();
}
```

```text
两种防御的分工：
  SameSite=strict/lax  → 浏览器层面「跨站不带 Cookie」（第一道）
  X-CSRF-Token 校验    → 服务端层面「请求确实来自本站页面」（第二道）
  只做 SameSite 不够：老浏览器不支持、且 SameSite=None 的跨站场景仍需 token
  只做 token 也不够：token 若通过 localStorage 传递，XSS 能直接读走 → 所以 Cookie 必须 HttpOnly
```

### 五、XSS 侧的兜底：输出编码与 CSP

```js
// 1) 前端渲染一律用文本节点，别拼 HTML
function renderUserName(el, name) {
  el.textContent = name;          // ✅ 自动转义
  // el.innerHTML = `<b>${name}</b>`;   // ❌ name 里带 <script> 就出事
}

// 2) 服务端给严格 CSP：禁止内联脚本、禁止外部源
const csp = [
  "default-src 'self'",
  "script-src 'self'",             // 不给 'unsafe-inline'
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "object-src 'none'",
  "frame-ancestors 'none'",
].join('; ');
res.setHeader('Content-Security-Policy', csp);
```

```text
一道自检：如果 token 存在 localStorage，那么任何一处 XSS 都能把它偷走；
把 token 放 HttpOnly Cookie 后，XSS 偷不到了，但 CSRF 风险上升 → 于是要 SameSite + CSRF token。
两者是配套设计，不能只做一半。
```

## 三视角解析
### 🧑‍💻 程序员视角
JWT 是无状态的，签发后无法单方面作废——「登出即失效」必须补状态：维护一个短 TTL 的黑名单（Redis），或用「短 access token + 长 refresh token + 版本号」。`alg: none` 攻击是老问题，校验时必须显式限定算法，不能信任 header 里的 `alg`。把 JWT 放 `localStorage` 会被 XSS 偷走，放 `HttpOnly` Cookie 又要防 CSRF——「双保险」是 Cookie + `SameSite` + CSRF token。密钥绝不能硬编码在代码里，且 HS256 的密钥要足够长（≥256 位）。

### 🎓 博士生视角
JWT 的安全性建立在「签名不可伪造」上，它提供的是「完整性 + 认证」，**不提供机密性**——payload 是 Base64 编码而非加密，任何人都能解开看。因此敏感信息不能放进去。无状态令牌与「可撤销」本质冲突：要撤销就必须引入服务端状态，这与 JWT 的初衷相悖，工程上用「短 TTL 缩小窗口 + 黑名单兜底」折中。OIDC 在 OAuth2 之上加了身份层，`id_token` 才是「你是谁」，`access_token` 只是「能做什么」。

### 📚 考研者视角
全栈面试高频：
1. **JWT 结构**：header.payload.signature 三段，签名算法与校验流程。
2. **无状态的代价**：无法主动失效、令牌体积大、续期方案（refresh token）。
3. **存储位置**：localStorage（XSS 风险）vs HttpOnly Cookie（CSRF 风险）的权衡。
4. **OAuth2 与 OIDC**：四种授权模式（授权码 + PKCE 是主流）、`id_token` 与 `access_token` 的区别。
