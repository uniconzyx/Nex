# 01 · 现代 CMake：target-centric 与 usage requirements 传播

CMake 本身不做编译，它是**构建系统生成器**（Makefile / Ninja / VS 工程）。
因此你在 CMakeLists 里写的每一行，最终都要落成「某个目标用什么命令、带什么 flag、按什么顺序」。
理解这一点，就能理解为什么现代 CMake 把表达方式从「变量」改成了「目标属性」。

## 一、从「目录级变量」到「目标级属性」：现代 CMake 的分水岭

**目录级命令**（旧式，directory-scope）：`include_directories()`、`link_directories()`、
`link_libraries()`、`add_definitions()`、`set(CMAKE_CXX_FLAGS ...)`、`set(CMAKE_CXX_STANDARD 17)`。
它们修改的是**当前目录作用域及其子目录**的变量，凡在此目录里定义的目标都被统一施加，
与「这个目标到底依赖谁」毫无关系。

**目标级命令**（现代，target-centric）：`target_include_directories()`、
`target_compile_definitions()`、`target_compile_options()`、`target_compile_features()`、
`target_link_libraries()`、`target_sources()`。它们把信息绑在**具体 target** 上。

本章 ex09 把这套取舍固化成了 10 条规则库（CM001–CM010），对正反两组 CMakeLists 做静态检查：
正例（target-centric 写法）0 问题，反例（目录级 + 缺关键字 + 全局 flag）9 问题，两组可区分。
ex07 则给出了一份可直接落地的现代 CMakeLists：核心库 `core`、头文件库 `log`、可执行文件 `app` 三层结构。

### 🧑‍💻 程序员视角
- **决策顺序**：先问「这个信息是给谁用的」→ 只给自己（`PRIVATE`）、自己和使用者都要（`PUBLIC`）、
  只给使用者（`INTERFACE`）；只有全局性的东西（`cmake_minimum_required`、`project`、
  `enable_testing()`）才放在文件顶部。
- **上线事故形态**：`set(CMAKE_CXX_STANDARD 17)` 写在顶层，结果 `FetchContent` 拉进来的第三方库
  被强制按 C++17 编译，自身要求的 C++20 特性全部报错——**你的配置污染了别人的代码**。
  这类问题在本地往往不复现，只在 CI 的干净容器里出现。
- **性能取舍**：目录级 include 会让每个目标都带上全部 `-I`，编译器的头文件搜索路径变长，
  更糟的是「谁都能 include 谁」，模块边界在物理上消失，重构时无法按目标拆分编译。
- **排查顺序**：`cmake --trace-expand` 看变量到底被谁改过；`cmake --graphviz=g.dot` 出依赖图；
  对目标属性用 `cmake --build . --target help` 之外的 `get_target_property()` 打印确认。

### 🎓 博士生视角
- **第一性原理**：构建描述本质是一个**有向图上的属性标注问题**。节点是 target，边是依赖关系。
  目录级命令把属性标在「目录」这个与依赖图无关的中间层上，所以它会**沿目录树而非依赖边传播**，
  这就是泄漏的形式化来源。target-centric 把属性标在节点上、传播沿边走，语义才闭合。
- **历史演进**：CMake 2.8 时代只有目录级命令；3.0（2014）引入 usage requirements 与
  `target_compile_features`，3.13 之后 `target_link_directories`、`target_link_options` 补齐，
  3.14+ `install(EXPORT)` 与 `FetchContent` 成熟。**目录级命令从未被移除**，只是不再推荐——
  这也是存量工程里两套写法混杂的根源。
- **生成器语义**：`target_compile_features(core PUBLIC cxx_std_17)` 不是「加 `-std=c++17`」，
  而是声明「我需要具备 C++17 的编译能力」，由 CMake 按编译器决定是 `-std=c++17`、
  `/std:c++17` 还是什么都不加（编译器默认已满足）。这是**需求声明**与**实现手段**的解耦。

### 📚 考研者视角
- **408/笔试关联**：CMake/Make 本身不在 408 考纲内，但与之直接相关的**「编译与链接」是操作系统
  与组成原理的常考点**：预处理 → 编译 → 汇编 → 链接四阶段；静态链接、装入时动态链接、
  运行时动态链接的区别；可重定位目标文件、符号表、重定位表的作用。
- **标准问法**：「`#include` 的头文件去哪里找」（`-I` 搜索路径 → 对应 `target_include_directories`）、
  「库文件去哪里找」（`-L` + `-l` → 对应 `target_link_libraries`）、
  「为什么改了头文件要重新编译」（依赖图失效 → 对应 target 的依赖边）。
- **易混对比**：`CMAKE_CURRENT_SOURCE_DIR`（当前 CMakeLists 所在目录，**可重定位，正确**）
  vs `CMAKE_SOURCE_DIR`（顶层源目录，写进 install 导出后就失效）——这是 ex09 的 CM008。
  另：`add_subdirectory` 建的是**目录树**，`target_link_libraries` 建的是**依赖图**，二者不是一回事。

