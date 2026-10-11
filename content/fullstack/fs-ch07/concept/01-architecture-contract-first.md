# fs-ch07 · 一、全栈分层、目录组织与契约优先

> 前置：fs-ch03（JS 核心：异步、模块、事件循环）、fs-ch05（数据库与 REST API 设计）。
> 本章把前几章的「零件」装成一台可运转的机器，视角从「单个知识点」抬到「一个工程怎么组织」。

## 一、分层与目录组织：前端 / 后端 / 共享类型

全栈工程的第一性问题不是「用什么框架」，而是**依赖方向**。一个能长期演进的全栈仓库，目录结构应当把「谁可以 import 谁」编码进物理布局：

```
repo/
├── apps/
│   ├── web/            前端应用：视图层 + 客户端状态（可依赖 shared / contract）
│   └── api/            后端服务：路由 + 领域逻辑 + 持久化（可依赖 shared / contract）
├── packages/
│   ├── shared/         共享纯逻辑：类型、校验函数、领域常量（零 IO、零框架）
│   └── contract/       OpenAPI 文档 + 由它生成的前端类型与服务端校验器
├── pnpm-workspace.yaml
└── README.md
```

三条硬规则，违反任意一条都会在三个月后反噬：

1. **依赖方向单一**：`apps/* → packages/*`，`packages/*` 之间只允许 `contract → shared`，任何包**不得反向依赖 `apps/`**。反向依赖一旦出现，共享包就退化成「只有一个人敢改」的巨石。
2. **`shared` 里只放纯逻辑**：能被前端与服务端同时 `import` 的代码，必须没有副作用、不碰 `fs`/`net`/`window`，否则打包器会在前端 bundle 里塞进 Node 内置模块（或反之）。
3. **契约置于依赖图下游**：`contract` 不依赖任何实现，只描述「请求长什么样、响应长什么样」。这样文档可以先于实现存在。

本章 ex08（归一化）、ex11（sqlite 端到端）演示了 `shared` 层最典型的产物：**把服务端返回的嵌套结构归一化成实体表**，这一步在前端 store 与服务端缓存里是同一份纯函数，放 `shared` 才能不重复实现。

### 🧑‍💻 程序员视角
- 落地顺序：先把 `packages/contract` 的 `openapi.yaml` 写出来再过接口联调，而不是「后端写完丢个 Postman 集合」。OpenAPI 是唯一能同时喂给前端代码生成器、后端请求校验器、CI 契约校验脚本的格式（本章 ex06 就是用 schema 子集做双向校验的最小实现）。
- 共享代码的类型漂移是最常见事故：前端 `interface User { name: string }`、后端 `type User struct { Name string }` 各写一份，字段改名时只改一边，运行到线上才 500。修法是**类型只从 contract 生成**，两边都不手写。
- 目录反模式：把 `utils.js` 塞进 `api/` 再让 `web/` 去 import。短期省事，长期是「前端构建依赖后端目录结构」的隐形耦合；正确做法是把真正共享的部分抽到 `shared/`，且一次只抽真正共享的——过度抽象比重复更贵。
- monorepo 工具（pnpm workspace / Turborepo / Nx）的价值不是「酷」，而是**只重建受影响的包**：改了 `shared` 只重跑依赖它的 `web` 与 `api`，CI 时间从全量降到增量。

