# 多文件编译与链接实战手记：凯喵和 undefined reference 缠斗的十二个夜晚

> 这一单元讲翻译单元、符号表、名字修饰、静态/动态链接、强弱符号。概念不复杂，但 `undefined reference` 和 `multiple definition` 这两类报错，是每个 C/C++ 工程师都躲不过的成人礼。这篇手记用十二个现场把链接器的脾气摸清楚。

## 开场：链接错误为什么比编译错误难查

编译错误指到行、给出类型不匹配的原因；链接错误只给你一句 `undefined reference to 'foo'`，不告诉你为什么找不到。

原因在于链接是**跨翻译单元**的工作。编译器每个 `.c` 单独看，它只保证「本单元语法和类型正确」，遇到未定义的符号就留个洞，指望链接器去补。链接器最后把所有 `.o` 的符号表拼在一起，逐个补洞——补不上就是 `undefined reference`，补重了就是 `multiple definition`。

所以排查链接错误的心法是：**先看符号在不在，再看名字对不对，最后看可见性**。下面十二个现场基本覆盖这条链。

### 现场一：声明了但没定义，编译器不报、链接器报

```c
/* util.h */
int add(int a, int b);        /* 只有声明 */

/* main.c */
#include "util.h"
int main(void) { return add(1, 2); }
```

`gcc main.c` 单独编译成功，一链接就 `undefined reference to 'add'`。因为声明只是「向编译器承诺这个符号存在」，定义才是「真正分配空间」。

这条的实用价值是：**看到 `undefined reference` 先问「这个符号有没有被编译进任何一个 `.o`」**，而不是去怀疑头文件。检查手段：

```bash
gcc -c util.c -o util.o
nm util.o | grep add          # 有 T add 说明定义在
nm main.o | grep add          # U add 表示 main.o 引用但未定义
```

`nm` 的字母含义要记牢：`T` 在代码段（已定义）、`U` 未定义（引用）、`B`/`D` 在 BSS/数据段、`W` 弱符号、`t` 是本地（static）符号。

### 现场二：忘了把 `.o` 加进链接命令

`gcc main.c util.c -o app` 正确；写成 `gcc main.c -o app` 就漏了 `util.c`。

更隐蔽的版本是 Makefile 里变量拼错：

```makefile
OBJS = main.o util.o helper.o
app: $(OBJ)
	gcc $^ -o $@          # 笔误：$(OBJ) 少了 S，展开为空
```

`$(OBJ)` 未定义时展开成空串，于是 `gcc -o app` 什么都没链接，报一堆 undefined。这类错误的特征是**报错数量特别多**（所有符号都找不到），一眼就能判断是「漏了整个文件」而不是「某个函数写错」。

### 现场三：C++ 调用 C 函数没加 `extern "C"`，名字被修饰了

C++ 支持重载，所以编译器会把参数类型编进符号名（name mangling）：`void foo(int)` 变成 `_Z3fooi`。C 编译器不做这个，`foo` 就是 `foo`。两边一对接，链接器找不到 `foo`。

修法是在**头文件里**用条件编译包住：

```c
/* clib.h —— 让 C++ 看到时按 C 的规则解析 */
#ifdef __cplusplus
extern "C" {
#endif

int c_add(int a, int b);
void c_log(const char *msg);

#ifdef __cplusplus
}
#endif
```

关键是这段必须写在头文件里、被 C++ 包含时才生效。只在本文件里写 `extern "C" int c_add(...)` 也能编过，但每个调用点都要写一遍，迟早漏。

用 `nm` 验证最直观：

```bash
g++ -c main.cpp -o main.o && nm main.o | grep c_add
# 正确：U c_add
# 漏写：U _Z5c_addii
```

### 现场四：头文件里定义了非 inline 函数，被多个 `.o` 包含

```c
/* helper.h */
int square(int x) { return x * x; }    /* 定义写在头文件里 */
```

两个 `.c` 都 `#include "helper.h"`，链接时报 `multiple definition of 'square'`。

三种修法，按推荐度：

```c
/* 方案一（C99 起）：inline */
static inline int square(int x) { return x * x; }   /* 每个 TU 一份副本，最省心 */

/* 方案二：C++17 的 inline 变量/函数 */
inline int square(int x) { return x * x; }          /* 链接器只保留一份 */

/* 方案三：头文件只放声明，定义放 .c */
int square(int x);                                   /* helper.h */
```

C 语言里 `inline` 的语义比较绕（不带 `static` 的 `inline` 不产生外部定义，需要配一个 `extern inline` 或另一处的非 inline 定义），所以**头文件里给函数用 `static inline` 最稳**。C++ 则直接用 `inline`。

