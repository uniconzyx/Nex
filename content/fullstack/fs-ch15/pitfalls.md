# fs-ch15 · Go + Gin 后端：并发模型、接口契约与 Java 路线对照 · 常见错误

1. **goroutine 泄漏：开了没退出条件** —— 错在：`go handle(req)` 里有个 `for {}` 或阻塞的 channel 操作，但没有任何退出信号。

   *为什么*：goroutine 不会自己消失，泄漏的 goroutine 会一直占内存、占调度，时间长了对齐到 GMP 的 M 也会堆积，最终 OOM 或调度变慢。

   *怎么改*：给 goroutine 配退出信号：用 `context.Context` 的 `Done()` 或关闭的 channel 来通知退出；长驻 goroutine 必须有「何时结束」的明确路径。

2. **多个 goroutine 共享变量却不上锁** —— 错在：N 个 goroutine 直接 `count++` 一个包级变量，以为「反正单进程」。

   *为什么*：Go 里这依然是数据竞争，`go run -race` 直接报警；在真实多核调度下 `count` 结果会小于预期且不可复现。

   *怎么改*：把「+1」作为事件发到 channel，由一个汇总 goroutine 收；或者确需共享时用 `sync.Mutex`/`atomic`，但优先用 channel。

3. **无缓冲 channel 没人接收导致永久阻塞** —— 错在：往一个无缓冲 channel `send`，但接收方永远没启动或提前退出了。

   *为什么*：无缓冲 channel 的 send 会一直阻塞等待会合，发送方 goroutine 卡死（也是一种泄漏）；若接收方已退出，发送方永远等不到。

   *怎么改*：明确收发双方的生命周期；用 `select` + `default` 或带超时的 `time.After` 避免永久阻塞；发送前确认接收方已就绪或会用 `close` 收尾。

4. **A Tour of Go 式误用：向已关闭的 channel 发送** —— 错在：多个生产者往同一个 channel 发，其中一个 `close` 了，另一个还在 `send`。

   *为什么*：向已关闭的 channel 发送会 `panic`（send on closed channel），且这个 panic 会炸掉整个 goroutine 甚至进程（若没 recover）。

   *怎么改*：关闭 channel 的责任要唯一：只让「唯一的发送方」或「协调者」关闭；多生产者场景用 `sync.WaitGroup` 等全部发完再由唯一方关闭。

5. **Gin 中间件 Abort 后还写 Next，请求仍被放行** —— 错在：鉴权失败调了 `c.Abort()`，后面又调了 `c.Next()`，期望「已经中断」。

   *为什么*：Abort 只是置「后续不再执行」标记，但本次 `Next()` 仍会触发链上下一个，导致本应被拦的请求继续走到 handler。

   *怎么改*：Abort 之后**不要**再 `c.Next()`；需要提前返回就直接 `return`，让中间件函数结束。

6. **Gin 中间件顺序排错造成安全漏洞** —— 错在：把限流中间件注册在认证中间件之前。

   *为什么*：未认证请求会先打到限流，攻击者可用大量未认证请求把限流配额打满，使正常用户也被拒；也可能绕过某些依赖认证上下文的逻辑。

   *怎么改*：按「先认证再限流/鉴权」的顺序注册；把安全相关中间件排在最前，顺序即策略。

7. **把 error 当异常忽略：`if err != nil { return }` 吞掉** —— 错在：拿到 err 后只 `return` 不包装、不记录，调用方拿到 `nil` 以为成功。

   *为什么*：错误在中间层被静默吞掉，上游无法感知失败，最终表现为「偶发无结果」且无法定位根因。

   *怎么改*：至少 `return fmt.Errorf("xxx: %w", err)` 保留链条并向上传；或在该层确有降级策略时显式处理并记录日志。

