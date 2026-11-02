# 本章避坑指南

1. **数组传参退化为指针** —— `void f(int a[5])` 内 `sizeof(a)` 是指针大小（如 8），拿不到数组长度；必须显式传 `size` 或用 `std::array`/`std::vector`。
2. **C 字符串忘了 `\0`** —— 字符数组未以 `\0` 结尾就当字符串用，`strlen`/`cout` 会越界读到垃圾或崩溃。务必留 `\0` 位置或用 `std::string`。
3. **string_view 悬空** —— `std::string_view v(getTempString());` 临时 string 析构后 v 指向已释放内存，访问 UB。确保底层字符串生命周期更长。
4. **下标越界无检查** —— `s[i]` / `a[i]` 越界是未定义行为（不抛异常），用 `at()` 或在访问前判长度。
5. **`&a` 与 `&a[0]` 步长不同** —— 两者地址值相同但类型不同：`&a + 1` 跳过整个数组（`int(*)[5]` 走 20 字节），`&a[0] + 1` 只跳一个元素。指针算术前先确认类型。
6. **`string_view` 当 C 字符串用** —— 它不保证 `\0` 结尾，`v.substr(2)` 可能指向大串中间。传给 C API 前先 `std::string{v}` 拷一份。
7. **`find` 结果与 `npos` 比较写成 `< 0`** —— `size_type` 是无符号，`< 0` 永远为假且无告警。写 `== std::string::npos`。
8. **`npos` 参与算术** —— `pos = s.find(x) + 1` 在未找到时回绕成 0，导致从头部重新查找 → 死循环。先判 `npos` 再加。
9. **`substr` 在循环里做拷贝** —— `s = s.substr(1)` 每次都复制剩余全部字符，整体 O(n²)。改用索引偏移或 `std::string_view`（零拷贝）。
10. **字符串字面量赋给 `char\*`** —— C++11 起编译错误；即使强转通过，写入只读段是 UB。只读用 `const char*`，要改就 `char arr[] = "...";`（拷贝到栈上）。
11. **`data()` 在空视图上解引用** —— 空 `string_view` 的 `data()` 可能是 `nullptr`，`sv.data()[0]` 是 UB。
12. **同时重载 `f(string)` 与 `f(string_view)`** —— 传字面量时两者都可匹配，产生调用歧义。函数重载里只保留 `string_view` 版本。
13. **`c_str()` 返回的指针在修改后失效** —— `s += "x"` 可能触发 realloc，使之前 `s.c_str()` 得到的指针悬垂。正确写法：要长期持有就 `strdup`/拷贝，别存裸指针。
14. **`operator[]` 越界不抛异常、`at()` 才抛** —— `s[i]` 越界是 UB，`s.at(i)` 越界抛 `out_of_range`。正确写法：需要边界检查用 `at()`，性能敏感且已确信安全才用 `[]`。
15. **用 `sprintf`/C 串函数导致缓冲区溢出** —— `sprintf(buf, "%s", user)` 不检查目标容量，用户超长就溢出。正确写法：用 `snprintf(buf, sizeof buf, ...)` 限长，或干脆用 `std::string`/`std::format` 完全避开手写缓冲。
