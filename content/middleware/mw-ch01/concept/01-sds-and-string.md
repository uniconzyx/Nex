# 一、SDS 与 String 对象编码

本文件覆盖两个核心主题：**① SDS 动态字符串** 与 **② String 对象的三种编码（int / embstr / raw）**。

---

## ① SDS：Redis 的二进制安全字符串

（中立陈述）Redis 没有直接用 C 原生 `\0` 结尾字符串存 key 和 value，而是定义了 `sdshdr` 结构：除字节数组 `buf` 外，额外维护 `len`（已用长度）、`alloc`（已分配容量），并用 `flags` 区分不同头部长度（`sdshdr5/8/16/32/64`）。读取长度、`\0` 结尾保留仅为复用 C 库函数，长度由 `len` 决定而非扫描。

### 🧑‍💻 程序员视角
- **不要用 `strlen` 思维**：拿到 Redis 字符串，取长度永远 `O(1)`；在客户端拼大 value 时无需担心长度计算开销，但**预分配**意味着你 `APPEND` 一个 1KB 字符串到 1MB 后，它可能实际占用 2MB（`len` 翻倍策略），`STRLEN` 看不出真实内存。
- **二进制安全是硬需求**：头像、序列化 protobuf、图片 bits 都能塞进 value；若你用 `GET` 后按 C 字符串 `strlen` 截断处理，会丢数据——必须按 `len` 解析。
- **踩坑**：把含 `\0` 的内容当文本 `printf` 会提前截断；线上排查 `DEBUG OBJECT` 看到 `serializedlength` 与 `STRLEN` 差异时，通常是多字节/二进制内容。

### 🎓 博士生视角
- **内存布局**：`sdshdr8` 为 `{ uint8_t len; uint8_t alloc; uint8_t flags; char buf[]; }`，`flags` 末 3 位编码类型，使小字符串头部仅 3 字节开销；大字符串用 `sdshdr64`，避免浪费。
- **空间预分配**：`len < 1MB` 时 `alloc = len*2`；`>=1MB` 时每次仅多给 1MB。这是**用内存换摊销 O(1) 追加**——证明：n 次追加总拷贝量从 `O(n²)` 降到 `O(n)`。
- **惰性释放**：`SDSCLEAR` 只把 `len` 置 0 不回收 `alloc`，下次复用；与 C++ `std::string` 的 `capacity` 思路同源，但显式分离 `len/free` 让 `free` 可被 `sdsavail` 直接读取。

### 📚 考研者视角（笔面考点）
- **标准问法**：「Redis 的 SDS 相比 C 字符串有什么优点？」标准答四点：① 获取长度 `O(1)`；② 二进制安全；③ 杜绝缓冲区溢出（先查 `alloc`）；④ 减少修改时的内存重分配次数（预分配 + 惰性释放）。
- **易错口径**：不要说「SDS 以 `\0` 结尾所以二进制安全」——恰恰相反，`\0` 结尾是兼容 C 函数的副产物，二进制安全来自 `len` 字段；考试写反会扣分。
- **计算题口径**：给定追加序列，问内存重分配次数或最终 `alloc`，按「翻倍上限 1MB、超出每次 +1MB」规则算。

---

## ② String 对象的三种编码

（中立陈述）Redis 的 `String` 对象 value 按内容选择编码：`long` 可表示的整数字面量 → `OBJ_ENCODING_INT`；长度 ≤44 字节的非整数短串 → `OBJ_ENCODING_EMBSTR`（对象头与 `buf` 一次性分配）；其余 → `OBJ_ENCODING_RAW`（对象头与 `buf` 两次分配）。阈值 44 来自 `OBJ_ENCODING_EMBSTR_SIZE_LIMIT`。

### 🧑‍💻 程序员视角
- **embstr 不可原地修改**：它被设计为只读紧凑结构，任何 `APPEND`/`INCR` 会先转成 `RAW` 再改；高频 `INCR` 小整数计数器虽是整数编码（`INT`），但注意 `INCR` 超限会变回字符串。
- **容量判断**：大 value（如几 MB 的 JSON）必然是 `RAW`，多一次内存分配；若业务是「读多写少的短串」，embstr 对 CPU 缓存更友好。
- **踩坑**：用 `SET` 存一个 45 字节字符串，再 `OBJECT ENCODING` 看会从 embstr 变 raw，别误以为「字符串变长会原地扩容」。

### 🎓 博士生视角
- **为什么是 44 字节**：`redisObject` 占 16 字节（4B type+encoding+refcount+lru + 8B ptr），jemalloc 最小分配粒度 64B；`64 - 16(robj) - 3(sdshdr8) - 1(\0) = 44`，刚好让「对象头 + sds 头 + 数据 + \0」落在单块 64B 内，一次分配、缓存友好。
- **INT 编码复用 ptr**：当值是 `long`，Redis 把数值直接塞进 `redisObject.ptr` 而不是另开 `buf`，省一次分配；超 `long` 范围（如超长数字串）则按字符串处理。
- **编码转换不回退**：embstr→raw 是单向；INT→RAW 发生在 `APPEND` 等改变类型操作时，体现「紧凑优先、按写放大升级」。

