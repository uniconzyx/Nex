# 易错点（spring-ch02）

1. **prototype 注入 singleton 不是每次新实例** —— 单例在创建时只注入一次 prototype，之后长期持有同一引用；想每次新实例要用 `ObjectProvider.getObject()` 或 `@Lookup`，而不是在字段上直接 `@Autowired PrototypeBean`。**正确写法**：`@Autowired ObjectProvider<Proto> provider;` 用时 `provider.getObject()`。

2. **@PostConstruct / @PreDestroy 方法必须无参且返回 void、且类被容器管理** —— 方法有参或有返回值、或类只是普通 new 出来的（未进容器），回调都不会触发、也不会报错，排查时极易误以为「逻辑没跑」。**正确写法**：`@PostConstruct void init(){}` 且类带 `@Component`/@`@Service` 等被扫描。

3. **初始化方法抛异常时，半成品 bean 不会走销毁回调** —— 若在 `afterPropertiesSet`/@PostConstruct 中抛异常，bean 创建中断，已分配但尚未就绪的对象不会调用 `@PreDestroy`/`DisposableBean`，可能泄漏连接/线程池。**正确写法**：初始化逻辑用 try/finally 兜底资源，或把易失败步骤推迟到 `ApplicationRunner`（所有单例就绪后、且异常可被容器统一处理）。

4. **BeanPostProcessor.postProcessAfterInitialization 返回 null 会把 bean 整体变 null** —— 自研 BPP 忘记 `return bean;`，于是该 bean 被替换成 null，所有注入点 `getBean` 拿到 null → NPE。**正确写法**：两个钩子都必须 `return bean;`（或返回包装后的代理），不要返回 null。

5. **构造器循环依赖启动即崩，三级缓存救不了** —— A、B 互相用构造器注入，实例化阶段对象还没 new 出来，无法暴露早期引用，直接 `BeanCurrentlyInCreationException`。**正确写法**：重构拆环，或在注入点加 `@Lazy` 延迟注入打破环。

6. **@Configuration 漏写变成 @Component，类内 @Bean 互调产出多例** —— 配置类只标 `@Component` 而非 `@Configuration`，`@Bean` 互调是普通方法调用，每次 `new`，本该单例的依赖出现多实例、状态不一致。**正确写法**：装配 bean 的配置类一律标 `@Configuration`，让 CGLIB 增强保证单例共享。

7. **prototype 作用域不会触发销毁回调** —— 容器对 prototype 只负责创建+初始化，不缓存也不注册销毁，`@PreDestroy`/`DisposableBean` 永不调用，资源需调用方自行释放，误以为「容器会帮我 close」会泄漏。**正确写法**：prototype 持有资源的，在调用方用 try-with-resources / 手动 close，别依赖容器销毁。

8. **单例 Bean 里存请求级状态**
   单例是全局共享的。把当前用户、`HttpServletRequest`、临时上下文存成成员字段，并发请求会互相覆盖，表现为「A 用户看到 B 用户的数据」这种最危险的一类 bug。
   ✅ 请求级数据走方法参数或 `RequestContextHolder`；确实需要 per-request 状态就用 `@Scope("request")`（或 `@RequestScope`）。

9. **在 `BeanPostProcessor` 里注入业务 Bean**
   BPP 会被极早创建，它依赖的业务 Bean 因此被**提前初始化**，绕过正常后处理链——AOP 代理可能还没织入，`@Transactional`、`@Async` 静默失效，排查起来极其反直觉。
   ✅ BPP 里只依赖基础设施 Bean；需要「所有 Bean 就绪后」的动作放到 `SmartInitializingSingleton` 或 `ApplicationListener<ContextRefreshedEvent>`。
