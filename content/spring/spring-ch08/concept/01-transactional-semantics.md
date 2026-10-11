# 一、@Transactional 的完整语义

`@Transactional` 是「声明式事务」的入口：它把「开启连接、begin、commit/rollback、释放连接」
这段样板代码交给 AOP 拦截器，业务方法只负责写逻辑。理解它，本质是理解
**一堆可配置的语义属性** 与 **它们各自的默认值**。

## 1. 传播行为：7 种取值与嵌套回滚的真实语义

传播行为（propagation）回答的是「当前方法被调用时，事务该怎么走」。
Spring 用 `Propagation` 枚举定义了 7 种取值，默认是 `REQUIRED`。

| 传播行为 | 有外层事务时 | 无外层事务时 | 回滚语义 |
|---|---|---|---|
| REQUIRED（默认） | 加入外层，共用一个事务 | 新建事务 | 内层抛异常会把整个事务标记为 rollback-only |
| REQUIRES_NEW | 挂起外层，新建独立事务 | 新建事务 | 内层独立提交/回滚，不影响外层 |
| NESTED | 在外层内建保存点（同连接） | 等价于 REQUIRED | 内层回滚到保存点，外层可继续提交 |
| SUPPORTS | 加入外层 | 以非事务方式运行 | 不新建事务 |
| NOT_SUPPORTED | 挂起外层，以非事务方式运行 | 非事务运行 | 无事务 |
| MANDATORY | 加入外层 | 抛 `IllegalTransactionStateException` | 必须已有事务 |
| NEVER | 抛异常 | 非事务运行 | 必须无事务 |

嵌套的真实差异（本机 `ex02` / `ex03` / `ex04` 实测）：

```
REQUIRED      外层回滚 -> 内层一起没了        db=[]
REQUIRES_NEW  外层回滚 -> 内层已提交仍在      db=[insert:item]
NESTED        内层回滚 -> 外层仍可提交        db=[insert:order]
NESTED        外层回滚 -> 内层也一起没了      db=[]
```

### 🧑‍💻 程序员视角
- 选型决策树：只读查询且外层已有事务 → `SUPPORTS`；必须绝对独立（如写审计日志、发消息落库）
  → `REQUIRES_NEW`；希望「内层失败但不影响外层主流程」→ `NESTED`（前提是数据库支持保存点）；
- 上线事故：把「写流水」写成 `REQUIRED`，主流程回滚时流水一起回滚，对账对不上；
  改成 `REQUIRES_NEW` 后又要小心它**新开一条数据库连接**——连接池小、并发高时会打死连接池；
- 排查顺序：先在日志里确认拦截器有没有触发（`logging.level.org.springframework.transaction=DEBUG`），
  再看「是不是同一个事务」（比较 `TransactionSynchronizationManager` 里的 resource）。

### 🎓 博士生视角
- 形式化：事务上下文是一组「资源槽位」`Map<Object key, Object value>`，key 是
  `DataSource` 或 `EntityManagerFactory`，value 是 `ConnectionHolder`；传播行为决定的
  其实是「要不要把当前线程的槽位复用、挂起、还是重建」，以及对应事务的提交点归属；
- NESTED 与 REQUIRES_NEW 的本质差别是**物理连接的条数**：NESTED 复用同一条 `Connection`，
  用 JDBC `Savepoint` 做子事务；REQUIRES_NEW 必须有第二条连接，因此它**不是真正的嵌套**，
  而是「挂起 + 并行事务」；
- `rollbackOnly` 是一个**单向标记**：一旦被置位，即使外层捕获异常后选择提交，Spring 也会
  在最终提交点抛 `UnexpectedRollbackException`——这正是「异常被吞」与「participation 回滚」
  两类事故的共同机制来源。

### 📚 考研者视角
- 笔面标准问法：「`REQUIRED` 和 `REQUIRES_NEW` 的区别？」标准答：前者加入当前事务、
  内外同生共死；后者挂起当前事务、新建独立事务，互不影响；
- 易混对比：`NESTED` ≠ `REQUIRES_NEW`——NESTED 依赖数据库保存点、共享连接、外层回滚会连带内层；
  REQUIRES_NEW 是新连接、外层回滚不影响内层。不少面试官用「内层回滚外层能不能提交」一问定生死；
- 常考边界：`MANDATORY` 无外层事务抛异常、`NEVER` 有外层事务抛异常，`SUPPORTS` 两种情形都不报错。

## 2. 隔离级别、readOnly、timeout 与回滚规则

