# sys：命令行参数、导入路径与标准流

## 1. `sys.argv`：最原始的入参通道

`sys.argv` 是一个列表：`argv[0]` 是脚本名（或 `-c` / `-m` 时的占位），之后是用户给的参数，**全部是字符串**。

```python
import sys

if len(sys.argv) < 3:
    sys.stderr.write("usage: tool.py <in> <out>\n")
    sys.exit(2)                     # 约定：2 表示「用法错误」

src, dst = sys.argv[1], sys.argv[2]
```

自己解析 `argv` 很快会失控（`-v`、`--verbose`、`--out=path`、`--out path`、可选参数、互斥参数……）。标准库 `argparse` 一次解决：

```python
import argparse

ap = argparse.ArgumentParser(prog="tool", description="清洗日志")
ap.add_argument("src", help="输入文件")
ap.add_argument("-o", "--out", default="-", help="输出文件，默认 stdout")
ap.add_argument("-v", "--verbose", action="store_true")
ap.add_argument("--min-level", choices=["INFO", "WARN", "ERROR"], default="INFO")
args = ap.parse_args()
```

`argparse` 自动处理 `-h/--help`、类型转换、`choices` 校验、缺参数时的错误码（**退出码 2**）。手工解析的代码通常长 3 倍，且错误码随手写 1，与 POSIX 约定不符。

**退出码约定**（面试常问）：

| 码 | 含义 |
|---|---|
| `0` | 成功 |
| `1` | 通用错误（业务失败） |
| `2` | 命令行用法错误（`argparse` 默认） |
| `126` / `127` | 权限不足 / 命令未找到（shell 层） |
| `128+n` | 被信号 `n` 杀死（如 `130` = Ctrl-C 的 SIGINT） |

## 2. `sys.path` 与导入解析顺序

`import foo` 时，Python 按 `sys.path` 的顺序查找：

1. 脚本所在目录（或 `-c` 时是 cwd，`-m` 时是 cwd）；
2. `PYTHONPATH` 环境变量里的目录；
3. 标准库目录；
4. `site-packages`（第三方包）。

```python
import sys

print(sys.path[0])           # 通常是脚本目录
sys.path.insert(0, "/opt/lib")   # 把自定义目录提到最前
```

**危险点**：`sys.path` 里脚本目录排第一，意味着**同目录下任何同名 `.py` 会遮蔽标准库**。命名一个 `json.py`、`random.py`、`types.py` 放在项目根，就会把标准库模块顶掉，报出莫名其妙的 `AttributeError`。这是新手最常见的「幽灵 bug」。

正确做法：项目用**包结构**（`src/mypkg/`）+ `pip install -e .`，而不是靠 `sys.path.append` 打补丁。

## 3. 标准流与输出重定向

| 流 | 用途 | 缓冲行为 |
|---|---|---|
| `sys.stdin` | 标准输入 | 通常行缓冲 |
| `sys.stdout` | 正常输出 | **管道/文件时块缓冲**，TTY 时行缓冲 |
| `sys.stderr` | 错误与日志 | **无缓冲**（或行缓冲），立刻可见 |

「管道时块缓冲」是个实战坑：`python tool.py | grep foo` 时，`print()` 的输出会攒到 8KB 才刷，导致你**看不到实时进度**。解法：

```python
print("processing...", flush=True)      # 单次强制刷新
# 或启动时：python -u tool.py
```

`sys.stdout.isatty()` 可以判断输出是否连到终端——**给终端上色、给管道纯文本**的标准做法：

```python
if sys.stdout.isatty():
    RED, RESET = "\033[31m", "\033[0m"
else:
    RED = RESET = ""
```

## 4. 解释器信息与编码

```python
import sys

sys.version            # '3.13.12 (main, ...)'
sys.version_info       # sys.version_info(major=3, minor=13, ...) —— 用它做版本判断
sys.platform           # 'win32' / 'linux' / 'darwin'
sys.getdefaultencoding()   # 'utf-8'（Python 3 固定）
sys.getfilesystemencoding()  # 文件系统编码，Windows 上是 'utf-8'（3.6+）
```

版本判断要用 `sys.version_info`，**不要**解析 `sys.version` 字符串：

