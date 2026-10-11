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
