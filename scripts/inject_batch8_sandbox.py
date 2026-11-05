# -*- coding: utf-8 -*-
"""批次八：给 spring 八章补 sandbox（Spring 学科首次接入交互玩法）。

与前几批同一套路：写进 content/_handmade/labs.json 的 chapters，
再由 gen_interactive.py 并入各章 interactive.json 与前端数据。

为什么是这八章
-------------
Spring 的坑大多被讲成「记住这个注解」，但每一章背后都有一笔能算的账：

  ch01  组件扫描要遍历整个类路径，每个类都要读注解元数据；懒加载只付用到的部分
  ch02  prototype 每次注入都新建一次（含初始化），singleton 只付一次
  ch03  CGLIB 按「被代理的类」生成子类，类多则元空间线性涨；JDK 代理按接口复用
  ch04  每个 starter 都带一串自动配置类，启动时要逐个评估 @Conditional
  ch05  响应体越大，序列化 CPU 与出带宽同时涨；gzip 用 CPU 换带宽
  ch06  N+1：一条主查询带出 N 条子查询，N=1000 就是 1001 次 RTT
  ch07  动态 SQL 的 K 个 <if> 组合出 2^K 条不同 SQL，执行计划缓存被撑爆
  ch08  Little 定律：连接需求 = QPS × 事务持有时间，事务里调 RPC 会放大它

八章共同点：**这些参数在真实系统里都可观测，配错了就是启动慢、连接打满、
元空间 OOM**——正好是沙盒最擅长的题材。

纪律（沿用前几批）
-----------------
1. checks 必须带规模下限。
2. 不锁「正确答案」，让预算判据自己淘汰错方案。
3. 默认值 = 真实事故配置（Spring 默认 + 新手写法）。
4. `if(c,a,b)` 急切求值 → 分支内除法保证除数非零常量。
5. fmt 只认 int / fix2 / pct；不支持科学计数法。
6. 判据阈值留 5% 以上余量。

写盘必须 indent=1 + newline="\\n"；且只替换本章 sandbox、保留 debug 等其它模块。
"""
import json
import os

LABS = os.path.join(os.path.dirname(__file__), "..", "content", "_handmade", "labs.json")


# ============================================================================
# spring/spring-ch01 · 两万个类全扫一遍，启动先花十秒
# ----------------------------------------------------------------------------
# 教学点：@ComponentScan 要遍历类路径下每个 .class，用 ASM 读注解元数据
# （约 20μs/类），命中的还要反射实例化 + 注入（约 500μs/个）。
# 大型单体两万个类 = 扫描 0.4 秒 + 初始化 10 秒。
# @Lazy 只实例化真正被用到的 10%，启动立刻回到 1 秒级。
# ============================================================================
spring_ch01 = {
    "kind": "sandbox",
    "title": "两万个类全扫一遍，启动先花十秒",
    "brief": (
        "`@ComponentScan` 启动时要把类路径下每个 `.class` 都打开、用 ASM 读一遍注解，"
        "命中的还要反射创建、注入依赖、跑初始化回调。"
        "两万个类的单体应用，光这一步就是十几秒——每次改代码重启都要等。"
        "把类数量与懒加载开关拖到真实规模，看这十几秒花在哪一半。"
    ),
    "params": [
        # 类路径下的类数（千个）
        {"key": "classesK", "label": "类路径类数（千）", "min": 1, "max": 60, "step": 1, "value": 20},
        # 是否懒加载
        {"key": "lazy", "label": "Bean 初始化", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["启动时全部实例化", "@Lazy 按需实例化"]},
    ],
    "metrics": [
        {"key": "classes", "label": "类路径类数", "expr": "classesK * 1000", "unit": "个", "fmt": "int"},
        # 扫描：每类约 20μs 读注解（无法省，全量遍历）
        {"key": "scanMs", "label": "注解扫描耗时", "expr": "classesK * 1000 * 20 / 1000", "unit": "ms", "fmt": "int"},
        # 实例化：每个 Bean 约 500μs（反射 + 注入 + 初始化回调）
        {"key": "eagerMs", "label": "全部实例化耗时", "expr": "classesK * 1000 * 500 / 1000", "unit": "ms", "fmt": "int"},
        # 懒加载：只实例化真正用到的 10%
        {"key": "lazyMs", "label": "按需实例化耗时", "expr": "classesK * 1000 * 500 / 1000 / 10", "unit": "ms", "fmt": "int"},
        # 当前方式的启动耗时
        {"key": "bootMs", "label": "启动耗时", "expr": "scanMs + if(lazy == 1, lazyMs, eagerMs)", "unit": "ms", "fmt": "int"},
        # 启动时创建的 Bean 数
        {"key": "beanCount", "label": "启动创建 Bean 数", "expr": "if(lazy == 1, classesK * 100, classesK * 1000)", "unit": "个", "fmt": "int"},
        # 常驻内存：每个 singleton Bean 约 2KB 元数据 + 实例
        {"key": "heapMB", "label": "容器常驻内存", "expr": "beanCount * 2 / 1024", "unit": "MB", "fmt": "int"},
    ],
    "checks": [
        # 下限：一万个类起，小项目怎么扫都快
        {"expr": "classes >= 10000", "label": "类路径 ≥1 万个类（大型单体/多模块工程的规模）"},
        # 痛点：全量实例化确实慢到影响开发
        {"expr": "eagerMs >= 5000", "label": "全量实例化 ≥5 秒（这就是每次重启都要等的原因）"},
        # 上限：启动压进 3 秒
        {"expr": "bootMs <= 3000", "label": "启动 ≤3 秒（可接受的热重启时间）"},
    ],
    "insight": (
        "启动时间可以拆成两段：**扫描**（读每个 class 的注解，约 20μs/类，躲不掉）"
        "和**初始化**（反射建对象、注入依赖、执行 `@PostConstruct`，约 500μs/个，"
        "是扫描的 25 倍）。两万个类的工程：扫描 0.4 秒，初始化 10 秒。"
        "所以优化顺序是先砍初始化："
        "① `@Lazy` / `spring.main.lazy-initialization=true`（只建真正被用到的）；"
        "② 缩小 `@ComponentScan` 范围（只扫业务包，别扫 `com.` 根）；"
        "③ 拆模块（`spring-boot-devtools` 的 restart classloader 只重载改动的类）。"
        "注意懒加载不是免费的：它把「启动时失败」变成「运行时第一次调用失败」，"
        "配置错误会推迟暴露——生产环境慎用全局懒加载，开发环境鼓励用。"
    ),
}


