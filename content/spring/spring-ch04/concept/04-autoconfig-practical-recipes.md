# SpringBoot 自动配置实战手记：凯喵的十二次「Bean 没装上，启动就崩」

> 这一篇来自凯喵给团队搭一个内部 starter 的经历。SpringBoot 的「约定优于配置」体验很好，但一旦出问题，排查路径很长：Bean 到底有没有被注册、条件为什么没生效、配置为什么没绑定上。十二个现场记录下来的结论是：**自动配置不是魔法，它是一套有明确加载顺序和条件判断的机制**。这篇按「启动流程 → 自动配置 → 配置绑定 → starter 封装」的顺序展开。

## 开场：一个空项目为什么能跑起来

`spring-boot-starter-web` 加一个 `main` 方法就能起一个带 Tomcat 的 Web 应用。这背后是三件事的叠加：

**起步依赖**替你选好了依赖版本，你不用管 Spring MVC、Jackson、Tomcat 各自什么版本兼容；**自动配置**根据 classpath 上有什么类，自动注册对应的 `@Bean`；**条件装配**决定这些 `@Bean` 到底装不装——没有 `DispatcherServlet` 就不装 MVC 相关的东西。

理解这三层，后面的十二个现场就有了统一的解释框架。凯喵的经验是：**遇到「Bean 找不到」，先问三件事——类在不在 classpath、条件是否满足、有没有被排除**。

### 现场一：@SpringBootApplication 是三个注解的组合

`@SpringBootApplication` 等价于 `@SpringBootConfiguration` + `@EnableAutoConfiguration` + `@ComponentScan`。

```java
@SpringBootApplication
public class App {
    public static void main(String[] args) {
        SpringApplication.run(App.class, args);
    }
}
```

`@ComponentScan` 默认扫描主类所在包及其子包。这解释了一个高频问题：**主类放在 `com.example.app`，而某个 `@Service` 在 `com.example.other` 包里，就扫不到**。

凯喵见过最典型的翻车：项目结构调整时把主类挪到了子模块里，其他模块的 Bean 全部扫不到，启动报 `NoSuchBeanDefinitionException`。修法是用 `@ComponentScan(basePackages = "com.example")` 显式指定，或者把主类放回顶层包。

### 现场二：自动配置类的加载靠 spring.factories 或 imports 文件

SpringBoot 2.x 用 `META-INF/spring.factories` 声明自动配置类；3.x 改成 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`。

```properties
# SpringBoot 3.x：META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
com.example.mystarter.MyAutoConfiguration
```

```properties
# SpringBoot 2.x：META-INF/spring.factories
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
com.example.mystarter.MyAutoConfiguration
```

这个文件是自动配置的「入口清单」。如果自己写的 starter 不生效，第一件事就是检查这个文件路径和内容对不对——3.x 用 2.x 的路径，是完全静默的失败，不报任何错。

### 现场三：@Conditional 家族决定 Bean 装不装

条件注解是自动配置的核心。常用的五种：

`@ConditionalOnClass`：classpath 上有指定类时才生效。`@ConditionalOnMissingBean`：容器里没有该类型的 Bean 时才生效。`@ConditionalOnProperty`：配置项满足条件时才生效。`@ConditionalOnBean`：容器里有指定 Bean 时才生效。`@ConditionalOnWebApplication`：是 Web 应用时才生效。

```java
@AutoConfiguration
@ConditionalOnClass(DataSource.class)
public class MyDataSourceAutoConfig {

    @Bean
    @ConditionalOnMissingBean
    public MyDataSource myDataSource(DataSourceProperties props) {
        return new MyDataSource(props.getUrl());
    }
}
```

`@ConditionalOnMissingBean` 是「允许用户覆盖」的标准手法：框架提供一个默认实现，用户自己定义了同类型 Bean 就用用户的。这个模式在几乎所有官方 starter 里都能看到。

### 现场四：条件注解的评估顺序有讲究

`@ConditionalOnClass` 必须能安全地评估——即使那个类不存在，也不能崩。所以 Spring 用 ASM 读字节码而不是加载类。这意味着**你不能在 `@ConditionalOnClass` 里引用那个类的字面量**，只能写字符串或 `name`。

```java
// 正确：用 name 字符串，类不存在也不会崩
@ConditionalOnClass(name = "com.example.OptionalLib")

