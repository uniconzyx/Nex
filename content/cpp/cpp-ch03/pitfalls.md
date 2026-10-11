# 本章避坑指南

1. **数组传参退化为指针** —— `void f(int a[5])` 内 `sizeof(a)` 是指针大小（如 8），拿不到数组长度；必须显式传 `size` 或用 `std::array`/`std::vector`。
2. **C 字符串忘了 `\0`** —— 字符数组未以 `\0` 结尾就当字符串用，`strlen`/`cout` 会越界读到垃圾或崩溃。务必留 `\0` 位置或用 `std::string`。
3. **string_view 悬空** —— `std::string_view v(getTempString());` 临时 string 析构后 v 指向已释放内存，访问 UB。确保底层字符串生命周期更长。
4. **下标越界无检查** —— `s[i]` / `a[i]` 越界是未定义行为（不抛异常），用 `at()` 或在访问前判长度。
