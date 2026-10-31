# fs-ch11 · Spring Boot 3 工程骨架：分层边界、异常与校验收口 · 常见错误

1. **在 Controller 里直接写 SQL / 调 Repository** —— 错在：`@RestController` 的方法里直接 `@Autowired JpaRepository` 然后 `repo.save(...)`，跳过了 service。

   *为什么*：这破坏了分层：事务边界、业务规则、缓存都失控；Repository 不知道自己在不在事务里，异常也绕过了 service 的统一处理。以后要加「保存前发消息」「保存后清缓存」只能回过头改 controller，牵一发动全身。

   *怎么改*：Controller 只注入 Service，由 Service 注入 Repository。所有写库与业务编排都在 service 的方法里（带上 `@Transactional`）。

2. **业务异常被当系统异常处理、堆栈返前端** —— 错在：advice 里 `return ApiError(500, e.getMessage())`，把 `e.toString()` 甚至堆栈写进响应体。

   *为什么*：业务异常（如「用户不存在」）本是产品体验的一部分，应给明确业务码+友好提示；而系统异常若把堆栈返前端，等于泄露类名/行号/SQL，给攻击者指纹信息。二者都错：前者让用户看不懂，后者危害安全。

   *怎么改*：区分 BizException（带 code+userMessage，可安全展示）与系统异常（只返「系统繁忙」+记日志，响应体不含 e 的任何内容）。用 `@ExceptionHandler` 分别匹配。

3. **把 Entity 直接当 DTO 序列化返前端** —— 错在：`return userRepository.findById(id)` 把整个 User 实体（含 password、salt）转 JSON 返给前端。

   *为什么*：实体对应表结构，常含敏感字段（密码、盐、内部标记）。直接序列化会把这些字段泄露出去，还可能因延迟加载（LazyInitializationException）或循环引用（关联对象互相引用）在序列化时炸。

   *怎么改*：定义专门的出站 VO/DTO，只含前端该看的字段，在转换层（converter/MapStruct）显式映射；用 `@JsonIgnore` 兜底隐藏敏感字段。

4. **校验写在 service 里而非边界 DTO** —— 错在：`if (dto.getName() == null || dto.getName().length() < 2) throw ...` 散落在各个 service 方法开头。

   *为什么*：格式类约束（必填、长度、正则）是「边界问题」，写在 service 会重复（多处调用同一 DTO 各写一遍）、且绕过了框架的声明式校验与统一错误结构，出错信息也不一致。

   *怎么改*：把格式约束放到入站 DTO 的 Jakarta 注解上（@NotNull/@Size/@Pattern），controller 用 @Validated 触发，advice 统一收集 fieldErrors 返回。

5. **分组校验用错导致约束不生效或误生效** —— 错在：DTO 上写了 `@NotNull(groups = Update.class) private Long id`，但 controller 用 `@Validated` 没指定分组，结果更新时 id 为 null 也没拦住。

   *为什么*：不指定分组时，只有「没标注任何 group」的约束会生效；标注了 `groups` 的约束在该场景被跳过。于是「更新必须带 id」形同虚设，脏数据进库。反过来指定了不该启用的分组也会误拦。

   *怎么改*：明确每个约束的分组；controller 方法用 `@Validated(Update.class)` 等指定当前用例；Insert 场景的 DTO 不要给 id 加约束。约束与用例一一对应，避免复制 DTO。

6. **自定义校验器里打全表查询导致性能崩** —— 错在：写了 `@UniqueUsername` 校验器，每次请求都对用户表做 `SELECT COUNT(*)` 查重，且没加索引。

   *为什么*：注册/保存接口本就高频，每次都触发一次全表扫描式查重，数据库压力随请求线性上升，高峰期直接拖垮整库。而且并发下还有竞态（查完到插入之间别人可能插入相同值）。

   *怎么改*：给被查字段加唯一索引，并把「查重」视为业务规则在 service 用「插入捕获唯一冲突 / 乐观锁」处理；自定义约束只做格式级校验，避免在校验器里做重 IO。

7. **事务边界放在 Controller 上** —— 错在：在 `@RestController` 方法上加 `@Transactional`，以为这样就能保证原子性。

   *为什么*：HTTP 层不该决定事务：controller 还要做参数解析、响应序列化，这些非业务操作也被包进事务，拉长事务持有连接的时间；而且异常在序列化阶段抛出时事务已提交/回滚行为难控。事务应属于业务用例，归属 service。

   *怎么改*：把 `@Transactional` 加在 service 的用例方法上，保持事务短小、只覆盖真正需要原子性的业务操作。controller 只调用 service。

8. **Service 间形成循环依赖** —— 错在：A service 构造器注入 B service，B service 又注入 A service，启动时报 `BeanCurrentlyInCreationException`。

   *为什么*：循环依赖破坏「依赖图无环」原则，Spring 虽然能解一部分（字段注入/setter），但会让初始化顺序脆弱、行为难推理，且常掩盖「职责划分不清」的设计问题（两个 service 其实该合并或抽公共逻辑）。

   *怎么改*：把共享逻辑抽到第三个 service 或 composable；若 A 真需 B，考虑让 B 只暴露接口、A 在方法内（而非构造器）获取。优先重构职责而非靠 Spring 的循环依赖兜底。

9. **用异常控制正常业务流程** —— 错在：`try { user = repo.findByUsername(x); } catch (NullPointerException e) { user = createDefault(); }`——拿 NPE 当「没找到」的分支。

   *为什么*：异常是为「意外」准备的，用它走正常分支会带来巨大性能开销（堆栈构建）、掩盖真实 bug（真 NPE 被吞）、且代码可读性极差。更糟的是后续真出问题会被这个 catch 静默吃掉。

   *怎么改*：用返回值/Optional 表达「可能不存在」：`user = repo.findByUsername(x); if (user == null) user = createDefault();`。只在真正意外时抛异常。

10. **错误码随手写字符串、前端硬编码文案** —— 错在：各处 `return ApiError("ERR_001", "用户名或密码错误")`，前端 `if (code === "ERR_001") show("用户名或密码错误")`。

   *为什么*：错误码散落字符串字面量，拼写错一个前端就匹配不到；文案写死在后端，多语言切换要改后端。错误码没有统一命名空间，时间一长重复、冲突、无人维护。

   *怎么改*：把错误码定义成枚举（如 `UserError.USER_NOT_FOUND`，带 code/httpStatus/message），前后端共享一份契约；前端按 code 映射本地化文案，后端只给 code。
