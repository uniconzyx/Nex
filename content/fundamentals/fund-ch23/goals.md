# fund-ch23 · 数据链路层

> 一句话引出：物理层把「0 和 1」送到对面，可对面怎么知道「从哪一位开始算一帧、这一帧有没有被电磁干扰打坏」？

## 一、知识目标

1. 说清链路层的**三个基本问题**：组帧（framing）、差错控制（error control）、流量控制（flow control），以及它们各自解决「哪一段边界上」的问题。
2. 掌握三种组帧方法的原理与**自恢复能力**差异：字符计数法、字节填充（PPP）、零比特填充（HDLC），并知道「违规编码法」的用法。
3. 掌握差错控制的三层手段：奇偶校验（1 位检错）、CRC（强检错）、海明码（纠 1 位），能徒手做 CRC 模 2 除法、能按 `2^r >= k+r+1` 求最少校验位、能写指误字。
4. 掌握流量控制与可靠传输三协议：停等、后退 N 帧（GBN）、选择重传（SR），能算信道利用率，能判断「给定序号位数 n，窗口最大取多少」，理解 GBN 为什么不能取 `W = 2^n`。
5. 掌握介质访问控制（MAC）的三类方法：信道划分（FDM/TDM/WDM/CDM）、随机访问（ALOHA、时隙 ALOHA、CSMA、CSMA/CD、CSMA/CA）、轮询访问（令牌传递），能算 ALOHA 吞吐上限、能算 CSMA/CD 最小帧长与争用期。
6. 掌握以太网与交换：MAC 帧格式与 64/1518 字节边界、交换机自学习与泛洪、冲突域 vs 广播域、VLAN（802.1Q）的 4 字节开销。
7. 能区分「链路层的可靠传输」与「传输层的可靠传输」各自解决什么问题，理解为什么以太网选择「检错 + 丢弃 + 上层重传」而不是「纠错」。

## 二、能力目标

- 能给一段原始比特流做零比特填充、再正确还原（含边界情况：恰好 5 个 1、连续 6 个 1）。
- 能用生成多项式手算 CRC 余数，并在接收端用「整帧除以 G 余数为 0」验证。
- 能给一组冲突次数算出二进制指数退避的平均等待时间，并解释「为什么重载时越堵越慢」。
- 能根据速率与 2τ 反推最小帧长，或根据最小帧长反推最大跨距，并说明为什么标准值比理论上限小。
- 能在抓包文件里指出「前导码 / 目的 MAC / 源 MAC / 类型 / 载荷 / FCS」各自的字节区间，并解释 VLAN Tag 插在哪两个字段之间。

## 三、三视角导航

| 视角 | 本章重点 |
|---|---|
| 🧑‍💻 程序员 | 抓包时看到的每一层封装；`ethtool`/`ip -s link` 里的 CRC 错误与丢弃计数；交换机泛洪导致的「同网段广播风暴」；容器网络（veth/bridge）为什么本质是软件交换机 |
| 🎓 博士生 | 为什么链路层把复杂度压到「检错不纠错」（端到端原则）；ALOHA→CSMA→CSMA/CD 的吞吐上界推导；GBN/SR 的窗口约束来自「序号空间必须大于在途帧数」这一信息论要求 |
| 📚 考研者 | 408 高频：三种组帧法对比、CRC 计算、海明码求 r 与指误字、GBN/SR 窗口上限、ALOHA 吞吐、CSMA/CD 最小帧长、交换机自学习与 VLAN、冲突域/广播域计数 |

## 四、前置

