# fs-ch11 · 工程骨架实战代码片段

> Spring Boot 3 + Jakarta 的最小可运行片段，覆盖分层、异常、校验三块。

### 分层调用：Controller → Service → Repository

```java
@RestController
@RequestMapping("/users")
public class UserController {
    private final UserService svc;          // 只注入 Service
    public UserController(UserService svc) { this.svc = svc; }
    @PostMapping
    public UserVO create(@Valid @RequestBody CreateUserDTO dto) {
        return svc.create(dto);             // 写库编排在 Service
    }
}
```

### 业务异常 + 错误码枚举

```java
public class BizException extends RuntimeException {
    private final ErrorCode code;
    public BizException(ErrorCode code) {
        super(code.userMessage()); this.code = code;
    }
    public ErrorCode getCode() { return code; }
}
public enum ErrorCode {
    USER_NOT_FOUND(40401, "用户不存在");
    final int http; final String msg;
    ErrorCode(int h, String m){ http=h; msg=m; }
    public String userMessage(){ return msg; }
}
```

### 统一异常处理 @ControllerAdvice

```java
@RestControllerAdvice
public class GlobalAdvice {
    @ExceptionHandler(BizException.class)
    public ApiError handleBiz(BizException e) {
        return new ApiError(e.getCode().http(), e.getCode().userMessage());
    }
    @ExceptionHandler(Exception.class)
    public ApiError handleSys(Exception e) {
        log.error("sys err", e);            // 系统异常只记日志
        return new ApiError(500, "系统繁忙"); // 不返堆栈
    }
}
```

### 入站 DTO + Jakarta 校验

```java
public class CreateUserDTO {
    @NotNull @Size(min = 2, max = 20)
    private String name;
    @Email
    private String email;
    // getter / setter
}
```

### 分组校验

```java
public interface Update {}        // 分组标记
public class UpdateUserDTO {
    @NotNull(groups = Update.class)
    private Long id;
    private String name;
}
// controller: public UserVO update(@Validated(Update.class) @RequestBody UpdateUserDTO dto)
```

### 出站 VO 转换（避免实体直出）

```java
public record UserVO(Long id, String name, String email) {}
public UserVO toVO(User u) {
    return new UserVO(u.getId(), u.getName(), u.getEmail()); // 不含 password
}
```

### 声明式事务边界

```java
@Service
public class UserService {
    @Transactional                      // 在 Service 用例方法上
    public UserVO create(CreateUserDTO dto) {
        User u = repo.save(toEntity(dto));
        eventPublisher.publish(...);    // 保存后发消息
        return toVO(u);
    }
}
```

### 自定义校验器只做格式级

```java
@Target({FIELD})
@Retention(RUNTIME)
@Constraint(validatedBy = PhoneValidator.class)
public @interface Phone {
    String message() default "手机号格式错误";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}
// PhoneValidator 只校验格式，不查库（查重放 Service）
```

## 三视角解析
### 🧑‍💻 程序员视角
Controller 只做「参数校验 + 调用 Service + 组装响应」，业务逻辑一律下沉到 Service——Controller 里写 SQL 是分层腐化的第一步。异常要分「业务异常」（可预期，带错误码）与「系统异常」（不可预期，记日志 + 500），用统一异常处理器转换，避免每个接口写一遍 `try/catch`。入站 DTO 必须加 `@Valid` 才生效，且校验注解只覆盖「格式」，业务规则（如「余额充足」）仍要在 Service 里判断。

### 🎓 博士生视角
分层的价值在于「依赖方向单一」：Controller → Service → Repository，反向依赖通过接口（依赖倒置）实现。这一结构让「业务逻辑可测试、基础设施可替换」。DTO/VO/Entity 的区分不是形式主义——Entity 映射数据库、DTO 承载入站契约、VO 承载出站视图，混用会把数据库结构泄漏到 API 契约里，导致「改表就要改前端」。

### 📚 考研者视角
后端面试高频：
1. **分层职责**：Controller、Service、Repository 各管什么，为什么不能跨层调用。
2. **DTO 与 Entity**：为什么不能直接把 Entity 返回给前端（敏感字段、循环引用、耦合）。
3. **统一异常**：`@ControllerAdvice` + 自定义异常 + 错误码设计。
4. **参数校验**：`@Valid` 与 `@Validated` 的区别、分组校验、自定义校验注解。

```text
04-snippets.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 分层调用：Controller → Service → Repository  (java)
    |
    v
  [02] 业务异常 + 错误码枚举  (java)
    |
    v
  [03] 统一异常处理 @ControllerAdvice  (java)
    |
    v
  [04] 入站 DTO + Jakarta 校验  (java)
    |
    v
  [05] 分组校验  (java)
    |
    v
  [06] 出站 VO 转换（避免实体直出）  (java)
    |
    v
  [07] 声明式事务边界  (java)
    |
    v
  [08] 自定义校验器只做格式级  (java)
    |
    v
  [END] 三视角解析收口
```
