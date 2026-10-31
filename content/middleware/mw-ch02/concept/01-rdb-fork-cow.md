# 一、RDB 快照：fork 与写时复制（COW）

本文件覆盖两个核心主题：**① RDB 快照与 fork + 写时复制（COW）** 与 **② save m n 多条件触发规则**。

---

## ① RDB 快照与 fork + 写时复制（COW）

（中立陈述）RDB 是 Redis 某一时刻内存数据的**二进制全量快照**。生成方式有 `SAVE`（主进程阻塞）与 `BGSAVE`（fork 子进程后台生成）。`BGSAVE` 的核心在于 `fork()` 系统调用：子进程与父进程共享同一份物理内存页，只有当父进程**修改**某页时，内核才将该页复制一份（Copy-On-Write），子进程始终读到的仍是 fork 时刻的一致性快照。见 `examples/ex01_rdb_fork_cow.json`。

### 🧑‍💻 程序员视角
- **线上别随便手敲 `SAVE`**：`SAVE` 在主线程跑，数据集大时直接卡死服务；要落盘一律用 `BGSAVE` / 自动触发，或 `redis-cli --rdb` 离线拉快照。
- **fork 阻塞是真实痛点**：fork 本身要拷贝页表，数据量越大（GB 级）页表越大，`latest_fork_usec` 可能到百毫秒级，期间主线程停顿；大内存实例要监控该指标并预留内存。
- **COW 的内存账**：`BGSAVE` 期间父进程持续写入会导致大量页被复制，瞬时内存可能翻倍；若触发了系统 OOM，Redis 会被 kill。做法是给 `maxmemory` 留出余量、控制写入峰值。
- 实战：从节点全量同步时主节点也会 `BGSAVE`，因此主从+持久化叠加要算清 fork 与 COW 的内存预算。

### 🎓 博士生视角
- **COW 的硬件/OS 机制**：fork 后父子共享页表项，页表项标记为只读；任一方写触发**缺页异常（page fault）**，内核在异常处理路径中复制该物理页、更新写方的页表项为可写，读方页表项仍指向原页。共享页的引用计数归内核管理。
- **为什么快照一致性成立**：子进程在 fork 返回瞬间获得了父进程地址空间的完整“逻辑视图”——后续父进程修改只是让子进程看到的旧页保持原样（COW），因此子进程遍历自身内存写出的就是 fork 那一刻的快照，无需加锁。
- **fork 复杂度**：O(进程页表项数) 而非 O(内存字节数)；Linux 下页表为多级（PGD/PUD/PMD/PTE），拷贝的是页表结构，所以 GB 级实例 fork 仍可能耗时数十~数百毫秒，且期间写时复制会放大 RSS。
- **与 AOF 对比的持久化语义**：RDB 是点快照，两次快照间崩溃会丢数据；COW 保证的是“快照生成过程中的一致性”，不是“不丢数据”。

### 📚 考研者视角（笔面考点）
- **标准问法**：「BGSAVE 为什么用 fork + COW，而不直接拷贝内存？」答：直接全量拷贝 O(数据量) 既慢又占双倍内存；fork + COW 只拷贝页表 O(页表)，未被修改的页父子共享，仅修改页才复制，大幅降低快照开销。
- **易错口径**：COW 解决的是「快照生成开销与一致性」，**不等于**「数据不丢」；RDB 仍是定期点快照，宕机丢间隔数据——这个区分是高频扣分点。
- **关联考点**：COW 与操作系统「写时复制」「缺页中断」「页表」直接相关，可联系虚拟内存章的 fork/exec 与共享内存命题。

---

## ② save m n：RDB 的自动触发规则

（中立陈述）`redis.conf` 中的 `save m n` 表示「在 m 秒内发生了至少 n 次修改，则触发一次 BGSAVE」。可配置多条规则，**任意一条满足即触发**。还有 `stop-writes-on-bgsave-error`、`rdbcompression`、`rdbchecksum` 等配套项。见 `examples/ex02_rdb_save_m_n.json`。

### 🧑‍💻 程序员视角
- **默认配置的含义**：`save 900 1`（15 分钟至少 1 次改）→ `save 300 10`（5 分钟 10 次）→ `save 60 10000`（1 分钟 1 万次）。流量低时靠长周期兜底，流量高时短周期更密。
- **关掉 RDB 的两种姿势**：要么注释所有 `save` 行，要么设 `save ""`；只做缓存、纯 AOF 的场景会这么做，但注意 `BGREWRITEAOF` 不受影响。
- **踩坑**：`stop-writes-on-bgsave-error yes`（默认）时，若磁盘满导致 BGSAVE 失败，Redis 会拒绝写入——生产环境磁盘监控必须到位，否则出现“读正常、写被拒”的诡异故障。

