# 02 · 方法重写与多态：invokevirtual 的动态分派

## 一、理论根基：override 是运行期的行为替换

- **重写（override）**：子类提供与父类**相同签名**的方法实现，运行期根据对象的实际类型选择版本。它体现的是"同一消息，不同实现"——面向对象多态的核心。
- **重载（overload）**：同一类中同名但参数列表不同的多个方法，**编译期**就按实参静态类型选定，与运行期对象类型无关。二者最大区别：**overload 静态解析，override 动态分派**——这是面试高频陷阱。

## 二、实现机制：JVM 如何做动态分派

核心指令是 **`invokevirtual`**（实例方法调用）。以 `Animal a = new Dog(); a.speak();` 为例：

1. 编译器把 `a.speak()` 编译成 `invokevirtual Animal.speak`（仅记录"在 Animal 类型上找一个叫 speak 的方法"）。
2. **运行期**，JVM 从对象头的 **Klass Pointer** 取出对象真实类（`Dog`）。
3. 在 `Dog` 的 **vtable（方法表）** 中查找 `speak` 的槽位——由于 `Dog` 重写了 `speak`，该槽位指向 `Dog.speak` 而非 `Animal.speak`。
4. 执行 `Dog.speak`。

> 这就是"晚绑定（late binding）"的全部秘密：绑定发生在运行期，依据**接收者的实际类型**，而非变量声明的静态类型。C++ 的多态靠 vptr/vtable，Java 的 HotSpot 用 Klass 的 vtable，**机制同源**。

**静态绑定的反例**（不发生动态分派，编译/链接期就定死）：
- `invokestatic`：静态方法。
- `invokespecial`：私有方法、构造器、`super.xxx()` 显式父类调用。
- `final` 实例方法：因不可被重写，HotSpot 可将其"去虚拟化（devirtualize）"为直接调用甚至内联。

**字段不参与分派**：字段访问是 `getfield/putfield`，按**静态类型**解析，没有 vtable。所以"字段没有多态"——`Base b = new Derived(); b.field` 取的是 `Base.field`（见 `examples/ex07-field-no-polymorphism.json`）。这与方法重写形成鲜明对比。

> 想亲眼看到字节码差异？对 `examples/ex10-abstract-vs-interface.json` 的 `.class` 执行 `javap -c`，会看到抽象类方法走 `invokevirtual`、接口 `default` 方法走 `invokeinterface`（下一节详述）。

## 三、工程实践

- **一定写 `@Override`**：一旦签名写错（比如参数类型不符），编译器立刻报错，而不是默默变成重载。
- **模板方法模式**：父类定义 `final` 的算法骨架（调自己的抽象/可重写步骤），子类只填步骤——既复用流程又允许定制，且 `final` 防止子类破坏骨架。
- **对扩展开放、对修改封闭**：新增子类即可新增行为，调用方用父类类型统一处理（见 `examples/ex12-polymorphic-array.json`）。

## 四、边界与陷阱

1. **override ≠ overload**：`void f(int)` 与 `void f(double)` 是重载，编译期定；`int f()` 与 `String f()` 在父子类间同名同参才是重写。写错极易"本想重写却成了重载 + 隐藏"。
2. **字段无多态**：子类同名字段是隐藏，父类引用永远看到父类字段；想要行为多态请用方法。
3. **重写不能降低访问权限**：父类 `public` 方法子类写成 `protected` 会编译失败。原因：LSP 要求子类可被当父类用，若缩小可见性，父类能调用之处子类反而不能——破坏契约。
4. **"两同两小一大"约束**：方法签名相同；返回类型可协变缩小（子类返回子类类型）；抛出的受检异常不大于父类；访问权限不小于父类。
5. **构造器里调可重写方法**：执行时 `this` 已动态指向子类，会调到子类覆写版，但**子类字段尚未初始化**（此时还是默认值），读到 0/null——隐蔽 bug（见 `examples/ex01` 反向思考：super 构造时子类字段未就绪）。

## 五、可运行代码

见 `examples/ex03-polymorphism-dispatch.json`（父类引用调子类实现）、`examples/ex07-field-no-polymorphism.json`（字段无多态）、`examples/ex08-override-contract.json`（协变返回 + 访问权限约束）、`examples/ex12-polymorphic-array.json`（多态数组统一处理）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **`@Override` 一定要写**：它让编译器检查签名是否真的重写了父类方法，能挡掉大量「以为重写了其实没有」的 bug。
- `static` / `private` / `final` 方法**不参与动态分派**（静态绑定），别指望它们表现出多态。
- 有性能疑虑时先测量：现代 JVM 对单态/双态调用点会做**内联缓存**，多态开销通常可以忽略。

### 🎓 博士生视角
- 实例方法的调用在字节码里是 **`invokevirtual`**：JVM 通过对象的**方法表（vtable）**按方法索引做动态分派；接口调用是 **`invokeinterface`**（通过 itable，且需要检查接收者是否实现该接口，历史上比 invokevirtual 慢）。
- 另外三种调用指令正是「静态绑定」的体现：`invokespecial`（构造器、私有方法、`super` 调用）、`invokestatic`（静态方法）、`invokedynamic`（lambda/字符串拼接等引导方法）。
- JIT 会在调用点记录**类型画像**并做内联缓存（单态直连、双态比较、多态查表）——所以「虚调用一定慢」是过时结论。
- 与 C++ 虚函数的对照：C++ 每个对象存 vptr 指向 vtable，Java 把 vtable 放在**类元数据**里（对象头存 Klass Pointer），这让每个对象少一个指针的开销。

### 📚 考研者视角
- **408 计组交叉**：**间接跳转/地址重定位**、指令流水线中的分支预测（多态调用点正是分支预测的难点）。
- 与 C++ 虚函数表对比是经典延伸题：「多态的底层实现是什么」。
- 记忆锚点：**`invokevirtual` 走 vtable、`invokeinterface` 走 itable、其余是静态绑定**；**字段没有多态**。
