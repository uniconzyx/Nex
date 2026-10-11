# py-ch04 · 标准库陷阱清单

1. **`"C:\new\test"` 里的 `\n` 是换行符** —— 反斜杠转义在路径字符串里会静默生效，字符串内容早已不是你以为的路径。正确写法：`r"C:\new\test"`、`Path(r"C:/new/test")`，或用正斜杠 `"C:/new/test"`（Windows API 同样接受）。

2. **用 `os.environ["KEY"]` 读配置** —— 变量缺失时抛 `KeyError`，本地有值、线上没注入就崩。正确写法：`os.environ.get("KEY", default)` 或 `os.getenv("KEY", default)`，默认值必须显式给出。

3. **`dirs = [...]` 想剪枝却没生效** —— `os.walk` 只在 `dirs` 被**原地修改**时才看到变化。正确写法：`dirs[:] = [d for d in dirs if ...]`，切片赋值才是原地替换。

4. **`list(Path(d).rglob("*"))` 在大目录上吃爆内存** —— 一次性物化整棵树。正确写法：直接迭代生成器 `for p in Path(d).rglob("*")`，需要顺序时才 `sorted()`（且评估规模）。

5. **依赖 `rglob` / `iterdir` 的返回顺序** —— 底层 `readdir` 顺序因文件系统而异，同目录增删文件后还会变。正确写法：任何需要可复现的场景（测试、快照、CI）显式 `sorted(...)`，并指定 key。

6. **在项目根目录放 `json.py` / `random.py` / `types.py`** —— 脚本目录在 `sys.path` 首位，会**遮蔽标准库同名模块**，导致依赖库 `import json` 拿到你的文件，报出无法定位的 `AttributeError`。正确写法：用包结构（`src/mypkg/`）+ 可安装包，不要靠 `sys.path.append` 打补丁。

7. **`python tool.py | grep x` 时看不到实时输出** —— stdout 连到管道时是**块缓冲**（默认 8KB）。正确写法：`print(..., flush=True)`，或启动加 `-u`（`python -u tool.py`）。

8. **成功时 `sys.exit(1)`、失败时 `sys.exit(2)`** —— 违反 POSIX 约定会让 CI/脚本的 `if cmd; then` 判断全错。正确约定：`0` 成功、`1` 通用业务错误、`2` 命令行用法错误（`argparse` 默认）、`128+n` 被信号 n 终止。

9. **用 `sys.version` 字符串判断版本** —— 字符串格式随构建变化（含编译器与日期）。正确写法：`sys.version_info >= (3, 11)`，用元组比较。

10. **`naive_datetime.timestamp()`** —— naive 时间会被**按本机时区**解释，同一份代码在北京和纽约得到差 12 小时的结果且不报错。正确写法：`datetime(..., tzinfo=timezone.utc).timestamp()`，或直接持有 aware 对象。

11. **用 `datetime + timedelta(days=1)` 做「加一天」** —— 在 DST 切换日「加一天」不等于「加 24 小时」，结果会偏移一小时。正确写法：在 UTC 上做算术再转本地：`(t.astimezone(timezone.utc) + timedelta(days=1)).astimezone(tz)`。

12. **手写 `timezone(timedelta(hours=8))` 表示「中国标准时间」** —— 固定偏移不带 DST 与历史变更规则，用于有夏令时的地区会错。正确写法：用 IANA 名 `ZoneInfo("Asia/Shanghai")`（无 DST，但跨库语义统一）。

13. **`json.dumps` 忘了 `ensure_ascii=False`** —— 默认把所有非 ASCII 转成 `\uXXXX`，文件大 6 倍且不可读。正确写法：写文件/传前端时显式 `ensure_ascii=False`，并保证以 UTF-8 写出。

14. **`json.dumps(float("nan"))` 产出 `NaN`** —— 那不是合法 JSON，Go/Rust/JS 的标准解析器会直接拒收。正确写法：对外接口设 `allow_nan=False`，让非法值在序列化阶段就 `ValueError`，早失败早定位。

15. **`default=` 里把 `set` 直接 `list(o)`** —— `set` 的迭代顺序依赖哈希，跨进程（`PYTHONHASHSEED` 随机）不确定，输出不可复现。正确写法：`sorted(o)`，并确认元素可比。

16. **用 `pickle` 在进程间 / 网络 / 磁盘传递数据** —— `pickle.loads` 可执行任意代码（`__reduce__`），且依赖类定义、跨版本易失效。正确写法：跨边界一律 `json`（或 msgpack/protobuf）；`pickle` 只用于同机同版本的可信临时缓存。

17. **`json.dumps({1: "a"})` 通过但往返后类型变了** —— `int` 键被静默转成字符串 `"1"`，`{1: "a"} != {"1": "a"}`。正确写法：JSON 的键只使用字符串；需要非字符串索引时，在业务层显式转换并记录。

18. **`strptime` 里 `%m` 与 `%M` 搞混** —— `%m` 是月、`%M` 是分，写错会得到「看起来正常但完全错误」的时间（分钟=1、秒=26）。正确写法：对照表核对，或优先用 `fromisoformat`（无需格式串，天然正确）。
