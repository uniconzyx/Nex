# -*- coding: utf-8 -*-
"""批次六：给 python 九章补 sandbox（Python 学科首次接入交互玩法）。

与前几批同一套路：写进 content/_handmade/labs.json 的 chapters，再由
gen_interactive.py 并入各章 interactive.json 与前端数据。

为什么是这九章
-------------
沙盒的硬门槛是「参数能调、判据能算」。Python 教学里最容易讲成口水话的
正是「这个写法快 / 那个写法省内存」——而它们全都可以算成账：

  py-ch01  str 不可变 → 循环 += 是 O(n²) 拷贝，''.join 是 O(n)
  py-ch02  朴素递归 F(n) 调用次数 ≈ φ^n，记忆化退化成 n
  py-ch03  列表推导先建整张表，生成器只留一个帧
  py-ch04  json.dumps 默认 ensure_ascii=True，中文膨胀成 \\uXXXX
  py-ch05  readlines 把整个文件搬进内存，逐行迭代只占一个缓冲
  py-ch06  嵌套量词 (a+)+ 的回溯是 2^n，线性写法只扫一遍
  py-ch07  GIL 下 CPU-bound 多线程不加速（还因切换略负优化）
  py-ch08  pandas object 列每格一个 str 对象，category 只存 code
  py-ch09  __dict__ 每个实例一张哈希表，__slots__ 只留字段

九章的共同教学点：**同一件事，写法不同，代价差一到几个数量级**。
每一关的默认值都是「新手真实写法」，一打开就红，红得有道理。

纪律（沿用批次三/四/五）
-----------------------
1. checks 必须带下限（规模、核数、长度），否则求解读会退化成「旋钮拉最小」。
2. 既定事实才用 `==` 锁；本批一律不锁「正确答案」，让预算判据自己逼出来。
3. 默认值 = 真实事故配置。
4. `if(c,a,b)` 急切求值 → 本批 if 的分支全是已算好的指标或常量，无除零风险。
5. fmt 只认 int / fix2 / pct。
6. 参数字段：key/label/min/max/step/value，离散枚举加 labels。

写盘必须 indent=1 + newline="\\n"，与仓库现有风格逐字节一致。
"""
import json
import os

LABS = os.path.join(os.path.dirname(__file__), "..", "content", "_handmade", "labs.json")


