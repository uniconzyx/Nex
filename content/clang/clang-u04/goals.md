# clang-u04 · 文件 IO 与二进制 · 学习目标

> **先修**：clang-u01 指针（缓冲区即内存块）、clang-u02 动态分配、clang-u03 结构体（二进制落盘的对象）。
> **衔接**：clang-u07 多文件与链接（stdio 的实现横跨多个翻译单元）、与系统编程（文件描述符/内核缓冲）衔接。
> **面试权重**：★★★★☆ —— 文本/二进制模式、缓冲、feof、部分读写是高频实务考点，也是「写得出来但写得对」的分水岭。

## 学完你能做到

1. **说清 FILE 与文件描述符的关系**：`FILE*` 是 C 标准库在 fd 之上的「带缓冲的句柄」，缓冲在哪、为什么需要 `fflush`/`fclose`。
2. **正确选择 fopen 模式**：`r/w/a`、`+`、`b` 的含义与组合，知道「文本模式 vs 二进制模式」在 Windows 上的换行转换陷阱。
3. **安全读写二进制**：用 `fread/fwrite` 处理结构体数组/内存块，并**始终检查返回值**判断部分读写与 EOF。
4. **用 fseek/ftell 做随机访问**：定位修改记录、求文件大小，理解 `SEEK_SET/CUR/END` 与文本模式下 ftell 不可移植。
5. **正确处理错误**：打开必判 `NULL`，用 `errno`/`perror`/`strerror` 报因，理解 `feof` 的语义（读失败后才置位，不能当循环条件）。
6. **管理缓冲区与退出**：程序退出前 `fclose`（或 `fflush`）否则丢失内核/用户态缓冲数据。
7. **区分用户态缓冲与内核缓冲**：`fflush` 只刷到内核，`fsync` 才落盘——数据安全性的真正边界。

## 博士视角（要理解到什么程度）

- **IO 栈是分层的**：`fprintf` → `FILE` 的用户态缓冲 → `write()` 系统调用 → 内核页缓存（page cache）→ 磁盘。每一层都可能在「刷出」前丢数据。`fclose` 会依次 flush 用户缓冲再 `close`；进程被 `kill -9` 或崩溃时，连内核页缓存都未必落盘（除非 `fsync`）。
- **文本模式的换行转换是「流层」特性**：C 标准允许实现把 `\n` 与宿主的「行结束符」互转；在 Windows 上就是 `\n`↔`\r\n`。这属于「文本流」的语义，二进制流不做转换——这就是为什么在 Windows 上用文本模式读写二进制数据会损坏（把 `0A` 偷偷变成 `0D 0A`）。
- **EOF 与错误是两套状态位**：`feof()` 只反映「已发生读越界」，`ferror()` 反映 I/O 错误；二者都需在操作后查询，而非作为循环前置条件——这是新手最常犯的逻辑错误。

## 程序员视角（要能用出来）

- 凡是读写二进制（图片、序列化、结构体落盘），**永远用 `"b"` 模式**，跨平台才安全。
- `fread(buf, 1, N, fp)` 的惯用法是把「元素大小」写成 1、「数量」写成 N，再依据返回值判断实际读了多少字节——这样能正确处理「读到文件尾只拿到一部分」与「短读（short read）」。
- 每个 `fopen` 都必须判 `NULL`，并 `perror`/`strerror(errno)` 输出原因，否则出错时静默得到空指针、后续解引用崩溃。
- 长生命周期/守护进程里，写完关键数据要 `fflush`（甚至 `fsync`）再继续，别等到 `fclose` 或进程退出才发现问题。


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
