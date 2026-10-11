# spring-ch05 易错点

1. **`@RestController` 与 `@Controller` 混用，返回 JSON 变成视图名/200 字符串页面** —— 在普通 `@Controller` 方法里直接 `return "ok"`，Spring 会拿它当视图名去解析，前端收到的是一段 HTML 而非 JSON。正确写法：要么类上用 `@RestController`，要么在方法上加 `@ResponseBody`；返回对象让消息转换器序列化。

2. **`@RequestParam` 默认 `required=true`，缺参会直接 400 而非拿到 null** —— 很多「参数收不到就 400」的诡异现象源于此。正确写法：可选参数显式 `required = false`，或用 `defaultValue`；真正可空的字段就别依赖隐式 null。

3. **`@PathVariable` 与 `@RequestParam` 混淆** —— 把 `/users/{id}` 里的 `id` 用 `@RequestParam` 取，结果永远收不到；或反过来把查询串 `?id=1` 当路径变量取。正确写法：路径模板变量用 `@PathVariable`，查询串/表单用 `@RequestParam`，**位置决定注解**。

4. **`@RequestBody` 只能读一次，拦截器/过滤器读过流后 Controller 收空体** —— 在 `Filter`/`Interceptor` 里为了打日志读了 `request.getInputStream()`，后续 Spring 读到的就是空。正确写法：用 `ContentCachingRequestWrapper` 缓存请求体，或把读体逻辑放到最里层只读取一次。

5. **GET 请求带 `@RequestBody` 被服务器/客户端拒绝** —— HTTP 语义上 GET 不应带请求体，部分容器直接忽略或报错，导致参数永远为空。正确写法：查询用 `@RequestParam`/路径变量；需要传复杂结构时用 POST/PUT。

6. **忘记加 `@Valid`，`@NotNull`/`@Size` 校验「静默不生效」** —— 注解贴了但方法参数前没写 `@Valid`（或类上没 `@Validated`），校验引擎根本不触发。正确写法：Controller 方法参数前加 `@Valid`，且校验失败要配 `@ExceptionHandler` 转成 400/422，而不是让它冒泡成 500。

7. **分组校验只在一边写了 `groups`** —— 字段标了 `@NotNull(groups = Update.class)`，方法上却没 `@Validated(Update.class)`，结果该约束永不执行，「看起来没生效」。正确写法：`groups` 在字段和方法上**两边都要声明**；不声明组的约束只在 `Default` 组生效。

8. **直接 `return map`/`ResponseEntity` 却手写 JSON 字符串** —— 绕过消息转换器手动拼 `"{\"a\":1}"`，既失去内容协商能力（永远只能 JSON），又容易因拼接引入 XSS/注入。正确写法：返回对象或 `ResponseEntity<T>`，让 Jackson 统一序列化。

9. **全局异常 `@ControllerAdvice` 只捕获 Controller 异常，Filter/Interceptor 异常进不去** —— 在过滤器里抛的鉴权异常不会被 `@ExceptionHandler` 接住，于是返回了容器默认的 500/错误页。正确写法：鉴权类异常要么在 Filter 内就地写响应，要么抛特定异常并配合 `HandlerExceptionResolver` 兜底。

10. **异常处理器返回 200 + 错误体 `{ok:false}`** —— 把本该是 404/400 的错误包成 200，客户端只能靠解析字符串判断成败，网关重试/熔断策略也失效。正确写法：按异常类型映射**真实状态码**（404/401/403/409/422/500），错误体只承载 message/code。

11. **DTO 直接复用 Entity，接口泄露 `password` 等敏感字段** —— `return userEntity` 让 Jackson 把整张表序列化出去。正确写法：定义不含敏感字段的 DTO，手写 `toDto()` 白名单拷贝，**DTO 里压根不出现 password** 才是根本解法。

12. **状态码乱用：创建也回 200、参数错误用 500** —— 成功一律 200、出错一律 500，客户端的错误分类与监控全部失真。正确写法：创建 201（+`Location`）、删除 204、参数错误 400、校验失败 422、业务冲突 409、未认证 401、无权限 403、服务器异常 500。

13. **POST 不做幂等，前端重试导致重复下单/重复扣款** —— 网络抖动时浏览器/网关自动重试 POST，没有去重就多次执行业务。正确写法：用「唯一请求号 / 资源版本号 / 去重表」保证重复请求得到同一结果；或改用幂等的 PUT 表达「创建或更新」。

14. **CORS 预检 OPTIONS 被拦截器/鉴权拦掉，跨域失败** —— 浏览器先发 `OPTIONS` 预检，若被登录拦截器拦下（因没带 token），正式请求永远发不出。正确写法：拦截器对 `OPTIONS` 方法直接放行，或在 `@CrossOrigin`/`WebMvcConfigurer` 里正确配置 `allowedMethods` 含 OPTIONS。
