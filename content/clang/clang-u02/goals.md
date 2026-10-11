# clang-u02 · 内存与动态分配（malloc/free）· 学习目标

> **先修**：clang-u01 指针与地址运算。
> **衔接**：clang-u03 结构体（动态结构体数组）、clang-u07 多文件与链接。
> **面试权重**：★★★★★ —— 「malloc 和 new 的区别」「内存泄漏怎么查」几乎是必问题。

## 学完你能做到

1. **说清栈与堆的分工**：生命周期、增长速度、容量上限、分配速度、碎片代价，能画进程内存分区图。
2. **准确区分 `malloc` / `calloc` / `realloc`**：各自是否清零、返回值语义、失败行为。
3. **正确使用 `realloc`**：理解它可能就地扩展也可能搬迁，写出不丢指针、不泄漏的标准写法。
4. **理解 `free` 的契约**：为什么必须传 `malloc` 返回的**原地址**，为什么释放后指针值不变（悬垂），为什么 `free(NULL)` 是安全的。
5. **识别并定位内存问题**：泄漏、use-after-free、double free、越界写、碎片；能用 ASan 在 CI 中兜住。
6. **手写常见动态结构**：动态一维数组、动态二维数组、动态字符串、简易内存池。

## 博士视角（要理解到什么程度）

- **分配器是「内存的二级市场」**：`malloc` 并不直接向内核要内存，而是从 `brk`/`mmap` 申请的大块中切分；小对象走**空闲链表/分离存储**（size class），大对象直接 `mmap`。这解释了为什么 malloc 有「空间开销」（每块都有头部元数据）与「碎片」。
- **元数据与对齐**：分配器在返回指针**之前**存放块大小等信息，且返回地址必须满足最大对齐（通常 16 字节）。所以 `malloc(1)` 实际占用远大于 1 字节。
- **虚拟内存视角**：`free` 通常**不归还物理页**给内核，只是把块放回空闲链表——因此「释放后 RSS 不降」是正常现象，不是泄漏。
- **UB 的边界**：use-after-free 与越界写之所以危险，是因为它们属于 UB，编译器可基于「不越界」的假设做激进优化，导致行为不可预测。

## 程序员视角（要能用出来）

- **所有权约定大于技巧**：明确「谁分配、谁释放、释放后谁置 NULL」；错误分支用单一出口（`goto cleanup`）保证释放配对。
- **接口成对设计**：`create`/`destroy` 成对；缓冲区一律「指针 + 长度」；只读参数加 `const`。
- **测量而非猜测**：用 ASan/valgrind 定位，不要靠肉眼读代码。
- **能不用动态分配就不用**：栈上定长数组、`static` 缓冲（注明不可重入）在很多嵌入式/系统场景更可靠。


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | 286133 | 项目驱动的实战教程合集（含 C 专题） |
| [TheAlgorithms/C](https://github.com/TheAlgorithms/C) | 22507 | C 语言实现的算法与数据结构合集 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 小甲鱼 · 带你学透 C 语言 | [视频](https://www.bilibili.com/video/BV1ti4y1K7rA/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 郝斌 · C 语言自学完整版 | [视频](https://www.bilibili.com/video/BV1vh411S7LV/) | 本学科配套视频，建议结合本章示例与习题观看 |
