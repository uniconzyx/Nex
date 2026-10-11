# 03 · 无序容器 unordered_*：哈希表、冲突与负载因子

## 一、理论根基：用「哈希」换平均 O(1)

当需要**纯按 key 点查、不关心顺序**时，红黑树的 O(log n) 仍不够快。理想是「像数组下标」一样 O(1) 访问——**哈希表（hash table）** 正是为此：把任意 key 经哈希函数映射到整数桶下标 `bucket = hash(key) % bucket_count`，直接定位。

`std::unordered_map` / `std::unordered_set` / `unordered_multimap` / `unordered_multiset` 即 C++ 的标准无序关联容器。它们的 `key` 无序，迭代器是**前向迭代器**（不能 `--it`、不能随机访问）。

## 二、实现机制：桶数组 + 链地址法（Separate Chaining）

libstdc++/libc++ 的实现采用**开链法（链式寻址）**：一个**桶数组 `bucket[]`**，每个桶挂着一条**单向链表**（libstdc++ 早期为链表，现代用「桶内节点 + 桶间桶数组」结构，但逻辑仍是链地址）。插入/查找流程：

1. `h = hash(key); b = h % bucket_count;` 定位桶。
2. 在桶 `b` 的链表里线性比对 `key`（用 `key_equal` 判等）。
3. 找到→命中；没找到→插入（map/set）或返回 `end()`。

> 对比开放寻址（线性探测/二次探测/双重哈希）：所有元素直接存在桶数组里，冲突时探测下一个空位。C++ 标准**未规定**必须用哪种，但主流 STL 都用链地址法——它对「删除」更友好、对缓存稍差（节点散落堆上）。

## 三、实现机制：负载因子与再哈希（rehash）

**负载因子 `load_factor = size() / bucket_count()`**，衡量「每个桶平均挂多少元素」。它决定了冲突概率与查询代价：

- 平均情况：每个桶约 `load_factor` 个元素，**平均查找 O(1 + load_factor)**。当 `load_factor` 保持常数，`size` 增长时 `bucket_count` 同步增长，平均操作仍是 **O(1)**。
- 最坏情况：若哈希函数把**所有 key 映射到同一桶**（或恶意构造碰撞），退化为**链表 O(n)**。这就是为什么「哈希质量」至关重要。

为维护平均 O(1)，容器设有阈值 **`max_load_factor`**（默认 1.0，libstdc++ 实际约为 1.0；有的实现默认 0.75/1.0）。当插入后 `load_factor > max_load_factor`，触发 **rehash**：
1. 把 `bucket_count` 增到下一个质数（libstdc++ 用一张质数表，约 2× 步进）；
2. **把全部已有元素重新哈希、重新挂桶**。

> rehash 的代价是 **O(n)** 一次性搬运，但均摊到每次插入仍是 O(1)；代价是——**rehash 会使所有迭代器失效**（指针/引用仍有效，因为元素对象本身没搬，只是桶链表重排）。这与 `vector` 扩容「元素都搬走、引用也失效」不同，务必区分（见 pitfalls）。

## 四、工程实践：怎么用好 unordered_*

1. **提供高质量哈希**：内置类型（`int`/`string` 等）已有效果良好的 `std::hash`。自定义 key 类型必须特化 `std::hash<YourKey>` 或提供哈希函数对象，且 `hash` 与 `key_equal` 必须**一致**（相等的 key 必须哈希到相同值）。
2. **预分配桶数**：已知元素规模时 `reserve(n)`（它按 `n / max_load_factor` 估算桶数），避免反复 rehash。注意 `reserve` 改的是桶数层面，不保证 `size`。
3. **`find`/`count`/`contains` 不插入**；只有 `operator[]`/`at` 有插入语义（`[]` 同 `map` 会值初始化插入）。
4. **对抗哈希碰撞/DoS**：若 key 来自不可信输入（如用户字符串），使用**带随机盐的哈希**（C++ 标准允许实现为 `std::hash` 加盐以抵御 Hash DoS；某些实现默认开启）。

## 五、边界与陷阱

