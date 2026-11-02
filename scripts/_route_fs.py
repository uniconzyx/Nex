# -*- coding: utf-8 -*-
"""来源颗粒度 · fullstack 收尾批次（12 章）。

两类问题：
  A. fs-ch02~08 三章共用一组「前端通用仓库」，且 ch04 起（Node/数据库/认证/实战/部署）
     这组仓库里根本没有对应代码 → 不只是「读法一样」，是「读法不可能对」。这里连仓库一起换掉。
  B. fs-ch10/11/13/14/15 的 goals.md 表格其实已写了章节级路线，但 manifest 的
     github_notes 还是「按本章小节定位相关目录」占位句 → 审计按 manifest 判重，
     于是被算成 5 章复制。这里把两侧对齐（顺带修掉指向不存在小节的 § 引用）。

口径见 scripts/audit_sources.py：notes 元组在同学科内唯一 = 章节级路线。
"""
import io
import json
import os
import re

from _route_granularity import apply

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')

SNAP_OLD = '2026-10-27'
SNAP_NEW = '2026-11-02'

# ---------------------------------------------------------------- A. 连仓库一起换
# (repo, star, 对应本章, 读什么)
FS_REPOS = {
    'fs-ch02': [
        ('w3c/csswg-drafts', 4901, '§2.2 box-sizing · §2.3 格式化上下文',
         '规范原文：`css-box-3/Overview.bs` 里 box-sizing 与 margin 合并的定义、`css-display-3/Overview.bs` 里 flow-root 生成 BFC 的条文——「margin 为什么穿透父元素」在这里是规范，不是经验'),
        ('Chalarangelo/30-seconds-of-code', 129352, '§5 实用片段',
         '片段库：读 `snippets/` 下带 `css` / `browser` 标签的条目（水平垂直居中、等分布局、清除浮动），每条都是可直接粘的最小实现，正好对照 §5 那四行 CSS 改了三天的那件事'),
        ('yangshun/front-end-interview-handbook', 44008, '§1.1 语义化 · §3.3 重排与重绘',
         '题库：`questions/html-questions.md` 用「全 div 堆出来的页面哪里坏了」讲语义化，`questions/css-questions.md` 把 reflow / repaint / 合成层分开问——与 §1.1、§3.3 的判据一一对应'),
    ],
    'fs-ch03': [
        ('tc39/ecma262', 15705, '§1.2 相等性三兄弟 · §3.1 原型链',
         '规范原文：`spec.html` 搜 `IsLooselyEqual` 与 `IsStrictlyEqual` 两段算法，`==` 的转换顺序（先 ToPrimitive，valueOf 优先于 toString）是逐条写死的，`[] == ![]` 可以照算法走一遍'),
        ('getify/You-Dont-Know-JS', 184837, '§2.1 TDZ · §2.2 this 五条规则',
         '书稿源码：`scope-closures/` 卷把提升与 TDZ 按「编译期 / 执行期」两段讲透，`objects-classes/` 卷把 this 的四类绑定排成判定树——对应 §2.1、§2.2，比背口诀可靠'),
        ('yangshun/front-end-interview-handbook', 44008, '§1.1 原始类型 · §4.2 组合子取舍',
         '题库：`questions/javascript-questions.md` 把 `typeof null`、`NaN !== NaN`、装箱拆箱列成快问快答；Promise 串行/并行/竞速的选择题对应 §4.2 的组合子取舍'),
    ],
    'fs-ch04': [
        ('nodejs/node', 123194, '§1.2 队列顺序 · §3.1 背压',
         '运行时本体：`lib/internal/process/task_queues.js` 是 nextTick 与微任务队列的真实调度，`lib/internal/streams/readable.js` 里 `highWaterMark` 与 `readableFlowing` 的状态迁移就是 §3.1 背压的机器版本'),
        ('expressjs/express', 69585, '§2.1 手写 HTTP 服务 · §2.3 中间件',
         '工业实现：`lib/application.js` 的 `app.use` 把中间件压进栈、`app.handle` 作为 `http.createServer` 的回调把 req/res 交出去；四参数错误中间件的识别就发生在这一层'),
        ('koajs/koa', 35683, '§2.3 洋葱模型',
         '对照实现：`lib/application.js` 的 `callback()` 用 `compose(this.middleware)` 把数组折成嵌套函数，`await next()` 前后各写一段——这就是 §2.3「进去一层、出来一层」的原始代码'),
    ],
    'fs-ch05': [
        ('sqlite/sqlite', 10890, '§1.2 索引结构 · 最左前缀',
         '存储引擎本体：`src/btree.c` 的 `sqlite3BtreeInsert` 与 `balance()` 演示 B+ 树怎么分裂合并，`src/where.c` 的 `whereBegin` 决定能用哪个索引前缀——「最左前缀」在这里是可用性判定，不是口诀'),
        ('graphql/dataloader', 13391, '§2.2 N+1',
         '修复范式：`src/index.js` 的 `enqueuePostPromiseJob` 把一个 tick 内的 key 全攒进 `_batch`，再一次性调 `batchLoadFn`——「用操作计数发现、用批量合并修复」的教科书实现'),
        ('OAI/OpenAPI-Specification', 31291, '§4.1 契约优先',
         '规范原文：`versions/3.1.0.md` 里 `paths` / `components/schemas` 的结构与 `$ref` 复用规则，`versions/3.0.3.md` 的 `nullable` 写法差异——先写契约再生成类型时，这两份是唯一权威'),
    ],
    'fs-ch06': [
        ('panva/jose', 7859, '§2.1 三段结构与签名',
         '规范级实现：`docs/jws/flattened/sign/README.md`、`docs/jws/compact/verify/functions/compactVerify.md` 说明签名的输入是 `BASE64URL(header).BASE64URL(payload)` 这串字节，不是解析后的 JSON——§2.1「签的是串不是对象」由此而来'),
        ('auth0/node-jsonwebtoken', 18182, '§2.2 alg 混淆 · §3.1 无法主动失效',
         '坑位本体：`verify.js` 的 `options.algorithms` 白名单是唯一能挡住 `alg:none` 的地方（不传就按 header 里声明的算法验）；`sign.js` 的 `expiresIn` 只写进 exp，服务端不查黑名单就撤不掉——§3.1 的固有缺陷'),
        ('OWASP/CheatSheetSeries', 33847, '§3.2 密码存储 · §4.2 CSRF/XSS',
         '权威基线：`cheatsheets/Password_Storage_Cheat_Sheet.md` 给了 argon2id 的参数下限与「不加盐等于送彩虹表」；`Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.md`、`Cross_Site_Scripting_Prevention_Cheat_Sheet.md` 分别对应 §4.2 的两类漏洞'),
    ],
    'fs-ch07': [
        ('realworld-apps/realworld', 84363, '§1 分层与契约 · §3.3 三态呈现',
         '全栈样板：`docs/src/content/docs/specifications/frontend/api.md` 把「页面 → 数据层 → API」的边界写成契约，`backend/error-handling.md` 规定统一错误体——十几种语言实现共用同一份契约，正是 §1.2 的实物'),
        ('TanStack/query', 50520, '§2.2 服务端状态 · 乐观更新',
         '状态层本体：`packages/query-core/src/query.ts` 的 `staleTime` 与 `gcTime` 两个时钟把「新鲜度」和「回收」拆开；`mutation.ts` 的 `onMutate` / `onError` 回滚就是 §2.2 乐观更新的标准写法'),
        ('vercel/next.js', 143463, '§4.1 懒加载与代码分割',
         '框架实现：`packages/next/src/client/` 的 `dynamic` 与路由级 chunk——构建期按入口拆 bundle、运行期按需拉，「首屏只付首屏的钱」在框架里是编译期决定，不是运行时的 `lazy()`'),
    ],
    'fs-ch08': [
        ('moby/buildkit', 10353, '§2.1 缓存是前缀链 · §2.2 多阶段',
         '构建器本体：`frontend/dockerfile/dockerfile2llb/convert.go` 把 Dockerfile 逐指令翻译成 LLB 图，`cache/manager.go` 按指令 + 输入摘要判命中——某层失效则其后全部重建，这条规律在这里是数据结构'),
        ('docker/compose', 38568, '§3.1 服务依赖与健康门',
         '编排实现：`pkg/compose/create.go` 按 `depends_on` 与 `condition` 建依赖图并定启动顺序，`up.go` 负责等 healthcheck 通过再往下走——「死等 vs 直接报错」的循环依赖检测发生在建图阶段'),
        ('systemd/systemd', 16979, '§1.2 unit 文件 · §1.3 日志',
         '语义权威：`man/systemd.service.xml` 规定 `Restart=` / `RestartSec=` / `StartLimitBurst=` 的精确含义（连重启节流都写在里面），`src/journal/journald.c` 说明结构化日志从哪来，`src/shared/logs-show.c` 是 `--since` / `--priority` 的过滤实现'),
        ('nektos/act', 72516, '§4.1 workflow → job → step',
         '本地执行器：`pkg/model/workflow.go` 是 YAML 到结构体的映射（缺 `on` / `runs-on` 在这里就露馅），`pkg/model/planner.go` 按 `needs` 建 DAG 并算出可并行的层——「needs 指向不存在的 job」本地一跑就复现'),
    ],
}

