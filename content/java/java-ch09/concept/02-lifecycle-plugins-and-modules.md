# 02 · 构建生命周期、插件与多模块工程

## 一、三套生命周期：各走各的，互不干扰

Maven 有**三条相互独立**的生命周期，每条由若干 phase 组成：

| 生命周期 | 主要 phase | 作用 |
|---|---|---|
| `clean` | `pre-clean` → `clean` → `post-clean` | 删除 `target/` |
| `default`（构建） | `validate` → `compile` → `test` → `package` → `verify` → `install` → `deploy` | 编译、测试、打包、发布 |
| `site` | `pre-site` → `site` → `post-site` → `site-deploy` | 生成站点文档 |

关键性质：**执行某个 phase 会把该生命周期中它前面的所有 phase 一并执行**。
所以 `mvn install` 必然先跑完 `validate/compile/test/package/verify`——这就是「为什么它顺便帮你测了」的原因。
三条生命周期之间**没有先后依赖**，`mvn clean install` 是两个命令，只是恰好常连用。

## 二、phase 与 goal：绑定关系，不是同一层概念

- **phase** 是生命周期的**阶段**（有序，无实现）。
- **goal** 是**插件提供的执行单元**（有实现），形如 `插件:目标`（`maven-compiler-plugin:compile`）。
- 默认绑定把常用 goal 挂到 phase 上，例如 `compile` phase → `compiler:compile`，
  `test` phase → `surefire:test`，`package` phase → `jar:jar`。
- `mvn 插件:目标` 可**跳过生命周期直接执行 goal**（如 `mvn dependency:tree` 不触发编译）。

**多执行（execution）**：同一个 goal 可以在同一 phase 绑定多次，用 `<id>` 区分，常用于
「一次编译用 Java 8 目标、另一次用 Java 17 目标」这类多版本产物。

## 三、多模块：聚合 ≠ 继承

这是最容易混淆的一对概念：

| | 聚合（Aggregation） | 继承（Inheritance） |
|---|---|---|
| 位置 | 父 POM 的 `<modules>` | 子 POM 的 `<parent>` |
| 方向 | 父 → 子（父知道子） | 子 → 父（子认父） |
| 作用 | **一次构建多个模块** | **复用配置与依赖版本** |
| 是否传递依赖 | 否 | 是（父的 `<dependencies>` 会传给子） |

实践中父 POM 通常**两者兼用**：`<modules>` 列子模块，同时自己被 `<parent>` 引用（或作为
被继承的 `pom` 打包根）。注意 `<modules>` 里的顺序**不决定构建顺序**，
Maven 会按**模块间依赖关系算出拓扑序**（被依赖的先构建）。

## 四、profile 与资源过滤：一套代码多套环境

```xml
<profiles>
  <profile>
    <id>prod</id>
    <activation><property><name>env</name><value>prod</value></property></activation>
    <properties><db.url>jdbc:mysql://prod-db:3306/app</db.url></properties>
  </profile>
</profiles>
```

配合 `src/main/resources/application.properties` 里的 `${db.url}` 占位与
`<resource><filtering>true</filtering></resource>`，就能在打包时把属性替换进配置。
**坑**：`filtering` 会把资源文件里所有 `${...}` 都尝试替换，若资源本身含 `${}` 语法
（如前端模板、`logback.xml` 的 `${LOG_HOME}`）就会被误替换——必须用 `<nonFilteredFileExtensions>` 排除。

## 五、打包：普通 jar 与 fat jar

- `maven-jar-plugin`：普通 jar，**不含依赖**，运行时需要 `java -cp "app.jar:lib/*"`。
- `maven-shade-plugin`：把依赖**解包后重新打进一个 jar**（uber jar），会做包重定位（relocation）以避免冲突。
- `spring-boot-maven-plugin:repackage`：保留依赖为**嵌套 jar**（`BOOT-INF/lib/`），
  由 `JarLauncher` 自定义类加载器加载，这是 Spring Boot 可执行 jar 的实现方式。

## 六、可运行代码：模拟生命周期与多模块构建顺序

```java
// 按 phase 全序执行绑定的 goal；多模块按依赖拓扑序构建
// 详见 examples/ex05-lifecycle-execution.json、examples/ex06-multi-module-order.json
```

## 三视角解析

### 🧑‍💻 程序员视角
### 🎓 博士生视角
### 📚 考研者视角

### 🧑‍💻 程序员视角
日常最常用的其实只有五条命令：`mvn -v`（看 JDK/Maven 版本，排查「环境不对」）、
`mvn clean package -DskipTests`（快速打包）、`mvn dependency:tree`（查冲突）、
`mvn -pl 模块 -am 目标`（只构建某模块及其**依赖**，多模块开发的高频操作）、
`mvn help:effective-pom`（看**合并后**的真实 POM，排查「父 POM 传了什么下来」）。
CI 里务必加 `-B`（批处理，去掉交互与彩色）和 `-U`（强制更新 SNAPSHOT）。
另一个高频坑：**`mvn test` 不重新编译资源变更时**要 `mvn clean`；增量失效判断失误导致的
「本地能跑、CI 挂」多半就出在这里。

### 🎓 博士生视角
生命周期可以形式化为三元组 `(P, ≺, bind)`：`P` 是 phase 的有限集合，`≺` 是**全序**（线性），
`bind: P → P(Goal)` 把每个 phase 映射到一个 goal 集合。执行 `mvn p` 即对
`{q | q ≺ p} ∪ {p}` 按序展开 `bind` 并逐个执行——**顺序确定、无分支**，这是 Maven
「构建可重现」的结构性保证。相对地，Gradle 把构建建模为 **DAG**，执行是对 DAG 的拓扑排序，
因此天然支持任务级增量与并行（代价是顺序不再由框架唯一确定，需要用户保证幂等）。
多模块构建顺序则是**模块依赖图的拓扑排序**；当出现环时会报
`The projects in the reactor contain a cyclic reference`——说明依赖图必须保持 **DAG**，
这也是「上层可以依赖下层、下层绝不能反向依赖上层」这条分层纪律在构建层面的体现。
`filtering` 的语义是**文本层的一次全量替换**，因此它**不是幂等的**：
对已含 `${}` 的资源重复过滤会二次替换，这解释了为什么要显式排除这类文件。

### 📚 考研者视角
固定口径，逐字记住：
- **default 生命周期主要 phase 顺序**：`validate → compile → test → package → verify → install → deploy`
  （考试常给一串让你排序，或问「`mvn package` 会执行哪些」→ 答：从 `validate` 到 `package` 全部）。
- **`install` vs `deploy`**：`install` 装到**本地仓库**（`~/.m2`），`deploy` 发布到**远程仓库**（私服/中央）。
- **三条生命周期相互独立**，`clean` 不属于 default。
- **phase 是阶段、goal 是任务，二者是「绑定」关系**——常考辨析题。
- **聚合 vs 继承**：`<modules>` 是聚合（为了**一次构建多个**），`<parent>` 是继承（为了**复用配置**）；
  两者可同时存在但语义不同，这是高频判断题。
- **`~/.m2/settings.xml`** 装私服镜像与凭证，**项目里不放**（凭证不进版本库）。
- **`SNAPSHOT` 会在每次构建重新解析**，而 release 版本一旦进本地仓库就不再重复下载。
