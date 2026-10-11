# 三、缓存体系：一级 / 二级的作用域、失效与陷阱

MyBatis 的缓存不是「一层可选的加速器」，而是**两个作用域截然不同的缓存**，
加上一个**由它们共同构成的三级查询路径**：

```text
  查询请求 (MappedStatement + 参数)
        |
        v
  +---------------------------+
  |  一级缓存 LocalCache      |  作用域: SqlSession（PerpetualCache + HashMap）
  |  Key = CacheKey            |  默认开启，无开关
  +---------------------------+
        | miss
        v
  +---------------------------+
  |  二级缓存 (namespace 级)   |  作用域: Mapper namespace（需 <cache/> 显式开启）
  |  TransactionalCache        |  事务提交后才对外可见
  +---------------------------+
        | miss
        v
  +---------------------------+
  |  Database                  |
  +---------------------------+
```

记住这张图的**三个数字**：一级缓存活不过一个 `SqlSession`；二级缓存活不过
「同一 namespace 的一次写操作」；两者都活不过 `flushCache="true"`。

## 一、一级缓存：SqlSession 级，Key 由四元组决定

一级缓存的 Key 是 `CacheKey`，由四部分拼成：`statementId` + `offset`（分页 offset）+
`limit`（分页 limit）+ **SQL 文本**（含 `?` 的模板）+ **参数值列表**。
把 `BoundSql` 的 `sql` 与 `parameterMappings` 的实参逐个 `update` 进 Key，
最后 `hashCode()` 作为 Map 的键。

失效触发点有且仅有四个：

1. **同一 SqlSession 内的任何 `insert`/`update`/`delete`** —— `BaseExecutor.update()` 会调用
   `clearLocalCache()`，把整个会话的一级缓存清空（不是只清相关表）；
2. `commit()` / `rollback()` —— 都会清空一级缓存；
3. `sqlSession.clearCache()` —— 手动清；
4. 语句上 `flushCache="true"`（`<select>` 默认 `false`，`<insert>/<update>/<delete>` 默认 `true`）。

`SqlSession` `close()` 之后缓存对象**整体废弃**（不是转移到二级，二级是提交时才写入的独立结构）。

### 🧑‍💻 程序员视角

- 最经典的一级缓存事故：**同一个 `SqlSession` 里混用「MyBatis 查询」和「直连 JDBC 写」**。
  直连 JDBC 绕过了 MyBatis 的 `update()`，于是 `clearLocalCache()` 不会执行，
  后续同名查询命中缓存返回旧值。表现是「同一个事务里读到自己刚写的数据是旧值」。
  修法：**要么全走 MyBatis，要么写完显式 `clearCache()`**，不要混用。
- 在 Spring 环境下有个反直觉的事实：**一级缓存的寿命等于一个事务**。
  `SqlSessionTemplate` 通过 `SqlSessionSynchronization` 把 SqlSession 绑在事务上，
  所以「同一个事务内两次相同查询只发一次 SQL」。这带来两个后果：
  - 好处：事务内重复查询零成本；
  - 坏处：**事务内其他事务提交的数据读不到**（读已提交隔离级别下本应能读到）——
    这是「同一个事务里刷新不到别人提交的数据」的根因。
- 性能取舍：一级缓存对「一个事务里反复查同一份配置/字典」收益极大；
  但如果你的查询是「列表页 + 每行再查一次子表」，一级缓存会缓存**每一条子查询**，
  缓存 Key 各不相同，反而只是纯粹的 Map 增长。别指望它治 N+1。
- 关掉它的方式：`localCacheScope=STATEMENT`，让每条语句执行完就清缓存。
  代价是事务内失去去重能力；当你遇到「事务内读到旧值」且无法改造调用方时，这是兜底手段。

### 🎓 博士生视角

- Key 里包含 SQL 文本意味着：**任何影响文本的因素都会分裂缓存**。
  动态 SQL 下 `<where>` 的切片不同 → 文本不同 → 不同 Key。
  这是设计上正确的（SQL 不同结果当然可能不同），但也意味着
  「用 `<where>` 拼参数化查询」时缓存命中率取决于**参数分布**：条件分支越多，命中越少。