# ---------------------------------------------------------------- B. 只对齐 manifest 读法
NOTES_ONLY = {
    'fs-ch10': {
        'vuejs/core': ('§1.1 Proxy 依赖收集 · §1.2 computed 派发',
                       '`packages/reactivity/src` 的 `effect.ts` 建 effect 树、`dep.ts` 用 Set 存订阅者、`baseHandlers.ts` 在 get 时 `track`、set 时 `trigger`；`computed.ts` 的 dirty 标记回答 §1.2「computed 什么时候才重算」'),
        'vuejs/pinia': ('§3.1 两种写法 · §3.3 反模式',
                        '`src/store.ts` 的 `defineStore` 同时接受对象与函数两种入参，内部都归一成 reactive state + actions——§3.1「两种写法不是两套机制」的源码依据；`mapHelpers` 里的 `storeToRefs` 是 §3.3 解构丢响应式的正解'),
        'vuejs/router': ('§2.1 ref 与生命周期边界',
                         '`src/router.ts` 的守卫按 `beforeEach → 组件内钩子 → afterEach` 排序；路由切换后 store 该不该重置，取决于你把 store 放进守卫还是放进组件——§2.1 的边界问题在这里有明确答案'),
        'vuejs/rfcs': ('§1.3 .value 的由来 · §2.3 设计取舍',
                       '`active-rfcs/` 里响应式相关提案（ref 拆包、reactivity transform）的讨论解释了为什么模板里不写 `.value`、JS 里必须写——§1.3 与 §2.3 的边界是设计决议，不是实现巧合'),
    },
    'fs-ch11': {
        'spring-projects/spring-boot': ('§1.1 三层与依赖方向',
                                        '`spring-boot-autoconfigure` 的 `AutoConfiguration.imports` + `@ConditionalOnMissingBean`：starter 只在你没自己声明时才装配——分层边界在框架里的落地方式'),
        'spring-projects/spring-framework': ('§2.1 统一异常收口 · §2.2 匹配顺序',
                                            '`spring-webmvc` 的 `ExceptionHandlerExceptionResolver` 按 `@ExceptionHandler` 的匹配精度挑方法，`@ControllerAdvice` 的 `basePackages` / `assignableTypes` 决定它盖住哪些 Controller——§2.2 的作用域规则'),
        'spring-projects/spring-security': ('§2.3 可观测性 · §1.2 职责边界',
                                            '`FilterChainProxy` 在 DispatcherServlet 之前就拦掉未认证请求，`AuthenticationEntryPoint` 决定 401/403 的响应体——业务层拿不到原始异常，堆栈自然不会漏到前端（§2.4）'),
        'openjdk/jdk': ('§3.2 边界与性能',
                       '`java.util.regex.Pattern` 的回溯实现：`(a+)+$` 这类嵌套量词能把校验入口的 CPU 打满（ReDoS）——§3.2「校验也要限长限深」不是洁癖'),
    },
    'fs-ch13': {
        'microsoft/playwright': ('§2.1 稳定的两条铁律',
                                 '`docs` 的 auto-waiting 与 actionability checks：可见、稳定、可接收事件三个条件同时满足才动手，等于把 `sleep` 换成「等状态」；`packages/playwright-core/src/server` 里每个 action 都过这套检查'),
        'cypress-io/cypress': ('§2.3 工具差异与可观测',
                               '时间旅行调试靠命令队列快照：`packages/driver/src/cy` 把每条命令执行后的 DOM 存下来，失败时能回放到出错那一步——与 Playwright 用 trace 达到的是同一目的'),
        'pact-foundation/pact-js': ('§3.1 消费者驱动契约 · §3.3 Pact 工作流',
                                    '`packages/core` 的 mock server 按消费者写的期望返回并生成 pact 文件，提供方用 `Verifier` 回放同一份契约——「契约是产物，不是文档」'),
        'facebook/react': ('§1.1 分层与测试替身 · §2.2 组件测试',
                           '框架自身的测试基建：`packages/react/src/__tests__` 配 `scripts/jest` 的自定义环境，断言的是渲染出来的树而非实现细节——这正是 §2.2 组件测试该断言的层次'),
    },
    'fs-ch14': {
        'vercel/ai': ('§1.1 SSE · §3.1 callId',
                      '`packages/ai/core/generate-text/stream-text.ts` 把模型增量转成 data stream 协议（`0:"文本"` 这种带前缀的行），工具调用带 `toolCallId`——§3.1 唯一 id 的来源就是协议本身'),
        'langchain-ai/langchain': ('§2.5 幂等恢复 · §3.2 重试幂等',
                                   '`libs/core` 的 `Runnable` 组合子与 `with_retry`：重试只重放同一次调用，跨轮状态由外层 graph / checkpoint 保存，对应 §2.5「同一个 id 可以重入」'),
        'gin-gonic/gin': ('§1.2 网关透传流式 · §4.3 限流',
                          '`context.go` 的 `Stream` 与 `sse.go` 的 `SSEvent` 是逐块 flush 的最小实现（不设 `Content-Length`、显式 `Flush`）；`middleware/` 里挂限流中间件正是 §4.3 的落地位置'),
        'huggingface/transformers': ('§4.1 token 计量',
                                     '`src/transformers/tokenization_utils.py` 的 `encode` / `decode` 决定「一段文本值多少 token」，同一句中文不同 tokenizer 能差一倍——§4.1 输入输出分开算的前提'),
    },
    'fs-ch15': {
        'gin-gonic/gin': ('§2.1 路由树 · §2.2 中间件',
                          '`tree.go` 是压缩前缀树，`routergroup.go` 的 `Use` 把 handler 拼成 `HandlersChain`，`context.go` 的 `Next()` 用索引往前走——与 Express 的数组栈是同一模型'),
        'gofiber/fiber': ('§2.3 框架对照',
                          '`app.go` 的路由与 `ctx.go` 的 `Next()` 形状和 Gin 几乎一样，但底层跑在 `fasthttp` 上、复用 `RequestCtx` 减少分配——对照点在于「API 相同、内存模型不同」'),
        'golang/go': ('§1.1 goroutine 与 channel · §3.1 error 即值',
                      '`src/runtime/proc.go` 的 GMP 调度与 `src/runtime/chan.go` 的 `hchan` 环形缓冲：channel 满时 `send` 阻塞并挂进 `sendq`——「不要通过共享内存通信」的机器实现'),
        'spring-projects/spring-framework': ('§2.3 中间件对照 · §3.3 契约对照',
                                             '`spring-web` 的 `ResponseEntityExceptionHandler` 把异常统一映射成 `ProblemDetail`（RFC 9457），和 Go 侧「error 作为值、显式返回」是两条路：一个靠容器兜底，一个靠调用方检查'),
    },
}


