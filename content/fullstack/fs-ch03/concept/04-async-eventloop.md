# 04 · 事件循环、Promise 与 async/await

## 一、事件循环：单线程如何不卡死

JavaScript 是**单线程**，靠**事件循环（Event Loop）**调度异步任务。运行时有一条**调用栈（call stack）**和若干队列：

- **宏任务（macrotask）**：`setTimeout` / `setInterval` / I/O / `setImmediate` / UI 渲染等。
- **微任务（microtask）**：`Promise.then/catch/finally` 的回调、`queueMicrotask`、Node 的 `process.nextTick`（优先级更高）、`await` 之后的继续。<br>
**每轮事件循环**：先清空调用栈，然后**一次性清空整个微任务队列**（含清空过程中新加入的微任务），再取一个宏任务执行，如此往复。因此「微任务优先于宏任务」「微任务之间连续执行」。

## 二、Promise / async / await 与组合子

- **Promise 状态机**：`pending → fulfilled`（带值）或 `pending → rejected`（带原因）。状态一旦落定**不可再变**；`then(onFulfilled, onRejected)` 返回新的 Promise，回调的返回值经 `Promise.resolve` 归一化（thenable 会被「展开」）。
- **async/await**：`async` 函数永远返回 Promise；`await` 把后续代码挂起为微任务，等价于 `promise.then(后续)`。`try/catch` 能直接捕获 `await` 的 reject。
- **四个组合子**：
  - `Promise.all`：全部 fulfilled 才 fulfilled（值为数组）；**任一 rejected 立即 reject**——`Promise.all([ok, Promise.reject])` 直接走 catch。
  - `Promise.allSettled`：**永远 fulfilled**，结果为每个的 `{status:'fulfilled'|'rejected', value|reason}` 数组，用于「不关心成败、都要结果」。
  - `Promise.race`：**第一个落定**（无论成败）即采用其结果。
  - `Promise.any`：**第一个 fulfilled** 即采用；全部 rejected 才 reject（`AggregateError`）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 绝不要写「同步阻塞」长循环（如大数组 O(n^2)）卡死主线程；把大任务拆成 `Promise` 微任务或交给 Worker。
- `Promise.all` 适合「并行多个独立请求」，但任一失败就整体失败——若需要「部分失败也继续」用 `allSettled`。
- `await` 后的代码是微任务，别以为 `await` 是同步的；连续 `await` 串行会拖慢，可先 `Promise.all` 并行再 `await`。
- 错误处理：async 函数里推荐 `try/catch`；全局兜底加 `unhandledrejection` 监听，防止静默丢失 reject。

### 🎓 博士生视角
- 事件循环是规范里的 **Jobs and Job Queues**：Promise 的 reactions 进 **PromiseJobs** 队列（微任务），`setTimeout` 的回调由 **Timer** 在后续迭代进宏任务队列。
- `await x` 的规范语义：`x` 经 `Promise.resolve` 归一化为 Promise，注册后续为 then 回调（微任务）；`await undefined/null` 会被当作已决议的 Promise 立即入队。
- `thenable 解析过程（Promise Resolve Thenable）`：当一个 thenable（有 `then` 方法的对象）被 `resolve`，引擎会递归调用其 `then` 以「展开」它，这是手写 Promise 兼容链的关键，也是 `Promise.resolve({then(){...}})` 特殊行为的来源。
- `Promise.all` 的 reject 是「第一个 reject 胜出」：内部对每个 promise 注册回调，任一 reject 立即 reject 聚合 Promise。

### 📚 考研者视角
- **笔面标准问法**：事件循环输出顺序题（同步→微任务→宏任务）、`Promise.all/race/any/allSettled` 区别、async 函数返回值、`await` 后面是什么。
- 易错口径：`setTimeout(fn, 0)` 不会「立刻」执行，它进宏任务队列，要等当前调用栈与**所有**微任务清空后才轮到；`Promise.then` 一定早于 `setTimeout`。
- 经典陈述题：「微任务队列每轮被清空」——这正是 `queueMicrotask` 嵌套也能在下一轮宏任务前全部跑完的原因。
- `async function f(){ return 1 }` 返回的是 `Promise.resolve(1)`，不是 `1`。
