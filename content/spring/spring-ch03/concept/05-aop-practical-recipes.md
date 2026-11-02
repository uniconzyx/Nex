# §5 spring-ch03 实战手记：凯喵带你把 AOP 用「失灵」

> 前四节把 JDK 代理、CGLIB、切点顺序、自调用讲透了。这一节凯喵把生产里 AOP 最容易「悄悄失效」的 12 个现场摆出来——日志没打、事务没提交、权限没拦，全是代理绕过的锅。

### 现场一：同类内部方法自调用，通知整段消失

凯喵排查过「加在 `createOrder` 上的事务为啥没生效」。`createOrder` 里调了同类的 `saveDetail`，而 `saveDetail` 上的 `@Transactional` 死活不触发。原因：Spring 的 AOP 是**代理对象**织入的，同类内部 `this.saveDetail()` 走的是原始对象、绕过了代理。解法：拆 Bean，或用 `AopContext.currentProxy()`。

```java
@Service
public class OrderService {
    @Transactional
    public void createOrder() {
        // ❌ this 是原始对象，saveDetail 的代理通知被绕过
        this.saveDetail();
    }
    @Transactional(propagation = REQUIRES_NEW)
    public void saveDetail() { ... }
}
```

### 现场二：AopContext.currentProxy() 忘了开 exposeProxy

凯喵写 `((OrderService) AopContext.currentProxy()).saveDetail()` 想救自调用，结果拿到 `null` 抛异常。根因：`@EnableAspectJAutoProxy(exposeProxy = true)` 没开，Spring 没把代理塞进 `ThreadLocal`。更推荐的做法其实是**拆 Bean**，避免用 currentProxy 这种反模式。

```java
@Configuration
@EnableAspectJAutoProxy(exposeProxy = true)   // ✅ 必须显式开
public class AopConfig { }

// 使用时通过代理调用，而非 this
((OrderService) AopContext.currentProxy()).saveDetail();
```

### 现场三：final 类 / final 方法，CGLIB 代理不了

凯喵新来的同事把类写成 `final class`，结果 Spring 报「无法生成子类」。CGLIB 靠**继承 + 方法覆写**织入，final 类不能继承、final 方法不能覆写，自然代理不了。规则：要被代理的类和方法别加 final（除非你确定不需要增强）。

```java
// ❌ final 类，CGLIB 无法生成子类
final class PaymentService { ... }

// ✅ 去掉 final，让 CGLIB 能继承
@Component
class PaymentService {
    public void pay() { ... }   // 可被代理
}
```

### 现场四：private 方法上的 @Transactional 不生效

凯喵见过有人在 `private void inner()` 上写 `@Transactional`，期待它独立开事务。但 Spring 代理只能拦截**外部可调用**的方法（public），private 方法根本进不了代理的拦截逻辑，注解等于白写。事务注解请放 public 方法。

```java
// ❌ private + @Transactional，代理拦截不到
@Transactional
private void inner() { ... }

// ✅ public 才能被代理拦截
@Transactional
public void outer() { ... }
```

### 现场五：@Around 不调 proceed，业务直接被吞

凯喵 review 代码看到有人写 `@Around` 但忘了 `joinPoint.proceed()`，结果方法体根本不执行——所有请求返回 null。Around 的本质是「包裹」，你必须手动调 proceed 才把控制权交还给原方法，否则链路断在这里。

```java
@Around("pointcut()")
public Object around(ProceedingJoinPoint pjp) throws Throwable {
    long t0 = System.nanoTime();
    try {
        return pjp.proceed();   // ✅ 必须调 proceed，否则原方法不执行
    } finally {
        log.info("{} 耗时 {}ms", pjp.getSignature(), (System.nanoTime()-t0)/1_000_000);
    }
}
```

### 现场六：切点表达式太宽，把内部方法也织进去了

凯喵见过 `@Around("execution(* com.x..*.*(..))")` 把 `toString`、`hashCode` 全包了，日志刷屏还死循环（切面里调 toString 又触发切面）。切入点要精确：限定 service 包、限定特定注解或方法名前缀，必要时用 `@annotation` 只切标记了自定义注解的方法。

```java
// ❌ 太宽，连 toString/getter 都织入
@Pointcut("execution(* com.x..*.*(..))") 

// ✅ 只切 service 包下 public 方法
@Pointcut("execution(public * com.x.service..*.*(..))")

// ✅ 或用注解驱动，最干净
@Pointcut("@annotation(com.x.LogTime)")
```

### 现场七：多个切面顺序混乱，日志和事务谁先谁后说不清

凯喵的团队曾因多个 `@Aspect` 顺序不定，出现「事务回了滚但日志记了成功」。用 `@Order` 或实现 `Ordered` 明确优先级：数字越小越先执行（Outer 先入）。全局切面（如日志/鉴权）用低值先执行，事务用较高值后执行。

```java
@Aspect
@Order(1)   // 先执行（最外层）
public class LogAspect { ... }

@Aspect
@Order(10)  // 后执行（更靠近目标方法）
public class TxAspect { ... }
```

