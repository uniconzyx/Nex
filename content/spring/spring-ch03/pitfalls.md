# AOP 与代理机制 · 易错点

> 以下条目为 AOP/代理在工程与面试中的高频踩坑。**编号行首，便于校验。**

1. **同类方法内部自调用绕过代理（最经典）** —— 被代理对象的 `save()` 内部 `this.update()`，
   `this` 是真实对象而非代理，`update()` 上的 `@Transactional`/`@Async` 等通知全部失效。
   正确写法：把 `update()` 拆到另一个 Bean 注入调用，或用 `AopContext.currentProxy()` / 自注入拿到代理再调。

2. **把 `InvocationHandler.invoke` 的第一个参数当 target** —— 第一个参数是**代理对象**，
   不是被代理的真实对象；用它去 `==` 比较或递归调自身会死循环/永不相等（见 ex08）。
   真实对象应作为字段单独持有，用 `method.invoke(target, args)` 委派。

3. **反射异常被 `InvocationTargetException` 包多层** —— `method.invoke` 抛出的业务异常会被包成
   `InvocationTargetException`，直接 `catch(Exception e)` 拿到的是包装异常、类型判断全错。
   正确写法：捕获后取 `e.getCause()` 得到真实异常（见 ex03）。

4. **JDK 动态代理只能代理接口，传普通类直接抛异常** —— `Proxy.newProxyInstance` 要求传入的是
   **接口数组**；若误传具体类会抛 `IllegalArgumentException: ... is not an interface`（见 ex06）。
   代理具体类必须改用 CGLIB。

5. **CGLIB 无法代理 `final` 类 / `final`、`private` 方法** —— 因 CGLIB 靠「继承 + 重写」，
   final 不可继承/不可重写，启动即报 `Cannot subclass final class`（见 ex12）。
   正确写法：去掉 final，或改用基于接口的 JDK 代理。

6. **切点写得过宽导致全量拦截** —— `execution(* *(..))` 会把 Spring 内部 Bean、`toString`/`hashCode`
   也织入，引发栈溢出或性能雪崩。正确写法：收窄到具体包/类/方法，或改用 `@annotation` 注解切点。

7. **混淆 `@After` 与 `@AfterReturning`** —— `@After` 类似 `finally`，**无论正常还是异常都执行**，
   且拿不到返回值；`@AfterReturning` 只在正常返回后执行、能拿到返回值；异常时走的是 `@AfterThrowing`。
   在 `@After` 里读返回值是 `null`，应在 `@AfterReturning` 里读。

8. **`AopContext.currentProxy()` 忘记开 `exposeProxy`** —— 想用 `currentProxy()` 解决自调用，
   却没在 `@EnableAspectJAutoProxy(exposeProxy = true)`，运行拿到 `null` 抛异常。
   正确写法：显式开启，或更推荐「拆 Bean」的方案。

9. **`@Transactional` 加在 private 方法上不生效** —— 代理只能拦截外部 public 调用，private 方法进不了拦截逻辑，注解等于白写。✅ 事务注解放 public 方法；需要内部增强就拆 Bean 或用 AspectJ 编译织入。
10. **`@Around` 不调 `proceed()` 导致原方法被吞** —— Around 必须手动 `joinPoint.proceed()` 才把控制交还原方法，漏写则请求返回 null、业务不执行。✅ 永远在 try/finally 里调 proceed 并 return 其结果。
11. **多切面顺序不定导致日志/事务谁先谁后混乱** —— 没指定 `@Order` 时切面顺序由扫描顺序决定，可能事务回滚了日志却记成功。✅ 用 `@Order` 明确：越小的越外层（如日志 1、事务 10）。
12. **`this` 与 `target` 混淆导致切点匹配错对象** —— `this` 匹配代理对象类型，`target` 匹配真实被代理对象；接口代理时二者不同，权限类应切真实类型用 `target`。✅ 明确要切的是代理还是目标，别混用。
13. **切点表达式过宽把 `toString`/`hashCode` 也织入** —— `execution(* com.x..*.*(..))` 连 getter、toString 都包了，日志刷屏甚至递归死循环。✅ 限定 service 包或改用 `@annotation` 只切标记方法。
14. **在业务里吞掉异常导致事务无法回滚** —— try/catch 不重抛，代理层收不到异常，`@Transactional` 默认只认抛到代理的异常才回滚。✅ catch 里 `setRollbackOnly()` 或重抛。
15. **只切 Controller 做鉴权被 Service 直调绕过** —— AOP 只拦截切面覆盖的入口，不是全局防火墙；有人直接调 Service 就绕过了鉴权。✅ 切到业务入口并配合网关纵深防御。
