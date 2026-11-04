# -*- coding: utf-8 -*-
"""cpp 学科来源笔记 · 第 3 部分（cpp-ch16 ~ cpp-ch20）。"""

NOTES: dict[str, list[str]] = {
    # ---------------- cpp-ch16 并发与多线程 ----------------
    # 仓库序：chenshuo/muduo / taskflow/taskflow / apache/brpc
    "cpp-ch16": [
        "§2.2 二、实现机制：三种 RAII 锁的差异 · 读 `chenshuo/muduo` 的 "
        "`muduo/base/Mutex.h`：`MutexLockGuard` 只在构造/析构里加解锁；"
        "配套 `muduo/base/Condition.h` 的 `wait()` 内部「解锁 → 等待 → 重新加锁」，"
        "`muduo/net/EventLoop.cc` 则示范 one loop per thread——"
        "三处合起来就是本章 §4.2「实现机制：wait 的三件事」的完整实现；"
        "注意 `wait` 必须传加锁的 guard，否则「检查条件」与「进入等待」之间存在丢唤醒窗口",

        "§5.3 三、线程池：为什么必要 · 读 `taskflow/taskflow` 的 "
        "`taskflow/core/executor.hpp`：`Executor` 预先起 `_config.num_workers` 个线程，"
        "每个 worker 在自己的 `_wsq`（work-stealing queue）上取任务，空闲时从别人队尾偷；"
        "读 `_wait_for_task` 与 `_steal` 两个函数，就懂「任务图 + 工作窃取」如何避免线程空转——"
        "这正是本章 §5.1「高层并发抽象」里说的「比裸线程多出来的那一层价值」",

        "§5.1 一、理论根基：高层并发抽象 · 读 `apache/brpc` 的 `src/bthread/bthread.h`："
        "`src/bthread/` 用 M:N 调度（大量 bthread 跑在少量 pthread 上），"
        "把「阻塞等待」换成用户态挂起；"
        "对照 `std::thread` 的 1:1 模型，能看清本章说的"
        "「线程池解决的是创建成本，协程解决的是调度成本」——"
        "两者叠加才是 §5.2「async 的启动策略」要权衡的全貌",
    ],

    # ---------------- cpp-ch17 元编程与类型萃取 ----------------
    # 仓库序：microsoft/STL / fmtlib/fmt / abseil/abseil-cpp
    "cpp-ch17": [
        "§1.3 三、is_destructible 与「类型是否可销毁」 · 读 `microsoft/STL` 的 "
        "`stl/inc/type_traits`：`is_destructible` 靠 `declval<T>().~T()` 的 SFINAE 探测，"
        "`conjunction`/`disjunction` 用短路继承避免多余实例化；"
        "把这几处读完，`<type_traits>` 就不再是「查表用的魔法」——"
        "本章 §1.2「模板特化与偏特化」讲的机制，在这里就是两行 `true_type`/`false_type` 分支",

        "§3.2 二、C++20 concept：可读的约束 · 读 `include/fmt/base.h` 里 "
        "`is_formattable`：它同时有 C++20 concept 版（`requires` 表达式）与旧编译器的 SFINAE 版，"
        "两份实现并列；对照它们能看清 concept 把「替换失败」从错误信息里救出来这件事有多实际——"
        "SFINAE 版报错指向模板定义处，concept 版直接说「T 不满足 formattable」",

        "§3.1 一、SFINAE：替换失败不是错误 · 读 `abseil/abseil-cpp` 的 "
        "`absl/meta/type_traits.h`：`absl::void_t`、`type_identity`、`is_comparable` "
        "都是为「检测某操作是否合法」准备的积木；"
        "读 `is_comparable` 的 `decltype` 表达式，是本章 SFINAE 一节最干净的例题——"
        "它同时检测 `a == b` 与 `a != b` 两侧，缺一个就整体失败，"
        "而本章 §3.3「requires 表达式与约束组合」用 `requires requires` 能写成两条并列约束",
    ],

    # ---------------- cpp-ch18 性能与底层 ----------------
    # 仓库序：simdjson/simdjson / google/benchmark / ClickHouse/ClickHouse
    "cpp-ch18": [
        "§1.2 二、显式对齐与协议布局：alignas / #pragma pack / 干扰尺寸 · 读 "
        "`simdjson/simdjson` 的 `src/generic/stage1/json_structural_indexer.h`："
        "每次吃 64 字节块，用 `SIMDJSON_ALIGNED` 保证输入指针对齐到 64 字节边界"
        "（否则 AVX2 加载会慢甚至崩）；"
        "这是「对齐不是学究问题，是 SIMD 的硬要求」的第一手证据——"
        "本章 §1.1「对齐规则与填充」讲的是编译器自动做的事，"
        "这里讲的是「编译器不肯做、只能手写」的那部分",

        "§3.2 二、链表 vs 数组，指针追逐与 std::vector 的连续性 · 配 "
        "`google/benchmark` 的 `include/benchmark/benchmark.h`："
        "`DoNotOptimize` 阻止编译器把结果删掉、`ClobberMemory` 强制刷新内存可见性；"
        "本章讲「链表 vs 数组」时，没有这两个工具测出来的数字基本不可信——"
        "编译器会把整个循环优化掉，而 §3.1「AoS vs SoA」的对比同样需要它们才有意义",

        "§3.1 一、AoS vs SoA，行优先 vs 列优先 · 读 `ClickHouse/ClickHouse` 的 "
        "`src/Columns/ColumnVector.cpp`：每个数值列就是一条连续 `PODArray`，"
        "`src/Common/PODArray.h` 负责带 padding 的增长；"
        "读 `ColumnVector::getData()` 直接返回裸指针——"
        "因为列存的前提就是「同类型紧挨着」，这正是本章要论证的局部性收益；"
        "配合 §4.1「内联、条件提示与去虚化」看，列存的另一好处是"
        "「按列处理的算子可以整段内联」，而 AoS 每行都要跨字段取址",
    ],

    # ---------------- cpp-ch19 工程化与测试 ----------------
    # 仓库序：google/googletest / catchorg/Catch2 / cpp-best-practices/gui_starter_template
    "cpp-ch19": [
        "§2.1 一、测试框架的最小内核与退出码语义 · 读 `google/googletest` 的 "
        "`googletest/src/gtest.cc`：`RUN_ALL_TESTS` → `UnitTest::Run` → "
        "逐个 `TestInfo::Run`，最后把失败数折成进程退出码；"
        "看清「退出码即结论」这条链，CI 里的 `ctest` 才知道该不该红——"
        "本章 §2.2「用例设计：等价类、边界值、参数化与夹具隔离」都在这个外壳之内，"
        "外壳不成立，用例写得再好也无法被 CI 判读",

        "§1.2 二、`PUBLIC` / `PRIVATE` / `INTERFACE`：使用要求的三种传播强度 · 读 "
        "`catchorg/Catch2` 的 `src/catch2/catch_session.cpp`：`Session::run` 返回失败用例数，"
        "`CMakeLists.txt` 里 `catch_discover_tests` 把用例注册成独立测试；"
        "对照 googletest 的「一次跑完」与 Catch2 的「逐用例发现」，"
        "能看出两种框架对 CI 并行粒度的不同假设——"
        "前者只需一个可执行文件，后者要求每个用例能被单点触发，"
        "这正是 `INTERFACE`（头文件依赖向上传递）在测试目标上的典型用法",

        "§4.1 一、workflow 的结构与 DAG：`needs` 决定一切 · 读 "
        "`cpp-best-practices/gui_starter_template`：根 `CMakeLists.txt` 用 target-based 写法，"
        "`cmake/` 放自写模块，`.github/workflows/` 里是完整的矩阵构建 + 缓存 + artifact；"
        "把它当作本章的参考实现逐条对照——"
        "这是少数把「现代 CMake + 测试 + CI」串成一条线的小型仓库；"
        "注意它的 `needs` 图与 §3.3「运行期防线：sanitizer 与三层门禁的排布」是对应的："
        "告警 → 静态分析 → sanitizer，越靠后越慢、越只在主干跑",
    ],

    # ---------------- cpp-ch20 综合项目与面试冲刺 ----------------
    # 仓库序：isocpp/CppCoreGuidelines / cpp-best-practices/cppbestpractices /
    #         practical-tutorials/project-based-learning
    "cpp-ch20": [
        "§3.1 一、异常安全等级（Basic / Strong / No-throw） · 读 "
        "`isocpp/CppCoreGuidelines` 的 `CppCoreGuidelines.md`：E.6（RAII 保证）"
        "与 C.vector 相关条款把「Basic / Strong / No-throw」写成了可引用规则；"
        "面试口述前先按编号找到原文，比背二手总结更抗追问——"
        "尤其是「为什么 `vector::push_back` 只给基本保证」这类题，"
        "原文会直接指到「重分配时移动构造若不是 noexcept 就退化为拷贝」",

        "§2.1 一、线程池：任务队列 + 条件变量 + 优雅关闭 · 读 "
        "`cpp-best-practices/cppbestpractices` 的 `README.md`："
        "`chapters/` 目录按主题分章（工具、风格、CMake、测试、CI），"
        "每章末尾给可执行检查项；"
        "拿它给自己的项目做一次体检，能找出「能跑但不能交付」的具体项——"
        "这正是本章在 §3.2「RAII 与所有权」之外要补的工程面",

        "§5.2 二、系统设计题答法 · 读 "
        "`practical-tutorials/project-based-learning` 的 `README.md` 的 C++ 一节："
        "它列了几十个「从零写一个 X」的项目（解释器、渲染器、数据库）；"
        "面试讲项目经历时，从这类项目里挑一个真正做完的，"
        "比堆功能列表更能撑住「你解决过什么真实约束」的追问——"
        "配合本章 §5.1「白板 coding 训练法」看，"
        "系统设计题的答法本质是把 §1「迷你 vector」与 §2「线程池」这类"
        "「你亲手写过的组件」复用成论据",
    ],
}
