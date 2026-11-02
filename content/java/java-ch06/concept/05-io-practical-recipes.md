# §5 java-ch06 实战手记：凯喵带你把 IO 用「漏」

> 前五节把流、Path、Channel、序列化讲透了。这一节凯喵把线上 IO 事故最集中的 12 个现场搬出来——句柄泄漏、编码乱码、Buffer 读空、反序列化 RCE。每个都是真金白银换来的教训。

### 现场一：忘记关流 = 句柄泄漏，三天后服务挂

凯喵第一次负责导出功能，循环里每次 `new FileOutputStream` 都不关，跑三天后 `java.io.IOException: Too many open files`。Linux 默认单进程文件描述符上限 1024，不关就耗尽。解法：一律 try-with-resources，编译器自动生成 `finally` 关流，连异常时的关闭顺序都帮你排好。

```java
// ❌ 漏关
FileOutputStream out = new FileOutputStream("a.txt");
out.write(data);   // 异常时 out 永远不会 close

// ✅ try-with-resources，自动关闭
try (FileOutputStream out = new FileOutputStream("a.txt")) {
    out.write(data);
} // 这里自动 out.close()，即使异常也关
```

### 现场二：编码发生在桥接点，不在 FileReader 里

凯喵见过「本地好好的，服务器上中文全变问号」。`FileReader` / `FileWriter` 用的是**平台默认编码**，开发机是 UTF-8，生产机可能是 GBK，于是乱码。编码转换只发生在 `InputStreamReader` / `OutputStreamWriter` 这个桥接处，必须显式传 charset。

```java
// ❌ 平台默认编码，跨机器玄学
try (BufferedReader r = new BufferedReader(new FileReader("f.txt"))) { ... }

// ✅ 显式 UTF-8
try (BufferedReader r = new BufferedReader(
        new InputStreamReader(new FileInputStream("f.txt"), StandardCharsets.UTF_8))) {
    String line;
    while ((line = r.readLine()) != null) { ... }
}
```

### 现场三：read() 返回 -1 当结束标志，漏判就死循环

凯喵带人写「边读边写」拷贝时，新人写 `while (in.read(buf) > 0)`。问题是**最后一块可能返回 0**（读到了但没满缓冲），于是循环条件 `> 0` 直接终止，文件尾部被吞。正确判断必须用 `-1` 表示「流结束」。

```java
byte[] buf = new byte[8192];
int n;
// ✅ -1 才是 EOF
while ((n = in.read(buf)) != -1) {
    out.write(buf, 0, n);
}
// ❌ while ((n = in.read(buf)) > 0) 会吞掉最后不足一块的数据
```

### 现场四：大文件一次性读进内存 = OOM

凯喵见过 `Files.readAllBytes(Paths.get(huge))` 读一个 4GB 文件，直接 `OutOfMemoryError`。`readAllBytes` 把整文件塞进一个 byte[]，堆撑不住。大文件必须流式分块读，或者上 NIO 的 `transferTo` 零拷贝。

```java
// ❌ 大文件 OOM
byte[] all = Files.readAllBytes(Paths.get("4gb.bin"));

// ✅ 流式拷贝，恒定内存
try (InputStream in = new FileInputStream("4gb.bin");
     OutputStream out = new FileOutputStream("out.bin")) {
    byte[] buf = new byte[8192]; int n;
    while ((n = in.read(buf)) != -1) out.write(buf, 0, n);
}
```

### 现场五：Files.walk 不关会锁目录

`Files.walk` 返回的是一个 `Stream<Path>`，底层持有 `DirectoryStream`。凯喵踩过：遍历完不关，Windows 上那个目录删不掉（被锁）。记得 `try (var s = Files.walk(dir))`。

```java
try (Stream<Path> s = Files.walk(Paths.get("/data"))) {
    s.filter(Files::isRegularFile)
     .filter(p -> p.toString().endsWith(".log"))
     .forEach(System.out::println);
} // 自动关流，释放目录锁
```

### 现场六：ByteBuffer 忘写 flip() 读出 0 字节

凯喵第一次手写 NIO 拷贝，`put` 完直接 `get`，结果读出来全是 0。原因是 `flip()` 把 `position` 重置到 0、`limit` 设到刚才写到的位置——不 flip，get 从写末尾继续读，自然是空的。口诀：**写后 flip 切读，读后 clear/compact 切写**。

