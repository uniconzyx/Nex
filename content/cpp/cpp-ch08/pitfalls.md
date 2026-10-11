# cpp-ch08 易错点（Pitfalls）

1. **vector 扩容导致迭代器/引用/指针全部失效**
   `push_back`/`insert`/`resize` 一旦触发扩容，底层会搬到新地址，旧块上的 `it`、`&v[0]`、`v.data()` 全部悬空。继续用就是 UB（常表现为数据错乱或崩溃）。
   ✅ 若循环中要增删且保留迭代器：用 `it = v.insert(it, x); ++it;` 的返回值推进；或先 `reserve` 预分配避免扩容；或改用下标 `i`。

2. **erase 循环中迭代器失效（最经典的段错误来源）**
   ```cpp
   for (auto it = v.begin(); it != v.end(); ++it) {
       if (*it % 2 == 0) v.erase(it);   // erase 后 it 失效，再 ++it 是 UB
   }
   ```
   ✅ 用返回值推进：`for (auto it = v.begin(); it != v.end(); ) it = (*it % 2 == 0) ? v.erase(it) : std::next(it);`
   ✅ 更简洁（C++20）：`std::erase_if(v, [](int x){ return x % 2 == 0; });`（`list`/`map` 等也有对应 `erase_if`）。

3. **range-for 中修改容器导致失效 / 无限循环**
   ```cpp
   for (auto& x : v) { v.push_back(x); }  // push_back 可能扩容 → x 悬空（UB）；也极易死循环
   ```
   ✅ range-for 期间**不要**插入/删除使迭代器失效；要改就把原容器内容先拷出，或改用带返回值的普通循环。

4. **unordered_map 哈希质量差 → 最坏 O(n)**
   自定义 key 的 `std::hash` 若把大量 key 映射到同一桶（如 `hash % 2` 式设计、或可被攻击者构造碰撞），查询退化为链表 O(n)，且 rehash 频繁。
   ✅ 用高质量哈希（如组合各字段的 FNV-1a / 标准 `std::hash` 组合）；不可信输入用实现自带的盐化哈希；`reserve` 降低负载因子。

5. **误用 map::operator[] 触发「意外插入」**
   ```cpp
   auto it = m.find("k");
   if (m["k"] > 0) { ... }   // 即使只想读，[] 也会插入默认 value！size 悄悄 +1
   ```
   ✅ 只读用 `m.find(k)`（判 `!= end()`）或 `m.at(k)`（越界抛异常、不插入）；C++20 用 `m.contains(k)` 做纯判断。

6. **认为 unordered_* 的遍历顺序可预期**
   `unordered_map` 顺序依赖桶布局/哈希，`reserve`/`rehash` 后顺序会变，**绝不能依赖遍历顺序做断言或序列化**。
   ✅ 需要有序输出就改用 `map`，或对 `unordered_*` 取出 key 后另行排序。

7. **erase 后仍在用被删迭代器 / 误以为 erase 返回 void**
   C++98 的 `map::erase(it)` 返回 `void`；C++11 起返回下一迭代器。旧代码 `m.erase(it++);` 仍对，但混用新写法更一致。
   ✅ 统一用 `it = c.erase(it);`（C++11+ 全容器通用）。

8. **把 list 当 vector 用追求「O(1) 插入」却牺牲缓存**
   仅因「中间插入 O(1)」就选 `list`，但场景其实是「建好后遍历多次」——结果比 `vector` 慢数倍（见 concept/04）。
   ✅ 先算访问模式；绝大多数情况 `vector` 是更优解，`list` 仅留给「频繁中部增删 + 持有迭代器不失效」场景。
