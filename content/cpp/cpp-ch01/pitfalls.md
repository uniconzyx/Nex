# 本章避坑指南

1. **引用返回局部变量** —— 函数返回 `int&` 指向局部变量 = 悬垂引用，未定义行为。
2. **`using namespace std;` 写进头文件** —— 污染所有包含者的命名空间，只允许在 .cpp 内使用。
3. **整数除法截断** —— `double avg = sum / n;` 当 sum、n 都是 int 时先整除再转 double，结果丢失小数。应写 `sum / static_cast<double>(n)`。
4. **`std::vector<bool>` 不是普通容器** —— 它是位压缩特化，`&v[0]` 不能得到 `bool*`。
