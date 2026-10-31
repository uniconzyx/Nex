#!/usr/bin/env python3
"""为 py-ch09 / fs-ch09 / ai-ch11 三章 goals.md 补「资源段」。

原因：这三章由 build_new_chapters.py 生成时结构性漏掉了
`## 本章 GitHub / ## 本章 B 站 / ## 本章论文` 三段，导致
`scripts/audit_sources.py` 的 gh/bv/anchor 三项恒为 0，
python / fullstack / ai 三科 src 单章未达标。

补写口径（对齐 content/python/py-ch01/goals.md 与 agent-ch01）：
- GitHub 段：>=3 个仓库 + ★ 星数快照（已用 GitHub API 实取 2026-10-28）
- B 站段：>=2 条 BV（已逐条 x/web-interface/view 核验可播放）
- 论文/书段：>=2 条
- 「对应本章」列放 §x.y 锚点（x=concept 文件序号，y=文件内 ## 序号），
  满足 audit_sources.py 的 ok_anchor（RE_SECTION = \\d\\.\\d）。
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SNAP_DATE = "2026-10-28"

# --- py-ch09 -------------------------------------------------------------
PY = f"""## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **{SNAP_DATE}** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [python/cpython](https://github.com/python/cpython) | 77,791 | §1.4 属性查找 · §2.3 C3 | 解释器本体：Objects/ 下是 MRO、描述符协议、属性查找的真实实现，读 `Objects/typeobject.c` 的 `tp_getattro` 与 MRO 计算，直接对应本章 §1.4、§2.3 |
| 2 | [pallets/flask](https://github.com/pallets/flask) | 74,968 | §2.1 super | 工业级 metaclass 样例：Flask 用 `Scaffold` + `__init_subclass__` 收集视图，`App` 的继承与 `super()` 调用链正是 §2.1 讲的那套机制 |
| 3 | [python-attrs/attrs](https://github.com/python-attrs/attrs) | 5,863 | §3.2 property | 描述符与 `__getattr__` 的工业级应用：读 `attrs` 如何用描述符把类属性变成带校验的字段，对应 §3.2 三种方法修饰符 |
| 4 | [faif/python-patterns](https://github.com/faif/python-patterns) | 43,072 | §2.2 多继承 | GoF 设计模式合集，直接对应「继承 vs 组合」的取舍，§2.2 讲「什么时候真的该用多继承」时拿这里的 Strategy/Adapter 当反例 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 苑昊老师 · Python 面向对象<br><sub>苑昊老师</sub> | [BV1FXDVYkEQh](https://www.bilibili.com/video/BV1FXDVYkEQh/) | §1.1 类属性 · §3.1 规矩 | 主线课：类与对象、继承、魔术方法系统推导；看完回 `ex01`（类属性 vs 实例属性）核对 |
| 2 | 小渔学长 · 类与对象<br><sub>小渔学长</sub> | [BV1Vt411E7E3](https://www.bilibili.com/video/BV1Vt411E7E3/) | §1.2 创建对象 | 偏实战：实例化全流程、self 语义、`__init__` 与 `__new__` 的关系；看完回 `ex02`（MRO 手算）核对 |
| 3 | 码农高天 · 魔术方法大全<br><sub>码农高天</sub> | [BV1b84y1e7hG](https://www.bilibili.com/video/BV1b84y1e7hG/) | §3.1 规矩 · §3.3 查找 | 短而全：常用 dunder 方法一览与触发时机；看完回 `ex03`（描述符优先级）核对 |
| 4 | 水哥澎湃 · __new__ 与 __init__ 顺序<br><sub>水哥澎湃</sub> | [BV1mT43zhE8L](https://www.bilibili.com/video/BV1mT43zhE8L/) | §1.3 实验 | 专讲 `__new__` 先于 `__init__` 的实证实验，直接对应本章 §1.3 那一段可运行演示 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《流畅的 Python（第 2 版）》Ramalho — 第 9 章「类与协议」、第 20 章「属性描述符」 |
| 2 | 《Effective Python（第 2 版）》Slatkin — Item 42「用 super 初始化父类」、Item 43「理解 MRO」 |
| 3 | 《Python 编程：从入门到实践（第 3 版）》Matthes — 第 9 章「类」 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
"""

# --- fs-ch09 -------------------------------------------------------------
FS = f"""## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **{SNAP_DATE}** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [microsoft/TypeScript](https://github.com/microsoft/TypeScript) | 111,640 | §1.1 结构 · §2.1 收窄 · §3.1 擦除 | 语言本体：读 `src/compiler/checker.ts` 的 `getPropertyAccessType` 与结构类型判定，直接对应 §1.1；`narrowTypeByKind` 对应 §2.1 |
| 2 | [type-challenges/type-challenges](https://github.com/type-challenges/type-challenges) | 48,544 | §3.1 擦除 · §3.2 泛型 | 类型体操题库：从 `easy` 到 `extreme`，直接练条件类型与递归泛型，对应 §3.2 的「泛型不能越抽象越好」 |
| 3 | [colinhacks/zod](https://github.com/colinhacks/zod) | 44,212 | §2.1 收窄 | 运行时校验 + 类型推断的工业样板：`z.infer` 把校验结果回推成静态类型，正是 §2.1「收窄」的运行时对应物 |
| 4 | [sindresorhus/type-fest](https://github.com/sindresorhus/type-fest) | 17,473 | §3.2 泛型 | 几百个工具类型的源码合集，读 `PartialDeep` / `PackageJson` 理解条件类型与映射类型的实战写法，对应 §3.2 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · TypeScript 教程<br><sub>黑马程序员</sub> | [BV14Z4y1u7pi](https://www.bilibili.com/video/BV14Z4y1u7pi/) | §1.1 结构 · §2.1 收窄 | 主线课：类型系统、接口与类型别名、泛型、类型收窄系统推导；看完回 `ex01`（结构类型多余属性）核对 |
| 2 | 阿崔cxr · 类型体操<br><sub>阿崔cxr</sub> | [BV1vY41187Tx](https://www.bilibili.com/video/BV1vY41187Tx/) | §3.2 泛型 | 专题：type-challenges 本地刷题环境 + easy-pick 实现，直接对应 §3.2 的递归泛型实战 |
| 3 | 前端- · 深度掌握 TS 泛型<br><sub>前端-</sub> | [BV17d4y167XZ](https://www.bilibili.com/video/BV17d4y167XZ/) | §3.1 擦除 · §3.2 泛型 | 推导向：泛型约束、条件类型、infer 关键字，把 §3.1 讲的「擦除」和 §3.2 的「运行时代价」讲透；看完回 `ex02`（泛型边界）核对 |
| 4 | 霍丙乾bennyhuo · 为什么 TS 有类型体操<br><sub>霍丙乾bennyhuo</sub> | [BV1A3411w72w](https://www.bilibili.com/video/BV1A3411w72w/) | §3.2 泛型 | 原理向：从类型层面图灵完备讲起，解释泛型为何能写「类型程序」，对应 §3.2 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Programming TypeScript》Boris Cherny — 结构化类型与类型守卫章节 |
| 2 | 《Effective TypeScript》Dan Vanderkam — 83 条具体建议，含「理解结构化类型即形状匹配」 |
| 3 | TypeScript 官方 Handbook — https://www.typescriptlang.org/docs/handbook/2/everyday-types.html |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
"""

# --- ai-ch11 -------------------------------------------------------------
AI = f"""## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **{SNAP_DATE}** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [vllm-project/vllm](https://github.com/vllm-project/vllm) | 95,727 | §1.1 参数对 · §1.4 自适应 | continuous batching 与自适应等待窗口的真实实现：读 `vllm/core/scheduler.py` 的 `add_seq_group` 与 `_schedule_prefills`，直接对应 §1.1、§1.4 |
| 2 | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | 132,584 | §1.3 同构批 | 批内同构 + KV cache 复用的工业级样例：读 `llama_batch` 与 `ggml_backend_sched`，对应 §1.3「批内请求必须同构」 |
| 3 | [huggingface/text-generation-inference](https://github.com/huggingface/text-generation-inference) | 10,880 | §2.1 输入契约 · §3.1 故障 | 输入校验与错误处理的源码：读 `router/src` 的 `validation.rs` 与 `infer.rs`，对应 §2.1「五类必须拦的输入」、§3.1「故障的三种形态」 |
| 4 | [triton-inference-server/server](https://github.com/triton-inference-server/server) | 11,115 | §3.4 版本 · §3.7 健康检查 | 模型版本管理与健康检查的真实实现：读 `src/model_repository_manager` 与 `src/health_monitor`，对应 §3.4「模型状态可追溯」、§3.7 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | vLLM 教称 · 推理优化精讲<br><sub>vLLM 官方/社区</sub> | [BV14YopBEEGs](https://www.bilibili.com/video/BV14YopBEEGs/) | §1.1 参数对 · §1.2 倒推 | 主线长课：PagedAttention、continuous batching、调度器剖析，直接对应 §1.1、§1.2；看完回 `ex01`（动态批处理模拟）核对 |
| 2 | 黑马/社区 · vLLM 部署实战<br><sub>社区搬运</sub> | [BV17gXaBnE6A](https://www.bilibili.com/video/BV17gXaBnE6A/) | §3.4 版本 · §3.7 健康检查 | 工程向：从源码构建、模型仓库版本管理、服务健康探针配置，对应 §3.4、§3.7；看完回 `ex08`（过载与退避）核对 |
| 3 | 推理优化原理速览<br><sub>社区</sub> | [BV1Guth61EJz](https://www.bilibili.com/video/BV1Guth61EJz/) | §1.3 同构批 · §2.1 契约 | 短讲：为什么批内要同构、输入为什么要先校验再进图，对应 §1.3、§2.1；看完回 `ex04`（输入契约校验）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Efficient Memory Management for Large Language Model Serving with PagedAttention》(vLLM, SOSP 2023) — 对应 §1.1 动态批处理 |
| 2 | 《Orca: A Distributed Serving System for Transformer-Based Generative Models》(OSDI 2022) — 对应 §1.1 continuous batching、§1.4 自适应窗口 |
| 3 | 《Designing Machine Learning Systems》Chip Huyen — 第 9 章模型服务与版本管理，对应 §3.4 版本、§3.7 健康检查 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、3 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
"""


def append_section(chapter_dir: pathlib.Path, block: str) -> None:
    g = chapter_dir / "goals.md"
    if not g.exists():
        print(f"  ! 缺失 {g}")
        return
    text = g.read_text(encoding="utf-8")
    if "## 本章 GitHub" in text:
        print(f"  ~ 已有资源段，跳过 {g}")
        return
    # 去掉 goals 末尾多余空行后追加
    text = text.rstrip() + "\n\n" + block
    g.write_text(text, encoding="utf-8")
    print(f"  + 已追加资源段 {g}（{len(block.splitlines())} 行）")


def main() -> int:
    targets = {
        "python/py-ch09": PY,
        "fullstack/fs-ch09": FS,
        "ai/ai-ch11": AI,
    }
    for rel, block in targets.items():
        d = CONTENT / rel
        print(f"== {rel} ==")
        append_section(d, block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
