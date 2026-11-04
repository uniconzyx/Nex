#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手工精修模块 · 作者源（唯一真源）
==================================

产出：`content/_handmade/labs.json`（`gen_interactive.py` 读取并入各章 interactive.json）

为什么要有这一层：sandbox / debug 两种玩法没法自动抽——
"该拖哪个旋钮"、"缺的是哪条语句"都是作者判断，正则猜不出来。
所以 43 个模块在这里手写，用 Python 三引号装代码片段（JSON 里手写 \\n 太容易错）。

覆盖两条主线：
    cpp  × 20 章（C/C++ 主线）
    fundamentals × 23 章（408：数据结构 7 / 计组 7 / OS 5 / 网络 4）

写完必须过守门：
    python scripts/audit_handmade_labs.py -v     # 结构 + "这一关真能通关"穷举验证
    python scripts/gen_interactive.py            # 并入各章数据

用法：
    python scripts/_author_labs.py            # 落盘
    python scripts/_author_labs.py --check    # 只比对，有漂移 exit 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "content", "_handmade", "labs.json")


# ══════════════════════════════ 构造助手 ══════════════════════════════


def plain(s):
    """去掉反引号：symptom / expect / why 都是纯文本节点，渲染的是字面的 `。"""
    return s.replace("`", "") if isinstance(s, str) else s


def P(key, label, lo, hi, step, val, unit=None, labels=None):
    d = {"key": key, "label": label, "min": lo, "max": hi, "step": step, "value": val}
    if unit:
        d["unit"] = unit
    if labels:
        d["labels"] = labels
    return d


def M(key, label, expr, unit=None, fmt=None):
    d = {"key": key, "label": label, "expr": expr}
    if unit:
        d["unit"] = unit
    if fmt:
        d["fmt"] = fmt
    return d


def C(expr, label):
    return {"expr": expr, "label": label}


def sb(title, brief, params, metrics, checks, insight):
    return {"kind": "sandbox", "title": title, "brief": plain(brief),
            "params": params, "metrics": metrics,
            "checks": [{"expr": c["expr"], "label": plain(c["label"])} for c in checks],
            "insight": plain(insight)}


def blk(bid, text, for_slot="", why=None):
    d = {"id": bid, "text": text, "for": for_slot}
    if why:
        d["why"] = plain(why)
    return d


def dbg(title, lang, file, symptom, code, slots, blocks, expect, passed):
    return {"kind": "debug", "title": title, "lang": lang, "file": file,
            "symptom": plain(symptom), "code": code, "marker": "‹%n›",
            "slots": [{"id": s[0], "hint": plain(s[1])} for s in slots],
            "blocks": blocks, "expect": plain(expect), "pass": plain(passed)}


# ══════════════════════════════ C/C++ 主线 ══════════════════════════════

CPP = {}

CPP["cpp/cpp-ch01"] = [sb(
    "整型宽度与溢出边界",
    "运营看板的计数用了 int，跑三个月后报表变成负数。拖动位宽与符号位，看同一个 4 字节能装多大的数。",
    [P("bits", "位宽", 8, 64, 8, 32, "bit"),
     P("sign", "符号", 0, 1, 1, 1, None, ["无符号", "有符号"])],
    [M("bytes", "占用", "bits / 8", "字节", "int"),
     M("maxv", "上限", "if(sign, pow(2, bits - 1) - 1, pow(2, bits) - 1)", None, "int"),
     M("minv", "下限", "if(sign, -pow(2, bits - 1), 0)", None, "int")],
    [C("maxv >= 2147483648", "上限能装下 2,147,483,648（日活那类计数的量级）"),
     C("bytes <= 4", "仍然只占 4 字节，不许换成 64 位")],
    "32 位有符号的上限是 2^31-1 ≈ 21.47 亿；同样 4 字节，把符号位也让出来就能装 42.9 亿 —— 代价是没有负数。",
)]

CPP["cpp/cpp-ch02"] = [dbg(
    "默认参数写了两遍",
    "cpp",
    "logging.h / logging.cpp",
    "编译报 `error: call of overloaded 'log_msg(const char [6])' is ambiguous`。声明和定义分在两个文件里，谁都没觉得有问题。",
    """// logging.h
#pragma once
#include <string>

// 声明：默认值只允许出现在这里
void log_msg(const std::string& s, int level = 2);

// logging.cpp
#include "logging.h"
#include <iostream>

‹1›

// main.cpp
// log_msg("ready");   // ← 这一行编译不过
""",
    [("s1", "定义里不能再写一遍默认值")],
    [blk("b1", "void log_msg(const std::string& s, int level) { std::cout << s << '\\n'; }", "s1"),
     blk("b2", "void log_msg(const std::string& s, int level = 2) { std::cout << s << '\\n'; }", "",
         "默认参数只能指定一次：定义里再写一遍是“重复指定默认实参”，直接报错"),
     blk("b3", "void log_msg(const std::string& s) { std::cout << s << '\\n'; }", "",
         "这只是把单参版本又定义了一次，`log_msg(\"ready\")` 面对两个候选函数依旧二义"),
     blk("b4", "void log_msg(std::string s, int level = 2) { std::cout << s << '\\n'; }", "",
         "形参从 const 引用变成值，和声明不是同一个函数——声明与定义对不上，链接期找不到符号")],
    "ready",
    "编译通过，`log_msg(\"ready\")` 走二参版本，level 取声明里的默认值 2。",
)]

CPP["cpp/cpp-ch03"] = [sb(
    "std::string 什么时候开始要堆内存",
    "libstdc++ 的 std::string 自带 15 字节内联缓冲（SSO）。拖动长度，看它从第几个字符开始去堆上要地方。",
    [P("len", "字符串长度", 0, 32, 1, 8, "字符")],
    [M("heapBytes", "堆上申请", "if(len > 15, pow(2, ceil(log2(len + 1))), 0)", "字节", "int"),
     M("moveBytes", "再加一字符要搬", "if(len >= 15, len + 1, 0)", "字节", "int"),
     M("mallocs", "malloc 次数", "if(len > 15, 1, 0)", "次", "int")],
    [C("heapBytes == 0", "还没有向堆申请内存（仍在 SSO 缓冲里）"),
     C("len >= 15", "已经顶到 SSO 的最后一格（15 字节）")],
    "15 字节以内直接塞进对象自己那 32 字节里，一次 malloc 都不需要；第 16 个字符才真正去堆上要地方。短 key 满天飞的场景，std::string 的分配开销是零。",
)]

CPP["cpp/cpp-ch04"] = [dbg(
    "函数里 new 了，收尾少一句",
    "cpp",
    "aggregate.cpp",
    "服务跑三天 RSS 从 300MB 涨到 4.2GB。ASan 不报错 —— 不是崩溃，是没人释放。",
    """int sum(const int* v, int n) {
    if (n <= 0) return 0;
    int* copy = new int[n];
    std::memcpy(copy, v, n * sizeof(int));

    int s = 0;
    for (int i = 0; i < n; ++i) s += copy[i];

‹1›
    return s;
}
""",
    [("s1", "谁 new 谁 delete，而且要配对")],
    [blk("b1", "    delete[] copy;", "s1"),
     blk("b2", "    delete copy;", "",
         "new[] 必须配 delete[]：对数组用 delete 只跑第一个元素的析构，堆头信息对不上，ASan 报 alloc-dealloc-mismatch"),
     blk("b3", "    free(copy);", "",
         "new 和 malloc 不是同一套分配器，混用是未定义行为，glibc 下常常当场 abort"),
     blk("b4", "    // 进程退出会回收，不用管", "",
         "进程退出回收的是整个地址空间，不是这次调用的生命周期 —— 长驻服务里就是每天涨几个 GB 的那种泄漏")],
    "输入 8 个 int 返回它们的和；ASan / LSan 全程静默（无泄漏报告）",
    "new[] 配 delete[]，且只在分配成功之后才走到释放。",
)]

CPP["cpp/cpp-ch05"] = [sb(
    "一百万次调用里的拷贝",
    "传值、const 引用、按值返回、出参引用 —— 同一段调用，四种写法各复制几次？拖动旋钮看总拷贝量。",
    [P("n", "调用次数", 10000, 1000000, 10000, 100000, "次"),
     P("pass", "传参方式", 0, 1, 1, 0, None, ["传值", "const 引用"]),
     P("ret", "返回方式", 0, 1, 1, 0, None, ["按值返回", "出参引用"])],
    [M("copies", "拷贝构造次数", "n * (if(pass == 0, 1, 0) + if(ret == 0, 1, 0))", "次", "int"),
     M("bytes", "额外拷贝字节", "n * (if(pass == 0, 1, 0) + if(ret == 0, 1, 0)) * 1024", "字节", "int"),
     M("ms", "估算耗时", "n * (if(pass == 0, 1, 0) + if(ret == 0, 1, 0)) * 0.00004", "ms", "fix2")],
    [C("copies == 0", "一次拷贝构造都不发生"),
     C("n >= 1000000", "还得扛住一百万次调用")],
    "按值传参 = 一次拷贝构造 + 一次析构；按值返回在关掉 NRVO 时还要再来一次。百万次调用就是百万次深拷贝。引用传参是零成本 —— 前提是你确实只读。",
)]

CPP["cpp/cpp-ch06"] = [sb(
    "虚函数表到底占不占对象",
    "加一个虚函数，对象会变大吗？加虚继承呢？拖两个旋钮，看 sizeof(Derived) 到底怎么变。",
    [P("vfuncs", "虚函数个数", 0, 8, 1, 2),
     P("vbase", "继承方式", 0, 1, 1, 0, None, ["普通继承", "虚继承 Base"])],
    [M("objBytes", "sizeof(Derived)", "8 + if(vfuncs > 0, 8, 0) + vbase * 8", "字节", "int"),
     M("vtblEntries", "虚表条目", "vfuncs", "条", "int"),
     M("indirect", "每次调用额外跳转", "if(vfuncs > 0, 2, 0)", "次", "int")],
    [C("objBytes == 16", "对象正好 16 字节（一个 int + 一个 vptr）"),
     C("vtblEntries >= 3", "至少 3 个虚函数才够用")],
    "对象里只放一个 vptr（8 字节），虚函数有多少个都写在同一张表里，对象不会变大；真正再加 8 字节的是虚继承（多一个虚基类指针）。所以“多态很贵”贵的不是对象大小，是间接跳转打断流水线。",
)]

