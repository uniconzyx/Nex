# datetime：naive / aware、时区与夏令时

## 1. 三种时间表示，别混着用

Python 的 `datetime` 对象分两类：

| 类型 | 特征 | 例子 |
|---|---|---|
| **naive**（朴素） | 不带时区信息，`tzinfo is None` | `datetime(2026, 10, 7, 14, 30)` |
| **aware**（感知） | 带 `tzinfo`，能定位到绝对时刻 | `datetime(2026, 10, 7, 14, 30, tzinfo=timezone.utc)` |

**核心规则：naive 与 aware 相减会抛 `TypeError`**。

```python
from datetime import datetime, timezone

a = datetime(2026, 10, 7, 14, 30)                       # naive
b = datetime(2026, 10, 7, 14, 30, tzinfo=timezone.utc)  # aware
a - b     # TypeError: can't subtract offset-naive and offset-aware datetimes
```

这是**有意的设计**：naive 时间没有绝对含义（「14:30」在哪？），硬相减必然算错。报错比静默算错好。

工程约定：**系统内部一律用 aware 时间（通常 UTC），只在展示层转本地时区**。

## 2. `timestamp()` 的坑：naive 会被当成本地时间

```python
from datetime import datetime, timezone

naive = datetime(2026, 10, 7, 14, 30)
naive.timestamp()            # ⚠️ 按【本机时区】解释！换台机器结果就变
aware = datetime(2026, 10, 7, 14, 30, tzinfo=timezone.utc)
aware.timestamp()            # ✅ 确定：1780842600.0
```

`naive.timestamp()` 会**假定 naive 是本地时间**，因此输出依赖 `TZ` 环境变量与系统时区设置。同一份代码在北京和纽约跑，得到的秒数差 12 小时，**而且不报错**。

迁移到「纯 UTC 内部表示」时，这类代码是最难查的——因为它本地测试永远正确。

## 3. 时区：`zoneinfo` 与夏令时

Python 3.9+ 引入 `zoneinfo`（PEP 615），用 IANA 时区数据库：

```python
from datetime import datetime
from zoneinfo import ZoneInfo

sh = ZoneInfo("Asia/Shanghai")
ny = ZoneInfo("America/New_York")

t = datetime(2026, 3, 8, 2, 30, tzinfo=ny)   # 纽约 2026-03-08 02:30
print(t.utcoffset())          # ⚠️ 该时刻处于 DST 跳变窗口
print(t.astimezone(sh))       # 转上海
```

**夏令时（DST）的两个陷阱**：

1. **不存在的时刻**（spring forward）：2026-03-08 纽约 02:00→03:00 直接跳过，`02:30` 这个本地时间**不存在**。`zoneinfo` 会给出一个「修正后」的偏移而不是报错，具体行为依实现，跨库不一致。
2. **重复的时刻**（fall back）：2026-11-01 纽约 01:00–02:00 出现两次（EDT 与 EST）。同一个「01:30」对应两个不同的 UTC 时刻，`fold` 属性用来区分：`datetime(..., fold=0)` 是第一次、`fold=1` 是第二次。

因此：**做「本地时间算术」时不要用 `+ timedelta(days=1)`**。因为「加一天」在 DST 边界上不等于「加 24 小时」。正确做法是**在 UTC 上做算术，再转本地展示**：

```python
import datetime as dt
from zoneinfo import ZoneInfo

ny = ZoneInfo("America/New_York")
t = dt.datetime(2026, 3, 7, 12, 0, tzinfo=ny)
next_day_utc = (t.astimezone(dt.timezone.utc) + dt.timedelta(days=1)).astimezone(ny)
# 若直接 t + timedelta(days=1)，会在 DST 切换日得到 13:00 而不是 12:00
```

## 4. 格式化与解析：`strftime` / `strptime` 与 ISO 8601

```python
from datetime import datetime, timezone

t = datetime(2026, 10, 7, 14, 30, 5, tzinfo=timezone.utc)
t.strftime("%Y-%m-%d %H:%M:%S")        # '2026-10-07 14:30:05'
t.isoformat()                          # '2026-10-07T14:30:05+00:00'

datetime.fromisoformat("2026-10-07T14:30:05+08:00")   # ✅ 3.11+ 支持大部分 ISO 8601
datetime.strptime("2026-10-07", "%Y-%m-%d")           # 需要显式格式
```

**关键取舍**：

