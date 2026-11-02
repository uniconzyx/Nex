# fs-ch15 · Go 并发与 Gin 实战代码片段

> Go + Gin 的最小可运行片段，覆盖 goroutine/channel、context、中间件、error 作为值。

### goroutine + channel 汇总

```go
func sum(nums []int) int {
    ch := make(chan int, len(nums))
    for _, n := range nums {
        go func(v int) { ch <- v * v }(n) // 每个 goroutine 捕获副本
    }
    total := 0
    for range nums { total += <-ch }
    return total
}
```

### context 取消信号

```go
func worker(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            return // 收到取消，退出 goroutine
        default:
            // 做点事
        }
    }
}
// 调用方：ctx, cancel := context.WithTimeout(ctx, 3*time.Second); defer cancel()
```

### 用 WaitGroup 等全部完成

```go
var wg sync.WaitGroup
for _, url := range urls {
    wg.Add(1)
    go func(u string) {
        defer wg.Done()
        fetch(u)
    }(url)
}
wg.Wait() // 启动前已 Add 完
```

### Gin 中间件（洋葱链）

```go
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        if !authorized(c) {
            c.AbortWithStatusJSON(401, gin.H{"error": "unauthorized"})
            return // Abort 后直接 return，不要 Next()
        }
        c.Next()
    }
}
// r.Use(AuthMiddleware(), RateLimit())  // 先认证再限流
```

### error 作为值：包装与判断

```go
func load(id string) (*User, error) {
    u, err := repo.Find(id)
    if err != nil {
        return nil, fmt.Errorf("load user %s: %w", id, err) // 保留链条
    }
    return u, nil
}
// 上层：if errors.Is(err, ErrNotFound) { ... }
```

### 消费者定义小接口

```go
type Fetcher interface { Fetch(ctx context.Context, id string) ([]byte, error) }
// 任何满足 Fetch 方法的类型自动可用，无需 implements 声明
type HTTPFetcher struct{ client *http.Client }
func (h *HTTPFetcher) Fetch(ctx context.Context, id string) ([]byte, error) { /* ... */ }
```

### select + 超时避免永久阻塞

```go
select {
case res := <-ch:
    handle(res)
case <-time.After(2 * time.Second):
    log.Println("timeout")
}
```

## 三视角解析
### 🧑‍💻 程序员视角
`goroutine` 泄漏是 Go 服务最常见的内存问题：向无缓冲 channel 发送但没人接收，协程永远阻塞——必须用 `context` 或 `select` + `done` 兜底。`WaitGroup` 的 `Add` 要在启动协程前调用，写在协程内部会与 `Wait` 竞争。`context` 的取消要逐层传递，且「谁创建谁取消」，不要到处 `context.Background()`。Gin 中间件的 `c.Next()` 是洋葱模型的核心，`c.Abort()` 才能中断后续处理。

### 🎓 博士生视角
Go 的并发模型是「CSP：通过通信共享内存」，channel 是「带类型的同步队列」，其阻塞语义由容量决定。`context` 是「取消与超时的传播机制」，它沿调用树向下传递，使「一个请求的所有子任务」能被统一取消。GMP 调度器把 goroutine 映射到 OS 线程，`GOMAXPROCS` 控制并行度；抢占式调度（Go 1.14+）解决了「长循环饿死其他 goroutine」的问题。

### 📚 考研者视角
Go 面试高频：
1. **goroutine 与线程**：用户态调度、栈可增长、创建成本低。
2. **channel**：有缓冲/无缓冲的语义、`close` 的规则（不能向已关闭的 channel 发送）。
3. **`context`**：`WithCancel`/`WithTimeout`/`WithValue` 的用法与传播。
4. **并发安全**：`sync.Mutex`、`sync.RWMutex`、`atomic`、`sync.Map` 的适用场景。