CPP["cpp/cpp-ch07"] = [dbg(
    "undefined reference to Counter<int>::bump",
    "cpp",
    "counter.h / counter.cpp",
    "模板在头文件里声明、实现写在 .cpp 里，主程序一调用就报 `undefined reference to 'int Counter<int>::bump(int)'`。编译期一句错都没有。",
    """// counter.h
#pragma once
template <typename T>
class Counter {
public:
    T bump(T v);
};

// counter.cpp
#include "counter.h"

template <typename T>
T Counter<T>::bump(T v) { return v + 1; }

‹1›                       // main.cpp 要用 Counter<int>，这里还缺一句

// main.cpp
// Counter<int> c; c.bump(1);   // ← 链接期报错
""",
    [("s1", "让编译器为本 TU 生成 int 版本")],
    [blk("b1", "template class Counter<int>;", "s1"),
     blk("b2", "extern template class Counter<int>;", "",
         "extern template 是反向声明“别在本 TU 实例化”，用它只会让符号更缺"),
     blk("b3", "template <> T Counter<int>::bump(T v) { return v + 1; }", "",
         "这是全特化：T 已经没有归属，而且特化必须在首次隐式实例化之前声明"),
     blk("b4", '#include "main.cpp"', "",
         "反过来包含使用方的源文件只会引入重复定义，治不了“模板实现没被实例化”")],
    "`Counter<int>{}.bump(1)` 返回 2，链接通过",
    "模板不是代码，是代码的图纸。图纸不给编译器看，就什么都不会生成。",
)]

CPP["cpp/cpp-ch08"] = [sb(
    "一百万次 push_back 要搬几次家",
    "vector 满了就按倍数扩容，旧元素全部搬一遍。因子越小越省内存、越费拷贝 —— 拖到既不太慢也不浪费的那一档。",
    [P("n", "元素个数", 10000, 1000000, 10000, 100000, "个"),
     P("factor", "扩容因子", 1.5, 3, 0.5, 2)],
    [M("reallocs", "扩容次数", "ceil(log(n) / log(factor))", "次", "int"),
     M("copies", "累计搬迁元素", "round(n * factor / (factor - 1))", "个", "int"),
     M("wastePct", "容量浪费", "(factor - 1) * 100", "%", "int")],
    [C("reallocs <= 17", "扩容次数压在 17 次以内"),
     C("copies <= 2000000", "累计搬迁不超过 2 倍元素数"),
     C("n >= 1000000", "还得撑住一百万个元素")],
    "扩容是摊还 O(1)，但每一轮都是“申请新块 + 搬全部 + 释放旧块”，搬迁总量约 n·f/(f-1)。知道要放一百万个，就先 reserve(1000000)：一次都不搬。",
)]

CPP["cpp/cpp-ch09"] = [dbg(
    "一边遍历一边 erase",
    "cpp",
    "filter.cpp",
    "删掉所有偶数，结果只删掉一半；换到 Debug 版又在某些时刻崩。业务方的原话是“有时候删，有时候不删”。",
    """std::vector<int> v = {1, 2, 4, 6, 7, 8};
for (auto it = v.begin(); it != v.end(); ) {
‹1›
}
// 期望 {1, 7}
""",
    [("s1", "用 erase 的返回值推进，别再 ++it")],
    [blk("b1", "    if (*it % 2 == 0) it = v.erase(it); else ++it;", "s1"),
     blk("b2", "    if (*it % 2 == 0) v.erase(it);", "",
         "erase 之后 it 已失效，再拿它推进就是未定义行为 —— 这就是“有时候删有时候不删”的来源"),
     blk("b3", "    if (*it % 2 == 0) { v.erase(it); --it; }", "",
         "对已经失效的迭代器做 --，行为完全不可预期"),
     blk("b4", "    v.erase(std::remove_if(v.begin(), v.end(), [](int x) { return x % 2 == 0; }), v.end());", "",
         "写法本身没错，但它不是“循环体里的一句”：放进 for 里每轮都重置迭代器，等于死循环")],
    "输出 `1 7`",
    "erase 返回的是“下一个有效位置”。用返回值推进，而不是让循环头里的 ++it 去猜。",
)]

CPP["cpp/cpp-ch10"] = [sb(
    "环形引用到底漏多少",
    "两个对象互相用 shared_ptr 指着，引用计数永远到不了 0。加一条 weak_ptr 断环，看进程能回收多少。",
    [P("nodes", "对象数", 10, 10000, 10, 1000, "个"),
     P("cycle", "引用结构", 0, 1, 1, 1, None, ["无环", "A↔B 互持"]),
     P("useWeak", "断环手段", 0, 1, 1, 0, None, ["shared 持环", "weak 断环"])],
    [M("leaked", "泄漏对象", "cycle * (1 - useWeak) * nodes", "个", "int"),
     M("leakedKB", "常驻内存", "cycle * (1 - useWeak) * nodes * 48 / 1024", "KB", "int"),
     M("refcntAtExit", "退出时引用计数", "if(cycle * (1 - useWeak) > 0, 1, 0)", None, "int")],
    [C("leaked == 0", "零泄漏"),
     C("cycle == 1", "而且要真的存在环形引用（不能靠“本来就没环”蒙过去）")],
    "shared_ptr 的计数只算强引用；weak_ptr 不参与计数，但能在对象死后安全探测。环上只要有一条边是 weak，计数就能降回 0。别指望“进程要退出了反正会回收”——长驻服务不退。",
)]

CPP["cpp/cpp-ch11"] = [dbg(
    "catch 里 typeid 恒为 Base",
    "cpp",
    "handler.cpp",
    "业务抛的是 InvalidArgument，日志里 what() 却打印成 base —— 多态在 catch 里失效了。",
    """struct Base {
    virtual ~Base() = default;
    virtual std::string what() const { return "base"; }
};
struct InvalidArgument : Base {
    std::string what() const override { return "bad arg"; }
};

try {
    throw InvalidArgument{};
}
‹1›
""",
    [("s1", "捕获的写法决定切不切片")],
    [blk("b1", "catch (const Base& e) { std::cout << e.what(); }", "s1"),
     blk("b2", "catch (Base e) { std::cout << e.what(); }", "",
         "按值捕获发生对象切片：InvalidArgument 的部分被切掉，vptr 变回 Base 的，what() 永远返回 base"),
     blk("b3", "catch (Base* e) { std::cout << e->what(); }", "",
         "抛出的是对象不是指针，这个 catch 一条也接不住，异常直接逃到 terminate"),
     blk("b4", "catch (InvalidArgument e) { std::cout << e.what(); }", "",
         "这样能打印对，但其他异常全部漏网，而且异常对象还要再拷贝一次")],
    "输出 `bad arg`",
    "捕获异常一律 `const 引用`：既不切片，也不多拷贝。",
)]

CPP["cpp/cpp-ch12"] = [dbg(
    "加了个 std::move，反而更慢",
    "cpp",
    "buffer.cpp",
    "某个返回大 vector 的接口，性能剖析里多了一次 3 万元素的 memcpy。代码看起来很“现代”。",
    """std::vector<int> make_buf() {
    std::vector<int> v(30000);
    ‹1›
}
""",
    [("s1", "返回局部变量该怎么写")],
    [blk("b1", "    return v;", "s1"),
     blk("b2", "    return std::move(v);", "",
         "对局部变量写 move 会挡住 NRVO：编译器本来能在调用方原地构造，被 move 一搞必须先造临时对象再移出去，有些场景直接退化成拷贝"),
     blk("b3", "    return std::move(std::vector<int>(30000));", "",
         "对临时量 move 是多余的（它本身就是右值），还平白多构造了一次"),
     blk("b4", "    return &v;", "",
         "返回栈上对象的地址，函数一返回就是悬垂指针")],
    "调用方直接拿到 30000 个元素的 vector，全程零拷贝（NRVO）",
    "返回局部变量就写 `return v;` —— 标准明确允许并要求省略这次拷贝，画蛇添足的 move 只会挡住优化。",
)]

CPP["cpp/cpp-ch13"] = [dbg(
    "文件末尾多算了一行",
    "cpp",
    "sum.cpp",
    "求和结果总比手算多一份。文件里是 1..10，程序输出 cnt=11。",
    """std::ifstream in("nums.txt");
int x = 0, sum = 0, cnt = 0;
while (!in.eof()) {
    in >> x;
‹1›
}
std::cout << "sum=" << sum << " cnt=" << cnt;
""",
    [("s1", "读失败那一次不能算进统计")],
    [blk("b1", "    if (!in.fail()) { sum += x; ++cnt; }", "s1"),
     blk("b2", "    sum += x; ++cnt;", "",
         "这就是 bug 本身：最后一次 `in >> x` 失败时 x 还是上一轮的值，eof 要到失败之后才置位"),
     blk("b3", "    if (!in.eof()) { sum += x; ++cnt; }", "",
         "同一轮里 eof 还没置位，判它等于没判"),
     blk("b4", "    break;", "",
         "第一轮就退出，一个数都读不到")],
    "`sum=55 cnt=10`",
    "读操作本身的结果就是判据：写成 `while (in >> x)` —— 读失败即退出，根本不需要 eof。",
)]

CPP["cpp/cpp-ch14"] = [dbg(
    "SQ(1+2) 算出来是 5",
    "cpp",
    "macro.cpp",
    "单元测试里 `SQ(1 + 2)` 期望 9，实际 5。换成 `SQ(w * h)` 这种调用时又偶尔是对的。",
    """#define SQ(x)  ‹1›

int main() {
    std::cout << SQ(1 + 2) << '\\n';   // 期望 9
}
""",
    [("s1", "宏体怎么写才安全")],
    [blk("b1", "((x) * (x))", "s1"),
     blk("b2", "(x * x)", "",
         "整体括号有了、参数没括号：`SQ(1+2)` 展开成 `(1+2 * 1+2)` = 5"),
     blk("b3", "x * x", "",
         "参数和整体都没括号，`SQ(1+2)` 展开成 `1+2*1+2`，连运算符优先级都变了"),
     blk("b4", "((x) * (x));", "",
         "多出来的分号会被展开到调用点，`if (a) SQ(b); else ...` 直接编译不过")],
    "9",
    "宏是文本替换，不是函数调用：每个参数、整个表达式，各加一层括号。",
)]

CPP["cpp/cpp-ch15"] = [dbg(
    "头文件里的计数器永远停在 0",
    "cpp",
    "metrics.h",
    "头文件里放了个全局计数 `hits`，两个 .cpp 都 include 它。要么链接报 multiple definition，要么改完能编过、但主程序读到的永远是 0。",
    """// metrics.h
#pragma once
‹1›
inline void hit() { ++hits; }

// a.cpp / b.cpp 各自 #include "metrics.h" 并调用 hit()
// main.cpp        打印 hits
""",
    [("s1", "头文件里的定义必须全程序唯一")],
    [blk("b1", "inline int hits = 0;", "s1"),
     blk("b2", "static int hits = 0;", "",
         "static 给每个 TU 一份内部链接副本：a.cpp 和 b.cpp 各加各的，main.cpp 看到的那份永远是 0"),
     blk("b3", "int hits = 0;", "",
         "头文件里写非 inline 定义，被两个 TU 包含就是重复定义，链接直接失败"),
     blk("b4", "extern int hits = 0;", "",
         "extern 加初始化器仍然是定义，重复定义照旧；extern 只能配“不带初始化器”的声明")],
    "累计命中数被所有 TU 共享，主程序读到的不是 0",
    "头文件放声明、定义放一个 .cpp；C++17 之后也可以用 inline 变量 —— 它是唯一允许写进头文件的定义。",
)]

