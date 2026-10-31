# -*- coding: utf-8 -*-
"""为 9 个新章的 concept 文件插入 ASCII 图表（渲染器只支持代码块内的等宽文本，
故用 ```text 围栏承载 ASCII 图，确保 App 内可见）。

用法：python scripts/_add_diagrams_new.py
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

# (subject, chapter, h2_start, diagram_text)
# h2_start：该 concept 文件里某个二级标题行开头，图插在它后面
INS = [
    ("fullstack", "fs-ch10", "## 依赖收集：effect 与 dep", r"""```text
   reactive(obj.x)          effect(fn)
        │                        │
        ▼                        ▼
   ┌─────────┐   track()   ┌──────────┐
   │  dep: x  │◀───────────│  active   │  读 obj.x 时把 effect 登记为依赖
   └─────────┘             │  effect   │
        ▲                   └──────────┘
        │   trigger()               │
        └────── obj.x = new ────────┘  写时反向通知 effect 重跑
```"""),

    ("fullstack", "fs-ch11", "## 经典三层：controller / service / repository", r"""```text
   请求 ─▶ Controller ── 只做收口(参数/DTO) ─▶ Service ── 业务 & 事务 ─▶ Repository ──▶ DB
             │                                      │                     │
             └──── DTO ⇄ Entity 转换边界 ────────────┘                Entity/Model
   禁止：Controller 直连 DB / Repository 反向调 Service / 跨层穿透
```"""),

    ("fullstack", "fs-ch12", "## 网关该管什么", r"""```text
   client ─▶ Gateway ──┬─ 路由     ─▶ service A
                       ├─ 鉴权     ─▶ service B
                       ├─ 限流     ─▶ (超阈值则拒绝 429)
                       └─ 聚合(BFF)─▶ 多服务扇出后合并
   网关不管：具体业务校验、DB 连接、领域计算（那是服务的事）
```"""),

    ("fullstack", "fs-ch13", "## 三层各自负责什么", r"""```text
        /\
       /E2E\        ← 少而慢：验端到端关键路径
      /----\
     / 集成 \       ← 中：模块协作、外部依赖
    /------\
   / 单元   \      ← 多而快：基底，占绝大多数
  /----------\
  倒金字塔(反例)：E2E 一堆、单测没几个 → 一改就红、定位慢
```"""),

    ("fullstack", "fs-ch14", "## SSE 与 WebSocket 在协", r"""```text
   Agent ──SSE 分块──▶ Gateway ──SSE 分块──▶ 浏览器
     ▲   (cancel)         ▲   (cancel)
     └─────────────────────┘   断线重连用 last-event-id 续传
   网关只透传流，不缓冲整段；背压从下游往上游反压
```"""),

    ("fullstack", "fs-ch14", "## 每次工具调用都要有唯一 id", r"""```text
   tool call ──callId=abc──▶ 去重表 ──首次──▶ 真正执行 → 结果
      (重试)   callId=abc ──▶ 去重表 ──命中──▶ 直接返回已存结果
   审计日志：callId + 输入哈希 + 输出哈希 → 哈希链，篡改即可检出
```"""),

    ("fullstack", "fs-ch15", "## Goroutine 有多轻", r"""```text
   G(goroutine) ─▶ P(逻辑处理器, 数量≈CPU) ─▶ M(系统线程) ─▶ 核
        │                │
        └──── channel 通信 ──── 代替「共享内存 + 锁」
   「不要通过共享内存来通信，而要通过通信来共享内存」
```"""),

    ("ai", "ai-ch12", "## 第一段：规则过滤（cheap，先挡掉", r"""```text
   原始语料 → 规则过滤 → 语义去重 → 训练集污染检测 → 留验隔离 → SFT 训练
                │           │            │              │
              去脏/短/重    SimHash    与评测集      train / valid
                          near-dup     重叠率         / test 分开
```"""),

    ("ai", "ai-ch13", "## 显存账：KV Cache 到底吃多少", r"""```text
   请求A: [block0][block1][block2]     物理块池 (PagedAttention)
   请求B: [block0][block3]             block1/2/3 可跨请求复用，不再连续占满
   传统: 每请求预分配最大长度 → 碎片多；分页: 按需取块 → 碎片≈0
```"""),

    ("ai", "ai-ch14", "## 链路拆解：版面检测 → 文本识别 →", r"""```text
   图像 → 版面检测(版心/表格) → 文本识别(OCR) → VLM 问答
            │                      │
            └── 失败模式：漏检/错认 ─┘ → 答案幻觉的来源
   成本：识别 + VLM 各算一次；延迟预算要拆成「预处理 / 推理 / 回传」
```"""),
]


def insert(subject: str, chapter: str, h2: str, block: str) -> str:
    d = CONTENT / subject / chapter / "concept"
    for f in sorted(d.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        if h2 in text and "```text" not in text.split(h2, 1)[1].split("\n", 3)[0:1]:
            # 在 h2 行后插入（避免重复插入：检查该 h2 之后是否已含本图标记）
            idx = text.index(h2)
            after = text[idx + len(h2): idx + len(h2) + 400]
            if "ASCII" in after or "```text" in after[:200]:
                return f"skip {f.name} (已含图)"
            new = text[:idx + len(h2)] + "\n\n" + block + "\n" + text[idx + len(h2):]
            f.write_text(new, encoding="utf-8")
            return f"ok {f.name}"
    return f"NO MATCH {chapter}:{h2}"


def main() -> int:
    for subject, ch, h2, block in INS:
        print(insert(subject, ch, h2, block))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
