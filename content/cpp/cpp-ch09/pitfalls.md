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

7. **把 `std::remove` 当成「删除元素」**
   ```cpp
   std::remove(v.begin(), v.end(), 3);        // 错：v.size() 一点没变
   ```
   `remove` 是**重排算法**：它把要保留的元素前移，返回新的逻辑尾，容器大小不变，尾部残留的是被「移走」的旧值（不是被删掉）。
   ✅ erase-remove 惯用法：`v.erase(std::remove(v.begin(), v.end(), 3), v.end())`；C++20 起直接 `std::erase(v, 3)`。

8. **在未排序区间上用 `lower_bound` / `binary_search`**
   ```cpp
   std::vector<int> v = {3, 1, 2};
   bool has = std::binary_search(v.begin(), v.end(), 2);   // 区间无序 → 结果未定义
   ```
   二分查找族（`lower_bound`/`upper_bound`/`equal_range`/`binary_search`）都要求区间**已按同一比较器有序**，否则不是「找不到」而是未定义行为。
   ✅ 先 `std::sort`，且查找比较器与排序比较器必须一致；只判存在且数据量小，用 `std::find` 更安全。

9. **`std::accumulate` 的初值类型决定整个累加的类型**
   ```cpp
   std::vector<double> v = {1.5, 2.5};
   double s = std::accumulate(v.begin(), v.end(), 0);      // 错：初值 0 是 int
   ```
   返回类型由**初值**推导，且每一步都按初值类型运算——浮点被逐次截断，不是在最后才转换；大整数则会中途溢出。
   ✅ 初值写对类型：`std::accumulate(v.begin(), v.end(), 0.0)`；累加大整数用 `0LL`，累加字符串用 `std::string{}`。

10. **给 `sort` 传 `<=` 作比较器**
   `[](int a, int b){ return a <= b; }` 违反严格弱序的非自反要求（`a <= a` 为真），行为是未定义，libstdc++ 上常直接崩。
   ✅ 比较器里只允许出现 `<`；多字段比较时每一级都用 `<`，最后一级也不要写成 `<=`。

11. **降序排序后仍用默认 `lower_bound`**
   用 `greater<>` 排成降序，查找时传默认的 `less<>`，二分方向反了，结果无意义且不报错。
   ✅ 排序与查找必须用同一个比较器：`lower_bound(first, last, v, std::greater<>{})`。

12. **循环里 `erase` 后用 `++it`**
   `v.erase(it); ++it;` 中 `it` 已失效，`++it` 是 UB，还会跳过紧跟的元素。
   ✅ 用返回值续接：`it = v.erase(it);`；或直接用 C++20 的 `std::erase_if(v, pred)`。

13. **`std::remove` 之后忘了 `erase`**
   `std::remove` 只把保留元素前移并返回新逻辑结尾，容器大小不变，尾部残留旧值。
   ✅ 用 erase-remove 惯用法：`v.erase(std::remove(v.begin(), v.end(), x), v.end())`；C++20 用 `std::erase(v, x)`。

14. **`accumulate` 初值写成 `0` 去累加浮点**
   类型由初值决定，`accumulate(v.begin(), v.end(), 0)` 对 `vector<double>` 会截断成整数，静默丢精度。
   ✅ 初值类型与期望结果一致：浮点用 `0.0`，大整数用 `0LL`，字符串用 `std::string{}`。

15. **ranges 管道被遍历多次，惰性计算重复执行**
   `auto r = data | filter | transform;` 之后 `for (x : r)` 两次，`transform` 里的昂贵逻辑就执行两遍。
   ✅ 需要多次访问就先物化成一个容器；只遍历一次时才用惰性管道，并把 `take` 尽量前置以短路上游计算。
