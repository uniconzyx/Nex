# TypeScript 类型系统实战手记：凯喵的十二次「编译通过但运行炸」现场

> 这一篇来自凯喵给一个内部后台做类型迁移的经历。项目从 JavaScript 迁到 TypeScript，全量 `strict: true` 之后，编译通过了，测试也绿了，但线上依然出现了三类事故：接口字段改名导致某个页面白屏、一个 `as` 断言掩盖了 undefined、以及一个泛型工具类型在运行时完全不存在。这些都不是「类型写错」，而是「对类型系统的运行时机理解有偏差」。十二个现场，逐个拆。

## 开场：类型是编译期的，运行时什么都没有

这句话听着像废话，但它是这一篇所有坑的总根。TypeScript 的类型在编译后**全部擦除**，产物里只剩下 JavaScript。所以任何依赖类型的运行时判断都不会起作用，任何泛型的运行时行为都只能靠你自己传进去的实参。

理解这一点的直接推论是：类型系统的价值在于「在编译期拦住错误」，而不是「在运行时保证正确」。凡是编译期无法确定的东西——来自网络的 JSON、来自 localStorage 的字符串、来自第三方 SDK 的返回值——类型标注都只是你的一厢情愿，必须靠运行时校验来兜底。

### 现场一：结构化类型让「鸭子」混进来了

TypeScript 用的是结构化类型系统：只要形状匹配，就被认为是同一个类型，不管它叫什么名字。这与 Java/C# 的标称类型完全不同。

```typescript
interface Point { x: number; y: number; }
interface Vector { x: number; y: number; }

const p: Point = { x: 1, y: 2 };
const v: Vector = p;   // 完全合法：形状一样就是一样
```

好处是灵活，坏处是**你以为的类型隔离其实不存在**。凯喵遇到过一个真实事故：两个不同业务域的 id 都是 `string`，函数签名上一个收 `UserId` 一个收 `OrderId`，看起来有类型保护，实际互相传值编译器一声不吭。

解决办法只有一个：**用「品牌类型」（branded type）给基础类型加上不可伪造的标记**。

```typescript
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

const asUserId = (s: string): UserId => s as UserId;
// asUserId(orderId) 会报错
```

这个技巧在类型层面零成本（编译后都是 string），但它把「语义不同的同形类型」区分开了。凡是 id、金额、时间戳这类基础类型承载业务含义的场景，都值得加品牌。

### 现场二：多余属性检查只在字面量上生效

这是结构化类型的一个著名「不一致」：

```typescript
interface Config { host: string; port: number; }

const c1: Config = { host: "a", port: 1, extra: true };  // 报错：多余属性
const tmp = { host: "a", port: 1, extra: true };
const c2: Config = tmp;                                   // 不报错
```

原因是为了防止拼写错误，TS 对**直接赋值的对象字面量**做了额外的多余属性检查，但对变量赋值不做（因为变量可能是别处传来的，形状兼容就允许）。

凯喵的应对是：接口定义要精确，不要用 `[key: string]: any` 兜底；需要严格控制时用 `satisfies` 或者显式的构造函数。别指望编译器在所有地方都帮你查多余字段。

### 现场三：类型收窄只对联合类型有效

`typeof`、`instanceof`、`in`、字面量判断这些手段能让 TS 收窄类型，但前提是**被判断的值本身是联合类型**。如果类型是 `any` 或 `unknown`，收窄就无从谈起。

```typescript
function parse(input: unknown) {
  if (typeof input === "string") {
    return input.trim();        // 收窄为 string
  }
  if (Array.isArray(input)) {
    return input.length;        // 收窄为 any[]
  }
  throw new TypeError("unsupported");
}
```

注意这里用的是 `unknown` 而不是 `any`。`unknown` 是「我不知道是什么，用之前必须先查」，`any` 是「别管了随便用」。前者逼你做检查，后者让类型系统彻底失效。**外部输入一律用 `unknown`**，这是凯喵团队写进规范的一条。

