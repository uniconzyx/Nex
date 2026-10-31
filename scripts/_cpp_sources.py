"""cpp 20 章的章节级来源路线数据。

设计原则（与 clang 的 CLANG_NOTES 一致）：
1. 每章 3 个仓库，尽量不与该章原来的「学科级三件套」重合；
2. 每条读法 = 真实入口文件 + 真实函数/类型 + 「它在本章证明什么」，不写「建议结合本章观看」这类空话；
3. 写 `§x.y` 的，编号必须与 content/cpp/cpp-chNN/concept/*.md 里真实的 `##` 标题对得上；
   cpp-ch01/03/04 的 concept 小节标题是模板骨架（「要点 / 三视角解析」），没有可锚定的知识点，
   所以这三章不写 §，由渲染层如实标成「全章」，绝不假装精确；
4. 全部仓库已用 GitHub API 核验存在并抓到 star（2026-10-28），star 落在 scripts/_link_cache.json。
"""

CPP_REPOS: dict[str, list[str]] = {
    "cpp-ch01": ["TheAlgorithms/C-Plus-Plus", "fmtlib/fmt", "nlohmann/json"],
    "cpp-ch02": ["fmtlib/fmt", "catchorg/Catch2", "TheAlgorithms/C-Plus-Plus"],
    "cpp-ch03": ["nlohmann/json", "fmtlib/fmt", "Tencent/rapidjson"],
    "cpp-ch04": ["google/leveldb", "DaveGamble/cJSON", "redis/redis"],
    "cpp-ch05": ["ssloy/tinyrenderer", "nlohmann/json", "google/leveldb"],
    "cpp-ch06": ["google/googletest", "llvm/llvm-project", "google/leveldb"],
    "cpp-ch07": ["fmtlib/fmt", "nlohmann/json", "microsoft/STL"],
    "cpp-ch08": ["microsoft/STL", "redis/redis", "TheAlgorithms/C-Plus-Plus"],
    "cpp-ch09": ["microsoft/STL", "simdjson/simdjson", "TheAlgorithms/C-Plus-Plus"],
    "cpp-ch10": ["google/leveldb", "abseil/abseil-cpp", "protocolbuffers/protobuf"],
    "cpp-ch11": ["fmtlib/fmt", "google/googletest", "nlohmann/json"],
    "cpp-ch12": ["AnthonyCalandra/modern-cpp-features", "microsoft/STL", "abseil/abseil-cpp"],
    "cpp-ch13": ["fmtlib/fmt", "Tencent/rapidjson", "nlohmann/json"],
    "cpp-ch14": ["DaveGamble/cJSON", "fmtlib/fmt", "include-what-you-use/include-what-you-use"],
    "cpp-ch15": ["fmtlib/fmt", "abseil/abseil-cpp", "apache/brpc"],
    "cpp-ch16": ["chenshuo/muduo", "taskflow/taskflow", "apache/brpc"],
    "cpp-ch17": ["microsoft/STL", "fmtlib/fmt", "abseil/abseil-cpp"],
    "cpp-ch18": ["simdjson/simdjson", "google/benchmark", "ClickHouse/ClickHouse"],
    "cpp-ch19": ["google/googletest", "catchorg/Catch2", "cpp-best-practices/gui_starter_template"],
    "cpp-ch20": ["isocpp/CppCoreGuidelines", "cpp-best-practices/cppbestpractices",
                 "practical-tutorials/project-based-learning"],
}

