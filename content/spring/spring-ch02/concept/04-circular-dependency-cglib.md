# 四、循环依赖、三级缓存与 @Configuration 代理

## 一、循环依赖与三级缓存（中立陈述）

**单例 + Setter/字段注入**的循环依赖（A 依赖 B、B 依赖 A）能被 Spring 解决，靠**三级缓存**：

- 一级 `singletonObjects`：成品单例。
- 二级 `earlySingletonObjects`：早期暴露的「半成品」引用（已实例化、未初始化完）。
- 三级 `singletonFactories`：能产出早期引用的 `ObjectFactory`（lambda，调用 `getEarlyBeanReference`）。

流程：实例化 A → 把「A 的早期引用工厂」放进三级缓存 → 填充 A 需要 B → 创建 B（同样暴露） → 填充 B 需要 A → 从三级缓存取 A 的早期引用（升到二级）注入 B → B 完成进一级 → 回到 A 注入成品 B。**构造器注入**和 **prototype** 的循环依赖救不了：前者还没实例就无法暴露早期引用，后者不缓存早期引用。

### 🧑‍💻 程序员视角
- 工程上**不要依赖循环依赖**：它是「能编过但设计有 smells」的信号，应抽接口/搬逻辑拆环；实在要保留时确保是字段/Setter 注入（单例），并加 `@Lazy` 兜底更稳。
- 排查：`BeanCurrentlyInCreationException` 即循环依赖创建中异常——构造器循环依赖启动即崩；prototype 循环依赖每次 `getBean` 都崩。
- 为什么三级而非两级：两级时「无循环也会提前生成 AOP 代理」违背懒代理；三级存工厂，把「是否提前代理」推迟到真正需要早期引用时。

### 🎓 博士生视角
- 为什么需要三级：`getEarlyBeanReference` 返回的可能是**原始对象**，也可能是**AOP 代理**（若该 bean 要被代理）。三级缓存存工厂而非直接存引用，使得「要不要代理、代理谁」延迟到「依赖方真正来取早期引用」那一刻才决定——避免无循环时白白生成代理、也保证有循环时注入的是最终会被增强的同一对象。
- 状态机：创建中 bean 名进 `singletonsCurrentlyInCreation` 集合；`doCreateBean` 在实例化后即 `addSingletonFactory`（进三级）；依赖方 `getSingleton` 命中三级时 `getObject()` 并 `move` 到二级；最终 `addSingleton`（进一级、清二级三级）。
- 为什么构造器救不了：`getEarlyBeanReference` 需要在「实例已存在」后才有东西可暴露；构造器注入阶段对象尚未 new 出来，无法提前暴露，循环链在实例化这一步就死锁。

### 📚 考研者视角
- 笔面标准问法：「Spring 怎么解决循环依赖？为什么用三级缓存而不是两级？」答：三级缓存 + 早期引用工厂；三级把「是否提前 AOP 代理」推迟到真正需要时，两级会无谓提前代理且无法统一原始/代理。
- 易错口径：说「二级缓存就够了」——忽略 AOP 场景下「早期引用到底是原始对象还是代理」必须延迟决策，这正是第三级工厂存在的意义。
- 命题角度：常追问「加了 AOP 后早期引用返回的是代理还是原始对象」——答：经 `getEarlyBeanReference` 若需代理则返回代理，保证注入与最终成品是同一被增强对象。

## 二、@Configuration 的 CGLIB 代理保证单例（中立陈述）

`@Configuration` 标注的配置类在容器里被**增强**：Spring 用 CGLIB 生成它的子类（`AppConfig$$SpringCGLIB`），**重写每个 `@Bean` 方法**，方法体变成「先去容器单例缓存查，命中就返回，未命中才调父类 `super.xxx()` 真正创建并注册」。这样即便类内 `@Bean` 方法**互调**（如 `audit()` 里调 `service()`），也走容器缓存，保证单例共享。若误写成 `@Component`，则只是普通类，`@Bean` 互调是普通方法调用，每次新建——单例变多例。

### 🧑‍💻 程序员视角
- 工程铁律：**装配 bean 的配置类必须标 `@Configuration`**，不要图省事标 `@Component`，否则类内 `@Bean` 互调悄悄产出多例，隐蔽且难查（单测可能碰巧通过，集成才暴露）。
- 验证：`@Configuration` 下 `config.service() == config.audit().getService()` 为 true；`@Component` 下为 false。
- 取舍：CGLIB 要求类非 final、方法非 final；`@Bean` 方法设成 `final` 会跳过增强，回到「普通调用」语义——别这么写。

### 🎓 博士生视角
- 机制：CGLIB 通过 `Enhancer` 生成子类，重写 `@Bean` 方法为 `BeanMethodInterceptor`：调用前查 `Container.singletonObjects`（或 `factoryBean` 缓存），命中返回、未命中才 `invokeSuper`。子类的「方法重写」正是把「方法调用」重定向到「容器查找」，等价于手工子类覆盖——见本章示例 ex10 的手写模拟。
- 为什么必须代理而不是反射调用：配置类可能有**多个 @Bean 互相依赖**，只有「每次进入 @Bean 方法都先过一遍容器」才能统一保证单例；反射无法在「方法内部互调」时拦截，唯有字节码层面重写方法体（CGLIB）或接口动态代理能做到。
- `@Component` 不增强：`@Component` 走的是普通组件注册路径，没有 `ConfigurationClassEnhancer` 介入，因此 `@Bean` 方法就是普通 Java 方法，互调自然每次 `new`。

### 📚 考研者视角
- 笔面标准问法：「@Configuration 和 @Component 里的 @Bean 有什么区别？」答：**@Configuration 被 CGLIB 增强、@Bean 互调走容器缓存保证单例；@Component 不增强、互调每次新建多例**。
- 易错口径：以为「只要标了 @Bean 就一定是单例」——错，是否单调取决于所在配置类是否被增强（@Configuration）。
- 关联考点：CGLIB 基于继承重写方法，故 `@Configuration` 类与 `@Bean` 方法都不能是 `final`；这与 JDK 动态代理（基于接口）形成对比。

### 三视角小结

| 主题 | 程序员视角 | 博士生视角 | 考研者视角 |
|---|---|---|---|
| 循环依赖与三级缓存 | 别依赖、@Lazy 兜底、异常识别 | 工厂延迟代理决策、状态机 | 三级 vs 两级、AOP 早期引用 |
| @Configuration CGLIB | 必须标 @Configuration、final 陷阱 | Enhancer 重写方法重定向容器 | @Configuration vs @Component |
