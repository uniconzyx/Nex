# cpp-ch19 易错点（Pitfalls）

1. **用 `include_directories()` 做全局包含** —— 它是**目录级**命令，会把 include 路径泄漏给本目录及子目录的全部目标，第三方代码也被污染。
   ✅ 改用 `target_include_directories(core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)`，把「谁能看到这个头」变成目标自己的属性（ex09 的 CM001）。

2. **`target_link_libraries()` 漏写关键字** —— 写成 `target_link_libraries(app core)` 时依赖语义未声明，CMake 无法决定要不要传播使用要求，行为随策略版本漂移。
   ✅ 永远显式写 `PUBLIC` / `PRIVATE` / `INTERFACE`（ex09 的 CM006/CM007）。

3. **把实现头写成 `PUBLIC`，把接口头写成 `PRIVATE`** —— 前者泄漏实现细节、拉长编译时间；后者让下游 `#include` 直接失败。
   ✅ 判据只有一条：**这个头出现在我自己的公开头文件里吗**？是 → `PUBLIC`，只在 `.cpp` 里用 → `PRIVATE`（ex10、ex15 的 HS001）。

4. **用 `set(CMAKE_CXX_STANDARD 17)` 或 `set(CMAKE_CXX_FLAGS ...)` 做全局设置** —— 会污染 `add_subdirectory` 拉进来的第三方代码，且换编译器时 flag 直接失效。
   ✅ 用 `target_compile_features(core PUBLIC cxx_std_17)` 表达「我需要 C++17」，由构建系统挑 flag；编译选项用 `target_compile_options(core PRIVATE ...)`（ex07 ④、ex09 的 CM004）。

5. **用 `${CMAKE_SOURCE_DIR}` / `${PROJECT_SOURCE_DIR}` 拼 include 路径** —— 目标一旦被 `install(EXPORT)` 或被其它工程引用，绝对路径就失效。
   ✅ 一律用 `${CMAKE_CURRENT_SOURCE_DIR}` + 相对路径，保证可重定位（ex09 的 CM008）。

6. **`file(GLOB)` 收集源文件** —— CMake 只在配置时展开一次，新增源文件不会触发重新配置，CI 上表现为「本地能编、CI 缺符号」。
   ✅ 显式列出源文件；确实要用 GLOB 就加 `CONFIGURE_DEPENDS`（ex09 的 CM005）。

7. **测试只打印、不看退出码** —— 测试程序 `return 0` 写死，断言失败也照常「通过」，CI 永远绿。
   ✅ 测试入口必须返回「失败断言数 ? 1 : 0」，并让 CTest/流水线以该退出码为准（ex01/ex02 的 `[CI] 退出码语义`）。

8. **用例之间共享静态/全局状态** —— 前一个用例写脏的状态被后一个用例读到，表现成「单独跑通过、整包跑失败」的假失败。
   ✅ 用夹具 `SetUp`/`TearDown` 给每个用例一个全新实例（ex05 的 `shared_state_leak_demo`）。

9. **把不可控依赖（时间、随机数、网络、文件系统）写死在被测代码里** —— 只能 `sleep` 等真实时间，用例又慢又不稳。
   ✅ 抽出接口（`IClock`），生产注入真实现、测试注入 `FakeClock`，被测逻辑零改动（ex06）。

10. **参数化测试只堆数量不做等价类划分** —— 50 个参数全落在同一个等价类里，覆盖率数字好看却一条 bug 也抓不到。
    ✅ 先划等价类（有效/无效），再取边界点（正好边界、边界 ±1），再让参数化去展开（ex03、ex04）。

11. **把覆盖率数字当目标** —— 补一堆只调用不断言的用例能把行覆盖率刷到 90%，但分支、边界依旧没测。
    ✅ 覆盖率是「用例质量」的镜像：看**未覆盖行清单**补用例，并配分支覆盖与断言密度一起看（ex14）。

12. **头文件里放非 `inline` 的自由函数定义** —— 被两个 TU 包含就产生两个强符号，链接期 `multiple definition`。
    ✅ 头里只放声明 + `inline`/模板定义；需要每 TU 一份私有实现就用 `static`/匿名 namespace（ex16）。

13. **`inline` 与强符号混用同名函数** —— 一个 TU 里是普通定义、另一个 TU 里是 `inline` 定义，标准不保证一致，**未定义行为**而非「链接器随便挑一个」。
    ✅ 同名同签名函数在全程序内必须「定义一致」；不一致就是 ODR 违规（ex16 用例2）。

14. **`-Werror` 全局开在 `CMAKE_CXX_FLAGS` 里** —— 会把第三方代码的告警也升级成错误，换编译器版本即大面积红灯。
    ✅ 只对自己的目标挂 `target_compile_options(core PRIVATE -Wall -Wextra -Werror)`，且不要外传给使用者（ex07 ⑤、ex17）。

15. **CI 里 `uses` 不固定版本** —— `actions/checkout` 不写 `@v4` 或提交 SHA，上游一改流水线就静默变行为，且不可审计。
    ✅ 固定到 tag 或 SHA；再加 `timeout-minutes` 防止挂死占满 runner（ex13 的 WF006/WF007）。

16. **矩阵构建 `fail-fast` 保持默认 `true`** —— 第一个平台失败就取消其余单元，一次只能看到一个平台的错误。
    ✅ 调试期设 `fail-fast: false` 一次看全；配合 `if: always()` 上传报告（ex08）。

17. **缓存 key 不含输入哈希** —— `key: deps-${{ matrix.os }}` 会导致依赖更新后仍命中旧缓存，出现「本地新、CI 旧」的鬼影 bug。
    ✅ key 里带上 `${{ hashFiles('CMakeLists.txt') }}` 之类的输入指纹，输入变则自动失效（ex08）。

18. **`needs` 里写错 job 名** —— 悬空引用让 DAG 断链，GitHub 直接拒绝该 workflow。
    ✅ 提交前跑一遍 workflow 静态校验；环检测同样要在本地做（ex13 的 WF005、ex11 的环检测）。
