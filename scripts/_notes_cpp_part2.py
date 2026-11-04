# -*- coding: utf-8 -*-
"""cpp 学科来源笔记 · 第 2 部分（cpp-ch10 ~ cpp-ch15）。"""

NOTES: dict[str, list[str]] = {
    # ---------------- cpp-ch10 智能指针与 RAII ----------------
    # 仓库序：google/leveldb / abseil/abseil-cpp / protocolbuffers/protobuf
    "cpp-ch10": [
        "§1.2 二、实现机制：析构调用到底是怎么被「插入」的 · 读 `google/leveldb` 的 "
        "`db/db_impl.cc`：`DBImpl::~DBImpl()` 里显式停后台线程、删 memtable、释放文件锁——"
        "所有清理都钉在析构里，因此 `DB::Open` 失败时只要 `delete impl` 就干净；"
        "注意 leveldb 用的是裸指针 + `delete`，正好用来对照本章 §1.1"
        "「为什么确定性析构是 C++ 的脊梁」——手写 RAII 与 `unique_ptr` 在语义上完全等价，"
        "差别只在「有没有可能忘记 delete」",

        "§1.3 三、工程实践：异常安全三保证与 RAII 的关系 · 读 `abseil/abseil-cpp` 的 "
        "`absl/cleanup/cleanup.h`：`absl::Cleanup` 把「析构时执行一段代码」抽成可组合对象，"
        "`absl/synchronization/mutex.h` 的 `MutexLock` 用它管锁；"
        "这两处合看，就明白 RAII 不是「智能指针专用技巧」，而是资源管理的通用形态——"
        "它保证的是「基本保证」这条下限：不管哪条路径退出，清理一定发生",

        "§3.3 三、实现机制：自定义删除器（类型擦除的成本差异） · 读 "
        "`protocolbuffers/protobuf` 的 `src/google/protobuf/arena.h`："
        "`Arena` 用 `unique_ptr` 管自己的块，但 `CreateMessage` 在 arena 上创建的对象"
        "由 arena 统一回收（不逐个 delete）；"
        "这是「所有权不在指针、而在容器」的典型，"
        "也解释了本章 §3.3 里自定义删除器为什么要做类型擦除——"
        "删除器一旦成为 `shared_ptr` 控制块的一部分，它就不再属于指针类型",
    ],

    # ---------------- cpp-ch11 异常处理与断言 ----------------
    # 仓库序：fmtlib/fmt / google/googletest / nlohmann/json
    "cpp-ch11": [
        "§1.2 二、实现机制：栈展开到底发生了什么 · 读 `include/fmt/base.h` 的 "
        "`FMT_THROW` 与 `FMT_ASSERT`：前者可被配置成抛异常或直接 abort，"
        "后者在 debug 下抛 `format_error`；"
        "读这两个宏的分支，就看清「库要不要让异常穿过自己」是一个可配置的契约，"
        "而不是语言强制——这也是本章 §1.4「边界与陷阱」里"
        "「析构函数抛异常会 terminate」为什么让库作者宁可 abort 的理由",

        "§3.4 四、断言：assert / static_assert / 契约（contracts） · 读 "
        "`google/googletest` 的 `googletest/include/gtest/gtest.h`："
        "`EXPECT_*` 失败继续跑、`ASSERT_*` 失败立刻 return，"
        "`EXPECT_THROW`/`EXPECT_NO_THROW` 把「抛不抛」变成可断言的性质，"
        "`ASSERT_DEATH` 连崩溃都能测；"
        "这套 API 是本章「断言与异常各管一段」的现实版——"
        "断言管「程序写错了」，异常管「外部输入不合法」",

        "§2.1 一、理论根基：异常安全的「契约」 · 读 `nlohmann/json` 的 "
        "`include/nlohmann/json.hpp`：`JSON_THROW` 由 `JSON_NOEXCEPTION` 决定展开成 "
        "`throw` 还是 `std::abort`，`parse(..., allow_exceptions=false)` "
        "则让调用方自己查 `is_discarded()`；"
        "同一个库给出三条错误处理路径，正好对应本章 §2.4「在真实项目里给保证」要做的选择——"
        "「异常 vs 错误码 vs 终止」没有对错，只有调用方愿不愿意为此写分支",
    ],

    # ---------------- cpp-ch12 现代 C++ 特性 ----------------
    # 仓库序：AnthonyCalandra/modern-cpp-features / microsoft/STL / abseil/abseil-cpp
    "cpp-ch12": [
        "§4.1 一、结构化绑定（Structured Bindings，C++17） · 读该仓 "
        "`README.md`：它按 C++11/14/17/20 分节，每节都有最小可编译示例；"
        "先读「rvalue references」「structured bindings」两节，"
        "把本章的术语和标准里的正式名字对上，再回代码里验证；"
        "本章 §2.2「值类别（Value Categories）：理解移动的前提」"
        "之所以难，就是因为「prvalue / xvalue / lvalue」这三个词在教材里常被简化成「左值/右值」",

        "§3.3 三、`emplace_back` vs `push_back`：构造次数差异 · 读 `microsoft/STL` 的 "
        "`stl/inc/vector`：`emplace_back` 直接把参数转发给 `_Emplace_reallocate` 里的 "
        "`construct_at`，全程只构造一次；而 `push_back(const T&)` 要先凑出一个 `T` 再移动。"
        "看这两条实现路径，就明白「构造次数差异」不是玄学而是参数转发位置不同——"
        "配合本章 §3.4「转发引用参数的陷阱」，"
        "当参数是 `{}` 或隐式转换类型时，`emplace_back` 反而可能选错构造重载",

        "§2.3 三、实现机制：`std::move` 只是一次无条件 cast · 读 `abseil/abseil-cpp` 的 "
        "`absl/utility/utility.h`：`absl::exchange` 与 `absl/types/optional.h` 的 "
        "`value() &&` 重载都靠 `std::move` 把左值转成右值再转发；"
        "注意它们转完从不「清空源对象」——移动后的源对象仍是有效但未指定状态，"
        "这是本章最常被误解的一条；"
        "而 §2.4「为什么移动构造要标 noexcept」正是这条语义的延伸："
        "标记了才敢在扩容时搬而不是拷",
    ],

    # ---------------- cpp-ch13 输入/输出与文件 ----------------
    # 仓库序：fmtlib/fmt / Tencent/rapidjson / nlohmann/json
    "cpp-ch13": [
        "§4.3 三、std::format（C++20）的设计动机 · 读 `fmtlib/fmt` 的 "
        "`include/fmt/format.h`：`format_to` 把结果直接写进输出迭代器，"
        "`include/fmt/ostream.h` 则给「只有 `operator<<` 的老类型」搭桥；"
        "两处合看就知道 `std::format` 为什么比 `stringstream` 快——"
        "它不建流对象、不碰 locale，解析格式串是一次性编译期检查；"
        "本章 §4.2「为什么 stringstream 慢」给的是病因，这里给的是药",

        "§3.2 二、实现机制：文件位置指针与文本/二进制差异 · 读 `Tencent/rapidjson` 的 "
        "`include/rapidjson/filereadstream.h`：`FileReadStream` 要你自己给一块 `buffer`"
        "（默认 64KB），`FileWriteStream` 同理；"
        "这解释了本章 §3.1「fstream 是流 + 文件缓冲区的组合」里的缓冲层次——"
        "库不替你藏缓冲，性能就变得可预测；"
        "对照 §1.3「`sync_with_stdio` 与 `tie` 的加速原理」会发现两者在做同一件事："
        "把「每字符一次系统调用」换成「每块一次」",

        "§4.4 四、工程实践：CSV 行解析 · 读 `nlohmann/json` 的 "
        "`include/nlohmann/json.hpp`：它的 `operator>>` 与 `dump()` 是"
        "「流式接口 + 一次性序列化」的组合；"
        "对比它和 `std::stringstream` 解析同一份 CSV 的代码量，"
        "能直观看出本章说的「手写分隔符解析为什么容易漏边界」——"
        "引号内的逗号、转义的双引号、行尾的 `\\r\\n`，每一条都是独立分支",
    ],

    # ---------------- cpp-ch14 预处理与宏 ----------------
    # 仓库序：DaveGamble/cJSON / fmtlib/fmt / include-what-you-use/include-what-you-use
    "cpp-ch14": [
        "§1.2 二、实现机制：#include 的「文本包含」语义 · 读 `DaveGamble/cJSON` 的 "
        "`cJSON.h`：顶部 `#ifndef cJSON__h` / `#define cJSON__h`，"
        "`CJSON_PUBLIC` 宏负责导出符号、`CJSON_EXPORT_SYMBOLS` 控制静态/动态；"
        "整个头文件只有声明——把「头文件该放什么」这件事做到了教科书级；"
        "本章 §1.3「`#pragma once` 与其局限」要对着它看："
        "守卫宏防的是「同一编译单元重复包含」，防不住「两个不同路径指向同一文件」",

        "§2.4 四、工程实践：宏与 inline 的取舍 · 读 `include/fmt/base.h` 的 "
        "`FMT_BEGIN_NAMESPACE`/`FMT_END_NAMESPACE`、`FMT_API`、`FMT_INLINE` 三层宏："
        "它们分别管「命名空间版本化、符号可见性、强制内联」；"
        "看清每个宏存在的理由，就明白为什么现代库仍需要宏——"
        "跨编译器差异无法用 C++ 语法表达，"
        "这也正是本章 §2.2「实现机制与坑」里「宏不是坏东西，是最后手段」的分寸",

        "§4.2 二、实现机制：日志宏如何「携带位置信息」 · 读 "
        "`include-what-you-use/include-what-you-use/iwyu.cc` 与同目录的 `iwyu_include_picker.cc`："
        "前者是主分析器，后者维护「哪个头文件该由谁包含」的映射表；"
        "拿它跑一遍本章的示例工程，`#include` 的传递闭包会被直接列出——"
        "这是「文本包含」语义最硬的证据，"
        "也是 §4.1「预定义宏是编译器注入的编译期常量」之外的另一类「编译期注入」"
        "（`__FILE__` 靠宏展开注入，头文件靠文本粘贴注入）",
    ],

    # ---------------- cpp-ch15 命名空间与模块化 ----------------
    # 仓库序：fmtlib/fmt / abseil/abseil-cpp / apache/brpc
    "cpp-ch15": [
        "§3.2 二、实现机制：透明性从何而来 · 读 `include/fmt/base.h`："
        "`FMT_BEGIN_NAMESPACE` 展开成 `namespace fmt { inline namespace v11 {`，"
        "于是 `fmt::format` 与 `fmt::v11::format` 是同一个实体；"
        "库靠它做到「ABI 版本可以换、用户代码不用改」——"
        "本章 §3.1「为什么需要 inline namespace」的答案是："
        "普通嵌套命名空间做不到「同名别名」，而 inline 让内层名字自动进入外层作用域",

        "§3.1 一、理论根基：为什么需要「inline namespace」 · 读 `abseil/abseil-cpp` 的 "
        "`absl/base/config.h`：`ABSL_NAMESPACE_BEGIN` 展开成 "
        "`namespace absl { ABSL_INTERNAL_NAMESPACE {`，"
        "具体名字由 `absl/base/options.h` 的 LTS 宏决定；"
        "对照 fmt 与 abseil 两种版本化命名空间，能看清「透明 vs 显式」的取舍——"
        "fmt 用 inline 让用户无感，abseil 让用户可以显式写 `absl::lts_20240116::` 锁死版本",

        "§1.2 二、实现机制：名字查找到底怎么走 · 读 `apache/brpc` 的 `src/brpc/server.h`："
        "`namespace brpc` 下再分 `policy`、`detail` 等子命名空间，对外只暴露少数类型；"
        "读它的 include 顺序与 `using` 声明，能看到「哪些名字允许被 ADL 找到、"
        "哪些必须写全限定名」是被刻意设计的——"
        "这正是本章 §1.5「五、可运行示例：眼见为实」里 ADL 那一例的现实约束："
        "ADL 只查实参类型所在命名空间，所以把重载放进 `detail` 就同时切断了 ADL",
    ],
}
