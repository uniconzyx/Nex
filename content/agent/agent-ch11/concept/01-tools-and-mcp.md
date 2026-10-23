# 工具层：function calling 的 schema、幂等与权限，MCP 的工具发现

> LLM 是大脑，工具是手。但手有三重风险：**拿错东西**（参数不合规）、
> **重复劳动**（重试变成重复副作用）、**乱拿东西**（越权访问）。
> 本章 tech_load 要求 3 个工具（含 MCP server）——工具层的三件事：
> schema 校验（ex02）、幂等键（ex03）、权限最小化，一个都不能少。
> 先记住一句话：**schema 拦形状，幂等拦重复，沙箱拦越权，三层是串联关系不是并列关系。**

## 1. 工具 schema 设计与参数校验：把模型的「自由发挥」拦在执行前

中立陈述：function calling 的工具有两部分——给人看的**自然语言描述**
（什么时候用、输入什么）和给机器校验的 **schema**（字段、类型、必填、枚举、范围）。
模型生成的是「看似 JSON」的文本，真实错误率不低：类型错（数字当字符串）、
缺必填字段、枚举越界（`priority: urgent` 而枚举只有 `low/normal/high`）、
白名单外字符（计算表达式里混入千分位逗号）。**schema 校验器的职责是在执行前
把这些错误分成三类**：可语义等价修复的（去千分位、数字转字符串、枚举归位、
范围截断）、不可猜的（缺必填、缺 pattern——拒发并把错误回喂给模型重试）、
schema 盲区的（除零、权限、业务语义——只能靠执行期异常与沙箱兜底）。

```
模型输出 ──▶ schema 校验 ──▶ 分类 ──▶ 执行
              │            ├─ 可修复（语义等价变换）─▶ 修复后放行
              │            ├─ 不可猜（缺必填/pattern）─▶ 拒发，错误回喂 → 模型重试
              │            └─ 盲区（除零/越权）─────▶ 执行期异常 + 沙箱
```

```python
def validate(call, schemas):
    errs = []
    if call["tool"] not in schemas:            # 工具白名单：防幻觉工具名
        return [f"未知工具 {call['tool']}"]
    spec = schemas[call["tool"]]
    for f in spec["required"]:                 # 必填缺失不可猜 → 拒发
        if f not in call["args"]:
            errs.append(f"缺必填 {f}")
    for f, v in call["args"].items():
        rule = spec["properties"].get(f)
        if rule is None:
            errs.append(f"未知字段 {f}")
        elif rule["type"] == "string" and not isinstance(v, str):
            errs.append(f"{f} 应为 string")
        if "enum" in rule and v not in rule["enum"]:
            errs.append(f"{f}={v} 不在枚举 {rule['enum']}")
    return errs
```

| 错误形态 | 实例 | 处置 | 为什么 |
|---|---|---|---|
| 类型错 | `query: 2024`（int） | 修复：`str(2024)` | 语义等价 |
| 枚举越界 | `priority: "urgent"` | 修复：归位到 `high` | 意图明确 |
| 范围越界 | `retries: 10`（max 5） | 修复：截到 5 | 与意图不冲突 |
| 字符越界 | `expr: "1,234.50*2"` | 修复：剔白名单外字符 | 千分位是习惯不是语义 |
| 缺必填 | 缺 `body` | 拒发 + 回喂错误 | 猜内容 = 编造 |
| pattern 缺失 | `to: "no-at-sign"` | 拒发 | 邮箱格式不可猜 |
| 语义错误 | `expr: "8450/0"` | schema 放行，执行期炸 | 形状合法 ≠ 语义合法 |

工具描述本身也是 schema 的一部分：描述写得差，模型选错工具、传错参数的概率直线上升。
工程判据是**「描述里能回答三个问题」**：这个工具什么时候用（触发条件）、
输入每个字段的格式与示例、失败时返回什么（错误码要能被模型理解并换策略）。

## 2. 幂等与副作用：重试为什么不能变成重复下单

中立陈述：有副作用的工具（发邮件、下单、写库、调用第三方）面临一个结构性困境：
**客户端超时不等于服务端未执行**。ack 丢失时重试是必然动作，而副作用不可回滚——
没有幂等机制，三次重试就是三次下单。幂等键的计算口径是
**工具名 + 归一化参数的哈希**：参数按键排序（顺序无关），并剔除 `nonce`、
`timestamp` 这类每次调用必然不同的字段——不剔它们，键永远不同，抑制完全失效。
调用命中已有键时，返回首次执行结果（`replayed=True`），调用方无感。
注意边界：**参数 genuinely 不同必须放行**（换收件人是新意图），
幂等抑制的是重复，不是新意图。

```
attempt-1 首次发送  ─┐
attempt-2 超时重试  ─┼─▶ 同一 idem_key ─▶ 首次执行 + 2 次抑制（回放首次结果）
attempt-3 带 nonce  ─┤   （nonce 被剔除，否则键不同、抑制失效）
attempt-4 换收件人  ─┘   ─▶ 新 idem_key ─▶ 新执行（新意图放行）
```

```python
def idem_key(tool, args, drop=("nonce", "ts")):
    canon = {k: v for k, v in sorted(args.items()) if k not in drop}
    return hashlib.sha256((tool + json.dumps(canon, sort_keys=True)).encode()).hexdigest()[:12]
```

