# fs-ch04 易错点（Pitfalls）

1. **在顶层脚本里认为 setTimeout(0) 一定先于 setImmediate** —— 实测顶层脚本中 setImmediate 反而先执行（0ms 被钳制为 ~1ms，循环先到 check 阶段）。✅ 需要「下一轮 check 阶段立即执行」用 setImmediate；只在 I/O 回调内顺序才稳定为 setImmediate 先。

2. **process.nextTick 里无限递归导致微任务饥饿** —— nextTick 队列优先级高于微任务与 I/O，递归推入会饿死事件循环、所有 I/O 永久延迟。✅ 让出事件循环改用 setImmediate，避免无限递归推入 nextTick。

3. **用 fs.readFileSync 等同步 API 阻塞主线程** —— 大文件会卡死所有并发请求。✅ 用异步 API，或把重 I/O 放 worker_threads / 改用流分块读取。

4. **HTTP 响应忘了 res.end()** —— 连接一直挂起、客户端超时、连接泄漏。✅ 任何分支都必须 res.end()（或 write 后 end），错误分支也要 end。

5. **手写路由把查询串当路径匹配** —— req.url 含 `?` 之后的查询串，直接拿它做路径匹配会失败。✅ 用 `new URL(req.url, base).searchParams` 取查询，或 `req.url.split('?')[0]` 取纯路径。

6. **Buffer 按字节切片截断多字节字符产生乱码** —— 中文等 UTF-8 变长编码在字节中间切断得到替换符（U+FFFD）。✅ 用字符串 slice / StringDecoder 累积解码，显式指定编码。

7. **中间件里 async 抛错却没传给 next(err)** —— async 函数 reject 不会自动进四参数错误中间件，进程可能 unhandledRejection。✅ await 包 try/catch 调 next(err)，或捕获 Promise rejection 后 next(err)。

8. **错误处理中间件参数少于 4 个** —— 框架靠 `(err, req, res, next)` 四参数识别错误中间件，少参数会被当普通中间件从而收不到错误。✅ 错误中间件签名必须是四参数。

9. **把 CPU 密集任务放主线程** —— 占满调用栈、饿死事件循环，所有 I/O 延迟、请求堆积。✅ 用 worker_threads 卸载 CPU 密集任务；I/O 密集才留主线程。

10. **require 循环依赖拿到 undefined** —— a 未填充完就 require b、b 又 require a，得到半截 exports。✅ 用 ESM 的 live binding，或重构消除循环、延迟到函数内 require。

11. **重赋值 module.exports 后 exports.xxx 失效** —— exports 只是 module.exports 的别名，重赋值 module.exports 后旧别名指向旧对象。✅ 要么只用 `module.exports = {...}`，要么只用 `exports.xxx`，不要混用重赋值。

12. **Writable 忽略 write() 返回的 false 继续狂写** —— 缓冲区无限增长、内存爆。✅ 返回 false 时暂停数据源（source.pause()），监听 'drain' 再 resume()。

13. **JSON body 不限制大小 / 不 try-catch JSON.parse** —— 大 body 致内存溢出，非法 JSON 致 500。✅ 限制请求体大小、用 try/catch 包裹解析、失败返回 400。

14. **认为 Node 是多线程或全程单线程** —— JS 在单调用栈执行，但 libuv 有线程池处理文件/DNS/crypto，worker_threads 还能跑并行 JS。✅ 理解「JS 单线程 + 底层线程池」分工，CPU 任务用 worker_threads。
