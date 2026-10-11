# cpp-ch09 易错点（Pitfalls）

1. **sort 比较器不满足严格弱序（Strict Weak Ordering）→ 未定义行为**
   ```cpp
   std::sort(v.begin(), v.end(), [](int a, int b){ return a <= b; }); // 错：用了 <=
   ```
   `sort` 用比较器判定「相等/可交换」，违反非对称/传递会越界读写、死循环或数据错乱，且**编译不报错**。
   ✅ 比较器只用 `<`（或 `>` 用于降序），保证 `comp(a,a)==false` 且 `comp(a,b) ⇒ !comp(b,a)`。

2. **迭代器失效：在 vector 上 erase 后继续使用旧迭代器**
   `vector` 删除元素会使「被删位置及之后」的迭代器/引用/指针失效；扩容（push_back 触发）会使**全部**失效。在循环里 `erase(it)` 后再 `++it` 是 UB（见 `examples/ex09`）。
   ✅ 用 `it = v.erase(it)` 拿返回值推进；或 C++20 `std::erase_if`。

3. **find 找不到时直接解引用 end()**
   ```cpp
   auto it = std::find(v.begin(), v.end(), x);
   std::cout << *it; // 若 x 不存在，it==end()，解引用 UB
   ```
   ✅ 先判 `if (it != v.end())`，再解引用（见 `examples/ex03`）。

4. **transform 目标区间容量不足 → 写入未分配空间**
   ```cpp
   std::vector<int> b;                       // 空！
   std::transform(a.begin(), a.end(), b.begin(), f); // UB：写到 b 的非法位置
   ```
   ✅ 预分配 `std::vector<int> b(a.size());`，或 `std::back_inserter(b)` 让算法 push_back。

5. **lambda 引用捕获悬垂（dangling reference）**
   ```cpp
   auto mk() { int k = 10; return [&k](int x){ return x + k; }; } // 返回后 k 已销毁
   ```
   按引用捕获的变量必须保证 lambda 调用时该对象仍存活。
   ✅ 生命周期可控时再用 `[&]`；否则 `[=]`/初始化捕获 `[k=std::move(big)]` 按值捕获（见 `examples/ex10`）。

6. **partition 不保证稳定性，误以为相等元素顺序不变**
   `std::partition` 会把「满足谓词」的元素聚到前端，但组内相对顺序**不保证**；需要保序用 `std::stable_partition` / `std::stable_sort`。
   ✅ 涉及「先按某键排序、再稳定分组/二次排序」时选 `stable_*`（见 `examples/ex02`、`ex07`）。
