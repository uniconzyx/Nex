# -*- coding: utf-8 -*-
"""批次九：给 clang 七单元 + java 七章补 sandbox（两学科首次接入交互玩法）。

与前几批同一套路：写进 content/_handmade/labs.json 的 chapters，
再由 gen_interactive.py 并入各章 interactive.json 与前端数据。

为什么是这十四章
-------------
C 和 Java 的初学者困惑大多被讲成「记住这个结论」，但每一个结论背后都有一笔
能算的账，而且算出来往往比结论本身更吓人：

  clang-u01  数组名当参数会退化成指针，函数里 sizeof 永远是 8——不传长度就丢数据
  clang-u02  glibc 最小 chunk 32 字节，24 字节的结构体实际吃 32 字节
  clang-u03  char/int/char/double 排下来 24 字节，按大小重排只要 16
  clang-u04  逐字节 fputc 一个 256MB 文件 = 2.7 亿次系统调用
  clang-u05  头文件守卫只防同一 TU 内重复包含，防不住 N 个 TU 各解析一遍
  clang-u06  改一行代码等两分钟：全量重编 + 头文件耦合 + 单线程
  clang-u07  静态链接让「修一个 CVE 要重发 N 个程序」

  java-ch01  金额用 double 累加，一千万笔差出几百块，对账永远不平
  java-ch02  Integer[] 比 int[] 贵 5 倍：每个元素多一个 16 字节对象头
  java-ch03  多实现调用点退化成 megamorphic，JIT 不再内联，慢 10 倍
  java-ch04  HashMap 不预设容量：200 万条要扩容 18 次、搬 800 万个节点
  java-ch05  用异常做控制流：每次 fillInStackTrace 都拍一份完整栈快照
  java-ch06  FileInputStream 逐字节读 512MB = 5 亿次 read 系统调用
  java-ch09  Maven 首次构建大半时间在下载：73 个 jar、182MB、2MB/s

十四章共同点：**参数在真实项目里都能观测，配错了就是启动慢、内存翻倍、
对账不平、CPU 打满**——正好是沙盒最擅长的题材。

纪律（沿用前几批）
-----------------
1. checks 必须带规模下限（小规模怎么配都对，没教学意义）。
2. 不锁「正确答案」，让预算判据自己淘汰错方案。
3. 默认值 = 真实事故配置（教材写法 / 默认参数 / 新手写法）。
4. `if(c,a,b)` 急切求值 → 分支内除法保证除数非零常量。
5. fmt 只认 int / fix2 / pct；不支持科学计数法。
6. 判据阈值留 5% 以上余量。

写盘必须 indent=1 + newline="\\n"；且只替换本章 sandbox、保留 debug 等其它模块。
"""
import json
import os

LABS = os.path.join(os.path.dirname(__file__), "..", "content", "_handmade", "labs.json")


