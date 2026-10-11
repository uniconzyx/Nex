# 03 · noexcept、断言与契约：把"承诺"写进类型与编译期

## 一、理论根基：noexcept 不是优化提示，而是一份"契约"

`noexcept` 同时出现在**函数声明**和**运算符/类型特性**两个层面，但它的本质是**对调用者的承诺**：

> "我这个函数不会传播异常。如果我内部真的抛了，那是 bug，请直接 `std::terminate` 终止进程，不要试图展开恢复。"

这与"异常安全"是**正交**的两个维度：
- 异常安全问的是"抛了之后状态如何"；
- `noexcept` 问的是"到底会不会抛"——它是一个**布尔契约**，编译器据此做决策。

### noexcept 的两处语义
1. **函数声明**：`void f() noexcept;` 表示 `f` 不抛；`void g() noexcept(false);` 显式标"可能抛"（与无说明的旧式默认不同，见下）。
2. **运算符 `noexcept(expr)`**：编译期布尔值，询问"表达式 `expr` 是否不抛"。标准库大量用它做分支（SFINAE / `if constexpr`）。

### C++17 之后默认约定的变化（重要）
- 默认非 `noexcept` 函数（无说明）**可能抛**，调用它时编译器必须按"可能抛"准备展开。
- 而**隐式生成的特殊成员函数**（默认构造、析构、移动等）在满足条件时**自动成为 `noexcept`**（如 `std::vector<int>::move` 不抛，因为 `int` 移动不抛；但 `std::vector<Throwing>::move` 会抛，故非 noexcept）。这点直接影响容器实现（见下）。

## 二、实现机制：noexcept 如何改变 std::vector 的"移动 vs 拷贝"

这是 `noexcept` **最经典、最该背下来的工程影响**：

> **`std::vector` 在扩容（reallocate）时，需要把旧元素搬到新缓冲。**
> 它优先用**移动构造**（更快、常 O(1)）；但**只有当元素的移动构造是 `noexcept` 时**才敢用移动——否则改用**拷贝构造**。

为什么这么保守？因为扩容是"逐个迁移 N 个元素"：若用移动，迁移到第 k 个时抛异常，旧缓冲已部分搬空、新缓冲未填满，**强保证（要么全成要么全败）无法满足**，且无法回滚。而**拷贝**是"先建新、再弃旧"，中间抛异常旧缓冲仍完整 → 强保证成立。因此：

- 元素 `move` 是 `noexcept` → vector 用**移动**（快，但需 `noexcept` 背书安全性）。
- 元素 `move` 非 `noexcept` → vector 用**拷贝**（慢，但保留强保证）。

**这就是"移动构造函数几乎总是要标 `noexcept`"的根本原因**——你的类若想被标准容器高效搬迁，移动操作必须 `noexcept`。可运行证据见 `examples/ex10-noexcept-vector-move.json`（noexcept move → `copies=0, moves=3`，全程走移动、零拷贝）与 `examples/ex11-noexcept-vector-copy.json`（非 noexcept move → `copies=1, moves=2`，扩容搬移退化为拷贝）。

## 三、实现机制：noexcept 函数的"违约"代价

若 `noexcept` 函数内部还是抛了（包括它调用的函数抛且未捕获），运行时会调用 `std::terminate`——**直接结束进程**，不展开、不运行后续析构。这既是"承诺的强制"，也是把"不可能发生的事"变成"一旦发生了就立刻崩，便于定位"的手段。见 `examples/ex13-noexcept-violation.json`。

> 注意：这与"析构函数抛异常导致 terminate"是同一套机制——标准对"栈展开途中再抛"与"noexcept 违约"都选择 `terminate`，因为此时恢复已不可信。

## 四、断言：assert / static_assert / 契约（contracts）

断言是另一种"契约"，但它处理的是**前条件/不变量**，与异常互补：

### 1. `assert`（运行时，来自 `<cassert>`）
- 宏：**未定义 `NDEBUG`**（通常是 Debug 构建）时，若条件为假则打印文件名/行号并 `abort`；**定义 `NDEBUG`**（Release）时整条语句被**剔除**（零成本，但不检查）。
- 用途：捕捉"本不该发生"的程序员错误（如指针非空、索引合法），**不用于健壮地处理用户/外部输入错误**——那该用异常或错误码。