真实系统里键还要带 **TTL 与租约**：无限回放缓存会让「过期的首次结果」被反复返回；
跨服务的幂等则要把键落到共享存储（Redis/DB），不能只存在于进程内存。

## 3. 权限最小化、沙箱与 MCP 的工具发现

中立陈述：工具权限的三条线——**最小化**（只给完成任务所需的最小权限集：
读文件工具不给写、查订单工具不给退款）、**沙箱**（代码执行类工具隔离文件系统/
网络/进程，白名单字符只是最弱的一层）、**审计**（每次调用落 who/when/args/result）。
MCP（Model Context Protocol）把「工具怎么被发现和调用」标准化成协议：
client 连接 server 后先 `list_tools` 拿工具清单（含每个工具的 `inputSchema`），
模型选定工具后 `call_tool` 带参数执行。它的价值不在性能而在**生态分工**——
工具方按协议写一个 server，任何 MCP client 都能用；权限、鉴权、沙箱在 server 侧实施，
不依赖模型自觉。

```
MCP client（Agent）                MCP server（工具方）
      │                                   │
      │── initialize（握手/能力协商）──────▶│
      │◀───────── serverInfo ──────────────│
      │── tools/list（工具发现）───────────▶│
      │◀───── 工具清单 + inputSchema ──────│
      │── tools/call（带 schema 校验后参数）▶│
      │◀───── 结果 / 错误（回喂模型）───────│
```

工程判据：工具清单要**按会话裁剪**（20 个工具全量塞给模型，选错率显著上升——
经验判断，可按 top-k 相关检索裁）；`inputSchema` 就是第 1 节的 schema，
校验逻辑应该在 client 侧做一遍（早失败）、server 侧再做一遍（防绕过）。

---

## 三视角解析

### 🧑‍💻 程序员视角

- 校验器放两处：client 侧早失败省 token，server 侧防绕过。两处用同一份 schema，
  别写两个实现——它们一定会漂移。
- 幂等键的字段剔除清单要显式维护：`nonce/ts/request_id/trace_id` 全剔，
  漏一个字段，抑制率就从 100% 掉到 0，而监控上看不出来（请求都返回 200）。
- 拒发时把错误信息回喂给模型是 ReAct 循环的 observation：`{"error": "缺必填 body"}`
  比静默失败有用一万倍；回喂文本要让模型能定位到具体字段。
- 代码执行类工具的白名单字符是必要条件不是充分条件：`eval` 即使字符白名单也可能
  `8450/0` 炸，还可能 `2**999999999` 烧 CPU——要配超时、内存上限、禁内省属性。
- MCP server 的鉴权别偷懒：stdio server 默认信任本地 client，一旦暴露成 remote server，
  OAuth/scope 必须补上，否则任何能连上的人都拿到了你全部工具的权限。

### 🎓 博士生视角

- function calling 的历史脉络：从 GPT-3 时代的「工具使用提示 + 正则解析」，
  到 OpenAI function calling（2023.6）把结构化调用变成模型的一等能力，
  再到 MCP（2024 末）把「工具描述与发现」从模型厂商的私有格式中解耦——
  演进主线是**接口标准化与生态开放**，不是模型能力的突变。
- 从形式化视角，schema 校验是一个**类型系统**问题：模型输出是「带噪声的程序」，
  校验器是 type checker，修复是受限的 program repair。可证明安全的修复只有
  「语义等价变换」一类；其余都是启发式——这解释了为什么工程上必须保留「拒发」分支。
- 幂等性的理论来源是分布式系统的 at-least-once / at-most-once / exactly-once
  三态：重试语义只能做到 at-least-once，exactly-once 是效果等价——
  「at-least-once 执行 + 幂等去重」在数学上不等于 exactly-once（有窗口期），
  但工程上足够，前提是接受窗口内的重复并配人工对账。
- 工具选择的准确率是 Agent 端到端成功率的第一级漏斗：工具描述空间大时
  「选错工具」比「参数错」更致命（做了但做错事），这是工具检索/裁剪问题的动机。

### 📚 考研者视角

- 必会概念链：**function calling = 工具描述 + 参数 schema + 结果回传**；
  MCP = 工具发现（list）→ 调用（call）→ 生命周期管理的标准协议，
  与「直接写 function calling」的区别在标准化与生态，不在能力。
- 常考对比：**幂等与非幂等操作**——GET/PUT 幂等、POST 非幂等；
  「客户端超时 ≠ 服务端未执行」是重试风暴的根因，必考简答。
- 计算口径：幂等键 = hash(工具名 + 归一化参数)，归一化 = 排序 + 剔除非语义字段；
  给定一组调用能判断哪些会被抑制、哪些会放行。
- 易混概念：**schema 校验与业务校验**——前者查形状（类型/必填/枚举），
  后者查语义（金额=数量×单价、税率合法）；除零属于业务/执行期，
  schema 合法照样炸，别把两道闸混为一谈。
- 简答题模板：「设计一个带副作用的工具调用链，说明你怎么保证 exactly-once 效果」——
  答题骨架：客户端重试（at-least-once）+ 服务端幂等键去重 + 键带 TTL/租约
  + 承认窗口期 + 人工对账兜底。
