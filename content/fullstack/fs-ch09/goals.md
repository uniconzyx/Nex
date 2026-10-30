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