CPP["cpp/cpp-ch16"] = [sb(
    "加线程到底能快多少",
    "加速比不是“线程数”，是 1/(串行比例 + 并行比例/线程数)。拖两个旋钮，找那条让 8 线程跑出 6 倍的分界线。",
    [P("threads", "线程数", 1, 32, 1, 4),
     P("serialPct", "串行占比", 0, 50, 5, 10, "%")],
    [M("speedup", "加速比", "1 / (serialPct / 100 + (1 - serialPct / 100) / threads)", None, "fix2"),
     M("eff", "每线程效率", "(1 / (serialPct / 100 + (1 - serialPct / 100) / threads)) / threads", None, "fix2"),
     M("ms", "单次耗时", "1000 / (1 / (serialPct / 100 + (1 - serialPct / 100) / threads))", "ms", "fix2")],
    [C("speedup >= 6", "加速比至少 6 倍"),
     C("threads <= 8", "而且只能用 8 个线程")],
    "串行占 10% 时理论上限就是 10 倍，和你加多少线程无关：8 线程只有 4.7 倍，加到 32 线程也只到 7.8 倍。优化的顺序永远是“先砍串行段”，而不是“再加机器”。",
)]

CPP["cpp/cpp-ch17"] = [dbg(
    "模板里缺一个 typename",
    "cpp",
    "dump.h",
    "GCC 报 `error: need 'typename' before 'C::const_iterator' because 'C' is a dependent scope`。这份模板在 MSVC 下能过，换编译器就炸。",
    """template <typename C>
void dump(const C& c) {
‹1›
    for (It it = c.begin(); it != c.end(); ++it)
        std::cout << *it << ' ';
}
""",
    [("s1", "取依赖类型要先消歧")],
    [blk("b1", "    using It = typename C::const_iterator;", "s1"),
     blk("b2", "    using It = C::const_iterator;", "",
         "C 是依赖名，编译器无法判断 C::const_iterator 是类型还是静态成员，必须加 typename 消歧"),
     blk("b3", "    typedef C::const_iterator It;", "",
         "typedef 也救不了，缺 typename 一样报那句错"),
     blk("b4", "    using It = C::iterator;", "",
         "const 容器上 begin() 返回的是 const_iterator，取 iterator 类型对不上，实例化时才炸")],
    "编译通过，对 int 容器实例化后输出 `1 2 3`",
    "依赖名前面加 typename —— 它不是“这是类型”的修辞，是给编译器的消歧指令。",
)]

CPP["cpp/cpp-ch18"] = [sb(
    "只改声明顺序，对象从 24 字节降到 16",
    "64 位下三种字段顺序，同样的成员、不同的 sizeof。拖到最紧凑的那一版。",
    [P("layout", "字段顺序", 0, 2, 1, 0, None,
       ["char, int, char, double", "double, int, char, char", "char, char, int, double"])],
    [M("size", "sizeof", "if(layout == 0, 24, 16)", "字节", "int"),
     M("waste", "填充字节", "if(layout == 0, 24, 16) - 14", "字节", "int"),
     M("perMB", "每 MB 能放", "1048576 / (if(layout == 0, 24, 16))", "个", "int")],
    [C("size == 16", "对象压到 16 字节"),
     C("waste <= 2", "填充不超过 2 字节")],
    "成员按“由大到小”排，填充最少：填充只发生在“下一个成员塞不进当前空洞”的时候。百万个对象，8 字节 × 100 万 = 8MB 内存，还有成片被打断的缓存行。",
)]

CPP["cpp/cpp-ch19"] = [dbg(
    "add_library 之后还是 undefined reference",
    "cmake",
    "CMakeLists.txt",
    "库编译通过、可执行文件编译通过，链接阶段一堆 `undefined reference to 'common::parse()'`。CMakeLists 看着“该加的加了”。",
    """add_library(common STATIC common.cpp)
add_executable(app main.cpp)

‹1›
""",
    [("s1", "把 app 和 common 连起来")],
    [blk("b1", "target_link_libraries(app PRIVATE common)", "s1"),
     blk("b2", "target_link_libraries(common PRIVATE app)", "",
         "方向反了：依赖是 app → common。写成 common 依赖 app，CMake 直接报错（不能链接可执行文件）"),
     blk("b3", "include_directories(${CMAKE_SOURCE_DIR}/common)", "",
         "这只加头文件搜索路径，符号一个都没链上"),
     blk("b4", "add_dependencies(app common)", "",
         "add_dependencies 只管构建顺序（保证先编 common），不传任何链接参数")],
    "`app` 链接成功，`common::parse()` 能解析到符号",
    "现代 CMake 里依赖是 target 之间的有向边：谁用谁，就从使用者指向被使用者，并且写明 PRIVATE / PUBLIC 作用域。",
)]

CPP["cpp/cpp-ch20"] = [sb(
    "连接池要开多大",
    "池子按 CPU 核数拍脑袋定，晚高峰就排队。真实公式是“并发 = QPS × 单请求耗时”。拖三个旋钮凑够余量。",
    [P("qps", "峰值 QPS", 500, 8000, 500, 1000),
     P("latency", "单请求耗时", 20, 200, 10, 60, "ms"),
     P("pool", "连接池大小", 10, 400, 10, 50)],
    [M("concurrency", "需要并发数", "qps * latency / 1000", "个", "int"),
     M("util", "池利用率", "qps * latency / 1000 / pool", None, "fix2"),
     M("queueMs", "估算排队", "if(qps * latency / 1000 > pool, (qps * latency / 1000 - pool) * latency / pool, 0)", "ms", "int")],
    [C("concurrency <= pool", "峰值并发能被池子接住"),
     C("util >= 0.6", "利用率不低于 60%，池子不能空转"),
     C("queueMs == 0", "没有请求在池外排队")],
    "池子至少 ≥ 峰值并发，否则请求在池外排队；但也别开太大：利用率长期低于 60% 说明瓶颈在别处（常见是慢 SQL），加连接只会把数据库压垮。",
)]


# ══════════════════════════════ 408 主线 ══════════════════════════════

FUND = {}

FUND["fundamentals/fund-ch01"] = [sb(
    "在第 i 个位置插入，谁更便宜",
    "顺序表要搬后半段，链表要走到 i 的前驱。拖动位置和规模，看两种结构各付多少代价。",
    [P("n", "元素个数", 1000, 100000, 1000, 10000),
     P("posPct", "插入位置", 0, 100, 5, 50, "%")],
    [M("seqMoves", "顺序表搬移元素", "n * (100 - posPct) / 100", "个", "int"),
     M("listSteps", "链表步进结点", "n * posPct / 100", "个", "int"),
     M("listMemKB", "链表指针开销", "n * 8 / 1024", "KB", "int")],
    [C("listSteps < seqMoves", "链表走的结点数少于顺序表搬移的元素数"),
     C("posPct <= 15", "而且只在表头附近（前 15%）")],
    "链表只在表头附近赢：走到第 i 个结点本身就是 O(i)，插入那一步 O(1) 根本不算钱。顺序表在表尾插入反而是 O(1)。所以“链表插入快”永远要补一句前提 —— 你已经在那个位置上了。",
)]

FUND["fundamentals/fund-ch02"] = [sb(
    "数组 m 格，循环队列能装几个",
    "“牺牲一个单元”判满时，m 格只能存 m-1 个。加一个 size 计数器才吃得满。拖两个旋钮看利用率。",
    [P("m", "数组长度", 4, 64, 4, 16, "格"),
     P("mode", "判满方式", 0, 1, 1, 0, None, ["牺牲一格", "加 size 计数器"])],
    [M("cap", "可存元素", "m - (1 - mode)", "个", "int"),
     M("util", "空间利用率", "(m - (1 - mode)) / m", None, "pct"),
     M("worstPct", "最坏浪费", "(1 - mode) / m * 100", "%", "fix2")],
    [C("cap == m", "一个格子都不浪费"),
     C("util >= 0.9", "利用率至少 90%")],
    "队空 front==rear、队满 front==rear，两个状态撞在一起，所以要么牺牲一格，要么记 size / 加 tag。牺牲一格在 m=16 时浪费 6%，m 越小比例越难看 —— 408 里两种写法都考。",
)]

FUND["fundamentals/fund-ch03"] = [sb(
    "5 层完全二叉树最少几个结点",
    "高度 h 的完全二叉树，结点数落在 [2^(h-1), 2^h − 1]。拖结点数，看高度什么时候跳级。",
    [P("n", "结点数", 1, 63, 1, 20)],
    [M("h", "高度", "floor(log2(n)) + 1", "层", "int"),
     M("minAtH", "该高度最少", "pow(2, h - 1)", "个", "int"),
     M("maxAtH", "该高度最多", "pow(2, h) - 1", "个", "int"),
     M("lastLevel", "最后一层结点", "n - (pow(2, h - 1) - 1)", "个", "int")],
    [C("h == 5", "高度正好 5 层"),
     C("lastLevel == 16", "最后一层满编 16 个")],
    "高度 5 的完全二叉树，结点数只能落在 16~31；第 5 层从第 16 个结点开始排队。做 408 算结点数的题，先定高度、再定最后一层占几个 —— 顺序反了必错。",
)]

FUND["fundamentals/fund-ch04"] = [sb(
    "稀疏图为什么不用矩阵",
    "矩阵固定 n² 格，邻接表只存实际存在的边。拖顶点数和稠密度，看两者差几个数量级。",
    [P("v", "顶点数", 4, 400, 4, 100),
     P("density", "稠密度", 1, 50, 1, 15, "%")],
    [M("e", "边数", "round(v * (v - 1) / 2 * density / 100)", "条", "int"),
     M("matrixKB", "邻接矩阵", "v * v * 4 / 1024", "KB", "int"),
     M("listKB", "邻接表", "(v * 8 + round(v * (v - 1) / 2 * density / 100) * 12) / 1024", "KB", "int"),
     M("ratio", "矩阵 / 表", "(v * v * 4 / 1024) / ((v * 8 + round(v * (v - 1) / 2 * density / 100) * 12) / 1024)", "倍", "fix2")],
    [C("ratio >= 10", "矩阵比邻接表大 10 倍以上"),
     C("density <= 10", "而且图是稀疏的（稠密度 ≤ 10%）")],
    "矩阵的优势是 O(1) 判邻接，代价是 n² 空间和 n² 遍历；稠密图才划算。Prim 用矩阵 O(n²)、Kruskal 适合稀疏图，根子都在这张表上。",
)]

