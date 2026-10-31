# 一、缓存穿透：查不到的数据把压力打到数据库
> 缓存三大经典问题本质是「查不到时往哪去、什么时候失效」：穿透是查不存在的 key 直击库，击穿是热点 key 突失效瞬间被打穿，雪崩是大量 key 同时过期把库冲垮。解法分别是空值/布隆、单飞/逻辑过期、错峰 TTL。

```text
① 缓存穿透：查 db 也没有的 key → 每次都打到库
   解：缓存空值(null,短时TTL) + 布隆过滤器挡非法 key

② 缓存击穿：某个热点 key 突然过期 → 瞬间大量请求穿透过载
   解：互斥单飞(只放1个去查库) + 逻辑过期(异步重建不阻塞)

③ 缓存雪崩：大量 key 同一时刻过期 / Redis 宕机 → 库被冲垮
   解：TTL 加随机抖动错峰 + 多级缓存 + 高可用(集群)

读路径： 请求 → Cache 命中? 返回 : 查 DB → 写回 Cache → 返回
写路径： 更新 DB → 删 Cache(或双删) → 防脏读
```


本文件覆盖两个核心主题：**① 布隆过滤器（bit 数组 + 多哈希 + 误判率）** 与 **② 空值缓存兜底**。二者是缓存穿透（查询根本不存在的 key，缓存与 DB 都没有，请求每次穿透到 DB）的两条主流防线。

---

## ① 布隆过滤器：用极少空间做「存在性」拦截

（中立陈述）布隆过滤器是一个长度为 `m` 的 bit 数组，配 `k` 个独立哈希函数。写入元素时，对元素算 `k` 个哈希，把对应 `k` 个 bit 置 1；查询元素时同样算 `k` 个 bit，若**全为 1** 则「可能存在」，只要**有一个为 0** 则「一定不存在」。它不存原值，空间极小，但存在假阳性（误判为存在）。见 `examples/ex01_bloom_filter_basic.json`、`ex02_penetration_bloom.json`。

### 🧑‍💻 程序员视角
- **上线第一道闸**：在缓存之前放一个布隆过滤器（如 RedisBloom / 自研 bit 数组）。对「一定不存在」的 key 直接返回，DB 完全不感知，能把穿透流量拦掉 99%+；对「可能存在」的 key 才放行去查缓存 / DB。
- **容量要算**：误判率 `p ≈ (1 - e^{-kn/m})^k`，给定可接受误判率 `p` 与目标元素数 `n`，反推 `m = -n·ln(p) / (ln2)²`、`k = m/n·ln2`。比如 n=1e8、p=1e-4 约需 23 bit/元素、k≈13。
- **不能删元素**：标准布隆不支持删除（一个 bit 被多个元素共享，清零会误伤别人）。要支持删除用 Counting Bloom Filter（bit 换计数器），否则删除只能重建整个过滤器。
- **误判要有兜底**：放行的「可能存在」里仍有少量假阳性，业务上对空结果要能正常处理（返回「无数据」而非崩溃）。

### 🎓 博士生视角
- **为什么不可能零误判**：bit 数组有限，随着元素数 `n` 增大，bit 被置 1 的比例趋近 `1 - e^{-kn/m}`；而「查询未插入元素却被判定存在」的概率正是剩余 0 位全被别的元素占满的概率，即 `(1 - e^{-kn/m})^k`——这是**空间换确定性的本质代价**，不存在「压缩到 0 误判且空间不变」的方案。
- **多哈希的 Kirsch–Mitzenmacher 技巧**：用两个基础哈希 `h1, h2` 线性组合 `g_i = h1 + i·h2 (mod m)` 生成 `k` 个哈希，既近似独立又只需算两次哈希，降低计算成本；`k` 存在**最优值**使误判率最小，偏离（过多哈希）反而因 bit 被更快填满而升高误判。
- **与完美哈希 / 集合的区别**：布隆是「概率型成员测试」，以「允许假阳性、杜绝假阴性」换取 O(1) 查询与 O(m) 空间（远小于存原集合的 O(n·|x|)）；它对「一定不存在」是**绝对正确**的，这是它能做穿透拦截的理论基础。

### 📚 考研者视角（笔面考点）
- **标准问法**：「什么是缓存穿透？怎么解决？布隆过滤器为什么会有误判？」答：穿透 = 查不存在的 key，缓存与 DB 皆无，请求每次打到 DB；解决 = 布隆过滤器拦截 + 空值缓存；布隆过滤器把元素映射到 bit 数组，查询全 1 才「可能存在」，有 0 即「一定不存在」，故只能消除假阴性、存在假阳性。
- **常考计算**：给出 `m, k, n` 估算误判率 `(1 - e^{-kn/m})^k`；或反推给定 `p, n` 所需 `m` 与最优 `k`。记清「误判率随 m 增大、随 n 增大而升高」。
- **易混点**：布隆过滤器「判断不存在一定对、判断存在可能错」——别把它当精确数据结构；「支持删除」是计数布隆的事，标准布隆不支持。

