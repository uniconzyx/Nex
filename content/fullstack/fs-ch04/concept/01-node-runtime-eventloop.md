# fs-ch04 · Node 运行时与事件循环


## 一、Node 单线程模型与 libuv 事件循环（六阶段）

Node 的 JavaScript 在主线程的单一调用栈上执行，靠 libuv 提供的事件循环调度异步任务；文件 I/O、DNS、crypto、zlib 等由 libuv 线程池（默认 4 线程）并行完成后，回调进入对应阶段。

### 🧑‍💻 程序员视角
- 单线程不等于「全程一个线程」：JS 层单调用栈，底层有线程池分工，避免把同步 API（fs.readFileSync）放进请求路径卡死主线程。
- CPU 密集任务会饿死事件循环：用 worker_threads 卸载到独立线程，用 cluster 在主进程 fork 多个 worker 以利用多核（每 worker 一个独立事件循环）。
- 生产里长任务要「让出事件循环」：分批 + setImmediate/process.nextTick，避免一次占满调用栈导致所有 I/O 延迟。

### 🎓 博士生视角
- libuv 事件循环固定六阶段：timers → pending callbacks → idle/prepare → poll → check → close callbacks；每阶段有独立 FIFO 队列，阶段内按顺序清空，阶段间切换时先清空微任务与 nextTick 队列。
- timers 阶段执行 setTimeout/setInterval 回调；poll 阶段检索并处理新 I/O 事件、决定阻塞时长；check 阶段执行 setImmediate；close 阶段触发 close 事件。
- 「单线程」是 JS 执行层的抽象边界：超出该边界的系统调用级并行由 libuv 线程池承担，这是 Node 既单线程又能高并发 I/O 的形式化依据。

### 📚 考研者视角
- 笔面标准问法：Node 为什么适合 I/O 密集、不适合 CPU 密集？事件循环有哪些阶段、顺序如何？
- 易错口径：事件循环「阶段」与「微任务队列」是两回事；微任务（Promise.then）与 nextTick 在阶段切换间隙清空，不在任何阶段内部。
- 常考陈述：给出一段含多个 setTimeout/setImmediate 的代码，要求写出打印顺序（顶层脚本与 I/O 回调内顺序不同）。

## 二、process.nextTick / Promise.then / setImmediate 三者顺序

三者都用于「延迟执行」，但进入的队列与优先级不同：process.nextTick 进 nextTick 队列（优先级最高，独立于微任务），Promise.then 进微任务（PromiseJobs）队列，setImmediate 进事件循环的 check 阶段（宏任务）。

### 🧑‍💻 程序员视角
- 在 I/O 回调里 setImmediate 一定先于 setTimeout(0)；需要「下一轮 check 阶段立即执行」用 setImmediate，需要「最小延迟计时」才用 setTimeout。
- 用 nextTick 做「当前操作之后、任何 I/O 之前」的收尾（如错误抛出前的清理）；但绝不在 nextTick/Promise 里无限递归，否则微任务饥饿（starvation）饿死事件循环。
- API 设计里要让出事件循环时用 setImmediate，不要用递归 nextTick 占满队列。

### 🎓 博士生视角
- 形式化边界：每次「操作」结束后，Node 先清空 nextTick 队列，再清空微任务（PromiseJobs）队列，然后才进入下一事件循环阶段；因此 nextTick > Promise.then > 宏任务（setImmediate / setTimeout）。
- setImmediate 属于 check 阶段（宏任务）；setTimeout(0) 属于 timers 阶段（宏任务）。顶层脚本中由于 0ms 被钳制为 ~1ms，实测 setImmediate 常先于 setTimeout；只有在 I/O 回调（poll 阶段之后进入 check）中顺序才「稳定」为 setImmediate 先。
- 微任务饥饿：持续向 nextTick/微任务队列推入回调，会使事件循环永远无法推进到宏任务阶段，I/O 回调被无限推迟。

### 📚 考研者视角
- 笔面标准题：给出 nextTick / Promise.then / setImmediate / setTimeout(0) 混合代码，预测打印顺序。
- 易错：认为 setTimeout(0) 一定比 setImmediate 早（顶层脚本实测相反）；认为 nextTick 属于事件循环某一阶段（它不属于，优先级最高且独立于阶段）。
- 经典陈述：nextTick 队列优先级高于 Promise 微任务队列，二者都在「阶段之间」清空。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### 事件循环阶段顺序：sync → nextTick → microtask → setImmediate → setTimeout