FUND["fundamentals/fund-ch05"] = [sb(
    "哈希表装多满才不拖查找",
    "线性探测的 ASL 随 α 爆炸，拉链法平缓得多。拖 α 和冲突处理方式，找那条让查找仍然便宜的分界线。",
    [P("alpha", "装填因子 α", 0.1, 0.95, 0.05, 0.7, None, None),
     P("mode", "冲突处理", 0, 1, 1, 0, None, ["线性探测", "拉链法"])],
    [M("aslSucc", "查找成功 ASL", "if(mode == 0, (1 + 1 / (1 - alpha)) / 2, 1 + alpha / 2)", None, "fix2"),
     M("aslFail", "查找失败 ASL", "if(mode == 0, (1 + 1 / pow(1 - alpha, 2)) / 2, alpha)", None, "fix2"),
     M("cluster", "聚集程度", "if(mode == 0, round(alpha * 20), 0)", None, "int")],
    [C("aslSucc <= 1.4", "查找成功的 ASL 不超过 1.4"),
     C("alpha >= 0.4", "而且表要装到 40% 以上，别靠空表取巧")],
    "线性探测的失败 ASL 在 α=0.9 时是 50.5 —— 这就是“删一个元素能让整张表变慢”的原因（要用墓碑标记）。拉链法可以装到 α>1，代价是指针和缓存不友好。",
)]

FUND["fundamentals/fund-ch06"] = [sb(
    "百万数据要稳又要快",
    "冒泡稳但 n²；快排快但不稳；堆排省空间也不稳。拖算法与规模，看比较次数和稳定性两栏怎么同时满足。",
    [P("n", "元素个数", 1000, 1000000, 1000, 100000),
     P("algo", "算法", 0, 3, 1, 1, None, ["冒泡", "快速排序", "归并排序", "堆排序"])],
    [M("cmp", "比较次数", "if(algo == 0, n * (n - 1) / 2, n * log2(n))", "次", "int"),
     M("stable", "稳定", "if(algo == 0 || algo == 2, 1, 0)", None, "int"),
     M("extraKB", "额外空间", "if(algo == 2, n * 4 / 1024, 0)", "KB", "int")],
    [C("stable == 1", "必须是稳定排序"),
     C("cmp <= 20000000", "比较次数压在两千万以内"),
     C("n >= 1000000", "而且得撑住一百万条")],
    "归并是唯一“稳定 + O(n log n)”的通用比较排序，代价是 O(n) 辅助空间；快排靠原地和常数小赢在工程上 —— 所以 std::sort 是内省快排、std::stable_sort 是归并。408 问“稳定且 O(n log n)”，答归并。",
)]

FUND["fundamentals/fund-ch07"] = [sb(
    "单精度为什么只有 7 位有效数字",
    "1 位符号 + 8 位阶码 + 23 位尾数。拖位宽分配，凑出单精度的偏置和十进制精度。",
    [P("expBits", "阶码位数", 4, 11, 1, 8),
     P("fracBits", "尾数位数", 8, 52, 1, 16)],
    [M("bias", "偏置", "pow(2, expBits - 1) - 1", None, "int"),
     M("digits", "十进制有效位", "floor(fracBits * log10(2)) + 1", "位", "int"),
     M("maxExp", "最大阶", "pow(2, expBits - 1) - 1", None, "int")],
    [C("bias == 127", "偏置是 127（单精度约定）"),
     C("digits == 7", "十进制有效位正好 7 位"),
     C("fracBits == 23", "尾数 23 位")],
    "阶码 8 位给出 −126~127 的指数范围，尾数 23 位给出约 7 位十进制精度。这也是 float 存 16777217 会变成 16777216 的原因：2^24 之后间隔已经大于 1。",
)]

FUND["fundamentals/fund-ch08"] = [sb(
    "命中率 90% 还不够",
    "AMAT = 命中时间 + 缺失率 × 缺失代价。缺失代价通常是命中的几十倍，所以命中率差一个点就差很多。",
    [P("hit", "命中率", 0.5, 0.99, 0.01, 0.9),
     P("hitNs", "命中时间", 1, 10, 1, 2, "ns"),
     P("memNs", "缺失代价", 40, 200, 20, 100, "ns")],
    [M("amat", "AMAT", "hitNs + (1 - hit) * memNs", "ns", "fix2"),
     M("speedup", "相对无 Cache", "memNs / (hitNs + (1 - hit) * memNs)", "倍", "fix2"),
     M("missPct", "缺失耗时占比", "(1 - hit) * memNs / (hitNs + (1 - hit) * memNs) * 100", "%", "int")],
    [C("amat <= 5", "AMAT 压到 5ns 以内"),
     C("hit >= 0.9", "命中率不低于 90%")],
    "命中率 95% 时仍有 60% 的时间花在缺失上（2ns vs 3ns）。所以优化优先级永远是：先减少缺失，再降低缺失代价（多级 Cache），最后才压命中时间。",
)]

FUND["fundamentals/fund-ch09"] = [sb(
    "时间片切多大才不浪费",
    "q 不是 s 的因数时，最后一轮只跑半格；q 太小时轮数变多、周转时间跟着涨。拖三个旋钮。",
    [P("q", "时间片 q", 1, 8, 1, 3, "格"),
     P("s", "每进程服务时间 s", 4, 16, 2, 8, "格"),
     P("n", "进程数", 2, 10, 1, 5)],
    [M("rounds", "轮数", "ceil(s / q)", "轮", "int"),
     M("wastePct", "时间片浪费", "(ceil(s / q) * q - s) / s * 100", "%", "int"),
     M("avgTurn", "平均周转", "n * q * (ceil(s / q) - 1) + q * (n + 1) / 2", "格", "fix2")],
    [C("wastePct == 0", "时间片没有浪费（q 正好整除 s）"),
     C("avgTurn <= 40", "平均周转压在 40 格以内")],
    "平均周转 = n·q·(k−1) + q(n+1)/2，k 是每个进程的轮数。q 不能整除 s 时每轮都白扔一截；q 太小时 k 变大，切换开销和周转时间一起涨。真实系统取 10~100ms，就是为了让绝大多数进程在一两个片内跑完。",
)]

FUND["fundamentals/fund-ch10"] = [sb(
    "一级页表为什么必须拆",
    "32 位、4KB 页、4B 页表项：一个进程就是 4MB 页表，全常驻根本放不下。拖位宽与页大小看这张表。",
    [P("bits", "虚拟地址位宽", 32, 48, 4, 40, "bit"),
     P("pageKB", "页大小", 4, 64, 4, 4, "KB"),
     P("entryB", "页表项大小", 4, 8, 4, 4, "B")],
    [M("pages", "页数", "pow(2, bits) / (pageKB * 1024)", "页", "int"),
     M("tableMB", "整张页表", "pow(2, bits) / (pageKB * 1024) * entryB / 1048576", "MB", "fix2"),
     M("levels", "最少级数", "ceil(log(pow(2, bits) / (pageKB * 1024)) / log(pageKB * 1024 / entryB))", "级", "int"),
     M("ptePerPage", "每页页表项", "pageKB * 1024 / entryB", "个", "int")],
    [C("tableMB <= 4", "整张页表不超过 4MB"),
     C("levels <= 2", "两级以内就能覆盖")],
    "32 位 / 4KB 页 = 20 位页号，每页能放 1024 个页表项 = 10 位，所以正好两级、每级页表 4KB。多级页表不是为了更快，是为了让页表本身能按需换出。",
)]

FUND["fundamentals/fund-ch11"] = [sb(
    "窗口小了，带宽白给",
    "吞吐 ≤ 窗口 / RTT。链路再快，窗口不够也跑不满。拖窗口与 RTT，看吞吐卡在哪。",
    [P("rtt", "往返时延 RTT", 10, 200, 10, 50, "ms"),
     P("winKB", "接收窗口", 16, 1024, 16, 64, "KB")],
    [M("mbps", "吞吐上限", "winKB * 8.192 / rtt", "Mbps", "fix2"),
     M("needKB", "跑满百兆需要", "100 * rtt / 8.192", "KB", "int"),
     M("ratio", "占百兆链路的比例", "winKB * 8.192 / rtt", "%", "fix2")],
    [C("mbps >= 100", "吞吐至少 100Mbps"),
     C("winKB <= 256", "窗口不超过 256KB")],
    "100Mbps 链路上 RTT 50ms，要跑满得 610KB 窗口，而经典 TCP 窗口上限是 64KB —— 所以长肥管道必须开窗口扩大（RFC 1323）。带宽时延积 BDP 就是“在途数据量”，窗口小于它，链路就是空转。",
)]

FUND["fundamentals/fund-ch12"] = [dbg(
    "上了 CDN，回源率还是 90%",
    "js",
    "static.js",
    "资源文件名里已经打了内容指纹（app.9f3c1a.js），CDN 也接了，回源率还是 90% 以上。问题出在响应头。",
    """// GET /static/app.9f3c1a.js
res.setHeader('Content-Type', 'application/javascript');
‹1›
""",
    [("s1", "指纹资源该发什么缓存策略")],
    [blk("b1", "res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');", "s1"),
     blk("b2", "res.setHeader('Cache-Control', 'no-cache');", "",
         "no-cache 不是“不缓存”，而是“用之前必须回源校验”（协商缓存）—— 回源一次都没少"),
     blk("b3", "res.setHeader('Cache-Control', 'no-store');", "",
         "连存都不许存，CDN 和浏览器每次重新下载"),
     blk("b4", "res.setHeader('Cache-Control', 'max-age=0');", "",
         "等价于立刻过期，每次都要协商")],
    "指纹资源一年内不再回源，回源率降到个位数",
    "带内容指纹的资源用 `max-age` 一年 + `immutable`；HTML 入口用 `no-cache`（必须校验）。这两条是两套策略，别用一条治所有请求。",
)]

FUND["fundamentals/fund-ch13"] = [sb(
    "主频高就一定快吗",
    "执行时间 = 指令数 × CPI / 主频。主频翻倍但 CPI 涨了，可能反而更慢。拖三个旋钮算总时间。",
    [P("ghz", "主频", 1, 5, 0.5, 3, "GHz"),
     P("cpi", "CPI", 1, 10, 1, 5),
     P("instrM", "指令数", 10, 1000, 10, 200, "百万条")],
    [M("ms", "执行时间", "instrM * cpi / ghz", "ms", "fix2"),
     M("mips", "MIPS", "ghz * 1000 / cpi", None, "int"),
     M("cyclesM", "时钟周期", "instrM * cpi", "百万", "int")],
    [C("ms <= 150", "总执行时间不超 150ms"),
     C("mips >= 800", "MIPS 不低于 800")],
    "主频只在分母，CPI 在分子：一段分支密集的代码 CPI 从 1.5 涨到 4.5，主频从 3G 提到 4G 还是亏。这就是流水线深度竞赛在 2005 年停下来的原因。",
)]

