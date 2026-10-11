# 03 · Spring Boot 启动流程与自动配置

## 一、@SpringBootApplication 是三个注解的合成

```java
@SpringBootApplication
// ≡ @SpringBootConfiguration      -> 表明这是一个配置类（含 @Configuration）
// + @EnableAutoConfiguration      -> 开启自动配置（SPI 加载 xxxAutoConfiguration）
// + @ComponentScan                -> 扫描当前包及子包的 @Component/@Service/@Repository/@Controller
public class App { public static void main(String[] a) { SpringApplication.run(App.class, a); } }
```

**关键推论**：`@ComponentScan` 默认扫描**主类所在包及其子包**。因此
「把启动类放到最外层包」是一条硬纪律——放到 `com.example.web` 里，
`com.example.service` 就永远扫不到，表现为「Bean 明明写了却 `NoSuchBeanDefinitionException`」。

## 二、SpringApplication.run 的启动阶段

```java
public static ConfigurableApplicationContext run(Class<?> primarySource, String... args) {
    return new SpringApplication(primarySource).run(args);
    // 1. 创建 SpringApplication：推断应用类型(SERVLET/REACTIVE/NONE)、
    //    加载 ApplicationContextInitializer 与 ApplicationListener（同样走 SPI）
    // 2. run():
    //    ① 启动计时器与监听器，发布 ApplicationStartingEvent
    //    ② 准备 Environment：加载 application.yml/properties、系统属性、命令行参数
    //    ③ 打印 Banner
    //    ④ 创建 ApplicationContext（Servlet 应用即 AnnotationConfigServletWebServerApplicationContext）
    //    ⑤ prepareContext：注册 primarySource，执行 Initializer（此时才轮到自动配置）
    //    ⑥ refreshContext：核心——invokeBeanFactoryPostProcessors 解析 @Import/@Conditional、
    //       注册全部 BeanDefinition，再实例化单例 Bean
    //    ⑦ afterRefresh：发布 ApplicationStartedEvent / ApplicationReadyEvent
}
```

事件顺序是排查启动问题的路标：能看到 `ApplicationStartedEvent` 说明上下文已刷新完成；
卡在它之前，问题就在**装配**（条件、Bean 定义、循环依赖）；卡在之后才是**业务初始化**
（如连数据库、加载缓存）。

## 三、自动配置的原理：SPI + 条件装配

`@EnableAutoConfiguration` 通过 `@Import(AutoConfigurationImportSelector.class)` 工作，
后者读取 **`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`**
（Spring Boot 2.7 之前是 `spring.factories` 的 `EnableAutoConfiguration` 键），
拿到**候选自动配置类全名列表**，再逐个用条件注解筛选：

| 条件注解 | 判定依据 |
|---|---|
| `@ConditionalOnClass` | classpath 中**有**某个类才生效 |
| `@ConditionalOnMissingBean` | 容器中**没有**该 Bean 才生效（**允许用户覆盖**的关键） |
| `@ConditionalOnProperty` | 配置项满足特定值 |
| `@ConditionalOnWebApplication` | 当前是 Web 应用 |

这套设计的意义：**用户自定义的 Bean 优先级高于自动配置**。
你写一个自己的 `DataSource`，`DataSourceAutoConfiguration` 的
`@ConditionalOnMissingBean(DataSource.class)` 就不成立，自动配置自动退让——
这就是「约定优于配置，且配置可覆盖」的实现机制。

## 四、起步依赖与内嵌容器

`spring-boot-starter-web` 本身几乎不含代码，它只是一个**依赖聚合**：
`spring-webmvc` + `spring-web` + `jackson` + `tomcat`（内嵌）+ 校验与日志。
因此「换容器」只需把 `spring-boot-starter-web` 里的 tomcat 排除、换引
`spring-boot-starter-jetty`——**因为容器是被 starter 引进来的普通依赖**，而不是框架的一部分。

内嵌容器的收益：应用成为**一个可执行 jar**，`java -jar app.jar` 即启动，无需外置 Tomcat 部署。

## 五、配置加载与优先级

同名前缀下，**优先级从高到低**（高者覆盖低者）：

