# 缓冲、flush、fsync：`write` 成功不等于数据安全

## 1. 三层存储，三次"提交"

一次 `f.write("hello")` 到数据真正落在磁盘上，跨过三层：

| 层 | 数据在哪 | 触发"提交"的动作 | 崩溃后果 |
|---|---|---|---|
| ① Python 缓冲区 | 进程内存 | `flush()` / 缓冲满 / `with` 退出 | 进程崩溃即丢 |
| ② OS 页缓存 | 内核内存 | `fsync()`（或 OS 定期回写） | 机器断电/内核崩溃即丢 |
| ③ 磁盘介质 | 物理设备 | 磁盘固件提交 | — |

**只有走到了第 ③ 层，才可以说"数据安全"。**

```python
with open("log.txt", "w", encoding="utf-8") as f:
    f.write("important")
    # 此刻：数据在 Python 缓冲区（或者刚推到 OS 页缓存），磁盘上什么都没有
# with 退出 -> 隐式 flush -> 数据在 OS 页缓存，仍未落盘
```

### 为什么很多人以为 `with` 就安全了

因为 `with` 退出时确实调了 `flush()`，**对"进程不崩溃"的场景够了**；
但断电、内核崩溃、容器被 kill 的场景下，页缓存里的数据会消失。
数据库、WAL、日志系统的"每写必 fsync"就是为了这个。

## 2. 缓冲策略与 `buffering` 参数

`open()` 的 `buffering`：

| 取值 | 含义 |
|---|---|
| `-1`（默认） | 二进制用 `io.DEFAULT_BUFFER_SIZE`（通常 8192 或 4096 的倍数）；文本用行缓冲/块缓冲 |
| `0` | **仅二进制**允许，无缓冲（每次 write 直接系统调用） |
| `1` | 仅文本模式，**行缓冲**（遇到 `\n` 就 flush） |
| `>1` | 指定字节大小的块缓冲 |

注意：**文本模式不允许 `buffering=0`**，会直接抛 `ValueError`。

## 3. `flush` 与 `fsync` 的分工

```python
import os

f = open("db.log", "a", encoding="utf-8")
f.write("commit tx=42")
f.flush()                  # ① Python 缓冲 -> OS 页缓存
os.fsync(f.fileno())       # ② OS 页缓存 -> 磁盘
f.close()
```

- `flush()` 是**文件对象**的方法，只搬第 ①→② 层；
- `os.fsync(fd)` 是**系统调用**，搬第 ②→③ 层；
- 顺序不能颠倒，`fsync` 之前必须先 `flush`，否则内核里根本没有数据。

### `fsync` 的代价

每次 `fsync` 都要等磁盘确认，机械盘数量级毫秒。因此常见折中：

- **`fsync` 频率**：每 N 条记录一次（批提交），或每 T 毫秒一次（组提交）；
- **`os.fdatasync`**：只同步数据、不同步元数据（如 mtime），比 `fsync` 便宜；
- **权衡**：`fsync` 越多越安全也越慢，这不是"要不要"的问题，而是"多久一次"的取舍。
### 🧑‍💻 程序员视角
## 4. 原子写入的完整形态

```python
import os, pathlib, tempfile

def atomic_write_bytes(path, data: bytes):
    path = pathlib.Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
```

**四要素**：同目录临时文件、`flush` + `fsync`、`os.replace` 原子替换、异常清理。
缺任一都可能留下"半截文件"或"孤儿临时文件"。

对于**目录项本身**也要持久化的场景（如创建新文件后立刻断电），
还需要对**父目录**也做一次 `fsync`：

```python
dirfd = os.open(str(path.parent), os.O_RDONLY)
try:
    os.fsync(dirfd)
finally:
    os.close(dirfd)
```

Windows 不支持对目录 `fsync`，该步骤是 POSIX 专有做法。
### 🎓 博士生视角
## 5. 崩溃一致性：为什么"覆盖写"是不安全的

考虑 `f = open("cfg.json", "w")` 后写 1 MB 数据，在第 500 KB 时断电：

- 文件长度可能已被更新（元数据先提交），但内容只有前 500 KB；
- 或者内容写满但长度元数据未更新 —— 不同文件系统行为不同。

两者的共同点是：**读到的既不是旧版本也不是新版本**，而是损坏的中间态。
原子写入（临时文件 + `os.replace`）之所以正确，是因为
`rename` 在 POSIX 中被规定为**原子操作**：观察者要么看到旧文件，要么看到新文件，
不存在中间态。

这是"**全部或全无（all-or-nothing）**"语义在文件系统层面的实现，
也是日志型文件系统、以及数据库 WAL 共同依赖的基础假设。

### 与数据库的关系

数据库的"写前日志（WAL）"把这一思路推到极致：
先顺序追加日志并 `fsync`，再异步刷数据页。
崩溃恢复时重放日志即可 —— 用**顺序写**换**随机写**，既安全又快。
### 📚 考研者视角
## 6. 大文件处理的内存红线

| 做法 | 峰值内存 | 适用 |
|---|---|---|
| `f.read()` | O(文件大小) | 小文件（< 可用内存 1/10） |
| `f.readlines()` | O(文件大小 + 行对象开销) | 明确知道行数不多时 |
| `for line in f` | O(最长行) | **首选**，恒定内存 |
| `f.read(chunk)` 循环 | O(chunk) | 定长记录 / 二进制流 |
| `mmap` | 虚拟地址空间 O(大小)，物理按需 | 随机访问大文件 |

## 三视角解析

### 🧑‍💻 程序员视角

- **决策树**：需要"断电不丢"吗？→ 不需要 → 只 `flush`；
  需要 → `flush` + `fsync`；还要"读者永远看不到半截"→ 加临时文件 + `os.replace`。
- **排查顺序**：日志文件出现空文件或半截 → ① 是否用 `"w"` 直接覆盖写（应该用原子替换）；
  ② 是否在 `fsync` 前就被 kill；③ 是否把临时文件放到了另一个分区（`os.replace` 退化为复制）。
- **性能提醒**：把 `fsync` 放在**循环里**是常见的性能自杀；
  正确做法是批量提交或交给专门的日志/数据库组件。

### 🎓 博士生视角

- `flush` / `fsync` 的分层对应 Unix 的 **VFS 抽象**：文件对象缓冲在用户态，
  页缓存在内核态，二者各自有独立的提交点。这一设计让"写到文件"这个动作
  在语义上被拆成三个可独立观测的持久化级别。
- `rename` 的原子性是 **POSIX 规范**要求的（同文件系统内），
  它不是实现优化而是可依赖的契约；跨文件系统时该保证消失，
  因为底层退化为"复制 + unlink"两步。
- 崩溃一致性问题本质上是**分布式系统的两阶段提交缩小到单机**：
  数据与元数据必须分别提交，中间窗口即不一致窗口。

### 📚 考研者视角

非 408 统考内容，按**笔面工程题**口径：

- **标准问法**：「`flush` 和 `fsync` 有什么区别？」
  标准答题结构 = 「`flush` 把用户态缓冲交给 OS 页缓存，`fsync` 把页缓存写到磁盘；
  前者进程崩溃即失效，后者才抗断电」。
- **易错口径**：
  1. 认为 `with` 退出就落盘了 —— 只到页缓存，**抗不住断电**。
  2. 认为 `fsync` 越频繁越好 —— 它与吞吐是明确的取舍关系，要问清场景。
  3. 混淆 `os.replace` 与 `os.rename` 的可移植性（Windows 上行为不同）。
- **记忆锚点**：**「flush 交内核，fsync 进磁盘；rename 才原子」**。
