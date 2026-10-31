# JDK 环境与第一个 Java 程序

Java 是编译型 + 解释型混合语言：源码 `.java` 先由 `javac` 编译为字节码 `.class`，再由 JVM 解释/JIT 执行，因此"一次编写，到处运行"。

这句话被引用得太多以至于失去信息量。真正需要理解的是：**为什么中间加一层字节码，能换来跨平台，代价又是什么**。

## 一、三个缩写的关系：JDK ⊃ JRE ⊃ JVM

```text
JDK / JRE / JVM 的包含关系

  ┌──────────── JDK（开发用）────────────┐
  │  javac 编译器、jdb 调试器、jlink 等工具 │
  │  ┌──────────── JRE（运行用）────────┐  │
  │  │  标准类库 rt（java.lang 等）      │  │
  │  │  ┌────────── JVM ──────────┐    │  │
  │  │  │  字节码执行引擎、GC、     │    │  │
  │  │  │  解释器 + JIT 编译器      │    │  │
  │  │  └────────────────────────┘    │  │
  │  └──────────────────────────────┘  │
  └────────────────────────────────────┘
```

- **JVM**：执行 `.class` 的抽象机器，规范定义指令集、类文件格式、内存模型。
- **JRE** = JVM + 标准类库：能"运行" Java 程序。
- **JDK** = JRE + 开发工具：能"编译" Java 程序。

生产容器只装 JRE（或 Java 9+ 的 `jlink` 裁剪运行时）就够了，镜像能小几百 MB。

## 二、从源码到运行：四步

1. **编译**：`javac Main.java` → `Main.class`（字节码，不是机器码）。
2. **加载**：`java Main` 启动 JVM，类加载器（Bootstrap → Platform → Application）按双亲委派逐级查找 `Main.class`。
3. **验证 + 准备 + 解析**：字节码校验（防止非法指令破坏 JVM）、静态字段分配默认值、符号引用解析。
4. **执行**：解释器先跑；热点方法被 JIT（C1 快速编译 / C2 激进优化）编译成本地机器码。

```java
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, Java");
    }
}
```

```bash
javac Main.java     # 生成 Main.class
java Main           # 运行，注意不带 .class 后缀
```

### 文件名与类的约束

- 一个 `.java` 文件里**最多一个 `public` 类**，且文件名必须与它同名。
- 非 `public` 类可以随便起名，一个文件里可以有多个。
- 入口签名固定：`public static void main(String[] args)`。少一个修饰符、写错参数类型，JVM 会报"找不到 main 方法"。

## 三、JIT 为什么让 Java "越跑越快"

Java 常被误解为"慢"。实际上长期运行的服务，JIT 编译出的代码可以接近 C++：

- **解释执行**先保证启动快。
- **热点探测**：方法被调用足够多次（C1 约 1500 次、C2 约 10000 次，阈值可调）后编译为本机码。
- **运行期信息驱动的优化**：JIT 能看到"这个接口实际只有一个实现"（单态内联）、"这个对象没有逃逸出方法"（逃逸分析 → 栈上分配），这些是 AOT 编译器做不到的——因为静态编译时不知道运行时分布。
- **去优化（deoptimization）**：假设被打破时（比如新加载了一个实现类），JIT 可以退回解释执行。这是"乐观优化 + 兜底"的经典设计。

代价是：**预热期**性能不稳、**内存占用高**（JIT 编译线程、元空间、代码缓存）、**启动慢**。所以微服务/Serverless 场景更倾向 GraalVM native-image（AOT），换取毫秒级启动，代价是失去运行期优化与部分反射能力。

## 四、classpath 与包：最常见的启动失败原因

`java -cp <路径> 全限定类名`，其中"全限定"包含包名：

```bash
java -cp out com.example.Main     # 不是 java out/com/example/Main.class
```

`ClassNotFoundException`（显式加载找不到）与 `NoClassDefFoundError`（编译时在、运行时缺）八成都是 classpath 问题。排查顺序：**先打印 `-verbose:class` 看类从哪加载，再怀疑代码**。