## 二、`PUBLIC` / `PRIVATE` / `INTERFACE`：使用要求的三种传播强度

CMake 把「使用一个目标所需的一切」称为 **usage requirements（使用要求）**，
主要落在 `INTERFACE_INCLUDE_DIRECTORIES`、`INTERFACE_COMPILE_DEFINITIONS`、
`INTERFACE_COMPILE_FEATURES`、`INTERFACE_LINK_LIBRARIES` 这四类 `INTERFACE_*` 属性上。

三个关键字决定一条依赖边要不要把使用要求传下去：

| 关键字 | 自己编译时可见 | 传给消费者 | 典型场景 |
|---|---|---|---|
| `PRIVATE` | ✅ | ❌ | 只在 `.cpp` 里用的实现头、只在本目标生效的 `-Werror` |
| `PUBLIC` | ✅ | ✅ | 出现在自己公开头文件里的依赖（下游也要能 include） |
| `INTERFACE` | ❌ | ✅ | 头文件库（header-only），自己没有编译单元 |

ex10 用求解器把这套语义算了一遍：**图 A**（`math` 以 `PUBLIC` 链接 `core`）中
`math` 的 `INTERFACE_INCLUDE_DIRECTORIES` 含 `core/include`，`app` 编译期可见 `core/include`；
**图 B**（`math` 以 `PRIVATE` 链接 `core`）中该集合为空，`app` 若直接 include `core` 的头必然编译失败。

### 🧑‍💻 程序员视角
- **决策树**：打开自己的公开头文件看一眼——里面 `#include` 了谁的头文件？那个依赖就是 `PUBLIC`。
  只在 `.cpp` 里出现的一律 `PRIVATE`。没有任何 `.cpp`、纯头文件的目标用 `INTERFACE`。
- **真实故障**：漏写 `PUBLIC` 的症状是下游报 `fatal error: xxx.h: No such file or directory`，
  而且往往是「编译 `app` 时才报」，容易误判为路径写错，实际是传播断了。
  反向错误（滥用 `PUBLIC`）更隐蔽：编译时间随模块数平方级增长，且最终二进制把不需要的库也链了进去。
- **与头文件可见性联动**：ex15 的检查器把这条规则机器化了——跨目标包含他人 `PRIVATE` 头即判
  `HS001` 违规；包含不属于任何目标的头判 `HS002`（多半是漏声明依赖）。把它接进 CI 就能防回归。
- **排查手法**：`cmake --graphviz` 看边，配合 `get_target_property(t core INTERFACE_INCLUDE_DIRECTORIES)`
  打印实际传播结果，比读 CMakeLists 猜快得多。

### 🎓 博士生视角
- **形式化**：设目标集合 $T$，依赖边 $E \subseteq T \times T$ 带标签 $\ell(e) \in \{PUBLIC, PRIVATE, INTERFACE\}$。
  一个目标 $t$ 的**自用属性** $U(t)$ = 自身声明；**导出属性** $I(t)$（即 `INTERFACE_*`）=
  $\bigcup_{(t \to d),\, \ell \in \{PUBLIC, INTERFACE\}} (U(d) \cup I(d))$。
  由于 $I(t)$ 依赖 $I(d)$，这是**依赖图上的传递闭包**，CMake 在生成阶段按拓扑序迭代到不动点。
- **复杂度与环**：闭包是 $O(V + E)$ 量级（按拓扑序单次扫描即可）。若依赖图有环，迭代不会自然终止，
  因此 CMake 对**静态库循环依赖**做了特判（允许环，由链接器用 `--start-group/--end-group`
  反复扫描解决符号），但对 `INTERFACE` 属性环会报错——这与链接器处理符号解析的方式一脉相承。
- **设计动机**：为什么必须要有 `INTERFACE` 这一档？因为**头文件库没有编译单元**，它的全部价值
  （include 路径、宏、要求的 C++ 标准）都是「给消费者用的」。ex07 的 `log` 目标就是典型：
  `add_library(log INTERFACE)` + `target_compile_definitions(log INTERFACE LOG_LEVEL_DEFAULT=2)`，
  自己不产生任何 `.o`。

### 📚 考研者视角
- **408 对接口**：`PUBLIC/PRIVATE/INTERFACE` 的语义与操作系统「**静态链接 vs 动态链接**」的考点同源：
  静态链接在**装入前**把库代码并进可执行文件（类比 `PUBLIC` 把依赖一并交给消费者），
  运行时动态链接把解析推迟到执行期（类比 `PRIVATE`，消费者根本看不到这层依赖）。
- **软件工程考点**：这正是**模块耦合度**的判定——`PUBLIC` 暴露依赖 = 提高耦合，
  `PRIVATE` 隐藏依赖 = 降低耦合（内容耦合 < 公共耦合 < 控制耦合 < 数据耦合，越低越好）。
  面试写法：用 `PRIVATE` 隐藏实现依赖，是「信息隐藏」原则在构建层的落实。
