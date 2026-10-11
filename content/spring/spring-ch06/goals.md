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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [macrozheng/mall](https://github.com/macrozheng/mall) | 84863 | SpringBoot + MyBatis 完整电商项目，最佳工程范例 |
| [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81563 | Spring Boot 官方仓库：源码、文档与示例 |
| [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 39566 | 企业级快速开发平台：Spring Boot + MyBatis Plus 全栈实现 |
| [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37326 | Spring 生态系统化教程代码 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · Spring 5 框架教程 | [视频](https://www.bilibili.com/video/BV1Vf4y127N5/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · SpringMVC 2021 教程 | [视频](https://www.bilibili.com/video/BV1Ry4y1574R/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · MyBatis 实战教程 | [视频](https://www.bilibili.com/video/BV1mW411M737/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 雷丰阳 · SpringBoot2 零基础入门 | [视频](https://www.bilibili.com/video/BV19K4y1L7MT/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Spring Cloud 微服务 | [视频](https://www.bilibili.com/video/BV18E411x7eT/) | 本学科配套视频，建议结合本章示例与习题观看 |