### 现场五：`static` 全局变量在两个文件里同名，以为是同一个

```c
/* a.c */ static int counter = 0;
/* b.c */ static int counter = 0;
```

两者互不影响——`static` 在文件作用域表示**内部链接**，符号只在本翻译单元可见。`nm a.o` 显示 `b counter`（小写 b 表示本地 BSS），而不是 `B`。

这既是保护（避免命名冲突），也是坑（有人想共享计数却各自加了一份）。要在多文件间共享，就去掉 `static`，并在头文件里写 `extern int counter;`。

顺带一个面试常考的对比：**函数内的 `static` 局部变量**是「只初始化一次、生命周期整个程序」，与文件作用域的 `static` 完全不是一回事。考题经常混着问。

### 现场六：静态库顺序写反，链接失败

```bash
gcc main.o -lfoo -lbar -o app      # 失败
gcc main.o -lbar -lfoo -o app      # 成功
```

原因：静态库的链接是**一次性从左到右扫描**。链接器扫到 `-lfoo` 时只取出「当前未定义符号」需要的成员；如果 `foo` 依赖 `bar` 里的符号，而 `bar` 在 `foo` 左边已经扫过了，就不会回头再取。

规则记法：**被依赖的库放在右边**。实在搞不清顺序，用 `--start-group ... --end-group` 让链接器循环扫描：

```bash
gcc main.o -Wl,--start-group -lfoo -lbar -Wl,--end-group -o app
```

动态库（`.so`）没有这个问题，因为它不在链接期解析成员，只在运行时按需加载。

### 现场七：强弱符号规则记反，`main` 被覆盖

链接器的强弱符号规则：多个**强**符号（普通函数/已初始化全局变量）同名 → 报错 `multiple definition`；强 + 弱（`__attribute__((weak))` 或未初始化全局变量在某些实现下）→ **强符号胜出，弱符号被丢弃**；多个弱符号 → 取任意一个。

常见误解是「后出现的覆盖先出现的」。实际是按强弱：

```c
/* lib.c */ __attribute__((weak)) int handler(void) { return 0; }   /* 默认实现 */
/* app.c */ int handler(void) { return 42; }                        /* 用户覆盖 */
/* 链接结果：app.c 的版本生效，lib.c 的是兜底 */
```

这个机制正是「库提供默认实现、应用可覆盖」的标准做法（比如 `__malloc_hook`、驱动里的弱回调表）。但反过来，如果有人把本该唯一的函数写成弱符号，两个实现会**静默**地只保留一个，症状是「代码明明改了却没生效」——比报错更难查。

### 现场八：`-fvisibility=hidden` 之后动态库导出为空

编译动态库时为了减少符号污染，常加 `-fvisibility=hidden`，默认所有符号只在库内可见。结果外部调用全部 `undefined`。

修法是显式标注需要导出的符号：

```c
#define API __attribute__((visibility("default")))

API int lib_init(void);
API void lib_free(void *p);
```

或者用版本脚本 `--version-script=exports.map` 精确控制导出列表。验证手段：

```bash
gcc -shared -fPIC -fvisibility=hidden lib.c -o libx.so
nm -D --defined-only libx.so      # 只有标了 default 的会出现在这里
```

`nm -D` 看的是动态符号表，注意与 `nm` 的静态符号表区分——很多「导出为空」的排查错误都出在看错了表。

### 现场九：`-fPIC` 漏了，动态库加载时报 relocation 错误

从源码编 `.so` 必须加 `-fPIC`（位置无关代码）。漏了会在某些平台上直接报：

```text
relocation R_X86_64_32 against `.rodata' can not be used when making a shared object; recompile with -fPIC
```

x86-64 上有时能编过但在加载时崩，更隐蔽。原因在于动态库被加载到任意地址，代码里不能出现「绝对地址」的立即数，否则加载器无法修正。

标准编译命令：

```bash
gcc -fPIC -c lib.c -o lib.o
gcc -shared lib.o -o libx.so
```

静态库不需要 `-fPIC`（因为它被直接拷进可执行文件，位置在链接期确定）。但**如果静态库最终要被打进动态库**，那它也必须用 `-fPIC` 编译——这是很常见的一层陷阱。

### 现场十：`-Wl,-rpath` 没设，运行时找不到 `.so`

编好了、链接也过了，一运行报 `error while loading shared libraries: libx.so: cannot open shared object file`。

这是**运行期**的搜索路径问题，与链接期无关。链接期用 `-L` 找库，运行期用 `DT_RUNPATH`/`LD_LIBRARY_PATH`/`ldconfig` 找库。三种修法：

```bash
# 方案一：编进 rpath（最省事，适合自带依赖的应用）
gcc main.c -L. -lx -Wl,-rpath,'$ORIGIN/lib' -o app
# 注意 $ORIGIN 要用单引号，否则被 shell 展开成空

