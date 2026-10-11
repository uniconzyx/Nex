# JDK 环境与第一个 Java 程序

Java 是编译型 + 解释型混合语言：源码 `.java` 先由 `javac` 编译为字节码 `.class`，再由 JVM 解释/JIT 执行，因此"一次编写，到处运行"。

## 要点

- 安装 JDK 后，用 `javac Main.java` 编译，用 `java Main` 运行（注意运行时不带 `.class` 后缀）
- 一个 `.java` 文件中 `public` 类只能有一个，且文件名须与该类同名
- 程序入口是固定签名：`public static void main(String[] args)`
- 输出用 `System.out.println`（带换行）或 `System.out.print`（不带换行）

```java
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, Java");
    }
}
```

> 命令行参数通过 `args` 数组传入；无参数时 `args.length == 0`。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 关系记牢：**JDK ⊃ JRE ⊃ JVM**；开发装 JDK，生产只需 JRE（容器镜像用 jre 变体更小）。
- 流程是「`javac` 编译成 `.class` 字节码 → `java` 启动 JVM 执行」；选 **LTS 版本**（17 / 21）而不是每个新版本。
- 排障第一课：`ClassNotFoundException` 与 `NoClassDefFoundError` 八成都指向 classpath/依赖问题，先看启动参数再怀疑代码。

### 🎓 博士生视角
- Java 的「一次编写、到处运行」依赖**字节码 + JVM 规范**这两件事：JVM 是一个被标准定义的抽象机器（指令集、类文件格式、内存模型），任何符合规范的实现都能运行同一份 class。
- **JIT 分层编译**是关键工程：解释执行先跑起来，热点方法（C1/C2）再编译成本地码并做内联、逃逸分析等激进优化——这解释了「为什么 Java 长时间运行会变快」。
- 与 AOT（GraalVM native-image）对比：AOT 换来启动快与内存小，代价是失去运行期动态优化与部分反射能力。

### 📚 考研者视角
- 与**编译原理**的「中间代码 + 虚拟机」直接对应：字节码是中间表示，JVM 是它的解释/即时编译执行器。
- 408 统考不考 Java；但若专业课含「程序设计语言原理」，常考「解释执行与编译执行的区别」「虚拟机的概念」。
- 记忆锚点：**JDK ⊃ JRE ⊃ JVM**；**先编译成 class，再由 JVM 执行**。
