import "package:flutter/material.dart";

/// 阶段 7 课程内容清单模型。
/// 数据镜像 content/cpp/_manifest.json（20 章 + C 语言独立模块 7 单元）。
/// 注意：done 为静态镜像，须随 content/_coverage.json 手动同步（无自动生成环节）。
/// 移动端用它渲染「课程大纲」，并显示完成度与真题/资源映射（仅元数据，不存题面正文）。

class ChapterSummary {
  final int order;
  final String id;
  final String title;
  final String group;
  final bool done;
  final List<String> leetcode;
  final List<String> nowcoder;
  final List<String> books;

  const ChapterSummary({
    required this.order,
    required this.id,
    required this.title,
    required this.group,
    required this.done,
    this.leetcode = const [],
    this.nowcoder = const [],
    this.books = const [],
  });
}

class ContentManifest {
  const ContentManifest._();

  static const Map<String, String> groupLabels = {
    "L1": "基础语法",
    "L2": "面向对象",
    "L3": "泛型与STL",
    "L4": "现代C++",
    "L5": "工程与系统",
    "L6": "进阶底层",
    "L7": "综合面试",
  };

  /// 20 章 C/C++ 课程体系。done 标志与 content/_coverage.json 保持同步
/// （由 server/scripts/validate_content.py 产出；修改内容后需重新同步）。
  static const List<ChapterSummary> chapters = [
    ChapterSummary(order: 1, id: "cpp-ch01", title: "C++ 基础语法：类型、变量与引用", group: "L1", done: true),
    ChapterSummary(order: 2, id: "cpp-ch02", title: "函数：声明/定义、重载、默认参数与 lambda", group: "L1", done: true, leetcode: ["1", "20"], nowcoder: ["BM89 合并区间"], books: ["《C++ Primer》第6章"]),
    ChapterSummary(order: 3, id: "cpp-ch03", title: "数组与字符串：C 数组、std::string 与字符串视图", group: "L1", done: true, leetcode: ["344", "415", "242"], nowcoder: ["BM83", "BM84"], books: ["《C++ Primer》第3/9章"]),
    ChapterSummary(order: 4, id: "cpp-ch04", title: "指针与内存管理：指针运算、new/delete 与悬垂", group: "L1", done: true, leetcode: ["206", "141"], nowcoder: ["BM1", "BM6"], books: ["《C++ Primer》第4/12章"]),
    ChapterSummary(order: 5, id: "cpp-ch05", title: "类与对象：封装、构造/析构、拷贝与运算符重载", group: "L2", done: true, leetcode: ["707"], nowcoder: ["BM101"], books: ["《C++ Primer》第7章"]),
    ChapterSummary(order: 6, id: "cpp-ch06", title: "继承与多态：虚函数、抽象类与 RTTI", group: "L2", done: true, leetcode: ["208"], nowcoder: ["BM65"], books: ["《C++ Primer》第15章"]),
    ChapterSummary(order: 7, id: "cpp-ch07", title: "模板与泛型：函数模板、类模板与特化", group: "L3", done: true, nowcoder: ["BM90"], books: ["《C++ Primer》第16章"]),
    ChapterSummary(order: 8, id: "cpp-ch08", title: "STL 容器：vector/list/map/set/unordered", group: "L3", done: true, leetcode: ["1", "49", "347"], nowcoder: ["BM50"], books: ["《C++ Primer》第9-11章"]),
    ChapterSummary(order: 9, id: "cpp-ch09", title: "STL 算法与迭代器：sort/find/lambda/范围", group: "L3", done: true, leetcode: ["75", "56"], nowcoder: ["BM89"], books: ["《C++ Primer》第10章"]),
    ChapterSummary(order: 10, id: "cpp-ch10", title: "智能指针与 RAII：unique_ptr/shared_ptr/weak_ptr", group: "L4", done: true, nowcoder: ["BM101"], books: ["《C++ Primer》第12/13章"]),
    ChapterSummary(order: 11, id: "cpp-ch11", title: "异常处理与断言：try/catch、noexcept 与契约", group: "L4", done: true, books: ["《C++ Primer》第18章"]),
    ChapterSummary(order: 12, id: "cpp-ch12", title: "现代 C++ 特性：auto/移动语义/范围 for/emplace", group: "L4", done: false, books: ["《Effective Modern C++》"]),
    ChapterSummary(order: 13, id: "cpp-ch13", title: "输入/输出与文件：iostream、fstream 与格式化", group: "L5", done: false, books: ["《C++ Primer》第8章"]),
    ChapterSummary(order: 14, id: "cpp-ch14", title: "预处理与宏：include/define/条件编译/头文件守卫", group: "L5", done: false, books: ["《C++ Primer》第2章"]),
    ChapterSummary(order: 15, id: "cpp-ch15", title: "命名空间与模块化：namespace/inline namespace/C++20 模块", group: "L5", done: false, books: ["《C++ Primer》第18章"]),
    ChapterSummary(order: 16, id: "cpp-ch16", title: "并发与多线程：thread/mutex/atomic/async", group: "L5", done: false, leetcode: ["1114", "1226"], books: ["《C++ Concurrency in Action》"]),
    ChapterSummary(order: 17, id: "cpp-ch17", title: "元编程与类型萃取：type_traits/constexpr/SFINAE/concept", group: "L6", done: false, books: ["《C++ Templates》第2版"]),
    ChapterSummary(order: 18, id: "cpp-ch18", title: "性能与底层：内存对齐、缓存友好与内联", group: "L6", done: false, books: ["《Effective C++》第16-25条"]),
    ChapterSummary(order: 19, id: "cpp-ch19", title: "工程化与测试：CMake、单元测试与 CI", group: "L6", done: false, books: ["《CMake 实践》"]),
    ChapterSummary(order: 20, id: "cpp-ch20", title: "综合项目与面试冲刺：系统设计、代码规范与复盘", group: "L7", done: false, leetcode: ["146", "348"], nowcoder: ["TOP101"], books: ["《剑指 Offer》"]),
  ];

  /// C 语言独立模块（7 单元）。
  static const List<ChapterSummary> clangUnits = [
    ChapterSummary(order: 1, id: "clang-u01", title: "指针与地址运算", group: "clang", done: false, nowcoder: ["BM1"]),
    ChapterSummary(order: 2, id: "clang-u02", title: "内存与动态分配（malloc/free）", group: "clang", done: false, books: ["《C 程序设计语言》第7章"]),
    ChapterSummary(order: 3, id: "clang-u03", title: "结构体与联合体", group: "clang", done: false, books: ["《C 程序设计语言》第6章"]),
    ChapterSummary(order: 4, id: "clang-u04", title: "文件 IO 与二进制", group: "clang", done: false, books: ["《C 程序设计语言》第7章"]),
    ChapterSummary(order: 5, id: "clang-u05", title: "预处理与宏", group: "clang", done: false, books: ["《C 程序设计语言》第4章"]),
    ChapterSummary(order: 6, id: "clang-u06", title: "Makefile 与构建", group: "clang", done: false, books: ["《GNU Make 手册》"]),
    ChapterSummary(order: 7, id: "clang-u07", title: "多文件编译与链接", group: "clang", done: false, books: ["《程序员的自我修养》"]),
  ];
}