- **易混点**：`PRIVATE` **不等于** C++ 的 `private` 成员——它只是「不导出使用要求」，
  符号本身照常进入静态库、照常被链接器看到；另外 `INTERFACE` 库 `add_library(x INTERFACE)`
  不生成任何二进制产物，它不是「空库」。

## 三、依赖获取与可重定位：`find_package` vs `FetchContent`，`install(EXPORT)`

拿到第三方依赖有两条路：
- **`find_package(fmt 10 REQUIRED)`**：在环境中找**已安装**的包，拿到导入目标 `fmt::fmt`。
  快、可复现、能用系统包管理器统一升级；缺点是环境必须先准备好，CI 镜像要预装。
- **`FetchContent_Declare` + `FetchContent_MakeAvailable`**：配置期把源码拉下来，
  作为本工程的一部分一起编译。**零环境依赖**、版本由 `GIT_TAG` 锁死；
  缺点是拖慢首次配置、把第三方代码纳入你的编译选项作用域（所以更要避免全局 flag）。

写完之后用 `install(TARGETS ... EXPORT ...)` + `install(EXPORT ...)` 导出目标，
别的工程才能 `find_package(cppmind_demo)` 直接复用你——**这才是 target-centric 的最终收益**：
一个目标连同它的使用要求被整体交付。

### 🧑‍💻 程序员视角
- **取舍判据**：依赖是「系统级、多项目共享、体积大」（如 OpenSSL、Boost）→ 优先 `find_package`；
  是「头文件库、版本敏感、项目专属」（如 nlohmann/json）→ 优先 `FetchContent` 并锁死 tag。
- **CI 提速**：`FetchContent` 配合缓存目录 `build/_deps`（ex08 把 `~/.cache/ccache` 与 `build/_deps`
  一起缓存），二次流水线可省掉整段下载与编译。
- **上线事故**：`FetchContent` 用了分支名而非 tag（`GIT_TAG master`），上游一次 force push
  就让你的 CI 红掉且无法复现历史构建。**必须锁到 tag 或 commit SHA**。
- **验证导出是否真的可用**：单独建一个空工程 `find_package(cppmind_demo)` 试一次，
  只在源目录里 `add_subdirectory` 自测是测不出路径问题的。

### 🎓 博士生视角
- **可重定位（relocatable）的本质**：导出文件里记录的路径必须是**相对于导入者**的，
  因此任何 `${CMAKE_SOURCE_DIR}` 拼出来的绝对路径都会在导出后失效（ex09 的 CM008）。
  CMake 用 `$<INSTALL_INTERFACE:...>` / `$<BUILD_INTERFACE:...>` 生成器表达式来区分
  「构建树里怎么看」和「安装树里怎么看」这两个不同的视角。
- **生成器表达式**：`$<...>` 是**求值延迟到生成阶段**的字符串，因为有些信息（配置名、
  安装前缀、目标文件位置）在配置期还不存在。它是 CMake 表达「同一份描述、多种构建配置」的机制。
- **版本与 ABI**：`find_package(fmt 10 REQUIRED)` 里的版本号只是**兼容性声明**，
  真正保证 ABI 一致要靠编译选项、C++ 标准、编译器三者统一——这也是为什么
  `target_compile_features(core PUBLIC cxx_std_17)` 必须 `PUBLIC`：让消费者和自己用同一档标准。

### 📚 考研者视角
- **笔试/面试考点**：「动态链接库与静态链接库的优缺点」是 408 操作系统高频简答——
  静态库：装入后无外部依赖、装载快，但磁盘/内存冗余、更新要重新链接；
  动态库：多进程共享、更新不用重链，但有「DLL Hell」式的版本依赖问题。
  这正好对应 `find_package`（共享、版本敏感）与 `FetchContent`（源码级内嵌、无外部依赖）的取舍。
- **常考计算口径**：若题目给「n 个可执行文件，每个都静态链接同一个大小为 S 的库」，
  磁盘总量按 $n \times S$ 算；动态链接则只算 $S$ 一份（内存还要看是否共享只读段）。
- **易混**：`find_package` 找到的是**已安装**的包，`FetchContent` 拿到的是**源码**；
  前者生成导入目标（`IMPORTED`），后者生成普通目标——只有普通目标会被你的全局设置污染。

---

## 三视角小结

| 主题 | 程序员视角 | 博士生视角 | 考研者视角 |
|---|---|---|---|
| 目录级 → 目标级 | 泄漏与污染的排查顺序 | 属性标注在目录树 vs 依赖图上 | 编译四阶段、-I/-L 搜索路径 |
| PUBLIC/PRIVATE/INTERFACE | 决策树与漏写后果 | 依赖图传递闭包与环处理 | 静态/动态链接、模块耦合度 |
| 依赖获取与导出 | find_package vs FetchContent 取舍 | 生成器表达式与可重定位 | 静/动态库优缺点与冗余计算 |