```js
const fs = require('fs');

const order = [];
const mark = (s) => {
  order.push(s);
  console.log(s);
};

// ---- 第一段：同步代码 + nextTick + Promise ----
mark('A sync');
process.nextTick(() => mark('B nextTick'));
Promise.resolve().then(() => mark('C promise.then'));
mark('F sync-end');

// ---- 第二段：setImmediate vs setTimeout(0) ----
// 关键：这两个必须注册在「I/O 回调内部」才有确定的先后顺序。
// 原因：事件循环顺序是 timers → pending → poll → check → close。
// 在 I/O 回调（poll 阶段）里注册，本轮 poll 结束后立刻进入 check 阶段，
// 所以 setImmediate 先执行；而 setTimeout(0) 要等下一轮 timers 阶段。
// 若注册在顶层同步代码里，则先进入哪一轮由事件循环启动时机决定，顺序不保证。
fs.readFile(__filename, () => {
  setImmediate(() => mark('E setImmediate'));
  setTimeout(() => {
    mark('D setTimeout');
    console.log('nextTick 先于 promise: ' + (order.indexOf('B nextTick') < order.indexOf('C promise.then')));
    console.log('setImmediate 先于 setTimeout: ' + (order.indexOf('E setImmediate') < order.indexOf('D setTimeout')));
  }, 0);
});
```

实际输出：

```text
A sync
F sync-end
B nextTick
C promise.then
E setImmediate
D setTimeout
nextTick 先于 promise: true
setImmediate 先于 setTimeout: true
```

> 出处：`examples/ex01-event-loop-order.json`。改一处再看输出变没变，比读三遍解释有用。

### 用内置 http 从零手写迷你 REST 服务器（路由表 / 路径变量 / JSON body / 状态码）

```js
const http = require('http');
const db = [{ id: 1, name: 'alpha' }, { id: 2, name: 'beta' }];
const routes = [];
function route(method, pattern, handler) {
  const keys = [];
  const rx = new RegExp('^' + pattern.replace(/:(\w+)/g, (_, k) => { keys.push(k); return '([^/]+)'; }) + '$');
  routes.push({ method, rx, keys, handler });
}
function match(method, path) {
  for (const r of routes) {
    if (r.method !== method) continue;
    const m = r.rx.exec(path);
    if (m) { const params = {}; r.keys.forEach((k, i) => params[k] = m[i + 1]); return { handler: r.handler, params }; }
  }
  return null;
}
route('GET', '/items', (req, res) => { res.writeHead(200, {'Content-Type':'application/json'}); res.end(JSON.stringify(db)); });
route('GET', '/items/:id', (req, res, params) => {
  const item = db.find(x => String(x.id) === params.id);
  if (!item) { res.writeHead(404, {'Content-Type':'application/json'}); res.end(JSON.stringify({error:'not found'})); return; }
  res.writeHead(200, {'Content-Type':'application/json'}); res.end(JSON.stringify(item));
});
route('POST', '/items', (req, res, params, body) => {
  const item = { id: db.length + 1, name: body.name };
  db.push(item);
  res.writeHead(201, {'Content-Type':'application/json'}); res.end(JSON.stringify(item));
});
const server = http.createServer((req, res) => {
  let data = '';
  req.on('data', c => data += c);
  req.on('end', () => {
    const body = data ? JSON.parse(data) : {};
    const found = match(req.method, req.url.split('?')[0]);
    if (!found) { res.writeHead(404, {'Content-Type':'application/json'}); res.end(JSON.stringify({error:'no route'})); return; }
    found.handler(req, res, found.params, body);
  });
});
server.listen(0, () => {
  const port = server.address().port;
  const get = (path, cb) => {
    const r = http.request({ port, method:'GET', path, headers:{'Connection':'close'} }, res => {
      let out = ''; res.on('data', c => out += c); res.on('end', () => cb(res.statusCode, out));
    });
    r.end();
  };
  const post = (path, payload, cb) => {
    const body = JSON.stringify(payload);
    const r = http.request({ port, method:'POST', path, headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(body),'Connection':'close'} }, res => {
      let out = ''; res.on('data', c => out += c); res.on('end', () => cb(res.statusCode, out));
    });
    r.write(body); r.end();
  };
  get('/items', (code, out) => {
    console.log('GET /items -> ' + code + ' ' + out);
    get('/items/2', (code2, out2) => {
      console.log('GET /items/2 -> ' + code2 + ' ' + out2);
      get('/items/999', (code3, out3) => {
        console.log('GET /items/999 -> ' + code3 + ' ' + out3);
        post('/items', {name:'gamma'}, (code4, out4) => {
          console.log('POST /items -> ' + code4 + ' ' + out4);
          server.close();
        });
      });
    });
  });
});
```

实际输出：

```text
GET /items -> 200 [{"id":1,"name":"alpha"},{"id":2,"name":"beta"}]
GET /items/2 -> 200 {"id":2,"name":"beta"}
GET /items/999 -> 404 {"error":"not found"}
POST /items -> 201 {"id":3,"name":"gamma"}
```

> 出处：`examples/ex02-http-rest.json`。改一处再看输出变没变，比读三遍解释有用。