### 📚 考研者视角（笔面考点）
- **标准问法**：「为什么 Redis 的字符串有 embstr 和 raw 两种，分界是多少？」答：44 字节，源于 64B jemalloc 块减去 robj(16)+sdshdr8(3)+\0(1)。
- **易错口径**：`embstr` 是**一次性内存分配**且**只读**，不是「分配两次但因为小所以快」——这是高频错误表述；改 embstr 会触发转 raw。
- **连问**：`SET k 123` 后 `OBJECT ENCODING k` 是什么？答 `int`；`APPEND k "x"` 后呢？答 `raw`（先转 raw 再追加）。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### SDS 动态字符串：长度前缀、预分配与二进制安全

```python
class SDS:
    def __init__(self, s):
        self.buf = bytearray(s.encode("utf-8", "surrogatepass"))
        self.len = len(self.buf)
        self.alloc = self.len
    def _ensure(self, need):
        if self.alloc >= need:
            return
        if self.len < 1024 * 1024:
            newalloc = need * 2
        else:
            newalloc = self.alloc + 1024 * 1024
        if newalloc < need:
            newalloc = need
        self.alloc = newalloc
    def append(self, s):
        b = s.encode("utf-8", "surrogatepass")
        self._ensure(self.len + len(b))
        self.buf.extend(b)
        self.len = len(self.buf)
    def __repr__(self):
        return "len=%d alloc=%d free=%d bytes=%s" % (self.len, self.alloc, self.alloc - self.len, list(self.buf))

s = SDS("hi")
print("init:", s)
s.append("A")          # len 2 -> need 3 (<1MB) -> alloc = 6
print("after append 'A':", s)
s.append("B" * 10)
print("after append 10B:", s)
s2 = SDS("a\x00b")     # 含 NUL，二进制安全
print("binary-safe len (should be 3):", s2.len)
print("c-string strlen would be:", len(s2.buf.split(b"\x00")[0]))
```

实际输出：

```text
init: len=2 alloc=2 free=0 bytes=[104, 105]
after append 'A': len=3 alloc=6 free=3 bytes=[104, 105, 65]
after append 10B: len=13 alloc=26 free=13 bytes=[104, 105, 65, 66, 66, 66, 66, 66, 66, 66, 66, 66, 66]
binary-safe len (should be 3): 3
c-string strlen would be: 1
```

> 出处：`examples/ex01_sds_dynamic_string.json`。改一处再看输出变没变，比读三遍解释有用。

### dict 渐进式 rehash：双表 + rehashidx 逐步搬迁

```python
import zlib

class Dict:
    def __init__(self, size=4):
        self.ht = [[[] for _ in range(size)], None]
        self.rehashidx = -1
        self.count = 0
    def _idx(self, table, key):
        return zlib.crc32(key.encode()) & (len(table) - 1)   # 确定性哈希（str 哈希带随机种子）
    def _put(self, table, key, val):
        i = self._idx(table, key)
        for pair in table[i]:
            if pair[0] == key:
                pair[1] = val
                return
        table[i].append([key, val])
    def _get(self, table, key):
        if table is None:
            return None
        i = self._idx(table, key)
        for k, v in table[i]:
            if k == key:
                return v
        return None
    def _move_one(self):
        if self.rehashidx < 0:
            return False
        while self.rehashidx < len(self.ht[0]) and not self.ht[0][self.rehashidx]:
            self.rehashidx += 1
        if self.rehashidx >= len(self.ht[0]):
            self.ht[0] = self.ht[1]; self.ht[1] = None; self.rehashidx = -1
            return False
        for pair in self.ht[0][self.rehashidx]:
            self._put(self.ht[1], pair[0], pair[1])
        self.ht[0][self.rehashidx] = []
        self.rehashidx += 1
        return True
    def put(self, key, val):
        if self.rehashidx >= 0:
            self._put(self.ht[1], key, val); self.count += 1; self._move_one(); return
        used = sum(len(b) for b in self.ht[0])
        if used / len(self.ht[0]) >= 1.0:
            self.ht[1] = [[] for _ in range(len(self.ht[0]) * 2)]
            self.rehashidx = 0
            self._put(self.ht[1], key, val); self.count += 1; self._move_one(); return
        self._put(self.ht[0], key, val); self.count += 1
    def get(self, key):
        v = self._get(self.ht[0], key)
        return v if v is not None else self._get(self.ht[1], key)

d = Dict(4)
for k in ["a", "b", "c", "d", "e", "f"]:
    d.put(k, 1)
print("after 6 inserts: count=%d ht0_buckets=%d ht1=%s rehashidx=%d" % (
    d.count, len(d.ht[0]), "present" if d.ht[1] is not None else "None", d.rehashidx))
steps = 0
while d.rehashidx >= 0:
    d._move_one(); steps += 1
print("rehash drained in %d more steps; ht0_buckets=%d ht1=%s" % (
    steps, len(d.ht[0]), "None" if d.ht[1] is None else "present"))
print("get 'c' =>", d.get("c"), " get 'f' =>", d.get("f"))
```

实际输出：

```text
after 6 inserts: count=6 ht0_buckets=4 ht1=present rehashidx=2
rehash drained in 2 more steps; ht0_buckets=8 ht1=None
get 'c' => 1  get 'f' => 1
```

> 出处：`examples/ex02_dict_incremental_rehash.json`。改一处再看输出变没变，比读三遍解释有用。

