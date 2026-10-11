# 二、CGLIB 子类代理与 JDK/CGLIB 边界

## 一、CGLIB 子类代理的原理（中立陈述）

CGLIB（Code Generation Library）通过**继承目标类、在运行时生成其子类**来代理：
子类重写父类的可覆写方法，在 `super.xxx()` 前后插入拦截器（`MethodInterceptor`）逻辑，
再把方法调用委派给父类实现。因为「生成子类」而非「实现接口」，所以**目标类无需实现任何接口**。

```
真实对象 UserService
   ↑ extends
UserService$$Enhancer (CGLIB 子类)  — 重写方法：before -> super.method() -> after
```

示例 ex05 用纯 JDK 手写了等效机制：定义 `Target_Enhancer extends Target` 并重写 `hello`，
在 `super.hello` 前后织入通知——这正是 CGLIB 的「原理内核」。

### 🧑‍💻 程序员视角
- 工程里 CGLIB 多见于「代理具体类」（如 MyBatis 的 Mapper 接口其实用 JDK，而 Spring 代理
  无接口 service 用 CGLIB；还有 `@Configuration` 的 Full 模式也是 CGLIB 子类）。
- 限制：CGLIB 无法代理 `final` 类（不能继承）、无法重写 `final`/`private` 方法
  （不能覆写，见 ex12）；构造器不会被代理，创建子类会先调父类无参构造。
- 性能：CGLIB 生成子类后方法是「直接调用 + 方法内拦截」，避免反射 `method.invoke`，
  单次调用比 JDK 代理快；但**生成代理类本身**有字节码生成开销，首次较慢。

### 🎓 博士生视角
- 字节码层面：CGLIB 用 ASM 在运行时改写字节码，生成 `Target$$Enhancer`，把 `MethodInterceptor`
  织进每个可覆写方法的开头/结尾；`invokeSuper` 才是调父类的真实方法（区别于 `invoke` 调自身导致递归）。
- 与 JDK 代理的本质同构：两者都是「在调用链上插入一个拦截层」——
  JDK 把拦截写在 `InvocationHandler.invoke`（接口方法体里调 Handler），
  CGLIB 把拦截写进子类重写方法体（方法体里调 Interceptor 再 `invokeSuper`）。AOP 的「代理范式」统一。
- 为何不能代理 final：Java 语义规定 `final` 方法不可重写、final 类不可继承，
  CGLIB 的「子类覆写」机制从根本上被堵死；这是语言层面的硬约束。

### 📚 考研者视角（面试笔试考点）
- 标准问法：「CGLIB 和 JDK 动态代理的区别？」答：JDK 基于接口、CGLIB 基于继承；
  JDK 不能代理类、CGLIB 不能代理 final 类/方法；CGLIB 运行时生成子类字节码。
- 常考口径：CGLIB 通过**继承 + 方法重写**实现，因此目标类不能是 `final`、方法不能是 `final`/`private`。
- 易混点：有人以为 CGLIB 也用反射委派——其实它生成子类后方法是直接调用（含拦截器），
  `MethodInterceptor.intercept` 里用 `methodProxy.invokeSuper(obj, args)` 调父类，
  用 `invoke` 会递归到自己。

## 二、JDK 与 CGLIB 的适用边界（中立陈述）

| 维度 | JDK 动态代理 | CGLIB |
|---|---|---|
| 前置条件 | 目标**必须实现接口** | 目标可为**普通类**（无需接口） |
| 实现方式 | 运行时生成接口实现类 | 运行时生成目标类的**子类** |
| 限制 | 只能代理接口方法 | 不能代理 `final` 类/`final`/`private` 方法 |
| 调用开销 | 反射 `method.invoke`（较慢） | 生成子类后直接调用（较快） |
| 生成开销 | 轻 | 字节码生成较重（首次） |

Spring 的取舍（默认策略）：
- Spring Boot 2.x 之前：有接口用 JDK，无接口用 CGLIB；
- Spring Boot 2.x 起：**默认强制 CGLIB**（`spring.aop.proxy-target-class=true`），
  以统一行为、避免「同一类型注入时 JDK 代理与 CGLIB 表现不一致」的困惑。

### 🧑‍💻 程序员视角
- 选型经验：若业务已抽接口（推荐做法），JDK 代理零额外依赖、更轻；若只是想给一个具体类加横切、
  又不想强行抽接口，用 CGLIB。现代 Spring Boot 项目基本无需纠结——默认 CGLIB。
- 坑：强制 CGLIB 后，若目标类是 `final` 或方法是 `final`，启动会直接失败
  （`Cannot subclass final class`），需改掉 final 或换 JDK 接口代理。
- 类型注入：`AopContext.currentProxy()` 可在自调用时拿到代理（见 04），但它要求
  `exposeProxy=true`，且仍比「抽取方法到协作 bean」脆弱。

### 🎓 博士生视角
- 边界的本质是「单继承」：JDK 代理类已 `extends Proxy`，无法再继承业务类 → 只能 implements 接口；
  CGLIB 放弃接口、选择继承 → 突破了「必须接口」，却撞上 `final` 的继承墙。
  两者都在 Java 类型系统的约束下各取一边。
- 性能差异来源：JDK 的反射调用每次都要做可访问性检查、参数装箱、Method 查表；
  CGLIB 生成的子类方法是「静态绑定 + 内联友好」的直接调用。但现代 JVM 对反射有方法句柄/
  内联缓存优化，差距在缩小；真正开销大头在「首次生成代理类」。

### 📚 考研者视角（面试笔试考点）
- 标准问答：「什么时候用 JDK 代理、什么时候用 CGLIB？」答：目标有接口→可 JDK；
  无接口或代理具体类→CGLIB；final 类/方法只能 JDK（前提是接口）。
- 常考命题：Spring AOP 默认用哪种？答：老版「有接口 JDK、无接口 CGLIB」，
  Spring Boot 2.x 起默认 CGLIB。
- 易错：以为「CGLIB 更快所以永远选 CGLIB」——忽略 final 限制与生成开销，也忽略接口优先的设计直觉。

### 三视角小结

| 主题 | 程序员视角 | 博士生视角 | 考研者视角 |
|---|---|---|---|
| CGLIB 子类代理原理 | 工程用途/final 限制/调用更快 | ASM 字节码/与 JDK 同构/final 硬约束 | 继承+重写、不能 final |
| JDK vs CGLIB 边界 | 选型经验/final 启动失败/exposeProxy | 单继承约束两面/性能来源 | 默认策略与最终答案 |
