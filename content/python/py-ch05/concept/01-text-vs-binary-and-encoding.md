# 文本模式与二进制模式：编码、换行与 BOM

## 1. 两种模式，两套世界

`open()` 的 `mode` 决定了 Python 给你的是 **`str`** 还是 **`bytes`**：

| 模式 | 读到的类型 | 是否做编码转换 | 是否做换行转换 |
|---|---|---|---|
| `"r"` / `"rt"` | `str` | 是（按 `encoding`） | 是（按 `newline`） |
| `"rb"` | `bytes` | 否 | 否 |
| `"w"` / `"wt"` | 写入 `str` | 是 | 是 |
| `"wb"` | 写入 `bytes` | 否 | 否 |

关键结论：**文本模式是有状态的编解码器**，二进制模式是**字节搬运工**。
凡是「字节层面有语义」的场景（图片、压缩包、协议报文、BOM、CRLF），
一律用 `"rb"` / `"wb"`，否则会被自动转换悄悄改坏。

```python
# 危险：文本模式 + 通用换行，会把 \r\n 统一成 \n
with open("proto.txt", "r") as f:
    data = f.read()          # 原始 \r\n 已丢失

# 正确：需要原始字节就用二进制
with open("proto.txt", "rb") as f:
    data = f.read()          # 原样保留
```

## 2. `encoding` 必须显式写

不写 `encoding` 时，Python 使用 **`locale.getpreferredencoding(False)`**，
即跟随操作系统区域设置。于是同一份代码：

- 在 Linux 容器（默认 UTF-8）读出中文正常；
- 在中文 Windows（默认 GBK / CP936）读出 `UnicodeDecodeError` 或乱码。

这是「本地能跑、上线就炸」的经典成因。**规则：任何文本文件读写都显式写 `encoding="utf-8"`。**
（PEP 686 提议将默认编码改为 UTF-8，但在当前主流版本中仍未生效。）

## 3. 换行符与 `newline` 参数

文本模式的**通用换行（universal newlines）**会把 `\r\n`、`\r`、`\n` 统一翻译成 `\n`。
写入时又把 `\n` 翻译成 `os.linesep`。

```python
# 想让 \n 原样写出（例如生成 CSV / HTTP 报文），必须禁用翻译
with open("out.csv", "w", encoding="utf-8", newline="") as f:
    ...
```

`csv` 模块文档明确要求 `newline=""`：否则 Windows 上每个字段分隔符后可能多出一个 `\r`，
产生空行。

## 4. BOM：看不见的三个字节

UTF-8 BOM 是文件开头的 `EF BB BF`。它能被 **`utf-8-sig`** 编解码器识别并剥离：

```python
# 读到 "中文" 却显示 "\ufeff中文" —— 说明文件带 BOM 而用了 "utf-8"
with open("from_excel.csv", "r", encoding="utf-8-sig") as f:
    text = f.read()       # \ufeff 被自动去掉
```

反过来，如果**必须**产出带 BOM 的文件（给旧版 Excel 打开 CSV），就用 `utf-8-sig` 写。
第一个字符是 `\ufeff` 是 BOM 污染最典型的表现，排查时先 `print(repr(text[:5]))`。
### 🧑‍💻 程序员视角
## 5. `errors` 策略：遇到坏字节怎么办

`open(..., errors=...)` 有五档，最常用三档：

| 取值 | 行为 | 适用 |
|---|---|---|
| `"strict"`（默认） | 直接抛 `UnicodeDecodeError` | 数据必须完整，宁可失败 |
| `"replace"` | 无法解码的字节替换成 `\ufffd` | 展示/日志，允许有损 |
| `"ignore"` | 直接丢弃坏字节 | **危险**：会静默丢内容、破坏列对齐 |

`"ignore"` 能"让程序跑通"，但它丢掉的字节在 CSV 里往往是一个分隔符，
整行字段因此错位——排查成本极高。生产代码优先 `"strict"` + 显式报错，
或 `"replace"` + 记录坏行数。
### 🎓 博士生视角
## 6. 一次读写的内存代价

`f.read()` 把整个文件读进内存：峰值内存 ≈ 文件大小 × (1 + 解码后膨胀系数)。
UTF-8 中文每字符 3 字节，但解码成 `str` 后每字符固定占 1 个「码点」，
CPython 里按最宽字符选择 1/2/4 字节表示，因此**峰值很可能高于文件自身大小**。

恒定内存的做法是**迭代**：

```python
with open("big.log", "r", encoding="utf-8") as f:
    for line in f:            # 逐行，缓冲区级别复用
        process(line)         # 内存 O(单行最大长度)
```

注意：`for line in f` 用的是内部缓冲区，**不要**在其内部再调用 `f.read()`，
否则会读到位置错乱的数据。
### 📚 考研者视角
## 三视角解析

### 🧑‍💻 程序员视角

- **决策顺序**：先问「这是字节还是文本？」→ 图片/压缩包/协议一律 `rb`；
  再问「谁写的这个文件？」→ 对方平台决定要不要处理 BOM 与 CRLF。
- **排查乱码三步**：① `repr(text[:10])` 看有没有 `\ufeff`；
  ② `print(chardet/from_bytes(bytes).best())` 看真实编码；
  ③ 对比 `len(open(...,'rb').read())` 与解码后长度，判断是否有 `\ufffd`。
- **上线守则**：所有 `open()` 显式写 `encoding=` 与 `newline=`；
  CI 里加一条 lint 规则禁止无 `encoding` 的 `open`。

### 🎓 博士生视角

- 文本模式本质是一个 **有状态转码器**：`io.TextIOWrapper` 包在 `BufferedReader` 之上，
  内部持有增量解码器（`codecs.IncrementalDecoder`）——这也是为什么它能跨 read 调用
  正确处理被切断的多字节字符。
- 通用换行是一个**规范化（normalization）**过程，不可逆：`\r\n → \n` 后无法还原原始
  行尾风格。需要无损就用二进制模式自己做行分割。
- BOM 的历史成因是 UTF-16/UTF-32 的字节序歧义；UTF-8 本身无字节序问题，
  但为了兼容旧 Windows 软件仍被打上 `EF BB BF`，于是成为一个纯粹的兼容性负担。

### 📚 考研者视角

该方向（Python 工程）非 408 统考科目，考察口径为**笔面工程题**，标准问法与易错点：

- **标准问法**：「`open` 的文本模式和二进制模式有什么区别？」答题要落到
  「返回类型（str/bytes）+ 是否转码 + 是否换行规范化」三点，缺一即不完整。
- **易错口径**：
  1. 误以为「默认编码就是 UTF-8」——实际是 locale，这是最常见的错误。
  2. 误以为 `"w"` 会追加——`"w"` 会**截断**文件，追加要用 `"a"`。
  3. 误以为二进制模式"更快"——它只是不转码，性能差异随数据而定，不是考点本质。
- **记忆锚点**：**「文本是解码后的世界，二进制是原始的世界」**。
