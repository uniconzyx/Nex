# §5 spring-ch01 实战手记：凯喵带你把 IoC/DI 用「懵」

> 前四节把 IoC 基础、DI 模式、组件扫描、循环依赖讲透了。这一节凯喵把刚上手 Spring 最容易「注入 null / 启动报错 / 行为静默变化」的 12 个现场摆出来——每个都够新人卡一下午。

### 现场一：同类型多 Bean 时靠字段名「猜」实现

凯喵 `@Autowired private UserService userService;`，存在两个 `UserService` 实现时，Spring 退化成**按字段名匹配 Bean 名**，改个字段名就换了实现，不报错、行为静默变。正确做法：显式 `@Qualifier("beanName")` 或 `@Primary`；要遍历所有实现注入 `Map<String, UserService>`。

```java
@Autowired @Qualifier("wechatUserService")   // ✅ 显式指定
private UserService svc;
// 或
@Primary                                    // 标一个默认实现
@Component class DbUserService implements UserService {}
```

### 现场二：忘了 @ComponentScan，一个 Bean 都没注册

凯喵新建的 `@Service` 注入是 null，启动不报错运行 NPE。主类 `@SpringBootApplication` 只扫**自己所在包及其子包**，新模块在别的顶层包就被漏。要么挪包，要么显式 `@ComponentScan("com.x")`。

```java
@SpringBootApplication
@ComponentScan("com.x")   // ✅ 扩大扫描范围
public class App {}
```

### 现场三：构造器注入 vs setter 注入选型乱

凯喵所有依赖都用字段注入，结果必填依赖没传也能启动，运行时才 NPE。规则：必填、不可变的依赖用**构造器注入**（启动即校验、利于测试）；可选/可变的用 setter。字段注入不利于测试和不可变，尽量少用。

```java
// ✅ 必填依赖用构造器注入，启动即校验
@Service
public class OrderService {
    private final PaymentClient client;
    public OrderService(PaymentClient client) { this.client = client; }
}
```

### 现场四：构造器循环依赖，启动直接抛异常

凯喵把 A、B 都用构造器互相注入，启动报 `BeanCurrentlyInCreationException`。Spring 解不了构造器级别的循环（实例化就要对方，对方还没出生）。至少一方改字段/setter 注入，或拆出第三方依赖。

```java
@Component
public class A { @Autowired private B b; }   // ✅ 至少一方非构造器注入
@Component
public class B { @Autowired private A a; }
```

### 现场五：@Autowired required 默认 true，缺 Bean 即失败

凯喵 `@Autowired private Optional<Feature> f;` 想表达「有就有没有拉倒」，旧版却因 required 默认 true 启动失败。Spring 4.3+ 对构造器参数支持 `Optional`/`@Nullable`；字段注入可用 `required=false`（已不推荐，改用 Optional）。

```java
// ✅ 可选依赖用 Optional，缺失不报错
public MyService(Optional<Cache> cache) { this.cache = cache; }
```

### 现场六：@Value 取不到配置，原因是占位符 or 类型

凯喵 `@Value("${app.timeout}")` 拿到 null，因为根本没在 `application.yml` 配这个 key，或类型不对（字符串塞进 int）。用 `:` 给默认值防缺失，复杂配置用 `@ConfigurationProperties` 绑定对象。

```java
@Value("${app.timeout:3000}")            // ✅ 缺失用默认值 3000
private int timeout;
// 或批量绑定
@ConfigurationProperties("app") class AppProps { int timeout; }
```

### 现场七：Bean 不是线程安全，singleton 里存状态

凯喵在 singleton `@Service` 存了「当前用户」字段，并发请求互相串号。singleton 默认无状态共享，存可变成员即线程不安全。请求级数据走方法参数或 `RequestContextHolder`，或 `@Scope("request")`。

```java
// ❌ singleton 存请求状态
private String currentUser;
// ✅ 方法参数传递
public void handle(String currentUser) { ... }
```

### 现场八：@Lazy 误用掩盖循环依赖

凯喵用 `@Lazy` 把启动时的循环依赖报错压到首次请求才炸，更难定位。@Lazy 是解耦手段不是创可贴，优先**重构依赖方向**而非一路 @Lazy。

```java
@Autowired @Lazy private HeavyService s;  // 仅当确实想延迟创建，而非藏循环
```

### 现场九：@PostConstruct 里依赖还没就绪的 Bean

凯喵在 `@PostConstruct` 用另一个 Bean，偶发 NPE——初始化顺序不保证按你写的来。依赖谁就**显式注入谁**，别假设它先好；需要「全部就绪后」动作放 `ApplicationRunner` / `SmartInitializingSingleton`。

