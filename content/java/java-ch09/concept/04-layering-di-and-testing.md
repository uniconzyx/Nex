# 04 · 分层架构、依赖注入与测试

## 一、分层：职责边界比技术选型更重要

```java
// controller（接口层）：只做参数校验、协议转换、返回包装；不写业务
@RestController
@RequestMapping("/api/users")
class UserController {
    private final UserService service;                       // 构造器注入
    UserController(UserService service) { this.service = service; }

    @GetMapping("/{id}")
    UserDto get(@PathVariable long id) { return UserDto.of(service.findById(id)); }
}

// service（业务层）：业务规则 + 事务边界；不感知 HTTP
@Service
class UserService { /* ... */ }

// repository（持久层）：只做数据存取；不做业务判断
interface UserRepository { User findById(long id); }
```

**判据**：controller 里出现 `if (业务规则)` 说明逻辑下沉不足；
repository 里出现 `if (权限)` 说明越权。DTO 与 Entity **必须分开**——
把 Entity 直接序列化返回，等于把数据库结构当 API 契约，改表就破坏接口兼容性。

## 二、依赖注入三种方式：为什么不推荐字段注入

| 方式 | 写法 | 优点 | 缺点 |
|---|---|---|---|
| 字段注入 | `@Autowired private X x;` | 最短 | **不可 final**、无法在构造时校验、脱离容器无法 `new`（单测必须反射或 Spring 上下文）、**掩盖循环依赖** |
| setter 注入 | `@Autowired void setX(X x)` | 可重配、适合可选依赖 | 对象可能**半初始化**（属性未设也能存在） |
| **构造器注入** | `X x; Ctor(X x){ this.x=x; }` | **依赖不可变（final）**、**缺依赖启动即失败**、**单测直接 new** | 参数多时略显冗长（可用 Lombok `@RequiredArgsConstructor`） |

Spring 官方从 4.3 起对**单构造器**省略 `@Autowired` 的支持，就是在引导大家用构造器注入。

## 三、Bean 作用域与线程安全

| 作用域 | 实例数 | 说明 |
|---|---|---|
| `singleton`（默认） | 每容器 1 个 | **必须无状态**，否则并发下共享可变字段会出数据竞争 |
| `prototype` | 每次获取新建 | Spring **不管理其销毁**（销毁回调不会被调用） |
| `request` / `session` | 每请求/会话 | 仅 Web 上下文；需 `proxyMode` 才能在单例中注入 |
| `application` | 每 ServletContext | 极少用 |

**核心纪律**：单例 Bean 里不要有可变的实例字段。要状态就放**方法局部变量**
或 `ThreadLocal`（记得在请求结束时 `remove()`，线程池复用下不清会**内存泄漏**）。

## 四、事务：@Transactional 的失效场景

`@Transactional` 生效依赖 **Spring AOP 代理**，因此以下情况**事务不生效**：

1. **同类内部方法自调用**——`this.methodB()` 不走代理，注解失效。
2. **方法不是 `public`**——默认代理策略对非 public 不织入。
3. **异常被吞掉**——默认只在 `RuntimeException` / `Error` 回滚，
   受检异常需 `rollbackFor = Exception.class`。
4. **多线程**——事务上下文绑定在 `ThreadLocal`，子线程不在同一事务。
5. **Bean 是自己 `new` 的**——不在容器中，没有代理。

**事务边界应放在 service 层**：controller 不该管事务（一次请求可能多次调用 service），
repository 也不该管（无法覆盖多表操作）。

## 五、测试金字塔与三类测试

| 层次 | 注解 / 工具 | 覆盖 | 代价 | 适用 |
|---|---|---|---|---|
| 单元测试 | JUnit + Mockito，**不起容器** | 单个类 | 毫秒级 | service 业务规则 |
| 切片测试 | `@WebMvcTest` / `@DataJpaTest` | 一层 | 秒级 | 控制器参数绑定、JSON 序列化 |
| 集成测试 | `@SpringBootTest` | 全链路 | 秒~分钟级 | 关键路径、事务与 SQL |

