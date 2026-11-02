# 易错点（spring-ch01）

1. **字段注入破坏可测试性** —— 把 `@Autowired` 写在私有字段上，单测无法像构造器那样直接传入 mock，必须启动容器或反射注入。**正确写法**：强制依赖改用构造器注入，`private final Repo repo;` 并在构造器上 `@Autowired`（单构造器时可省略）。

2. **扫不到 bean（包不在扫描根包下）** —— 业务类放在启动类上层/平行包，默认 `@ComponentScan` 扫不到，运行期 NPE。**正确写法**：把启动类放在最外层根包，或用 `@ComponentScan("com.xxx")` 显式指定基础包。

3. **构造器循环依赖启动即崩** —— A、B 互相用构造器注入，三级缓存救不了，抛 `BeanCurrentlyInCreationException`。**正确写法**：重构拆解依赖（抽接口/搬逻辑），或在一方加 `@Lazy` 延迟注入打破环。

4. **@Component 里的 @Bean 方法互调产生多例** —— 配置类只标了 `@Component` 而非 `@Configuration`，类内 `@Bean` 互调是普通方法调用，每次新建，单例变多例。**正确写法**：装配 bean 的配置类标 `@Configuration`，让 CGLIB 增强保证单例共享。

5. **同类型多 bean 未加 @Qualifier 抛歧义** —— 一个接口两个实现都进容器，注入时 `NoUniqueBeanDefinitionException`。**正确写法**：用 `@Qualifier("name")` 精确点名，或在默认实现上标 `@Primary`。

6. **prototype + 互相注入必然失败** —— prototype 每次新建且不缓存早期引用，循环依赖直接 `BeanCurrentlyInCreationException`，没有任何缓存能救。**正确写法**：改为单例协作，或抽一个被双方依赖的第三方 bean。

7. **误以为 ApplicationContext 比 BeanFactory「运行更快」** —— 二者单例获取都是 Map 查找，差异只在启动期是否预实例化；ApplicationContext 启动更慢但 fail-fast、运行期无差别。**正确写法**：按「是否需要国际化/事件/AOP/更早暴露装配错误」选 ApplicationContext，不要以性能为由选 BeanFactory。

8. **字段注入 `@Autowired` 让类无法脱离容器测试**
   字段注入的对象只能靠反射塞进去，单元测试要么起半个 Spring 上下文（慢），要么用 `ReflectionTestUtils`（脆）。字段还不能 `final`，等于放弃了「依赖不可变」。
   ✅ 构造器注入（只有一个构造器时可省注解）；字段声明 `final`，依赖缺失在编译/启动期就暴露。

9. **同类型多 Bean 时靠字段名「猜」实现**
   `@Autowired private UserService userService;` 在存在两个 `UserService` 实现时，Spring 会退化成**按字段名匹配 Bean 名**。改个字段名就换了实现，不报错、行为静默改变。
   ✅ 显式 `@Qualifier("beanName")` 或 `@Primary`；需要遍历所有实现时注入 `Map<String, UserService>`。

10. **字段注入导致必填依赖启动不校验** —— `@Autowired` 字段在运行时才填，缺依赖启动不报错、运行 NPE。✅ 必填不可变依赖用构造器注入，启动即校验。
11. **自己 new Bean 导致 @Autowired 全为 null** —— `new UserService()` 不被容器管理，里面的依赖不注入。✅ 让容器创建（注入或 getBean）。
12. **prototype 被 singleton 持有没真多例** —— prototype 只在直接 getBean / ObjectProvider.getObject 时每次新建。✅ 需要每次新实例用 ObjectProvider。
13. **@Value 取不到配置** —— key 没配或类型不符。✅ 用 `:默认值` 兜底，复杂配置用 `@ConfigurationProperties` 绑定对象。
14. **singleton 里存可变状态致线程不安全** —— 并发请求互相串号。✅ 请求数据走方法参数或 RequestContextHolder，或 @Scope("request")。
15. **@Lazy 掩盖真正的循环依赖** —— 启动报错被压到首次请求才炸，更难定位。✅ 优先重构依赖方向而非一路 @Lazy。
