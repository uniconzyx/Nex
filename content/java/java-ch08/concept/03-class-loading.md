# 03 · 类加载机制：五阶段、双亲委派与三次「被打破」

## 一、类加载五阶段

```
加载 → 验证 → 准备 → 解析 → 初始化 → 使用 → 卸载
                ↑____________↓
              （解析可在初始化之后，支持动态绑定）
```

1. **加载（Loading）**：通过全限定名用**类加载器**读二进制字节流 → 生成**方法区内的运行时数据结构** → 堆中生成 `Class` 对象作为访问入口。
2. **验证（Verification）**：文件格式（魔数 `0xCAFEBABE`）→ 元数据（继承合法性、`final` 不被覆写）→ 字节码（控制流、类型检查）→ 符号引用。
3. **准备（Preparation）**：为**静态变量分配内存并设零值**。注意：`static int a = 10;` 在此阶段是 `a = 0`，**赋 10 发生在初始化阶段**。但 `static final int A = 10;` 是**编译期常量**，准备阶段就直接是 10。
4. **解析（Resolution）**：把常量池的**符号引用**替换为**直接引用**（类/字段/方法/接口方法四类）。
5. **初始化（Initialization）**：执行 **`<clinit>()`**（静态变量赋值 + 静态代码块，**按源码顺序**合并），是真正「用」类的开始。

**特别注意**：JVM 保证 `<clinit>()` 的**线程安全**（加锁），所以**静态内部类单例**天然线程安全且**懒加载**。

## 二、类初始化的六种主动引用（其余都是被动，不触发）

1. `new`、读写静态字段（非 `final` 常量）、调用静态方法
2. **反射**：`Class.forName("X")`（注意它**会**触发初始化）
3. 初始化子类前，先初始化**父类**
4. 虚拟机启动时的**主类**
5. `MethodHandle` / `VarHandle` 解析的结果
6. 接口的**默认方法**（`default`）被实现类初始化时

**被动引用三例（不触发初始化）**：
- 通过**子类**访问**父类的静态字段** → 只初始化父类
- **数组定义**：`X[] arr = new X[10];` → 不初始化 `X`
- **常量传播**：访问 `static final` 编译期常量 → 编译期内联，不初始化（编译期常量不触发）。

## 三、双亲委派模型

```
Bootstrap（C++ 实现，加载 JAVA_HOME/lib 核心类）
   ↑ parent
Extension / Platform（JDK 9+ 为 Platform ClassLoader）
   ↑ parent
Application（加载 classpath）
   ↑ parent
自定义 ClassLoader
```

**规则**：收到加载请求先**委派给 parent**，parent 加载不了才自己加载。

**价值（两句话背）**：
1. **安全**：核心类库不被篡改——你自己写个 `java.lang.String` 也没机会加载，Bootstrap 先加载了。
2. **避免重复**：同一个类在各级加载器中**只被加载一次**（保证了 `Class` 对象的唯一性，即 `equals`/`isAssignableFrom` 语义）。

**类的唯一性 = 类加载器 + 全限定名**。同一个 `.class` 被两个不同加载器加载，得到的 `Class` 对象 **不相等**。

## 四、三次「被打破」的历史

| 打破 | 场景 | 手段 |
|---|---|---|
| **第一次** | JDK 1.2 兼容老代码 | 重写 `loadClass()`（不调用 `super.loadClass`） |
| **第二次** | **SPI**（JDBC `DriverManager`、JNDI、`ServiceLoader`） | **线程上下文类加载器** `Thread.currentThread().getContextClassLoader()` —— 父加载器「反向」委派给子加载器 |
| **第三次** | 热替换 / 热部署（OSGi、Tomcat） | **自定义加载器 + 平级委派/网状委派**，每个 WebApp 一个加载器，实现**应用隔离** |

**Tomcat 的类加载顺序**（面试常问）：`Bootstrap → Platform → WebApp/classes → WebApp/lib → Common → Catalina`（先自己，后委派——**打破了双亲委派**），目的是让**每个 WebApp 用自己版本的库**。

## 五、字节码文件结构

```
ClassFile {
    u4  magic;               // 0xCAFEBABE
    u2  minor_version;     
    u2  major_version;       // JDK 8=52, 11=55, 17=61, 21=65, 23=67
    u2  constant_pool_count;
    cp_info constant_pool[]; // 常量池（符号引用 + 字面量）
    u2  access_flags;
    u2  this_class; u2 super_class;
    u2  interfaces_count; u2 interfaces[];
    u2  fields_count;      field_info fields[];
    u2  methods_count;     method_info methods[];   // 含 Code 属性（字节码）
    u2  attributes_count;  attribute_info attributes[];
}
```

**五种方法调用指令**（高频考点）：

| 指令 | 用于 | 分派方式 |
|---|---|---|
| `invokestatic` | 静态方法 | 静态分派（编译期定） |
| `invokespecial` | 构造器、私有方法、`super` 调用 | 静态分派 |
| `invokevirtual` | 普通实例方法 | **动态分派**（虚方法表 vtable） |
| `invokeinterface` | 接口方法 | **动态分派**（itable） |
| `invokedynamic` | **lambda、字符串拼接、记录类** | 由 `BootstrapMethod` 动态决定 |

## 六、可运行代码：双亲委派链与自定义加载器

