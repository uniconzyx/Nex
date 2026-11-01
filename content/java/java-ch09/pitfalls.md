# java-ch09 · 陷阱清单：Maven 与 Spring Boot 最容易错的十二件事

1. **把 `dependencyManagement` 当成引入依赖** —— 它**只是版本字典**，子依赖不写 `<version>` 时提供默认值；**真正引入**依赖的是 `<dependencies>`。写反了会出现「配了却没生效」。

2. **记错依赖调解规则** —— 是「**路径最短优先**，同长度时**先声明优先**」，不是「后声明覆盖先声明」。排查命令：`mvn dependency:tree -Dverbose`，看 `omitted for conflict with X`。

3. **`provided` 的库上线后 `ClassNotFoundException`** —— `provided` 只在编译与测试可见，**运行时不进产物**。典型误用：把 `lombok` 之外的东西设成 `provided`，或自认为「容器会提供」但实际运行环境（如独立 `java -jar`）不提供。

4. **把 `@ComponentScan` 漏掉的类当成框架 bug** —— 默认只扫**主类所在包及子包**。启动类放太深（如 `com.example.web`）会导致 `com.example.service` 扫不到，报 `NoSuchBeanDefinitionException`。规矩：**启动类放最外层包**。

5. **用字段注入，然后在单测里 `new` 不出来** —— 字段注入的对象脱离容器后字段全 null，单测只能反射或起 Spring 上下文。**改用构造器注入**，依赖声明为 `final`，单测可直接 `new`。

6. **写 `@Transactional` 却在同类内部自调用** —— `this.methodB()` **不经过 AOP 代理**，事务（以及任何切面）失效。修法：把方法挪到另一个 Bean，或注入自身代理（`AopContext.currentProxy()`，需 `exposeProxy=true`，不推荐）。

7. **受检异常导致事务不回滚** —— 默认只对 `RuntimeException` / `Error` 回滚。抛 `IOException` 时事务已提交，数据留下半个操作。修法：`@Transactional(rollbackFor = Exception.class)`。

8. **`filtering` 把不该替换的 `${}` 也替换了** —— 资源过滤是**全量文本替换**且**不幂等**。`logback.xml` 里的 `${LOG_HOME}`、前端模板里的 `${x}` 会被误改。修法：`<nonFilteredFileExtensions>` 排除，或把这类文件放到不做 filtering 的资源目录。

9. **忘记 `mvn clean` 导致的「本地能跑、CI 挂」** —— 资源/注解处理器的增量判断有时会失效，`target/` 里残留旧 class。CI 脚本统一用 `mvn clean install`。

10. **把 `SNAPSHOT` 依赖带到生产** —— SNAPSHOT 每次构建都重新解析，同一版本号内容可能不同，构建**不可重现**。发布前必须锁定 release 版本。

11. **单例 Bean 里放可变字段** —— `singleton` 是整个容器共享一个实例，可变实例字段在多请求并发下就是**数据竞争**。要状态用方法局部变量或 `ThreadLocal`（且必须在 `finally` 里 `remove()`，否则线程池复用会泄漏）。

12. **把集成测试命名成 `*Test`** —— `surefire` 会在 `mvn test` 阶段跑掉全部集成测试，构建从秒级变分钟级。约定：单元测试 `*Test`，集成测试 `*IT`（交给 `failsafe` 在 `verify` 阶段跑）。

13. **把 `proxyBeanMethods=false` 当成纯优化，却在配置类里做 Bean 间调用**
`@Configuration(proxyBeanMethods = false)` 是 Boot 2.2+ 的推荐写法（省掉 CGLIB 代理、启动更快），但代价是**配置类内部的方法调用不再被拦截**：`@Bean` 方法里直接 `otherBean()` 会真的 new 一个新对象，而不是取容器里的单例。判断标准很简单——配置类里是否有「一个 `@Bean` 方法调用另一个 `@Bean` 方法」。有就保持默认 `proxyBeanMethods = true`，或把依赖改成方法参数注入（推荐，两种模式下都正确）。

14. **以为 `mvn install` 装的是当前源码**
`install` 装进本地仓库的是 `target/` 里的**上一次打包产物**。IDE 编译输出（`out/`、`build/`）与 Maven 的 `target/classes` 是两套目录，改完代码只在 IDE 里运行过就 `install`，装进去的仍是旧 jar。多模块工程的表现是「改了 common、service 里还是旧行为」。本地验证一律 `mvn clean install`；只装单模块时用 `mvn install -pl common -am`，避免漏掉上游。

15. **用 `@SpringBootTest` 测纯工具类**
`@SpringBootTest` 会拉起**完整应用上下文**（含数据源、MVC、定时任务），一个上下文几秒到几十秒。纯函数/工具类测试直接 `new` 即可，根本不需要 Spring。确实需要容器但不需要 MVC 时，显式写 `webEnvironment = NONE` 比默认的 `MOCK` 更省。另外每个不同的配置组合会新建一个上下文，测试类之间配置越一致、上下文复用率越高——这是整包测试从 10 分钟降到 2 分钟的关键。