// 错误：直接引用，类不存在时注解解析就炸
// @ConditionalOnClass(com.example.OptionalLib.class)
```

另一个顺序问题：`@ConditionalOnBean` 只能看到「已经注册的 Bean」，所以它依赖自动配置类的加载顺序。如果两个自动配置类互相 `@ConditionalOnBean`，可能出现都不生效的情况。修法是用 `@AutoConfigureAfter` / `@AutoConfigureBefore` 显式声明顺序。

### 现场五：@ConditionalOnProperty 的 havingValue 是字符串精确比较

这个坑非常隐蔽。`havingValue = "true"` 只能匹配字面量 `"true"`，配置里写 `TRUE`、`1`、`yes` 都不匹配。

```java
@ConditionalOnProperty(name = "feature.cache.enabled", havingValue = "true")
```

而且如果配置项**根本不存在**，默认是不匹配（`matchIfMissing = false`）。要让它「没配就开启」，必须显式写 `matchIfMissing = true`。

凯喵踩过这个坑：本地测试时 `application.yml` 里写了 `enabled: true`，一切正常；生产环境用环境变量注入 `ENABLED=1`，功能静默失效。排查了半天才发现是字符串比较的问题。

规约：**布尔开关一律用 `true` / `false` 字面量，别用 `1` / `0` / `yes`**，并且在文档里写清楚。

### 现场六：@ConfigurationProperties 需要显式启用

写了 `@ConfigurationProperties` 的类，不会自动成为 Bean。要么在类上加 `@Component`，要么在配置类上加 `@EnableConfigurationProperties(XxxProperties.class)`。

```java
@ConfigurationProperties(prefix = "app.mail")
public class MailProperties {
    private String host;
    private int port = 25;
    private Duration timeout = Duration.ofSeconds(5);
    // getter / setter
}

@AutoConfiguration
@EnableConfigurationProperties(MailProperties.class)   // 必须显式启用
public class MailAutoConfig { }
```

凯喵的偏好是用 `@EnableConfigurationProperties`，因为这样 Properties 类可以保持「纯数据」，不带 `@Component`，测试时更容易直接 new 出来用。

注意：**必须有 getter/setter（或用构造器绑定）**。忘了 setter 会导致所有字段都是 null，而且不报错——绑定是「有就设，没有就跳过」。

### 现场七：宽松绑定让配置名有多种写法

`app.mail.smtp-host`、`app.mail.smtpHost`、`APP_MAIL_SMTPHOST` 在绑定时是等价的。这叫宽松绑定（relaxed binding），目的是让 YAML、Properties、环境变量三种来源都能用。

```yaml
app:
  mail:
    smtp-host: smtp.example.com
    max-retry-count: 3
```

```java
@ConfigurationProperties(prefix = "app.mail")
public class MailProperties {
    private String smtpHost;        // 对应 smtp-host
    private int maxRetryCount;      // 对应 max-retry-count
}
```

规则是：配置名里的短横线、下划线、大小写差异在绑定时都被归一化。但**环境变量必须以大写加下划线**，因为 shell 不允许小写点号。所以 `app.mail.smtp-host` 对应 `APP_MAIL_SMTPHOST`。

凯喵提醒：宽松绑定只对 `@ConfigurationProperties` 生效，`@Value("${app.mail.smtp-host}")` 是精确匹配，不宽松。这是两者最大的差别之一。

### 现场八：@Value 与 @ConfigurationProperties 的取舍

`@Value` 适合单个配置项，支持 SpEL 表达式；`@ConfigurationProperties` 适合一组相关配置，支持类型安全、校验、宽松绑定、以及在 IDE 里有元数据提示。

```java
// 单值：@Value 够用
@Value("${app.name}")
private String appName;

// 一组：用 @ConfigurationProperties
@ConfigurationProperties(prefix = "app.mail")
public class MailProperties { /* host, port, username, password... */ }
```

凯喵的规矩：**超过三个相关配置项就用 `@ConfigurationProperties`**。理由很实际——`@Value` 散落在各处，改配置名时要全局搜索；`@ConfigurationProperties` 集中在一个类里，一目了然，还能加 `@Validated` 做校验。

### 现场九：@Validated 让配置在启动时就校验

配置错了最好启动就失败，而不是运行时才发现。在 `@ConfigurationProperties` 上加 `@Validated`，字段上加 JSR-303 注解，启动时会校验。

```java
@ConfigurationProperties(prefix = "app.mail")
@Validated
public class MailProperties {
    @NotBlank
    private String host;

    @Min(1) @Max(65535)
    private int port = 25;

    @DurationMin(seconds = 1)
    private Duration timeout = Duration.ofSeconds(5);
}
```

这条的价值在于「快速失败」。凯喵见过太多「配置漏了，跑到某个分支才空指针」的事故。启动时校验能让问题在生产部署的第一秒就暴露。

注意需要引入 `spring-boot-starter-validation` 依赖，否则注解会被静默忽略。

### 现场十：自动配置的排除方式有三种

不想要某个自动配置，可以排除：

```java
// 方式 1：注解排除
@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)

