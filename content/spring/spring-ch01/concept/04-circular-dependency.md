# 四、循环依赖与三级缓存

## 一、单例循环依赖与三级缓存

（中立陈述）单例 + **Setter/字段注入**的循环依赖（A 依赖 B，B 依赖 A）可以被 Spring 解决，核心是一套
**三级缓存**：① `singletonObjects`（一级，成品单例）② `earlySingletonObjects`（二级，早期暴露的
半成品引用）③ `singletonFactories`（三级，能产出早期引用的 ObjectFactory）。流程：实例化 A（仅
`new`，未填充）→ 把「A 的早期引用工厂」放进三级缓存 → 填充 A 时发现要 B → 创建 B 同样暴露早期引用 →
填充 B 时要 A → 从三级缓存拿到 A 的早期引用（并升到二级缓存）注入给 B → B 完成进入一级缓存 → 回到
A 把成品 B 注入。从而 A、B 都拿到彼此的引用，且最终都是成品。

### 🧑‍💻 程序员视角
- 工程建议：**不要依赖循环依赖「能跑」**——它是历史兼容特性，Spring 官方明确不鼓励。能解不代表该写；
  真正该做的是重构（抽接口 / 搬逻辑 / 用 `@Lazy` 延迟一方）。
- 踩坑：构造器注入一旦出现循环依赖，**三级缓存救不了**，启动直接抛
  `BeanCurrentlyInCreationException`；这是设计上的「早失败」，比运行期诡异 bug 好。
- 性能：三级缓存是三个 Map 的查找/插入，O(1)；`earlySingletonObjects` 只是「提前暴露引用」的过渡态，
  正常无循环时不参与，几乎无开销。

### 🎓 博士生视角
- 为什么需要「三级」而非「两级」：一级只放成品，二级放半成品引用，但有些 bean 的早期引用需要**经
  过处理**（如 AOP 代理）才能暴露——三级 `singletonFactories` 存的是「getEarlyBeanReference」
  工厂，能在真正需要早期引用时才决定是否返回原始对象还是代理，从而把「是否提前代理」的时机推迟到
  必要时刻，避免无循环时也提前生成代理。
- 机制：`getSingleton(beanName, allowEarlyReference)` 依次查一二三级；三级命中会调用
  `singletonFactory.getObject()` 得到早期引用并升入二级，随后清除三级，保证「同一 bean 早期引用唯一」。
- 设计动机：循环依赖本质是「对象图有环」，但对象可拆成「引用（地址）」与「完整状态」两阶段；先暴露
  地址、后填状态，环就能闭合。这是用「时间维度上的分阶段暴露」破解「空间上的环」。

### 📚 考研者视角
- 笔面标准问法：「Spring 怎么解决循环依赖？为什么用三级缓存而不是两级？」标准口径：**用三级缓存
  （singletonObjects 成品 / earlySingletonObjects 早期引用 / singletonFactories 早期引用工厂）
  解决单例 Setter 注入的循环依赖；三级缓存是为了把「是否需要提前 AOP 代理」推迟到真正需要早期引用时
  才决定，避免无循环时也提前生成代理。**
- 易错口径：① 说「三级缓存解决所有循环依赖」——**构造器注入、prototype 作用域的循环依赖都解决不了**；
  ② 说「二级就够了」——忽略了 AOP 代理的延迟暴露需求。
- 常见追问：「构造器循环依赖为什么解不了？」答：构造器注入在实例化阶段就要拿到完整依赖，而此时对方
  还没 `new` 出来，无法暴露早期引用，环在「地址生成前」就死锁。

## 二、prototype 循环依赖为何必然失败

（中立陈述）`prototype` 作用域的 bean **每次 `getBean` 都新建**，容器不缓存成品也不缓存早期引用
（一二级缓存对 prototype 无效）。因此 A 要 B、B 要 A 时，双方都无法拿到「已存在的早期引用」，
只能无限地 new 下去，Spring 直接抛 `BeanCurrentlyInCreationException`，且**没有缓存机制能救**。

### 🧑‍💻 程序员视角
- 工程惯例：prototype 本就为「每次新实例」，它和「共享单例引用」语义冲突，循环依赖在概念上就不该出现；
  若真需要，应改为单例 + 内部延迟获取，或抽一个被双方依赖的第三 bean。
- 踩坑：把本应是单例的协作类误配成 `prototype` 又彼此注入，启动即报错且难排查——先看 `@Scope`。
- 性能：prototype 无缓存，创建成本高（每次反射/构造 + 填充），高频调用应慎用。

### 🎓 博士生视角
- 机制：prototype 的创建走 `createBean` 但不走 `getSingleton` 的缓存登记，因而 `beforeSingletonCreation`
  的「正在创建」集合（singletonsCurrentlyInCreation）在递归注入时会检测到同一 beanName 再次进入，
  立刻抛 `BeanCurrentlyInCreationException`。
- 形式化：循环依赖可建模为图；单例靠「提前暴露顶点（地址）」允许环存在，prototype 不允许任何顶点被
  复用，于是含环的图无法拓扑构造——等价于「有环图无法被实例化顺序满足」。
- 设计动机：prototype 语义是「不共享」，而循环依赖要求「双方互相持有同一引用」，二者根本矛盾，框架
  选择直接失败而非制造语义歧义。

### 📚 考研者视角
- 笔面标准问法：「prototype 的循环依赖能解决吗？为什么？」标准口径：**不能。prototype 每次新建、
  不缓存早期引用，无法像单例那样提前暴露半成品引用，递归创建会触发 BeanCurrentlyInCreationException。**
- 易错口径：把「单例三级缓存能解」误推到「prototype 也能解」——作用域语义决定了 prototype 无解。
- 常见追问：「request / session 作用域的循环依赖呢？」答：它们基于单例的 scoped proxy（代理）间接
  持有，本质仍是单例代理在兜底，与普通 prototype 不同。
