# 易错点（spring-ch01）

1. **字段注入破坏可测试性** —— 把 `@Autowired` 写在私有字段上，单测无法像构造器那样直接传入 mock，必须启动容器或反射注入。**正确写法**：强制依赖改用构造器注入，`private final Repo repo;` 并在构造器上 `@Autowired`（单构造器时可省略）。

2. **扫不到 bean（包不在扫描根包下）** —— 业务类放在启动类上层/平行包，默认 `@ComponentScan` 扫不到，运行期 NPE。**正确写法**：把启动类放在最外层根包，或用 `@ComponentScan("com.xxx")` 显式指定基础包。

3. **构造器循环依赖启动即崩** —— A、B 互相用构造器注入，三级缓存救不了，抛 `BeanCurrentlyInCreationException`。**正确写法**：重构拆解依赖（抽接口/搬逻辑），或在一方加 `@Lazy` 延迟注入打破环。

4. **@Component 里的 @Bean 方法互调产生多例** —— 配置类只标了 `@Component` 而非 `@Configuration`，类内 `@Bean` 互调是普通方法调用，每次新建，单例变多例。**正确写法**：装配 bean 的配置类标 `@Configuration`，让 CGLIB 增强保证单例共享。

5. **同类型多 bean 未加 @Qualifier 抛歧义** —— 一个接口两个实现都进容器，注入时 `NoUniqueBeanDefinitionException`。**正确写法**：用 `@Qualifier("name")` 精确点名，或在默认实现上标 `@Primary`。

6. **prototype + 互相注入必然失败** —— prototype 每次新建且不缓存早期引用，循环依赖直接 `BeanCurrentlyInCreationException`，没有任何缓存能救。**正确写法**：改为单例协作，或抽一个被双方依赖的第三方 bean。

7. **误以为 ApplicationContext 比 BeanFactory「运行更快」** —— 二者单例获取都是 Map 查找，差异只在启动期是否预实例化；ApplicationContext 启动更慢但 fail-fast、运行期无差别。**正确写法**：按「是否需要国际化/事件/AOP/更早暴露装配错误」选 ApplicationContext，不要以性能为由选 BeanFactory。
