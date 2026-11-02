# -*- coding: utf-8 -*-
"""来源颗粒度 · database 8 章。

三个仓库的角色分工：
  Snailclimb/JavaGuide —— MySQL 专题文档，用来「校准口径」（索引/事务/锁/范式）
  macrozheng/mall      —— 真实电商库，用来看「表怎么建、索引怎么加、什么时候故意反范式」
  doocs/advanced-java  —— 面试向深挖（分库分表、读写分离、分片键）
"""
import sys

from _route_granularity import apply

GUI = 'Snailclimb/JavaGuide'
MALL = 'macrozheng/mall'
ADV = 'doocs/advanced-java'

DATA = {
    'db-ch01': {
        GUI: ('§1.2', '讲「键的四层概念」时读 `docs/database/mysql/` 下的索引专题：超键/候选键/主键/外键的区别在文档里被压成一张表，重点是「主键选择为什么影响聚簇索引的物理顺序」'),
        MALL: ('§3.2', '讲「JOIN 全景」时看 `document/sql/mall.sql`：`pms_product` 与 `pms_sku_stock` 的一对多、`oms_order` 与 `oms_order_item` 的从属关系，都是真实业务的连接样本，比教学用的 dept/emp 两表更接近工程'),
        ADV: ('§1.5', '讲「NULL 与三值逻辑」时对照 `docs/high-concurrency/` 的 MySQL 系列：`count(col)` 跳过 NULL、`NOT IN` 遇到 NULL 返回空集，这两个坑它各给了一条可复现的 SQL'),
    },
    'db-ch02': {
        GUI: ('§4.1', '讲「子查询的三种形态」时读 `docs/database/mysql/` 的 SQL 优化篇：标量子查询、`IN`、`EXISTS` 在执行计划里的差异是「是否被改写成半连接」，这决定了相关子查询会不会被逐行执行'),
        MALL: ('§3.1', '讲「JOIN 与聚合」时看 `mall-mbg` 生成的 Example/Criteria 类：它把「动态 WHERE + ORDER BY」拼成 SQL，能直观看到「条件组合爆炸」是怎么发生的，也能理解为什么复杂查询要手写 XML'),
        ADV: ('§2.2', '讲「IN vs EXISTS」时对照 `docs/high-concurrency/` 的 MySQL 优化文章：小表驱动大表、`EXISTS` 在外层小的时候更快，这条结论来自「谁做驱动表」而非语法本身'),
    },
    'db-ch03': {
        GUI: ('§1.1', '讲「为什么是 B+ 树」时读 `docs/database/mysql/mysql-index.md`：B+ 树把数据全放叶子、非叶子只存键，因此一个 16KB 页能装更多键、树更矮——磁盘 IO 次数稳定在 3~4 次，这是它胜过二叉树与哈希的根本原因'),
        MALL: ('§2.1', '讲「聚簇索引与二级索引」时看 `document/sql/mall.sql` 里每张表的 `PRIMARY KEY (id)` 与业务唯一键：InnoDB 的二级索引叶子存主键，所以「按业务键查」要回表一次，这解释了「为什么覆盖索引能把这次回表省掉」'),
        ADV: ('§3.3', '讲「MVCC 与当前读」时对照 `docs/high-concurrency/mysql-lock.md`：快照读靠 undo 版本链 + ReadView，当前读（`SELECT ... FOR UPDATE`）才加锁——「可重复读下仍会幻读」的现场就出在这两者的边界上'),
    },
    'db-ch04': {
        GUI: ('§1.2', '讲「type 的优劣阶梯」时读 `docs/database/mysql/` 的 EXPLAIN 专题：`system > const > eq_ref > ref > range > index > ALL` 这条链要能背，且要知道 `ALL` 出现在大表上就意味着全表扫描'),
        MALL: ('§3.1', '讲「索引失效」时看 `mall-admin` 的商品搜索实现：`LIKE "%关键词%"` 前导通配符让索引失效，真实工程用「ES 检索 + 主键回表」绕开，而不是硬调 SQL'),
        ADV: ('§3.2', '讲「深分页与 JOIN 优化」时对照 `docs/high-concurrency/` 的慢查询文章：`LIMIT 1000000, 20` 要先扫掉一百万行，正确写法是「延迟关联」或「游标分页（记住上一页最后一行的 id）」'),
    },
    'db-ch05': {
        GUI: ('§1.1', '讲「存储过程与函数的差异」时读 `docs/database/mysql/` 的过程化编程章节：函数必须 RETURN 一个值、过程靠 OUT 参数，二者的调用位置（表达式 vs CALL）决定了它们不能互换'),
        MALL: ('§4.1', '讲「存储过程与应用的边界」时看 `mall` 的 Service 层：业务规则全在 Java 里、SQL 只出现在 mapper XML 中，这是「存储过程不适合互联网团队」的直接证据——版本管理、单测、灰度发布都做不了'),
        ADV: ('§1.3', '讲「触发器与审计」时对照 `docs/high-concurrency/` 的数据库设计文章：触发器把逻辑藏进数据库，排查时「看不见调用方」，审计场景更推荐 binlog 订阅（Canal）而非触发器'),
    },
    'db-ch06': {
        GUI: ('§2.1', '讲「1NF 与 2NF」时读 `docs/database/mysql/` 的范式专题：属性原子性与「非主属性完全依赖候选键」是两个独立的判据，把「多值字段存逗号串」当 1NF 违规是最常见的误判'),
        MALL: ('§4.3', '讲「何时故意反范式」时看 `pms_product` 与 `pms_sku_stock`：商品名、价格在 SKU 表里冗余一份，是为了「列表页一次查询拿全」而不做 JOIN——冗余的代价是「改商品名要同步更新所有 SKU」'),
        ADV: ('§3.2', '讲「反范式与分库分表」时对照 `docs/high-concurrency/mysql-sharding.md`：分片后跨库 JOIN 不可用，只能靠「冗余字段 + 异步补偿」，这时范式让位于「查询能不能一次走完」'),
    },
    'db-ch07': {
        GUI: ('§1.1', '讲「逻辑备份 vs 物理备份」时读 `docs/database/mysql/` 的运维章节：`mysqldump` 导出的是 SQL 文本（可跨版本、慢），`xtrabackup` 拷的是数据文件（快、要同版本），两者的恢复时间差一个数量级'),
        MALL: ('§3.1', '讲「最小权限」时看 `mall` 的 `application.yml` 里的数据源账号：业务账号只需要 `SELECT/INSERT/UPDATE/DELETE`，给 `DROP` 权限等于把「一次注入」升级成「删库」'),
        ADV: ('§2.2', '讲「binlog 与 PITR」时对照 `docs/high-concurrency/` 的 MySQL 文章：`ROW` 格式记的是行变更前后镜像，所以能做「精确到秒的时间点恢复」，`STATEMENT` 格式在 `NOW()`/`UUID()` 上无法重现'),
    },
    'db-ch08': {
        GUI: ('§1.1', '讲「复制链路」时读 `docs/database/mysql/` 的主从章节：`binlog dump → IO 线程写 relay log → SQL 线程重放`，三个环节各自的延迟来源不同，排查要分开看'),
        MALL: ('§1.2', '讲「读写分离」时看 `mall` 的单库配置：这个项目没有分库分表，正好用来对照「什么规模不需要拆」——单表千万级以内、QPS 几千，加索引与缓存比拆库划算得多'),
        ADV: ('§2.1', '讲「分片键与扩容」时对照 `docs/high-concurrency/mysql-sharding.md`：哈希分片扩容要「翻倍 + 迁移一半」，范围分片扩容简单但会热点——选哪种取决于「写入是否均匀」而不只是「查询方便」'),
    },
}

if __name__ == '__main__':
    sys.exit(apply('database', DATA))