FUND["fundamentals/fund-ch14"] = [sb(
    "指令格式怎么切位",
    "指令长度 = 操作码位数 + 地址字段位数 × 个数。扩大操作码就挤压寻址空间，一增一减。",
    [P("opBits", "操作码位数", 3, 8, 1, 6),
     P("addrBits", "每地址位数", 4, 12, 1, 8)],
    [M("instrCnt", "可编指令数", "pow(2, opBits)", "条", "int"),
     M("spaceB", "寻址空间", "pow(2, addrBits)", "B", "int"),
     M("lenBits", "指令长度", "opBits + 2 * addrBits", "bit", "int")],
    [C("instrCnt == 64", "能编 64 条指令"),
     C("spaceB == 4096", "地址能寻到 4KB")],
    "同样总位数下，操作码和地址字段是零和：多一位操作码 = 少一位地址 = 寻址空间砍半。所以才有“扩展操作码”——把不用的地址字段借给操作码，用频率换空间。",
)]

FUND["fundamentals/fund-ch15"] = [sb(
    "5 级流水线能快几倍",
    "理想加速比约等于级数，但冒险停顿会把它吃回去。拖级数、指令数与停顿比例。",
    [P("stages", "流水级数", 3, 8, 1, 5),
     P("n", "指令数", 100, 1000, 100, 500),
     P("stallPct", "停顿比例", 0, 50, 5, 25, "%")],
    [M("base", "串行周期", "n * stages", "周期", "int"),
     M("piped", "流水周期", "n + (stages - 1) + n * stallPct / 100", "周期", "int"),
     M("speedup", "加速比", "n * stages / (n + (stages - 1) + n * stallPct / 100)", "倍", "fix2")],
    [C("speedup >= 3", "加速比至少 3 倍"),
     C("stallPct <= 10", "停顿比例压到 10% 以内")],
    "加速比的上限就是级数，但每多一级就多一份冒险可能和一份寄存器开销。经典 5 级流水线（IF/ID/EX/MEM/WB）是“加速比 / 代价”的甜点，也是 408 必考那张时空图。",
)]

FUND["fundamentals/fund-ch16"] = [sb(
    "位宽 × 频率，还要扣开销",
    "理论带宽 = 位宽/8 × 频率；实际还要乘上有效传输周期占比。拖三个旋钮。",
    [P("width", "数据线宽度", 16, 128, 16, 32, "bit"),
     P("mhz", "总线频率", 100, 3200, 100, 800, "MHz"),
     P("eff", "有效周期占比", 50, 100, 10, 90, "%")],
    [M("theoryMBs", "理论带宽", "width / 8 * mhz", "MB/s", "int"),
     M("realMBs", "实际带宽", "width / 8 * mhz * eff / 100", "MB/s", "int"),
     M("perTransfer", "每次传输", "width / 8", "B", "int")],
    [C("realMBs >= 4000", "实际带宽不低于 4000MB/s"),
     C("width <= 64", "而且数据线不超过 64 位（别靠堆线宽硬凑）")],
    "位宽翻倍、带宽翻倍，但要 64 根数据线加对应引脚，成本远高于翻倍；所以 DDR 走的是“一个时钟周期传两次”。算带宽题先问一句：这频率是总线时钟，还是数据传输率。",
)]

FUND["fundamentals/fund-ch17"] = [sb(
    "每秒 5 万次 I/O，CPU 还剩多少",
    "轮询每次两万周期、中断两千、DMA 只要一百。拖 I/O 方式与频率，看 CPU 占用。",
    [P("iops", "每秒 I/O 次数", 1000, 100000, 1000, 50000),
     P("mode", "I/O 方式", 0, 2, 1, 0, None, ["程序轮询", "中断驱动", "DMA"]),
     P("ghz", "主频", 1, 4, 0.5, 3, "GHz")],
    [M("cycles", "每次 CPU 周期", "if(mode == 0, 20000, if(mode == 1, 2000, 100))", "周期", "int"),
     M("cpuPct", "CPU 占用", "iops * (if(mode == 0, 20000, if(mode == 1, 2000, 100))) / (ghz * 1000000000) * 100", "%", "fix2"),
     M("maxIops", "CPU 打满时上限", "ghz * 1000000000 / (if(mode == 0, 20000, if(mode == 1, 2000, 100)))", "次/秒", "int")],
    [C("cpuPct <= 1", "CPU 占用不超 1%"),
     C("iops >= 50000", "而且每秒得扛住 5 万次")],
    "每次 I/O 的 CPU 周期从 2 万降到 100，差 200 倍 —— DMA 把“搬数据”从 CPU 手里拿走，只留一次“搬完了”的中断。高吞吐的磁盘和网卡必须走 DMA，就是这个道理。",
)]

FUND["fundamentals/fund-ch18"] = [sb(
    "并查集的两个优化各管一半",
    "不优化时并查集能退化成一条链，find 是 O(n)；两个优化一起用才近似 O(1)。拖开关。",
    [P("n", "元素个数", 1000, 1000000, 1000, 100000),
     P("compress", "路径压缩", 0, 1, 1, 0, None, ["不做", "路径压缩"]),
     P("byRank", "合并策略", 0, 1, 1, 0, None, ["随便挂", "按秩合并"])],
    [M("worst", "最坏 find 步数", "if(compress == 1 && byRank == 1, 4, if(compress == 1 || byRank == 1, log2(n), n))", "步", "int"),
     M("total", "n 次 find 总步数", "if(compress == 1 && byRank == 1, 4, if(compress == 1 || byRank == 1, log2(n), n)) * n", "步", "int")],
    [C("worst <= 5", "最坏情况 5 步以内查完"),
     C("n >= 1000000", "而且规模要到百万")],
    "只用其中一个：O(log n)；两个一起用：O(α(n))，α 是反阿克曼函数，10 亿个元素也只有 4。并查集“近似 O(1)”的前提，是两个优化都在。",
)]

FUND["fundamentals/fund-ch19"] = [sb(
    "生产者消费者：缓冲区开多大",
    "每搬一个元素就唤醒一次，上下文切换会把 CPU 吃光。拖缓冲区大小与总量。",
    [P("items", "元素总数", 10000, 1000000, 10000, 100000),
     P("buf", "缓冲区大小", 1, 256, 1, 16, "个")],
    [M("switches", "上下文切换", "items / buf * 2", "次", "int"),
     M("switchMs", "切换耗时", "items / buf * 2 * 0.005", "ms", "fix2"),
     M("batch", "每次唤醒处理", "buf", "个", "int")],
    [C("switches <= 2000", "切换次数压到 2000 以内"),
     C("items >= 100000", "而且总量还是十万级")],
    "缓冲区不是越大越好：它买来“少切换”，卖掉的是内存和端到端延迟。Kafka、管道都是按“每批几百到几千条”调的 —— 让每次唤醒都摊到足够多的元素上。",
)]

FUND["fundamentals/fund-ch20"] = [sb(
    "三级间接索引是怎么逼出来的",
    "12 个直接块 + 一/二/三级间接。拖块大小和指针位数，看什么时候非上三级不可。",
    [P("blockKB", "块大小", 1, 4, 1, 2, "KB"),
     P("ptrBits", "块指针位数", 8, 10, 1, 8, "bit"),
     P("direct", "直接块个数", 10, 12, 1, 12)],
    [M("ptrs", "每块指针数", "pow(2, ptrBits)", "个", "int"),
     M("noTripleKB", "只有两级间接", "blockKB * (direct + pow(2, ptrBits) + pow(2, ptrBits) * pow(2, ptrBits))", "KB", "int"),
     M("maxKB", "三级齐全", "blockKB * (direct + pow(2, ptrBits) + pow(2, ptrBits) * pow(2, ptrBits) + pow(2, ptrBits) * pow(2, ptrBits) * pow(2, ptrBits))", "KB", "int")],
    [C("maxKB >= 102400", "最大文件能到 100MB"),
     C("noTripleKB < 102400", "但只有两级时到不了 100MB（所以非上三级不可）")],
    "1KB 块、8 位指针只能寻址 4MB，两级间接上限 64MB —— 所以 100MB 的文件必须有三级。这类题的抓手永远是“每一级能装多少个指针”，不是背公式。",
)]

FUND["fundamentals/fund-ch21"] = [sb(
    "一次磁盘访问要多久",
    "随机 I/O 的时间几乎全花在等磁头到位。拖寻道、转速与传输率，看单次访问和 IOPS。",
    [P("seek", "平均寻道", 1, 20, 1, 5, "ms"),
     P("rpm", "转速", 3600, 14400, 1800, 3600, "rpm"),
     P("mbs", "持续传输率", 50, 500, 50, 200, "MB/s")],
    [M("rotMs", "平均旋转延迟", "60000 / rpm / 2", "ms", "fix2"),
     M("xferMs", "传输 4KB", "4 / 1024 / mbs * 1000", "ms", "fix2"),
     M("total", "单次随机读", "seek + 60000 / rpm / 2 + 4 / 1024 / mbs * 1000", "ms", "fix2"),
     M("iops", "IOPS", "1000 / (seek + 60000 / rpm / 2 + 4 / 1024 / mbs * 1000)", "次/秒", "int")],
    [C("total <= 10", "单次随机读压在 10ms 内"),
     C("iops >= 100", "IOPS 至少 100")],
    "机械盘随机读那 8ms 里，7.98ms 是“等”——传输只占 0.02ms。所以数据库要 WAL 顺序化、OS 要预读、SSD 要有 FTL：全都在绕开“寻道 + 旋转”这两项。",
)]

FUND["fundamentals/fund-ch22"] = [sb(
    "30dB 的电话线能跑多快",
    "奈奎斯特给“码元数”上限，香农给“信噪比”上限，实际速率取两者的小值。",
    [P("bKHz", "带宽", 1, 20, 1, 4, "kHz"),
     P("levels", "码元种类", 2, 64, 2, 16),
     P("snrDb", "信噪比", 0, 60, 5, 30, "dB")],
    [M("nyquist", "奈奎斯特上限", "bKHz * 2 * log2(levels)", "kbps", "fix2"),
     M("shannon", "香农上限", "bKHz * log2(1 + pow(10, snrDb / 10))", "kbps", "fix2"),
     M("realKbps", "实际可达", "min(bKHz * 2 * log2(levels), bKHz * log2(1 + pow(10, snrDb / 10)))", "kbps", "fix2")],
    [C("realKbps >= 30", "实际速率至少 30kbps"),
     C("realKbps == shannon", "而且此时卡在香农上限（不是奈奎斯特）")],
    "4kHz 带宽 + 30dB 信噪比的香农极限约 40kbps —— 这就是 56k 猫要“借用”电话线没用上的高频段的原因。带宽和信噪比不够时，增加码元种类完全无效，那时候是奈奎斯特在管。",
)]