- Key 不含「数据库会话的隔离级别/事务 ID」，因此一级缓存在语义上是
  **事务内一致性读的近似**：它假定「本事务内没有别人改这些行」。
  在 `REPEATABLE READ` 下这个假定与数据库语义一致；在 `READ COMMITTED` 下它**比数据库更强**，
  于是出现了「数据库允许读到新提交值，MyBatis 却给了旧值」的语义偏差。
  这就是「缓存比隔离级别更严格」的典型症状。
- `clearLocalCache()` 是**全量清除**而非按表清除，因为 `CacheKey` 里没有表名信息。
  因此**一次与本查询无关的写也会让缓存全废**——这是简单实现的代价，
  也解释了为什么「写多读少」的事务里一级缓存几乎无命中。
- 一个形式化视角：一级缓存是一个 `Map<CacheKey, List<Object>>`，
  其中 `CacheKey` 是 (statementId, offset, limit, sql, params) 的哈希。
  **无并发保护需求**（SqlSession 非线程安全），所以可以不做同步，这也是它比二级缓存轻的原因。

### 📚 考研者视角

- 面试标准问法：「一级缓存的作用域和失效条件？」标准答：作用域是 `SqlSession`；
  同一会话内相同 `statementId + SQL + 参数` 命中；**同一会话中执行任意增删改会清空整个一级缓存**；
  `commit`/`rollback`/`clearCache()`/`flushCache="true"` 也会失效。
- 常考口径：「一级缓存能关闭吗？」——能，`localCacheScope=STATEMENT`；
  但**没有「只开一半」的配置**，要么 SESSION 要么 STATEMENT。
- 易混点：**一级缓存 `close()` 后不会「晋升」到二级**。二级缓存的写入发生在
  `commit()`/`rollback()`（`TransactionalCacheManager` 把 `TransactionalCache` 的
  `entriesToAddOnCommit` 提交）。「close 时刷入二级」是常见误答。

## 二、二级缓存：namespace 级，提交后才可见

开启方式是在 Mapper XML 里写 `<cache/>`（或在接口上 `@CacheNamespace`）。
它的作用域是 **Mapper namespace**——同一个 namespace 下的所有 `MappedStatement` 共享一份缓存；
不同 namespace 各有一份，**互不可见，也不互相失效**。

`<cache>` 的关键属性：

| 属性 | 默认 | 含义 |
|---|---|---|
| `eviction` | `LRU` | 淘汰策略（`LRU`/`FIFO`/`SOFT`/`WEAK`） |
| `flushInterval` | 无（不主动刷） | 定时清空毫秒数 |
| `size` | `1024` | 最多缓存条目数 |
| `readOnly` | `false` | `true` 时返回同一对象引用（快但可能被污染）；`false` 时**序列化拷贝** |
| `type` | `PerpetualCache` | 自定义 Cache 实现（接 Redis 等） |

两条硬规则：

1. **返回对象需可序列化**（`readOnly=false` 时用 `SerializedCache` 做深拷贝，
   要求实现 `java.io.Serializable`）；
2. **写入发生在事务提交时**——`commit()` 之前，其他 SqlSession 看不到这次查询的结果。

### 🧑‍💻 程序员视角

- 二级缓存的三类真实事故，按出现频率排序：
  - **跨 namespace 更新导致脏读**：`UserMapper` 缓存了数据，但 `OrderMapper` 里的
    `UPDATE t_user` 不会清 `UserMapper` 的二级缓存（因为清只按 namespace）。
    修法：在多表写场景**不开二级缓存**，或让写操作走「与读相同的 namespace」，
    或用 `@CacheNamespaceRef` 显式关联（但仍不覆盖所有跨表写）。
  - **对象引用污染**：`readOnly=true` 时缓存返回同一引用；业务层改了字段（哪怕只是
    `setXxx` 做过格式化），缓存里的对象也变了。修法：`readOnly=false`（付出序列化成本）
    或返回后立刻做防御性拷贝/转 DTO。
  - **分布式下失效不传播**：二级缓存是**进程内**的（默认 `PerpetualCache`），
    多实例部署时 A 节点更新只清 A 自己的缓存，B 节点继续读旧值。
    修法：改用 Redis 作为 `Cache` 实现（`type=mybatis-redis` 或 MyBatis-Plus 的
    `RedisCache`），或干脆放弃二级缓存改用 Spring Cache + 分布式失效。
