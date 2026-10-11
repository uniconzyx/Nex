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
