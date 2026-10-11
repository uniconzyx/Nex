# 内存泄漏、调试工具与内存池

## 一、什么是内存泄漏

**定义**：已分配的堆内存**失去所有引用**——既无法再访问，也无法再释放。进程常驻内存持续增长，最终 OOM。

```
栈/全局：p ─╳    （p 被覆盖或作用域结束）
堆：      [==============]  ← 失去引用，永不释放
```

## 二、六大典型成因

1. **忘记 `free`**：最直接。
2. **错误分支提前返回**：

```c
int f(void) {
    char *buf = malloc(1024);
    if (some_error()) {
        return -1;          /* ❌ buf 泄漏 */
    }
    free(buf);
    return 0;
}
```

3. **指针被覆盖**：

```c
p = malloc(100);
p = malloc(200);    /* ❌ 第一块失去引用 */
```

4. **`realloc` 失败后直接赋值**（见 clang-u02 概念 2）。
5. **别名与所有权不明**：两个指针指向同一块，一个 `free` 后另一个仍被当有效使用 → 既可能 double free，也可能泄漏。
6. **容器/链表删除节点只摘链不释放**。

**统一解法**：**单一出口 + 所有权约定**。

```c
int f(void) {
    char *buf = NULL;
    int rc = -1;
    buf = malloc(1024);
    if (!buf) goto cleanup;
    if (some_error()) goto cleanup;
    rc = 0;
cleanup:
    free(buf);
    return rc;
}
```

## 三、碎片

- **外部碎片**：空闲总量够但不连续，大请求失败。
- **内部碎片**：元数据 + 对齐造成的浪费。

**工程对策**：内存池、对象复用、避免大小混合的频繁分配。

## 四、调试工具

| 工具 | 能发现 | 用法 |
|---|---|---|
| **ASan**（AddressSanitizer） | 越界、use-after-free、double free、泄漏 | `gcc -fsanitize=address,undefined -g` |
| **UBSan** | 未定义行为（溢出、对齐、空指针解引用） | 同上（`undefined`） |
| **valgrind** | 泄漏、未初始化读、越界 | `valgrind --leak-check=full ./prog` |
| **`-fstack-protector-all`** | 栈溢出破坏返回地址 | 编译选项 |

**CI 实践**：把 ASan 构建作为一个**必过的 job**——它把「偶发的 UB」变成「稳定可复现的报错」，是 C 项目质量的关键闸门。

**注意**：ASan 会显著增加内存与时间开销，**只用于测试构建**，不用于发布。

## 五、内存池（pool allocator）

**动机**：频繁 `malloc/free` 小对象 → 分配器开销大 + 外部碎片严重。

**做法**：一次性向系统申请一大块，自己按固定尺寸切成等长槽位，用**空闲链表**管理：

```c
typedef struct Block { struct Block *next; } Block;

typedef struct {
    Block  *free_list;
    void   *slab;
    size_t  block_size, capacity, used;
} Pool;

void *pool_alloc(Pool *p) {
    if (!p->free_list) return NULL;      /* 简版：不自动扩容 */
    Block *b = p->free_list;
    p->free_list = b->next;
    p->used++;
    return b;
}

void pool_free(Pool *p, void *ptr) {
    Block *b = (Block *)ptr;
    b->next = p->free_list;
    p->free_list = b;
    p->used--;
}
```

**收益**：分配/释放变成 O(1) 链表操作；无外部碎片；批量释放（整个 slab 一次 `free`）极大简化生命周期管理。

**代价**：只适合**固定尺寸**对象；需要自己处理扩容；释放必须归还到**原池**。

**真实应用**：Linux 内核 slab 分配器、Nginx 内存池、游戏引擎对象池。

## 六、C 的替代方案（面试加分）

- **栈分配**：能不放堆就不放堆。
- **C99 变长数组（VLA）**：`int a[n];` 运行时确定大小，但栈容量有限且 C11 起为可选特性，慎用。
- **`alloca`**：栈上分配，函数返回自动回收——但**不可移植**且大块会栈溢出。
- 真正的解法往往是**迁移到带所有权机制的抽象**（C++ RAII / 智能指针，或 Rust 借用检查）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 工具链标配：**AddressSanitizer（`-fsanitize=address`）** 开发期强制开启，valgrind 用于无法重编译的场景；两者都能定位泄漏与越界。
- 原则：**谁分配谁释放**，并把释放点与分配点写在同一个人能看到的代码范围内；跨模块传递所有权必须有明确约定（文档化）。
- 高频小对象（如链表节点）用**内存池**：一次申请大块、自己切分复用，能把分配开销降一个量级。

### 🎓 博士生视角
- 泄漏的准确定义是「**对象已不可达但未被释放**」——可达性是判断依据，而不是「有没有 free」。
- 有引用计数的语言（CPython、Swift）把「可达性丢失」自动化为引用归零；有 GC 的语言（Java、Go）用追踪算法处理循环引用。C 没有这些机制，只能靠约定 + 工具。
- 内存池（空闲链表复用槽位）本质是**把分配器的工作下沉到应用层**：用「固定尺寸 + 一次性申请」换「无碎片 + O(1) 分配」，代价是尺寸单一与手工管理。
- 另一种视角是**分配器与调试器的信息不对称**：分配器只知地址与大小，调试器需要回溯调用栈，因此 ASan 用影子内存（shadow memory）记录每个字节的可访问状态。

### 📚 考研者视角
- 与 408 的**动态存储管理**（空闲链表、分配算法、内存回收）直接对应，属于自命题数据结构的模拟题素材。
- 常考概念题：「内存泄漏与内存溢出的区别」（前者是未释放累积、后者是地址空间/栈空间耗尽）。
- 记忆锚点：**ASan / valgrind 是 C 程序员标配**；**「谁分配谁释放」**。
