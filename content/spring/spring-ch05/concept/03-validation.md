# 三、参数校验：Bean Validation 的元数据模型
## 1. JSR-303/380 的元数据模型：约束注解 + ConstraintValidator

Bean Validation 把校验规则表达为**注解（元数据）**贴在字段上（`@NotNull`/`@Size`/`@Min`），运行时由校验引擎通过**反射**读取这些注解并调用对应的 `ConstraintValidator` 执行。规则与代码解耦。

### 🧑‍💻 程序员视角
- 校验要**显式触发**：方法参数前加 `@Valid`（或 `@Validated`），否则注解只是一个「无声的标记」，不生效——这是最高频踩坑。
- 校验失败抛出 `MethodArgumentNotValidException`，在 `@ExceptionHandler` 里转成 400/422 的统一错误体返回，别让它冒泡成 500。
- 想收集**所有**违反项（而非遇到第一个就停），使用 `Validator` API 的 `validate()`，它天然收集全部约束违反。

### 🎓 博士生视角
- 元数据模型是「声明式约束」：注解本身不含逻辑，逻辑在 `ConstraintValidator<A, T>` 实现里，约束注解通过 `@Constraint(validatedBy=...)` 关联到实现，形成「标注 → 验证器」的注册表。
- 引擎的反射驱动：拿到对象后遍历字段/`getConstraintsForClass`，对每个带约束注解的字段调用对应验证器，并把 `ConstraintViolation` 收集进 `Set`——这正是「收集所有违反项而非首个失败」的实现基础。
- 设计动机：把「合法性断言」从业务代码里抽离成可复用、可组合、可国际化的声明，符合关注点分离与开闭原则。

### 📚 考研者视角
- 笔面标准问法：「Bean Validation 怎么工作的？」标准答：约束注解是元数据，`Validator` 通过反射读取并用 `ConstraintValidator` 执行，结果收集为 `ConstraintViolation` 集合。
- 易错：认为「加了 `@NotNull` 就自动校验」——**缺 `@Valid` 不触发**；也认为「校验只报第一个错」——实际 `validate()` 收集全部。
- 关联考点：`@Valid` 与 `@Validated` 区别（后者支持分组与 Spring 的 method-level 校验，前者是标准 JSR 注解）。
## 2. 分组校验与级联校验

分组校验（`groups`）让同一对象在不同场景用不同规则：例如新增时 `id` 为空、更新时 `id` 必填。级联校验（`@Valid` 嵌套）让对象里的子对象也被一并校验。

### 🧑‍💻 程序员视角
- 用法：`@NotNull(groups=Update.class)` 标注字段，`@Validated(Update.class)` 标在 Controller 方法上——**两边都要带组**，漏一边就不校验。
- 默认组（`Default`）与自定义组是独立的；不带组的约束只在 `Default` 下生效，方法不指定组时只跑默认组。
- 级联：字段是对象/集合时加 `@Valid`，校验会递归进子对象；否则只校验当前层，子对象里的 `@NotNull` 全部被跳过。

### 🎓 博士生视角
- 分组是「约束的可选标签集合」：校验引擎只执行**本次调用声明的组**所标注的约束，从而在同一 DTO 上复用多套规则。
- 组可声明继承（`interface Update extends Create {}`），实现「更新包含创建的全部约束」这类层级关系，避免重复标注。
- 级联校验本质是**约束树的深度优先遍历**：`@Valid` 是「进入子节点」的边，遍历过程把整棵对象图的违反项汇成同一个 `Set`。

### 📚 考研者视角
- 笔面标准问法：「怎么让同一个 DTO 在新增/更新用不同校验？」标准答：用 `groups` 分组 + 方法上 `@Validated(组)`。
- 易错：「只在字段上写 `groups` 却在方法上不声明组」→ 该约束永不执行，是分组校验「看起来没生效」的根因。
- 关联考点：`@Validated` 标注在类上做 method-level 校验（Service 层也能校验），这是它的额外能力。
## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 缺 @Valid 不生效；用 Validator.validate 收集全部违反；分组/级联两边都得标。 |
| 博士生 | 注解是元数据，引擎反射驱动 ConstraintValidator，级联=约束树遍历。 |
| 考研者 | 工作原理 + @Valid 触发条件 + 分组/级联是标准三问。 |