本章前置：fund-ch22（物理层：码元、奈氏/香农、编码、传输介质）。
本章是 fund-ch11（分层模型与 TCP/IP）的**下层细化**，也是 fund-ch12（应用层）链路的最底端一环；与 fund-ch04（图）无直接依赖，但 Kruskal/并查集（fund-ch18）在「生成树协议 STP」里会再次出现。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 2026-10-29 GitHub REST API 实取星数快照（星数每日漂移，取到即为准）。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [lwip-tcpip/lwip](https://github.com/lwip-tcpip/lwip) | 1773 | §1.2 组帧 / §4.4 以太网帧 | 读 `src/netif/ethernet.c` 的 `ethernet_input`：它先检查 `len >= SIZEOF_ETH_HDR`，再按 type 分发——「帧太短直接丢」在代码里只有一行，却对应本章的最小帧长约束；配套看 `src/core/ipv4/etharp.c` 的 ARP 表，就是「MAC 地址怎么被学出来」 |
| 2 | [wireshark/wireshark](https://github.com/wireshark/wireshark) | 10134 | §4.4 以太网帧结构 | 读 `epan/dissectors/packet-eth.c`：字段注册顺序就是教材帧格式的顺序（dst/src/type），VLAN 用 `packet-vlan.c` 单独一层 dissector 插进去——「4 字节 Tag 插在哪」一看便知 |
| 3 | [the-tcpdump-group/tcpdump](https://github.com/the-tcpdump-group/tcpdump) | 3256 | §4.4 帧解析与截断 | 读 `print-ether.c` 的 `ether_print`：它先打印长度、再判 `caplen < ETHER_HDRLEN` 就报 `[|ether]`——这正是「抓包丢失尾部导致无法校验 FCS」的现场 |
| 4 | [torvalds/linux](https://github.com/torvalds/linux) | 254007 | §4.5 交换机与网桥 | 读 `net/core/dev.c` 的 `netif_receive_skb` 与 `net/bridge/br_fdb.c`：前者是「帧进入协议栈的总入口」，后者是**软件交换机 MAC 表**（`br_fdb_update` 更新、老化由 `br_fdb_cleanup` 定时器做）——交换机自学习在这里是几十行 C |
| 5 | [mininet/mininet](https://github.com/mininet/mininet) | 5875 | §4.5 冲突域与实验 | 读 `mininet/link.py` 与 `mininet/node.py` 的 `OVSBridge`：用 `tc` 给链路注入带宽/延迟/丢包，用 OVS 做交换机——把本章的「最小帧长、争用期、退避」放进可控环境里实测 |

## 本章 B 站视频路线

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 王道 · 计算机网络（考研） | [BV19E411D78Q](https://www.bilibili.com/video/BV19E411D78Q/) | 全章 | 组帧、差错控制、流量控制、介质访问控制逐节精讲（408 主线） |
| 2 | 王道 · 操作系统（考研） | [BV1YE411D7nH](https://www.bilibili.com/video/BV1YE411D7nH/) | §4.5 缓冲类比 | 用「缓冲区/队列」类比滑动窗口与交换机缓存 |
| 3 | 王道 · 计算机组成原理 | [BV1BE411D7ii](https://www.bilibili.com/video/BV1BE411D7ii/) | §4.3 CSMA/CD 时序 | 总线仲裁与冲突检测的硬件时序视角 |
| 4 | 王道 · 数据结构（考研） | [BV1b7411N798](https://www.bilibili.com/video/BV1b7411N798/) | §4.5 STP | 生成树协议用到的图论基础（最小生成树） |

## 本章配套论文与书

| # | 文献 / 章节 |
|---|---|
| 1 | 《计算机网络（第 8 版）》谢希仁 · 第 3 章 数据链路层 |
| 2 | 《计算机网络：自顶向下方法（第 8 版）》Kurose & Ross · 第 6 章 The Link Layer and LANs |
| 3 | 《数据通信与网络（第 5 版）》Forouzan · 第 11 章 Data Link Control、第 12 章 Multiple Access |
| 4 | Metcalfe R. M., Boggs D. R. *Ethernet: Distributed Packet Switching for Local Computer Networks*, CACM 1976（以太网原始论文，CSMA/CD 的出处） |
| 5 | Saltzer J., Reed D., Clark D. *End-to-End Arguments in System Design*, ACM TOCS 1984（解释「为什么链路层只检错不纠错」） |
