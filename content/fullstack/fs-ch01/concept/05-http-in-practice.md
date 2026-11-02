# HTTP 实战：报文、缓存与连接复用

> 概念讲完了，落地时会遇到三件具体事：**报文长什么样**、**响应为什么没变**、
> **连接断了重试会不会重复下单**。本节用可运行的最小例子把这三件事固定下来。

### 一、一次请求的完整报文

```text
GET /api/v1/exercises?subject=cpp HTTP/1.1
Host: 127.0.0.1:8000
User-Agent: curl/8.5.0
Accept: application/json
Connection: keep-alive

（空行后是请求体）
```

```text
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Cache-Control: no-store
ETag: "W/\"a41c\""
Content-Length: 87

{"items":[{"id":"cpp-ch01-01","title":"指针与数组"}]}
```

看两处：**状态行后面的版本与状态码**决定后续行为（1.1 支持 keep-alive，304 表示用缓存），
**响应头里的 `Cache-Control`/`ETag`**决定浏览器与中间代理会不会复用。

### 二、缓存：让第二次请求变便宜

```js
// 服务端：给出可缓存的响应，带 ETag；客户端带 If-None-Match，命中就回 304
const crypto = require('node:crypto');

const PAYLOAD = JSON.stringify({ items: [{ id: 'cpp-ch01-01', title: '指针与数组' }] });
const etag = '"' + crypto.createHash('sha1').update(PAYLOAD).digest('hex').slice(0, 8) + '"';

function handle(req, res) {
  if (req.headers['if-none-match'] === etag) {
    res.writeHead(304, { ETag: etag });
    return res.end();               // 304 无响应体，省带宽
  }
  res.writeHead(200, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'private, max-age=60',
    ETag: etag,
  });
  res.end(PAYLOAD);
}

module.exports = { handle, etag };
```

关键点：**带用户隐私的响应必须 `private`/`no-store`**，否则 CDN 会把 A 用户的响应发给 B 用户。

### 三、幂等重试：网络抖动不该等于重复下单

```js
// 客户端：超时/5xx 时带同一个 Idempotency-Key 重试，服务端据此去重
const crypto = require('node:crypto');

async function postWithRetry(url, body, max = 3) {
  const key = crypto.randomUUID();                 // 一次业务操作一个 key
  for (let attempt = 1; attempt <= max; attempt += 1) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(3000),
      });
      if (res.status >= 500) throw new Error('server ' + res.status);
      return await res.json();
    } catch (err) {
      if (attempt === max) throw err;
      await new Promise((r) => setTimeout(r, 200 * attempt));   // 退避
    }
  }
}
```

服务端要记住 `Idempotency-Key`（Redis 设 TTL），否则重试会真的重复创建。

### 四、CORS：浏览器发的跨域请求长什么样

```text
# 浏览器发起跨域 POST：
POST /api/v1/auth/login
Origin: https://app.example.com
Content-Type: application/json

# 服务端必须回：
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Credentials: true
Access-Control-Allow-Headers: content-type
Vary: Origin

# 预检（复杂请求先发 OPTIONS，浏览器代替你问「能不能发」）：
OPTIONS /api/v1/auth/login
Origin: https://app.example.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type
→ 204 + 同样的 Allow-* 头
```

```js
// 允许来源要用「回显 + Vary」，不要写死通配符 + 凭证（浏览器会直接拒绝）
function cors(origin) {
  const allowed = new Set(['https://app.example.com', 'http://localhost:1420']);
  return {
    'Access-Control-Allow-Origin': allowed.has(origin) ? origin : allowed.values().next().value,
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Headers': 'content-type, authorization',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Access-Control-Max-Age': '600',
    Vary: 'Origin',
  };
}
```

**CORS 是浏览器的策略，不是服务端鉴权**：`curl` 不受它限制，所以跨域配置再松也不会成为
"绕过鉴权"的漏洞——真正的防线在 token 校验与权限判定上。