# key 形如 "章id|owner/repo"，与 CLANG_NOTES 同一套约定
CPP_NOTES: dict[str, str] = {
    # ── ch01 基础语法：类型、变量与引用 ───────────────────────────────
    "cpp-ch01|TheAlgorithms/C-Plus-Plus":
        r"本章讲「值传参 vs 引用传参」时，先看 `math/greatest_common_divisor.cpp` 与 `math/lcm.cpp`："
        r"参数写成 `int` 还是 `const T&` 不是风格问题——内建类型按值、可能很大的对象按 const 引用，"
        r"这份仓库把两种写法放在同一个目录里，一眼能对照出选择依据",
    "cpp-ch01|fmtlib/fmt":
        r"讲「引用绑定与类型退化」看 `include/fmt/base.h` 的 `type_mapper`（v11 起；v10 及以前在 `core.h`）："
        r"它把 `T`、`const T&`、`T&` 分别映射成同一套呈现方式，这是标准库 `std::decay` 之外最实用的"
        r"「引用到底绑到了什么」的工业样本",
    "cpp-ch01|nlohmann/json":
        r"讲「类型别名与 const 正确性」看 `include/nlohmann/json.hpp` 顶部的 `using string_t = StringType;`、"
        r"`using number_integer_t = ...`：全部用 `using` 而不是 `typedef`，且返回 `const string_t&` 不返回副本，"
        r"正是本章「引用避免拷贝」那一条的落地",

    # ── ch02 函数：声明/定义、重载、默认参数与 lambda ────────────────
    "cpp-ch02|fmtlib/fmt":
        r"§2.1 函数重载的工业规模样本：`include/fmt/base.h` 里 `format_to` 有十几个重载"
        r"（`OutputIt` 版本、`locale` 版本、`memory_buffer` 版本），参数个数与类型各差一点；"
        r"读它们之前先问「编译器凭什么在这么多同名函数里选中这一个」，再回 §2.1 看重载决议的排序规则",
    "cpp-ch02|catchorg/Catch2":
        r"§3.1 捕获方式：`src/catch2/catch_test_macros.hpp` 的 `TEST_CASE`/`SECTION` 宏最终展开成"
        r"「注册一个 lambda」，`INTERNAL_CATCH_TEST` 里按值捕获比较表达式两侧；"
        r"看清它为什么不按引用捕获（section 结束后临时对象已经没了）",
    "cpp-ch02|TheAlgorithms/C-Plus-Plus":
        r"§2.2 默认参数的替代方案：`sort/` 目录里同一算法常有两个版本——一个只用 `<`，"
        r"一个多接一个比较器；对照本章说的「默认参数 vs 重载 vs 模板参数」，看真实代码更愿意选哪种、为什么",

    # ── ch03 数组与字符串 ───────────────────────────────────────────
    "cpp-ch03|nlohmann/json":
        r"本章讲「string_view 式零拷贝」看 `include/nlohmann/json.hpp` 的 `get_ref<const string_t&>()`："
        r"它不复制字符串，直接把内部 `std::string` 以 const 引用交出去；"
        r"再读 `get<std::string>()` 的返回类型，对比「视图」和「拥有」在这一个 API 上的分野",
    "cpp-ch03|fmtlib/fmt":
        r"`include/fmt/core.h`（v11 起并入 `base.h`）里的 `basic_string_view` 是 fmt 自带实现："
        r"只存 `const Char* data_` 与 `size_t size_`，`substr` 返回新视图而非新字符串；"
        r"把它和 `std::string` 的 `substr` 并排看，就明白本章「视图不拥有内存」的代价与收益",
    "cpp-ch03|Tencent/rapidjson":
        r"「视图 vs 拥有」的极端案例：`include/rapidjson/document.h` 的 `kParseInsituFlag` 直接在你的缓冲区上"
        r"把 token 切开（原地写 `\\0`），解析完字符串指针指向原缓冲——省掉全部拷贝，代价是原数据不能再用",

    # ── ch04 指针与内存管理 ────────────────────────────────────────
    "cpp-ch04|google/leveldb":
        r"本章讲「大块预分配 + bump 指针」看 `util/arena.h` 与 `util/arena.cc`："
        r"`Arena::Allocate` 只在当前 4KB 块里移动 `alloc_ptr_`，块用完才 `new char[]`；"
        r"`AllocateAligned` 还会按 `align` 把指针向上取整——这就是本章说的「指针运算 + 手动对齐」",
    "cpp-ch04|DaveGamble/cJSON":
        r"「一 malloc 一 free 配对」的标准形态：`cJSON.c` 的 `cJSON_New_Item` 先 `malloc` 再 `memset` 清零，"
        r"`cJSON_Delete` 递归释放 `child`/`next` 链表；重点看 `cJSON_Parse` 的失败路径——"
        r"每个提前 return 前都先 `cJSON_Delete`，否则就是本书反复警告的那类泄漏",
    "cpp-ch04|redis/redis":
        r"「指针往前挪一格做记账」看 `src/zmalloc.c`：`zmalloc` 多申请 `PREFIX_SIZE` 字节，"
        r"把长度写在返回指针之前，`zmalloc_size` 用 `(size_t*)ptr - 1` 取回；"
        r"这是本章「指针算术 + 内存布局」最直接的工业用法，也解释了 `zmalloc_used_memory` 为什么准",

    # ── ch05 类与对象 ──────────────────────────────────────────────
    "cpp-ch05|ssloy/tinyrenderer":
        r"§3.2 与 §3.4 的活样本：`geometry.h` 里 `Vec3` 的 `operator+`/`operator*` 全部返回**值**（不是引用），"
        r"因为 `a+b` 的结果是个临时量；而 `operator+=` 返回 `Vec3&` 以支持链式。"
        r"把这两个返回类型并排看，就是「复合赋值返回引用、二元运算返回值」的判据",
    "cpp-ch05|nlohmann/json":
        r"§2.2 与 §2.4 对照：`include/nlohmann/json.hpp` 的 `basic_json` 显式写了拷贝构造、拷贝赋值、`swap`；"
        r"读 `swap` 的实现会发现它交换的是内部 `json_value` union 与指针——"
        r"这正是「拷贝赋值用 copy-and-swap 拿到强异常安全」的实例",
    "cpp-ch05|google/leveldb":
        r"§1.2「对象在内存里到底是什么」：`include/leveldb/slice.h` 的 `Slice` 只有 `const char* data_` 与"
        r"`size_t size_` 两个成员，`sizeof(Slice)` 就是 16 字节且不拥有任何内存；"
        r"它把「轻量值类型」做到了极致——按值传参也不亏，因为拷贝的只是这两个字段",

    # ── ch06 继承与多态 ────────────────────────────────────────────
    "cpp-ch06|google/googletest":
        r"§2.2 vtable 与动态绑定：`googletest/src/gtest.cc` 里 `Test::Run()` 是虚函数，"
        r"`UnitTestImpl::RunAllTests` 只持有 `TestInfo*`，通过基类指针调用 `Run()`——"
        r"派生类 `TestBody()` 的具体实现到运行时才被选中，这就是 vptr 指到派生类 vtable 的结果",
    "cpp-ch06|llvm/llvm-project":
        r"§3.2 RTTI 的另一条路：`llvm/include/llvm/Support/Casting.h` 的 `classof` + `dyn_cast` 自己实现类型判别，"
        r"不依赖 `dynamic_cast`（LLVM 默认关闭 RTTI）。读 `isa`/`cast`/`dyn_cast` 三件套，"
        r"就明白「RTTI 只是手段，类型判别可以有更便宜的实现」",
    "cpp-ch06|google/leveldb":
        r"§3.1 接口隔离的标准写法：`include/leveldb/env.h` 的 `class Env` 几乎全是纯虚函数（文件、锁、线程全抽象掉），"
        r"实现放在 `util/env_posix.cc` 的 `PosixEnv : public Env`；"
        r"整份 leveldb 只通过 `Env*` 访问系统调用——这是「面向接口编程」在 C++ 里的完整闭环",

    # ── ch07 模板与泛型 ────────────────────────────────────────────
    "cpp-ch07|fmtlib/fmt":
        r"§2.3 全特化的实战：`include/fmt/base.h` 的 `template <typename T, typename Char> struct formatter` "
        r"主模板故意不实现 `format()`，谁要支持格式化就特化谁（`formatter<std::string>`、`formatter<int>`）；"
        r"读主模板那条注释，它写清了「为什么主模板要留空」",
    "cpp-ch07|nlohmann/json":
        r"§3.3 SFINAE 的工程写法：`include/nlohmann/json.hpp` 里 `is_compatible_type`、`has_to_json`、"
        r"`has_from_json` 全靠「替换失败不算错」来探测用户类型有没有提供 `to_json`/`from_json`；"
        r"顺着 `has_to_json` 的 `decltype` 表达式看，能看清 SFINAE 到底在哪一步生效",
    "cpp-ch07|microsoft/STL":
        r"§3.3 与 §3.5 的底层：`stl/inc/type_traits` 里 `void_t`、`enable_if`、`conjunction` 的真实实现；"
        r"看完再读 `stl/inc/concepts`（若你所看的版本已含 C++20 约束），"
        r"就能对照出「SFINAE 时代」与「concept 时代」表达同一约束的成本差",

    # ── ch08 STL 容器 ─────────────────────────────────────────────
    "cpp-ch08|microsoft/STL":
        r"§1.2 的 2× 扩容：`stl/inc/vector` 的 `_Calculate_growth` 做 `max(size + size/2, requested)` 再对齐，"
        r"`_Emplace_reallocate` 分配新块、搬移旧元素、释放旧块——三步全在这里；"
        r"对照本章算的摊销 O(1)，能看出「1.5× 还是 2×」对重新分配次数的影响",
    "cpp-ch08|redis/redis":
        r"§3.3 负载因子与 rehash：`src/dict.c` 的 `dictExpand` 建两张表，`dictRehash` 每次只搬 `n` 个桶"
        r"（渐进式 rehash），查找时两张表都要看；这是「不一次性搬完以免卡顿」的工程答案，"
        r"与 `unordered_map` 的一次性 rehash 形成对照",
    "cpp-ch08|TheAlgorithms/C-Plus-Plus":
        r"「选容器」的实例库：`data_structures/` 下同一个结构常有数组版与链表版两种实现，"
        r"`sort/` 下也区分「适合 vector」与「只能链表做」的算法；"
        r"把本章的容器选择决策树拿过来，逐目录验证一遍你的判断",

    # ── ch09 STL 算法与迭代器 ─────────────────────────────────────
    "cpp-ch09|microsoft/STL":
        r"§2.2 sort 的真实实现：`stl/inc/algorithm` 的 `sort` 调 `_Sort_unchecked`，"
        r"内部是「快排分区 → 递归深度超限就转堆排 → 小区间用插排」三段式（introsort）；"
        r"找到那个深度阈值常量，就明白本章说的「最坏 O(n log n) 靠什么兜底」",
    "cpp-ch09|simdjson/simdjson":
        r"§1.1「迭代器是算法与容器的契约」：`include/simdjson/dom/array.h` 的 `iterator` 只提供 "
        r"`operator*`/`operator++`/`operator!=`，够 `std::distance` 与范围 for 用，却不暴露底层实现；"
        r"再看 `ondemand` 版的迭代器语义差异，能体会「迭代器范畴决定算法能用多强」",
    "cpp-ch09|TheAlgorithms/C-Plus-Plus":
        r"§1.2 范畴差异的实际后果：`numeric/` 与 `sort/` 里 `std::accumulate`、`std::sort`、`std::reverse` "
        r"各自要求输入迭代器/随机访问迭代器；把同一段代码的容器从 `list` 换成 `vector` 再编译，"
        r"报错信息就是范畴不够用的证据",

    # ── ch10 智能指针与 RAII ──────────────────────────────────────
    "cpp-ch10|google/leveldb":
        r"§1.2「析构调用是编译器插入的」：`db/db_impl.cc` 的 `DBImpl::~DBImpl()` 里显式停后台线程、"
        r"删 memtable、释放文件锁——所有清理都钉在析构里，因此 `DB::Open` 失败时只要 `delete impl` 就干净；"
        r"注意 leveldb 用的是裸指针 + `delete`，正好用来对照「手写 RAII 与 unique_ptr 的等价关系」",
    "cpp-ch10|abseil/abseil-cpp":
        r"§1.2 的通用化：`absl/cleanup/cleanup.h` 的 `absl::Cleanup` 把「析构时执行一段代码」抽成可组合对象，"
        r"`absl/synchronization/mutex.h` 的 `MutexLock` 用它管锁；"
        r"这两处合看，就明白 RAII 不是「智能指针专用技巧」，而是资源管理的通用形态",
    "cpp-ch10|protocolbuffers/protobuf":
        r"§2.2 与 §3.3 的所有权边界：`src/google/protobuf/arena.h` 里 `Arena` 用 `unique_ptr` 管自己的块，"
        r"但 `CreateMessage` 在 arena 上创建的对象由 arena 统一回收（不逐个 delete）；"
        r"这是「所有权不在指针、而在容器」的典型，也解释了自定义删除器为什么要做类型擦除",

    # ── ch11 异常处理与断言 ───────────────────────────────────────
    "cpp-ch11|fmtlib/fmt":
        r"§1.2 栈展开前的最后一站：`include/fmt/base.h` 的 `FMT_THROW` 可被配置成抛异常或直接 abort，"
        r"`FMT_ASSERT` 在 debug 下抛 `format_error`；读这两个宏的分支，"
        r"就看清「库要不要让异常穿过自己」是一个可配置的契约，而不是语言强制",
    "cpp-ch11|google/googletest":
        r"§3.4 断言分级：`googletest/include/gtest/gtest.h` 里 `EXPECT_*` 失败继续跑、`ASSERT_*` 失败立刻 return，"
        r"`EXPECT_THROW`/`EXPECT_NO_THROW` 把「抛不抛」变成可断言的性质，`ASSERT_DEATH` 连崩溃都能测；"
        r"这套 API 是本章「断言与异常各管一段」的现实版",
    "cpp-ch11|nlohmann/json":
        r"§2.1 异常安全契约的开关：`include/nlohmann/json.hpp` 的 `JSON_THROW` 由 `JSON_NOEXCEPTION` 决定展开成"
        r"`throw` 还是 `std::abort`，`parse(..., allow_exceptions=false)` 则让调用方自己查 `is_discarded()`；"
        r"同一个库给出三条错误处理路径，正好对本章的「异常 vs 错误码 vs 终止」取舍",

    # ── ch12 现代 C++ 特性 ───────────────────────────────────────
    "cpp-ch12|AnthonyCalandra/modern-cpp-features":
        r"§2.2 值类别与 §4.1 结构化绑定的对照表：`README.md` 按 C++11/14/17/20 分节，"
        r"每节都有最小可编译示例；建议先读「rvalue references」「structured bindings」两节，"
        r"把本章的术语和标准里的正式名字对上，再回代码里验证",
    "cpp-ch12|microsoft/STL":
        r"§3.3 emplace_back 与 push_back 的差别：`stl/inc/vector` 的 `emplace_back` 直接把参数转发给"
        r"`_Emplace_reallocate` 里的 `construct_at`，全程只构造一次；"
        r"而 `push_back(const T&)` 要先凑出一个 `T` 再移动。看这两条实现路径，"
        r"就明白「构造次数差异」不是玄学而是参数转发位置不同",
    "cpp-ch12|abseil/abseil-cpp":
        r"§2.3 `std::move` 只是一次 cast：`absl/utility/utility.h` 的 `absl::exchange` 与 "
        r"`absl/types/optional.h` 的 `value() &&` 重载都靠 `std::move` 把左值转成右值再转发；"
        r"注意它们转完从不「清空源对象」——移动后的源对象仍是有效但未指定状态，这是本章最常被误解的一条",

    # ── ch13 IO 与格式化 ─────────────────────────────────────────
    "cpp-ch13|fmtlib/fmt":
        r"§4.3 `std::format` 的设计动机：`include/fmt/format.h` 的 `format_to` 把结果直接写进输出迭代器，"
        r"`include/fmt/ostream.h` 则给「只有 `operator<<` 的老类型」搭桥；"
        r"两处合看就知道 `std::format` 为什么比 `stringstream` 快——它不建流对象、不碰 locale",
    "cpp-ch13|Tencent/rapidjson":
        r"§1.3 与 §3.2 的缓冲策略：`include/rapidjson/filereadstream.h` 的 `FileReadStream` 要你自己给一块"
        r"`buffer`（默认 64KB），`FileWriteStream` 同理；"
        r"这解释了本章「stdio 缓冲 vs 流对象」的层次——库不替你藏缓冲，性能就变得可预测",
    "cpp-ch13|nlohmann/json":
        r"§4.4 结构化文本解析：`include/nlohmann/json.hpp` 的 `operator>>` 与 `dump()` 是「流式接口 + 一次性序列化」"
        r"的组合；对比它和 `std::stringstream` 解析同一份 CSV 的代码量，"
        r"能直观看出本章说的「手写分隔符解析为什么容易漏边界」",

    # ── ch14 预处理与宏 ──────────────────────────────────────────
    "cpp-ch14|DaveGamble/cJSON":
        r"§1.2 与 §1.3 头文件守卫的现实版：`cJSON.h` 顶部 `#ifndef cJSON__h` / `#define cJSON__h`，"
        r"`CJSON_PUBLIC` 宏负责导出符号、`CJSON_EXPORT_SYMBOLS` 控制静态/动态；"
        r"整个头文件只有声明——把「头文件该放什么」这件事做到了教科书级",
    "cpp-ch14|fmtlib/fmt":
        r"§2.4 宏与 inline 的取舍：`include/fmt/base.h` 的 `FMT_BEGIN_NAMESPACE`/`FMT_END_NAMESPACE`、"
        r"`FMT_API`、`FMT_INLINE` 三层宏分别管「命名空间版本化、符号可见性、强制内联」；"
        r"看清每个宏存在的理由，就明白为什么现代库仍需要宏——跨编译器差异无法用 C++ 语法表达",
    "cpp-ch14|include-what-you-use/include-what-you-use":
        r"§1.2 的量化工具：`iwyu.cc` 是主分析器，`iwyu_include_picker.cc` 维护「哪个头文件该由谁包含」的映射表；"
        r"拿它跑一遍本章的示例工程，`#include` 的传递闭包会被直接列出——这是「文本包含」语义最硬的证据",

    # ── ch15 命名空间与模块化 ────────────────────────────────────
    "cpp-ch15|fmtlib/fmt":
        r"§3.1 与 §3.2 inline namespace 的工业用法：`include/fmt/base.h` 里 `FMT_BEGIN_NAMESPACE` 展开成"
        r"`namespace fmt { inline namespace v11 {`，于是 `fmt::format` 与 `fmt::v11::format` 是同一个实体；"
        r"库靠它做到「ABI 版本可以换、用户代码不用改」",
    "cpp-ch15|abseil/abseil-cpp":
        r"§3.1 的另一套做法：`absl/base/config.h` 的 `ABSL_NAMESPACE_BEGIN` 展开成 `namespace absl { "
        r"ABSL_INTERNAL_NAMESPACE {`，具体名字由 `absl/base/options.h` 的 LTS 宏决定；"
        r"对照 fmt 与 abseil 两种版本化命名空间，能看清「透明 vs 显式」的取舍",
    "cpp-ch15|apache/brpc":
        r"§1.2 名字查找的实际分层：`src/brpc/server.h` 里 `namespace brpc`，其下再分 `policy`、`detail` 等子命名空间，"
        r"对外只暴露少数类型；读它的 include 顺序与 `using` 声明，"
        r"能看到「哪些名字允许被 ADL 找到、哪些必须写全限定名」是被刻意设计的",

    # ── ch16 并发与多线程 ────────────────────────────────────────
    "cpp-ch16|chenshuo/muduo":
        r"§2.2 三种 RAII 锁与 §4.2 wait 的三件事：`muduo/base/Mutex.h` 的 `MutexLockGuard` 只在构造/析构里"
        r"加解锁，`muduo/base/Condition.h` 的 `wait()` 内部「解锁 → 等待 → 重新加锁」；"
        r"`muduo/net/EventLoop.cc` 则示范 one loop per thread——三处合起来就是本章的锁 + 条件变量 + 线程模型",
    "cpp-ch16|taskflow/taskflow":
        r"§5.3 线程池：`taskflow/core/executor.hpp` 的 `Executor` 预先起 `_config.num_workers` 个线程，"
        r"每个 worker 在自己的 `_wsq`（work-stealing queue）上取任务，空闲时从别人队尾偷；"
        r"读 `_wait_for_task` 与 `_steal` 两个函数，就懂「任务图 + 工作窃取」如何避免线程空转",
    "cpp-ch16|apache/brpc":
        r"§5.1 高层并发抽象的另一种答案：`src/bthread/` 用 M:N 调度（大量 bthread 跑在少量 pthread 上），"
        r"把「阻塞等待」换成用户态挂起；对照 `std::thread` 的 1:1 模型，"
        r"能看清本章说的「线程池解决的是创建成本，协程解决的是调度成本」",

    # ── ch17 元编程与类型萃取 ────────────────────────────────────
    "cpp-ch17|microsoft/STL":
        r"§1.1 与 §1.3 的原始实现：`stl/inc/type_traits` 里 `is_destructible` 靠 `declval<T>().~T()` 的"
        r"SFINAE 探测，`conjunction`/`disjunction` 用短路继承避免多余实例化；"
        r"把这几处读完，`<type_traits>` 就不再是「查表用的魔法」",
    "cpp-ch17|fmtlib/fmt":
        r"§3.1 与 §3.2 的过渡样本：`include/fmt/base.h` 里 `is_formattable` 同时有 C++20 concept 版"
        r"（`requires` 表达式）与旧编译器的 SFINAE 版，两份实现并列；"
        r"对照它们能看清 concept 把「替换失败」从错误信息里救出来这件事有多实际",
    "cpp-ch17|abseil/abseil-cpp":
        r"§3.1 的工具箱：`absl/meta/type_traits.h` 的 `absl::void_t`、`type_identity`、`is_comparable` "
        r"都是为「检测某操作是否合法」准备的积木；"
        r"读 `is_comparable` 的 `decltype` 表达式，是本章 SFINAE 一节最干净的例题",

    # ── ch18 性能与底层 ──────────────────────────────────────────
    "cpp-ch18|simdjson/simdjson":
        r"§1.1 对齐与 §1.2 显式对齐：`src/generic/stage1/json_structural_indexer.h` 每次吃 64 字节块，"
        r"用 `SIMDJSON_ALIGNED` 保证输入指针对齐到 64 字节边界（否则 AVX2 加载会慢甚至崩）；"
        r"这是「对齐不是学究问题，是 SIMD 的硬要求」的第一手证据",
    "cpp-ch18|google/benchmark":
        r"配 §3.2 的测量方法：`include/benchmark/benchmark.h` 的 `DoNotOptimize` 阻止编译器把结果删掉、"
        r"`ClobberMemory` 强制刷新内存可见性；本章讲「链表 vs 数组」时，"
        r"没有这两个工具测出来的数字基本不可信",
    "cpp-ch18|ClickHouse/ClickHouse":
        r"§3.1 AoS vs SoA 的极致：`src/Columns/ColumnVector.cpp` 每个数值列就是一条连续 `PODArray`，"
        r"`src/Common/PODArray.h` 负责带 padding 的增长；"
        r"读 `ColumnVector::getData()` 直接返回裸指针——因为列存的前提就是「同类型紧挨着」，这正是本章要论证的局部性收益",

    # ── ch19 工程化与测试 ───────────────────────────────────────
    "cpp-ch19|google/googletest":
        r"§2.1 测试框架的最小内核：`googletest/src/gtest.cc` 的 `RUN_ALL_TESTS` → `UnitTest::Run` → "
        r"逐个 `TestInfo::Run`，最后把失败数折成进程退出码；"
        r"看清「退出码即结论」这条链，CI 里的 `ctest` 才知道该不该红",
    "cpp-ch19|catchorg/Catch2":
        r"§2.1 的另一种内核与 §1.2 的 CMake 用法：`src/catch2/catch_session.cpp` 的 `Session::run` 返回失败用例数，"
        r"`CMakeLists.txt` 里 `catch_discover_tests` 把用例注册成独立测试；"
        r"对照 googletest 的「一次跑完」与 Catch2 的「逐用例发现」，"
        r"能看出两种框架对 CI 并行粒度的不同假设",
    "cpp-ch19|cpp-best-practices/gui_starter_template":
        r"§1.2、§1.3 与 §4.1 的整体样板：根 `CMakeLists.txt` 用 target-based 写法，`cmake/` 放自写模块，"
        r"`.github/workflows/` 里是完整的矩阵构建 + 缓存 + artifact；"
        r"把它当作本章的参考实现逐条对照——这是少数把「现代 CMake + 测试 + CI」串成一条线的小型仓库",

    # ── ch20 综合项目与面试冲刺 ─────────────────────────────────
    "cpp-ch20|isocpp/CppCoreGuidelines":
        r"§3.1 异常安全等级的规范表述：`CppCoreGuidelines.md` 的 E.6（RAII 保证）与 C.vector 相关条款"
        r"把「Basic / Strong / No-throw」写成了可引用规则；面试口述前先按编号找到原文，"
        r"比背二手总结更抗追问",
    "cpp-ch20|cpp-best-practices/cppbestpractices":
        r"§2.1 线程池之外的另一半——工程化清单：`chapters/` 目录按主题分章（工具、风格、CMake、测试、CI），"
        r"每章末尾给可执行检查项；拿它给自己的项目做一次体检，能找出「能跑但不能交付」的具体项",
    "cpp-ch20|practical-tutorials/project-based-learning":
        r"§5.2 系统设计取材：`README.md` 的 C++ 一节列了几十个「从零写一个 X」的项目（解释器、渲染器、数据库）；"
        r"面试讲项目经历时，从这类项目里挑一个真正做完的，"
        r"比堆功能列表更能撑住「你解决过什么真实约束」的追问",
}
