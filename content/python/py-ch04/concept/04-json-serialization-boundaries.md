# json：序列化边界、参数与自定义编码

## 1. 类型映射表：什么能过、什么会炸

`json` 模块只认识 JSON 规范里的 6 种类型。Python 类型到 JSON 的映射：

| Python | JSON | 方向 |
|---|---|---|
| `dict` | `object` | 双向 |
| `list` / `tuple` | `array` | Python→JSON 都成数组；JSON→Python **只回到 `list`** |
| `str` | `string` | 双向 |
| `int` / `float` | `number` | 双向（**`int` 无精度上限，但 JS 侧只有 53 位**） |
| `True` / `False` | `true` / `false` | 双向 |
| `None` | `null` | 双向 |

**会炸的类型**（`TypeError: Object of type X is not JSON serializable`）：`set`、`datetime`、`bytes`、自定义类实例、`complex`、以及**非字符串的 dict key**。

```python
import json

json.dumps({1: "a"})          # '{"1": "a"}'  ✅ int key 被静默转成字符串
json.dumps({(1, 2): "a"})     # ❌ TypeError：tuple key 不能转
```

注意第一行的**静默转换**：`int` 键被转成 `"1"`。反序列化回来是 `{"1": "a"}`——**类型已经变了**。往返一圈不相等（`{1: "a"} != {"1": "a"}`），这是数据管道里最隐蔽的一致性 bug 之一。**约定：JSON 的 key 只用字符串**。

另一个静默转换：`float('nan')` / `float('inf')` 会被写成 `NaN` / `Infinity`——**这不是合法 JSON**，只是 Python 的扩展。标准 JSON 解析器（Go、Rust、JS 的 `JSON.parse`）会直接拒收。

```python
json.dumps(float("nan"))                    # 'NaN'（非法 JSON！）
json.dumps(float("nan"), allow_nan=False)   # ✅ ValueError，早失败
```

对外接口**一律设 `allow_nan=False`**，把非法值在序列化时就拦下，而不是等对方解析崩。

## 2. `dumps` / `dump` 常用参数

```python
import json

data = {"b": 1, "a": [1, 2], "note": "中文"}

json.dumps(data, ensure_ascii=False)     # 保留中文（默认 True 会转成 \\u4e2d\\u6587）
json.dumps(data, indent=2)               # 缩进美化（给人和 git diff 看）
json.dumps(data, sort_keys=True)         # 键排序（让 diff 稳定）
json.dumps(data, separators=(",", ":"))  # 紧凑：去掉空格，省带宽
```

两个工程要点：

- **`ensure_ascii=False`**：默认 `True` 会把所有非 ASCII 转义成 `\uXXXX`，文件体积大 6 倍且人不可读。写文件/传给现代前端时都该关掉（需保证编码为 UTF-8）。
- **`sort_keys=True` + `indent=2`**：这是**让 JSON 可 diff** 的组合。配置文件、快照测试里必须开，否则键顺序随机变动会让 diff 全是噪声。

`dump` / `load` 是「写到文件对象」的版本，还多一个 `json.dump(obj, f, ensure_ascii=False)` 的常见误用——**忘了开 `ensure_ascii=False` 导致中文全变 `\u` 序列**。

## 3. 无法直接序列化时：`default` 与自定义编码器

给 `default` 传一个函数，遇到不认识的类型就调用它：

```python
import json
from datetime import datetime, timezone

def enc(o):
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, (set, frozenset)):
        return sorted(o)              # 排序保证确定性！
    raise TypeError(f"不可序列化: {type(o).__name__}")

json.dumps({"t": datetime.now(timezone.utc), "tags": {"b", "a"}}, default=enc, ensure_ascii=False)
# '{"t": "2026-10-07T...", "tags": ["a", "b"]}'
```

三点必须注意：

1. **`set` 转 list 前一定要 `sorted()`**。`set` 迭代顺序依赖哈希，同一份数据在不同进程（`PYTHONHASHSEED` 随机）里顺序可能不同 → 输出不可复现 → 测试偶发失败。
2. **`default` 里抛 `TypeError`** 是规范做法，能被上层识别为「真的不支持」，而不是返回 `None` 悄悄丢数据。
3. 更结构化的写法是继承 `json.JSONEncoder` 并覆写 `default`，然后 `json.dumps(obj, cls=MyEncoder)`。适合多处复用。

## 4. `json` vs `pickle`：为什么不要用 pickle 传数据

| 维度 | `json` | `pickle` |
|---|---|---|
| 跨语言 | ✅ 通用 | ❌ 只有 Python |
| 类型覆盖 | 只有 6 种 | 几乎任意 Python 对象 |
| 安全性 | ✅ 纯数据 | ❌ **反序列化可执行任意代码** |
| 人类可读 | ✅ | ❌ 二进制 |
| 版本兼容 | 稳定 | 依赖类定义（改名即失效） |

