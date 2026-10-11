# fs-ch05 · 四、API 契约、版本策略与稳定性治理

## 一、契约优先（Design-First）与 OpenAPI

OpenAPI 3.1 是一份 JSON/YAML 文档，描述 `paths`、`operations`、`parameters`、`requestBody`、`responses`、`components.schemas`。两种工作流：

- **代码优先（code-first）**：先写实现，用注解或反射生成文档。上手快，但文档容易滞后于实现，最终出现「文档说 200 实际 422」的漂移。
- **契约优先（design-first）**：先写 OpenAPI，再生成服务端骨架与客户端 SDK。契约成为唯一事实来源，可以做**契约测试**（用文档反查实现是否符合约定）。

本章 ex11 演示「从路由表生成 OpenAPI 3.1 文档」，并输出一组可以自动化断言的判据：

```
operations=4
  GET /articles -> listArticles
  POST /articles -> createArticle
  GET /articles/{id} -> getArticle
  DELETE /articles/{id} -> deleteArticle
unique_operation_ids=true
path_params_always_required=true
every_operation_has_2xx=true
every_4xx_uses_problem_json=true
all_refs_resolve=true
```

这五条断言就是契约测试的最小集合：

1. `operationId` 全局唯一（SDK 生成器靠它命名方法，重名会生成冲突代码）；
2. 路径参数必须 `required: true`（路径参数天然必填，写 false 是文档 bug）；
3. 每个操作至少一个 2xx 响应；
4. 所有 4xx 响应统一 `$ref` 到 `Problem` 且媒体类型为 `application/problem+json`（与本章第三节的错误契约一致）；
5. 所有 `$ref` 都能在 `components` 里解析（没有断链）。

### 🧑‍💻 程序员视角
- 工程落地：用「路由表 → OpenAPI」的生成器（ex11 的思路）保证文档与实现同源，而不是靠人肉同步 YAML；生成物进 CI，diff 即契约变更，需要人工 review。
- 契约测试两层：① 结构层——文档自检（上面五条断言）；② 行为层——按文档构造请求，断言实际响应的状态码与媒体类型与文档一致。
- 事故画像：客户端按文档传 `limit=200`，服务端实际限 100 且静默夹取，客户端以为拿到了全部数据导致漏数据。修复是把边界写进文档（`maximum: 100`）并让客户端能感知（ex04 的夹取策略必须在文档里声明）。
- 版本与文档联动：文档要标出「已废弃（deprecated）」的 operation 与参数，并给出替代项，否则无法推动客户端迁移。

### 🎓 博士生视角
- 契约优先的本质是把**接口的规范性描述提升为一等工件**：一旦文档是输入而不是输出，它就有了独立的生命周期（版本控制、评审、生成代码），这正是「单一事实来源」原则在接口层的应用。
- OpenAPI 的表达力边界：它描述的是**接口形状**（结构、媒体类型、状态码），不描述时序语义（如「先建订单再扣库存」）。所以文档齐全也无法表达业务不变量，这是它与其他接口描述语言（如带时序语义的形式化规范）的本质分工。
- `$ref` 与组件复用带来**引用图的正确性问题**：组件化让描述可复用，但也引入断链风险与循环引用，因此「引用可解析」必须是可自动验证的不变量（ex11 的 `all_refs_resolve=true`）。
- 生成的 SDK 与「语义等价」：从文档生成的客户端只保证结构层等价，无法保证语义等价（如重试策略、幂等键的正确使用）。这也是为什么幂等这类语义必须写进文档的描述字段与运维手册，而不是指望代码生成。

