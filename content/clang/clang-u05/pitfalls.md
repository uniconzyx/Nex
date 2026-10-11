# clang-u05 · 易错点（Pitfalls）

1. **宏参数不加括号，被外层运算符优先级「吃掉」**
   `#define SQUARE(x) x * x` 在 `SQUARE(2 + 1)` 中展开成 `2 + 1 * 2 + 1 = 5`。
   ✅ 参数与整体都加括号：`#define SQUARE(x) ((x) * (x))`。

2. **宏参数带副作用导致多重求值**
   `#define MAX(a,b) ((a)>(b)?(a):(b))`，调用 `MAX(i++, 2)` 会让 `i++` 被求值两次（比较一次、返回一次），结果依赖求值顺序且产生未指定行为。
   ✅ 先把值算进局部变量再传，或改用 `static inline` 函数；绝不给宏传自增/赋值等带副作用的实参。

3. **多语句宏未用 `do { } while (0)` 包裹**
   `#define LOG(x) printf("A\n"); printf("B\n");` 放在 `if (c) LOG(k);` 中，只有第一条语句受 `if` 管辖，第二条恒执行。
   ✅ 一律写成 `#define LOG(x) do { printf("A\n"); printf("B\n"); } while (0)`。参见 examples/ex03.json。

4. **头文件缺守卫导致重复定义**
   头文件里放了 `struct`/`inline` 定义却没守卫，被多个 `.c` 间接包含后同一翻译单元出现两份定义 → 编译报 `redefinition`。
   ✅ 每个头文件加 `#ifndef XXX_H / #define XXX_H / #endif`（或 `#pragma once`）。参见 examples/ex07.json。

5. **`#` 字符串化前没有「二次展开」层，拿到的是宏名而非值**
   `#define VERSION 2026` + `STR(VERSION)` 得到 `"VERSION"` 而非 `"2026"`，因为 `#` 会抑制参数展开。
   ✅ 用 `TOSTR(x) STR(x)` 间接一层，先让 `VERSION` 展开成 `2026` 再字符串化。参见 examples/ex04.json。

6. **头文件里放「带存储的全局变量定义」引发 multiple definition**
   在头文件写 `int g = 0;`，每个包含它的 `.c` 都会定义一份 `g`，链接期冲突。
   ✅ 头文件用 `extern int g;`，真正的定义只放在**一个** `.c` 里。

7. **`_Generic` 加了 `default` 后漏掉的类型不再报警**
   `default: ...` 会吞掉所有未列出的类型分支，可能掩盖本该覆盖的类型。
   ✅ 仅当确实要兜底时才加 `default`；核心类型逐一显式列出。

8. **条件编译里引用了拼错的宏名却静默走 else**
   `#if ENABLE_FOO` 中 `ENABLE_FOO` 若拼写错误，会被当作 `0`，条件静默为假，逻辑悄悄改变且无任何报错。
   ✅ 关键开关用 `#ifdef`/`defined()` 显式判断，或配合 `_Static_assert`/`#pragma message` 自检。
