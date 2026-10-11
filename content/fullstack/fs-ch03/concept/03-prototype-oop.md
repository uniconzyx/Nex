# 03 · 原型链、class 语法糖与继承

## 一、原型链：JavaScript 的「类」真相

JavaScript 的对象**没有真正的类**（ES6 `class` 只是语法糖）。每个对象都有一个内部槽 `[[Prototype]]`（可通过 `Object.getPrototypeOf(obj)` 读取，旧写法 `obj.__proto__`），指向它的**原型对象**。

属性访问 `obj.x` 的查找过程：

1. 先看 `obj` 自身是否有自有属性（own property）；
2. 没有则沿 `[[Prototype]]` 向上查，直到 `null`（原型链顶端）；
3. 中途找到即返回，整条链路即**原型链（prototype chain）**。

**方法共享**靠原型：构造函数 `F` 的 `F.prototype` 是被 `new F()` 创建对象的原型，把所有实例方法放在 `F.prototype` 上即可共享，而非每实例一份。

## 二、继承：Object.create 与 class

- `Object.create(proto)`：直接以 `proto` 为原型创建一个新对象——最纯粹的「委托」式继承。
- `class Sub extends Base`：语法糖，底层仍是原型链；`Sub.prototype` 的 `[[Prototype]]` 指向 `Base.prototype`，且 `Sub` 自身通过 `super` 调用 `Base` 构造函数（先 `super()` 才能用 `this`）。
- `instanceof`：沿**左侧对象的原型链**查找是否能到达右侧构造函数的 `prototype`，即 `Sub.prototype.isPrototypeOf(obj)` 的变体。
- `hasOwnProperty`：仅判断**自有属性**，不含原型链上的；据此区分「自己的」和「继承来的」。

V8 视角：对象有一个 **隐藏类（shape / map）**，描述属性布局。同名属性按相同顺序添加的对象共享 shape，属性访问被编译成偏移量读取（接近 C++ 成员访问速度）；**动态增删属性或改顺序会「去优化」生成新 shape**，拖慢访问。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 共享方法一定放原型上（`class` 的方法默认就在原型），避免每个实例都拷贝一份函数，节省内存。
- 不要用 `__proto__` 在热路径上改原型（性能差且已不推荐）；要用 `Object.create` / `class`。
- `instanceof` 跨 realm（不同 iframe/窗口）会失效：用 `Array.isArray` / `Object.prototype.toString.call` 做类型判断更稳。
- 保持对象「形状稳定」：构造函数里一次性初始化所有字段、避免运行时随机加属性，能让 V8 持续走内联缓存（IC）快速路径。

### 🎓 博士生视角
- 原型链是「基于原型（prototype-based）」而非「基于类（class-based）」的继承模型：对象直接委托给另一个对象，而非实例化蓝图。
- 形式化：`obj.[[Get]](P)` = 若 `obj` 自有 `P` 返回之，否则 `obj.[[GetPrototypeOf]]().[[Get]](P)` 递归，直到 `null` 返回 `undefined`。
- `class` 不改变模型，只改变写法：`extends` 设置 `Sub.prototype.[[Prototype]] = Base.prototype`，`super` 解析为 `Base.prototype` 上的方法。
- shape 的本质是「隐藏类」：属性名与顺序构成 key，相同 key 的对象共享同一份描述符布局，V8 用其做 IC 缓存偏移量。

### 📚 考研者视角
- **笔面标准口径**：原型链的定义与查找过程；`prototype` 与 `__proto__`（或 `[[Prototype]]`）的区别——前者是构造函数的属性、后者是实例的内部原型。
- 高频题：手写 `new`（创建空对象→设原型→执行构造函数→返回）、手写 `instanceof`、手写继承。
- 易错：`Sub.prototype = Object.create(Base.prototype)` 后一定要补 `Sub.prototype.constructor = Sub`，否则 `sub.constructor` 会顺着原型链指到 `Base`。
- `hasOwnProperty` vs `in`：`in` 会查原型链，`hasOwnProperty` 不会。