FUND["fundamentals/fund-ch23"] = [sb(
    "停等协议的利用率",
    "发一帧、等一个 RTT、再发下一帧 —— RTT 里链路完全空着。窗口是唯一的解药。",
    [P("frameBits", "帧长", 1000, 16000, 1000, 4000, "bit"),
     P("rate", "链路速率", 1, 100, 1, 100, "Mbps"),
     P("rtt", "往返时延 RTT", 1, 200, 1, 20, "ms"),
     P("win", "窗口大小", 1, 128, 1, 1, "帧")],
    [M("txMs", "发送时延", "frameBits / (rate * 1000)", "ms", "fix2"),
     M("utilPct", "链路利用率", "min(1, win * frameBits / (rate * 1000) / (frameBits / (rate * 1000) + rtt)) * 100", "%", "fix2"),
     M("realMbps", "有效吞吐", "min(1, win * frameBits / (rate * 1000) / (frameBits / (rate * 1000) + rtt)) * rate", "Mbps", "fix2")],
    [C("utilPct >= 80", "链路利用率至少 80%"),
     C("win <= 16", "窗口还不许开到 16 帧以上")],
    "停等的利用率 = T/(T+RTT)：帧越小、RTT 越大越惨。把窗口开到 RTT/T 帧就能跑满 —— 这就是 GBN / 选择重传存在的理由，也是卫星链路不能用停等的原因。",
)]


# ══════════════════════════════ 收尾补 sandbox：ml / ai / database ══════════════════════════════
# 「后处理」批次：给 122 章里可量化的章节补 sandbox。优先 ml/ai/database。
# 每条都经 scripts/audit_handmade_labs.py 守门：存在解 + 默认值不开局通关。

ML = {}

ML["ml/ml-ch01"] = [sb(
    "学习率调多大才不炸",
    "学习率太小收敛慢，太大在碗壁间震荡甚至发散。拖学习率与问题条件数，找那条既稳又快的线。",
    [P("lr", "学习率", 0.01, 2, 0.01, 1.5),
     P("cond", "条件数 κ", 1, 100, 1, 20)],
    [M("steps", "收敛步数", "ceil(cond / lr / 5)", "步", "int"),
     M("diverged", "是否发散", "if(lr > 2 / cond, 1, 0)", None, "int"),
     M("finalErr", "终误差", "if(lr > 2 / cond, 999, 1 / (1 + lr * cond))", None, "fix2")],
    [C("diverged == 0", "没有发散（学习率没越过稳定上界 2/κ）"),
     C("steps <= 2000", "收敛步数压在 2000 步内"),
     C("cond >= 5", "而且问题得是有点病态的（条件数 ≥ 5）")],
    "最速下降的稳定上界是 lr ≤ 2/κ。条件数越大（等值线越扁），能用的学习率越小——病态问题要靠特征缩放把 κ 压下来。lr 太大发散，太小只是慢。",
)]

ML["ml/ml-ch02"] = [sb(
    "正则化强度该取多大",
    "λ=0 过拟合（训练好测试差），λ 太大又欠拟合。拖 λ 与样本噪声，看测试误差的 U 形最低点。",
    [P("lam", "正则 λ", 0, 10, 0.5, 0),
     P("noise", "标签噪声", 0, 5, 0.5, 2),
     P("n", "样本量", 50, 5000, 50, 500)],
    [M("trainErr", "训练误差", "1 + lam * 0.1", None, "fix2"),
     M("testErr", "测试误差", "1 + lam * 0.1 + noise * noise * 0.3 + (lam - 2) * (lam - 2) * 0.15", None, "fix2"),
     M("gap", "泛化差距", "noise * noise * 0.3 + (lam - 2) * (lam - 2) * 0.15", None, "fix2")],
    [C("testErr <= 3", "测试误差控制住（没过拟合也没欠拟合）"),
     C("lam > 0", "λ 不能为 0（完全不正则就是过拟合）"),
     C("lam <= 5", "λ 也不能太大（否则欠拟合，测试误差又升回去）")],
    "测试误差随 λ 呈 U 形：λ=0 时把训练集噪声也背下来；λ 太大把真信号压平。甜点在中间，所以用验证集挑 λ，不是训练集。",
)]

ML["ml/ml-ch04"] = [sb(
    "模型复杂度卡在哪最稳",
    "太简单欠拟合（高偏差），太复杂过拟合（高方差）。拖复杂度与样本量，找总误差最低的那一档。",
    [P("c", "模型复杂度", 1, 10, 1, 10),
     P("n", "样本量", 100, 100000, 100, 1000)],
    [M("bias", "偏差", "20 / c", None, "fix2"),
     M("variance", "方差", "c * 5000 / n", None, "fix2"),
     M("totalErr", "总误差", "bias * bias / 10 + variance", None, "fix2")],
    [C("totalErr <= 15", "总误差压在 15 以内（偏差方差取得平衡）"),
     C("c <= 6", "复杂度不能顶满（太复杂方差爆炸）"),
     C("c >= 3", "复杂度也不能太低（否则高偏差欠拟合）")],
    "总误差 = 偏差² + 方差。复杂度低偏差主导，高方差随样本量反比暴涨。最佳在两者交叉处，且样本越多越能容忍高复杂度——更多数据 > 更花哨的模型。",
)]

ML["ml/ml-ch05"] = [sb(
    "决策树砍多深才不记答案",
    "深度越大训练集越准，但也把噪声背下来了。拖深度与样本量，看测试精度什么时候开始掉。",
    [P("d", "最大深度", 1, 15, 1, 15),
     P("n", "样本量", 200, 20000, 200, 2000)],
    [M("trainAcc", "训练精度", "clamp(50 + d * 5, 0, 100)", "%", "int"),
     M("overfit", "过拟合惩罚", "max(0, d - 6) * (2000 / n) * 6", "%", "fix2"),
     M("testAcc", "测试精度", "clamp(trainAcc - overfit, 0, 100)", "%", "int")],
    [C("testAcc >= 80", "测试精度保住 80% 以上"),
     C("d <= 8", "深度不能无脑拉满（超过 8 就开始背噪声）")],
    "训练精度随深度单调涨，测试精度在 6~8 之后掉头——多出来的层只是把训练集噪声背下来。max_depth 截断本质是卡在偏差方差交叉点之前。",
)]

ML["ml/ml-ch06"] = [sb(
    "k 选多少簇才不欠不溢",
    "k 太小合并了本不同的簇，太大又把一团拆碎。拖 k 与真实簇数，看簇内平方和什么时候稳下来。",
    [P("k", "设定簇数", 1, 10, 1, 10),
     P("g", "真实簇数", 2, 8, 1, 4),
     P("n", "样本量", 500, 20000, 500, 5000)],
    [M("inertia", "簇内平方和", "5000 * g / k + if(k > g, (k - g) * 200, 0)", None, "int"),
     M("perCluster", "平均簇样本", "n / k", "个", "int")],
    [C("k <= g", "不过度拆（k 不超过真实簇数）"),
     C("k >= g - 1", "也不少并（k 不低于真实簇数 − 1）"),
     C("inertia <= 6000", "簇内平方和在合理范围")],
    "肘部法则看 inertia 随 k 的下降拐点：k 小于真实簇数时每合并一个簇 inertia 暴涨，等于之后下降变缓。k 比真实簇数多只会徒增碎片。",
)]

AI = {}

AI["ai/ai-ch03"] = [sb(
    "注意力为什么吃显存",
    "自注意力的显存与序列长度平方成正比。拖序列长度、头数与隐藏维度，看 KV 占用什么时候爆。",
    [P("seq", "序列长度", 128, 8192, 128, 8192),
     P("heads", "注意力头数", 1, 32, 1, 8),
     P("dim", "隐藏维度", 64, 1024, 64, 512)],
    [M("attnMem", "注意力矩阵", "seq * seq * heads * 2 / 1048576", "MB", "int"),
     M("kvMem", "KV Cache", "2 * seq * dim * 2 / 1048576", "MB", "int"),
     M("totalMB", "合计显存", "seq * seq * heads * 2 / 1048576 + 2 * seq * dim * 2 / 1048576", "MB", "int")],
    [C("attnMem <= 2048", "单卡 4GB 显存里注意力矩阵别超过 2GB"),
     C("seq <= 4096", "序列长度别硬顶到 8192（长序列要用稀疏/分块注意力）")],
    "自注意力是 O(n²) 显存：序列翻倍，注意力矩阵变四倍。所以长文本要分段/稀疏注意力，推理侧要 KV Cache 分页（PagedAttention）——都在绕开这个平方项。",
)]

AI["ai/ai-ch04"] = [sb(
    "LoRA 秩 r 取多大才够",
    "秩 r 太小学不动，太大又失去低秩假设、参数量回弹。拖 r 看可训练参数占比。",
    [P("r", "秩 r", 1, 64, 1, 1),
     P("d", "隐藏维度", 256, 4096, 256, 2048),
     P("layers", "LoRA 层数", 1, 32, 1, 16)],
    [M("loraParams", "LoRA 参数", "2 * r * d * layers", "个", "int"),
     M("fullParams", "全量参数", "d * d * layers", "个", "int"),
     M("trainablePct", "可训练占比", "loraParams / (fullParams + loraParams) * 100", "%", "fix2")],
    [C("trainablePct <= 5", "可训练参数压在 5% 以内（低秩假设成立）"),
     C("loraParams >= 1000000", "但也不能太小（r=1 基本学不动）")],
    "LoRA 把权重更新约束成低秩矩阵 BA，可训练参数只有 2·r·d·L，是全量的百分之一。r 太小欠拟合，r 太大既失去低秩意义又把参数量拖回全量级——典型 r 取 8/16/32。",
)]

AI["ai/ai-ch13"] = [sb(
    "量化到几位才划算",
    "FP16/INT8/INT4 每降一档显存减半、速度变快，但精度会掉。拖位宽与校准开关看显存与精度损失。",
    [P("bits", "权重位宽", 4, 16, 4, 4),
     P("paramsB", "参数量", 1, 70, 1, 7, "B"),
     P("calib", "是否校准", 0, 1, 1, 0, None, ["不校准", "校准后"])],
    [M("memGB", "显存占用", "paramsB * bits / 8", "GB", "fix2"),
     M("speedup", "相对 FP16", "16 / bits", "倍", "fix2"),
     M("accDrop", "精度损失", "if(calib, 1, 3) * (16 - bits) * 0.25", "pt", "fix2")],
    [C("memGB <= 8", "单张消费级显卡（8GB）能装下"),
     C("accDrop <= 3", "精度损失不超过 3 个百分点（可用范围）")],
    "每降一档位宽，显存与带宽需求减半、吞吐近似翻倍；代价是量化误差。INT8 配校准通常只掉 1~2 个点，INT4 不校准能掉近 10 个点。先校准再量化、敏感层保留高精度是部署标配。",
)]

DATABASE = {}

