# -*- coding: utf-8 -*-
"""来源颗粒度 · spring 8 章。

四个仓库的角色分工：
  spring-projects/spring-boot —— 框架本体，看「机制的真实实现」
  macrozheng/mall             —— 单模块拆分的业务工程，看「配置怎么写」
  YunaiV/ruoyi-vue-pro        —— 多模块脚手架，看「starter 怎么封」
  eugenp/tutorials            —— 最小样例，用来对照自己的写法
"""
import sys

from _route_granularity import apply

BOOT = 'spring-projects/spring-boot'
MALL = 'macrozheng/mall'
RUOYI = 'YunaiV/ruoyi-vue-pro'
TUT = 'eugenp/tutorials'

DATA = {
    'spring-ch01': {
        BOOT: ('§1.3', '讲「构造器注入 vs 字段注入」时读 `spring-boot-project/spring-boot/src/main/java/org/springframework/boot/` 下的自动配置类：框架自己全部用构造器注入，依赖写在 `final` 字段上——这是「不可变 + 可单测」的示范，不是风格偏好'),
        MALL: ('§2.1', '讲「同类型多 Bean 如何选」时看 `mall-security` 模块：安全配置类与业务 Service 分属不同包，靠 `@Qualifier` 或字段名消歧；字段名恰好等于 Bean 名才能注入成功，改名即启动失败'),
        RUOYI: ('§3.1', '讲「分包与组件扫描」时看 `yudao-framework/` 的 starter 划分：每个 starter 自带 `@AutoConfiguration` 与 `AutoConfiguration.imports`，业务模块只需引依赖——这是「扫描范围由 starter 决定」的工程化答案'),
        TUT: ('§4.1', '讲「Bean 作用域」时看 `spring-boot-tutorials` 模块：`@Scope("prototype")` 注入到单例后只创建一次，样例里用 `ObjectProvider` 才能每次取新实例'),
    },
    'spring-ch02': {
        BOOT: ('§2.2', '讲「Bean 生命周期」时读 `spring-boot/src/main/java/org/springframework/boot/SpringApplication.java` 的 `run` 方法：`prepareContext` → `refreshContext` → `afterRefresh`，`BeanPostProcessor` 的介入点就藏在这三步之间'),
        MALL: ('§1.3', '讲「Aware 回调与初始化顺序」时看 `mall` 里实现 `ApplicationRunner` 的启动任务：它比 `@PostConstruct` 更晚，适合「容器就绪后才执行」的预热逻辑'),
        RUOYI: ('§3.2', '讲「多模块下的 Bean 覆盖」时看 `yudao-module-system` 对 framework 里默认 Bean 的替换：靠 `@ConditionalOnMissingBean` 让业务方可以覆盖，这是 starter 设计的通用约定'),
        TUT: ('§4.2', '讲「循环依赖」时看 `spring-boot-tutorials` 里的构造器注入案例：两个 Bean 互相构造器依赖会直接抛 `BeanCurrentlyInCreationException`，三级缓存救不了它'),
    },
    'spring-ch03': {
        BOOT: ('§1.2', '讲「AOP 的代理边界」时读 `spring-boot` 的 `@ConditionalOnMissingBean` 与 `AopAutoConfiguration`：`proxyTargetClass` 决定用 CGLIB 还是 JDK 代理，而 CGLIB 无法代理 `final` 类/方法——这就是「注解失效」的框架级原因'),
        MALL: ('§2.1', '讲「自调用导致通知失效」时看 `mall-admin` 的 Service 实现：同类方法内部互调不经过代理，`@Transactional`/`@Cacheable` 直接失效，解法是注入自身或拆到另一个 Bean'),
        RUOYI: ('§3.2', '讲「自定义切面」时看 `yudao-framework/yudao-spring-boot-starter-*` 里的日志与权限切面：用 `@Around` 包住方法、用 `@Order` 控制顺序，比散落的拦截器更好维护'),
        TUT: ('§4.1', '讲「JDK 动态代理 vs CGLIB」时看 `spring-boot-tutorials` 的 AOP 示例：目标类实现接口时默认走 JDK 代理，注入时必须按接口类型，否则 `ClassCastException`'),
    },
    'spring-ch04': {
        BOOT: ('§3.1', '讲「自动配置的加载方式」时读 `spring-boot-project/spring-boot-autoconfigure/src/main/resources/META-INF/spring/` 下的 `AutoConfiguration.imports`：2.7 起用它替代 `spring.factories`，条件装配类按顺序列出'),
        MALL: ('§1.2', '讲「`@SpringBootApplication` 的三合一」时看 `mall-admin` 的启动类：它只加这一个注解，扫描范围就是启动类所在包——所以 Controller 必须放在子包里，放外面就「找不到 Bean」'),
        RUOYI: ('§4.1', '讲「起步依赖怎么封」时看 `yudao-framework` 的模块组织：`starter` 只放依赖与自动配置类、具体实现在同级的 `-core` 模块，这是「依赖聚合与实现分离」的标准做法'),
        TUT: ('§2.2', '讲「`@ConditionalOnProperty`」时看 `spring-boot-tutorials` 的条件装配示例：一个开关决定 Bean 是否注册，比在代码里写 if 更符合「配置驱动」的设计'),
    },
    'spring-ch05': {
        BOOT: ('§2.1', '讲「参数绑定与消息转换」时读 `spring-boot` 的 `HttpMessageConvertersAutoConfiguration`：`Content-Type` 决定选哪个转换器，选不到就报 415——这个错误码的根因在自动配置而非 Controller'),
        MALL: ('§1.3', '讲「统一返回体」时看 `mall-common` 的 `CommonResult`：`code/message/data` 三字段 + 静态工厂方法，配合 `@RestControllerAdvice` 把异常也转成同一结构，前端只需处理一种形状'),
        RUOYI: ('§3.2', '讲「校验分组」时看 `yudao-module-system` 的 DTO：新增与修改用不同 group，`@Validated(AddGroup.class)` 才生效——不加 `@Valid` 的校验注解等于没写'),
        TUT: ('§4.1', '讲「`@PathVariable` 与 `@RequestParam`」时看 `spring-boot-tutorials` 的 REST 示例：路径段用前者、查询串用后者，混用会导致 404 而不是 400，排查时容易误判'),
    },
    'spring-ch06': {
        BOOT: ('§1.1', '讲「MyBatis 与 Spring 的接缝」时读 `spring-boot` 的 `MybatisAutoConfiguration`（在 MyBatis 官方 starter 里）：`SqlSessionFactory` 由 `DataSource` 构建，这也是「多数据源要手动配多个 Factory」的原因'),
        MALL: ('§2.1', '讲「Mapper 与 XML 的对应」时看 `mall-mbg` 生成的 `*Mapper.xml`：`namespace` 必须等于 Mapper 接口全限定名、`id` 等于方法名，任一处写错就是 `BindingException`'),
        RUOYI: ('§3.1', '讲「`#{}` 与 `${}`」时看 `yudao-module-system` 的分页查询 XML：所有用户输入走 `#{}`，只有排序字段用 `${}` 且必须白名单校验——这是防注入的底线'),
        TUT: ('§4.2', '讲「驼峰映射」时看 `spring-boot-tutorials` 的 MyBatis 配置：`map-underscore-to-camel-case=true` 才能把 `user_name` 映射到 `userName`，不开就是一堆 `null`'),
    },
    'spring-ch07': {
        BOOT: ('§2.2', '讲「一级/二级缓存」时读 `spring-boot` 的事务同步机制：MyBatis 的一级缓存挂在 `SqlSession` 上，而 `SqlSession` 与事务绑定——所以「同一事务内改完再查仍是旧值」是缓存语义而非 bug'),
        MALL: ('§1.2', '讲「动态 SQL」时看 `mall-mbg` 的 `Example` 生成的 `<if>`/`<foreach>`：条件越多 SQL 越不可控，复杂查询应手写 XML 而不是让代码生成器堆条件'),
        RUOYI: ('§3.3', '讲「插件机制」时看 `yudao-framework/yudao-spring-boot-starter-mybatis` 的分页与数据权限插件：拦截 `Executor.query` 改写 SQL，比在业务层手写 `limit` 更统一'),
        TUT: ('§4.1', '讲「resultMap 关联查询」时看 `spring-boot-tutorials` 的 MyBatis 示例：`association`（一对一）与 `collection`（一对多）的嵌套映射，配 `fetchType="lazy"` 可延迟加载'),
    },
    'spring-ch08': {
        BOOT: ('§1.1', '讲「声明式事务的实现」时读 `spring-boot` 的 `TransactionAutoConfiguration`：`@EnableTransactionManagement` 加 AOP 代理，代理边界决定「哪些方法真的在事务里」——自调用不生效就出在这'),
        MALL: ('§3.1', '讲「传播行为」时看 `mall` 的下单流程：主流程用 `REQUIRED`、记流水用 `REQUIRES_NEW`，后者会挂起外层事务并占用第二个连接，嵌套深了会打满连接池'),
        RUOYI: ('§2.2', '讲「多数据源事务」时看 `yudao-framework` 的多数据源配置：每个 `DataSource` 要配独立的事务管理器，`@Transactional` 必须指定 `transactionManager`，否则只对默认库生效'),
        TUT: ('§4.3', '讲「`rollbackFor`」时看 `spring-boot-tutorials` 的事务示例：默认只回滚 `RuntimeException`，受检异常必须显式 `rollbackFor = Exception.class`，样例里有能复现的对照'),
    },
}

if __name__ == '__main__':
    sys.exit(apply('spring', DATA))
