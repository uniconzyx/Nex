# fs-ch12 · 关键实现片段：网关路由与配置中心

> 承接 `01-何时该拆`、`02-网关边界`、`03-配置中心`。本节给出两处最易写错的实现片段，作为前面原则的「可运行锚点」。

## 1. 本节定位

原则和代码之间是同一件事的两面。下面两段是 §2、§3 里反复提到的「路由匹配顺序」「配置默认值兜底」的最小可运行写法。

### 2. 网关路由：精确优先 + 显式优先级

Spring Cloud Gateway 里路由按声明顺序匹配，宽泛前缀必须放在具体路由**之后**，否则会被 catch-all 吞掉：

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: orders-specific
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - name: RequestRateLimiter   # 漏桶/令牌桶在网关做
              args:
                redis-rate-limiter.replenishRate: 100
                redis-rate-limiter.burstCapacity: 200
        - id: api-catch-all
          uri: lb://fallback-service
          predicates:
            - Path=/api/**
```

`/api/orders/1` 必须命中 `orders-specific` 而非 `api-catch-all`——顺序写反就是「大部分请求都能通，但打到了错误的上游」这类难查 bug。

### 3. 配置中心客户端：默认值兜底

配置中心抖动时实例不能起不来。读取每一项都要给默认值，拿不到就用默认启动：

```java
@Value("${order.timeout.ms:3000}")        // 冒号后是默认值
private int orderTimeoutMs;

@PostConstruct
void init() {
    if (orderTimeoutMs <= 0) orderTimeoutMs = 3000;  // 双保险
}
```

新增字段必须向后兼容，旧实例忽略未知字段；配置变更与代码同样版本化、可回滚。这样配置中心短暂不可用时，服务靠默认值仍能起来，热更新反而提升韧性而非成为单点。