---

## ② 空值缓存：把「查无此物」也写进缓存

（中立陈述）当查询的 key 在 DB 中确实不存在时，把「空结果（null / 特殊标记）」也按较短 TTL 写入缓存。这样同一 key 的重复穿透请求在 TTL 内直接命中空值缓存、不再查 DB。它常与布隆过滤器组合：布隆拦掉「结构性不存在」，空值缓存兜住「偶发不存在」。

### 🧑‍💻 程序员视角
- **短 TTL 防污染**：空值缓存的 TTL 要明显短于正常数据（如 1~5 分钟），避免「DB 后来写入了该 key」却长期读到旧空值；同时给空值一个特殊标记（而非真的 null）便于与「未命中」区分。
- **防滥用**：攻击者若用大量**不同**的非法 key 打空值缓存，会把缓存写满（缓存污染 / 击穿另一种形式）。此时需配合布隆过滤器（非法 key 根本不进缓存）或限流、key 合法性校验。
- **组合拳**：生产实践 = 布隆过滤器（前置拦截明确不存在的 key）+ 空值缓存（兜底偶发 miss）+ 限流，三层防穿透。

### 🎓 博士生视角
- **空间 / 正确性权衡**：空值缓存把「不存在」也变成缓存条目，换取 DB 的零穿透，但牺牲了缓存空间与「写入后短期不可见」的一致性窗口；其本质是**用时间局部性假设**——同一非法 key 会被短期内重复访问。
- **与布隆的互补边界**：布隆过滤器的假阳性会把「不存在的 key」误放行到空值缓存（无害，只是多写一条空值）；而真正的「存在 key 被布隆误判为不存在」概率为 0，不会漏拦。二者组合后系统的「漏拦率 = 0」、「误拦率 = 布隆假阳性率」。
- **一致性窗口的形式化**：设空值 TTL = `t_null`，则在 `t_null` 内对该 key 的 DB 写入对读方不可见；该窗口是设计参数，要在「防穿透强度」与「写后可见延迟」间取折中。

### 📚 考研者视角（笔面考点）
- **标准问法**：「缓存穿透除了布隆过滤器还有什么办法？」答：空值缓存（null caching）——查 DB 为空也写缓存并设短 TTL；以及接口层校验 / 限流。
- **常考对比**：布隆过滤器 vs 空值缓存——前者不存原值、空间极小、有假阳性、不能删；后者存空结果、有空间成本、有「写后短期不可见」窗口、需短 TTL 防污染。
- **易错口径**：空值缓存若 TTL 过长会「缓存了不存在」，导致刚写入的合法数据短期读不到；别把空值 TTL 设得和正常数据一样长。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### 布隆过滤器：bit 数组与多哈希的基本判定

```python
import zlib

class BloomFilter:
    """m 个 bit、k 个哈希的布隆过滤器。"""
    def __init__(self, m_bits, k):
        self.m = m_bits
        self.k = k
        self.bits = bytearray((m_bits + 7) // 8)

    def _positions(self, key):
        b = key.encode("utf-8") if isinstance(key, str) else bytes(key)
        pos = []
        for i in range(self.k):
            # 用 crc32 派生 k 个确定性哈希（内置 hash() 受 PYTHONHASHSEED 影响，不可复现）
            h = zlib.crc32(b + bytes([i]))
            pos.append(h % self.m)
        return pos

    def add(self, key):
        for p in self._positions(key):
            self.bits[p // 8] |= (1 << (p % 8))

    def contains(self, key):
        return all(self.bits[p // 8] & (1 << (p % 8)) for p in self._positions(key))

    def bits_set(self):
        return sum(bin(byte).count("1") for byte in self.bits)


bf = BloomFilter(m_bits=512, k=3)
data = ["user:1", "user:2", "user:3", "user:4", "user:5"]
for d in data:
    bf.add(d)

print("参数: m=%d bits, k=%d" % (bf.m, bf.k))
print("插入元素数: %d" % len(data))
print("被置位的 bit 数: %d / %d" % (bf.bits_set(), bf.m))

print("--- 已插入元素的查询（必须全部为 True，布隆无假阴性）---")
for d in data:
    print("contains(%s) = %s" % (d, bf.contains(d)))

print("--- 未插入元素的查询（False=一定不存在；True=假阳性）---")
for d in ["user:100", "user:200", "user:300", "user:400", "user:500"]:
    print("contains(%s) = %s" % (d, bf.contains(d)))

probes = ["user:%d" % i for i in range(1000, 1100)]
fp = sum(1 for d in probes if bf.contains(d))
print("用 100 个未插入元素测误判: 误判 %d 次" % fp)
print("结论: 判定 False 一定不存在（无假阴性），判定 True 只是可能存在（有假阳性）")
```

