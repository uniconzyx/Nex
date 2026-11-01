# spring-ch05 学习目标：Web 层：REST 控制器与参数校验

## 一、本章定位

`spring-ch04` 解决了「容器如何自动把 Bean 备好」。`spring-ch05` 解决的是更靠外的
一层：**一个 HTTP 请求是怎么从「`/`」一路走到你的业务方法，又怎么变成一个 JSON 响应的**。

这一层叫 Web 层 / 表现层，核心是三件事：

1. **路由与映射**：`@RestController` + `@RequestMapping` 把「HTTP 方法 + 路径」绑定到方法；
2. **参数绑定与校验**：把请求体 / 路径 / 查询串变成 Java 对象，并用 Bean Validation 守住边界；
3. **统一出口**：用 `@ControllerAdvice` 做全局异常处理、用 DTO 隔离实体，保证对外契约稳定。

## 二、知识目标

1. 能说清 `@RestController` = `@Controller` + `@ResponseBody`，以及 `@RequestMapping`
   系列注解（类级前缀 + 方法级子路径 + method/produces/consumes）的匹配语义。
2. 掌握三类参数绑定的差异：`@RequestParam`（查询串 / 表单）、`@PathVariable`（路径变量）、
   `@RequestBody`（请求体 JSON），以及内容协商如何选消息转换器。
3. 掌握 Bean Validation（JSR-303/380）的**元数据模型**：约束注解 + `ConstraintValidator`，
   以及分组校验、级联校验 `@Valid`，并理解「为何不加 `@Valid` 校验不生效」。
4. 能列出常用 HTTP 状态码的适用场景（200/201/204/400/401/403/404/405/409/422/500），
   并据此设计**幂等**接口（PUT 幂等、POST 不幂等）。
5. 掌握 `@ControllerAdvice` + `@ExceptionHandler` 的全局异常→状态码映射，
   以及 DTO 与实体分离（防止 `password` 等敏感字段泄露）的工程纪律。

## 三、能力目标

- 能用**纯 JDK**手写一个迷你 Web 层：路由分发器（方法+路径匹配、路径变量提取、查询串解析）、
  参数绑定与类型转换失败返回 400、JSR-303 风格反射校验器、状态码语义表、
  幂等判据、内容协商（Accept→JSON/XML）、全局异常处理器、DTO 映射器（字段裁剪）。
- 能针对「重复提交」「跨域预检被拦」「校验不生效」「状态码乱用」等真实事故给出根因与修法。

## 四、学习路径建议

1. 先读 `concept/01`（REST 语义与映射、状态码与幂等），建立全图景；
2. 再读 `concept/02`（参数绑定与内容协商）、`concept/03`（校验元数据模型与分组）；
3. 最后读 `concept/04`（全局异常处理与 DTO 隔离）；
4. 跑 `examples/` 的 12 个纯 JDK 示例，每个都可独立 `javac`/`java`；
5. 用 `exercises.json` / `interview.json` / `project.json` 自测。

## 五、前置知识

- `spring-ch04`：SpringBoot 自动配置（内嵌容器如何启动、DispatcherServlet 如何被注册）。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,863 | 全章 | SpringBoot + MyBatis 完整电商项目，最佳工程范例；本章先读与「@RestControll…」「状态码选择与第一性的幂等性」相关的部分 |
| 2 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81,772 | 全章 | Spring Boot 官方仓库：源码、文档与示例；本章先读与「@RestControll…」「状态码选择与第一性的幂等性」相关的部分 |
| 3 | [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 40,081 | 全章 | 企业级快速开发平台：Spring Boot + MyBatis Plus 全栈实现；本章先读与「@RestControll…」「状态码选择与第一性的幂等性」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,326 | 全章 | Spring 生态系统化教程代码；本章先读与「@RestControll…」「状态码选择与第一性的幂等性」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Spring 框架（源码级）<br><sub>尚硅谷</sub> | [BV1Vf4y127N5](https://www.bilibili.com/video/BV1Vf4y127N5/) | 全章 | IoC 容器启动流程、Bean 生命周期、AOP 代理与事务传播：每节都对着源码讲，看完能回答「@Autowired 到底怎么注进去的」；看完回 `ex01`（ex01-router-basic）核对 |
| 2 | 黑马程序员 · SSM 框架全套<br><sub>黑马程序员</sub> | [BV1WZ4y1P7Bp](https://www.bilibili.com/video/BV1WZ4y1P7Bp/) | §1.1 @RestControll… | Spring + SpringMVC + MyBatis 三件套打通：MyBatis 的 Mapper 代理绑定与动态 SQL 在这里最清楚；看完回 `ex02`（ex02-path-variable）核对 |
| 3 | 黑马程序员 · JavaWeb（含 Spring+MyBatis）<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | 全章 | 工程视角：分层、DTO/VO、统一响应与异常处理；事务与多数据源在最后几章；看完回 `ex03`（ex03-query-parse）核对 |
| 4 | 尚硅谷 · SpringBoot 2 零基础<br><sub>尚硅谷</sub> | [BV19K4y1L7MT](https://www.bilibili.com/video/BV19K4y1L7MT/) | 全章 | 自动配置原理（@Conditional 家族 + imports 文件）、起步依赖、内嵌容器与配置优先级；看完回 `ex04`（ex04-binding-failure）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Spring 实战（第 6 版）》Walls |
| 2 | 《Spring Boot 编程思想》小马哥 |
| 3 | 《MyBatis 从入门到精通》刘增辉 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
