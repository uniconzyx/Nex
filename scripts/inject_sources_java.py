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

MANIFEST = "content/java/_manifest.json"
CH_DIR = "content/java"

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
    # ---------------- java-ch01 环境与基础语法 ----------------
    "java-ch01": [
        "§2.1 八种基本类型与它们的固定位宽 · 读 `docs/java/basis/` 下的基本类型问答："
        "它把「`byte` 恒为有符号」与「`char` 是 16 位无符号 UTF-16 码元」两条一次讲透，"
        "正好解释「Java 没有无符号整型」为什么会让 `byte b = 200` 编译失败；"
        "配合 §2.4「char 是 UTF-16 码元，不是字符」，就明白 `emoji` 为什么占两个 char",

        "§1.4 classpath 与包：最常见的启动失败原因 · 看 `mall-common` 模块的 "
        "`com.macro.mall.common` 包结构：一个被其余模块依赖的公共包必须只放「无业务状态」的工具与统一返回体，"
        "这比背 classpath 定义更能说明「包边界 = 依赖方向」；"
        "这也解释了 §1.2 四个步骤里「class 找不到」为什么总发生在公共包被循环依赖之后",

        "§1.3 JIT 为什么让 Java「越跑越快」 · 对照 `docs/high-concurrency/` 里的 JVM 系列文章："
        "它解释了「解释执行 → C1 → C2」的分层编译与逃逸分析，"
        "回读本章 §1.2 四步流程就能说清「为什么预热前后同一段循环耗时差一个数量级」",

        "§3.1 `if` 与布尔条件：没有「真值」概念 · 看 `core-java` 模块的语法示例："
        "Java 的 `if` 只接受 `boolean`，不存在 C 的「非零即真」，"
        "这份仓库用最小样例把这条差异固定下来，可直接拿来对照自己的写法；"
        "配合 §3.2 `switch` 从穿透到表达式，两条控制流的边界就都清楚了",
    ],
    # ---------------- java-ch02 类与对象 ----------------
    "java-ch02": [
        "§4.2 实现机制：为什么两者必须同时重写 · 读 `docs/java/basis/` 的对象基础问答："
        "等价关系必须自反/对称/传递，哈希值必须与 equals 一致"
        "——它用 `HashMap` 查不到键的现场说明违反契约的后果；"
        "先读 §4.1「等价关系是数学约束」，再看这个现场，因果链就完整了",

        "§1.1 理论根基：对象是「带标签的连续内存」 · 看 `mall-common` 里的 `CommonResult`："
        "一个只有 `code/message/data` 三个字段的返回体，字段顺序与类型决定对象头之后的内存排布，"
        "也是「为什么 DTO 要小而扁平」的现成样本；"
        "这直接对应 §4.2 里 hashCode 的计算成本——字段越多，默认哈希算得越慢",

        "§4.2 实现机制：为什么两者必须同时重写（哈希分布视角） · 对照 `docs/high-concurrency/` 的 HashMap 系列："
        "它把「扰动函数 + 扩容 rehash」讲到面试深度，能解释为什么自定义 key 的 `hashCode` 分布不均会让链表变长；"
        "读时对照本章 §4.3 工程实践里用 `Objects.hash` 与手写的取舍",

        "§3.2 实现机制：重载、this() 链与初始化顺序 · 看 `core-java` 的构造器重载示例："
        "`this(...)` 必须首行、`super(...)` 与它互斥，这两条限制在这份仓库里各有一个最小反例，"
        "比文字描述好记；"
        "理解它们再看 §3.1「构造器是建立不变式的契约」，就明白为什么初始化顺序不能随意调",
    ],
    # ---------------- java-ch03 继承与多态 ----------------
    "java-ch03": [
        "§2.2 实现机制：JVM 如何做动态分派 · 读 `docs/java/basis/` 的面向对象问答："
        "它把「重载看编译期、重写看运行期」用一段代码跑出两种结果，"
        "正好对应本章 `invokevirtual` 的分派逻辑；"
        "读完再回 §2.1「override 是运行期的行为替换」，就明白为什么「字段不参与动态分派」",

        "§3.2 实现机制：invokevirtual vs invokeinterface · 看 `mall-security` 的 "
        "`JwtAuthenticationTokenFilter`：它继承 `OncePerRequestFilter` 只填 `doFilterInternal`，"
        "父类负责「只执行一次」的骨架——这是「抽象类给骨架、子类填一步」的工业样本；"
        "注意它是继承而非实现接口，所以走 `invokevirtual`",

        "§3.1 理论根基：两者回答不同的问题 · 对照 `docs/high-concurrency/` 与 `docs/micro-services/` 里的接口设计讨论："
        "什么时候该用接口做「能力声明」、什么时候用抽象类做「骨架复用」，它的取舍标准和本章一致；"
        "读完再看 §3.2 的字节码指令差异，就明白「接口多实现」为什么不增加方法表查找成本",

        "§4.1 理论根基：final 是「约束即契约」 · 看 `core-java` 的 final 示例："
        "final 字段必须在构造器结束前赋值、final 类不可继承，两个限制各有一个能编译失败的对照样例；"
        "配合 §4.2 里 `String` 为什么是 final——不可变才能安全地被多线程共享",
    ],
    # ---------------- java-ch04 集合框架 ----------------
    "java-ch04": [
        "§2.2 实现机制：ArrayList 扩容的 1.5 倍与 JVM 细节 · 读 `docs/java/collection/` 下的 ArrayList 源码分析："
        "`oldCapacity + (oldCapacity >> 1)` 的 1.5 倍增长与 `Arrays.copyOf` 的整段复制，"
        "解释了「为什么预估容量能省掉多次复制」；"
        "配合 §2.4「怎么选」，就能算出「一万条数据差几次复制」",

        "§5.1 Queue 与 Deque：双端抽象与 ArrayDeque · 看 `mall-admin` 里批量导入的写法："
        "一次查询取出 `List` 再分批处理，而不是循环单条查库"
        "——这是「集合选择决定 IO 次数」的直接证据；"
        "读时对照 §2.5 边界与陷阱，就明白为什么这里不用 `LinkedList`",

        "§3.2 实现机制（JDK 8）：四层结构 · 对照 `docs/high-concurrency/` 的 HashMap 深挖系列："
        "数组 + 链表 + 红黑树、树化阈值 8 与退化阈值 6、扩容时的「原位或原位+旧容量」，"
        "这三条是面试追问的固定落点；"
        "先读 §3.1「哈希表的本质」，再来看「为什么要树化」，逻辑才顺",

        "§4.1 理论根基：Set 是「约束后的 Map」 · 看 `core-java` 的集合示例："
        "`HashSet` 去重依赖 `hashCode` + `equals`，`TreeSet` 依赖 `compareTo`，"
        "两份样例放在一起就能看出「去重判据被换掉了」；"
        "这正是 §4.3「去重与排序的正确姿势」要分开讲的原因",
    ],
    # ---------------- java-ch05 异常体系与泛型进阶 ----------------
    "java-ch05": [
        "§1.2 实现机制：编译期的「受检」检查 · 读 `docs/java/basis/` 的异常体系问答："
        "受检异常在字节码里与运行时异常没有区别，区别只在编译期的 `throws` 检查；"
        "理解这一点再看 §1.3「受检异常的调用方契约与函数式接口的冲突」，"
        "就明白 `Stream.map` 里为什么不能直接抛 `IOException`",

        "§2.1 理论根基：资源的「获取即释放」契约 · 看 `mall-admin` 里的文件读写实现："
        "`try-with-resources` 把 `close()` 放进编译器生成的 `finally`，"
        "异常在 `close` 时也不会丢——这正是 §2.2 编译器展开 TWR 的关键；"
        "对照 §3.4 `suppressed` 与 `cause` 的配合，就知道被吞掉的异常去了哪",

        "§3.1 理论根基：finally 的语义是「无论怎样都执行」 · 看 `core-java` 的 finally 示例："
        "`finally` 里 `return` 会覆盖 try 的返回值，这条反例比任何描述都直接；"
        "配合 §3.2 字节码层面的顺序，就能解释「为什么 catch 里 return 了 finally 还在跑」",

        "§4.1 理论根基：为什么 Java 选了「擦除」而非「具化」 · 读 `docs/java/basis/` 的泛型章节："
        "擦除是为了「升级 JDK 不破坏已有二进制」，代价是运行时拿不到类型参数；"
        "读完再回 §4.3「桥接方法为何存在」，就明白 `List<String>` 与 `List<Integer>` 为什么是同一个类",
    ],
    # ---------------- java-ch06 IO 与 NIO ----------------
    "java-ch06": [
        "§1.1 主题一：字节与字符的分工 · 读 `docs/java/io/` 的基础篇："
        "编码发生在 `InputStreamReader` 这个桥接点，`FileReader` 用平台默认编码所以跨环境必乱码"
        "——这条结论在本章有对应的可运行代码；"
        "配合 §1.2「装饰器模式与缓冲的语义」，就明白 `BufferedReader` 套在谁外面才有意义",

        "§2.1 主题一：File 与 Path 的差别，以及「路径拼接」的正确算法 · 看 `mall-admin` 的文件上传实现："
        "`Files.copy`/`Files.createDirectories` 替代了 `File` 的布尔返回值风格，异常直接抛出而不是静默返回 false；"
        "这对应 §2.2「目录遍历与文件属性」里 `Files.walk` 为什么用 `Stream` 而非返回数组",

        "§3.2 主题二：Selector 多路复用与零拷贝 · 对照 `docs/high-concurrency/` 里「为什么 Redis 单线程还快」的分析："
        "IO 多路复用把「等待」从线程里拿掉，与本章 Channel/Buffer/Selector 的模型是同一套思路；"
        "读之前先看 §3.1「ByteBuffer 的三游标与状态机」——不懂 flip 就理解不了非阻塞读写",

        "§4.1 主题一：序列化机制的三个真相 · 看 `core-java` 的序列化示例："
        "`serialVersionUID` 不一致会抛 `InvalidClassException`、`transient` 字段不参与序列化，"
        "两个坑各有一条最小复现；"
        "配合 §4.2「IO 模型与 Java 的对应关系」，就能解释为什么跨进程传输更愿意用 JSON 而非原生序列化",
    ],
    # ---------------- java-ch07 并发 ----------------
    "java-ch07": [
        "§2.2 happens-before：JMM 给出的「可见性合同」 · 读 `docs/java/concurrent/` 的并发基础问答："
        "`volatile` 给可见性与有序性、不给原子性，`count++` 用它照样丢更新"
        "——本章的可运行代码会把这个结论跑出来；"
        "先读 §2.1 并发三大问题，才知道要分别用哪条语义去解",

        "§3.2 `ThreadPoolExecutor` 的七个构造参数 · 看 `mall-portal` 里的异步任务配置："
        "核心数、队列、拒绝策略三者的组合决定了「任务堆积时是先扩容还是先拒绝」，"
        "无界队列会让 OOM 来得更晚但更猛；"
        "这正是 §3.3「execute() 的判定链」在真实项目里的落点",

        "§3.3 任务提交流程（`execute()` 的判定链） · 对照 `docs/high-concurrency/threadpool.md`："
        "核心线程 → 队列 → 最大线程 → 拒绝策略的四级判定，它用图示说明了「为什么不是先扩容」；"
        "配合 §3.8「Executors 四个工厂方法的误用风险」，就明白 `newFixedThreadPool` 的无界队列坑在哪",

        "§4.1 理论根基：AQS —— JUC 的「半成品锁」 · 看 `core-java` 的锁示例："
        "公平锁与非公平锁的吞吐差异、`tryLock` 的超时语义，样例里能直接改参数对比；"
        "读完再回 §4.2「ReentrantLock vs synchronized」，取舍标准才对得上有依据",
    ],
    # ---------------- java-ch08 JVM ----------------
    "java-ch08": [
        "§1.1 五块运行时数据区 · 读 `docs/java/jvm/` 的内存区域篇："
        "堆分代、方法区（元空间）、虚拟机栈的职责边界，"
        "它配了「哪块会 OOM、哪块不会」的对照表；"
        "配合 §1.2 堆的分代结构，就能解释「为什么栈溢出报 StackOverflowError 而不是 OOM」",

        "§4.1 四类 OOM 与各自的第一反应 · 看 `mall-admin` 的 Dockerfile："
        "容器里必须显式给 `-Xmx`，否则 JVM 按宿主机内存算堆，"
        "容器被 OOMKill 时日志里连 OOM 都不一定有——"
        "这正是本章「容器化后堆大小算错」的经典现场，定位要回 §4.2 工具链",

        "§2.4 七种收集器与停顿模型 · 对照 `docs/high-concurrency/` 的 JVM 系列："
        "CMS 的并发失败、G1 的 Region 与 Mixed GC、ZGC 的染色指针，"
        "三条线索能解释「为什么低延迟场景要换收集器」；"
        "读之前先看 §2.3 三大 GC 算法，否则分不清收集器之间的差别是在「算法」还是「工程实现」",

        "§3.3 双亲委派模型 · 看 `core-java` 的 ClassLoader 示例："
        "自定义 ClassLoader 覆写 `findClass` 而不是 `loadClass`，才能保留委派链"
        "——这是「打破双亲委派」的正确姿势；"
        "对照 §3.4 三次「被打破」的历史，就明白 Tomcat 为什么要自己实现一个",
    ],
    # ---------------- java-ch09 Maven 与 Spring Boot 入门 ----------------
    "java-ch09": [
        "§1.2 传递依赖与依赖调解 · 读 `docs/java/basis/` 的工程化章节："
        "最短路径优先 + 先声明优先，两条规则决定了「为什么你的 jar 版本被别人带偏」，"
        "本章的冲突排查步骤与它一致；"
        "配合 §1.3 BOM，就明白为什么统一版本管理能消掉大半这类问题",

        "§1.3 dependencyManagement 与 BOM：只声明「版本」，不引入依赖 · 看 `mall` 根 `pom.xml`："
        "子模块只写 `groupId/artifactId` 不写版本，版本统一在父 POM 管"
        "——这就是「只声明版本、不引入依赖」的现成用法；"
        "读时对照 §2.3「多模块：聚合 ≠ 继承」，就分清 `modules` 与 `parent` 两个不同机制",

        "§3.3 自动配置的原理：SPI + 条件装配 · 对照 `docs/micro-services/` 的微服务落地文章："
        "条件装配 + SPI 让「引入依赖即生效」，这也是 Spring Cloud starter 的组织方式；"
        "读完再回本章 §3.1「`@SpringBootApplication` 是三个注解的合成」，因果就完整了",

        "§3.2 SpringApplication.run 的启动阶段 · 看 `spring-boot-tutorials` 模块："
        "一个最小 `@SpringBootApplication` 类加一个 `CommandLineRunner`，"
        "就能观察到「容器刷新完成 → 回调执行」的时序；"
        "配合 §3.7「`--debug` 之后看什么」，启动慢或 Bean 没注册时就有了排查入口",
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
