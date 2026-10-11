# 02 · 回表、覆盖索引与最左前缀原则

> 博士看"访问路径代价模型"，程序员看"如何让一条 SQL 只走索引、不碰聚簇索引"。

## 1. 回表（Bookmark Lookup）：二级索引的隐含成本

二级索引叶子只存 `(索引列, 主键值)`。当查询还需要其它列时，InnoDB 用拿到的主键**回聚簇索引再查一次**取完整行。回表次数 = 二级索引命中的行数。命中 1 行回表 1 次；命中 10 万行就回表 10 万次——这就是为什么"大结果集 + 二级索引 + SELECT *"有时不如直接全表扫描。

## 2. 覆盖索引（Covering Index）：避免回表

若索引**本身包含查询所需的全部列**（包括 SELECT 列与 WHERE 列），引擎在二级索引叶子就能拿到一切，**无需回表**。`EXPLAIN` 的 `Extra` 出现 **`Using index`** 即表示覆盖索引生效。

例：索引 `(dept_id, salary)`，查询 `SELECT dept_id, salary FROM emp WHERE dept_id=20` —— 两列都在索引里 → 覆盖，`Extra: Using index`。
而 `SELECT * FROM emp WHERE dept_id=20` —— 还要 name 等列，索引没有 → 必须回表，`Extra` 无 `Using index`。

设计技巧：把"常一起查的列"放进联合索引末尾（如 `(user_id, status, created_at)` 覆盖"某用户、某状态、按时间"的列表查询），用少量冗余索引空间换掉回表 I/O。

## 3. 最左前缀原则（Leftmost Prefix）

联合索引 `(a, b, c)` 相当于建了 `(a)`、`(a,b)`、`(a,b,c)` 三套前缀。查询**必须从最左列开始**才能利用索引：
- `WHERE a=1` → 用 `(a)`
- `WHERE a=1 AND b=2` → 用 `(a,b)`
- `WHERE b=2` 或 `WHERE b=2 AND c=3` → **用不上该索引**（缺少最左列 a）→ 退化全表扫描
- `WHERE a=1 AND c=3` → 仅用 `(a)`，c 只能在回表后/ICP 过滤，**不能**用索引定位 c

**范围查询会"截断"后续列**：`WHERE a=1 AND b>10 AND c=5`，a 等值、b 范围，索引能用到 `(a,b)` 做范围定位，但 **c 无法再用于索引定位**（b 已是范围，后续列顺序失效），c 靠 **索引下推（ICP）** 在引擎层过滤。

## 4. 索引下推 ICP（Index Condition Pushdown，5.6+）

没有 ICP 时，存储引擎按索引把 `a=1 AND b>10` 命中的行**全部回表**交给 Server 层，Server 再判断 `c=5`。
有 ICP 时，`c=5` 这个条件被**下推到存储引擎**，在读取索引时就顺手过滤掉不满足 c 的行，**减少回表行数**。`EXPLAIN` 的 `Extra` 出现 **`Using index condition`**。这是"最左前缀被范围截断后"的重要补救。

## 5. 工程实践与坑

- 列顺序口诀：**等值列在前、范围列在中、排序/覆盖列在后**（如 `(status, created_at)` 支持 `WHERE status=1 ORDER BY created_at`）。
- `LIKE 'abc%'`（前缀匹配）能用上索引；`LIKE '%abc'`（前导通配）**用不上**（违反最左前缀）。
- 对索引列做函数/运算（`WHERE YEAR(created_at)=2023`、`WHERE amount*1 > 100`）→ 索引失效，应改成范围（`created_at BETWEEN '2023-01-01' AND '2023-12-31'`）。
- 隐式类型转换（`WHERE phone=13800138000`，phone 是 VARCHAR）→ 等价于对列套函数 → 失效。

## 6. 可运行代码

见 `examples/ex02-covering-index.json`（覆盖索引 `Using index`）、`examples/ex03-back-to-table.json`（`SELECT *` 回表对比）、`examples/ex04-leftmost-prefix-fail.json`（缺最左列全表扫）、`examples/ex05-leftmost-range-break.json`（范围截断）、`examples/ex06-index-condition-pushdown.json`（ICP）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- `EXPLAIN` 的 `Extra` 出现 **`Using index`** 就说明用了覆盖索引，省掉了回表——这是最有效的读优化之一。
- **索引列上不要做函数运算或隐式类型转换**：`WHERE DATE(create_time) = '2026-01-01'` 与 `WHERE phone = 13800000000`（varchar 列传数字）都会让索引失效。
- 记住最左前缀：建 `(a,b,c)` 时 `(a)`、`(a,b)`、`(a,b,c)` 可用，**单独 `(b)` 不可用**；范围查询后的列也不能用于定位。

### 🎓 博士生视角
- 最左前缀原则源于联合索引按复合键的**字典序**排列：B+ 树只在「前缀连续相等」的子区间内才有序，因此只有前缀能用于范围定位——这是「有序性的可用范围」问题，而非实现细节。
- **回表**是二级索引到聚簇索引的二次查找，本质是随机 IO；**覆盖索引**把两次查找降为一次顺序扫描，用「索引变大」换「少一次随机 IO」。
- 索引下推（ICP）进一步把 WHERE 条件下推到存储引擎层过滤，减少回表行数——这体现了「尽量在数据所在层过滤」的通用优化原则。

### 📚 考研者视角
- 自命题高频：**给定查询与索引，判断能否走上索引、是否引发回表、是否覆盖索引**；以及「给出建索引建议」。
- 若考题含 408 数据结构，会把「B+ 树的范围查询为何高效」与「叶子链表 + 有序」绑定考查。
- 记忆锚点：**索引列上做函数运算或隐式类型转换 → 索引失效**；**覆盖索引 = 避免回表**。