### 现场四：可辨识联合是穷尽性检查的基础

要让 `switch` 自动做完备性检查，联合类型的每个成员必须有一个共同的、字面量类型的判别字段。

```typescript
type Shape =
  | { kind: "circle"; r: number }
  | { kind: "rect"; w: number; h: number };

function area(s: Shape): number {
  switch (s.kind) {
    case "circle": return Math.PI * s.r ** 2;
    case "rect": return s.w * s.h;
    default: {
      const never_: never = s;   // 新增成员时这行会报错
      throw new Error(`unhandled: ${JSON.stringify(never_)}`);
    }
  }
}
```

那个 `never` 赋值是精髓：当你往 `Shape` 里加了第三个成员却忘了处理，`s` 在 default 分支里的类型就不是 `never` 了，编译立刻失败。这把「漏处理一个分支」从运行时的静默错误变成了编译期的硬错误。

凯喵把这个模式用在了所有状态机、所有 API 响应、所有事件类型上。凡是「有几种情况」的地方，都该用可辨识联合。

### 现场五：as 断言是「我说了算」，不是「帮我检查」

`as` 的作用是告诉编译器「相信我，我知道它是什么」。它不做任何运行时检查，也不能把明显不兼容的类型转换过去（除非先 `as unknown as`）。

```typescript
const raw = localStorage.getItem("config");      // string | null
const cfg = JSON.parse(raw) as Config;           // 危险：raw 可能是 null
```

上面这行在 `raw` 为 `null` 时会抛 `SyntaxError`，而类型系统完全不知道。正确的写法是运行时校验：

```typescript
function isConfig(v: unknown): v is Config {
  return typeof v === "object" && v !== null
    && typeof (v as Config).host === "string";
}

const raw = localStorage.getItem("config");
const parsed: unknown = raw ? JSON.parse(raw) : null;
if (!isConfig(parsed)) throw new Error("bad config");
// 此处 parsed 已收窄为 Config
```

凯喵的规矩是：**`as` 只允许出现在两类地方**——已经做过运行时校验之后的收窄，以及测试代码里构造假数据。业务代码里出现 `as`，就要在 review 时解释清楚为什么安全。

### 现场六：泛型在运行时不存在

泛型是纯编译期概念，编译后完全擦除。所以你不能在运行时做 `if (x instanceof T)`，也不能 `new T()`。

```typescript
// 编译报错：'T' only refers to a type
function create<T>() { return new T(); }

// 正确：把构造器作为参数传进来
function create<T>(Ctor: new () => T): T { return new Ctor(); }
```

这条对写工具库的人尤其重要。凡是要在运行时用到类型信息的场景（反序列化、依赖注入、ORM 映射），都必须显式把「运行时能用的东西」——构造器、工厂函数、校验器、schema——作为参数传进去。类型参数本身传不过去。

凯喵见过一个 ORM 包装库试图用泛型自动推断表名，最后只能靠装饰器在运行时存元数据。这不是 TS 的缺陷，而是「类型擦除」这个设计选择的必然结果。

### 现场七：条件类型与 infer 是类型层面的 if

条件类型让类型可以「分支」，`infer` 让类型可以「解构」。这两个组合起来能写出非常强的工具类型。

```typescript
type ElementOf<T> = T extends (infer U)[] ? U : never;
type Awaited2<T> = T extends Promise<infer U> ? Awaited2<U> : T;

type X = ElementOf<string[]>;              // string
type Y = Awaited2<Promise<Promise<number>>>; // number
```

关键在于理解它的执行方式：条件类型对**联合类型是分配的**（distributive），`T extends U ? X : Y` 当 T 是联合时会逐个成员判断再合并。这个特性既是威力来源，也是坑的来源——如果你不想分配，要用 `[T] extends [U]` 包一层。