```java
ByteBuffer buf = ByteBuffer.allocate(1024);
buf.put("hello".getBytes());
// buf.flip();            // ❌ 漏了，get 读到 0 字节
buf.flip();                 // ✅ position=0, limit=写到的位置
byte[] out = new byte[buf.remaining()];
buf.get(out);
System.out.println(new String(out)); // hello
```

### 现场七：Selector 注册后忘 remove 就绪 key，事件被重复处理

凯喵的 NIO 回声服务器曾「一条消息反复回显」。根因：`selectedKeys()` 里的 key 不会自动移除，你 `next()` 出来不 `remove()`，下一轮 `select()` 又把它算作就绪，同一条消息被处理 N 次。处理完必须 `it.remove()`。

```java
while (true) {
    selector.select();
    Iterator<SelectionKey> it = selector.selectedKeys().iterator();
    while (it.hasNext()) {
        SelectionKey k = it.next();
        it.remove();   // ✅ 必须移除，否则重复触发
        if (k.isReadable()) handleRead(k);
    }
}
```

### 现场八：无条件注册 OP_WRITE 导致 CPU 打满

凯喵的网关一度 100% CPU。原因是「无论如何都注册 `OP_WRITE`」——写事件几乎总是就绪，`select()` 立刻返回形成忙等。正确做法：只有真写不进去（write 返回 0）才注册 OP_WRITE，写完立刻 `cancel()` 并只保留 OP_READ。

```java
// 只在写不进去时注册
int written = channel.write(buf);
if (written == 0) {
    key.interestOps(SelectionKey.OP_WRITE);
} else {
    key.interestOps(SelectionKey.OP_READ);
}
```

### 现场九：Path.normalize() 不防目录穿越

凯喵做过一个「用户给文件名，服务端拼路径」的功能，以为 `normalize()` 能挡 `../../etc/passwd`。错。`normalize` 只做**语法化简**（`a/./b` → `a/b`），不解析符号链接，挡不住 `..` 上跳。要防穿越得 `toRealPath()` 再校验 `startsWith(允许的根)`。

```java
Path root = Paths.get("/srv/upload").toRealPath();
Path user = root.resolve(input).normalize();
// ❌ 只 normalize 不够
if (!user.toRealPath().startsWith(root)) {      // ✅ 真实路径再校验
    throw new SecurityException("目录穿越");
}
```

### 现场十：transferTo 比手拷快，因为是零拷贝

凯喵优化大文件分发时，把「读进 byte[] 再写」换成 `in.transferTo(out)`，吞吐直接翻倍。原理：数据从磁盘文件经 DMA 直送网卡/目标文件，**不经过用户态内存**，少了两次内核态↔用户态拷贝。Linux 下是 `sendfile` 系统调用。

```java
try (FileChannel in = FileChannel.open(src, READ);
     FileChannel out = FileChannel.open(dst, WRITE, CREATE)) {
    in.transferTo(0, in.size(), out);   // 零拷贝，恒定内存
}
```

### 现场十一：序列化版本号 serialVersionUID 不一致 = 反序列化失败

凯喵的缓存系统升级后，老缓存全部 `InvalidClassException`。因为类改了字段却没固定 `serialVersionUID`，JVM 自动按类结构算了一个，新旧对不上。规则：**凡是 `implements Serializable` 的类，显式声明 `serialVersionUID`**，这样字段微调也能兼容老数据。

```java
class User implements Serializable {
    private static final long serialVersionUID = 1L;  // ✅ 显式固定
    String name;
    // 加字段不破坏老数据兼容性
}
```

### 现场十二：ObjectInputStream 读不可信数据 = 直接 RCE

这是 IO 最危险的一处。凯喵严肃提醒：`ObjectInputStream.readObject()` 会实例化输入流里出现的**任意可加载类**，攻击者构造恶意字节流就能执行任意代码。绝不要用它读来自网络 / MQ / 缓存的数据。对外交换改用 JSON / Protobuf，必须用时加 `ObjectInputFilter` 白名单。

```java
// ❌ 读不可信数据，等于开门迎黑客
Object o = new ObjectInputStream(socket.getInputStream()).readObject();

// ✅ 白名单过滤 + 改用 JSON
ObjectInputFilter f = ObjectInputFilter.Config.createFilter("com.myapp.Safe;!*");
try (ObjectInputStream ois = new ObjectInputStream(in)) {
    ois.setObjectInputFilter(f);
    Object o = ois.readObject();
}
```

> 凯喵总结：IO 的事故八成是「资源忘了关」「编码默认了」「边界没判 -1」「不可信数据当可信读」。把这 12 个现场过一遍，线上少背三回锅。