### 🎓 博士生视角
- **判定是增量的**：规则判定基于「距上次成功 save 的时长 × 累计修改计数」，每次命令递增脏计数，serverCron 周期性检查各规则；触发后重置该规则的计时与计数（实现上是重置一个全局 `dirty` 计数器与 `lastsave` 时间戳，凡满足条件的规则一起判定）。
- **多规则是“或”关系**：`serverCron` 遍历所有 `save` 项，任一 `(now - lastsave) >= seconds && dirty >= changes` 成立即触发，触发后 `dirty=0`、`lastsave=now`，所以不会出现“每条规则各存一份”的误解。
- **与 COW/fork 的耦合**：save 判定本身很轻量，真正昂贵的是触发后的 fork + 遍历内存；因此规则不宜设得过密（如 `save 1 1` 会让每次写都尝试 fork）。

### 📚 考研者视角（笔面考点）
- **标准定义**：`save m n` = m 秒内至少 n 次写操作则自动 BGSAVE；多条规则为“或”关系，满足其一即触发。
- **常考辨析**：`SAVE` 与 `BGSAVE` 的区别（阻塞 vs 后台 fork）、RDB 文件是「二进制紧凑」且「全量」、「恢复远快于 AOF 重放」。
- **易混点**：RDB 保存的是**触发时刻的内存数据**，不是写命令日志；因此“RDB 能恢复到最近一次命令”是错误的，应表述为“恢复到最近一次快照点”。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### RDB 快照：fork + 写时复制(COW) 模拟

```python
class KV:
    def __init__(self):
        self.data = {f"k{i}": i for i in range(5)}
    def fork_snapshot(self):
        # 模拟 COW：子进程拿到 fork 时刻的只读视图（浅拷贝共享页）
        return dict(self.data)

db = KV()
print("BGSAVE 触发，fork 子进程生成 RDB 快照")
snapshot = db.fork_snapshot()
print("快照内容:", snapshot)
# 主进程继续服务写入，COW 让子进程视图不受影响
db.data["k0"] = 999
db.data["k6"] = 6
print("父进程新增/修改后当前数据:", db.data)
print("快照内容(未被父进程写入影响):", snapshot)
print("COW 收益: 仅被修改的页在父进程侧复制, 未改页父子共享, fork 开销=O(页表)")
```

实际输出：

```text
BGSAVE 触发，fork 子进程生成 RDB 快照
快照内容: {'k0': 0, 'k1': 1, 'k2': 2, 'k3': 3, 'k4': 4}
父进程新增/修改后当前数据: {'k0': 999, 'k1': 1, 'k2': 2, 'k3': 3, 'k4': 4, 'k6': 6}
快照内容(未被父进程写入影响): {'k0': 0, 'k1': 1, 'k2': 2, 'k3': 3, 'k4': 4}
COW 收益: 仅被修改的页在父进程侧复制, 未改页父子共享, fork 开销=O(页表)
```

> 出处：`examples/ex01_rdb_fork_cow.json`。改一处再看输出变没变，比读三遍解释有用。

### RDB 触发条件：save m n 规则判定

```python
saves = [(900, 1), (300, 10), (60, 10000)]
state = {"last_save_t": 0, "changes_since": 0}
def check(t, change_delta):
    state["changes_since"] += change_delta
    for sec, changes in saves:
        if t - state["last_save_t"] >= sec and state["changes_since"] >= changes:
            return True
    return False

events = [(0, 0), (120, 5), (300, 0), (305, 8), (600, 3)]
for t, d in events:
    triggered = check(t, d)
    if triggered:
        print(f"t={t}s 变更累计={state['changes_since']} -> 满足 save 规则, 触发 BGSAVE")
        state["last_save_t"] = t
        state["changes_since"] = 0
    else:
        print(f"t={t}s 变更累计={state['changes_since']} -> 未达任何 save 规则")
```

实际输出：

```text
t=0s 变更累计=0 -> 未达任何 save 规则
t=120s 变更累计=5 -> 未达任何 save 规则
t=300s 变更累计=5 -> 未达任何 save 规则
t=305s 变更累计=13 -> 满足 save 规则, 触发 BGSAVE
t=600s 变更累计=3 -> 未达任何 save 规则
```

> 出处：`examples/ex02_rdb_save_m_n.json`。改一处再看输出变没变，比读三遍解释有用。

