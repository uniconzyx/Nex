# §5 spring-ch02 实战手记：凯喵带你把 IoC 容器用「炸」

> 前四节把生命周期、作用域、后置处理器、循环依赖讲透了。这一节凯喵把 Bean 容器最容易「启动失败 / 注入 null / 代理失效」的 12 个现场摆出来——每个都够你背一晚上锅。

### 现场一：构造器注入循环依赖，容器直接抛 BeanCurrentlyInCreationException

凯喵把 A、B 都用构造器互相注入，启动即报错。Spring **解决不了构造器循环的依赖**（实例化时就要对方，但对方还没出生）。解法：至少一方改用**字段/setter 注入**，或拆出第三方依赖。

```java
@Component
public class A {
    // ❌ 构造器循环，容器无解
    // public A(B b) { this.b = b; }
    @Autowired private B b;   // ✅ 改成字段/setter 注入
}
```

### 现场二：prototype 注入 singleton，每次拿到的还是同一个

凯喵把 `prototype` 的 Bean 用 `@Autowired` 注进 `singleton`，满心以为每次是新实例，结果一直是一个。singleton 只初始化一次，注入时就把 prototype 的固定引用存进去了。**想每次拿新实例要用 `ObjectProvider` 或 `ApplicationContext.getBean()`**。

```java
@Autowired ObjectProvider<Task> taskProvider;   // ✅ 每次 get 一个新 prototype
void run() { Task t = taskProvider.getObject(); }
```

### 现场三：忘了加 @ComponentScan，一个 Bean 都没注册

凯喵新建的 `@Service` 死活注入为 null，启动不报错但运行 NPE。根因：主类上的 `@SpringBootApplication` 只扫描**自己所在包及其子包**，新模块放在别的顶层包就被漏掉。要么挪包，要么显式 `@ComponentScan("com.x")`。

```java
@SpringBootApplication
@ComponentScan("com.x")   // ✅ 显式扩大扫描范围
public class App { public static void main(String[] a){ SpringApplication.run(App.class,a);} }
```

### 现场四：@Lazy 误用，掩盖了真正的循环依赖

凯喵用 `@Lazy` 把启动时的循环依赖报错压下去，以为修好了，结果首次请求时才懒加载、那时才炸，且更难定位。@Lazy 是解耦手段不是创可贴，优先**重构依赖方向**而非一路 @Lazy。

```java
@Autowired @Lazy private HeavyService s;  // 仅当确实想延迟创建；别用来藏循环依赖
```

### 现场五：@PostConstruct / InitializingBean 顺序搞混

凯喵在 `@PostConstruct` 里依赖另一个还没初始化的 Bean，偶发 NPE。Bean 初始化顺序由依赖决定，不保证和你写的顺序一致。依赖某个 Bean 就**显式注入它**，别假设它先好。

```java
@PostConstruct
void init() {
    // ✅ 依赖的 bean 通过字段注入进来，保证已就绪
    this.cache = buildCache(config.getSize());
}
```

### 现场六：Bean 不是线程安全，singleton 里存了请求级状态

凯喵在 singleton 的 `@Service` 里存了个 `Map` 记录「当前用户」，并发请求互相串号。singleton Bean 默认**无状态共享**，存可变成员就是线程不安全。请求级数据走方法参数或 `RequestContextHolder`。

```java
// ❌ singleton 里存请求状态
private Map<String,Object> ctx;
// ✅ 用方法参数传递，或 @Scope("request")
public void handle(User u) { Map<String,Object> ctx = new HashMap<>(); ... }
```

### 现场七：@Scope("prototype") 但被 singleton 持有，没真正多例

凯喵给 Bean 标了 `@Scope("prototype")`，却又把它 `@Autowired` 进 singleton，结果容器只在注入那一刻 new 一次。prototype 的「每次请求新实例」只对**直接 getBean** 或 **ObjectProvider.getObject** 生效。

```java
@Autowired ObjectProvider<LogEntry> entryProvider; // ✅ 每次 getObject 新实例
```

### 现场八：BeanPostProcessor 里注入业务 Bean，AOP 静默失效

凯喵写了一个 BPP 去依赖业务 Bean，结果那个业务 Bean 的 `@Transactional` 全失效了。BPP 极早创建，把业务 Bean 提前初始化，绕过了正常后处理链——代理还没织入。BPP 只依赖基础设施 Bean，要在所有 Bean 就绪后做事用 `SmartInitializingSingleton`。