# ============================================================================
# clang/clang-u01 · 函数里的 sizeof 永远是 8
# ----------------------------------------------------------------------------
# 教学点：数组名作函数参数时退化成指向首元素的指针，函数内 sizeof(arr) 拿到的是
# 指针大小（64 位 = 8 字节），不是数组总字节数。`sizeof(arr)/sizeof(arr[0])`
# 这个"标准写法"在函数里恒等于 2（8/4）——遍历两个元素就停，剩下全漏；
# 若按"总长度"去写循环，则越界读。
# 唯一正解：把长度一起传进来（显式参数 / 结构体带 len / C23 的
# `int arr[static n]`）。这是 C 语言最经典的静默错误之一。
# ============================================================================
clang_u01 = {
    "kind": "sandbox",
    "title": "函数里的 sizeof 永远是 8",
    "brief": (
        "`void walk(int arr[])` 里的 `arr` 已经不是数组，是指针。"
        "于是 `sizeof(arr) / sizeof(arr[0])` 算出 `8 / 4 = 2`——"
        "无论你传进来一千个还是一万个元素，函数都只认两个。"
        "把数组规模与传参方式拖到真实体量，看这个「标准写法」漏掉多少数据、"
        "或者按真实长度去循环会越界读多少字节。"
    ),
    "params": [
        # 数组元素数
        {"key": "total", "label": "数组元素数", "min": 10, "max": 5000, "step": 10, "value": 1000},
        # 传参方式
        {"key": "pass", "label": "函数接收方式", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["只传 int arr[]", "传 arr + len", "传带 len 的结构体"]},
    ],
    "metrics": [
        # 函数内 sizeof(arr)：恒定 8 字节（指针大小），与数组多长无关
        {"key": "sizeofInFunc", "label": "函数内 sizeof(arr)", "expr": "8", "unit": "字节", "fmt": "int"},
        # 按 sizeof 推算出来的元素个数
        {"key": "believed", "label": "sizeof 推算的元素数", "expr": "if(pass == 0, 2, total)", "unit": "个", "fmt": "int"},
        # 真正被处理到的元素
        {"key": "handled", "label": "实际处理元素数", "expr": "if(pass == 0, 2, total)", "unit": "个", "fmt": "int"},
        # 漏掉的元素
        {"key": "missed", "label": "漏掉的元素数", "expr": "if(pass == 0, total - 2, 0)", "unit": "个", "fmt": "int"},
        # 若按真实长度去循环，越界读的字节数（每个 int 4 字节）
        {"key": "oobBytes", "label": "越界读字节", "expr": "if(pass == 0, (total - 2) * 4, 0)", "unit": "字节", "fmt": "int"},
        # 漏掉的数据占全量比例
        {"key": "missPct", "label": "漏掉的数据占比", "expr": "if(pass == 0, (total - 2) * 100 / total, 0)", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        # 下限：一千起的数组才有意义，两个元素的数组漏不漏无所谓
        {"expr": "total >= 500", "label": "数组 ≥500 个元素（真实的数据数组）"},
        # 上限：不许越界
        {"expr": "oobBytes <= 0", "label": "越界读 0 字节（UB 一次都不能有）"},
        # 上限：不许漏数据
        {"expr": "missed <= 0", "label": "漏掉 0 个元素（每个元素都要处理到）"},
    ],
    "insight": (
        "`sizeof(arr)` 在函数里恒等于 8，因为形参 `int arr[]` 被编译器改写成 `int *arr`——"
        "**数组名在参数位置一定会退化成指针**，这是 C 语言规定的，没有例外。"
        "所以 `sizeof(arr)/sizeof(arr[0])` 只在**同一作用域内的真数组**上成立，"
        "一旦跨过函数边界就变成 `8/4 = 2`，是个能编译、能跑、结果错一半的静默 bug。"
        "三种正解："
        "① **显式传长度**（`walk(arr, n)`）——最常见，缺点是要调用方保证 `n` 正确；"
        "② **结构体打包**（`struct arr { int *p; size_t n; }`）——长度和指针绑在一起，传不错；"
        "③ **C23 的 `int arr[static n]`**（或 GCC 的 `arr[static n]`）——把长度写进形参类型，"
        "编译器还能据此做优化提示。"
        "C++ 里对应的是 `std::span` 或 `template <size_t N> void walk(int (&arr)[N])`。"
        "顺带一个残酷事实：`-Wall -Wextra` 对这条**不报警**（数组下标是真的，"
        "只是商家算错了长度），`-Wsizeof-array-argument` 也得你主动开。"
    ),
}


# ============================================================================
# clang/clang-u02 · 24 字节的结构体，堆上吃了 32 字节
# ----------------------------------------------------------------------------
# 教学点：glibc malloc 每块都有 chunk 头（size 字段），且按 16 字节对齐，
# 最小 chunk 32 字节。于是请求 24 字节 → 实占 32（33% 内部碎片）；
# 请求 8 字节 → 也占 32（300%）。更要命的是每次 malloc/free 都是一次
# 分配器操作（约 50ns），百万次就是几十毫秒的纯开销。
# 池化/arena 一次要一大块再自己切，省掉每块的头与每次调用。
# ============================================================================
clang_u02 = {
    "kind": "sandbox",
    "title": "24 字节的结构体，堆上吃了 32 字节",
    "brief": (
        "`malloc(24)` 拿到的看着是 24 字节，实际从分配器手里切走的是 32 字节："
        "每块有 8 字节 chunk 头，再按 16 字节向上取整，最小块 32。"
        "而且每调一次 `malloc`/`free` 都要走一趟分配器（约 50ns）。"
        "把记录数与结构体大小拖到真实体量，看「一个个分配」和「一次要一大块自己切」"
        "在堆占用和调用次数上差多少。"
    ),
    "params": [
        # 记录数（千）
        {"key": "recordsK", "label": "记录数（千）", "min": 10, "max": 2000, "step": 10, "value": 200},
        # 单条记录字节数
        {"key": "size", "label": "单条记录大小", "min": 8, "max": 256, "step": 8, "value": 24},
        # 分配策略
        {"key": "mode", "label": "分配策略", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["每条一次 malloc", "批量池化（arena）"]},
    ],
    "metrics": [
        # 实际记录数
        {"key": "records", "label": "记录数", "expr": "recordsK * 1000", "unit": "条", "fmt": "int"},
        # glibc chunk：size + 8 字节头，16 字节对齐，最小 32
        {"key": "chunk", "label": "每块实际占用（malloc）", "expr": "max(32, round(ceil((size + 8) / 16) * 16))", "unit": "字节", "fmt": "int"},
        # arena 切片：8 字节对齐，无每块头
        {"key": "arenaChunk", "label": "每块实际占用（池化）", "expr": "round(ceil(size / 8) * 8)", "unit": "字节", "fmt": "int"},
        # 当前策略每块占用
        {"key": "perRecord", "label": "当前每记录占用", "expr": "if(mode == 0, max(32, round(ceil((size + 8) / 16) * 16)), round(ceil(size / 8) * 8))", "unit": "字节", "fmt": "int"},
        # 内部碎片率
        {"key": "overheadPct", "label": "内部碎片率", "expr": "if(mode == 0, (max(32, round(ceil((size + 8) / 16) * 16)) - size) * 100 / size, (round(ceil(size / 8) * 8) - size) * 100 / size)", "unit": "%", "fmt": "int"},
        # 堆总量
        {"key": "heapMB", "label": "堆占用", "expr": "records * if(mode == 0, max(32, round(ceil((size + 8) / 16) * 16)), round(ceil(size / 8) * 8)) / 1048576", "unit": "MB", "fmt": "int"},
        # 分配器调用次数（池化只一次大块）
        {"key": "allocCalls", "label": "malloc/free 调用次数", "expr": "if(mode == 0, records, 2)", "unit": "次", "fmt": "int"},
        # 分配开销：malloc 约 50ns/次，池化约 2ns/条（指针加法）
        {"key": "allocMs", "label": "分配开销", "expr": "if(mode == 0, records * 50 / 1000000, records * 2 / 1000000)", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        # 下限：十万条起，小数组栈上分配就完了
        {"expr": "records >= 100000", "label": "记录数 ≥10 万（真实的数据集）"},
        # 上限：内部碎片不超过 15%
        {"expr": "overheadPct <= 15", "label": "内部碎片率 ≤15%（堆不能一半喂给对齐）"},
        # 上限：分配器调用次数受控
        {"expr": "allocCalls <= 1000", "label": "malloc/free ≤1000 次（别让分配器成为热点）"},
        # 上限：分配开销别超过 10ms
        {"expr": "allocMs <= 10", "label": "分配开销 ≤10ms"},
    ],
    "insight": (
        "`malloc(24)` 的真实代价要分两层看。"
        "**空间层**：glibc 的每个 chunk 前面有 8 字节 size 字段，整块按 16 字节对齐，"
        "且最小 chunk 是 32 字节（要能装下 free list 的两个指针）。"
        "所以 `malloc(24)` 实占 32（+33%），`malloc(8)` 也占 32（+300%）。"
        "**时间层**：每次 `malloc`/`free` 都要走空闲链表、可能触发 `brk`/`mmap`、"
        "要做合并——约 50ns/次，一百万次就是 50 毫秒纯开销，还没算上缓存局部性变差。"
        "**正解是减少分配次数而不是减少字节数**："
        "① **arena / 池化**：一次 `malloc(n * sizeof(T))`，自己用下标切；"
        "② **对象池 / free list**：回收复用，稳态零分配；"
        "③ **小对象分配器**（jemalloc / tcmalloc）把 size class 分得更细，"
        "对 24 字节这类尺寸的内部碎片比 glibc 小；"
        "④ C++ 侧用 `std::pmr::monotonic_buffer_resource` 或 `vector` 预留容量。"
        "反向的坑：池化后**每个对象不能单独 `free`**，生命周期要统一管理；"
        "池子按峰值大小长期占住，可能换来 RSS 不降——这是空间换时间的明账。"
    ),
}


# ============================================================================
# clang/clang-u03 · 字段顺序换一下，内存省三分之一
# ----------------------------------------------------------------------------
# 教学点：结构体成员按声明顺序排布，每个成员都要落在自身对齐要求上，
# 中间补 padding、末尾补齐到最大对齐。`{char, int, char, double}` 排下来是
# 1 + 3pad + 4 + 1 + 7pad + 8 = 24 字节，而实际数据只有 14 字节。
# 按对齐降序重排 `{double, int, char, char}` = 16 字节，padding 只剩 2。
# ============================================================================
clang_u03 = {
    "kind": "sandbox",
    "title": "字段顺序换一下，内存省三分之一",
    "brief": (
        "`struct { char a; int b; char c; double d; }` 的成员加起来 14 字节，"
        "`sizeof` 却是 24——中间和末尾被补了 10 字节 padding。"
        "编译器不会替你重排字段（C 标准保证声明顺序即内存顺序）。"
        "把记录数与字段顺序拖到真实体量，看这一行「调换顺序」能省下多少内存、"
        "以及每个缓存行里有多少字节是白读的。"
    ),
    "params": [
        # 记录数（万条）
        {"key": "recordsW", "label": "记录数（万）", "min": 10, "max": 800, "step": 10, "value": 200},
        # 字段顺序
        {"key": "order", "label": "字段声明顺序", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["char,int,char,double", "double,int,char,char"]},
    ],
    "metrics": [
        {"key": "records", "label": "记录数", "expr": "recordsW * 10000", "unit": "条", "fmt": "int"},
        # 声明顺序 char@0 int@4 char@8 double@16 → 24
        # 重排        double@0 int@8 char@12 char@13 → 16
        {"key": "sizeBytes", "label": "sizeof(struct)", "expr": "if(order == 0, 24, 16)", "unit": "字节", "fmt": "int"},
        # 真实数据 1+4+1+8 = 14 字节
        {"key": "payloadBytes", "label": "真实数据字节", "expr": "14", "unit": "字节", "fmt": "int"},
        # padding = sizeof - payload
        {"key": "paddingBytes", "label": "padding 字节", "expr": "if(order == 0, 10, 2)", "unit": "字节", "fmt": "int"},
        # 总内存
        {"key": "totalMB", "label": "数组总占用", "expr": "recordsW * 10000 * sizeBytes / 1048576", "unit": "MB", "fmt": "int"},
        # 纯 padding 浪费
        {"key": "padMB", "label": "其中 padding 浪费", "expr": "recordsW * 10000 * if(order == 0, 10, 2) / 1048576", "unit": "MB", "fmt": "int"},
        # 顺序扫描时的有效字节率
        {"key": "usefulPct", "label": "缓存有效字节率", "expr": "if(order == 0, 58, 88)", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        # 下限：百万条起，十几条记录怎么排都无所谓
        {"expr": "records >= 1000000", "label": "记录数 ≥100 万（真实的表/数组规模）"},
        # 上限：padding 压到 2 字节以内
        {"expr": "paddingBytes <= 2", "label": "padding ≤2 字节（只允许末尾对齐补齐）"},
        # 上限：总内存受控
        {"expr": "totalMB <= 40", "label": "总占用 ≤40MB"},
        # 下限：缓存有效字节率（说明不是靠砍数据过的）
        {"expr": "usefulPct >= 80", "label": "缓存有效字节率 ≥80%（真实数据要占满缓存行）"},
    ],
    "insight": (
        "结构体的 `sizeof` 由三件事决定：**成员顺序**（C 保证按声明顺序排）、"
        "**每个成员的对齐要求**（`char` 1、`short` 2、`int` 4、`double`/指针 8）、"
        "**结构体整体对齐 = 最大成员的对齐**（末尾也要补齐）。"
        "`{char, int, char, double}`：`char`@0，`int` 要 4 对齐所以 @4（补 3），`char`@8，"
        "`double` 要 8 对齐所以 @16（补 7），尾部已是 8 的倍数 → **24 字节，10 字节 padding**。"
        "按对齐降序重排 `{double, int, char, char}`：@0 / @8 / @12 / @13，"
        "尾部补齐到 16 → **16 字节，padding 只剩 2**。省 33%，纯靠调顺序，零成本。"
        "三条实操："
        "① **按对齐从大到小声明**（`double/long long/指针` → `int/float` → `short` → `char/bool`），"
        "这是唯一一条不需要思考就永远成立的规则；"
        "② 百万级数组要考虑 **AoS → SoA**（结构体数组改成数组结构体），"
        "顺序扫描只读用到的列，缓存命中率能翻倍；"
        "③ 真要压字节再上 `__attribute__((packed))`——但**会破坏对齐**，"
        "非对齐访问在 x86 上只是慢，在 ARM 上可能直接 fault，而且取地址会 UB。"
        "别忘了 `sizeof` 会和文件格式/网络协议绑定：落盘或发网络前先定死布局，"
        "否则换个编译器版本 padding 变了，旧数据就读不出来了（正解是用序列化库或显式 padding 字段）。"
    ),
}


# ============================================================================
# clang/clang-u04 · 逐字节写文件 = 两亿七千万次系统调用
# ----------------------------------------------------------------------------
# 教学点：`fputc` 一次写一个字节。若流是全缓冲（默认对普通文件），
# 满 4KB 才真正 write 一次；但很多新手用 `setbuf(f, NULL)` 或 write(2)
# 逐字节写，就变成每字节一次系统调用（约 1μs），256MB = 2.7 亿次 = 268 秒。
# fputc 本身的用户态调用也不免费：每字节一次函数调用（约 5ns）。
# ============================================================================
clang_u04 = {
    "kind": "sandbox",
    "title": "逐字节写文件 = 两亿七千万次系统调用",
    "brief": (
        "`while (c = *p++) fputc(c, fp);` 看着很自然。"
        "如果没有缓冲，每个字节都要掉进内核一次 `write`，一次约 1 微秒——"
        "256MB 就是 2.7 亿次、268 秒。加了 4KB 缓冲后系统调用降到 6.5 万次，"
        "但 `fputc` 的每字节函数调用还在（用户态 1.3 秒）。"
        "把文件大小与缓冲方式拖到真实体量，看时间花在内核还是用户态。"
    ),
    "params": [
        # 文件大小（MB）
        {"key": "fileMB", "label": "文件大小", "min": 1, "max": 1024, "step": 1, "value": 256},
        # 写入方式
        {"key": "mode", "label": "写入方式", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["无缓冲逐字节", "4KB 缓冲逐字节", "64KB 缓冲逐字节"]},
    ],
    "metrics": [
        {"key": "bytes", "label": "总字节数", "expr": "fileMB * 1048576", "unit": "字节", "fmt": "int"},
        # 用户态：每字节一次 fputc 调用（约 5ns），与缓冲无关
        {"key": "userMs", "label": "用户态 fputc 开销", "expr": "fileMB * 1048576 * 5 / 1000000", "unit": "ms", "fmt": "int"},
        # 缓冲块大小
        {"key": "bufKB", "label": "缓冲块大小", "expr": "if(mode == 0, 0, if(mode == 1, 4, 64))", "unit": "KB", "fmt": "int"},
        # 系统调用次数：无缓冲时每字节一次
        {"key": "syscalls", "label": "write 系统调用次数", "expr": "if(mode == 0, fileMB * 1048576, fileMB * 1024 / if(mode == 1, 4, 64))", "unit": "次", "fmt": "int"},
        # 系统调用耗时：约 1μs/次
        {"key": "sysMs", "label": "内核态开销", "expr": "if(mode == 0, fileMB * 1048576 / 1000, fileMB * 1024 / if(mode == 1, 4, 64) / 1000)", "unit": "ms", "fmt": "int"},
        # 总耗时
        {"key": "totalMs", "label": "总写入耗时", "expr": "fileMB * 1048576 * 5 / 1000000 + if(mode == 0, fileMB * 1048576 / 1000, fileMB * 1024 / if(mode == 1, 4, 64) / 1000)", "unit": "ms", "fmt": "int"},
        # 吞吐
        {"key": "mbps", "label": "有效吞吐", "expr": "fileMB * 1000 / (fileMB * 1048576 * 5 / 1000000 + if(mode == 0, fileMB * 1048576 / 1000, fileMB * 1024 / if(mode == 1, 4, 64) / 1000))", "unit": "MB/s", "fmt": "fix2"},
        # 用户态占比
        {"key": "userPct", "label": "用户态占比", "expr": "userMs * 100 / totalMs", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        # 下限：128MB 起，小文件怎么写都瞬间完成
        {"expr": "fileMB >= 128", "label": "文件 ≥128MB（日志/导出/镜像这类真实体量）"},
        # 上限：系统调用次数受控
        {"expr": "syscalls <= 100000", "label": "write 调用 ≤10 万次（别让 syscall 成为瓶颈）"},
        # 上限：总耗时
        {"expr": "totalMs <= 5000", "label": "总耗时 ≤5 秒"},
        # 上限：吞吐
        {"expr": "mbps >= 40", "label": "吞吐 ≥40MB/s"},
    ],
    "insight": (
        "写文件的时间由两段相加：**用户态每字节的函数调用** + **内核态每次 write 的切换成本**。"
        "`fputc` 本身约 5ns（一次函数调用 + 缓冲区判满），`write` 系统调用约 1μs"
        "（用户态/内核态切换 + VFS + 页缓存拷贝）。"
        "256MB：无缓冲 = 2.7 亿次 syscall ≈ 268 秒；4KB 缓冲 = 6.5 万次 ≈ 65 毫秒，"
        "**差了四千倍**。而且缓冲后剩下的 1.3 秒全是 `fputc` 的每字节调用——"
        "这才是该上 `fwrite(buf, 1, n, fp)` 的时候：一次调用搬一整块，用户态开销直接消失。"
        "四层优化，按收益排序："
        "① **别关缓冲**（`setvbuf(fp, NULL, _IONBF, 0)` 是最常见的自伤）；"
        "② **整块 `fwrite`** 而不是逐字节 `fputc`；"
        "③ 大文件用 `writev`/`mmap` 或 `O_DIRECT`（绕过页缓存，适合顺序大 IO）；"
        "④ `fsync` 只在**需要持久性保证**时调，每写一次就 fsync 会把机械盘打到 100 IOPS 以下。"
        "还有一条容易忽略的：**缓冲不是万能的**，程序崩溃时缓冲区里的数据会丢；"
        "日志系统要在「每条日志 fsync」和「吞吐」之间明确取舍（通常选后者 + 定期 fsync）。"
    ),
}


# ============================================================================
# clang/clang-u05 · 头文件守卫治不了编译时间
# ----------------------------------------------------------------------------
# 教学点：`#ifndef/#define` 守卫只能防「同一个翻译单元里重复包含」，
# 而 N 个 .c 各自 include 同一个头时，每个 TU 都要从磁盘读一遍、预处理一遍、
# 词法语法语义分析一遍——守卫完全不起作用。200 个 TU × 3 万行头文件（含重复
# 间接包含 3 次）= 1800 万行解析，约 18 秒。只有预编译头（PCH）/ C++20 模块
# 能把「解析」这件事做成一次。
# ============================================================================
clang_u05 = {
    "kind": "sandbox",
    "title": "头文件守卫治不了编译时间",
    "brief": (
        "`#ifndef HEADER_H` 只挡住「同一个 .c 里重复包含」，挡不住「两百个 .c 各自包含一遍」。"
        "每个翻译单元都要把这个三万行的头重新读进来、重新解析、重新建符号表。"
        "把翻译单元数与头文件规模拖到真实体量，看守卫、去重、预编译头各自能省下多少——"
        "你会发现前两者对总时间几乎无效。"
    ),
    "params": [
        # 翻译单元数
        {"key": "tus", "label": "翻译单元数（.c）", "min": 10, "max": 600, "step": 10, "value": 200},
        # 头文件规模（千行）
        {"key": "headerK", "label": "头文件规模（千行）", "min": 1, "max": 60, "step": 1, "value": 30},
        # 单个 TU 内间接包含该头的次数
        {"key": "dup", "label": "每 TU 间接包含次数", "min": 1, "max": 5, "step": 1, "value": 3},
        # 头文件守卫
        {"key": "guard", "label": "头文件守卫", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["无守卫", "#ifndef 守卫"]},
        # 预编译头
        {"key": "pch", "label": "预编译头", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["不用 PCH", "预编译头 PCH"]},
    ],
    "metrics": [
        # 该头被真正解析的次数：PCH 只解析一次；守卫让每 TU 只解析一次；无守卫按 dup 次
        {"key": "parses", "label": "头文件被解析次数", "expr": "if(pch == 1, 1, tus * if(guard == 1, 1, dup))", "unit": "次", "fmt": "int"},
        # 总解析行数
        {"key": "parseLines", "label": "总解析行数", "expr": "if(pch == 1, headerK * 1000, tus * headerK * 1000 * if(guard == 1, 1, dup))", "unit": "行", "fmt": "int"},
        # 解析耗时：约 100 万行/秒（预处理 + 词法 + 语法 + 语义）
        {"key": "parseMs", "label": "头文件解析耗时", "expr": "if(pch == 1, headerK * 1000 / 1000, tus * headerK * if(guard == 1, 1, dup))", "unit": "ms", "fmt": "int"},
        # PCH 加载：每 TU 一次 mmap + 反序列化，约 5ms
        {"key": "pchLoadMs", "label": "PCH 加载耗时", "expr": "if(pch == 1, tus * 5, 0)", "unit": "ms", "fmt": "int"},
        # 总预处理/编译前置耗时
        {"key": "totalMs", "label": "总耗时", "expr": "if(pch == 1, headerK * 1000 / 1000 + tus * 5, tus * headerK * if(guard == 1, 1, dup))", "unit": "ms", "fmt": "int"},
        # PCH 文件体积（约解析行数 / 20 KB）
        {"key": "pchMB", "label": "PCH 文件体积", "expr": "if(pch == 1, headerK * 1000 / 20 / 1024, 0)", "unit": "MB", "fmt": "int"},
    ],
    "checks": [
        # 下限：一百个 TU 起，单文件工程不需要 PCH
        {"expr": "tus >= 100", "label": "翻译单元 ≥100 个（真实的多文件工程）"},
        # 前提：头文件要足够大，预处理才会成为瓶颈
        {"expr": "headerK >= 20", "label": "头文件 ≥2 万行（重模板/大接口头）"},
        # 上限：总解析行数受控
        {"expr": "parseLines <= 2000000", "label": "总解析行数 ≤200 万行"},
        # 上限：总耗时 ≤3 秒
        {"expr": "totalMs <= 3000", "label": "总耗时 ≤3 秒"},
    ],
    "insight": (
        "**头文件守卫（include guard）解决的是「同一 TU 内重复包含」，"
        "不是「多 TU 重复解析」**。`#pragma once` 同理。"
        "200 个 `.c` 各自 `#include \"big.h\"`，`big.h` 就要被独立解析 200 次——"
        "守卫在每次编译新 TU 时都是「新的一局」，宏状态是空的。"
        "三种手段的收益量级："
        "① **守卫**：只去掉同一 TU 内的重复（本例 dup=3 → 3 倍降到 1 倍），"
        "对「多 TU 各一遍」的 N 倍完全无效；"
        "② **预编译头 PCH**（`g++ -x c++-header big.h` 或 CMake 的 `target_precompile_headers`）："
        "解析一次、序列化成二进制，之后每个 TU 直接 mmap 加载（约 5ms），"
        "把 N×T 变成 T + N×load——**这才是数量级的改善**；"
        "③ **C++20 模块（modules）**：`import big;` 从根本上不再有「文本包含」，"
        "编译器只构建一次 BMI，且不像 PCH 那样受宏状态影响，是长期正解。"
        "另外两条工程纪律：**头文件里少 include**（能前置声明就别 include 定义）、"
        "**用 `-H` 或 `clang -ftime-trace` 看是谁在拖时间**——"
        "真实项目里往往不是你的头，而是 `<iostream>`/`<regex>` 这类重型标准库头。"
    ),
}


# ============================================================================
# clang/clang-u06 · 改一行代码等两分钟
# ----------------------------------------------------------------------------
# 教学点：Makefile 的增量构建靠「目标比依赖新就跳过」。三个独立因素叠加成
# 两分钟：① 全量重编（`.PHONY: all` 或依赖写错导致每次都编）；② 头文件耦合
# （改一个 .h，所有 include 它的文件都要重编，60% 很常见）；③ 单线程（-j 没用上）。
# ============================================================================
clang_u06 = {
    "kind": "sandbox",
    "title": "改一行代码等两分钟",
    "brief": (
        "全量重编 600 个文件 × 每个 800 毫秒 = 8 分钟；就算写了增量规则，"
        "改一个头文件也会让 60% 的 .c 重编（它们都 include 了它）；再加上 `make` 不加 `-j`，"
        "永远单线程。三个因素叠起来就是「改一行等两分钟」。"
        "把文件数、构建模式、解耦程度、并行度拖到真实值，看每一个旋钮各能省多少。"
    ),
    "params": [
        # 源文件数
        {"key": "files", "label": "源文件数", "min": 10, "max": 2000, "step": 10, "value": 600},
        # 构建模式
        {"key": "mode", "label": "构建模式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["每次全量重编", "按 .o 时间戳增量"]},
        # 头文件解耦
        {"key": "decouple", "label": "头文件耦合度", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["头里 include 实现依赖（改头 60% 重编）", "前置声明+不透明指针（改头 10% 重编）"]},
        # 并行度
        {"key": "jobs", "label": "make -j 并行度", "min": 1, "max": 16, "step": 1, "value": 1},
    ],
    "metrics": [
        # 改头文件时受影响的文件比例
        {"key": "fanoutPct", "label": "改头文件影响面", "expr": "if(decouple == 1, 10, 60)", "unit": "%", "fmt": "int"},
        # 本次实际重编的文件数
        {"key": "recompiled", "label": "实际重编文件数", "expr": "if(mode == 0, files, round(files * if(decouple == 1, 10, 60) / 100))", "unit": "个", "fmt": "int"},
        # 单文件编译 800ms
        {"key": "perFileMs", "label": "单文件编译耗时", "expr": "800", "unit": "ms", "fmt": "int"},
        # 总耗时
        {"key": "buildMs", "label": "本次构建耗时", "expr": "if(mode == 0, files * 800 / jobs, round(files * if(decouple == 1, 10, 60) / 100) * 800 / jobs)", "unit": "ms", "fmt": "int"},
        # 相对「单线程全量」的加速比
        {"key": "speedup", "label": "相对单线程全量加速", "expr": "(files * 800) / (if(mode == 0, files * 800 / jobs, round(files * if(decouple == 1, 10, 60) / 100) * 800 / jobs))", "unit": "×", "fmt": "fix2"},
        # 每天改 50 次，一天浪费在等待上的时间
        {"key": "dailyMin", "label": "每天等待（改 50 次）", "expr": "buildMs * 50 / 60000", "unit": "分钟", "fmt": "int"},
    ],
    "checks": [
        # 下限：五百个文件起，十几个文件的工程怎么编都快
        {"expr": "files >= 500", "label": "源文件 ≥500 个（中大型工程）"},
        # 上限：重编文件数受控（说明真增量 + 低耦合）
        {"expr": "recompiled <= files * 15 / 100", "label": "重编文件 ≤总文件 15%（改一个头不该牵动半个工程）"},
        # 上限：单次构建 20 秒内
        {"expr": "buildMs <= 20000", "label": "单次构建 ≤20 秒"},
        # 下限：加速比至少 10 倍
        {"expr": "speedup >= 10", "label": "相比单线程全量加速 ≥10 倍"},
    ],
    "insight": (
        "编译慢是三个独立因素**相乘**的结果，所以也要三处一起改："
        "**① 增量**——`make` 的规则是「目标比所有依赖旧才重编」。"
        "写成 `.PHONY: all` 把 `all` 声明成伪目标没问题，但把**源文件也列成伪目标**"
        "（或依赖里写了不存在的文件）就会每次都全量。检查方法：`make -n` 看它要编几个。"
        "**② 解耦**——改一个 `.h` 导致 60% 重编，是因为那 60% 都 include 了它，"
        "而它又 include 了一堆实现依赖。正解是**前置声明 + 不透明指针**（PImpl）："
        "头里只写 `struct Foo;` 和函数签名，成员与 include 全搬进 `.c`；"
        "C++ 还可用 `std::unique_ptr<Impl>` 配显式析构函数。"
        "把「改头影响面」从 60% 压到 10%，等于把增量构建的收益放大 6 倍。"
        "**③ 并行**——`make -j$(nproc)`（或 `-j8`）几乎线性加速到核数为止；"
        "但注意 `-j` 会让编译错误信息交错、内存占用 ×N，CI 上还要配 `ccache`。"
        "顶层还有两招：**分布式编译**（distcc/icecc）和 **`ccache`**（命中时直接复用 .o，"
        "对「切换分支后重编」特别有效）。"
        "反过来说，如果一个工程 `make -j16` 还要几分钟，先量 `clang -ftime-trace`——"
        "通常时间不在你的代码里，而在几个重型模板头的实例化上。"
    ),
}


# ============================================================================
# clang/clang-u07 · 修一个 CVE，要重发 N 个程序
# ----------------------------------------------------------------------------
# 教学点：静态链接把库代码复制进每个可执行文件——20 个程序各带一份 80MB 的库，
# 磁盘 1.7GB、内存 1.7GB（不同程序的可执行文件页不能共享），
# 而且库出安全漏洞时要重新编译、重新发布、重新部署 20 次。
# 动态链接共享一份 SO，但代价是运行时加载、版本兼容（SONAME）与「找不到库」。
# ============================================================================
clang_u07 = {
    "kind": "sandbox",
    "title": "修一个 CVE，要重发 N 个程序",
    "brief": (
        "静态链接把库代码复制进每个可执行文件：20 个程序各带一份 80MB 的库，"
        "磁盘和内存都是 1.7GB。更麻烦的是库爆了 CVE——静态链接意味着"
        "20 个程序全部重新编译、重新发布、重新部署；动态链接只要换一个 `.so`。"
        "把程序数量与库体积拖到真实值，看这两种链接方式在磁盘、内存、补丁成本上的账。"
    ),
    "params": [
        # 程序数量
        {"key": "progs", "label": "程序数量", "min": 1, "max": 60, "step": 1, "value": 20},
        # 库体积（MB）
        {"key": "libMB", "label": "库体积", "min": 5, "max": 300, "step": 5, "value": 80},
        # 链接方式
        {"key": "mode", "label": "链接方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["静态链接", "动态链接（共享库）"]},
    ],
    "metrics": [
        # 每个程序自身代码固定 5MB
        {"key": "appMB", "label": "单程序自身代码", "expr": "5", "unit": "MB", "fmt": "int"},
        # 磁盘总量：静态每程序一份库；动态一份库 + 各程序自身
        {"key": "diskMB", "label": "部署磁盘总量", "expr": "if(mode == 0, progs * (5 + libMB), libMB + progs * 5)", "unit": "MB", "fmt": "int"},
        # 同时运行全部程序的内存占用
        {"key": "ramMB", "label": "同时运行内存占用", "expr": "if(mode == 0, progs * (5 + libMB), libMB + progs * 5)", "unit": "MB", "fmt": "int"},
        # 单程序体积
        {"key": "perProgMB", "label": "单个程序体积", "expr": "if(mode == 0, 5 + libMB, 5)", "unit": "MB", "fmt": "int"},
        # 补丁要重编/重发的程序数
        {"key": "rebuildCount", "label": "修库 CVE 要重发的程序数", "expr": "if(mode == 0, progs, 1)", "unit": "个", "fmt": "int"},
        # 发布耗时：每个程序 2 分钟（构建 + 打包 + 上传 + 灰度）
        {"key": "patchMin", "label": "补丁发布耗时", "expr": "if(mode == 0, progs * 2, 2)", "unit": "分钟", "fmt": "int"},
        # 部署传输耗时：50MB/s
        {"key": "deployS", "label": "全量部署传输耗时", "expr": "if(mode == 0, progs * (5 + libMB), libMB + progs * 5) / 50", "unit": "秒", "fmt": "int"},
    ],
    "checks": [
        # 下限：10 个程序起，单程序的静态链接反而是优点
        {"expr": "progs >= 10", "label": "程序数 ≥10 个（同一套库被多个程序复用）"},
        # 前提：库要有体积，小库怎么链都无所谓
        {"expr": "libMB >= 50", "label": "库体积 ≥50MB（重依赖：SSL/图像/数据库客户端）"},
        # 上限：磁盘总量
        {"expr": "diskMB <= 300", "label": "部署磁盘 ≤300MB"},
        # 上限：补丁只需重发一个
        {"expr": "rebuildCount <= 1", "label": "修库 CVE 只需重发 ≤1 个产物"},
        # 上限：补丁发布 10 分钟内完成
        {"expr": "patchMin <= 10", "label": "补丁发布 ≤10 分钟"},
    ],
    "insight": (
        "静态链接与动态链接的取舍是**「部署简单」对「运维成本」**："
        "静态链接的产物是自包含的（不依赖目标机装了什么库，Docker 里特别省心，"
        "`scratch` 基础镜像就能跑），代价是**每个程序一份副本**——"
        "20 个程序 × 80MB 库 = 1.7GB 磁盘、1.7GB 内存（不同可执行文件的代码页"
        "不能互相共享，只有同一文件的多进程才共享）。"
        "更要命的是**补丁半径**：库爆 CVE 时，静态链接要重编重发 N 个程序"
        "（本例 20 个 × 2 分钟 = 40 分钟），动态链接只需替换一个 `.so`。"
        "动态链接的代价则转移到**运行时**："
        "① `SONAME` 版本兼容——库升级了大版本，老程序可能直接 `symbol not found`；"
        "② `LD_LIBRARY_PATH` / `ldconfig` / rpath 配错就是「在我机器上能跑」；"
        "③ 启动时要走动态加载器解析符号（几十毫秒，对 CLI 工具是可见延迟）。"
        "所以真实工程的做法是分场景："
        "**面向最终用户的桌面/CLI 工具倾向静态**（免装依赖、单文件分发）；"
        "**服务器端同一套服务多实例倾向动态**（共享页、补丁快、镜像层可复用）；"
        "**容器时代的新答案是「静态链接 + 多阶段构建」**——用静态换「镜像小、启动快」，"
        "补丁靠重建镜像统一走 CI，把「重发 N 次」自动化掉。"
    ),
}


# ============================================================================
# java/java-ch01 · 一千万笔账，double 差出五百块
# ----------------------------------------------------------------------------
# 教学点：金额每笔都要「乘税率/打折后保留到分」，double 二进制浮点无法精确
# 表示 0.01 这类十进制小数，每笔的舍入误差虽小（平均约半分），
# 但一千万笔累加就是几百分的对账差异。long 存「分」是整数运算，零误差；
# BigDecimal 也零误差但每次运算约 120ns（比 long 慢两个数量级）。
# ============================================================================
java_ch01 = {
    "kind": "sandbox",
    "title": "一千万笔账，double 差出五百块",
    "brief": (
        "金额用 `double` 存「元」，每笔乘完税率再累加——单笔误差小到看不见，"
        "但一千万笔之后对账就差出几百块。原因在二进制浮点：`0.1` 在 double 里"
        "不是精确的 0.1，每笔的舍入误差按半分累积。"
        "把笔数与金额类型拖到真实体量，看三种表示法在「精度」和「耗时」上怎么取舍。"
    ),
    "params": [
        # 笔数（万）
        {"key": "itemsW", "label": "交易笔数（万）", "min": 10, "max": 2000, "step": 10, "value": 1000},
        # 金额表示
        {"key": "type", "label": "金额表示", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["double 存元", "long 存分", "BigDecimal"]},
    ],
    "metrics": [
        {"key": "items", "label": "交易笔数", "expr": "itemsW * 10000", "unit": "笔", "fmt": "int"},
        # double 每笔平均舍入偏差约半分（0.005 分）
        {"key": "errPerItem", "label": "单笔误差", "expr": "if(type == 0, 0.005, 0)", "unit": "分", "fmt": "fix2"},
        # 累计误差（分）
        {"key": "errFen", "label": "累计误差", "expr": "itemsW * 10000 * if(type == 0, 0.005, 0)", "unit": "分", "fmt": "int"},
        # 累计误差（元）
        {"key": "errYuan", "label": "累计误差（元）", "expr": "errFen / 100", "unit": "元", "fmt": "fix2"},
        # 单笔运算成本：double 2ns、long 1ns、BigDecimal 120ns
        {"key": "costNs", "label": "单笔运算成本", "expr": "if(type == 0, 2, if(type == 1, 1, 120))", "unit": "ns", "fmt": "int"},
        # 总耗时
        {"key": "totalMs", "label": "总耗时", "expr": "itemsW * 10000 * if(type == 0, 2, if(type == 1, 1, 120)) / 1000000", "unit": "ms", "fmt": "int"},
        # 每万笔的耗时
        {"key": "msPerW", "label": "每万笔耗时", "expr": "10000 * if(type == 0, 2, if(type == 1, 1, 120)) / 1000000", "unit": "ms", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：百万笔起，几十笔的误差看不出来
        {"expr": "items >= 1000000", "label": "交易 ≥100 万笔（日终对账的真实量级）"},
        # 上限：误差必须小于 1 分（对账要求精确到分）
        {"expr": "errFen <= 1", "label": "累计误差 ≤1 分（对账必须平）"},
        # 上限：总耗时
        {"expr": "totalMs <= 3000", "label": "总耗时 ≤3 秒"},
    ],
    "insight": (
        "`double` 是二进制浮点，**能精确表示的只有分母是 2 的幂的分数**；"
        "`0.1`、`0.01`、`0.13` 这些十进制小数在 double 里都是无限循环小数的截断。"
        "单笔误差在 1e-17 量级，肉眼不可见，但**每笔都要 `Math.round(x*100)/100` 保留到分**，"
        "这个舍入动作会把「截断误差」变成「半分级的偏差」，一千万笔累积就是几百元。"
        "这不是理论洁癖，是真实的日终对账差异来源（也是财务系统审计必查项）。"
        "三种正解，按推荐顺序："
        "① **`long` 存「分」**（或「厘」）——纯整数运算，零误差、最快（1ns），"
        "范围 ±9.2e16 分 = ±9.2e14 元，一个国家的 GDP 都够存；"
        "② **`BigDecimal`**——任意精度 + 显式 `RoundingMode`，"
        "适合「利率/汇率/分摊」这类必须记录舍入规则的场景，"
        "代价是每次运算约 120ns（慢两个数量级）且**必须用 `String` 构造**"
        "（`new BigDecimal(0.1)` 会把 double 的误差原样带进来）；"
        "③ 展示层再格式化（`DecimalFormat`），**存储与计算永远用整数或 BigDecimal**。"
        "一句话记住：**钱不能是浮点数**。同理适用于任何「必须精确的小数」——"
        "税率、汇率、积分、库存数量（用最小单位整数）。"
    ),
}


# ============================================================================
# java/java-ch02 · Integer[] 比 int[] 贵五倍
# ----------------------------------------------------------------------------
# 教学点：`int[]` 每个元素 4 字节；`Integer[]` 每个元素是「4 字节引用 +
# 一个 16 字节的 Integer 对象」（64 位压缩指针：12 字节对象头 + 4 字节 value，
# 对齐到 8 的倍数 = 16）。同样一千万个数，4MB 变 190MB。
# 对象数量还决定 GC 扫描量：一千万个对象 vs 一个数组。
# ============================================================================
java_ch02 = {
    "kind": "sandbox",
    "title": "Integer[] 比 int[] 贵五倍",
    "brief": (
        "`new int[1000万]` 是 40MB；`new Integer[1000万]` 是 190MB。"
        "多出来的不是数据，是**每个元素一个对象**：对象头 12 字节 + value 4 字节，"
        "对齐后 16，再加引用本身 4 字节。"
        "而且 GC 要逐个扫描这一千万个对象。把规模与元素类型拖到真实值，"
        "看「自动装箱」在内存和 GC 上的账单。"
    ),
    "params": [
        # 元素数（万）
        {"key": "countW", "label": "元素数（万）", "min": 10, "max": 5000, "step": 10, "value": 1000},
        # 元素类型
        {"key": "kind", "label": "容器类型", "min": 0, "max": 2, "step": 1, "value": 1,
         "labels": ["int[] 原始数组", "Integer[] 包装数组", "Point[] 小对象数组"]},
    ],
    "metrics": [
        {"key": "count", "label": "元素数", "expr": "countW * 10000", "unit": "个", "fmt": "int"},
        # int[] 4B；Integer 引用 4 + 对象 16 = 20；Point(2 int) 引用 4 + 对象 24 = 28
        {"key": "perElem", "label": "每个元素占用", "expr": "if(kind == 0, 4, if(kind == 1, 20, 28))", "unit": "字节", "fmt": "int"},
        # 堆总量
        {"key": "heapMB", "label": "堆占用", "expr": "countW * 10000 * if(kind == 0, 4, if(kind == 1, 20, 28)) / 1048576", "unit": "MB", "fmt": "int"},
        # 堆上的对象数量（int[] 是 1 个数组对象）
        {"key": "objects", "label": "堆上对象数", "expr": "if(kind == 0, 1, countW * 10000)", "unit": "个", "fmt": "int"},
        # GC 扫描：每对象约 4ns
        {"key": "gcScanMs", "label": "单次 GC 扫描耗时", "expr": "if(kind == 0, 4, countW * 10000 * 4) / 1000", "unit": "ms", "fmt": "int"},
        # 相对 int[] 的膨胀倍数
        {"key": "blowup", "label": "相对 int[] 膨胀", "expr": "if(kind == 0, 1, if(kind == 1, 5, 7))", "unit": "×", "fmt": "int"},
        # 一次扩容复制的字节量（Arrays.copyOf）
        {"key": "copyMB", "label": "扩容一次复制", "expr": "countW * 10000 * 4 / 1048576", "unit": "MB", "fmt": "int"},
    ],
    "checks": [
        # 下限：五百万起，小数组的差距无感
        {"expr": "count >= 5000000", "label": "元素 ≥500 万（真实的数据批处理规模）"},
        # 上限：堆占用
        {"expr": "heapMB <= 60", "label": "堆占用 ≤60MB"},
        # 上限：对象数量受控（别让 GC 被小对象淹死）
        {"expr": "objects <= 1000000", "label": "堆上对象 ≤100 万个"},
        # 上限：单次 GC 扫描
        {"expr": "gcScanMs <= 60", "label": "单次 GC 扫描 ≤60ms"},
    ],
    "insight": (
        "64 位 JVM 开压缩指针（`-XX:+UseCompressedOops`，默认开，堆 <32GB）时，"
        "**对象头 = 12 字节**（8 字节 Mark Word + 4 字节 Klass Pointer），"
        "引用 = 4 字节，对象整体按 8 字节对齐。于是："
        "`Integer` = 12 + 4 = 16 字节；`Point{int x; int y;}` = 12 + 8 = 20 → 对齐 24；"
        "`Long` = 12 + 8 = 20 → 对齐 24。"
        "**而 `int[]` 的每个元素就是 4 字节，没有对象**——所以 `Integer[]` 是"
        "「4 字节引用 + 16 字节对象」= 20 字节/元素，**5 倍**。"
        "三个真实后果："
        "① **内存**：一千万个 int 从 40MB 变 190MB，直接把堆推进老年代；"
        "② **GC**：标记阶段要遍历一千万个对象（每个至少一次指针追逐），"
        "停顿时间从「扫一个数组」变成「扫一千万个对象」；"
        "③ **缓存**：`int[]` 连续 40MB 顺序扫描，`Integer[]` 是指针跳跃，"
        "CPU 缓存命中率掉一个数量级。"
        "实操：**热数据用原始数组**（`int[]`/`long[]`/`double[]`），"
        "集合只在需要 API 时用；必须用 `List<Integer>` 时优先 `ArrayList` 预分配容量；"
        "小整数（-128~127）会命中 `Integer` 缓存不新建对象——**但这个优化只对小值有效，"
        "一千万个订单号完全用不上**。Java 的 `List<int>` 至今不存在，"
        "所以高性能数值代码通常直接操作数组 + 下标，或用第三方原始类型集合库（fastutil/trove）。"
    ),
}


# ============================================================================
# java/java-ch03 · 多实现调用点，JIT 不再内联
# ----------------------------------------------------------------------------
# 教学点：`invokeinterface` 的调用点若只见过一两种实现类型，JIT 能做成
# 「类型判断 + 直接内联」；一旦见过 3 种以上就退化成 megamorphic（超多态），
# 只能走 vtable/itable 查表，每次 20ns 量级，且彻底失去内联机会
# （内联是后续逃逸分析、标量替换、锁消除的前提）。
# 正解：按类型拆分调用点（Visitor / 类型 switch 提到循环外），恢复单态。
# ============================================================================
java_ch03 = {
    "kind": "sandbox",
    "title": "多实现调用点，JIT 不再内联",
    "brief": (
        "一个 `shape.area()` 调用点在循环里被一百万个对象调用。"
        "如果这些对象的实际类型只有一两种，JIT 会内联成「判断类型 + 直接算」；"
        "一旦超过两种，调用点变成 megamorphic，只能查 itable，每次慢 10 倍，"
        "而且内联失效会连带失去逃逸分析和锁消除。"
        "把实现类数量、调用次数与调用点组织方式拖到真实值，看这 20 纳秒怎么来的。"
    ),
    "params": [
        # 实现类数量
        {"key": "impls", "label": "实现类数量", "min": 3, "max": 24, "step": 1, "value": 12},
        # 调用次数（百万）
        {"key": "callsM", "label": "调用次数（百万）", "min": 1, "max": 200, "step": 1, "value": 100},
        # 调用点组织
        {"key": "split", "label": "调用点组织", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["一个调用点吃下所有类型", "按类型拆成独立调用点"]},
    ],
    "metrics": [
        {"key": "calls", "label": "调用次数", "expr": "callsM * 1000000", "unit": "次", "fmt": "int"},
        # 单次成本：拆分后每点单态可内联 2ns；未拆分且多实现 22ns
        {"key": "nsPer", "label": "单次调用成本", "expr": "if(split == 1, 2, if(impls <= 2, 3, 22))", "unit": "ns", "fmt": "int"},
        # 总耗时
        {"key": "totalMs", "label": "总耗时", "expr": "callsM * 1000000 * if(split == 1, 2, if(impls <= 2, 3, 22)) / 1000000", "unit": "ms", "fmt": "int"},
        # itable 查表次数
        {"key": "itableLookups", "label": "itable 查表次数", "expr": "if(split == 1, 0, callsM * 1000000)", "unit": "次", "fmt": "int"},
        # 内联状态
        {"key": "inlined", "label": "是否可内联", "expr": "if(split == 1, 1, 0)", "unit": "是/否", "fmt": "int"},
        # 相对拆分后的减速倍数
        {"key": "slowdown", "label": "相对单态减速", "expr": "if(split == 1, 1, if(impls <= 2, 1, 11))", "unit": "×", "fmt": "int"},
    ],
    "checks": [
        # 下限：六种实现起，两三种实现的调用点 JIT 还能应付
        {"expr": "impls >= 6", "label": "实现类 ≥6 种（真实业务的策略/插件体系）"},
        # 下限：五千万次调用，才够触发 JIT 编译并让开销显形
        {"expr": "calls >= 50000000", "label": "调用 ≥5000 万次（热点路径）"},
        # 上限：总耗时
        {"expr": "totalMs <= 500", "label": "总耗时 ≤500ms"},
        # 上限：减速倍数
        {"expr": "slowdown <= 2", "label": "相对单态减速 ≤2 倍（JIT 必须能内联）"},
        # 上限：itable 查表次数
        {"expr": "itableLookups <= 1000000", "label": "itable 查表 ≤100 万次"},
    ],
    "insight": (
        "JVM 的虚方法调用有四个 fast path（`invokevirtual` / `invokeinterface` 同理）："
        "**单态（monomorphic）**——调用点只见过一种实际类型，JIT 编译成"
        "「比较 Klass 指针 + 直接跳转」，并且**可以内联**；"
        "**双态（bimorphic）**——见过两种，编译成一次条件分支 + 两段内联代码，仍然很快；"
        "**多态（polymorphic，≤2 种即算）** 同上；"
        "**超多态（megamorphic，>2 种）**——JIT 放弃，退回 itable 查表（约 20ns）。"
        "注意 20ns 本身不算什么，**真正的代价是内联失效**："
        "内联是逃逸分析、标量替换、锁消除、常量折叠的**前置条件**，"
        "一个 megamorphic 调用点会让整条调用链失去优化机会——实测常常是 5-20 倍。"
        "三种正解："
        "① **拆分调用点**：`for (Shape s : list) if (s instanceof Circle c) ... else if ...`，"
        "把类型判断提到循环外，每种类型一个单态循环（本例 22ns → 2ns）；"
        "② **Visitor 模式**（双重分派）：`shape.accept(visitor)`，"
        "每个实现类里写死自己的处理，调用点变成「每种类型一个单态点」；"
        "③ **数据导向**：把「按类型分支」换成「按字段/枚举 switch」，"
        "或干脆用「数组 + 类型标签」的 SoA 布局，绕开虚调用。"
        "反例：Spring 里 `List<Handler>` 遍历 `handler.supports()` 就是典型 megamorphic 场景，"
        "量小时无感，量大时要预分组。"
    ),
}


# ============================================================================
# java/java-ch04 · HashMap 不预设容量，扩容十八次
# ----------------------------------------------------------------------------
# 教学点：HashMap 默认 16 桶、负载因子 0.75。放 200 万条要一路扩容到
# 419 万桶——18 次，每次都要新建桶数组并 rehash 全部已有节点。
# `new HashMap<>(expected)` 一次到位，省掉 800 万次 rehash 和十几轮数组分配，
# 也避免最后一次扩容的长暂停。
# ============================================================================
java_ch04 = {
    "kind": "sandbox",
    "title": "HashMap 不预设容量，扩容十八次",
    "brief": (
        "`new HashMap<>()` 默认 16 个桶、负载因子 0.75。往里塞 200 万条，"
        "它会从 16 一路翻倍扩到 419 万桶——**扩容 18 次，累计 rehash 800 万个节点**，"
        "最后一次扩容要搬 209 万个节点（约 84 毫秒的停顿）。"
        "`new HashMap<>(expected)` 一次算到位就没有这些。"
        "把条数与是否预设容量拖到真实值，看这笔「一行构造参数」的账。"
    ),
    "params": [
        # 条数（万）
        {"key": "entriesW", "label": "键值对数量（万）", "min": 10, "max": 1000, "step": 10, "value": 200},
        # 是否预设容量
        {"key": "preset", "label": "构造方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["new HashMap<>() 默认 16", "new HashMap<>(expected) 预设"]},
    ],
    "metrics": [
        {"key": "entries", "label": "键值对数量", "expr": "entriesW * 10000", "unit": "条", "fmt": "int"},
        # 最终桶数组容量：2^k >= entries/0.75
        {"key": "finalCap", "label": "最终桶数组容量", "expr": "pow(2, ceil(log2(entriesW * 10000 / 0.75)))", "unit": "桶", "fmt": "int"},
        # 扩容次数：16 → finalCap 的 log2 差
        {"key": "resizes", "label": "扩容次数", "expr": "if(preset == 1, 0, round(log2(finalCap / 16)))", "unit": "次", "fmt": "int"},
        # 累计 rehash 节点数（每次搬迁已有节点，近似最终容量的 2 倍）
        {"key": "rehashOps", "label": "累计 rehash 节点数", "expr": "if(preset == 1, 0, finalCap * 2)", "unit": "个", "fmt": "int"},
        # 桶数组内存（4 字节引用/桶）
        {"key": "arrMB", "label": "桶数组占用", "expr": "finalCap * 4 / 1048576", "unit": "MB", "fmt": "int"},
        # Node 对象内存（16 头 + 4 hash + 4 key + 4 val + 4 next = 32）
        {"key": "nodeMB", "label": "Node 对象占用", "expr": "entriesW * 10000 * 32 / 1048576", "unit": "MB", "fmt": "int"},
        # 总耗时：每条 50ns 插入 + 未预设时额外 60ns 的搬迁摊销
        {"key": "totalMs", "label": "总插入耗时", "expr": "entriesW * 10000 * (50 + if(preset == 1, 0, 60)) / 1000000", "unit": "ms", "fmt": "int"},
        # 最后一次扩容的停顿（搬一半节点，每节点 40ns）
        {"key": "pauseMs", "label": "单次扩容最长停顿", "expr": "if(preset == 1, 0, finalCap / 2 * 40 / 1000000)", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        # 下限：百万条起，几千条的 HashMap 扩容无感
        {"expr": "entries >= 1000000", "label": "键值对 ≥100 万（真实的缓存/索引规模）"},
        # 上限：不扩容
        {"expr": "resizes <= 0", "label": "扩容 0 次（一次算准容量）"},
        # 上限：总插入耗时
        {"expr": "totalMs <= 200", "label": "总插入耗时 ≤200ms"},
        # 上限：单次停顿
        {"expr": "pauseMs <= 5", "label": "单次最长停顿 ≤5ms（别让扩容卡住请求）"},
    ],
    "insight": (
        "HashMap 的扩容逻辑是**翻倍 + 全量 rehash**：容量从 16 开始，"
        "负载因子 0.75，元素数超过 `capacity * 0.75` 就新建一个 2 倍大的桶数组，"
        "把每个节点按 `(n-1) & hash` 重新落位。"
        "200 万条要扩到 `2^22 = 419 万`桶，路径是 16→32→…→4194304，**18 次**；"
        "累计搬迁节点数约 `2 × 最终容量`（几何级数求和）≈ 800 万个。"
        "每次搬迁都要重新算索引、改链表/红黑树指针——**而且是在插入路径上同步做的**，"
        "所以是一次可见的停顿（本例最后一次约 84ms）。"
        "正解一行：`new HashMap<>((int) (expected / 0.75f) + 1)`"
        "（Guava 的 `Maps.newHashMapWithExpectedSize(n)` 帮你算好了）。"
        "注意几个细节："
        "① **容量一定是 2 的幂**（`tableSizeFor` 会向上取整），因为有 `(n-1) & hash` 的位运算优化；"
        "② **树化阈值 8 / 退化 6**：单桶超过 8 个节点转红黑树（防哈希碰撞攻击），"
        "低于 6 退回链表，中间的 7 是缓冲带防抖动；"
        "③ **负载因子 0.75 是空间与查找长度的折中**（0.75 时桶内平均 0.75 个节点，"
        "泊松分布下长度 8 的概率约 6e-8，刚好是树化阈值）；"
        "④ 并发场景用 `ConcurrentHashMap`，它扩容是**多线程协同搬迁**（helpTransfer），"
        "单次停顿比 HashMap 小得多——这也是为什么高并发下不要用 `Collections.synchronizedMap`。"
    ),
}


# ============================================================================
# java/java-ch05 · 用异常做控制流，一个核没了
# ----------------------------------------------------------------------------
# 教学点：`new Exception()` 会调 `fillInStackTrace()`，遍历当前线程整个栈、
# 为每一帧分配一个 `StackTraceElement` 对象并填入类名/方法名/文件名/行号。
# 40 层栈约 5μs/次，还说每秒 20 万次 → 一个核 100% 在这一件事上，
# 同时每秒产生 250MB 垃圾。正解：用返回值/状态码/Optional，异常只留给真正异常。
# ============================================================================
java_ch05 = {
    "kind": "sandbox",
    "title": "用异常做控制流，一个核没了",
    "brief": (
        "「查不到就抛 NotFoundException」看着很干净——但每次 `new` 一个异常，"
        "JVM 都要 `fillInStackTrace()`：遍历整个调用栈，为每一帧创建一个 "
        "`StackTraceElement`（类名/方法名/文件/行号）。40 层栈约 5 微秒，"
        "每秒 20 万次就是一个核满载，还顺带每秒 250MB 垃圾。"
        "把异常频率、栈深与处理方式拖到真实值，看这笔账。"
    ),
    "params": [
        # 每秒异常次数（千）
        {"key": "excK", "label": "每秒异常次数（千）", "min": 1, "max": 500, "step": 1, "value": 200},
        # 栈深
        {"key": "depth", "label": "调用栈深度", "min": 5, "max": 200, "step": 5, "value": 40},
        # 处理方式
        {"key": "mode", "label": "未命中处理方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["抛异常", "返回 Optional/状态码"]},
    ],
    "metrics": [
        # 每次异常成本：固定开销 300ns + 每帧 120ns（分配 + 填充 StackTraceElement）
        {"key": "nsPer", "label": "单次成本", "expr": "if(mode == 0, 300 + depth * 120, 3)", "unit": "ns", "fmt": "int"},
        # 每秒 CPU 毫秒
        {"key": "cpuMsPerSec", "label": "每秒消耗 CPU", "expr": "excK * 1000 * if(mode == 0, 300 + depth * 120, 3) / 1000000", "unit": "ms", "fmt": "int"},
        # 占单核百分比
        {"key": "cpuPct", "label": "占单核比例", "expr": "excK * 1000 * if(mode == 0, 300 + depth * 120, 3) / 1000000 / 10", "unit": "%", "fmt": "int"},
        # 每秒垃圾：异常对象 40B + 每帧 StackTraceElement 24B + 数组 16+8*depth
        {"key": "gcMBPerSec", "label": "每秒产生垃圾", "expr": "if(mode == 0, excK * 1000 * (40 + depth * 24 + 16 + 8 * depth) / 1048576, 0)", "unit": "MB", "fmt": "int"},
        # 每秒需要的核数
        {"key": "cores", "label": "折算核数", "expr": "cpuMsPerSec / 1000", "unit": "核", "fmt": "fix2"},
        # 每秒 Young GC 次数（按 20MB 的 Eden 估算）
        {"key": "ygcPerSec", "label": "每秒 Young GC 次数", "expr": "gcMBPerSec / 20", "unit": "次", "fmt": "int"},
    ],
    "checks": [
        # 下限：每秒十万次起，低频异常完全没问题
        {"expr": "excK >= 100", "label": "异常 ≥10 万次/秒（高频未命中：缓存穿透/限流/参数校验）"},
        # 上限：CPU 占用（单核 20% 以内）
        {"expr": "cpuPct <= 20", "label": "CPU 占用 ≤单核 20%"},
        # 上限：垃圾产生
        {"expr": "gcMBPerSec <= 5", "label": "垃圾 ≤5MB/s（别让 GC 陪跑）"},
        # 上限：Young GC 频率
        {"expr": "ygcPerSec <= 1", "label": "Young GC ≤1 次/秒"},
    ],
    "insight": (
        "异常的昂贵不在「抛出」，在 `fillInStackTrace()`："
        "**它要遍历当前线程的整个调用栈**，为每一帧 `new` 一个 `StackTraceElement`"
        "（含 declaringClass / methodName / fileName / lineNumber），"
        "再填进 `Throwable` 的 `stackTrace` 数组。40 层栈约 5μs，"
        "栈越深越慢——**成本与调用栈深度成正比**，这是它最反直觉的地方。"
        "高频路径的三条正解："
        "① **返回值 / 状态码 / `Optional`**（本例 5μs → 3ns，差三个数量级）；"
        "② 必须用异常表达「业务失败」时，**关掉栈快照**："
        "重写 `fillInStackTrace()` 返回 `this`（或构造器传 `writableStackTrace=false`），"
        "把 5μs 压到 0.3μs，代价是日志里没有堆栈（要自己补上下文）；"
        "③ **静态单例异常**（不填栈、不 new），适合「无参数、纯信号」的场景。"
        "反过来，**异常该用的地方不要为了性能不用**：真正的错误（文件不存在、"
        "连接断了、参数非法）就该抛，因为它的发生频率低，语义清晰比省 5μs 重要。"
        "判据是**频率**：每秒几千次以上就要考虑换控制流，每秒几次就老老实实抛。"
        "JIT 还能帮一点忙：同一异常反复抛时，热点代码里的 `fillInStackTrace` 会被优化，"
        "但**对象分配和数组填充不会被消除**（逃逸到 catch 块之外的语义要求）——"
        "所以 GC 压力是实打实的。"
    ),
}


# ============================================================================
# java/java-ch06 · 逐字节读 512MB = 五亿次系统调用
# ----------------------------------------------------------------------------
# 教学点：`FileInputStream.read()` 一次读一个字节，每次都是一次系统调用
# （约 150ns：用户态/内核态切换 + 文件偏移更新）。512MB = 5.37 亿次 = 80 秒。
# `BufferedInputStream` 8KB 一次装满，系统调用降到 6.5 万次；
# `FileChannel` + 直接缓冲还能省掉一次内核→堆的拷贝。
# ============================================================================
java_ch06 = {
    "kind": "sandbox",
    "title": "逐字节读 512MB = 五亿次系统调用",
    "brief": (
        "`while ((b = in.read()) != -1)` 是最常见的读文件写法，"
        "也是最常见的性能事故：`FileInputStream.read()` 每次只读一个字节，"
        "每次都是一次系统调用（约 150 纳秒）。512MB 就是 5.37 亿次、80 秒。"
        "包一层 `BufferedInputStream`（8KB）系统调用降到 6.5 万次。"
        "把文件大小与读法拖到真实值，看时间花在哪。"
    ),
    "params": [
        # 文件大小（MB）
        {"key": "fileMB", "label": "文件大小", "min": 16, "max": 4096, "step": 16, "value": 512},
        # 读法
        {"key": "mode", "label": "读取方式", "min": 0, "max": 2, "step": 1, "value": 0,
         "labels": ["FileInputStream 逐字节", "BufferedInputStream 8KB", "FileChannel 64KB 直接缓冲"]},
    ],
    "metrics": [
        {"key": "bytes", "label": "总字节数", "expr": "fileMB * 1048576", "unit": "字节", "fmt": "int"},
        # 每次 read 搬运的字节数
        {"key": "bufB", "label": "单次 read 字节数", "expr": "if(mode == 0, 1, if(mode == 1, 8192, 65536))", "unit": "字节", "fmt": "int"},
        # read 调用次数 = 系统调用次数
        {"key": "syscalls", "label": "read 系统调用次数", "expr": "fileMB * 1048576 / if(mode == 0, 1, if(mode == 1, 8192, 65536))", "unit": "次", "fmt": "int"},
        # 系统调用耗时：约 150ns/次
        {"key": "sysMs", "label": "系统调用开销", "expr": "fileMB * 1048576 / if(mode == 0, 1, if(mode == 1, 8192, 65536)) * 0.15 / 1000", "unit": "ms", "fmt": "int"},
        # 磁盘读取：约 2GB/s（NVMe）
        {"key": "diskMs", "label": "磁盘读取耗时", "expr": "fileMB * 1024 / 2000", "unit": "ms", "fmt": "int"},
        # 总耗时
        {"key": "totalMs", "label": "总耗时", "expr": "fileMB * 1048576 / if(mode == 0, 1, if(mode == 1, 8192, 65536)) * 0.15 / 1000 + fileMB * 1024 / 2000", "unit": "ms", "fmt": "int"},
        # 吞吐
        {"key": "mbps", "label": "有效吞吐", "expr": "fileMB * 1000 / (fileMB * 1048576 / if(mode == 0, 1, if(mode == 1, 8192, 65536)) * 0.15 / 1000 + fileMB * 1024 / 2000)", "unit": "MB/s", "fmt": "fix2"},
        # 系统调用占时间比例
        {"key": "sysPct", "label": "系统调用占比", "expr": "sysMs * 100 / totalMs", "unit": "%", "fmt": "int"},
    ],
    "checks": [
        # 下限：256MB 起，小文件随便读
        {"expr": "fileMB >= 256", "label": "文件 ≥256MB（日志/备份/镜像这类真实体量）"},
        # 上限：系统调用次数
        {"expr": "syscalls <= 1000000", "label": "read 调用 ≤100 万次"},
        # 上限：总耗时
        {"expr": "totalMs <= 1500", "label": "总耗时 ≤1.5 秒"},
        # 下限：吞吐
        {"expr": "mbps >= 150", "label": "吞吐 ≥150MB/s"},
    ],
    "insight": (
        "`FileInputStream.read()` 的每一次调用都是一次 **`read(2)` 系统调用**："
        "用户态 → 内核态（保存寄存器、切换栈）→ VFS 层 → 页缓存（命中则内存拷贝）"
        "→ 返回用户态，全程约 150ns。**读一个字节和读 8KB 的系统调用成本是一样的**，"
        "所以逐字节读等于把成本放大 8192 倍。512MB：5.37 亿次 ≈ 80 秒；"
        "8KB 缓冲：6.5 万次 ≈ 10 毫秒——**差了八千倍**。"
        "四层手段，按收益排序："
        "① **`BufferedInputStream` / `BufferedReader`**（8KB 起步）——最小的改动，最大的收益；"
        "② **`FileChannel` + `ByteBuffer`**：批量搬运，`transferTo` 走 `sendfile` 还能零拷贝；"
        "③ **`MappedByteBuffer`（mmap）**：大文件随机访问，页缓存直接映射进地址空间，"
        "省掉内核→用户的拷贝（但要注意文件截断会触发 `SIGBUS`）；"
        "④ **直接缓冲（DirectByteBuffer）**：JVM 堆外，读写时不再有「堆内→堆外」的中转拷贝，"
        "适合长时间的大吞吐 IO。"
        "两个更常见的坑：**忘记 `close()`**（用 try-with-resources）导致句柄泄漏"
        "（Linux 默认 1024 个 fd，几千并发立刻 `Too many open files`）；"
        "**`read()` 返回值当「读满了」用**——`read(buf)` 返回的是**实际读到的字节数**，"
        "可能小于 buffer 大小，正确写法是 `while ((n = in.read(buf)) != -1) process(buf, 0, n)`。"
    ),
}


# ============================================================================
# java/java-ch09 · Maven 首次构建，大半时间在等下载
# ----------------------------------------------------------------------------
# 教学点：一个 12 模块的工程，依赖树展开约 73 个 jar、182MB。中央仓库
# 直连 2MB/s 要 91 秒；配国内镜像 20MB/s 只要 9 秒；`~/.m2` 已缓存则 0 秒。
# 再加每模块 3 秒的编译/打包，总时间就是「下载 + 构建」两段之和——
# 「Maven 慢」的抱怨大半来自第一段，而它跟代码规模无关。
# ============================================================================
java_ch09 = {
    "kind": "sandbox",
    "title": "Maven 首次构建，大半时间在等下载",
    "brief": (
        "`mvn clean package` 卡住十分钟，多数人以为是「代码多」。"
        "实际是依赖下载：12 个模块展开约 73 个 jar、182MB，"
        "中央仓库直连 2MB/s 就是 91 秒，而真正编译只占 36 秒。"
        "把模块数、仓库镜像与本地缓存拖到真实值，看「Maven 慢」到底慢在哪。"
    ),
    "params": [
        # 模块数
        {"key": "modules", "label": "Maven 模块数", "min": 1, "max": 40, "step": 1, "value": 12},
        # 仓库镜像
        {"key": "mirror", "label": "仓库地址", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["中央仓库直连 2MB/s", "国内镜像 20MB/s"]},
        # 本地缓存
        {"key": "cache", "label": "本地仓库 ~/.m2", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["空（首次构建）", "已缓存依赖"]},
    ],
    "metrics": [
        # 依赖 jar 数：基础 25 个 + 每模块 4 个
        {"key": "jars", "label": "依赖 jar 数", "expr": "25 + modules * 4", "unit": "个", "fmt": "int"},
        # 下载量：平均 2.5MB/jar
        {"key": "depMB", "label": "依赖总大小", "expr": "(25 + modules * 4) * 2.5", "unit": "MB", "fmt": "int"},
        # 下载耗时
        {"key": "dlS", "label": "依赖下载耗时", "expr": "if(cache == 1, 0, (25 + modules * 4) * 2.5 / if(mirror == 1, 20, 2))", "unit": "秒", "fmt": "int"},
        # 编译打包：每模块 3 秒
        {"key": "compileS", "label": "编译打包耗时", "expr": "modules * 3", "unit": "秒", "fmt": "int"},
        # 总耗时
        {"key": "totalS", "label": "构建总耗时", "expr": "if(cache == 1, 0, (25 + modules * 4) * 2.5 / if(mirror == 1, 20, 2)) + modules * 3", "unit": "秒", "fmt": "int"},
        # 下载占比
        {"key": "dlPct", "label": "下载占比", "expr": "dlS * 100 / totalS", "unit": "%", "fmt": "int"},
        # 每天 CI 跑 20 次，一天浪费
        {"key": "ciMinPerDay", "label": "CI 每天等待（20 次）", "expr": "totalS * 20 / 60", "unit": "分钟", "fmt": "int"},
    ],
    "checks": [
        # 下限：十个模块起，单模块工程的下载量不大
        {"expr": "modules >= 10", "label": "Maven 模块 ≥10 个（多模块工程）"},
        # 上限：总耗时 90 秒内
        {"expr": "totalS <= 90", "label": "构建总耗时 ≤90 秒"},
        # 上限：下载时间 30 秒内
        {"expr": "dlS <= 30", "label": "依赖下载 ≤30 秒"},
        # 上限：下载占比
        {"expr": "dlPct <= 50", "label": "下载不超过总耗时一半（构建才是主体）"},
    ],
    "insight": (
        "Maven 的耗时 = **依赖解析与下载** + **插件执行（编译/测试/打包）**，"
        "而第一段跟你的代码量几乎无关，只跟依赖树的规模有关。"
        "12 个模块的工程依赖树展开约 73 个 jar（每个 starter 会带一串传递依赖），"
        "平均 2.5MB/个 = 182MB。中央仓库从国内直连约 2MB/s → 91 秒；"
        "换成国内镜像（阿里云/华为云）20MB/s → 9 秒；`~/.m2` 已缓存则 0 秒。"
        "三条实操："
        "① **配镜像**（`settings.xml` 的 `<mirrors>` 指向阿里云），"
        "这是「Maven 慢」最常见也最有效的解法；"
        "② **CI 缓存 `~/.m2/repository`**（GitHub Actions 的 `actions/cache`、"
        "GitLab 的 `cache: paths`），命中后整个下载段归零；"
        "③ **`-o` 离线模式**（依赖已齐时跳过联网检查）+ **`-T 1C` 并行构建**"
        "（按核数并行跑模块，多模块工程能再省 50%）。"
        "顺带解释两个常见困惑："
        "**为什么删了 `target` 还要重下依赖**——`target` 是构建输出，"
        "依赖在 `~/.m2`，删前者不影响后者；"
        "**为什么 `mvn` 第一次特别慢**——它在下载 Maven 自己的插件（"
        "`maven-compiler-plugin`、`maven-surefire-plugin` 等），"
        "这些也是 jar，也走同一条下载路径。"
        "更远一步：Gradle 的增量构建和构建缓存比 Maven 快，"
        "但多模块工程的依赖下载问题是一样的——**镜像 + 缓存**是通用解。"
    ),
}


MODULES = {
    "clang/clang-u01": clang_u01,
    "clang/clang-u02": clang_u02,
    "clang/clang-u03": clang_u03,
    "clang/clang-u04": clang_u04,
    "clang/clang-u05": clang_u05,
    "clang/clang-u06": clang_u06,
    "clang/clang-u07": clang_u07,
    "java/java-ch01": java_ch01,
    "java/java-ch02": java_ch02,
    "java/java-ch03": java_ch03,
    "java/java-ch04": java_ch04,
    "java/java-ch05": java_ch05,
    "java/java-ch06": java_ch06,
    "java/java-ch09": java_ch09,
}


def main() -> int:
    """读取 labs.json → 写入 14 个 sandbox → 按仓库风格（indent=1/LF）落盘。"""
    with open(LABS, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.setdefault("chapters", {})
    existed = sum(1 for k in MODULES if k in chapters)
    for key, mod in MODULES.items():
        # 幂等 + 不吞同章其它玩法：只替换本章的 sandbox，保留 debug 等其它模块
        kept = [m for m in chapters.get(key, []) if m.get("kind") != "sandbox"]
        chapters[key] = [mod] + kept
        extra = f"（保留其它模块 {len(kept)} 个）" if kept else ""
        print(f"added {key:<22} ({len(mod['params'])} params / {len(mod['metrics'])} metrics / {len(mod['checks'])} checks){extra}")

    with open(LABS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"written {os.path.normpath(LABS)}  (共 {len(chapters)} 章有精修模块，本次覆盖 {len(MODULES)}，其中已存在 {existed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
