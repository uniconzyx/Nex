# 模型接入：把「调一次 API」当成一次外部依赖治理

> 这一章所有内容都建立在一个事实上：**模型服务不是函数，是一个有配额、有延迟分布、
> 会部分失败、会按 token 收费的远程依赖。**
> 你在业务代码里写下的每一行 `client.chat(...)`，都要回答四个问题：超时多少、失败怎么办、
> 并发多少、这次花了多少钱。

## 1. 鉴权与密钥管理：密钥不是配置，是资产

主流厂商都用 `Authorization: Bearer <key>`。真正的工程问题不在 header 怎么写，而在**密钥怎么不进代码库**。

| 做法 | 风险 | 适用 |
|---|---|---|
| 硬编码在源码 / 提交 `.env` | 一旦推到 GitHub，几分钟内就会被扫描并盗刷 | 任何环境都不允许 |
| 环境变量 + 启动时校验 | 进程环境可被同机其他进程读取 | 单机开发、临时验证 |
| 密钥管理服务（KMS/Vault）+ 短期令牌 | 接入成本高，但可审计、可轮换 | 生产环境 |
| 网关代持（业务只调内部网关） | 网关成为单点，需要高可用 | 多业务共享配额时 |

工程口径：

- **最小权限 + 分环境**：开发/测试/生产三把钥匙，各自独立配额；测试钥匙泄露不影响生产账单。
- **可轮换**：客户端支持同时持有新旧两把钥匙，轮换时灰度切流，而不是停服改配置。
- **不落日志**：请求日志里只记录 key 的指纹（如 `sha256(key)[:8]`），不记录明文；
  错误上报前做一次 header 脱敏。
- **配额与告警绑定**：给每个 key 设日预算，超过 80% 告警，超过 100% 自动停用——
  被盗刷时，止损靠的是配额而不是「发现得早」。

```python
# 启动时校验，缺失就 fail fast，不要等到第一个请求才 401
import os

def load_key(env: str) -> str:
    key = os.environ.get(f"LLM_API_KEY_{env.upper()}")
    if not key or not key.startswith("sk-"):
        raise RuntimeError(f"missing/invalid key for env={env}")
    return key

# 日志里只留指纹
import hashlib
def fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:8]
```

> 经验判断：把「密钥轮换」写进 runbook 的团队不到一半；真正出事时，能否在 10 分钟内换钥匙，
> 比有没有做密钥加密更能决定损失大小。

## 2. 流式（SSE）与超时：两个阈值，不是一 个

流式响应的协议是 Server-Sent Events：服务端持续写 `data: {...}\n\n`，客户端按行读取。
它带来两个必须分开设的超时：

- **首字超时（TTFT, time to first token）**：从发出请求到收到第一个有效 token。
  它决定用户是否觉得「卡住了」，通常设 2~5 秒。
- **总超时**：从请求开始到流结束。它决定资源占用上限，通常按最大输出长度估：
  `总超时 ≈ 首字超时 + max_tokens / 输出速度`，再留 1.5 倍余量。

只设总超时会导致：模型排队 30 秒才开始吐字，用户盯着空白页，最后虽然「成功」但体验已经失败。
只设首字超时会导致：模型一直慢慢吐字，连接占用十分钟。

SSE 解析的三条硬规则（示例 ex03 用真实形状的流做过验证）：

1. **按行缓冲，不按网络包缓冲**。一个 JSON 可能被切成 3 个 TCP 包，也可能 5 个事件挤在一个包里。
2. **`data:` 可以多行**，按 SSE 规范用 `\n` 拼接后再 `json.loads`。
3. **`[DONE]` 与 usage 是独立事件**：最后一个 chunk 常常是空 `choices` + `usage`，
   只读 `delta.content` 会丢掉计费数据。

```python
buf, data_lines = "", []
for chunk in transport:                 # transport 是任意切分的字节/字符串流
    buf += chunk
    while "\n" in buf:
        line, buf = buf.split("\n", 1)
        line = line.rstrip("\r")
        if line == "":                  # 空行 = 一个事件结束
            if data_lines:
                payload = "\n".join(data_lines)
                data_lines = []
                if payload == "[DONE]":
                    break
                yield json.loads(payload)
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
```

超时的时间预算要写进 SLA，而不是散落在代码里：

```
用户可接受等待 W = 3s（首字）
  ├─ 连接/排队 0.5s
  ├─ 首字生成 2.0s
  └─ 余量 0.5s
总预算 T = 15s（含 800 token 输出）
  └─ 超过 T 未结束：主动断开，返回已生成部分 + "继续生成" 按钮
```

