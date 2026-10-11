# fs-ch05 · 三、RESTful 资源设计、分页与错误契约

## 一、资源设计：名词复数、方法语义与幂等性

REST 的核心约束是：**用 URI 标识资源、用 HTTP 方法表达对资源的动作**，而方法语义由 RFC 9110 定义，不由开发者自由发挥。

| 方法 | 安全（无副作用） | 幂等（重复执行结果相同） | 典型用途 | 常用成功码 |
|---|---|---|---|---|
| GET | 是 | 是 | 读取集合或单个资源 | 200 |
| POST | 否 | 否 | 在集合下创建、触发不可重复的动作 | 201（带 Location） |
| PUT | 否 | 是 | 整体替换（客户端提交全量表示） | 200 / 204 |
| PATCH | 否 | 否（除非显式定义为幂等） | 部分更新 | 200 / 204 |
| DELETE | 否 | 是 | 删除资源 | 204 |
| HEAD | 是 | 是 | 只要响应头 | 200 |

命名规则：路径段用**小写复数名词**（`/articles`、`/articles/42/comments`），不用动词（`/getArticle` 错），不用驼峰或下划线（`/articleList`、`/user_profile` 错），不带文件扩展名（`/articles.json` 错）。本章 ex01 用纯函数把这些判据跑了一遍：`articles`、`users` 通过，而 `articleList`、`getUsers`、`user_profile`、`article` 全部不通过——这些是可以在 CI 里自动化的断言，不是口头规范。

状态码映射（同样取自 ex01 实跑）：

```
GET    /articles          集合读取      -> 200 (2xx)
POST   /articles          创建成功      -> 201 (2xx)
DELETE /articles/42       删除成功      -> 204 (2xx)
POST   /articles          非法 JSON     -> 400 (4xx)
GET    /articles/999      资源不存在    -> 404 (4xx)
PATCH  /articles/42       唯一键冲突    -> 409 (4xx)
POST   /articles          schema 不过   -> 422 (4xx)
POST   /articles          媒体类型不对  -> 415 (4xx)
GET    /articles          超过配额      -> 429 (4xx)
TRACE  /articles          方法不允许    -> 405 (4xx)
```

幂等性的工程落点是**网络不可靠**：客户端超时重试是常态，所以非幂等的 POST 创建必须配幂等键（`Idempotency-Key` 头）加去重存储。本章 ex07 用内存 Map 模拟：

```
key=k-1  title=alpha  status=201 id=1 replayed=false (executed and cached)
key=k-1  title=alpha  status=201 id=1 replayed=true  (replayed from cache)
key=k-1  title=alpha  status=201 id=1 replayed=true  (replayed from cache)
key=k-2  title=beta   status=201 id=2 replayed=false (executed and cached)
key=k-2  title=changed status=422 id=- replayed=false (rejected)       # 同键换载荷
k-1_executed_once=true
k-1_returns_same_id=true
k-1_reuse_with_new_payload_rejected=true
```

三次相同请求只产生一次副作用，第三次直接回放缓存的响应；同一键换载荷被拒（422）而不是静默复用——这一点常被实现者忽略，会产生「用户改了内容却拿到旧结果」的隐蔽错误。

### 🧑‍💻 程序员视角
- 落地检查清单：每个接口写清「成功码 / 参数错误码 / 未认证码 / 不存在码 / 冲突码」，再拿 ex01 的表逐条对照，避免出现「创建返回 200」「删除返回 200 带空体」这类语义漂移。
- 契约细节（ex02 实跑可验证）：201 必须带 `Location`（输出里 `loc=/articles/3`）；204 不能有响应体（输出里 `status=204` 且 `body=null`、`ct=-`）；405 必须带 `Allow`（`PUT /articles/2 -> status=405 allow=GET, DELETE`）。
- 幂等键的实现要点：键要和「请求指纹」一起存（请求体的规范化哈希），同键不同指纹必须**拒绝**而不是复用；键要有 TTL 与清理任务，否则去重表无限增长变成新的数据库问题。
- 事故画像：把「取消订单」做成 `GET /orders/42/cancel`，被浏览器预取或爬虫触发批量取消。修复是改成状态机字段的 PATCH（`{"status":"cancelled"}`）或 POST 到动作子资源。

