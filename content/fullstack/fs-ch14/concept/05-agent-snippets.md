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

## 三视角解析
### 🧑‍💻 程序员视角
SSE 透传 LLM 流式响应时，要注意「逐块转发而非缓冲」：中间层若开了 `compression` 或缓冲，用户会看到「卡很久然后一次性出完」。长任务要设计状态机 + 断线重连：客户端带 `task_id` 重连，服务端从断点续推，而不是从头再来。`tool_call` 必须有幂等键——模型可能重复调用同一个工具，没有幂等就会重复扣款/重复下单。审计日志要记录「模型输入、输出、工具调用、耗时、token 数」，出问题时才有据可查。

### 🎓 博士生视角
Agent 与前端的接缝本质是「不确定性的后端 + 有状态的前端」，其核心挑战是「可观测性与可恢复性」。流式协议（SSE）天然单向，双向交互需 WebSocket 或「SSE + 独立 POST」，后者更易穿过代理与网关。工具调用的幂等性设计要沿用分布式系统的老办法：幂等键 + 去重表 + 状态机，模型只是「不可靠的调用方」，不能假设它不会重复。

### 📚 考研者视角
AI 应用/全栈面试高频：
1. **流式协议**：SSE 与 WebSocket 的差异、代理与缓冲的影响、心跳保活。
2. **长任务**：状态机设计、断点续传、超时与取消。
3. **工具调用**：幂等键、参数校验、权限边界（模型不能直接执行任意操作）。
4. **审计与合规**：日志留存、敏感信息脱敏、用户可追溯。

```text
05-agent-snippets.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 流式响应（SSE 透传）  (ts)
    |
    v
  [02] 长任务状态机与重连  (ts)
    |
    v
  [03] tool_call 幂等键  (ts)
    |
    v
  [04] 审计日志落库  (ts)
    |
    v
  [05] 成本与限流中间件  (ts)
    |
    v
  [06] 降级开关热更新  (ts)
    |
    v
  [07] 背压与排队  (-)
    |
    v
  [08] 断点续传 chunk 恢复  (-)
    |
    v
  [... 其余 2 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
