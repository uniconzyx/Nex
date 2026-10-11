# fund-ch11 · 计算机网络：分层模型与 TCP/IP · 学习目标

- 掌握 **OSI 七层**与 **TCP/IP 四层（五层教学模型）**的对应关系、各层 **PDU 名称**、典型协议与典型设备
- 能完整描述**封装（encapsulation）与分用（demultiplexing）**过程，并算出每层的**首部开销**与**有效载荷率**
- 掌握**数据链路层**的成帧方法、差错控制（**奇偶校验 / 海明码 / CRC**）的检错纠错能力对比
- 掌握**以太网帧格式**（前导码、目的/源 MAC、类型、数据、FCS）与 **MTU 1500** 的意义，理解 **CSMA/CD** 与交换机的**自学习 + 泛洪**
- 掌握 **IPv4 编址**：分类地址、**子网划分与子网掩码**、**CIDR 与路由聚合**，能算网络地址、广播地址、可用主机数与网段归属
- 掌握**最长前缀匹配（longest prefix match）**的路由查找规则，理解 **ARP 解析**与 **DHCP** 的工作过程
- 掌握 **ICMP** 的差错报告（类型 3/4/5/11）与询问报文（`ping`、`traceroute` 的实现原理）
- 掌握 **TCP 首部字段**与**连接管理**：三次握手、四次挥手、TIME_WAIT、SYN 洪泛与半连接队列
- 掌握 TCP **可靠传输**：序号/确认号、超时重传、**RTT 估计（Jacobson/Karels 与 Karn 算法）**、快速重传
- 掌握 TCP **流量控制**（滑动窗口、零窗口探测、糊涂窗口综合征与 Nagle）与 **拥塞控制**（慢启动、拥塞避免、快重传、快恢复、Reno/CUBIC/BBR）
- 掌握 **UDP** 的特性与适用场景，理解 **QUIC** 为什么在用户态重新实现可靠传输
- 能读懂一次真实抓包的关键字段，并说明**一次 HTTP 请求背后发生了多少次 TCP 交互**

## 前置
- 无（本章可独立学习；如需抓包实操，参考 tool-ch02 Linux 命令）

## 学习资源（GitHub star 最高）
- [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) —— 网络与协议在系统设计中的位置
- [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) —— 网络分层与 TCP/IP 自学路径
- [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) —— 中文网络面试核心考点

## 推荐书目
- 《计算机网络》谢希仁 第 1~5 章
- 《TCP/IP 详解 卷1：协议》

## 验收标准
- 能画出「应用数据 → 报文段 → 数据报 → 帧」的封装图，并标出每层首部与 MTU 限制
- 给定 `192.168.10.130/26`，能算出网络地址、广播地址、可用主机数与该网段范围
- 给定一张含多条前缀的路由表与一个目的 IP，能说出选中的下一跳及理由（最长前缀匹配）
- 能画出 TCP 三次握手/四次挥手的报文序列，标出 `seq`/`ack`/`SYN`/`FIN`/`ACK` 与两端状态迁移
- 能说明 `TIME_WAIT` 为什么必须等 **2MSL**，并列举三个工程影响（端口耗尽、`SO_REUSEADDR`、服务重启）
- 给定 `cwnd` 初值、`ssthresh` 与丢包时机，能画出 `cwnd` 随时间的变化曲线并说明各阶段
- 能用 RTT 估计公式算出新的 `RTO`（`RTTs`、`RTTd` 的更新过程）
- 能解释「为什么 TCP 不能在 UDP 上简单复刻」（拥塞控制与内核态/用户态的权衡）


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 373461 | 系统设计入门：性能、一致性、可用性与面试题（408 之上的系统视野） |
| [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 362479 | 完整的计算机科学自学计划：数据结构、算法、OS、网络全覆盖 |
| [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186393 | 中文技术面试必备：操作系统、计算机网络、组成原理、算法、数据库 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 青岛大学 · 王卓 数据结构与算法 | [视频](https://www.bilibili.com/video/BV1nJ411V7bd/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 王道考研 · 计算机组成原理 | [视频](https://www.bilibili.com/video/BV1ps4y1d73V/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 哈工大 · 李治军 操作系统 | [视频](https://www.bilibili.com/video/BV1d4411v7u7/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 湖南科技大学 · 计算机网络微课堂 | [视频](https://www.bilibili.com/video/BV1c4411d7jb/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 清华 · 邓俊辉 数据结构与算法 | [视频](https://www.bilibili.com/video/BV1jt4y117KR/) | 本学科配套视频，建议结合本章示例与习题观看 |
