# csv 与 json：结构化文件的读写与边界

## 1. `csv`：为什么必须 `newline=""`

`csv.writer` 自己负责写 `\r\n`（RFC 4180 规定行尾是 CRLF）。
若文件用文本模式打开且**未**禁用换行翻译，Windows 上 `\n` 会被再翻译成 `\r\n`，
结果是每个字段后多出 `\r`，Excel 里表现为**空行或多出空列**。

```python
import csv

# ✓ 官方文档写法
with open("out.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["城市", "销量"])
    w.writerow(["北京", 120])

# 读回来同理
with open("out.csv", "r", encoding="utf-8", newline="") as f:
    for row in csv.reader(f):
        print(row)
```

**规则**：`csv` 模块的文件一律 `newline=""`，不解释。

### `DictReader` / `DictWriter` 与字段名

```python
with open("s.csv", encoding="utf-8-sig", newline="") as f:
    for rec in csv.DictReader(f):        # 首行自动作为键
        print(rec["城市"], rec["销量"])
```

注意 `DictReader` 读到的值**永远是 `str`**，`"120"` 不是 `120`。
需要数值必须自己 `int()` / `float()`，并处理空串与 `"N/A"`。

### 方言与分隔符探测

现实中的"CSV"可能是 TSV、分号分隔、带注释头。
`csv.Sniffer` 能做启发式探测，但它**不保证正确**，生产代码应当
**优先用显式配置**，探测只作为兜底并记录日志。
### 🧑‍💻 程序员视角
## 2. `json`：`ensure_ascii` 与编码

```python
import json

data = {"城市": "北京", "销量": 120}

# 默认 ensure_ascii=True：非 ASCII 被转成 \uXXXX 转义
print(json.dumps(data))                          # {"\u57ce\u5e02": "\u5317\u4eac", ...}
print(json.dumps(data, ensure_ascii=False))      # {"城市": "北京", ...}
```

两者**都合法**，只是可读性不同。要点：

- `json.dumps` 返回 `str`，**不涉及文件编码**；写文件时才需要 `encoding="utf-8"`。
- `json.dump(obj, f)` 底层把 `str` 交给 `f.write`，此时才受 `encoding` 影响。
- 想产出人可读的中文 JSON：`json.dump(..., ensure_ascii=False, indent=2)`。

### 类型侵蚀（round-trip 不保真）

JSON 只有 string / number / boolean / null / array / object 六种类型：

| Python | JSON | 读回 |
|---|---|---|
| `tuple` | array | **`list`**（元组信息丢失） |
| `int` key | string | **`str`**（键类型丢失） |
| `datetime` | 无法序列化 | 需自定义 `default=` |
| `float('nan')` | `NaN`（非法 JSON） | 其它语言解析器会报错 |

因此不要拿 JSON 当"通用对象持久化"，它只是**数据交换格式**。
### 🎓 博士生视角
## 3. 序列化格式的取舍

| 格式 | 可读性 | 类型保真 | 体积/速度 | 安全 |
|---|---|---|---|---|
| JSON | 高 | 低（6 种类型） | 中 | 高（纯数据） |
| CSV | 高 | 极低（全 `str`） | 小 | 高 |
| pickle | 无 | **高（任意对象）** | 小、快 | **危险**：反序列化即执行代码 |
| MessagePack / Parquet | 无 | 中高 | 小、快 | 高 |

**红线**：`pickle.loads` 对不可信数据等于 `eval`。
Web 服务、跨组织传输一律不用 pickle；需要类型保真且安全时选
Parquet（列存）、MessagePack、或 JSON + 显式 schema 校验。

### 为什么 CSV 全 `str` 反而"好"

CSV 的"无类型"使它在异构系统间**最不容易产生歧义**（代价是解析方必须自己定 schema）。
这也是数据分析场景下 CSV 长盛不衰的原因——类型推断交给读取方，
而不是隐含在文件里。
### 📚 考研者视角
## 4. 流式处理与内存

### 逐行读 CSV

```python
import csv

# 常量内存：适合超大文件
with open("huge.csv", encoding="utf-8", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    total = 0
    for row in reader:
        total += int(row[1])
```

### 增量写 JSON（JSON Lines）

标准 JSON 不支持流式追加（一个数组必须整体合法）。
需要流式场景改用 **JSON Lines（NDJSON）**：一行一个 JSON 对象。

```python
import json

with open("events.ndjson", "w", encoding="utf-8", newline="") as f:
    for ev in events:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
```

优点：可追加、可逐行处理、坏一行不影响其它行。
大数据/日志场景的事实标准。

### 编码与 BOM 的组合

| 场景 | 推荐 |
|---|---|
| 自己平台内部流转 | `encoding="utf-8"`, `newline=""` |
| 交给 Excel / Windows 软件 | 写 `utf-8-sig`（带 BOM），读 `utf-8-sig`（自动剥 BOM） |
| 与旧系统交换 | 显式 `gbk`，并 `errors="replace"` + 记录坏行 |

## 三视角解析

### 🧑‍💻 程序员视角

- **排查顺序**：CSV 打开有多余空行 → 检查 `newline=""`；
  中文乱码 → 检查 `encoding`；首字符异常 → 看是否 BOM（`\ufeff`）；
  数字变成字符串 → `DictReader` 不推断类型，自己 `int()`。
- **决策**：内部服务间传输优先 JSON（或 Protobuf）；给业务同学看的数据用 CSV；
  大数据场景用 Parquet；**永远不用 pickle 跨信任边界**。
- **踩坑**：`csv.writer` 与 `print` 混用同一文件会破坏格式；
  `json.dump` 遇到 `Decimal` / `datetime` 会直接抛 `TypeError`，需 `default=`。

### 🎓 博士生视角

- CSV 的规范（RFC 4180）本身很薄，现实中"方言"泛滥：
  分隔符、引号转义、行尾、编码、缺失值表示都无共识。
  这就是为什么"读 CSV"在工业界是一个需要配置而不是需要解析的问题。
- JSON 的类型系统是**封闭的六元组**，任何宿主语言的更丰富类型都必须
  投影到其上，投影必不单射 —— 这是 round-trip 不保真的根本原因，
  不是实现缺陷。
- JSON Lines 用"每行独立合法"换取了**可追加性**与**错误局部性**，
  代价是牺牲了整体结构校验（无法在文件层面表达嵌套数组）。

### 📚 考研者视角

非 408 统考内容，按**笔面工程题**口径：

- **标准问法**：「Python 读写 CSV 为什么建议 `newline=""`？」
  标准答题结构 = 「`csv` 模块自己写 `\r\n`；不禁用换行翻译时，
  Windows 上 `\n` 会被再翻译成 `\r\n`，导致多余回车与空行」。
- **易错口径**：
  1. 认为 `json.dumps` 的 `ensure_ascii` 影响文件编码 —— 它只影响**转义**，
     与编码无关。
  2. 认为 `csv` 会做类型推断 —— 全部是 `str`。
  3. 把 pickle 当作"更方便的 JSON" —— 它涉及**反序列化执行代码**的安全问题。
- **记忆锚点**：**「CSV 要 `newline=""`；JSON 只有六种类型；pickle 不可信不用」**。
