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
