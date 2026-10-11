1. **用 `FileReader`/`FileWriter` 读线上文件** —— 它们使用平台默认字符集，Windows 与 Linux 行为不同，跨机器必乱码。正确写法：`Files.newBufferedReader(p, StandardCharsets.UTF_8)`。

2. **忘了给 `Serializable` 类声明 `serialVersionUID`** —— 字段增删会让编译器算出的隐含值变化，跨版本反序列化抛 `InvalidClassException`。正确写法：显式 `private static final long serialVersionUID = 1L;`。

3. **把 `transient` 当成"私有字段"的替代** —— `transient` 与访问控制无关，它只表示「不参与序列化」。密码字段标 `private` 仍会被序列化写进流里。

4. **`ByteBuffer` 写完不 `flip()` 就读** —— position 停在末尾，`get()` 抛 `BufferUnderflowException`，或"读到 0 字节"。正确写法：`put` 完 → `flip()` → `get` 到 `!hasRemaining()` → `clear()`/`compact()`。

5. **以为 `clear()` 会清空数据** —— 它只把 `position=0; limit=capacity`，数据仍在，下次写会直接覆盖。要"保留未读数据再继续写"必须用 `compact()`。

6. **用 `available()` 当文件大小** —— `available()` 只保证「不阻塞能读到的字节数」，对本地文件它约等于剩余长度但**规范不保证**，对网络流更是无意义。

7. **`read()` 的返回值用 `byte` 接** —— `read()` 返回 `int`，`-1` 表示 EOF；用 `byte` 接会把 `-1` 当成有效数据 0xFF，导致「文件末尾多读一个字节」或死循环。

8. **`readLine()` 返回 `""` 时当成结束** —— `""` 表示空行，只有 `null` 才表示流结束。用 `equals("")` 判断会半路截断文件。

9. **`Files.lines` / `Files.walk` 不关流** —— 它们持有文件句柄，长期运行必然触发 `Too many open files`。必须用 try-with-resources 包住返回的 Stream。

10. **`Files.copy` / `Files.move` 忘传 `REPLACE_EXISTING`** —— 目标已存在时抛 `FileAlreadyExistsException`；而跨文件系统时 `ATOMIC_MOVE` 会抛 `AtomicMoveNotSupportedException`，本机通过不代表线上可用。

11. **Selector 循环里忘记 `it.remove()`** —— 就绪 key 不会自动清除，同一个事件会被反复处理，表现为「消息被重复回显」。必须在 `next()` 之后立刻 `remove()`。

12. **无条件注册 `OP_WRITE`** —— 写事件几乎总是就绪，`select()` 会立刻返回形成忙等，CPU 打满。正确做法：真写不进去时才注册，写完立即 `cancel()` 并重新只注册 `OP_READ`。

13. **把用户可控路径直接 `resolve` 后使用** —— `normalize()` **不解析符号链接**，只做语法化简，因此 `normalize` 不能防目录穿越。正确做法：`toRealPath()` 后校验 `startsWith(允许的根)`。

14. **用 `ObjectInputStream` 读来自网络/MQ/缓存的数据** —— `readObject()` 会实例化输入流里出现的任意可加载类，是直接的 RCE 攻击面。正确做法：对外交换改用 JSON/Protobuf；必须用时加 `ObjectInputFilter` 白名单。
