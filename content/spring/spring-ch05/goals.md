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
