# -*- coding: utf-8 -*-
"""来源颗粒度 · java 9 章：把「全章 + 仓库简介」升级为章节级读法。

四个仓库的角色分工固定：
  Snailclimb/JavaGuide   —— 索引型文档库，用来「校准概念口径」
  macrozheng/mall        —— 真实业务工程，用来「看概念在工程里的落点」
  doocs/advanced-java    —— 面试向深挖，用来「看这个点会被追问到多深」
  eugenp/tutorials       —— 最小可运行样例，用来「对照自己的实现」
"""
import sys

from _route_granularity import apply

GUI = 'Snailclimb/JavaGuide'
MALL = 'macrozheng/mall'
ADV = 'doocs/advanced-java'
TUT = 'eugenp/tutorials'

DATA = {
    'java-ch01': {
        GUI: ('§2.1', '讲「八种基本类型的固定位宽」时读 `docs/java/basis/` 下的基本类型问答：它把 `byte` 恒为有符号、`char` 是 16 位无符号 UTF-16 码元这两条一次讲透，正好解释「Java 没有无符号整型」为什么会让 `byte b = 200` 编译失败'),
        MALL: ('§1.4', '讲「classpath 与包」时看 `mall-common` 模块的 `com.macro.mall.common` 包结构：一个被其余模块依赖的公共包必须只放「无业务状态」的工具与统一返回体，这比背 classpath 定义更能说明「包边界 = 依赖方向」'),
        ADV: ('§1.3', '讲「JIT 让 Java 越跑越快」时对照 `docs/high-concurrency/` 里的 JVM 系列文章：它解释了「解释执行 → C1 → C2」的分层编译与逃逸分析，回读本章四步流程就能说清「为什么预热前后同一段循环耗时差一个数量级」'),
        TUT: ('§3.1', '讲「if 与布尔条件」时看 `core-java` 模块的语法示例：Java 的 `if` 只接受 `boolean`，不存在 C 的「非零即真」，这份仓库用最小样例把这条差异固定下来，可直接拿来对照自己的写法'),
    },
    'java-ch02': {
        GUI: ('§4.1', '讲「equals 与 hashCode 契约」时读 `docs/java/basis/` 的对象基础问答：等价关系必须自反/对称/传递，哈希值必须与 equals 一致——它用 `HashMap` 查不到键的现场说明违反契约的后果'),
        MALL: ('§1.1', '讲「对象内存布局」时看 `mall-common` 里的 `CommonResult`：一个只有 `code/message/data` 三个字段的返回体，字段顺序与类型决定对象头之后的内存排布，也是「为什么 DTO 要小而扁平」的现成样本'),
        ADV: ('§4.2', '讲「哈希分布」时对照 `docs/high-concurrency/` 的 HashMap 系列：它把「扰动函数 + 扩容 rehash」讲到面试深度，能解释为什么自定义 key 的 `hashCode` 分布不均会让链表变长'),
        TUT: ('§3.2', '讲「构造器与 this」时看 `core-java` 的构造器重载示例：`this(...)` 必须首行、`super(...)` 与它互斥，这两条限制在这份仓库里各有一个最小反例，比文字描述好记'),
    },
    'java-ch03': {
        GUI: ('§2.1', '讲「方法重写的动态分派」时读 `docs/java/basis/` 的面向对象问答：它把「重载看编译期、重写看运行期」用一段代码跑出两种结果，正好对应本章 `invokevirtual` 的分派逻辑'),
        MALL: ('§3.2', '讲「抽象类与模板方法」时看 `mall-security` 的 `JwtAuthenticationTokenFilter`：它继承 `OncePerRequestFilter` 只填 `doFilterInternal`，父类负责「只执行一次」的骨架——这是「抽象类给骨架、子类填一步」的工业样本'),
        ADV: ('§3.1', '讲「抽象类 vs 接口」时对照 `docs/high-concurrency/` 与 `docs/micro-services/` 里的接口设计讨论：什么时候该用接口做「能力声明」、什么时候用抽象类做「骨架复用」，它的取舍标准和本章一致'),
        TUT: ('§4.1', '讲「final 与不可变」时看 `core-java` 的 final 示例：final 字段必须在构造器结束前赋值、final 类不可继承，两个限制各有一个能编译失败的对照样例'),
    },
    'java-ch04': {
        GUI: ('§2.1', '讲「ArrayList 扩容」时读 `docs/java/collection/` 下的 ArrayList 源码分析：`oldCapacity + (oldCapacity >> 1)` 的 1.5 倍增长与 `Arrays.copyOf` 的整段复制，解释了「为什么预估容量能省掉多次复制」'),
        MALL: ('§5.1', '讲「Queue/Deque 与批处理」时看 `mall-admin` 里批量导入的写法：一次查询取出 `List` 再分批处理，而不是循环单条查库——这是「集合选择决定 IO 次数」的直接证据'),
        ADV: ('§3.1', '讲「HashMap 的四层结构」时对照 `docs/high-concurrency/` 的 HashMap 深挖系列：数组 + 链表 + 红黑树、树化阈值 8 与退化阈值 6、扩容时的「原位或原位+旧容量」，这三条是面试追问的固定落点'),
        TUT: ('§4.1', '讲「Set 去重」时看 `core-java` 的集合示例：`HashSet` 去重依赖 `hashCode` + `equals`，`TreeSet` 依赖 `compareTo`，两份样例放在一起就能看出「去重判据被换掉了」'),
    },
    'java-ch05': {
        GUI: ('§1.1', '讲「受检与非受检异常」时读 `docs/java/basis/` 的异常问答：`Error`/`Exception`/`RuntimeException` 三分与「受检异常强制调用方决策」的取舍，它给出了「什么时候该包成运行时异常」的判断口径'),
        MALL: ('§3.1', '讲「异常链与根因保留」时看 `mall-common` 的统一返回体与业务异常：`ApiException` 携带错误码、原异常挂在 cause 上，缺了 cause 线上就只能看到「操作失败」四个字'),
        ADV: ('§2.1', '讲「try-with-resources」时对照 `docs/distributed-system/` 里对「资源泄漏导致雪崩」的描述：连接/句柄不释放最终表现为「Too many open files」，TWR 的 suppressed 语义正是为了防止 close 异常掩盖主异常'),
        TUT: ('§4.1', '讲「泛型擦除」时看 `core-java` 的泛型示例：`List<String>` 与 `List<Integer>` 在运行期是同一个类，所以不能 `new T[]`、不能对泛型做 `instanceof`——样例里有一条能编译失败的反例'),
    },
    'java-ch06': {
        GUI: ('§1.1', '讲「字节流与字符流的边界」时读 `docs/java/io/` 的基础篇：编码发生在 `InputStreamReader` 这个桥接点，`FileReader` 用平台默认编码所以跨环境必乱码——这条结论在本章有对应的可运行代码'),
        MALL: ('§2.1', '讲「Path 与 Files」时看 `mall-admin` 的文件上传实现：`Files.copy`/`Files.createDirectories` 替代了 `File` 的布尔返回值风格，异常直接抛出而不是静默返回 false'),
        ADV: ('§3.1', '讲「Selector 多路复用」时对照 `docs/high-concurrency/` 里「为什么 Redis 单线程还快」的分析：IO 多路复用把「等待」从线程里拿掉，与本章 Channel/Buffer/Selector 的模型是同一套思路'),
        TUT: ('§4.1', '讲「序列化」时看 `core-java` 的序列化示例：`serialVersionUID` 不一致会抛 `InvalidClassException`、`transient` 字段不参与序列化，两个坑各有一条最小复现'),
    },
    'java-ch07': {
        GUI: ('§2.1', '讲「JMM 与 happens-before」时读 `docs/java/concurrent/` 的并发基础问答：`volatile` 给可见性与有序性、不给原子性，`count++` 用它照样丢更新——本章的可运行代码会把这个结论跑出来'),
        MALL: ('§3.1', '讲「线程池七参数」时看 `mall-portal` 里的异步任务配置：核心数、队列、拒绝策略三者的组合决定了「任务堆积时是先扩容还是先拒绝」，无界队列会让 OOM 来得更晚但更猛'),
        ADV: ('§3.2', '讲「线程池任务流程」时对照 `docs/high-concurrency/threadpool.md`：核心线程 → 队列 → 最大线程 → 拒绝策略的四级判定，它用图示说明了「为什么不是先扩容」'),
        TUT: ('§4.1', '讲「AQS 与 ReentrantLock」时看 `core-java` 的锁示例：公平锁与非公平锁的吞吐差异、`tryLock` 的超时语义，样例里能直接改参数对比'),
    },
    'java-ch08': {
        GUI: ('§1.1', '讲「五块运行时数据区」时读 `docs/java/jvm/` 的内存区域篇：堆分代、方法区（元空间）、虚拟机栈的职责边界，它配了「哪块会 OOM、哪块不会」的对照表'),
        MALL: ('§2.1', '讲「GC 与容器内存限制」时看 `mall-admin` 的 Dockerfile：容器里必须显式给 `-Xmx`，否则 JVM 按宿主机内存算堆，容器被 OOMKill 时日志里连 OOM 都不一定有'),
        ADV: ('§2.2', '讲「七种收集器与停顿模型」时对照 `docs/high-concurrency/` 的 JVM 系列：CMS 的并发失败、G1 的 Region 与 Mixed GC、ZGC 的染色指针，三条线索能解释「为什么低延迟场景要换收集器」'),
        TUT: ('§3.1', '讲「双亲委派」时看 `core-java` 的 ClassLoader 示例：自定义 ClassLoader 覆写 `findClass` 而不是 `loadClass`，才能保留委派链——这是「打破双亲委派」的正确姿势'),
    },
    'java-ch09': {
        GUI: ('§1.1', '讲「Maven 依赖调解」时读 `docs/java/basis/` 的工程化章节：最短路径优先 + 先声明优先，两条规则决定了「为什么你的 jar 版本被别人带偏」，本章的冲突排查步骤与它一致'),
        MALL: ('§1.3', '讲「dependencyManagement 与 BOM」时看 `mall` 根 `pom.xml`：子模块只写 `groupId/artifactId` 不写版本，版本统一在父 POM 管——这就是「只声明版本、不引入依赖」的现成用法'),
        ADV: ('§3.1', '讲「自动配置」时对照 `docs/micro-services/` 的微服务落地文章：条件装配 + SPI 让「引入依赖即生效」，这也是 Spring Cloud starter 的组织方式'),
        TUT: ('§3.2', '讲「SpringApplication.run 的启动阶段」时看 `spring-boot-tutorials` 模块：一个最小 `@SpringBootApplication` 类加一个 `CommandLineRunner`，就能观察到「容器刷新完成 → 回调执行」的时序'),
    },
}

if __name__ == '__main__':
    sys.exit(apply('java', DATA))
