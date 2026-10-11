# py-ch05 · 常见陷阱与正确写法

1. **不写 `encoding`** —— `open("f.txt")` 跟随系统 locale，中文 Windows 上是 GBK，换到 Linux 就乱码或抛 `UnicodeDecodeError`。正确：**任何文本文件读写都显式写 `encoding="utf-8"`**。

2. **用文本模式读写二进制内容** —— 文本模式会对 `\r\n` 做规范化、对字节做解码，图片/压缩包/协议报文会被改坏。正确：`"rb"` / `"wb"`。

3. **`csv` 不加 `newline=""`** —— `csv` 自己写 `\r\n`，不禁用换行翻译会让 Windows 上多出 `\r`，Excel 里显示空行。正确：`open(..., newline="")`。

4. **把 `\ufeff` 当成数据** —— 带 BOM 的文件用 `utf-8` 读，首字符会多出 `\ufeff`，导致 `csv.DictReader` 的第一个键名被污染、`json.loads` 直接报错。正确：读 `utf-8-sig`；排查时先 `print(repr(text[:5]))`。

5. **`errors="ignore"` 掩盖数据损坏** —— 坏字节被静默丢弃，CSV 里往往丢的正是分隔符，导致字段错位且极难定位。正确：`"strict"` 显式失败，或 `"replace"` + 统计坏字节数。

6. **以为 `with` 退出就落盘了** —— `with` 只 `flush` 到 OS 页缓存，断电/容器被 kill 仍会丢。正确：需要抗断电就 `flush()` + `os.fsync(f.fileno())`。

7. **`fsync` 放在循环里** —— 每条记录都等磁盘确认，吞吐量断崖式下降。正确：批量提交或定时组提交；只读元数据不同步时用 `os.fdatasync`。

8. **`os.rename` 覆盖已存在文件** —— Windows 上目标存在会直接抛错，跨平台行为不一致。正确：统一用 `os.replace`。

9. **临时文件放在别的目录** —— `os.replace` 的原子性只在**同一文件系统**内成立，跨盘退化为"复制 + 删除"，中途崩溃仍可能留下损坏文件。正确：临时文件与目标**同目录**（`tempfile.mkstemp(dir=...)`）。

10. **`f.write()` 返回值被忽略** —— `write` 返回写入的**字符数**（不是字节数），短写不会自动重试。正确：需要确认写入完整时检查返回值，或改用 `f.write` 后 `flush` + 校验长度。

11. **文本模式设 `buffering=0`** —— 只有二进制模式允许无缓冲，文本模式会抛 `ValueError`。正确：文本模式用默认或 `buffering=1`（行缓冲）。

12. **`for line in f` 内部再调 `f.read()`** —— 迭代器与 `read` 共用文件位置，会读到错乱数据；`read` 还会把剩余内容一次性读进内存，破坏恒定内存的初衷。正确：迭代时只用当前行。

13. **`json.dumps` 的 `ensure_ascii` 被误解为编码设置** —— 它只决定非 ASCII 字符是否转义成 `\uXXXX`，与文件编码无关。正确：要中文可读用 `ensure_ascii=False`；文件编码另行显式指定 `utf-8`。

14. **`json.dump` 直接写 `datetime` / `Decimal`** —— 会抛 `TypeError`。正确：传 `default=` 自行序列化，或先转成 ISO 字符串 / `str`。

15. **拿 pickle 做跨服务或跨信任边界的数据交换** —— `pickle.loads` 可执行任意代码，等同于 `eval`。正确：跨边界用 JSON / Protobuf / Parquet；pickle 只用于本机可信的临时缓存。

16. **`f.readlines()` 处理大文件** —— 峰值内存 O(文件大小 + 每行对象开销)，10 GB 日志会直接 OOM。正确：`for line in f` 或 `f.read(chunk)` 循环。

17. **用标准 JSON 追加日志** —— 一个 JSON 数组必须整体合法，无法在末尾追加一行。正确：改用 JSON Lines（NDJSON），一行一个对象，可追加、错误局部化。