# ============================================================================
# spring/spring-ch02 · prototype 作用域到底新建了多少个对象
# ----------------------------------------------------------------------------
# 教学点：singleton 全容器只有一份，初始化只付一次；prototype 每注入一次
# 就新建一个（含全部初始化逻辑），所以「初始化里有 IO / 正则编译 / 加载配置」
# 的 bean 一旦设成 prototype，成本会乘以注入点数。
# ============================================================================
spring_ch02 = {
    "kind": "sandbox",
    "title": "prototype 作用域到底新建了多少个对象",
    "brief": (
        "`@Scope(\"prototype\")` 的语义是「每次要就给一个新的」——每次注入、每次 "
        "`getBean()` 都完整跑一遍构造和初始化。"
        "如果初始化里有加载配置、编译正则、建连接这类重活，二十万个注入点就是二十万次。"
        "而 singleton 全程只初始化一次。把注入点数与初始化成本拖到真实规模，"
        "看作用域这一行注解能放大出多少启动时间。"
    ),
    "params": [
        # 注入点/取用次数（千个）
        {"key": "pointsK", "label": "注入/取用次数（千）", "min": 10, "max": 500, "step": 10, "value": 200},
        # 单次初始化成本（ms）
        {"key": "initMs", "label": "单次初始化成本", "min": 1, "max": 20, "step": 1, "value": 5, "unit": "ms"},
        # 作用域：0 = singleton，1 = prototype
        {"key": "scope", "label": "Bean 作用域", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["singleton（全容器一份）", "prototype（每次新建）"]},
    ],
    "metrics": [
        {"key": "points", "label": "注入/取用次数", "expr": "pointsK * 1000", "unit": "次", "fmt": "int"},
        # 创建次数：singleton 1 次，prototype 每次
        {"key": "creations", "label": "对象创建次数", "expr": "if(scope == 1, pointsK * 1000, 1)", "unit": "次", "fmt": "int"},
        # 初始化总耗时
        {"key": "initTotalMs", "label": "初始化总耗时", "expr": "if(scope == 1, pointsK * 1000 * initMs, initMs)", "unit": "ms", "fmt": "int"},
        # 存活实例数（prototype 由调用方持有，直到被回收）
        {"key": "liveObjs", "label": "同时存活实例", "expr": "if(scope == 1, pointsK * 1000, 1)", "unit": "个", "fmt": "int"},
        # 堆占用：每个实例约 3KB
        {"key": "heapMB", "label": "实例堆占用", "expr": "liveObjs * 3 / 1024", "unit": "MB", "fmt": "int"},
        # 单次取用延迟
        {"key": "perCallMs", "label": "单次取用延迟", "expr": "if(scope == 1, initMs, 0)", "unit": "ms", "fmt": "int"},
        # 对照：若设成 prototype 会创建多少次（与当前选择无关，用于表达痛点）
        {"key": "naiveCreations", "label": "若 prototype 的创建次数", "expr": "pointsK * 1000", "unit": "次", "fmt": "int"},
    ],
    "checks": [
        # 下限：十万次取用，规模真实
        {"expr": "points >= 100000", "label": "注入/取用 ≥10 万次（真实业务的 Bean 取用规模）"},
        # 下限：初始化确实有成本
        {"expr": "initMs >= 3", "label": "单次初始化 ≥3ms（有 IO / 重计算的 Bean）"},
        # 痛点：prototype 在这个规模下确实慢
        {"expr": "naiveCreations >= 100000", "label": "若 prototype 要创建 ≥10 万次（这就是要解决的痛点）"},
        # 上限：初始化总耗时压进 1 秒
        {"expr": "initTotalMs <= 1000", "label": "初始化总耗时 ≤1 秒"},
        # 上限：堆占用压进 64MB
        {"expr": "heapMB <= 64", "label": "实例堆占用 ≤64MB"},
    ],
    "insight": (
        "`singleton` 和 `prototype` 的差别不是「线程安全与否」，是**创建次数**："
        "singleton 全容器一份、初始化一次；prototype 每注入一次就完整跑一遍构造 + `@PostConstruct`。"
        "二十万次取用 × 5ms 初始化 = 1000 秒，而 singleton 只要 5ms。"
        "所以判断标准很简单：**这个 Bean 的初始化里有 IO 或重计算吗？有就别设 prototype**。"
        "什么时候真的需要 prototype？——Bean 持有**每次使用都必须独立**的可变状态"
        "（如一次请求的上下文、非线程安全的 builder）。"
        "更好的替代是 `ObjectProvider<T>` 按需取、或在方法里 `new` 一个普通对象（不归容器管），"
        "把「需要新实例」的范围缩到真正需要的地方，而不是让整个 Bean 都变成 prototype。"
    ),
}


