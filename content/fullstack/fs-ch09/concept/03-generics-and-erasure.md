# 泛型、条件类型与它们的运行时代价

泛型让「同一段逻辑适配不同类型」不必靠复制粘贴。最朴素的用法：

```ts
function first<T>(arr: readonly T[]): T | undefined {
  return arr[0];
}

const n = first([1, 2, 3]);      // number | undefined
const s = first(["a", "b"]);     // string | undefined
```

真正让 TS 泛型区别于 Java 泛型的是**它能在类型层面做运算**。条件类型 + 映射类型可以
从已有类型推导出新类型，而不必手写：

```ts
// 把对象所有字段变成可选（这就是内置的 Partial<T>）
type MyPartial<T> = { [K in keyof T]?: T[K] };

// 条件类型：只把函数类型的返回值取出来
type ReturnOf<T> = T extends (...args: never[]) => infer R ? R : never;

type A = ReturnOf<() => string>;   // string
```

这类工具类型是在**编译期**完成的，产物里一行都不剩。所以：

```ts
function identity<T>(x: T): T { return x; }
console.log(identity<string>("hi"));   // 运行时看不到任何 <string>
```

```text
泛型只在编译期存在，运行时全部擦除
    function id<T>(x: T): T   ->   编译后 function id(x)
    -> 不能 new T()、不能 T instanceof、不能读 T 的静态成员
    -> 想在运行时拿到类型，必须显式传值（class 引用或 schema）

条件类型与分布式：
    T extends U ? X : Y
    对裸类型参数 T 做联合分发：('a'|'b') extends string ? X : Y 会逐成员分发再合并

常用工具类型的本质：
    Partial<T>    { [K in keyof T]?: T[K] }
    Record<K,V>   { [P in K]: V }
    ReturnType<F> F extends (...a: any) => infer R ? R : never

    infer = 「在类型里捕获一个未知类型」，是 ReturnType / Awaited 的基石
```

## 擦除（erasure）意味着什么

类型在运行时不存在，因此：

1. **不能 `x instanceof T`**（T 是泛型参数）——没有可比较的运行时值。要判断就得传入构造函数：
   `function isInstance<T>(x: unknown, ctor: new () => T): x is T`。
2. **不能用类型做重载分派**——`f(x: string)` 与 `f(x: number)` 编译后是同一个函数，
   想按类型分派必须自己在运行时判断。
3. **不能校验外部数据**——`JSON.parse` 返回 `any`，赋给业务类型**不会**被检查。
   这是 TS 项目最常见的严重漏洞：类型看着对，运行时全是 undefined。

## 泛型不是越抽象越好

`function pick<T, K extends keyof T>(o: T, keys: K[]): Pick<T, K>` 这种签名很好，
但调用方 `pick(data, ["a", "b"])` 写错字段名会报错——这是收益。反过来，
把 `T` 一路往下传五层、每层都加 `extends` 约束，会让类型错误信息变成一屏天书。
工程判据：**泛型参数不超过三个；类型错误信息读不懂时，先简化签名而不是加约束**。

## 三视角解析

### 🧑‍💻 程序员视角
- 会写 `Partial` / `Pick` / `Omit` / `Record` 就够应付 90% 业务。自己从零写条件类型前，先去 `lib.es5.d.ts` 看内置实现，多半已经有人写好了。
- 边界（API 响应、配置、消息）一律 schema 校验。内部函数之间可以放心用泛型，因为调用方是同一个人写的代码；边界不可信。
- `extends` 在泛型里是「约束」，在条件类型里是「判断」。同一个词两种角色，读签名时要分清位置：`<T extends X>` 是约束，`T extends X ? A : B` 是判断。

### 🎓 博士生视角
- 擦除的直接后果是「类型系统与运行时语义脱钩」，这决定了 TS 无法提供健全性（soundness）保证——`as` 断言、`any`、索引签名都能绕过检查。TS 明确承认自己是「gradually typed / unsound」的，这是设计取舍不是缺陷。
- 与 Java 泛型擦除的差别：Java 擦除后仍有 `Class<?>` 与反射，能在运行时拿到部分类型信息（也因此有 type erasure 带来的 `new T()` 不可能问题）；TS 连这层都没有，类型完全不进入产物。
- 条件类型 + `infer` 让 TS 具备了轻量的类型级计算能力，理论上可编码 Peano 数做类型级运算。这类「类型体操」在多数组件库里用于推导 API 签名（如 tRPC 的端到端类型），是工程价值，不是炫技。

### 📚 考研者视角
- 与 408/C++ 模板对照：C++ 模板是**单态化**（每个类型实例生成一份代码），Java 与 TS 是**擦除**（一份代码适配所有类型）。代价与收益正好相反：单态化运行时快、二进制大；擦除体积小、有装箱/无运行时类型。
- 常考辨析：C++ `template` 与 Java 泛型的实现差异，是考研与面试的双高频题。
- 记忆锚点：**C++ 模板单态化生成多份代码；Java/TS 擦除共用一份代码**。
