# 序列化与 IO 模型选型

## 主题一：序列化机制的三个真相

`Serializable` 是个**标记接口**（没有任何方法），但它真正做的事是：
授予 `ObjectOutputStream` 通过反射**读写对象全部字段**的权限，
且绕过了构造器（反序列化不调用构造方法）。

三个必须知道的真相：

1. **`serialVersionUID` 决定兼容性**。不显式声明时由编译器按结构算出一个哈希，
   任何字段增删都会改变它，导致 `InvalidClassException`。
   显式声明（`private static final long serialVersionUID = 1L;`）等于承诺"我自己管兼容"。
2. **`transient` 字段不参与序列化**（反序列化后是默认值，不是 null/0 之外的任何东西）。
   密码、Socket、线程、`InputStream` 都必须标 `transient`。
3. **`readObject()` 是攻击面**。它会对输入流里出现的**任何可加载类**执行
   反序列化，攻击者可以构造 gadget chain 触发任意方法调用 → RCE。
   这不是"用不好"的问题，是**机制本身不可用于不可信数据**。

所以现代做法：对外交换用 JSON / Protobuf / Avro，
Java 原生序列化只用于**进程内可信**的临时场景（如 RMI、Session 复制——即使这些也常被禁用）。

### 🧑‍💻 程序员视角
工程红线（能背下来就能拦住绝大多数事故）：
- 不可信来源（网络、上传、缓存、MQ 消息体）**禁止** `ObjectInputStream`
- 必须用时加 `ObjectInputFilter` 白名单（JDK 9+），并配 `resolveClass` 校验
- 需要 `Serializable` 的类**永远显式**声明 `serialVersionUID`
- 需要自定义初始化逻辑时实现 `private void readObject(ObjectInputStream)`，
  且**必须**在其中做参数校验（因为构造器被绕过）

```java
private static final long serialVersionUID = 1L;

private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
    in.defaultReadObject();
    if (amount < 0) throw new InvalidObjectException("amount < 0");   // 不加这行就是漏洞
}
```

### 🎓 博士生视角
为什么反序列化不调用构造器？因为它的语义是**恢复对象图**而不是**创建对象**：
流里已经包含所有字段值，构造器可能做副作用（注册、开连接）会破坏幂等。
代价是**类不变量失去强制点**——构造器是唯一能"保证对象创建后合法"的地方，
绕过它就必须在 `readObject` 里手工重建这些不变量。

从攻击面看，漏洞的根因是**类型由数据决定**（流里带类名）：
这是一种"数据即代码"的反模式。安全序列化格式（Protobuf/Avro）的做法相反——
schema 由**接收方预先持有**，流里只带字段号与值，类型由 schema 决定而非数据。
把「类型来源」从数据侧移到代码侧，是消除这类漏洞的根本手段。

### 📚 考研者视角
- **高频问**：「`Serializable` 有什么用？为什么要有 `serialVersionUID`？」
  标准答：标记接口，授权对象图 I/O；`serialVersionUID` 用于版本兼容校验，
  不一致时抛 `InvalidClassException`。
- **易错口径 1**：`transient` 只能修饰字段，不能修饰类或方法。
- **易错口径 2**：静态字段**本来就不参与**序列化（属于类不属于对象），
  加 `transient` 是多余但无害。
- **易错口径 3**：反序列化**不调用**构造器（包括无参构造），但会调用
  第一个非 `Serializable` 父类的无参构造器。
- **易错口径 4**：`Externalizable` 需要我们提供 `public` 无参构造器且
  自己实现 `writeExternal`/`readExternal`，与 `Serializable` 的行为差异是常考点。
- **必答**：写 `ObjectOutputStream` 时**先写文件头**（魔数 + 版本），
  所以它不能直接写入一个已有内容的文件中间。

## 主题二：IO 模型与 Java 的对应关系

五种 IO 模型与 Java 的映射：

| 模型 | 阶段一（等数据） | 阶段二（拷贝到用户态） | Java 对应 |
|---|---|---|---|
| 阻塞 BIO | 阻塞 | 阻塞 | `InputStream` + 每连接一线程 |
| 非阻塞 NIO | 轮询 | 阻塞 | `configureBlocking(false)` |
| IO 多路复用 | `select` 阻塞 | 阻塞 | `Selector` |
| 信号驱动 | 回调 | 阻塞 | Java 无原生支持 |
| 异步 AIO | 都不阻塞 | 都不阻塞 | `AsynchronousChannelGroup` |

分清「多路复用」与「异步」的差别是面试分水岭：
**多路复用只解决了"等数据"阶段的阻塞，"拷贝到用户态"这一阶段仍然要等**；
只有 AIO 才把两个阶段都交给内核。

Linux 上 AIO 实现长期不成熟（`io_uring` 才有实质改善），
所以 Java 生态实际被 Netty（多路复用）统治；
JDK 21 的**虚拟线程**用另一条路解决了同样的问题——让阻塞式代码
在调度层面变得廉价，从而不必改写业务逻辑。

### 🧑‍💻 程序员视角
选型决策树：
1. 并发连接 < 几百，业务是 CPU 或数据库密集 → **BIO + 线程池**，最易维护
2. 并发连接上万且长连接 → **Netty**（不要自己写 Selector 循环）
3. JDK 21+ 且业务是"阻塞式调用外部服务" → **虚拟线程**，代码几乎不用改
4. 文件/流对拷 → `transferTo`

反面案例：用 `Selector` 处理"每个请求都要查数据库"的业务——
数据库调用本身是阻塞的，一旦在事件循环里阻塞，整个 Selector 停摆。
Netty 的规矩「不要在 EventLoop 里做阻塞操作」就是这个原因。

### 🎓 博士生视角
从调度成本看，把一个阻塞线程切换到另一个的代价约为微秒级，
而一次网络往返是毫秒级——所以「线程池 + 阻塞 IO」在连接数不极端时，
其总成本与「复杂的事件循环」相当，但**可维护性高一个量级**。
虚拟线程把线程栈压到几百字节并放在堆上，让「一个连接一个线程」
的模型在万级并发下重新可用，本质是**用工程手段绕过了 select 的复杂度**。

形式化地说：多路复用把「等待」从每个连接转移到了一次 `epoll_wait`，
代价是**事件驱动式的控制反转**（你的代码不再是顺序的），
这正是它难写易错的原因；虚拟线程保留了顺序语义，把反转交还给运行时。

### 📚 考研者视角
- **高频问**：「BIO、NIO、AIO 的区别？」标准答（必须分两阶段说）：
  BIO 两阶段都阻塞；NIO 的等数据阶段非阻塞（靠 Selector 轮询）；AIO 两阶段都异步。
- **易错口径 1**：「NIO 一定比 BIO 快」——错。连接数少时 BIO 更快更简单
  （少了事件分发开销）。
- **易错口径 2**：`select` / `poll` / `epoll` 常被并列问：
  `select` 有 FD 数量上限（1024）且每次要拷贝 fd 集合；`epoll` 用红黑树 + 就绪链表，
  复杂度与连接数无关。
- **易错口径 3**：`FileChannel` 不能注册到 Selector（文件永远就绪），
  这点常被当作「NIO 的一个例外」来考。
- **必答**：「零拷贝」指数据不经过用户态，不是"不拷贝"——
  至少仍有内核缓冲区之间的拷贝。
