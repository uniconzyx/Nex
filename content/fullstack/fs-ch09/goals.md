# fs-ch09 · TypeScript：结构化类型、泛型与类型收窄 · 学习目标

- 能讲清「结构类型：形状对了就是对的」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「类型收窄与穷尽性检查」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「泛型、条件类型与它们的运行时代价」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 7 道题（含 2 道编程题）与 4 条错题辨析，并能复述 5 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-28** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [microsoft/TypeScript](https://github.com/microsoft/TypeScript) | 111,640 | §1.1 为什么这样设计 | 读 `microsoft/TypeScript` 仓库的 `src/compiler/`（核心文件是 `checker.ts`）：里面的 `getPropertyAccessType` 与结构类型判定直接对应本节——TS 判「A 能否赋给 B」只看 B 要求的属性在 A 上是否存在且类型相容，完全不看声明关系；这解释了本章 §1.4「结构类型的三个边界反例」里「空对象 `{}` 能赋给几乎所有接口」为什么成立 |
| 2 | [type-challenges/type-challenges](https://github.com/type-challenges/type-challenges) | 48,544 | §2.1 收窄的几种来源 | 先从 `type-challenges/type-challenges` 的 `easy` 到 `extreme` 练条件类型与递归泛型，再回 `src/compiler/` 的 `checker.ts` 读 `narrowTypeByKind`：题库让你先建立「类型是可以在编译期被计算的」直觉，源码告诉你收窄发生在 `if` / `typeof` / 判别式（`tagged union`）三个入口；配合 §2.2「为什么 `any` 是逃生舱而不是工具」——`any` 一旦进入表达式，后面的收窄全部失效，因为它的每个属性访问都是 `any` |
| 3 | [colinhacks/zod](https://github.com/colinhacks/zod) | 44,212 | §2.1 收窄的几种来源（运行时对应物） | 读 `colinhacks/zod`：`z.infer` 把校验结果回推成静态类型，正是本节「收窄」的运行时对应物——编译期的收窄只是「你怎么向编译器证明」，而 zod 是「你怎么向编译器证明这段外部数据确实是这个形状」；本章 §4.2「收尾：类型是文档，也是约束，但不是保证」说的就是这件事：没有运行时校验时，类型在边界上是一句无凭据的断言 |
| 4 | [sindresorhus/type-fest](https://github.com/sindresorhus/type-fest) | 17,473 | §3.2 泛型不是越抽象越好 | 读 `sindresorhus/type-fest` 的几百个工具类型源码：先读 `PartialDeep` / `PackageJson` 理解条件类型与映射类型的实战写法，再回头看它为什么为每一个小场景单独出一个类型（而不是做一个万能 `Deep<T>`）——那就是本节「泛型不是越抽象越好」的证据：抽象层级每上一级，报错信息的可读性与推导性能都会下降 |

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
