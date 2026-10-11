# 二、自动配置的 SPI 加载与条件装配

## 1. 候选清单从哪来：SPI 机制的演进

**Spring Boot 2.7 之前**：所有扩展点统一写在 `META-INF/spring.factories` 里，用键值对区分：

```properties
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
com.example.FooAutoConfiguration,\
com.example.BarAutoConfiguration
```

问题在于：这个文件是**万能注册表**，自动配置、初始化器、监听器、失败分析器等全挤在一起，
体积膨胀且语义混杂；`=` 后面的**全限定类名写错不会报错**（框架只做反射加载，失败被吞）。

**Spring Boot 2.7+ / 3.x**：自动配置独立成清单文件，**每行一个类名，无 key**：

```
# META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
com.example.FooAutoConfiguration
com.example.BarAutoConfiguration
```

动机很明确：**单一职责**（一个文件只表达一件事）、**格式更简**（无需转义续行）、
**可校验**（Spring Boot 3 在编译期提供注解处理器校验类名是否存在）。
`spring.factories` 仍保留给其他扩展点，但**不再承载自动配置**。

## 2. 条件装配：决定「装不装」的那组注解

自动配置类几乎每个方法上都挂条件注解，语义如下：

| 注解 | 判定内容 | 典型用途 |
|---|---|---|
| `@ConditionalOnClass` | 类路径**存在**某类 | 「有 Redis 客户端才装配 RedisTemplate」 |
| `@ConditionalOnMissingClass` | 类路径**不存在**某类 | 与上者互补 |
| `@ConditionalOnMissingBean` | 容器里**还没有**某 Bean | 「用户没自己定义才给默认实现」 |
| `@ConditionalOnBean` | 容器里**已有**某 Bean | 「先有 DataSource 才配 JdbcTemplate」 |
| `@ConditionalOnProperty` | 配置项等于/不等于某值 | 开关式装配 |
| `@ConditionalOnWebApplication` | 当前是 Web 应用 | 区分 Servlet / Reactive / 非 Web |
| `@ConditionalOnResource` | 存在某资源文件 | 有配置文件才启用 |
| `@ConditionalOnExpression` | SpEL 表达式为真 | 复杂组合条件（**尽量少用**，可读性差） |

所有条件的**总入口是 `Condition` 接口**：

```java
@FunctionalInterface
public interface Condition {
    boolean matches(ConditionContext context, AnnotatedTypeMetadata metadata);
}
```

`@ConditionalOnXxx` 都是 `@Conditional(OnXxxCondition.class)` 的快捷写法 ——
**没有魔法，全部落到 `matches()` 返回的布尔值上**。这也是本章示例用纯 JDK
手写条件评估器的依据。

## 3. 关键约束：顺序决定结果

- `@ConditionalOnMissingBean` 的答案取决于**评估时刻容器里有什么**，因此
  自动配置类必须**晚于**用户的 `@Configuration` 被处理，否则会「重复注册」。
- 自动配置类之间用 `@AutoConfigureBefore` / `@AutoConfigureAfter` /
  `@AutoConfigureOrder` 声明相对顺序，框架据此做**拓扑排序**后按序评估。
- 依赖成环时会退化为「按类名字典序」并打警告日志 —— 所以**不要让自动配置互相强依赖**。

### 🧑‍💻 程序员视角

- **写自定义 starter 时，条件注解是必需品不是装饰品**：不加 `@ConditionalOnMissingBean`，
  使用方就无法覆盖你的默认 Bean，会到处打架。
- **`@ConditionalOnClass` 要用 `name` 属性写字符串**（`@ConditionalOnClass(name="com.x.Y")`）
  而不是直接引用 `.class`，否则当该类不存在时会发生 `NoClassDefFoundError`——
  这是自动配置类里最容易踩的坑之一。
- **`@ConditionalOnProperty` 的 `havingValue` 语义**：只写 `name` 不写 `havingValue` 时，
  要求值为 `"true"` 或**非 `"false"`**；`matchIfMissing=true` 表示配置缺失也算匹配。
  开关式配置写错这两点，会出现「配了却关不掉」。
- **排障**：`--debug` 启动会打印 `CONDITIONS EVALUATION REPORT`，分
  `Positive matches`（生效）与 `Negative matches`（未生效，附带未匹配原因）。
  这是定位「为什么我的 Bean 没来」的**唯一权威渠道**。

### 🎓 博士生视角

- **条件评估是「定义期」的谓词计算**：`Condition.matches` 在 BeanDefinition 阶段执行，
  因此它**不能**依赖某个 Bean 的实例状态（只能通过 `ConditionContext.getBeanFactory()`
  查询已有定义/单例名）。把「实例是否已创建」当作条件依据，会得到随机行为。
- **为什么用「排序 + 即时求值」而不是「两遍扫描」**：Spring 选择一次性有序评估，
  换取 O(n) 的评估次数；代价是引入了对**顺序**的依赖（顺序错了结论就错）。
  这是典型的「用约定换性能」的工程取舍，与编译器里的**单遍语义分析**是同一种取舍。
- **拓扑排序的退化策略**：DAG 上做 `@AutoConfigureAfter` 的相对排序，
  等价于「偏序关系的线性扩展」。出现环时无法线性化，Spring 的兜底是退化为字典序 +
  告警 —— 保证**永远能启动**（可用性优先于顺序精确性），这是框架设计的一贯取向。
- **SPI 的两种流派**：JDK 原生 `ServiceLoader`（服务文件 `META-INF/services/<接口全名>`，
  按接口名分文件）与 Spring 的清单文件（按用途分文件）。二者都是「约定的资源路径 + 反射实例化」，
  区别在**分组维度**：`ServiceLoader` 按接口分组，Spring 按用途分组。

### 📚 考研者视角

- **标准问法**：「SpringBoot 怎么做到『约定优于配置』？条件注解怎么用？」
  答题要点：SPI 清单给候选 → 条件注解做过滤 → 用户配置优先（`@ConditionalOnMissingBean`）。
- **高频追问**：「`@ConditionalOnMissingBean` 为什么有时失效？」
  标准答案：判定依赖注册顺序，它只在自动配置类中可靠；在用户 `@Configuration` 中使用
  或自动配置被提前处理时会失效。
- **易混对比**：`@ConditionalOnBean` 与 `@ConditionalOnClass` ——
  前者查**容器里的 Bean**（运行期容器状态），后者查**类路径上的类**（构建期依赖）。
  面试常把两者混着问，答错就暴露「只背了名词」。
- 与 408 的关联：`@AutoConfigureAfter` 形成的顺序约束就是**有向图**；
  「能否给出一个合法的评估顺序」即「该图是否是 DAG、能否拓扑排序」。
  数据结构里「拓扑排序 + 判环」的算法（Kahn 或 DFS）在本章示例 `ex03` 中被真实实现。
