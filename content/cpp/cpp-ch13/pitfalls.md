# cpp-ch13 易错点（Pitfalls）

1. **输入失败后不 `clear()` 导致后续读取全废**
   `cin >> x` 遇非法输入会置 `failbit`，此后所有 `cin >>` 都变成 no-op，`x` 保持旧值或不确定。
   ✅ 先 `cin.clear()` 清状态位，再 `cin.ignore(n, '\n')` 丢弃坏字符后才能继续读取。

2. **误用 `eof()` 作为循环条件**
   `while (!cin.eof()) { cin >> x; ... }` 会在读到末尾那次提取失败后仍进入循环体，处理一次脏数据。
   ✅ 写成 `while (cin >> x) { ... }`：提取成功才进循环，到 EOF 自然终止。

3. **`getline` 与 `>>` 混用留下换行**
   先 `cin >> n;` 读整数，缓冲区残留 `'\n'`，紧接着 `getline(cin, s)` 会立刻读到空行。
   ✅ 在 `>>` 之后、`getline` 之前调用 `cin.ignore()` 吃掉换行；或统一用 `getline` + `istringstream` 解析。

4. **浮点默认精度丢失的错觉**
   `cout << 0.123456789;` 默认只打印 6 位有效数字，看起来「丢精度」，实际值未变。
   ✅ 用 `cout << fixed << setprecision(n)` 显式控制位数；注意 `setprecision` 在默认模式下表示有效数字。

5. **忘记检查 `is_open()`**
   打开文件失败（权限/路径错误）时流进入 fail 状态，后续读写全部静默失败，得到空结果。
   ✅ 打开后立即 `if (!f.is_open()) { /* 报错处理 */ }`，再做读写。

6. **用文本模式读写二进制数据**
   `ofstream`/`ifstream` 默认文本模式，Windows 上 `'\n'` ↔ `'\r\n'` 会被翻译，含 `0x0A/0x0D` 或 `0x1A` 的字节会被篡改，文件损坏。
   ✅ 读写结构化数据必须用 `ios::binary` 模式（`write`/`read`）。

7. **`fstream` 同时读写未 seek 就换向**
   在读写混合的 `fstream` 中，从读切到写（或反之）前若未 `seek`/`flush`，行为未定义，可能读到旧缓冲或写入丢失。
   ✅ 每次切换方向前调用一次 `seekg`/`seekp`（哪怕偏移到原位）以隔断。

8. **`ofstream` 默认截断清空文件**
   `ofstream f("log.txt")` 等价于 `ios::out | ios::trunc`，会直接清空已有文件；误以为「打开即可追加」。
   ✅ 需要追加用 `ios::app`；需要读写不破坏用 `ios::in | ios::out`（不要加 trunc）。
