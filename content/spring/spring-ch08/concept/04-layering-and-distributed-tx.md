# 四、分层架构、DTO/VO 转换与分布式事务概览

事务边界落在哪一层、对象在层与层之间怎么转换，决定了系统的可维护性；
当一次业务跨越多个数据库/服务时，本地事务不够用，就需要分布式事务方案。

## 1. 分层架构与 Entity / DTO / VO 的职责边界

```
Controller  --(DTO 入参 / VO 出参)-->  Service  --(Entity / 领域对象)-->  Mapper
   |                                     |
   |  参数校验、HTTP 语义                 |  事务边界（@Transactional 加在 Service）
   +-------------------------------------+
```

- **Entity**：与数据库表一一对应，承载持久化状态，**可含敏感字段**（password、身份证）；
- **DTO**（Data Transfer Object）：层间传输/入参对象，只含**可写**字段，用于接收前端数据；
- **VO**（View Object）：返回给前端的视图对象，做**脱敏/裁剪/聚合**，**绝不带敏感字段**。

职责口诀：**转换发生在 Service 层**（DTO→Entity 入库、Entity→VO 出参），
Mapper 只认 Entity，Controller 只认 DTO/VO。

本机 `ex14` 实测：

```
entity from DTO: id=1001 name=Tom phone=13800001234
VO: id=1001 name=Tom phoneMasked=138****1234
VO carries password field: false
```

### 🧑‍💻 程序员视角
- 工程惯例：Service 方法签名用 DTO 进、VO 出；Entity 不出 Service（否则持久化对象泄漏到 Web 层，
  前端能直接改 id/内部状态）；敏感字段用 `@JsonIgnore` 只是补救，根因是**用了 Entity 当出参**；
- 事故：把 Entity 直接返回给前端，`password` 被序列化；或把前端传入的 Entity 直接 `updateById`，
  前端伪造了 `role=admin` 字段导致越权（**过度绑定**）；
- 排查顺序：出参里出现不该有的字段 → 查是否返回了 Entity；入库字段被篡改 → 查是否用 DTO 白名单
  而不是「前端 JSON 直接映射 Entity」。

### 🎓 博士生视角
- 分层的形式化动机：给每层一个**独立的类型**，就把「外部契约」与「内部模型」解耦，
  演化时互不牵连（数据库加字段不必改 API、API 改字段不必改表）；这是**接口隔离**在数据模型上的投影；
- DTO/VO 的划分本质是「信息流的方向性」：入参要能写、出参要能脱敏，二者约束相反，
  强行共用一个类型必然要么过度暴露、要么无法写入（Mass Assignment 漏洞的根因）；
- 转换的实现方式（手写 / MapStruct / BeanUtils）差异只是性能与类型安全，语义边界不变。

### 📚 考研者视角
- 笔面标准问法：「DTO、VO、Entity 有什么区别？」标准答：Entity 对应表、含持久化字段；
  DTO 用于层间传输（入参）；VO 用于返回前端（脱敏）；转换放 Service；
- 常考追问：「为什么不直接把 Entity 返回给前端？」答：暴露敏感/内部字段、耦合表结构、
  引发过度绑定与越权；
- 关联考点：Mass Assignment（过度绑定）与越权、对象序列化的字段裁剪策略。

## 2. 多数据源与分布式事务：2PC/XA、TCC、Saga、本地消息表、Seata AT

当一个业务要写**两个库**（或两个服务），本地事务的 ACID 就不够用了。

| 方案 | 一致性 | 思想 | 代价 |
|---|---|---|---|
| 2PC / XA | 强一致 | 准备(投票) + 提交，协调者统一决定 | 同步阻塞、协调者单点、长事务持锁 |
| TCC | 最终一致 | Try 预留 / Confirm 确认 / Cancel 补偿 | 业务侵入大，要写三个方法、处理空回滚/悬挂 |
| Saga | 最终一致 | 一串本地事务 + 失败走补偿 | 无隔离性，需保证补偿幂等 |
| 本地消息表 | 最终一致 | 本地事务内写「消息表」，异步投递 | 需轮询投递、保证幂等 |
| Seata AT | 最终一致（近似强一致） | 代理 SQL，记 `undo_log`，全局锁 + 两阶段 | 需 TC 组件、对全局锁有依赖 |

`ex15` 用 2PC 模拟了经典失败场景：

```
phase1 all prepared (vote YES): True
coordinator crashed before sending COMMIT to P3
P1 committed=True P2 committed=True P3 committed=False
blocked participants: ['P3']
inconsistent state: True
recovery: replayed decision log -> all committed: True
```

这就是 2PC 的**阻塞问题**：参与者投 YES 后必须持锁等待，协调者崩溃就让 P3 一直阻塞；
若协调者带着「已决定提交」的日志恢复，可以重发 COMMIT 收敛（`recovery` 一行的 True）。

### 🧑‍💻 程序员视角
- 选型：能用一个库就别分布式；必须跨库时，优先「本地消息表 + 幂等消费」（业务侵入最小、
  对账好做）；对一致性要求高且有 TC 组件运维能力时用 Seata AT；对账类业务可用 Saga/TCC；
- 事故：把 XA 用在长业务流程上 → 全局锁长时间不释放，数据库连接被打满；
  Seata AT 下不恰当的全局锁顺序 → 死锁；
- 排查顺序：先看是不是「跨库」，再看「补偿是否幂等」「消息是否重复投递」，最后看
  「全局事务是否悬挂/空回滚」（TCC 的两大经典问题）。

### 🎓 博士生视角
- 理论背景：2PC 的阻塞源于「参与者投 YES 后放弃自主决定权」，属于**阻塞式原子提交**；
  3PC 引入超时与 pre-commit 缓解阻塞但增加了复杂度与「网络分区下仍可能不一致」的问题
  （FLP 不可能性在网络分区场景下的体现）；
- CAP 视角：跨库强一致（2PC）要牺牲可用性（A），最终一致方案（Saga/消息表）牺牲一致性（C）换可用性；
  选择哪条边取决于业务对「中间态」的容忍度；
- Seata AT 的本质：用「全局锁 + 前后镜像 `undo_log`」把「补偿」自动化，把「写 SQL」这件事
  从「业务自己写补偿」降级为「框架自动生成反向 SQL」，代价是引入了 TC 与全局锁这一层新的耦合。

### 📚 考研者视角
- 笔面标准问法：「分布式事务有哪些方案？2PC 的问题是什么？」标准答：2PC/XA、TCC、Saga、
  本地消息表、Seata AT；2PC 问题是同步阻塞、协调者单点、数据不一致窗口；
- 常考追问：「TCC 的空回滚和悬挂是什么？怎么解决？」答：空回滚=Cancel 先于 Try 到达；
  悬挂=Cancel 后 Try 才到；用「事务状态记录 + 幂等 + 防悬挂校验」解决；
- 易错点：以为 Seata AT 是「强一致」——它是**全局锁保证的近似强一致**，本质仍是两阶段 + 补偿。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 转换放 Service；Entity 不出层；跨库优先本地消息表；Seata 有全局锁成本。 |
| 博士生 | 分层=接口隔离在数据模型上的投影；2PC 是阻塞式原子提交；最终一致在 CAP 上换可用性。 |
| 考研者 | 必考「DTO/VO/Entity 区别」与「分布式事务方案对比 + 2PC 三宗罪」。 |