8. **用 panic 处理可预期的失败** —— 错在：网络超时、下游返回错误码时也 `panic`，指望 recover 中间件兜住。

   *为什么*：panic/recover 本用于不可恢复状态，滥用会让控制流混乱、性能差，且一个漏兜的 panic 直接 500 甚至崩进程；也无法像 error 那样被精细地 `errors.Is` 判断。

   *怎么改*：可预期的失败一律 `error` 返回让上层降级；只在「配置缺失、穷尽性被破坏」等不可能状态才 panic。

9. **Java 思维定义「提供方接口」，导致过度耦合** —— 错在：在公共库里定义一个大 `interface Service { A(); B(); C(); ... }`，要求所有实现类 `implements`。

   *为什么*：Go 的惯用法是「消费者定义小接口」，大接口强迫实现方暴露它根本用不到的方法，耦合度高、难 mock、难替换。

   *怎么改*：把接口拆小、在使用方按「只用到的方法」定义；任何满足方法集的类型自动可用，无需 implements 声明。

10. **goroutine 里 panic 没 recover 炸整个进程** —— 错在：在 `go func(){ ... }()` 里直接 panic，外层没 `defer recover()`。

   *为什么*：goroutine 的 panic 不会被主 goroutine 的 recover 捕获，会一路冒泡到 runtime 导致进程退出（除非该 goroutine 自己 recover）。

   *怎么改*：在 goroutine 入口 `defer func(){ if r:=recover(); r!=nil { log.Println(r) } }()`；或确保只在主流程用 panic。

11. **`context` 用 `Background()` 又没传超时** —— 错在：所有请求都 `context.Background()`，下游超时/取消信号传不进来。

   *为什么*：`Background` 是不可取消的根；若不基于它派生带 `WithTimeout`/`WithCancel` 的 child，整个调用链无法超时，容易 goroutine 与连接堆积。

   *怎么改*：请求入口用 `context.WithTimeout(ctx, 3*time.Second)` 派生；把 ctx 一路透传，不在中间随意 `Background()`。

12. **`sync.WaitGroup.Add` 放在 goroutine 内部** —— 错在：`go func(){ wg.Add(1); do() }()`，main 在 `wg.Wait()` 时可能 Add 还没执行。

   *为什么*：`Add` 必须在启动 goroutine 之前（或已持有 WaitGroup 引用时）调用，否则 `Wait` 可能在计数器仍 0 时就返回，或发生并发 Add 竞争。

   *怎么改*：在 `go` 之前 `wg.Add(1)`；或在已知固定数量时用循环先 Add 完再启动。

13. **`defer` 在循环里堆积** —— 错在：`for { defer f.Close() }` 把成百上千个 defer 推到函数返回时才执行，文件描述符耗尽。

   *为什么*：defer 在函数退出时统一执行，循环里不断追加会撑爆 fd/内存，且顺序 LIFO 难预期。

   *怎么改*：把循环体抽成函数，让 defer 在每次迭代的函数返回时立即生效；或显式 `Close()` 不依赖 defer。

14. **`range` 遍历时取地址拿到同一变量** —— 错在：`for _, v := range slice { go func(){ use(&v) }() }`，所有 goroutine 共享同一个 `v` 地址，拿到最后的值。

   *为什么*：`range` 的循环变量在每次迭代复用同一地址，goroutine 异步读时循环已结束，`v` 是末值。

   *怎么改*：循环内 `v := v`（或传参 `go func(v T){...}(v)`），让每个 goroutine 捕获各自的副本。

15. **`http.Response.Body` 没关导致连接泄漏** —— 错在：`resp, _ := http.Get(url)` 拿到 resp 后直接用，没 `defer resp.Body.Close()`。

   *为什么*：不关 Body 会让底层 TCP 连接无法复用/释放，高并发下 fd 耗尽、请求卡住。即使不读 body 也要关。

   *怎么改*：`defer resp.Body.Close()` 紧跟 `http.Get`；读完后也确保关闭，或用 `io.Copy(io.Discard, resp.Body)` 排空再关。