- 工程惯例：**互联网业务默认不开二级缓存**。理由是写多读少、跨表写频繁、
  多实例部署——三个条件恰好把二级缓存的三大风险全点满了。
  二级缓存真正适合的场景是「单实例 + 读极多写极少 + 单表读写」。
- 想安全使用，最少做四件事：`readOnly=false`、`flushInterval` 兜底、
  只在单表 CRUD 的 Mapper 上开、多实例部署前换成 Redis 并确认失效广播。

### 🎓 博士生视角

- 二级缓存的实现是一个**两级委托**：`TransactionalCache` 包装 `PerpetualCache`，
  在事务内把写操作攒进 `entriesToAddOnCommit`，`commit` 时才 `put` 进真正的缓存，
  并把 `clearOnCommit` 标记生效。这就是「其他会话在提交前看不到」的机制来源——
  它是**为满足「提交前不可见」的隔离语义而刻意引入的一层**，
  而不是简单的「延迟写入」优化。
- 为什么 `readOnly=false` 需要序列化：缓存要保证「取出的对象与缓存内的对象无别名关系」
  （no aliasing），否则调用方的写会破坏缓存不变量。
  实现手段只有深拷贝，而 Java 中无需额外依赖的深拷贝手段就是序列化往返。
  代价是 `O(对象图大小)` 的 CPU 与临时字节数组分配——这是**用时间换不变式**的经典取舍。
- namespace 隔离的根因：缓存的失效协议是「谁拥有 namespace，谁负责清」。
  这要求**所有对同一张表的写都发生在拥有该 namespace 的 Mapper 里**。
  一旦表被多个 namespace 写，失效协议就出现了**覆盖缺口**——
  这是一个「约定优于配置」留下的正确性责任，而不是 bug。
  想在架构上消除它，只有两条路：把失效做成**表级/数据级**（如按表名注册失效），
  或把缓存移出 MyBatis 交给 Redis（用键前缀 + 主动失效）。
- LRU 的实现在 MyBatis 里是 `LruCache` 装饰 `PerpetualCache`：
  内部维护一个 `LinkedHashMap` 记录访问顺序，超过 `size` 时移除最久未访问的键。
  注意它**不是线程安全的**（`PerpetualCache` 用 `HashMap`），
  所以 MyBatis 要求缓存对象「按 namespace 单例」并由 `TransactionalCacheManager` 统一访问——
  并发安全依赖上层的会话隔离，而不是缓存自身。

### 📚 考研者视角

- 面试标准问法：「二级缓存的作用域与开启方式？」标准答：作用域是 Mapper 的
  **namespace**，跨 SqlSession 共享，需在 Mapper 中显式 `<cache/>` 开启，
  缓存对象需可序列化。
- 常考口径：「一二级缓存的查询顺序」——先查二级缓存，命中则返回；
  未命中查一级；仍未命中查数据库，结果写入一级；
  **会话关闭/提交时**一级结果才写入二级（`TransactionalCache` 语义）。
- 易混点：「MyBatis 缓存与 Spring Cache 的关系」——两者独立，
  `@Cacheable` 是方法级（Spring 层面），MyBatis 二级缓存是 namespace 级（框架层面），
  同时开会出现**双层缓存叠加**，失效更难排查。这也是面试里常被追问的「缓存分层混乱」问题。

## 三、缓存陷阱实战：四类症状与定位口径

