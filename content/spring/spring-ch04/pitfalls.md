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
