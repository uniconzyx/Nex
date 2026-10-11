# os 与 pathlib：路径对象、目录遍历与跨平台

## 1. 路径不是字符串：`pathlib` 把路径变成一等对象

早期 Python 用 `os.path` 把路径当**普通字符串**处理：

```python
import os

p = os.path.join("data", "raw", "a.csv")
base = os.path.splitext(os.path.basename(p))[0]
```

问题在于：路径的语义（分隔符、扩展名、父目录、是否绝对）全靠**函数约定**拼出来，字符串本身不带信息。`pathlib` 把它们变成 `Path` 对象的方法与属性：

```python
from pathlib import Path

p = Path("data") / "raw" / "a.csv"   # 运算符重载：/ 就是 join
p.name        # 'a.csv'
p.stem        # 'a'
p.suffix      # '.csv'
p.parent      # Path('data/raw')
p.parts       # ('data', 'raw', 'a.csv')
p.is_absolute()
```

三条关键差异：

1. **`/` 运算符是跨平台安全的**。`Path("a") / "b"` 在 Windows 上用 `\`，在 Linux 上用 `/`；手写 `"a" + "/" + "b"` 在 Windows 的部分 API 上会碎。
2. **`Path` 不可变**。所有「修改」都返回新对象：`p.with_suffix(".json")` **不会**改变 `p`。这让你可以把 `Path` 当值传递，不必担心被下游改掉。
3. **`Path` 与 `str` 不混用**。需要字符串时显式 `str(p)`，需要 `Path` 时 `Path(s)`。`open()` 两者都收，但很多第三方 SDK（老版本 `requests` 的某些参数、某些 C 扩展）只认 `str`——混用会在边界处炸。

## 2. 目录遍历：`walk` / `iterdir` / `rglob` 怎么选

| 需求 | 写法 | 说明 |
|---|---|---|
| 只列本层（文件 + 目录） | `Path(d).iterdir()` | 返回迭代器，**不排序**；要顺序稳定需自己 `sorted()` |
| 递归匹配模式 | `Path(d).rglob("*.csv")` | 等价 `glob("**/*.csv")`，只匹配文件与目录名 |
| 自顶向下逐层处理 | `os.walk(d)` | 返回 `(root, dirs, files)` 三元组，**可以原地修改 `dirs` 来剪枝** |

`os.walk` 独有的价值是**剪枝**：

```python
import os

for root, dirs, files in os.walk("proj"):
    dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules"}]
    for f in files:
        ...
```

注意 `dirs[:] = [...]` 是**原地替换**。写成 `dirs = [...]` 只会重绑局部变量，`walk` 看不到——这是一个静默失效的经典坑。

`rglob` 的返回值也**不保证顺序**：底层依赖 `os.scandir` 的目录顺序，不同文件系统不一样。任何「结果必须可复现」的场景（测试、快照比对、CI）都要显式 `sorted()`：

```python
files = sorted(Path("data").rglob("*.csv"))   # 按字典序
```

## 3. 环境变量与进程信息

```python
import os

os.environ["APP_MODE"]                    # KeyError 若不存在
os.environ.get("APP_MODE", "dev")         # 推荐：给默认值
os.getenv("APP_MODE", "dev")              # 等价写法