### 📚 考研者视角
- **面试/笔试考点**：简答「OpenAPI 是什么、与 Swagger 的关系」。标准答法：OpenAPI 是规范（原 Swagger Specification 捐赠给 OpenAPI Initiative 后更名），Swagger 现指围绕该规范的一套工具（Swagger UI / Editor / Codegen）。不要把工具名当规范名。
- **口径**：`operationId` 唯一、路径参数必填、响应按状态码分组——这三条是文档评审的硬性检查项，也是笔试题常考的「文档完整性」清单。
- **易混点**：`parameters` 的 `in` 取值（path / query / header / cookie）；`requestBody` 只在 OpenAPI 3.x 出现，2.0（Swagger 2.0）用 body/formData 参数表达。
- **延伸**：契约测试（consumer-driven contract）与本章的版本策略是同一主题的两面：契约越明确，版本升级越可预测。

## 二、版本策略：URL 版本 vs 媒体类型/Header 版本

三条主流路线及其代价：

| 策略 | 形态 | 优点 | 代价 |
|---|---|---|---|
| URL 版本 | `GET /v1/articles` | 显式、可被默认缓存、访问日志直接可见版本、浏览器可直接测 | 同一资源有多个 URI（身份被污染）；版本无法在同一 URI 内协商 |
| 媒体类型版本 | `Accept: application/vnd.articles.v2+json` | URI 稳定、符合内容协商 | 必须配合 `Vary: Accept`，否则共享缓存会串版本；浏览器手测不便 |
| 自定义 Header 版本 | `API-Version: 2` | 实现最简单、URI 干净 | 自定义头不参与默认缓存键；跨域预检与调试成本高 |

本章 ex12 用同一张路由表跑两种解析器，暴露了真正的问题不在「选哪种」，而在「缺省版本」与「未知版本」必须显式定义：

```
request GET /v3/articles  headers={}
  url_strategy    version=v3 handler=- note=no such route in v3
  header_strategy version=v1 handler=v1.listArticles note=matched      # 静默回退到默认 v1

request GET /articles     headers={"accept":"application/vnd.articles.v2+json"}
  url_strategy    version=- handler=- note=no /vN prefix
  header_strategy version=v2 handler=v2.listArticles note=matched

request GET /articles/9   headers={"api-version":"v9"}
  header_strategy version=v9 handler=- note=no such route in v9
```

同一路径 `/v3/articles` 在 URL 策略下是「版本不存在」，在 Header 策略下却悄悄回退到 v1。若线上两种策略同时开着（很常见的迁移中间态），就会出现「同一个 URL 返回不同版本的响应」这种极难排查的事故。

### 🧑‍💻 程序员视角
- 选择口径：**对外公开 API 用 URL 版本**（可观测性优先，日志、缓存、排障都省事）；**内部服务间用媒体类型或 Header 版本**（URI 稳定，网关能统一处理）。选一条，不要两条并存。
- 无论选哪条，必须显式定义三件事：① 缺省版本是什么；② 未知版本是报错（404/406）还是回退；③ 已废弃版本的下线时间与通知机制。
- 兼容性优先于版本号：能加字段、加可选参数解决的变更就不要升版本（新增字段属于兼容变更，删除/改语义才需要新版本）。版本是最后手段，不是第一手段。
- 事故画像：新增 `Vary: Accept` 之前就上线了媒体类型版本，导致 CDN 把 v2 的响应缓存后返回给了 v1 客户端。根因是缓存键没包含 Accept，修复是补 `Vary` 或改用 URL 版本。

### 🎓 博士生视角
- 版本化本质上是对「资源标识的稳定性」与「表示的可协商性」的权衡：URL 版本把版本编码进标识（标识不再稳定，但可缓存性最好）；媒体类型版本把版本放进表示协商（标识稳定，但依赖缓存的 `Vary` 机制正确实现）。
- 缓存的正确性条件：HTTP 缓存键默认包含方法与 URI，媒体类型版本必须通过 `Vary: Accept` 显式扩展缓存键，否则「同一个 URI 的不同表示」会互相污染。这是协议层机制（缓存键构造）与设计选择耦合的典型例子。
- 未知版本的处理语义：理论上「客户端请求了服务端不支持的表示」更贴近 406 Not Acceptable（无法产出可接受的表示），而「路径不存在」才是 404。两种选择都有实践，但必须在文档里声明，因为客户端的重试与降级逻辑依赖它。
- 与演进策略的关系：向后兼容的加性变更（additive change）在类型论上对应「子类型关系保持」，因此不需要新版本；破坏性变更对应「类型不再兼容」，必须并行提供新旧两版并给出迁移窗口。这是把「兼容性」形式化为类型关系的实践价值。