```java
public class Main {
    /** 重写 findClass（遵守委派）：父加载不到时走自己的逻辑 */
    static class MyLoader extends ClassLoader {
        MyLoader(ClassLoader parent) { super(parent); }
        @Override protected Class<?> findClass(String name) throws ClassNotFoundException {
            System.out.println("  findClass called for: " + name);
            throw new ClassNotFoundException(name);   // 本示例不真正定义新类
        }
    }

    /** 重写 loadClass（打破委派）：先自己找，找不到再交给父 */
    static class BreakingLoader extends ClassLoader {
        BreakingLoader(ClassLoader parent) { super(parent); }
        @Override protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
            synchronized (getClassLoadingLock(name)) {
                Class<?> c = findLoadedClass(name);
                if (c == null) {
                    System.out.println("  BreakingLoader tries first: " + name);
                    try { c = findClass(name); }
                    catch (ClassNotFoundException ignored) { }
                    if (c == null) c = super.loadClass(name, resolve);   // 兜底委派
                }
                if (resolve) resolveClass(c);
                return c;
            }
        }
    }

    public static void main(String[] args) throws Exception {
        ClassLoader app = Main.class.getClassLoader();
        System.out.println("=== delegation chain ===");
        for (ClassLoader cl = app; cl != null; cl = cl.getParent())
            System.out.println("  " + cl);
        System.out.println("bootstrap parent is null: " + (platformParentOf(app) == null));

        System.out.println("=== findClass path (delegation respected) ===");
        Class<?> s = new MyLoader(app).loadClass("java.lang.String");
        System.out.println("java.lang.String from: " + (s == String.class ? "BOOTSTRAP (same Class object)" : "other"));

        System.out.println("=== loadClass override (delegation broken) ===");
        ClassLoader bl = new BreakingLoader(app);
        System.out.println("load java.lang.String ok: " + (bl.loadClass("java.lang.String") != null));

        System.out.println("=== identity = loader + FQN ===");
        ClassLoader c1 = new BreakingLoader(app), c2 = new BreakingLoader(app);
        System.out.println("two loaders, same class name, same Class object: "
                + (c1.loadClass("java.lang.String") == c2.loadClass("java.lang.String")));
    }

    static ClassLoader platformParentOf(ClassLoader app) {
        ClassLoader p = app.getParent();
        return p == null ? null : p.getParent();
    }
}
```

## 三视角解析

### 🧑‍💻 程序员视角
- **`Class.forName(String)` 与 `ClassLoader.loadClass(String)` 的区别**：前者默认**初始化**（还会用调用者的加载器），后者默认**不初始化**（只加载+链接）。JDBC 老代码写 `Class.forName("com.mysql.cj.jdbc.Driver")` 正是为了触发**静态块里的 `DriverManager.registerDriver`**。
- **热部署为什么难**：类唯一性含加载器，所以「重新加载」必须**换一个新加载器**，且旧加载器及其加载的所有类、静态引用**必须全部可回收**——任何一处静态缓存/`ThreadLocal`/线程池持有引用都会**整片泄漏**（这就是反复 `devtools` 重启后 Metaspace OOM 的原因）。
- **`ClassNotFoundException` vs `NoClassDefFoundError`**：前者是**加载时**找不到（受检异常，`Class.forName`/`loadClass` 抛）；后者是**链接/初始化时**找不到（`Error`，通常表示编译时有、运行期缺）。
- **别在自定义加载器里缓存 `Class` 却不释放**：`findLoadedClass` 由 JVM 维护，但你自己的 `Map<String,Class>` 会成为**强引用根**，让类永远卸载不掉。

### 🎓 博士生视角
- **「类加载器 + 全限定名」作为类身份**，本质是把「命名空间」从语言层下推到**运行时子系统**，从而让同一份字节码在不同加载器下成为**不同类型**——这是 OSGi/Tomcat 隔离的形式化基础，对应类型论里的**名义子类型 vs 结构子类型**之争。
- **`<clinit>()` 的线程安全**由 JVM 通过「类初始化锁」实现，且做了**死锁检测**（若初始化线程 A 等待 B 初始化、B 又等 A，则只让一个完成，另一个继续）——这是 JLS 规定的「递归初始化」语义。
- **SPI 打破委派的根本矛盾**：接口在**核心库**（Bootstrap 加载），实现类在**应用**（App 加载），父加载器看不到子加载器的东西，于是只能用**线程上下文加载器**做一次「逆向委派」。**依赖倒置在这里表现为「上下文传递」**。
- **`invokedynamic` 的 `BootstrapMethod` 在首次执行时生成 `CallSite`**，lambda 因此**只生成一个内部方法 + 一个动态调用点**，不产生匿名类文件（JDK 8 之前用匿名类，LambdaMetafactory 代替了它）。这就是「lambda 不生成 `.class`」的原因。

### 📚 考研者视角
- 直接对应 **408 操作系统的「程序的链接」**：**静态链接 / 装入时动态链接 / 运行时动态链接**。JVM 的**解析**≈符号地址到逻辑地址的转换，**类加载**≈**装入**，**双亲委派**≈**装入模块的查找顺序策略**。
- 常考「**编译期常量 vs 运行期常量**」：`static final int A = 10`（编译期常量，不触发初始化）与 `static final int B = f()`（运行期赋值，触发 `<clinit>`）——**这是初始化时机题的标准陷阱**。
- 408 讲**重定位**：JVM 的**解析阶段把符号引用换成直接引用**就是标准的**动态重定位**，只不过它发生在类级别而非进程级别。
- 记忆锚点：**「加载验证准备解析初始化」五阶段、『准备给零值，初始化给真值』、『Bootstrap→Platform→App→自定义，先委派后自己』、『唯一性 = 加载器 + 全限定名』**。
