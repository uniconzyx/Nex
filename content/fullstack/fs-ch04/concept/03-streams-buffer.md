# fs-ch04 · 流、背压与 Buffer 编码


## 一、Stream 流控与背压（highWaterMark / write 返回值 / drain）

流是处理「连续数据」的抽象：Readable 生产数据、Writable 消费数据、Transform 既是又是。背压是有界缓冲下的反馈机制：消费者慢于生产者时，靠 write() 的布尔返回值 + drain 事件形成负反馈，使内存占用有界。

### 🧑‍💻 程序员视角
- 大文件/大响应用流而非一次 readFile 进内存；pipe() 自动处理背压，手动转发流时必须检测 write() 返回值。
- Writable.write() 返回 false 表示内部缓冲区已满：此时暂停数据源（source.pause()），监听 'drain' 事件后再 resume()。
- highWaterMark 控制缓冲上限（默认字节流 16KB、对象流 16 个）；忽略 false 继续狂写会无限增长内存直至 OOM。

### 🎓 博士生视角
- 背压是流控理论中的反馈闭环：当 buffered >= highWaterMark，write 返回 false 触发上游降速；消费者消费（cb 确认）后缓冲下降，降到阈值下时触发 'drain'，上游恢复——这正是「有界缓冲队列」在流抽象上的体现。
- highWaterMark 是阈值而非硬上限：一次 write 可能短暂超过它（允许写完当前 chunk），返回 false 是「将满」信号而非「已满拒绝」。
- pipe() 内部已实现这套反馈：自动在 false 时 pause 源、drain 时 resume，因此工程上优先用 pipe 而非手写转发。

### 📚 考研者视角
- 常考：背压是什么、如何触发、write() 返回值含义、drain 何时触发、为什么大文件要用流。
- 易错：认为 write() 返回 false 等于「写入失败」（其实 chunk 已入缓冲，只是提示降速）；认为 pipe 不需要关心背压（其实已内置）。
- 经典陈述：背压让生产/消费速率解耦，内存占用与数据总量无关、只与 highWaterMark 成正比。

## 二、Buffer 与编码（UTF-8 多字节切片坑）

Buffer 是字节视图（Uint8Array 子类），与字符串不同：字符串按码点索引，Buffer 按字节索引。UTF-8 用 1–4 字节变长编码一个码点，按字节切片可能在码点中间切断，产生替换符（U+FFFD）乱码。

### 🧑‍💻 程序员视角
- 处理文本永远按字符（string 的 slice/索引）而非字节切分；Buffer.from(str).subarray 在 multibyte 字符中间切断会得到替换符。
- 正确做法：用字符串 slice、或用 StringDecoder 累积解码（它会跨 chunk 拼接不完整多字节序列，等齐了再输出）；显式指定编码（utf8/gbk）。
- JSON 序列化含中文时按 UTF-8 字节，传输/存储不要对其再做字节切片；网络分包要按协议边界而非任意字节偏移。

### 🎓 博士生视角
- UTF-8 是变长编码：ASCII 1 字节、常用汉字 3 字节、部分字符 4 字节；Buffer.subarray 是纯字节偏移切片，不感知码点边界。
- 在码点中间切断得到非法字节序列，解码器按「最大子串」原则替换为 U+FFFD（Unicode 替换符），该信息不可逆丢失——这是编码层而非 Buffer 层的特性。
- StringDecoder 之所以能避免乱码，是因为它在内部持有「未完成的尾随字节」，等下一个 chunk 补齐码点后再解码，本质是流式的码点对齐。

### 📚 考研者视角
- 常考：为什么 Buffer 切片会乱码、UTF-8 变长特性、如何安全截取字符串、编码与解码关系。
- 易错：认为 Buffer 长度等于字符数（实际是字节数）；认为 subarray 像 string.slice 一样按字符切。
- 经典陈述：中文截断乱码根因是「按字节切分破坏了 UTF-8 码点边界」，修复用字符级 API 或 StringDecoder。
