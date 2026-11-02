# fs-ch14 · Agent × 全栈接缝实战片段

> 把 §1–§4 的机制落成可跑的最小实现：流式、长任务、幂等、成本。

### 流式响应（SSE 透传）

```ts
app.get('/chat/stream', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream')
  const stream = await llm.chat(req.body, { stream: true })
  for await (const chunk of stream) {
    res.write(`data: ${JSON.stringify(chunk)}\n\n`)
  }
  res.end()
})
```

### 长任务状态机与重连

```ts
type TaskState = 'queued' | 'running' | 'done' | 'failed'
const states: Record<string, TaskState> = {}
// 客户端断线重连用 taskId 拉取最新 state，而非重启任务
app.get('/task/:id', (req, res) => res.json({ state: states[req.params.id] }))
```

### tool_call 幂等键

```ts
async function callTool(name: string, args: any, idempotencyKey: string) {
  const cached = await kv.get(idempotencyKey)
  if (cached) return cached            // 同一 key 直接返回，防重复执行
  const r = await tools[name](args)
  await kv.set(idempotencyKey, r, { ttl: 3600 })
  return r
}
```

### 审计日志落库

```ts
await audit.insert({
  tool: name, args, result: r, userId, ts: Date.now(), key: idempotencyKey,
})
// 审计与业务结果分离存储，便于事后对账与追责
```

### 成本与限流中间件

```ts
app.use(async (req, res, next) => {
  const cost = estimateTokens(req.body)
  if (await budget.exceeded(req.user, cost)) return res.status(429).json({ error: 'budget' })
  await budget.consume(req.user, cost)
  next()
})
```

### 降级开关热更新

```ts
const flags = { queue: true, cacheFallback: false, reject: false }
config.watch('agent.flags', (v) => Object.assign(flags, v))  // 阈值可热更新，免发版
```

### 背压与排队

当并发任务超过 worker 数，用有界队列 + 信号量限流，避免内存被无限堆积的流式缓冲撑爆。

### 断点续传 chunk 恢复

长任务分段落盘，客户端用 `fromChunk` 续传；中断后从最后成功段继续，而非从头。

### 多租户隔离

每个租户独立预算、独立 idempotency 命名空间、独立审计表；跨租户共享 worker 但数据不串。

### 错误分类与重试预算

区分「可重试」（超时/5xx/限流）与「不可重试」（4xx 参数错）；每次调用消耗重试预算，预算耗尽走降级而非无限重试。
