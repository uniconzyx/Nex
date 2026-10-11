# java-ch06 · IO 与 NIO

## 一、为什么单独学一章 IO

Java 的 IO 是**面试密度最高、工程出事最多**的一块：
文件句柄泄漏、编码乱码、序列化漏洞、`read()` 返回 -1 被忽略导致死循环、
大文件一次性读进内存 OOM —— 这些都不是语法问题，而是「模型没建立起来」。

本章把 IO 拆成四条主线，每条都能独立落地：

| 主线 | 核心问题 | 典型事故 |
|---|---|---|
| 字节流 / 字符流 | 编码发生在哪一层？ | 中文乱码、跨平台不一致 |
| Path / Files | 路径怎么算才对？遍历怎么不爆栈？ | 路径拼接错误、资源未关 |
| Channel / Buffer / Selector | 如何不靠线程堆并发？ | Buffer 状态用错、数据截断 |
| 序列化与 IO 模型 | 什么能序列化、什么绝不该序列化？ | 反序列化 RCE、性能踩坑 |

## 二、学习目标

### 基础层（必须达成）
1. 能说清 `InputStream`/`OutputStream` 与 `Reader`/`Writer` 的分工边界，
   并指出**编码转换发生在桥接点**（`InputStreamReader`/`OutputStreamWriter`）。
2. 熟练使用 try-with-resources 管理任意 `AutoCloseable`，理解关闭顺序与 suppressed 异常。
3. 能用 `Path` + `Files` 完成：读写文本、遍历目录、查询属性、原子移动。

### 进阶层（面试重点）
4. 讲清 `ByteBuffer` 的 position/limit/capacity 三个游标在
   `put → flip → get → clear/compact` 全过程的变化，并解释**为什么忘写 `flip()` 会读出 0 字节**。
5. 讲清 Selector 多路复用的工作方式：注册 → `select()` → 就绪集合 → 处理 → 迭代器移除。
6. 说出 `transferTo` 为什么快（避免用户态与内核态之间的重复拷贝）。

### 工程层（就业刚需）
7. 知道 `FileReader`/`FileWriter` 使用**平台默认编码**，因此线上必须显式指定 charset。
8. 知道 `ObjectInputStream.readObject()` 对不可信数据是**远程代码执行风险面**，
   并给出替代方案（JSON / Protobuf + 白名单）。
9. 能按场景选型：BIO / NIO / AIO / 虚拟线程，以及各自的适用边界。

## 三、前置

- `java-ch01` 语法与面向对象（接口、抽象类、泛型基础）
- `java-ch05` 异常与 try-with-resources（本章大量复用）

## 四、交付物（学完应能独立写出）

- 一个「逐行处理大文件且内存恒定」的工具（`BufferedReader` + 流式聚合）
- 一个「目录扫描 + 属性过滤 + 原子替换」的批处理脚本
- 一个「单线程 Selector 回显服务」的最小实现
- 一份「为什么日志里出现了乱码」的排查清单

## 五、常见误区（先立靶子）

1. 以为 `Reader` 读出来就一定是「对的」——其实取决于构造时用的 charset。
2. 以为 `BufferedReader` 只是为了快——它真正的语义价值是**按行读取**与**减少系统调用**。
3. 以为 `ByteBuffer.flip()` 是可有可无的「习惯」——它是读写模式切换的唯一开关。
4. 以为 `Serializable` 只是个空接口、随便实现——它等于对外暴露了**对象图的完全控制权**。


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159056 | Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计 |
| [macrozheng/mall](https://github.com/macrozheng/mall) | 84863 | SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例 |
| [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79141 | 互联网 Java 工程师进阶知识：高并发、分布式、微服务 |
| [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37326 | Spring 官方生态的系统化代码教程仓库 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · Java 零基础（宋红康） | [视频](https://www.bilibili.com/video/BV1Qb411g7cz/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚学堂 · 高淇 Java 300 集 | [视频](https://www.bilibili.com/video/BV1ct411n7oG/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 求知课堂 · Java 入门到精通 | [视频](https://www.bilibili.com/video/BV1CJ411m7gg/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · 谷粒商城（分布式实战项目） | [视频](https://www.bilibili.com/video/BV1np4y1C7Yf/) | 本学科配套视频，建议结合本章示例与习题观看 |