### 📚 考研者视角
- **面试考点**：简答「API 版本化的几种方式及各自优缺点」。标准答法要覆盖 URL 版本（显式、可缓存、URI 不纯）、Header/媒体类型版本（URI 稳定、需 Vary、难调试）两大类，并补一句「兼容性变更不应触发版本升级」。
- **口径**：`Vary` 响应头的作用是扩展缓存键，使缓存按指定请求头区分表示；媒体类型版本必须配它。这是 HTTP 缓存章节与 API 设计的联合考点。
- **易混点**：版本号放在 URL 的路径段（`/v1/articles`）与放在查询串（`/articles?version=1`）是两种不同策略，后者更不推荐（语义上是同一资源的参数，却改变了表示结构）。
- **延伸**：语义化版本（SemVer）描述的是库的版本，与 API 版本策略不是一回事，答题时不要把两者混谈。

## 三、限流与超时：稳定性治理的两个基本手段

限流算法对比：

| 算法 | 状态量 | 是否允许突发 | 主要缺陷 |
|---|---|---|---|
| 固定窗口计数器 | 计数 + 窗口起点 | 是（窗口边界可放行 2 倍） | 临界问题上流量翻倍 |
| 滑动窗口日志 | 每请求时间戳 | 是 | 内存 O(请求数) |
| 令牌桶 | `tokens` + `lastRefillAt` | 是（最多到容量） | 需要处理补充与取用的并发 |
| 漏桶 | 队列 + 恒定输出速率 | 否 | 突发被平滑掉，也可能被丢弃 |

令牌桶是最常用的折中：**容量管突发、补充速率管长期**，状态只有两个变量。本章 ex13 用虚拟时钟（显式时间轴，不读墙钟，保证输出确定）跑出三组判据：

```
scenario1_burst: capacity=3 refill=1/s, 5 requests at t=0
  req#1 allowed=true  tokens_left=2
  req#2 allowed=true  tokens_left=1
  req#3 allowed=true  tokens_left=0
  req#4 allowed=false tokens_left=0
  req#5 allowed=false tokens_left=0
  allowed=3 refused=2

scenario2_steady: 5 requests spaced 1000ms
  allowed=5 all_allowed=true

scenario3_burst_then_decay: capacity=2 refill=4/s, 100 requests spaced 50ms
  window1_requests=20 window1_seconds=0.95 allowed=5 rate_per_sec=5.263
  window2_requests=80 window2_seconds=4    allowed=16 rate_per_sec=4
  total_allowed=21 total_refused=79
  window1_upper_bound=5.8 allowed_within_bound=true
  rate_decays_after_burst=true
  steady_rate_equals_refill=true
```

关键读数：瞬时 5 连发只放行 3 个（容量 3 限制突发）；间隔 1s 的请求全部放行；长跑 100 个请求时第一段（0.95s）放行 5 个、实测速率 5.263/s（高于补充速率，因为吃掉了初始容量 2 形成突发），第二段（4s）放行 16 个、速率恰好 4.0/s——**突发会衰减，长期速率收敛到补充速率**。这就是「容量管突发、速率管长期」的实测证据。

超时是**分级预算**，不是单个数字：

```
客户端超时  >  网关/负载均衡超时  >  服务端请求总超时  >  单个下游调用超时  >  单条 SQL 超时
```

三条工程约束：
1. 任一级超时必须能**取消下游**（连接中断要向下传播），否则队列堆积、资源被已放弃的请求占住。
2. 超时与重试必须联动：只有幂等请求可自动重试，且要有退避与次数上限；非幂等请求的重试必须带幂等键（第一节）。
3. 限流要与协议协同：429 响应应带 `Retry-After`（ex06 实跑输出 `Retry-After: 30`），让客户端按指示退避，而不是立刻重试把下游打穿。

