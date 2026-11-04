# -*- coding: utf-8 -*-
"""fullstack 来源笔记 · 第 1 部分（fs-ch01 ~ fs-ch07）。"""

NOTES: dict[str, list[str]] = {
    # ---------------- fs-ch01 Web 工作原理 ----------------
    # 仓库序：system-design-primer / CyC2018/CS-Notes / nodejs/node / hoppscotch/hoppscotch
    "fs-ch01": [
        "§1.2 二、实现机制：报文的确切结构 · 读 `system-design-primer` 的 `README.md`："
        "它的 HTTP 一节给了请求/响应报文的逐行拆解，"
        "对照本章这个 |状态行 + 首部 + 空行 + 主体| 的四段结构——"
        "重点是那个「空行」，它是首部结束的唯一判据，"
        "少一行就变成「首部还没发完，主体已经在路上」；"
        "别只记 GET/POST，先确认四段的边界怎么被协议解析器识别",

        "§3.2 二、实现机制 · 读 `CyC2018/CS-Notes` 的 `docs/` 计算机网络专题："
        "它把强缓存与协商缓存分成两节写，读它「304 为什么不带主体」，"
        "就懂本章 §3.1「HTTP 无状态，一切记忆都是外置的」"
        "为什么缓存也算一种「记忆」——"
        "`Cache-Control: max-age` 把服务端的状态搬到了客户端，"
        "而 304 是「你那份还能用，别再要」的确认，省的是主体那段带宽",

        "§2.3 三、工程实践：头部才是 HTTP 的表达力所在 · 读 `nodejs/node` 的 "
        "`lib/_http_outgoing.js`：`writeHead` 决定首部何时定型；"
        "读它就知道本章 §1.4「边界与陷阱」里的首部时序里"
        "「头部必须在主体前发完」不是约定而是实现约束——"
        "一旦第一次 `write()` 调过，首部就已经写到 socket，"
        "此后想再 `setHeader` 只会抛 `ERR_HTTP_HEADERS_SENT`",

        "§4.2 二、实现机制 · 读 `hoppscotch/hoppscotch` 的 `packages/` 请求模块："
        "它能直接看/改请求头，手动构造一个 `OPTIONS` 预检，"
        "本章 §4.1「为什么必须知道整条链路」当场可见——"
        "预检里 `Access-Control-Request-Headers` 会把你准备用的异常头逐个列出来，"
        "服务端 `Access-Control-Allow-Headers` 少一项，真正的请求就发不出去",
    ],

    # ---------------- fs-ch02 前端基础：HTML 语义化与 CSS 盒模型/布局 ----------------
    # 仓库序：w3c/csswg-drafts / Chalarangelo/30-seconds-of-code / yangshun/front-end-interview-handbook
    "fs-ch02": [
        "§2.2 二、实现机制：`content-box` vs `border-box` · 读 "
        "`w3c/csswg-drafts` 的 `css-box-3/Overview.bs`，"
        "再读同仓 `css-display-3/Overview.bs` 里 flow-root 生成 BFC 的条文："
        "「margin 为什么穿透父元素」在规范里是定义，不是经验——"
        "本章 §2.3「BFC：块级格式化上下文」之所以能当「补丁」用，"
        "就是因为规范把「谁与谁参与同一个格式化上下文」写成了可判定的条件",

        "§4.4 四、工程实践 · 读 `Chalarangelo/30-seconds-of-code` 的 "
        "`snippets/` 下带 `css` / `browser` 标签的条目"
        "（水平垂直居中、等分布局、清除浮动）：每条都是可直接粘的最小实现，"
        "正好对照本章 §4.2「实现机制：Flexbox」与 §4.3「Grid」——"
        "同一件事在 flex 时代只需三行，在 float 时代要一个 clearfix 加一个负 margin，"
        "这个差就是「一维 vs 二维」判据的实际收益",

        "§3.3 三、Reflow / Repaint / Composite-only 的区别（面试高频） · 读 "
        "`yangshun/front-end-interview-handbook` 的 `questions/html-questions.md` 与 "
        "`questions/css-questions.md`：前者用「全 div 堆出来的页面哪里坏了」讲语义化，"
        "后者把 reflow / repaint / 合成层分开问——"
        "与本章 §1.1「语义化不是好看，而是机器可读」、§3.3 的判据一一对应；"
        "注意题库里对「transform 为什么不触发 reflow」的回答，"
        "正是本节「合成层只改图层属性」的直接推论",
    ],

    # ---------------- fs-ch04 Node.js 与后端 API ----------------
    # 仓库序：nodejs/node / expressjs/express / koajs/koa
    "fs-ch04": [
        "§1.2 二、process.nextTick / Promise.then / setImmediate 三者顺序 · 读 "
        "`nodejs/node` 的 `lib/internal/process/task_queues.js`："
        "它是 nextTick 与微任务队列的真实调度，"
        "配合 `lib/internal/streams/readable.js` 里 `highWaterMark` 与 "
        "`readableFlowing` 的状态迁移，就构成本章 §3.1「Stream 流控与背压」的机器版本；"
        "先看 §1.1 的六阶段图，再看这份调度代码，"
        "才会明白「nextTick 在自己那一层内递归，能把事件循环饿死」",

        "§2.1 一、从零手写 HTTP 服务器（路由 / 路径变量 / JSON body / 状态码） · 读 "
        "`expressjs/express` 的 `lib/application.js`：`app.use` 把中间件压进栈、"
        "`app.handle` 作为 `http.createServer` 的回调把 req/res 交出去；"
        "四参数错误中间件的识别就发生在这一层——"
        "它靠 `fn.length === 4` 判断，这个「用参数个数编码语义」的做法"
        "正是本章 §2.3「中间件模型与 compose」的起点",

        "§2.2 可运行代码：compose 的洋葱模型 · 读 `koajs/koa` 的 `lib/application.js`："
        "它的 `callback()` 用 `compose(this.middleware)` 把数组折成嵌套函数，"
        "`await next()` 前后各写一段——这就是 §2.3「进去一层、出来一层」的原始代码；"
        "对照 express 的「线性 next()」，"
        "能看清 koa 的洋葱之所以可能，靠的是 async/await 的 Promise 链，"
        "而不是回调栈",
    ],

    # ---------------- fs-ch05 数据库与 REST API 设计 ----------------
    # 仓库序：sqlite/sqlite / graphql/dataloader / OAI/OpenAPI-Specification
    "fs-ch05": [
        "§1.2 二、索引：B+ 树、最左前缀与覆盖索引 · 读 `sqlite/sqlite` 的 `src/btree.c`："
        "`sqlite3BtreeInsert` 与 `balance()` 演示 B+ 树怎么分裂合并，"
        "再做 `src/where.c` 的 `whereBegin` 决定能用哪个索引前缀——"
        "「最左前缀」在这里是可用性判定，不是口诀："
        "where 子句里的列顺序与索引列顺序一旦错位，优化器就直接放弃这条索引；"
        "而本章 §1.1「关系型与文档型的选型判据」也由此落地——"
        "文档库没有这种「按前缀匹配的确定性」，代价是范围查询只能靠扫描",

        "§2.2 二、N+1：用操作计数发现，用批量合并修复 · 读 `graphql/dataloader` 的 "
        "`src/index.js`：`enqueuePostPromiseJob` 把一个 tick 内的 key 全攒进 `_batch`，"
        "再一次性调 `batchLoadFn`——"
        "「用操作计数发现、用批量合并修复」的教科书实现；"
        "注意它靠的是「同一 tick 内合并」，"
        "所以跨 tick 循环里逐个 `await load(id)` 依然会 N+1，"
        "这正是本章 §2.1「ORM / ODM：用类型安全换控制力」要警惕的隐性成本",

        "§4.1 一、契约优先（Design-First）与 OpenAPI · 读 "
        "`OAI/OpenAPI-Specification` 的 `versions/3.1.0.md`："
        "`paths` / `components/schemas` 的结构与 `$ref` 复用规则写得很细，"
        "对照 `versions/3.0.3.md` 的 `nullable` 写法差异——"
        "3.1 用 JSON Schema 的 `type: [\"string\", \"null\"]` 取代了 3.0 的 `nullable: true`；"
        "先写契约再生成类型时，这两份是唯一权威，"
        "也是 §4.2「版本策略」为什么必须在契约层而不是在路由层决定的原因",
    ],

    # ---------------- fs-ch06 用户认证 / JWT / 鉴权 ----------------
    # 仓库序：panva/jose / auth0/node-jsonwebtoken / OWASP/CheatSheetSeries
    "fs-ch06": [
        "§2.1 一、JWT 三段结构与签名算法（HS256 vs RS256） · 读 `panva/jose` 的 "
        "`docs/jws/compact/verify/functions/compactVerify.md`："
        "它说明签名的输入是 `BASE64URL(header).BASE64URL(payload)` 这串字节，"
        "不是解析后的 JSON——"
        "本章「签的是串不是对象」由此而来；"
        "实务差别在于：任何重排 JSON 键序、改空白的外部处理都会让签名失效，"
        "所以验签必须先验串、再解析",

        "§2.2 二、校验清单与 alg:none / 算法混淆攻击 · 读 `auth0/node-jsonwebtoken` 的 "
        "`verify.js`：`options.algorithms` 白名单是唯一能挡住 `alg:none` 的地方"
        "（不传就按 header 里声明的算法验，等于让攻击者选算法）；"
        "配套 `sign.js` 的 `expiresIn` 只写进 `exp`，服务端不查黑名单就撤不掉——"
        "这就是本章 §3.1「JWT 无法主动失效（固有缺陷）与缓解」的全部技术根源",

        "§3.2 二、密码存储：bcrypt / scrypt / argon2 的加盐与成本 · 读 "
        "`OWASP/CheatSheetSeries` 的 `cheatsheets/Password_Storage_Cheat_Sheet.md`："
        "它给了 argon2id 的参数下限与「不加盐等于送彩虹表」的量化说明；"
        "配套读同目录 `Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.md` 与 "
        "`Cross_Site_Scripting_Prevention_Cheat_Sheet.md`，"
        "正好对应本章 §4.2「OAuth2 授权码 + PKCE，CSRF/XSS 与常见漏洞」的两类攻击面——"
        "一个借用户的浏览器发请求，一个把脚本塞进你的页面",
    ],

    # ---------------- fs-ch07 全栈项目实战 ----------------
    # 仓库序：realworld-apps/realworld / TanStack/query / vercel/next.js
    "fs-ch07": [
        "§1.2 二、契约优先：OpenAPI 驱动、类型生成与边界校验 · 读 "
        "`realworld-apps/realworld` 的 `README.md` 与 `specs/`："
        "它把「页面 → 数据层 → API」的边界写成契约（`api.md`）"
        "并规定统一错误体（`error-handling.md`），十几种语言实现共用同一份契约——"
        "正是本节「契约先于实现」的实物；"
        "配合 §3.3「错误处理与三态呈现」看："
        "统一错误体让 loading/empty/error 三态的判断不依赖各实现自己的约定",

        "§2.2 二、数据流转：缓存失效、乐观更新与列表合并 · 读 `TanStack/query` 的 "
        "`packages/query-core/src/query.ts`：`staleTime` 与 `gcTime` 两个时钟"
        "把「新鲜度」和「回收」拆开，"
        "`packages/query-core/src/mutation.ts` 的 `onMutate` / `onError` 回滚"
        "就是本节乐观更新的标准写法；"
        "要点是 `onMutate` 里要返回旧快照，`onError` 才有东西可回滚",

        "§4.1 一、性能：懒加载与代码分割、列表虚拟化、请求去重与取消 · 读 "
        "`vercel/next.js` 的 `packages/next/src/client/`：`dynamic` 与路由级 chunk——"
        "构建期按入口拆 bundle、运行期按需拉，"
        "「首屏只付首屏的钱」在框架里是编译期决定，不是运行时的 `lazy()`；"
        "这条区别解释了本章 §4.3「读得懂大厂源码：入口 → 路由 → 数据层 → 组件树」"
        "为什么第一步要看构建配置而不是组件",
    ],
}
