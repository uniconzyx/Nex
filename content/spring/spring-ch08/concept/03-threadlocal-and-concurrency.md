# 三、ThreadLocal 保存事务状态与并发陷阱

事务是「线程绑定」的：同一个线程内的所有数据库操作必须拿到**同一条连接**，否则
begin 在 A、commit 在 B，事务根本不成立。Spring 用 ThreadLocal 把连接绑到线程上。

## 1. ThreadLocal 与事务同步管理器

```
TransactionSynchronizationManager（每个线程一份）
  ThreadLocal<Map<Object, Object>> resources
        key   = DataSource 实例
        value = ConnectionHolder（包装了这条 Connection + 事务状态）

同一线程内：Service -> Mapper 反复 getConnection()
            都从 ThreadLocal 里拿到同一个 ConnectionHolder -> 同一条连接
```

`ConnectionHolder` 上记着 `transactionActive`、`savepoint` 等状态；`commit` / `rollback`
发生在拦截器的 `finally` 里，最后把资源从 ThreadLocal 解绑。

### 🧑‍💻 程序员视角
- 工程含义：**任何跨越线程边界的数据库操作都会脱离当前事务**。`new Thread`、
  `ExecutorService.submit`、`CompletableFuture.supplyAsync`、`@Async` 都在新线程里执行，
  拿不到原线程的 `ConnectionHolder`；
- 事故：主流程 `@Transactional` 里用线程池并发写入，主事务回滚了，子线程的写入却已提交（或反之）；
- 排查顺序：看日志里两次 SQL 的连接 id 是否一致；用
  `TransactionSynchronizationManager.isActualTransactionActive()` 在子线程里断言；
  确认「是不是同一个线程」。

### 🎓 博士生视角
- 形式化：`TransactionSynchronizationManager` 的核心是
  `ThreadLocal<Map<Object, Object>> resources` + `ThreadLocal<Set<TransactionSynchronization>> synchronizations`，
  提供「资源与线程的绑定/解绑」以及「事务生命周期回调」两件事；
- 为什么是 ThreadLocal 而不是参数透传：事务上下文需要**隐式**穿过 Service→Mapper 多层调用，
  显式透传会污染所有方法签名；ThreadLocal 用「线程」这个天然的调用栈载体换取零侵入，
  代价是「上下文与线程强耦合」；
- 解绑必须发生在 `finally`：ThreadLocal 不清会随线程存活；在线程池里就是
  **内存泄漏 + 上下文串号**（见 `ex09` 实测：线程池复用不清理 → 串号 = true）。

### 📚 考研者视角
- 笔面标准问法：「Spring 事务为什么能保证同一线程用同一条连接？」标准答：靠
  `TransactionSynchronizationManager` 的 ThreadLocal 把 `ConnectionHolder` 绑定到当前线程；
- 常考追问：「ThreadLocal 有什么坑？」答：内存泄漏（线程池复用不 remove）、
  上下文串号、跨线程丢失；`InheritableThreadLocal` 只对「新建子线程」生效，对线程池无效；
- 关联考点：ThreadLocal 的 `ThreadLocalMap` 结构与弱引用 key（`Entry extends WeakReference<ThreadLocal>`）。

## 2. 线程池与异步下的事务丢失 / 串号

本机 `ex09` 实测：

```
单线程：上下文正确         = true
单线程：remove() 后为空    = true
线程池复用且不清理：串号   = true   <-- 上个任务的事务上下文被下个任务读到
```

### 🧑‍💻 程序员视角
- 异步里要参与事务的正确姿势：把需要入库的写操作**放在事务线程内同步完成**；
  真要异步，则用 `@Transactional` 在异步方法**自成一个事务**（注意它不再属于外层事务），
  或用 `TransactionSynchronizationManager.registerSynchronization` 在**事务提交后**触发
  （`afterCommit`）副作用；
- 事故：`@Async` + `@Transactional` 写在同一个类里，`@Async` 通过代理生效、事务却因
  自调用或线程切换而错乱；表现为「偶尔丢失」；
- 实践惯例：发 MQ / 发通知这类副作用放进 `afterCommit` 回调，保证「库提交了才发消息」，
  避免「消息发了、库回滚了」的不一致（本地消息表思想，见 `concept/04`）。

### 🎓 博士生视角
- 线程池复用让 ThreadLocal 的生命周期从「线程」变成「池中线程的整个存活期」，与「任务」
  不再对齐；因此「任务级上下文」必须显式清理，或用 `TransmittableThreadLocal`（TTL）
  在提交任务时做快照传递；
- 事务与异步的语义冲突是本质的：事务是**线程绑定的原子单元**，异步是按任务并行的执行模型；
  强行让两者共享上下文，只会得到「部分提交」的中间态；
- `@Async` 的传播：它把调用搬到另一线程，`AopContext` / `TransactionSynchronizationManager`
  的 ThreadLocal 都不会跟过去，所以异步方法内 `isActualTransactionActive()` 为 false。

### 📚 考研者视角
- 笔面标准问法：「`@Async` 方法里的 `@Transactional` 和外层是同一个事务吗？」标准答：不是；
  异步在新线程执行，线程绑定的连接与事务上下文都不共享，它自己开启/提交自己的事务；
- 常考追问：「事务提交后想发消息怎么办？」答：`TransactionSynchronization#afterCommit`
  或事务消息 / 本地消息表；
- 易错点：以为 `InheritableThreadLocal` 能解决线程池传递——它对线程池复用无效（线程是复用的、
  不会重新继承）。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 事务是线程绑定的；跨线程必丢；副作用放 `afterCommit`；线程池里必须清理 ThreadLocal。 |
| 博士生 | `resources` 是 ThreadLocal 的 Map；绑定/解绑在拦截器 finally；线程池复用破坏「任务级上下文」。 |
| 考研者 | 必考「ThreadLocal 绑定连接」与「@Async 不在同一事务」；关联 ThreadLocal 弱引用与内存泄漏。 |
