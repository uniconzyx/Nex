# 类型收窄与穷尽性检查

一个变量的类型可以随代码路径变化，这叫收窄（narrowing）。收窄不是注解出来的，是编译器
顺着控制流**推**出来的：

```ts
function area(shape: Shape): number {
  switch (shape.kind) {
    case "circle":    return Math.PI * shape.r ** 2;   // 这里 shape 是 Circle
    case "square":    return shape.side ** 2;          // 这里 shape 是 Square
    default:
      const never_: never = shape;   // 如果漏了一种，这行编译报错
      throw new Error(`未处理的形状: ${JSON.stringify(never_)}`);
  }
}
```

`const never_: never = shape` 是穷尽性检查的惯用写法：当所有分支都被覆盖，`shape` 的类型是
`never`，赋值合法；一旦以后新增了 `Triangle` 而忘了加分支，这里立刻报错。
**这是把「以后有人改代码」这件事也纳入类型系统。**

## 收窄的几种来源

| 手段 | 例子 | 编译器的判断依据 |
|---|---|---|
| `typeof` | `typeof v === "string"` | 原始类型可直接收窄 |
| 字面量判别 | `shape.kind === "circle"` | 可辨识联合（discriminant） |
| `in` 运算符 | `"r" in shape` | 成员存在性 |
| `instanceof` | `err instanceof TypeError` | 原型链（仅对 class 有效） |
| 自定义守卫 | `function isUser(x): x is User` | 你自己写的 boolean，编译器选择相信 |
| 真值判断 | `if (v)` | 排除了 `null`/`undefined`/`0`/`""` |

自定义守卫是唯一「编译器无条件相信你」的一条。写错守卫比不写更危险：

```ts
// 危险：只要非空就返回 true，但 null 也会被 typeof 判成 "object"
function isUser(x: unknown): x is User {
  return typeof x === "object" && x !== null;
}
```

正确的做法是**校验每一个必需字段**，或者直接用 Zod 生成守卫：

```ts
const User = z.object({ id: z.string(), name: z.string() });
type User = z.infer<typeof User>;          // 类型从 schema 推出来，不会两处漂移
const isUser = (x: unknown): x is User => User.safeParse(x).success;
```

## 为什么 `any` 是逃生舱而不是工具

`any` 会让类型检查**整段失效**，而且会传染：一个 `any` 传给一个函数，函数返回值也可能退化成 `any`。
需要「暂时不知道类型」时用 `unknown`——它同样能接任何值，但**不能直接使用**，必须先收窄。
这一字之差就是「关掉检查」和「推迟判断」的区别。

### 收窄会在函数边界处失效

收窄不是「赋值那一刻的快照」，而是编译器沿着控制流持续维护的判断。它失效的真实条件比多数人以为的窄——
**不是「用了 `let` 就失效」，而是「这个绑定在某处被重新赋值」**。

下面四种写法，用 `tsc --strict` 实测（TypeScript 5.9）：

```ts
declare const maybeUser: User | null;

// A：let + 回调 —— 不报错，收窄保持
function a() {
  if (!maybeUser) return;
  let u = maybeUser;
  setTimeout(() => { u.name; }, 1);
}

// B：形参 + 转存 const —— 不报错
function b(user: User | null) {
  if (!user) return;
  const u = user;
  setTimeout(() => { u.name; }, 1);
}

// C：同一个变量在闭包里被重新赋值 —— 报错 TS18047
function c() {
  let user: User | null = maybeUser;
  if (!user) return;
  const f = () => { user = null; };
  setTimeout(() => { user.name; }, 1);   // ✗ 'user' is possibly 'null'
  return f;
}
```

实测结果：A、B 都通过，只有 C 报 `TS18047`。所以判据是：

> **绑定被重新赋值（无论在何处）→ 收窄在引用点失效；只读绑定 → 收窄一直有效。**

这个结论比「`let` 会丢收窄」更准确，也更有用：它意味着你可以放心用 `let`，
只要不在闭包里给它重赋值，就不需要为了类型安全而改成 `const`——改成 `const` 的价值在「防止自己犯错」，不在「编译器要求」。

第二条推论更值得记住：**收窄结论不能跨函数边界传递**。

