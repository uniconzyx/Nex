# -*- coding: utf-8 -*-
"""新增章节的唯一手写源（2026-10-28 · 全栈双线 + 知识面缺口）。

为什么把数据单独放一个文件：13 章 × 7 类内容 = 近 200 个文件，如果内容散在
生成器里，改一句话要翻几千行。这里只放「写什么」，
`scripts/build_new_chapters.py` 负责「写成什么形状」。

字段规范（与既有章节逐字段对齐，见 content/java/java-ch02）：
  id / order / group / title / summary / prerequisites
  concept: [(slug, 标题, 正文 markdown)]       —— 正文必须含三视角，标记带 ZWJ
  pitfalls: [(标题, 错在哪, 为什么错, 怎么改)]
  exercises: [_choice(...) | _output(...) | _fix(...) | _coding(...)]
  interview: [(问, 答, [追问...])]
  project: (标题, 要求, [(任务, 验收)])
  sources: 该章可引用的已核验仓库（必须在 scripts/_link_cache.json 里）
"""

# ────────────────────────────────────────────────────────────── 三元视角标记
# 回归教训（2026-10-08）：早期脚本产出的 🧑‍💻 缺零宽连接符，validate_content
# 会把它记为「不规范」。这里统一用常量，不手敲。
P = "### 🧑‍💻 程序员视角"      # 🧑 U+1F9D1 + ZWJ U+200D + 💻 U+1F4BB
D = "### 🎓 博士生视角"
E = "### 📚 考研者视角"


def tri(points_p: list[str], points_d: list[str], points_e: list[str]) -> str:
    def render(head: str, pts: list[str]) -> str:
        return head + "\n" + "\n".join(f"- {x}" for x in pts)
    return "\n\n".join([
        "## 三视角解析",
        render(P, points_p),
        render(D, points_d),
        render(E, points_e),
    ])


def view(head: str, body: str) -> str:
    """六段式里嵌一个视角小节（bigdata 风格的 # 一级节用）。"""
    return f"{head}\n{body}"


# ══════════════════════════════════════════════════════════════
# 第一批：TypeScript（fs 线）+ Python 面向对象（py 缺口）
# ══════════════════════════════════════════════════════════════

CHAPTERS: list[dict] = []