os.getpid()                               # 当前进程号
os.cpu_count()                            # 逻辑核数
os.name                                   # 'nt'(Windows) / 'posix'
```

**读取环境变量一律用 `.get()` 带默认值**。用 `os.environ["X"]` 会在变量缺失时抛 `KeyError`，而这通常发生在生产环境（12-Factor 应用靠环境变量注入配置），本地跑得欢、上线就崩。

写环境变量时注意：`os.environ` 是**进程内**的映射，改它只影响当前进程与其子进程，**不会**写回 shell。

## 4. 跨平台陷阱清单

| 陷阱 | 错误写法 | 正确写法 |
|---|---|---|
| 硬编码分隔符 | `open("data\\a.csv")` | `Path("data") / "a.csv"` |
| `Path` 直接当字符串用 | `"prefix" + str_path` | `f"prefix{str(str_path)}"` 或 `os.fspath(p)` |
| 依赖相对路径 | `open("config.json")` | 以 `Path(__file__).parent` 为基准 |
| 假定遍历有序 | `next(Path(d).iterdir())` | `sorted(Path(d).iterdir())[0]` |
| Windows 反斜杠转义 | `"C:\new\test"`（`\n` `\t` 被转义） | `r"C:\new\test"` 或 `Path(r"C:/new/test")` |

最后一条尤其阴险：`"C:\new\test"` 里的 `\n` 是**换行符**、`\t` 是**制表符**，字符串内容早已不是你以为的路径。要么用 raw string，要么用 `/`（Windows 的 API 同时接受 `/` 与 `\`）。

`Path(__file__).parent` 这个写法值得背下来：它让脚本的「相对路径」变成「相对脚本文件」的绝对路径，从而**不受启动时工作目录影响**。CI、systemd、cron 启动脚本时的 cwd 往往与你在终端里手敲时不同，这是「本地能跑、定时任务崩」的头号原因。

## 5. 速记

- 路径 → `pathlib`；`/` 是 join；`Path` 不可变；`str(p)` 才转字符串
- 遍历 → 本层用 `iterdir()`，模式匹配用 `rglob()`，要剪枝用 `os.walk` + `dirs[:] = [...]`
- 顺序 → 任何时候都 `sorted()`，别赌文件系统
- 环境变量 → 一律 `.get(k, default)`
- 基准目录 → `Path(__file__).parent`，别赌 cwd

## 三视角解析

### 🧑‍💻 程序员视角

**排查顺序**：脚本报 `FileNotFoundError` 时，先打印 `Path.cwd()` 与 `Path(__file__).resolve()`，**十次有八次是 cwd 不符预期**，而不是文件真丢了。其次检查路径里有没有被转义的 `\t` / `\n`（把路径 `repr()` 出来看）。

**工程决策**：新项目一律 `pathlib`；只有在对接「只接受 `str` 的老 SDK」时才在边界处 `str(p)`。目录遍历若涉及大目录树（>10 万文件），`rglob` 会一次性构建生成器但底层 `scandir` 仍是流式，内存可控；但**不要**写 `list(rglob(...))`——那等于把整棵树读进内存。

**性能**：`Path` 的每次 `/` 都会新建对象。热循环里拼 10 万次路径时，先拼成字符串再一次性 `Path()` 会快一些；但这是「先有 profile 证据再优化」的场景，默认别提前操心。

### 🎓 博士生视角

**路径的抽象层级**：Unix 把一切资源建模为文件，路径因此是**字符串到 inode 的一个映射函数**；Windows 则引入盘符与 UNC 前缀，语义空间不同。`pathlib` 用 `PurePath`（纯词法运算，不做 I/O）与 `Path`（继承 `PurePath`，带 I/O）分层，本质是把「路径的**语法**」与「路径的**语义解析**」分离，这正是编译原理里「词法 vs 语义」在标准库上的投影。

**剪枝的本质**：`os.walk` 允许修改 `dirs` 列表，等价于在**深度优先遍历中动态改变后继集合**。这意味着遍历顺序不影响正确性但影响复杂度——剪掉一个含 $k$ 个节点的子树，整体从 $O(n)$ 降到 $O(n-k)$。

**为什么遍历顺序不可依赖**：`scandir` 返回顺序取决于底层 `readdir(3)`，而后者在不同文件系统（ext4 的 htree、NTFS 的 B+ 树、NFS 的服务端顺序）上不同，甚至同一目录在**增删文件后**顺序就会变。所以「顺序」不是路径这个抽象的一部分——把它当契约就是错的。

### 📚 考研者视角

**笔试常见问法与口径**：

1. 「`os.path` 与 `pathlib` 的区别」——标准答法从**类型抽象**切入（字符串 vs 对象），再举 `/` 运算符、不可变性、跨平台安全三点；不要只答「写法更简洁」。
2. 「如何遍历一个目录下的所有 `.py` 文件」——`Path(d).rglob("*.py")` 一行即可，面试官常追问「要不要排序」「要不要跳过 `__pycache__`」，这两点必须主动提。
3. 「`os.walk` 的 `dirs` 为什么能剪枝」——答「这是**原地修改可变列表**，而不是重绑变量」，用 `dirs[:] = [...]` 与 `dirs = [...]` 的差异作答。
4. 易错口径：**`pathlib.Path` 不可变**，`p.with_suffix(".json")` 返回新对象，原对象不变——这是最常考的细节。
