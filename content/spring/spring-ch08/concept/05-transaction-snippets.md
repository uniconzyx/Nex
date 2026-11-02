# 事务代码速查：凯喵的五段可复制片段

> 这一篇是配套速查。前四篇讲清了事务语义、失效场景与并发控制，这一篇把它们落成代码。每段都标注「为什么这么写」，因为事务这一块的坑几乎全在「看起来对的写法其实不对」上。

## 一、正确的最小事务方法

```java
@Service
public class OrderService {

    @Transactional(rollbackFor = Exception.class)
    public void place(Order order) {
        orderMapper.insert(order);
        stockMapper.decr(order.getSkuId(), order.getQty());
    }
}
```

`rollbackFor = Exception.class` 是关键：Spring 默认只对 `RuntimeException` 和 `Error` 回滚，受检异常（如 `IOException`）**不会回滚**，这是最高频的误解。写上它之后，任何异常都会触发回滚。

另一个隐含要求是方法必须是 `public`——代理只能拦截 public 方法，`private`/`protected` 上的注解会被静默忽略。

## 二、自调用的失效与三种修法

```java
@Service
public class Svc {

    @Autowired private Svc self;          // 方案一：注入自己（可能循环依赖）

    public void outer() {
        // this.inner();                  // 错了：不走代理，事务失效
        self.inner();                     // 对了：走代理
    }

    @Transactional
    public void inner() { /* ... */ }
}
```

另外两种修法：把 `inner` 拆到另一个 Bean（推荐，语义清楚），或者用 `TransactionTemplate` 手动控制。凯喵的偏好是拆 Bean——它能从结构上消除这类问题，而不是靠记住「不要自调用」。

## 三、TransactionTemplate 的显式控制

需要精确控制事务边界时，模板比注解更可控。

```java
@Service
public class Svc {
    private final TransactionTemplate tx;

    public Svc(PlatformTransactionManager tm) {
        this.tx = new TransactionTemplate(tm);
        this.tx.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    }

    public void run() {
        tx.executeWithoutResult(status -> {
            // 这里的异常会自动回滚
        });
    }
}
```

`REQUIRES_NEW` 会挂起当前事务、开一个新事务，适合「主流程失败但日志必须留下」这类场景。注意它会占用额外的数据库连接，嵌套多层时有连接池耗尽的风险。

## 四、传播行为的四行对照

```text
REQUIRED      有则加入，无则新建      ← 默认，90% 场景
REQUIRES_NEW  挂起当前，总是新建      ← 独立事务（记日志、发消息）
NESTED        有则建保存点，无则等同 REQUIRED   ← 部分回滚
SUPPORTS      有则加入，无则以非事务运行        ← 只读查询
```

凯喵的提醒：`NESTED` 只在支持保存点的数据源上有效（JDBC 支持，某些 JPA 实现不支持），写之前先确认。而 `REQUIRES_NEW` 与 `REQUIRED` 混用时，外层回滚不会影响内层已提交的事务——这个特性既能救命也能埋雷。

## 五、乐观锁与重试

```java
@Retryable(
    retryFor = OptimisticLockingFailureException.class,
    maxAttempts = 3,
    backoff = @Backoff(delay = 50, multiplier = 2))
@Transactional
public void updateBalance(Long id, BigDecimal delta) {
    Account a = repo.findById(id).orElseThrow();
    a.setBalance(a.getBalance().add(delta));
    // 提交时 @Version 不匹配会抛 OptimisticLockingFailureException
}
```

关键点是 `@Retryable` 必须在**事务外层**——如果重试发生在同一个事务里，被重试的代码读到的是同一个快照，重试多少次都一样。所以实际做法是把重试加在调用方，或者用 `TransactionTemplate` 让每次重试都开新事务。

## 收尾

这五段代码对应事务实践里最常出错的五件事：回滚规则、自调用失效、显式事务边界、传播行为、乐观锁重试。凯喵的经验是，事务的坑几乎都能归到一句：**注解只有经过代理才生效**。所以任何「明明加了 `@Transactional` 却没回滚」的情况，第一反应就应该是「这个方法有没有真的被代理调用」。
