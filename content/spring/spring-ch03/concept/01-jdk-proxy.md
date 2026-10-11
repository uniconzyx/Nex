# 一、JDK 动态代理：原理与四类通知

## 一、JDK 动态代理的工作机制（中立陈述）

JDK 动态代理是 `java.lang.reflect.Proxy` 在**运行时**为「一组接口」生成的代理类
（命名形如 `jdk.proxyN.$ProxyK`，实现给定接口）。所有接口方法的调用都被路由到
统一的 `InvocationHandler.invoke(proxy, method, args)`：

```
调用方 --接口方法--> 代理对象($Proxy) --invoke--> InvocationHandler --反射 method.invoke(target,args)--> 真实对象
```

四类通知在 `invoke` 内按位置织入：
- **前置（Before）**：`method.invoke` 之前打印/校验；
- **环绕（Around）**：前后都包，可改参数、吞异常、替换返回值、计时；
- **后置返回（AfterReturning）**：`method.invoke` 正常返回后；
- **异常（AfterThrowing）**：`method.invoke` 抛 `InvocationTargetException` 后取其 `cause`。

### 🧑‍💻 程序员视角
- 工程里 JDK 代理是「无侵入增强」的最小可行工具：给任意接口加日志/鉴权/重试，不动业务类。
- 性能：每次调用走反射 `method.invoke`，比直接调用慢（约数倍到十倍量级）；高频热点路径别滥用，
  或换 ByteBuddy/手工生成的代理。
- 坑：Handler 里 `method.invoke(target, args)` 抛出的业务异常会被包成 `InvocationTargetException`，
  取真实异常要用 `e.getCause()`（见 ex03），否则拿到的是包装异常、类型判断全错。
- 替代：JDK 代理只能代理接口；要代理类用 CGLIB（见 02）。

### 🎓 博士生视角
- `Proxy.newProxyInstance` 在运行时调用 `ProxyGenerator.generateProxyClass` 生成字节码：
  代理类的每个接口方法体都编译成「调 `h.invoke(this, <对应的 Method>, <参数数组>)`」。
  因此所有方法共享同一个 Handler，Handler 靠 `Method` 对象区分目标方法。
- 为什么必须接口：`Proxy` 生成的类**已经 extends Proxy**（Java 单继承），无法再 extends 业务类，
  只能 implements 接口——这是「单继承限制」的直接后果。
- 反射委派的内存模型：`method` 是从接口提取的 `Method` 对象，调用时按 `target` 的实际类型分派，
  与代理类无关；代理类只负责「拦截 + 转发」，不持有业务逻辑。

### 📚 考研者视角（面试笔试考点）
- 标准问法：「JDK 动态代理的实现原理？」答：运行时为接口生成实现类（`$Proxy`），
  方法调用统一进入 `InvocationHandler.invoke`，内部反射调用目标对象。
- 常考口径：JDK 动态代理**只能代理接口**（不能代理普通类），原因是生成的代理类已继承 `Proxy`、
  受 Java 单继承限制。
- 易混点：`InvocationTargetException` 是反射调用目标方法抛异常时的「包装」，
  真实异常在 `getCause()` 中——笔试常考「如何拿到原始异常」。

## 二、InvocationHandler 与反射委派（中立陈述）

`InvocationHandler` 是函数式接口（仅 `invoke` 方法），是 JDK 代理的「拦截中枢」。
它持有 `target`（被代理的真实对象），`invoke` 内用 `method.invoke(target, args)` 完成真正的业务调用。
代理对象、Handler、真实对象三者职责分离，Handler 可叠加任意横切逻辑。

### 🧑‍💻 程序员视角
- 实践惯例：把 Handler 写成「可复用拦截器」，通过构造器注入 target 与多个 Advice 列表，
  实现「一个 Handler 串起多类通知」（`ex04`/`ex11` 的多拦截器责任链即此思路）。
- 风险：`invoke` 内若对**所有方法**（含 `hashCode`/`equals`/`toString`）都做重逻辑，
  可能引发死循环或语义偏差；需要时要按方法名过滤或特殊处理。
- 自调用陷阱（重点）：Handler 里调 `method.invoke(target, ...)`，**target 是原始对象**，
  若业务方法内部又调了同对象的其它被代理方法，不会再次进 Handler → 通知丢失（见 ex09）。

### 🎓 博士生视角
- Handler 把「横切逻辑」与「目标调用」解耦：横切逻辑在 `invoke` 体内、目标调用是一行反射。
  这种「中央拦截点」结构正是 AOP 代理范式的统一形态，CGLIB/AspectJ 代理在概念上等价
  （只是把 `invoke` 编译进了子类重写方法里）。
- 反射调用 `method.invoke(target, args)` 的参数必须是 `Object[]`，基本类型会被自动装箱；
  返回值若是基本类型会被自动拆箱——注意 `null` 返回值与 `void` 方法的返回约定
  （`void` 方法 `invoke` 返回 `null`）。

### 📚 考研者视角（面试笔试考点）
- 标准定义：`InvocationHandler.invoke(Object proxy, Method method, Object[] args)` 三个参数含义：
  `proxy` 是代理对象本身（不是 target！）、`method` 是被调接口方法、`args` 是实参数组。
- 命题角度：常问「`invoke` 的第一个参数是 target 吗？」——**不是**，是代理对象，
  拿它做 `==` 比较或递归调自己都会出错（与 `target` 永不相等，见 ex08）。
- 易错：手写代理时若在 Handler 里用 `proxy` 而非 `target` 去调方法，会无限递归进 `invoke`。

### 三视角小结

| 主题 | 程序员视角 | 博士生视角 | 考研者视角 |
|---|---|---|---|
| JDK 代理机制与通知 | 无侵入增强、反射性能、cause 取异常 | $Proxy 字节码/单继承限制 | 只能代理接口 + InvocationTargetException |
| Handler 与反射委派 | 可复用拦截器/自调用陷阱 | 中央拦截点等价 AOP 范式 | proxy≠target、void 返回 null |