## 3. 错误码分类：先决定「能不能重试」，再谈退避

错误处理最常见的写法是 `except Exception: retry(3)`。它把三类完全不同的错误混在一起：

| 类别 | 典型码 | 可重试 | 正确动作 |
|---|---|---|---|
| 鉴权/配置 | 401, 403, model_not_found | 否 | 快速失败、告警、检查密钥与模型名 |
| 入参/策略 | 400, 422, context_too_long, content_filter | 否 | 修请求；超长则截断/分段；命中策略则拒答 |
| 限流 | 429 | 是（看 `Retry-After`） | 退避 + 令牌桶，必要时排队 |
| 过载/网关 | 503, 502, 500 | 是（有限次） | 指数退避 + 熔断 + 降级到备用厂商 |
| 超时 | timeout / 连接重置 | 仅幂等请求 | 短退避重试；非幂等则查状态再决定 |

**指数退避 + 抖动**的标准形式：

```
sleep_n = min(cap, base × 2^(n-1)) × U(0, 1)      # full jitter
```

`U(0,1)` 的作用不是「更随机」，而是**把同一时刻失败的一批客户端打散**。没有抖动时，
100 个客户端会在 200ms、400ms、800ms 同时再次撞向已经过载的服务，形成重试风暴（thundering herd）。
示例 ex02 的模拟里，去相关抖动把同一 100ms 桶内的重试峰值从 100 压到 39。

重试的**边界**比次数更重要：

- 只有**幂等**请求能重试。`POST /chat/completions` 本身无副作用，可以重试；但「扣款」「下单」
  这类包裹在工具调用里的写操作，必须带幂等键（idempotency key），由下游去重。
- 重试预算要计入总超时：3 次重试 × 每次 10 秒 = 30 秒，用户早就走了。
- 重试次数不是越多越好：示例 ex02 中 6 次尝试把成功率从 55% 提到 97%，但 P95 从 1.05s 涨到 3.25s；
  再往上加次数，成功率的边际收益已经很小，尾部延迟继续恶化。

## 4. 令牌桶限流：容量和速率是两个旋钮

令牌桶的两个参数：

- `r`（rate）：每秒补充多少令牌，决定**长期平均吞吐**；
- `C`（capacity）：桶最多存多少令牌，决定**能吸收多长的突发**。

```
tokens = min(C, tokens + r × Δt)
if tokens >= 1: tokens -= 1; allow()
else: reject()  # 或排队
```

一个常被忽略的事实：**C 必须至少覆盖一个到达批次的大小**。示例 ex01 里 `r=5/s, C=1`，
即使长期速率够，稳态每秒仍丢 2 个请求——因为 3 个请求同时到达，桶里最多只有 1 个令牌，
补进来的令牌顶到上限就浪费了。`C/r` 就是系统能吸收的突发时长。

限流的落点也有讲究：

- **客户端限流**保护下游，也保护自己的账单；按「厂商 × 模型」分别建桶。
- **服务端 429** 是事实，不是建议：收到 429 应先看 `Retry-After`，不要盲目指数退避。
- **并发上限**与 QPS 限流不是一回事：长流式请求会长期占用连接，需要独立的并发信号量。

## 5. 幂等与重试边界：一次下单不能变成三次

模型调用本身通常幂等，但 Agent 会调用工具。工具调用的幂等设计：

```python
# 错误：重试时重新生成 request_id，下游无法去重
def charge(order_id, amount):
    return payment_api.charge(order_id, amount)

# 正确：幂等键由业务事实决定，重试复用同一个键
def charge(order_id, amount, attempt):
    key = f"charge:{order_id}:{amount}"     # 不含 attempt
    return payment_api.charge(order_id, amount, idempotency_key=key)
```

判据：**如果这个操作被执行两次，业务上会不会多扣钱/多发消息/多建工单？**
会，就必须幂等；不确定，就按「会」处理。

## 6. OpenAI 兼容层：形状兼容 ≠ 语义兼容

「改个 `base_url` 就能换厂商」是接入层最大的幻觉。真实差异至少有五处：