// 方式 2：配置排除
// spring.autoconfigure.exclude=org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration

// 方式 3：条件不满足自然不生效（最推荐）
```

凯喵的建议是优先用方式 3：让条件注解自己判断，而不是手工排除。手工排除的问题是「排除了但不知道后果」，而且版本升级后类名可能变。

只有一种情况必须手工排除：引入了某个依赖（比如为了用其中的工具类），但不想让它触发自动配置。这时候必须在文档里写清楚为什么排除。

### 现场十一：自己写 starter 的两个模块结构

官方推荐拆成两个模块：`xxx-spring-boot-autoconfigure` 放自动配置逻辑，`xxx-spring-boot-starter` 只放依赖声明。

```text
my-spring-boot-autoconfigure/
  src/main/java/.../MyAutoConfiguration.java
  src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports

my-spring-boot-starter/
  pom.xml  (依赖 autoconfigure 模块 + 第三方库)
```

拆分的意义是：用户可以选择只用 autoconfigure（自己控制依赖版本），也可以用 starter（省事）。这是 Spring 官方 starter 的通用做法。

凯喵见过把两者合成一个模块的 starter，结果用户想排除某个传递依赖时无从下手。多一个模块，换来的灵活性很值。

### 现场十二：自动配置的调试手段

最后一条最实用。当你不确定某个 Bean 为什么装上了或者为什么没装上，有三个工具：

**启动加 `--debug`**，会打印「条件评估报告」，列出所有自动配置类以及每个条件的结果（matched / did not match 及原因）。

**`ConditionEvaluationReport`** 可以从 `ApplicationContext` 里拿到，效果一样但可以在代码里用。

**Actuator 的 `/actuator/conditions`** 端点，运行期随时查。

```text
Positive matches:
-----------------
   DataSourceAutoConfiguration matched:
      - @ConditionalOnClass found required classes 'javax.sql.DataSource'

Negative matches:
-----------------
   MongoAutoConfiguration:
      Did not match:
         - @ConditionalOnClass did not find required class 'com.mongodb.MongoClient'
```

凯喵的习惯是：**每次遇到「Bean 找不到」，第一件事就是开 debug 看报告**。它能直接告诉你哪个条件没满足，比猜快一百倍。这个技能在排查第三方 starter 问题时尤其有用。

## 收尾：自动配置是「有条件生效的默认值」

凯喵最后总结：SpringBoot 自动配置的本质是**给出一套合理的默认值，并允许你在任何一点覆盖它**。三个机制共同实现这件事：

**starter 给依赖**——让 classpath 上有正确的类；**自动配置给 `@Bean`**——`@ConditionalOnClass` 判断该不该给；**`@ConditionalOnMissingBean` 让用户覆盖**——你定义了同类型 Bean，框架就退让。

所以排查顺序永远是：**类在不在 → 条件满不满足 → 有没有被用户覆盖 → 排除列表里有没有**。这四步走完，九成的问题都能定位。

至于自己写 starter，核心是把「默认值 + 可覆盖 + 可排除」这三件事做对。做对了，使用者会觉得「加上依赖就能用，改配置就能调」；做错了，使用者会觉得「加了依赖什么都没发生，也不知道为什么」——而这正是凯喵最初踩的那些坑。

再补一层关于「该不该自建 starter」的判断标准。很多团队在有第二个项目需要复用同一套配置逻辑时就开始抽 starter，结果抽出来的东西只有自己用，维护成本却按公共库的标准来算。凯喵的经验是，判断标准不在于「有没有被复用」，而在于「复用点是否稳定」。如果这套配置在三个项目里已经有三个不同的改法，那它还不是「公共约定」，只是「还没收敛的探索」，此时抽 starter 只会把不确定性固化下来。等到同一个模式在两三个项目里连续半年没有变化，再抽也不迟。抽的时候把「哪些必须由使用者决定、哪些可以由默认值兜住、哪些允许被完全关掉」这三件事写进 README，比写一堆示例代码更有价值，因为后来的人遇到问题时，最先找的就是这份边界说明。

最后一句提醒：自动配置的坑，多数不是「机制不懂」，而是「机制懂了却没去验证」。开一次 debug 报告，看一眼条件评估结果，比读十篇源码解析都快。养成这个动作，排查时间能从半天缩短到五分钟。
而这个动作的门槛，其实只是记住加一个 `--debug` 参数而已。