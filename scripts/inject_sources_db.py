# -*- coding: utf-8 -*-
"""middleware 学科来源锚点重写（批次 M1，8 章 32 条）。

依据：逐章 grep concept/*.md 的真实 `##` 标题，按「文件序号.文件内小节序号」重编 §。
每条格式：`§x.y 小节标题 · 读什么`（分隔符为前后各一空格的中间点）。

本批除了编号错位，还清了三条「跑题」条目：
  mw-ch04#3 原讲「过期与淘汰」，属 mw-ch02 的内容，本章讲缓存设计 → 换成缓存一致性
  mw-ch01#4 原拿 Kafka 集合实现凑数，与本章编码切换无关      → 换成 skiplist 结构
  mw-ch07#3 原拿 Redis 落盘对比，与「存储端不丢」隔一层        → 换成副本/ISR
"""
import json
import os
import re

MANIFEST = "content/database/_manifest.json"
CH_DIR = "content/database"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)


def split_note(note: str) -> tuple[str, str]:
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
    """只改「## 本章 GitHub」小节内的 `| n |` 表格行（B 站表格同形，须框定范围）。"""
    path = os.path.join(CH_DIR, cid, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")

    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    if not row_idx:
        return False, "小节内无表格行"
    if len(row_idx) != len(notes):
        return False, f"表格 {len(row_idx)} 行、notes {len(notes)} 条，不匹配"

    for i, note in zip(row_idx, notes):
        m = RE_GH_ROW.match(lines[i])
        head, tail = split_note(note)
        lines[i] = (
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )

    out = "\n".join(lines)
    if out == s:
        return True, "已是同源"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    return True, f"表格 {len(row_idx)} 行已同步"


NOTES: dict[str, list[str]] = {
    # ---------------- db-ch01 关系模型与 SQL 基础 ----------------
    "db-ch01": [
        "§1.2 键的四层概念 · 读 `docs/database/mysql/` 下的索引专题："
        "超键/候选键/主键/外键的区别在文档里被压成一张表，"
        "重点是「主键选择为什么影响聚簇索引的物理顺序」——这条直接接上 §1.3 三类完整性约束里的实体完整性",

        "§3.3 JOIN 全景 · 看 `document/sql/mall.sql`：`pms_product` 与 `pms_sku_stock` 的一对多、"
        "`oms_order` 与 `oms_order_item` 的从属关系，都是真实业务的连接样本，比教学用的 dept/emp 两表更接近工程；"
        "读时对照 §3.2「两个顺序别搞混」——`FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY`",

        "§1.5 `NULL`：三值逻辑的代价 · 对照 `docs/high-concurrency/` 的 MySQL 系列："
        "`count(col)` 跳过 NULL、`NOT IN` 遇到 NULL 返回空集，这两个坑它各给了一条可复现的 SQL；"
        "验证方法：把本章 §1.8 可运行示例里的表加一行 NULL，两个查询的结果会同时变空",
    ],
    # ---------------- db-ch02 表连接与子查询 ----------------
    "db-ch02": [
        "§2.3 `IN` vs `EXISTS`：别再背「小表用 IN、大表用 EXISTS」 · 读 `docs/database/mysql/` 的 SQL 优化篇："
        "标量子查询、`IN`、`EXISTS` 在执行计划里的差异是「是否被改写成半连接」，"
        "这决定了相关子查询会不会被逐行执行；先读 §2.2「MySQL 如何拆掉子查询」再来看这条结论",

        "§1.2 实现机制：InnoDB/优化器怎么选 · 看 `mall-mbg` 生成的 Example/Criteria 类："
        "它把「动态 WHERE + ORDER BY」拼成 SQL，能直观看到「条件组合爆炸」是怎么发生的，"
        "也能理解为什么 §1.3 工程实践里复杂的多表关联仍要手写 XML 而不是靠 Criteria 拼",

        "§4.3 工程实践：何时反范式 · 对照 `docs/high-concurrency/` 的 MySQL 优化文章："
        "「小表驱动大表」这条结论来自「谁做驱动表」而非语法本身；"
        "把它带到 §4.1「范式是不让数据说假话的规则」一起看，"
        "就明白为什么反范式是用冗余换掉一次 JOIN，而不是随手去重",
    ],
    # ---------------- db-ch03 索引与事务 ----------------
    "db-ch03": [
        "§1.1 理论根基：为什么是 B+树，不是哈希/红黑树/B树 · 读 `docs/database/mysql/mysql-index.md`："
        "B+ 树把数据全放叶子、非叶子只存键，因此一个 16KB 页能装更多键、树更矮"
        "——磁盘 IO 次数稳定在 3~4 次，这是它胜过二叉树与哈希的根本原因；"
        "对照 §1.2 的页结构，就能算出三层树能存多少行",

        "§2.1 回表（Bookmark Lookup）：二级索引的隐含成本 · 看 `document/sql/mall.sql` 里每张表的 "
        "`PRIMARY KEY (id)` 与业务唯一键：InnoDB 的二级索引叶子存主键，所以「按业务键查」要回表一次；"
        "这解释了 §2.2 覆盖索引为什么能把这次回表省掉——代价是索引里多存几列",

        "§3.3 MVCC：多版本并发控制（核心） · 对照 `docs/high-concurrency/mysql-lock.md`："
        "快照读靠 undo 版本链 + ReadView，当前读（`SELECT ... FOR UPDATE`）才加锁"
        "——「可重复读下仍会幻读」的现场就出在这两者的边界上；"
        "配合 §3.4 当前读 vs 快照读，就能解释同一个事务里两次查询结果为何不一致",
    ],
    # ---------------- db-ch04 查询优化与执行计划 ----------------
    "db-ch04": [
        "§1.2 type 的优劣阶梯（面试必背） · 读 `docs/database/mysql/` 的 EXPLAIN 专题："
        "`system > const > eq_ref > ref > range > index > ALL` 这条链要能背，"
        "且要知道 `ALL` 出现在大表上就意味着全表扫描；"
        "配合 §1.3 Extra 的关键信号（`Using filesort` / `Using temporary`），"
        "才能从一列 `type` 看出真正的瓶颈",

        "§2.1 索引失效清单（逐条给改写） · 看 `mall-admin` 的商品搜索实现："
        "`LIKE \"%关键词%\"` 前导通配符让索引失效，真实工程用「ES 检索 + 主键回表」绕开，"
        "而不是硬调 SQL；这正是 §2.3「选择性为什么低区分度列不该单独建索引」的反面教材",

        "§3.2 深分页：`LIMIT offset, n` 的线性代价 · 对照 `docs/high-concurrency/` 的慢查询文章："
        "`LIMIT 1000000, 20` 要先扫掉一百万行，正确写法是「延迟关联」或「游标分页（记住上一页最后一行的 id）」；"
        "读时回 §3.1「先把慢 SQL 找出来」，慢日志里这类语句的 `Rows_examined` 会远大于返回行数",
    ],
    # ---------------- db-ch05 存储过程 / 触发器 / 函数 ----------------
    "db-ch05": [
        "§1.1 存储过程与自定义函数：定义、调用与差异 · 读 `docs/database/mysql/` 的过程化编程章节："
        "函数必须 RETURN 一个值、过程靠 OUT 参数，二者的调用位置（表达式 vs CALL）决定了它们不能互换；"
        "读完再回 §1.2 参数模式 IN/OUT/INOUT，就明白为什么过程适合「多返回值 + 副作用」的场景",

        "§4.1 为什么互联网公司普遍不用存储过程 · 看 `mall` 的 Service 层："
        "业务规则全在 Java 里、SQL 只出现在 mapper XML 中，这是「存储过程不适合互联网团队」的直接证据"
        "——版本管理、单测、灰度发布都做不了；"
        "这正是 §4.2「存储过程内的事务语义」之外的第二重代价",

        "§2.2 NEW / OLD 行镜像的可用性矩阵与审计日志落地 · 对照 `docs/high-concurrency/` 的数据库设计文章："
        "触发器把逻辑藏进数据库，排查时「看不见调用方」，审计场景更推荐 binlog 订阅（Canal）而非触发器；"
        "读时对照 §2.1 的 ECA 模型——`INSERT` 只有 NEW、`DELETE` 只有 OLD、`UPDATE` 两者都有，"
        "这条矩阵正是「写审计触发器时取错值」的根因",
    ],
    # ---------------- db-ch06 范式与数据库建模 ----------------
    "db-ch06": [
        "§2.1 1NF 与 2NF：原子性与部分依赖 · 读 `docs/database/mysql/` 的范式专题："
        "属性原子性与「非主属性完全依赖候选键」是两个独立的判据，"
        "把「多值字段存逗号串」当 1NF 违规是最常见的误判；"
        "配合 §1.1 函数依赖的三种类型，才能判断一个表到底卡在哪一范",

        "§4.3 反范式：何时故意冗余 · 看 `mall` 的 `pms_product` 与 `pms_sku_stock`："
        "商品名、价格在 SKU 表里冗余一份，是为了「列表页一次查询拿全」而不做 JOIN"
        "——冗余的代价是「改商品名要同步更新所有 SKU」；"
        "读完再回 §4.1 ER 建模，就明白冗余字段本质上是把一次 JOIN 固化进表结构",

        "§3.1 两个正确性标准：无损连接与保持依赖 · 对照 `docs/high-concurrency/mysql-sharding.md`："
        "分片后跨库 JOIN 不可用，只能靠「冗余字段 + 异步补偿」，"
        "这时范式让位于「查询能不能一次走完」；"
        "但分片本身仍要满足 §3.2 无损连接——否则拆完的表拼不回原关系",
    ],
    # ---------------- db-ch07 备份恢复与权限安全 ----------------
    "db-ch07": [
        "§1.1 逻辑备份与物理备份：两种「备份」根本不是一回事 · 读 `docs/database/mysql/` 的运维章节："
        "`mysqldump` 导出的是 SQL 文本（可跨版本、慢），`xtrabackup` 拷的是数据文件（快、要同版本），"
        "两者的恢复时间差一个数量级；这正是 §1.3「备份要可信」必须先做恢复演练的原因",

        "§3.3 最小权限：从原则到可执行的审计 · 看 `mall` 的 `application.yml` 里的数据源账号："
        "业务账号只需要 `SELECT/INSERT/UPDATE/DELETE`，给 `DROP` 权限等于把「一次注入」升级成「删库」；"
        "读时对照 §3.1「账号是『用户@主机』」，就明白为什么 `'app'@'%'` 本身就是一条越权风险",

        "§2.1 binlog 到底记了什么：三种格式（STATEMENT / ROW / MIXED） · "
        "对照 `docs/high-concurrency/` 的 MySQL 文章：`ROW` 格式记的是行变更前后镜像，"
        "所以能配合 §2.2 的 PITR 做到「精确到秒的时间点恢复」，"
        "而 `STATEMENT` 格式在 `NOW()`/`UUID()` 上无法重现——这是「回滚后数据仍不一致」的经典根因",
    ],
    # ---------------- db-ch08 高可用 / 主从 / 分库分表 ----------------
    "db-ch08": [
        "§1.1 复制链路：binlog dump → relay log → 重放 · 读 `docs/database/mysql/` 的主从章节："
        "`binlog dump → IO 线程写 relay log → SQL 线程重放`，三个环节各自的延迟来源不同，排查要分开看；"
        "这正是 §1.3 主从延迟成因的分层依据——IO 慢还是 SQL 线程单线程回放慢，处置完全不同",

        "§1.2 复制模式：异步 / 半同步 / 组复制 · 看 `mall` 的单库配置："
        "这个项目没有分库分表，正好用来对照「什么规模不需要拆」"
        "——单表千万级以内、QPS 几千，加索引与缓存比拆库划算得多；"
        "这也解释了 §1.3「读己之写」为什么在小规模下几乎不是问题",

        "§2.1 切分维度：范围 / 哈希 / 一致性哈希 / 基因法 · 对照 `docs/high-concurrency/mysql-sharding.md`："
        "哈希分片扩容要「翻倍 + 迁移一半」，范围分片扩容简单但会热点"
        "——选哪种取决于「写入是否均匀」而不只是「查询方便」；"
        "配合 §2.3 分布式 ID 与二次分片，就能判断这次扩容要不要动分片键",
    ],
}


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        nl = "\r\n" if b"\r\n" in fb.read() else "\n"
    data = json.load(open(MANIFEST, encoding="utf-8"))

    done = 0
    changed = False
    for ch in data.get("chapters", []):
        cid = ch.get("id")
        if cid not in NOTES:
            continue
        new = NOTES[cid]
        res = ch.setdefault("resources", {})
        old = res.get("github_notes", [])
        if len(old) != len(new):
            print(f"!! {cid} 原 {len(old)} 条、新 {len(new)} 条，不匹配，跳过")
            continue
        if old != new:
            res["github_notes"] = new
            changed = True
        done += 1
        ok, msg = rewrite_goals_table(cid, new)
        print(f"{'OK ' if ok else '!! '}{cid}: notes {len(new)} 条｜{msg}")

    if changed:
        with open(MANIFEST, "w", encoding="utf-8", newline=nl) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"manifest 已写盘（{done} 章）")
    else:
        print(f"manifest 已是目标状态（{done} 章），未写盘")


if __name__ == "__main__":
    main()
