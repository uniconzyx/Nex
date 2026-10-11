# 三、组件扫描与 Java 配置

## 一、组件扫描与 stereotype 注解

（中立陈述）`@Component` 及其语义化派生 `@Service` / `@Repository` / `@Controller` /
`@Configuration` 统称 **stereotype 注解**。`@ComponentScan` 在指定包下扫描这些注解标注的类，
把它们解析成 `BeanDefinition` 注册进容器。被扫描到的类默认 bean 名为「类名首字母小写」。

### 🧑‍💻 程序员视角
- 工程惯例：`@SpringBootApplication` 已自带 `@ComponentScan`（扫启动类所在包及其子包）；
  若业务类放在启动类**上层/平行**包，会扫不到——经典的「bean 找不到」事故。
- 踩坑：`@Repository` 还额外提供持久层异常转译（把 JDBC/ORM 异常包成 Spring 的
  `DataAccessException`），别只当普通 `@Component` 用；`@Controller` 与 `@RestController`
  决定返回值是否被视图解析/直接写 body。
- 性能：启动期扫描是 I/O + 字节码/注解读取，类很多时占启动时间；生产可用 `@ComponentScan` 收窄
  基础包，或编译期索引（spring-context-indexer）加速。

### 🎓 博士生视角
- 机制：`ClassPathScanningCandidateComponentProvider` 用 `ResourcePatternResolver` 把包名转成
  `classpath*:包/**/*.class`，再经 `TypeFilter`（含 `AnnotationTypeFilter`）筛出带 stereotype 的类，
  生成 `ScannedGenericBeanDefinition`。
- 抽象：stereotype 注解是**元注解 `@Component` 的派生**（用 `@Component` 作 meta-annotation），
  扫描器只需认 `@Component` 一种即可「顺着元注解」识别全部派生，这是注解的复用设计。
- 设计动机：约定优于配置——按包路径 + 注解自动注册，省去逐 bean 的 XML/Java 声明。

### 📚 考研者视角
- 笔面标准问法：「@Component、@Service、@Repository、@Controller 有什么区别？」标准口径：**本质都是
  @Component 的派生；语义不同：@Repository 多一层持久层异常转译，@Controller/@RestController 用于
  Web 层决定请求映射与响应方式；@Service 仅作业务层语义标识。**
- 易错口径：答「它们功能完全一样」——`@Repository` 的异常转译是真实差异，不能忽略。
- 常见追问：「为什么扫描不到我的 bean？」答：包不在扫描根包下 / 类不是具体类（接口或抽象类）/ 注解
  写错位置。

## 二、@Bean 与 @Configuration（Java 配置 / 工厂方法）

（中立陈述）`@Bean` 标注在**方法**上，方法的返回值被注册为容器中的一个 bean（即「工厂方法」）。
`@Bean` 方法通常写在 `@Configuration` 类里。关键细节：`@Configuration` 类会被 CGLIB **增强**，
使类内 `@Bean` 方法互相调用时返回的是**容器里的同一个单例**；而 `@Component` 里的 `@Bean` 方法
只是普通方法调用，可能每次新建。

### 🧑‍💻 程序员视角
- 工程惯例：装配**第三方库对象**（如 `RestTemplate`、`DataSource`）用 `@Bean`——你无法给别人的类
  加 `@Component`；业务类用 `@Component` 扫描更省事。
- 踩坑：`@Bean` 方法内调用另一个 `@Bean` 方法，若配置类没标 `@Configuration`（只是 `@Component`），
  会得到多个实例而非共享单例——这是典型的「单例变多例」隐蔽 bug。
- 性能：`@Configuration` 的 CGLIB 增强在启动期发生一次，运行期通过增强后的方法走容器缓存，无额外成本。

### 🎓 博士生视角
- 机制：`ConfigurationClassPostProcessor` 把 `@Configuration` 类增强为 CGLIB 子类，覆写 `@Bean`
  方法：调用前先 `beanFactory.getBean(beanName)`，命中则直接返回，未命中才真正执行方法体。
  这就是「full @Configuration」保证单例共享的原理。
- 对比：`lite @Configuration`（即 `@Component` + `@Bean`）不增强，方法体每次照常执行，单例靠
  `getBean` 缓存兜底，但「方法内互调」绕过缓存就会新建。
- 设计动机：`@Bean` 把「对象如何构造」的表达权交回 Java 代码（强类型、可写任意逻辑），比 XML 更
  易重构、类型安全。

### 📚 考研者视角
- 笔面标准问法：「@Component 里的 @Bean 和 @Configuration 里的 @Bean 有区别吗？」标准口径：
  **@Configuration 类被 CGLIB 增强，类内 @Bean 互调返回同一单例；@Component 里的 @Bean 是普通
  方法调用，互调可能新建多个实例。**
- 易错口径：混淆「@ComponentScan 注册的 bean」与「@Bean 注册的 bean」——前者作用于类（加注解），
  后者作用于方法（返回对象），可以混用。
- 常见追问：「@Configuration 为什么要 CGLIB？」答：为了在方法级拦截、保证 @Bean 互调返回同一单例。
