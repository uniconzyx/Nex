# fs-ch05 易错点（Pitfalls）

1. **用 offset 深分页，还在并发写入下翻页** —— ex03 实跑：插入一条高分记录后 offset 第 2 页由 `[5,4,3]` 变成 `[6,5,4]`，把第 1 页已出现过的 6 又返回一次（`offset_repeats_row_from_page1=True`）；游标页仍为 `[5,4,3]`（`cursor_stable_across_insert=True`）。✅ 翻页用游标（keyset）：`WHERE (sort_key, id) < (cursor_key, cursor_id)`，且游标必须包含完整排序键（含唯一键）。

2. **复合索引列序按「选择性高到低」排** —— 索引的有序性由列序决定，把低频列放第一位会让「只查高频列」的查询无法定位。✅ 按最左前缀的实际查询组合排：等值条件列在前、范围条件列在后；ex09 的 `(tenant_id, kind)` 同时支持 `tenant_id=? AND kind=?` 与 `tenant_id=? AND kind>?`。

3. **以为「建了索引就一定走索引」** —— ex09 实跑 `SELECT id, payload FROM events WHERE kind = ?` 在 `(tenant_id, kind)` 上仍是 `SCAN events`（`uses_index=False`）。✅ 以计划串为唯一判据：出现 `SEARCH ... USING INDEX` 才是走了索引，`SCAN` 就是没走；建索引后必须复查计划。

4. **以为「只查主键就一定覆盖」或「有索引就一定覆盖」** —— ex09 中同一索引、同一条 WHERE，`SELECT id` 报 `USING COVERING INDEX`，而 `SELECT id, payload` 退回 `USING INDEX`（需回表取 payload）。✅ 覆盖的判定是「查询涉及的所有列 ⊆ 索引列 ∪ 主键」，多一个非索引列就需要回表。

5. **把「游标分页」当成「更快的 offset」** —— 两者的差别是**语义**不是性能：offset 依赖绝对位置会漂移，游标把位置编码进数据。✅ 把游标当 API 契约的一部分设计：编码格式、版本号、签名、TTL 都要定，否则客户端可以伪造游标越权读取。

6. **循环访问 ORM 的关联属性** —— ex08 实跑：5 个作者的嵌套写法发 6 次查询（1+N），JOIN 写法发 1 次，两者结果完全相同（`same_result=true`）。✅ 用**操作计数**（而非代码观感）判定 N+1，修复用 JOIN 或 `WHERE fk IN (...)` 批量合并，并断言修复后返回数据一致。

7. **用 GET 触发有副作用的操作** —— GET 是安全方法，会被浏览器预取、代理缓存、爬虫抓取，一个 `GET /orders/42/cancel` 可能被批量触发。✅ 有副作用用 POST；状态变更优先设计成对资源的 PATCH/PUT（如 `{"status":"cancelled"}`）。

8. **POST 用来更新、PUT 用来打补丁** —— PUT 的语义是整体替换（缺失字段应被清空或整体校验失败），PATCH 才是部分更新。✅ 按 RFC 9110 的方法语义分配：PUT 全量、PATCH 部分、POST 在集合下创建并返回 201 + Location。

9. **状态码一律 200 加业务码，或出错一律 500** —— 这等于关掉代理重试、熔断、429 退避、503 摘节点等全部协议层能力。✅ 按语义映射（ex01 表）：创建 201、删除 204、不存在 404、唯一键冲突 409、schema 不过 422、媒体类型不支持 415、超配额 429、方法不允许 405。

10. **把排序/过滤字段名直接拼进 SQL，以为参数化能保护** —— 占位符只能保护「值」，不能保护「标识符」。✅ 字段名走白名单映射：ex04 中 `sort=password` 与 `sort=id; DROP TABLE articles` 均在解析阶段被拒（`sort: field not in whitelist` / `sort: malformed token`）。

11. **只校验类型、不校验边界与多余字段** —— ex05 实跑：`score=101` 必须报 `maximum is 100`，`score=1.5` 必须报 `expected integer`，`extraField` 必须报 `additional property not allowed`（防 mass assignment）。✅ 必填、类型、边界、枚举、正则、多余字段六类都要显式声明，并给出 JSON Pointer 路径。

12. **每个接口自己造错误体字段** —— 客户端无法程序化处理，文档与实现持续漂移。✅ 统一 RFC 9457 Problem Details（ex06：5 个核心成员 + 允许的扩展成员），并让所有 4xx 都 `$ref` 到同一个 schema（ex11 的 `every_4xx_uses_problem_json=true`）。

13. **URL 版本与 Header 版本混用、且不定义缺省与未知版本** —— ex12 实跑：同一路径 `/v3/articles` 在 URL 策略下是「版本不存在」，在 Header 策略下静默回退到 v1；两种策略同时上线会出现「同一 URL 返回不同版本」。✅ 选一条策略，并显式定义「缺省版本、未知版本（404/406/回退）、废弃时间表」三件事。

14. **限流只用固定窗口计数器、超时只设客户端** —— 固定窗口在边界可放行 2 倍流量；只设客户端超时会让服务端继续处理已被放弃的请求，连接与 CPU 被占满。✅ 用令牌桶（ex13：容量管突发、补充速率管长期，第一段速率 5.263/s 衰减到第二段 4/s），并按「客户端 > 网关 > 服务端 > 下游 > SQL」分级设置超时且保证可取消。
