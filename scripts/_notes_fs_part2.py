# -*- coding: utf-8 -*-
"""fullstack 来源笔记 · 第 2 部分（fs-ch08 ~ fs-ch15）。"""

NOTES: dict[str, list[str]] = {
    # ---------------- fs-ch08 部署 / CI-CD / Docker ----------------
    # 仓库序：moby/buildkit / docker/compose / systemd/systemd / nektos/act
    "fs-ch08": [
        "§2.1 一、镜像分层、写时复制与构建缓存 · 读 `moby/buildkit` 的 "
        "`frontend/dockerfile/dockerfile2llb/convert.go`："
        "它把 Dockerfile 逐指令翻译成 LLB 图，"
        "而 `cache/manager.go` 按「指令 + 输入摘要」判命中——"
        "某层失效则其后全部重建，这条规律在这里是数据结构而不是经验；"
        "所以本章 §2.2「多阶段构建与镜像瘦身」里「把 COPY 依赖清单放在 COPY 源码之前」"
        "不是风格问题，而是让失效点尽量后移",

        "§3.1 一、Docker Compose：服务依赖、网络、卷与健康检查 · 读 `docker/compose` 的 "
        "`pkg/compose/create.go`：它按 `depends_on` 与 `condition` 建依赖图并定启动顺序，"
        "`up.go` 负责等 healthcheck 通过再往下走——"
        "「死等 vs 直接报错」的循环依赖检测发生在建图阶段；"
        "这正对应本章 §3.2「12-Factor 与配置外置」之外的另一半："
        "配置外置解决「同一镜像跑多环境」，依赖编排解决「多容器按什么顺序起」",

        "§1.2 二、进程管理：systemd / pm2 / supervisor · 读 `systemd/systemd` 的 "
        "`man/systemd.service.xml`：它规定 `Restart=` / `RestartSec=` / `StartLimitBurst=` "
        "的精确含义（连重启节流都写在里面）；"
        "配套 `src/journal/journald.c` 说明结构化日志从哪来，"
        "`src/shared/logs-show.c` 是 `--since` / `--priority` 的过滤实现——"
        "这正是本章 §1.3「日志：journalctl 与 logrotate」"
        "为什么能「按字段查」而不是「按行 grep」的技术底子",

        "§4.1 一、CI/CD 流水线设计（GitHub Actions） · 读 `nektos/act` 的 "
        "`pkg/model/workflow.go`：它是 YAML 到结构体的映射"
        "（缺 `on` / `runs-on` 在这里就露馅），"
        "`pkg/model/planner.go` 按 `needs` 建 DAG 并算出可并行的层——"
        "「needs 指向不存在的 job」本地一跑就复现；"
        "本章 §4.2「环境与发布策略：蓝绿、金丝雀、滚动与回滚」"
        "要落在这张 DAG 上，所以顺序设计的本质是「哪些 job 可以并行、哪些必须串」",
    ],

    # ---------------- fs-ch09 TypeScript ----------------
    # 仓库序：microsoft/TypeScript / type-challenges/type-challenges / colinhacks/zod / sindresorhus/type-fest
    "fs-ch09": [
        "§1.1 为什么这样设计 · 读 `microsoft/TypeScript` 仓库的 `src/compiler/`"
        "（核心文件是 `checker.ts`）："
        "里面的 `getPropertyAccessType` 与结构类型判定直接对应本节——"
        "TS 判「A 能否赋给 B」只看 B 要求的属性在 A 上是否存在且类型相容，"
        "完全不看声明关系；"
        "这解释了本章 §1.4「结构类型的三个边界反例」里"
        "「空对象 `{}` 能赋给几乎所有接口」为什么成立",

        "§2.1 收窄的几种来源 · 先从 `type-challenges/type-challenges` 的 `easy` 到 `extreme` "
        "练条件类型与递归泛型，再回 `src/compiler/` 的 `checker.ts` 读 `narrowTypeByKind`："
        "题库让你先建立「类型是可以在编译期被计算的」直觉，"
        "源码告诉你收窄发生在 `if` / `typeof` / 判别式（`tagged union`）三个入口；"
        "配合 §2.2「为什么 `any` 是逃生舱而不是工具」——"
        "`any` 一旦进入表达式，后面的收窄全部失效，因为它的每个属性访问都是 `any`",

        "§2.1 收窄的几种来源（运行时对应物） · 读 `colinhacks/zod`：`z.infer` "
        "把校验结果回推成静态类型，正是本节「收窄」的运行时对应物——"
        "编译期的收窄只是「你怎么向编译器证明」，"
        "而 zod 是「你怎么向编译器证明这段外部数据确实是这个形状」；"
        "本章 §4.2「收尾：类型是文档，也是约束，但不是保证」说的就是这件事："
        "没有运行时校验时，类型在边界上是一句无凭据的断言",

        "§3.2 泛型不是越抽象越好 · 读 `sindresorhus/type-fest` 的几百个工具类型源码："
        "先读 `PartialDeep` / `PackageJson` 理解条件类型与映射类型的实战写法，"
        "再回头看它为什么为每一个小场景单独出一个类型"
        "（而不是做一个万能 `Deep<T>`）——"
        "那就是本节「泛型不是越抽象越好」的证据："
        "抽象层级每上一级，报错信息的可读性与推导性能都会下降",
    ],

    # ---------------- fs-ch10 Vue 3 + TypeScript + Pinia ----------------
    # 仓库序：vuejs/core / vuejs/pinia / vuejs/router / vuejs/rfcs
    "fs-ch10": [
        "§1.1 一、机制：Proxy 与依赖收集 · 读 `vuejs/core` 的 "
        "`packages/reactivity/src/effect.ts` 与同目录 `dep.ts`、`baseHandlers.ts`："
        "`effect.ts` 建 effect 树、`dep.ts` 用 Set 存订阅者、"
        "`baseHandlers.ts` 在 get 时 `track`、set 时 `trigger`；"
        "再读 `computed.ts` 的 dirty 标记，就回答了本节 §1.2 里"
        "「computed 什么时候才重算」——只有依赖脏了才重算，否则直接返回缓存值",

        "§3.1 一、写法、依赖与 Vuex 对照 · 读 `vuejs/pinia` 的 `packages/pinia/src/store.ts`："
        "`defineStore` 同时接受对象与函数两种入参，内部都归一成 "
        "reactive state + actions——"
        "这就是本节「两种写法不是两套机制」的源码依据；"
        "而 `storeToRefs` 是本章 §3.2「四个高频陷阱」里「解构丢响应式」的正解："
        "直接解构 `const { count } = store` 会把 proxy 拆成裸值",

        "§2.1 一、选型与两个高频坑 · 读 `vuejs/router` 的 `src/router.ts`："
        "守卫按 `beforeEach → 组件内钩子 → afterEach` 排序；"
        "路由切换后 store 该不该重置，取决于你把 store 放进守卫还是放进组件——"
        "本节「两个高频坑」里「跨路由共享的 store 状态残留」在这里有明确答案："
        "守卫里 `store.$reset()` 能清，组件里 `onUnmounted` 只能清自己持有的那部分",

        "§1.3 三、调试、对照与取舍 · 读 `vuejs/rfcs` 的 `active-rfcs/` 下响应式相关提案"
        "（ref 拆包、reactivity transform）：这些讨论解释了为什么模板里不写 `.value`、"
        "JS 里必须写——"
        "本节「调试」那一半的工具（`effectScope` 的 on 钩子、`triggerRef`）"
        "之所以存在，也是因为这些提案没有走到「自动拆包所有场景」；"
        "这与 §2.3「设计取舍与跨框架对照」一起说明：边界是设计决议，不是实现巧合",
    ],

    # ---------------- fs-ch11 Spring Boot 3 工程骨架 ----------------
    # 仓库序：spring-boot / spring-framework / spring-security / openjdk/jdk
    "fs-ch11": [
        "§1.2 二、把职责钉死在具体位置 · 读 `spring-projects/spring-boot` 的 "
        "`spring-boot-autoconfigure` 模块的 `AutoConfiguration.imports` 与 "
        "`@ConditionalOnMissingBean`：starter 只在你没自己声明时才装配——"
        "这就是本节「职责边界在框架里的落地方式」；"
        "注意 `@ConditionalOnMissingBean` 的判定发生在你定义的 Bean **之后**，"
        "所以想覆盖自动配置，只需声明同名同类型 Bean，不用排除自动配置类",

        "§2.2 二、匹配顺序与作用域 · 读 `spring-projects/spring-framework` 的 "
        "`spring-webmvc` 模块的 `org/springframework/web/servlet/mvc/method/annotation/` "
        "下 `ExceptionHandlerExceptionResolver`："
        "它按 `@ExceptionHandler` 的匹配精度挑方法，"
        "`@ControllerAdvice` 的 `basePackages` / `assignableTypes` 决定它盖住哪些 Controller——"
        "本节要讲的「作用域规则」就是这两条：越精确的 `@ExceptionHandler` 优先，"
        "多个 `@ControllerAdvice` 之间按 `@Order` 而不是声明顺序",

        "§2.4 四、事故复盘与协作边界 · 读 `spring-projects/spring-security` 的 "
        "`FilterChainProxy`：它在 DispatcherServlet 之前就拦掉未认证请求，"
        "`AuthenticationEntryPoint` 决定 401/403 的响应体——"
        "业务层拿不到原始异常，堆栈自然不会漏到前端；"
        "这解释了本节「协作边界」为什么必须落在过滤器层："
        "放在 Controller 里，未进 Controller 的请求就没被覆盖",

        "§3.2 二、边界、性能与文档 · 读 `openjdk/jdk` 里 `java.util.regex.Pattern` 的回溯实现："
        "`(a+)+$` 这类嵌套量词能把校验入口的 CPU 打满（ReDoS）——"
        "本节「校验也要限长限深」不是洁癖，而是这条回溯路径的代价随嵌套层数指数增长；"
        "实务判据是先限长度上限，再确保正则里没有「量词套量词」的可选组",
    ],

    # ---------------- fs-ch12 服务拆分与网关 ----------------
    # 仓库序：spring-cloud/spring-cloud-gateway / nestjs/nest / vercel/next.js / google/guava
    "fs-ch12": [
        "§2.1 一、职责边界：该管与不该管 · 读 "
        "`spring-cloud/spring-cloud-gateway` 的 `RoutePredicateHandlerMapping` "
        "与同模块的过滤器链：谓词决定「这个请求归哪条路由」，过滤器链决定「沿途改什么」——"
        "两段职责分开，就是本节「该管与不该管」的框架侧表达；"
        "本章 §2.2「四项核心能力与反模式」里的反模式，"
        "多半是把业务判断塞进了过滤器",

        "§1.1 一、先想清楚：为什么拆、按什么切 · 读 `nestjs/nest` 的 module/provider 模型："
        "它的边界设计（一个 module 显式声明 imports/providers/exports）与本节"
        "「按什么切」的判据同构——"
        "能写清「这个模块对外只暴露哪几个 provider」的服务边界才是真的，"
        "写不清的其实就是「一组文件的命名空间」",

        "§2.2 二、四项核心能力与反模式 · 读 `vercel/next.js` 的中间件与 BFF 用法"
        "（`middleware.ts` 与 `app/api/` 路由）：BFF 是「为某一前端定制的聚合层」，"
        "而框架里的 middleware 只能改请求/响应、不能做重业务——"
        "这个能力边界正好划出本节「四项核心能力」里"
        "「聚合」与「编排」该放在 BFF、不该放进网关的那条线",

        "§3.1 一、外置、隔离、热更新与密钥 · 读 `google/guava` 的 `RateLimiter`："
        "它是「令牌桶」的原语实现，"
        "而本节要讲的是「限流参数本身就是配置中心最常见的动态项」——"
        "把 `RateLimiter` 的速率做成可热更新的配置，"
        "就同时踩了「热更新」与「密钥/阈值治理」两条；"
        "注意 `RateLimiter` 是单机限流，集群维度要靠配置中心下发一致的配额",
    ],

    # ---------------- fs-ch13 前端测试与质量门禁 ----------------
    # 仓库序：microsoft/playwright / cypress-io/cypress / pact-foundation/pact-js / facebook/react
    "fs-ch13": [
        "§2.1 一、稳定的两条铁律 · 读 `microsoft/playwright` 的 "
        "`docs/src/api/class-page.md` 里 auto-waiting 与 actionability checks 两节："
        "可见、稳定、可接收事件三个条件同时满足才动手，"
        "等于把 `sleep` 换成「等状态」——"
        "这就是本节「两条铁律」的第一条；"
        "第二条「只断言用户可见的结果」则对应它强调的 locator 语义"
        "（按 role/label 定位而非 DOM 路径）",

        "§2.3 三、flaky 归因、工具差异与可观测 · 读 `cypress-io/cypress` 的 "
        "`packages/driver/src/cy/commands/actions/click.ts`："
        "时间旅行调试靠命令队列快照把每条命令执行后的 DOM 存下来，"
        "失败时能回放到出错那一步——"
        "与 Playwright 用 trace 达到的是同一目的；"
        "本节「工具差异」的关键不在 API，而在「失败时你能看到哪一刻的状态」",

        "§3.3 三、Pact 工作流与契约演进 · 读 `pact-foundation/pact-js` 的 `src/index.ts`："
        "mock server 按消费者写的期望返回并生成 pact 文件，"
        "提供方用 `Verifier` 回放同一份契约——"
        "「契约是产物，不是文档」；"
        "本节 §3.1 讲的「值在哪」也由此落地："
        "契约文件可以进 CI 当门禁（§3.2），而文档不能",

        "§2.2 二、组件测试与测试卫生 · 读 `facebook/react` 的 `packages/react/src/` "
        "下 `jsx/__tests__/` 等测试目录：框架自身的测试配 `scripts/jest` 的自定义环境，"
        "断言的是渲染出来的树而非实现细节——"
        "这正是本节「组件测试该断言的层次」；"
        "反过来说，一旦测试里出现对内部 state 变量名的断言，"
        "它就已经从组件测试退化成实现测试",
    ],

    # ---------------- fs-ch14 Agent × 全栈工程接缝 ----------------
    # 仓库序：vercel/ai / langchain-ai/langchain / gin-gonic/gin / huggingface/transformers
    "fs-ch14": [
        "§1.1 SSE 与 WebSocket 在协议层的差别 · 读 `vercel/ai` 的 "
        "`packages/ai/src/generate-text/stream-text.ts`："
        "它把模型增量转成 data stream 协议（`0:\"文本\"` 这种带前缀的行），"
        "工具调用带 `toolCallId`——"
        "本节「SSE 之所以够用」的原因就在这里：单向、可断点续传、走普通 HTTP；"
        "而本章 §3.1「每次工具调用都要有唯一 id」的来源也正是这个协议字段",

        "§2.5 幂等恢复：同一个 id 可以重入 · 读 `langchain-ai/langchain` 的 `libs/core`："
        "`Runnable` 组合子与 `with_retry` 让重试只重放同一次调用，"
        "跨轮状态由外层 graph / checkpoint 保存——"
        "这就对应本节「同一个 id 可以重入」；"
        "关键区别是「重试」与「重入」的边界："
        "重试假设副作用没发生，重入必须假设可能已发生，所以要有 §3.2 的去重记录",

        "§1.2 网关透传流式的三种实现路径 · 读 `gin-gonic/gin` 的 `context.go` "
        "的 `Stream` 方法与 SSE 相关中间件：逐块 flush 的最小实现"
        "（不设 `Content-Length`、显式 `Flush`）；"
        "这正是本节「三种实现路径」里最直接的一种；"
        "而 `middleware/` 里挂限流中间件正是本章 §4.3「三种经典限流算法」的落地位置——"
        "注意流式响应一旦开始，限流只能按「连接数」而不能按「请求数」计",

        "§4.1 token 计量：输入与输出分开算 · 读 `huggingface/transformers` 的 "
        "`src/transformers/tokenization_utils.py`：`encode` / `decode` 决定"
        "「一段文本值多少 token」，同一句中文不同 tokenizer 能差一倍——"
        "这就是本节「输入输出分开算」的前提；"
        "§4.4「降级与预算」里的预算阈值必须按实际 tokenizer 估，"
        "用字符数折算会在中文场景系统性低估",
    ],

    # ---------------- fs-ch15 Go + Gin 后端 ----------------
    # 仓库序：gin-gonic/gin / gofiber/fiber / golang/go / spring-framework
    "fs-ch15": [
        "§2.1 一、路由与中间件机制 · 读 `gin-gonic/gin` 的 `tree.go` 与 `routergroup.go`、"
        "`context.go`：`tree.go` 是压缩前缀树，"
        "`routergroup.go` 的 `Use` 把 handler 拼成 `HandlersChain`，"
        "`context.go` 的 `Next()` 用索引往前走——"
        "与 Express 的数组栈是同一模型，差别只在「路径匹配是树而不是正则」；"
        "这也解释本节 §2.2「与其他框架对照」里路由性能差距的来源",

        "§2.2 二、与其他框架对照 · 读 `gofiber/fiber` 的 `app.go`："
        "它的路由与 `Next()` 形状和 Gin 几乎一样，"
        "但底层跑在 `fasthttp` 上、复用 `RequestCtx` 减少分配——"
        "本节「与其他框架对照」的核心点就在「API 相同、内存模型不同」；"
        "代价是 `fasthttp` 的 ctx 不能跨 goroutine 持有，"
        "这与 Gin 可以直接把 `*http.Request` 传下去是两条契约",

        "§1.1 一、模型本体：goroutine 与 channel · 读 `golang/go` 的 "
        "`src/runtime/proc.go` 的 GMP 调度与 `src/runtime/chan.go` 的 `hchan` 环形缓冲："
        "channel 满时 `send` 阻塞并挂进 `sendq`——"
        "「不要通过共享内存通信」的机器实现；"
        "本节 §1.2「与其他运行时对照」里「Go 的 goroutine 比线程轻在哪」"
        "就在这里：栈初始 2KB 可增长、调度在用户态完成",

        "§3.2 二、接口契约与跨语言对照 · 读 `spring-projects/spring-framework` 的 "
        "`spring-webmvc` 模块的 `org/springframework/web/servlet/mvc/method/annotation/` "
        "下 `ResponseEntityExceptionHandler`："
        "它把异常统一映射成 `ProblemDetail`（RFC 9457），"
        "和 Go 侧「error 作为值、显式返回」是两条路——"
        "一个靠容器兜底、一个靠调用方检查；"
        "这就是本节「跨语言对照」最值得对照的一处："
        "容器兜底能保证「不漏」，显式返回能保证「不隐式」",
    ],
}
