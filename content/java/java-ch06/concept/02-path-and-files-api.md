# Path 与 Files：现代文件操作的唯一正确姿势

## 主题一：File 与 Path 的差别，以及「路径拼接」的正确算法

`java.io.File` 是 1995 年的设计：路径拼接靠字符串（`new File(dir, name)` 尚可，
手写 `dir + "/" + name` 必然出问题——Windows 分隔符是 `\`）。
`java.nio.file.Path` 是不可变的、**平台无关**的路径抽象，配套 `Files` 工具类。

`Path` 的四个易混操作：

| 方法 | 语义 | 例子（`/a/b/c`） |
|---|---|---|
| `normalize()` | 消掉 `.` 与 `..`，**纯语法**操作 | `/a/b/../c` → `/a/c` |
| `resolve()` | 拼接（右为绝对路径时**直接返回右**） | `/a` + `b` → `/a/b`；`/a` + `/x` → `/x` |
| `relativize()` | 求相对路径 | `/a/b` 相对 `/a` → `b` |
| `toRealPath()` | 解析符号链接，**访问文件系统** | 会抛 IOException |

注意 `normalize()` **不检查文件是否存在**，也**不解析软链接**——
所以「用 normalize 做安全校验」是错的：`/safe/../../etc/passwd` normalize 后
变成 `/etc/passwd`，看起来"正常"但已经越界。安全的做法是 `toRealPath()` 后
判断是否以允许的根路径开头。

### 🧑‍💻 程序员视角
工程口诀：**「拼接用 `resolve`，判断用 `startsWith`，落地校验用 `toRealPath`」**。

用户可控路径（上传文件名、URL 参数）必须三段式校验：
```java
Path base = Path.of("/data/uploads").toRealPath();
Path target = base.resolve(userName).normalize();
if (!target.toRealPath().startsWith(base)) throw new SecurityException("path traversal");
```
只做 `normalize()` 不做 `toRealPath()` 的校验，可以被「先建软链接再访问」绕过。

### 🎓 博士生视角
路径语义差异的根源是各操作系统的**目录模型不同**：POSIX 只有单一根 `/`，
Windows 有盘符 + UNC 前缀，还有「大小写不敏感但保留大小写」的怪异语义。
`Path` 的设计把「语法路径」（`Path`）与「真实文件」（`toRealPath` 的结果）分开，
本质上是在**语法层不做任何文件系统假设**——这保证了 `Path` 运算可以纯离线、无副作用。

符号链接带来的循环是可判定的：`toRealPath` 内部维护已访问集合，
遇到环抛 `FileSystemException: Too many levels of symbolic links`。
这与早期 `find -L` 的循环检测是同一类问题。

### 📚 考研者视角
- **易错口径 1**：「`normalize()` 可以防目录穿越」——**错**，它不解析软链接，
  也不感知权限；正确做法是 `toRealPath()` + `startsWith` 白名单。
- **易错口径 2**：`resolve` 传入绝对路径会**丢弃**原路径。这点经常被拿来做陷阱题。
- **易错口径 3**：`File.getAbsolutePath()` **不解析** `..`；`getCanonicalPath()` 才解析，
  且会访问文件系统、可能抛 IOException。二者在笔试里是高频对比。
- **易错口径 4**：`new File("a", "b")` 与 `new File("a/b")` 在 Windows 上都能工作
  （Java 会规范化分隔符），但手写字符串拼接的 `"a/" + "b"` 在某些 API 上会失败。
- **必答对比**：`Files.readAllBytes` 一次性读入内存；`Files.lines` 是**惰性流**
  且持有文件句柄，**必须用 try-with-resources 包住**，否则句柄泄漏（这点在 Linux 上
  长时间运行必然触发 "Too many open files"）。

## 主题二：目录遍历与文件属性

两种遍历方式，语义完全不同：

- `Files.newDirectoryStream(dir)` —— **只列直接子项**，不递归，返回可关闭的迭代器。
- `Files.walk(dir, maxDepth)` —— **递归**（默认无限深度），返回惰性 `Stream<Path>`。

`Files.walk` 的坑：它默认**跟随或不跟随**软链接取决于是否传 `FOLLOW_LINKS`；
不传时不会跟随，因此不会因为软链接成环而无限递归。但深度不限制时，
面对 `/` 这种大目录会遍历海量文件——生产代码应始终给 `maxDepth`。

文件属性用 `Files.readAttributes(path, BasicFileAttributes.class)` 一次拿到
size/创建时间/最后修改时间/是否目录/是否符号链接，
比 `File.length()` + `lastModified()` 多次调用更省系统调用。

### 🧑‍💻 程序员视角
遍历选型：
- 只要一层 → `newDirectoryStream`
- 要递归 + 过滤 → `Files.walk` + `filter`（记得 `maxDepth`）
- 要「边遍历边删除」→ `Files.walkFileTree` + `SimpleFileVisitor`，
  在 `visitFile` 里删文件、`postVisitDirectory` 里删目录（**顺序不能反**，否则目录非空删不掉）。

`Files.delete` 对非空目录抛 `DirectoryNotEmptyException`；`Files.deleteIfExists`
只是把「不存在」变成 false，不改变「非空失败」的行为。

### 🎓 博士生视角
`walkFileTree` 采用**访问者模式**，把递归控制权交给调用方却保持遍历顺序，
本质上是把「先序 / 后序」这一策略外置：文件删除必须用**后序**
（子先于父），所以删除逻辑放在 `postVisitDirectory`。

从系统调用角度看，一次 `walk` 就是反复的 `getdents64` + `stat`，
其复杂度是 $O(\text{目录项数})$ 加上 $O(\text{深度})$ 的栈开销；
`DirectoryStream` 的迭代器模式让内存占用与目录大小无关（流式），
而 `Files.walk(...).collect(toList())` 会把所有路径装进内存——这是「能不能处理千万文件」的分水岭。

### 📚 考研者视角
- **高频问**：「`Files.walk` 和 `Files.walkFileTree` 怎么选？」
  标准答：前者是便捷流式 API，适合过滤/统计；后者可控遍历顺序与异常处理，
  适合删除、复制、权限继承这类需要「先子后父」的场景。
- **易错口径 1**：`Files.lines` / `Files.walk` 返回的 Stream **持有文件句柄**，
  不关闭就泄漏。面试常问「为什么 try-with-resources 要包 Stream」。
- **易错口径 2**：`Files.copy` 默认**不覆盖**已存在目标，会抛
  `FileAlreadyExistsException`；要覆盖必须传 `REPLACE_EXISTING`。
- **易错口径 3**：`Files.move` 跨文件系统时**退化为复制+删除**，此时
  `ATOMIC_MOVE` 会抛 `AtomicMoveNotSupportedException`。本机测试通过≠跨设备可用。
- **易错口径 4**：`File.deleteOnExit()` 只在 JVM 正常退出时执行，
  且顺序不确定（不要依赖父目录先于子目录）。