# ─────────────────────────────── fs-ch09 · TypeScript 类型系统
CHAPTERS.append({
    "subject": "fullstack",
    "id": "fs-ch09",
    "order": 9,
    "group": "L2",
    "title": "TypeScript：结构化类型、泛型与类型收窄",
    "summary": (
        "TypeScript 的类型不是注释，是一套在编译期跑的约束求解。本章讲清：结构类型（structural typing）"
        "与名义类型的差别、`unknown` 与 `any` 的边界、联合类型的收窄（narrowing）与穷尽性检查、"
        "泛型与条件类型/映射类型如何把「运行时才发现的错」提前到编译期；以及最重要的一条——"
        "类型在运行时不存在（erasure），所以类型不能替代校验。"
    ),
    "prerequisites": ["fs-ch03"],
    "concept": [
        ("01-structural-typing.md", "结构类型：形状对了就是对的", r"""
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

""" + tri(
        [
            "函数参数一律写「需要什么」，不要写「是什么类」。写成 interface 之后，测试里造一个 `{ ... }` 字面量就能替身，不必构造真实对象。",
            "看到 `as` 就要警觉：断言等于关掉检查。优先用类型守卫（type guard）把「判断」写进代码，让编译器自己收窄。",
            "跨层传递的数据（API 响应、localStorage 读回）一律先过 schema 校验（Zod/Valibot）再赋成业务类型。类型在运行时不存在，这一步不能省。",
        ],
        [
            "结构类型与名义类型的取舍本质是「子类型关系由谁定义」：名义类型由声明者定义，结构类型由使用者定义。后者更开放，也更容易出现意外的兼容。",
            "它与 Haskell 的 type class、Rust 的 trait 处于不同回答层面：Haskell 用类型类表达「具备某能力」，TS 的结构类型只是「形状匹配」，没有能力语义，也没有 coherence 检查。",
            "TypeScript 的类型是 erasure 语义——编译产物里没有任何类型信息。所以它不能提供运行时的安全性，只能提供「编译期能证明的部分」。这一点与 Java 的泛型擦除相似，但 TS 连泛型的运行时痕迹都不留。",
        ],
        [
            "408 没有这一层，但可以借用「接口 vs 实现」的类比：结构类型相当于只约定接口，不约定继承关系。",
            "面试常问「interface 和 type 的区别」——标准答案是：interface 可声明合并、可被继承扩展；type 能表达联合/交叉/条件类型，但不能合并。选择判据是「需不需要扩展」而非「哪个更新」。",
            "记忆锚点：**结构类型比形状、名义类型比名字；类型只在编译期存在**。",
        ],
    )),

        ("02-narrowing-and-exhaustive.md", "类型收窄与穷尽性检查", r"""
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

""" + tri(
        [
            "把 `switch` 的 `default` 分支写成 `never` 断言，是成本最低的防御：新增分支忘了处理会在编译期炸，而不是在生产上返回 undefined。",
            "API 响应用 Zod 定义一次 schema，`z.infer` 出类型，校验和类型从此单一来源。手写 interface + 手写校验函数，两者迟早漂移。",
            "`catch (e)` 里 `e` 是 `unknown`（TS 4.4+ 默认行为），不要 `as any` 了事——先 `e instanceof Error` 收窄，否则 `.message` 取不到。",
        ],
        [
            "可辨识联合是「代数数据类型（ADT）」的工程近似：`kind` 扮演构造函数标签，`switch` 扮演模式匹配，`never` 检查扮演穷尽性证明。区别是 ADT 的穷尽性是类型系统强制的，TS 的靠一行断言近似。",
            "收窄本质上是「控制流敏感的类型推导」（flow-sensitive typing），与 TypeScript 同时期的 Flow、以及 Python 的 mypy 都属这一类；它们都要在「推导精度」和「编译速度」之间做取舍，这是 TS 在大项目里偶发「明明收窄了却报错」的根因。",
            "自定义类型守卫的 `x is T` 断言语义上是一个**不可验证的证明**——编译器不检查守卫体与 T 是否一致。这与 Rust 的 `From` 实现、Haskell 的 `unsafeCoerce` 都属于「把证明责任交给程序员」的设计，差别在后果严重程度。",
        ],
        [
            "与 408 的「类型检查时机」对照：静态类型检查在编译期，动态类型检查在运行期。TS 两者都有——静态部分靠收窄，动态部分（外部输入）必须自己补。",
            "常考辨析：`any` 与 `unknown` 的区别（前者跳过检查、后者要求先收窄）；`never` 与 `void` 的区别（前者表示「不存在返回值/不可达」，后者表示「返回 undefined」）。",
            "记忆锚点：**`never` 是类型的空集，用它做穷尽性检查；`unknown` 是类型的安全顶，用它接外部输入**。",
        ],
    )),

        ("03-generics-and-erasure.md", "泛型、条件类型与它们的运行时代价", r"""
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

""" + tri(
        [
            "会写 `Partial` / `Pick` / `Omit` / `Record` 就够应付 90% 业务。自己从零写条件类型前，先去 `lib.es5.d.ts` 看内置实现，多半已经有人写好了。",
            "边界（API 响应、配置、消息）一律 schema 校验。内部函数之间可以放心用泛型，因为调用方是同一个人写的代码；边界不可信。",
            "`extends` 在泛型里是「约束」，在条件类型里是「判断」。同一个词两种角色，读签名时要分清位置：`<T extends X>` 是约束，`T extends X ? A : B` 是判断。",
        ],
        [
            "擦除的直接后果是「类型系统与运行时语义脱钩」，这决定了 TS 无法提供健全性（soundness）保证——`as` 断言、`any`、索引签名都能绕过检查。TS 明确承认自己是「gradually typed / unsound」的，这是设计取舍不是缺陷。",
            "与 Java 泛型擦除的差别：Java 擦除后仍有 `Class<?>` 与反射，能在运行时拿到部分类型信息（也因此有 type erasure 带来的 `new T()` 不可能问题）；TS 连这层都没有，类型完全不进入产物。",
            "条件类型 + `infer` 让 TS 具备了轻量的类型级计算能力，理论上可编码 Peano 数做类型级运算。这类「类型体操」在多数组件库里用于推导 API 签名（如 tRPC 的端到端类型），是工程价值，不是炫技。",
        ],
        [
            "与 408/C++ 模板对照：C++ 模板是**单态化**（每个类型实例生成一份代码），Java 与 TS 是**擦除**（一份代码适配所有类型）。代价与收益正好相反：单态化运行时快、二进制大；擦除体积小、有装箱/无运行时类型。",
            "常考辨析：C++ `template` 与 Java 泛型的实现差异，是考研与面试的双高频题。",
            "记忆锚点：**C++ 模板单态化生成多份代码；Java/TS 擦除共用一份代码**。",
        ],
    )),
    ],
    "pitfalls": [
        (
            "把 `any` 当「先跑通再说」",
            "`function handler(req: any) { return req.body.user.name; }` —— 一路 any 到底，编译零报错。",
            "`any` 会让整条调用链的类型检查失效，而且会传染：返回 `any` 的函数赋给有类型的变量也不会报错。上线后 `req.body.user` 为 undefined 时，错误信息是 `Cannot read properties of undefined`，距离真正原因隔了五层。",
            "外部入口用 `unknown`，进门第一步收窄或 schema 校验。真的暂时不知道类型时，写 `unknown` 并加 `// TODO(type): 待接入 schema`，让 `unknown` 逼你在使用点做判断。",
        ),
        (
            "用 `as` 代替类型守卫",
            "`const user = data as User;` —— 把接口返回直接断言成业务类型。",
            "断言只在编译期有效，且**编译器不检查可行性**（只拦明显不可能的转换）。运行时 `data` 是什么就是什么，字段缺失时类型系统完全不知道。这类 bug 在联调期和数据格式变更后集中爆发。",
            "改成 `const user = UserSchema.parse(data)`（Zod）。校验失败会抛出带字段路径的错误，比五层之后的 undefined 好定位得多。",
        ),
        (
            "以为泛型能约束运行时",
            "`function isType<T>(x: unknown): x is T { return true; }` —— 想写一个通用类型判断。",
            "类型被擦除，`T` 在运行时不存在，函数体里无法知道 `T` 是什么，所以只能 `return true`（等于永远相信）。这种守卫会让所有下游收窄都建立在谎言上，比不写更糟。",
            "要么传入构造函数做 `instanceof`，要么传入 schema 做运行时校验。二者都需要把「类型」以值的形式带到运行时。",
        ),
        (
            "用 interface 期望拦住多余字段",
            "`interface User { id: string }` 然后期待 `{ id, isAdmin: true }` 赋值时报错。",
            "结构类型只看「有没有缺少必需成员」，多出来的成员默认允许（只有对象字面量直接赋值时才有 excess property check，一旦经过变量中转就失效）。",
            "需要严格排他时用可辨识联合 + `never` 检查，或在边界处用 schema 的 `.strict()`。不要指望 interface 做字段白名单。",
        ),
    ],
    "exercises": [
        {
            "type": "choice", "category": "基础题", "platform": "book", "difficulty": "easy",
            "title": "关于 TypeScript 的结构类型，正确的是",
            "content_md": "选择**正确**的描述。",
            "options": [
                {"key": "A", "text": "结构类型要求两个类型声明继承自同一个父类型才能互相赋值"},
                {"key": "B", "text": "结构类型只比较成员形状：多出成员合法，缺少必需成员不合法"},
                {"key": "C", "text": "结构类型在运行时也会检查对象形状，因此能替代数据校验"},
                {"key": "D", "text": "结构类型下 `{ id: string }` 与 `{ orderId: string }` 不能互相赋值"},
            ],
            "answer": {"correct": ["B"]},
            "explanation": "结构类型比形状不比名字：具备所需成员即可赋值，多出的成员不报错、缺少必需成员报错。类型在运行时被擦除，不做任何检查，因此不能替代数据校验。A 描述的是名义类型；D 恰好说反了——同形状不同类型在结构类型下可以互相赋值，这正是需要品牌类型的原因。",
            "tags": ["structural-typing", "interface"],
            "source": "book",
            "source_ref": "TypeScript Handbook · Type Compatibility",
        },
        {
            "type": "output", "category": "基础题", "platform": "book", "difficulty": "mid",
            "title": "读代码写输出（类型擦除）",
            "content_md": "```ts\ninterface Circle { kind: \"circle\"; r: number }\ninterface Square { kind: \"square\"; side: number }\ntype Shape = Circle | Square;\n\nfunction describe(s: Shape): string {\n  if (s.kind === \"circle\") return `circle:${typeof s.r}`;\n  return `square:${typeof s.side}`;\n}\n\nconsole.log(describe({ kind: \"circle\", r: 2 }));\nconsole.log(describe({ kind: \"square\", side: 3 }));\nconsole.log(typeof describe);\n```",
            "answer": {"output": "circle:number\nsquare:number\nfunction"},
            "explanation": "前三行与类型无关，只需注意两点：① `typeof s.r` 是 JS 的 typeof 运算符，返回运行时类型字符串 `number`，不是 TS 的类型查询；② 第三行 `typeof describe` 在函数声明之后返回 `function`。类型本身（Circle/Shape）编译后不存在，无法被 typeof 观察到。",
            "tags": ["erasure", "typeof", "narrowing"],
            "source": "book",
            "source_ref": "TypeScript Handbook · Everyday Types",
        },
        {
            "type": "fix", "category": "基础题", "platform": "book", "difficulty": "mid",
            "title": "改错：这个守卫为什么形同虚设",
            "content_md": "下面的类型守卫编译通过，但在运行时会把 `{ r: 1 }` 判成 `Circle`，导致 `area` 返回 `NaN`。指出问题并改正。\n\n```ts\nfunction isCircle(x: unknown): x is Circle {\n  return typeof x === \"object\" && x !== null;\n}\n\nfunction area(s: unknown): number {\n  if (isCircle(s)) return Math.PI * s.r ** 2;\n  throw new Error(\"not a circle\");\n}\n```",
            "answer": {"reference_code": "function isCircle(x: unknown): x is Circle {\n  return (\n    typeof x === \"object\" && x !== null &&\n    (x as { kind?: unknown }).kind === \"circle\" &&\n    typeof (x as { r?: unknown }).r === \"number\"\n  );\n}"},
            "explanation": "守卫只判断了「是对象且非 null」，任何对象都会通过，于是 `s.r` 取到 undefined，`undefined ** 2` 得到 NaN。类型守卫的正确性靠逐字段校验，而 `x is Circle` 只是向编译器声明「我保证」，编译器不会验证。修法：校验判别字段 `kind === \"circle\"` 与必需字段 `r` 的类型。生产代码更推荐用 Zod 从 schema 生成守卫，避免手写与类型漂移。",
            "tags": ["type-guard", "narrowing"],
            "source": "book",
            "source_ref": "TypeScript Handbook · Narrowing",
        },
        {
            "type": "choice", "category": "基础题", "platform": "book", "difficulty": "mid",
            "title": "`unknown` 与 `any` 的差别",
            "content_md": "关于 `unknown`，正确的是",
            "options": [
                {"key": "A", "text": "`unknown` 与 `any` 完全等价，只是写法不同"},
                {"key": "B", "text": "`unknown` 能接受任何值，但使用前必须先收窄，否则编译报错"},
                {"key": "C", "text": "`unknown` 只能用于函数参数，不能用于变量"},
                {"key": "D", "text": "`unknown` 会在运行时做类型检查，`any` 不会"},
            ],
            "answer": {"correct": ["B"]},
            "explanation": "`unknown` 是类型系统的「安全顶」：任何值都能赋给它，但它不能直接参与运算或取属性，必须先收窄（typeof / 守卫 / 断言）。`any` 则双向通行、跳过所有检查。二者在运行时都不存在，所以 D 错误。C 也错——`let x: unknown` 完全合法。",
            "tags": ["unknown", "any"],
            "source": "book",
            "source_ref": "TypeScript Handbook · Unknown",
        },
        {
            "type": "coding", "category": "算法题", "platform": "book", "difficulty": "hard",
            "title": "实现类型安全的 groupBy",
            "content_md": "实现一个泛型函数 `groupBy<T, K extends string>(items: T[], keyOf: (item: T) => K): Record<K, T[]>`：把数组按 `keyOf` 返回的键分组，返回一个 Partial 语义的字典（某键可能不存在）。要求：① 不使用 `any`；② 空数组返回空对象；③ 同一键的元素保持原有相对顺序。写出实现并在 main 中自测两组数据。",
            "answer": {"reference_code": "function groupBy<T, K extends string>(items: T[], keyOf: (item: T) => K): Partial<Record<K, T[]>> {\n  const out: Partial<Record<K, T[]>> = {};\n  for (const it of items) {\n    const k = keyOf(it);\n    (out[k] ??= []).push(it);\n  }\n  return out;\n}\n\nconst people = [{ name: \"a\", dept: \"eng\" }, { name: \"b\", dept: \"design\" }, { name: \"c\", dept: \"eng\" }];\nconsole.log(JSON.stringify(groupBy(people, (p) => p.dept as \"eng\" | \"design\")));"},
            "explanation": "要点有三：① 返回类型用 `Partial<Record<K, T[]>>` 而不是 `Record<K, T[]>`——后者声称每个键都存在，与事实不符，会在运行时误导调用方（取到 undefined 却以为有数组）；② `??=` 保证同键追加而不是覆盖，且顺序天然保持；③ 全程零 `any`，`keyOf` 的返回类型由泛型 `K` 约束，调用方传错字段名会在编译期报错。",
            "tags": ["generics", "record", "partial"],
            "source": "book",
            "source_ref": "TypeScript Handbook · Generics",
        },
        {
            "type": "coding", "category": "算法题", "platform": "book", "difficulty": "mid",
            "title": "用可辨识联合 + never 实现穷尽检查",
            "content_md": "定义三种形状：`Circle`（r）、`Square`（side）、`Triangle`（a、b、c）。用可辨识联合 `Shape` 表示，实现 `area(s: Shape): number`，并在 `default` 分支上用 `never` 做穷尽性检查。然后新增一种 `Rect`（w、h）但**故意不写**它的分支，用注释说明此时编译器的报错会出现在哪一行。",
            "answer": {"reference_code": "type Circle = { kind: \"circle\"; r: number };\ntype Square = { kind: \"square\"; side: number };\ntype Triangle = { kind: \"triangle\"; a: number; b: number; c: number };\ntype Shape = Circle | Square | Triangle;\n\nfunction area(s: Shape): number {\n  switch (s.kind) {\n    case \"circle\": return Math.PI * s.r ** 2;\n    case \"square\": return s.side ** 2;\n    case \"triangle\": {\n      const p = (s.a + s.b + s.c) / 2;\n      return Math.sqrt(p * (p - s.a) * (p - s.b) * (p - s.c));\n    }\n    default: {\n      const never_: never = s;\n      throw new Error(`未处理的形状: ${JSON.stringify(never_)}`);\n    }\n  }\n}\n\nconsole.log(area({ kind: \"square\", side: 3 }).toFixed(2)); // 9.00\nconsole.log(area({ kind: \"triangle\", a: 3, b: 4, c: 5 }).toFixed(2)); // 6.00"},
            "explanation": "三角形用海伦公式。穷尽检查的关键是 `const never_: never = s`：三个 case 全过后 `s` 的类型被收窄成 `never`，赋值成立；一旦给 `Shape` 加第四种 `Rect` 而 switch 没加分支，`s` 在 default 里将是 `Rect`，赋给 `never` 立刻报 `Type 'Rect' is not assignable to type 'never'`。报错位置就在这一行——这就是「以后有人改代码」也被纳入检查的意思。",
            "tags": ["discriminated-union", "never", "exhaustive"],
            "source": "book",
            "source_ref": "TypeScript Handbook · Narrowing",
        },
        {
            "type": "output", "category": "基础题", "platform": "book", "difficulty": "easy",
            "title": "读代码写输出（泛型擦除后的行为）",
            "content_md": "```ts\nfunction first<T>(arr: readonly T[]): T | undefined {\n  return arr[0];\n}\nconsole.log(first([10, 20]));\nconsole.log(first<string>([]));\nconsole.log(String(first([\"a\"])));\n```",
            "answer": {"output": "10\nundefined\na"},
            "explanation": "泛型参数 `<string>` 只在编译期存在，产物里 `first([])` 与 `first([10, 20])` 是同一个函数，都只是取下标 0。空数组取 `[0]` 得 `undefined`，`console.log(undefined)` 打印 `undefined`；第三行显式 `String()` 所以打印 `a` 而不是带引号的 `'a'`。",
            "tags": ["generics", "erasure"],
            "source": "book",
            "source_ref": "TypeScript Handbook · Generics",
        },
    ],
    "interview": [
        (
            "TypeScript 的类型在运行时存在吗？这对工程实践有什么影响？",
            "不存在，TS 是 erasure 语义：编译后类型信息全部删除，产物是普通 JavaScript。影响有三层：① 不能用类型做运行时判断（`instanceof T` 对泛型参数不成立，重载编译后是同一函数）；② 外部数据（API 响应、localStorage、URL 参数）必须在入口做运行时校验，类型系统帮不上忙；③ `as` 断言零成本也零保护，它只影响编译期。",
            ["既然类型不存在，`as` 到底做了什么？", "为什么 `JSON.parse` 返回 `any` 而不是 `unknown`？", "端到端类型安全（如 tRPC）是怎么绕过这个限制的？"],
        ),
        (
            "结构类型和名义类型各有什么问题？实际项目里怎么补救结构类型的不足？",
            "结构类型比形状，开放但会「意外的兼容」——`{ id: string }` 既能当 UserId 也能当 OrderId。名义类型比名字，安全但需要显式继承，跨库时常常被迫适配。补救结构类型的三个手段：① 品牌类型（`string & { __brand: 'UserId' }`）给同形状不同类型打标签；② 可辨识联合用 `kind` 字段区分语义；③ 边界处 schema 校验（Zod/Valibot），同时产出类型与运行时校验。",
            ["品牌类型在运行时有什么痕迹？", "为什么说 TS 是 unsound 的？举两个绕过检查的例子。", "Zod 的 `z.infer` 与手写 interface 相比解决了什么问题？"],
        ),
        (
            "`any`、`unknown`、`never` 三者分别用在什么场景？",
            "`any` 关闭检查，能双向赋值，是会传染的逃生舱——只应出现在从 JS 迁移的过渡代码里并加 TODO。`unknown` 是安全顶，任何值都能赋给它但不能直接使用，必须先收窄；外部输入一律用它。`never` 是空集，任何值都不能赋给它（除 never 本身），用途有三：表示不可达的 default 分支做穷尽检查、表示永不返回的函数（如 `throwError(): never`）、在条件类型里作过滤结果。",
            ["`never` 和 `void` 有什么区别？", "为什么 `never` 能赋值给所有类型，反过来不行？", "函数返回 `never` 和返回 `void` 在控制流分析上有什么不同？"],
        ),
        (
            "泛型约束（`extends`）和条件类型里的 `extends` 是同一个东西吗？",
            "不是，同一个关键字两种角色。出现在类型参数位置 `<T extends X>` 是**约束**：限制 T 必须是 X 的子类型，不满足直接报错。出现在类型表达式 `T extends X ? A : B` 是**判断**：在类型层面做条件分派，配合 `infer` 可以从输入类型里提取片段（如 `ReturnType`）。读签名时要先看位置再判断含义。",
            ["`infer` 能用在哪些位置？举一个从函数的参数类型提取的例子。", "分布条件类型（naked type parameter）为什么对联合类型会展开？", "`keyof` 与 `T[K]` 索引访问类型分别解决什么问题？"],
        ),
        (
            "大型项目里如何组织 TS 类型？什么该放全局，什么该就近定义？",
            "原则是「类型跟着使用者走，只在跨模块共享时才提升」：① 组件的 Props/State 就地定义在组件文件中，不放进全局 types 目录——否则会退化成一个什么都装的大杂烩；② 跨层契约（API DTO、领域实体）放 `types/` 或与 schema 同文件，且**由 schema 推导**而不是手写，保证单一来源；③ 第三方库缺失类型的补丁放 `types/*.d.ts` 并加注释说明来源；④ 禁止用全局 `declare global` 扩散，它会让依赖关系变成隐式的。",
            ["monorepo 里多个 package 共享类型，用 project references 还是发布一个 types 包？", "`paths` 别名与 `baseUrl` 对类型解析有什么影响？", "为什么说「由 schema 推导类型」比「手写类型 + 手写校验」更可靠？"],
        ),
    ],
    "project": (
        "把 fs-ch07 的项目改成 TypeScript：从 JS 迁移并加上端到端类型安全",
        """选一个此前用纯 JS 写的小项目（没有就做：任务清单 API + 前端页面），完成迁移：

1. 打开 `strict` 全家桶（`strict: true`、`noUncheckedIndexedAccess`、`exactOptionalPropertyTypes`），逐项修掉报错，不许用 `as any` 绕过；
2. 为所有 API 边界（请求体、响应、query 参数）写 Zod schema，类型由 `z.infer` 生成，删除手写 interface；
3. 前端调用后端时，响应先 `parse` 再用；`parse` 失败要给出可读的错误路径；
4. 挑两处真正需要穷尽性的地方（如状态机、消息类型），用可辨识联合 + `never` 做穷尽检查；
5. 用 `tsc --noEmit` 接入 CI，并在 README 里写下迁移前后各修掉了哪类真实 bug。""",
        [
            ("打开 strict 并把报错清零（记录每类报错的解法）",
             {"type": "test", "desc": "`tsc --noEmit` 零报错，且源码中 `as any` 出现次数为 0（除第三方声明补丁）"}),
            ("API 边界改为 Zod schema 驱动",
             {"type": "test", "desc": "所有请求/响应类型由 schema 推导；删掉重复的手写 interface；构造一个字段缺失的响应，确认能给出字段路径错误"}),
            ("接入可辨识联合做穷尽检查",
             {"type": "test", "desc": "新增一个状态/消息类型而忘记处理时，`tsc` 在 `never` 断言处报错"}),
            ("CI 接入类型检查",
             {"type": "test", "desc": "PR 上有独立的 typecheck 步骤；故意植入一个类型错误，确认 CI 变红"}),
        ],
    ),
    "sources": ["yangshun/front-end-interview-handbook", "Chalarangelo/30-seconds-of-code", "trekhleb/javascript-algorithms"],
})

