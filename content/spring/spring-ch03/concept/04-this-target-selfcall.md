# 四、this 与 target 区别及自调用代理失效

## 一、this 与 target 的语义区别（中立陈述）

在 AOP 语境里：
- **`target`**：被代理的**真实对象**（业务实现），即 `InvocationHandler` 持有的那个 `target`，
  或 CGLIB 子类的 `super`。
- **`this`**：**代理对象本身**（`$Proxy` / `$$Enhancer` 实例）。

示例 ex08 验证：`Proxy.isProxyClass(proxy.getClass())==true`（this 是代理），
`target.getClass().getSimpleName()` 是真实类，且 `proxy == target` 为 `false`——
二者是不同对象。切点里 `this(类型)` 匹配的是「代理对象类型」、`target(类型)` 匹配的是「真实对象类型」，
在 CGLIB 下二者类型不同（代理是子类），JDK 下 this 是实现接口的不相关类。

### 🧑‍💻 程序员视角
- 工程里分清二者能避免奇怪 bug：比如想在通知内拿到「当前代理」走代理（而非原始对象）要用 `this`；
  想强制走真实方法、避免二次拦截要直接操作 `target`。
- `AopContext.currentProxy()` 能在被代理对象内部拿到 `this`（代理），用于解决自调用（见下）；
  但它要求 `exposeProxy=true`，且仍比「抽取方法到协作 bean」脆弱。
- 切点表达式中 `this()`/`target()` 在 CGLIB 代理下差异明显：`this(RealService)` 不命中
  （this 是子类 `RealService$$Enhancer`），`target(RealService)` 命中——写错就织不进去。

### 🎓 博士生视角
- 二者的差异是「代理层」存在的直接证据：`target` 处于调用链末端（真正干活），
  `this` 处于链首（拦截入口）。它们在内存里是两个独立对象，`this` 通过「持有 target 引用 +
  转发调用」与 target 产生关联，但身份不同。
- 类型关系：JDK 代理里 `this` 是「接口实现者、extends Proxy」的 `$Proxy`，
  `target` 是实现该接口的业务类——`this instanceof 业务类` 为 false；CGLIB 里
  `this` 是 `target` 的**子类**，`this instanceof target类型` 为 true（见 ex05 的 `instanceof` 验证）。
- 为什么 `proxy==target` 恒 false：代理从来不「是」真实对象，只是「包裹」它；
  任何想把代理当真实对象 `==` 比较、或把代理强转成未实现的类，都会失败。

### 📚 考研者视角（面试笔试考点）
- 标准问法：「AOP 里 this 和 target 的区别？」答：this 是代理对象、target 是被代理的真实对象；
  JDK 代理下 this 不是业务类实例，CGLIB 下 this 是 target 的子类。
- 常考口径：切点 `this(X)` 与 `target(X)` 命中差异——CGLIB 代理时 this 是 X 子类、target 是 X，
  因此 `target(X)` 命中、`this(X)` 可能不命中（取决于是否按父类匹配）。
- 易错：以为 `this` 在 AOP 里指「业务对象」——恰恰相反，它指代理；真要业务对象用 target。

## 二、同类内部自调用导致代理失效（中立陈述）

当被代理对象的方法 **A** 内部直接调用同对象的 **B**（且 B 本应被增强）时，这个内部调用是
`this.B()`——而此时的 `this` 是**真实对象**（target），**不是代理**，
于是 B 的调用不会经过 `InvocationHandler`/`MethodInterceptor`，B 上的通知全部丢失。
示例 ex09 显示：`proxy.a()` 触发了 a 的环绕通知，但 a 内部 `b()` 的调用**没有任何通知**——
只有从外部直接 `proxy.b()` 才有通知。

根因：Spring 的 AOP 是「代理层」增强，只有「从代理进入」的调用才被拦截；
对象内部的 `this.method()` 绕过代理，直接命中真实方法。

### 🧑‍💻 程序员视角
- 这是 AOP 最经典的生产坑：事务方法 `save()` 调同类的 `update()`（`@Transactional`），
  结果 `update` 的事务不生效、没回滚——根因就是自调用绕过代理。
- 修复手段（按推荐度）：
  1. 把被调方法抽到另一个 Spring Bean，用依赖注入调用（最干净）；
  2. 用 `AopContext.currentProxy()` 拿代理再调（`((X) AopContext.currentProxy()).update()`）；
  3. 用自注入（`@Autowired X self;`）再 `self.update()`（本质是拿到代理）。
- 经验法则：**「想让 AOP 生效，调用必须经由 Spring 容器返回的代理对象」**；
  凡是 `this.xxx()`、私有方法互调，都要警惕。

### 🎓 博士生视角
- 失效的精确机理：代理增强只发生在「调用方持有的是代理引用、且经接口/CGLIB 转发」的路径上。
  一旦进入真实对象的方法体，方法体里的 `this` 是 JVM 提供的真实对象自身（`aload_0`），
  与代理无关；后续 `invokevirtual` 直接绑到真实方法，不经过任何拦截层。
- 与「代理层位置」的必然关系：AOP 不是改写业务字节码（那是 AspectJ 的 LTW/CTW 编译织入），
  而是「外包一层代理」。代理之外（对象内部）自然无增强——这是「代理型 AOP」的固有边界，
  也是 AspectJ 编译期织入能解决自调用的原因。
- `AopContext.currentProxy()` 的原理：Spring 在创建代理时把代理引用 `ThreadLocal` 暴露，
  真实方法体内读取它即拿到代理，从而「自我经由代理再调用」，代价是线程绑定与可测试性下降。

### 📚 考研者视角（面试笔试考点）
- 标准问答：「为什么 @Transactional 在同类方法互调时失效？」答：自调用走 `this` 真实对象、
  绕过代理，通知不触发；解决靠拆 Bean / `AopContext` / 自注入。
- 常考命题：给一段「serviceA 调 this.serviceB 的事务方法」代码，问「B 的事务是否生效」——答不生效。
- 易错：以为「只要方法标了注解就一定增强」，忽略「调用路径是否经过代理」才是前提。

### 三视角小结

| 主题 | 程序员视角 | 博士生视角 | 考研者视角 |
|---|---|---|---|
| this 与 target | 分清二者避坑/切点差异/exposeProxy | 代理层两端、类型关系、== 恒 false | this 是代理、target 是真实 |
| 自调用代理失效 | 事务失效经典坑、三种修复 | 代理层边界/AspectJ 对比/ThreadLocal | 同类互调事务不生效 |