除了传播行为，`@Transactional` 还有四个关键属性：

- **isolation**：默认 `DEFAULT`（用数据库默认）。Spring 的 `Isolation` 枚举会翻译成
  `java.sql.Connection` 上的 `TRANSACTION_*` 常量；
- **readOnly**：默认 `false`。置 `true` 表示「本事务只读」，是一个**给驱动/Hibernate 的提示**，
  不是数据库强制约束（写操作是否被拒取决于驱动与 `FlushMode`）；
- **timeout**：默认 `-1`（不超时），单位秒。超时后事务被标记回滚，提交点抛异常；
- **rollbackFor / noRollbackFor**：默认「**只对 `RuntimeException` 与 `Error` 回滚，对 checked
  异常不回滚**」，这是最经典的坑。

隔离级别与三种读现象（本机 `ex10` 实测矩阵）：

```
READ_UNCOMMITTED  dirty=true  nonrepeatable=true  phantom=true
READ_COMMITTED    dirty=false nonrepeatable=true  phantom=true
REPEATABLE_READ   dirty=false nonrepeatable=false phantom=true
SERIALIZABLE      dirty=false nonrepeatable=false phantom=false
```

Spring `Isolation` 与数据库的映射关系：

| Spring Isolation | java.sql 常量 | MySQL 默认？ | Oracle 默认？ |
|---|---|---|---|
| READ_UNCOMMITTED | TRANSACTION_READ_UNCOMMITTED | 否 | 否 |
| READ_COMMITTED | TRANSACTION_READ_COMMITTED | 否 | **是** |
| REPEATABLE_READ | TRANSACTION_REPEATABLE_READ | **是** | 否 |
| SERIALIZABLE | TRANSACTION_SERIALIZABLE | 否 | 否 |

### 🧑‍💻 程序员视角
- 上手经验：**别乱改隔离级别**。多数业务用数据库默认即可；`readOnly=true` 值得加在查询方法上，
  它让 Hibernate 关闭脏检查、部分驱动走只读连接，是低成本的优化；
- 事故：把「扣款」方法写成 `@Transactional(readOnly = true)`，本地 MySQL 因为不会真拦写操作，
  在测试环境「看起来正常」，换到某些严格驱动或只读从库上直接抛
  `Connection is read-only`；
- 排查顺序：对账不平先查「是不是 checked 异常没回滚」，再看「是不是超时被静默回滚」，
  最后才怀疑隔离级别。

### 🎓 博士生视角
- `readOnly` 的语义层级：Spring 只是把它传给 `Connection.setReadOnly` 与 `Session` 的
  `FlushMode`，真正的强制点（如 MySQL 对只读事务的优化、从库拒绝写）在数据库侧；因此它是
  **优化提示 + 约定**，不是安全边界；
- 隔离级别的映射是「标准 SQL 隔离级别 → JDBC 常量 → 数据库实现」的三段翻译，语义落地时
  可能被数据库改写：InnoDB 的 REPEATABLE READ 借助 next-key lock 在多数场景下**抑制了幻读**，
  与「标准 RR 允许幻读」不同，所以「MySQL 的 RR ≈ 其他库的 SERIALIZABLE（部分）」；
- `rollbackFor` 的默认口径源自 `TransactionAspectSupport` 里
  `rollbackOn(Throwable)` 的判定：`RuntimeException || Error` 为真，checked 异常为假。

### 📚 考研者视角
- 笔面标准问法：「三种读现象的定义？」标准答：脏读=读到未提交数据；不可重复读=同一行两次读值不同；
  幻读=同一范围两次查询行数不同（多出新行）；
- 常考口径：给出隔离级别，判断哪些现象可能发生（对照上表）；反向给出「要杜绝脏读选哪个级别」；
- 易混点：「不可重复读」针对**同一行的值**，「幻读」针对**行的集合/数量**，二者常被混为一谈；
  另外要记住 `@Transactional` **默认不回滚 checked 异常**这一反直觉默认值。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 默认 REQUIRED + 只回滚运行时异常；REQUIRES_NEW 会新开连接；readOnly 是提示不是约束。 |
| 博士生 | 传播行为本质是资源槽位的复用/挂起/重建；NESTED 用 Savepoint 共享连接；rollbackOnly 单向不可逆。 |
| 考研者 | 必考「REQUIRED vs REQUIRES_NEW vs NESTED」与「三种读现象矩阵」；默认不回滚 checked 异常。 |