# ─────────────────────────────── py-ch09 · Python 面向对象
CHAPTERS.append({
    "subject": "python",
    "id": "py-ch09",
    "order": 9,
    "group": "L3",
    "title": "面向对象：类、继承与魔术方法",
    "summary": (
        "Python 的类是「带描述符协议的名字空间」，不是 Java 那种编译期定型的东西。本章讲清："
        "实例字典与类字典的查找顺序、`__init__` 与 `__new__` 的分工、继承与方法解析顺序（MRO）与 `super()`、"
        "魔术方法如何让对象接入 Python 的语言协议（`__repr__`/`__eq__`/`__hash__`/`__len__`/`__iter__`），"
        "以及 `@property`、`@classmethod`、`@staticmethod` 三者的真实区别。"
    ),
    "prerequisites": ["py-ch02", "py-ch03"],
    "concept": [
        ("01-class-namespace-and-lookup.md", "类、实例与属性查找顺序", r"""
# 类、实例与属性查找顺序

Python 里「对象有哪些属性」不是编译期决定的，而是每次访问时**查一遍**：

    实例的 __dict__  →  类型（及其 MRO）的 __dict__  →  类型的父类 ...

```python
class Cat:
    sound = "meow"          # 存在 Cat.__dict__ 里

    def __init__(self, name):
        self.name = name    # 存在实例 __dict__ 里

c = Cat("mimi")
print(c.name)     # mimi        —— 实例字典找到
print(c.sound)    # meow        —— 实例字典没有，去类字典找
c.sound = "nya"   # 注意：这是给 *实例* 新建了一个 sound，不是改类属性
print(Cat.sound, c.sound)   # meow nya
```

最后两行是最常见的误解来源：`c.sound = ...` **不会**修改类属性，它在实例字典里新建了一项，
从此遮蔽（shadow）了类属性。想改类属性必须写 `Cat.sound = ...`。

## 可变类属性是共享的

```python
class Bad:
    tags = []                    # 类属性，所有实例共享同一个 list

a, b = Bad(), Bad()
a.tags.append("x")
print(b.tags)                    # ['x']  —— b 也被改了
```

这不是 bug，是「类属性只有一个」。需要每实例一份时，在 `__init__` 里赋值。

## `__init__` 不负责创建对象

很多人以为 `__init__` 是构造函数。实际分工是：

| 阶段 | 方法 | 职责 |
|---|---|---|
| 创建 | `__new__(cls, ...)` | 分配内存、返回实例（默认由 `object.__new__` 完成） |
| 初始化 | `__init__(self, ...)` | 往已存在的实例上挂属性 |

所以 `__init__` 必须返回 `None`，它的返回值会被丢弃。需要控制「是否真的创建对象」时才重写
`__new__`——典型场景是单例、不可变类型（`int`/`str`/`tuple` 的子类）、以及 `namedtuple` 风格的工厂。
日常写业务代码不需要碰 `__new__`。

""" + tri(
        [
            "类属性只放常量与不可变默认值（如 `MAX_RETRY = 3`）。凡是每实例可能不同的，一律在 `__init__` 里赋值——这条能消灭「为什么我的对象被别人的数据污染了」这一类 bug。",
            "`__slots__` 能去掉实例 `__dict__`、显著省内存（十万级对象时值得），代价是不能动态加属性、不能被 `__dict__` 反射。先测内存再决定，不要默认加。",
            "调试「属性到底从哪来」时用 `vars(obj)`、`vars(type(obj))`、`type(obj).__mro__` 三件套，比猜快得多。",
        ],
        [
            "属性查找是一个**协议**而非简单的字典链：数据描述符（定义了 `__set__` 的，如 `property`）优先级高于实例字典，非数据描述符（普通函数）低于实例字典。这条不对称规则正是「方法可以被实例属性遮蔽，property 不能被遮蔽」的原因。",
            "这套机制叫 descriptor protocol，是 Python 对象模型的地基：`property`、`classmethod`、`staticmethod`、函数本身全部是描述符。理解了描述符，`@property` 就不再是语法糖而是一个可解释的实现。",
            "与 Java 的根本差异：Java 的字段布局在编译期固定（对象头 + 固定偏移），Python 的对象是「字典 + 指向类的指针」。这决定了 Python 的属性访问慢一个量级，也决定了它可以在运行时给任意对象加属性。",
        ],
        [
            "与 408 的「对象在内存中的表示」对照：C++/Java 的对象是固定布局，字段访问是「基址 + 偏移」；Python 是「字典查键」。前者的空间与时间都可预测，后者灵活但慢。",
            "面试常问「类属性和实例属性的区别」：类属性存在类对象里、所有实例共享；给实例赋值只会创建同名实例属性并遮蔽类属性，不会改类属性。",
            "记忆锚点：**实例字典优先于类字典；可变类属性是所有实例共享的**。",
        ],
    )),

        ("02-inheritance-mro-super.md", "继承、MRO 与 super()", r"""
# 继承、MRO 与 super()

Python 支持多继承，这带来一个必须回答的问题：`obj.method()` 到底调哪一个？答案是沿
**方法解析顺序（MRO）** 找第一个。

```python
class A:
    def hello(self): return "A"
class B(A):
    def hello(self): return "B"
class C(A):
    def hello(self): return "C"
class D(B, C):
    pass

print(D().hello())      # B —— B 在 MRO 里排在 C 前面
print([c.__name__ for c in D.__mro__])   # ['D', 'B', 'C', 'A', 'object']
```

MRO 用的算法是 **C3 线性化**：保证「子类在父类之前」「同一父类的多个子类保持声明顺序」
「每个类只出现一次」。出现无法同时满足的情况时直接报 `TypeError`，而不是让你猜。

## `super()` 不是「父类」

这是最深的误解。`super()` 返回的是「MRO 上当前类的**下一个**类」，不一定是父类：

```python
class Base:
    def __init__(self):
        print("Base")
class A(Base):
    def __init__(self):
        print("A"); super().__init__()
class B(Base):
    def __init__(self):
        print("B"); super().__init__()
class C(A, B):
    def __init__(self):
        print("C"); super().__init__()

C()     # C → A → B → Base
```

在 `A.__init__` 里 `super()` 找到的是 **B**，不是 `Base`——因为它的查找起点是 A 在
`type(self).__mro__`（这里是 C 的 MRO）中的位置。这个「按实例的实际 MRO 走」的行为叫
协作式多继承（cooperative multiple inheritance）。

工程后果：**多继承链上的每个 `__init__` 都必须调用 `super().__init__()` 并接受 `**kwargs` 透传**，
否则链会断。标准库的 `collections.abc` 容器类、Django 的 mixin 全部遵守这条约定。

## 什么时候真的该用多继承

大多数情况下不该。Python 界的共识是：

- **mixin（能力混入）**：每个 mixin 只提供一小块正交能力（如 `JSONMixin` 提供 `to_json()`），
  且不定义 `__init__` 状态——这是多继承唯一被广泛认可的用法。
- **抽象基类（ABC）**：用 `abc.ABC` + `@abstractmethod` 声明接口，`isinstance` 检查会生效。
- **菱形继承的「数据」部分**：几乎总是该用组合（composition）。`has-a` 用组合，`is-a` 用继承，
  这条判据在 Python 里比其他语言更要紧，因为允许多继承会让错误更容易被发现得晚。

""" + tri(
        [
            "写 mixin 时**不要**有 `__init__` 状态，也不要假设自己的方法被谁调用。mixin 只承诺「我提供这些方法」，不承诺调用顺序。",
            "多继承链上的 `__init__` 统一写成 `def __init__(self, *args, **kwargs)` 再 `super().__init__(*args, **kwargs)`，否则协作链必断。",
            "`isinstance` 配合 ABC 比 `type(x) is T` 好：前者尊重子类与鸭子类型的注册（`register()`），后者在代理/装饰器场景下必然失败。",
        ],
        [
            "C3 线性化是为了同时满足「局部优先序」与「单调性」——父类的 MRO 必须在子类的 MRO 中保持相对顺序。Python 2.2 时期的旧式类用的是深度优先，导致菱形继承行为反直觉，C3 是那次的正式修复。",
            "`super()` 的零参数形式依赖编译器注入 `__class__` 闭包单元，这使它在运行时能知道「我是在哪个类里被调用的」。这也是为什么 `super()` 不能用在类外的普通函数里。",
            "把 mixin 与 Haskell 的 type class、Rust 的 trait 对比可见：后两者是「列出的能力由类型显式声明」，Python 的 mixin 是「谁在 MRO 上谁生效」，更隐式、更难静态检查（mypy 对 MRO 的推导有限）。",
        ],
        [
            "与 408 的「多继承二义性」对照：C++ 用虚继承解决菱形问题，Java 干脆禁止类多继承、只允许多实现接口。Python 选择全开放 + C3 线性化，代价是运行期才能确定行为。",
            "面试常问「Python 支持多继承吗？怎么解决菱形问题？」——答：支持；用 C3 线性化生成 MRO，冲突时报 TypeError，配合 `super()` 做协作式调用。",
            "记忆锚点：**MRO 是 C3 线性化；super() 找的是 MRO 上下一个，不是父类**。",
        ],
    )),

        ("03-dunder-protocols.md", "魔术方法：让对象接入语言协议", r"""
# 魔术方法：让对象接入语言协议

`__len__`、`__iter__`、`__eq__` 这些双下划线方法不是「特殊函数」，而是 Python 语言语法的
**钩子**。写对了，你的对象就能用在 `len()`、`for`、`==`、`in` 里；写错了，就会出现「看着对、
行为怪」的对象。

```python
class Playlist:
    def __init__(self, songs):
        self._songs = list(songs)

    def __len__(self):              # len(pl)
        return len(self._songs)

    def __getitem__(self, i):       # pl[0] / 切片 / for 循环（旧协议）
        return self._songs[i]

    def __iter__(self):             # for x in pl（新协议，优先于 __getitem__）
        return iter(self._songs)

    def __contains__(self, x):      # "x" in pl —— 不写的话会退化成 for 循环
        return x in self._songs

    def __repr__(self):             # 给开发者看，应可重建对象
        return f"Playlist({self._songs!r})"

    def __eq__(self, other):        # pl1 == pl2
        if not isinstance(other, Playlist):
            return NotImplemented
        return self._songs == other._songs

    def __hash__(self):             # 想放进 set / 当 dict 键才需要
        return hash(tuple(self._songs))
```

## 三个必须知道的规矩

**1. 定义 `__eq__` 会把 `__hash__` 置为 `None`。**
Python 认为「相等的对象应该 hash 相同」，你改了相等语义就默认你不能被 hash（否则会破坏 dict 的
不变式）。要可 hash 就显式实现，并且只 hash 不可变的部分。

**2. `__eq__` 遇到陌生类型要返回 `NotImplemented`，不要 `return False`。**
`NotImplemented` 是让 Python 去试对方的 `__eq__`（可能是更精确的实现）；`False` 会直接终止比较，
导致 `a == b` 为 False 而 `b == a` 为 True 这种不对称。

**3. `__repr__` 是给开发者，`__str__` 是给用户。**
只写一个时写 `__repr__`（`print()` 会自动回退到它）。`__repr__` 的目标是
`eval(repr(obj))` 能重建对象——这条判据能帮你避免写出 `<Playlist object at 0x...>` 这种毫无信息的东西。

## `@property` 与三种方法修饰符

```python
class Circle:
    def __init__(self, r):
        self._r = r

    @property
    def area(self):                 # 调用时不用写 ()：c.area
        return 3.14159 * self._r ** 2

    @area.setter
    def area(self, v):              # 赋值时校验：c.area = 10 会走这里
        raise AttributeError("area 是只读的")

    @classmethod
    def unit(cls):                  # 第一个参数是类，适合做工厂
        return cls(1.0)

    @staticmethod
    def is_valid(r):                # 不接收 self/cls，纯函数挂在类上
        return r > 0
```

判据：需要访问实例状态用普通方法；需要创建实例（工厂）或访问类属性用 `classmethod`；
与类型无关的纯工具函数用 `staticmethod`（很多场景直接写模块级函数更清楚）。

""" + tri(
        [
            "只写 `__repr__` 不写 `__str__` 是绝大多数场景的正确选择。`__repr__` 里用 `!r` 格式化字段（`f\"{self.name!r}\"`），这样字符串字段带引号，能一眼看出类型。",
            "自定义类要放进 `set` 或当 `dict` 键时，`__eq__` 与 `__hash__` 必须成对实现，且参与 hash 的字段必须不可变。用 `@dataclass(frozen=True)` 可以自动生成正确的这一对。",
            "需要「看起来像数字/容器/可调用」时优先用 `collections.abc` 的基类继承（如 `MutableSequence`），它会补齐 `__contains__`/`__reversed__` 等一大批方法，并让 `isinstance` 通过。",
        ],
        [
            "魔术方法是「语言协议」而非「命名约定」，因此它们由解释器在**类型上**查找，绕过实例字典——`obj.__len__ = lambda: 5` 不会让 `len(obj)` 返回 5。这是 CPython 的 special method lookup 特例。",
            "`__eq__` 与 `__hash__` 的耦合是「等价关系」的必然要求：hash 必须对相等元素给出相同值，因此一旦相等更「宽」（比较更多字段），hash 也必须更「窄」（只用不可变子集）——否则 dict 会找不到刚放进去的键。",
            "Python 的协议是隐式的（structural），没有显式 `implements` 声明；这与 Java interface、Go interface 的选择相反。收益是无需预先声明，代价是无法静态确认「这个类真的完整实现了序列协议」。",
        ],
        [
            "与 408 的「运算符重载」对照：C++ 通过 `operator+` 等实现，编译期决定；Python 通过 `__add__`，运行期按类型查找。两者都是「让自定义类型接入语言语法」，只是绑定时机不同。",
            "面试常问「`__new__` 和 `__init__` 的区别」「为什么定义了 `__eq__` 之后对象不能当 dict 键」——后者答：`__hash__` 被隐式置为 `None`。",
            "记忆锚点：**`__eq__` 与 `__hash__` 成对；`__repr__` 给开发者；魔术方法在类型上查找**。",
        ],
    )),
    ],
    "pitfalls": [
        (
            "可变默认参数 / 可变类属性",
            "`class Foo: items = []` 或 `def f(x, acc=[])`，然后往里 append。",
            "类属性与函数默认值都在**定义时只求值一次**，所有实例/所有调用共享同一个对象。表现出来就是「第二次调用时里面还有上次的数据」，而这在单元测试里常常因为用例顺序不同而时好时坏。",
            "类里改成在 `__init__` 中 `self.items = []`；函数里用 `def f(x, acc=None)` 再 `if acc is None: acc = []`。",
        ),
        (
            "`super()` 用错对象",
            "多继承链里写成 `Base.__init__(self)` 直接调父类，或者子类 `__init__` 忘了调 `super()`。",
            "直接点名父类会绕过 MRO，导致链上其他 mixin 的初始化被跳过；忘了调用则父类状态根本没初始化，属性访问时 AttributeError。在多继承里这两种错都不会在定义时报，只在运行时某个路径上炸。",
            "一律写 `super().__init__(*args, **kwargs)`，让 Python 按实际 MRO 走；每个参与协作的类都要接受并透传 `**kwargs`。",
        ),
        (
            "`__eq__` 返回 False 而不是 NotImplemented",
            "`def __eq__(self, other): return self.x == other.x`，没有先判断类型。",
            "传入不同类型时 `other.x` 可能不存在（AttributeError），或者返回 False 阻断了对方更精确的比较。表现为 `a == b` 与 `b == a` 结果不一致，或者排序/去重出现莫名其妙的错误。",
            "先 `if not isinstance(other, type(self)): return NotImplemented`，再比较字段。需要跨类型比较时显式写出对方的处理分支。",
        ),
        (
            "重写 `__eq__` 后忘了 `__hash__`",
            "定义了 `__eq__`，然后把对象放进 `set` 或当 dict 键，发现「明明放进去了却取不到」。",
            "定义 `__eq__` 时 Python 自动把 `__hash__` 设为 `None`，对象变成不可 hash，`set` 会直接抛 `TypeError: unhashable type`。更隐蔽的情况是手动实现了一个错误的 `__hash__`（比如 hash 了可变字段），导致对象改了之后再也找不到。",
            "要可 hash 就显式实现 `__hash__`，且只 hash 不可变字段；或者直接用 `@dataclass(frozen=True)` 让它自动生成正确的 `__eq__` 与 `__hash__`。",
        ),
    ],
    "exercises": [
        {
            "type": "output", "category": "基础题", "platform": "book", "difficulty": "easy",
            "title": "读代码写输出（实例属性遮蔽类属性）",
            "content_md": "```python\nclass Cat:\n    sound = \"meow\"\n\nc = Cat()\nprint(c.sound)\nc.sound = \"nya\"\nprint(Cat.sound, c.sound)\nprint(\"sound\" in vars(c), \"sound\" in vars(Cat))\n```",
            "answer": {"output": "meow\nmeow nya\nTrue True"},
            "explanation": "第一行从类字典取到 `meow`。`c.sound = \"nya\"` 在**实例字典**里新建一项，不修改类属性，所以第二行打印 `meow nya`。第三行用 `vars()` 看字典内容：实例字典里现在有 `sound`（True），类字典里本来就有（True）——两者并存，实例遮蔽类。",
            "tags": ["class-attribute", "shadowing"],
            "source": "book",
            "source_ref": "《流畅的 Python》第 1 章 数据模型",
        },
        {
            "type": "choice", "category": "基础题", "platform": "book", "difficulty": "mid",
            "title": "关于 `super()`，正确的是",
            "content_md": "在 `class D(B, C)` 的 `B` 的方法里调用 `super()`，它会去找",
            "options": [
                {"key": "A", "text": "`B` 的所有直接父类，按定义顺序依次调用"},
                {"key": "B", "text": "`B` 的父类 `object`"},
                {"key": "C", "text": "`type(self).__mro__` 中 `B` 之后的下一个类，可能是 `C`"},
                {"key": "D", "text": "总是 `B` 自己，形成递归"},
            ],
            "answer": {"correct": ["C"]},
            "explanation": "无参 `super()` 的查找起点是「当前类在实例实际 MRO 中的位置之后」，因此 `D` 的实例走 `B` 时，下一个是 `C` 而不是 B 的父类。这正是协作式多继承能工作（也要求链上每个类都调用 `super()`）的原因。",
            "tags": ["mro", "super"],
            "source": "book",
            "source_ref": "《流畅的 Python》第 2 章 序列构成的数组",
        },
        {
            "type": "fix", "category": "基础题", "platform": "book", "difficulty": "mid",
            "title": "改错：为什么这个 set 查不到刚放进去的元素",
            "content_md": "下面的代码在 `s.add(p)` 之后 `p in s` 返回 False。找出原因并修正。\n\n```python\nclass Point:\n    def __init__(self, x, y):\n        self.x, self.y = x, y\n\n    def __eq__(self, other):\n        return self.x == other.x and self.y == other.y\n\np = Point(1, 2)\ns = {Point(1, 2)}\nprint(p in s, p == Point(1, 2))\n```",
            "answer": {"reference_code": "class Point:\n    __slots__ = (\"x\", \"y\")\n\n    def __init__(self, x, y):\n        self.x, self.y = x, y\n\n    def __eq__(self, other):\n        if not isinstance(other, Point):\n            return NotImplemented\n        return (self.x, self.y) == (other.x, other.y)\n\n    def __hash__(self):\n        return hash((self.x, self.y))\n\np = Point(1, 2)\ns = {Point(1, 2)}\nprint(p in s, p == Point(1, 2))  # True True"},
            "explanation": "定义 `__eq__` 时 Python 自动把 `__hash__` 置为 `None`，对象不可 hash。原代码能建出 set 说明 `__hash__` 未被定义时的默认 id 版 hash 仍生效——两个不同实例 hash 不同，set 用 hash 定位，因此 `p in s` 为 False，而 `p == Point(1,2)` 因为走了 `__eq__` 为 True。修法：显式实现 `__hash__`，hash 的字段必须与 `__eq__` 参与比较的字段一致，并先做类型判断返回 `NotImplemented`。",
            "tags": ["hash", "eq", "set"],
            "source": "book",
            "source_ref": "《流畅的 Python》第 1 章 数据模型",
        },
        {
            "type": "choice", "category": "基础题", "platform": "book", "difficulty": "mid",
            "title": "`classmethod` 与 `staticmethod`",
            "content_md": "需要一个「根据参数创建实例」的工厂方法，并希望子类调用时创建的是子类实例。应该用",
            "options": [
                {"key": "A", "text": "`@staticmethod`，因为它不依赖实例"},
                {"key": "B", "text": "`@classmethod`，第一个参数 `cls` 保证子类调用时绑定到子类"},
                {"key": "C", "text": "普通实例方法，在外部先 `__new__` 一个空对象"},
                {"key": "D", "text": "`@property`，把构造逻辑包装成属性"},
            ],
            "answer": {"correct": ["B"]},
            "explanation": "`classmethod` 的第一个参数是类本身，子类调用时 `cls` 就是子类，所以工厂里写 `return cls(...)` 能自动产出正确的子类实例。`staticmethod` 拿不到类，只能硬编码基类名，子类调用会返回基类实例——这是工厂方法最常见的隐蔽 bug。",
            "tags": ["classmethod", "staticmethod", "factory"],
            "source": "book",
            "source_ref": "《流畅的 Python》第 5 章 一等函数",
        },
        {
            "type": "coding", "category": "算法题", "platform": "book", "difficulty": "mid",
            "title": "实现一个可迭代、可 len、可 in 的 Playlist",
            "content_md": "实现 `Playlist` 类：构造时接受任意可迭代对象并拷贝一份；支持 `len(pl)`、`for x in pl`、`x in pl`、`pl[0]`、切片 `pl[1:3]`；`repr()` 输出形如 `Playlist(['a', 'b'])`；两个 Playlist 内容相同时 `==` 为 True。要求写出 `__len__`、`__iter__`、`__contains__`、`__getitem__`、`__repr__`、`__eq__`，并在 `main` 中自测。",
            "answer": {"reference_code": "class Playlist:\n    def __init__(self, songs):\n        self._songs = list(songs)\n\n    def __len__(self):\n        return len(self._songs)\n\n    def __iter__(self):\n        return iter(self._songs)\n\n    def __contains__(self, x):\n        return x in self._songs\n\n    def __getitem__(self, i):\n        return self._songs[i]\n\n    def __repr__(self):\n        return f\"Playlist({self._songs!r})\"\n\n    def __eq__(self, other):\n        if not isinstance(other, Playlist):\n            return NotImplemented\n        return self._songs == other._songs\n\npl = Playlist([\"a\", \"b\", \"c\"])\nprint(len(pl), list(pl), \"b\" in pl, pl[0], pl[1:3], pl == Playlist([\"a\", \"b\", \"c\"]), repr(pl))"},
            "explanation": "要点：① `__init__` 里 `list(songs)` 拷贝一份，避免外部列表后续变化影响对象，也允许传入生成器；② `__iter__` 返回 `iter(...)` 而不是 `self`，避免对象自身状态污染迭代；③ `__getitem__` 既支持下标也支持切片（`list` 的切片自然返回 list）；④ `__eq__` 先返回 `NotImplemented` 再比较，保证对称性；⑤ `__repr__` 用 `!r` 让字符串带引号。",
            "tags": ["dunder", "iterator", "protocol"],
            "source": "book",
            "source_ref": "《流畅的 Python》第 1 章 数据模型",
        },
        {
            "type": "coding", "category": "算法题", "platform": "book", "difficulty": "hard",
            "title": "用 ABC + mixin 实现一个带序列化能力的容器",
            "content_md": "实现 `JsonMixin`（提供 `to_json()`，用标准库 `json.dumps` 序列化 `self._items`）与 `Bag`（继承 `JsonMixin` 与 `collections.abc.MutableSequence`，内部用 list 存储，实现 `__getitem__`/`__setitem__`/`__delitem__`/`__len__`/`insert`）。要求：不重复写 `__iter__`/`__contains__`/`append`/`pop`，验证 ABC 自动补齐后行为正确。",
            "answer": {"reference_code": "import json\nfrom collections.abc import MutableSequence\n\nclass JsonMixin:\n    def to_json(self):\n        return json.dumps(self._items, ensure_ascii=False)\n\nclass Bag(JsonMixin, MutableSequence):\n    def __init__(self, items=()):\n        self._items = list(items)\n    def __getitem__(self, i): return self._items[i]\n    def __setitem__(self, i, v): self._items[i] = v\n    def __delitem__(self, i): del self._items[i]\n    def __len__(self): return len(self._items)\n    def insert(self, i, v): self._items.insert(i, v)\n\nb = Bag([1, 2])\nb.append(3)\nprint(len(b), list(b), 2 in b, b.pop(), b.to_json())"},
            "explanation": "`MutableSequence` 只要求实现五个方法（`__getitem__`/`__setitem__`/`__delitem__`/`__len__`/`insert`），其余 `append`/`extend`/`pop`/`remove`/`__iter__`/`__contains__`/`index`/`count`/`reverse` 由 ABC 通过 mixin 方法自动提供——这正是「继承 ABC 而不是手写容器」的收益。`JsonMixin` 放在前面，MRO 上优先，`to_json` 直接可用；它不定义 `__init__`，所以不会打断协作链。",
            "tags": ["abc", "mixin", "mro", "mutable-sequence"],
            "source": "book",
            "source_ref": "《流畅的 Python》第 5 章 一等函数",
        },
        {
            "type": "output", "category": "基础题", "platform": "book", "difficulty": "easy",
            "title": "读代码写输出（类属性共享）",
            "content_md": "```python\nclass Box:\n    items = []\n    def add(self, x):\n        self.items.append(x)\n\na, b = Box(), Box()\na.add(1)\nb.add(2)\nprint(a.items, b.items)\nprint(a.items is b.items)\n```",
            "answer": {"output": "[1, 2] [1, 2]\nTrue"},
            "explanation": "`items = []` 是类属性，定义时求值一次，`a` 与 `b` 都没有自己的 `items`，`self.items.append(...)` 解析到同一个 list 并原地修改。所以两次 append 都落在同一个列表里，两个实例看到 `[1, 2]`，且 `is` 判断为同一个对象。修法是在 `__init__` 里 `self.items = []`。",
            "tags": ["class-attribute", "mutable-default"],
            "source": "book",
            "source_ref": "《流畅的 Python》第 1 章 数据模型",
        },
    ],
    "interview": [
        (
            "Python 的属性和方法查找顺序是怎样的？描述符协议在哪一步生效？",
            "先查类型（及其 MRO）上是否存在**数据描述符**（定义了 `__set__`/`__delete__` 的，如 `property`），有则直接用它；否则查实例 `__dict__`；再否则查类型上的非数据描述符（普通函数、`classmethod`）或普通类属性；都没有再走 `__getattr__`。这条不对称规则解释了「方法能被实例属性遮蔽，property 不能」。",
            ["为什么 `property` 不能被实例字典遮蔽，而普通方法可以？", "`__getattr__` 与 `__getattribute__` 的调用时机有什么区别？", "`__slots__` 生效后，属性查找路径哪里变了？"],
        ),
        (
            "多继承的 MRO 是怎么算的？`super()` 到底做了什么？",
            "MRO 用 C3 线性化：保证子类先于父类、父类间保持声明顺序、每个类只出现一次，无法满足时抛 `TypeError`。`super()` 不是「父类」，它返回一个代理，从「当前类在 `type(self).__mro__` 中的下一个位置」开始查找。所以 `class D(B, C)` 中 `B` 里的 `super()` 会找到 `C`。这也是协作式多继承要求链上每个类都调用 `super().__init__(**kwargs)` 的原因。",
            ["C3 线性化为什么比深度优先更合理？举个它会报错的例子。", "mixin 为什么不应该定义 `__init__` 状态？", "`super()` 为什么不能用在类外的普通函数里？"],
        ),
        (
            "为什么定义了 `__eq__` 之后对象就不能当 dict 的键了？怎么正确实现？",
            "因为 Python 认为「相等的对象 hash 必须相同」，改写了相等语义就等于放弃了默认的 id-based hash，所以自动把 `__hash__` 置为 `None`（不可 hash）。正确实现要满足两条：① `__hash__` 使用的字段是 `__eq__` 比较字段的子集；② 这些字段不可变。最简单的方式是 `@dataclass(frozen=True)`，它会自动生成满足契约的一对。",
            ["如果对象包含 list 字段又想可 hash，怎么办？", "`__hash__` 返回常量行不行？会有什么性能后果？", "为什么 `frozen=True` 的 dataclass 还要额外注意字段本身的可变性？"],
        ),
        (
            "`__new__` 和 `__init__` 有什么区别？什么时候必须用 `__new__`？",
            "`__new__` 负责创建并返回实例（类方法，第一参数是 `cls`），`__init__` 负责初始化已存在的实例且必须返回 `None`。日常业务只写 `__init__`。必须用 `__new__` 的场景：① 单例/受控实例数量；② 继承不可变类型（`int`/`str`/`tuple`）想改构造语义，因为它们的值在 `__new__` 里就固定了，`__init__` 改不了；③ 需要根据参数返回不同类的实例（工厂）。",
            ["为什么不可变类型的子类不能只重写 `__init__`？", "`__new__` 里返回一个别的类的实例会发生什么？", "`object.__new__` 在参数不匹配时的行为是什么？"],
        ),
        (
            "为什么 Python 推荐「组合优于继承」？什么情况下继承仍然合适？",
            "继承把父类的实现细节变成子类的隐性依赖——父类改一个私有方法就可能破坏子类，这叫「脆弱的基类问题」。组合只依赖对方的公开接口，可替换、可 mock、可注入。继承仍然合适的场景：① 真正的 `is-a` 且父类是为扩展设计的（模板方法模式）；② 用 ABC 声明接口；③ 无状态的 mixin 混入正交能力。判据：如果只是想「复用几个方法」，用组合或模块级函数。",
            ["mixin 与组合分别适合什么规模的能力复用？", "`collections.abc` 的继承为什么是合理的使用？", "如何在重构中把继承改成组合而不破坏调用方？"],
        ),
    ],
    "project": (
        "用 OOP 重写小工具：从函数式脚本到可扩展的对象模型",
        """选一个此前用一堆函数写的脚本（如 JSON 配置读写器、CSV 清洗器、爬虫），改成面向对象设计：

1. 抽象出一个基类（用 `abc.ABC` + `@abstractmethod`），声明「必须实现哪些方法」；
2. 用 `classmethod` 提供至少两个工厂入口（如 `from_file()` / `from_dict()`），并验证子类调用时返回子类实例；
3. 用 mixin 提供一项正交能力（如 `JsonSerializableMixin.to_json()`），mixin 不持有 `__init__` 状态；
4. 至少一处用 `@property` 暴露只读派生属性，并拒绝外部赋值；
5. 为数据类实现 `__repr__`、`__eq__`、`__hash__`，并说明为什么 hash 只用不可变字段；
6. 写一个对比说明：改造前后的调用方代码各长什么样，扩展一个新格式需要改几个文件。""",
        [
            ("抽象基类 + 至少两个子类实现",
             {"type": "test", "desc": "`ABC` 中声明的抽象方法缺一个就实例化失败；两个子类行为不同且都通过同一套测试"}),
            ("工厂方法返回正确子类",
             {"type": "test", "desc": "对子类调用 `from_file()` 返回的是子类实例（`type(obj) is SubClass`）"}),
            ("mixin 不破坏协作链",
             {"type": "test", "desc": "mixin 无 `__init__`；多继承链上所有 `__init__` 走 `super()`，打印 MRO 符合预期"}),
            ("`__eq__`/`__hash__` 契约成立",
             {"type": "test", "desc": "相等对象可互相在 set 中找到；修改可变字段后行为符合文档说明"}),
            ("扩展性对比说明",
             {"type": "doc", "desc": "README 含「新增一种格式需要改动哪些文件」的清单，且行数少于改造前"}),
        ],
    ),
    "sources": ["jackfrued/Python-100-Days", "TheAlgorithms/Python", "microsoft/ML-For-Beginners"],
})