def _fmt_row(i, repo, stars, sec, what):
    return '| %d | [%s](https://github.com/%s) | %s | %s | %s |' % (
        i, repo, repo, format(stars, ','), sec, what)


def replace(subject, cid, rows):
    """整组替换：manifest 的 github / github_stars / github_notes + goals.md 表格与出处行。"""
    mf_path = os.path.join(CONTENT, subject, '_manifest.json')
    manifest = json.loads(io.open(mf_path, encoding='utf-8').read())
    unit = next((u for u in manifest['chapters'] if u['id'] == cid), None)
    if unit is None:
        print('[skip] manifest 无此章', cid)
        return
    res = unit.setdefault('resources', {})
    res['github'] = [r[0] for r in rows]
    res['github_stars'] = [r[1] for r in rows]
    res['github_notes'] = ['%s %s' % (r[2], r[3]) for r in rows]

    gp = os.path.join(CONTENT, subject, cid, 'goals.md')
    text = io.open(gp, encoding='utf-8').read()
    lines = text.split('\n')

    # 只替换「本章 GitHub 学习路线」小节里那张表的数据行：
    # 从该标题往下找第一组连续 `| n |` 行，遇到第一个非行就停——
    # 不能全文件扫（B 站表、论文表的数据行也以 `| 1 |` 开头，会连坐删掉）。
    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith('## 本章 GitHub'))
    except StopIteration:
        print('[warn] 缺 GitHub 小节', cid)
        return
    idx = []
    for i in range(start, len(lines)):
        if re.match(r'^\| \d+ \|', lines[i]):
            idx.append(i)
        elif idx:
            break
    if not idx:
        print('[warn] 表格未命中', cid)
        return
    head, tail = idx[0], idx[-1]
    new_rows = [_fmt_row(i + 1, *r) for i, r in enumerate(rows)]
    lines[head:tail + 1] = new_rows

    out = '\n'.join(lines)
    out = out.replace(SNAP_OLD, SNAP_NEW)
    out = re.sub(r'共 \d+ 个 GitHub 来源', '共 %d 个 GitHub 来源' % len(rows), out)
    out = re.sub(r'^- GitHub 资源（见 `_manifest\.json`）：.*$',
                 '- GitHub 资源（见 `_manifest.json`）：' +
                 '、'.join('%s（%d★）' % (r[0], r[1]) for r in rows) + '。',
                 out, flags=re.M)
    io.open(gp, 'w', encoding='utf-8', newline='\n').write(out)
    print('[ok] %-9s 换仓 %d 个 → %s' % (cid, len(rows), ', '.join(r[0] for r in rows)))

    io.open(mf_path, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


def main():
    for cid, rows in FS_REPOS.items():
        replace('fullstack', cid, rows)
    apply('fullstack', NOTES_ONLY)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
