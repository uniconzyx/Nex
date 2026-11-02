# spring-ch04 易错点

1. **`@SpringBootApplication` 的扫描范围只覆盖主类所在包及其子包** —— 主类放在
   `com.example.demo`，而业务代码在 `com.example.service`，`@ComponentScan` 扫不到，
   表现为「Bean 找不到」。正确做法：把主类放在所有业务包的最外层
   （如 `com.example`），或显式 `@ComponentScan(basePackages = "com.example")`。
   **这不是自动配置问题，是组件扫描问题**，两者要分清。

2. **`@ConditionalOnMissingBean` 的判定依赖「注册顺序」，因此自动配置类必须排在用户配置之后** ——
   若自动配置类先被执行，它看不到用户定义的 Bean，就会把自己的默认 Bean 也注册进去，
   导致「我明明写了 Bean 却生效了两个」。正确认知：`@ConditionalOnMissingBean` 只在
   **自动配置类**里才安全；配套的是 `@AutoConfigureBefore/After` 与自动配置的
   「最后加载」约定。在用户自己的 `@Configuration` 里写它，行为不可靠。

3. **`spring.factories` 与 `AutoConfiguration.imports` 混用会重复加载** ——
   Spring Boot 2.7 起，自动配置类改用
   `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
   （每行一个全限定类名，**无 key**）；而 `spring.factories` 里若仍保留
   `EnableAutoConfiguration=` 键，在 2.7 的过渡期会导致同一配置类被加载两次。
   正确做法：3.x 项目只保留 `AutoConfiguration.imports`，`spring.factories` 只用于
   其他扩展点（如 `ApplicationContextInitializer`、`EnvironmentPostProcessor`）。

4. **`@ConfigurationProperties` 绑定失败不报错，只是静默为 null** ——
   与 `@Value` 不同，`@ConfigurationProperties` 的松散绑定对「拼错的 key」是**静默忽略**的，
   排查时极易误判为「配置没读到」。正确做法：加 `@Validated` +
   `@NotNull`/`@NotBlank` 校验，或用 `spring-boot-configuration-processor` 生成元数据让 IDE 提示；
   绑定时长用 `@DurationUnit` 明确单位，避免默认毫秒的误判。

5. **配置文件优先级记混** —— 实际生效顺序（从高到低）大致为：
   命令行参数 → `SPRING_APPLICATION_JSON` → ServletConfig/Context 参数 →
   JNDI → Java System properties → 操作系统环境变量 → `application-{profile}.properties`
   （jar 包外） → `application-{profile}.properties`（jar 包内） → `application.properties`（外） →
   `application.properties`（内）。常见错误是以为「带 profile 的一定覆盖不带 profile 的」——
   **只有在同一层级目录下**才成立，jar 包外的无 profile 配置会覆盖 jar 包内的带 profile 配置。

6. **把 starter 写成一个大模块，且不加 `optional`/`provided`** ——
   自定义 starter 应拆成 `autoconfigure` 模块（含自动配置源码，依赖 `spring-boot-autoconfigure`
   且标 `optional`）与 `starter` 模块（只做 `autoconfigure` + 具体实现的聚合依赖）。
   写成单模块会把自动配置类暴露给使用者并被组件扫描到，破坏「自动配置由 SPI 驱动」的约定。

7. **`@ConditionalOnProperty` 的 `havingValue` 是精确字符串比较**
   不带 `havingValue` 时只要属性存在且不等于 `false` 就生效；一旦写了 `havingValue="true"`，值必须**恰好**是 `"true"`——配成 `1`、`TRUE`、`yes` 都不匹配，条件静默不成立，Bean 就是不注册，日志里也未必有痕迹。
   ✅ 布尔开关统一写 `havingValue="true"` + `matchIfMissing=false`，并在文档里固定写法；启动后用 `/actuator/conditions` 确认条件是否命中。

8. **BOM 与 parent 混用，版本被自己写死的号覆盖**
   `spring-boot-starter-parent` 与 `spring-boot-dependencies` 同时引入时，`<dependencyManagement>` 的 import 顺序决定最终版本（后者覆盖前者）；而在 `<dependencies>` 里手写版本号会直接让 BOM 失效，于是同一项目里 Spring 各组件的版本悄悄分叉。
   ✅ 二选一：用 parent，或只 import `dependencies` 这个 BOM；被 BOM 管理的依赖一律不写 `<version>`。

9. **自己写的 starter 放错自动配置清单路径** —— 错在：SpringBoot 3.x 项目里还在用 `META-INF/spring.factories`，依赖加上后什么也没发生。

   *为什么*：3.x 改成了 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`，旧路径被静默忽略，不报任何错。这是最难查的一类问题——依赖在、类在、就是不生效。

   *怎么改*：按版本放对路径；自动配置类用 `@AutoConfiguration` 而非 `@Configuration`；排除前先用 `--debug` 看条件报告确认它到底有没有被加载。