### 2. `static_assert`（编译期）
- `static_assert(常量布尔表达式, "消息");` 在**编译期**求值，失败则编译错误。
- 用途：约束模板实参（如"T 必须是算术类型"）、检查平台假设（如 `sizeof(int)==4`）、确保对齐。它把"契约"前移到编译期，最快、最省。见 `examples/ex05-static-assert.json`。

### 3. C++20 Contracts（前瞻）
- 原生 `[[pre]]` / `[[post]]` / `[[assert]]` 属性表达前条件/后条件/断言，配合构建配置决定检查强度。虽各编译器支持进度不一，但理念明确：**契约是接口的一部分，应在边界处被校验**。

### 断言 vs 异常：何时用哪个
| 维度 | `assert` | 异常 |
|---|---|---|
| 检查对象 | 程序员错误 / 不变量违背 | 可预期的运行时失败（IO 失败、解析错误） |
| 构建差异 | Release 下被关闭 | 始终生效 |
| 失败后果 | `abort`（开发期快速暴露） | 可被 `catch` 恢复 |
| 典型位置 | 内部不变式、前条件 debug 校验 | 库/系统边界、用户可触发错误 |

## 五、边界与陷阱（详见 pitfalls.md）

- 把 `assert(x != nullptr)` 当成"防空指针"的手段是错的：Release 下它消失，等于没检查。真正要处理的可为空，应显式 `if (!p) throw ...;`。
- `noexcept` 一旦发布就难改：把原本 `noexcept` 的函数改成可能抛，是**破坏性变更**（调用方可能已依赖其不抛）。
- `static_assert(false)` 永远失败；在模板里想"按需失败"要用依赖型表达式（如 `static_assert(depends_on<T>, ...)`）否则**无论是否实例化**都立即报错。

## 六、可运行示例

见：
- `examples/ex04-noexcept-fn.json`：`noexcept` 函数正常调用。
- `examples/ex05-static-assert.json`：编译期约束模板实参为算术类型。
- `examples/ex06-assert-trigger.json`：Debug 下 `assert` 失败触发 `abort`。
- `examples/ex10-noexcept-vector-move.json` / `ex11-noexcept-vector-copy.json`：`noexcept` 决定 vector 移动/拷贝。
- `examples/ex13-noexcept-violation.json`：noexcept 函数内抛 → `std::terminate`。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **移动构造/移动赋值务必标 `noexcept`**：否则 `vector` 扩容时因怕强保证被破坏而**退化为拷贝**，性能断崖式下跌。这是最容易被忽略的实战性能坑。
- `static_assert` 做**编译期契约检查**（如「类型必须是 8 字节」）；`assert` 只在 debug 生效，**绝不能用来做参数校验**（release 下被移除）。
- `noexcept` 一旦承诺就必须守住：内部抛异常会直接 `terminate`，没有回旋余地。

### 🎓 博士生视角
- `noexcept` 是**类型系统的一部分**（`noexcept` 运算符可在编译期查询），因此能参与重载决议与容器策略选择——这是「把承诺编码进类型」的范例。
- 「零开销异常」的另一面是**代码体积与编译期元数据**：异常表随函数数量增长，嵌入式场景常以 `-fno-exceptions` 关闭并使用错误码。
- `static_assert` 与 `assert` 的分野体现**编译期 vs 运行期**两个不同的验证阶段，前者可证伪不可达代码，后者只能覆盖实际执行路径。

### 📚 考研者视角
- 记忆锚点：**`noexcept` 影响 `vector` 扩容走移动还是拷贝**（这条是 C++ 高性能面试的经典题）。
- 对比记忆：**`static_assert` 编译期检查（不适配直接编译失败）vs `assert` 运行期检查（release 被裁掉）**。
- 若考「契约式设计」：可回答**前置/后置条件/不变式**三要素，以及 C++ 用 `assert`/`noexcept`/`[[expects]]`（TS）各自覆盖哪一部分。

---
