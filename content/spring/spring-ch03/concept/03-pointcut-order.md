# 三、切点表达式与通知执行顺序

## 一、execution 切点匹配（中立陈述）

切点是「对哪些连接点织入通知」的断言。Spring 用 AspectJ 切点表达式，最常用 `execution`：
`execution([修饰符] 返回类型 包.类.方法(参数) [异常])`，其中 `*` 为通配、`..` 表示「任意包/任意参数」。
示例 ex07 手写了简化版匹配器：解析 `ret pkg.Cls.method(args)`，
对返回类型、包（支持 `pkg.*`）、类、`save*` 前缀方法、`(int)`/`(..)` 参数个数做匹配。

典型表达式：
- `execution(* com.demo.*.*(..))`：com.demo 包下任意类的任意方法、任意返回、任意参数；
- `execution(* com.demo.UserService.save*(..))`：save 前缀方法；
- `execution(public int com.demo.*.calc(int))`：返回 int、单 int 参数。

### 🧑‍💻 程序员视角
- 工程惯例：切点**收窄到接口/具体方法**，别写 `execution(* *(..))` 全量拦截——
  会把 Spring 内部 Bean、toString/hashCode 都织进去，既慢又易出循环依赖/栈溢出。
- 实用技巧：用 `@annotation(com.x.Log)` 这种「注解驱动切点」替代冗长 execution，
  把「要不要增强」的决定权交给业务方打标签，可读性最好。
- 坑：execution 的「类」写的是**目标类型**，CGLIB 代理时若写 `UserService+`（`+` 表示含子类）
  与只写 `UserService` 结果不同；JDK 代理时只有接口类型，别写实现类。

### 🎓 博士生视角
- 切点匹配是「模式 ⇒ 布尔」的纯函数：给定 `(retType, declaringClass, methodName, paramTypes)`
  四元组，与表达式做结构比对。`*` 是单段通配、`..` 是「零或多段/零或多参数」的贪婪通配，
  解析时要把字符串按 `.`/`(`/`)` 切分成「包段序列 + 类 + 方法 + 参数签名」再逐段比对。
- 性能：真实 AspectJ 会把切点编译成「类型/方法索引 + 快速前缀判定」，避免每次调用全量正则；
  手写匹配器（ex07）是 O(表达式项数) 的线性匹配，足以讲清原理。
- 与「注解切点」的等价：注解切点本质是把「匹配键」从「签名文本」换成「类上的元数据标签」，
  匹配成本更低（一次 `isAnnotationPresent` 即可）。

### 📚 考研者视角（面试笔试考点）
- 标准问法：「execution 表达式怎么写？`*` 和 `..` 什么意思？」答：`*` 单段任意、
  `..` 任意层包或任意参数；`execution(* com.x.*.*(..))` 是「某包全部方法」的模板写法。
- 常考口径：给定表达式判断「某方法是否命中」是高频选择/判断题型，先判返回、再判包、再判类、方法、参数。
- 易混点：`*` 与 `..` 粒度不同——`com.x.*.Service` 只匹配 com.x 的**直接子包**下一层，
  而 `com.x..*.Service` 的 `..` 才能跨多层包。

## 二、通知执行顺序（中立陈述）

Spring AOP 同一切点上有多通知时的顺序：环绕 `@Around` **包裹**其余通知；
进入方法前 `@Around` 先跑、`@Before` 随后；方法返回后 `@After`(始终) →
`@AfterReturning`(正常) / `@AfterThrowing`(异常)，最后 `@Around` 收尾返回。
多个同类通知之间有 `@Order` 优先级。责任链视角下（ex11），拦截器按列表顺序「先进后出」嵌套，
形成 `Interceptor1 → Interceptor2 → … → 目标 → … → Interceptor2 → Interceptor1`。

### 🧑‍💻 程序员视角
- 经验：把「开启/提交事务」放 `@Around`、「记日志/计时」也放 `@Around`、「参数校验」放 `@Before`、
  「资源清理」放 `@After`。顺序错了（如把提交放 Before 之前）会破坏事务语义。
- 两个 `@Around` 嵌套时，外层先进入、后退出——理解「嵌套而非并列」是避免重复计时/重复提交的关键。
- 坑：`@After` 与 `@AfterReturning` 区别在于前者**无论成败都执行**（像 finally）、后者只在正常返回时；
  在 `@After` 里拿返回值会拿到 `null`，要在 `@AfterReturning` 拿。

### 🎓 博士生视角
- 顺序由「通知类型 → 责任链编织顺序」决定。Spring 把每个通知包装成 `MethodInterceptor`，
  按 `@Order` + 类型优先级排成链：`@Around` 最先入链（因为它要包裹全部），`@Before` 次之，
  `@After`/`@AfterReturning`/`@AfterThrowing` 在链尾以「先注册先靠近目标」的方式夹住目标调用。
- 形式化：令链为 `C = [A_round, B_before, ... ， target ， A_after... ]`，
  `proceed()` 逐层下沉，归程逆序执行 after 类通知——这正对应 ex11 打印的嵌套输出。
- `@Order` 越小越靠近目标（优先级越高、越早进入），这是与「拦截器链顺序」一致的约定。

### 📚 考研者视角（面试笔试考点）
- 标准问答：「同一切点多个通知，执行顺序是？」答：Around 进入 → Before → 目标 →
  After（始终）→ AfterReturning/AfterThrowing → Around 退出；多通知按 `@Order` 区分。
- 常考命题：给出打印顺序填空，核心是「Around 包裹、After 类像 finally、异常时走 AfterThrowing 不走 AfterReturning」。
- 易错：把 `@After` 当成「方法返回后」而忽略它**异常也执行**；以及混淆 `@AfterReturning` 与 `@AfterThrowing` 的二选一。

### 三视角小结

| 主题 | 程序员视角 | 博士生视角 | 考研者视角 |
|---|---|---|---|
| execution 切点匹配 | 收窄切点/注解切点/类型陷阱 | 四元组匹配函数/性能/等价注解 | * 与 .. 语义、命中判断 |
| 通知执行顺序 | 通知分工/嵌套理解/After 语义 | 责任链编织/Order 约定/形式化 | Around 包裹、After 类二选一 |
