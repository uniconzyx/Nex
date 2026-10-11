# clang-u06 · 常见陷阱

1. **recipe 用空格缩进 → `missing separator`** —— Makefile 的词法规则要求 recipe 行**必须以 Tab 开头**。
   现代编辑器默认「按 Tab 插入 N 个空格」，于是从别处复制的片段必然踩这个坑。
   报错原文是 `Makefile:5: *** missing separator. Stop.`，且**报错行号指向第一条 recipe**。
   正确做法：把 `Makefile` 的缩进设为「制表符」；`cat -A Makefile` 可看到 `^I`（Tab）与空格的区别。

2. **缺 `.PHONY` 导致目标被静默跳过** —— 若目录里恰好存在名为 `clean` / `test` / `all` 的文件，
   Make 会认为该 target「已是最新」，**什么都不做并返回 0**。这是最恶劣的一类 bug：
   无报错、无警告，你以为清理过了，其实旧 `.o` 还在。**规则：所有动作型目标一律 `.PHONY`。**

3. **只声明 `.c` 依赖、漏掉 `.h`** —— `util.o: util.c` 是**不完整**的声明。
   `util.c` 通过 `#include` 依赖 `util.h`，而 Make 无从知晓（它不做预处理）。
   后果：改了头文件不重编，链接成功但行为陈旧，甚至多个 `.o` 结构体布局不一致导致内存错乱。
   正确做法：`-MMD -MP` 生成 `.d` 并 `-include`。

4. **`-include` 写成 `include`** —— 首次构建时 `.d` 文件尚不存在，
   `include` 会直接报 `No such file or directory` 而终止。必须用 **`-include`**（减号表示「缺失不算错误」）。

5. **`=` 里放 `$(shell ...)` 导致命令重复执行** —— 递归展开变量每次被引用都重新求值。
   `STAMP = $(shell date +%s)` 会在每次 `$(STAMP)` 出现时都执行一次 `date`，
   得到一个「每次都不一样」的值，让构建变得不可复现。改用 `:=`。

6. **`make -j` 并行构建出现随机的产物损坏** —— 根因几乎总是**依赖声明不完整**，
   使两个 recipe 会在无依赖关系的情况下并发访问同一文件。
   判定法则：**`-j1` 稳定成功而 `-j8` 偶尔失败 ⇒ 依赖缺失**，不要怀疑编译器。
   修法：补全依赖边；生成头文件的规则必须显式声明为依赖。

7. **`clean` 漏删中间产物** —— 只删 `app` 不删 `*.o` / `*.d`，下次构建复用陈旧 `.o`，
   于是「`make clean && make` 居然没修好问题」。`clean` 必须删掉**全部**生成物：
   `rm -f $(TARGET) $(OBJS) $(OBJS:.o=.d)`。

8. **在链接规则里误用 `$<`** —— `$<` 只代表**第一个**依赖。
   链接规则 `$(TARGET): $(OBJS)` 里用 `$<` 只会链上 `main.o`，其他 `.o` 全丢，
   表现为一堆 `undefined reference`。链接要用 **`$^`（全部依赖）**。

9. **Windows 上 `make` 命令不存在，其实叫 `mingw32-make`** —— MinGW-w64 发行版为避免
   与 MSYS/Cygwin 的 `make` 冲突，把 GNU Make 命名为 `mingw32-make`。
   于是 `make -j8` 报 `command not found` 而 `mingw32-make -j8` 正常。
   这不是 Makefile 的问题，是**发行版命名差异**——排查时先确认命令到底叫什么。
