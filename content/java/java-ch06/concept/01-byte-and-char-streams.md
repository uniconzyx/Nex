# 字节流与字符流：编码的边界在哪里

## 主题一：字节与字符的分工

`InputStream` / `OutputStream` 处理的是**字节**（`byte[]`），
`Reader` / `Writer` 处理的是**字符**（`char`，UTF-16 码元）。

关键点：**Java 的 `char` 是 UTF-16 码元，不是「一个字符」**。
所以 `"𝄞".length()` 是 2 —— 一个补充平面字符占两个 char。这一点在按字符切片时必炸。

编码转换只发生在**桥接点**：

```java
InputStream in = new FileInputStream("a.txt");              // 字节
Reader r = new InputStreamReader(in, StandardCharsets.UTF_8); // 字节 -> 字符（唯一转换点）
```

如果直接用 `FileReader`，它内部用的是 `Charset.defaultCharset()` ——
**同一个 jar 在 Windows（GBK）和 Linux（UTF-8）上行为不同**，这是"本地跑得好好的，
上服务器就乱码"的根因。

### 🧑‍💻 程序员视角
```java
// 工程决策树：拿到一个"要读文本"的需求，先问三个问题
// 1) 编码确定吗？——不确定就不要用 FileReader/FileWriter
// 2) 文件多大？—— 大于可用堆就要流式处理，禁止 readAllBytes
// 3) 需要对端/他人复现吗？——需要就写死 StandardCharsets.UTF_8
Reader r = Files.newBufferedReader(path, StandardCharsets.UTF_8);
```
排查顺序：先看**字节层面**（`xxd`/`Format-Hex` 看有没有 EF BB BF 的 BOM、
是不是合法的 UTF-8 序列），再看字符层面。跳过字节层直接猜编码，是最常见的低效排查。

### 🎓 博士生视角
字符流的本质是**状态机 + 码元解码器**：`CharsetDecoder` 把字节序列按编码规则
映射到 Unicode 码点序列，其中可能出现三种状态——完整、不完整（需要更多字节）、
非法（`MalformedInputException`）。

严格解码（`CodingErrorAction.REPORT`）与替换解码（`REPLACE`，产生 U+FFFD）是**语义不同**的：
前者保证「解出来的都是真的」，后者保证「不中断」。流式网络协议里通常选严格模式，
因为错误必须能被发现；日志脱敏场景可选替换模式，因为不能因为一行坏字节丢掉整批数据。

UTF-8 的**自同步性**（每个字节的高位模式唯一确定其角色）是它抗截断的根本原因，
这也是 `RandomAccessFile` 能在任意字节偏移处开始解码的前提（前提：偏移必须落在字符边界）。

### 📚 考研者视角
笔试面试标准问法与易错口径：

- **高频问**：「`FileReader` 和 `InputStreamReader` 有什么区别？」
  标准答：`FileReader` 是便捷类，使用平台默认字符集；`InputStreamReader` 允许显式指定
  字符集，是**唯一可控**的字节→字符转换入口。（新面试口径还会追问 `Files.newBufferedReader`。）
- **易错口径 1**：「`char` 占 2 字节，所以一个 char 就是一个字符」——错。UTF-16 码元 ≠ 码点。
- **易错口径 2**：「`Reader.read()` 返回 `char`」——错，返回 `int`，`-1` 表示流结束；
  必须用 `int` 接住再判断，用 `byte`/`char` 接会吞掉 `-1` 判断。
- **易错口径 3**：`available()` 的返回值**不是**文件总长度，它只是「不阻塞就能读到的字节数」。
  用 `available()` 当文件大小是典型错误。
- **必背**：`read()` 返回 -1 表示 EOF；`read(byte[])` 返回本次实际读到的字节数，也可能是 0（阻塞流极少见）。

## 主题二：装饰器模式与缓冲的语义

`BufferedInputStream` / `BufferedReader` 不是为了「好看」，它的两个真实作用是：

1. **减少系统调用**：底层 `FileInputStream.read()` 每次都是一次 `read(2)`，
   逐字节读 1MB 文件 ≈ 100 万次系统调用。缓冲后按 8KB 块读，约 128 次。
2. **提供行语义**：`BufferedReader.readLine()` 是唯一标准的「按行读」手段。

装饰器模式的代价是**层级嵌套**，这也是「关最外层即可」的原因：
`FilterInputStream.close()` 会向下传播（`in.close()`），
所以 try-with-resources 里只需要声明最外层资源。

### 🧑‍💻 程序员视角
判断要不要缓冲：**只要循环里调用 `read()`/`write()` 的次数可能很大，就必须缓冲**。
经典口诀：*"内外层反过来写不出来"* —— `new BufferedReader(new FileReader(f))` 可以，
`new FileReader(new BufferedReader(...))` 编译不过（类型不匹配，正好拦住了错误用法）。

工程里我更倾向直接 `Files.newBufferedReader` / `Files.readAllLines`（小文件），
少一层手工嵌套就少一次关错资源的可能。

### 🎓 博士生视角
缓冲的收益是**摊销模型**：设系统调用单次代价 $c$、块大小 $B$、总数据量 $N$，
无缓冲代价 $cN$，有缓冲代价 $c\lceil N/B\rceil + N$（第二项是内存拷贝）。
当 $c \gg 1$（真实系统中 `read(2)` 是微秒级而内存拷贝是纳秒级）时收益约为 $B$ 倍。

但注意：**缓冲会改变可见性时机**。`BufferedWriter` 不 `flush()` 时数据可能仍在内存中，
进程崩溃就丢；这在「写日志后立即要求另一个进程可见」的场景是硬伤。
`PrintWriter` 默认不自动 flush（除非构造时传 `autoFlush=true`，且仅对 `println` 生效）。

### 📚 考研者视角
- **高频问**：「缓冲流为什么快？」标准答：减少系统调用次数（不是"减少磁盘 IO"——磁盘
  本身也有页缓存）。补一句「本质是把 $N$ 次系统调用摊销为 $N/B$ 次」是加分项。
- **易错口径 1**：`BufferedWriter` 写完必须 `flush()` 或 `close()`，否则数据可能丢失。
  try-with-resources 会 close，close 内部会 flush，所以别在 try 外依赖数据已落盘。
- **易错口径 2**：`readLine()` 返回的**不含换行符**；遇到连续空行返回空字符串 `""`，
  只有到达文件末尾才返回 `null`。把 `""` 当成结束条件是经典 bug。
- **易错口径 3**：`read()` 无参返回 `int`（0~255 或 -1），不是 `byte`。
- **易错口径 4**：`mark`/`reset` 只在支持 mark 的流上有效，且超出 `readAheadLimit` 后 reset 会抛 IOException。