### 🧑‍💻 程序员视角
- 限流维度选择：按「用户 / API Key / IP / 全局」分别设阈，并在响应头返回配额信息（`Retry-After`、剩余量），让客户端自适应；只做全局限流会让单个异常客户端拖垮所有用户。
- 状态存储：单机令牌桶在内存即可；多实例部署必须用共享存储（Redis + Lua 原子脚本）或「本地桶 + 定期同步」，否则每个实例各放行一份配额。这个决定直接影响限流是否真的生效。
- 超时预算落地：给每个下游调用设置「剩余预算」而不是固定值（若请求总预算 1s 且已用 800ms，下游调用最多 200ms），避免超时叠加把总响应拖到最坏情况之和。
- 事故画像：只设了客户端超时（5s），服务端没有超时，客户端断开后服务端仍在跑重查询，连接池与 CPU 被占满，形成雪崩。修复是补齐服务端与 SQL 层超时并使超时可取消。

### 🎓 博士生视角
- 令牌桶的形式化：以速率 r 连续补充、容量 C 为上限的桶，允许的长期平均速率 ≤ r，瞬时突发 ≤ C。这是「漏桶（恒定输出）」与「允许突发」两类需求的分界：漏桶输出严格平稳，令牌桶把突发预算显式参数化。
- 固定窗口的临界问题可以用反例证明：窗口 1s、阈值 100，在 t=0.99s 打 100 个、t=1.01s 再打 100 个，两个计数分属不同窗口，实际在 0.02s 内放行 200 个，是阈值的 2 倍。滑动窗口与令牌桶都可以消除这一现象。
- 分布式限流的根本困难是**原子性与时钟**：读-改-写必须原子（否则并发请求各自读到旧令牌数），且依赖时钟单调性（NTP 回拨会让补充量计算出错）。这正是实践中用 Lua 脚本 + 单调时钟的原因。
- 超时的理论依据是「队列稳定性」：若到达率 λ 长期大于服务率 μ，队列长度无界增长；超时把「等待时间」截断为有限值，从而让队列在超载时保持有界（代价是丢弃/失败请求）。因此超时不是可选优化，而是系统在过载下不崩溃的必要条件。

### 📚 考研者视角
- **面试考点**：简答「常见限流算法及区别」——必须能说出固定窗口 / 滑动窗口 / 漏桶 / 令牌桶四类及各自是否允许突发；追问「分布式限流怎么实现」——答共享存储 + 原子操作（Redis + Lua）。
- **口径**：令牌桶的两参数是「容量（burst）」与「补充速率（rate）」；漏桶的关键是「输出速率恒定」，因此不允许突发。把两者说反是常见失分点。
- **易混点**：限流（rate limiting，控制速率）与熔断（circuit breaking，失败率超标后快速失败）、降级（返回兜底内容）是三种不同机制，常被合并出题，答题要分开定义。
- **延伸**：`Retry-After` 头参与「客户端退避」；与 HTTP 缓存章节的 `Cache-Control: max-age` 不同，前者控制重试时机，后者控制缓存新鲜度。

## 三视角小结
| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| OpenAPI 契约 | 路由表生成文档进 CI；契约测试两层 | 描述边界（形状 vs 时序）、引用图不变量 | OpenAPI 与 Swagger 的关系、文档完整性清单 |
| 版本策略 | 对外 URL 版本、内部 Header 版本；显式定义缺省与未知版本 | 标识稳定性 vs 表示协商、缓存键与 Vary、兼容性即类型关系 | 各版本策略优缺点、Vary 的作用 |
| 限流与超时 | 多维限流、共享存储、超时预算可取消 | 令牌桶形式化、原子与时钟、队列稳定性 | 四类限流算法、限流/熔断/降级辨析 |