```ts
function needUser(u: User) { return u.name; }

function process(user: User | null) {
  if (!user) return;
  needUser(user);   // ✓ 调用点已收窄，传参没问题
}
```

传参这一步没问题，但请注意：`needUser` 内部看到的仍是**形参声明的类型**。
所以形参要写「它真正需要的最小形状」——写成 `User | null`，等于要求每个调用点都重新收窄一次，
而这个函数本不需要 `null`。

### 一个真实的失效陷阱：解构之后

```ts
function handle(opts: { user?: User; timeout?: number }) {
  const { user } = opts;
  if (!user) return;
  setTimeout(() => {
    user.name;      // ✓ 没问题，user 是 const 解构出来的只读绑定
  }, 1);
}
```

解构出来的绑定是 `const`，收窄保持。但如果写成 `const { user } = opts;` 之后又在别处
`user = otherUser`，就必须先声明成 `let`，那才会回到第 C 种情况。

结论可以压缩成一句：**看绑定会不会变，而不是看它是 `let` 还是 `const`。**

### 类型守卫的可靠性分级

不是所有收窄手段都同样可靠。可以按「编译器能否自行验证」分三级：

| 级别 | 手段 | 谁来保证正确 |
|---|---|---|
| 强 | `typeof`、`in`、`instanceof`、可辨识联合、`===` 字面量 | 编译器推导，不会错 |
| 中 | `Array.isArray`、`Number.isFinite` 等内置类型谓词 | 内置谓词的签名是可信的 |
| 弱 | 自定义 `x is T` 守卫 | **你自己**，编译器无条件相信 |

弱的这一级不是「不推荐」，而是「要特别小心」：写错守卫不会报错，只会让所有下游收窄建立在错误前提上。
可控的用法是把守卫写薄——守卫体内部用强手段组合判断，而不是随手 `return true`：

```ts
function isUser(x: unknown): x is User {
  return typeof x === "object" && x !== null
    && typeof (x as { id?: unknown }).id === "string"
    && typeof (x as { name?: unknown }).name === "string";
}
```

更彻底的方案是让 schema 生成守卫（`z.infer` + `safeParse`），把「类型」与「校验」变成同一份声明，
从根上消灭两者漂移。

## 三视角解析

### 🧑‍💻 程序员视角
- 把 `switch` 的 `default` 分支写成 `never` 断言，是成本最低的防御：新增分支忘了处理会在编译期炸，而不是在生产上返回 undefined。
- API 响应用 Zod 定义一次 schema，`z.infer` 出类型，校验和类型从此单一来源。手写 interface + 手写校验函数，两者迟早漂移。
- `catch (e)` 里 `e` 是 `unknown`（TS 4.4+ 默认行为），不要 `as any` 了事——先 `e instanceof Error` 收窄，否则 `.message` 取不到。

### 🎓 博士生视角
- 可辨识联合是「代数数据类型（ADT）」的工程近似：`kind` 扮演构造函数标签，`switch` 扮演模式匹配，`never` 检查扮演穷尽性证明。区别是 ADT 的穷尽性是类型系统强制的，TS 的靠一行断言近似。
- 收窄本质上是「控制流敏感的类型推导」（flow-sensitive typing），与 TypeScript 同时期的 Flow、以及 Python 的 mypy 都属这一类；它们都要在「推导精度」和「编译速度」之间做取舍，这是 TS 在大项目里偶发「明明收窄了却报错」的根因。
- 自定义类型守卫的 `x is T` 断言语义上是一个**不可验证的证明**——编译器不检查守卫体与 T 是否一致。这与 Rust 的 `From` 实现、Haskell 的 `unsafeCoerce` 都属于「把证明责任交给程序员」的设计，差别在后果严重程度。

### 📚 考研者视角
- 与 408 的「类型检查时机」对照：静态类型检查在编译期，动态类型检查在运行期。TS 两者都有——静态部分靠收窄，动态部分（外部输入）必须自己补。
- 常考辨析：`any` 与 `unknown` 的区别（前者跳过检查、后者要求先收窄）；`never` 与 `void` 的区别（前者表示「不存在返回值/不可达」，后者表示「返回 undefined」）。
- 记忆锚点：**`never` 是类型的空集，用它做穷尽性检查；`unknown` 是类型的安全顶，用它接外部输入**。