DATABASE["database/db-ch02"] = [sb(
    "两表 JOIN 该用哪种算法",
    "小表驱动大表，嵌套循环是 R×S；哈希连接只扫一遍两表。拖行数与内表索引开关，看哪种更划算。",
    [P("R", "外表行数", 1000, 1000000, 1000, 100000, "行"),
     P("S", "内表行数", 1000, 1000000, 1000, 100000, "行"),
     P("idx", "内表索引", 0, 1, 1, 0, None, ["无索引", "有索引"])],
    [M("nlCost", "嵌套循环代价", "R * if(idx, log2(S), S)", "次", "int"),
     M("hashCost", "哈希连接代价", "R + S", "次", "int"),
     M("speedup", "哈希/嵌套", "R * if(idx, log2(S), S) / (R + S)", "倍", "fix2")],
    [C("nlCost <= 100000000", "嵌套循环代价压在 1 亿次比较以内（大表不能裸跑）"),
     C("hashCost <= 2000000", "哈希连接代价压在 200 万以内")],
    "嵌套循环是 R×S，大表一上来就是十亿级比较；内表建索引降到 R·logS，哈希连接更是只扫一遍两表（R+S）。「小表驱动大表 + 建索引」不是玄学，是代价公式里那两个因子。",
)]

DATABASE["database/db-ch03"] = [sb(
    "B+ 树要几层才够",
    "一亿条记录，每页能放几百个指针。拖记录数与扇出，看树高会不会撑爆层数。",
    [P("N", "记录数", 100000, 100000000, 100000, 1000000, "条"),
     P("fan", "节点扇出", 10, 1000, 10, 200)],
    [M("height", "树高", "ceil(log(N) / log(fan))", "层", "int"),
     M("leaves", "叶子节点", "ceil(N / fan)", "个", "int"),
     M("io", "每次查询随机 IO", "ceil(log(N) / log(fan))", "次", "int")],
    [C("height <= 4", "树高不超过 4 层（3 次磁盘 IO 内拿到数据）"),
     C("N >= 10000000", "而且得是千万级以上的大表")],
    "B+ 树把「记录数 N」换成「以扇出为底的对数」，千万级数据也只要 3~4 层。扇出每翻一倍，树高就降一层——所以页要塞满指针，别让它稀疏。",
)]

DATABASE["database/db-ch04"] = [sb(
    "全表扫描还是走索引",
    "EXPLAIN 里一张大表，过滤条件命中多少行决定走不走索引。拖行数与选择率。",
    [P("R", "表行数", 100000, 10000000, 100000, 1000000, "行"),
     P("sel", "选择率", 0.1, 50, 0.1, 20, "%"),
     P("clustered", "聚簇索引", 0, 1, 1, 0, None, ["堆表", "聚簇"])],
    [M("scanCost", "全表扫描代价", "R", "次", "int"),
     M("idxCost", "索引扫描代价", "R * sel / 100 * if(clustered, 1, 2)", "次", "int"),
     M("savedPct", "省下比例", "(R - R * sel / 100 * if(clustered, 1, 2)) / R * 100", "%", "int")],
    [C("idxCost < scanCost", "索引扫描比全表扫描便宜"),
     C("sel <= 5", "选择率不超过 5%（高选择性才值得建索引）")],
    "索引的代价是「选出的行 × 回表次数」，所以只有高选择性（小结果集）才划算。选择率超 10% 时优化器往往回头走全表——这就是「建了索引却不走」最常见的原因。",
)]

DATABASE["database/db-ch08"] = [sb(
    "分几片才不撑爆单库",
    "单库建议不超过 500GB。拖总数据量与分片数，看单片是不是落进安全区。",
    [P("totalGB", "总数据量", 100, 5000, 100, 3000, "GB"),
     P("shards", "分片数", 2, 64, 2, 2)],
    [M("perShard", "单片大小", "totalGB / shards", "GB", "int"),
     M("ratio", "占安全线比", "totalGB / shards / 500", None, "fix2")],
    [C("perShard <= 500", "单片不超过 500GB 安全线"),
     C("shards >= 4", "至少分 4 片（单分片既是容量瓶颈也是热点）")],
    "分片数 = 总数据量 / 单分片安全容量。单分片既是容量天花板也是写入热点，通常按「2 的整数幂、每节点 1~2 片」来定。分太少撑不住，分太多元数据与跨片事务反而拖垮。",
)]


# ══════════════════════════════ 收尾补 sandbox · 批次二 ══════════════════════════════
# db / ml / ai 剩余可量化章节。每条经 scripts/audit_handmade_labs.py 守门：
# 默认值不开局通关 + 参数空间存在通关解 + 单参数档位 ≤5000。

DATABASE["database/db-ch01"] = [sb(
    "定长 CHAR 还是变长 VARCHAR",
    "用户名、邮箱这种长短不一的字段，用 CHAR 会按声明宽度全补齐，白白浪费空间。拖三个旋钮看存储差异。",
    [P("nRows", "表行数", 1000, 100000, 1000, 100000, "行"),
     P("avgLen", "平均长度", 10, 100, 10, 10, "字符"),
     P("declLen", "声明宽度", 20, 100, 10, 100, "字符"),
     P("useVarchar", "类型", 0, 1, 1, 0, None, ["CHAR 定长", "VARCHAR 变长"])],
    [M("wastePct", "空间浪费", "if(useVarchar == 1, 0, (declLen - avgLen) / declLen * 100)", "%", "fix2"),
     M("bytes", "占用", "if(useVarchar == 1, nRows * avgLen, nRows * declLen)", "B", "int")],
    [C("wastePct <= 20", "空间浪费不超过 20%（别用定长 CHAR 装长短不一的字段）"),
     C("nRows >= 50000", "而且得是万行级以上的真实表")],
    "CHAR 按声明宽度补齐，邮箱声明 100 字符、实际 20，剩下 80 都是空格；VARCHAR 按实际长度存。短字段 + 大宽度时，CHAR 浪费能到 80%。DDL 选型看着小，亿级行上一存就是几十 GB。",
)]

DATABASE["database/db-ch05"] = [sb(
    "游标逐行还是集合操作",
    "存储过程里用游标一行一行处理，和写一句集合操作 SQL，差距不在写法而在它扫了多少遍。拖批量和写法看总成本。",
    [P("n", "批量行数", 1000, 100000, 1000, 100000, "行"),
     P("useCursor", "写法", 0, 1, 1, 1, None, ["集合操作", "游标逐行"])],
    [M("cursorCost", "游标总成本", "n * 50", "单位", "int"),
     M("setCost", "集合操作成本", "n", "单位", "int"),
     M("totalCost", "实际成本", "if(useCursor == 1, n * 50, n)", "单位", "int")],
    [C("totalCost <= 200000", "总处理成本压在 20 万以内（别用游标逐行）"),
     C("n >= 50000", "而且得是五万行以上的批量操作")],
    "游标对每一行都走一遍完整处理（n×50），集合操作让引擎一次扫完（n）。几万行时游标就是几百倍的差距，而且还会长时间占锁。存储过程里能写集合 SQL 就别用游标。",
)]

DATABASE["database/db-ch06"] = [sb(
    "这张表到底到第几范式",
    "部分函数依赖、传递函数依赖、非原子属性——每多一种异常，就掉一档范式。逐个关掉，看能爬到 BCNF 吗。",
    [P("nonAtomic", "非原子属性", 0, 1, 1, 1, None, ["无", "有（字段里塞列表）"]),
     P("partialDep", "部分函数依赖", 0, 1, 1, 0, None, ["无", "有"]),
     P("transitDep", "传递函数依赖", 0, 1, 1, 0, None, ["无", "有"])],
    [M("nf", "达到范式", "if(nonAtomic == 1, 1, if(partialDep == 1, 2, if(transitDep == 1, 3, 4)))", "级", "int"),
     M("anomaly", "剩余异常数", "nonAtomic + partialDep + transitDep", "类", "int")],
    [C("nf == 4", "达到 BCNF（消除全部三类异常）")],
    "非原子属性卡在 1NF，部分依赖卡在 2NF，传递依赖卡在 3NF；三类都消掉才是 BCNF。范式的每一级都在消灭一类更新异常——不是为了考试，是怕同一份数据在表里存了 n 份、改一处漏九处。",
)]

DATABASE["database/db-ch07"] = [sb(
    "备份策略决定能丢多少",
    "只做每周全量，最坏要丢一整周数据（RPO=7天）；加增量把 RPO 压到小时级，但存储会涨。拖两个旋钮平衡。",
    [P("totalGB", "数据总量", 100, 5000, 100, 1000, "GB"),
     P("hasIncr", "备份方式", 0, 1, 1, 0, None, ["仅全量", "全量 + 增量"]),
     P("incrHours", "增量间隔", 1, 24, 1, 1, "小时")],
    [M("fullGB", "全量备份", "totalGB * 0.3", "GB", "int"),
     M("incrGB", "每日增量", "totalGB * 0.01 * if(hasIncr == 1, 24 / incrHours, 0)", "GB", "int"),
     M("storGB", "备份总存储", "totalGB * 0.3 + totalGB * 0.01 * if(hasIncr == 1, 24 / incrHours, 0)", "GB", "int"),
     M("rpoHours", "恢复点目标", "if(hasIncr == 1, incrHours, 168)", "小时", "int")],
    [C("rpoHours <= 24", "RPO ≤ 1 天（不能靠每周全量，真出事丢一周）"),
     C("storGB <= 2000", "备份存储不超过 2TB")],
    "RPO 是“最多能丢多久的数据”。只做全量且一周一次，最坏丢 7 天；把增量频率提到每小时，RPO 就压到 1 小时，代价只是多存一份当天增量。容灾第一课是先定 RPO/RTO，再反推备份频率。",
)]

ML["ml/ml-ch03"] = [sb(
    "批大小卡在哪最稳",
    "批太小梯度噪声大、训练抖；批太大每轮更新步数太少、收敛慢。拖批大小和数据量找甜点。",
    [P("B", "批大小", 16, 512, 16, 16, "样本"),
     P("N", "样本总量", 1000, 100000, 1000, 100000, "样本")],
    [M("stepsPerEpoch", "每轮更新步数", "N / B", "步", "int"),
     M("gradNoise", "梯度噪声指数", "100 / sqrt(B)", "%", "fix2"),
     M("totalUpdates", "总更新步数", "30 * N / B", "步", "int")],
    [C("gradNoise <= 20", "梯度噪声指数 ≤ 20（批太小噪声大、训练抖）"),
     C("stepsPerEpoch >= 50", "每轮至少 50 步更新（批太大步数太少、收敛慢）")],
    "批大小 B 决定两件事：梯度估计的方差 ∝ 1/√B，每轮更新步数 = N/B。B 太小方差爆炸、loss 上下乱跳；B 太大每轮只走几步、要更多轮才收敛。甜点通常是“方差可接受 + 每轮几十到几百步”。",
)]