### 🎓 博士生视角
- 这一层结构本质是在依赖图上构造一个**有向无环图（DAG）**，并把「无环」作为不变量。反向依赖等价于引入环，环会导致：① 拓扑排序失败、增量构建退化；② 循环 import 在 ES Module 下产生**暂时性死区（TDZ）**——被循环引用的绑定在初始化前是 `undefined`，报错往往出现在很远的下游，排查成本极高。
- 为什么把 `shared` 约束为「纯」：纯函数满足**引用透明（referential transparency）**，即相同输入必得相同输出、可被任意替换为它的求值结果。只有纯代码才能同时安全地跑在浏览器（无 `fs`）、Node（无 `window`）、以及未来的 Edge Runtime（无 `net` 原生 socket）三套语义不同的宿主里。副作用一旦进入共享层，「在哪运行」就成了运行期问题而非编译期问题。
- `contract` 独立于实现，对应的是**接口与实现分离**这一经典原则在 Web 领域的落地：OpenAPI Document 是一个可被机器处理的**形式化规约**，它同时是文档、代码生成输入、请求/响应校验器、以及 mock 服务器的事实来源。单一事实来源（Single Source of Truth）的意义在于消除「文档与实现双写」导致的必然漂移。
- 与类型系统的关系：契约生成的类型是**名义类型（nominal）的近似**——从 schema 生成的结构类型（structural）无法表达「这个 string 是服务端 ID 而非任意字符串」，因此边界处仍需运行期校验（ex06 的正反用例），编译期类型只是第一道防线。

### 📚 考研者视角
- **笔试/面试考点**（非 408 课目，对准计算机方向笔试与面试）：简答「monorepo 与 multirepo 的取舍」「为什么共享类型应该从契约生成」。
- **可迁移的 408 映射**：本章的「依赖 DAG + 无环」是**编译原理**中「模块依赖图拓扑排序」的直接应用；循环依赖导致 TDZ，与**程序的静态作用域与初始化顺序**同源。答题时把「工程惯例」上升到「依赖图不变量」是加分点。
- **标准口径**：单例/模块初始化顺序在 ES Module 规范里由「Module Records 的 [[Evaluation]] 深度优先」定义；循环 import 中，先求值的一方拿到的绑定可能尚未初始化（`let/const` 抛 TDZ，`function` 声明提升可用）。常考「循环依赖为什么有时不报错」。
- **易混对比**：`dependencies` 与 `devDependencies`（运行期必需 vs 仅构建期）；`peerDependencies`（宿主提供，避免多份实例）；monorepo 的「工作区依赖」是软链接而非发布包，因此改了 `shared` 立即生效、不会出现「装了旧版本」的错觉。

## 二、契约优先：OpenAPI 驱动、类型生成与边界校验

契约优先（contract-first / design-first）把顺序倒过来：**先定义接口，再各自实现**。一个最小可用的契约包含四件事：

| 元素 | 作用 | 本章示例 |
|---|---|---|
| 路径 + 方法 | 资源寻址与语义（fs-ch05 已讲） | — |
| 请求 schema | 类型、必填、边界、枚举、`additionalProperties: false` | ex06 |
| 响应 schema | 客户端类型生成的唯一来源 | ex06 |
| 错误契约 | 所有 4xx 统一为 `application/problem+json`（RFC 9457） | fs-ch05 ex06/ex11 |

ex06 用 schema 子集做**双向校验**，把「契约」从文档变成可执行断言：

```
req_ok_all_pass=true (2)                       # 合法请求体全部通过
req_bad_all_rejected=true (6/6)                # 非法请求体全部被拒
req_missing_title=$.title: required
req_bad_pattern=$.status: must match ^(draft|published)$
req_bad_float=$.score: expected integer
req_bad_max=$.score: maximum is 100
req_bad_extra=$.extra: additional property not allowed
res_ok_all_pass=true (1)                       # 合法响应体通过
res_bad_all_rejected=true (2/2)                # 非法响应体被拒（服务端自身违约也要拦）
res_bad_min=$.id: minimum is 1
res_missing_title=$.title: required
```

注意 6 类非法样例各命中一条规则：缺必填、字符串下界、正则不匹配、类型不符（`1.5` 不是整数）、数值上界、多余字段。每一类都输出 `$` 开头的字段路径（JSON Pointer 风格），前端才能精确高亮字段。

**响应也要校验**，这是最容易被忽略的一环：如果服务端返回了不符合自己契约的数据，客户端会拿到「类型正确但语义错误」的对象（最常见是 `null` 混进非空字段），崩在渲染层而不是接口层。ex06 的 `res_bad_*` 两行就是在拦这类「服务端违约」。