实际输出：

```text
参数: m=512 bits, k=3
插入元素数: 5
被置位的 bit 数: 15 / 512
--- 已插入元素的查询（必须全部为 True，布隆无假阴性）---
contains(user:1) = True
contains(user:2) = True
contains(user:3) = True
contains(user:4) = True
contains(user:5) = True
--- 未插入元素的查询（False=一定不存在；True=假阳性）---
contains(user:100) = False
contains(user:200) = False
contains(user:300) = False
contains(user:400) = False
contains(user:500) = False
用 100 个未插入元素测误判: 误判 5 次
结论: 判定 False 一定不存在（无假阴性），判定 True 只是可能存在（有假阳性）
```

> 出处：`examples/ex01-bloom-basic.json`。改一处再看输出变没变，比读三遍解释有用。

### 布隆过滤器误判率：理论公式与实测对比

```python
import math, zlib

class BloomFilter:
    def __init__(self, m_bits, k):
        self.m = m_bits
        self.k = k
        self.bits = bytearray((m_bits + 7) // 8)

    def _positions(self, key):
        b = key.encode("utf-8")
        return [zlib.crc32(b + bytes([i])) % self.m for i in range(self.k)]

    def add(self, key):
        for p in self._positions(key):
            self.bits[p // 8] |= (1 << (p % 8))

    def contains(self, key):
        return all(self.bits[p // 8] & (1 << (p % 8)) for p in self._positions(key))


def theory_fpr(m, n, k):
    return (1.0 - math.exp(-k * n / m)) ** k


def k_opt(m, n):
    return max(1, int(round((m / n) * math.log(2))))


n = 1000
for m in [5000, 10000, 20000]:
    k = k_opt(m, n)
    bf = BloomFilter(m, k)
    inserted = ["key-%d" % i for i in range(n)]
    for x in inserted:
        bf.add(x)
    probes = ["probe-%d" % i for i in range(2000)]
    fp = sum(1 for x in probes if bf.contains(x))
    rate = fp / len(probes)
    print("m=%6d bits, n=%d, k_opt=%d -> 理论 %.4f, 实测 %.4f (%d/%d)"
          % (m, n, k, theory_fpr(m, n, k), rate, fp, len(probes)))

print("--- 固定 m/n=10 时，k 对误判率的影响（k 不是越大越好）---")
m = 10000
bf0 = BloomFilter(m, 3)
for i in range(n):
    bf0.add("key-%d" % i)
for k in range(1, 9):
    bf = BloomFilter(m, k)
    for i in range(n):
        bf.add("key-%d" % i)
    fp = sum(1 for x in ["probe-%d" % i for i in range(2000)] if bf.contains(x))
    print("k=%d -> 理论 %.4f, 实测 %.4f" % (k, theory_fpr(m, n, k), fp / 2000))
print("最优 k = (m/n)*ln2 = %d" % k_opt(m, n))
```

实际输出：

```text
m=  5000 bits, n=1000, k_opt=3 -> 理论 0.0918, 实测 0.1020 (204/2000)
m= 10000 bits, n=1000, k_opt=7 -> 理论 0.0082, 实测 0.0110 (22/2000)
m= 20000 bits, n=1000, k_opt=14 -> 理论 0.0001, 实测 0.0000 (0/2000)
--- 固定 m/n=10 时，k 对误判率的影响（k 不是越大越好）---
k=1 -> 理论 0.0952, 实测 0.0840
k=2 -> 理论 0.0329, 实测 0.0300
k=3 -> 理论 0.0174, 实测 0.0235
k=4 -> 理论 0.0118, 实测 0.0125
k=5 -> 理论 0.0094, 实测 0.0135
k=6 -> 理论 0.0084, 实测 0.0125
k=7 -> 理论 0.0082, 实测 0.0110
k=8 -> 理论 0.0085, 实测 0.0105
最优 k = (m/n)*ln2 = 7
```

> 出处：`examples/ex02-bloom-false-positive-rate.json`。改一处再看输出变没变，比读三遍解释有用。