| 症状 | 大概率原因 | 定位口径 | 修法 |
|---|---|---|---|
| 同一事务内读到自己刚写的旧值 | 一级缓存 + 绕过 MyBatis 直连写 | 看是否有 `clearCache()` 调用 | 全走 MyBatis 或显式清缓存 |
| 事务内看不到其他事务刚提交的数据 | 一级缓存寿命 = 事务 | 换 `localCacheScope=STATEMENT` 复现 | 缩短事务、或改 STATEMENT |
| 单实例正常、多实例读到旧值 | 二级缓存是进程内的 | 多实例压测对比 | 换 Redis 实现或关闭二级 |
| 改 A 表后读 B 表的缓存还是旧值 | 跨 namespace 写不清对方缓存 | 看写操作在哪个 namespace | 关闭二级缓存 |

### 🧑‍💻 程序员视角

- 排查顺序建议固定在：
  **① 先确认是缓存问题**（`localCacheScope=STATEMENT` + 关 `<cache/>` 复现一次，
  若现象消失则确诊）；
  **② 再确认是哪一级**（同一 SqlSession 内是否复现）；
  **③ 最后定位失效链路**（谁写了这张表，在哪个 namespace）。
- 压测口径：不要在压测环境开二级缓存，因为压测通常是多实例；
  二级缓存的命中率在多实例下会「看起来很高但数据是错的」，比不开更危险。
- 一个低成本高收益的替代方案：**用 Spring Cache + Redis 做应用级缓存**，
  键设计成 `表名:id`，写操作显式 `@CacheEvict`。虽然更啰嗦，
  但失效路径是**显式可见的**，比 MyBatis 二级缓存的「隐式 namespace 失效」好排查得多。

### 🎓 博士生视角

- 这四类症状可以统一到「缓存有效性依赖的假设被打破」：
  - 一级缓存假设「本事务内本进程是唯一写入者」→ 被直连 JDBC 打破；
  - 一级缓存假设「读到的值在事务内不再变」→ 被 READ COMMITTED 打破；
  - 二级缓存假设「单进程 + 单 namespace 独占该表」→ 被多实例/跨表写打破。
  把假设列出来，症状就是「哪条假设被破坏了」的机械推论。
- 缓存一致性在工程上的现实结论：**没有全局失效机制的两级缓存，正确性上限就是「单进程 + 单写者」**。
  想突破这个上限必须引入外部协调（Redis 发布订阅 / 消息队列广播失效），
  代价是额外的可用性依赖——这是分布式缓存的固有成本，不是实现缺陷。
- 一个量化观察：一级缓存的收益大致正比于「事务内重复查询次数」，
  而二级缓存的收益正比于「跨事务、跨会话的重复查询次数」。
  若一次请求 = 一个事务、且每次查询参数都不同，那么**两级缓存的命中率都接近 0，
  而维护成本不为 0**。这就是「先量化再开缓存」的原因。

### 📚 考研者视角

- 面试标准问法：「MyBatis 缓存有什么坑？」标准答要点化：
  一级缓存生命周期是一个 SqlSession（Spring 下是一次事务），
  混用直连 JDBC 或跨事务读到旧值；二级缓存有跨 namespace 失效缺口、
  要求可序列化、多实例下失效不传播。
- 常考口径：「怎么关闭二级缓存？」——不在 Mapper 里写 `<cache/>`
  （或在 `<select>` 上 `useCache="false"`，在 `<insert>` 上 `flushCache="true"`）。
- 易混点：`useCache`（该语句是否**写入/读取**二级缓存）与
  `flushCache`（该语句执行后是否**清空**缓存）是两个独立开关，常被混淆。
  `<select>` 默认 `useCache=true` / `flushCache=false`；
  `<insert|update|delete>` 默认 `flushCache=true`（且 `useCache` 无意义）。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 互联网业务默认不开二级缓存；一级缓存的寿命等于一个事务，混用直连 JDBC 必踩旧值。 |
| 博士生 | 二级缓存的 `TransactionalCache` 层是为「提交前不可见」而存在；namespace 失效协议要求单写者。 |
| 考研者 | 必答作用域（SqlSession / namespace）+ 失效条件（增删改、commit、flushCache）+ 可序列化要求。 |
