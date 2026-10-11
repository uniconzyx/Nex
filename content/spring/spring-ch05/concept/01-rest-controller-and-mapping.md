# 一、REST 控制器与请求映射
## 1. @RestController 的语义与请求映射

`@RestController` 是 `@Controller` 与 `@ResponseBody` 的组合注解；`@RequestMapping` 在类级定义基准路径前缀，在方法级定义子路径与 HTTP method（`@GetMapping` 等是它的快捷形式），并可用 `produces`/`consumes` 约束媒体类型。请求进入后由 `RequestMappingHandlerMapping` 把「请求条件」映射到 `HandlerMethod`。

### 🧑‍💻 程序员视角
- 工程惯例：Controller 层**只做协议转换 + 编排**，业务逻辑下沉 Service，否则单测必须起容器才能跑。
- `produces` 写错会让内容协商失败返回 **406**；常见坑：返回 `String` 被当成视图名（少了 `@ResponseBody`，或类不是 `@RestController`）。
- 类级 `@RequestMapping("/api/v1/users")` 统一定义版本前缀，便于灰度与废弃，比散落在每个方法里更易维护。

### 🎓 博士生视角
- `@ResponseBody` 的本质是把 Handler 返回值交给 `HttpMessageConverter` 写响应体，而非交给 `ViewResolver` 解析视图；`@RestController` 用 `@AliasFor` 把 `@ResponseBody` 提到**类级**。
- 路径匹配在 DispatcherServlet 阶段由 `RequestMappingHandlerMapping` 完成，建立「请求条件 → HandlerMethod」的映射表；条件是可组合的（method/path/params/headers/produces）。
- 版本化 API 两种主流：URL 前缀（`/v1`）对网关/缓存更友好；Accept 头（`application/vnd.x.v1+json`）更「REST 纯粹」——二者是工程取舍而非对错。

### 📚 考研者视角
- 笔面标准问法：「`@RestController` 和 `@Controller` 区别？」标准答：前者每个方法默认 `@ResponseBody`，返回值直接写响应体；后者配合视图解析器返回**视图名**（方法上加 `@ResponseBody` 即等价）。
- 易错：认为 `@RestController` 比 `@Controller` **多路由能力**是错的，路由能力来自 `@RequestMapping` 系列，二者相同。
- 状态码口径：GET 成功 200、创建 201、删除 204、参数错误 400、未认证 401、无权限 403、不存在 404。
## 2. 状态码选择与第一性的幂等性

REST 用 HTTP 状态码表达结果；**幂等性**指「多次相同请求产生相同副作用」。GET/PUT/DELETE 幂等，POST 不幂等。创建资源用 POST（201 + `Location`），更新整资源用 PUT（幂等，200/204），部分更新用 PATCH（非幂等）。

### 🧑‍💻 程序员视角
- 幂等落地：用「唯一请求号 / 资源版本号 / 去重表」保证 POST 重试安全；**支付下单必须做幂等**，否则网络重试会重复扣款。
- 不要用 `200` 包住错误体（`{"ok":false}`），客户端按状态码分支更简洁，也利于网关重试与熔断策略。
- 创建成功后务必返回 `Location` 头指向新资源，前端据此轮询/跳转，这是 HATEOAS 的最基础实践。

### 🎓 博士生视角
- 幂等严格定义来自 HTTP 语义：`f(f(x)) = f(x)`，即**重复应用不改变最终状态**（不要求每次响应体相同，PUT 第二次仍返回 200 合法）。
- 状态码是带层级语义的「类型标签」：2xx 成功、4xx 客户端缺陷、5xx 服务端缺陷；同一错误用 4xx 还是 5xx 取决于**责任方**。
- 405 vs 404：路径存在但方法不被允许是 405，路径本身不存在是 404——这是路由匹配「先路径后方法」两阶段判定的直接后果。

### 📚 考研者视角
- 标准问法：「GET/POST/PUT/DELETE 哪些幂等？」答：GET、PUT、DELETE 幂等；POST 不幂等；GET 同时安全且幂等，PUT 幂等但不安全。
- 易错：认为「返回相同响应就是幂等」是错的，幂等看**副作用终态**，与响应体是否相同无关。
- 401 与 403 区别（前者未认证/未登录，后者已登录但无权限）是高频送分题，必须一字不差。
## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | Controller 只做编排；幂等靠去重表/请求号；别用 200 包错误。 |
| 博士生 | 幂等=终态不变；状态码按责任方分层；405/404 源于两阶段匹配。 |
| 考研者 | REST 问法固定：注解区别、状态码分类、幂等集合、401 vs 403。 |