### 🎓 博士生视角
- 幂等在数学上是 f(f(x)) = f(x)。映射到 HTTP 指的是：多次执行同一请求对**服务端状态**的影响与执行一次相同。注意这是「状态等价」而不是「响应字节相同」——所以第二次 DELETE 返回 404 依然是幂等的（状态已达成）。把两者混淆会导致「为了幂等而返回伪造的 200」，那是更糟的设计。
- 安全（safe）是比幂等更强的约束：安全 ⇒ 幂等，反之不成立（PUT 幂等但不安全）。这个偏序关系是「能否缓存 / 能否预取 / 能否自动重试」的形式化依据：只有安全方法可被缓存与预取，只有幂等方法可被自动重试。
- URI 设计的动机来自 HATEOAS（超媒体作为应用状态引擎）：资源标识应稳定、可寻址、与实现解耦，这样代理与网关可以在不理解业务语义的前提下正确工作（缓存 GET、按路径分流、按状态码决定是否重试）。把版本、动作、格式塞进 URI 会破坏这一前提。
- 状态码是**协议层的可编程接口**：502/503/504 让负载均衡器决定摘除或重试节点，429 让客户端退避，409 让客户端重新读取后提交，410 让搜索引擎移除索引。把一切塞成「200 + 业务码」，等于一次性关掉这些能力，代价由整个基础设施承担。

### 📚 考研者视角
- **笔试/面试考点**（本章非 408 课目，视角对准计算机方向笔试与面试的标准问法）：简答「幂等与非幂等方法的区别及典型场景」「201/204/400/401/403/404/409/422/429 各用于什么场景」。
- **标准口径**：幂等 = 同一请求重复执行对资源状态的影响相同；安全 = 不改变资源状态。PUT 幂等、POST 不幂等是标准结论；若用幂等键实现「重复 POST 只生效一次」，答题必须点明「这是**应用层的幂等补偿**，并未改变 POST 在协议层的定义」——这是区分「背过」与「理解」的关键一句。
- **易混对比**：401 vs 403（未认证 vs 已认证但无权限）；404 vs 410（不存在 vs 曾存在且永久移除）；400 vs 422（语法层不可解析 vs 语法正确但语义校验失败）；502 vs 503 vs 504（上游返回非法响应 vs 服务不可用 vs 上游超时）；415 vs 406（不支持的请求媒体类型 vs 无法产出可接受的响应媒体类型）。
- **延伸**：安全方法与缓存的关系（RFC 9111）常与 HTTP 缓存章节联合出题。

## 二、分页、过滤与排序

三种分页口径：

| 方案 | 谓词 | 依赖 | 深分页代价 | 抗并发写入 |
|---|---|---|---|---|
| offset/limit | `LIMIT n OFFSET k` | 排序下的**绝对位置** | O(k) 扫描并丢弃 | 否（窗口漂移） |
| 游标/keyset | `WHERE (sort...) < (cursor...)` | **上一行的排序键** | O(log n) 定位 | 是 |
| 快照/无状态跳页 | 绑定快照 ID | 快照 | 视快照实现 | 是（但成本高） |

本章 ex03 用 sqlite 实跑给出判据（写入一条高分新记录，模拟第 1 页与第 2 页之间的并发插入）：

```
offset_page1=[8, 7, 6]                 cursor_page1=[8, 7, 6]
offset_page2_before_insert=[5, 4, 3]   cursor_page2_before_insert=[5, 4, 3]
offset_page2_after_insert=[6, 5, 4]    cursor_page2_after_insert=[5, 4, 3]
offset_stable_across_insert=False      cursor_stable_across_insert=True
offset_repeats_row_from_page1=True     cursor_repeats_row_from_page1=False
offset_needs_count_query_for_total_pages=True
cursor_needs_count_query_for_total_pages=False
```

offset 的第 2 页在插入后变成 `[6,5,4]`，把已经在第 1 页出现过的 6 又返回了一次（重复）；游标页保持 `[5,4,3]` 不变。同时 offset 方案要显示「共 N 页」必须额外发一次 `COUNT(*)` 查询，而游标方案可以不做总数（或做近似总数）。

过滤与排序的安全前提是**白名单**。要点在于：字段名会进入 SQL 的**标识符位置**，而参数化占位符只能保护「值」、不能保护「标识符」，所以必须白名单映射。ex04 实跑：

```
sort=-score&status=published&limit=25&offset=50   -> ok   orderSql="score" DESC  filters={"status":"published"} limit=25 offset=50
sort=id%3B%20DROP%20TABLE%20articles              -> 拒   sort: malformed token: "id; DROP TABLE articles"
sort=password                                     -> 拒   sort: field not in whitelist: password
tag=%3Cscript%3E                                  -> 拒   filter tag: illegal characters
tag=abc (数值字段)                                -> 拒   filter score: not an integer
limit=99999                                       -> ok   limit=100（夹到上限）
limit=0                                           -> 拒   limit: must be >= 1
```

