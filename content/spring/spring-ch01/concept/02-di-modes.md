# 二、依赖注入的三种方式

## 一、构造器注入 vs Setter 注入 vs 字段注入

（中立陈述）Spring 支持三种注入点：**构造器注入**（通过构造参数）、**Setter 注入**（通过
`setXxx` 方法）、**字段注入**（直接给字段赋值，如 `@Autowired` 标注 field）。三者都满足「容器
把依赖塞进来」，但在不可变性、必填性、可测试性上差异显著。

### 🧑‍💻 程序员视角
- 工程惯例（Spring 官方推荐）：**强制依赖用构造器注入**——依赖可声明为 `final`，对象构造即完整、
  不可变、线程更安全；可选依赖才用 Setter。
- 字段注入的代价：`@Autowired private Repo repo;` 写在私有字段上，单测必须启动容器或反射才能注入，
  无法像构造器那样直接 `new Service(mockRepo)` 传入，可测试性差；且 IDE 可能报「未使用」警告。
- 踩坑：构造器注入出现**循环依赖**会直接启动失败（`BeanCurrentlyInCreationException`），这其实是
  好事——逼你重构；而字段/Setter 注入会被三级缓存「悄悄」解决，隐藏设计坏味道。

### 🎓 博士生视角
- 不可变性原理：构造器注入让依赖字段可标 `final`，对象在构造结束后即处于**不变式成立**状态，
  无需额外同步即可线程安全；Setter/字段注入允许构造后变更，引入「部分初始化对象」的可能。
- 注入时机差异：构造器注入发生在 `createBeanInstance` 阶段（实例化即拿到完整依赖）；
  Setter/字段注入发生在 `populateBean` 阶段（先有空壳对象，再回填属性）。
- 设计动机：把「必填依赖」放进构造签名，等于用类型系统强制调用方提供依赖，比靠约定更可靠
  （编译期校验优于运行期 NPE）。

### 📚 考研者视角
- 笔面标准问法：「构造器注入和字段注入怎么选？」标准口径：**强制/不可变依赖用构造器；可选依赖用
  Setter；字段注入不推荐（破坏可测试性、无法声明 final）。**
- 易错口径：有人答「字段注入性能最好」——注入方式不影响运行期性能，字段注入只是少了样板代码，
  代价在可测试性与不可变性，不是性能。
- 常见追问：「为什么 Spring 官方推荐构造器注入？」答：不可变 + 必填编译期保证 + 易单测 + 循环依赖
  早失败。

## 二、依赖解析：按类型与按名称（@Qualifier）

（中立陈述）容器注入时先按**类型（byType）**在 `beanDefinitionMap` 中找候选。若同类型只有一个
bean，直接注入；若有多个候选，需退化为**按名称（byName）**或借助 `@Qualifier("name")` /
`@Primary` 指定，否则抛出 `NoUniqueBeanDefinitionException`。

### 🧑‍💻 程序员视角
- 工程惯例：同一接口多个实现时，用 `@Qualifier("mysqlEngine")` 显式点名，或在一个实现上标
  `@Primary` 作为默认；避免让容器「猜」。
- 踩坑：字段名与 bean 名不一致又没写 `@Qualifier`，会抛 `NoUniqueBeanDefinitionException`；
  改名或加注解即可。
- 性能：类型匹配靠 `Class.isAssignableFrom` 遍历候选，候选很少时开销可忽略；不要在单例解析路径
  里放复杂逻辑。

### 🎓 博士生视角
- 解析算法：`DefaultListableBeanFactory.resolveDependency` 先 `findAutowireCandidates`（byType），
  再按 `@Qualifier` / `@Primary` / 字段名（byName 兜底）二次筛选；都不是唯一则抛歧义异常。
- 机制：`@Primary` 是「优先级标记」，`@Qualifier` 是「精确命名」，二者都在 `beanName` 维度做区分，
  本质是给「byType 多候选」提供一个确定性 tie-breaker。
- 设计动机：类型驱动的自动装配降低配置量，但多候选时必须有人拍板，否则自动化反而制造不确定性。

### 📚 考研者视角
- 笔面标准问法：「一个接口有两个实现，怎么注入指定的那个？」标准口径：**@Qualifier 指定 bean 名，
  或 @Primary 设默认，或字段名等于目标 bean 名（byName 兜底）。**
- 易错口径：把 `@Qualifier` 当成「按类型过滤」——它是**按 bean 名称精确匹配**，配合 `@Autowired`
  的 byType 结果做收窄。
- 常见追问：「@Primary 和 @Qualifier 优先级谁高？」答：`@Qualifier` 精确命名优先于 `@Primary`。