- **哈希质量决定最坏复杂度**：设计一个「所有 key 同余」的哈希函数会让查询退化为 O(n)；面试官常问「为什么 unordered_map 最坏 O(n)」。
- **rehash 使迭代器失效，但引用/指针有效**：这是与 `map`/`vector` 不同的微妙点。
- `bucket_count` 是质数表跳跃增长，不要假设「恰好 2×」；`load_factor` 默认约 1.0，想更稀疏可 `max_load_factor(0.5)` 换缓存友好。
- 自定义类型做 key：必须同时提供相等比较（`==` 或 `key_equal`），否则插入/查找逻辑错乱。
- 遍历 `unordered_*` 的**顺序不可预期**（依赖桶布局），测试不要依赖顺序。

## 六、可运行示例：频次统计 + rehash 观察

```cpp
#include <iostream>
#include <unordered_map>
#include <string>

int main() {
    std::unordered_map<std::string, int> freq;
    std::cout << "init: buckets=" << freq.bucket_count()
              << " load=" << freq.load_factor() << '\n';
    for (std::string w : {"a","b","c","a","b","a","d","e","f","g","h"})
        freq[w]++;                       // operator[] 插入/累加
    std::cout << "after 11 inserts: size=" << freq.size()
              << " buckets=" << freq.bucket_count()
              << " load=" << freq.load_factor() << '\n';

    // 频次统计结果（顺序不可预期）
    int a = freq["a"];
    std::cout << "freq[\"a\"]=" << a << '\n';

    // rehash 显式触发
    freq.reserve(1000);
    std::cout << "after reserve(1000): buckets=" << freq.bucket_count()
              << " load=" << freq.load_factor() << '\n';
}
```

**输出**（桶数随实现/质数表略有差异，示意）：
```
init: buckets=1 load=0
after 11 inserts: size=8 buckets=11 load=0.727273
freq["a"]=3
after reserve(1000): buckets=1021 load=0.007836
```

> 观察点：① 11 次插入后 `size=8`（去重后 8 个不同词），`a` 出现 3 次；② 桶数随负载触发自动增长；③ `reserve(1000)` 后桶数跳到质数 1021，负载骤降——这就是「rehash 维持平均 O(1)」的可视化。

## 七、与 Java 对照

| 维度 | C++ `std::unordered_map` | Java `HashMap` |
|---|---|---|
| 底层 | 链地址哈希表（桶+链） | 链地址哈希表（JDK8 后桶超 8 转红黑树） |
| 默认负载因子 | ≈1.0（实现相关） | 0.75 |
| 默认初始容量 | 实现相关（质数桶表） | 16（2 的幂） |
| 最坏 | 哈希碰撞 O(n) | 碰撞且桶长>8 退化为红黑树 O(log n) |
| 抗 Hash DoS | 实现可加盐 | 同（扰动+随机化） |

---

## 三视角解析

### 🧑‍💻 程序员视角
- `unordered_map` 的键必须**可哈希**（自定义类型要提供 `std::hash` 特化），且 `operator==` 与 hash 要**语义一致**——否则元素「存进去找不到」。
- **负载因子（默认 1.0）**触发 rehash：会重分配桶数组并**使全部迭代器失效**（但引用/指针仍有效，因为节点不搬）。已知规模用 `reserve` 预分配。
- 遍历顺序**不保证稳定**，别依赖；需要稳定顺序用 `map` 或额外排序。

### 🎓 博士生视角
- `unordered_map` 是**桶数组 + 链表**（链地址法），libstdc++ 采用**单链表 + 桶前指针**，使迭代器可跨桶单向前进；查找期望 O(1) 的前提是**哈希均匀**。
- 最坏情况退化为 O(n)（全部冲突到同一条链），这是「哈希函数的攻击面」——实践中用**随机化哈希种子（如 SipHash）**防 HashDoS。
- 负载因子是**空间-时间的显式旋钮**：调小 → 冲突少但内存大；调大 → 内存省但链变长。这与 `vector` 的扩容倍率一起，构成标准库的「性能调参面」。

### 📚 考研者视角
- 408 哈希表考点：**除留余数法、线性探测/二次探测/再哈希/链地址法**四种冲突处理；必会算**ASL（成功/不成功）**并说明与装填因子 α 的关系。
- 常考辨析：**开放定址法不能物理删除（要做「墓碑」标记）**，而链地址法可以直接摘链。
- 记忆锚点：哈希查找的**期望 O(1) 依赖装填因子**；装填因子越接近 1，探测次数急剧上升。

---