### 🧑‍💻 程序员视角
- 选择口径：无限滚动、时间线、移动端列表 → 游标；后台管理表格（要显示总页数、可跳页）且数据量可控 → offset；两者可以并存（默认游标，管理后台走 offset）。
- 游标实现细节：游标里必须包含**完整的排序键集合**（如 `(score, id)`），否则排序键有重复值时 `score < cursor` 会漏行；游标建议签名或 base64 编码并带版本号，防止客户端伪造游标越权读数据。
- 过滤参数白名单化：把可过滤字段写成「字段 → 类型」的映射，逐字段校验；数值型必须整体匹配整数正则（防 `1 OR 1=1`），字符串型限制字符集与长度（ex04 中 `<script>` 被拒）。
- limit 越界必须显式决策：夹到上限（ex04 的 `99999 → 100`）或返回 400，二者都行，但不能既不夹也不报错地直拼 SQL。

### 🎓 博士生视角
- offset 的代价函数：即便走索引有序扫描，「跳到第 k 行」也必须先遍历前 k 个索引项（B+ 树无法直接跳到第 k 个叶子，除非另建计数索引）。因此深分页代价随页深**线性增长**，与返回行数无关。这是 offset 的结构性缺陷，不是实现瑕疵。
- 游标的正确性条件有两条：① 排序键上存在**全序**，即 `(sort_key..., 唯一键)` 唯一定序，否则「严格小于游标」会漏掉与游标同值的其余行；② 排序键**单调稳定**，不能选频繁更新的可变列，否则同一行会在页与页之间移动、造成重复或遗漏。
- 与隔离级别的关系：offset 在 READ COMMITTED 下每次查询取各自时点的快照，两次查询之间的写入会让窗口漂移；游标把「位置」编码进数据，天然免疫窗口漂移，但仍受「行被删除」影响——如果上一页的最后一行被删掉，下一页可能从该行之后的下一行开始，造成一行遗漏。这是 keyset 分页已知的边界。
- 与 SQL 标准的关系：keyset 分页的本质是用**行值比较**（row value comparison）替代绝对偏移。`(a, b) < (x, y)` 自 SQL:1999 起由行值构造器支持，PostgreSQL 与 MySQL 8 均可直接书写，并能走 (a, b) 复合索引——这正是本章第一节的最左前缀在分页上的应用。

### 📚 考研者视角
- **笔试/面试考点**：简答「为什么深分页用 offset 会慢」——标准答案必须落到「必须扫描并丢弃前 offset 行，代价 O(offset)」；追问「怎么优化」——答游标/keyset 并把排序键作为游标。
- **口径辨析**：`LIMIT/OFFSET` 的执行顺序是「先排序、再跳过、再取」。常考「`ORDER BY` 不唯一时 `LIMIT` 结果不确定」——排序键不唯一时数据库不保证稳定顺序，必须补唯一键作次级排序键；这与游标要求全序是同一结论的两面。
- **易混点**：offset 与页号换算（`offset = (page-1) * size`）；`LIMIT 0` 表示返回空集而非报错；MySQL 的 `LIMIT offset, count` 简写与 SQL 标准的 `OFFSET ... FETCH` 语义等价但不可混写。
- **延伸**：小数据量下 offset 与游标结果集相同（ex03 中插入前的第 2 页两者都是 `[5,4,3]`），差别只在并发写入后显现——这一点常被拿来出「陷阱选择题」。

## 三、请求校验与统一错误响应（RFC 9457 Problem Details）

三层防线，顺序不可颠倒：

1. **传输层**：`Content-Type` 不受支持 → 415；请求体超过大小上限 → 413；方法不在允许集 → 405（带 `Allow`）。
2. **结构层**：body 能否 `JSON.parse` → 失败 400。
3. **语义层**：字段级 schema 校验（类型、必填、边界、枚举、正则、是否拒绝多余字段）→ 失败 422，并在错误体里给出**字段路径**。

本章 ex05 用 4 个合法用例 + 10 个非法用例跑出判据（`all_valid_pass=true`、`all_invalid_rejected=true`），每类非法都输出精确路径与原因：

```
invalid#0 errors=["$.title: required"]                            # 缺必填
invalid#1 errors=["$.title: minLength is 1 (got 0)"]              # 边界（下界）
invalid#3 errors=["$.score: maximum is 100"]                      # 边界（上界）
invalid#4 errors=["$.score: expected integer"]                    # 类型（1.5 不是整数）
invalid#5 errors=["$.tags: maxItems is 3 (got 4)"]                # 数组长度
invalid#6 errors=["$.slug: must match ^[a-z0-9-]+$"]              # 正则
invalid#7 errors=["$.featured: expected boolean"]                 # 类型
invalid#8 errors=["$.extraField: additional property not allowed"]# 多余字段（防 mass assignment）
invalid#9 errors=["$: expected object"]                           # 顶层类型
```