| 维度 | 常见差异 | 工程后果 |
|---|---|---|
| tool call | `tool_calls[].id` 长度/字符集不同；有的厂商要求把 assistant 的 tool_calls 原样回传 | 回传时丢字段 → 400 或工具结果对不上 |
| JSON 模式 | 有的是 `response_format={"type":"json_object"}`，有的用 `json_schema`，有的只保证「像 JSON」 | 直接 `json.loads` 会偶发失败，必须校验+重试 |
| reasoning | `reasoning_content` 与 `content` 分离，部分厂商不返回思维链 | 把 reasoning 当答案展示 → 用户看到草稿 |
| usage | 缓存命中 token 的字段名不同（`cached_tokens` / `prompt_cache_hit_tokens`） | 成本统计漏项，账单对不上 |
| 停止原因 | `finish_reason` 枚举不一致（`length` / `max_tokens` / `stop`） | 截断被当成正常结束 |

接入层的正确做法是**能力探测 + 适配器**，而不是 if-else 散落在业务里：

```python
CAPS = {                       # 启动时探测一次，落配置
    "vendor_a": {"json_schema": True,  "reasoning": True,  "tool_id_max": 40},
    "vendor_b": {"json_schema": False, "reasoning": False, "tool_id_max": 24},
}

def adapt_tools(vendor, tools):
    if CAPS[vendor]["tool_id_max"] < 40:
        return [{**t, "id": t["id"][:CAPS[vendor]["tool_id_max"]]} for t in tools]
    return tools
```

> 经验判断：切换厂商的返工，80% 不在模型效果，而在 tool call 回传格式、JSON 校验、
> usage 字段这三件事上。接入层把这三件事抽象掉，换厂商才是改配置。

---

## 三视角解析

### 🧑‍💻 程序员视角

- 先写**超时与取消**，再写业务。没有取消的流式接口会在大促时把连接池占满；
  Python 的 `asyncio.timeout` / Go 的 `context.WithTimeout` 要把整条调用链传下去。
- 重试不要写在业务函数里，写在**客户端中间件**：这样所有调用共享同一套策略，
  也能统一打点（`retry_count`、`error_class`）。
- 日志一定要有 `request_id` 和 `trace_id`，并且**在重试时保持不变**——
  否则一次请求的 3 次尝试会变成 3 条互不相关的日志，排障时拼不起来。
- 成本统计放在响应返回处，用厂商返回的 usage，不要用自己估的 token；
  估算是闸门，账单以 usage 为准。
- 密钥不要进镜像、不要进前端、不要进异常堆栈。上线前用 `grep -r "sk-"` 扫一遍仓库。

### 🎓 博士生视角

- 重试的成功率模型：若单次成功概率为 `p`、最多 `n` 次独立尝试，则总成功率 `1-(1-p)^n`。
  但真实失败是**相关**的（过载时所有请求一起失败），独立性假设会高估重试收益；
  这也是为什么熔断（快速失败）比无限重试更有效。
- 指数退避的尾部延迟：full jitter 下第 `n` 次等待服从 `U(0, b·2^{n-1})`，
  期望等待 `b·2^{n-2}`，方差随 `n` 指数增长。它用「更大的方差」换「更小的碰撞概率」，
  是典型的**随机化算法**取舍（类似 CSMA/CD 的二进制指数退避）。
- 令牌桶是漏桶的对偶：令牌桶允许突发（桶里有存货），漏桶强制平滑输出。
  在网络流量整形里，`(r, C)` 对应到达曲线与服务曲线的 `(σ, ρ)` 约束；
  `C/r` 是最大突发时长，这个结论在排队论里对应「突发度」的定义。
- OpenAI 兼容层本质是**接口标准化失败**：厂商竞争导致语义分叉，
  适配器模式只能覆盖可观测差异，无法覆盖「JSON 模式到底多严格」这类行为差异——
  后者只能靠契约测试（contract test）持续验证。

### 📚 考研者视角

- 自命题 AI 专业课常考「API 调用与工程实践」，标准表述要能写出：
  **HTTP 状态码分类（4xx 客户端 / 5xx 服务端）**、**指数退避公式**、**令牌桶的 (r, C) 含义**。
- 常考计算：单次成功率 0.6、最多 3 次重试，总成功率 `1-0.4^3=93.6%`；
  若每次重试平均多花 0.4s，则期望延迟要按几何分布算，不能简单乘 3。
- 易混概念：**限流（rate limiting） vs 熔断（circuit breaking） vs 降级（degradation）**。
  限流是「入口控制流量」，熔断是「下游故障时快速失败」，降级是「用更弱的能力兜底」。
  三者解决的不是同一个问题，答题时不要互相替代。
- 另一个易错点：**SSE 不是 WebSocket**。SSE 是单向、基于 HTTP 的文本流，自带重连与
  `Last-Event-ID`；WebSocket 是双向长连接。流式生成用 SSE 就够了，不需要上 WebSocket。
