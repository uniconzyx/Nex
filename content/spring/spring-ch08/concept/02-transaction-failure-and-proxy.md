# 二、事务失效的典型场景与 AOP 代理机制

「加了 `@Transactional` 却没回滚」几乎总能归结为一句话：**这次调用根本没经过事务代理**，
或者**经过了代理、但规则不允许它回滚**。前者是代理问题，后者是属性配置问题。

## 1. 八类事务失效场景

```
失效归因两大分支
├── 代理没生效（拦截器没跑）
│   ├── 同类自调用：this.method()
│   ├── 非 public 方法：代理不增强
│   ├── 对象不是 Spring Bean（自己 new 出来的）
│   └── 数据库引擎不支持事务（MyISAM）
└── 代理跑了，但规则不回滚
    ├── 异常被 catch 吞掉（方法正常返回）
    ├── checked 异常默认不回滚
    ├── 多线程/异步：不在同一线程，上下文丢失
    └── 传播行为用错（如误用 NOT_SUPPORTED / NEVER）
```

本机实测证据：

- `ex01`：`proxy.audited()` 触发拦截器 = **true**；`this.audited()` 自调用 = **false**；
  经 `exposed proxy` 自调用 = **true**（说明「暴露代理」可修复自调用）；
- `ex06`：RuntimeException 回滚 = **true**；checked 异常回滚 = **false**（经典坑）；
- `ex07`：异常被 catch 吞掉 → 事务提交 = **true**；异常外抛 → 回滚 = **true**；
- `ex08`：public `@Tx` 经代理被拦截 = **true**；package-private / private 的 `@Tx`
  在接口上不存在、也不被代理增强；
- `ex09`：单线程上下文正确 = **true**，但线程池复用且不清理时**串号** = **true**。

### 🧑‍💻 程序员视角
- 自调用的工程修法三选一：把内层方法挪到**另一个 Bean**、注入**自身代理**、
  或开启 `@EnableAspectJAutoProxy(exposeProxy = true)` 后用 `AopContext.currentProxy()`；
- 上线事故：Service 里一个 `public` 方法调用本类另一个 `@Transactional` 的私有/包级方法，
  线上「偶尔不回滚」——切面根本没织入，日志里连事务 begin 都没有；
- 排查顺序：① 看拦截器是否触发（`TransactionInterceptor` 的 DEBUG 日志）；② 看方法是不是
  `public`、是不是通过注入的 Bean 调用；③ 看异常类型是否在 `rollbackFor` 内；
  ④ 看异常有没有被上层 catch；⑤ 看是否跨线程。

### 🎓 博士生视角
- 代理的本质约束：Spring AOP 只能增强**从代理对象进入**的调用。`this.m()` 是对目标对象的
  直接调用，字节码里是一次 `invokespecial`，**天然绕开代理**——这不是 Spring 的 bug，
  而是「运行时代理」范式的必然边界（与之相对，AspectJ 的编译期/加载期织入能增强自调用）；
- 「非 public 不增强」的根因：`AbstractAutoProxyCreator` 只对 `public` 方法（以及 CGLIB 的
  `protected`/包可见方法）做可见性判定，JDK 代理更是只能代理接口的 public 方法；
- `rollbackOnly` 与「异常被吞」的耦合：若参与了外层事务而内层异常被吞，外层提交时会因
  `rollbackOnly` 抛 `UnexpectedRollbackException`——「数据没保存」却「方法没报错」的诡异现象。

### 📚 考研者视角
- 笔面标准问法：「`@Transactional` 什么情况下失效？」标准答（照上面两大分支作答，能答满 6~8 条最佳）；
- 常考追问：「同类调用为什么失效？怎么解决？」标准答：不走代理；改用自注入 / 拆 Bean /
  `AopContext.currentProxy()`；
- 易错点：把「`@Transactional` 加在 `private` 方法上」当成会生效——实际上 Spring 代理模式下无效
  （AspectJ 模式例外，需显式说明）。

## 2. 事务与 AOP 代理：JDK 动态代理 vs CGLIB

Spring 事务的底座是 `TransactionInterceptor`，它挂在一个代理对象上。

```
调用方 --> [ 代理对象 ] --(环绕通知)--> [ 目标对象 ]
              |                              |
              | TransactionInterceptor:      |
              |  begin / commit / rollback   |
              +------------------------------+
JDK 动态代理：要求目标实现接口，代理与被代理是「兄弟关系」（都实现同一接口）
CGLIB 代理  ：继承目标类生成子类，代理与被代理是「父子关系」（无需接口，不能代理 final）
```

关键配置：`@EnableAspectJAutoProxy(exposeProxy = true, proxyTargetClass = true)`。
`exposeProxy=true` 会把当前代理放进 `AopContext` 的 ThreadLocal，让自调用也能拿到代理。
Spring Boot 2.x 起默认 `proxyTargetClass=true`（即默认走 CGLIB）。

### 🧑‍💻 程序员视角
- 选型：有接口时 JDK 代理够用且更「轻」；需要代理类上方法（无接口）或字段注入时用 CGLIB；
  Spring Boot 默认 CGLIB，所以「明明没写接口也能被增强」是正常的；
- 事故：给 `final` 类 / `final` 方法加 `@Transactional`——CGLIB 无法子类化，
  启动直接报错或注解静默失效；
- 排查顺序：先 `AopUtils.isAopProxy(bean)` / `AopUtils.isCglibProxy(bean)` 看代理类型，
  再看 `bean` 是不是原始对象（`AopProxyUtils.getSingletonTarget`）。

### 🎓 博士生视角
- CGLIB 通过 ASM 生成子类并覆写方法，在方法内插入 `MethodInterceptor` 回调；因此
  `final` / `private` / `static` 方法无法被覆写 → 无法增强；JDK 代理只需实现接口，
  但代价是「只能按接口类型注入」，`@Autowired` 按实现类注入时可能注入失败（除非也实现接口）；
- 自调用的形式化边界：增强点在「方法入口的调用边」上，而非「方法本身」。`this.m()` 不产生
  新的调用边（同一对象内），故无增强点；
- `AopContext.currentProxy()` 的代价：它依赖一个 ThreadLocal，跨线程同样会丢；
  且要求 `exposeProxy=true`，属于「为绕开范式边界打的补丁」。

### 📚 考研者视角
- 笔面标准问法：「Spring AOP 用 JDK 代理还是 CGLIB？」标准答：目标实现接口默认 JDK，
  否则 CGLIB；可用 `proxyTargetClass=true` 强制 CGLIB；Spring Boot 2.x 默认 CGLIB；
- 常考追问：「为什么 `final` 方法不能被事务增强？」答：CGLIB 靠继承覆写，`final` 不可覆写；
- 关联考点：`@Transactional` 生效的前提是「Spring 容器管理的 Bean + 从代理进入的 public 调用」。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 失效先分「代理没生效」还是「规则不回滚」；自调用三选一修复；`final`/非 public 高度危险。 |
| 博士生 | 代理范式只增强「从代理进入的调用边」，`this.m()` 无新调用边；CGLIB 靠子类覆写，故 final 失效。 |
| 考研者 | 必考「失效场景清单」与「JDK vs CGLIB」；记住 `exposeProxy` 与 `AopContext.currentProxy()`。 |
