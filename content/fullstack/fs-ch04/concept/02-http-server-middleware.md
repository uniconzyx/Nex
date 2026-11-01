# fs-ch04 · HTTP 服务与中间件


```text
从零手写 HTTP 的最小闭环：
    net.createServer ─▶ 逐 chunk 拼接 body（不是一次到齐）
      ─▶ 解析 start-line + headers（\r\n\r\n 是分界）
      ─▶ 路由匹配（method + path 模板 / token）
      ─▶ res.writeHead(status, headers) ─▶ res.end(body)

中间件 = (req, res, next) 的洋葱链：
    ┌ A 前 ─┬ B 前 ─┬ handler ┬ B 后 ┬ A 后 ┐
    next() 向下走；返回时向上走；next(err) 直接跳到错误中间件

必须处理的边界：
    Content-Length 与实际 body 不一致 / chunked 传输编码
    请求体大小上限（否则一个超大 body 打满内存）
    未捕获异常 -> 统一 500，且不把堆栈泄漏给客户端
```

## 一、从零手写 HTTP 服务器（路由 / 路径变量 / JSON body / 状态码）

Node 内置 http 模块把 socket 字节流按 RFC 7230 解析为 req/res 对象；服务器 = 一个 createServer 回调，需在回调内做路由匹配、请求体解析与响应。状态码是三位数字，首位表类别。

### 🧑‍💻 程序员视角
- 路由用「方法 + 路径」查表：路径变量（/items/:id）用正则捕获段；查询串用 new URL(req.url).searchParams 取，别把 ? 后的部分当路径。
- 永远 res.end()（或 write 后 end），否则连接挂起、客户端超时；JSON 响应务必带 'Content-Type':'application/json' 与正确 Content-Length。
- 解析 JSON body 要 try/catch 并限制大小，非法 JSON 返回 400 而非让进程 500；生产用 Fastify/Express/Koa，但必须理解底层这些步骤。
- 状态码语义：200 成功、201 创建、400 坏请求、401 未认证、403 禁止、404 未找到、500 内部错误。

### 🎓 博士生视角
- HTTP 是应用层文本协议；Node 在底层把 TCP 数据累积并按状态行/头部/空行/主体切分，主体本身是 stream，需手动 'data'/'end' 累积再 JSON.parse（注意背压与大小上限）。
- 状态码首位类别化：2xx 成功、3xx 重定向、4xx 客户端错误、5xx 服务端错误，是客户端/代理做缓存、重试、鉴权决策的依据。
- 响应边界由 Content-Length 或 chunked 分块界定；长度声明错误会导致客户端混淆多条响应，是协议层的硬约束而非语法糖。

### 📚 考研者视角
- 常考「手写一个 HTTP 服务器 / 路由表 / 路径变量提取」。
- 状态码分类（2xx/3xx/4xx/5xx 各自含义）；GET 与 POST 语义契约（GET 安全幂等、POST 非幂等建资源）。
- 易错：为什么必须 res.end()、query string 与 path 的区别、JSON body 解析为何要 try/catch。

## 可运行代码：compose 的洋葱模型

中间件的「进去一圈、出来一圈」由 `next()` 返回 Promise 保证——`await next()` 之后才继续，
那么后置逻辑就必然在**内层全部跑完之后**执行：

```js
function compose(middlewares) {
  return function (ctx) {
    let last = -1;                       // 防止同一个中间件里 next() 被调两次
    function dispatch(i) {
      if (i <= last) return Promise.reject(new Error("next() called multiple times"));
      last = i;
      const fn = middlewares[i];
      if (!fn) return Promise.resolve();
      try {
        return Promise.resolve(fn(ctx, () => dispatch(i + 1)));
      } catch (err) {
        return Promise.reject(err);
      }
    }
    return dispatch(0);
  };
}

const mw = [
  async (ctx, next) => { ctx.log.push("A-in");  await next(); ctx.log.push("A-out"); },
  async (ctx, next) => { ctx.log.push("B-in");  await next(); ctx.log.push("B-out"); },
];

const ctx = { log: [] };
compose(mw)(ctx).then(() => console.log(ctx.log));
// [ 'A-in', 'B-in', 'B-out', 'A-out' ]
```

输出顺序就是洋葱：进入时 A→B，退出时 B→A。`ctx.log` 能被所有中间件共享，是因为**同一个 ctx
对象被逐层传下去**；`last` 这个变量则拦住了「一个中间件里写两次 `await next()`」这种会重复执行
后续链路的写法。错误处理中间件之所以要四个参数 `(err, ctx, next)`，也是因为它是**在 catch 里
被调用的**，参数形态与普通中间件不同——Express 靠 `fn.length === 4` 来识别它。

## 二、中间件模型与 compose（next 传递、错误处理中间件四参数）

中间件是 fn(ctx, next)（Koa）或 fn(req, res, next)（Express）；compose 把数组规约为单函数，靠 next() 串成「洋葱模型」：进入时从外到内，返回时从内到外。错误中间件通过 4 个参数 (err, req, res, next) 被框架识别。

### 🧑‍💻 程序员视角
- 中间件顺序即执行顺序：日志/认证 → 路由 → 错误处理；顺序写错会漏掉鉴权或吞异常。
- 错误处理中间件「必须」四参数 (err, req, res, next)，少一个会被当成普通中间件从而收不到错误。
- async 中间件抛错不会自动进错误中间件：await 包 try/catch 调 next(err)，或捕获 Promise rejection 调 next(err)；Koa 用 ctx，Express 用 (req,res,next)，不要混签名。

### 🎓 博士生视角
- 中间件链是责任链模式的变体；compose 用递归 next 把数组折叠为单函数，每次 next() 推进到下一个中间件，对应调用栈的逐层展开与回卷（洋葱模型）。
- 错误中间件依赖「err 参数存在与否」区分：框架在 next(err) 时跳过普通中间件，直接寻找形参长度为 4 的函数；这是靠函数 arity 做的协议约定，而非类型系统。
- async 错误需手动传递，因为 EventEmitter/回调风格无法跨异步边界自动冒泡 reject，是 JS 错误模型与回调调度耦合的结果。

### 📚 考研者视角
- 笔面题：写出中间件执行顺序（洋葱：A in → B in → B out → A out）；错误处理中间件为什么是 4 参数。
- 易错：Koa 与 Express 中间件签名差异；async 函数 reject 不会自动被 4 参数错误中间件捕获。
- 经典陈述：next(err) 触发错误传播链，错误中间件负责收口并返回 500/错误体。
