# 03 · C++20 ranges：惰性求值与可组合管道

## 一、理论根基：从「立即执行」到「惰性视图」

C++98–17 的传统算法（如 `std::transform` / `std::copy_if`）是 **eager（立即执行）** 的：必须先把结果写进一个**已分配好的容器**里，再喂给下一个算法——于是产生大量中间 `vector` 与拷贝。`<ranges>`（基于 Eric Niebler 的 range-v3，见 manifest 资源）把**视图（view）**引入标准：视图是**对底层数据的轻量、非拥有、可组合的包装**，只在被消费时才真正计算每个元素。

> 设计哲学：**管道 `|` 不是「传输数据」，而是「描述一段计算」**。 composition 在编译期完成，运行时每个元素「流过」整条管道一次（pull 模型）。

## 二、实现机制：惰性如何发生

`std::views::filter` 返回的是一个 **`filter_view`**，它内部只存「底层区间 + 谓词」。当你写：

```cpp
for (int y : v | views::filter(even) | views::transform(sq) | views::take(3)) { ... }
```

迭代器自增时会**在 filter_view 内部反复 `++` 直到谓词为真**，transform_view 再对通过的元素套函数，take_view 数到第 3 个就停止。整个过程：
- **不分配任何中间容器**（零堆分配）；
- **只计算被需要的元素**——`examples/ex08` 里「找第一个 3 的倍数」只访问了源的前 3 个元素就停止，而不是先过滤出全部再取第一个。

这正是 **惰性（laziness）** 的实证：与传统「先 `filter` 生成整段、再 `take`」相比，复杂度的常数与内存都大幅占优。

### 与 Python / Java Stream 的对比

| 维度 | C++20 ranges | Python 生成器 | Java Stream |
|---|---|---|---|
| 惰性 | ✅ view 惰性 | ✅ 生成器惰性 | ✅ Stream 惰性 |
| 中间容器 | 无 | 无 | 无 |
| 组合语法 | `a | b | c` 管道 | 嵌套 `map(f, filter(p, xs))` | `xs.stream().filter(p).map(f)` |
| 并行 | `views::parallel`(实验) / 另行调度 | `multiprocessing` | `.parallel()` 一行 |
| 短路 | ✅ take 提前终止 | ✅ `islice` / `next` | ✅ `limit` / `findFirst` |

> 关键区别：Python 的惰性靠运行时生成器对象、Java 靠 Stream 管线；C++ ranges 的惰性**完全在编译期展开成嵌套迭代器适配器**，运行时没有 lambda 闭包的分发开销——既惰性又零开销，这是 C++ 的独门优势。

## 三、工程实践：程序员视角的取舍

- **`views::filter` 后元素仍是引用语义**，注意别让 view 生命周期超过底层容器（view 不拥有数据，悬空 view 解引用是 UB）。
- **`views::transform` 返回的是只读视图**；要落盘就配 `ranges::copy` 到容器，或用 C++23 `ranges::to<vector>()`。
- 管道可读性强、易测试；但**调试时看不到中间结果**——需要时先用 `for` 打印分段验证。
- 需要「修改原容器」时仍用传统 `std::transform`（写回 `begin()`），ranges view 默认不写回。

## 四、边界与陷阱

- **view 悬空**：`auto r = getVec() | views::filter(...)` 若 `getVec()` 返回临时对象，view 立刻悬空（C++23 用 `views::all` + 生命周期管理规避）。
- `views::reverse` 需要双向迭代器；对 `istream` 这类输入迭代器不可用。
- `views::take` 不会修改源，只是「截断视图」。

## 五、可运行示例

见 `examples/ex08`：惰性管道 `filter(even) | transform(sq) | take(3)`，并用计数器实证「只访问了必要元素」——证明惰性求值。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **`views` 是惰性的**：`v | views::filter(...) | views::transform(...)` 不会立刻计算，只在遍历（如 `for` 或 `ranges::to`）时才逐个产出——省内存，但要注意**底层容器生命周期**（view 不拥有数据）。
- `views` 可以组合成管道，可读性远胜嵌套算法调用；需要物化时用 `ranges::to<vector>()`（C++23）或手动拷贝。
- 编译期报错更友好：`ranges` 用 `concept` 约束，错误信息直指「不满足哪个概念」。

### 🎓 博士生视角
- ranges 把**迭代器对**抽象成**范围（range）**，再用 `view` 表达**惰性序列变换**——这是把「函数式管道」引入 C++，且做到**零运行时开销**：view 在编译期展开为手写循环。
- `concept` 取代 SFINAE 让约束成为**类型系统的一等公民**，错误信息从「替换失败」变成「不满足 `sortable`」，这是 C++20 最重要的可诊断性改进。
- 从语义看，`filter`/`transform` 是 **stream/lazy list** 的构造子；与 Python 生成器、Java Stream 同构，但 C++ 版本在编译期完成组合、不产生装箱开销。

### 📚 考研者视角
- 408 不考 ranges，但**「惰性求值」**作为概念可能出现在「算法设计/语言特性」简答中。
- 记忆锚点：**视图不拥有数据、惰性求值适用于「只遍历一遍或需要短路」的场景**；需要多次遍历或随机访问时应物化成容器。
- 与迭代器对比记忆：**迭代器是「位置」，范围是「一段位置」**；ranges 是迭代器抽象的上一层封装。

---