凯喵在写一个 API 响应类型工具时踩过这个坑：想让 `Result<T>` 在 T 是联合时保持整体，结果被自动拆成了多个分支。加上方括号就好了。

### 现场八：映射类型能改写整个类型的形状

映射类型遍历一个类型的所有键，生成新类型。`Partial`、`Required`、`Readonly`、`Pick`、`Omit` 全都是它的语法糖。

```typescript
type MyPartial<T> = { [K in keyof T]?: T[K] };
type Setters<T> = { [K in keyof T as `set${Capitalize<string & K>}`]: (v: T[K]) => void };

interface State { name: string; age: number; }
type StateSetters = Setters<State>;
// { setName: (v: string) => void; setAge: (v: number) => void }
```

`as` 子句（键重映射）是 TS 4.1 引入的，配合模板字面量类型可以自动生成一堆样板方法名。凯喵用它把「手写十个 setter」变成了一个类型定义，代码量少了七成。

代价是可读性：映射类型嵌套两层以上就很难看懂。团队规范里加了一条——**超过两层的类型体操必须写注释说明它产出的形状**。

### 现场九：interface 和 type 的选择不是风格问题

两者大部分场景可以互换，但有几处关键差异：

`interface` 可以被声明合并（同名 interface 自动合并），`type` 不行。这在扩展第三方库类型时是唯一手段。`interface` 能被 `extends`，`type` 要用交叉类型。`type` 能定义联合、元组、条件类型，`interface` 不能。

```typescript
// 扩展第三方库：只能靠 interface 合并
declare module "express" {
  interface Request { userId?: string; }
}
```

凯喵的选择标准：**描述对象形状用 interface，需要联合/条件/工具类型用 type**。别为了「统一」强行全用 type，会在需要 augmentation 的时候卡住。

### 现场十：any 会传染，unknown 不会

`any` 一旦进入表达式，整个表达式的结果都是 `any`，类型检查从此失效，而且它会顺着赋值、返回值一路扩散。凯喵见过一个 `JSON.parse` 的返回值被标成 `any`，然后它流经五个函数，最后整条链路的类型保护全部消失。

`unknown` 则是「安全的 any」：可以接收任何值，但不能直接使用，必须先收窄。

```typescript
const bad: any = JSON.parse("{}");
bad.foo.bar.baz();          // 编译通过，运行时炸

const good: unknown = JSON.parse("{}");
// good.foo                   // 编译报错：Object is of type 'unknown'
```

开启 `noImplicitAny` 是基础，但更重要的是**主动避免显式写 any**。真要「什么都接受」，用 `unknown`；真要「什么都返回」，定义准确的返回类型。凯喵的团队在 ESLint 里禁掉了显式 `any`，只在白名单文件里允许。

### 现场十一：strictNullChecks 关掉就等于放弃一半类型系统

`strictNullChecks: false` 时，`null` 和 `undefined` 可以赋给任何类型，于是「可能为空」这个信息彻底丢失，`?.` 和 `??` 也失去了意义。

这是老项目迁移时最常见的妥协：打开它会有几百个报错，于是先关掉。凯喵的建议是反过来——**新代码一律 strict，老代码用 `// @ts-strict-ignore` 逐文件豁免，然后按模块逐步清**。关掉全局开关，等于让所有新代码陪着老代码一起裸奔。

`strict: true` 打开的是全家桶：`strictNullChecks`、`strictFunctionTypes`、`strictBindCallApply`、`noImplicitThis`、`alwaysStrict`、`useUnknownInCatchVariables`。每一项都对应一类真实的 bug。

### 现场十二：类型检查通过 ≠ 运行时正确

最根本的一条。类型只在编译期存在，以下场景全部在类型系统之外：网络返回的 JSON、`localStorage` 里的字符串、URL 参数、第三方 SDK 的返回值、`JSON.parse` 的结果、以及任何跨进程边界的数据。

