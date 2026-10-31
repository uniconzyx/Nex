# 结构类型：形状对了就是对的

TypeScript 判断「A 能不能当 B 用」，比的是**成员形状**，不是「A 是否声明继承 B」。
这叫 structural typing（结构类型）；Java/C#/C++ 用的是 nominal typing（名义类型），比的是类型名。

```ts
interface Point { x: number; y: number }

const p = { x: 1, y: 2, label: "origin" };   // 多了一个 label
const q: Point = p;                           // ✓ 合法：多了不报错
// p.label 在这里仍然可访问，q.label 不行 —— 类型是从「接收方视角」看的
```

反过来，**少一个成员就不行**：

```ts
const r = { x: 1 };
const s: Point = r;   // ✗ Property 'y' is missing in type '{ x: number; }'
```

## 为什么这样设计

JS 是鸭子类型（duck typing）语言：运行时只看对象有没有那个方法/属性，从不看它是谁 new 出来的。
TypeScript 想在不改运行时语义的前提下加类型，就只能让类型系统服从同一套判据——
否则「明明能跑」的代码会被编译器拦住。

代价是两个经典坑：

1. **同一个结构在不同领域含义不同**。`{ id: string }` 既可能指用户也可能指订单，
   结构类型认为二者可以互相赋值。这需要「品牌类型」（branded type）来人为打标记：

```ts
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };
// 现在 string 不能直接当 UserId，必须显式断言，误传在编译期就被拦下
```

2. **过宽的类型会静默通过**。`{ x: 1, y: 2, z: 3 }` 能赋给 `Point`，
   但把它再往下传时，`z` 就已经丢了（作为参数传入函数时会发生 excess property check 之外的丢失）。

## 一条实用判据

接口描述「这个对象必须具备什么」，而不是「这个对象只能是什么」。
需要「只能是什么」时，用品牌类型或可辨识联合（discriminated union），不要指望 interface 拦住。

## 多余属性检查：为什么有时多也不行

上面说「多了不报错」，但有个例外。**直接写字面量**时，编译器会额外做一次
excess property check（多余属性检查），把「明显写错」的字段当成笔误拦下来：

```ts
interface Point { x: number; y: number }

const a: Point = { x: 1, y: 2, z: 3 };
// ✗ Object literal may only specify known properties, and 'z' does not exist in type 'Point'

const tmp = { x: 1, y: 2, z: 3 };
const b: Point = tmp;   // ✓ 先过一层变量就不报了
```

同一份数据，写两行就报错，先存变量就放行。这不是编译器在闹脾气，而是刻意的设计取舍：

- **字面量**是「就地新建」的值，编译器有充分理由相信 `z` 是手误（`y` 打成 `z`），
  报错成本低、收益高。
- **变量**是「别处已存在的值」，它可能有自己的完整类型，只是恰好能当 `Point` 用。
  此时拒绝反而会阻碍正常的类型复用——比如把一个完整 `Config` 对象传给只要 `{host, port}` 的函数。

理解了这一点，就能解释为什么「函数传参」和「变量赋值」行为不一致：

```ts
function connect(cfg: { host: string; port: number }) { /* ... */ }
connect({ host: "db", port: 5432, retry: 3 });   // ✗ 字面量，多属性报错
const cfg = { host: "db", port: 5432, retry: 3 };
connect(cfg);                                     // ✓ 变量，放行
```

**实践含义**：接口不要设计成「精确匹配全部字段」。如果某个接口会被用来接收上游完整对象，
它就该只声明自己真正用到的字段；反过来，如果你**希望**拦住多余字段，那就把参数直接写成
字面量的形状，而不是先存变量。

## 结构类型的三个边界反例

以下三类场景，结构类型会给出「能用但不对」的结果，需要人工加约束：

| 场景 | 结构类型怎么看 | 实际风险 | 应对 |
|---|---|---|---|
| 两个语义不同的 ID 都是 `string` | 可互相赋值 | 把 `orderId` 传给了要 `userId` 的接口，编译通过，运行查不到数据 | 品牌类型 |
| 空对象 `{}` | 是最宽的类型，任何非空值都能赋给它 | `Record<string, never>` 误当「空配置」用 | 用 `Record<never, never>` 或显式联合 |
| 可选字段全缺的接口 | `{ id?: string }` 与 `{}` 兼容 | 层层透传后拿到 `undefined` | 校验放在边界，而不是靠类型 |

第一类最值得展开。品牌类型不是给值「打标签」，而是在编译期造出一个只能由构造函数产生的
新类型——这样「意外兼容」被切断，而运行时开销为零：

```ts
type Brand<T, B extends string> = T & { readonly __brand: B };
type UserId = Brand<string, "UserId">;

const asUserId = (raw: string) => raw as UserId;   // 唯一入口，可在此做格式校验
```

代价是：任何从 `string` 转成 `UserId` 的地方都要显式经过 `asUserId`。
这不是负担，而是**把「这里确实是一个合法用户 ID」这一判断集中到一处**。

## interface 与 type 怎么选

初学者常在这两者之间纠结。判据只有一条：**你要不要「后来往上面加东西」**。

- `interface` 支持声明合并（declaration merging），同名声明会自动合并。适合描述
  「这个模块对外暴露的形状」，第三方库扩展你类型时靠的就是这一条。
- `type` 能表达 interface 表达不了的形状：联合、交叉、条件类型、映射类型、模板字面量。
- 性能上，`interface` 的类型关系会被缓存，大项目里通常更快；`type` 每次都要重新计算。
  这个差异只在几万行级别的类型规模上才感觉得到，日常不必为此改动设计。

大多数情况下选 `interface` 描述对象形状、选 `type` 描述「别名与组合」，是阻力最小的默认。

## 三视角解析

### 🧑‍💻 程序员视角
- 函数参数一律写「需要什么」，不要写「是什么类」。写成 interface 之后，测试里造一个 `{ ... }` 字面量就能替身，不必构造真实对象。
- 看到 `as` 就要警觉：断言等于关掉检查。优先用类型守卫（type guard）把「判断」写进代码，让编译器自己收窄。
- 跨层传递的数据（API 响应、localStorage 读回）一律先过 schema 校验（Zod/Valibot）再赋成业务类型。类型在运行时不存在，这一步不能省。

### 🎓 博士生视角
- 结构类型与名义类型的取舍本质是「子类型关系由谁定义」：名义类型由声明者定义，结构类型由使用者定义。后者更开放，也更容易出现意外的兼容。
- 它与 Haskell 的 type class、Rust 的 trait 处于不同回答层面：Haskell 用类型类表达「具备某能力」，TS 的结构类型只是「形状匹配」，没有能力语义，也没有 coherence 检查。
- TypeScript 的类型是 erasure 语义——编译产物里没有任何类型信息。所以它不能提供运行时的安全性，只能提供「编译期能证明的部分」。这一点与 Java 的泛型擦除相似，但 TS 连泛型的运行时痕迹都不留。

### 📚 考研者视角
- 408 没有这一层，但可以借用「接口 vs 实现」的类比：结构类型相当于只约定接口，不约定继承关系。
- 面试常问「interface 和 type 的区别」——标准答案是：interface 可声明合并、可被继承扩展；type 能表达联合/交叉/条件类型，但不能合并。选择判据是「需不需要扩展」而非「哪个更新」。
- 记忆锚点：**结构类型比形状、名义类型比名字；类型只在编译期存在**。