# ============================================================================
# python/py-ch01 · 循环里拼字符串，为什么越拼越慢
# ----------------------------------------------------------------------------
# 教学点：str 在 Python 里不可变。`s += part` 语义上是「新建一个更长的串，
# 把旧内容和 part 都拷进去」——循环 n 次，第 i 次要拷 i·L 字节，
# 总拷贝量 = L·n(n+1)/2 ≈ O(n²)。`''.join(parts)` 先算总长度、只分配一次、
# 再逐段 memcpy，总拷贝量 = n·L，是 O(n)。
# 注：CPython 对「引用计数为 1 的 str」有原地 resize 的实现细节优化，
# 但官方明确不承诺，PyPy/有别名时立刻退化成 O(n²)——本关按语义代价算账。
# ============================================================================
py_ch01 = {
    "kind": "sandbox",
    "title": "循环里拼字符串，为什么越拼越慢",
    "brief": (
        "把一万条日志片段拼成一个大字符串，最直觉的写法是循环里 `s += part`。"
        "但 Python 的 str 是不可变的：每次 `+=` 都要新建一个更长的串，"
        "把旧内容和新增片段一起拷进去，第 i 次要拷 i 段。"
        "片段数翻倍，拷贝量翻四倍——这就是 O(n²) 的来源。"
        "把片段数拖到真实日志的规模，看两种写法的拷贝量差出几个数量级。"
    ),
    "params": [
        # 片段数：1 千到 10 万，覆盖"小脚本"到"日志聚合"
        {"key": "n", "label": "片段数", "min": 1000, "max": 100000, "step": 1000, "value": 50000},
        # 拼接方式：0 = 循环 +=（新手写法），1 = ''.join
        {"key": "mode", "label": "拼接方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["循环 s += part", "''.join(parts)"]},
    ],
    "metrics": [
        {"key": "parts", "label": "片段数 n", "expr": "n", "unit": "段", "fmt": "int"},
        # 总输出大小：每段平均 20 字节
        {"key": "outKB", "label": "结果字符串", "expr": "n * 20 / 1024", "unit": "KB", "fmt": "int"},
        # += 的总拷贝量：L·n(n+1)/2，用 L=20
        {"key": "grossMB", "label": "+= 累计拷贝", "expr": "20 * n * (n + 1) / 2 / 1048576", "unit": "MB", "fmt": "int"},
        # join 的总拷贝量：只拷一遍
        {"key": "joinMB", "label": "join 拷贝", "expr": "n * 20 / 1048576", "unit": "MB", "fmt": "int"},
        # 当前写法实际拷贝量（两分支都是已算好的指标）
        {"key": "chosenMB", "label": "当前写法拷贝", "expr": "if(mode == 1, joinMB, grossMB)", "unit": "MB", "fmt": "int"},
        # 放大倍数：随 n 线性增长（n=5 万时约 2.5 万倍）
        {"key": "ratio", "label": "+= / join", "expr": "grossMB / joinMB", "unit": "倍", "fmt": "int"},
    ],
    "checks": [
        # 下限：规模要够，小到 1000 段时两者都瞬间完成，看不出问题
        {"expr": "parts >= 20000", "label": "片段数 ≥2 万（规模够大才谈得上复杂度）"},
        # 痛点：朴素写法在这个规模下拷贝量过 GB
        {"expr": "grossMB >= 1024", "label": "+= 累计拷贝 ≥1GB（这就是要解决的痛点）"},
        # 上限：选定写法必须把拷贝量压进 64MB
        {"expr": "chosenMB <= 64", "label": "当前写法拷贝 ≤64MB（常规内存带宽下秒级完成）"},
    ],
    "insight": (
        "`s += part` 看起来是「追加」，语义上却是「新建 + 全量拷贝」——"
        "不可变对象没有 append 这回事。n 段拼下来总拷贝量是 L·n²/2，"
        "5 万段就是 25GB 的内存搬运，而 `''.join` 只搬 1MB。"
        "CPython 确实对引用计数为 1 的 str 做过原地 resize 优化，"
        "但这属于实现细节、官方不承诺，PyPy 或一旦有别名就立刻退化。"
        "同样的道理适用于 bytes、tuple 的循环相加："
        "**需要累积时先用 list 收着，最后一次性 join / tuple()**。"
    ),
}


# ============================================================================
# python/py-ch02 · 一个闭包，把指数级递归按回线性
# ----------------------------------------------------------------------------
# 教学点：朴素递归 F(n)=F(n-1)+F(n-2) 的调用次数 ≈ 2·φⁿ（φ=1.618），
# 因为同一批子问题被重复求解了指数多次。加一层 dict 缓存（闭包持有），
# 每个 n 只算一次，调用次数降到 n。这正是「闭包 + 一等公民函数」的
# 第一个真实用途：把状态藏在函数对象里，不改调用方签名。
# ============================================================================
py_ch02 = {
    "kind": "sandbox",
    "title": "一个闭包，把指数级递归按回线性",
    "brief": (
        "写 `fib(n)` 最自然的方式是递归：`fib(n-1) + fib(n-2)`。"
        "但每个 n 会被算过指数多次——n=35 时函数调用四千万次，"
        "本来该是毫秒级的计算要跑几十秒。"
        "解法不是改算法，而是加一层缓存：用一个 dict 记住算过的 n（闭包正好干这事），"
        "调用次数立刻从 φⁿ 掉到 n。拖动规模，看两条曲线怎么分岔。"
    ),
    "params": [
        # n：20 起步（φ^20≈1.5万，还能忍），到 40（φ^40≈2.3亿，彻底跑不动）
        {"key": "n", "label": "n", "min": 20, "max": 40, "step": 1, "value": 35},
        # 实现方式：0 = 朴素递归，1 = 闭包记忆化
        {"key": "memo", "label": "实现方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["朴素递归", "闭包记忆化"]},
    ],
    "metrics": [
        # 朴素递归调用次数：≈ 2·φⁿ，用 1.618 近似 φ
        {"key": "naiveCalls", "label": "朴素递归调用次数", "expr": "2 * pow(1.618, n)", "unit": "次", "fmt": "int"},
        # 记忆化调用次数：每个 n 一次
        {"key": "memoCalls", "label": "记忆化调用次数", "expr": "n", "unit": "次", "fmt": "int"},
        # 当前实现的调用次数
        {"key": "calls", "label": "当前实现调用次数", "expr": "if(memo == 1, memoCalls, naiveCalls)", "unit": "次", "fmt": "int"},
        # 缓存条目数：记忆化后正好 n+1 条
        {"key": "cacheEntries", "label": "缓存条目", "expr": "if(memo == 1, n + 1, 0)", "unit": "条", "fmt": "int"},
        # 递归深度：两种实现一样，都是 n（提示默认递归上限 1000 不是瓶颈）
        {"key": "depth", "label": "递归深度", "expr": "n", "unit": "层", "fmt": "int"},
        # 按每秒 1000 万次函数调用估算的耗时
        {"key": "sec", "label": "预计耗时", "expr": "calls / 10000000", "unit": "秒", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：n 要够大，n<25 时朴素递归也就几十万次，看不出指数爆炸
        {"expr": "n >= 30", "label": "n ≥30（φ³⁰ 已是百万级，指数爆炸才显形）"},
        # 上限：调用次数压在 100 万以内（约 0.1 秒）
        {"expr": "calls <= 1000000", "label": "函数调用 ≤100 万次（约 0.1 秒可完成）"},
        # 缓存真的在起作用，不是空转
        {"expr": "cacheEntries >= 31", "label": "缓存条目 ≥31（说明 n 个状态各只算了一次）"},
    ],
    "insight": (
        "朴素递归慢的根源不是「递归」本身，是**重复子问题**：F(35) 里 F(20) 被算了上千次。"
        "调用次数服从 φⁿ（φ=1.618 是斐波那契的特征根），n 每加 5 就乘 11 倍。"
        "记忆化后每个 n 只算一次，调用次数 = n，复杂度从指数掉到线性。"
        "实现上闭包是最轻的载体——`cache = {}` 藏在函数对象里，"
        "调用方签名不用改，也不用引入全局变量："
        "这正是「一等公民函数 + 闭包」在工程里第一个真实用途，"
        "也是 `functools.lru_cache` 的雏形（它只是把 dict 换成了 LRU 淘汰表）。"
    ),
}


# ============================================================================
# python/py-ch03 · 一亿个整数，列表推导和生成器差多少内存
# ----------------------------------------------------------------------------
# 教学点：列表推导式先把整张表建出来——每个元素一个 PyObject（int 28 字节）
# 加数组里一个 8 字节指针，一亿个就是 3.6GB。生成器只持有一个帧对象，
# 元素算完就丢，内存与 n 无关。这是「惰性 vs 急切」最直观的一次对比。
# 同时给出「小整数缓存」对照：0~256 的 int 对象复用，只花指针的 8 字节。
# ============================================================================
py_ch03 = {
    "kind": "sandbox",
    "title": "一亿个整数，列表推导和生成器差多少内存",
    "brief": (
        "`[x*x for x in range(n)]` 会先把 n 个结果全建出来再交给你，"
        "每个 int 对象 28 字节，列表里还要一个 8 字节指针——一亿个就是 3.6GB。"
        "`(x*x for x in range(n))` 只返回一个生成器，算一个丢一个，内存是常数。"
        "把元素数拖到真实数据管道的规模，看「急切建表」和「惰性求值」的内存分岔。"
    ),
    "params": [
        # 元素数（百万）：1 到 200
        {"key": "nM", "label": "元素数（百万）", "min": 1, "max": 200, "step": 1, "value": 50},
        # 求值方式：0 = 列表推导式，1 = 生成器表达式
        {"key": "mode", "label": "求值方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["列表推导式 [ ]", "生成器表达式 ( )"]},
    ],
    "metrics": [
        {"key": "elems", "label": "元素数", "expr": "nM * 1000000", "unit": "个", "fmt": "int"},
        # 列表推导：n × (int 对象 28B + 指针 8B)
        {"key": "listMB", "label": "列表推导占用", "expr": "nM * 1000000 * 36 / 1048576", "unit": "MB", "fmt": "int"},
        # 生成器：一个帧对象 + 迭代器，常数级
        {"key": "genMB", "label": "生成器占用", "expr": "0.05", "unit": "MB", "fmt": "int"},
        # 当前方案
        {"key": "chosenMB", "label": "当前方案占用", "expr": "if(mode == 1, genMB, listMB)", "unit": "MB", "fmt": "int"},
        # 对照：小整数（0~256）复用对象，列表里只剩指针
        {"key": "smallIntMB", "label": "若命中整数缓存（只算指针）", "expr": "nM * 1000000 * 8 / 1048576", "unit": "MB", "fmt": "int"},
        # 倍数
        {"key": "ratio", "label": "列表 / 生成器", "expr": "listMB / 0.05", "unit": "倍", "fmt": "int"},
    ],
    "checks": [
        # 下限：千万级起步，小了两种写法都无所谓
        {"expr": "elems >= 10000000", "label": "元素数 ≥1000 万（规模够大才需要选惰性）"},
        # 痛点：急切建表必然过 GB
        {"expr": "listMB >= 800", "label": "列表推导占用 ≥800MB（这才是要解决的痛点）"},
        # 上限：选定方案压进 64MB
        {"expr": "chosenMB <= 64", "label": "当前方案 ≤64MB（进程能安心活着）"},
    ],
    "insight": (
        "列表推导式不是「写法糖」，它是一句 `list(...)`：先把所有元素落实成对象，"
        "再交给你。每个非缓存 int 占 28 字节，列表还要 8 字节指针，"
        "所以一亿个元素是 3.6GB——而生成器只有 O(1) 的帧开销。"
        "这条差异决定了数据管道的写法："
        "`sum(x*x for x in data)` 全程不落地，`sum([x*x for x in data])` 先建一遍全表。"
        "注意 `smallIntMB` 那行：0~256 的整数被 CPython 缓存复用，"
        "列表里只剩指针，这也是「同样一亿个元素，内存可能差 4.5 倍」的原因——"
        "**对象个数不等于元素个数**，这是 Python 内存账本里最容易漏的一项。"
    ),
}


# ============================================================================
# python/py-ch04 · 接口返回的中文，为什么体积大了 1.7 倍
# ----------------------------------------------------------------------------
# 教学点：json.dumps 默认 ensure_ascii=True，所有非 ASCII 字符会被转成
# \uXXXX 六个字节。一个中文字符 UTF-8 是 3 字节，转义后 6 字节——翻倍。
# 一条 100 字符的记录（60 ASCII + 40 中文）从 180 字节涨到 300 字节。
# 这正是"接口返回中文特别大 / 抓包里全是 \u4f60\u597d"的真实成因。
# ============================================================================
py_ch04 = {
    "kind": "sandbox",
    "title": "接口返回的中文，为什么体积大了 1.7 倍",
    "brief": (
        "`json.dumps` 默认带 `ensure_ascii=True`，它会把所有非 ASCII 字符转成 "
        "`\\uXXXX`——一个中文字符从 UTF-8 的 3 字节变成 6 字节。"
        "一条记录里中文越多，膨胀越明显；日志和接口里那些 "
        "`\\u4f60\\u597d` 就是这么来的。"
        "拖动记录数与转义开关，把这个 1.7 倍的隐性开销压回预算里。"
    ),
    "params": [
        # 记录数（千条）：10 到 350
        {"key": "recsK", "label": "记录数（千条）", "min": 10, "max": 350, "step": 10, "value": 350},
        # ensure_ascii 开关：0 = False（直接 UTF-8），1 = True（\u 转义，默认值）
        {"key": "ascii", "label": "ensure_ascii", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["False（直接 UTF-8）", "True（转成 \\uXXXX，默认）"]},
    ],
    "metrics": [
        {"key": "recs", "label": "记录数", "expr": "recsK * 1000", "unit": "条", "fmt": "int"},
        # 每条记录 60 个 ASCII 字符 + 40 个中文字符
        # UTF-8：60 + 40*3 = 180 字节；转义：60 + 40*6 = 300 字节
        {"key": "perRecUtf", "label": "每条（UTF-8）", "expr": "180", "unit": "B", "fmt": "int"},
        {"key": "perRecAsc", "label": "每条（\\u 转义）", "expr": "300", "unit": "B", "fmt": "int"},
        {"key": "utfMB", "label": "UTF-8 序列化体积", "expr": "recsK * 1000 * 180 / 1048576", "unit": "MB", "fmt": "int"},
        {"key": "ascMB", "label": "\\u 转义序列化体积", "expr": "recsK * 1000 * 300 / 1048576", "unit": "MB", "fmt": "int"},
        # 当前设置下的体积
        {"key": "chosenMB", "label": "当前设置体积", "expr": "if(ascii == 1, ascMB, utfMB)", "unit": "MB", "fmt": "int"},
        # 膨胀倍数：固定 300/180 = 1.67
        {"key": "ratio", "label": "转义 / UTF-8", "expr": "ascMB / utfMB", "unit": "倍", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：10 万条起，数据量真实
        {"expr": "recs >= 300000", "label": "记录数 ≥30 万（生产规模的接口/日志才有体积问题）"},
        # 痛点：默认转义方案在这个规模下会超预算
        {"expr": "ascMB >= 80", "label": "转义方案 ≥80MB（默认设置的真实代价）"},
        # 上限：当前设置的体积压进 64MB
        {"expr": "chosenMB <= 64", "label": "当前设置 ≤64MB（传输与落盘预算）"},
    ],
    "insight": (
        "`ensure_ascii=True` 是 json 模块为了「输出只含 ASCII、任何老系统都能读」做的保守默认，"
        "代价是每个非 ASCII 字符从 3 字节涨到 6 字节。"
        "一条 100 字符的记录里 40 个中文，体积从 180B 涨到 300B——1.67 倍。"
        "所以对接中文接口时先关掉它：`json.dumps(obj, ensure_ascii=False)`，"
        "再配合 `encode('utf-8')` 落盘。"
        "顺带一提，`indent=2` 是另一个隐性膨胀源：每层缩进都占字节，"
        "日志/传输场景一律用 `separators=(',', ':')` 压到最紧。"
    ),
}


# ============================================================================
# python/py-ch05 · 两个 G 的日志，为什么 readlines 直接把进程打死
# ----------------------------------------------------------------------------
# 教学点：`f.readlines()` 把整个文件解成 str 列表搬进内存——不只是原始字节，
# 每行还要一个 49 字节的 str 头（PyASCIIObject）+ 指针。
# 2GB / 100 字符一行 → 2000 万行 → 约 3GB 常驻。
# `for line in f` 只维持一个 8KB 缓冲和当前行，内存与文件大小无关。
# ============================================================================
py_ch05 = {
    "kind": "sandbox",
    "title": "两个 G 的日志，为什么 readlines 直接把进程打死",
    "brief": (
        "`f.readlines()` 会一次性把整个文件解成字符串列表塞进内存："
        "不只是原始 2GB 字节，每行还要一个 49 字节的 str 对象头和 8 字节指针。"
        "两千万行日志，常驻内存直接冲到 3GB 以上，容器当场 OOM。"
        "`for line in f` 只维持一个 8KB 读缓冲和当前行，"
        "内存与文件大小完全无关。把文件规模拖到真实日志量级，看两条线的差别。"
    ),
    "params": [
        # 文件大小（MB）：100 到 4096
        {"key": "fileMB", "label": "日志文件大小", "min": 100, "max": 4096, "step": 100, "value": 2048, "unit": "MB"},
        # 读法：0 = readlines 全量，1 = 逐行迭代（流式）
        {"key": "mode", "label": "读取方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["f.readlines() 全读", "for line in f 流式"]},
    ],
    "metrics": [
        # 行数：假设每行 100 字符
        {"key": "linesM", "label": "行数", "expr": "fileMB * 1048576 / 100 / 1000000", "unit": "百万行", "fmt": "fix2"},
        # readlines 常驻：每行 str 头 49B + 内容 100B + 列表指针 8B ≈ 1.57 倍原始体积
        {"key": "readMB", "label": "readlines 常驻内存", "expr": "fileMB * 1.57", "unit": "MB", "fmt": "int"},
        # 流式：8KB 缓冲 + 当前行，常数
        {"key": "streamMB", "label": "流式常驻内存", "expr": "0.05", "unit": "MB", "fmt": "int"},
        # 当前方案
        {"key": "chosenMB", "label": "当前方案常驻", "expr": "if(mode == 1, streamMB, readMB)", "unit": "MB", "fmt": "int"},
        # 倍数
        {"key": "ratio", "label": "全读 / 流式", "expr": "readMB / 0.05", "unit": "倍", "fmt": "int"},
        # 需要遍历的字符总数：说明流式并不减少总工作量，只减少峰值内存
        {"key": "totalGB", "label": "总共要处理的字符", "expr": "fileMB / 1024", "unit": "GB", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：1GB 起，小文件两种写法都无感
        {"expr": "fileMB >= 1024", "label": "文件 ≥1GB（真实日志量级）"},
        # 痛点：全读方案必然过 1.5GB
        {"expr": "readMB >= 1500", "label": "readlines 常驻 ≥1.5GB（这就是 OOM 的原因）"},
        # 上限：当前方案压进 512MB
        {"expr": "chosenMB <= 512", "label": "当前方案常驻 ≤512MB（容器能活下来）"},
    ],
    "insight": (
        "「文件大」本身不是问题，**峰值内存**才是。`readlines()` 把文件大小"
        "直接翻译成常驻内存，还要叠上每行一个 str 对象（49 字节头）的开销，"
        "2GB 日志能吃掉 3GB 内存。"
        "`for line in f` 用的是文件对象的迭代协议：内部 8KB 缓冲，读满解析出一行就交给你，"
        "内存是 O(1)，总处理量一点没少（总字符串总量还是 2GB）。"
        "所以流式处理的关键不是「更快」，是「峰值可控」——"
        "同理适用于 `csv.reader(f)`、`json.load` vs `ijson`、`pd.read_csv(chunksize=...)`。"
        "判据里那行 `totalGB` 就是提醒：流式不会让活儿变少，只让内存不涨。"
    ),
}


# ============================================================================
# python/py-ch06 · 一条正则，把 CPU 卡死三十秒
# ----------------------------------------------------------------------------
# 教学点：嵌套量词 `(a+)+$` 在匹配失败时会枚举所有切分方式，回溯次数 2^n。
# 输入长度 30 就是十亿步；长度每加 1 翻倍。改成 `a+$`（或加占有量词/原子组）
# 后引擎不做回溯，线性扫一遍。这就是 ReDoS。
# ============================================================================
py_ch06 = {
    "kind": "sandbox",
    "title": "一条正则，把 CPU 卡死三十秒",
    "brief": (
        "`re.match(r'(a+)+$', 'aaaa...a!')` 对 30 个 a 加一个叹号，"
        "会让你等上几十秒——它不是一个字符一个字符地扫，"
        "而是在失败时枚举「这串 a 该切成几段」的所有可能，回溯 2³⁰ 次。"
        "长度每加 1，时间翻倍；这就是 ReDoS 攻击的原理。"
        "把输入长度拖到攻击者随手就能构造的规模，看灾难性回溯和线性匹配的差距。"
    ),
    "params": [
        # 输入长度：10 到 40
        {"key": "n", "label": "输入长度（个 a）", "min": 10, "max": 40, "step": 2, "value": 30},
        # 写法：0 = 嵌套量词（灾难性），1 = 单层量词（线性）
        {"key": "safe", "label": "正则写法", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["(a+)+$ 嵌套量词", "a+$ 单层量词"]},
    ],
    "metrics": [
        # 灾难性写法：2^n 次回溯
        {"key": "badSteps", "label": "嵌套量词回溯次数", "expr": "pow(2, n)", "unit": "步", "fmt": "int"},
        # 线性写法：n 个字符扫一遍
        {"key": "goodSteps", "label": "单层量词步骤", "expr": "n", "unit": "步", "fmt": "int"},
        # 当前写法
        {"key": "steps", "label": "当前写法步骤", "expr": "if(safe == 1, goodSteps, badSteps)", "unit": "步", "fmt": "int"},
        # 按每秒 1 亿步估算
        {"key": "ms", "label": "预计耗时", "expr": "steps / 100000", "unit": "ms", "fmt": "int"},
        # 倍数：2^n / n
        {"key": "ratio", "label": "嵌套 / 单层", "expr": "badSteps / n", "unit": "倍", "fmt": "int"},
    ],
    "checks": [
        # 下限：长度 28 起，短输入时 2^n 还能忍，看不出问题
        {"expr": "n >= 28", "label": "输入长度 ≥28（2²⁸ 已过亿步，攻击者随手就能构造）"},
        # 上限：步骤压进 1000 万（约 0.1 秒）
        {"expr": "steps <= 10000000", "label": "匹配步骤 ≤1000 万（约 0.1 秒，不会被拖死）"},
        # 痛点：嵌套写法在这个长度下必然爆炸
        {"expr": "badSteps >= 100000000", "label": "嵌套量词 ≥1 亿步（灾难性回溯确实存在）"},
    ],
    "insight": (
        "正则引擎（PCRE、Python re、Java 的 java.util.regex）默认是**回溯式**的："
        "遇到失败就退回上一个选择点换一种切分再试。`(a+)+` 给了引擎两层选择点，"
        "`aaaa...a!` 结尾那个 `!` 让每种切分都失败，于是 2ⁿ 种切分全试一遍。"
        "修法有三条，从轻到重："
        "① 改成等价的线性写法（`a+$`）；"
        "② 用占有量词 `a++$` 或原子组 `(?>a+)+$` 禁止回溯；"
        "③ 换非回溯引擎（RE2、Rust regex），代价是不再支持反向引用。"
        "**永远不要用用户输入去匹配带嵌套量词的正则**——这就是 ReDoS，"
        "一个 30 字节的字符串能让单核跑满三十秒。"
    ),
}


# ============================================================================
# python/py-ch07 · 多线程跑满八核，为什么总时长一点没降
# ----------------------------------------------------------------------------
# 教学点：CPython 的 GIL 保证同一时刻只有一个线程执行字节码，
# CPU-bound 任务开多线程只是轮流跑，还额外付切换开销（略负优化）。
# 要吃满多核必须上多进程。判据要求「任务数 ≥ 核数」才有意义
# （任务比核少时进程也吃不满）。
# ============================================================================
py_ch07 = {
    "kind": "sandbox",
    "title": "多线程跑满八核，为什么总时长一点没降",
    "brief": (
        "八个 CPU-bound 任务，开 8 个线程跑，总时长几乎和串行一样——"
        "因为 CPython 有 GIL，同一时刻只有一个线程在执行字节码，"
        "多线程只是让它们在单核上轮流跑，还要额外付切换开销（比串行还慢一点）。"
        "要吃满多核必须换多进程。把核数与任务数拖到真实场景，"
        "看两种并发模型的加速比怎么分岔。"
    ),
    "params": [
        # 核数：1 到 16
        {"key": "cores", "label": "CPU 核数", "min": 1, "max": 16, "step": 1, "value": 4},
        # 并发模型：0 = threading，1 = multiprocessing
        {"key": "mode", "label": "并发模型", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["threading 多线程", "multiprocessing 多进程"]},
        # 任务数：2 到 64
        {"key": "tasks", "label": "任务数", "min": 2, "max": 64, "step": 2, "value": 32},
    ],
    "metrics": [
        # 线程：GIL 串行 + 5% 切换开销
        {"key": "threadSpeedup", "label": "多线程加速比", "expr": "1 / 1.05", "unit": "倍", "fmt": "fix2"},
        # 进程：吃满 min(核数, 任务数) 个核，付 2% 进程/序列化开销
        {"key": "procSpeedup", "label": "多进程加速比", "expr": "min(cores, tasks) / 1.02", "unit": "倍", "fmt": "fix2"},
        # 当前模型
        {"key": "speedup", "label": "当前加速比", "expr": "if(mode == 1, procSpeedup, threadSpeedup)", "unit": "倍", "fmt": "fix2"},
        # GIL 每秒切换次数：默认 5ms 一次
        {"key": "gilSwitch", "label": "GIL 每秒切换", "expr": "200", "unit": "次/秒", "fmt": "int"},
        # 实际能用的并行度
        {"key": "parallel", "label": "实际并行度", "expr": "if(mode == 1, min(cores, tasks), 1)", "unit": "核", "fmt": "int"},
        # 浪费的核
        {"key": "wasted", "label": "闲置的核", "expr": "cores - parallel", "unit": "核", "fmt": "int"},
    ],
    "checks": [
        # 下限：4 核起，单核机器上讨论并发没意义
        {"expr": "cores >= 4", "label": "核数 ≥4（多核机器才有并行的余地）"},
        # 下限：任务数要 ≥8，任务太少连进程也吃不满
        {"expr": "tasks >= 8", "label": "任务数 ≥8（任务比核少时，多进程也吃不满）"},
        # 上限：必须真的拿到 3.5 倍以上加速
        {"expr": "speedup >= 3.5", "label": "加速比 ≥3.5 倍（要真加速，不是心理安慰）"},
    ],
    "insight": (
        "GIL（Global Interpreter Lock）是 CPython 为保护对象引用计数加的一把全局锁，"
        "同一时刻只有一个线程在执行 Python 字节码。所以："
        "**CPU-bound 多线程 = 单核轮流跑 + 切换开销**，加速比约 0.95（负优化）；"
        "要吃满多核必须上 `multiprocessing`，每个进程一个解释器、一把自己的 GIL。"
        "反过来，**IO-bound 场景多线程是有效的**——线程在等 socket/磁盘时释放 GIL，"
        "这段时间别的线程能跑，所以爬虫、请求聚合用线程池完全够。"
        "判断标准只有一条：任务时间花在**算**上还是花在**等**上。"
        "（Python 3.13 起有 free-threaded 构建可以关掉 GIL，但生态兼容仍在推进中。）"
    ),
}


# ============================================================================
# python/py-ch08 · 一千万行 DataFrame，为什么光一列文本就吃掉 680MB
# ----------------------------------------------------------------------------
# 教学点：pandas 的 object 列每格存一个 Python str 对象的指针，
# 每个 str 至少 49 字节头 + 内容；category 列只存一个整数 code（4 字节）
# 加一张小的类别字典。低基数列（城市、状态、品类）上差距是几十倍。
# ============================================================================
py_ch08 = {
    "kind": "sandbox",
    "title": "一千万行 DataFrame，为什么光一列文本就吃掉 680MB",
    "brief": (
        "pandas 的 `object` 列并不是「紧凑的字符串数组」，它存的是指向 Python str 的指针——"
        "每个字符串至少 49 字节头加内容，一千万行就是几百 MB。"
        "而这些列往往只有几十个不同取值（城市、状态、品类）。"
        "`category` dtype 只存一个 4 字节整数 code，加一张几十项的字典表。"
        "把行数与 dtype 拖到真实数据规模，看这一列的内存怎么从 680MB 掉到 40MB。"
    ),
    "params": [
        # 行数（百万）：1 到 50
        {"key": "rowsM", "label": "行数（百万）", "min": 1, "max": 50, "step": 1, "value": 10},
        # dtype：0 = object（默认），1 = category
        {"key": "cat", "label": "文本列 dtype", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["object（默认）", "category"]},
    ],
    "metrics": [
        {"key": "rows", "label": "行数", "expr": "rowsM * 1000000", "unit": "行", "fmt": "int"},
        # object：每格 str 对象（49B 头 + ~11B 内容）+ 8B 指针 ≈ 68B
        {"key": "objectMB", "label": "object 列占用", "expr": "rowsM * 1000000 * 68 / 1048576", "unit": "MB", "fmt": "int"},
        # category：每行一个 int32 code + 100 个类别的字典表
        {"key": "catMB", "label": "category 列占用", "expr": "rowsM * 1000000 * 4 / 1048576 + 0.01", "unit": "MB", "fmt": "int"},
        # 当前 dtype
        {"key": "chosenMB", "label": "当前 dtype 占用", "expr": "if(cat == 1, catMB, objectMB)", "unit": "MB", "fmt": "int"},
        # 压缩倍数
        {"key": "ratio", "label": "object / category", "expr": "objectMB / catMB", "unit": "倍", "fmt": "fix2"},
        # 整表估算（假设还有 3 个数值列，每列 8 字节）
        {"key": "tableMB", "label": "整表估算（另 3 个 float64 列）", "expr": "chosenMB + rowsM * 1000000 * 24 / 1048576", "unit": "MB", "fmt": "int"},
    ],
    "checks": [
        # 下限：500 万行起，数据量小了不在乎这几十 MB
        {"expr": "rows >= 5000000", "label": "行数 ≥500 万（真实数据管线规模）"},
        # 痛点：object 列必然过 512MB
        {"expr": "objectMB >= 450", "label": "object 列 ≥450MB（这才是要解决的痛点）"},
        # 上限：当前 dtype 压进 128MB
        {"expr": "chosenMB <= 128", "label": "当前 dtype ≤128MB（单列不该吃掉半个容器）"},
    ],
    "insight": (
        "`object` dtype 是 pandas 的「什么都能装」，代价是每格一个 Python 对象指针。"
        "一千万行的城市列，虽然只有 100 个不同取值，却存了一千万个 str 对象——"
        "680MB 换 40MB，只要一句 `astype('category')`。"
        "低基数列（类别数 ≪ 行数）都是 category 的适用场景：省内存、`groupby` 更快、"
        "排序按类别顺序而不是字典序。反例是高基数列（user_id、订单号），"
        "转 category 反而更慢更占内存——它的字典表会涨到和行数同量级。"
        "配套的还有：`float64 → float32`、时间列用 `datetime64` 而不是字符串、"
        "`pd.read_csv(dtype=..., usecols=...)` 在**读入时**就定好类型（比读进来再转省一半峰值）。"
    ),
}


# ============================================================================
# python/py-ch09 · 一百万个对象，__slots__ 到底省了什么
# ----------------------------------------------------------------------------
# 教学点：普通类的实例带一个 __dict__（一个紧凑哈希表），
# 小对象加 4 个属性时这张表约 216 字节——比对象本身大一个数量级。
# __slots__ 把字段布局钉进类型，实例只有「对象头 + 字段指针」，
# 同时禁止动态加属性。百万级实例时差距是 5~6 倍。
# ============================================================================
py_ch09 = {
    "kind": "sandbox",
    "title": "一百万个对象，__slots__ 到底省了什么",
    "brief": (
        "普通类的每个实例都挂着一张 `__dict__`——一个为「随时能加任意属性」准备的哈希表。"
        "哪怕你只用了 4 个字段，这张小表也要两百多字节，比对象本身大一个数量级。"
        "`__slots__` 把字段布局直接钉进类型定义，实例里只剩对象头和 4 个指针，"
        "代价是不能再动态加属性。把实例数拖到百万级，看这笔账差出多少。"
    ),
    "params": [
        # 实例数（百万）：1 到 20
        {"key": "instM", "label": "实例数（百万）", "min": 1, "max": 20, "step": 1, "value": 5},
        # 类定义：0 = 普通类（带 __dict__），1 = __slots__
        {"key": "slots", "label": "类定义", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["普通类（有 __dict__）", "__slots__"]},
    ],
    "metrics": [
        {"key": "inst", "label": "实例数", "expr": "instM * 1000000", "unit": "个", "fmt": "int"},
        # 普通类：对象头 16B + __dict__ 指针 8B + 小 dict 216B + 4 个值指针 32B ≈ 272B
        {"key": "dictMB", "label": "普通类占用", "expr": "instM * 1000000 * 272 / 1048576", "unit": "MB", "fmt": "int"},
        # __slots__：对象头 16B + 4 个字段指针 32B = 48B
        {"key": "slotsMB", "label": "__slots__ 占用", "expr": "instM * 1000000 * 48 / 1048576", "unit": "MB", "fmt": "int"},
        # 当前定义
        {"key": "chosenMB", "label": "当前定义占用", "expr": "if(slots == 1, slotsMB, dictMB)", "unit": "MB", "fmt": "int"},
        # 每个实例的字节数
        {"key": "perInst", "label": "每实例字节", "expr": "if(slots == 1, 48, 272)", "unit": "B", "fmt": "int"},
        # 压缩倍数
        {"key": "ratio", "label": "普通类 / __slots__", "expr": "dictMB / slotsMB", "unit": "倍", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：200 万实例起，少量对象时这点内存无所谓
        {"expr": "inst >= 2000000", "label": "实例数 ≥200 万（规模够大才值得改类定义）"},
        # 痛点：普通类必然过 512MB
        {"expr": "dictMB >= 480", "label": "普通类 ≥480MB（这才是要解决的痛点）"},
        # 上限：当前定义压进 320MB
        {"expr": "chosenMB <= 320", "label": "当前定义 ≤320MB（容器内存预算内）"},
    ],
    "insight": (
        "`__dict__` 是 Python「对象可以随时长出新属性」的代价：每个实例一张哈希表，"
        "哪怕只有 4 个字段也要预留扩容空间，实测约 216 字节。"
        "`__slots__ = ('a','b','c','d')` 把字段名编译进类型，实例只存 4 个指针，"
        "单实例从 272B 降到 48B（5.7 倍），还能顺带防止手滑打错属性名。"
        "代价是：不能再动态加属性、不支持多继承中两个带非空 slots 的基类、"
        "也不能被 `__weakref__` 弱引用了（要弱引用得显式加进 slots）。"
        "工程判断：**大量小对象**（点、边、token、坐标、行情 tick）值得上 slots 或 "
        "`dataclass(slots=True)`；配置类、领域模型这类十几个实例的对象，可读性优先，不必折腾。"
        "另一条路是直接换 `numpy` 结构化数组 / `array` 模块，把「对象」变成「列」，"
        "但那就不再是 OOP 的用法了。"
    ),
}


MODULES = {
    "python/py-ch01": py_ch01,
    "python/py-ch02": py_ch02,
    "python/py-ch03": py_ch03,
    "python/py-ch04": py_ch04,
    "python/py-ch05": py_ch05,
    "python/py-ch06": py_ch06,
    "python/py-ch07": py_ch07,
    "python/py-ch08": py_ch08,
    "python/py-ch09": py_ch09,
}


def main() -> int:
    """读取 labs.json → 写入 9 个 sandbox → 按仓库风格（indent=1/LF）落盘。"""
    with open(LABS, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.setdefault("chapters", {})
    existed = sum(1 for k in MODULES if k in chapters)
    for key, mod in MODULES.items():
        # 幂等：同一章节重复运行结果一致，不会叠加两份
        # 只替换本章的 sandbox，保留 debug 等其它模块（直接赋值会把同章其它玩法静默抹掉）
        kept = [m for m in chapters.get(key, []) if m.get("kind") != "sandbox"]
        chapters[key] = [mod] + kept
        print(f"added {key:<20} ({len(mod['params'])} params / {len(mod['metrics'])} metrics / {len(mod['checks'])} checks)")

    # indent=1 + newline="\n"：与仓库现有风格逐字节一致（indent=2 或 CRLF 会整份假 diff）
    with open(LABS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"written {os.path.normpath(LABS)}  (共 {len(chapters)} 章有精修模块，本次覆盖 {len(MODULES)}，其中已存在 {existed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