```java
@PostConstruct
void init() { this.cfg = load(this.config.getPath()); }  // config 已注入则安全
```

### 现场十：用 new 创建 Bean，@Autowired 全失效

凯喵 `new UserService()` 自己 new 对象，结果里面的 `@Autowired` 字段全是 null——Spring 只管理它**自己创建的** Bean，你手动 new 的容器不碰。要用容器里的依赖必须让容器创建（注入或 `getBean`）。

```java
// ❌ new 出来的对象不走容器，依赖为 null
UserService s = new UserService();
// ✅ 交给容器
@Autowired UserService s;
```

### 现场十一：原型 Bean 被 singleton 持有，没真正多例

凯喵给 Bean 标 `@Scope("prototype")` 又 `@Autowired` 进 singleton，容器只在注入时 new 一次。prototype 的「每次新实例」只对**直接 getBean / ObjectProvider.getObject** 生效。

```java
@Autowired ObjectProvider<Task> taskProvider;  // ✅ 每次 getObject 新实例
```

### 现场十二：条件化 Bean 没生效，@Profile 拼错

凯喵写 `@Profile("prod")` 的 Bean 在 dev 也加载，因为 `--spring.profiles.active` 没传或拼错成 `pro`。条件化 Bean 依赖激活的环境，先用 `Environment` 打印确认当前 profile。

```bash
--spring.profiles.active=prod   # 确认激活的 profile 正确
```

> 凯喵总结：IoC/DI 的坑九成在「扫描范围」「多 Bean 歧义」「循环依赖」「线程安全」。把这 12 个现场刻进上手笔记，Spring 启动失败少一半。

### 现场之外：凯喵的注入三原则
刚上手 Spring，凯喵定下三个原则避免踩坑。第一，依赖从哪来就由谁来管：容器创建的 Bean 才能享受自动装配，自己 new 的对象里的 @Autowired 永远是 null，这个铁律记住能省下无数 NPE。第二，必填依赖用构造器注入，启动即校验，缺一个 Bean 立刻报错而不是运行到一半才炸。第三，单例里不要存任何会变的成员，singleton 是全局共享的，凡是请求级状态都让它活在方法参数里。三条原则贯彻下去，Spring 的「魔法」就不再是玄学。

### 现场拾遗：从看报错到看容器
再补一句：遇到 Bean 相关的问题，别急着改代码，先看容器的启动日志和 Bean 定义。Spring 启动时打印的 Bean 名、创建顺序、注入来源，基本能把「为啥是 null」「为啥注入了错的实现」讲得明明白白。养成「先看容器、再改业务」的习惯，排查 IoC 问题能快好几倍。

### 一句话收尾
凯喵最后提醒：IoC 不是魔法，它只是把「对象怎么造、怎么连」这件事从你手里收归容器统一管。你写的还是普通类和普通方法，只不过创建和装配的时机交了出去。想明白这一点，那些「为什么注入是 null」「为什么顺序不对」的问题，都会变成「对象生命周期」这一个问题的不同侧面，不再零散难记。

## 三视角解析
### 🧑‍💻 程序员视角
同类型有多个 Bean 时，Spring 先按类型找、再按字段名匹配——字段名恰好等于某个 Bean 名就「碰巧」注入了，改个字段名立刻启动失败。`@ComponentScan` 漏配是「Bean 找不到」的头号原因：默认只扫启动类所在包及子包，跨包必须显式指定。构造器注入优于字段注入：依赖不可变、能暴露循环依赖、单测不用反射。构造器循环依赖无解，因为对象都还没构造出来，只能靠 `@Lazy` 或重构打破环。

### 🎓 博士生视角
IoC 容器的本质是「对象图的生命周期管理 + 依赖解析」：`BeanDefinition` 描述如何创建，`BeanFactory` 负责实例化与注入，`ApplicationContext` 在其上叠加事件、国际化、资源加载等企业级能力。三级缓存解决的是「单例 setter 注入的循环依赖」：一级存成品、二级存半成品、三级存工厂，通过提前暴露引用打破环。但构造器注入无法用缓存解决，因为对象尚未构造，这也是 Spring 官方推荐构造器注入的深层原因之一——它让循环依赖在启动期就暴露。

### 📚 考研者视角
面试必问：
1. **IoC 与 DI 的区别**：IoC 是「控制权反转」的思想，DI 是其实现方式。
2. **三种注入方式**：构造器（推荐）、setter、字段；各自对循环依赖与不可变性的影响。
3. **Bean 的作用域**：`singleton`（默认）、`prototype`、`request`、`session`、`application`。
4. **Bean 的生命周期**：实例化 → 属性注入 → `Aware` 回调 → `BeanPostProcessor` 前置 → `init` → 使用 → `destroy`。
