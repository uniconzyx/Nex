# -*- coding: utf-8 -*-
"""cpp 学科来源笔记 · 第 1 部分（cpp-ch02 / 05 / 06 / 07 / 08 / 09）。"""

NOTES: dict[str, list[str]] = {
    # ---------------- cpp-ch02 函数：声明/定义、重载、默认参数与 lambda ----------------
    # 仓库序：fmtlib/fmt / catchorg/Catch2 / TheAlgorithms/C-Plus-Plus
    "cpp-ch02": [
        "§2.2 二、重载决议的四级阶梯 · 读 `include/fmt/base.h` 里 `format_to` 的十几个重载"
        "（`OutputIt` 版本、`locale` 版本、`memory_buffer` 版本）："
        "参数个数与类型各差一点，编译器凭什么在这么多同名函数里选中这一个——"
        "答案就是本章这四级阶梯（精确匹配 → 提升 → 转换 → 用户定义转换）；"
        "先看 §2.1「重载解决的是什么问题」再看它，才不会把「模板 + 重载」当两件事",

        "§3.1 一、捕获方式与它们的真实含义 · 读 `catchorg/Catch2` 的 "
        "`src/catch2/catch_test_macros.hpp`：`TEST_CASE`/`SECTION` 宏最终展开成「注册一个 lambda」，"
        "`INTERNAL_CATCH_TEST` 里按值捕获比较表达式两侧——"
        "看清它为什么不按引用捕获：section 结束后临时对象已经没了，"
        "这正是本章 §3.3「生命周期：唯一真正危险的地方」在工业代码里的规避方式",

        "§2.3 三、默认参数：调用点的静态填充 · 读 `TheAlgorithms/C-Plus-Plus` 的 "
        "`math/` 与 `sorting/` 下的实现：同一算法常有两个版本——一个只用 `<`，一个多接一个比较器；"
        "对照本章说的「默认参数 vs 重载 vs 模板参数」三种方案，"
        "看真实代码更愿意选哪种：库作者选重载（避免默认参数与虚函数、默认参数在派生类里的重绑定问题），"
        "算法示例选「多接一个比较器」的重载，因为调用点一眼能看出用的是哪种序",
    ],

    # ---------------- cpp-ch05 类与对象 ----------------
    # 仓库序：ssloy/tinyrenderer / nlohmann/json / google/leveldb
    "cpp-ch05": [
        "§3.4 四、工程实践：返回类型与复合赋值的约定 · 读 `ssloy/tinyrenderer` 的 "
        "`geometry.h`：`Vec3` 的 `operator+`/`operator*` 全部返回值（不是引用），"
        "因为 `a+b` 的结果是个临时量；而 `operator+=` 返回 `Vec3&` 以支持链式。"
        "把这两个返回类型并排看，就是本章「复合赋值返回引用、二元运算返回值」的判据；"
        "配合 §3.3「成员函数 vs 非成员函数：对称性判据」，"
        "再看 `Vec3 operator*(float, const Vec3&)` 为什么必须写成非成员",

        "§2.4 四、工程实践：正确的拷贝赋值写法 · 读 `nlohmann/json` 的 "
        "`include/nlohmann/json.hpp` 里 `basic_json`：它显式写了拷贝构造、拷贝赋值、`swap`；"
        "读 `swap` 的实现会发现它交换的是内部 `json_value` union 与指针——"
        "这正是「拷贝赋值用 copy-and-swap 拿到强异常安全」的实例，"
        "对应本章 §2.3「实现机制：拷贝省略与 RVO」之外的另一半："
        "RVO 省掉的是构造，copy-and-swap 保证的是「要么成功要么原样」",

        "§1.2 二、实现机制：对象在内存里到底是什么 · 读 `google/leveldb` 的 "
        "`include/leveldb/env.h` 与同目录的 `slice.h`：`Slice` 只有 `const char* data_` "
        "与 `size_t size_` 两个成员，`sizeof(Slice)` 就是 16 字节且不拥有任何内存；"
        "它把「轻量值类型」做到了极致——按值传参也不亏，因为拷贝的只是这两个字段；"
        "本章 §1.3「工程实践：程序员视角的取舍」里的「值语义 vs 引用语义」判据，"
        "在这两行成员上就有了具体形态",
    ],

    # ---------------- cpp-ch06 继承与多态 ----------------
    # 仓库序：google/googletest / llvm/llvm-project / google/leveldb
    "cpp-ch06": [
        "§2.2 二、实现机制：vtable 与 vptr（核心） · 读 `google/googletest` 的 "
        "`googletest/src/gtest.cc`：`Test::Run()` 是虚函数，"
        "`UnitTestImpl::RunAllTests` 只持有 `TestInfo*`，通过基类指针调用 `Run()`——"
        "派生类 `TestBody()` 的具体实现到运行时才被选中，这就是 vptr 指到派生类 vtable 的结果；"
        "本章 §2.1「理论根基：为什么需要运行期多态」给的是动机，这里给的是「为什么恰好快」",

        "§3.2 二、RTTI：dynamic_cast 与 typeid 的运行时查表 · 读 `llvm/llvm-project` 的 "
        "`llvm/include/llvm/Support/Casting.h`：`classof` + `dyn_cast` 自己实现类型判别，"
        "不依赖 `dynamic_cast`（LLVM 默认关闭 RTTI）。"
        "读 `isa`/`cast`/`dyn_cast` 三件套，就明白「RTTI 只是手段，类型判别可以有更便宜的实现」——"
        "`classof` 基于一个静态的类 ID 字段做整数比较，代价是一次比较而非查表",

        "§3.1 一、纯虚函数与抽象类：接口隔离的契约 · 读 `google/leveldb` 的 "
        "`include/leveldb/env.h`：`class Env` 几乎全是纯虚函数（文件、锁、线程全抽象掉），"
        "实现放在 `util/env_posix.cc` 的 `PosixEnv : public Env`；"
        "整份 leveldb 只通过 `Env*` 访问系统调用——这是「面向接口编程」在 C++ 里的完整闭环，"
        "也是本章 §2.4「override / final：把错误交给编译器」为什么必须开 `override` 的理由："
        "接口一改，所有实现立刻编译不过",
    ],

    # ---------------- cpp-ch07 模板与泛型 ----------------
    # 仓库序：fmtlib/fmt / nlohmann/json / microsoft/STL
    "cpp-ch07": [
        "§2.5 五、工程实践：特化的正确用法与陷阱 · 读 `include/fmt/base.h` 的 "
        "`template <typename T, typename Char> struct formatter`："
        "主模板故意不实现 `format()`，谁要支持格式化就特化谁"
        "（`formatter<std::string>`、`formatter<int>`）；"
        "读主模板那条注释，它写清了「为什么主模板要留空」——"
        "留空让「不支持的类型」在编译期报错，而不是运行期输出垃圾；"
        "这正是本章 §2.3「全特化」与 §2.4「偏特化」的选用判据",

        "§3.3 三、理论根基：SFINAE —— 替换失败并非错误 · 读 `nlohmann/json` 的 "
        "`include/nlohmann/json.hpp`：`is_compatible_type`、`has_to_json`、`has_from_json` "
        "全靠「替换失败不算错」来探测用户类型有没有提供 `to_json`/`from_json`；"
        "顺着 `has_to_json` 的 `decltype` 表达式看，能看清 SFINAE 到底在哪一步生效——"
        "在模板实参替换阶段，而不是在函数体实例化阶段，这就是它和 §3.4「检测是否有某成员」的分界",

        "§3.5 五、concept 的前世今生：SFINAE 的终结者 · 读 `microsoft/STL` 的 "
        "`stl/inc/type_traits` 里 `void_t`、`enable_if`、`conjunction` 的真实实现；"
        "看完再读同目录 `stl/inc/concepts`（C++20 约束），"
        "就能对照出「SFINAE 时代」与「concept 时代」表达同一约束的成本差——"
        "前者要写 `enable_if_t<...>` 挤在返回类型里、报错指向替换点，"
        "后者只写一行 `requires`、报错直接指出违反哪条约束；"
        "本章 §3.6「工程实践与陷阱」里说的「错误信息可读性」就是这么来的",
    ],

    # ---------------- cpp-ch08 STL 容器 ----------------
    # 仓库序：microsoft/STL / redis/redis / TheAlgorithms/C-Plus-Plus
    "cpp-ch08": [
        "§1.2 二、实现机制：amortized 2× 扩容到底发生了什么 · 读 `microsoft/STL` 的 "
        "`stl/inc/vector`：`_Calculate_growth` 做 `max(size + size/2, requested)` 再对齐，"
        "`_Emplace_reallocate` 分配新块、搬移旧元素、释放旧块——三步全在这里；"
        "注意 MSVC 实际取的是 **1.5×**（`size + size/2`）而不是 2×，"
        "对照本章算的摊销 O(1)，能看出倍数只影响常数、不影响均摊结论，"
        "但会影响「旧块能否被后续分配复用」——这正是 §1.3「迭代器/引用/指针的失效规则」的由来",

        "§3.3 三、实现机制：负载因子与再哈希（rehash） · 读 `redis/redis` 的 "
        "`src/dict.c`：`dictExpand` 建两张表，`dictRehash` 每次只搬 `n` 个桶"
        "（渐进式 rehash），查找时两张表都要看；"
        "这是「不一次性搬完以免卡顿」的工程答案，"
        "与 `unordered_map` 的一次性 rehash 形成对照——"
        "标准容器为了满足 §3.2「桶数组 + 链地址法」的迭代器语义只能整体重建，"
        "而 Redis 单线程服务可以接受「两张表短暂并存」",

        "§4.3 三、容器选择决策树（工程实践） · 读 `TheAlgorithms/C-Plus-Plus` 的 "
        "`graph/` 与 `sorting/` 目录：同一个结构常有邻接矩阵版与邻接表版两种实现，"
        "排序也区分「适合 vector」与「只能链表做」的算法；"
        "把本章 §4.1「list / forward_list：节点结构为何缓存不友好」"
        "与 §4.4「内存局部性与缓存友好的量化直觉」的判据拿过来，逐目录验证一遍你的判断——"
        "同一份代码换成链表版，性能差的那部分就是节点指针跳转的代价",
    ],

    # ---------------- cpp-ch09 STL 算法与迭代器 ----------------
    # 仓库序：microsoft/STL / simdjson/simdjson / TheAlgorithms/C-Plus-Plus
    "cpp-ch09": [
        "§2.2 二、实现机制：sort 的 introsort（混合排序） · 读 `microsoft/STL` 的 "
        "`stl/inc/algorithm`：`sort` 调 `_Sort_unchecked`，"
        "内部是「快排分区 → 递归深度超限就转堆排 → 小区间用插排」三段式（introsort）；"
        "找到那个深度阈值常量（MSVC 是 `2 * log2(n)`），"
        "就明白本章说的「最坏 O(n log n) 靠什么兜底」——"
        "深度超限时切堆排，把快排的 O(n²) 最坏情况挡住",

        "§1.1 一、理论根基：迭代器是「算法与容器之间的接口契约」 · 读 "
        "`simdjson/simdjson` 的 `include/simdjson/dom/array.h`："
        "它的 `iterator` 只提供 `operator*`/`operator++`/`operator!=`，"
        "够 `std::distance` 与范围 for 用，却不暴露底层实现；"
        "再看 `ondemand` 版的迭代器语义差异，能体会「迭代器范畴决定算法能用多强」——"
        "本章 §1.2「范畴如何被编译器强制」说的就是这条契约怎么被静态检查出来",

        "§1.2 二、实现机制：范畴如何被编译器强制（concept 之前 vs 之后） · 读 "
        "`TheAlgorithms/C-Plus-Plus` 的 `numeric/` 与 `sorting/`："
        "`std::accumulate`、`std::sort`、`std::reverse` 各自要求输入迭代器 / 随机访问迭代器；"
        "把同一段代码的容器从 `list` 换成 `vector` 再编译，报错信息就是范畴不够用的证据——"
        "C++17 前是 `no matching function` 加几十行模板展开，"
        "C++20 后 concept 会直接说「list 的迭代器不满足 random_access_iterator」，"
        "这就是 §1.5「可运行示例：迭代器范畴差异（编译期可观察）」想让你亲眼看到的差别",
    ],
}