1. 命令行参数（`--server.port=9090`）
2. `SPRING_APPLICATION_JSON`（环境变量形式的 JSON）
3. 操作系统环境变量 / Java 系统属性（`-Dserver.port=9090`）
4. `application-{profile}.yml`（激活的 profile 专属）
5. `application.yml`
6. `@PropertySource` 与默认属性

注意：**profile 专属文件覆盖通用文件**（不是补充），所以 `application-prod.yml` 里
没写的键会**回落到** `application.yml` 的值——这是「覆盖 + 回落」的组合语义。

## 六、可运行代码

```java
// 用 Map 链模拟配置源的覆盖顺序；用条件谓词模拟 @Conditional 装配
// 详见 examples/ex07-boot-startup-phases.json、examples/ex08-config-priority.json
```

## 三视角解析

### 🧑‍💻 程序员视角
### 🎓 博士生视角
### 📚 考研者视角

### 🧑‍💻 程序员视角
启动问题的排查顺序是固定的：先看**有没有打出 `Started App in Xs`**（有 → 应用已就绪，
问题在业务初始化；没有 → 卡在装配）。装配阶段的两大高频故障：
① **`NoSuchBeanDefinitionException`** —— 九成是**包不在扫描范围**（启动类位置不对）或
类是 `new` 出来的（没交给容器）；② **循环依赖**（两个 Bean 构造器互相注入），
Spring Boot 2.6+ **默认禁止**循环依赖，需 `spring.main.allow-circular-references=true` 才能开，
但**正确做法是重构**（抽出第三个组件打破环）。生产上建议显式写
`spring.main.banner-mode=off`、`logging.level.root=INFO`，并给 `application.yml` 加
`spring.config.import` 来引入配置中心——**配置项越少写死在 jar 里越好**（12-Factor 原则）。

### 🎓 博士生视角
`@EnableAutoConfiguration` 是一套**基于 classpath 谓词的元编程装配系统**，
形式化看是「在 Bean 定义图上按条件谓词求不动点」：`refreshContext` 过程中
`ConfigurationClassPostProcessor` 递归解析 `@Import`（含 `ImportSelector` /
`DeferredImportSelector`）与 `@Conditional`，直到没有新的配置类被引入，
随后 `BeanFactoryPostProcessor` 注册全部 `BeanDefinition`，再交由 `DefaultListableBeanFactory`
按**依赖图的拓扑序**实例化单例。这里的关键不变量是
**「用户定义优先」**，由 `@ConditionalOnMissingBean` 保证：它把用户 Bean 视作
优先级更高的断言，等价于「自动配置是**默认值**，不是**强制值**」。
`DeferredImportSelector` 的延迟性是必要的——自动配置必须**最后**处理，
否则它无法观察到用户已经注册的 Bean。这也解释了 `spring.factories` → `AutoConfiguration.imports`
的迁移：从「按接口聚合的元数据」改为「专用清单文件」，加载更快、语义更窄。

### 📚 考研者视角
背下这组标准问答：
- **`@SpringBootApplication` 由哪三个注解组成？** `@SpringBootConfiguration` + `@EnableAutoConfiguration` + `@ComponentScan`。
- **自动配置怎么生效？** `@EnableAutoConfiguration` 引入 `AutoConfigurationImportSelector`，
  它从 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`（旧版 `spring.factories`）
  读取候选配置类，再用 `@ConditionalOnXxx` 筛选后注册。**答「靠 `spring.factories`」在 2.7+ 已不完整**，
  要补一句新路径。
- **为什么用户自定义 Bean 能覆盖自动配置？** 因为自动配置类上普遍有 `@ConditionalOnMissingBean`。
- **`@ComponentScan` 默认范围？** 主类所在包及**子包**——所以启动类要放最外层。
- **`@RestController` = `@Controller` + `@ResponseBody`**。
- **依赖注入三种方式与推荐**：字段注入（简洁但不推荐，破坏不可变性、难单测）、
  setter 注入（可选依赖）、**构造器注入（官方推荐，保证依赖不为 null 且可 final）**。
- **配置优先级最高的是命令行参数**，最低是默认属性；**profile 文件覆盖通用文件**。
- **`@Configuration` 与 `@Component` 差异**：前者带 `proxyBeanMethods`（默认 true），
  用 CGLIB 代理保证内部 `@Bean` 方法调用返回**同一个单例**。
