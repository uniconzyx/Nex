# Channel / Buffer / Selector：NIO 的三大件

## 主题一：ByteBuffer 的三游标与状态机

`ByteBuffer` 内建三个游标：

```
0            position      limit        capacity
|---- 已读 ---|-- 可读写 ---|---- 空闲 ----|
```

- `put(x)`：写一个元素，position++
- **`flip()`**：`limit = position; position = 0` —— 从「写模式」切到「读模式」
- `get()`：读一个元素，position++
- `clear()`：`position = 0; limit = capacity` —— 「整块作废，重新写」
- `compact()`：把未读部分挪到开头，position 指向其后 —— 「保留未读，继续写」

**忘写 `flip()` 的后果**：position 停在末尾、limit 仍是 capacity，
于是 `get()` 立刻抛出 `BufferUnderflowException`；如果之前 position 恰好等于 limit，
读出来就是 0 字节（数据"凭空消失"）。

`clear()` 与 `compact()` 的选择是经典的业务判断：
- 整块数据都已处理完 → `clear()`
- 只处理了一部分，剩余要接续 → `compact()`

### 🧑‍💻 程序员视角
调试经验：Buffer 相关 bug 几乎都是**模式切换漏了**。固定排查动作是
在每次读写边界打印 `pos/lim/cap` 三元组。现代工程里更推荐
**相对方法 `get`/`put` 配绝对方法 `get(i)` 混用**要格外小心：
绝对方法**不移动** position，用它"顺手看一眼"不会破坏状态。

另一个高频坑：`ByteBuffer` **不是线程安全的**，但 `position/limit` 的修改
对其他线程可见性没有保证。多线程共享一个 Buffer 必须外部同步，
而正确做法是每个线程一个 Buffer（线程本地或 Channel 独享）。

### 🎓 博士生视角
`Buffer` 的状态机是**读写同体**这一设计选择的必然结果：
如果为读和写各开一个游标，就得多存两个 int；用一个游标加模式切换，
省内存但把状态管理责任推给了调用方。

从内存层次看，`HeapByteBuffer` 的数组在 Java 堆上，做 IO 时先被拷到直接内存；
`DirectByteBuffer` 直接在堆外分配，可以和内核零拷贝共享，
但分配/释放代价高（受 `MaxDirectMemorySize` 限制，且依赖 `Cleaner` 延迟回收）。
所以「小块高频」用堆缓冲、「大块长生命周期 IO」用直接缓冲，
`FileChannel.map` 返回的 `MappedByteBuffer` 是操作系统页缓存的映射视图，
它的回收由 GC 触发（存在著名的"删不掉文件"问题）。

一个形式化的视角：Buffer 的 `position/limit` 定义了半开区间 $[\text{position}, \text{limit})$，
所有读写操作都是在这个区间上的单调推进 —— `flip` 就是把这个区间的端点做了一个"交换"。

### 📚 考研者视角
- **高频问**：「`flip` / `clear` / `compact` 的区别？」标准答（必须能画图）：
  flip 切读模式；clear 全清重写；compact 保留未读数据再切回写模式。
- **易错口径 1**：「`clear()` 会清空数据」——错。它只重置游标，**数据还在**，
  下次写会覆盖。这是最爱考的"名不副实"方法。
- **易错口径 2**：`rewind()` 只把 position 置 0，**limit 不动**；
  所以 `rewind` 之后仍处于读模式，与 `clear` 完全不同。
- **易错口径 3**：`array()` 只在 `HeapByteBuffer` 上可用，`DirectByteBuffer` 上抛
  `UnsupportedOperationException`。判断可读性用 `hasArray()`。
- **易错口径 4**：`flip()` 的等价物是 `limit(position()); position(0)`，
  面试让你手写实现要能写出来。
- **必背**：`remaining() = limit - position`。

## 主题二：Selector 多路复用与零拷贝