- **对外传输用 ISO 8601**（`isoformat()` / `fromisoformat()`），因为它**自带时区**、可排序、跨语言通用。
- **只给人看用 `strftime`**。
- **不要发明格式**（如 `2026/10/07 2:30 PM`）——解析会因 locale 出错（`%p` 依赖 locale）。

`strptime` 的两个易错指令：`%m` 是月（01–12）、`%M` 是分（00–59）；`%y` 是两位年（26 → 2026）、`%Y` 是四位年。搞混会得到「分钟=1、秒=26」这种看似正常但完全错误的结果。

## 5. 速记

- naive 无时区、aware 有时区；**两者相减必报 `TypeError`**
- `naive.timestamp()` 按**本地时区**解释 → 跨机器不一致；**只用 aware**
- 时区用 `zoneinfo`（IANA 名，如 `Asia/Shanghai`），**不要**手写 `timezone(timedelta(hours=8))` 做 DST 地区
- DST 有「不存在的时刻」与「重复的时刻」；本地时间算术要在 UTC 上做
- 传输用 ISO 8601（自带时区）；展示才用 `strftime`
- `%m` 月 / `%M` 分，`%y` 两位年 / `%Y` 四位年

## 三视角解析

### 🧑‍💻 程序员视角

**排查顺序**：跨时区时间错 8 小时 → 依次查：① 存的是 naive 还是 aware；② 是否调用了 `naive.timestamp()`；③ 容器 `TZ` 与宿主是否一致（Docker 默认 UTC，宿主常是 CST）。第 ③ 条是「本地对、线上差 8 小时」的最常见原因，**部署时显式设 `TZ` 或统一走 UTC**。

**工程决策**：数据库字段一律 `TIMESTAMP WITH TIME ZONE`（PG）或存 UTC 的 `datetime`；API 出入参一律 ISO 8601 带偏移；前端本地化只做展示。**不要**在 DB 里存「本地时间字符串」——那等于把时区信息丢进业务代码，日后无法全局修正。

**性能**：`zoneinfo.ZoneInfo` 有缓存（同一 key 返回同一对象），不要每次 `ZoneInfo("Asia/Shanghai")` 新建；模块级建一次即可。频繁格式化大量时间时，`isoformat()` 比自定义 `strftime` 快，且天然正确。

### 🎓 博士生视角

**naive 与 aware 的类型论含义**：aware 时间是**绝对时刻**（UTC 时间轴上的一个点），naive 时间是**未定位的墙上时刻**，两者是不同**类型**。Python 用 `TypeError` 而非隐式补齐，是在遵循「不做有损的隐式转换」原则——与强类型语言里禁止 `int + string` 同构。

**DST 为什么不可逆**：本地时间到 UTC 的映射在 DST 边界处**不是双射**——spring forward 处是**非单射**（不存在的时刻无原像），fall back 处是**非单射**（重复时刻有两个原像）。`fold` 参数就是为消解第二种歧义而引入的显式标记。这解释了为什么「按本地时间排序」在跨 DST 时可能给出违反直觉的顺序。

**`timestamp()` 的语义漂移**：`datetime.timestamp()` 定义在「本地时区」上，但「本地时区」是**进程环境**的一部分，不是日期对象的属性。于是这个方法的输出依赖**隐式全局状态**——这与函数式「显式优于隐式」原则相悖。aware 版本的 `timestamp()` 才是纯函数（输出只依赖对象自身）。

### 📚 考研者视角

**笔试常见问法与口径**：

1. 「naive 和 aware 的区别」——标准答法：**`tzinfo` 是否为 `None`**，并补充「两者相减抛 `TypeError`」这一可验证的行为。
2. 「`datetime.now()` 与 `datetime.utcnow()` 的区别」——`now()` 返回本地 naive 时间，`utcnow()` 返回 UTC naive 时间；**两者都是 naive**（这是 3.12 起 `utcnow()` 被标记 deprecated 的原因）。标准做法是 `datetime.now(timezone.utc)`（aware）。
3. 「时间戳是什么」——从 1970-01-01T00:00:00Z 起的秒数（**UTC 基准，与时区无关**），是绝对时刻的规范表示。
4. 「DST 的两种情况」——多考「不存在的时刻」与「重复的时刻」，能说出 `fold` 是加分项。
5. 易错口径：`strftime("%Y-%m-%d")` 的 `%m` 是**月**，`%M` 是**分**，一字之差常被拿来考细心度。
