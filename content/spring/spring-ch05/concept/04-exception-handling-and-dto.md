# 四、全局异常处理与 DTO 隔离
## 1. @ControllerAdvice 全局异常处理与异常→状态码映射

`@ControllerAdvice` 是集中式的横切Advice，配合 `@ExceptionHandler` 捕获所有 Controller 抛出的特定异常，统一转成「状态码 + 错误体」，避免每个方法写 try-catch。

### 🧑‍💻 程序员视角
- 映射表思维：自定义异常 `NotFoundException → 404`、`UnauthorizedException → 401`、`ConflictException → 409`，未匹配的运行时异常兜底 500；这是「异常类型 → 状态码」的查表。
- 全局处理器**只覆盖 Controller 层**：Filter / Interceptor 抛的异常不经过它，需在 `FilterChain` 或 `@ControllerAdvice` 之外的 `HandlerExceptionResolver` 兜底。
- 错误体要统一结构（如 `{"code":404,"message":"..."}`），前端按 `code` 而非字符串匹配；别返回 200 + 错误体。

### 🎓 博士生视角
- 异常→状态码映射本质是**类型分派（pattern matching on type）**：JVM 的多态/instanceof 链把异常类型映射到响应，替代了散落在各处的 `if (e instanceof ...)` 错误处理，是 AOP 思想在错误通道上的体现。
- `@ControllerAdvice` 由 `ExceptionHandlerExceptionResolver` 在 `HandlerAdapter` 调用后、`DispatcherServlet` 的 `processHandlerException` 阶段介入，因此它能改写状态码与响应体。
- 设计动机：把「正常返回」与「异常返回」在**同一个出口**收敛，保证对外契约（状态码语义、错误结构）一致，符合单一职责。

### 📚 考研者视角
- 笔面标准问法：「怎么统一处理异常？」标准答：`@ControllerAdvice` + `@ExceptionHandler` 按异常类型映射状态码与错误体，未捕获兜底 500。
- 易错：以为它能捕获**所有**异常——Filter/Interceptor 的异常不进它，需要额外兜底；也别在处理器里把 4xx 错误包成 200。
- 关联考点：与 AOP `@AfterThrowing` 的区别（异常处理更语义化、能改状态码，且只在 Web 层）。
## 2. DTO 与实体分离：防止敏感字段泄露

DTO（Data Transfer Object）是对外传输的数据结构，Entity 是持久层对象。**对外永远返回 DTO，不返回 Entity**——尤其要裁剪掉 `password`、`salt` 等敏感字段，否则会直接序列化泄露。

### 🧑‍💻 程序员视角
- 映射用 MapStruct / 手写 `toDto()`；手写时**显式只拷贝白名单字段**，`password` 绝不出现在 DTO 类里。
- 千万别 `return userEntity;` 让 Jackson 直接序列化——即使加 `@JsonIgnore` 也有疏漏风险，最稳的是「DTO 里压根没有这字段」。
- 分层边界：Controller 收 `XxxRequest`、返 `XxxResponse`；Service 用 Entity/领域对象；转换在边界处发生一次，职责清晰。

### 🎓 博士生视角
- 隔离的第一性原理是**关注点分离 + 最小暴露面**：Entity 的结构随持久层演化，把它直接当 API 契约会把内部实现泄漏给调用方，破坏稳定性。
- 字段裁剪本质是「投影（projection）」：只选取调用方需要的列，等价于 SQL 里的 `SELECT` 投影，既安全又省带宽。
- 这与 REST 的「表现层与资源内部表示分离」一致：URL/资源是稳定的，DTO 是它的**对外表现**，与数据库行的内部形状无关。

### 📚 考研者视角
- 笔面标准问法：「为什么不直接返回 Entity？」标准答：防止敏感字段泄露、解耦内外结构、避免 API 随表结构变化而破坏契约。
- 易错：以为「加了 `@JsonIgnore` 就安全」——一旦有人误删注解或换序列化器就泄露；**DTO 里没有该字段**才是根本。
- 关联考点：VO/BO/DO/DTO 的分层命名（表现层 VO、业务 BO、持久 DO、传输 DTO），常被追问。
## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 异常→状态码查表；Filter 异常不进 Advice；DTO 白名单字段，password 别进。 |
| 博士生 | 异常分派是多态类型匹配；DTO 隔离=最小暴露面的投影。 |
| 考研者 | 全局异常处理写法 + 不直接返 Entity 的三条理由必考。 |
