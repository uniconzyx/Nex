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
9. **不检查文件是否打开成功** —— `ofstream f("C:/no/such/dir/x.txt"); f << "d";` 目录不存在时流静默失败、数据丢失。正确写法：打开后立刻 `if (!f) { /* 报错 */ }`。
10. **`getline` 与 `>>` 混用残留换行** —— `cin >> n` 留下 `\n`，紧接着 `getline` 读到空行。正确写法：混用前 `cin.ignore()` 丢弃残留换行。
11. **`endl` 每次都 flush 拖慢 IO** —— `endl` = 换行 + 强制 flush，大循环能慢几十倍。正确写法：普通换行用 `'\n'`，仅需立刻落盘才 `flush`/`endl`。
12. **流状态位未 clear 导致后续全失效** —— 读失败置 `failbit` 后所有操作被忽略。正确写法：出错 `clear()` 再 `ignore()` 丢弃坏输入，才能继续。
13. **文本模式读写二进制被篡改** —— Windows 下文本模式把 `\n`→`\r\n`、遇 `0x1A` 当 EOF。正确写法：二进制必须开 `std::ios::binary`。
14. **`stringstream` 复用前未双清** —— 只 `str("")` 不清状态位会残留失败标记。正确写法：每次复用前 `ss.str(""); ss.clear();`。
15. **locale 影响数字/日期格式导致解析错** —— `imbue(locale)` 改变千位符、小数点。正确写法：处理机器数据用 `std::locale::classic()`（C locale）。
