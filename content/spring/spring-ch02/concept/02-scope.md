# 二、Bean 作用域：singleton / prototype / request / session

## 一、四种作用域的语义差异（中立陈述）

Spring 通过 `scope` 决定 `getBean` 时返回的是「同一实例」还是「新实例」：

- **singleton**（默认）：整个容器共享唯一实例，存于 `singletonObjects` 一级缓存，容器关闭时才销毁。
- **prototype**：每次 `getBean` 都新建一个，容器只负责「创建 + 初始化」，**不缓存、不管理销毁**。
- **request**：每个 HTTP 请求一个实例，请求结束即回收（Web 环境）。
- **session**：每个 HTTP Session 一个实例，Session 失效时回收（Web 环境）。

`request` / `session` 本质是对「请求/Session 上下文」做了一层 `Map` 绑定的 scope 实现（Spring 用 `RequestScope` / `SessionScope` 挂在 `RequestContextHolder` 上）。

### 🧑‍💻 程序员视角
- 默认 singleton 能满足绝大多数无状态 bean（Service/Repository/Controller），天然线程安全靠的是「无字段可变状态」而非「每次新建」；有可变成员字段的单例类是并发雷区。
- 选型：有状态且需隔离的对话型对象（如用户购物车、表单草稿）用 `request`/`session`；像「每次都要全新、用完即弃」的批量处理器用 `prototype`。
- 坑：`@Async` 方法所在 bean 若想并发，注意它是 singleton——`@Async` 走代理提交任务到线程池，bean 本身仍是单例，没问题；但不要把请求级数据塞进单例字段。

### 🎓 博士生视角
- 抽象：`Scope` 是一个接口，`get(String name, ObjectFactory<?> objectFactory)` 决定「从哪取、取不到怎么造、造完存哪」。singleton 的 `get` 走 `singletonObjects` 缓存；request/session 的 `get` 走 `RequestAttributes` 里绑定的 `Map`。`objectFactory` 把「真正创建 bean」延迟到 scope 决定「需要新实例」时才调用——这是模板方法 + 策略模式的组合。
- 为何 prototype 不触发销毁？容器在 `getBean` 路径上只调用到 `createBean` + 初始化，销毁逻辑（`registerDisposableBean`）只在 singleton 分支注册；prototype 创建后容器「放手」，引用交给调用方，GC 负责回收，因此 `@PreDestroy`/`DisposableBean` 对 prototype 不生效。
- 内存布局：singleton 实例常驻老年代（存活整个进程）；prototype/request 随使用频繁在新生代分配与回收，需警惕高频创建大对象引发的 GC 压力。

### 📚 考研者视角
- 笔面标准问法：「singleton 和 prototype 的区别？」标准答：**singleton 容器内唯一、容器管销毁；prototype 每次新建、容器不管销毁、@PreDestroy 不触发**。
- 易错口径：把 `request`/`session` 当成「和 prototype 一样每次新实例」——错，它们是「同一请求/会话内共享」，跨请求才新。
- 关联考点：request/session 作用域依赖 Web 环境（`DispatcherServlet` 绑定 `RequestContextHolder`），在非 Web 单元测试里直接注入会报 `IllegalStateException: No thread-bound request`。

## 二、prototype 注入 singleton 的陷阱（中立陈述）

当**单例 bean 依赖 prototype bean** 时，容器只在「创建单例」那一刻注入一次 prototype 实例；此后单例长期持有这同一个 prototype 引用，后续 `getBean` 不会重新注入。于是「想每次用新 prototype」的直觉落空——得到的是创建时那唯一一个。要每次拿新实例，需用 `ObjectProvider` / `Provider` / `lookup-method`。

### 🧑‍💻 程序员视角
- 真实事故：单例 `OrderProcessor` 注入 prototype `OrderContext`（带可变状态），并发处理多笔订单时所有线程共享同一个 `OrderContext`，数据互相串台。修复用 `ObjectProvider<OrderContext>.getIfAvailable()` 每次取新，或 `@Lookup`。
- 写法：`@Autowired ObjectProvider<OrderContext> ctxProvider;`，用时 `ctxProvider.getObject()` 拿全新实例；Spring 4.3+ 直接注入 `ObjectProvider` 即可，无需 `@Lazy`。
- 反向安全：singleton 注入 singleton 永远共享同一实例（正确）；prototype 注入 singleton 没问题（prototype 每次新建但共用的那个 singleton 仍是单例）。

### 🎓 博士生视角
- 根因：依赖注入发生在「单例创建期」，而单例只创建一次，因此注入动作只发生一次。`prototype` 的「每次新建」语义只作用于「调用方主动 `getBean`/provider 取」这条路径，容器不会在单例生命周期内反复重注。
- `lookup-method`（CGLIB 重写方法返回 `getBean`）与 `ObjectProvider`（延迟到调用点再 `getBean`）本质都是把「获取 prototype」从「创建期」推迟到「使用期」，从而绕过「注入只一次」的限制。二者区别：lookup 用子类重写方法，provider 用持有工厂的轻量对象。
- 形式化：设单例 S 在某时刻 t0 注入 P0；此后 S 持有的 P 始终 = P0。要让 S 在时刻 t 拿到 P_t，必须把「取 P」建模为函数 `f(t)=getBean(P)`，而非字段 `S.p`。

### 📚 考研者视角
- 笔面标准问法：「singleton 里注入 prototype，每次拿到的是新实例吗？」答：**不是，只在单例创建时注入一次，之后一直是那一个**；想要新实例用 `ObjectProvider` 或 `@Lookup`。
- 易错口径：以为「prototype 就是每次新」因而「被 singleton 持有也每次新」——这是最常见的误解，需明确指出「注入时机」才是关键。
- 命题角度：常给一段代码让你判断单例持有的 prototype 是否随调用变化，答案是不变。

### 三视角小结

| 主题 | 程序员视角 | 博士生视角 | 考研者视角 |
|---|---|---|---|
| 四种作用域 | 无状态用 singleton、有状态用 request/session | Scope 接口 + 模板/策略 | singleton vs prototype 标准答 |
| prototype 注入 singleton 陷阱 | 数据串台事故 + ObjectProvider 修复 | 注入只发生一次 | 不是每次新、用 @Lookup |
