# fs-ch09 · TypeScript：结构化类型、泛型与类型收窄 · 常见错误

1. **把 `any` 当「先跑通再说」** —— 错在：`function handler(req: any) { return req.body.user.name; }` —— 一路 any 到底，编译零报错。

   *为什么*：`any` 会让整条调用链的类型检查失效，而且会传染：返回 `any` 的函数赋给有类型的变量也不会报错。上线后 `req.body.user` 为 undefined 时，错误信息是 `Cannot read properties of undefined`，距离真正原因隔了五层。

   *怎么改*：外部入口用 `unknown`，进门第一步收窄或 schema 校验。真的暂时不知道类型时，写 `unknown` 并加 `// TODO(type): 待接入 schema`，让 `unknown` 逼你在使用点做判断。

2. **用 `as` 代替类型守卫** —— 错在：`const user = data as User;` —— 把接口返回直接断言成业务类型。

   *为什么*：断言只在编译期有效，且**编译器不检查可行性**（只拦明显不可能的转换）。运行时 `data` 是什么就是什么，字段缺失时类型系统完全不知道。这类 bug 在联调期和数据格式变更后集中爆发。

   *怎么改*：改成 `const user = UserSchema.parse(data)`（Zod）。校验失败会抛出带字段路径的错误，比五层之后的 undefined 好定位得多。

3. **以为泛型能约束运行时** —— 错在：`function isType<T>(x: unknown): x is T { return true; }` —— 想写一个通用类型判断。

   *为什么*：类型被擦除，`T` 在运行时不存在，函数体里无法知道 `T` 是什么，所以只能 `return true`（等于永远相信）。这种守卫会让所有下游收窄都建立在谎言上，比不写更糟。

   *怎么改*：要么传入构造函数做 `instanceof`，要么传入 schema 做运行时校验。二者都需要把「类型」以值的形式带到运行时。

4. **用 interface 期望拦住多余字段** —— 错在：`interface User { id: string }` 然后期待 `{ id, isAdmin: true }` 赋值时报错。

   *为什么*：结构类型只看「有没有缺少必需成员」，多出来的成员默认允许（只有对象字面量直接赋值时才有 excess property check，一旦经过变量中转就失效）。

   *怎么改*：需要严格排他时用可辨识联合 + `never` 检查，或在边界处用 schema 的 `.strict()`。不要指望 interface 做字段白名单。

5. **`switch` 的 `default` 直接 `throw` 而不做 `never` 检查** —— 错在：可辨识联合写成 `default: throw new Error("unreachable")`，以为运行时抛错就安全了。

   *为什么*：这只能拦住「运行时真的走到 default」，拦不住「新增了一个 `kind` 却忘了加 case」——因为编译不报错，问题只在真有人提交那种数据时才暴露。类型系统本来能在这个 PR 里就提示，被 `throw` 放弃了。

   *怎么改*：`default` 里先写 `const _exhaustive: never = shape;`，再 throw。这样新增分支忘处理时是**编译期**报错，而且报错信息精确指向那个 `switch`。

6. **`catch` 里 `as any` 了事** —— 错在：`catch (e: any) { console.log(e.message) }`，或者直接 `catch (e) { e.message }` 被 TS 报错后改成 `as any`。

   *为什么*：`catch` 捕获的东西理论上可以是任何值——JS 里 `throw "字符串"`、`throw {code: 1}` 都合法。断言成 `any` 之后，`e.message` 在抛的是字符串时就是 `undefined`，日志里没有任何有用信息，而编译期一句话都不说。

   *怎么改*：先收窄再取属性：`if (e instanceof Error) { e.message } else { String(e) }`。或者用 `unknown` 配合工具函数 `toMessage(e: unknown): string` 统一处理。

7. **把 `enum` 当唯一选项，忽略 `as const` 对象** —— 错在：用数字 `enum` 表示状态，接口返回 `0/1/2`，前后端各维护一份映射。

   *为什么*：数字 enum 在编译后留下双向映射对象（`{0: "Active", Active: 0}`），体积翻倍；而且接口里传的是数字，语义完全丢失，后端加一个状态值前端不会报错。字符串 enum 好一些，但仍是运行时对象。

   *怎么改*：需要「一组常量 + 一个联合类型」时用 `const STATUS = { Active: "active", ... } as const; type Status = typeof STATUS[keyof typeof STATUS]`。它有 enum 的类型安全，编译产物是普通对象，且与 JSON 天然对齐。

