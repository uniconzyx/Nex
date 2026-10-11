# 二、参数绑定与内容协商
## 1. 三类参数绑定：`@RequestParam` / `@PathVariable` / `@RequestBody`

三者分别吃不同的请求位置：`@RequestParam` 取查询串或表单字段（`?page=2`），`@PathVariable` 取路径模板变量（`/users/{id}`），`@RequestBody` 把整个请求体（通常 JSON）反序列化成对象。绑定失败（类型转换错误）默认导致 400。

### 🧑‍💻 程序员视角
- `@RequestParam` 默认 `required=true`，缺参会直接 **400**；可选参数务必显式 `required=false` 或给 `defaultValue`。
- `@RequestBody` 只能读**一次**：若在 Filter/Interceptor 里读过流，Controller 会收到空体——需缓存请求体（content caching）。
- GET 带 `@RequestBody` 会被多数客户端/服务器拒绝（HTTP 语义不允许 GET 有体），遇到「参数收不到」先确认是不是用错了注解。

### 🎓 博士生视角
- 绑定是「字符串 → 目标类型」的**类型转换管道**：`WebDataBinder` 借助 `ConversionService` 与 `Formatter` 完成，自定义类型（如 `LocalDate`）要注册对应 `Converter`/`Formatter`。
- `@PathVariable` 的提取是**模式匹配 + 变量捕获**：模板段 `{id}` 与真实路径段对齐，非模板段必须字面值相等，二者共同决定匹配成败。
- `@RequestBody` 的反序列化由 `HttpMessageConverter` 链完成：按 `Content-Type` 选转换器（JSON 走 Jackson），与内容协商共用同一套机制。

### 📚 考研者视角
- 笔面标准问法：「`@RequestParam`、`@PathVariable`、`@RequestBody` 区别与适用场景？」标准答：查询/表单参数、路径变量、请求体对象，分别对应三者。
- 易错：把「路径里的值」当 `@RequestParam` 取，或反过来——**位置**决定注解，混淆会导致收不到值或 400。
- 常考：`@RequestParam` 的 `required`/`defaultValue` 语义，以及「同名多值」用 `List` 接收的写法。
## 2. 内容协商与消息转换器链

内容协商（Content Negotiation）指服务器根据客户端 `Accept` 头选择返回格式（JSON/XML）。Spring 用 `HttpMessageConverter` 链：写响应时按 `Accept` 与转换器支持类型匹配；读请求体时按 `Content-Type` 匹配。

### 🧑‍💻 程序员视角
- 工程上 99% 场景只走 JSON（Jackson）；但对外暴露的开放 API 常需同时支持 XML，此时要显式注册 `MappingJackson2XmlHttpMessageConverter`。
- 协商失败（客户端要的格式服务端不支持）返回 **406 Not Acceptable**；这是 `produces` 约束的来源。
- 自定义对象直接 `return entity` 即可，别手动拼 JSON 字符串——会失去协商能力与统一包装，且易引入注入/XSS。

### 🎓 博士生视角
- 协商是「带权重的媒体类型匹配」：`Accept: application/json;q=0.9,application/xml;q=0.8` 中 `q` 是质量因子，服务器在自身支持的集合里选**加权最高且兼容**的表示。
- 转换器链是有序列表，匹配顺序决定优先级；JSON 转换器通常排在 XML 之前，因此 `Accept: */*` 时默认回 JSON。
- 这与 REST 的「资源 + 表现层分离」第一性原理一致：URL 标识资源，**元数据（Accept/Content-Type）** 选择表现。

### 📚 考研者视角
- 笔面标准问法：「Spring 怎么根据 Accept 返回不同格式？」标准答：`ContentNegotiationManager` + `HttpMessageConverter` 链，按 `Accept` 的 `q` 权重选转换器。
- 易错：以为「返回什么格式由 Controller 决定」——实际由**协商 + 转换器支持度**共同决定；服务端不支持就 406。
- 关联考点：406 与 415（不支持的媒体类型，请求体 `Content-Type` 不匹配）是两个不同方向的协商失败。
## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 按位置选注解；@RequestBody 只读一次；协商失败 406，手动拼 JSON 是大忌。 |
| 博士生 | 绑定=字符串→类型的转换管道；协商=带 q 权重的媒体类型匹配。 |
| 考研者 | 三注解区别是必考题；406/415 是协商的两个失败方向。 |
