# -*- coding: utf-8 -*-
"""批次七：给 cpp 十一章补 sandbox（覆盖 C++ 从函数对象到 CI 的整条工程链）。

与 batch3/4/5/6 同一套路：写进 content/_handmade/labs.json 的 chapters，
再由 gen_interactive.py 并入各章 interactive.json 与前端数据。

为什么是这十一章
---------------
cpp 已有 9 章沙盒（ch01 整型宽度、ch03 SSO、ch05 拷贝、ch06 虚表、ch08 扩容、
ch10 环形引用、ch16 线程加速比、ch18 对象布局、ch20 连接池）。余下 11 章
同样每章都有一个「能用数字算清」的真实成本：

  ch02  std::function 的 SBO 只有 16 字节，捕获超了每个回调一次 malloc
  ch04  逐个 new 一个小对象，glibc 最小 chunk 32 字节 → 8 倍膨胀
  ch07  模板按 (类型 × 函数) 实例化，类型擦除只留一份
  ch09  n 次线性查找是 n·k，排序+二分是 n·log n + k·log n
  ch11  异常不抛时零成本，一抛就是 2μs 栈展开，别拿它做控制流
  ch12  push_back(T(...)) 构造两次，emplace_back 只构造一次
  ch13  endl 每次都 flush（一次 write 系统调用），`\\n` 只在缓冲满时写
  ch14  宏在文本层展开，每个调用点一份代码；inline/constexpr 只有一份
  ch15  #include 让同一个头文件被每个 TU 重新解析一遍；模块只解析一次
  ch17  递归模板实例化 N 层 vs 折叠表达式一次展开
  ch19  CI 串行跑测试 vs 并行，但固定开销（checkout/build）不可压缩（Amdahl）

纪律（沿用前几批）
-----------------
1. checks 必须带规模下限，否则求解读退化成「旋钮全拉到最小」。
2. 不锁「正确答案」，让预算判据自己把错方案淘汰掉。
3. 默认值 = 真实事故配置（新手默认写法）。
4. `if(c,a,b)` 急切求值 → 分支内不做除法，除数全为非零常量。
5. fmt 只认 int / fix2 / pct；**不支持科学计数法，指数一律写完整数字**。
6. 判据阈值留 5% 以上余量，不要贴着网格取值算。

写盘必须 indent=1 + newline="\\n"。
"""
import json
import os

LABS = os.path.join(os.path.dirname(__file__), "..", "content", "_handmade", "labs.json")