```java
// ❌ BPP 依赖业务 Bean -> 提前初始化破坏代理
// ✅ 用 SmartInitializingSingleton 或 ContextRefreshedEvent
@Override public void afterSingletonsInstantiated() { /* Bean 全部就绪 */ }
```

### 现场九：用 @Bean 方法互相调用想拿代理，结果拿到原始对象

凯喵在 `@Configuration` 里 `beanA()` 内部直接调用 `beanB()`，以为拿到的是增强后的代理。其实 `@Configuration` 是 CGLIB 代理类，内部调用会被拦截返回单例；但若写成 `@Component` 的普通类，内部 `this.beanB()` 就是普通调用、绕过容器。统一用 `@Configuration`。

```java
@Configuration
public class Cfg {
    @Bean A a() { return new A(b()); }  // ✅ 走容器，拿的是同一个 b 单例
    @Bean B b() { return new B(); }
}
```

### 现场十：@DependsOn 顺序错了，依赖的 Bean 还没建好

凯喵用 `@DependsOn("dbInitializer")` 想保证数据库先初始化，但拼错 Bean 名或漏了，结果初始化顺序仍不对。@DependsOn 只保证**初始化顺序**，不保证你以为的那个 Bean；名字要和 `@Bean`/`@Component` 的 id 完全一致。

```java
@DependsOn("dbInitializer")   // Bean 名必须精确匹配
@Component public class CacheWarm { ... }
```

### 现场十一：条件化 Bean 没生效，@Profile / @Conditional 拼错

凯喵写 `@Profile("prod")` 的 Bean 在 dev 环境也加载了，因为启动参数 `--spring.profiles.active` 没传或拼错成 `pro`。条件化 Bean 依赖**激活的环境 / 条件类**，先用 `Environment` 打印确认当前 profile。

```bash
# 确认激活的 profile
--spring.profiles.active=prod
```

### 现场十二：销毁方法没调用，连接池泄漏

凯喵的 `@Bean` 返回了数据库连接池却没配销毁，`close()` 从没被调，应用关停时连接泄漏。有 `AutoCloseable` 的 Bean 容器会自动在关闭时调用 `close()`；自定义资源显式配 `destroyMethod`。

```java
@Bean(destroyMethod = "close")   // ✅ 容器关闭时释放资源
public DataSource ds() { return new HikariDataSource(); }
```

> 凯喵总结：IoC 的坑几乎都在「作用域」「初始化顺序」「循环依赖」「代理时机」。把这 12 个现场刻进配置手感，启动失败少一半。

## 三视角解析
### 🧑‍💻 程序员视角
`prototype` 的 Bean 注入到 `singleton` 里，只会创建一次——因为注入发生在单例初始化时，之后不再重新获取。要每次拿到新实例，得注入 `ObjectProvider` 或 `@Lookup`。`@Lazy` 能「解决」循环依赖，但多数时候只是把问题推迟到第一次调用时暴露，掩盖了真正的设计问题。Bean 名字冲突时 Spring 默认允许覆盖（Boot 2.1 起默认禁止），升级后突然启动失败往往就是两个同名 `@Bean`。

### 🎓 博士生视角
Spring 的 Bean 创建流程可以概括为「推断构造器 → 实例化 → 属性填充 → 初始化 → 后置处理」，其中 `BeanPostProcessor` 是最大的扩展点：AOP 代理、`@Autowired` 注入、`@PostConstruct` 都由它驱动。循环依赖的三级缓存本质是「提前引用暴露」，它只对「单例 + setter/字段注入」有效，对原型与构造器注入无效。理解这一点，就能解释「为什么加了 `@Async` 之后循环依赖突然报错」——代理对象的创建时机变了。

### 📚 考研者视角
面试高频：
1. **循环依赖**：三级缓存的三个 Map 各存什么、为什么需要第三级（AOP 代理）。
2. **Bean 作用域与生命周期**：`singleton` 容器级、`prototype` 每次新建，销毁回调对 `prototype` 不生效。
3. **`@Autowired` 与 `@Resource`**：前者按类型（可配 `@Qualifier`），后者按名称。
4. **`FactoryBean` 与 `BeanFactory`**：前者是「生产 Bean 的 Bean」，后者是容器本身。