### 现场八：@After 读返回值永远是 null

凯喵新人想在「后置」里拿返回值做统计，写在 `@After` 里拿到 null。混淆了 `@After`（等同 finally，异常/正常都跑，拿不到返回值）和 `@AfterReturning`（只在正常返回后跑，能拿到 `returning` 参数）。要在 finally 里做事用 `@After`；要拿返回值用 `@AfterReturning`。

```java
@After("pointcut()")
public void after() { /* 拿不到返回值，等同于 finally */ }

@AfterReturning(pointcut = "pointcut()", returning = "ret")
public void afterReturning(Object ret) {
    log.info("返回值 = {}", ret);   // ✅ 这里能拿到
}
```

### 现场九：this 与 target 指向不同，切点匹配错对象

凯喵排查权限拦截失效，发现表达式用了 `this(AdminService)`。`this` 匹配的是**代理对象类型**，`target` 匹配的是**被代理的真实对象类型**。当接口代理时二者可能不同，权限这类应切真实类型的场景要用 `target`，别用 `this`。

```java
// this：代理对象（可能是接口代理）
@Pointcut("this(com.x.AdminService)")
// target：真实被代理对象
@Pointcut("target(com.x.AdminService)")
```

### 现场十：JDK 动态代理要求目标有接口

凯喵把没实现接口的类交给 Spring 默认配置，结果注入时报「找不到代理」。默认「有接口用 JDK 动态代理、无接口用 CGLIB」。若强制 `proxyTargetClass=false` 又没接口，就直接失败。Boot 2.x 起默认 `proxyTargetClass=true`（强制 CGLIB），代理具体类没问题。

```java
@Configuration
@EnableAspectJAutoProxy(proxyTargetClass = true)  // ✅ 强制 CGLIB，可代理具体类
public class AopConfig { }
```

### 现场十一：切面里捕获了异常，事务无法回滚

凯喵的同事在业务方法里 `try { ... } catch (Exception e) { log.error(e); }` 吞了异常，结果事务不回滚——因为 `@Transactional` 只认**抛出到代理层**的异常。要回滚就重抛，或用 `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()` 显式标记。

```java
@Transactional
public void biz() {
    try {
        dao.insert();
    } catch (Exception e) {
        // ❌ 吞掉异常 -> 事务提交
        TransactionAspectSupport.currentTransactionStatus()
            .setRollbackOnly();   // ✅ 显式标记回滚
        throw e;                  // ✅ 或重抛给代理
    }
}
```

### 现场十二：用 Aspect 做鉴权，却漏了内部入口

凯喵的权限切面只切 `Controller`，结果有人直接调 `Service` 绕过鉴权。AOP 只拦截它**切面覆盖的入口**，不是全局防火墙。安全类增强要切到「所有外部可达入口」（Controller + 内部 RPC），并配合网关层鉴权做纵深防御，不能只靠一个切面。

```java
// ❌ 只切 Controller，Service 直调绕过
@Pointcut("within(com.x.controller..*)")
// ✅ 切到业务入口更稳（再配合网关）
@Pointcut("within(com.x.service..*) || within(com.x.controller..*)")
```

> 凯喵总结：AOP 的坑几乎都绕不开「代理」二字——自调用绕过、final 代理不了、private 拦不到、Around 不 proceed、异常被吞。记住「一切增强发生在代理对象上」，这 12 个现场就不再是玄学。

## 三视角解析
### 🧑‍💻 程序员视角
同类内部方法自调用（`this.method()`）不走代理，`@Transactional`/`@Cacheable` 整段失效——因为调用没经过代理对象。要生效得注入自身代理（`AopContext.currentProxy()` 需开 `exposeProxy`）或把方法拆到另一个 Bean。`final` 类与 `final` 方法无法被 CGLIB 代理，Spring 会静默退回 JDK 动态代理或直接失败。`private` 方法上的 `@Transactional` 完全不生效，因为代理无法覆写它。

### 🎓 博士生视角
Spring AOP 是「运行期代理」而非「编译期织入」：JDK 动态代理基于接口，CGLIB 基于继承生成子类。这决定了它的能力边界——只能拦截「经代理对象的公开方法调用」，无法拦截自调用、构造器、静态方法与 `final` 方法。AspectJ 的编译期/加载期织入能突破这些限制，代价是构建复杂度。理解「代理边界」是排查「注解不生效」类问题的唯一钥匙，比背注解列表有用得多。

### 📚 考研者视角
面试必问：
1. **AOP 术语**：切面、连接点、切点、通知（前置/后置/环绕/异常/最终）、织入。
2. **两种代理**：JDK 动态代理要求目标实现接口，CGLIB 生成子类；Boot 2.x 默认 CGLIB。
3. **自调用失效**：原因（不走代理）与三种解法（自注入、`AopContext`、拆 Bean）。
4. **通知执行顺序**：多个切面用 `@Order` 控制，环绕通知内可修改返回值。