ML["ml/ml-ch08"] = [sb(
    "折扣因子 γ 取多大才看得远",
    "γ 太小只看眼前一步，γ 太大几乎不折扣、价值估计方差爆炸。拖 γ 和视野长度看有效规划步数。",
    [P("gamma", "折扣因子 γ", 0.5, 0.95, 0.01, 0.5, None),
     P("H", "回合长度", 10, 50, 5, 30, "步")],
    [M("totalReturn", "累计折扣回报", "(1 - pow(gamma, H)) / (1 - gamma)", "单位", "fix2"),
     M("effHorizon", "有效视野", "floor(log(0.05) / log(gamma))", "步", "int")],
    [C("gamma >= 0.8", "折扣因子足够大（有效视野不短于几十步）"),
     C("gamma <= 0.95", "但不接近 1（否则训练不稳、信用分配难）"),
     C("effHorizon >= 20", "有效视野 ≥ 20 步（能规划较远的未来）")],
    "折扣回报 G=Σγᵗr。γ=0.9 时单步权重每步打九折，约 22 步后衰减到 5% 以下——这就是“有效视野”。γ 太小鼠目寸光，γ 太大长期信用分配困难。ε-贪心之外，γ 是 RL 里最容易被调崩的旋钮。",
)]

ML["ml/ml-ch09"] = [sb(
    "SVM 的 C 越大间隔越小",
    "软间隔 SVM 里 C 控制“容忍误分类”的代价：C 太大硬要把样本全分开，间隔被压到极小（过拟合）；C 太小又留误分类。拖 C 和线性可分性找平衡。",
    [P("C", "正则化 C", 0.1, 100, 0.1, 100, None),
     P("separable", "数据可分性", 0, 1, 1, 1, None, ["近似可分", "严格线性可分"])],
    [M("wNorm", "||w||", "log10(C) + 2", "单位", "fix2"),
     M("margin", "分类间隔", "2 / (log10(C) + 2)", "单位", "fix2"),
     M("misclassified", "误分类数", "if(C < 1 && separable == 0, 3, 0)", "个", "int")],
    [C("margin >= 1.0", "间隔够大（至少 1.0，泛化好）"),
     C("misclassified == 0", "没有误分类样本"),
     C("C <= 50", "C 不过大（否则间隔被压到极小，过拟合）")],
    "间隔 = 2/‖w‖，而 ‖w‖ 随 C 增大而增大（对误分类的惩罚更重）。C→∞ 逼出硬间隔，但间隔塌缩、对噪声极敏感；C 太小又容忍太多误分类。实践中用验证集挑 C，而不是训练集。",
)]

AI["ai/ai-ch01"] = [sb(
    "一次矩阵乘要多少 FLOPs",
    "全连接层就是一次大矩阵乘。维度每翻一倍，计算量涨八倍。拖三个维度看单层前向耗时。",
    [P("M", "输出维度", 64, 1856, 256, 64, None),
     P("N", "输入维度", 64, 1856, 256, 64, None),
     P("K", "隐维度", 64, 1856, 256, 64, None),
     P("tflops", "算力", 10, 100, 10, 10, "TFLOPS")],
    [M("flops", "浮点运算量", "2 * M * N * K", "FLOPs", "int"),
     M("ms", "前向耗时", "2 * M * N * K / (tflops * 10000000000000) * 1000", "ms", "fix2")],
    [C("ms <= 50", "单层前向不超 50ms（实时推理预算内）"),
     C("M >= 512 && N >= 512 && K >= 512", "三个维度都得上规模（小矩阵体现不出计算量）")],
    "矩阵乘 FLOPs = 2·M·N·K（乘加各算一次）。维度翻倍 = 每个维度 ×2，总量 ×8。所以大模型里“宽一点”比“深一点”贵得多——也是 MoE 把“宽”稀疏化的动机。",
)]

AI["ai/ai-ch02"] = [sb(
    "卷积为什么比全连接省参数",
    "同样把一张图映射到特征，全连接会给每个像素对都配一套权重；卷积靠“权重共享”只学一组小核。拖架构和维度看差距。",
    [P("arch", "层类型", 0, 1, 1, 0, None, ["全连接", "卷积"]),
     P("H", "图高", 32, 128, 32, 64, "像素"),
     P("W", "图宽", 32, 128, 32, 64, "像素"),
     P("Cin", "输入通道", 3, 32, 1, 3, None),
     P("Cout", "输出通道", 8, 64, 8, 8, None)],
    [M("convParams", "卷积参数量", "3 * 3 * Cin * Cout + Cout", "个", "int"),
     M("fcParams", "全连接参数量", "(H * W * Cin) * (H * W * Cout)", "个", "int"),
     M("params", "实际参数量", "if(arch == 1, 3 * 3 * Cin * Cout + Cout, (H * W * Cin) * (H * W * Cout))", "个", "int"),
     M("ratio", "全连接/卷积", "(H * W * Cin) * (H * W * Cout) / (3 * 3 * Cin * Cout + Cout)", "倍", "int")],
    [C("params <= 500000", "参数量压在 50 万以内（大模型也扛得住）"),
     C("arch == 1", "用卷积层（权重共享）而不是全连接")],
    "卷积核只有 k×k×Cin×Cout 个参数，却作用在 H×W 个位置上——权重共享让它不随图像尺寸爆炸。同样一张 64×64 图，全连接要给每个像素对配权重，参数量是卷积的几万倍。CNN 之所以能吃图像，靠的就是这招。",
)]

AI["ai/ai-ch08"] = [sb(
    "提示缓存命中率决定成本",
    "系统提示每次都前置、几乎不变，命中缓存后这部分不再计费。命中率越低，越是把同样的 token 反复付钱。拖三个旋钮看单价。",
    [P("shared", "共享前缀 token", 100, 2000, 100, 1000, "token"),
     P("unique", "每请求独有", 200, 2000, 100, 2000, "token"),
     P("hitRate", "缓存命中率", 0, 100, 5, 0, "%")],
    [M("costPerReq", "单请求成本", "unique + shared * (1 - hitRate / 100)", "token", "int"),
     M("savingPct", "省下比例", "shared * hitRate / 100 / (unique + shared) * 100", "%", "int")],
    [C("costPerReq <= 800", "单请求成本压在 800 token 以内（共享前缀要真正被复用）"),
     C("hitRate >= 80", "缓存命中率 ≥ 80%（系统提示要稳定前置）"),
     C("unique <= 1500", "独有内容别太长（缓存只省共享部分）")],
    "prompt caching 把“稳定前置的 token”缓存下来，命中后这部分计费打一折甚至免费。命中率从 0 提到 90%，成本能砍掉一大截——前提是系统提示真的稳定不变、且放在最前面。多轮对话、固定 few-shot 都是它的主场。",
)]

AI["ai/ai-ch10"] = [sb(
    "单卡放不下就切分",
    "一个 7B 模型训练态要吃掉上百 GB 显存（参数+梯度+优化器状态）。单卡装不下时，数据并行是复制、模型并行是切分。拖参数量和卡数看单卡压力。",
    [P("P", "参数量", 1, 70, 1, 7, "B"),
     P("G", "GPU 数", 1, 8, 1, 8, "张"),
     P("mode", "并行方式", 0, 1, 1, 0, None, ["数据并行(全复制)", "模型并行(切分)"])],
    [M("modelMemGB", "模型总显存", "P * 16", "GB", "int"),
     M("perGPU_GB", "单卡显存", "P * 16 / if(mode == 1, G, 1)", "GB", "int")],
    [C("perGPU_GB <= 24", "单卡显存 ≤ 24GB（消费级/主流训练卡放得下）"),
     C("mode == 1", "用模型并行切分（大模型的唯一出路）"),
     C("G >= 4", "至少用 4 张卡分摊")],
    "训练态显存 ≈ 16 字节/参数（FP16 参数+梯度 8B，加上 FP32 主副本与 Adam 动量/方差 12B）。7B 模型就是 ~112GB，单卡放不下；模型并行把权重切片分到多卡，每卡只扛 1/G。数据并行只是复制，解决不了单模型太大。",
)]

AI["ai/ai-ch12"] = [sb(
    "标注一致性够不够用",
    "两个标注员，光看“都标对了”还不够——随机也能蒙对一部分。Cohen's κ 扣掉随机一致率后，才算真一致。拖两个一致率看 κ。",
    [P("po", "观察一致率", 0.5, 1.0, 0.01, 0.85, None),
     P("pe", "随机期望一致率", 0.1, 0.9, 0.01, 0.6, None)],
    [M("kappa", "Cohen κ", "(po - pe) / (1 - pe)", "系数", "fix2"),
     M("agree", "原始一致", "po * 100", "%", "int")],
    [C("kappa >= 0.8", "κ ≥ 0.8（几乎完全一致，标注可用）"),
     C("po >= 0.9", "观察一致率 ≥ 90%（标注本身得靠谱）")],
    "κ=(Po−Pe)/(1−Pe)：Po 是实际一致率，Pe 是两个标注员“随便标也能撞上”的概率。Po 高但 Pe 也高（比如类别极不平衡），κ 照样低。SFT 数据质量的第一道关就是标注重复率，κ<0.6 的数据直接重标。",
)]

AI["ai/ai-ch14"] = [sb(
    "图像分辨率拉多高清才值",
    "VLM 把图像切成 14×14 的小块，每块一个视觉 token——分辨率每翻一倍，token 数翻四倍、成本和延迟都涨。拖分辨率和单价看单图账单。",
    [P("res", "分辨率", 224, 700, 28, 224, "像素"),
     P("textTokens", "文本 token", 50, 500, 50, 50, "token"),
     P("price", "单价", 0.001, 0.01, 0.001, 0.001, "$/token")],
    [M("visTokens", "视觉 token", "(res / 14) * (res / 14)", "个", "int"),
     M("totalTokens", "总 token", "(res / 14) * (res / 14) + textTokens", "个", "int"),
     M("cost", "单图成本", "((res / 14) * (res / 14) + textTokens) * price", "$", "fix2")],
    [C("cost <= 5", "单张图成本压在 5 单位内（分辨率别无脑拉满）"),
     C("res >= 336", "分辨率至少 336（太低 VLM 看不清细节）"),
     C("visTokens >= 576", "视觉 token 够多（res≥336 → 24×24=576）")],
    "视觉 token 数 = (分辨率/14)²，所以分辨率翻倍、token 翻四倍。224→448 看着只是“清晰点”，成本已经是 4 倍。多模态落地的成本优化第一招就是“按任务动态降分辨率”：OCR 要高清，分类 336 足够。",
)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    chapters = {}
    for d in (CPP, FUND, ML, AI, DATABASE):
        for k, v in d.items():
            chapters[k] = v
    doc = {
        "_comment": "sandbox / debug 手工精修模块。由 scripts/_author_labs.py 生成，gen_interactive.py 并入各章 interactive.json。改内容请改作者源。",
        "version": 1,
        "chapters": dict(sorted(chapters.items())),
    }
    text = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"

    if args.check:
        old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if old != text:
            print("!! labs.json 与作者源不一致，跑一次 python scripts/_author_labs.py")
            return 1
        print("· labs.json 与作者源一致")
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    n = sum(len(v) for v in chapters.values())
    kinds = {}
    for v in chapters.values():
        for m in v:
            kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
    print(f"· 已写 {OUT} · {n} 个模块 / {len(chapters)} 章 · {kinds}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
