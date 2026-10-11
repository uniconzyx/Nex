# 三、BeanPostProcessor 与 Aware 回调

## 一、BeanPostProcessor 原理与执行时机（中立陈述）

`BeanPostProcessor`（BPP）是 Spring 的**容器级 bean 拦截器**：在「每个 bean 实例化、属性填充之后」统一执行，提供两个钩子：

- `postProcessBeforeInitialization(bean, beanName)`：初始化（@PostConstruct 等）之前。
- `postProcessAfterInitialization(bean, beanName)`：初始化之后、进入单例缓存之前。

返回的对象会**替换原 bean**——这正是 AOP 生成代理的落点（`AbstractAutoProxyCreator` 在 `after` 里把原始 bean 换成代理）。与之相对，`BeanFactoryPostProcessor`（BFPP）在容器刷新、`BeanDefinition` 全部加载后、任何 bean 实例化**之前**执行，用来修改 bean 定义元数据（如占位符 `${}` 替换）。

### 🧑‍💻 程序员视角
- 实战：自研 BPP 做统一日志、字段脱敏、依赖校验。注意 `postProcessAfterInitialization` 里**必须返回 bean 本身**（或代理），返回 `null` 会把该 bean 整个替换成 null，所有注入点 NPE。
- 顺序：BPP 之间可用 `@Order` / 实现 `Ordered` 控制；AOP 的 `AbstractAutoProxyCreator` 默认 `order` 很低（靠后），保证业务 BPP 先跑。
- 性能：BPP 对「每一个 bean」都执行，逻辑里别做重活；用 `beanName` 或 `bean instanceof` 早退，只对目标 bean 处理。

### 🎓 博士生视角
- 机制：`AbstractAutowireCapableBeanFactory.initializeBean` 在「初始化」前后分别遍历 `beanPostProcessors` 列表调用两个钩子；`applyBeanPostProcessorsBeforeInitialization` 遇到返回 null 直接抛 `BeanPostProcessorException`，这就是「返回 null 即崩」的来源。
- BPP vs BFPP：`BFPP.postProcessBeanFactory` 操作的是 `ConfigurableListableBeanFactory` 上的 `BeanDefinition`（改类元数据，如改 scope、改构造器参数）；BPP 操作的是**已实例化的对象**（改/包装实例）。前者在「类定义层」、后者在「对象层」，层次不同。
- 为什么 AOP 在 `after` 而非 `before`：代理需要在「依赖已填充、初始化已完成」的对象上包一层，否则代理里的目标对象字段是空的；`after` 保证包的是完整 bean。

### 📚 考研者视角
- 笔面标准问法：「BeanPostProcessor 和 BeanFactoryPostProcessor 区别？」答：**BPP 在 bean 实例化后介入、能返回/替换实例（AOP 在此）；BFPP 在所有 bean 定义加载后、实例化前介入、改的是 BeanDefinition 元数据**。
- 易错口径：把 BPP 说成「在 getBean 之前执行」——不准确，它是在「bean 已 new 出来、填充之后、初始化前后」执行；「实例化之前」是 BFPP 的领地。
- 命题角度：常问「AOP 代理在哪一步生成」——答 `BeanPostProcessor.postProcessAfterInitialization`。

## 二、Aware 回调体系（中立陈述）

`Aware` 是一族「让 bean 感知容器基础设施」的标记接口，命名即 `XxxAware` + `setXxx(...)`：

- `BeanNameAware.setBeanName`：拿到 bean 在容器中的名字。
- `BeanFactoryAware.setBeanFactory`：拿到 `BeanFactory` 引用。
- `ApplicationContextAware.setApplicationContext`：拿到 `ApplicationContext`（功能最全）。
- 还有 `EnvironmentAware` / `ResourceLoaderAware` / `MessageSourceAware` 等。

回调时机统一在「属性填充之后、BPP 之前」由 `ApplicationContextAwareProcessor` 触发。

### 🧑‍💻 程序员视角
- 工程里尽量避免 `ApplicationContextAware`：它把业务 bean 和容器强耦合，破坏了 IoC「不主动要、等注入」的初衷；需要容器能力时优先用依赖注入直传所需对象（如直接注入 `ApplicationEventPublisher`）。
- 例外：`BeanNameAware` 偶尔用于按名打日志；自研框架/ starter 内部用 `ApplicationContextAware` 拿上下文属正常。
- 踩坑：实现 `ApplicationContextAware` 后若又被 AOP 代理，拿到的 `applicationContext` 是原始上下文没问题，但别在 `setApplicationContext` 里立刻用还没就绪的 bean。

### 🎓 博士生视角
- 机制：`ApplicationContextAwareProcessor` 是注册在容器里的特殊 BPP，在 `postProcessBeforeInitialization` 里判断 bean 是否实现某 `Aware`，是则调用对应 `setXxx`。它本质上**复用 BPP 通道**完成「回调式注入」，避免为每类 Aware 单独写注入代码。
- 设计动机：IoC 主张「对象不持有容器引用」，但有些基础设施（事件发布、环境读取）确实需要上下文。`Aware` 用「显式实现接口」换取上下文，比「到处 `new ClassPathXmlApplicationContext`」更可控，是 IoC 的受控例外。
- 顺序：`BeanNameAware` → `BeanFactoryAware`（及其子）在 `ApplicationContextAwareProcessor` 内按接口类型依次调用，均在初始化之前。

### 📚 考研者视角
- 笔面标准问法：「Aware 接口是干嘛的？常见有哪些？」答：**让 bean 拿到容器/环境等基础设施引用**；列举 `BeanNameAware`/`BeanFactoryAware`/`ApplicationContextAware`/`EnvironmentAware`。
- 易错口径：以为 Aware 在初始化之后回调——实际在「属性填充后、初始化前」（`ApplicationContextAwareProcessor` 的 BPP 前置阶段）。
- 关联考点：Aware 与 BPP 的关系——`ApplicationContextAwareProcessor` 本身就是 BPP，Aware 回调借 BPP 通道触发。

### 三视角小结

| 主题 | 程序员视角 | 博士生视角 | 考研者视角 |
|---|---|---|---|
| BeanPostProcessor | 自研拦截器、勿返 null、性能 | initializeBean 遍历、BPP vs BFPP 层次 | BPP vs BFPP 区别、AOP 落点 |
| Aware 回调 | 避免容器耦合、例外用法 | 复用 BPP 通道、受控例外 | 接口用途 + 回调时机 |
