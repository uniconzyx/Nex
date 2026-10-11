# 一、Bean 生命周期：从定义到销毁

## 一、完整生命周期阶段（中立陈述）

Spring 单例 Bean 在 `ApplicationContext` 启动时（或首次 `getBean` 时，懒加载）经历一条确定性流水线：

1. **BeanDefinition 注册**：容器把 `<bean>` / `@Component` / `@Bean` 解析成 `BeanDefinition`，存进 `beanDefinitionMap`（beanName → 定义）。
2. **实例化（Instantiation）**：反射调用构造器 `ctor.newInstance()` 得到一个「半成品」对象。
3. **属性填充（Populate）**：按注入方式把依赖 set 进字段/Setter（DI 的核心动作）。
4. **Aware 回调**：若实现 `BeanNameAware` / `BeanFactoryAware` / `ApplicationContextAware` 等，容器回调注入对应上下文。
5. **BeanPostProcessor 前置**：所有 BPP 的 `postProcessBeforeInitialization` 依次执行。
6. **初始化**：`@PostConstruct` → `InitializingBean.afterPropertiesSet()` → 自定义 `init-method`（顺序固定）。
7. **BeanPostProcessor 后置**：`postProcessAfterInitialization`（AOP 代理常在此生成）。
8. **就绪使用**：bean 进入 `singletonObjects` 一级缓存，对外提供服务。
9. **销毁**：容器关闭时，`@PreDestroy` → `DisposableBean.destroy()` → `destroy-method`。

### 🧑‍💻 程序员视角
- 工程里记住关键不变量：**Aware 在初始化之前、BPP 前后夹着初始化、初始化三方式顺序固定**（@PostConstruct 最早）。线上排查「某初始化逻辑没执行」最先怀疑：类是否被容器管理？是否因抛异常直接中断？
- 性能：BPP 是「每个 bean 都会过一遍」的全局拦截器，数量多了放大启动耗时；自研 BPP 要用 `getBeanName()` 过滤作用范围，别无差别地扫全部 bean。
- 踩坑：在 `@PostConstruct` 里调别的 bean，那个 bean 可能还没初始化完（依赖未就绪）→ 偶发 NPE。把逻辑挪到 `ApplicationRunner`/`CommandLineRunner`（所有单例就绪后统一跑）更稳妥。

### 🎓 博士生视角
- **实例化**是「分配对象内存、调构造器」（对象已存在但字段可能为空），**初始化**是「对象已完整、业务就绪」。Spring 在实例化后即暴露「早期引用」（三级缓存的 ObjectFactory），正是为了让循环依赖方能在「初始化之前」拿到引用。
- 初始化三方式有固定顺序：`@PostConstruct` 由 `CommonAnnotationBeanPostProcessor` 在 BPP 前置阶段触发；`InitializingBean` 由 `invokeInitMethods` 在 BPP 之后、`init-method` 之前直接调用；`init-method` 通过反射最后调用。顺序是「注解驱动 → 接口契约 → 配置约定」的优先级叠放。
- 形式化：把生命周期看成状态机 `∅ → instantiated → populated → aware → initialized → ready → destroyed`，每个迁移由特定处理器触发，BPP 在 `populated→initialized` 与 `initialized→ready` 两个边上各挂一个切面。

### 📚 考研者视角
- 面试/笔试标准问法：「说一下 Bean 的生命周期。」标准骨架就是上面 9 步，能按顺序背出并点出「初始化三方式顺序、销毁三方式顺序」即可拿分。
- 易错口径：把 `@PostConstruct` 和构造器混淆——**构造器属于「实例化」阶段，@PostConstruct 属于「初始化」阶段，先后明确**。不要说「构造器里就能用注入的依赖」，那时还没填充。
- 命题角度：常让判断「@PostConstruct / afterPropertiesSet / init-method 哪个最先」——答 @PostConstruct；销毁同理 @PreDestroy 最先。

## 二、初始化与销毁的三种方式及顺序（中立陈述）

Spring 提供两套各三种等价钩子：
- **初始化**：`@PostConstruct`（JSR-250 注解）、`InitializingBean.afterPropertiesSet()`、`init-method`（XML/@Bean 指定方法名）。
- **销毁**：`@PreDestroy`（JSR-250）、`DisposableBean.destroy()`、`destroy-method`。

调用顺序——初始化：`@PostConstruct` → `afterPropertiesSet` → `init-method`；销毁相反：`@PreDestroy` → `destroy` → `destroy-method`。

### 🧑‍💻 程序员视角
- 工程首选 `@PostConstruct` / `@PreDestroy`：零侵入、与 Spring 解耦（JSR 标准，换框架也能认）；`InitializingBean`/`DisposableBean` 让代码耦合 Spring 接口，一般不优先；`init-method` 适合接入第三方没法加注解的类。
- 实战：数据源、Redis 连接、线程池等需显式 close 的资源，务必在销毁钩子里释放，否则容器关停时连接泄漏；把 `ExecutorService.shutdown()` 放在 `@PreDestroy`。
- 替代：Spring Boot 里「容器起来后做一次性任务」更推荐 `ApplicationRunner`，它保证所有单例已就绪，而 `@PostConstruct` 时序偏早。

### 🎓 博士生视角
- 这几套钩子本质是「生命周期回调契约」的三种来源：注解（通用标准）、接口（框架强契约）、配置（外部约定），框架按「内外优先级」统一调度，归一化到同一个 `invokeInitMethods` / `invokeDestroyMethods` 调用点——「多入口、单处理点」的设计。
- 为什么注解优先于接口？`CommonAnnotationBeanPostProcessor` 作为 BPP 在「初始化前」就执行注解，而 `InitializingBean` 是 `AbstractAutowireCapableBeanFactory` 在 `invokeInitMethods` 里硬编码调用——注解路径更早且不需要 bean 实现框架接口（开闭原则更好）。
- 调用顺序由源码语句顺序决定，不是配置项，因此「@PostConstruct 永远先于 afterPropertiesSet」是确定性、可依赖的。

### 📚 考研者视角
- 标准问答：「三种初始化方式谁先谁后？」固定答：**@PostConstruct → InitializingBean.afterPropertiesSet → init-method**；销毁：**@PreDestroy → DisposableBean.destroy → destroy-method**。
- 易错：有人以为 `init-method` 比接口方法早——错，接口契约在框架内部、配置约定最晚。
- 关联考点：这些注解来自 JSR-250（`jakarta.annotation`），属「Java 通用注解」而非 Spring 专有，笔试常考出处。

### 三视角小结

| 主题 | 程序员视角 | 博士生视角 | 考研者视角 |
|---|---|---|---|
| 完整生命周期 | 不变量 + BPP 性能 + 启动期时序 | 实例化≠初始化、状态机 | 9 步骨架 + 顺序判定 |
| 初始化/销毁三方式 | 首选注解、资源释放 | 多入口单处理点 | 固定顺序背记 |
