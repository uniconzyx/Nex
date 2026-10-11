# 一、@SpringBootApplication 的「三合一」与启动主干

## 1. 一个注解，三个职责

```java
@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) { SpringApplication.run(DemoApplication.class, args); }
}
```

`@SpringBootApplication` 本身几乎不做事，它是一组注解的**复合（composed annotation）**：

| 组成注解 | 职责 | 缺失后的症状 |
|---|---|---|
| `@SpringBootConfiguration` | 本质是特殊的 `@Configuration`，标记「这是配置类」 | 直接被 `@Configuration` 的语义接管，用于被 `@SpringBootTest` 查找主配置 |
| `@EnableAutoConfiguration` | 通过 SPI 把候选自动配置类拉进容器 | 内嵌 Tomcat、DataSource 等全都不装配 |
| `@ComponentScan` | 扫描主类所在包及其子包下的 `@Component` 系 | 自己写的 `@Service`/`@Controller` 全部找不到 |

关键点：**自动配置不是组件扫描的结果**。`@ComponentScan` 只扫**你自己的**包；
Spring Boot 官方 jar 里的配置类在 `org.springframework.boot.autoconfigure` 包，
与你的包毫无关系，它们是被 `@EnableAutoConfiguration` 通过 **SPI 清单文件**显式加载的。

## 2. `SpringApplication.run` 的启动主干

剥掉事件与日志，主干可以压缩成一条链：

```
SpringApplication.run()
 └─ new SpringApplication(...)                  /* 推断应用类型 SERVLET/REACTIVE/NONE */
 └─ run(args)
     ├─ 1. 准备 Environment（加载配置源、命令行参数、profile）
     ├─ 2. 打印 Banner
     ├─ 3. 创建 ApplicationContext（按类型选 Servlet/Reactive/Annotation）
     ├─ 4. prepareContext：把主配置类注册为 BeanDefinition
     ├─ 5. refreshContext()   ← 就是 spring-ch01 讲过的 AbstractApplicationContext#refresh
     │      ├─ invokeBeanFactoryPostProcessors()
     │      │    └─ ConfigurationClassPostProcessor
     │      │         ├─ 解析 @ComponentScan  → 注册你的 Bean
     │      │         └─ 解析 @Import(AutoConfigurationImportSelector)
     │      │              └─ 读 SPI 清单 → 条件过滤 → 注册自动配置类
     │      ├─ registerBeanPostProcessors()
     │      ├─ onRefresh()  ← Servlet 容器在此创建并启动（内嵌 Tomcat）
     │      └─ finishRefresh()
     └─ 6. 发布 ApplicationReadyEvent，启动完成
```

**记忆锚点**：自动配置发生在 `refresh()` 的
**`invokeBeanFactoryPostProcessors` 阶段**，即「Bean 定义阶段」而非「Bean 实例化阶段」。
这解释了一个常见现象：即使某个自动配置类的条件不满足，它的**类名依然会出现在
`--debug` 的 Negative matches 列表里** —— 因为「评估条件」需要先知道候选是谁，
候选清单正是此刻被读出来的。

### 🧑‍💻 程序员视角

- **排障第一反应**：Bean 没注入，先看是「扫不到」（自己包）还是「没条件装配」（官方包）。
  前者查 `@ComponentScan` 范围与包结构，后者加 `--debug` 或看 `/actuator/conditions`。
- **主类位置是约定**：脚手架默认 `com.example.demo.DemoApplication`，若你的业务类在
  `com.example`（父包），会扫不到。工程惯例是把主类放在**根包**，
  所有模块都在其下（`com.example.order`、`com.example.user`）。
- **`refresh()` 里别做重活**：`ApplicationRunner`/`CommandLineRunner` 才是放业务初始化的地方；
  往 `BeanFactoryPostProcessor` 里塞网络请求会导致启动期难以观测的阻塞。
- **启动耗时定位**：`--debug` 之外的现代手段是 `ApplicationStartup` + `BufferingApplicationStartup`
  （`spring-boot-actuator` 的 startup 端点），能给出每个步骤的耗时，比手写计时准确。

### 🎓 博士生视角

- **复合注解不是语法糖，是语义收敛**：Spring 用 `@AliasFor` 把三个注解的属性做双向绑定
  （如 `@SpringBootApplication(scanBasePackages=...)` 实际写到 `@ComponentScan` 上），
  因此「属性覆盖」有明确的优先级规则；用 `@AliasFor` 而非简单嵌套，是为了让元注解属性
  在 IDE 与处理器里可被统一解析。
- **为什么要区分 BeanDefinition 阶段与实例化阶段**：Spring 的架构把「发现/改写定义」
  与「创建实例」分离，才使得 `@ConditionalOnMissingBean`（需要知道「有没有」但不触发实例化）、
  `@Import`、`@Lazy` 这些机制能够成立。这是一个典型的**两阶段提交式设计**：
  定义阶段可以任意修改，实例化阶段只执行。
- **SPI 与依赖倒置**：`AutoConfigurationImportSelector` 位于 `spring-boot-autoconfigure`，
  而它要加载的配置类分散在成千上万个第三方 jar 中。用「jar 内清单文件」而非「中心注册表」，
  使**第三方 jar 无需被框架知晓即可参与装配**，这是依赖倒置在构建期的体现。

### 📚 考研者视角

- Spring 不属于 408 大纲，本节按 **Java/后端岗笔试面试** 的标准口径整理：
  - **标准问法**：「SpringBoot 自动配置原理？」标准答法是四步：
    ①`@SpringBootApplication` 引出 `@EnableAutoConfiguration`；
    ②它 `@Import` 了 `AutoConfigurationImportSelector`；
    ③该 Selector 通过 SPI 读取候选配置类清单；
    ④再用 `@Conditional` 系列做过滤，最终注册生效的 Bean。
  - **易错口径**：把第③④步说成「扫描类路径下的所有 `@Configuration`」是错的 ——
    必须强调清单文件（`spring.factories` / `AutoConfiguration.imports`）。
  - **对比题**：`@SpringBootApplication` 与 `@EnableAutoConfiguration` 的区别
    （前者=后者+配置类+组件扫描），是高频送分题。
- 与 408 的知识关联：`@ComponentScan` 的「按包递归扫描」本质是一次**目录树遍历**；
  自动配置的「拓扑排序」是**有向无环图的拓扑序**问题（408 数据结构考点，见本章 concept 02）。
