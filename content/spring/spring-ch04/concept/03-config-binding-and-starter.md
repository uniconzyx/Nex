# 三、配置绑定、优先级与自定义 starter

## 1. `@ConfigurationProperties` vs `@Value`

| 维度 | `@ConfigurationProperties` | `@Value` |
|---|---|---|
| 绑定粒度 | **整个前缀**（`app.mail.*`）批量绑定到对象的字段 | 单个键，逐个写 |
| 松散绑定 | **支持**：`app.my-name` / `app.myName` / `APP_MY_NAME` 均可绑定 `myName` | **不支持**，必须逐字符写对 |
| SpEL | 不支持 | 支持 `#{...}` |
| 校验 | 可配合 `@Validated` + JSR-303 | 不支持 |
| 复杂类型 | 支持 List/Map/嵌套对象 | 需手写 SpEL 或数组语法 |
| 缺失时的行为 | 默认值（若声明）或 **null，静默** | 直接启动失败 |

**工程结论**：成组配置一律用 `@ConfigurationProperties`（类型安全 + 可校验 + IDE 元数据提示）；
只有零散的、需要 SpEL 的单个值才用 `@Value`。

**松散绑定的规范化规则**（把配置键统一成小写短横线的「规范形式」）：

```
my-name      → my-name
myName       → my-name
my_name      → my-name
MY_NAME      → my-name
app.myName   → app.my-name
```

注意：**只有前缀以外**的部分做松散匹配；前缀本身必须严格匹配。

## 2. 配置优先级与 profile

同一层级内，**profile 专属文件覆盖通用文件**：

```
application.properties          ← 通用
application-prod.properties     ← 激活 prod 时覆盖上面的同名键
```

但跨层级时，**位置优先于 profile**（从高到低）：

```
命令行参数 --server.port=9090
  > SPRING_APPLICATION_JSON / 环境变量
  > Java System properties (-D)
  > OS 环境变量
  > jar 包外 application-{profile}.properties
  > jar 包内 application-{profile}.properties
  > jar 包外 application.properties
  > jar 包内 application.properties
  > @PropertySource / 默认属性
```

**最反直觉的一条**：jar 包外的 `application.properties`（无 profile）
优先级 **高于** jar 包内的 `application-prod.properties`。
运维「外置配置覆盖内置」的诉求正是靠这条实现的，也是「为什么本地跑得好、上线就变」的常见根因。

## 3. 自定义 starter 的两模块结构

```
xxx-spring-boot-autoconfigure/        ← 自动配置实现
├── pom.xml                           （依赖 spring-boot-autoconfigure，scope=optional）
└── src/main/java/.../XxxAutoConfiguration.java
    src/main/resources/META-INF/spring/
        org.springframework.boot.autoconfigure.AutoConfiguration.imports
xxx-spring-boot-starter/              ← 聚合依赖
└── pom.xml                           （只依赖 autoconfigure + 具体实现库）
```

**为什么必须拆两个模块？**
若合成一个模块，使用方引入后，其中的自动配置类会落在**被组件扫描的包路径**下
（如果包名与使用方重叠），或者被迫把自动配置类暴露为可被扫描的候选，
从而破坏「**自动配置只应由 SPI 驱动**」这条边界。拆开后，`starter` 模块**不含任何代码**，
纯粹是依赖聚合，语义干净。

**命名约定**：官方 starter 是 `spring-boot-starter-xxx`；第三方应命名为
`xxx-spring-boot-starter`（把自己的名字放前面），以便与官方区分。

### 🧑‍💻 程序员视角

- **`@ConfigurationProperties` 拼错 key 不会报错**：默认静默为 null，
  线上表现为「功能默默不生效」。所以生产项目应加 `@Validated` 强制校验，
  并引入 `spring-boot-configuration-processor` 生成 `spring-configuration-metadata.json`，
  让 IDE 能对键名做补全与告警。
- **`@DurationUnit` / `@DataSizeUnit` 必写**：`Duration` 默认单位是**毫秒**，
  写成 `timeout: 30` 会被解释成 30 毫秒而不是 30 秒。用了单位注解后
  `timeout: 30s` 才可读且无歧义。
- **敏感配置不要进 git**：用环境变量或配置中心；Spring Boot 3 支持
  `spring.config.import=configtree:/etc/secrets/` 从 Docker/K8s 挂载的 secret 目录读取。
- **自定义 starter 的自动配置类必须加 `@ConditionalOnMissingBean`**，
  否则使用方无法用自定义 Bean 覆盖默认实现，starter 就变成「霸道依赖」。

### 🎓 博士生视角

- **松散绑定是一套规范化函数**：实现上把候选键做「去分隔符 + 小写化」后建索引
  （`ConfigurationPropertyName`），再与目标字段的规范名比对。
  这解释了为什么 `my-name` 与 `myName` 等价，而 `myname` 与 `my-name` **不等价**
  （后者的规范名仍是 `my-name`）。它不是「模糊匹配」，而是**多写法归一化**。
- **配置源的合并是「有序覆盖」而非「优先查询」**：`Environment` 把所有
  `PropertySource` 放进一个有序列表，读取时**从前往后第一个命中即为答案**，
  因此「优先级」本质是**列表顺序**。profile 的处理则是在构建这个有序列表时，
  用 `Profiles` 谓词决定哪些文件被加入、插入到哪个位置。
- **starter 的两模块拆分是「依赖可见性」设计**：`autoconfigure` 模块把
  `spring-boot-autoconfigure` 标为 `optional`，意味着它**不会被传递**给使用方 ——
  这样使用方不会被强制带入一堆与自己无关的实现，是**最小依赖**原则的体现。
- **与「插件系统」的类比**：starter = 插件包（聚合）+ 插件元数据（imports 清单）+
  插件实现（autoconfigure）。与操作系统插件、浏览器扩展的「清单 + 实现」结构同构。

### 📚 考研者视角

- **标准问法**：「SpringBoot 配置优先级？」「`@Value` 和 `@ConfigurationProperties` 区别？」
  「怎么自定义 starter？」——这三个是后端面试的固定三连。
- **答题要点（starter）**：①建两个模块；②`autoconfigure` 模块写配置类 + 条件注解；
  ③在 `AutoConfiguration.imports` 里登记类名；④`starter` 模块聚合依赖；
  ⑤命名用 `xxx-spring-boot-starter`。
- **易错点**：只说「写个 `@Configuration` 就行」而漏掉 ③ 的清单文件登记 ——
  这是最容易被追问倒的地方，必须强调**没有清单文件就不叫自动配置**。
- **与 408 的关联**：配置优先级是**有序表的查找**（命中即返回，
  等价于按优先级排序后的线性探测）；profile 的启用/禁用是**集合运算**（交集/差集）。
  这两个都可以在 408 的「查找」与「集合」章节里找到对应模型。