# 方案二：环境变量（调试用，别上生产）
LD_LIBRARY_PATH=/opt/app/lib ./app

# 方案三：系统级注册
echo /opt/app/lib | sudo tee /etc/ld.so.conf.d/app.conf && sudo ldconfig
```

`$ORIGIN` 表示「可执行文件所在目录」，是发布包里最常用的写法，因为它不依赖安装路径。

### 现场十一：`ldd` 显示 `not found`，但文件明明存在

`ldd ./app` 输出 `libx.so => not found`，`ls` 一看文件就在旁边。

三个常见原因，按概率排序：

1. **架构不匹配**：`file libx.so` 显示 `ARM aarch64` 而应用是 x86-64。
2. **依赖的依赖缺失**：`libx.so` 自己能找到，但它依赖的 `liby.so` 找不到——`ldd` 会把间接依赖也列出来，注意看是哪一行 `not found`。
3. **SONAME 不匹配**：库文件叫 `libx.so.1.2.3`，但 `SONAME` 是 `libx.so.1`，而目录里只有 `libx.so` 这个开发链接，缺运行期链接。

排查命令链：

```bash
file libx.so                 # 架构
readelf -d libx.so | grep -E 'SONAME|NEEDED'   # 它声明了什么
ls -l /opt/app/lib           # 实际文件名对不对
LD_DEBUG=libs ./app 2>&1 | head -30            # 看加载器找了哪些路径
```

`LD_DEBUG=libs` 是排查动态库问题最强的一招，它会把加载器的每一次尝试都打出来。

### 现场十二：增量构建只重编了 `.c` 没重编依赖它的文件

改了头文件里的结构体定义，`make` 只重编了直接包含它的那个 `.c`，其他文件用的是旧 `.o`，于是结构体偏移不一致，运行时出现莫名其妙的字段错位。

根因是 Makefile 里没有生成**头文件依赖**。手工维护依赖列表必然漏，正确做法是用编译器自动生成：

```makefile
CFLAGS = -MMD -MP
OBJS = main.o util.o helper.o

app: $(OBJS)
	$(CC) $^ -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

-include $(OBJS:.o=.d)     # 关键：把编译器生成的 .d 依赖文件包含进来
```

`-MMD` 让编译器在生成 `.o` 时顺带写一个 `.d` 文件，内容是「这个 `.o` 依赖哪些头文件」；`-MP` 补上空目标避免头文件被删后 make 报错。`-include`（带减号）表示文件不存在也不报错。

这一条是最容易被忽略、但影响面最大的一条——它不会立刻报错，而是让「某些机器上能跑、某些不能跑」的灵异 bug 出现。

## 收尾：凯喵的链接排查口诀

五句话应付九成情况：

**先看符号在不在**——`nm` 查 `T`/`U`，确认是「没编译进去」还是「名字不对」。

**名字先怀疑修饰**——C++ 调 C 必写 `extern "C"`，用 `nm` 看有没有 `_Z` 前缀。

**重复定义查头文件**——头文件里的函数定义一律 `static inline` 或 `inline`。

**库顺序被依赖靠右**——不确定就用 `--start-group`。

**跑不起来查 rpath**——链接期的 `-L` 和运行期的 `rpath` 是两件事，`LD_DEBUG=libs` 一看就清楚。

链接这件事的特点是：**报错信息极度贫乏，但归因路径非常固定**。只要你养成「先 `nm` 再看顺序最后查路径」的习惯，绝大多数链接问题都能在三分钟内定位。凯喵见过的最痛苦的排查，几乎都是因为跳过了 `nm` 这一步、直接去改代码——方向错了，改多少遍都没用。

最后一句方法上的建议：这一章最值得动手做的练习，是**故意制造每一种错误**。去掉 `extern "C"` 看报什么、把库顺序调反看报什么、删掉 `-fPIC` 看报什么、把 `rpath` 去掉看运行时报什么。每种都亲眼看一遍报错，以后在真实项目里遇到底层完全相同的信号时，你能在一秒内认出它。这种「报错模式识别」的能力，比记住任何规则都更快生效。