### 🧑‍💻 程序员视角
- 生成链路的落地：`openapi.yaml` →（openapi-typescript / orval / openapi-generator）→ 前端 TS 类型 + 请求函数；同一份 yaml →（express-openapi-validator / zod 从 schema 生成）→ 服务端请求校验中间件。**两边同源**，字段改名只改 yaml。
- `additionalProperties: false` 是安全默认值：它拦的是 mass assignment（攻击者往请求体塞 `{"role":"admin"}`）。ex06 里 `extra` 字段被拒就是这条规则在起作用；若服务端直接把 body 透传给数据库，多余字段会被静默写入。
- 契约校验必须进 CI：把「文档超前于实现 / 实现未纳入文档」做成双向比对的退出码（本章 project.json 第二个任务），否则契约会在两周内腐烂成一份没人看的 yaml。
- 版本演进：新增**可选**字段是向后兼容的；删字段、改类型、收窄枚举是破坏性的，必须走新版本或双写过渡期（fs-ch05 的版本策略章节）。

### 🎓 博士生视角
- 契约的本质是一个**部分函数**的类型签名：`request: Request → Response ∪ Error`。schema 描述的是该函数定义域（合法输入集合）与值域（合法输出集合）的**子集刻画**。ex06 的正反用例，本质是在断言「定义域成员全部落在实现内、非成员全部被拒」——这就是把规约当成可执行的谓词。
- 为什么 `additionalProperties: false` 在类型论上重要：结构类型（structural typing）默认是**开放**的，多出的字段不影响类型兼容；这与「拒绝未知字段」的安全需求冲突。JSON Schema 的 `additionalProperties: false` 把对象类型从「至少包含这些字段」收紧为「恰好包含这些字段」，即从开放类型变成**封闭类型**，才让 mass assignment 在类型层面不可能。
- Design-first 与 code-first 的分歧点：code-first（从类型/装饰器生成文档）的优点是实现永远与文档一致，缺点是文档被实现细节绑架、无法表达「尚未实现但已达成一致」的接口；design-first 反过来。真正决定性的是**多方并行**需求：当移动端、Web、第三方同时接入时，只有先把契约冻结，各方才能并行开发，此时 design-first 的价值压倒 code-first 的一致性优势。
- 校验的层次与「语法 vs 语义」的分野（承接 fs-ch05）：ex06 的 `pattern` 属于语义（`'archived'` 语法合法但不在枚举内），`expected integer` 属于类型/语法。把两者分成不同错误码，客户端才能决定「改格式」还是「改取值」。

### 📚 考研者视角
- **笔试/面试考点**：简答「design-first 与 code-first 的取舍」「OpenAPI 与 Swagger 的关系（Swagger 是工具集，OpenAPI 是规范，3.0 起 Swagger 仅仅指工具链）」。
- **标准口径**：JSON Schema 的 `type` 关键字只做基本类型分类（`integer` 与 `number` 分离，`1.0` 在 JSON Schema 里可视为 integer）；`required` 与 `type` 是正交的，缺 `required` 时字段可缺省。答题要点：**校验的是「实例 vs schema」的关系，不是「值 vs 值」**。
- **易混对比**：`nullable`（3.0 写法）与 `type: ["string","null"]`（3.1 写法）；`enum`（闭集，值必须在列内）与 `pattern`（正则，字符级约束）；`minLength`（字符数）与 `minItems`（数组元素数，fs-ch05 ex05 用过）。
- **延伸**：契约与幂等键（fs-ch05 ex07）联合出题时，注意「同键换载荷必须 422」这一条，本质也是「请求指纹 = 契约实例的规范化哈希」。

## 三视角小结
| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| 分层与目录组织 | 依赖单向、shared 只放纯逻辑、契约在下游、monorepo 增量构建 | 依赖 DAG 无环不变量、引用透明、接口与实现分离、结构 vs 名义类型 | 循环依赖与 TDZ、拓扑排序、dependencies 种类辨析 |
| 契约优先 | yaml 单一来源、生成类型与校验器、CI 双向比对、兼容性演进 | 契约是部分函数刻画、封闭 vs 开放类型、design/code-first 分歧 | JSON Schema 语义、3.0/3.1 差异、枚举 vs 正则 |
