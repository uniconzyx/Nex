# spring-ch06 学习目标：MyBatis 基础：映射与 CRUD

## 一、本章定位

`spring-ch05` 解决了「HTTP 请求如何变成业务调用」。`spring-ch06` 继续往下，
解决「Java 对象如何与关系数据库互相转换」——也就是持久层。本章聚焦 MyBatis：
一个「半自动」ORM，把 SQL 控制权交还开发者，同时自动完成参数绑定与结果映射。

## 二、知识目标

1. 理解 MyBatis 的「半自动 ORM」定位，以及 SqlSession 与 Mapper 接口的动态代理绑定机制；
2. 掌握 `#{}` 预编译占位符与 `${}` 字符串拼接的本质差异，并能据此解释 SQL 注入根因；
3. 掌握 `resultType` 自动映射、`resultMap` 显式映射、驼峰映射（mapUnderscoreToCamelCase）与关联映射；
4. 掌握主键回填（`useGeneratedKeys` / `<selectKey>`）与 `insert` 返回值语义；
5. 理解 XML 映射与注解两种写法的归一（都生成 MappedStatement），以及全局 `<settings>` 的作用。

## 三、能力目标

- 能用**纯 Python**从零模拟 MyBatis 核心机制：Mapper XML 解析、#{} 与 ${} 替换语义、
  PreparedStatement 占位符绑定、ResultMap/驼峰映射、CRUD 的 SQL 生成、
  动态 SQL 标签解析、一级/二级缓存命中与失效、插件责任链的环绕执行顺序；
- 能针对「SQL 注入」「字段映射为 null」「主键拿不到」「缓存读到旧值」等真实事故给出根因与修法。

## 四、学习路径建议

1. 先读 `concept/01`（定位与 Mapper 绑定）、`concept/02`（#{} 与 ${} / 注入）；
2. 再读 `concept/03`（resultMap / 驼峰 / 关联）、`concept/04`（主键回填 / 配置）；
3. 跑 `examples/` 的 12 个纯 Python 示例，每个都可独立 `python main.py`；
4. 用 `exercises.json` / `interview.json` / `project.json` 自测。

## 五、前置知识

- `spring-ch01`：IoC/DI 与 Mapper 注入的容器基础；
- 软前置（可选，不阻断学习）：`java-ch04` Java 集合与泛型（若已掌握可跳过）。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | 全章 | SpringBoot + MyBatis 完整电商项目，最佳工程范例；本章先读与「半自动 ORM 的定位与…」「与 JDBC / JPA…」相关的部分 |
| 2 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81,772 | 全章 | Spring Boot 官方仓库：源码、文档与示例；本章先读与「半自动 ORM 的定位与…」「与 JDBC / JPA…」相关的部分 |
| 3 | [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 40,149 | 全章 | 企业级快速开发平台：Spring Boot + MyBatis Plus 全栈实现；本章先读与「半自动 ORM 的定位与…」「与 JDBC / JPA…」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | 全章 | Spring 生态系统化教程代码；本章先读与「半自动 ORM 的定位与…」「与 JDBC / JPA…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Spring 框架（源码级）<br><sub>尚硅谷</sub> | [BV1Vf4y127N5](https://www.bilibili.com/video/BV1Vf4y127N5/) | §1.1 半自动 ORM 的定位与… | IoC 容器启动流程、Bean 生命周期、AOP 代理与事务传播：每节都对着源码讲，看完能回答「@Autowired 到底怎么注进去的」；看完回 `ex01`（ex01-xml-mapper-pars）核对 |
| 2 | 黑马程序员 · SSM 框架全套<br><sub>黑马程序员</sub> | [BV1WZ4y1P7Bp](https://www.bilibili.com/video/BV1WZ4y1P7Bp/) | 全章 | Spring + SpringMVC + MyBatis 三件套打通：MyBatis 的 Mapper 代理绑定与动态 SQL 在这里最清楚；看完回 `ex02`（ex02-hash-vs-dollar）核对 |
| 3 | 尚硅谷 · SpringBoot 2 零基础<br><sub>尚硅谷</sub> | [BV19K4y1L7MT](https://www.bilibili.com/video/BV19K4y1L7MT/) | 全章 | 自动配置原理（@Conditional 家族 + imports 文件）、起步依赖、内嵌容器与配置优先级；看完回 `ex03`（ex03-sql-injection-d）核对 |
| 4 | 尚硅谷 · SpringCloud 微服务<br><sub>尚硅谷</sub> | [BV18E411x7eT](https://www.bilibili.com/video/BV18E411x7eT/) | 全章 | 分布式事务、服务治理与配置中心；只在讲「多数据源/分布式」时选看，不必通读；看完回 `ex04`（ex04-preparedstateme）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Spring 实战（第 6 版）》Walls |
| 2 | 《Spring Boot 编程思想》小马哥 |
| 3 | 《MyBatis 从入门到精通》刘增辉 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