**Selector** 是「一个线程管很多连接」的关键：把多个 `Channel`
注册到同一个 `Selector` 上并指明关心的事件（`OP_ACCEPT` / `OP_READ` / `OP_WRITE`），
然后 `select()` 阻塞直到**至少一个**通道就绪，返回就绪数量。

标准事件循环（必须背下来）：

```java
while (running) {
    selector.select();                       // 阻塞直到有就绪事件
    Iterator<SelectionKey> it = selector.selectedKeys().iterator();
    while (it.hasNext()) {
        SelectionKey key = it.next();
        it.remove();                          // 必须先移除，否则下次重复处理
        if (key.isAcceptable()) { /* accept + register */ }
        else if (key.isReadable()) { /* read */ }
        else if (key.isWritable()) { /* write */ }
    }
}
```

**`it.remove()` 是全班最容易忘、后果最直接的一行**：忘记移除会让同一个 key
被反复处理，表现为「同一条消息被回显多次」。

**零拷贝**：`FileChannel.transferTo(position, count, target)` 让数据在
内核内部直接从文件页缓存搬到 socket 缓冲区，跳过用户态。
`RandomAccessFile` + `transferTo` 是现代静态文件服务器的基本做法。

### 🧑‍💻 程序员视角
选型决策：
- 连接数少、每连接数据量大 → **BIO + 线程池**（代码最简单，别过度设计）
- 连接数万级、每连接数据量小 → **NIO + Selector**（Netty 就是这套）
- 单机文件/流对拷 → `transferTo` / `transferFrom`

必须注意：`OP_WRITE` **几乎总是就绪的**，无条件注册它会导致 `select()`
空转烧 CPU。正确做法是「写不进去时才注册 `OP_WRITE`，写完立即取消」。

### 🎓 博士生视角
Selector 的底层是各平台的**就绪通知机制**：Linux 上是 epoll
（O(1) 返回就绪集合），早期 BSD 上是 kqueue，Windows 上是 IOCP 的模拟层。
这也解释了为什么 `select()` 返回的是「就绪数量」而不是数据——
它只告诉你**可以动了**，不代你做任何 IO。

零拷贝的收益可以用拷贝次数刻画：传统 `read + write` 是 4 次上下文切换 + 4 次拷贝
（磁盘→内核页缓存→用户态→socket 缓冲区→网卡），`transferTo` 在支持
`splice`/`sendfile` 的平台上降到 2 次拷贝、2 次切换。
注意：如果对传输的数据做了加密/压缩，内核无法直接转发，零拷贝就失效——
这是「HTTPS 让 sendfile 退化为普通拷贝」的原因。

Reactor 模式的形式化：`Selector` 提供了事件源，事件循环是单线程的
「分发器」，业务处理可以派给工作线程池 —— 这就是 Netty 的
`EventLoopGroup`（boss 处理 accept、worker 处理 read/write）的来源。

### 📚 考研者视角
- **高频问**：「NIO 是 Non-blocking IO 吗？」标准答：更准确说是 **New IO**，
  它同时提供了非阻塞模式与 Buffer/Channel 抽象；阻塞与否由 `configureBlocking` 决定。
- **易错口径 1**：「Selector 只能管理 Channel，不能管理 InputStream」——对，
  `FileChannel` 甚至**不能**注册到 Selector（文件永远"就绪"）。
- **易错口径 2**：`select()` 返回 0 可能是**超时**（带超时版本），
  不是"没有事件"；`selectNow()` 才是立即返回。
- **易错口径 3**：`OP_WRITE` 就绪 ≠ 能写完；仍然要看 `write()` 的返回值，
  可能只写了一半（必须循环写到 `remaining()==0`）。
- **易错口径 4**：`Channel` 是线程安全的（规范要求），但**复合操作**
  （先读后写同一连接）不是；`ByteBuffer` 不是线程安全的。
- **必背**：`ByteBuffer.allocateDirect` 分配堆外内存；`FileChannel` 由
  `FileInputStream.getChannel()` / `Files.newByteChannel` 获得。