**Maven 的测试命名约定**：`surefire` 跑 `*Test`（单元，`mvn test`），
`failsafe` 跑 `*IT`（集成，`mvn verify`）。把集成测试命名成 `*Test` 会让
`mvn test` 变慢——这是 CI 提速的常见手段。

**Mock 的本质**是「用替身替换协作对象」：`when(repo.findById(1)).thenReturn(u)`
把外部依赖（数据库、HTTP）切断，从而让被测对象的**行为**成为唯一变量。

## 六、可运行代码

```java
// 手写迷你容器：构造器/字段/setter 三种注入 + 手写 Mock 校验调用次数
// 详见 examples/ex09-di-three-ways.json、examples/ex10-layered-mock-test.json
```

## 三视角解析

### 🧑‍💻 程序员视角
### 🎓 博士生视角
### 📚 考研者视角

### 🧑‍💻 程序员视角
分层落地时的实操细节：**DTO 用 record**（不可变、自带 `equals/hashCode`），
Entity 保留 setter 给 ORM；controller 上放 `@Valid` + `@ControllerAdvice` 统一异常处理
（**不要**在每个方法里 try-catch），把校验失败、业务异常、系统异常映射成统一错误码。
事务的「只读优化」`@Transactional(readOnly = true)` 在查询方法上加上，能让部分数据库
走只读路径并抑制脏检查（Hibernate 会跳过 flush）。单测里凡是 `@SpringBootTest` 都能
换成 `@ExtendWith(MockitoExtension.class)` + `@Mock` 的就换掉——**启动一次上下文约
几百毫秒，一百个测试累积就是几分钟**。

### 🎓 博士生视角
依赖注入的形式化表述是**控制反转**：对象不再自己 `new` 协作者，而是由容器按
**依赖图的拓扑序**注入，等价于把「构造顺序」从代码里**外化**成声明。
构造器注入之所以优于字段注入，是因为它在**类型系统层面**保证了不变量：
所有 `final` 字段在构造完成时必然已赋值，即「不存在半初始化对象」——
这是**不可变对象（immutable object）** 的前提，而不可变性与线程安全之间的
一致性（无数据竞争）是并发正确性的基础。字段注入把这个保证**推迟到运行时的反射阶段**，
于是对象可以在容器外被 `new` 出来却是坏的（字段全 null），
本质是**把编译期可检查的约束降级为运行时不变量**。
事务代理则体现了**横切关注点（cross-cutting concern）** 与**代理模式的结合**：
`@Transactional` 的语义是「在方法调用外包一层 BEGIN/COMMIT/ROLLBACK」，
因此它只能作用于**经代理进入的调用**——「自调用失效」不是实现缺陷，
而是代理模式的**必然推论**（`this.methodB()` 不经过代理对象）。
这也解释了为什么 Spring Boot 2.6+ 默认禁止循环依赖：循环依赖会迫使容器在
**未完成初始化的对象**上暴露引用（早期引用），破坏上述不变量。

### 📚 考研者视角
高频问答与易错口径：
- **三种注入方式及推荐**：构造器（推荐）、setter、字段（不推荐）；理由是构造器注入保证
  依赖**不为 null** 且可 `final`，且**便于单元测试**（可直接 `new`）。
- **`@Autowired` 注入规则**：默认 **byType**，多个同类型时按 **`@Qualifier` / 字段名** 匹配；
  `required=false` 允许为空。
- **`@Resource`（JSR-250）默认 byName**，`@Autowired` 默认 byType——常考辨析。
- **`@Transactional` 失效场景**（背 5 条）：非 public 方法、自调用、异常被吞、
  非运行时异常未配 `rollbackFor`、多线程/未托管 Bean。
- **默认回滚规则**：只对 `RuntimeException` 与 `Error` 回滚，受检异常**不回滚**（除非显式声明）。
- **`@Transactional` 的 `propagation`**：常考 `REQUIRED`（默认，加入现有事务）、
  `REQUIRES_NEW`（挂起当前、新开事务）、`NESTED`（保存点）。
- **测试命名约定**：`surefire` 管 `*Test`，`failsafe` 管 `*IT`，分别绑定 `test` 与 `verify` phase。
- **`@RestController` = `@Controller` + `@ResponseBody`**，返回对象直接序列化为 JSON。
