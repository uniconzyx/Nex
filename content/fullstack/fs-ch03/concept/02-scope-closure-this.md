# 02 · 作用域、闭包与 this 绑定

## 一、作用域、提升与 TDZ

JavaScript 采用**词法作用域（lexical scope）**：函数能访问哪些变量由「定义时的位置」决定，而非调用位置。

- `var`：**函数作用域** + **提升（hoisting）**。声明被提升到函数顶部并初始化为 `undefined`，所以「先使用后声明」读到的是 `undefined` 而非报错。
- `let/const`：**块级作用域** + 提升但**不初始化**，从块开始到声明语句之间存在**暂时性死区（TDZ）**，访问会抛 `ReferenceError`。`const` 还禁止重新赋值（但对象内部属性可变）。
- **闭包（closure）**：函数与其定义时所处的词法环境（变量绑定）绑定在一起。即使外层函数已返回，内层函数仍持有外层变量的引用。代价是外层变量无法被 GC，可能内存泄漏；收益是「私有状态 + 工厂函数」。

经典坑：循环里用 `var i` 注册回调，所有回调共享同一个 `i`，最终都打印循环终值；改用 `let`（每次迭代产生新绑定）即修复。

## 二、this 的五条绑定规则

`this` 不是一个固定值，而是在**每次函数调用时**根据调用点决定的：

1. **默认绑定**：独立函数调用（非严格）`this` 指向全局对象；严格模式（`'use strict'`）下为 `undefined`。
2. **隐式绑定**：`obj.fn()` 中 `this` 指向 `obj`（谁调用归谁）。注意把方法「裸传」（`const f = obj.fn; f()`）会丢失绑定。
3. **显式绑定**：`fn.call(obj, ...)` / `fn.apply(obj, [...])` / `fn.bind(obj)` 强行指定 `this`。
4. **new 绑定**：`new Fn()` 时 `this` 指向新创建的对象。
5. **箭头函数**：**没有自己的 `this`**，取定义时外层（词法）作用域的 `this`，且优先级最高、不可被以上规则改写。

优先级（非箭头）：`new` > 显式 `bind/call` > 隐式 > 默认。

---

## 可运行代码：TDZ 与 this 的五条规则

提升、死区、绑定优先级三件事都能在同一个脚本里看到差别：

```js
// ① var 提升：声明提了、赋值没提
console.log(typeof b);          // "undefined"（不报错）
var b = 2;

// ② let 的 TDZ：声明前访问直接抛错，不是 undefined
try {
  console.log(a);
} catch (e) {
  console.log(e.constructor.name, "-", e.message);   // ReferenceError - Cannot access 'a' before initialization
}
let a = 1;

// ③ this 的五条绑定规则，按优先级从低到高
const obj = { name: "obj", show() { return this.name; } };
console.log(obj.show());                              // "obj"   隐式绑定
const fn = obj.show;
console.log(fn());                                    // undefined 隐式丢失 → 默认绑定
console.log(fn.call({ name: "call" }));               // "call"  显式绑定
console.log(fn.bind({ name: "bind" })());             // "bind"  硬绑定，后续 call 也改不回
console.log(new (fn.bind(null))().name);              // undefined  new 优先于 bind
```

关键结论：`b` 打印 `undefined` 而不报错，`a` 直接抛 `ReferenceError`——**提升不是「提到顶部赋值」，
而是「声明与初始化分离」**，`var` 的初始化被设为 `undefined`，`let` 则留在 TDZ 里。
最后一行最能体现优先级：`bind` 通常不可覆盖，但 `new` 比它更高，`this` 仍指向新创建的对象。

## 三视角解析

### 🧑‍💻 程序员视角
- 工程中**优先用箭头函数**写回调，避免 `that = this` / `self = this` 的 hack；但对象方法需要自己的 `this` 时别用箭头。
- 循环注册事件/定时器：用 `let` 或 `bind` 固定索引，否则经典「全打印最后一项」bug。
- 闭包持有大对象会内存泄漏：SPA 卸载组件时记得解绑事件、清空引用。
- `this` 丢失常见于React：类方法作为回调要 `this.method = this.method.bind(this)` 或在构造函数里 `bind`，或用类字段箭头函数。

### 🎓 博士生视角
- 词法作用域的本质是「作用域链」：查找变量时从当前环境记录沿 outer 指针逐级上溯，直到全局环境。闭包就是把这条链「冻结」下来。
- TDZ 对应规范里的「LexicalBinding 在初始化前处于未初始化状态」，引擎用内部 slot 标记，访问即抛错——这是编译期就能决定的语义错误。
- 箭头函数的 `this` 取自「 enclosing lexical environment 的 ThisBinding」，因为箭头没有自己的 Environment Record 里的 ThisBinding 字段。

### 📚 考研者视角
- **笔面标准问法**：`var/let/const` 的差异（作用域、提升、TDZ、能否重复声明）；闭包的定义与用途；`this` 的四种（或五条）绑定规则。
- 易错口径：`var`「提升」常被说成「变量被移到顶部」，准确说法是「声明提升、初始化留在原地（得 undefined）」；`let/const` 是「提升但不初始化（TDZ）」。
- 闭包题几乎必出（如「实现私有变量」「实现 once / 防抖」）；`this` 题常给一串嵌套调用让人判输出。
- 箭头函数没有 `this/arguments` 也是高频考点。