8. **泛型约束写成 `T extends any`** —— 错在：写 `function first<T extends any>(xs: T[]): T`，以为这是「任意类型」的规范写法。

   *为什么*：`any` 作为约束等于没有约束，`T` 依然是任意类型，而且 `any` 的传染性会影响推断。更实际的问题是：这个签名没有表达「`xs` 必须有长度」——传 `{}` 也能过编译。

   *怎么改*：写无约束的 `function first<T>(xs: T[]): T` 即可；需要约束就写真实形状，如 `T extends { length: number }`。约束越具体，能接受的值越少、能做的事越多。

9. **可选属性与 `undefined` 混为一谈** —— 错在：`interface Opts { timeout?: number }` 然后读 `opts.timeout!` 强断言，或用 `withDefaults` 之外的方式补默认值。

   *为什么*：`?:` 表示「这个键可以不存在」，`| undefined` 表示「键存在但值是 undefined」。两者在多数场景等价，但在 `Object.keys`、JSON 序列化、`in` 判断、以及 `exactOptionalPropertyTypes` 开启时行为不同。用 `!` 抹掉 undefined 只是把运行时错误推后。

   *怎么改*：在入口一次性补默认值（解构 `const { timeout = 3000 } = opts`），之后所有下游都拿到非可选类型。别让「可选」这件事渗透到每一层。

10. **类型断言绕过 `null` 检查** —— 错在：`document.getElementById("app")!`，或 `JSON.parse(s) as Config`。

    *为什么*：`!` 只对编译器说谎。DOM 元素不存在时 `!` 得到 `null`，后面 `.appendChild` 直接 TypeError；`as Config` 在 JSON 缺字段时也是同样的后果。这两处恰是「外部世界进入程序」的边界，最需要校验。

    *怎么改*：DOM 查询用显式判空 + 早退（`if (!el) throw new Error("missing #app")`）；外部 JSON 用 schema 的 `.parse()`，让它抛出带字段路径的错误。


11. **用结构化类型做「名义隔离」** —— 错在：定义 `type UserId = string` 和 `type OrderId = string`，以为编译器会拦住互相传值。

   *为什么*：TypeScript 是结构化类型系统，`string` 与 `string` 形状完全相同，别名在编译后完全擦除。把 `OrderId` 传给要 `UserId` 的函数，零报错。

   *怎么改*：用品牌类型 `type UserId = string & { readonly __brand: "UserId" }`，并通过 `asUserId()` 这类工厂函数构造。类型层面零成本，但把同形不同义的类型区分开了。

12. **以为多余属性检查处处生效** —— 错在：看到对象字面量赋值会报「多余属性」错误，就认为接口对字段做了严格约束。

   *为什么*：多余属性检查只对**直接赋值的对象字面量**生效。赋给中间变量再传进去就不检查了，因为变量可能是别处传来的，形状兼容就放行。

   *怎么改*：接口定义要精确，别用 `[key: string]: any` 兜底；需要严格校验外部数据用 schema（zod 等）在运行时兜底，不要指望编译期。

13. **在泛型里做运行时判断** —— 错在：写 `function create<T>() { return new T(); }` 或 `if (x instanceof T)`，报错后以为是语法问题。

   *为什么*：泛型是纯编译期概念，编译后完全擦除，运行时不保留任何类型信息。`T` 在产物里不存在，自然不能 `new`、不能 `instanceof`。

   *怎么改*：把「运行时能用的东西」显式传进来——构造器 `new () => T`、工厂函数、或校验器 schema。凡是要运行时用类型信息的库（ORM、DI、反序列化），都必须走这条路。

14. **条件类型在联合上自动分配，把结果拆碎了** —— 错在：写 `type Wrap<T> = T extends any ? Promise<T> : never`，传入联合类型后得到的是多个 Promise 的联合而不是整体的 Promise。

   *为什么*：条件类型对裸类型参数是**分配式**的，`T` 为联合时逐个成员判断再合并。想要整体判断必须阻止分配。

   *怎么改*：用元组包一层：`type Wrap<T> = [T] extends [any] ? Promise<T> : never`。方括号阻断了分配到成员的行为。

15. **`strictNullChecks` 关掉换「编译通过」** —— 错在：老项目迁移时被几百个报错吓到，先把 `strictNullChecks` 关掉，打算「以后再开」。

   *为什么*：关掉之后 `null`/`undefined` 可以赋给任何类型，「可能为空」这个信息彻底丢失，`?.` 与 `??` 也失去意义。所有新代码陪着老代码一起裸奔，技术债只会越滚越大。

   *怎么改*：新代码一律 `strict: true`，老文件用 `// @ts-strict-ignore` 逐文件豁免，然后按模块逐个清。全局关开关是最差的选择。