`pickle` 的安全问题是致命的：`pickle.loads(untrusted_bytes)` 可以**执行任意代码**（通过 `__reduce__` 构造）。所以：

- **跨进程/跨网络/落盘的数据一律 `json`**（或 msgpack / protobuf）；
- `pickle` 只用于**同机、同版本、可信来源**的临时缓存（如 `multiprocessing` 内部通信）；
- 存模型权重那种场景用专门的格式（`safetensors` 等），不要用 `pickle` 直接 dump。另外，`json` 也不支持循环引用（`a["self"] = a` 会 `ValueError`），`pickle` 支持——但需要循环引用的数据本来就不适合序列化。

## 5. 速记

- 只有 6 种类型能过；`set` / `datetime` / `bytes` / 非 str 键（除 int）都会炸
- `int` 键被**静默转字符串**；往返不相等 → JSON key 只用字符串
- `NaN` / `Infinity` 非法 → 对外接口设 `allow_nan=False`
- `ensure_ascii=False` 保中文；`sort_keys=True` + `indent=2` 让 diff 稳定
- 自定义类型用 `default=`；`set` 转 list **必须 `sorted()`** 保证可复现
- 跨进程/跨网络用 `json`；`pickle` 只用于可信同版本场景

## 三视角解析

### 🧑‍💻 程序员视角

**排查顺序**：接口报「JSON 解析失败」→ 先看**是不是 `NaN`/`Infinity`**（Python 能写、别的语言不能读），再看**时间字段格式**（ISO 带时区 vs 无时区字符串），最后看**键类型**（有没有非字符串键被静默转掉）。这三个覆盖了 90% 的跨语言 JSON 事故。

**工程决策**：定义 Pydantic / dataclass 模型而不是到处手写 `json.dumps(dict)`——类型校验发生在**边界**而不是散落各处。序列化时统一封装一个 `to_json(obj)` 工具函数（固定 `ensure_ascii=False` / `sort_keys=True` / `allow_nan=False`），避免每次调用都重新想一遍参数。**`json.dumps` 的参数组合是一种团队约定，应该固化到代码里而不是靠记忆**。

**性能**：解析大 JSON 时 `json.loads` 是 C 实现的，通常够快；瓶颈常在**构造大量中间对象**。超大文件（>100MB）考虑流式解析（`ijson`）或换行分隔的 JSONL（一行一条，可逐行解析、可追加写）。写 JSON 时 `separators=(",", ":")` 能省 10%–20% 体积。

### 🎓 博士生视角

**JSON 的类型系统是不完备的**：JSON 规范只有 object / array / string / number / boolean / null 六种，没有日期、没有集合、没有二进制、没有精度语义。任何「用 JSON 表达富类型」的方案都必须在**编码约定**层面补齐（如 ISO 8601 表示时间、base64 表示二进制）——这就是为什么 API 设计里「约定」比「格式」更重要。JSON Schema 正是在做这件事：把隐含约定显式化。

**`int` 的精度断裂**：Python 的 `int` 是任意精度，JSON 规范对 number 的精度**没有规定**，而实际实现（JS `JSON.parse`）用 IEEE 754 双精度，只有 53 位有效整数位。于是 `json.dumps({"id": 9007199254740993})` 在 Python 侧无损，传到 JS 侧**静默变成** `9007199254740992`。这是「用 JSON 传大整数 ID」（如雪花算法 ID、Twitter ID）的经典事故——**解法是把 ID 序列化为字符串**。

**`pickle` 的可执行性从何而来**：`pickle` 的字节流本质是一段**虚拟机指令**（`pickle` opcodes），`REDUCE` 指令会调用可调用对象。这与「数据」的直觉定义冲突——它更像 **Lisp 的 `eval`**。任何「反序列化不可信数据」的设计都必须先解决这个信任边界问题，这与 Protobuf（纯 schema 驱动、无代码执行）的哲学相反。

### 📚 考研者视角

**笔试常见问法与口径**：

1. 「`json.dumps` 默认会不会转义中文」——**会**（`ensure_ascii=True` 是默认值），转成 `\uXXXX`；要保留中文需显式 `ensure_ascii=False`。
2. 「哪些 Python 类型不能直接 `json.dumps`」——`set` / `datetime` / `bytes` / 自定义对象 / tuple 作为**键**。注意 `tuple` 作为**值**是可以的（转成数组）。
3. 「`json` 和 `pickle` 的区别」——从**跨语言、类型覆盖、安全性**三个维度答，安全性必须提「`pickle` 反序列化可执行任意代码」。
4. 「为什么大整数 ID 传 JSON 会出错」——因为 JS 侧 `number` 是 IEEE 754 双精度，超过 $2^{53}$ 无法精确表示。
5. 易错口径：`json.loads` 把 JSON 数组**只会还原成 `list`**，不会还原成 `tuple`——即使你 dump 的是 tuple。往返类型不守恒。