所以完整的防线是两层：**编译期靠类型拦住内部错误，运行时要靠 schema 校验拦住外部输入**。凯喵的团队用 zod 做边界校验，把「外部数据」和「内部数据」在类型上分开：

```typescript
import { z } from "zod";

const UserSchema = z.object({ id: z.string(), name: z.string() });
type User = z.infer<typeof UserSchema>;

function loadUser(json: unknown): User {
  return UserSchema.parse(json);   // 运行时校验 + 类型收窄一步到位
}
```

这个模式的价值在于：schema 是唯一真相，类型从 schema 推导出来，永远不会出现「类型和校验逻辑不一致」的问题。手写 interface 再加上手写校验函数，迟早会漂移。

## 三视角解析
### 🧑‍💻 程序员视角
TypeScript 是结构化类型：只要形状匹配就兼容，所以「鸭子」能混进来——要名义类型得用「品牌类型」（`string & { __brand: 'UserId' }`）。多余属性检查只在「对象字面量直接赋值」时生效，先赋给变量再传就不检查，这是「明明多写了一个字段却不报错」的原因。类型收窄只对联合类型有效，对 `any`/`unknown` 要先做类型守卫。可辨识联合（`kind` 字段）是穷尽性检查的基础，配 `never` 能在漏分支时编译报错。

### 🎓 博士生视角
TypeScript 的类型系统是「结构化 + 可擦除」：类型只在编译期存在，运行期全部消失，因此不能依赖类型做运行时校验（需 `zod`/`io-ts` 之类的运行时 schema）。类型运算（条件类型、映射类型、模板字面量类型）使其成为「图灵完备的类型级编程语言」，但也带来「类型体操」的可维护性问题。`strict` 系列开关（`strictNullChecks`、`noImplicitAny`）决定了类型系统的严格程度，新项目应全开。

### 📚 考研者视角
前端面试高频：
1. **`interface` 与 `type`**：前者可声明合并、适合对象；后者可联合/交叉/条件类型。
2. **泛型约束**：`extends`、`keyof`、`infer` 的用法。
3. **类型守卫**：`typeof`、`instanceof`、自定义守卫（`x is T`）、可辨识联合。
4. **工具类型**：`Partial`、`Pick`、`Omit`、`Record`、`ReturnType` 的实现原理（映射类型）。

## 收尾：类型是文档，也是约束，但不是保证

凯喵最后想说：TypeScript 最强的地方不是「让你写得更快」，而是「让你在重构时敢动手」。改了字段名，编译器会把所有引用点列出来；改了函数签名，调用方全部标红。这种「改一处、编译器告诉你影响范围」的能力，是动态语言给不了的。

但它给的是一份**静态的、编译期的**保证。凡是跨越边界的、凡是来自运行时的、凡是通过 `as` 绕过去的，都不在这份保证里。把这两层分清楚，你就不会在类型全绿的时候误以为系统一定正确。

结构化类型带来灵活，也带来「同形即同类型」的隐患；泛型带来抽象，也在运行时彻底消失；收窄带来精确，但只对联合类型有效。理解每条规则背后的「为什么」，比记住语法重要得多——因为语法可以查，理解只能自己长出来。

```text
04-typescript-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 现场一：结构化类型让「鸭子」混进来了  (typescript)
    |
    v
  [02] 现场二：多余属性检查只在字面量上生效  (typescript)
    |
    v
  [03] 现场三：类型收窄只对联合类型有效  (typescript)
    |
    v
  [04] 现场四：可辨识联合是穷尽性检查的基础  (typescript)
    |
    v
  [05] 现场五：as 断言是「我说了算」，不是「帮我检查」  (typescript)
    |
    v
  [06] 现场六：泛型在运行时不存在  (typescript)
    |
    v
  [07] 现场七：条件类型与 infer 是类型层面的 if  (typescript)
    |
    v
  [08] 现场八：映射类型能改写整个类型的形状  (typescript)
    |
    v
  [... 其余 4 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
