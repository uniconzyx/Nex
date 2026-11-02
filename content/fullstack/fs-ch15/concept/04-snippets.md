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
