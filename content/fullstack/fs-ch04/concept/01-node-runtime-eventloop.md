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