# ============================================================================
# cpp/cpp-ch02 · 一个 std::function，捕获大了就要堆分配
# ----------------------------------------------------------------------------
# 教学点：std::function 有 SBO（small buffer optimization），libstdc++ 的容量
# 是 16 字节。捕获的东西能塞进这 16 字节就原地存，塞不进就 new 一块堆内存。
# 一百万个回调、每个捕获 48 字节 = 一百万次 malloc，光分配就多花 0.1 秒、
# 45MB 堆内存。这就是"lambda 明明只是个函数，为什么注册回调会变慢"的答案。
# ============================================================================
cpp_ch02 = {
    "kind": "sandbox",
    "title": "一个 std::function，捕获大了就要堆分配",
    "brief": (
        "`std::function` 要先擦掉类型才能存任何可调用对象，它靠一块内置缓冲区"
        "（libstdc++ 里是 16 字节）装下小的捕获。装得下就原地存，装不下就 new。"
        "捕获三个 shared_ptr 就是 48 字节——每个回调一次堆分配。"
        "把捕获的指针个数与回调数量拖到真实事件系统的规模，"
        "看这一百万次 malloc 是怎么把注册接口拖慢的。"
    ),
    "params": [
        # 按值捕获的 shared_ptr 个数：每个 16 字节（对象指针 + 控制块指针）
        {"key": "ptrs", "label": "捕获 shared_ptr 个数", "min": 1, "max": 4, "step": 1, "value": 3},
        # 回调数量（百万）
        {"key": "callbacksM", "label": "回调数量（百万）", "min": 1, "max": 10, "step": 1, "value": 1},
        # 对策：0 = 按值捕获（每份拷贝），1 = 收敛成一个 shared_ptr<Context>
        {"key": "mode", "label": "捕获方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["按值捕获全部", "收敛成 1 个 Context 指针"]},
    ],
    "metrics": [
        {"key": "callbacks", "label": "回调数量", "expr": "callbacksM * 1000000", "unit": "个", "fmt": "int"},
        # 捕获体积：每个 shared_ptr 16 字节
        {"key": "capB", "label": "捕获体积", "expr": "ptrs * 16", "unit": "B", "fmt": "int"},
        # libstdc++ 的 SBO 容量
        {"key": "sboB", "label": "SBO 容量", "expr": "16", "unit": "B", "fmt": "int"},
        # 按值捕获时：超出 SBO → 每个回调一次 malloc
        {"key": "naiveAllocs", "label": "按值捕获的分配次数", "expr": "if(ptrs * 16 <= 16, 0, callbacks)", "unit": "次", "fmt": "int"},
        # 按值捕获时堆上多占的内存
        {"key": "naiveHeapMB", "label": "按值捕获堆占用", "expr": "if(ptrs * 16 <= 16, 0, callbacks * ptrs * 16 / 1048576)", "unit": "MB", "fmt": "int"},
        # 收敛方案：每个回调仍存一个 shared_ptr（16 字节，正好卡进 SBO），零堆分配
        {"key": "ctxMB", "label": "收敛方案占用", "expr": "callbacks * 16 / 1048576", "unit": "MB", "fmt": "int"},
        # 当前方式的分配次数
        {"key": "chosenAllocs", "label": "当前分配次数", "expr": "if(mode == 1, 0, naiveAllocs)", "unit": "次", "fmt": "int"},
        # 当前方式的堆占用
        {"key": "chosenMB", "label": "当前堆占用", "expr": "if(mode == 1, ctxMB, naiveHeapMB)", "unit": "MB", "fmt": "int"},
        # 分配耗时：每次 malloc 约 100ns
        {"key": "allocMs", "label": "分配耗时", "expr": "chosenAllocs * 100 / 1000000", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        # 下限：百万级回调，少了这点开销无所谓
        {"expr": "callbacks >= 1000000", "label": "回调数 ≥100 万（真实事件系统的规模）"},
        # 下限：确实按值捕获了多个 shared_ptr（否则本来就在 SBO 里）
        {"expr": "ptrs >= 2", "label": "捕获 ≥2 个 shared_ptr（超过 16 字节的 SBO 才出问题）"},
        # 痛点：按值捕获确实要在堆上多占几十 MB
        {"expr": "naiveHeapMB >= 32", "label": "按值捕获堆占用 ≥32MB（这就是要解决的痛点）"},
        # 上限：一次堆分配都不该有
        {"expr": "chosenAllocs <= 0", "label": "当前方式堆分配 0 次（必须落进 SBO）"},
        # 上限：堆占用也要压下来
        {"expr": "chosenMB <= 32", "label": "当前堆占用 ≤32MB"},
    ],
    "insight": (
        "`std::function` 是类型擦除的代价：为了能存任意 lambda，它得在对象里留一块定长缓冲区，"
        "libstdc++ 给的是 16 字节（libc++ 更小）。捕获超过这个尺寸，构造时就要 `new`，"
        "调用时还要多一次指针间接——一百万个回调就是一百万次 malloc、0.1 秒和 45MB。"
        "工程上的三条对策："
        "① 捕获 `this` 或一个指针（8 字节）而不是按值拷几个 shared_ptr；"
        "② 高频回调改用模板参数 / `function_ref`（C++26）/ 自定义类型擦除，把 SBO 做大；"
        "③ 真要共享状态，就让所有回调只捕获一个 `std::shared_ptr<Context>`——"
        "16 字节刚好卡在 SBO 阈值上（本关的收敛方案），共享一份上下文而不是每个回调拷一份。"
        "顺带一条反直觉的：`std::function` 的对象大小是固定的（32~40 字节），"
        "捕获多少都不影响 `sizeof`，超出的部分全在堆上——所以 `sizeof` 看不出这里的内存问题。"
    ),
}


# ============================================================================
# cpp/cpp-ch04 · 一亿个小对象，为什么 new 出来的内存是 8 倍
# ----------------------------------------------------------------------------
# 教学点：`new int` 请求 4 字节，glibc malloc 最少给一个 32 字节的 chunk
# （8 字节 size 头 + 对齐 + 最小可用块）。一亿个 int 名义 400MB，
# 实际占 3.2GB——8 倍膨胀。而"分配器/arena/连续容器"一次要一大块、
# 自己切片，元数据只付一次。
# ============================================================================
cpp_ch04 = {
    "kind": "sandbox",
    "title": "一亿个小对象，为什么 new 出来的内存是 8 倍",
    "brief": (
        "`new int(0)` 只请求 4 字节，但 glibc 的 malloc 最小块是 32 字节——"
        "8 字节的 size 头、16 字节对齐、再加最小可用空间。"
        "一亿个 int 名义上 400MB，实际吃掉 3.2GB。"
        "换成一次分配大块、自己按下标切片（arena / 连续容器），"
        "元数据只付一次，内存立刻回到 400MB。把对象数与分配策略拖到真实规模试试。"
    ),
    "params": [
        # 对象数（百万个 int）
        {"key": "nM", "label": "对象数（百万）", "min": 1, "max": 200, "step": 1, "value": 100},
        # 分配策略：0 = 逐个 new，1 = 一次大块 + 下标切片
        {"key": "mode", "label": "分配策略", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["逐个 new int", "一次大块 + 切片"]},
    ],
    "metrics": [
        {"key": "objs", "label": "对象数", "expr": "nM * 1000000", "unit": "个", "fmt": "int"},
        # 逐个 new：每个 chunk 32 字节（4B 数据 + 头/对齐）
        {"key": "newMB", "label": "逐个 new 占用", "expr": "nM * 1000000 * 32 / 1048576", "unit": "MB", "fmt": "int"},
        # 连续切片：只有 4 字节数据
        {"key": "arenaMB", "label": "大块切片占用", "expr": "nM * 1000000 * 4 / 1048576", "unit": "MB", "fmt": "int"},
        # 当前策略
        {"key": "chosenMB", "label": "当前策略占用", "expr": "if(mode == 1, arenaMB, newMB)", "unit": "MB", "fmt": "int"},
        # 膨胀倍数：固定 8 倍
        {"key": "ratio", "label": "new / 切片", "expr": "newMB / arenaMB", "unit": "倍", "fmt": "fix2"},
        # 分配次数：逐个 new 是 n 次，切片是 1 次
        {"key": "allocCount", "label": "分配次数", "expr": "if(mode == 1, 1, nM * 1000000)", "unit": "次", "fmt": "int"},
        # 分配耗时：每次 malloc 约 50ns
        {"key": "allocMs", "label": "分配耗时", "expr": "allocCount * 50 / 1000000", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        # 下限：5000 万个对象起
        {"expr": "objs >= 50000000", "label": "对象数 ≥5000 万（规模够大才看得见元数据开销）"},
        # 痛点：逐个 new 必然过 2GB
        {"expr": "newMB >= 2048", "label": "逐个 new 占用 ≥2GB（这就是要解决的痛点）"},
        # 上限：当前策略压进 1GB
        {"expr": "chosenMB <= 1024", "label": "当前策略 ≤1GB（容器内存预算内）"},
        # 分配次数也得降下来，否则只剩内存达标、耗时照样炸
        {"expr": "allocCount <= 1000", "label": "分配次数 ≤1000（不能每个对象都向系统要一次）"},
    ],
    "insight": (
        "每个 `new` 都带一本账：glibc 的 chunk 要存 size、要满足 16 字节对齐，"
        "最小块 32 字节。请求 4 字节拿到 32 字节，**8 倍膨胀**；"
        "一亿个对象就是 3.2GB，而数据本身只有 400MB。"
        "更贵的是调用开销：一亿次 malloc 至少 5 秒（每次 50ns 起），"
        "还要加上碎片导致的 cache miss。"
        "对策按侵入性排序：`std::vector<int>` 连续存（最省）、"
        "对象池/arena 一次要一大块自己切片、`std::pmr::monotonic_buffer_resource`（标准库现成的 arena）。"
        "反面案例是「节点式容器 + 小对象」：`std::list<int>` 每个节点要两个指针加一次分配，"
        "一亿个 int 能吃到 2.4GB——这也是「默认用 vector」这条建议的数学依据。"
    ),
}


# ============================================================================
# cpp/cpp-ch07 · 模板按类型复制代码，类型一多就膨胀
# ----------------------------------------------------------------------------
# 教学点：函数模板为每组 (类型, 函数) 生成一份机器码。16 种类型 × 8 个函数
# = 128 份实例化，二进制涨到几百 KB、编译时间线性上涨。
# 类型擦除（variant + 一次 visit，或虚函数）只留一份代码，
# 代价是每次调用一次间接跳转。这是"模板 vs 多态"的真实取舍。
# ============================================================================
cpp_ch07 = {
    "kind": "sandbox",
    "title": "模板按类型复制代码，类型一多就膨胀",
    "brief": (
        "函数模板不是「写一次编译一次」，而是**每组类型参数各生成一份机器码**。"
        "16 种消息类型 × 8 个处理函数，就是 128 份实例化，二进制里塞满几乎相同的代码。"
        "改成一个 `std::variant` + 类型擦除，代码只剩 8 份，代价是每次调用多一次间接跳转。"
        "把类型数与函数数拖到真实协议栈的规模，看编译产物怎么膨胀。"
    ),
    "params": [
        # 类型数
        {"key": "types", "label": "消息类型数", "min": 2, "max": 32, "step": 2, "value": 16},
        # 每个类型要实例化的函数数
        {"key": "funcs", "label": "每个类型的函数数", "min": 1, "max": 12, "step": 1, "value": 8},
        # 方案：0 = 模板实例化，1 = variant 类型擦除
        {"key": "mode", "label": "实现方案", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["模板实例化", "variant 类型擦除"]},
    ],
    "metrics": [
        # 模板方案的实例化份数：types × funcs
        {"key": "templateInsts", "label": "模板实例化份数", "expr": "types * funcs", "unit": "份", "fmt": "int"},
        # 类型擦除：每个函数一份
        {"key": "erasedInsts", "label": "类型擦除份数", "expr": "funcs", "unit": "份", "fmt": "int"},
        # 当前方案的份数
        {"key": "insts", "label": "当前份数", "expr": "if(mode == 1, erasedInsts, templateInsts)", "unit": "份", "fmt": "int"},
        # 代码体积：模板每份约 4KB，类型擦除每份约 6KB（含 visit 派发）
        {"key": "templateKB", "label": "模板方案代码", "expr": "templateInsts * 4", "unit": "KB", "fmt": "int"},
        {"key": "erasedKB", "label": "类型擦除代码", "expr": "erasedInsts * 6", "unit": "KB", "fmt": "int"},
        {"key": "chosenKB", "label": "当前方案代码", "expr": "if(mode == 1, erasedKB, templateKB)", "unit": "KB", "fmt": "int"},
        # 编译时间：每份实例化约 8ms
        {"key": "compileMs", "label": "编译耗时", "expr": "insts * 8", "unit": "ms", "fmt": "int"},
        # 每次调用的额外代价：模板可内联（0），擦除要间接跳转
        {"key": "callNs", "label": "单次调用开销", "expr": "if(mode == 1, 3, 0)", "unit": "ns", "fmt": "int"},
    ],
    "checks": [
        # 下限：类型足够多，才谈得上膨胀
        {"expr": "types >= 8", "label": "类型数 ≥8（类型少了模板怎么都好）"},
        {"expr": "funcs >= 5", "label": "每类型函数数 ≥5（组合数才上得去）"},
        # 痛点：模板方案确实膨胀
        {"expr": "templateKB >= 256", "label": "模板方案 ≥256KB（这就是要解决的痛点）"},
        # 上限：当前方案压进 96KB
        {"expr": "chosenKB <= 96", "label": "当前方案 ≤96KB（二进制体积预算）"},
    ],
    "insight": (
        "模板是「零成本抽象」，但零成本指的是**运行时**——编译期它按每组类型参数复制一份代码。"
        "16 种消息 × 8 个 handler = 128 份几乎一样的机器码，二进制和编译时间都线性涨；"
        "而 variant + 一次 visit 只留 8 份。"
        "这里的取舍不能一刀切："
        "热路径、类型少、需要内联 → 用模板（多出的代码换掉一次间接跳转）；"
        "类型多、代码体积敏感（嵌入式、移动端）、编译时间是瓶颈 → 用类型擦除。"
        "工业界的中间态是「模板在前、擦除在边界」："
        "核心算法全模板（可内联），跨模块导出时收敛到少数几个擦除接口，"
        "既保住热路径又挡住实例化爆炸。"
    ),
}


# ============================================================================
# cpp/cpp-ch09 · 一万次查找要不要先排序
# ----------------------------------------------------------------------------
# 教学点：线性查找 n 个元素 k 次 = n·k 次比较；排序 n·log n 之后二分 k·log n。
# 数据量大、查询多时后者快几个数量级——这就是"先建索引"的数学依据。
# ============================================================================
cpp_ch09 = {
    "kind": "sandbox",
    "title": "一万次查找要不要先排序",
    "brief": (
        "在一百万条记录里查一万次，最直接的办法是每次都从头扫一遍——"
        "那是 10¹⁰ 次比较，跑十秒以上。"
        "先花 n·log n 排一次序（或建哈希表），之后每次查询只要 log n 步，"
        "总代价掉到两千万次。把数据量与查询次数拖到真实业务规模，"
        "看「线性扫」和「排序 + 二分」两条线什么时候交叉、什么时候分岔。"
    ),
    "params": [
        # 数据量（千条）
        {"key": "nK", "label": "数据量（千条）", "min": 10, "max": 2000, "step": 10, "value": 2000},
        # 查询次数（千次）
        {"key": "qK", "label": "查询次数（千次）", "min": 2, "max": 100, "step": 2, "value": 20},
        # 方案：0 = 每次线性扫，1 = 排序 + 二分
        {"key": "mode", "label": "查找方案", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["每次线性扫", "排序 + 二分"]},
    ],
    "metrics": [
        {"key": "n", "label": "数据量 n", "expr": "nK * 1000", "unit": "条", "fmt": "int"},
        {"key": "q", "label": "查询次数 k", "expr": "qK * 1000", "unit": "次", "fmt": "int"},
        # 线性扫：n × k
        {"key": "linearOps", "label": "线性扫比较次数", "expr": "nK * 1000 * qK * 1000", "unit": "次", "fmt": "int"},
        # 排序代价：n log2 n
        {"key": "sortOps", "label": "排序比较次数 n·log₂n", "expr": "nK * 1000 * log2(nK * 1000)", "unit": "次", "fmt": "int"},
        # 二分代价：k log2 n
        {"key": "binOps", "label": "二分比较次数 k·log₂n", "expr": "qK * 1000 * log2(nK * 1000)", "unit": "次", "fmt": "int"},
        # 排序 + 二分总代价
        {"key": "sortedOps", "label": "排序+二分合计", "expr": "sortOps + binOps", "unit": "次", "fmt": "int"},
        # 当前方案
        {"key": "chosenOps", "label": "当前方案比较次数", "expr": "if(mode == 1, sortedOps, linearOps)", "unit": "次", "fmt": "int"},
        # 按每秒 10 亿次比较估算的耗时
        {"key": "ms", "label": "预计耗时", "expr": "chosenOps / 1000000", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        # 下限：百万条 + 万次查询，规模真实
        {"expr": "n >= 1000000", "label": "数据量 ≥100 万条（真实业务表规模）"},
        {"expr": "q >= 10000", "label": "查询 ≥1 万次（查得够多才值得建索引）"},
        # 痛点：线性扫必然过百亿次比较
        {"expr": "linearOps >= 10000000000", "label": "线性扫 ≥100 亿次比较（这就是要解决的痛点）"},
        # 上限：当前方案压进 1 亿次
        {"expr": "chosenOps <= 100000000", "label": "当前方案 ≤1 亿次比较（约 0.1 秒）"},
    ],
    "insight": (
        "查找的复杂度账要按**总代价**算，不是单次：线性扫是 `k·n`，"
        "排序+二分是 `n·log n + k·log n`。k 一大，`n` 就被 `log n` 彻底压住。"
        "200 万条查 2 万次：线性 4×10¹⁰ vs 排序+二分 4.2×10⁷，差三个数量级。"
        "这条结论有三个推论："
        "① 查一次就完事的场景（k=1）排序反而更慢，别过度索引；"
        "② 索引是**一次性投入**，摊到 k 次查询上才划算（和 ch04 的 arena 同构）；"
        "③ 哈希表把 `log n` 也省成 O(1)，但要求可哈希、且不支持范围查询——"
        "数据库里 B+ 树而不是哈希索引，正是为了 `ORDER BY` 和范围扫描。"
    ),
}


# ============================================================================
# cpp/cpp-ch11 · 用异常做控制流，代价是每次 2 微秒
# ----------------------------------------------------------------------------
# 教学点：异常在**不抛**时几乎零成本（表驱动展开，无运行期判断），
# 但一旦抛出，栈展开 + 构造 what() 大约 2μs，比返回错误码（~1ns）贵 2000 倍。
# 一千万次调用里 10% 走异常分支 = 一百万次 throw = 2 秒。
# ============================================================================
cpp_ch11 = {
    "kind": "sandbox",
    "title": "用异常做控制流，代价是每次 2 微秒",
    "brief": (
        "异常在「不抛」的时候几乎不花钱——编译器用表驱动展开，运行期零判断。"
        "但一旦真的 throw，要查表、逐层展开栈、构造异常对象，一次约 2 微秒，"
        "比返回错误码贵两千倍。"
        "如果把它当 if/else 用（比如「找不到就抛」），错误率一高，"
        "整条路径就慢得离谱。把错误率和调用量拖到真实规模看看。"
    ),
    "params": [
        # 调用量（百万次）
        {"key": "callsM", "label": "调用量（百万次）", "min": 1, "max": 50, "step": 1, "value": 10},
        # 错误率（%）
        {"key": "errPct", "label": "错误率", "min": 0, "max": 50, "step": 5, "value": 10, "unit": "%"},
        # 方案：0 = 抛异常，1 = 返回错误码
        {"key": "mode", "label": "错误处理方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["throw 异常", "返回错误码"]},
    ],
    "metrics": [
        {"key": "calls", "label": "调用次数", "expr": "callsM * 1000000", "unit": "次", "fmt": "int"},
        # 错误次数
        {"key": "errors", "label": "错误次数", "expr": "callsM * 1000000 * errPct / 100", "unit": "次", "fmt": "int"},
        # 异常方案：每次 throw 约 2μs
        {"key": "excMs", "label": "异常方案耗时", "expr": "errors * 2000 / 1000000", "unit": "ms", "fmt": "int"},
        # 错误码方案：每次检查约 1ns
        {"key": "errMs", "label": "错误码方案耗时", "expr": "calls * 1 / 1000000", "unit": "ms", "fmt": "int"},
        # 当前方案
        {"key": "chosenMs", "label": "当前方案耗时", "expr": "if(mode == 1, errMs, excMs)", "unit": "ms", "fmt": "int"},
        # 单次错误代价比
        {"key": "ratio", "label": "异常 / 错误码（单次错误）", "expr": "2000", "unit": "倍", "fmt": "int"},
        # 成功路径代价：异常方案 0（零成本），错误码每次一次分支
        {"key": "okPathNs", "label": "成功路径单次开销", "expr": "if(mode == 1, 1, 0)", "unit": "ns", "fmt": "int"},
    ],
    "checks": [
        # 下限：千万次调用，规模真实
        {"expr": "calls >= 10000000", "label": "调用 ≥1000 万次（真实热路径规模）"},
        # 下限：确实有相当多的错误，否则异常不花钱
        {"expr": "errors >= 100000", "label": "错误 ≥10 万次（错误够多才暴露异常的开销）"},
        # 痛点：异常方案确实慢
        {"expr": "excMs >= 100", "label": "异常方案 ≥100ms（这就是要解决的痛点）"},
        # 上限：当前方案压进 20ms
        {"expr": "chosenMs <= 20", "label": "当前方案 ≤20ms（热路径预算）"},
    ],
    "insight": (
        "C++ 的异常是**零成本抽象**，但「零成本」只针对不抛的那条路径："
        "编译器把 try 块编译成表项，正常执行时一条指令都不多花。"
        "一旦 throw，就要查异常表、沿栈逐层找 handler、沿途析构局部对象——"
        "实测一次约 2μs，比 `return errno` 的 1ns 贵 **2000 倍**。"
        "所以判据只有一条：**异常用于「不该发生的事」**（磁盘掉了、协议被破坏、"
        "前置条件被违反），不要用于「常见分支」（查不到、解析失败、队列空）。"
        "Google C++ Style 直接禁异常、LLVM 用 `Expected<T>`、Rust 用 `Result`——"
        "思路一致：把「可预期的失败」放进返回值类型，让编译期强制处理；"
        "异常留给真正异常的状态。"
    ),
}


# ============================================================================
# cpp/cpp-ch12 · push_back 和 emplace_back 差在哪
# ----------------------------------------------------------------------------
# 教学点：`push_back(T(args))` 先在栈上构造一个临时 T，再移动/拷贝进容器
# ——两次构造；`emplace_back(args)` 把参数完美转发到容器内存上原地构造
# ——一次构造。元素构造成本高（string 要分配、对象要初始化）时差一倍。
# ============================================================================
cpp_ch12 = {
    "kind": "sandbox",
    "title": "push_back 和 emplace_back 差在哪",
    "brief": (
        "`v.push_back(std::string(1000, 'x'))` 会先在栈上造一个临时 string"
        "（一次堆分配），再把它移动进 vector（又一次构造）——两倍的开销。"
        "`v.emplace_back(1000, 'x')` 把参数直接转发到 vector 的内存上原地构造，只构造一次。"
        "一百万个元素就是一百万次多余的构造和析构。"
        "把元素数拖到真实规模，看这两种写法的构造成本差多少。"
    ),
    "params": [
        # 元素数（百万）
        {"key": "nM", "label": "元素数（百万）", "min": 1, "max": 50, "step": 1, "value": 10},
        # 写法：0 = push_back(T(...))，1 = emplace_back(...)
        {"key": "mode", "label": "插入写法", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["push_back(T(...))", "emplace_back(...)"]},
    ],
    "metrics": [
        {"key": "elems", "label": "元素数", "expr": "nM * 1000000", "unit": "个", "fmt": "int"},
        # push_back：临时构造 + 移动构造 = 2 次
        {"key": "pushCtors", "label": "push_back 构造次数", "expr": "nM * 1000000 * 2", "unit": "次", "fmt": "int"},
        # emplace_back：原地构造 = 1 次
        {"key": "emplaceCtors", "label": "emplace_back 构造次数", "expr": "nM * 1000000", "unit": "次", "fmt": "int"},
        # 当前写法
        {"key": "ctors", "label": "当前构造次数", "expr": "if(mode == 1, emplaceCtors, pushCtors)", "unit": "次", "fmt": "int"},
        # 堆分配次数：每个 string 构造都要分配一次
        {"key": "allocs", "label": "堆分配次数", "expr": "if(mode == 1, emplaceCtors, pushCtors)", "unit": "次", "fmt": "int"},
        # 耗时：每次构造约 80ns（含一次小分配）
        {"key": "ms", "label": "构造耗时", "expr": "ctors * 80 / 1000000", "unit": "ms", "fmt": "int"},
        # 多出来的临时对象占的栈/堆
        {"key": "wasteMB", "label": "多余临时对象内存", "expr": "if(mode == 1, 0, nM * 1000000 * 32 / 1048576)", "unit": "MB", "fmt": "int"},
    ],
    "checks": [
        # 下限：500 万元素，规模真实
        {"expr": "elems >= 5000000", "label": "元素数 ≥500 万（真实数据加载规模）"},
        # 痛点：push_back 必然两倍构造
        {"expr": "pushCtors >= 10000000", "label": "push_back 构造 ≥1000 万次（这就是要解决的痛点）"},
        # 上限：当前写法构造次数压进 800 万
        {"expr": "ctors <= 8000000", "label": "当前写法构造 ≤800 万次（一个元素只该构造一次）"},
    ],
    "insight": (
        "`push_back` 收的是**已经构造好的对象**，所以你必须先造一个临时的；"
        "`emplace_back` 收的是**构造函数的参数**，转发到容器内存上原地构造。"
        "对 `int` 这种平凡类型两者完全一样（编译器直接优化掉），"
        "但对 `std::string`、`std::vector`、带资源的类，差的是"
        "**一次构造 + 一次析构 + 一次移动**。"
        "不过 emplace 不是万能的，它有两个坑："
        "① 遇到 explicit 构造会静默通过（`v.emplace_back(3.14)` 造出一个元素，"
        "而 `push_back(3.14)` 会编译失败）——想保持类型安全就还是 push_back；"
        "② emplace 传的是构造参数，`v.emplace_back(x)` 里 x 是另一个 vector 时"
        "可能命中拷贝构造而不是你以为的初始化列表。"
        "结论：**默认 emplace_back，遇到显式构造/初始化列表歧义时退回 push_back**。"
    ),
}


# ============================================================================
# cpp/cpp-ch13 · 两百万行输出，为什么卡在 endl 上
# ----------------------------------------------------------------------------
# 教学点：`std::endl` = `'\\n'` + `flush()`。每次 flush 就是一次 write 系统调用
# （约 1μs），两百万行 = 两百万次 syscall = 2 秒。`'\\n'` 只在缓冲区满时才写。
# 加上 iostream 默认和 C stdio 同步（每次 << 都要过一遍同步层），再慢 3 倍。
# 两行改动（关同步 + 用 '\\n'）能快几十倍——这是竞赛和日志的标准操作。
# ============================================================================
cpp_ch13 = {
    "kind": "sandbox",
    "title": "两百万行输出，为什么卡在 endl 上",
    "brief": (
        "`std::endl` 不只是换行，它等于 `'\\n'` 加一次 `flush()`——"
        "每写一行就发一次 write 系统调用，两百万行就是两百万次，光系统调用就两秒。"
        "`'\\n'` 只在缓冲区满（通常 4~8KB）时才真正写盘。"
        "再加上 iostream 默认要和 C 的 stdio 保持同步，每次 `<<` 都要多绕一圈。"
        "把行数与两个开关拖到真实日志的规模，看这几行代码值多少倍性能。"
    ),
    "params": [
        # 输出行数（千行）
        {"key": "linesK", "label": "输出行数（千行）", "min": 100, "max": 5000, "step": 100, "value": 2000},
        # 换行方式：0 = '\\n'（缓冲），1 = std::endl（每次都 flush）
        {"key": "endl", "label": "换行方式", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["'\\n'（缓冲）", "std::endl（每次 flush）"]},
        # 同步开关：0 = sync_with_stdio(false)，1 = 保持默认同步
        {"key": "sync", "label": "stdio 同步", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["关闭（sync_with_stdio(false)）", "保持默认同步"]},
    ],
    "metrics": [
        {"key": "lines", "label": "输出行数", "expr": "linesK * 1000", "unit": "行", "fmt": "int"},
        # 若用 endl：每行一次 write
        {"key": "endlSyscalls", "label": "endl 的系统调用数", "expr": "linesK * 1000", "unit": "次", "fmt": "int"},
        # 实际系统调用：endl 每行一次，'\n' 按 8KB 缓冲约 200 行一次
        {"key": "syscalls", "label": "当前系统调用数", "expr": "if(endl == 1, linesK * 1000, linesK * 5)", "unit": "次", "fmt": "int"},
        # 系统调用耗时：每次约 1μs
        {"key": "syscallMs", "label": "系统调用耗时", "expr": "syscalls / 1000", "unit": "ms", "fmt": "int"},
        # 格式化开销：每次 << 约 70ns，同步模式下乘 3
        {"key": "fmtMs", "label": "格式化耗时", "expr": "linesK * 1000 * 70 / 1000000 * if(sync == 1, 3, 1)", "unit": "ms", "fmt": "int"},
        # 合计
        {"key": "totalMs", "label": "总耗时", "expr": "syscallMs + fmtMs", "unit": "ms", "fmt": "int"},
        # 相对最优写法的倍数
        {"key": "ratio", "label": "相对最优写法", "expr": "totalMs / (linesK * 5 / 1000 + linesK * 1000 * 70 / 1000000)", "unit": "倍", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：百万行起，小输出怎么都无所谓
        {"expr": "lines >= 1000000", "label": "输出 ≥100 万行（真实日志/竞赛输出规模）"},
        # 痛点：endl 在这个规模下必然百万次系统调用
        {"expr": "endlSyscalls >= 1000000", "label": "endl 方案 ≥100 万次系统调用（这就是要解决的痛点）"},
        # 上限：总耗时压进 500ms
        {"expr": "totalMs <= 500", "label": "总耗时 ≤500ms（交互/判题的时间预算）"},
    ],
    "insight": (
        "`std::endl` 是「换行 + 刷新」，不是「换行」。刷新意味着这次 write 必须真的落到内核，"
        "一次约 1μs；两百万行就是两秒，而 `'\\n'` 攒满 8KB 缓冲才写一次，只要一万次调用。"
        "第二个隐形开销是 iostream 默认 `sync_with_stdio(true)`：C++ 流要和 C 的 stdio 共享缓冲，"
        "每次 `<<` 都过一遍同步层，所以 `cin/cout` 比 `scanf/printf` 慢 3 倍左右。"
        "两行改动就能拿回几十倍："
        "`ios::sync_with_stdio(false); cin.tie(nullptr);` + 全部 `endl` 改 `'\\n'`。"
        "（真需要立即落盘时才 flush——比如崩溃前要留下最后一行日志，"
        "那种场景该用 `std::flush` 或直接写无缓冲的 `write(2)`。）"
    ),
}


# ============================================================================
# cpp/cpp-ch14 · 一个宏在两千个调用点展开成多少代码
# ----------------------------------------------------------------------------
# 教学点：宏是**文本替换**，每个调用点都完整展开一份，20000 个调用点 ×
# 20 条语句就是 40 万条指令散落在二进制各处，还各自占一份 I-cache。
# inline 函数 / constexpr 函数只生成一份，靠调用指令复用——
# 这就是"宏没有类型检查、还会让代码膨胀"的量化版本。
# ============================================================================
cpp_ch14 = {
    "kind": "sandbox",
    "title": "一个宏在两千个调用点展开成多少代码",
    "brief": (
        "宏是文本替换：写在头文件里的一行 `LOG(...)`，在两万个调用点就展开两万份代码，"
        "每份都占指令缓存。而同样功能的 inline / constexpr 函数，编译器只生成一份，"
        "其余地方都是一条 call。"
        "这就是「用宏做工具函数」在大型项目里最先撞上的墙——不是可读性，是体积。"
        "把调用点数与宏体大小拖到真实工程的规模看看。"
    ),
    "params": [
        # 调用点数（千个）
        {"key": "sitesK", "label": "调用点数（千个）", "min": 1, "max": 100, "step": 1, "value": 20},
        # 宏体语句数
        {"key": "stmts", "label": "宏体语句数", "min": 2, "max": 40, "step": 2, "value": 20},
        # 实现方式：0 = 宏，1 = inline/constexpr 函数
        {"key": "mode", "label": "实现方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["宏 #define", "inline / constexpr 函数"]},
    ],
    "metrics": [
        {"key": "sites", "label": "调用点数", "expr": "sitesK * 1000", "unit": "个", "fmt": "int"},
        # 宏：每个调用点一份代码，每条语句约 4 字节
        {"key": "macroKB", "label": "宏展开代码体积", "expr": "sitesK * 1000 * stmts * 4 / 1024", "unit": "KB", "fmt": "int"},
        # 函数：只一份
        {"key": "funcKB", "label": "函数方案代码体积", "expr": "stmts * 4 / 1024 + 0.01", "unit": "KB", "fmt": "fix2"},
        # 当前方案
        {"key": "chosenKB", "label": "当前方案体积", "expr": "if(mode == 1, funcKB, macroKB)", "unit": "KB", "fmt": "fix2"},
        # I-cache 压力：展开的代码要跨多少个 32KB 的 L1i
        {"key": "icachePages", "label": "占用的 L1i 块数", "expr": "if(mode == 1, 1, sitesK * 1000 * stmts * 4 / 32768)", "unit": "块", "fmt": "int"},
        # 编译时间：宏在每个 TU 都要重新展开一遍
        {"key": "compileMs", "label": "展开耗时", "expr": "sites * stmts / 100", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        # 下限：上万个调用点，规模真实（日志宏就是这样）
        {"expr": "sites >= 10000", "label": "调用点 ≥1 万（真实工程里日志/断言宏的量级）"},
        # 痛点：宏方案确实膨胀
        {"expr": "macroKB >= 512", "label": "宏展开 ≥512KB（这就是要解决的痛点）"},
        # 上限：当前方案压进 16KB
        {"expr": "chosenKB <= 16", "label": "当前方案 ≤16KB（一份实现就够）"},
    ],
    "insight": (
        "宏做的是**文本替换**，编译器看不到「这是同一个函数」。两万个调用点就是两万份代码，"
        "每条语句 4 字节，20 条语句 × 2 万 = 1.6MB——塞满了指令缓存，"
        "热路径反而因为 I-cache miss 变慢。"
        "`inline` 函数只生成一份（编译器决定是否真的内联），其余走 call 复用；"
        "`constexpr` 更进一步，能在编译期算完的直接变成常量。"
        "而且宏还附带三个坑：没有类型检查、参数会被求值多次（`MAX(i++, j)`）、"
        "没有作用域（内部变量名污染调用点）。"
        "**现代 C++ 的判据**：能用 `constexpr` 函数就不用 `inline` 函数，"
        "能用 `inline` 函数就不用宏；宏只留给三件事——"
        "条件编译（`#if`）、字符串化（`#x`）、以及需要拿到调用点信息的断言/日志"
        "（`__FILE__`/`__LINE__`，这类用 `std::source_location` 也能替代）。"
    ),
}


# ============================================================================
# cpp/cpp-ch15 · 五百个源文件，为什么改一行要等十分钟
# ----------------------------------------------------------------------------
# 教学点：#include 是**文本粘贴**。一个 1 万行的头文件被 500 个 TU 各包含一次，
# 编译器就要解析 500 万行。C++20 模块把这 1 万行只编译一次，产出 BMI，
# 每个 TU 加载 BMI 只花常数时间——编译时间从 O(TU × 头文件) 降到 O(头文件 + TU)。
# ============================================================================
cpp_ch15 = {
    "kind": "sandbox",
    "title": "五百个源文件，为什么改一行要等十分钟",
    "brief": (
        "`#include` 本质是文本粘贴：一个 1 万行的头文件被 500 个 .cpp 各包含一次，"
        "编译器就要把这一万行解析 500 遍——500 万行，全是重复劳动。"
        "C++20 模块把这份头文件只编译一次、产出二进制接口（BMI），"
        "每个 TU 加载 BMI 是常数时间。"
        "把 TU 数与头文件规模拖到真实工程的量级，看这条线性增长从哪来。"
    ),
    "params": [
        # 编译单元数
        {"key": "tu", "label": "编译单元（.cpp）数", "min": 50, "max": 1000, "step": 50, "value": 500},
        # 公共头文件行数（千行）
        {"key": "hLinesK", "label": "公共头文件行数（千行）", "min": 1, "max": 20, "step": 1, "value": 10},
        # 方案：0 = #include，1 = C++20 模块
        {"key": "mode", "label": "组织方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["#include 头文件", "C++20 模块"]},
    ],
    "metrics": [
        # #include：每个 TU 都解析一遍头文件
        {"key": "headerLines", "label": "#include 解析行数", "expr": "tu * hLinesK * 1000", "unit": "行", "fmt": "int"},
        # 模块：头文件编译一次 + 每个 TU 加载 BMI（约 50 行等价成本）
        {"key": "moduleLines", "label": "模块方案等效行数", "expr": "hLinesK * 1000 + tu * 50", "unit": "行", "fmt": "int"},
        # 当前方案
        {"key": "chosenLines", "label": "当前方案等效行数", "expr": "if(mode == 1, moduleLines, headerLines)", "unit": "行", "fmt": "int"},
        # 编译时间：每 100 万行约 2 秒
        {"key": "sec", "label": "编译耗时", "expr": "chosenLines * 2 / 1000000", "unit": "秒", "fmt": "fix2"},
        # 改一次头文件要重编多少个 TU（这里是依赖数，两种方式都一样）
        {"key": "rebuild", "label": "改头文件后重编 TU", "expr": "tu", "unit": "个", "fmt": "int"},
        # 倍数
        {"key": "ratio", "label": "#include / 模块", "expr": "headerLines / moduleLines", "unit": "倍", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：200 个 TU、规模真实
        {"expr": "tu >= 200", "label": "编译单元 ≥200 个（真实中型工程规模）"},
        # 痛点：#include 要解析上百万行
        {"expr": "headerLines >= 2000000", "label": "#include 解析 ≥200 万行（这就是编译慢的根因）"},
        # 上限：当前方案压进 10 万行等效
        {"expr": "chosenLines <= 100000", "label": "当前方案 ≤10 万行等效（约 0.2 秒）"},
    ],
    "insight": (
        "C++ 的编译慢有一半来自 `#include` 的语义：它把被包含文件的**全文**粘进当前 TU，"
        "再由编译器重新解析、重建符号表。500 个 TU 包含同一个 1 万行头文件，"
        "就是 500 万行重复解析——而你只改了一行注释。"
        "三种缓解手段的层次："
        "① **前向声明 + 只在 .cpp 里 include**（最便宜，立刻见效）；"
        "② **PCH 预编译头**（`target_precompile_headers`），只省解析不省语义；"
        "③ **C++20 模块**：头文件编译一次产出 BMI，TU 只 `import`——"
        "这才是从 O(TU × N) 降到 O(TU + N)。"
        "注意 `rebuild` 那行：模块**没有自动解决**「改头文件重编所有下游」的问题，"
        "依赖图还是要正确（`ninja`/`ccache` 的用武之地）。"
    ),
}


# ============================================================================
# cpp/cpp-ch17 · 递归模板实例化一万层，编译器先崩
# ----------------------------------------------------------------------------
# 教学点：`template<int N> struct Sum { enum { v = N + Sum<N-1>::v }; };`
# 会实例化 N 个不同的类型，每个都要占编译器内存、写进调试信息，
# 默认模板深度限制 900 层、递归超过就报 "template instantiation depth exceeded"。
# 折叠表达式 `(args + ...)` 或 `constexpr` 循环只展开成一个表达式。
# ============================================================================
cpp_ch17 = {
    "kind": "sandbox",
    "title": "递归模板实例化一万层，编译器先崩",
    "brief": (
        "想用模板算 `1+2+...+N`，教科书写法是 `Sum<N>` 递归继承 `Sum<N-1>`——"
        "这会实例化 N 个**不同类型**，每个都进符号表和调试信息，"
        "编译器默认只允许 900 层深度，一万层直接报错退出。"
        "C++17 的折叠表达式 `(args + ...)` 一次展开，只产生一个表达式。"
        "把规模拖到真实元编程代码的量级，看编译器要背多少份实例化。"
    ),
    "params": [
        # 模板参数规模（千层）
        {"key": "nK", "label": "模板规模（千）", "min": 1, "max": 100, "step": 1, "value": 50},
        # 实现方式：0 = 递归模板，1 = 折叠表达式
        {"key": "mode", "label": "实现方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["递归模板实例化", "折叠表达式 / constexpr"]},
    ],
    "metrics": [
        {"key": "n", "label": "规模 N", "expr": "nK * 1000", "unit": "层", "fmt": "int"},
        # 递归方案：N 份实例化
        {"key": "naiveInsts", "label": "递归实例化份数", "expr": "nK * 1000", "unit": "份", "fmt": "int"},
        # 折叠表达式：1 份
        {"key": "foldInsts", "label": "折叠表达式份数", "expr": "1", "unit": "份", "fmt": "int"},
        # 当前方案
        {"key": "insts", "label": "当前实例化份数", "expr": "if(mode == 1, foldInsts, naiveInsts)", "unit": "份", "fmt": "int"},
        # 编译耗时：每份实例化约 5μs
        {"key": "compileMs", "label": "编译耗时", "expr": "insts * 5 / 1000", "unit": "ms", "fmt": "int"},
        # 模板递归深度：对比编译器默认上限 900
        {"key": "depth", "label": "模板递归深度", "expr": "if(mode == 1, 1, nK * 1000)", "unit": "层", "fmt": "int"},
        # 是否超过默认深度限制
        {"key": "overLimit", "label": "超出默认深度上限", "expr": "if(depth > 900, 1, 0)", "unit": "", "fmt": "int"},
    ],
    "checks": [
        # 下限：一万层起，小规模递归模板确实没感觉
        {"expr": "n >= 10000", "label": "规模 ≥1 万（真实元编程代码的量级）"},
        # 痛点：递归方案确实要实例化上万份
        {"expr": "naiveInsts >= 10000", "label": "递归方案 ≥1 万份实例化（这就是要解决的痛点）"},
        # 上限：当前方案编译耗时压进 50ms
        {"expr": "compileMs <= 50", "label": "编译耗时 ≤50ms"},
        # 硬约束：不能超出编译器默认模板深度（900）
        {"expr": "depth <= 900", "label": "递归深度 ≤900（编译器默认上限，超了直接编译失败）"},
    ],
    "insight": (
        "模板实例化不是「编译期免费」：每个 `Sum<k>` 都是一个**独立类型**，"
        "要占符号表、调试信息、还要参与重载决议。一万层就是一万个类型，"
        "编译时间线性涨、内存跟着涨，超过默认深度 900 还会直接报错。"
        "C++17 的折叠表达式把整个展开压成一个表达式："
        "`(std::forward<Ts>(args) + ...)` 编译期只走一遍 AST，运行期是 N-1 条加法指令。"
        "`constexpr` 函数循环是另一条路——它算的是值，不产生类型。"
        "判断标准很清楚：**要「类型」才用模板递归（typelist、tuple 展开），"
        "要「值」就用折叠表达式或 constexpr**。"
        "现代代码里还在用递归模板算数值的，基本都是没跟上 C++17 的老写法。"
    ),
}


# ============================================================================
# cpp/cpp-ch19 · 一万个测试串行跑，CI 从八十分钟压到六分钟
# ----------------------------------------------------------------------------
# 教学点：CI 时间 = 固定开销（checkout + 构建）+ 测试总时间 / 并行度。
# 串行跑一万个 500ms 的测试 = 83 分钟；16 路并行只要 5 分钟，
# 但固定开销那 1 分钟压不下去——这就是 Amdahl 定律在流水线上的样子。
# ============================================================================
cpp_ch19 = {
    "kind": "sandbox",
    "title": "一万个测试串行跑，CI 从八十分钟压到六分钟",
    "brief": (
        "CI 的总时长 = 固定开销（拉代码、配置、编译，约 1 分钟）+ 跑测试的时间 / 并行度。"
        "一万个测试、每个 500ms，串行跑是 83 分钟，开发者的每次提交都要等一个多小时。"
        "并行到 16 路只要 5 分钟——但再怎么加机器也压不到 1 分钟以下，"
        "那是固定开销，正是 Amdahl 定律限制的部分。"
        "把测试数与并行度拖到真实流水线规模，看这条曲线怎么变平。"
    ),
    "params": [
        # 测试数
        {"key": "testsK", "label": "测试数（千个）", "min": 1, "max": 20, "step": 1, "value": 10},
        # 单测试耗时（ms）
        {"key": "testMs", "label": "单测试耗时", "min": 100, "max": 2000, "step": 100, "value": 500, "unit": "ms"},
        # 并行度（同时跑几个 job）
        {"key": "parallel", "label": "并行度", "min": 1, "max": 32, "step": 1, "value": 1},
    ],
    "metrics": [
        {"key": "tests", "label": "测试数", "expr": "testsK * 1000", "unit": "个", "fmt": "int"},
        # 串行总时长（分钟）：tests × testMs / 60000
        {"key": "serialMin", "label": "串行总时长", "expr": "testsK * 1000 * testMs / 60000", "unit": "分钟", "fmt": "fix2"},
        # 固定开销 60 秒
        {"key": "fixedSec", "label": "固定开销（checkout+构建）", "expr": "60", "unit": "秒", "fmt": "int"},
        # 并行后总时长（分钟）
        {"key": "totalMin", "label": "并行后总时长", "expr": "60 / 60 + testsK * 1000 * testMs / parallel / 60000", "unit": "分钟", "fmt": "fix2"},
        # 加速比
        {"key": "speedup", "label": "加速比", "expr": "(testsK * 1000 * testMs / 60000) / totalMin", "unit": "倍", "fmt": "fix2"},
        # 理论下限：固定开销那 1 分钟
        {"key": "floorMin", "label": "理论下限（固定开销）", "expr": "1", "unit": "分钟", "fmt": "int"},
    ],
    "checks": [
        # 下限：5000 个测试，规模真实
        {"expr": "tests >= 5000", "label": "测试数 ≥5000（真实项目的集成测试量级）"},
        # 下限：串行确实慢到不可接受
        {"expr": "serialMin >= 30", "label": "串行 ≥30 分钟（这就是要解决的痛点）"},
        # 上限：并行后压进 10 分钟
        {"expr": "totalMin <= 10", "label": "并行后 ≤10 分钟（开发者可接受的反馈时间）"},
    ],
    "insight": (
        "CI 时长可以拆成两段：**固定开销**（拉代码、装依赖、编译，1 分钟）"
        "和**可并行部分**（跑测试，`tests × testMs`）。加机器只能压第二段，"
        "所以 Amdahl 定律给出的下界就是固定开销那一分钟——从 83 分钟压到 5 分钟后，"
        "再加到 32 路并行也只能从 5 分钟降到 3.6 分钟，收益迅速归零。"
        "真正有效的优化顺序是："
        "① 先把固定开销压下去（缓存依赖、增量构建、ccache）；"
        "② 再切分慢测试（一个跑 10 分钟的测试会拖死整个 job）；"
        "③ 最后才加并行度。"
        "另外并行度不等于机器数：测试之间有共享资源（数据库、端口、临时目录）时，"
        "盲上加并行会变成互相踩，收益远低于线性。"
    ),
}


MODULES = {
    "cpp/cpp-ch02": cpp_ch02,
    "cpp/cpp-ch04": cpp_ch04,
    "cpp/cpp-ch07": cpp_ch07,
    "cpp/cpp-ch09": cpp_ch09,
    "cpp/cpp-ch11": cpp_ch11,
    "cpp/cpp-ch12": cpp_ch12,
    "cpp/cpp-ch13": cpp_ch13,
    "cpp/cpp-ch14": cpp_ch14,
    "cpp/cpp-ch15": cpp_ch15,
    "cpp/cpp-ch17": cpp_ch17,
    "cpp/cpp-ch19": cpp_ch19,
}


def main() -> int:
    """读取 labs.json → 写入 11 个 sandbox → 按仓库风格（indent=1/LF）落盘。"""
    with open(LABS, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.setdefault("chapters", {})
    existed = sum(1 for k in MODULES if k in chapters)
    for key, mod in MODULES.items():
        # 幂等 + 不吞同章其它玩法：只替换本章的 sandbox，保留 debug 等其它模块。
        # （cpp 这 11 章原本各带一个 debug 模块，直接 chapters[key]=[mod] 会静默抹掉）
        kept = [m for m in chapters.get(key, []) if m.get("kind") != "sandbox"]
        chapters[key] = [mod] + kept
        extra = f"（保留其它模块 {len(kept)} 个）" if kept else ""
        print(f"added {key:<16} ({len(mod['params'])} params / {len(mod['metrics'])} metrics / {len(mod['checks'])} checks){extra}")

    with open(LABS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"written {os.path.normpath(LABS)}  (共 {len(chapters)} 章有精修模块，本次覆盖 {len(MODULES)}，其中已存在 {existed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