错误体统一采用 **RFC 9457 Problem Details**（取代 RFC 7807），媒体类型 `application/problem+json`。五个核心成员：

- `type`：标识问题类型的 URI 引用，缺省为 `about:blank`；
- `title`：给人读的短摘要，对同一 `type` 应保持稳定；
- `status`：HTTP 状态码（与响应行冗余，便于日志单看）；
- `detail`：本次发生的具体说明；
- `instance`：本次问题对应的具体 URI。

扩展成员可自由添加（如字段级 `errors` 数组、`retryAfterSec`），但不得与核心成员冲突。ex06 实跑 5 个响应，`all_core_fields_ok=true`，并验证 `extension_members=["errors"]` 与 `["retryAfterSec"]` 都没有撞核心字段；同时 429 响应输出 `Retry-After: 30`（协议层与错误体协同）。

### 🧑‍💻 程序员视角
- 校验顺序固定为「媒体类型 → 大小 → 可解析 → schema」。顺序颠倒会把「超大 body」报成「JSON 语法错误」，把排查引向错误方向。
- 错误体必须带**机器可读定位**：`errors[].pointer` 用 JSON Pointer（如 `/title`），前端据此精确高亮字段；只给一句自然语言，前端只能整体提示，也无法做自动化测试断言。
- 兜底原则：任何未预期异常都收口到同一个四参数错误中间件（fs-ch04 的成果）→ 500 + Problem Details，绝不把堆栈、SQL 语句或内部主机名回给客户端。
- 工程细节：`type` 建议指向团队文档站的真实 URL，成为「错误类型目录」的锚点，便于按 type 聚合告警；不要编造不存在的 URL。

### 🎓 博士生视角
- 把错误做成「资源」的结构性收益：`type` 是 URI，因此错误类型可被寻址、可文档化、可按 type 做**程序化分支**（客户端 switch type 而非匹配自然语言），文档也能有单一事实来源。
- 为什么需要新媒体类型：`application/json` 无法区分「成功资源」与「错误描述」，两者结构完全不同却同用一个媒体类型，通用客户端只能靠状态码猜结构。`application/problem+json` 让「解析器选择」不再依赖上下文，这是内容协商思想的直接应用；代价是它必须显式协商，否则默认降级会丢语义。
- 与 RFC 7807 的关系：RFC 9457 是 7807 的修订版，成员集合不变，主要变化是明确允许 `type` 为相对 URI 引用、补充缺省推断规则、增加注册表与安全考虑，因此两版在字段层面兼容，升级不需要改客户端结构。
- 422 的语义边界：RFC 9110 定义 422 为「服务器理解请求实体的内容类型、语法正确，但无法处理其中包含的指令」——即语法通、语义不通。与 400 的分界点在实现中常被混淆，标准把它们分开是为了让客户端判断「要不要改语法」。

### 📚 考研者视角
- **面试/笔试考点**：简答「输入校验应该放在哪一层、为什么前端校验不能替代服务端校验」。标准答案：前端校验是体验优化（可被绕过），服务端校验是安全边界（不可绕过），二者不可互相替代。
- **口径**：400 与 422 的划分依据是「语法 vs 语义」；415 的触发条件是请求体的 `Content-Type` 不被支持。答题要落到语义分层，不要答成「400 什么都能管」。
- **易混点**：`Content-Type` 描述请求体、`Accept` 描述期望的响应类型，方向相反；415 与 406 分别是「不支持的请求媒体类型」与「无法产出可接受的响应媒体类型」。
- **延伸**：OWASP 输入校验原则（白名单优于黑名单、边界值必须显式定义）与本章 ex05 的 `additionalProperties: false`（拒绝多余字段、防 mass assignment）一一对应，是常考的联合考点。

## 三视角小结
| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| REST 资源与方法语义 | 接口表逐条对照状态码；201 带 Location、405 带 Allow | 幂等的状态等价定义、安全⊃幂等、状态码作为协议接口 | 幂等/安全标准口径、401/403、400/422、502/503/504 辨析 |
| 分页与过滤 | 无限滚动用游标、后台表格用 offset；字段名白名单 | offset 代价 O(k)、游标全序与单调性、行值比较 | 深分页慢的标准答法、LIMIT/OFFSET 执行顺序 |
| 校验与错误响应 | 三层防线定序；pointer 定位；错误中间件收口 | 错误作为资源、媒体类型与内容协商 | 前后端校验不可互替、415/406 辨析 |