包的目录结构与声明必须一致：`package com.example;` 的文件必须放在 `com/example/` 下，否则 `javac` 能过、运行期找不到。

## 五、边界与陷阱

- **`java Main.class` 是错的**：参数是类名，不是文件名。
- **`public class` 与文件名不一致**：编译报错 `class X is public, should be declared in a file named X.java`。
- **`main` 签名写错**：`public void main(String[] args)`（缺 `static`）不报编译错，但运行时报"找不到主方法"。
- **`javac` 与 `java` 版本不一致**：用 JDK 21 编译、JRE 8 运行会报 `UnsupportedClassVersionError`。编译时可用 `--release 17` 锁定目标版本。
- **类路径分隔符跨平台不同**：Windows 是 `;`，Unix 是 `:`。用 `-cp` 时注意，构建工具（Maven/Gradle）会替你处理。

## 六、可运行示例：验证参数、类名与版本

```java
public class Main {
    public static void main(String[] args) {
        System.out.println("args.length = " + args.length);
        for (int i = 0; i < args.length; i++) {
            System.out.println("args[" + i + "] = " + args[i]);
        }
        System.out.println("java.version = " + System.getProperty("java.version"));
        System.out.println("java.home    = " + System.getProperty("java.home"));
        System.out.println("classpath    = " + System.getProperty("java.class.path"));
    }
}
```

```bash
javac Main.java && java Main alpha beta
```

`args` 就是命令行参数数组，不含程序名（这点与 C 的 `argv` 不同——C 的 `argv[0]` 是程序名）。`java.home` 告诉你实际用的是哪个 JRE，排查"多版本 JDK 冲突"时这条最有用。

## 三视角解析

### 🧑‍💻 程序员视角
- 关系记牢：**JDK ⊃ JRE ⊃ JVM**；开发装 JDK，生产只需 JRE（容器镜像用 jre 变体更小）。
- 流程是「`javac` 编译成 `.class` 字节码 → `java` 启动 JVM 执行」；选 **LTS 版本**（17 / 21）而不是每个新版本。
- 排障第一课：`ClassNotFoundException` 与 `NoClassDefFoundError` 八成都指向 classpath/依赖问题，先看启动参数再怀疑代码。
- 用 SDKMAN / jenv / IDE 的 toolchain 固定版本，避免"我本机是好的"这类环境差异。

### 🎓 博士生视角
- Java 的「一次编写、到处运行」依赖**字节码 + JVM 规范**这两件事：JVM 是一个被标准定义的抽象机器（指令集、类文件格式、内存模型），任何符合规范的实现都能运行同一份 class。
- **JIT 分层编译**是关键工程：解释执行先跑起来，热点方法（C1/C2）再编译成本地码并做内联、逃逸分析等激进优化——这解释了「为什么 Java 长时间运行会变快」。
- 与 AOT（GraalVM native-image）对比：AOT 换来启动快与内存小，代价是失去运行期动态优化与部分反射能力。
- 双亲委派模型（Bootstrap → Platform → Application）保证核心类不被应用层伪造替换，也是 Tomcat 等容器需要打破它来实现应用隔离的原因。
- 字节码校验器（verifier）是 JVM 安全模型的基石：它保证栈平衡、类型安全、访问控制合法，从而让"下载来的 class"可以在沙箱里执行——这是 Java 早期作为浏览器语言的设计遗产。

### 📚 考研者视角
- 与**编译原理**的「中间代码 + 虚拟机」直接对应：字节码是中间表示，JVM 是它的解释/即时编译执行器。
- 408 统考不考 Java；但若专业课含「程序设计语言原理」，常考「解释执行与编译执行的区别」「虚拟机的概念」。
- 常考辨析：编译型（C/C++，直接生成机器码）vs 解释型（Python，逐行解释）vs 混合型（Java/C#，先编译成中间码再解释/JIT）。
- 记忆锚点：**JDK ⊃ JRE ⊃ JVM**；**先编译成 class，再由 JVM 执行**；**JIT 让热点代码接近原生性能**。
