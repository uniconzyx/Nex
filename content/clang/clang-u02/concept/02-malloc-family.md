# malloc / calloc / realloc / free 的契约

## 一、四个函数的语义

| 函数 | 是否清零 | 说明 |
|---|---|---|
| `void *malloc(size_t n)` | ❌ **不清零**（内容是脏数据） | 申请 n 字节 |
| `void *calloc(size_t k, size_t n)` | ✅ **清零** | 申请 k×n 字节并全零；会检查乘法溢出 |
| `void *realloc(void *p, size_t n)` | 新扩展部分不清零 | 调整已有块大小，返回**新地址** |
| `void free(void *p)` | — | 归还内存；`free(NULL)` 是**空操作** |

```c
int *a = malloc(10 * sizeof(int));   /* 内容不确定 */
if (!a) { /* 必须判空 */ }
int *b = calloc(10, sizeof(int));    /* 10 个 0 */
```

**选择建议**：需要「初始为 0」的语义就用 `calloc`——它同时避免「读到脏数据」的隐蔽 bug，且现代实现对该路径有优化。

## 二、`realloc` 的正确写法（高频考点）

`realloc` 可能**原地扩展**，也可能**分配新块 + 拷贝 + 释放旧块**，所以它返回的是**新地址**，旧指针可能失效。

```c
/* ❌ 错误：一旦 realloc 失败返回 NULL，原指针 p 被覆盖 → 内存泄漏 */
p = realloc(p, new_n);

/* ✅ 正确：用临时变量接，成功后再赋值 */
void *tmp = realloc(p, new_n);
if (!tmp) {
    /* 原 p 仍然有效，需自行释放或向上抛错 */
    free(p);
    return NULL;
}
p = tmp;
```

**另外两点**：

- `realloc(p, 0)` 的行为是实现定义（C23 已明确为「释放并返回 NULL」的等价），不要依赖。
- `realloc(NULL, n)` **等价于 `malloc(n)`**。

## 三、`free` 的契约与陷阱

**契约**：传给 `free` 的必须是 `malloc`/`calloc`/`realloc` 返回的**原始地址**（不能是偏移后的指针，也不能是栈/全局地址）。分配器靠「返回地址 - 头部偏移」找回元数据，传错地址会破坏堆。

**为什么 `free` 后指针值不变**：

```c
int *p = malloc(sizeof(int));
free(p);        /* p 的值（地址）不变，仍指向该块 —— 但块已归还 */
/* *p = 5;      /* use-after-free，UB */
p = NULL;       /* 规范做法：free 后立即置空 */
```

- `free(NULL)` 是**安全空操作**，这正是「释放后置 NULL」这一习惯可靠的原因。
- **double free**（重复释放同一块）会破坏分配器元数据 → 崩溃或被利用。置 NULL 后重复 `free(NULL)` 无害，能挡住这一整类 bug。

## 四、`malloc` 失败的处理

**必须判空**——但难点在于「判空之后做什么」：

```c
int *a = malloc(n * sizeof(int));
if (!a) {
    fprintf(stderr, "out of memory\n");
    return NULL;        /* 向上传播，不要继续用 a */
}
```

**注意乘法溢出**（安全向考点）：

```c
size_t count = user_input;
int *a = malloc(count * sizeof(int));   /* ❌ count 极大时乘法溢出 → 分配过小 → 堆溢出 */
```

正解之一是用 `calloc`（自带溢出检查），或显式检查：

```c
if (count > SIZE_MAX / sizeof(int)) return NULL;
```

## 五、`malloc(0)` 与对齐

- `malloc(0)` 返回**实现定义**：可能 `NULL`，也可能返回一个可 `free` 的最小块。不要依赖。
- `malloc` 返回的地址**满足 `max_align_t` 对齐**（通常 16 字节），可直接存放任何基本类型与大多数结构体——这是可以安全转型为任意对象指针的前提。

## 六、C 中不需要强转

```c
int *a = malloc(n * sizeof(int));     /* C：无需 (int*) 强转 */
```

C 中 `void*` 可隐式转换为任意对象指针。**C++ 中则必须强转**（C++ 不允许 `void*` 隐式转 `T*`）。所以看到「C 代码里到处写 `(int*)malloc(...)`」，通常是 C++ 程序员写的 C 代码。

---

## 三视角解析

### 🧑‍💻 程序员视角
- `malloc` 返回值**必须判 NULL**；`calloc` 会清零而 `malloc` 不会（这是二者最实际的差别）。
- `realloc` 必须用**临时变量接返回值**：失败时返回 NULL 而原指针仍有效，直接覆盖原指针就泄漏了。
- `free(NULL)` 是合法且无操作的；`free` 后置指针为 NULL，能防住重复释放的大部分场景。

### 🎓 博士生视角
- 分配器要为每块内存保存**元数据**（如 glibc 的 chunk header 存 size 与标志位），所以 `malloc(1)` 实际占用的远不止 1 字节（对齐到 `max_align_t`，通常 16 字节，加头部常在 32 字节量级）。
- `realloc` 可能原地扩展（后面的空闲块够大）也可能**搬移到新地址**并复制内容——因此任何指向旧块的指针都会悬垂。
- glibc 在小请求时用 `brk` 扩展堆、在大请求（超过 `M_MMAP_THRESHOLD`，默认约 128KB）时直接用 `mmap`；前者延迟归还、后者立即归还。
- **`free` 之后进程 RSS 通常不下降是正常现象**：内存被分配器缓存以备复用，它不是泄漏。判断泄漏要看「长期趋势」而不是「释放后是否立刻归还」。

### 📚 考研者视角
- **408 数据结构交叉**：动态存储管理、**空闲链表**、首次适配/最佳适配/最差适配算法的模拟计算（给出空闲分区表与分配序列，求分配结果与剩余分区）。
- 常考概念题：「`malloc` 与 `new` 的区别」「`calloc` 与 `malloc` 的区别」「内存泄漏的原因与检测」。
- 记忆锚点：**`malloc` 不清零、`calloc` 清零**；**`realloc` 用临时变量接**。
