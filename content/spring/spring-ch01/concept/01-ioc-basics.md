# 一、IoC 基础与容器定位

## 一、什么是 IoC / 控制反转

（中立陈述）IoC（Inversion of Control，控制反转）是一种设计原则：传统程序里对象自己用 `new`
创建依赖；IoC 把「创建依赖、装配依赖、管理生命周期」的控制权交给一个**容器**。DI（Dependency
Injection，依赖注入）是 IoC 最常用的实现手段——容器在运行时把依赖「注入」到对象中。Spring 的
`ApplicationContext` 就是这样一个容器。

### 🧑‍💻 程序员视角
- 日常工程里：Controller 不再 `new Service()`，而是在构造器上写 `Service svc`，由 Spring 注入；
  这样单测时可以用 mock 替换依赖，可测试性直接提升一个档次。
- 踩坑：把 `@Service` 标在接口上不会生效（应标在实现类或被扫描的具体类）；忘记加 `@ComponentScan`
  或启动类位置不对，会导致「所有 bean 都没被注册」的空指针。
- 性能：容器启动期做一次反射/代理开销，运行期 `getBean` 命中单例缓存几乎是 O(1) 的 Map 查找，
  与手写 `new` 的运行期差异可忽略，瓶颈在启动耗时而非调用。

### 🎓 博士生视角
- 第一性原理：IoC 是把「对象图（object graph）的构造逻辑」从业务代码里**外置**为声明式配置，
  使业务类只表达「我需要什么」，不表达「它怎么来」。这本质是**依赖关系的可置换化**（依赖倒置 DIP）。
- 机制：容器维护一个 `beanName -> BeanDefinition` 的注册表；`getBean` 走
  `getBean -> doGetBean -> createBean -> populateBean -> initializeBean` 的确定性流程。
- 设计动机：把「装配」这一横切关注点集中管理，换来可测试性、可替换性、生命周期统一托管，
  这是框架相对于「随手 new」的范式收益。

### 📚 考研者视角
- 笔面标准问法：「IoC 和 DI 的区别？」「什么是控制反转？」
  标准口径：**IoC 是思想（把控制权交给容器），DI 是实现（容器注入依赖）**，二者是原则与手段的关系，
  不要答反。
- 易错口径：有人把 IoC 等同于「工厂模式」。工厂模式只是 IoC 的一种实现载体；DI 是更具体的实现。
- 相关考点：IoC 与「依赖倒置原则（DIP）」「好莱坞原则（don't call us, we'll call you）」的对应关系，
  面试常让举例说明。

## 二、BeanFactory 与 ApplicationContext 的差异

（中立陈述）`BeanFactory` 是最基础的容器接口，提供 `getBean` 等核心能力，**懒加载**（首次
`getBean` 才实例化）。`ApplicationContext` 是 `BeanFactory` 的超集，在启动时**预实例化单例
bean**，并额外提供国际化（MessageSource）、事件发布（ApplicationEvent）、环境与 Profile、
AOP 基础设施等。二者都满足「持有 bean 定义」，但能力边界不同。

### 🧑‍💻 程序员视角
- 工程选型：99% 的 Spring / Spring Boot 应用直接用 `ApplicationContext`（如
  `AnnotationConfigApplicationContext`），因为它启动即把单例都建好，能尽早暴露装配错误
  （fail-fast），而不是等到第一次请求才崩。
- 踩坑：在 `BeanFactory` 下若依赖在首次 `getBean` 时才创建，循环依赖相关错误会延迟暴露；
  `ApplicationContext` 在 `refresh()` 阶段就完成单例预实例化，问题更早暴露。
- 性能取舍：预实例化牺牲一点启动时间，换运行期零创建开销与更早的失败检测，生产环境几乎都选它。

### 🎓 博士生视角
- 抽象关系：`ApplicationContext extends ListableBeanFactory, HierarchicalBeanFactory, ...`，
  它通过**组合**多个子接口把「bean 工厂 + 环境 + 事件 + 国际化」聚合成一个统一门面。
- 机制差异：`AbstractApplicationContext.refresh()` 在 `finishBeanFactoryInitialization`
  阶段遍历 `beanDefinitionMap` 调用 `getBean` 预实例化非懒加载单例；
  `DefaultListableBeanFactory` 作为 `BeanFactory` 实现本身并不主动预实例化。
- 历史演进：早期 `XmlBeanFactory` 已被废弃，官方统一推荐使用 `ApplicationContext` 体系，
  因为高级特性（事件、AOP）都挂在它上面。

### 📚 考研者视角
- 笔面标准问法：「BeanFactory 和 ApplicationContext 有什么区别？」
  标准口径答三点：**① ApplicationContext 继承 BeanFactory；② ApplicationContext 预实例化单例
  （饿汉），BeanFactory 懒加载；③ ApplicationContext 多了国际化、事件、AOP 等能力。**
- 易错口径：不要说「ApplicationContext 比 BeanFactory 快」——运行期两者单例获取都是 Map 查找；
  差异在启动期是否预实例化，应说「启动更慢但更早暴露错误、运行期无差别」。
- 常见追问：「为什么有了 BeanFactory 还要 ApplicationContext？」答：能力扩展 + fail-fast。