```python
if sys.version_info >= (3, 11):
    ...   # 用 tomllib
```

Windows 控制台的历史遗留：Python 3.6 之前 `sys.stdout.encoding` 是 `cp936`（GBK），打印 emoji 会 `UnicodeEncodeError`。现在（3.15 起将默认 UTF-8）多数情况已好，但**跨平台脚本仍应避免在 stdout 上打印非 ASCII 的装饰性字符**。

## 5. 速记

- 参数 → `argv[0]` 是脚本名；正式项目用 `argparse`
- 退出码 → 成功 0、业务错 1、用法错 2、`128+n` 表示信号
- 导入 → `sys.path` 首项是脚本目录，**别在项目根放同名标准库文件**
- 缓冲 → 管道下 stdout 块缓冲；用 `flush=True` 或 `-u`
- 版本判断 → `sys.version_info`，不是 `sys.version` 字符串

## 三视角解析

### 🧑‍💻 程序员视角

**排查顺序**：脚本「在终端能跑，在 CI 挂掉」→ 先查三样：① cwd（用 `Path.cwd()` 打印）；② `sys.path[0]`；③ stdout 缓冲导致日志缺失（加 `-u` 再看）。三者覆盖了绝大多数 CI 环境差异。

**工程决策**：命令行工具一律 `argparse`，并给每个参数写 `help`——这比写 README 更有效，因为 `--help` 永远与代码同步。日志**写 stderr**，数据**写 stdout**，这样 `cmd > out.txt` 只落数据，用户能在终端看到进度。这是 Unix 工具的基本礼仪，很多自研脚本违反它。

**性能**：`sys.stdout` 是 `TextIOWrapper`，每次 `print` 有一次编码与缓冲检查。处理百万行输出时，用 `sys.stdout.write("\n".join(lines))` 批量写比逐行 `print` 快数倍；但**只有在 profile 显示 I/O 是瓶颈时才这么做**。

### 🎓 博士生视角

**为什么 `sys.path` 是「列表即配置」的反模式**：把导入搜索路径暴露为一个可变全局列表，意味着**模块解析依赖运行时的、顺序敏感的可变状态**。这与「静态可得」原则冲突：同一个 `import foo` 在不同入口脚本下可能解析到不同模块。现代方案（`importlib.metadata`、显式包安装、`pyproject.toml` 声明依赖）本质上是在**恢复静态可分析性**，让工具链（mypy、打包器）能确定性地知道依赖图。

**缓冲策略的信息论视角**：块缓冲把 $n$ 次小写合并为 $\lceil n \cdot s / B \rceil$ 次系统调用（$s$ 为单条大小、$B$ 为缓冲区大小），系统调用开销从 $O(n)$ 降到 $O(ns/B)$。代价是**引入了延迟**——你无法在写满缓冲区前看到输出。这是吞吐与延迟的经典取舍：`flush=True` 就是「用吞吐换延迟」。

**退出码的语义层次**：POSIX 把退出码定义为 8 位（0–255），其中 `0` 与「成功」的绑定是**约定**而非语言语义。`128+n` 表示信号是 shell 的编码约定，让「正常退出」与「被信号终止」在同一个整数字段里可区分——这是把两种正交状态压缩进一个字节的设计。

### 📚 考研者视角

**笔试常见问法与口径**：

1. 「`sys.argv` 里各元素是什么类型」——**全是字符串**，包括看起来像数字的参数；要转类型必须显式 `int(...)`。
2. 「`import foo` 时 Python 去哪找 foo」——按 `sys.path` 顺序：脚本目录 → `PYTHONPATH` → 标准库 → `site-packages`。这是标准答法，顺序必须说全。
3. 「为什么不要在项目根目录放 `json.py`」——因为脚本目录在 `sys.path` 首位，会**遮蔽标准库同名模块**，导致其他库的 `import json` 拿到你的文件。
4. 「stdout 与 stderr 的区别」——答「用途（数据 vs 诊断）**与**缓冲行为（块缓冲 vs 无缓冲）」两点，只说用途会被追问。
5. 易错口径：`sys.exit(0)` 与**正常函数返回**的区别在于前者会抛 `SystemExit`，能被 `try/except BaseException` 捕获，从而被中间层拦住。