10. **@ConditionalOnProperty 用 1/yes 当布尔值** —— 错在：本地 `application.yml` 写 `enabled: true` 一切正常，生产用环境变量注入 `ENABLED=1`，功能静默失效。

   *为什么*：`havingValue` 是**精确字符串比较**，`"1"`、`"yes"`、`"TRUE"` 都不等于 `"true"`。而且属性不存在时默认不匹配（`matchIfMissing = false`）。

   *怎么改*：布尔开关一律用 `true`/`false` 字面量；需要「没配就开启」时显式写 `matchIfMissing = true`；文档里写清楚接受哪些值。

11. **@ConfigurationProperties 忘了启用或忘了 setter**
   只写注解不 `@EnableConfigurationProperties`（也没 `@Component`），Bean 根本不存在；或者字段没有 setter，绑定时静默跳过，全是 null。

   *为什么*：`@ConfigurationProperties` 本身不是组件扫描的目标，需要显式注册。绑定是「有 setter 就设，没有就跳过」，不会报错。

   *怎么改*：配置类上加 `@EnableConfigurationProperties(XxxProperties.class)`；Properties 类补齐 getter/setter（或用构造器绑定 + `@ConstructorBinding`）；配合 `@Validated` 让错误在启动时暴露。

12. **用 @Value 管一组配置，改配置名要全局搜索**
   把 host/port/user/password/timeout 五项都写成散落的 `@Value`，改前缀时漏改一处就静默失效。

   *为什么*：`@Value` 是精确匹配、不支持宽松绑定、不支持校验、不集中在类型里，规模一大就不可维护。

   *怎么改*：超过三个相关配置项就用 `@ConfigurationProperties` 集中管理，配合 `@Validated` 校验，让配置成为一等的类型。

13. **@ComponentScan 范围盖不住其他模块**
   主类放在 `com.example.app`，某个 `@Service` 在 `com.example.other`，启动报 `NoSuchBeanDefinitionException`。

   *为什么*：`@SpringBootApplication` 内含 `@ComponentScan`，默认只扫主类所在包及其子包。项目结构调整（主类挪进子模块）时最容易踩。

   *怎么改*：主类放回顶层包；或显式 `@ComponentScan(basePackages = "com.example")`；多模块项目统一约定包名层级。

14. **手工排除自动配置，却不知道后果**
   `@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)`，之后某个功能莫名不可用，也找不到原因。

   *为什么*：排除是「一刀切」，把该配置类下的所有 `@Bean` 全部拿掉，包括你可能还在依赖的那些。版本升级后类名变化，排除还可能失效或编译失败。

   *怎么改*：优先让条件注解自己判断（`@ConditionalOnProperty` 关掉开关），而不是手工排除；确实必须排除时，在代码里写注释说明原因和影响范围。

15. **`@ConditionalOnBean` 看到的是「已注册」而非「全部」**
   两个自动配置类互相 `@ConditionalOnBean` 对方的产物，结果两边都不生效，且没有任何报错。

   *为什么*：`@ConditionalOnBean` 只检查**当前已注册**的 Bean，取决于自动配置类的加载顺序。互相依赖时形成死锁，双方的条件都不满足。

   *怎么改*：用 `@AutoConfigureAfter` / `@AutoConfigureBefore` 显式声明顺序；避免双向条件依赖；用 `--debug` 的条件报告确认每个条件的评估结果。