# ============================================================================
# spring/spring-ch03 · 五千个 Bean 全用 CGLIB，元空间先炸
# ----------------------------------------------------------------------------
# 教学点：CGLIB 为**每个被代理的类**生成一个子类，字节码常驻 Metaspace；
# JDK 动态代理为**每个接口**生成一个实现类，接口通常远少于实现类。
# 五千个类各生成一个代理子类，元空间多出几十 MB；接口代理只多几份。
# ============================================================================
spring_ch03 = {
    "kind": "sandbox",
    "title": "五千个 Bean 全用 CGLIB，元空间先炸",
    "brief": (
        "Spring AOP 默认优先用 CGLIB——它给**每个被代理的类**生成一个子类，"
        "字节码常驻元空间，永远不回收。五千个类各生成一份，就是几十 MB 加上每个方法的拦截逻辑。"
        "JDK 动态代理按**接口**生成实现类，接口数通常只有几十个，元空间几乎不涨。"
        "把被代理类数与代理方式拖到真实工程规模，看元空间怎么被吃掉。"
    ),
    "params": [
        # 被代理的类数
        {"key": "classes", "label": "被代理类数", "min": 100, "max": 8000, "step": 100, "value": 5000},
        # 每类方法数（影响代理代码里的拦截方法数量）
        {"key": "methods", "label": "每类方法数", "min": 2, "max": 30, "step": 2, "value": 10},
        # 代理方式：0 = CGLIB 子类，1 = JDK 接口代理
        {"key": "mode", "label": "代理方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["CGLIB（按类）", "JDK 动态代理（按接口）"]},
    ],
    "metrics": [
        # CGLIB：每类一个子类（约 5KB）+ 每个方法一段拦截逻辑（约 0.3KB）
        {"key": "cglibKB", "label": "CGLIB 代理字节码", "expr": "classes * 5 + classes * methods * 0.3", "unit": "KB", "fmt": "int"},
        # JDK：按接口生成（假设全工程 40 个接口）
        {"key": "jdkKB", "label": "JDK 代理字节码", "expr": "40 * 6 + 40 * methods * 0.3", "unit": "KB", "fmt": "int"},
        # 当前方案
        {"key": "metaKB", "label": "当前代理字节码", "expr": "if(mode == 1, jdkKB, cglibKB)", "unit": "KB", "fmt": "int"},
        # 代理类个数
        {"key": "proxyClasses", "label": "生成的代理类数", "expr": "if(mode == 1, 40, classes)", "unit": "个", "fmt": "int"},
        # 元空间占用（MB）
        {"key": "metaMB", "label": "元空间占用", "expr": "metaKB / 1024", "unit": "MB", "fmt": "fix2"},
        # 每个代理调用多一次间接跳转：约 3ns
        {"key": "callNs", "label": "单次调用开销", "expr": "3", "unit": "ns", "fmt": "int"},
        # 启动时生成代理的耗时：每类约 1ms
        {"key": "genMs", "label": "生成代理耗时", "expr": "proxyClasses * 1", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        # 下限：一千个类起，类少了两种方式都无所谓
        {"expr": "classes >= 1000", "label": "被代理类 ≥1000 个（中大型工程的 Bean 量级）"},
        # 痛点：CGLIB 确实要吃掉几十 MB 元空间
        {"expr": "cglibKB >= 15000", "label": "CGLIB 代理 ≥15MB 字节码（这就是元空间压力的来源）"},
        # 上限：当前方式压进 8MB
        {"expr": "metaMB <= 8", "label": "当前代理 ≤8MB（元空间预算内）"},
        # 上限：代理类数量不能太多（每个类都要占 metaspace 的 Class 结构）
        {"expr": "proxyClasses <= 100", "label": "代理类 ≤100 个（按接口复用，不是按实现类）"},
    ],
    "insight": (
        "CGLIB 的代理是**继承**：给每个被代理的类生成一个子类，覆写所有非 final 方法。"
        "所以它的数量级跟「被代理的类数」走——五千个 `@Service` 就是五千个代理类，"
        "每个 5KB 起，加上方法拦截逻辑，元空间几十 MB，而且**永不回收**（Class 卸载条件极苛刻）。"
        "JDK 动态代理是**实现接口**：一个接口一个代理类，全工程四十个接口就只有四十份，"
        "跟实现类数量无关。"
        "Spring Boot 2.x 起默认 `proxyTargetClass=true`（全用 CGLIB），"
        "好处是不要求接口、能代理包级类；代价就是上面这笔元空间账。"
        "对策：① `spring.aop.proxy-target-class=false` 让有接口的走 JDK 代理；"
        "② 只给真正需要横切的 Bean 加切点（别用 `execution(* com..*.*(..))` 一把梭）；"
        "③ 元空间要给够（`-XX:MaxMetaspaceSize`），否则热部署时会 OOM。"
    ),
}


# ============================================================================
# spring/spring-ch04 · 引一个 starter，带进来一百个自动配置类
# ----------------------------------------------------------------------------
# 教学点：每个 starter 通过 spring.factories / AutoConfiguration.imports 带进
# 一批自动配置类，启动时 Spring 要逐个评估 @Conditional（读注解 + 检查类路径
# + 检查已有 Bean），每类约 2.5ms。引 50 个 starter 就是上千个类、2.5 秒。
# ============================================================================
spring_ch04 = {
    "kind": "sandbox",
    "title": "引一个 starter，带进来一百个自动配置类",
    "brief": (
        "`spring-boot-starter-*` 的便利来自自动配置：每个 starter 都登记了一批配置类，"
        "启动时 Spring 要逐个评估 `@ConditionalOnClass`、`@ConditionalOnMissingBean` 这些条件。"
        "每个类约 2.5ms（读注解 + 类路径检查 + 容器查询），五十个 starter 就是上千个类、两三秒。"
        "把 starter 数与每个带来的配置类数拖到真实工程规模，"
        "看「随手加个依赖」的代价有多大。"
    ),
    "params": [
        # 引入的 starter 数
        {"key": "deps", "label": "starter 数量", "min": 10, "max": 100, "step": 5, "value": 50},
        # 每个 starter 带进的自动配置类数
        {"key": "autoPer", "label": "每 starter 配置类数", "min": 5, "max": 30, "step": 5, "value": 20},
        # 策略：0 = 全量引入，1 = 按需裁剪（排除不需要的自动配置）
        {"key": "mode", "label": "依赖策略", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["全量引入", "按需裁剪 / 排除"]},
    ],
    "metrics": [
        # 全量引入的自动配置类数
        {"key": "naiveAuto", "label": "全量自动配置类数", "expr": "deps * autoPer", "unit": "个", "fmt": "int"},
        # 裁剪后：只留 1/10
        {"key": "trimmedAuto", "label": "裁剪后配置类数", "expr": "deps * autoPer / 10", "unit": "个", "fmt": "int"},
        # 当前策略
        {"key": "autoClasses", "label": "当前配置类数", "expr": "if(mode == 1, trimmedAuto, naiveAuto)", "unit": "个", "fmt": "int"},
        # 每个配置类约 2.5ms 条件评估
        {"key": "startupMs", "label": "条件评估耗时", "expr": "autoClasses * 2500 / 1000", "unit": "ms", "fmt": "int"},
        # 传递依赖数（每个 starter 平均带 3 个）
        {"key": "transitiveDeps", "label": "传递依赖数", "expr": "deps * 3", "unit": "个", "fmt": "int"},
        # 每个配置类的元数据常驻（约 1KB）
        {"key": "metaMB", "label": "配置类元数据", "expr": "autoClasses / 1024", "unit": "MB", "fmt": "fix2"},
    ],
    "checks": [
        # 下限：30 个 starter 起，小项目无所谓
        {"expr": "deps >= 30", "label": "starter ≥30 个（中大型工程的真实依赖量）"},
        {"expr": "autoPer >= 10", "label": "每 starter ≥10 个配置类"},
        # 痛点：全量引入确实过千
        {"expr": "naiveAuto >= 400", "label": "全量自动配置 ≥400 个类（这就是启动慢的隐性成本）"},
        # 上限：当前策略压进 300 个
        {"expr": "autoClasses <= 300", "label": "当前配置类 ≤300（条件评估控制在 1 秒内）"},
        # 上限：启动耗时压进 1.5 秒
        {"expr": "startupMs <= 1500", "label": "条件评估 ≤1.5 秒"},
    ],
    "insight": (
        "自动配置的本质是「**条件装配的候选池**」：每个 starter 把自己的配置类登记到 "
        "`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`，"
        "启动时 Spring 把它们全读进来，再逐个跑 `@Conditional`——"
        "条件不满足就跳过，但**评估本身要花钱**（读注解、查类路径、查容器）。"
        "五十个 starter × 二十个配置类 = 一千个候选，2.5 秒起步，还带来一百多个传递依赖。"
        "所以「引一个 starter 试试」不是零成本："
        "① 用 `spring-boot-starter-web` 而不是挨个引 spring-webmvc/jackson/tomcat；"
        "② 用 `@SpringBootApplication(exclude = {...})` 或 "
        "`spring.autoconfigure.exclude` 排掉用不到的（如数据源、安全）；"
        "③ 用 `--debug` 或 `/actuator/conditions` 看「哪些配置类被评估、为什么没生效」——"
        "这是排查「Bean 没装上」的第一现场。"
    ),
}


# ============================================================================
# spring/spring-ch05 · 一万 QPS 的接口，响应体大一点就顶不住
# ----------------------------------------------------------------------------
# 教学点：吞吐 = QPS × 响应体大小。一万 QPS × 200KB = 2GB/s，
# 序列化按每核 100MB/s 算要 20 个核；gzip 把体积压到 1/5，CPU 却只多一倍，
# 于是核数掉到 4 个——这是「用 CPU 换带宽」的经典权衡。
# ============================================================================
spring_ch05 = {
    "kind": "sandbox",
    "title": "一万 QPS 的接口，响应体大一点就顶不住",
    "brief": (
        "接口的吞吐不是「QPS 多少」，而是 **QPS × 响应体大小**："
        "一万 QPS 返回 200KB，就是每秒 2GB 出流量，"
        "按每核 100MB/s 的序列化速度，光 Jackson 就要 20 个核。"
        "打开 gzip 把体积压到五分之一，CPU 只多一倍，核数立刻掉到四个。"
        "把 QPS、响应体大小与压缩开关拖到真实场景，看带宽和 CPU 谁先成为瓶颈。"
    ),
    "params": [
        # QPS
        {"key": "rps", "label": "QPS", "min": 1000, "max": 50000, "step": 1000, "value": 10000},
        # 单响应体大小（KB）
        {"key": "bodyKB", "label": "响应体大小", "min": 10, "max": 500, "step": 10, "value": 200, "unit": "KB"},
        # 是否 gzip
        {"key": "gzip", "label": "响应压缩", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["不压缩", "gzip（压缩比约 5:1）"]},
    ],
    "metrics": [
        # 出带宽（MB/s）
        {"key": "bwMBs", "label": "出带宽", "expr": "rps * bodyKB / 1024", "unit": "MB/s", "fmt": "int"},
        # 压缩后的带宽
        {"key": "gzMBs", "label": "压缩后带宽", "expr": "rps * bodyKB / 1024 / 5", "unit": "MB/s", "fmt": "int"},
        # 当前实际带宽
        {"key": "chosenMBs", "label": "当前出带宽", "expr": "if(gzip == 1, gzMBs, bwMBs)", "unit": "MB/s", "fmt": "int"},
        # 折算成 Mbps（千兆网卡 125MB/s，万兆 1250MB/s）
        {"key": "netMbps", "label": "折算网络带宽", "expr": "chosenMBs * 8", "unit": "Mbps", "fmt": "int"},
        # 序列化所需核数：每核 100MB/s，压缩再乘 2
        {"key": "cores", "label": "序列化所需核数", "expr": "chosenMBs / 100 * if(gzip == 1, 2, 1)", "unit": "核", "fmt": "fix2"},
        # 千兆网卡是否够（125MB/s）
        {"key": "nicMBs", "label": "单张千兆网卡能力", "expr": "125", "unit": "MB/s", "fmt": "int"},
    ],
    "checks": [
        # 下限：QPS 五千起，规模真实
        {"expr": "rps >= 5000", "label": "QPS ≥5000（真实线上接口量级）"},
        # 痛点：不压缩时的吞吐确实压不住
        {"expr": "bwMBs >= 500", "label": "未压缩出带宽 ≥500MB/s（这就是要解决的痛点）"},
        # 上限：序列化核数压进 8 核
        {"expr": "cores <= 10", "label": "序列化 ≤10 核（单机还有余量给业务逻辑）"},
        # 上限：带宽要能被网卡吃下（千兆 125MB/s × 4 网卡 = 500MB/s）
        {"expr": "chosenMBs <= 500", "label": "出带宽 ≤500MB/s（四张千兆网卡的上限）"},
    ],
    "insight": (
        "接口优化的第一性原理是 **`吞吐 = QPS × 单响应字节`**，两个因子都要看。"
        "一万 QPS × 200KB = 2GB/s：按每核 100MB/s 的序列化速度要 20 个核，"
        "按千兆网卡 125MB/s 要 16 张网卡——两个维度同时爆。"
        "三条对策，按性价比排序："
        "① **砍字段**（最有效）：DTO 只返回前端要的，别把整个实体（含大字段、关联对象）扔出去，"
        "`@JsonIgnore` / `@JsonView` / 专用 VO；"
        "② **gzip**：JSON 文本压缩比通常 5:1，用约 2 倍 CPU 换 5 倍带宽；"
        "③ **分页 + 缓存**：别让同一个重查询每秒跑一万次，加 Redis / HTTP 缓存。"
        "注意压缩不是万能的：已经压过的内容（图片、protobuf）再 gzip 只浪费 CPU；"
        "而且 gzip 有固定开销，小于 1KB 的响应压完反而更大（所以 Spring 的 "
        "`server.compression.min-response-size` 默认 2KB）。"
    ),
}


# ============================================================================
# spring/spring-ch06 · 一千条订单，为什么发了一千零一条 SQL
# ----------------------------------------------------------------------------
# 教学点：N+1 查询——一条主查询拿到 N 条记录，再为每条记录发一条子查询。
# N=1000 就是 1001 次网络往返，每次 1ms 就是 1 秒；改成批量 IN 只要 2 次。
# 这是 ORM/MyBatis 场景最常见的性能事故，也是最容易修的。
# ============================================================================
spring_ch06 = {
    "kind": "sandbox",
    "title": "一千条订单，为什么发了一千零一条 SQL",
    "brief": (
        "查订单列表时，每条订单还要查它的商品明细——循环里调一次 `selectByOrderId`，"
        "一千条订单就发了一千零一次 SQL。每次往返 1ms，光等数据库就是一秒。"
        "改成「先查主表，再用 `IN` 批量查子表」，两条 SQL 就够。"
        "把记录数与查询方式拖到真实业务规模，看这条 N+1 曲线怎么随数据量线性恶化。"
    ),
    "params": [
        # 主记录数
        {"key": "parents", "label": "主记录数", "min": 100, "max": 10000, "step": 100, "value": 1000},
        # 查询方式：0 = N+1 循环查，1 = 批量 IN
        {"key": "mode", "label": "查询方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["N+1（循环里查）", "批量 IN 查询"]},
    ],
    "metrics": [
        {"key": "rows", "label": "主记录数", "expr": "parents", "unit": "条", "fmt": "int"},
        # N+1：1 条主查询 + N 条子查询
        {"key": "nPlusOne", "label": "N+1 的 SQL 次数", "expr": "parents + 1", "unit": "次", "fmt": "int"},
        # 批量：2 条
        {"key": "batch", "label": "批量方案的 SQL 次数", "expr": "2", "unit": "次", "fmt": "int"},
        # 当前方案
        {"key": "sqls", "label": "当前 SQL 次数", "expr": "if(mode == 1, 2, parents + 1)", "unit": "次", "fmt": "int"},
        # 总往返耗时：每次 1ms
        {"key": "totalMs", "label": "数据库往返耗时", "expr": "sqls * 1", "unit": "ms", "fmt": "int"},
        # 连接占用时间（并发高时是致命项）
        {"key": "connHoldMs", "label": "单请求持有连接", "expr": "totalMs", "unit": "ms", "fmt": "int"},
        # 放到 100 并发下需要的连接数（Little 定律）
        {"key": "connNeed", "label": "100 并发所需连接", "expr": "totalMs * 100 / 1000", "unit": "个", "fmt": "int"},
    ],
    "checks": [
        # 下限：1000 条起，数据少时 N+1 也看不出来
        {"expr": "rows >= 1000", "label": "主记录 ≥1000 条（真实列表页/批量任务规模）"},
        # 痛点：N+1 确实上千次 SQL
        {"expr": "nPlusOne >= 1000", "label": "N+1 方案 ≥1000 次 SQL（这就是要解决的痛点）"},
        # 上限：当前方案 SQL 次数压进 10
        {"expr": "sqls <= 10", "label": "当前 SQL 次数 ≤10（批量一次拿完）"},
        # 上限：往返耗时压进 50ms
        {"expr": "totalMs <= 50", "label": "数据库往返 ≤50ms"},
    ],
    "insight": (
        "N+1 的公式就是它的名字：**1 次主查询 + N 次子查询**。"
        "代价不在数据库算得慢，而在**网络往返次数**——每次 1ms 的 RTT，"
        "一千条就是一秒，而且数据量越大越糟，是标准的线性恶化。"
        "修法有三档："
        "① **批量 IN**（`WHERE order_id IN (...)`）：1000 条分成几十个批次，SQL 次数从 1001 降到 2；"
        "② **JOIN 一次查完**：适合一对一/一对少，注意一对多会笛卡尔膨胀（1000 订单 × 10 明细 = 1 万行，"
        "要自己做去重聚合）；"
        "③ **MyBatis 的 `<collection>` + `fetchType=\"lazy\"` 或 `@BatchSize`**，"
        "本质也是帮你做批量 IN。"
        "检测手段：开 MyBatis 的 SQL 日志或 `p6spy`，一眼就能看到「同一条 SQL 刷了 1000 遍」；"
        "Spring Data JPA 用 `@EntityGraph` / `join fetch` 解决同类问题。"
        "另外注意 `connHoldMs` 那行：N+1 把连接持有时间也放大了 1000 倍，"
        "高并发下会先把连接池打满（见 spring-ch08 的 Little 定律）。"
    ),
}


# ============================================================================
# spring/spring-ch07 · 十个 <if> 标签，组合出 1024 条不同的 SQL
# ----------------------------------------------------------------------------
# 教学点：动态 SQL 的每个 <if> 都是可选条件，K 个就有 2^K 种 SQL 文本组合。
# 数据库的执行计划缓存按**SQL 文本**命中，所以最坏情况要缓存 2^K 条计划；
# K=16 是 65536 条、按每条 2KB 算就是 128MB，还伴随命中率暴跌。
# 拆成两条专用 SQL（按场景分流），组合数从 2^K 降到 2·2^(K/2)。
# ============================================================================
spring_ch07 = {
    "kind": "sandbox",
    "title": "十个 <if> 标签，组合出 1024 条不同的 SQL",
    "brief": (
        "动态 SQL 里每加一个 `<if test=\"...\">` 就多一种可选条件，"
        "K 个标签就有 2^K 种不同的 SQL 文本。执行计划缓存按文本命中，"
        "所以最坏要缓存 2^K 条计划——16 个标签就是 65536 条、一百多 MB，命中率还一路下滑。"
        "把条件数与组织方式拖到真实查询规模，看「一个万能查询」怎么把 plan cache 撑爆。"
    ),
    "params": [
        # <if> 条件数
        {"key": "ifCount", "label": "<if> 条件数", "min": 4, "max": 20, "step": 1, "value": 16},
        # 组织方式：0 = 一个万能 SQL，1 = 按场景拆成两条专用 SQL
        {"key": "mode", "label": "SQL 组织方式", "min": 0, "max": 1, "step": 1, "value": 0,
         "labels": ["一个万能动态 SQL", "按场景拆成专用 SQL"]},
    ],
    "metrics": [
        {"key": "ifs", "label": "条件数 K", "expr": "ifCount", "unit": "个", "fmt": "int"},
        # 万能 SQL：2^K 种组合
        {"key": "naivePlans", "label": "万能 SQL 的文本组合", "expr": "pow(2, ifCount)", "unit": "种", "fmt": "int"},
        # 拆分后：每个专用 SQL 覆盖一半条件
        {"key": "splitPlans", "label": "拆分后的组合", "expr": "pow(2, floor(ifCount / 2)) * 2", "unit": "种", "fmt": "int"},
        # 当前方案
        {"key": "plans", "label": "当前方案组合数", "expr": "if(mode == 1, splitPlans, naivePlans)", "unit": "种", "fmt": "int"},
        # 计划缓存占用：每条计划约 2KB
        {"key": "cacheMB", "label": "计划缓存占用", "expr": "plans * 2 / 1024", "unit": "MB", "fmt": "fix2"},
        # 硬解析次数（缓存未命中时）：假设请求随机命中各组合，缓存能装 5000 条
        {"key": "hitRate", "label": "计划缓存命中率", "expr": "if(plans <= 5000, 100, 5000 * 100 / plans)", "unit": "%", "fmt": "int"},
        # 每秒 1 万请求、每次硬解析 100μs：满命中也只占 1000ms/s，未命中率直接乘上去
        {"key": "parseMsPerSec", "label": "硬解析每秒耗 CPU", "expr": "(100 - if(plans <= 5000, 100, 5000 * 100 / plans)) * 10", "unit": "ms/s", "fmt": "int"},
    ],
    "checks": [
        # 下限：12 个条件起，条件少时组合数还能忍
        {"expr": "ifs >= 12", "label": "条件数 ≥12（真实后台列表页的筛选维度）"},
        # 痛点：万能 SQL 确实组合爆炸
        {"expr": "naivePlans >= 4096", "label": "万能 SQL ≥4096 种组合（这就是 plan cache 被撑爆的原因）"},
        # 上限：当前方案组合数压进 2000
        {"expr": "plans <= 2000", "label": "当前组合数 ≤2000（计划缓存装得下）"},
        # 上限：缓存占用压进 4MB
        {"expr": "cacheMB <= 4", "label": "计划缓存 ≤4MB"},
        # 上限：硬解析不能吃掉一个核以上
        {"expr": "parseMsPerSec <= 300", "label": "硬解析 ≤300ms/s CPU（留余量给真正执行 SQL）"},
    ],
    "insight": (
        "动态 SQL 的成本不是「拼接字符串」，而是**文本组合数**：K 个 `<if>` 就是 2^K 条不同 SQL。"
        "数据库（和 MyBatis 自己的 `localCacheScope`/执行计划缓存）都按 SQL 文本命中，"
        "16 个条件 = 65536 条计划 × 2KB = 128MB，还要加上每条都要软解析、"
        "优化器对每条都重算一遍执行计划。"
        "两个层面的对策："
        "① **拆 SQL**：按业务场景拆成「列表页查询」「导出查询」「后台检索」几条专用 SQL，"
        "每条只带自己需要的固定条件，组合数从 2^K 掉到 2·2^(K/2)；"
        "② **固定文本**：把可选条件改写成 `AND (col = #{v} OR #{v} IS NULL)`，"
        "SQL 文本恒定、永远只命中一条计划——代价是索引可能用不上（优化器对 `OR NULL` 的处理很保守），"
        "适合条件少、表小的场景。"
        "顺带一句：这也解释了为什么 `${}` 拼接（见 spring-ch06）比 `<if>` 更危险——"
        "它把**参数值**也变成 SQL 文本的一部分，组合数是参数取值数的乘积，且直接开 SQL 注入的口子。"
    ),
}


# ============================================================================
# spring/spring-ch08 · 事务里调一次 RPC，连接池就被打满了
# ----------------------------------------------------------------------------
# 教学点：Little 定律——并发连接数 = QPS × 平均持有时间。
# 事务里做一次 500ms 的远程调用，等于把连接持有时间从 5ms 拉到 505ms；
# 1000 QPS 下需要的连接从 5 个涨到 505 个，50 个的池瞬间排队。
# ============================================================================
spring_ch08 = {
    "kind": "sandbox",
    "title": "事务里调一次 RPC，连接池就被打满了",
    "brief": (
        "连接池该开多大？不是拍脑袋，是 Little 定律：**所需连接 = QPS × 平均持有时间**。"
        "一个事务如果只做本地 SQL，5ms 就还连接，1000 QPS 只要 5 个连接；"
        "但只要里面夹了一次 500ms 的远程调用，持有时间变成 505ms，"
        "同样 1000 QPS 就需要 505 个——50 个的池当场排队超时。"
        "把 QPS、RPC 耗时与池大小拖到真实负载，再决定这次调用该不该待在事务里。"
    ),
    "params": [
        # QPS
        {"key": "qps", "label": "QPS", "min": 100, "max": 5000, "step": 100, "value": 1000},
        # 事务里那次远程调用的耗时（ms）
        {"key": "rpcMs", "label": "远程调用耗时", "min": 100, "max": 500, "step": 50, "value": 500, "unit": "ms"},
        # 关键选择：这次 RPC 放在事务内还是移出去
        {"key": "inTx", "label": "RPC 的位置", "min": 0, "max": 1, "step": 1, "value": 1,
         "labels": ["在事务内（持锁期间调）", "移到事务外（先调再开事务）"]},
        # 连接池大小
        {"key": "pool", "label": "连接池大小", "min": 10, "max": 200, "step": 10, "value": 50},
    ],
    "metrics": [
        # 本地 SQL 部分固定 5ms
        {"key": "sqlMs", "label": "本地 SQL 耗时", "expr": "5", "unit": "ms", "fmt": "int"},
        # 当前实际持有时间
        {"key": "holdMs", "label": "事务持有连接时间", "expr": "5 + if(inTx == 1, rpcMs, 0)", "unit": "ms", "fmt": "int"},
        # 若 RPC 留在事务里会持有多久（与当前选择无关，用于表达痛点）
        {"key": "naiveHoldMs", "label": "RPC 留在事务内时持有", "expr": "5 + rpcMs", "unit": "ms", "fmt": "int"},
        # Little 定律：所需连接 = QPS × 持有时间(秒)
        {"key": "connNeed", "label": "所需连接数（Little 定律）", "expr": "qps * (5 + if(inTx == 1, rpcMs, 0)) / 1000", "unit": "个", "fmt": "int"},
        # 若 RPC 留在事务里会需要多少连接
        {"key": "naiveConn", "label": "RPC 留在事务内所需连接", "expr": "qps * (5 + rpcMs) / 1000", "unit": "个", "fmt": "int"},
        # 池能支撑的最大 QPS
        {"key": "poolTps", "label": "池能支撑的 TPS", "expr": "pool * 1000 / (5 + if(inTx == 1, rpcMs, 0))", "unit": "QPS", "fmt": "int"},
        # 池利用率
        {"key": "utilPct", "label": "连接池利用率", "expr": "qps * (5 + if(inTx == 1, rpcMs, 0)) * 100 / 1000 / pool", "unit": "%", "fmt": "int"},
        # 排队等待（超出池容量的部分按排队近似）
        {"key": "waitMs", "label": "平均排队等待", "expr": "if(qps * (5 + if(inTx == 1, rpcMs, 0)) / 1000 > pool, (qps * (5 + if(inTx == 1, rpcMs, 0)) / 1000 / pool - 1) * (5 + if(inTx == 1, rpcMs, 0)), 0)", "unit": "ms", "fmt": "int"},
    ],
    "checks": [
        # 下限：QPS 500 起，流量小随便怎么配
        {"expr": "qps >= 500", "label": "QPS ≥500（真实线上流量）"},
        # 场景前提：确实有一次不可忽略的远程调用
        {"expr": "rpcMs >= 100", "label": "远程调用 ≥100ms（真实的下游接口耗时）"},
        # 痛点：RPC 留在事务里时，连接需求确实超出常规池
        {"expr": "naiveConn >= 150", "label": "RPC 留在事务内需 ≥150 个连接（这就是连接池被打满的原因）"},
        # 上限：所需连接必须装得进池子
        {"expr": "connNeed <= pool", "label": "当前所需连接 ≤池大小（Little 定律不能破）"},
        # 上限：池利用率不超过 80%（留余量给突发）
        {"expr": "utilPct <= 80", "label": "池利用率 ≤80%（留突发余量）"},
        # 上限：不算排队
        {"expr": "waitMs <= 0", "label": "无排队等待"},
    ],
    "insight": (
        "连接池大小的唯一正确算法是 Little 定律：**`所需连接 = QPS × 平均持有时间`**。"
        "1000 QPS × 5ms = 5 个连接就够；一旦事务里夹了 500ms 的 RPC，"
        "持有时间变成 505ms，所需连接直接涨到 505 个——放大 100 倍。"
        "这就是「事务里不要做远程调用」的数学依据，不是风格建议："
        "① **RPC/HTTP 移出事务**（先查后算，最后开短事务写）；"
        "② **事务里不做文件上传、发消息、调第三方**（改成事务提交后发，用 `@TransactionalEventListener`）；"
        "③ 池大小按 `QPS × p99 持有时间 × 1.2` 配，别照抄「HikariCP 默认 10」；"
        "④ 长事务还会拖住 `undo log`/MVCC 快照，让别的查询变慢——这是连接之外的第二种伤害。"
        "反过来，池开太大也不是好事：连接数是数据库的并发上限，开 500 个只会把数据库压垮，"
        "正确做法是「按数据库能承受的并发倒推池大小」。"
    ),
}


MODULES = {
    "spring/spring-ch01": spring_ch01,
    "spring/spring-ch02": spring_ch02,
    "spring/spring-ch03": spring_ch03,
    "spring/spring-ch04": spring_ch04,
    "spring/spring-ch05": spring_ch05,
    "spring/spring-ch06": spring_ch06,
    "spring/spring-ch07": spring_ch07,
    "spring/spring-ch08": spring_ch08,
}


def main() -> int:
    """读取 labs.json → 写入 8 个 sandbox → 按仓库风格（indent=1/LF）落盘。"""
    with open(LABS, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.setdefault("chapters", {})
    existed = sum(1 for k in MODULES if k in chapters)
    for key, mod in MODULES.items():
        # 幂等 + 不吞同章其它玩法：只替换本章的 sandbox，保留 debug 等其它模块
        kept = [m for m in chapters.get(key, []) if m.get("kind") != "sandbox"]
        chapters[key] = [mod] + kept
        extra = f"（保留其它模块 {len(kept)} 个）" if kept else ""
        print(f"added {key:<22} ({len(mod['params'])} params / {len(mod['metrics'])} metrics / {len(mod['checks'])} checks){extra}")

    with open(LABS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"written {os.path.normpath(LABS)}  (共 {len(chapters)} 章有精修模块，本次覆盖 {len(MODULES)}，其中已存在 {existed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
