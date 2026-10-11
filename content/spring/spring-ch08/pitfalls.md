# spring-ch08 易错点

1. **以为加了 `@Transactional` 就一定会回滚** —— 默认只对 `RuntimeException` 和 `Error` 回滚，**checked 异常不回滚**（`ex06` 实测：checked 异常回滚 = false）。正确写法：需要 checked 异常也回滚时显式声明 `@Transactional(rollbackFor = Exception.class)`。

2. **同类方法自调用导致事务失效** —— `this.method()` 不经过代理，拦截器不触发（`ex01`：自调用拦截 = false）。正确写法：把被调方法拆到另一个 Bean、注入自身代理，或用 `@EnableAspectJAutoProxy(exposeProxy = true)` + `AopContext.currentProxy()`。

3. **把 `@Transactional` 加在非 public（private / package-private）方法上** —— 代理模式只增强 public 方法（`ex08`：package-private 方法不出现在接口上）。正确写法：事务方法必须是 public，且从代理进入。

4. **异常被 catch 吞掉，方法正常返回** —— 拦截器看到「正常返回」就提交，脏数据落库（`ex07` 实测：吞掉后提交 = true）。正确写法：要么把异常抛出去，要么在 catch 里手动 `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()`。

5. **跨线程/异步执行数据库操作** —— 事务上下文靠 ThreadLocal 绑定线程，`new Thread` / 线程池 / `@Async` / `CompletableFuture` 都拿不到（`ex09` 线程池串号 = true）。正确写法：写操作留在事务线程内；副作用放 `TransactionSynchronization#afterCommit`。

6. **线程池复用不清理 ThreadLocal** —— 上一个任务的上下文被下一个任务读到（`ex09` 实测串号 = true），既串号也内存泄漏。正确写法：`finally` 里 `remove()`，或用 `TransmittableThreadLocal` 做任务级快照。

7. **数据库引擎不支持事务** —— 表用 MyISAM 建，`begin/commit` 形同虚设。正确写法：用 InnoDB（或等价支持事务的引擎），上线前确认 `SHOW TABLE STATUS` 的 Engine。

8. **`REQUIRES_NEW` 在高并发下打死连接池** —— 它每次都新开一条连接（挂起外层）。正确写法：评估连接池大小与并发量；能用 `REQUIRED` 就用 `REQUIRED`，`REQUIRES_NEW` 只用于确实要独立提交的场景（如审计日志）。

9. **把 `NESTED` 当成 `REQUIRES_NEW` 用** —— `NESTED` 依赖数据库保存点、共享外层连接，**外层回滚会连带内层**（`ex04`：外层回滚 → 内层也没了）。正确写法：要「外层回滚不影响内层」必须用 `REQUIRES_NEW`。

10. **参与外层事务的内层异常被吞，提交时抛 `UnexpectedRollbackException`** —— 事务被标记 `rollbackOnly` 后，外层即使选择提交也会失败。正确写法：内层异常要么上抛，要么明确不参与外层事务（`REQUIRES_NEW`）。

11. **`readOnly = true` 却执行写操作** —— readOnly 只是给驱动/Hibernate 的提示，不是数据库强制约束；某些驱动/只读从库会直接抛 `Connection is read-only`。正确写法：只读事务只做查询；写方法不要标 readOnly。

12. **长事务里做远程调用 / 大批量处理 / 等用户输入** —— 事务长时间持有连接与行锁，拖垮数据库。正确写法：把非数据库操作移出事务；缩小事务边界（只包住必要的 SQL）。

13. **多数据源下用错了连接** —— `@Transactional` 若不指定事务管理器（`@Transactional(transactionManager = "xxxTxManager")`），或方法内手写新连接，会脱离事务。正确写法：多数据源时显式指定事务管理器，避免混用直连。

14. **以为 `@Async` 方法上的 `@Transactional` 和外层是同一个事务** —— 异步在别的线程执行，是**另一个独立事务**。正确写法：明确区分「主事务」与「异步副作用」；需要一致就放进 `afterCommit` 或走消息表。

15. **把 Entity 直接返回给前端 / 用 Entity 接收前端入参** —— 前者泄漏敏感字段（`ex14` 实测：VO 上不存在 password 字段，`hasPasswordField=false`），后者引发过度绑定（前端伪造 `role=admin`）。正确写法：入参用 DTO、出参用 VO、转换放 Service 层。

16. **跨库用 2PC/XA 处理长业务导致全局锁长时间不释放** —— 参与者投 YES 后持锁等待，协调者崩溃就阻塞（`ex15`：P3 阻塞、状态不一致）。正确写法：能用单库就别分布式；跨库优先本地消息表 + 幂等，或 Seata AT，并评估锁与超时。

17. **补偿不幂等导致重复扣款/重复发货** —— TCC/Saga 的重试与网络重发会让 `Cancel`/补偿被执行多次。正确写法：所有 Confirm/Cancel 幂等；记录事务状态，处理「空回滚」与「悬挂」。

18. **事务提交与缓存更新顺序错乱** —— 先删缓存再提交事务，并发下会把旧值重新写回缓存。正确写法：先提交事务、再删缓存（或延迟双删 / binlog 订阅），并接受短暂不一致。
