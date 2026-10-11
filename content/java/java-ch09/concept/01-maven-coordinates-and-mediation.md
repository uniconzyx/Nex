# 01 · Maven 坐标、依赖调解与冲突排查

## 一、坐标与仓库：一次依赖是怎么被找到的

Maven 用**三元坐标**唯一标识一个构件：

```
groupId:artifactId:version        例：org.springframework.boot:spring-boot-starter-web:3.2.0
```

仓库解析顺序固定为 **本地仓库 → 私服（settings.xml 的 mirror）→ 中央仓库**：

| 层级 | 位置 | 典型用途 |
|---|---|---|
| 本地仓库 | `~/.m2/repository` | 已下载构件，离线可用 |
| 私服（Nexus/Artifactory） | 公司内网 | 缓存加速 + 内部构件托管 + 审计 |
| 中央仓库 | `repo.maven.apache.org` | 公共构件源 |

命中的第一步是**校验**：Maven 会检查 `.pom`、`.jar` 与校验和（`*.sha1`）。若本地已有
`_remote.repositories` 记录但 `.jar` 缺失，会出现经典的
`The POM for X is missing, no dependency information available`——**删掉该目录重下**是最快的修法。

## 二、传递依赖与依赖调解

你在 POM 里写了一个依赖，它自己又依赖别的构件，这叫**传递依赖**。深度不受限，
但版本会冲突。Maven 用两条规则裁决，**顺序不可颠倒**：

1. **最近优先（nearest wins）**：依赖树中**层级更浅**的胜出，与声明顺序无关。
2. **声明优先（first declared wins）**：层级相同时，POM 中**先声明**的胜出。

```
A
├── B:1.0
│   └── C:1.0        <- C 在层级 2
└── C:2.0            <- C 在层级 1  => 胜出（最近优先）
```

`dependency:tree -Dverbose` 会把被裁剪的节点标成 `omitted for duplicate`（同坐标重复）
或 `omitted for conflict with X`（版本冲突），这是排查的第一入口。

**排除传递依赖**：当某条支路带来的版本必须移除时用 `<exclusions>`：

```xml
<dependency>
  <groupId>com.example</groupId>
  <artifactId>lib-a</artifactId>
  <version>1.0</version>
  <exclusions>
    <exclusion><groupId>commons-logging</groupId><artifactId>commons-logging</artifactId></exclusion>
  </exclusions>
</dependency>
```

## 三、dependencyManagement 与 BOM：只声明「版本」，不引入依赖

`<dependencyManagement>` 是一个**版本字典**：它**不会**把依赖加进 classpath，
只负责在子依赖没写 `<version>` 时提供默认版本。

- **BOM（Bill of Materials）**：把一组协调好的版本打成一个只含 `dependencyManagement` 的 POM，
  用 `<scope>import</scope>` 导入。`spring-boot-dependencies` 就是最典型的 BOM。
- 效果：升级框架版本只改一处，避免「A 要 3.2、B 要 3.1」的散乱局面。

## 四、Scope：依赖在各阶段 classpath 的可见性

| scope | 编译 | 测试 | 运行 | 打包进产物 | 典型用例 |
|---|---|---|---|---|---|
| `compile`（默认） | ✓ | ✓ | ✓ | ✓ | 业务库（Jackson、Guava） |
| `provided` | ✓ | ✓ | ✗ | ✗ | `servlet-api`（容器已提供）、Lombok |
| `runtime` | ✗ | ✓ | ✓ | ✓ | JDBC 驱动、SLF4J 实现 |
| `test` | ✗ | ✓ | ✗ | ✗ | JUnit、Mockito |
| `system` | ✓ | ✓ | ✓ | ✗ | 本机路径 jar（**不推荐**） |
| `import` | — | — | — | — | 仅用于 `<dependencyManagement>` 导入 BOM |

最容易错的三个点：
- `provided` 的库**编译能过、上线就 `ClassNotFoundException`**（因为容器/运行环境没给）。
- `test` 的库在 `main` 里引用会**编译失败**。
- `runtime` 的库不能在 `main` 里写 `import`（编译期不可见），只能通过反射/SPI 使用，这正是 JDBC 驱动的工作方式。

## 五、可运行代码：用纯 JDK 实现依赖调解

```java
// 依赖树按「层级」裁决：最近优先；同层则声明在先者胜
static String resolve(List<String[]> edges, List<String> declared) { ... }
// 详见 examples/ex01-dependency-mediation.json
```

## 三视角解析

### 🧑‍💻 程序员视角
### 🎓 博士生视角
### 📚 考研者视角

### 🧑‍💻 程序员视角
拿到 `NoSuchMethodError` / `ClassNotFoundException` 的第一反应不是改代码，而是**先看依赖树**：
`mvn dependency:tree -Dincludes=出问题的坐标`。九成这类线上问题都是**版本被调解掉了**——
你写的 3.2 被另一条浅层支路的 3.1 顶掉。处置优先级：
① 在 `dependencyManagement` 里钉死版本（最稳，全局生效）；
② 在出问题的依赖上 `exclusions` 剪掉坏支路；
③ 实在要强推用「直接声明 + 提到最浅层」。
另外**打包体积**也是工程决策点：`spring-boot-maven-plugin` 打出 fat jar 方便交付，
但会带来「同一个类出现在嵌套 jar 与外层」的排查复杂度；lib 模块则应打普通 jar 供他人依赖，
**不要**给 lib 模块配 `repackage`。

### 🎓 博士生视角
依赖调解本质是**有向图上的一次确定性遍历**：把「构件坐标」当节点、「依赖声明」当带权有向边，
Maven 求的是**每个坐标在「层级优先、同级先声明优先」字典序下的最小元素**——
这是一个偏序的线性化，代价为一次 DFS（O(V+E)），且**不追求全局最优**。
这带来一个形式化后果：调解结果对**声明顺序敏感**，因此「同一份 POM 在不同聚合顺序下产生不同产物」
在理论上是可能的（除非用 `dependencyManagement` 把版本钉成常量，即把偏序退化为全序）。
同理，BOM 的价值在于把「版本选择」从**求解问题**变成**查表问题**，从而让构建具备**可重现性**。
生命周期则是**阶段的全序 + 绑定的函数**：`phase → {goal…}`，`mvn install` 实际是
对全序前缀执行其绑定的全部 goal——这也是「为什么 `mvn test` 会自动先 `compile`」的原因。

### 📚 考研者视角
笔面高频口径，务必分清：
- **依赖调解两条规则**：① 路径最短优先；② 路径长度相同时，**先声明优先**（不是「后者覆盖前者」）。
- **`dependencyManagement` 不引入依赖**，只统一版本；`<dependencies>` 才真正引入。这句是固定考点。
- **`optional=true`** 的依赖**不传递**给下游，需要在用到的模块里自己再声明一次。
- **`SNAPSHOT` 与 `RELEASE`**：SNAPSHOT 每次构建都去仓库拉最新（开发期），release 一旦发布不可变，
  因此**禁止把 SNAPSHOT 带到生产**。
- **scope 记忆口诀**：`compile` 全周期、`provided` 编译测试有但运行时没有、`runtime` 编译没有运行时才有、
  `test` 只在测试。
- **Maven vs Gradle**：Maven 用「约定优于配置 + 固定生命周期」，Gradle 用「DAG 任务 + 增量构建」，
  后者灵活、前者确定性强。
