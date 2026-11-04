# -*- coding: utf-8 -*-
"""middleware 学科来源锚点重写（批次 M1，8 章 32 条）。

依据：逐章 grep concept/*.md 的真实 `##` 标题，按「文件序号.文件内小节序号」重编 §。
每条格式：`§x.y 小节标题 · 读什么`（分隔符为前后各一空格的中间点）。

本批除了编号错位，还清了三条「跑题」条目：
  mw-ch04#3 原讲「过期与淘汰」，属 mw-ch02 的内容，本章讲缓存设计 → 换成缓存一致性
  mw-ch01#4 原拿 Kafka 集合实现凑数，与本章编码切换无关      → 换成 skiplist 结构
  mw-ch07#3 原拿 Redis 落盘对比，与「存储端不丢」隔一层        → 换成副本/ISR
"""
import json
import os
import re

MANIFEST = "content/spring/_manifest.json"
CH_DIR = "content/spring"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)


def split_note(note: str) -> tuple[str, str]:
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
    """只改「## 本章 GitHub」小节内的 `| n |` 表格行（B 站表格同形，须框定范围）。"""
    path = os.path.join(CH_DIR, cid, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")

    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    if not row_idx:
        return False, "小节内无表格行"
    if len(row_idx) != len(notes):
        return False, f"表格 {len(row_idx)} 行、notes {len(notes)} 条，不匹配"

    for i, note in zip(row_idx, notes):
        m = RE_GH_ROW.match(lines[i])
        head, tail = split_note(note)
        lines[i] = (
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )

    out = "\n".join(lines)
    if out == s:
        return True, "已是同源"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    return True, f"表格 {len(row_idx)} 行已同步"


NOTES: dict[str, list[str]] = {
    # ---------------- spring-ch01 IoC 容器与依赖注入 ----------------
    "spring-ch01": [
        "§2.2 依赖解析：按类型与按名称（@Qualifier） · 看 `mall-security` 模块："
        "安全配置类与业务 Service 分属不同包，靠 `@Qualifier` 或字段名消歧；"
        "字段名恰好等于 Bean 名才能注入成功，改名即启动失败"
        "——这正是 §2.1「字段注入」最脆的一处，对比构造器注入要靠 `@Primary` 才不打架",

        "§2.1 构造器注入 vs Setter 注入 vs 字段注入 · 读 "
        "`spring-boot-project/spring-boot/src/main/java/org/springframework/boot/` 下的自动配置类："
        "框架自己全部用构造器注入，依赖写在 `final` 字段上"
        "——这是「不可变 + 可单测」的示范，不是风格偏好；"
        "配合 §4.1 三级缓存，也解释了为什么构造器注入的循环依赖救不了",

        "§3.2 @Bean 与 @Configuration（Java 配置 / 工厂方法） · 看 `yudao-framework/` 的 starter 划分："
        "每个 starter 自带 `@AutoConfiguration` 与 `AutoConfiguration.imports`，业务模块只需引依赖"
        "——这是「扫描范围由 starter 决定」的工程化答案；"
        "读时注意 `@Bean` 方法相互调用时 `@Configuration` 的 CGLIB 代理如何保证单例",

        "§4.1 单例循环依赖与三级缓存 · 看 `spring-boot-tutorials` 模块："
        "`@Scope(\"prototype\")` 注入到单例后只创建一次，样例里用 `ObjectProvider` 才能每次取新实例；"
        "同一个模块里另有构造器循环依赖的例子——它直接抛 `BeanCurrentlyInCreationException`，"
        "对应 §4.2「prototype 循环依赖为何必然失败」",
    ],
    # ---------------- spring-ch02 Bean 生命周期与作用域 ----------------
    "spring-ch02": [
        "§3.2 Aware 回调体系 · 看 `mall` 里实现 `ApplicationRunner` 的启动任务："
        "它比 `@PostConstruct` 更晚，适合「容器就绪后才执行」的预热逻辑；"
        "按时间轴排一遍 `@PostConstruct` → `InitializingBean.afterPropertiesSet` → "
        "`ApplicationRunner.run`，就对应 §1.2 初始化三种方式的顺序",

        "§1.1 完整生命周期阶段（中立陈述） · 读 "
        "`spring-boot/src/main/java/org/springframework/boot/SpringApplication.java` 的 `run` 方法："
        "`prepareContext` → `refreshContext` → `afterRefresh`，"
        "`BeanPostProcessor` 的介入点就藏在这三步之间；"
        "配合 §1.3 可运行示例，能亲眼看到每个回调的打印顺序",

        "§2.2 prototype 注入 singleton 的陷阱（中立陈述） · 看 `yudao-module-system` 对 framework 里默认 Bean 的替换："
        "靠 `@ConditionalOnMissingBean` 让业务方可以覆盖，这是 starter 设计的通用约定；"
        "注意「覆盖」只在单例阶段有效——prototype Bean 每次新建，条件注解不再参与后续实例的判定",

        "§4.2 @Configuration 的 CGLIB 代理保证单例 · 看 `spring-boot-tutorials` 里的构造器注入案例："
        "两个 Bean 互相构造器依赖会直接抛 `BeanCurrentlyInCreationException`，三级缓存救不了它；"
        "这正是 §4.1 三级缓存的天花板——它只对「字段/Setter 注入形成的环」有效",
    ],
    # ---------------- spring-ch03 AOP 与代理机制 ----------------
    "spring-ch03": [
        "§4.2 同类内部自调用导致代理失效 · 看 `mall-admin` 的 Service 实现："
        "同类方法内部互调不经过代理，`@Transactional`/`@Cacheable` 直接失效，"
        "解法是注入自身或拆到另一个 Bean；"
        "理解它要先读 §4.1「this 与 target 的语义区别」——`this` 是原始对象，`target` 才是被代理的实例",

        "§2.2 JDK 与 CGLIB 的适用边界 · 读 `spring-boot` 的 `AopAutoConfiguration`："
        "`proxyTargetClass` 决定用 CGLIB 还是 JDK 代理，而 CGLIB 无法代理 `final` 类/方法"
        "——这就是「注解失效」的框架级原因；"
        "对照 §1.1 JDK 动态代理的工作机制，就明白为什么「实现了接口」会改变默认代理方式",

        "§3.2 通知执行顺序 · 看 `yudao-framework/yudao-spring-boot-starter-*` 里的日志与权限切面："
        "用 `@Around` 包住方法、用 `@Order` 控制顺序，比散落的拦截器更好维护；"
        "读时注意多个切面套在同一个方法上时，`@Order` 小的在外层——"
        "这决定了权限校验能不能挡住日志切面里的参数打印",

        "§1.1 JDK 动态代理的工作机制 · 看 `spring-boot-tutorials` 的 AOP 示例："
        "目标类实现接口时默认走 JDK 代理，注入时必须按接口类型，否则 `ClassCastException`；"
        "配合 §1.2 `InvocationHandler` 与反射委派，就明白「代理对象不是目标对象的子类」这条推断",
    ],
    # ---------------- spring-ch04 自动配置与起步依赖 ----------------
    "spring-ch04": [
        "§1.1 一个注解，三个职责 · 看 `mall-admin` 的启动类："
        "它只加 `@SpringBootApplication` 一个注解，扫描范围就是启动类所在包"
        "——所以 Controller 必须放在子包里，放外面就「找不到 Bean」；"
        "这正是「`@ComponentScan` 默认基准包」那条隐含约定的实际后果",

        "§2.1 候选清单从哪来：SPI 机制的演进 · 读 "
        "`spring-boot-project/spring-boot-autoconfigure/src/main/resources/META-INF/spring/` 下的 "
        "`AutoConfiguration.imports`：2.7 起用它替代 `spring.factories`，条件装配类按顺序列出；"
        "配合 §2.3「顺序决定结果」，就明白为什么 `@AutoConfigureAfter` 不是可有可无的装饰",

        "§3.3 自定义 starter 的两模块结构 · 看 `yudao-framework` 的模块组织："
        "`starter` 只放依赖与自动配置类、具体实现在同级的 `-core` 模块，"
        "这是「依赖聚合与实现分离」的标准做法；"
        "读时对照 §3.1 `@ConfigurationProperties` 与 `@Value` 的取舍——前者才能给 starter 做类型化配置",

        "§2.2 条件装配：决定「装不装」的那组注解 · 看 `spring-boot-tutorials` 的条件装配示例："
        "一个开关决定 Bean 是否注册，比在代码里写 if 更符合「配置驱动」的设计；"
        "重点看 `@ConditionalOnProperty` 与 `@ConditionalOnMissingBean` 的差别："
        "前者读配置、后者看容器现状——这正是 §4.2「自动配置是有条件生效的默认值」的两种手段",
    ],
    # ---------------- spring-ch05 Web 层：REST 与校验 ----------------
    "spring-ch05": [
        "§4.1 @ControllerAdvice 全局异常处理与异常→状态码映射 · 看 `mall-common` 的 `CommonResult`："
        "`code/message/data` 三字段 + 静态工厂方法，配合 `@RestControllerAdvice` 把异常也转成同一结构，"
        "前端只需处理一种形状；这正对应 §1.2「状态码选择」那条——业务码放 body、HTTP 码表语义",

        "§2.2 内容协商与消息转换器链 · 读 `spring-boot` 的 `HttpMessageConvertersAutoConfiguration`："
        "`Content-Type` 决定选哪个转换器，选不到就报 415"
        "——这个错误码的根因在自动配置而非 Controller；"
        "读完再回 §2.1 三类参数绑定，就明白 `@RequestBody` 为什么不能用表单提交",

        "§3.2 分组校验与级联校验 · 看 `yudao-module-system` 的 DTO："
        "新增与修改用不同 group，`@Validated(AddGroup.class)` 才生效"
        "——不加 `@Valid` 的校验注解等于没写；"
        "配合 §3.1 JSR-303/380 的元数据模型，就能自己写一个 `ConstraintValidator` 而不用到处 if",

        "§2.1 三类参数绑定：`@RequestParam` / `@PathVariable` / `@RequestBody` · "
        "看 `spring-boot-tutorials` 的 REST 示例：路径段用 `@PathVariable`、查询串用 `@RequestParam`，"
        "混用会导致 404 而不是 400，排查时容易误判；"
        "这正是 §2.3「四种参数来源的绑定写法」要逐个跑一遍的原因",
    ],
    # ---------------- spring-ch06 MyBatis 基础 ----------------
    "spring-ch06": [
        "§1.1 半自动 ORM 的定位与 SqlSession / Mapper 动态代理 · 看 `mall-mbg` 生成的 `*Mapper.xml`："
        "`namespace` 必须等于 Mapper 接口全限定名、`id` 等于方法名，任一处写错就是 `BindingException`"
        "——这就是「动态代理靠约定把方法调用翻译成 SQL」的代价；"
        "配合 §1.2 与 JDBC/JPA 的取舍，就明白半自动意味着「映射要自己写」",

        "§4.1 主键回填：useGeneratedKeys 与 selectKey · 读 `spring-boot` 的 `MybatisAutoConfiguration`"
        "（在 MyBatis 官方 starter 里）：`SqlSessionFactory` 由 `DataSource` 构建，"
        "这也是「多数据源要手动配多个 Factory」的原因；"
        "理解这一层才能明白 `useGeneratedKeys` 的开关是配在 Factory 的全局配置上",

        "§2.1 #{} 与 ${} 的语义差异 · 看 `yudao-module-system` 的分页查询 XML："
        "所有用户输入走 `#{}`，只有排序字段用 `${}` 且必须白名单校验——这是防注入的底线；"
        "配合 §2.2 PreparedStatement 预编译原理，就明白 `#{}` 生成的是占位符而 `${}` 是字面拼接",

        "§3.2 驼峰映射与关联映射 · 看 `spring-boot-tutorials` 的 MyBatis 配置："
        "`map-underscore-to-camel-case=true` 才能把 `user_name` 映射到 `userName`，不开就是一堆 `null`；"
        "但这只解决同表映射，嵌套对象仍要 §3.1 的 `resultMap` 手写 `association`/`collection`",
    ],
    # ---------------- spring-ch07 MyBatis 进阶 ----------------
    "spring-ch07": [
        "§1.2 智能修剪：`<where>` / `<set>` / `<trim>` · 看 `mall-mbg` 的 `Example` 生成的 `<if>`/`<foreach>`："
        "条件越多 SQL 越不可控，复杂查询应手写 XML 而不是让代码生成器堆条件；"
        "读时盯住 `<where>` 怎么自动吞掉多余的 `AND`——这正是 §1.1 `<if>` 拼不出合法 SQL 时的补丁",

        "§3.1 一级缓存：SqlSession 级，Key 由四元组决定 · 读 `spring-boot` 的事务同步机制："
        "MyBatis 的一级缓存挂在 `SqlSession` 上，而 `SqlSession` 与事务绑定"
        "——所以「同一事务内改完再查仍是旧值」是缓存语义而非 bug；"
        "看清 Key 的四元组，就知道为什么「换个参数就查库」但「同一参数永远命中」",

        "§3.3 缓存陷阱实战：四类症状与定位口径 · 看 "
        "`yudao-framework/yudao-spring-boot-starter-mybatis` 的分页与数据权限插件："
        "拦截 `Executor.query` 改写 SQL，比在业务层手写 `limit` 更统一；"
        "但插件改写后缓存 Key 也随之变化——这是「加了分页插件后二级缓存命中率归零」的根因",

        "§2.2 注入利用链：从「拼进去」到「改语义」 · 看 `spring-boot-tutorials` 的 MyBatis 示例："
        "它给了 `${}` 被拼接后改变 SQL 结构的对照；"
        "理解这一点再看 §2.1「ParameterMapping + TypeHandler vs OGNL 插值」，"
        "就知道 `#{}` 的安全不是因为「转义了引号」，而是因为它走的是参数绑定而非文本替换",
    ],
    # ---------------- spring-ch08 事务管理与工程实践 ----------------
    "spring-ch08": [
        "§1.1 传播行为：7 种取值与嵌套回滚的真实语义 · 看 `mall` 的下单流程："
        "主流程用 `REQUIRED`、记流水用 `REQUIRES_NEW`，后者会挂起外层事务并占用第二个连接，"
        "嵌套深了会打满连接池；"
        "配合 §5.4 传播行为的四行对照，就能算出「同一请求最多占几个连接」",

        "§2.2 事务与 AOP 代理：JDK 动态代理 vs CGLIB · 读 `spring-boot` 的 `TransactionAutoConfiguration`："
        "`@EnableTransactionManagement` 加 AOP 代理，代理边界决定「哪些方法真的在事务里」"
        "——自调用不生效就出在这；"
        "这正是 §2.1 八类失效场景里最常见的一类，修法见 §5.2 三种",

        "§4.2 多数据源与分布式事务：2PC/XA、TCC、Saga、本地消息表、Seata AT · "
        "看 `yudao-framework` 的多数据源配置：每个 `DataSource` 要配独立的事务管理器，"
        "`@Transactional` 必须指定 `transactionManager`，否则只对默认库生效；"
        "这也说明「跨库」在单体里就已经不可原子，分布式事务方案是在补这个缺口",

        "§1.2 隔离级别、readOnly、timeout 与回滚规则 · 看 `spring-boot-tutorials` 的事务示例："
        "默认只回滚 `RuntimeException`，受检异常必须显式 `rollbackFor = Exception.class`，样例里有能复现的对照；"
        "读时一并看 `readOnly=true` 的收益——它不只是提示，某些驱动会因此跳过脏检查",
    ],
}


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        nl = "\r\n" if b"\r\n" in fb.read() else "\n"
    data = json.load(open(MANIFEST, encoding="utf-8"))

    done = 0
    changed = False
    for ch in data.get("chapters", []):
        cid = ch.get("id")
        if cid not in NOTES:
            continue
        new = NOTES[cid]
        res = ch.setdefault("resources", {})
        old = res.get("github_notes", [])
        if len(old) != len(new):
            print(f"!! {cid} 原 {len(old)} 条、新 {len(new)} 条，不匹配，跳过")
            continue
        if old != new:
            res["github_notes"] = new
            changed = True
        done += 1
        ok, msg = rewrite_goals_table(cid, new)
        print(f"{'OK ' if ok else '!! '}{cid}: notes {len(new)} 条｜{msg}")

    if changed:
        with open(MANIFEST, "w", encoding="utf-8", newline=nl) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"manifest 已写盘（{done} 章）")
    else:
        print(f"manifest 已是目标状态（{done} 章），未写盘")


if __name__ == "__main__":
    main()
