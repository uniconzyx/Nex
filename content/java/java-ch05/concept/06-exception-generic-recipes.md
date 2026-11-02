# java-ch05 · 异常与泛型实战：把机制落成代码

> §1–§5 讲清体系，这一节用可粘贴的片段把易错点焊死。凯喵在代码评审里最常挑出的几条。

### 受检异常不是敌人

`IOException` 这类受检异常逼你处理错误路径，是好事。别为了省事一层层 `throws` 甩到 main，也别无脑 `catch(Exception)` 吞掉。该处理的处理，该上抛的上抛。

### 异常链：cause 别丢

捕获底层异常后抛业务异常，**一定要把原异常作为 cause 传入**，否则排错时只剩顶层信息，根因消失。凯喵见过 `throw new BizException("fail")` 不带 cause，排查耗了一下午。

```java
try { repo.save(e); }
catch (SQLException ex) {
    throw new BizException("保存失败", ex);   // ex 作为 cause 保留
}
```

### try-with-resources 自动关

任何 `Closeable`/`AutoCloseable`（流、连接、锁）都用 try-with-resources，编译器自动在 finally 里调 `close()`，且能正确叠加多个资源关闭时的异常。手写 try/finally 容易漏关或把原异常吞了。

```java
try (Connection c = ds.getConnection();
     PreparedStatement ps = c.prepareStatement(sql)) {
    ps.executeUpdate();
} // 两个资源自动按逆序关闭，异常互不掩盖
```

### finally 里的 return 吞异常

`finally` 里写 `return` 会**覆盖** try/ catch 里抛出的异常或返回值，导致异常静默消失。finally 只做清理，不要有 return。

```java
int f() {
    try { return 1; }
    finally { /* 清理，千万别 return */ }
}
```

### 泛型擦除的运行时真相

编译后 `List<String>` 和 `List<Integer>` 都是 `List`，类型参数被擦除。所以 `list instanceof List<String>` 编译不过，`new T[]` 不行（不知道 T 大小）。凯喵用 `Array.newInstance(componentType, n)` 绕开。

### 桥接方法为何而生

泛型子类重写父类方法时，编译器合成一个桥接方法（如 `setData(Object)` 转发到 `setData(Integer)`）保证多态正确。它是编译器私有的，反射遍历方法要用 `isBridge()` 过滤，别在业务里依赖它。

### PECS：生产者 extends 消费者 super

`Producer Extends, Consumer Super`。只读的集合用 `? extends T`（能取 T 及其子），只写的用 `? super T`（能放 T 及其父）。凯喵记法：extends 出、super 入。

```java
void copy(List<? extends Number> src, List<? super Number> dst) {
    for (Number n : src) dst.add(n);  // src 取、dst 放，各司其职
}
```

### 自限定类型做递归约束

`class Node<T extends Node<T>>` 让类型参数引用自身，常见于链式 builder / 枚举式继承，表达「子类必须把自己作为类型参数传回」。看懂它才能读懂一些库源码。

### 通配符捕获的 ? 盒

`List<?>` 是「未知类型列表」，不能直接 `add`（编译器不敢保证类型安全）。需要操作未知类型时用 helper 方法「捕获」它：`<T> void help(List<T> l)`，让编译器能给 T 一个名字。

### 自定义异常的设计清单

异常要携带可操作信息：稳定错误码、是否可重试、是否需告警。别只传 message 字符串；把分类（如 `Retryable` / `Fatal`）做成接口或基类标记，调用方按类型决策而非解析文案。
