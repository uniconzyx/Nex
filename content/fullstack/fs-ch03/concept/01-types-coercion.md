# 01 · 类型系统与相等性：原始类型、typeof 陷阱、== 与 Object.is

## 一、值与类型：原始类型 vs 引用类型

JavaScript 的值分两大类：

- **原始类型（primitive）**：`Undefined`、`Null`、`Boolean`、`Number`、`String`、`Symbol`、`BigInt` 共 7 种。它们**不可变、按值比较**，且通常分配在栈或 V8 的「值表示」里（小整数用 SMI 直接存，其他用堆上的指针 + 标签）。
- **引用类型（object）**：对象、数组、函数、日期等。变量持有的是**堆地址的引用**，按引用比较（两个不同对象即使字段相同也不 `===`）。

`typeof` 返回 7 种字符串之一：`undefined` / `object`（含 `null`！）/ `boolean` / `number` / `string` / `symbol` / `function`（函数这个 object 子类型的特例）/`bigint`。注意它没有 `array` 或 `null` 这类返回值——这是历史包袱。

## 二、相等性三兄弟：== 、=== 、Object.is

- `==`（抽象相等）：会先做**隐式类型转换（coercion）**再比较。规则见 ECMAScript「Abstract Equality Comparison」：数字与字符串比时字符串转数字；布尔转数字（true→1）；对象与原语比时对象走 `ToPrimitive`；`null == undefined` 为 true，但二者都不等于任何其他值。
- `===`（严格相等）：**不转换**，类型不同直接 false。工程默认用 `===`。
- `Object.is(a, b)`：与 `===` 几乎一致，但两个特例不同：`Object.is(NaN, NaN) === true`（因为 `NaN` 不等于自身），且 `Object.is(+0, -0) === false`（`+0 === -0` 却是 true）。

记住几个经典结果：`1 == '1'` → true；`[] == false` → true；`NaN == NaN` → false；`null == undefined` → true。`+0 === -0` → true 但 `Object.is(+0,-0)` → false。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 工程里**默认 `===`**，只在确实需要「空值合并 / 宽松判断」时用 `==`；更稳的是 `?.` 与 `??`。
- `typeof x === 'object'` 不能区分 `null` 与对象：判断真对象用 `x !== null && typeof x === 'object' && !Array.isArray(x)`。
- 判断 `NaN` 用 `Number.isNaN`（不会把 `'abc'` 这类非数字转成 NaN 后误判），不用全局 `isNaN`。
- 这些坑在上线事故里很常见：表单 `0 == ''` 为真导致「0 被当成空」、价格比较用 `==` 引入字符串拼接 bug。

### 🎓 博士生视角
- 原始类型的「不可变」是值语义：`let s='a'; s+='b'` 是生成新字符串，原值不变；这与引用类型形成对比。
- `==` 的 coercion 可由形式化规则描述：先把操作数按 `ToPrimitive`/`ToNumber`/`ToBoolean` 归约到可比较的规范类型再判等；`Object.is` 则是「同值相等（SameValue）」算法，比 `===`（SameValueZero 用于数组去重）多处理 `±0`。
- 规范层面，`typeof null === 'object'` 源于 JS 初版用 32 位 tag 表示值，null 的 tag 与对象相同（低位置 0），属于历史实现泄漏到语义。

### 📚 考研者视角
- **笔面标准口径**：7 种原始类型要能默写；`typeof` 的返回值集合与两个例外（`null`→object、函数→function）是高频考点。
- `==` vs `===`：答「`==` 会类型转换，`===` 不会」只是开头，要补一句「`Object.is` 额外区分 `NaN` 与 `±0`」。
- 易错：`NaN === NaN` 为 false；`null == undefined` 为 true 但 `null === undefined` 为 false——这两句几乎必考。
- `[1] == 1`、`'' == 0`、`'0' == false` 都为 true，是经典「隐式转换」陷阱题。
